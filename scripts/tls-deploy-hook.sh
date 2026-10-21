#!/usr/bin/env bash
# lego deploy hook: restart the companion so its HTTPS listener picks up the new certificate.
# A script, not an inline `sh -c '…'`: lego 5 splits the hook on whitespace without shell quoting.
# The companion may not be installed yet (first run in host:promote): a failed restart is fine.
launchctl kickstart -k "gui/$(id -u)/io.github.fum4.stremio-plus-plus.companion" || true
