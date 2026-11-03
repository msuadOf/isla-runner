#!/usr/bin/env python3
"""对候选IR的纯数据出口做局部负变异，核永久检查不会误绿。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / 'isla/test/float_ir/check_float_closure_branches.py'
CASES = (
    ('rounded_of_nx_swap', 'zieee_f16_rounded_exceptions',
     'zz440, zz450, zz45)', 'zz45, zz450, zz440)', 'check_rounded'),
    ('rounded_self_eq', 'zieee_f16_rounded_exceptions',
     'zfp32_eq(zlo, zz40)', 'zfp32_eq(zlo, zlo)', 'check_rounded'),
    ('rounded_uf_without_tiny', 'zieee_f16_rounded_exceptions',
     'zstrict_and_bool(zz45, zz448)', 'zstrict_and_bool(zz45, zz45)', 'check_rounded'),
    ('threshold_nx_lost', 'zieee_exact_threshold_exceptions',
     'zz420, zz436, zz40)', 'zz420, zz436, false)', 'check_exact_threshold'),
    ('int_nx_lost', 'zieee_fp_to_int_core',
     'false, false, zz427)', 'false, false, false)', 'check_fp_to_int_core'),
    ('round_quiet_mode_wrong', 'zieee_round16_exceptions',
     'zieee_operand_invalid(false, zz41)', 'zieee_operand_invalid(true, zz41)', 'check_round'),
    ('conversion_finite_facts_lost', 'zieee_convert32_to_16_exceptions',
     'return = zz49 `', 'return = zieee_empty_exceptions(zz40) `', 'check_conversion_gate'),
    ('rod_nx_false_also_jam', 'zieee_rod32_to_16',
     'zitezIB16zK(zz415, zz416, zz47)', 'zitezIB16zK(zz415, zz416, zz416)', 'check_rod_helper'),
    ('rod_quiet_mode_wrong', 'zieee_rod32_to_16',
     'zieee_operand_invalid(false, zz41)', 'zieee_operand_invalid(true, zz41)', 'check_rod_helper'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('float_closure_checker', CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    functions = checker.functions(args.ir.read_text())
    rows = []
    for label, name, before, after, check_name in CASES:
        original = functions[name]
        assert sum(line.count(before) for line in original) == 1, label
        changed = [line.replace(before, after) for line in original]
        check = getattr(checker, check_name)
        extra = ((name,) if check_name in ('check_rounded', 'check_round', 'check_conversion_gate',
                                          'check_rod_helper') else ())
        if check_name == 'check_round':
            extra = (name,)
            suffix = (16,)
        elif check_name == 'check_conversion_gate':
            suffix = (32, 'zieee_exact16_exceptions')
        elif check_name == 'check_rod_helper':
            suffix = (32, 16)
        else:
            suffix = ()
        try:
            check(*extra, changed, *suffix)
            rejected, reason = False, None
        except (AssertionError, KeyError, ValueError) as error:
            rejected, reason = True, str(error)
        rows.append({'case': label, 'rejected': rejected, 'reason': reason})
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
