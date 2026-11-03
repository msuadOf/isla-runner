#!/usr/bin/env python3
"""对收敛IR局部变异，核永久回归拒绝错接的控制和值字段。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / 'isla/test/float_ir/check_float_closure_branches.py'
CASES = (
    ('mul_nv_lost', 'zieee_mul16_exceptions',
     'return = zieee_exception_facts(zz421, false, false, false, false)',
     'return = zieee_exception_facts(false, false, false, false, false)'),
    ('mul_gate_wrong', 'zieee_mul16_exceptions',
     'jump zz416 goto 47', 'jump zz45 goto 47'),
    ('div_dz_lost', 'zieee_div16_exceptions',
     'return = zieee_exception_facts(zz433, zz415, false, false, false)',
     'return = zieee_exception_facts(zz433, false, false, false, false)'),
    ('narrow_flags_reversed', 'zriscv_f16ToI8_pure',
     'zitezIB5zK(zz44, zz421, zz42)', 'zitezIB5zK(zz44, zz42, zz421)'),
    ('narrow_value_reversed', 'zriscv_f16ToI8_pure',
     'zitezIB8zK(zz44, zz415, zz423)', 'zitezIB8zK(zz44, zz423, zz415)'),
    ('integer_invalid_reversed', 'zriscv_f16ToI32',
     'zitezIB32zK(zz416, zz46, zz44)', 'zitezIB32zK(zz416, zz44, zz46)'),
    ('integer_nan_limit_lost', 'zriscv_f16ToI32',
     'zitezIB32zK(zz47, 0x7FFFFFFF, zz49)',
     'zitezIB32zK(zz47, 0x80000000, zz49)'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('float_closure_checker', CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    original = args.ir.read_text()
    checker.check(original, args.ir)
    rows = []
    for label, name, before, after in CASES:
        match = re.search(r'(?ms)^fn ' + re.escape(name) + r'\([^\n]*\) \{\n(.*?)^\}', original)
        assert match, name
        body = match.group(1)
        assert body.count(before) == 1, (label, body.count(before))
        mutant = original[:match.start(1)] + body.replace(before, after, 1) + original[match.end(1):]
        try:
            checker.check(mutant, label)
            rejected, reason = False, None
        except (AssertionError, KeyError, ValueError) as error:
            rejected, reason = True, str(error)
        rows.append({'case': label, 'function': name, 'rejected': rejected, 'reason': reason,
                     'mutant_sha256': hashlib.sha256(mutant.encode()).hexdigest()})
    result = {'ir_sha256': hashlib.sha256(args.ir.read_bytes()).hexdigest(),
              'checker_sha256': hashlib.sha256(CHECKER.read_bytes()).hexdigest(),
              'count': len(rows), 'all_rejected': all(row['rejected'] for row in rows), 'cases': rows}
    with args.output.open('x') as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print(json.dumps({'count': result['count'], 'all_rejected': result['all_rejected']},
                     ensure_ascii=False))
    if not result['all_rejected']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
