#!/usr/bin/env bash
# Run a command with the companion's runtime secrets (ADDON_TOKEN) in its environment, in memory only
# (devbox repo-secrets: a secret enters a process via `repo-secrets exec`, never a decrypted file).
set -euo pipefail
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
exec repo-secrets exec secrets/companion.env.age -- "$@"
