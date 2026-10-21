"""Phase-0 LIVE prototype (scratch, not repo code): Stremio subtitles addon that generates
Romanian subtitles for whatever the TV plays.

TV -> addon /subtitles/... (filename, videoSize, videoHash) -> match the engine in the local
server's /stats.json -> background job: 120 s audio chunks from the stream -> Whisper turbo
(mlx) -> Claude Haiku via the `claude` CLI (subscription) -> SRT served at /live/<ih>-<idx>.srt.
The track is re-fetched each time it is re-selected on the TV, so re-selecting refreshes it.
"""

import json
import re
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

import mlx_whisper
import numpy as np

LAN_IP, PORT = sys.argv[1], int(sys.argv[2])
SERVER = "http://127.0.0.1:11470"
MODEL = "mlx-community/whisper-large-v3-turbo"
CHUNK_S, OVERLAP_S = 120, 2
OUT = Path("/tmp/stremio-companion-live/out")
OUT.mkdir(exist_ok=True)
MAX_LINE, MAX_LINES = 42, 2
SCHEMA = json.dumps({
    "type": "object",
    "properties": {"cues": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "ro": {"type": "string"}},
        "required": ["id", "ro"], "additionalProperties": False}}},
    "required": ["cues"], "additionalProperties": False})
SYSTEM = (
    "You translate English TV subtitles into natural, idiomatic Romanian as a professional "
    "subtitler would: correct diacritics (ă â î ș ț), concise, colloquial where the speech is, "
    "keep names, keep profanity at the same strength. You get numbered cues; return exactly one "
    "translation per id, same ids, no merging or splitting. Earlier cues are given only as context."
)
LOCK = threading.Lock()  # one Whisper inference at a time (GPU)
# Subscription guardrails: personal use, one CLI call at a time, hard hourly cap.
CLAUDE_LOCK = threading.Lock()
MAX_CALLS_PER_HOUR = 120
CALL_TIMES: list[float] = []


def claude_slot() -> None:
    while True:
        now = time.time()
        CALL_TIMES[:] = [t for t in CALL_TIMES if now - t < 3600]
        if len(CALL_TIMES) < MAX_CALLS_PER_HOUR:
            CALL_TIMES.append(now)
            return
        log(ev="claude-cap-wait", calls_last_hour=len(CALL_TIMES))
        time.sleep(60)


def log(**kw: object) -> None:
    print(json.dumps({"t": time.strftime("%H:%M:%S"), **kw}, ensure_ascii=False), flush=True)


def ts(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def wrap(text: str) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > MAX_LINE:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    if len(lines) > MAX_LINES:  # rebalance into two lines rather than drop words
        half = len(words) // 2
        lines = [" ".join(words[:half]), " ".join(words[half:])]
    return "\n".join(lines)


@dataclass
class Job:
    ih: str
    idx: int
    name: str
    audio_index: int = 0
    center: bool = False
    cues: list[dict] = field(default_factory=list)  # {start, end, en, ro}
    ready_to: float = 0.0
    done: bool = False
    error: str | None = None

    @property
    def url(self) -> str:
        return f"{SERVER}/{self.ih}/{self.idx}"

    @property
    def srt_path(self) -> Path:
        return OUT / f"{self.ih}-{self.idx}.ro.srt"


JOBS: dict[tuple[str, int], Job] = {}


def probe(job: Job) -> None:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-rw_timeout", "60000000", "-select_streams", "a",
         "-show_entries", "stream=index,channels,channel_layout:stream_tags=language,title:stream_disposition=default",
         "-of", "json", job.url], capture_output=True, text=True, timeout=120).stdout
    streams = json.loads(out or "{}").get("streams", [])
    def rank(s: dict) -> tuple[int, int]:
        tags = s.get("tags", {})
        if "comment" in tags.get("title", "").lower():
            return (9, 9)
        return (0 if tags.get("language") == "eng" else 1, 0 if s.get("disposition", {}).get("default") else 1)
    if streams:
        best = sorted(enumerate(streams), key=lambda p: rank(p[1]))[0]
        job.audio_index, s = best
        job.center = "FC" in (s.get("channel_layout") or "").upper() or s.get("channels", 2) >= 6
    log(ev="probe", file=job.name, audio_index=job.audio_index, center=job.center, streams=len(streams))


