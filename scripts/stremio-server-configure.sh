#!/usr/bin/env bash
# Apply infra/stremio-server/settings.json to the running server (POST /settings merges;
# the server persists it to $APP_PATH/server-settings.json). Waits up to 30 s for the server.
set -euo pipefail
: "${STREMIO_SERVER_URL:?run via mise}"
for _ in $(seq 1 30); do curl -sf -m2 "$STREMIO_SERVER_URL/settings" >/dev/null && break; sleep 1; done
curl -sf -X POST -H 'content-type: application/json' \
  --data @infra/stremio-server/settings.json "$STREMIO_SERVER_URL/settings" | grep -q '"success":true'
echo "server settings applied from infra/stremio-server/settings.json"
