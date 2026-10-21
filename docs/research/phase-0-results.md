# Phase 0 — results

Spike run on Batman. Each row: result · evidence · date. Owner go/no-go at the bottom.

## Setup
| Step | Result |
|---|---|
| Server install (server.js under node, launchd) | ✅ `mise run install-service server` — server.js v4.22.4 under node 24.22.0, listening `*:11470` (+ `*:12470` https). 2026-10-21 |
| Cache Infinite + fastest profile — how (UI vs `POST /settings`), resulting `server-settings.json` | ✅ `POST /settings` from `infra/stremio-server/settings.json` (`mise run server:configure`); persisted as `cacheSize: null` + ultra-fast values; survives restart. 2026-10-21 |

## Server-side pause experiment (no TV) — 2026-10-21
Torrent: Ubuntu 26.10 desktop ISO (6.6 GB, legal, well seeded), `/{ih}/0`, script `pin_test.py` (session scratch). One `Range: bytes=0-` request, read 1 byte, then:

| Variant | Result |
|---|---|
| **No pin**: close the stream after 5 s, poll `stats.json` every 10 s | downloads at 2–17 MB/s for ~115 s, then engine gone at t≈120 s (`Engine … is inactive, destroying it`). Polling `stats.json` does **not** keep an engine alive |
| **Pin**: keep the socket open, read nothing more | download continues past 120 s at ~10 MB/s (1.24 GB at t=160 s, still rising); engine stays |
| Recreating the engine after it died | `Resizing cache size to 0MB from 6573MB by deleting 5 files`: the null cache wiped the ISO's own partial file (and BBB) → re-download from 0 |

→ The pin works and is **required**. It must outlive processing, not just the pause (backlog: pin lifetime). Real-world speed on this LAN/ISP: ~10 MB/s typical, peaks 17 MB/s. A 1080p film (2–4 GB) is fully down in ~4–7 min.

## TV checks
| Check | Result |
|---|---|
| TV app has a streaming-server URL setting | ✅ Settings → Streaming → server URL |
| `http://192.168.1.132:11470` on the TV | ❌ "offline" — **zero requests reached Batman**. Batman ↔ TV reachable both ways (TV API on :8001 answered; launchd-run node reaches the TV, so not macOS Local Network Privacy) → Theater refuses plain http to non-localhost (mixed-content rule; `http://127.0.0.1` is exempt) |
| `https://192-168-1-132.519b6502d940.stremio.rocks:12470` (server `remoteHttps`) | ✅ **online** — TV (192.168.1.134) connected to :12470 and called `/get-https`. Public DNS → 192.168.1.132; Let's Encrypt `*.519b6502d940.stremio.rocks`, valid to 2026-12-24 |
| Playback through Batman | ✅ MobLand S01E01→E02 (4K HEVC 10-bit, DDP 5.1, season pack) plays; subtitles from strem.io fetched by Batman via `/subtitles.vtt?from=` |
| Download keeps rising during a 2+ min pause — **without** pin | ✅ paused ~01:57–02:01: E02 went 7 % → 26 %+ (~1 GB), speed rose 2.4 → 5.2 MB/s; resume was instant |
| …same — **with** a manual pin (curl Range read) | not needed for a short pause (see next row); pin proven on the server side above |
| Does the TV close its HTTP connection on pause? | **No**: 1 ESTABLISHED TV↔:12470 connection throughout a 4-min pause → no engine timeout. Pin stays for long pauses / TV standby / processing after playback (untested: TV standby) |
| Why it stalled before (root cause) | **Confirmed** from the TV's own server (`http://192.168.1.134:11470/settings`, reachable on the LAN): v4.20.8, `cacheSize: 0` (45 MB ring buffer, stops at 75 % full ≈ 30 s of 4K), hard cap 3.5 MiB/s, 55 connections |
| TV shows subtitles from a hand-served **plain-http** addon on the LAN | ❌ addon installed via the Mac app (it fetched the manifest), TV synced, played → **zero requests** from the TV to the addon |
| …same addon over **HTTPS** (temporary Cloudflare quick tunnel, shut down right after) | ✅ TV (UA `SMART-TV; LINUX; Tizen 5.5 … Chrome 69`) called `/subtitles/series/tt31510819:1:3/…` **twice per load**: first `filename=` only, ~6 s later `filename` + `videoSize` + `videoHash` (after `/opensubHash`). Selecting the track → TV asks Batman's server `/subtitles.vtt?from=http://192.168.1.132:11471/test.srt` → server (node `Needle`) fetches the SRT over **plain LAN http** → cues shown on the TV at the right times (owner confirmed) |
| Theater addon UI | no addon list and no "add by URL"; only a **Sync addons** button. Addons are installed from another client (Mac app) on the same account |
| Server `/proxy` as an HTTPS relay for the addon | ❌ only fetches `https://` upstreams (`ERR_INVALID_PROTOCOL`) |
| Revert to the TV's own server is one setting | _pending_ |
| Batman sleeps mid-film → what the TV shows | _pending_ |
| DTS-audio file plays (server transcodes audio?) · DV file colours | _pending_ |

