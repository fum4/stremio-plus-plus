#!/usr/bin/env bash
# Run a command with the companion's runtime secrets (ADDON_TOKEN) in its environment, in memory only
# (devbox repo-secrets: a secret enters a process via `repo-secrets exec`, never a decrypted file).
set -euo pipefail
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
# Only the owner's host has the age key; everyone else runs without (config/host.py generates the
# token into secrets.toml instead).
if command -v repo-secrets >/dev/null && [ -f "$HOME/.config/age/stremio-plus-plus.key" ]; then
  # The owner's host: its installed addon URL is on ADDON_DOMAIN. Missing, the companion would
  # serve the addon under the stremio.rocks name and the installed addon would silently break, so
  # it has to be a choice: ADDON_DOMAIN=<domain>, or ADDON_DOMAIN= (empty) for the zero-config path.
  if [ -z "${ADDON_DOMAIN+set}" ]; then
    echo "with-secrets: owner host (age key present) but ADDON_DOMAIN is not set: add ADDON_DOMAIN=stremio.nomadware.io to .env.local, or ADDON_DOMAIN= (empty) to use the zero-config certificate (migrate-host.md step 4)" >&2
    exit 1
  fi
  exec repo-secrets exec secrets/companion.env.age -- "$@"
fi
if [ -n "${ADDON_DOMAIN:-}" ]; then  # the owner's setup: a new token would break the installed addon
  echo "with-secrets: ADDON_DOMAIN is set but the age key or repo-secrets is missing (migrate-host.md step 2)" >&2
  exit 1
fi
exec "$@"
