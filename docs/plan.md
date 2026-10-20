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
| 2 | **Best RO track, zero clicks**: our addon is the only RO source and returns one "RO" track = synced human sub (OpenSubtitles candidates → ffsubsync `--no-fix-framerate` → verified against our Whisper transcript) or else AI; TV preferred subtitle language = Romanian | any title with an RO human sub plays with synced RO subs, no clicks |
| 3 | **Generate**: Whisper turbo (centre channel) → Haiku RO via the `claude` CLI on the owner's subscription (serial, hourly cap) → SRT; work ahead (rest of the file + next episodes of a season pack); delay the first answer ~1 min; auto re-select via the TV remote API when generation passes the playhead | first-time AI-only title shows RO subs with zero clicks |
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
| Subtitle file fetched once per track selection (verified: re-selecting re-fetches) | late-generated cues invisible until the next fetch | work ahead, delayed first answer, automated re-select via TV remote API (to verify) |
| Subscription use for translation | account risk if it looks like abuse | personal use only, one call at a time, hourly cap, LAN-only addon; API key (~$0.05/episode) stays a one-setting switch |

## Not doing (v1)
Debrid; a fork of the TV app; a file library (Bazarr-style); translating to anything but Romanian.
