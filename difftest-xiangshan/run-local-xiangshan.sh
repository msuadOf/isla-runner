#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
EMU=${XIANGSHAN_EMU:-"$ROOT/xiangshan/build/emu"}
DIFF_SO=${XIANGSHAN_DIFF_SO:-"$ROOT/xiangshan/ready-to-run/riscv64-nemu-interpreter-so"}

test -x "$EMU"
test -f "$DIFF_SO"
export XIANGSHAN_EMU="$EMU"
export XIANGSHAN_DIFF_SO="$DIFF_SO"
exec "$ROOT/run.sh"
