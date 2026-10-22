# Shared by launchd-install.sh / launchd-uninstall.sh. Service name = template basename.
REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/stremio-plus-plus"
LABEL_PREFIX="io.github.fum4.stremio-plus-plus"

service_label() { echo "$LABEL_PREFIX.$1"; }

service_names() {
  if [ "$#" -gt 0 ]; then
    for n in "$@"; do
      [ -f "$REPO_ROOT/launchd/$n.plist.template" ] || { echo "unknown service: $n" >&2; exit 1; }
      echo "$n"
    done
  else
    for f in "$REPO_ROOT"/launchd/*.plist.template; do
      n="$(basename "$f" .plist.template)"
      # The lego renewal agent only exists for an own domain; without one the addon uses the
      # streaming server's certificate, which the companion renews itself.
      [ "$n" = tls ] && [ -z "${ADDON_DOMAIN:-}" ] && continue
      echo "$n"
    done
  fi
}
