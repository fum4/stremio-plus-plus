#!/usr/bin/env bash
# Read-only health check of this host's setup (`mise run host:doctor`). Exit 1 if anything is red.
set -uo pipefail
red=0
ok()   { printf '  \033[32m✔\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✘\033[0m %s\n      → %s\n' "$1" "$2"; red=1; }
warn() { printf '  \033[33m!\033[0m %s\n      → %s\n' "$1" "$2"; }

claude_bin="${CLAUDE_CLI:-}"; claude_bin="${claude_bin/#\~/$HOME}"  # config paths may start with ~

echo "Tools"
for bin in ffmpeg ffprobe age gh; do
  command -v "$bin" >/dev/null && ok "$bin" || bad "$bin missing" "mise run setup (Brewfile)"
done
[ -x "$claude_bin" ] && ok "claude CLI at $claude_bin" || bad "claude CLI not found at ${claude_bin:-<unset>}" "install Claude Code, or set CLAUDE_CLI in .env.local"
if [ -x "$claude_bin" ] && "$claude_bin" auth status 2>/dev/null | grep -q '"loggedIn": true'; then
  ok "claude CLI logged in (subscription translates the subtitles)"
else
  bad "claude CLI not logged in" "run: claude, then /login"
fi

echo "Network"
current_ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [ -z "${HOST_LAN_IP:-}" ]; then
  bad "HOST_LAN_IP unset" "add HOST_LAN_IP=<this Mac's reserved LAN IP> to .env.local"
elif [ "$current_ip" != "$HOST_LAN_IP" ]; then
  bad "HOST_LAN_IP=$HOST_LAN_IP but Wi-Fi has ${current_ip:-no IP}" "fix the DHCP reservation or .env.local, then mise run server:configure and update the TV URL"
else
  ok "LAN IP $HOST_LAN_IP matches Wi-Fi"
fi

echo "Services"
if curl -sf -m3 "$STREMIO_SERVER_URL/settings" >/dev/null; then
  ok "streaming server up ($STREMIO_SERVER_URL)"
  tv_url="$(curl -sf -m5 "$STREMIO_SERVER_URL/get-https?ipAddress=${HOST_LAN_IP:-}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("https://%s:%s" % (d["domain"], d["port"]))' 2>/dev/null)"
  [ -n "$tv_url" ] && ok "TV server URL: $tv_url" || warn "no HTTPS endpoint yet" "mise run server:configure"
else
  bad "streaming server down" "mise run services:install server"
fi
curl -sf -m3 "http://127.0.0.1:$COMPANION_PORT/health" >/dev/null && ok "companion up (:$COMPANION_PORT)" || bad "companion down" "mise run services:install companion; logs: ~/Library/Logs/stremio-companion/companion.log"
launchctl print "gui/$(id -u)/io.github.fum4.stremio-companion.cleanup" >/dev/null 2>&1 && ok "daily cleanup agent loaded" || bad "cleanup agent missing" "mise run services:install cleanup"

echo "Addon (HTTPS)"
cert="${COMPANION_DATA_DIR/#\~/$HOME}/tls/certificates/$ADDON_DOMAIN.crt"
if [ -f "$cert" ]; then
  end="$(openssl x509 -noout -enddate -in "$cert" | cut -d= -f2)"
  days=$(( ( $(date -j -f '%b %e %T %Y %Z' "$end" +%s) - $(date +%s) ) / 86400 ))
  [ "$days" -ge 14 ] && ok "certificate for $ADDON_DOMAIN valid $days more days" || bad "certificate expires in $days days" "mise run tls:renew (weekly agent: services:install tls)"
else
  bad "no certificate for $ADDON_DOMAIN" "mise run tls:renew"
fi
resolved="$(dig +short "$ADDON_DOMAIN" @1.1.1.1 | tail -1)"
[ "$resolved" = "${HOST_LAN_IP:-}" ] && ok "$ADDON_DOMAIN → $resolved (this host)" || bad "$ADDON_DOMAIN → ${resolved:-nothing}, not ${HOST_LAN_IP:-?}" "update the stremio record in Nomadware.io infra/terraform/records.tf"
# --resolve: test the service itself, independent of this Mac's resolver cache (Tailscale MagicDNS
# can hold a stale answer for a while after DNS changes).
code="$(curl -s -o /dev/null -w '%{http_code}' -m5 --resolve "$ADDON_DOMAIN:$ADDON_HTTPS_PORT:${resolved:-127.0.0.1}" "https://$ADDON_DOMAIN:$ADDON_HTTPS_PORT/${ADDON_TOKEN:-x}/manifest.json")"
[ "$code" = 200 ] && ok "addon answers over HTTPS (mise run addon:url for the install URL)" || bad "addon over HTTPS returned ${code}" "mise run services:restart companion; companion.log"
local_answer="$(dig +short "$ADDON_DOMAIN" | tail -1)"
[ "$local_answer" = "$resolved" ] || warn "this Mac's resolver answers '${local_answer:-nothing}' for $ADDON_DOMAIN" "stale cache (Tailscale MagicDNS); clears on its own, or: sudo killall -HUP mDNSResponder"
launchctl print "gui/$(id -u)/io.github.fum4.stremio-companion.tls" >/dev/null 2>&1 && ok "weekly certificate renewal agent loaded" || bad "tls agent missing" "mise run services:install tls"

echo "TV"
if nc -z -G 3 "$TV_HOST" 8002 2>/dev/null; then ok "TV reachable ($TV_HOST)"; else warn "TV not reachable at $TV_HOST" "TV off/asleep, or its IP changed (TV_HOST in infra/env/companion.env)"; fi
python -m stremio_companion.tv.cli status >/dev/null 2>&1 && ok "this host is paired with the TV" || bad "not paired with the TV" "mise run tv -- pair (press Allow on the TV)"

echo "Data"
if python -c 'from huggingface_hub import try_to_load_from_cache as t; from stremio_companion.subtitles.constants import WHISPER_MODEL as m; import sys; sys.exit(0 if isinstance(t(m, "config.json"), str) else 1)' 2>/dev/null; then
  ok "Whisper model cached"
else
  bad "Whisper model not downloaded" "mise run models:fetch"
fi
free_gb="$(df -g "$HOME" | awk 'NR==2{print $4}')"
[ "$free_gb" -ge 20 ] && ok "disk: ${free_gb} GiB free" || warn "disk: only ${free_gb} GiB free" "whole-file caching wants room for a few episodes"

[ "$red" = 0 ] && echo "All green." || echo "Some checks failed."
exit "$red"
