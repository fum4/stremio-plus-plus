# TBD

## Where Batman's own machine config lives · 2026-10-21
Brewfile/launchd for *this project* live here, but machine-wide config (shell, mise global, `~/.local/bin/repo-secrets`, macOS defaults) has no home. Options: a chezmoi `darwin` profile in fum4/devbox; a separate `fum4/dotfiles-mac`. **Revisit when:** the owner picks, or a second Mac-only tool needs installing.

## Fork stremio-web? · 2026-10-21
Owner approved a public fork `fum4/stremio-web`, deferred. Note (2026-10-21): the TV runs closed-source **Stremio Theater**, so the fork means switching the TV to a different app (stremio-web sideloaded), not patching the current one. **Revisit when:** phase 0 shows the official app can't do a feature (no server-URL setting, no http addon subtitles), or mid-film track refresh is wanted.
