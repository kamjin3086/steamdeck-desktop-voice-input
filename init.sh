#!/usr/bin/env bash
# SteamOS: install only in this checkout and the current user's home.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
finish() {
    result=$?
    if (( result != 0 )); then
        echo "Installation incomplete (exit code $result). Resolve the error above and run again."
    fi
    if [[ -t 0 && ${VOICE_INPUT_NO_PAUSE:-0} != 1 ]]; then
        read -r -p 'Press Enter to close this window...' _ || true
    fi
}
trap finish EXIT
command -v python3 >/dev/null || { echo 'Python 3.10 or newer is required.'; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ is required"'
# Inspect first, then repair missing/broken venvs and dependencies.
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
    python3 -m venv --clear .venv
fi
if ! .venv/bin/python -c 'import sherpa_onnx; from PySide6 import QtCore, QtWidgets, QtNetwork' >/dev/null 2>&1 \
    || ! .venv/bin/python -m pip check; then
    .venv/bin/python -m pip install --only-binary=:all: --upgrade --force-reinstall -r requirements.txt
fi
.venv/bin/python -m voice_input.setup "$@"
