#!/usr/bin/env bash
# Get or renew the Let's Encrypt certificate for ADDON_DOMAIN (DNS-01 via Cloudflare), then restart
# the companion so its HTTPS listener picks it up. Run through `mise run tls:renew`, which hands
# CF_DNS_API_TOKEN to this process only (repo-secrets exec). Idempotent: lego renews only when due.
set -euo pipefail
: "${ADDON_DOMAIN:?run via mise}" "${COMPANION_DATA_DIR:?run via mise}" "${CF_DNS_API_TOKEN:?run via mise run tls:renew}"
tls_dir="${COMPANION_DATA_DIR/#\~/$HOME}/tls"
mkdir -p "$tls_dir" && chmod 700 "$tls_dir"
# The companion may not be installed yet (first run in host:promote): a failed restart is fine.
restart="sh -c 'launchctl kickstart -k gui/$(id -u)/io.github.fum4.stremio-plus-plus.companion || true'"
# Public resolvers for the propagation check: the system resolver may be Tailscale's MagicDNS
# (100.100.100.100), which can serve stale answers.
lego run --accept-tos --dns cloudflare --dns.resolvers 1.1.1.1:53 --dns.resolvers 8.8.8.8:53 \
  --domains "$ADDON_DOMAIN" --path "$tls_dir" --deploy-hook "$restart"
