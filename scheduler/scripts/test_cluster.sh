#!/usr/bin/env bash
set -euo pipefail
SCHEDULER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$SCHEDULER_DIR/scripts/test_cluster.py" "$@"
