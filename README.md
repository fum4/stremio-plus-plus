# stremio++

Repo and package slug: `stremio-plus-plus` (GitHub allows no `+` in names).

Makes the **official Stremio app on a Samsung TV** play torrents better, using a Mac on the same Wi-Fi:

| | What you get | Status |
|---|---|---|
| **Smooth playback** | The Mac downloads the whole file, so pausing actually buffers and resume is instant. The TV's built-in server only keeps ~45 MB. | ✅ working |
| **Next episode ready** | Starting an episode of a season pack starts downloading the next one. | ✅ working |
| **One "Stremio++" source, first in the list** | Asks every stream addon you have installed (Torrentio, ThePirateBay+, debrid addons…) and plays the best release: already on the Mac > same release as the last episode > plays on the TV > up to 4K > most seeders. Video untouched, original audio when the TV plays it (Dolby Digital Plus 5.1/Atmos included), DTS/TrueHD → Dolby Digital 5.1. | ✅ working |
| **Romanian (AI) subtitles** | Generated from the audio (Whisper on the Mac → Claude Haiku), starting where you are in the video. On the Stremio++ source they're **inside the stream**: pick *Romanian (AI)* in the subtitles menu once and they show at once and keep coming, no toggling. On any other source they're an ordinary track (the TV loads it once; the next episode is generated in full ahead). Stored forever, so a resume or rewatch is instant. | ✅ working |
| **Automatic cleanup** | Daily at 04:30: deletes torrents nobody played for 7 days; keeps ≥ 3 GiB free. | ✅ working |
| Zero-click subtitles, synced human RO subs | Track picked automatically; existing human subtitles re-timed to the audio. | planned ([docs/plan.md](docs/plan.md)) |

No modified TV app: everything works through two settings in the stock Stremio app.

## How it fits together

```
Samsung TV — Stremio app ("Stremio Theater")
  │  server URL:  https://<mac-ip-dashed>.519b6502d940.stremio.rocks:12470   (HTTPS: the TV refuses plain http)
  │  addon:       "Stremio++"  https://<mac-ip-dashed>.519b6502d940.stremio.rocks:8443/<secret>/manifest.json
  │               (the streaming server's own certificate, reused; or your own domain; installed once per account)
  ▼
Mac (launchd agents, all from this repo)
  ├─ Stremio streaming server   official server.js (pinned), node        :11470 http · :12470 https
  │     cache kept until the companion deletes it; "ultra fast" torrent profile
  ├─ companion                  Python / FastAPI                :11471 http (LAN: settings UI) · :8443 https (addon)
  │     ├─ watches the server log → which file the TV plays, where it seeks
  │     ├─ stream: the "Stremio++" source: best release from your addons, repackaged as HLS
  │     │   (ffmpeg, video copied) with the subtitle track inside, switched from the menu
  │     ├─ downloads: keeps the playing file + next episode downloading
  │     └─ subtitles: audio → Whisper (MLX) → Claude Haiku (`claude` CLI, your plan) → SRT, stored in SQLite
  ├─ cleanup (daily 04:30)      torrents unplayed for 7 days; LRU when disk < 3 GiB
  └─ tls (weekly, own domain only)  renews the addon certificate (lego, DNS-01 via Cloudflare)
```

Why it's built this way, with evidence from the server.js bundle: [docs/research/stremio-internals.md](docs/research/stremio-internals.md). Tool choices and benchmarks: [docs/research/subtitle-stack.md](docs/research/subtitle-stack.md).

## Watching

1. Play anything on the TV as usual.
2. Pick the **Stremio++** source (first in the list). Subtitles are whatever Stremio picks, as usual (real Romanian subtitles from OpenSubtitles when they exist: nothing is generated for nothing).
3. For AI subtitles: subtitles menu → **Romanian (AI)**. They appear at once and keep coming inside the stream; Stremio remembers the choice for the next episode. Picking another track in the menu turns ours off (lines already buffered, ~10–30 s, still show). Stremio's own **Off** can't be seen by the addon: pick another track instead. How it works: [docs/design/hls-stream.md](docs/design/hls-stream.md).
   On another source, *Romanian (AI)* is an ordinary track the TV loads once: if the lines run out, switch it off and on again. The next episode is generated in full ahead, so it needs no toggle.
4. Pause as long as you like; the download continues.

If the Mac is asleep or off, torrents won't play. Switch the TV back to its own server: [revert](docs/runbooks/tv-setup.md#4-revert).

## Install on a Mac

