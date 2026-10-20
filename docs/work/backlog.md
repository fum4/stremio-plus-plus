# Backlog

## Pin lifetime vs cache cleanup · 2026-10-21 · S
With `cacheSize: null` the server deletes inactive engines' files on every engine creation (stremio-internals § Cache). The pin must therefore outlive processing (sync/generate done), not just the pause. First step: in phase 1, release a pin only when the file is fully downloaded **and** no job holds it.

## Linux (systemd) templates for the always-on box · 2026-10-21 · S
`launchd/` only today. When the move to a Mac mini / N100 is decided: add `systemd/` units mirroring the plists and branch `install-service` on `uname`.

## Converge the Mac gate with `wt` · 2026-10-21 · S
`.githooks/pre-push` and `scripts/pre-merge-gate.sh` are Mac stand-ins for the devbox global hooks + `wt pre-merge`. If `wt`/the hooks become installable on macOS, delete these and use them.
