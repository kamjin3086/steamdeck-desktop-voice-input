#!/usr/bin/env bash
# Reuse registry download, repair, and checksum verification.
# Usage: scripts/fetch_model.sh [zh14m|bilingual|whisper-small ...]
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if (( $# == 0 )); then set -- zh14m; fi
exec ./run.sh models install "$@"
