#!/usr/bin/env bash
# Render the nightly-update launchd agent for this checkout into ~/Library/LaunchAgents (does not load it).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
dest="$HOME/Library/LaunchAgents/ca.cityhallvotes.update.plist"
path="${LAUNCHD_PATH:-$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin}"
mkdir -p "$(dirname "$dest")" "$repo/state/logs"
sed -e "s|{{REPO}}|$repo|g" -e "s|{{PATH}}|$path|g" "$here/ca.cityhallvotes.update.plist.template" > "$dest"
plutil -lint "$dest"
echo "Wrote $dest. To turn it on: launchctl load \"$dest\""
