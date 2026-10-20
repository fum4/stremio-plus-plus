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
| TV app has a streaming-server URL setting; playback through Batman works | _pending_ |
| `/{ih}/{idx}/stats.json` bytes keep rising during a 2+ min pause — **without** pin | _pending_ |
| …same — **with** a manual pin (curl Range read) | _pending_ |
| Does the TV close its HTTP connection on pause? (`lsof` / server log) | _pending_ |
| TV shows subtitles from a hand-served plain-http addon on the LAN | _pending_ |
| Revert to the TV's own server is one setting | _pending_ |
| Batman sleeps mid-film → what the TV shows | _pending_ |
| DTS-audio file plays (server transcodes audio?) · DV file colours | _pending_ |

## Benchmarks (M4 Pro, 10 min of real movie audio)
| Bench | Result |
|---|---|
| ffsubsync on a deliberately offset SRT — time, score, residual offset | _pending_ |
| parakeet-mlx vs mlx-whisper turbo — speed, WER-ish eyeball | _pending_ |
| Haiku 5.5 vs Sonnet 5.5 EN→RO on ~200 cues — cost, owner's verdict | _pending_ |

## Go / no-go
_pending_
