#!/usr/bin/env python3
"""Generate matched generated-Sail and direct-SoftFloat executable matrices."""
import csv
import re
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
out = Path(sys.argv[1])
root = here.parent.parent
rows = [r for r in csv.DictReader((here / 'native_calls.tsv').open(), delimiter='\t')
        if r['call_sites'] and r['sail_name'] not in
        {'ite', 'strict_and_bool', 'strict_or_bool', 'isla_bool_to_bit'}]
assert len(rows) == 97
source = (root / 'sail-riscv/model/prelude/ieee_fp_primops.sail').read_text()
sigs = {name: sig for name, sig in re.findall(r'^val (\w+) = (?:pure|impure) (?:"[^"]+"|\{[^}]+\}) : (.*)$', source, re.M)}

formats = {16: '0x3e00', 32: '0x3fc00000', 64: 'UINT64_C(0x3ff8000000000000)',
           128: 'float128_t{{0, UINT64_C(0x3fff800000000000)}}'}
second = {16: '0x3d00', 32: '0x3fa00000', 64: 'UINT64_C(0x3ff4000000000000)',
          128: 'float128_t{{0, UINT64_C(0x3fff400000000000)}}'}
third = {16: '0x3800', 32: '0x3f000000', 64: 'UINT64_C(0x3fe0000000000000)',
         128: 'float128_t{{0, UINT64_C(0x3ffe000000000000)}}'}

def fp(width, index=0):
    val = [formats, second, third][index][width]
    return val if width == 128 else f'float{width}_t{{{val}}}'

def result_expr(name, rm, width):
    if name.startswith('round_'):
        return 'static_cast<uint64_t>(' + {'round_nearest_ties_to_even': 'softfloat_round_near_even',
                'round_nearest_ties_to_away': 'softfloat_round_near_maxMag',
                'round_toward_positive': 'softfloat_round_max',
                'round_toward_negative': 'softfloat_round_min',
                'round_toward_zero': 'softfloat_round_minMag'}[name] + ')'
    if name == 'fp128_zero':
        return 'float128_t{{0, 0}}'
    match = re.match(r'fp(16|32|64|128)_(.*)', name)
    assert match, name
    n, op = int(match[1]), match[2]
    a, b, c = fp(n), fp(n, 1), fp(n, 2)
    if op == 'abs':
        mask = {32: 'UINT32_C(0x7fffffff)', 64: 'UINT64_C(0x7fffffffffffffff)',
                128: 'UINT64_C(0x7fffffffffffffff)'}[n]
        return f'abs_bits({a}, {mask})'
    if op in ('is_nan', 'is_negative'):
        return 'false'
    if op == 'from_ieee':
        return 'float128_t{{UINT64_C(0x123456789abcdef0), UINT64_C(0x3fff800000000000)}}' if n == 128 else a
    if op == 'to_ieee':
        return f'{a}.v'
    if op == 'sqrt':
        return f'f{n}_sqrt({a})'
    if op == 'round_to_integral':
        return f'f{n}_roundToInt({a}, {rm}, true)'
    conv = re.fullmatch(r'to_fp(16|32|64|128)', op)
    if conv:
        return f'f{n}_to_f{conv[1]}({a})'
    if op in ('from_signed', 'from_unsigned'):
        tag = 'i' if op == 'from_signed' else 'ui'
        if width == 32:
            val = 'INT32_MIN' if tag == 'i' else 'UINT32_MAX'
        else:
            val = 'INT64_MIN' if tag == 'i' else 'UINT64_MAX'
        return f'{tag}{width}_to_f{n}({val})'
    if op in ('eq', 'lt', 'lteq', 'gt', 'gteq'):
        fn = {'eq': 'eq', 'lt': 'lt_quiet', 'lteq': 'le_quiet',
              'gt': 'lt_quiet', 'gteq': 'le_quiet'}[op]
        x, y = (b, a) if op in ('gt', 'gteq') else (a, b)
        return f'f{n}_{fn}({x}, {y})'
    if op in ('add', 'sub', 'mul', 'div'):
        return f'f{n}_{op}({a}, {b})'
    if op == 'fma':
        return f'f{n}_mulAdd({a}, {b}, {c})'
    conv = re.fullmatch(r'to_(signed|unsigned)(32|64)', op)
    if conv:
        fn = 'i' if conv[1] == 'signed' else 'ui'
        return f'static_cast<uint{conv[2]}_t>(f{n}_to_{fn}{conv[2]}({a}, {rm}, true))'
    if op == 'to_bf16':
        return f'f32_to_bf16({a}).v'
    raise AssertionError(name)

