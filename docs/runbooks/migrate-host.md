# Move the setup to another Mac

Everything the host needs is in this repo; per-machine state is three things: `.env.local`, the companion's `state.db` (subtitles + play history), and logins. Allow ~30 min, most of it downloads.

## Before you start: is this Mac a good host?
- **Apple Silicon** (M1 or later): Whisper runs on MLX. An Intel Mac can't generate subtitles.
- **Always on, on power, on the same Wi-Fi as the TV.** The host serves every torrent the TV plays.
- **Disk:** whole episodes and the next one are cached; a few hundred GB free is comfortable (cleanup keeps ≥ 3 GiB free regardless).
- **No Stremio desktop app running on it**: it starts its own server on port 11470 and collides with ours (you can still use it on another machine to install addons).

## On the new Mac
0. **Host settings (one-time, macOS, needs your password):**
   - Never sleep on power: `sudo pmset -c sleep 0 disksleep 0` (the display may still sleep: `displaysleep` is fine). Check with `pmset -g custom`.
   - Survive reboots: System Settings → Users & Groups → **Automatic login** → your user. launchd agents only start after a login; with FileVault on, macOS asks for the password once at boot instead.
   - If the macOS firewall is on (System Settings → Network → Firewall): when prompted, **Allow incoming connections** for `node` (the streaming server) and `python` (the companion).
1. **Prereqs:** Homebrew; `brew install mise gh`; `gh auth login` (as `fum4`); Claude Code installed and logged in (`claude`, then `/login` with the plan that should pay for subtitle translation).
2. **Repo age key (required):** copy `~/.config/age/stremio-plus-plus.key` from the old Mac (mode 600). It decrypts the addon token and the certificate's Cloudflare token; without it the companion won't start.
3. **Clone:** `git clone https://github.com/fum4/stremio-plus-plus ~/_work/stremio-plus-plus && cd ~/_work/stremio-plus-plus && mise trust && mise install`
4. **Fixed LAN IP:** router → DHCP reservation for the new Mac's Wi-Fi MAC (`ifconfig en0 | awk '/ether/{print $2}'`; with *Private Wi-Fi address* = **Fixed** that's the private MAC). Then create `.env.local`:
   ```
   HOST_LAN_IP=<the reserved IP>
   ```
   (Only if Claude Code lives elsewhere: `CLAUDE_CLI=<path>`.)
5. **Bring over the history (optional but recommended)** — demote the old Mac first (`mise run host:demote`), then copy
   `~/Library/Application Support/stremio-plus-plus/companion/state.db*` from old → same path on the new Mac. Generated subtitles come with it; the torrent cache doesn't need to (it re-downloads).
6. **Install:** `mise run host:promote` (Brewfile, venv, git hooks, Whisper model ~1.6 GB, **TLS certificate**, launchd agents: server, companion, daily cleanup, weekly certificate renewal, **pairing with the TV**, then the doctor). Have the TV on: when it shows **"stremio++ wants to connect"**, press **Allow** within a minute. From then on this host controls the TV (`mise run tv -- key KEY_HOME`, `mise run tv -- text '<url>'`). Fix anything red; `mise run host:doctor` re-checks any time.
7. **Addon address:** `host:promote` already fetched the certificate. If the new Mac has a **different LAN IP**, update the `stremio` record in `fum4/Nomadware.io` (`infra/terraform/records.tf`, then `mise run tf -- apply`); with the same reserved IP nothing changes. `mise run host:doctor` checks it.

## On the TV
8. **Server URL:** Stremio → Settings → Streaming → server URL → the `TV server URL` line `mise run host:doctor` prints. No typing on the remote: select the field so the on-screen keyboard opens, then on the Mac `mise run tv -- text '<that URL>'` (`https://<ip-dashed>.519b6502d940.stremio.rocks:12470`). The IP is baked into that hostname, so a new host IP means a new URL.
9. **Addon:** nothing to do: the URL (`mise run addon:url`) is the same on every host.

## On the old Mac
10. Already done in step 5 if you copied the history; otherwise `mise run host:demote` (stops server, companion, cleanup, certificate renewal). Optional: delete `~/Library/Application Support/stremio-plus-plus/` to reclaim the cache.
11. Optional: on the TV, revoke the old host's pairing (TV Settings → General → External Device Manager → Device Connection Manager → Device List).

## Revert
TV server URL → `http://127.0.0.1:11470` (the TV's own server) — playback works with no Mac at all ([tv-setup.md](tv-setup.md)).