## Server self-test
At boot the server tests VideoToolbox: **audio hw transcode ✅, video (HEVC) ❌** → "no viable acceleration profiles"; any video transcode falls back to software.

## Benchmarks (M4 Pro, 10 min of real movie audio)
| Bench | Result |
|---|---|
| ffsubsync on a deliberately offset SRT — time, score, residual offset | ✅ ffsubsync 0.5.1: +3.7 s offset **and** +2 s + 25→23.976 drift both fixed in **0.8–2 s** (scale 0.959 found); residual a constant 50–60 ms (= its own VAD bias on the untouched file). alass: no macOS release binary; Homebrew bottle `alass 2.0.0` exists → Brewfile |
| parakeet-mlx vs mlx-whisper turbo — speed, quality | see table below |
| Haiku 5.5 vs Sonnet 5.5 EN→RO on ~200 cues — cost, owner's verdict | _pending_ |

### Speech-to-text detail — 2026-10-21
*Tears of Steel* (CC-BY), first 600 s, mono 16 kHz; reference = official EN SRT (76 cues). WER normalized (lowercase, no punctuation).

| System | Speed (cached, 600 s audio) | WER (in cue windows) | Cues covered | Notes |
|---|---|---|---|---|
| parakeet-tdt-0.6b-v3 (parakeet-mlx 0.5.3) | 6 s infer, **~100× realtime**, ~0.8 GB RSS | 27.1 % | 75–80 % | no hallucinations, but **drops speech**: gaps > 15 s, misses short shouts and lines in action scenes |
| whisper-large-v3-turbo (mlx-whisper 0.4.3), CLI defaults | 25 s, 24× | 74 % (112 % whole text) | 82–87 % | **hallucination loops** ("I'm not." ×dozens) — unusable |
| whisper-large-v3-turbo, `--condition-on-previous-text False --hallucination-silence-threshold 2` | 21 s, **29×**, ~1.9 GB RSS | **17.5 %** | **96–97 %** | deterministic; residue = "Ah!/Oh, no!" fillers in action |

- Model load from cache < 0.5 s; first download ~3.5–4 min per model (parakeet 2.5 GB, whisper 1.6 GB).
- mlx-whisper's CLI and Python API have **different defaults** (API: temperature fallback, 37 s vs 21 s, different output). Phase 3 must set every decoding option explicitly.
- Cue-start error ≈ 0.4 s median for both (coarse: reference cues sit on 0.5 s boundaries).
- At 29× a 2 h film transcribes in ~4 min — far below the torrent download time, so speed isn't the deciding factor; coverage is.

## What this means for the design
- **Addon endpoints (manifest + `/subtitles/…json`) must be HTTPS** with a publicly trusted cert. Plan: `subs.nomadware.io` (owner's domain) → A record to Batman's LAN IP, Let's Encrypt via DNS-01; LAN-only traffic.
- **Subtitle files may stay plain http on the LAN**: Batman's streaming server fetches and converts them (`/subtitles.vtt?from=`).
- Match the engine on the **second** request (`videoHash` + `videoSize`); the first (filename only) can be answered from the filename or with nothing.

## Live Romanian AI subtitles on the TV — 2026-10-21
Spike `spikes/phase-0/live_ro.py` behind a temporary HTTPS quick tunnel; MobLand S01E03 (4K, E-AC-3 5.1).

| Check | Result |
|---|---|
| Pipeline speed | first 2 min of RO ready **25–28 s** after the TV's request (audio 0.5 s, Whisper 5–10 s, Haiku ~12–15 s); whole 50-min episode (814 cues) in **~8 min**, ~5× faster than playback |
| Owner verdict | "it fucking works" — RO subs shown in sync at 8:50 after a re-select |
| Refresh | the TV fetches the file once per track selection → a re-select pulls everything generated so far (verified 3×) |
| Translation via subscription | `claude -p --model claude-haiku-5-5 --tools "" --strict-mcp-config --setting-sources "" --no-session-persistence --system-prompt … --json-schema …` → `structured_output`; `--bare` refuses subscription auth. ~1.3–10 s per call |
| Usage per 2-min chunk | ~2.4k input (mostly cache) + 2.8k output (1.5k thinking) ≈ $0.002 API-equivalent → **~$0.05 / episode**, ~25 calls |
| Quality notes | natural, correct diacritics; line breaking needs work (`de / fapt` split) |
| Real-content STT (bench) | centre channel 13.7 % WER, 197/197 cues covered; downmix 30.9 % (transcribed a song) → centre channel confirmed |

Owner decisions: AI subs for now (label **"Romanian (AI)"**), zero-click selection is the goal (plan phases 2–3), subscription OK with guardrails (serial, hourly cap, personal use).

## Go / no-go
_pending_
