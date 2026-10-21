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
| Playback through Batman | _pending_ |
| `/{ih}/{idx}/stats.json` bytes keep rising during a 2+ min pause — **without** pin | _pending_ |
| …same — **with** a manual pin (curl Range read) | _pending_ |
| Does the TV close its HTTP connection on pause? (`lsof` / server log) | _pending_ |
| TV shows subtitles from a hand-served plain-http addon on the LAN | _pending_ — expected ❌ given the above; fallback: own-domain HTTPS |
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

## Go / no-go
_pending_
