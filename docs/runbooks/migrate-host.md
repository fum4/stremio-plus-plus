# Move the setup to another Mac

Everything the host needs is in this repo; per-machine state is three things: `.env.local`, the companion's `state.db` (subtitles + play history), and logins. Allow ~30 min, most of it downloads.

## On the new Mac
1. **Prereqs:** Homebrew; `brew install mise gh`; `gh auth login` (as `fum4`); Claude Code installed and logged in (`claude`, then `/login` with the plan that should pay for subtitle translation).
2. **Clone:** `git clone https://github.com/fum4/stremio-companion ~/_work/stremio-companion && cd ~/_work/stremio-companion && mise trust && mise install`
3. **Fixed LAN IP:** router → DHCP reservation for the new Mac's Wi-Fi MAC (`ifconfig en0 | awk '/ether/{print $2}'`; with *Private Wi-Fi address* = **Fixed** that's the private MAC). Then create `.env.local`:
   ```
   HOST_LAN_IP=<the reserved IP>
   ```
   (Only if Claude Code lives elsewhere: `CLAUDE_CLI=<path>`.)
4. **Bring over the history (optional but recommended)** — demote the old Mac first (`mise run host:demote`), then copy
   `~/Library/Application Support/stremio-companion/companion/state.db*` from old → same path on the new Mac. Generated subtitles come with it; the torrent cache doesn't need to (it re-downloads).
5. **Install:** `mise run host:promote` (Brewfile, venv, git hooks, Whisper model ~1.6 GB, launchd agents: server, companion, daily cleanup, then the doctor). Fix anything red; `mise run host:doctor` re-checks any time.
6. **HTTPS front for the addon:** today `mise run addon:tunnel` (temporary; prints a new `https://…trycloudflare.com` URL each run). After the `nomadware.io` setup this step becomes "nothing".

## On the TV
7. **Server URL:** Stremio → Settings → Streaming → server URL → the `TV server URL` line `mise run host:doctor` prints (`https://<ip-dashed>.519b6502d940.stremio.rocks:12470`). The IP is baked into that hostname, so a new host IP means a new URL.
8. **Addon:** in the Stremio desktop app (same account): Addons → uninstall "Romanian (AI)" → install `<HTTPS front>/manifest.json`. On the TV: Settings → *Sync addons*.

## On the old Mac
9. Already done in step 4 if you copied the history; otherwise `mise run host:demote` (stops server, companion, cleanup). Optional: delete `~/Library/Application Support/stremio-companion/` to reclaim the cache.

## Revert
TV server URL → `http://127.0.0.1:11470` (the TV's own server) — playback works with no Mac at all ([tv-setup.md](tv-setup.md)).
