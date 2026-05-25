#!/usr/bin/env bash
# Manual one-shot update for the FortytwoBot workstation agent (Linux + macOS).
#
# Run this when you want to pull the latest code from origin/main and
# bounce the agent right now (instead of waiting up to 30 min for the
# built-in auto-updater).
#
# Detects whether the agent is running under systemd --user, systemd
# system-wide, or launchd, and uses the right restart command.
#
# Usage (from anywhere):
#   ./agent/update-agent.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo ""
echo "=== Updating FortytwoBot agent ==="
echo "Repo:   $REPO_ROOT"
echo ""

echo "[1/3] git pull --ff-only"
git -C "$REPO_ROOT" pull --ff-only || {
    echo "  WARN: git pull non-zero exit -- continuing, but restart may run old code."
}

echo ""
echo "[2/3] Restarting agent service"
RESTARTED=""
LOG_PATH=""

if command -v systemctl >/dev/null 2>&1; then
    if systemctl --user is-active fortytwo-agent.service >/dev/null 2>&1; then
        systemctl --user restart fortytwo-agent.service
        RESTARTED="systemd --user"
        LOG_PATH="$HOME/.cache/fortytwo-agent.log"
    elif systemctl is-active fortytwo-agent.service >/dev/null 2>&1; then
        sudo systemctl restart fortytwo-agent.service
        RESTARTED="systemd system"
        LOG_PATH="/var/log/fortytwo-agent.log"
    fi
fi

if [[ -z "$RESTARTED" ]] && command -v launchctl >/dev/null 2>&1; then
    if launchctl list 2>/dev/null | grep -q com.fortytwo.agent; then
        launchctl kickstart -k "gui/$(id -u)/com.fortytwo.agent"
        RESTARTED="launchd (macOS)"
        LOG_PATH="$HOME/Library/Logs/fortytwo-agent.log"
    fi
fi

if [[ -z "$RESTARTED" ]]; then
    echo "  WARN: Couldn't find an active agent service. Start it via ./install-linux.sh"
    echo "        or ./install-mac.sh, or run python3 ./agent/push_agent.py manually."
    exit 1
fi
echo "  Restarted via $RESTARTED"

echo ""
echo "[3/3] agent.log tail (last 5 lines):"
sleep 5
if [[ -n "$LOG_PATH" && -f "$LOG_PATH" ]]; then
    tail -n 5 "$LOG_PATH" | sed 's/^/  /'
else
    echo "  (log not found at $LOG_PATH yet -- agent may still be starting)"
fi

echo ""
echo "Done. Verify the dashboard meta line shows the latest agent_version SHA."
