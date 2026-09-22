#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export XS_VLEN_BITS=128
export ISLA_JSON="$ROOT/smoke/isla-v128-vsetivli.json"
exec "$ROOT/run-local-xiangshan.sh"
