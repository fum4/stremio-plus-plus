# stremio++ — repo rules

The cross-repo rules are the owner's global agent rules (devbox `agents/AGENTS.md`); this file adds only what is specific to this repo. Never restate a global rule here.

## What this is
A Python service + launchd setup on the owner's Mac (**Batman**) that extends the official Stremio TV app: engine pin (keep torrents downloading while paused), subtitle sync, subtitle generation (EN → RO). Plan and phases: [docs/plan.md](docs/plan.md).

## Invariants
- **The TV must always be revertible in one setting.** Nothing we do may leave the TV unable to play without Batman. Every TV-side change is recorded with its revert step in [docs/runbooks/tv-setup.md](docs/runbooks/tv-setup.md) in the same PR.
- **Never set the server cache to 0** (it switches to a 45 MB in-memory ring buffer that stops while paused). Cache policy and its exact semantics: [docs/research/stremio-internals.md](docs/research/stremio-internals.md) § Cache.
- **server.js is a pinned, closed binary** (`infra/env/stremio-server.env`, sha256-verified). Tune it only through its settings / `POST /settings`, never by patching the bundle.
- **Portable host.** Everything the Mac needs is in the repo: `Brewfile`, `.mise.toml`, `launchd/`, `scripts/`, `infra/env/`. No hand-tweaked machine state; Linux (systemd) must stay a template away.
- **External subtitle tracks are loaded once per selection** (stremio-core): a served SRT is all the player will ever show from it. Live subtitles go inside our HLS stream instead (docs/design/hls-stream.md); the SRT for our own stream is only the bridge for segments already buffered.
- **The translation model never sees timestamps.** Cue ids in, cue ids out; code re-applies timings and re-wraps (≤ 2 lines × ~42 chars).

## Layering (src/stremio_plus_plus/)
`config/` (typed env, the only reader of the environment) · `log/` → `server/` (Stremio server HTTP client) · `state/` (SQLite, append-only migrations) → `watch/` (server-log tracker → playback events) → feature packages (`downloads/`, `subtitles/`, `stream/`, `sources/`) → `app/` (FastAPI routes + lifespan wiring) → `boot.py`. Imports point only leftwards; feature packages never import each other. One concern per file, ≤ ~200 LOC, a `constants.py` per package for magic values, tests as `*_test.py` next to the code (Python module names are `snake_case`; the global kebab-case filename rule yields to the import system here).
- Every request the companion makes to the server carries `?src=companion` (`server.client.StremioServer.file_url`) so the tracker never mistakes our reads for the TV's.
- Per-run env overrides go through `mise exec -- env KEY=… <cmd>`: mise's env files win over variables set before `mise exec`.

## Mac-specific workflow (no `wt`, `devstack`, Ansible on Batman)
- Branch + PR for every change; `.githooks/pre-push` refuses pushes to `main` and runs `mise run pre-push`.
- Before merging: `mise run gate` (stand-in for `wt pre-merge`) posts `devbox/pre-merge` on the PR head.
- Session artifacts go to `/tmp/stremio-plus-plus-*`, never the repo.

## Routing
| Occasion | Doc | Guardrail |
|---|---|---|
| Make it usable by others (config, providers, distribution) | [docs/design/public-release.md](docs/design/public-release.md) | proposal: nothing built until the owner decides the open questions |
| Move to another host | [docs/runbooks/migrate-host.md](docs/runbooks/migrate-host.md) | everything per-machine lives in `.env.local`, `state.db` and logins; `mise run host:doctor` must be all green |
| Change anything on the TV | [docs/runbooks/tv-setup.md](docs/runbooks/tv-setup.md) | record the current value and the revert step first |
| Rely on a server.js behaviour | [docs/research/stremio-internals.md](docs/research/stremio-internals.md) | re-verify against the pinned bundle; cite file:line |
| Pick or change a subtitle tool/model | [docs/research/subtitle-stack.md](docs/research/subtitle-stack.md) | benchmark on Batman before switching |
| Add a secret | devbox `docs/repo-secrets.md` | `secrets/*.age` via `repo-secrets` only — see [TODO.md](TODO.md) for the macOS engine status |
| Defer work / a decision / an owner action | `docs/work/backlog.md` · `tbd.md` · `ideas.md` · `TODO.md` | nothing lives only in chat |
| Phase 0 results | [docs/research/phase-0-results.md](docs/research/phase-0-results.md) | go/no-go recorded before phase 1 |