def transcribe(audio: np.ndarray, start: float) -> list[dict]:
    with LOCK:
        res = mlx_whisper.transcribe(
            audio, path_or_hf_repo=MODEL, language="en", task="transcribe", temperature=0.0,
            condition_on_previous_text=False, hallucination_silence_threshold=2.0,
            word_timestamps=True, verbose=None)
    return [{"start": start + s["start"], "end": start + s["end"], "en": s["text"].strip()}
            for s in res["segments"] if s["text"].strip()]


def translate(batch: list[dict], context: list[dict]) -> list[str]:
    ctx = "\n".join(f"{c['en']}" for c in context[-15:])
    body = "\n".join(f"{i + 1}: {c['en']}" for i, c in enumerate(batch))
    prompt = (f"Context (earlier lines, do not translate):\n{ctx}\n\n" if ctx else "") + f"Translate:\n{body}"
    for attempt in range(3):
        with CLAUDE_LOCK:
            claude_slot()
            r = subprocess.run(
            ["claude", "-p", "--model", "claude-haiku-5-5", "--tools", "", "--strict-mcp-config",
             "--setting-sources", "", "--no-session-persistence", "--system-prompt", SYSTEM,
             "--json-schema", SCHEMA, "--output-format", "json"],
                input=prompt, capture_output=True, text=True, timeout=180)
        try:
            d = json.loads(r.stdout)
            got = {c["id"]: c["ro"] for c in (d.get("structured_output") or {}).get("cues", [])}
            if all(i + 1 in got for i in range(len(batch))):
                return [got[i + 1] for i in range(len(batch))]
            log(ev="translate-missing-ids", attempt=attempt, got=len(got), want=len(batch))
        except (json.JSONDecodeError, AttributeError) as e:
            log(ev="translate-error", attempt=attempt, err=repr(e)[:120], stderr=r.stderr[:200])
    return [c["en"] for c in batch]  # last resort: keep English rather than a hole


def write_srt(job: Job) -> None:
    lines = []
    for n, c in enumerate(job.cues, 1):
        lines.append(f"{n}\n{ts(c['start'])} --> {ts(c['end'])}\n{wrap(c.get('ro') or c['en'])}\n")
    tmp = job.srt_path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    tmp.replace(job.srt_path)


def read_exact(stream, n: int, deadline_s: float) -> bytes:
    """Read n bytes from the ffmpeg pipe; a wall-clock watchdog, since partial-torrent reads can idle forever."""
    buf, t0 = bytearray(), time.time()
    while len(buf) < n:
        part = stream.read1(n - len(buf)) if hasattr(stream, "read1") else stream.read(n - len(buf))
        if not part:
            break
        buf += part
        if time.time() - t0 > deadline_s:
            raise TimeoutError(f"audio stalled after {len(buf)} bytes")
    return bytes(buf)


