# Plan

Planned 2026-10-20 in the devbox session "Explore Reframe and Set It Up on TV" (thread `58950eed-1903-48d2-b6e8-a2ea15cb342e`); built on Batman from 2026-10-21.

## Goal
On the Samsung TV's official Stremio app, with torrent streams (no debrid):
1. **Keep buffering while paused** — download the whole file regardless of the playhead.
2. **Auto-sync subtitles** against the movie's audio.
3. **Auto-generate subtitles** when none exist — transcribe (usually EN), translate to **Romanian**.

v1 runs on Batman (MacBook Pro M4 Pro, 48 GB). It may move to an always-on box (Mac mini / N100) → everything is config-as-code.

## Phases (one PR each, each behind a green pre-merge)
| # | What | Exit criterion |
|---|---|---|
| 0 | **Spike**: server on Batman, TV pointed at it, pause/subtitle/revert checks, benchmarks | [phase-0-results.md](research/phase-0-results.md) + owner go/no-go |
| 1 | Companion skeleton: FastAPI, addon manifest, launchd, **engine pin** + tests | paused 5 min on the TV, download keeps rising, playback resumes |
| 2 | **Sync**: request → engine match → ffprobe/ffmpeg chunk → ffsubsync (alass fallback); cache by videoHash | offset SRT fixed on the TV |
| 3 | **Generate**: parakeet-mlx chunks 2–5 min ahead → Haiku RO → SRT, served when ready | film with no subs gets RO subs after a reload |
| 4 | Optional fork (`fum4/stremio-web`) for mid-film track refresh / native AVPlay | only if phase 0–3 show the official app can't |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| TV app refuses plain-http addons / subtitle URLs | features 2–3 blocked | phase 0 check; fallback: tailscale-serve HTTPS or the thin fork |
| TV app has no streaming-server URL setting | everything blocked | phase 0 check; fallback: fork + sideload via Tizen `sdb` |
| Batman asleep / off mid-film | TV can't play torrents | runbook: one-setting revert; `caffeinate`/`pmset` guidance; later an always-on box |
| Disk space — Batman had **~10 GiB free** (98%) on 2026-10-21; a 4K remux is 20–60 GB | film can't be cached whole; macOS unstable when full | `cacheSize: null` already cleans inactive torrents on each new engine (verified); owner frees space or picks an external drive as `cacheRoot` |
| TV can't decode the codec (HEVC/DV/DTS) and can't transcode | no playback | record TV model/codec support; server's HLS transcode path (ffmpeg on Batman) |
| server.js changes behaviour on bump | pin breaks | pinned + sha256; re-verify [stremio-internals.md](research/stremio-internals.md) on every bump |
| Subtitles requested once per load | generated track not visible until reload | serve only finished tracks; optional "generating… reload in N min" stub |

## Not doing (v1)
Debrid; a fork of the TV app; a file library (Bazarr-style); translating to anything but Romanian.
