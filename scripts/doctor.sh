#!/usr/bin/env bash
# Read-only health check of this host's setup (`mise run doctor`). Exit 1 if anything is red.
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
  bad "streaming server down" "mise run install-service server"
fi
curl -sf -m3 "http://127.0.0.1:$COMPANION_PORT/health" >/dev/null && ok "companion up (:$COMPANION_PORT)" || bad "companion down" "mise run install-service companion; logs: ~/Library/Logs/stremio-companion/companion.log"
launchctl print "gui/$(id -u)/io.github.fum4.stremio-companion.cleanup" >/dev/null 2>&1 && ok "daily cleanup agent loaded" || bad "cleanup agent missing" "mise run install-service cleanup"

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
