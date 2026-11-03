#!/usr/bin/env python3
"""对真实新IR做局部负变异，证明永久CFG回归拒绝关键误绿。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / 'isla/test/float_ir/check_float_closure_branches.py'
CASES = (
    ('flags_old_vs_joined', 'zaccrue_fflags', 'zeq_anythingzIB5zK(zz40, zz41)',
     'zeq_anythingzIB5zK(zz41, zz41)'),
    ('flags_sd_zero', 'zaccrue_fflags', 'z_update_Mstatus_SD(zz423, 0b1)',
     'z_update_Mstatus_SD(zz423, 0b0)'),
    ('signed_self_compare', 'zriscv_f16ToI16_pure', 'zeq_anythingzIB32zK(zz43, zz46)',
     'zeq_anythingzIB32zK(zz43, zz43)'),
    ('signed_wrong_negative_limit', 'zriscv_f16ToI16_pure', '0x8000', '0x0000'),
    ('div_zero_reason_lost', 'zieee_div16_exceptions', 'jump zz45 goto 106',
     'jump zz410 goto 106'),
    ('div_finite_gate_lost', 'zieee_div16_exceptions', 'jump zz424 goto 72',
     'jump zz45 goto 72'),
    ('rod_mode_five', 'zriscv_f32ToF16', 'zz42 = 0b110', 'zz42 = 0b101'),
    ('rod_nx_gate_lost', 'zieee_rod32_to_16', 'jump zz414 goto 36',
     'jump zz42 goto 36'),
    ('of_exit_lost', 'zieee_f16_rounded_exceptions',
     'zieee_exception_facts(false, false, true, zz450, zz45)',
     'zieee_exception_facts(false, false, false, zz450, zz45)'),
    ('add_inf_sign_reversed', 'zieee_add16_exceptions',
     'zz411 = znot_bool(zz412)', 'zz411 = zz412'),
    ('rounded_of_nx_swapped', 'zieee_f16_rounded_exceptions',
     ('jump zz440 goto 111', 'jump zz45 goto 107'),
     ('jump zz45 goto 111', 'jump zz440 goto 107')),
    ('rod_jam_base_lost', 'zieee_rod32_to_16',
     'zz418 = zor_vec(zz416, zz417)', 'zz418 = zor_vec(zz417, zz417)'),
    ('fma_product_sign_reversed', 'zieee_fma16_exceptions',
     'zz439 = znot_bool(zz440)', 'zz439 = zz440'),
    ('sqrt_negative_zero_reversed', 'zieee_sqrt16_exceptions',
     'zz45 = znot_bool(zz46)', 'zz45 = zz46'),
    ('add_nv_exit_lost', 'zieee_add16_exceptions',
     'return = zieee_empty_exceptions(true) `43 254:4-254:31',
     'return = zieee_empty_exceptions(false) `43 254:4-254:31'),
    ('mul_nv_exit_lost', 'zieee_mul16_exceptions',
     'return = zieee_empty_exceptions(true) `43 408:4-408:31',
     'return = zieee_empty_exceptions(false) `43 408:4-408:31'),
    ('sqrt_nv_exit_lost', 'zieee_sqrt16_exceptions',
     'return = zieee_empty_exceptions(true) `43 466:4-466:31',
     'return = zieee_empty_exceptions(false) `43 466:4-466:31'),
    ('fma_nv_exit_lost', 'zieee_fma16_exceptions',
     'return = zieee_empty_exceptions(true) `43 502:4-502:31',
     'return = zieee_empty_exceptions(false) `43 502:4-502:31'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('float_closure_checker', CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    original = args.ir.read_text()
    checker.check(original, args.ir)
    rows = []
    for label, name, old, new in CASES:
        match = re.search(r'(?ms)^fn ' + re.escape(name) + r'\([^\n]*\) \{\n(.*?)^\}', original)
        assert match, name
        body = match.group(1)
        changes = list(zip(old, new)) if isinstance(old, tuple) else [(old, new)]
        changed = body
        for before, after in changes:
            assert changed.count(before) == 1, (label, before, changed.count(before))
            changed = changed.replace(before, after, 1)
        mutant = original[:match.start(1)] + changed + original[match.end(1):]
        try:
            checker.check(mutant, label)
            rejected, reason = False, None
        except (AssertionError, KeyError, ValueError) as exc:
            rejected, reason = True, str(exc)
        rows.append({'case': label, 'function': name, 'old': old, 'new': new,
                     'mutant_sha256': hashlib.sha256(mutant.encode()).hexdigest(),
                     'rejected': rejected, 'reason': reason})
    result = {'ir_sha256': hashlib.sha256(args.ir.read_bytes()).hexdigest(),
              'checker_sha256': hashlib.sha256(CHECKER.read_bytes()).hexdigest(),
              'count': len(rows), 'all_rejected': all(row['rejected'] for row in rows),
              'cases': rows}
    with args.output.open('x') as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print(json.dumps({'count': result['count'], 'all_rejected': result['all_rejected']},
                     ensure_ascii=False))
    if not result['all_rejected']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
