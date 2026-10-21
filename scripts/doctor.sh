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
# server.js is single-threaded: while it downloads at full speed it can take seconds to answer.
if server_s="$(curl -sf -m10 -o /dev/null -w '%{time_total}' "$STREMIO_SERVER_URL/settings")"; then
  ok "streaming server up ($STREMIO_SERVER_URL)"
  awk -v t="$server_s" 'BEGIN { exit !(t > 3) }' && warn "streaming server slow (${server_s}s to answer: busy downloading)" "normal during fast downloads; persistent → mise run services:restart server"
  tv_url="$(curl -sf -m10 "$STREMIO_SERVER_URL/get-https?ipAddress=${HOST_LAN_IP:-}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("https://%s:%s" % (d["domain"], d["port"]))' 2>/dev/null)"
  [ -n "$tv_url" ] && ok "TV server URL: $tv_url" || warn "no HTTPS endpoint yet" "mise run server:configure"
else
  bad "streaming server down" "mise run services:install server"
fi
curl -sf -m3 "http://127.0.0.1:$COMPANION_PORT/health" >/dev/null && ok "companion up (:$COMPANION_PORT)" || bad "companion down" "mise run services:install companion; logs: ~/Library/Logs/stremio-plus-plus/companion.log"
settings_err="$(curl -sf -m3 -H 'X-Stremio-Plus-Plus: 1' "http://127.0.0.1:$COMPANION_PORT/api/settings" | python3 -c 'import json,sys; print(json.load(sys.stdin)["error"] or "")' 2>/dev/null)"
if [ -n "$settings_err" ]; then
  bad "config.toml is invalid (last good settings still running): $settings_err" "fix ${CONFIG_DIR:-~/.config/stremio-plus-plus}/config.toml or use the UI"
fi
[ -f "${UI_DIR:-web/dist}/index.html" ] && ok "admin UI built: http://${HOST_LAN_IP:-<host>}:$COMPANION_PORT/" || warn "admin UI not built" "mise run ui:build"
launchctl print "gui/$(id -u)/io.github.fum4.stremio-plus-plus.cleanup" >/dev/null 2>&1 && ok "daily cleanup agent loaded" || bad "cleanup agent missing" "mise run services:install cleanup"

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
launchctl print "gui/$(id -u)/io.github.fum4.stremio-plus-plus.tls" >/dev/null 2>&1 && ok "weekly certificate renewal agent loaded" || bad "tls agent missing" "mise run services:install tls"

echo "TV"
# Control port and pairing gesture per TV_OS (src/stremio_plus_plus/tv/; only samsung is hardware-verified).
tv_os="${TV_OS:-samsung}"
case "$tv_os" in
  samsung) tv_port=8002 tv_pair="press Allow on the TV" ;;
  webos) tv_port="3000 3001" tv_pair="accept the prompt on the TV" ;;  # ws, or wss only on newer firmware
  androidtv) tv_port=6466 tv_pair="type the code the TV shows" ;;
  firetv) tv_port=5555 tv_pair="Developer options → ADB debugging ON first, then Always allow + OK" ;;
  *) tv_port=0 tv_pair="" ; bad "TV_OS=$tv_os is not samsung|webos|androidtv|firetv" "fix TV_OS in infra/env/companion.env" ;;
esac
tv_up=""
for p in $tv_port; do nc -z -G 3 "$TV_HOST" "$p" 2>/dev/null && { tv_up=$p; break; }; done
if [ -n "$tv_up" ]; then ok "TV reachable ($tv_os at $TV_HOST:$tv_up)"; else warn "TV not reachable at $TV_HOST:$tv_port ($tv_os)" "TV off/asleep, its IP changed (TV_HOST), or TV_OS is wrong (infra/env/companion.env)"; fi
python -m stremio_plus_plus.tv.cli status >/dev/null 2>&1 && ok "this host is paired with the TV" || bad "not paired with the TV" "mise run tv -- pair ($tv_pair)"

echo "Data"
if python -c 'from huggingface_hub import try_to_load_from_cache as t; from stremio_plus_plus.subtitles.constants import WHISPER_MODEL as m; import sys; sys.exit(0 if isinstance(t(m, "config.json"), str) else 1)' 2>/dev/null; then
  ok "Whisper model cached"
else
  bad "Whisper model not downloaded" "mise run models:fetch"
fi
free_gb="$(df -g "$HOME" | awk 'NR==2{print $4}')"
[ "$free_gb" -ge 20 ] && ok "disk: ${free_gb} GiB free" || warn "disk: only ${free_gb} GiB free" "whole-file caching wants room for a few episodes"

[ "$red" = 0 ] && echo "All green." || echo "Some checks failed."
exit "$red"
