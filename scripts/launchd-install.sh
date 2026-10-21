#!/usr/bin/env bash
# Render launchd/<name>.plist.template → ~/Library/LaunchAgents/<label>.plist and (re)load it.
# Placeholders: @REPO@ (this checkout), @HOME@, @MISE@ (absolute mise path).
set -euo pipefail
source "$(dirname "$0")/launchd-lib.sh"
mise_bin="$(command -v mise)"
mkdir -p "$AGENTS_DIR" "$LOG_DIR"
for name in $(service_names "$@"); do
  label="$(service_label "$name")"; plist="$AGENTS_DIR/$label.plist"
  sed -e "s|@REPO@|$REPO_ROOT|g" -e "s|@HOME@|$HOME|g" -e "s|@MISE@|$mise_bin|g" \
    "$REPO_ROOT/launchd/$name.plist.template" >"$plist"
  plutil -lint -s "$plist"
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$plist"
  echo "loaded $label (logs: $LOG_DIR/$name.log)"
done
