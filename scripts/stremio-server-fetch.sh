#!/usr/bin/env bash
# Fetch the pinned server.js (infra/env/stremio-server.env, loaded by mise) and verify it.
set -euo pipefail
: "${STREMIO_SERVER_VERSION:?run via mise}" "${STREMIO_SERVER_SHA256:?run via mise}"
dest="var/stremio-server/server.js"
if [ -f "$dest" ] && shasum -a 256 "$dest" | grep -q "^$STREMIO_SERVER_SHA256 "; then
  echo "server.js $STREMIO_SERVER_VERSION already present"; exit 0
fi
mkdir -p "$(dirname "$dest")"
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
curl -sfL "https://dl.strem.io/server/$STREMIO_SERVER_VERSION/desktop/server.js" -o "$tmp"
actual="$(shasum -a 256 "$tmp" | cut -d' ' -f1)"
if [ "$actual" != "$STREMIO_SERVER_SHA256" ]; then
  echo "server:fetch: sha256 mismatch for $STREMIO_SERVER_VERSION (got $actual)" >&2; exit 1
fi
mv "$tmp" "$dest"; trap - EXIT
echo "server.js $STREMIO_SERVER_VERSION installed at $dest"
