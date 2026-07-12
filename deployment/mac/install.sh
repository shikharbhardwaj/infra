#!/bin/bash
# Applies deployment/mac/launch-agents/*.plist to this machine: substitutes
# USERNAME for the current user, copies into ~/Library/LaunchAgents, and
# (re)loads each agent. Safe to re-run after `git pull`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$DEST_DIR"

for src in "$SCRIPT_DIR"/launch-agents/*.plist; do
    name="$(basename "$src")"
    dest="$DEST_DIR/$name"
    label="$(basename "$name" .plist)"

    sed "s/USERNAME/$(whoami)/g" "$src" > "$dest"

    launchctl unload "$dest" 2>/dev/null || true
    launchctl load "$dest"
    echo "Loaded $label"
done