def generated_args(name, rm, width):
    if name.startswith('round_') or name == 'fp128_zero':
        return ['UNIT']
    n, op = re.match(r'fp(16|32|64|128)_(.*)', name).groups()
    n = int(n)
    if op == 'from_ieee':
        return ['wide_input' if n == 128 else formats[n]]
    if op in ('from_signed', 'from_unsigned'):
        val = ('UINT64_C(0xffff000080000000)' if op == 'from_signed' else 'UINT64_C(0xffff0000ffffffff)') if width == 32 else ('UINT64_C(0x8000000000000000)' if op == 'from_signed' else 'UINT64_MAX')
        return [str(rm), val]
    if op in ('abs', 'is_nan', 'is_negative', 'to_ieee'):
        return [fp(n)]
    if op in ('eq', 'lt', 'lteq', 'gt', 'gteq'):
        return [fp(n), fp(n, 1)]
    if op in ('sqrt', 'round_to_integral') or op.startswith(('to_fp', 'to_signed', 'to_unsigned', 'to_bf16')):
        return [str(rm), fp(n)]
    if op in ('add', 'sub', 'mul', 'div'):
        return [str(rm), fp(n), fp(n, 1)]
    if op == 'fma':
        return [str(rm), fp(n), fp(n, 1), fp(n, 2)]
    raise AssertionError(name)

prelude = '''#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <climits>
#include <cassert>
#include <type_traits>
static void row(const char *name, uint64_t x) { std::printf("%s %016" PRIx64, name, x); }
static void row(const char *name, bool x) { row(name, static_cast<uint64_t>(x)); }
template<class T, std::enable_if_t<std::is_integral<T>::value && !std::is_same<T, bool>::value && !std::is_same<T, uint64_t>::value, int> = 0>
static void row(const char *name, T x) { row(name, static_cast<uint64_t>(x)); }
static void row(const char *name, float16_t x) { row(name, x.v); }
static void row(const char *name, float32_t x) { row(name, x.v); }
static void row(const char *name, float64_t x) { row(name, x.v); }
static void row(const char *name, float128_t x) { std::printf("%s %016" PRIx64 ":%016" PRIx64, name, x.v[1], x.v[0]); }
static float32_t abs_bits(float32_t x, uint32_t mask) { x.v &= mask; return x; }
static float64_t abs_bits(float64_t x, uint64_t mask) { x.v &= mask; return x; }
static float128_t abs_bits(float128_t x, uint64_t mask) { x.v[1] &= mask; return x; }
'''
generated = ['#include "closure.h"', prelude, 'int main() {', '  model::Model m;', '  m.model_init();',
             '  lbits wide_input;', '  CREATE(lbits)(&wide_input);', '  wide_input.len = 128;',
             '  mpz_set_str(*wide_input.bits, "3fff800000000000123456789abcdef0", 16);']
oracle = ['#ifndef SOFTFLOAT_FAST_INT64', '#error "wrong ABI"', '#endif',
          'extern "C" {', '#include "softfloat.h"', '}', prelude,
          'int main() {']
count = 0
for row_data in rows:
    name = row_data['sail_name']
    sig = sigs[name]
    for width in ([32, 64] if "'n" in sig else [None]):
        has_rm = sig.split(' -> ')[0].find('float_rounding_mode') >= 0
        rms = range(5) if has_rm else [0]
        for rm in rms:
            label = name + (f'_{width}' if width else '') + (f'_rm{rm}' if has_rm else '')
            generated_name = name.replace('zero', 'zzero')
            method = 'zprobe_' + generated_name + (f'_{width}' if width else '')
            args = ', '.join(generated_args(name, rm, width))
            generated += [f'  row("{label}", m.{method}({args}));', '  std::putchar(\'\\n\');']
            native = result_expr(name, rm, width)
            oracle += [f'  softfloat_roundingMode = {rm};',
                       '  softfloat_detectTininess = softfloat_tininess_afterRounding;',
                       '  softfloat_exceptionFlags = 0;',
                       f'  row("{label}", {native});',
                       '  std::printf(" %02x\\n", static_cast<unsigned>(softfloat_exceptionFlags));']
            count += 1
generated += ['  KILL(lbits)(&wide_input);', '  m.model_fini();', '}']
oracle += ['}']
(out / 'matrix_generated.cpp').write_text('\n'.join(generated) + '\n')
(out / 'matrix_oracle.cpp').write_text('\n'.join(oracle) + '\n')
print(f'{len(rows)} typed FP declarations, {count} RM/width numeric cases')
