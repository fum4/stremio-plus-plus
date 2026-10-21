#!/usr/bin/env bash
# Print where to finish the setup: the companion's UI on this Mac's LAN address.
set -euo pipefail
: "${COMPANION_PORT:?run via mise}"
ip="${HOST_LAN_IP:-$(ipconfig getifaddr "$(route -n get default | awk '/interface:/{print $2}')")}"
printf '\nstremio++ is running. Finish the setup in your browser (from any device at home):\n  http://%s:%s/\n\n' "$ip" "$COMPANION_PORT"
