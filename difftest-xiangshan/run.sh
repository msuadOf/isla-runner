#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
WORK=${WORK:-"$ROOT/work"}
XS_VLEN_BITS=${XS_VLEN_BITS:-128}
ISLA_JSON=${ISLA_JSON:-"$ROOT/smoke/isla-v128-vsetivli.json"}
EMULATOR=${XIANGSHAN_EMU:-/tools/emu}
DIFF_SO=${XIANGSHAN_DIFF_SO:-/tools/riscv64-spike-so}

python3 "$ROOT/pipeline.py" build --vlen-bits "$XS_VLEN_BITS" --input "$ISLA_JSON" --output "$WORK/elf"
python3 "$ROOT/pipeline.py" run --cases "$WORK/elf" --emulator "$EMULATOR" --diff-so "$DIFF_SO"
