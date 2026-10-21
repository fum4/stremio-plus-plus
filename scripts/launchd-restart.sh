#!/usr/bin/env bash
# Restart already-installed launchd agents (`mise run services:restart [server|companion]`).
set -euo pipefail
source "$(dirname "$0")/launchd-lib.sh"
names="${*:-server companion}"
for name in $names; do
  label="$(service_label "$name")"
  launchctl kickstart -k "gui/$(id -u)/$label"
  echo "restarted $label"
done
