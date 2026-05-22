#!/usr/bin/env bash
# Uninstall the FortytwoBot launchd agent.
set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.fortytwo.agent.plist"
LOG="$HOME/Library/Logs/fortytwo-agent.log"

if [[ ! -f "$PLIST" ]]; then
    echo "Not installed: $PLIST"
    exit 0
fi

launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"

echo "Unloaded and removed: $PLIST"
if [[ -f "$LOG" ]]; then
    echo "Log file kept at: $LOG (delete manually if you want)"
fi
