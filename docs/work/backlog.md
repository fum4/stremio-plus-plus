# Backlog

## Cache cleanup policy for an Infinite cache · 2026-10-21 · M
Infinite cache never trims; Batman's disk will fill. Deferred until phase 1 shows real usage. First step: measure cache growth per film; then an age/LRU sweep of our own `APP_PATH` cache dir that skips files of active engines.

## Linux (systemd) templates for the always-on box · 2026-10-21 · S
`launchd/` only today. When the move to a Mac mini / N100 is decided: add `systemd/` units mirroring the plists and branch `install-service` on `uname`.

## Converge the Mac gate with `wt` · 2026-10-21 · S
`.githooks/pre-push` and `scripts/pre-merge-gate.sh` are Mac stand-ins for the devbox global hooks + `wt pre-merge`. If `wt`/the hooks become installable on macOS, delete these and use them.
