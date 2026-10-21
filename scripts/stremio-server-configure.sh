#!/usr/bin/env bash
# Apply infra/stremio-server/settings.json + this host's LAN IP to the running server
# (POST /settings merges; the server persists it to $APP_PATH/server-settings.json).
# remoteHttps = the LAN IP: the server then serves HTTPS on :12470 under a strem.io-issued
# cert for <ip-dashed>.<id>.stremio.rocks — the TV app refuses plain http to non-localhost.
set -euo pipefail
: "${STREMIO_SERVER_URL:?run via mise}"
: "${STREMIO_REMOTE_HTTPS_IP:?set STREMIO_REMOTE_HTTPS_IP=<LAN IP> in .env.local}"
for _ in $(seq 1 30); do curl -sf -m2 "$STREMIO_SERVER_URL/settings" >/dev/null && break; sleep 1; done
body="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d["remoteHttps"]=sys.argv[2]; print(json.dumps(d))' \
  infra/stremio-server/settings.json "$STREMIO_REMOTE_HTTPS_IP")"
curl -sf -X POST -H 'content-type: application/json' --data "$body" "$STREMIO_SERVER_URL/settings" \
  | grep -q '"success":true'
https="$(curl -sf "$STREMIO_SERVER_URL/get-https?ipAddress=$STREMIO_REMOTE_HTTPS_IP" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("https://%s:%s" % (d["domain"], d["port"]))')"
echo "server settings applied; TV server URL: $https"
