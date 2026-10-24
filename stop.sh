#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# stdlib only: also works if the project's venv is damaged.
exec python3 -m voice_input.runtime
