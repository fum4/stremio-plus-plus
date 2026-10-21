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
| 0 | **Spike** — done 2026-10-21 | [phase-0-results.md](research/phase-0-results.md) |
| 1 | **Companion core**: FastAPI app + launchd agent; Stremio server client; **watch tracker** (tails the server log: which file the TV opens, where it seeks, when it stops); persistent state (SQLite) | `mise run dev` shows live TV playback events |
| 2 | **Downloads**: engine pin while the TV or a job needs the file; **prefetch the next episode** of a season pack as soon as one starts; cache policy = keep until disk pressure; **daily cleanup** of files not played for 7 days (launchd calendar job) | E04 downloading as soon as E03 starts; untouched files gone after 7 days |
| 3 | **Romanian (AI) subtitles**: persistent subtitle store (per file, per window: 15 s growing to 2 min, [subtitle-latency.md](research/subtitle-latency.md)); generation starts **at the playhead** and works outward (ahead first, then back-fill), so resuming mid-episode is instant the second time and fast the first; Whisper turbo (centre channel) → Haiku via the `claude` CLI (subscription, serial, hourly cap); label "Romanian (AI)"; spike code deleted | resume at minute 30 shows subs within ~30 s; a rewatch shows them instantly |
| 4 | **Migration-ready**: one-command `mise run host:promote`, migration runbook (new host, LAN IP, TV URL, Claude CLI login, age key), HTTPS for the addon on `stremio.nomadware.io` (done 2026-10-21) | fresh Mac → working setup by following one runbook |
| 6 | **Public, self-hosted release** — proposal: [design/public-release.md](design/public-release.md) | owner decisions pending |
| 5 | Later: zero-click selection (preferred language + synced human RO subs), exact playhead via a proxy, fallback when the host sleeps | — |

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| TV app refuses plain-http addons / subtitle URLs | features 2–3 blocked | phase 0 check; fallback: tailscale-serve HTTPS or the thin fork |
| TV app has no streaming-server URL setting | everything blocked | phase 0 check; fallback: fork + sideload via Tizen `sdb` |
| Batman asleep / off mid-film | TV can't play torrents | runbook: one-setting revert; `caffeinate`/`pmset` guidance; later an always-on box |
| Disk space — Batman ~7 GiB free; the target host (owner's other Mac) has plenty | caching whole files and next episodes | cache = keep until disk pressure (server trims LRU only when the disk would overflow) + 7-day cleanup; manager keeps ≥ 3 GiB free |
| TV can't decode the codec (HEVC/DV/DTS) and can't transcode | no playback | record TV model/codec support; server's HLS transcode path (ffmpeg on Batman) |
| server.js changes behaviour on bump | pin breaks | pinned + sha256; re-verify [stremio-internals.md](research/stremio-internals.md) on every bump |
| Subtitle file fetched once per track selection; the player also auto-selects a remembered language at load (fetch before generation starts), and re-selecting the *active* track does not re-fetch — switching off and back on does (verified on Theater 2026-10-21) | late-generated cues invisible until the next fetch | work ahead, delayed first answer, automated re-select via TV remote API (to verify) |
| Subscription use for translation | account risk if it looks like abuse | personal use only, one call at a time, hourly cap, LAN-only addon; API key (~$0.05/episode) stays a one-setting switch |

## Not doing (v1)
Debrid; a fork of the TV app; a file library (Bazarr-style); translating to anything but Romanian.
