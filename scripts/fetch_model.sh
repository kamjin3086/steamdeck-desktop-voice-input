#!/usr/bin/env bash
# Reuse registry download, repair, and checksum verification.
# Usage: scripts/fetch_model.sh [sensevoice|qwen3|omnilingual ...]
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if (( $# == 0 )); then set -- sensevoice; fi
exec ./run.sh models install "$@"
