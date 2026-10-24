#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
UNIT="$HOME/.config/systemd/user/voice-input.service"
mkdir -p "$(dirname "$UNIT")"
sed "s|%h/projects/voice-input|$PWD|g" packaging/voice-input.service > "$UNIT"
systemctl --user daemon-reload
systemctl --user enable --now voice-input.service
echo "Started. Follow logs: journalctl --user -u voice-input -f"
echo "Stop/uninstall: systemctl --user disable --now voice-input && rm $UNIT"
