# stremio-companion

A small service that runs next to a Stremio streaming server on a Mac (later: an always-on box) and makes the **official Stremio app on a Samsung TV** better at three things:

1. **Keep buffering while paused** — torrents keep downloading the whole file regardless of the playhead.
2. **Auto-sync subtitles** — out-of-sync subtitles are re-timed against the movie's audio.
3. **Auto-generate subtitles** — no subtitles? Transcribe the audio and translate it to **Romanian**.

No fork of the TV app is needed for any of this (to be confirmed by phase 0 — [docs/plan.md](docs/plan.md)).

## Architecture

```
TV: official Stremio app ── streaming server URL = http://<mac-LAN-IP>:11470
                        └─ companion addon (synced via the Stremio account) = http://<mac-LAN-IP>:11471/manifest.json
Mac:
  Stremio streaming server (official server.js, pinned, under node)           :11470
    settings: cache = Infinite; torrent profile = fastest
  stremio-companion (this repo; Python, launchd)                              :11471
    ├─ engine pin: holds a Range read open per active torrent so a paused TV
    │   doesn't let the server destroy the engine (ENGINE_TIMEOUT 120 s)
    ├─ subtitles addon: filename + videoSize + videoHash → active engine via /stats.json
    ├─ sync: ffsubsync, fallback alass
    └─ generate: parakeet-mlx / Whisper (mlx) → Claude Haiku EN→RO → SRT
```

Details and evidence: [docs/research/stremio-internals.md](docs/research/stremio-internals.md), [docs/research/subtitle-stack.md](docs/research/subtitle-stack.md).

## Install on a Mac

Prereqs: Homebrew, `mise` (`brew install mise`), `gh`.

```bash
git clone https://github.com/fum4/stremio-companion ~/_work/stremio-companion
cd ~/_work/stremio-companion
mise trust && mise install
mise run setup                 # Brewfile deps, venv, git hooks
mise run install-service       # fetch the pinned server.js, load the launchd agents
```

- Logs: `~/Library/Logs/stremio-companion/{server,companion}.log`
- Server data + cache: `~/Library/Application Support/stremio-companion/stremio-server/`
- Stop / remove: `mise run uninstall-service`
- Per-machine overrides (e.g. your LAN IP): `.env.local` (gitignored). Committed config: `infra/env/*.env`.

## Point the TV at it — and back

Full steps: [docs/runbooks/tv-setup.md](docs/runbooks/tv-setup.md). In short: give the Mac a DHCP reservation, then in the TV app set **Settings → Streaming → server URL** to `http://<mac-LAN-IP>:11470`. **To revert**, set it back to the value recorded in the runbook. If the Mac is asleep or off, torrents won't play on the TV until you revert or wake it.

## Develop

`mise tasks` lists everything. `mise run dev` · `test` · `lint` · `format` · `typecheck`. Hooks: `git push` runs `mise run pre-push` (format check, lint, pyright strict); before merging, `mise run gate` runs the tests and posts the `devbox/pre-merge` status on the PR head.
