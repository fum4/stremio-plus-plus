# Shared by launchd-install.sh / launchd-uninstall.sh. Service name = template basename.
REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/stremio-companion"
LABEL_PREFIX="io.github.fum4.stremio-companion"

service_label() { echo "$LABEL_PREFIX.$1"; }

service_names() {
  if [ "$#" -gt 0 ]; then
    for n in "$@"; do
      [ -f "$REPO_ROOT/launchd/$n.plist.template" ] || { echo "unknown service: $n" >&2; exit 1; }
      echo "$n"
    done
  else
    for f in "$REPO_ROOT"/launchd/*.plist.template; do basename "$f" .plist.template; done
  fi
}
