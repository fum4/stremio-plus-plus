# Backlog

## Pin lifetime vs cache cleanup · 2026-10-21 · S
With `cacheSize: null` the server deletes inactive engines' files on every engine creation (stremio-internals § Cache). The pin must therefore outlive processing (sync/generate done), not just the pause. First step: in phase 1, release a pin only when the file is fully downloaded **and** no job holds it.

## Linux (systemd) templates for the always-on box · 2026-10-21 · S
`launchd/` only today. When the move to a Mac mini / N100 is decided: add `systemd/` units mirroring the plists and branch `install-service` on `uname`.

## Converge the Mac gate with `wt` · 2026-10-21 · S
`.githooks/pre-push` and `scripts/pre-merge-gate.sh` are Mac stand-ins for the devbox global hooks + `wt pre-merge`. If `wt`/the hooks become installable on macOS, delete these and use them.

## Server log holds the Stremio authKey in plain text · 2026-10-21 · S
server.js logs `GET /get-https?authKey=…` to `~/Library/Logs/stremio-companion/server.log`. First step: create the log dir 0700 / file 0600 in `launchd-install.sh`, and add rotation (newsyslog conf in the repo) so it doesn't grow forever.

## Permanent TV remote control from Batman · 2026-10-21 · M
Owner wants Batman to control the TV for good (typing URLs with the remote is painful). Proven in phase 0: Samsung WS API `wss://192.168.1.134:8002/api/v2/channels/samsung.remote.control` paired after one on-TV "Allow"; the TV sends `ms.remote.touchDisable/Enable` before `ms.channel.connect`, which `samsungtvws` 3.0.6 treats as failure → own small client. First step: a `tv/` package (pair, key, text, power via Wake-on-LAN) + `mise run tv -- …`; the pairing token is a credential → `secrets/*.age` once the macOS repo-secrets decision lands.
