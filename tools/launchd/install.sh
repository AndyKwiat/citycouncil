#!/usr/bin/env bash
# Render the nightly-update launchd agent for this checkout into ~/Library/LaunchAgents (does not load it).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
dest="$HOME/Library/LaunchAgents/ca.cityhallvotes.update.plist"
# launchd starts jobs with a bare PATH; the job needs claude, npx (nvm), cargo and ssh, so take this shell's PATH.
path="${LAUNCHD_PATH:-$PATH}"
mkdir -p "$(dirname "$dest")" "$repo/state/logs"
sed -e "s|{{REPO}}|$repo|g" -e "s|{{PATH}}|$path|g" "$here/ca.cityhallvotes.update.plist.template" > "$dest"
plutil -lint "$dest"
echo "Wrote $dest. To turn it on: launchctl bootstrap gui/$(id -u) \"$dest\""
