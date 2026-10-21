#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/launchd-lib.sh"
for name in $(service_names "$@"); do
  label="$(service_label "$name")"
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  rm -f "$AGENTS_DIR/$label.plist"
  echo "removed $label"
done
