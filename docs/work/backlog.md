# Backlog

## Per-episode cleanup inside season packs · 2026-10-21 · M
Cleanup deletes whole torrents only: the server keeps a per-torrent piece bitfield, and deleting one file of a pack would leave it claiming data that's gone. First step: delete one file of a test pack, recreate the engine, and see whether server.js re-verifies (then per-file deletion is safe) or serves zeros.

## Pins should also wait for subtitle jobs · 2026-10-21 · S
Pins are released once a file is complete; phase 3's subtitle job reads the file after that. Fine while the engine lives (the job's own reads keep it alive), but make the pin release explicit: release only when complete **and** no job holds the file.

## Linux (systemd) templates for the always-on box · 2026-10-21 · S
`launchd/` only today. When the move to a Mac mini / N100 is decided: add `systemd/` units mirroring the plists and branch `install-service` on `uname`.

## Converge the Mac gate with `wt` · 2026-10-21 · S
`.githooks/pre-push` and `scripts/pre-merge-gate.sh` are Mac stand-ins for the devbox global hooks + `wt pre-merge`. If `wt`/the hooks become installable on macOS, delete these and use them.

## Next episode across torrents · 2026-10-21 · M
Prefetch only works inside one torrent (season packs). Single-episode torrents would need us to pick a stream for E+1 ourselves (query the stream addon, match release group/quality). First step: log how often the owner plays single-episode torrents.

## Server log holds the Stremio authKey in plain text · 2026-10-21 · S
server.js logs `GET /get-https?authKey=…` to `~/Library/Logs/stremio-companion/server.log`. First step: create the log dir 0700 / file 0600 in `launchd-install.sh`, and add rotation (newsyslog conf in the repo) so it doesn't grow forever.

## Permanent TV remote control from Batman · 2026-10-21 · M
Owner wants Batman to control the TV for good (typing URLs with the remote is painful). Proven in phase 0: Samsung WS API `wss://192.168.1.134:8002/api/v2/channels/samsung.remote.control` paired after one on-TV "Allow"; the TV sends `ms.remote.touchDisable/Enable` before `ms.channel.connect`, which `samsungtvws` 3.0.6 treats as failure → own small client. First step: a `tv/` package (pair, key, text, power via Wake-on-LAN) + `mise run tv -- …`; the pairing token is a credential → `secrets/*.age` once the macOS repo-secrets decision lands.
