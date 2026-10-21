# Phase 0 — results

Spike run on Batman. Each row: result · evidence · date. Owner go/no-go at the bottom.

## Setup
| Step | Result |
|---|---|
| Server install (server.js under node, launchd) | _pending_ |
| Cache Infinite + fastest profile — how (UI vs `POST /settings`), resulting `server-settings.json` | _pending_ |

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

## Benchmarks (M4 Pro, 10 min of real movie audio)
| Bench | Result |
|---|---|
| ffsubsync on a deliberately offset SRT — time, score, residual offset | _pending_ |
| parakeet-mlx vs mlx-whisper turbo — speed, WER-ish eyeball | _pending_ |
| Haiku 5.5 vs Sonnet 5.5 EN→RO on ~200 cues — cost, owner's verdict | _pending_ |

## Go / no-go
_pending_
