#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${XIANGSHAN_TOOLS:?请设置 XIANGSHAN_TOOLS，目录中必须含 emu 和 NEMU DiffTest 动态库}"
XIANGSHAN_EMU_NAME=${XIANGSHAN_EMU_NAME:-emu}
XIANGSHAN_DIFF_SO_NAME=${XIANGSHAN_DIFF_SO_NAME:-riscv64-nemu-interpreter-so}
test -f "$XIANGSHAN_TOOLS/$XIANGSHAN_EMU_NAME"
test -f "$XIANGSHAN_TOOLS/$XIANGSHAN_DIFF_SO_NAME"

docker build -t dx_run_difftest:latest "$ROOT"
docker rm -f dx_run_difftest >/dev/null 2>&1 || true
docker run --name dx_run_difftest --rm \
  -v "$ROOT:/workspace/difftest-xiangshan" \
  -v "$ROOT/../isla:/workspace/isla:ro" \
  -v "$XIANGSHAN_TOOLS:/tools:ro" \
  -e XS_VLEN_BITS="${XS_VLEN_BITS:-128}" \
  -e ISLA_DROP_VREG_STATE="${ISLA_DROP_VREG_STATE:-1}" \
  -e XIANGSHAN_EMU="/tools/$XIANGSHAN_EMU_NAME" \
  -e XIANGSHAN_DIFF_SO="/tools/$XIANGSHAN_DIFF_SO_NAME" \
  dx_run_difftest:latest /workspace/difftest-xiangshan/run.sh