An Apple Silicon Mac that stays on, on the same network as the TV. Needs [Homebrew](https://brew.sh), then:

```bash
brew install mise git
git clone https://github.com/fum4/stremio-plus-plus ~/stremio-plus-plus && cd ~/stremio-plus-plus
mise trust && mise install
mise run install        # dependencies, the settings UI, background services; prints a link
```

Open the link it prints (`http://<this-mac>:11471/`, from any device at home) and follow the setup: it checks the Mac, sets up the streaming server for the TV, lets you pick the translator (your Claude subscription or an Anthropic API key) and try it, downloads the speech model, and walks you through the two steps on the TV and in Stremio. No domain, DNS or certificate work: the addon reuses the certificate Stremio issues for your server.

Tip: give the Mac a fixed address in your router (DHCP reservation); the URL on the TV contains it. Settings live in `~/.config/stremio-plus-plus/config.toml`: edit them in the UI, by hand, or ask an agent. Moving to another Mac: [docs/runbooks/migrate-host.md](docs/runbooks/migrate-host.md). The owner's own setup (own domain, TV control, encrypted token) uses `mise run host:promote` with the values in `.env.local`: [docs/runbooks/tv-setup.md](docs/runbooks/tv-setup.md).

## Everyday commands

| Command | Does |
|---|---|
| `http://<this-mac>:11471/` | The settings UI: status, translator and style, downloads, setup and health checks |
| `mise run host:doctor` | Checks everything (tools, Claude login, LAN IP, services, model, disk) and prints the TV server URL |
| `mise run services:install [server\|companion\|cleanup]` | (Re)installs and restarts the launchd agents (all by default) |
| `mise run services:restart` / `services:logs` | Restart the agents / follow all logs |
| `mise run host:demote` | Stop being the host: removes every agent (data stays) |
| `mise run cleanup -- --dry-run` | Shows what the daily cleanup would delete |
| `mise run server:configure` | Re-applies the server settings (cache, torrent profile, HTTPS for the LAN IP) |
| `mise run tv -- pair\|status\|key HOME DOWN ENTER\|text '<s>'` | Controls the TV from the Mac (`TV_OS` = samsung · webos · androidtv · firetv; only Samsung is tested on a real TV): [TV runbook §6](docs/runbooks/tv-setup.md#6-tv-control-from-the-host) |
| `mise run addon:url` | The addon URL with an own domain (otherwise: the UI's Install page). Keep it private |
| `mise run tls:renew` | Own domain only: get/renew its Let's Encrypt certificate (a weekly agent does this automatically) |
| `mise tasks` | Everything else |

## Where things live

| What | Where |
|---|---|
| Committed config | `infra/env/*.env`, `infra/stremio-server/settings.json` |
| Your settings | `~/.config/stremio-plus-plus/config.toml` (+ `secrets.toml`: API key, addon token; mode 600) |
| This Mac's wiring | `.env.local` (gitignored), all optional: `HOST_LAN_IP`, `CLAUDE_CLI`; the owner's `ADDON_DOMAIN`, `TV_HOST`, `TV_OS` |
| Logs | `~/Library/Logs/stremio-plus-plus/{server,companion,cleanup}.log` |
| Torrent cache | `~/Library/Application Support/stremio-plus-plus/stremio-server/stremio-cache/` |
| Subtitles + play history | `~/Library/Application Support/stremio-plus-plus/companion/state.db` |
| Whisper model | `~/.cache/huggingface/` |

## Troubleshooting

| Symptom | Check |
|---|---|
| TV says the server is **offline** | `mise run host:doctor`. Is the URL on the TV the **https** one it prints? Did the Mac's IP change (then `server:configure` and re-enter the URL)? |
| No **Romanian (AI)** track | Is the **Stremio++** addon installed (desktop app → Addons, URL from `mise run addon:url`)? `mise run host:doctor` checks the certificate and that the addon answers over HTTPS. `companion.log` should show a `subtitles` request when a title opens. |
| No **Stremio++** source | Is the addon installed and first (`stream_picked` in `companion.log` shows what it found)? `addon_streams_failed` names an addon that didn't answer. |
| Stremio++ source won't play | `stream_unsupported` (AV1 / unusual codecs) or `stream_segment_unavailable` (torrent too slow) in `companion.log`; pick another source. |
| Track shows only *"Se generează…"* (another source) | Switch subtitles **off and back on to Romanian (AI)** (re-selecting the active track does nothing). `companion.log` shows `subtitle_window` lines as windows are generated. |
| Subtitles stopped mid-film | The TV loaded them up to the point of your last selection; switch subtitles off and back on to Romanian (AI). `companion.log` `srt_served` shows what each load got. |
| Disk filling up | `mise run cleanup -- --dry-run`; the cleanup keeps ≥ 3 GiB free automatically. |

## Develop

Python 3.14 + uv, FastAPI, SQLite; layering and rules in [CLAUDE.md](CLAUDE.md). `mise run dev` · `test` · `lint` · `format` · `typecheck`. `git push` runs `mise run pre-push` (format, lint, pyright strict); before merging, `mise run gate` runs the tests and posts the `devbox/pre-merge` status on the PR. Plan and phases: [docs/plan.md](docs/plan.md); open work: [docs/work/](docs/work/), owner to-dos: [TODO.md](TODO.md).
