#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

root, out, sail = map(lambda s: Path(s).resolve(), sys.argv[1:4])
bindings = Path(sys.argv[4]).resolve() if len(sys.argv) > 4 and sys.argv[4] else None
extra_test = Path(sys.argv[5]).resolve() if len(sys.argv) > 5 and sys.argv[5] else None
files = [
    *sorted((root / 'tools/unified_backend_p1_adapter').rglob('*')),
    root / 'sail-riscv/model/prelude/ieee_fp_primops.sail',
    root / 'sail-riscv/dependencies/softfloat/CMakeLists.txt',
    root / 'sail-riscv/dependencies/softfloat/berkeley-softfloat-3/source/softfloat_state.c',
    root / 'sail-riscv/dependencies/softfloat/berkeley-softfloat-3/source/include/softfloat.h',
    root / 'sail-riscv/dependencies/softfloat/berkeley-softfloat-3/source/include/softfloat_types.h',
    root / 'isla/target/float-solve-evidence/unified-backend-p0/20260926T162859Z/compiler.patch',
    root / 'isla/target/float-solve-evidence/unified-backend-bindings/20260927/candidate-final/bindings.json',
    root / 'agents/float_support_review/tools/unified_backend_p2_wide/sail_softfloat_wide.h',
    root / 'agents/float_support_review/tools/unified_backend_p2_wide/sail_softfloat_wide.cpp',
    root / 'agents/float_support_review/tools/unified_backend_p2_native_extra/sail_softfloat_extra.h',
    root / 'agents/float_support_review/tools/unified_backend_p2_native_extra/sail_softfloat_extra.cpp',
    sail.parent / '_build/install/default/bin/sail',
    sail.parent / '_build/install/default/share/libsail/plugins/sail_plugin_c.cmxs',
    out / 'closure.sail', out / 'closure.cpp', out / 'closure.h',
    out / 'matrix_generated.cpp', out / 'matrix_oracle.cpp',
    out / 'all_calls.inc', out / 'test.stdout', out / 'matrix_compare.stdout',
    out / 'public_test.stdout', out / 'extra_test.stdout',
    out / 'build/softfloat_tls/libsoftfloat.a',
    out / 'build/libsail_softfloat.a',
    out / 'build/closure_test',
    out / 'build/generated_cases', out / 'build/native_oracle',
    out / 'build/matrix_generated', out / 'build/matrix_oracle',
    out / 'build/public_values_test', out / 'build/extra_integrated_test',
    out / 'build/CMakeFiles/sail_softfloat.dir/flags.make',
    out / 'build/softfloat_tls/CMakeFiles/softfloat.dir/flags.make',
    out / 'tls_symbols.txt',
]
if bindings:
    files.append(bindings)
if extra_test:
    files.extend(extra_test / name for name in ('extra.cpp', 'extra.h', 'numeric_tests.cpp'))
    files.append(root / 'agents/float_support_review/tools/unified_backend_p2_native_extra/test_support.h')
def display(path):
    return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)

manifest = {'sail_source_archive_commit': '446fb477c508853595ccc937ed60765aa685ae31',
            'full_bindings': display(bindings) if bindings else None,
            'extra_test_fixture': display(extra_test) if extra_test else None,
            'files_sha256': {str(p.relative_to(root)) if p.is_relative_to(root) else str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in files if p.is_file()}}
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
