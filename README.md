# stremio++

Repo and package slug: `stremio-plus-plus` (GitHub allows no `+` in names).

Makes the **official Stremio app on a Samsung TV** play torrents better, using a Mac on the same Wi-Fi:

| | What you get | Status |
|---|---|---|
| **Smooth playback** | The Mac downloads the whole file, so pausing actually buffers and resume is instant. The TV's built-in server only keeps ~45 MB. | ✅ working |
| **Next episode ready** | Starting an episode of a season pack starts downloading the next one. | ✅ working |
| **Romanian (AI) subtitles** | Generated from the audio (Whisper on the Mac → Claude Haiku), starting where you are in the video; stored forever, so a resume or rewatch is instant. | ✅ working |
| **Automatic cleanup** | Daily at 04:30: deletes torrents nobody played for 7 days; keeps ≥ 3 GiB free. | ✅ working |
| Zero-click subtitles, synced human RO subs | Track picked automatically; existing human subtitles re-timed to the audio. | planned ([docs/plan.md](docs/plan.md)) |

No modified TV app: everything works through two settings in the stock Stremio app.

## How it fits together

```
Samsung TV — Stremio app ("Stremio Theater")
  │  server URL:  https://<mac-ip-dashed>.519b6502d940.stremio.rocks:12470   (HTTPS: the TV refuses plain http)
  │  addon:       "Romanian (AI)"  https://stremio.nomadware.io:8443/<secret>/manifest.json
  │               (public name → the Mac's LAN IP, Let's Encrypt certificate; installed once from the desktop app)
  ▼
Mac (launchd agents, all from this repo)
  ├─ Stremio streaming server   official server.js (pinned), node        :11470 http · :12470 https
  │     cache kept until the companion deletes it; "ultra fast" torrent profile
  ├─ companion                  Python / FastAPI                :11471 http (LAN) · :8443 https (addon)
  │     ├─ watches the server log → which file the TV plays, where it seeks
  │     ├─ downloads: keeps the playing file + next episode downloading
  │     └─ subtitles: audio → Whisper (MLX) → Claude Haiku (`claude` CLI, your plan) → SRT, stored in SQLite
  ├─ cleanup (daily 04:30)      torrents unplayed for 7 days; LRU when disk < 3 GiB
  └─ tls (weekly)               renews the addon certificate (lego, DNS-01 via Cloudflare)
```

Why it's built this way, with evidence from the server.js bundle: [docs/research/stremio-internals.md](docs/research/stremio-internals.md). Tool choices and benchmarks: [docs/research/subtitle-stack.md](docs/research/subtitle-stack.md).

## Watching

1. Play anything on the TV as usual.
2. For Romanian subtitles: subtitles menu → **Romanian (AI)**. The first time a title plays, the first lines take ~30 s. If you see *"Se generează subtitrarea…"*, wait a minute and **select the track again**: each selection loads everything generated so far. On a resume or rewatch they're there immediately.
3. Pause as long as you like; the download continues.

If the Mac is asleep or off, torrents won't play. Switch the TV back to its own server: [revert](docs/runbooks/tv-setup.md#4-revert).

## Install on a Mac

Needs Homebrew, `brew install mise gh`, Claude Code logged in (`claude`, then `/login`), and a fixed LAN IP for the Mac (router DHCP reservation, see the [TV runbook](docs/runbooks/tv-setup.md#1-give-the-mac-a-fixed-lan-ip)).

```bash
git clone https://github.com/fum4/stremio-plus-plus ~/_work/stremio-plus-plus
cd ~/_work/stremio-plus-plus
mise trust && mise install
echo "HOST_LAN_IP=<the Mac's reserved LAN IP>" > .env.local
mise run host:promote   # this Mac becomes the Stremio host: Brewfile, venv, hooks, Whisper model (~1.6 GB), launchd agents, doctor
```

Then point the TV at it and install the addon: [docs/runbooks/tv-setup.md](docs/runbooks/tv-setup.md). Moving to another Mac: [docs/runbooks/migrate-host.md](docs/runbooks/migrate-host.md).

## Everyday commands

| Command | Does |
|---|---|
| `mise run host:doctor` | Checks everything (tools, Claude login, LAN IP, services, model, disk) and prints the TV server URL |
| `mise run services:install [server\|companion\|cleanup]` | (Re)installs and restarts the launchd agents (all by default) |
| `mise run services:restart` / `services:logs` | Restart the agents / follow all logs |
| `mise run host:demote` | Stop being the host: removes every agent (data stays) |
| `mise run cleanup -- --dry-run` | Shows what the daily cleanup would delete |
| `mise run server:configure` | Re-applies the server settings (cache, torrent profile, HTTPS for the LAN IP) |
| `mise run addon:url` | The addon URL to install in Stremio (`https://stremio.nomadware.io:8443/<secret>/manifest.json`; keep it private) |
| `mise run tls:renew` | Get/renew the addon's Let's Encrypt certificate (a weekly agent does this automatically) |
| `mise tasks` | Everything else |

## Where things live

| What | Where |
|---|---|
| Committed config | `infra/env/*.env`, `infra/stremio-server/settings.json` |
| This Mac's settings | `.env.local` (gitignored): `HOST_LAN_IP`, optional `CLAUDE_CLI` |
| Logs | `~/Library/Logs/stremio-plus-plus/{server,companion,cleanup}.log` |
| Torrent cache | `~/Library/Application Support/stremio-plus-plus/stremio-server/stremio-cache/` |
| Subtitles + play history | `~/Library/Application Support/stremio-plus-plus/companion/state.db` |
| Whisper model | `~/.cache/huggingface/` |

## Troubleshooting

| Symptom | Check |
|---|---|
| TV says the server is **offline** | `mise run host:doctor`. Is the URL on the TV the **https** one it prints? Did the Mac's IP change (then `server:configure` and re-enter the URL)? |
| No **Romanian (AI)** track | Is the addon installed (desktop app → Addons, URL from `mise run addon:url`)? `mise run host:doctor` checks the certificate and that the addon answers over HTTPS. `companion.log` should show a `subtitles` request when a title opens. |
| Track shows only *"Se generează…"* | Re-select it after a minute. `companion.log` shows `subtitle_chunk` lines as minutes are generated. |
| Subtitles stopped mid-film | They were generated up to the point of your last selection; re-select the track. |
| Disk filling up | `mise run cleanup -- --dry-run`; the cleanup keeps ≥ 3 GiB free automatically. |

## Develop

Python 3.14 + uv, FastAPI, SQLite; layering and rules in [CLAUDE.md](CLAUDE.md). `mise run dev` · `test` · `lint` · `format` · `typecheck`. `git push` runs `mise run pre-push` (format, lint, pyright strict); before merging, `mise run gate` runs the tests and posts the `devbox/pre-merge` status on the PR. Plan and phases: [docs/plan.md](docs/plan.md); open work: [docs/work/](docs/work/), owner to-dos: [TODO.md](TODO.md).
