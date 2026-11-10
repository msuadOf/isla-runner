#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$here/../.." && pwd)
out=${1:-"$root/.tmp/unified-backend-p1-adapter"}
sail_tool=${2:-"$root/isla/target/float-solve-evidence/unified-backend-p0/20260926T162859Z/sail-src/sail"}
sail_runtime=$(cd "$(dirname "$sail_tool")/lib" && pwd)
softfloat_source="$root/sail-riscv/dependencies/softfloat/berkeley-softfloat-3"
p2_wide_dir=${P2_WIDE_DIR-"$root/agents/float_support_review/tools/unified_backend_p2_wide"}
p2_extra_dir=${P2_EXTRA_DIR-"$root/agents/float_support_review/tools/unified_backend_p2_native_extra"}
extra_test_dir=${P2_EXTRA_TEST_DIR-}
mkdir -p "$out"
out=$(cd "$out" && pwd)

fixture_args=()
if [[ -n ${FULL_BINDINGS:-} ]]; then fixture_args+=(--all-bindings "$FULL_BINDINGS"); fi
full_public=OFF
if [[ -n ${FULL_BINDINGS:-} ]]; then full_public=ON; fi
python3 "$here/generate_fixture.py" "$root/sail-riscv/model/prelude/ieee_fp_primops.sail" "$out/closure.sail" "${fixture_args[@]}" | tee "$out/fixture_generation.txt"
preserve=()
while IFS= read -r name; do preserve+=(--c-preserve "$name"); done < "$out/preserve.txt"
"$sail_tool" --cpp --c-no-main --no-memo-z3 --no-color "${preserve[@]}" \
  --c-header-include sail_softfloat_types.h --c-include sail_softfloat.h \
  -o "$out/closure" "$out/closure.sail" > "$out/closure.stdout" 2> "$out/closure.stderr"
python3 "$here/generate_test_calls.py" "$out/closure.h" "$out/all_calls.inc" | tee "$out/call_generation.txt"
python3 "$here/generate_numeric_matrix.py" "$out" | tee "$out/matrix_generation.txt"

cmake -S "$here" -B "$out/build" \
  -DSOFTFLOAT_SOURCE_DIR="$softfloat_source" \
  -DSAIL_RUNTIME_DIR="$sail_runtime" \
  -DP2_WIDE_DIR="$p2_wide_dir" \
  -DP2_EXTRA_DIR="$p2_extra_dir" \
  -DP2_EXTRA_TEST_DIR="$extra_test_dir" \
  -DFULL_PUBLIC="$full_public" \
  -DGENERATED_CPP="$out/closure.cpp" -DGENERATED_DIR="$out" \
  -DCMAKE_BUILD_TYPE=Release > "$out/cmake.stdout" 2> "$out/cmake.stderr"
cmake --build "$out/build" --target closure_test generated_cases native_oracle matrix_generated matrix_oracle -j2 \
  > "$out/build.stdout" 2> "$out/build.stderr"
"$out/build/closure_test" > "$out/test.stdout" 2> "$out/test.stderr"
python3 "$here/compare_cases.py" "$out/build/generated_cases" "$out/build/native_oracle" \
  > "$out/compare.stdout" 2> "$out/compare.stderr"
python3 "$here/compare_cases.py" "$out/build/matrix_generated" "$out/build/matrix_oracle" \
  > "$out/matrix_compare.stdout" 2> "$out/matrix_compare.stderr"
state_object=$(find "$out/build/softfloat_tls" -name softfloat_state.c.o -print -quit)
readelf --wide -s "$state_object" | rg 'softfloat_(roundingMode|detectTininess|exceptionFlags)' > "$out/tls_symbols.txt"
cat "$out/test.stdout"
tail -1 "$out/compare.stdout"
tail -1 "$out/matrix_compare.stdout"
if [[ $full_public == ON ]]; then
  cmake --build "$out/build" --target public_values_test -j2 > "$out/public_build.stdout" 2> "$out/public_build.stderr"
  "$out/build/public_values_test" > "$out/public_test.stdout" 2> "$out/public_test.stderr"
  cat "$out/public_test.stdout"
fi
if [[ -n $extra_test_dir ]]; then
  cmake --build "$out/build" --target extra_integrated_test -j2 > "$out/extra_build.stdout" 2> "$out/extra_build.stderr"
  "$out/build/extra_integrated_test" > "$out/extra_test.stdout" 2> "$out/extra_test.stderr"
  tail -1 "$out/extra_test.stdout"
fi
python3 "$here/write_manifest.py" "$root" "$out" "$sail_tool" "${FULL_BINDINGS:-}" "$extra_test_dir"
