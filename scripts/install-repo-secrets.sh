#!/usr/bin/env bash
# Install the devbox repo-secrets engine (the one engine, never a copy in the repo) into
# ~/.local/bin, pinned to a reviewed devbox commit and verified by sha256.
# Bump: pick a devbox commit, review the engine diff, update both values.
set -euo pipefail
DEVBOX_COMMIT=4537eca43efe6fead32226a34b976075cb29b16f
ENGINE_SHA256=5005b2390c24aa17beed77b079802469507155ccc7e723c73c63e0ed48384960
dest="$HOME/.local/bin/repo-secrets"
if [ -f "$dest" ] && shasum -a 256 "$dest" | grep -q "^$ENGINE_SHA256 "; then
  echo "repo-secrets already at devbox@${DEVBOX_COMMIT:0:7}"; exit 0
fi
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
gh api "repos/fum4/devbox/contents/chezmoi/dot_local/bin/executable_repo-secrets?ref=$DEVBOX_COMMIT" \
  --jq .content | base64 -d >"$tmp"
actual="$(shasum -a 256 "$tmp" | cut -d' ' -f1)"
[ "$actual" = "$ENGINE_SHA256" ] || { echo "tools:repo-secrets: sha256 mismatch ($actual)" >&2; exit 1; }
mkdir -p "$(dirname "$dest")"; install -m 755 "$tmp" "$dest"
echo "repo-secrets installed from devbox@${DEVBOX_COMMIT:0:7}"