def run(job: Job) -> None:
    try:
        probe(job)
        # One continuous audio-only decode (no seeking: an MKV index at the tail would force tail pieces).
        af = ["-af", "pan=mono|c0=FC"] if job.center else ["-ac", "1"]
        ff = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-rw_timeout", "300000000", "-i", job.url, "-map", f"0:a:{job.audio_index}",
             "-vn", "-sn", "-dn", *af, "-ar", "16000", "-f", "s16le", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        assert ff.stdout is not None
        start, tail = 0.0, np.zeros(0, np.float32)
        while True:
            t0 = time.time()
            raw = read_exact(ff.stdout, CHUNK_S * 16000 * 2, deadline_s=600)
            t_audio = time.time() - t0
            fresh = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
            if fresh.size < 16000:
                break
            audio = np.concatenate([tail, fresh])  # prepend overlap so a word cut at the boundary survives
            offset = start - tail.size / 16000
            segs = [s for s in transcribe(audio, offset) if s["start"] >= job.ready_to - 0.3]
            t_stt = time.time() - t0 - t_audio
            if segs:
                ro = translate(segs, job.cues)
                for s, r in zip(segs, ro):
                    s["ro"] = r
                job.cues.extend(segs)
            job.ready_to = start + fresh.size / 16000
            write_srt(job)
            log(ev="chunk", file=job.name[:40], start=start, ready_to=round(job.ready_to), cues=len(job.cues),
                audio_s=round(t_audio, 1), stt_s=round(t_stt, 1), total_s=round(time.time() - t0, 1))
            if fresh.size / 16000 < CHUNK_S:
                break
            tail = fresh[-OVERLAP_S * 16000:]
            start += CHUNK_S
        ff.kill()
        job.done = True
        log(ev="done", file=job.name[:40], cues=len(job.cues))
    except Exception as e:  # prototype: surface, don't crash the server
        job.error = repr(e)[:200]
        log(ev="job-error", err=job.error)


def match_engine(filename: str, size: int | None) -> tuple[str, int, str] | None:
    with urllib.request.urlopen(f"{SERVER}/stats.json", timeout=5) as r:
        engines = json.load(r)
    for ih, e in engines.items():
        for i, f in enumerate(e.get("files", [])):
            if (filename and f.get("name") == filename) or (size and f.get("length") == size):
                return ih, i, f["name"]
    return None


def mmss(t: float) -> str:
    return f"{int(t) // 60}:{int(t) % 60:02}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a: object) -> None:
        pass

    def send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = unquote(self.path)
        if path == "/manifest.json":
            m = {"id": "io.github.fum4.stremio-companion.phase0", "version": "0.0.3",
                 "name": "Romanian (AI)", "description": "AI-generated Romanian subtitles (Whisper + Claude), from stremio-companion",
                 "resources": ["subtitles"], "types": ["movie", "series"], "idPrefixes": ["tt", "kitsu"],
                 "catalogs": []}
            return self.send(200, json.dumps(m).encode(), "application/json")
        if path.startswith("/subtitles/"):
            extra = dict(re.findall(r"(filename|videoSize|videoHash)=([^&]*?)(?=&|\.json$)", path))
            log(ev="subtitles-request", ua=(self.headers.get("User-Agent") or "")[:30], **extra)
            subs = []
            hit = match_engine(extra.get("filename", ""), int(extra["videoSize"]) if extra.get("videoSize") else None)
            if hit:
                ih, idx, name = hit
                job = JOBS.get((ih, idx))
                if not job:
                    job = JOBS[(ih, idx)] = Job(ih, idx, name)
                    threading.Thread(target=run, args=(job,), daemon=True).start()
                    log(ev="job-start", file=name)
                subs.append({"id": f"companion-ro-{ih[:8]}-{idx}", "lang": "ron",
                             "url": f"http://{LAN_IP}:{PORT}/live/{ih}-{idx}.srt?v={int(job.ready_to)}",
                             "label": "Romanian (AI)"})
            return self.send(200, json.dumps({"subtitles": subs}).encode(), "application/json")
        if path.startswith("/live/"):
            key = path.split("/live/")[1].split(".srt")[0]
            p = OUT / f"{key}.ro.srt"
            body = p.read_bytes() if p.exists() else b"1\n00:00:00,000 --> 00:00:05,000\nSe genereaza subtitrarea... reselecteaza in 2 min\n"
            log(ev="srt-fetch", key=key[:12], bytes=len(body))
            return self.send(200, body, "application/x-subrip; charset=utf-8")
        self.send(404, b"{}", "application/json")


log(ev="listening", port=PORT)
ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
