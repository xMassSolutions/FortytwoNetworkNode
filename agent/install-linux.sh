#!/usr/bin/env bash
# Install the FortytwoBot agent as a systemd --user service on Linux.
#
# Usage:
#   ./install-linux.sh <bot-url> <agent-token> <scripts-root> [docker-container]
#
# After install, the agent runs at user login (lingers across logout if
# `loginctl enable-linger $USER` is set), restarts on failure, and writes
# logs to ~/.cache/fortytwo-agent.log.
#
# Pass a docker-container name as the 4th arg if the FortyTwo node is
# running inside a Docker container (the agent will use `docker top` /
# `docker inspect` instead of pgrep). Leave blank for native installs.
#
# System-wide install (root, runs without a logged-in user — useful for
# headless servers): set FORTYTWO_SYSTEMD_SCOPE=system before running.

set -euo pipefail

if [[ $# -lt 3 ]]; then
    cat >&2 <<EOF
Usage: $0 <bot-url> <agent-token> <scripts-root> [docker-container]

Example (native):
    $0 https://<your-bot>.onrender.com \\
        \$(openssl rand -hex 20) \\
        ~/FortytwoCLI/fortytwo-p2p-inference-scripts-main

Example (Docker — pass the container name as the 4th arg):
    $0 https://<your-bot>.onrender.com \\
        \$(openssl rand -hex 20) \\
        ~/fortytwo-data/scripts \\
        fortytwo-p2p-inference

For a system-wide install (root, runs without a logged-in user):
    FORTYTWO_SYSTEMD_SCOPE=system sudo -E $0 <args>
EOF
    exit 2
fi

BOT_URL="$1"
AGENT_TOKEN="$2"
SCRIPTS_ROOT="$3"
DOCKER_CONTAINER="${4:-}"
SCOPE="${FORTYTWO_SYSTEMD_SCOPE:-user}"  # user (default) or system

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT="$HERE/push_agent.py"
TEMPLATE="$HERE/fortytwo-agent.service"

if [[ ! -f "$AGENT" ]]; then
    echo "ERROR: push_agent.py not found at $AGENT" >&2
    exit 1
fi
if [[ ! -f "$TEMPLATE" ]]; then
    echo "ERROR: systemd unit template not found at $TEMPLATE" >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not on PATH. Install Python 3 first." >&2
    exit 1
fi
if ! command -v systemctl >/dev/null 2>&1; then
    echo "ERROR: systemctl not available. This installer is systemd-only." >&2
    echo "  Run the agent manually:" >&2
    echo "  python3 $AGENT --bot-url $BOT_URL --agent-token <token> --scripts-root $SCRIPTS_ROOT" >&2
    exit 1
fi

# Expand ~ in scripts-root
SCRIPTS_ROOT="${SCRIPTS_ROOT/#\~/$HOME}"
if [[ ! -d "$SCRIPTS_ROOT" ]]; then
    echo "WARNING: $SCRIPTS_ROOT does not exist. Agent will fail until logs appear there." >&2
fi

chmod +x "$AGENT"

# Resolve python3 path explicitly so the unit file doesn't depend on PATH.
PYTHON_BIN="$(command -v python3)"

# Decide where the unit lives + log path.
if [[ "$SCOPE" == "system" ]]; then
    UNIT_DIR="/etc/systemd/system"
    LOG_PATH="/var/log/fortytwo-agent.log"
    SYSTEMCTL="systemctl"
    # Ensure the log file exists and is writable
    sudo touch "$LOG_PATH" || { echo "ERROR: can't create $LOG_PATH (need sudo)" >&2; exit 1; }
    sudo chmod 666 "$LOG_PATH"
else
    UNIT_DIR="$HOME/.config/systemd/user"
    LOG_PATH="$HOME/.cache/fortytwo-agent.log"
    SYSTEMCTL="systemctl --user"
fi

mkdir -p "$UNIT_DIR"
mkdir -p "$(dirname "$LOG_PATH")"
touch "$LOG_PATH"

UNIT_PATH="$UNIT_DIR/fortytwo-agent.service"

# Optional --docker-container arg pair
if [[ -n "$DOCKER_CONTAINER" ]]; then
    EXTRA_ARGS="--docker-container $DOCKER_CONTAINER"
else
    EXTRA_ARGS=""
fi

# Render template with sed
# Use | as the delimiter so paths with / don't need escaping.
sed \
    -e "s|/usr/bin/python3|$PYTHON_BIN|" \
    -e "s|{{AGENT_PATH}}|$AGENT|g" \
    -e "s|{{BOT_URL}}|$BOT_URL|g" \
    -e "s|{{AGENT_TOKEN}}|$AGENT_TOKEN|g" \
    -e "s|{{SCRIPTS_ROOT}}|$SCRIPTS_ROOT|g" \
    -e "s|{{EXTRA_ARGS}}|$EXTRA_ARGS|g" \
    -e "s|{{LOG_PATH}}|$LOG_PATH|g" \
    "$TEMPLATE" >"$UNIT_PATH.tmp"

# System-wide installs need root for /etc/systemd
if [[ "$SCOPE" == "system" ]]; then
    sudo mv "$UNIT_PATH.tmp" "$UNIT_PATH"
else
    mv "$UNIT_PATH.tmp" "$UNIT_PATH"
fi

# Enable + start
$SYSTEMCTL daemon-reload
$SYSTEMCTL enable fortytwo-agent.service
$SYSTEMCTL restart fortytwo-agent.service

echo "Agent installed:"
echo "  Scope:       $SCOPE"
echo "  Unit:        $UNIT_PATH"
echo "  Log:         $LOG_PATH"
echo "  Scripts:     $SCRIPTS_ROOT"
echo "  Bot URL:     $BOT_URL"
if [[ -n "$DOCKER_CONTAINER" ]]; then
    echo "  Docker:      $DOCKER_CONTAINER (using \`docker top\` for process detection)"
fi
echo
echo "Verify within ~60s:"
echo "  tail -f $LOG_PATH"
echo "  $SYSTEMCTL status fortytwo-agent"
echo
if [[ "$SCOPE" == "user" ]]; then
    echo "For the agent to survive logout, run once:"
    echo "  loginctl enable-linger \$USER"
    echo
fi
echo "Uninstall:"
echo "  $SYSTEMCTL stop fortytwo-agent"
echo "  $SYSTEMCTL disable fortytwo-agent"
echo "  rm $UNIT_PATH"
