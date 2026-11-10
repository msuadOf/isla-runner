#!/usr/bin/env python3
"""Emit a runtime call for each actual generated wrapper signature."""
import argparse
import re
from pathlib import Path


def argument(typ, name):
    for width in (65, 113, 129, 1024):
        if typ == 'lbits' and name.endswith(f'_{width}'):
            return f'wide_{width}'
    return {
        'unit': 'UNIT',
        'uint_fast8_t': '0',
        'uint64_t': '42',
        'bool': 'true',
        'float16_t': 'float16_t{0x3c00}',
        'float32_t': 'float32_t{0x3f800000}',
        'float64_t': 'float64_t{UINT64_C(0x3ff0000000000000)}',
        'float128_t': 'float128_t{{0, UINT64_C(0x3fff000000000000)}}',
        'lbits': 'wide_input',
        'lbits *': '&wide_output',
        'lbits *rop': '&wide_output',
        'struct zprobe_record *rop': '&record_output',
        'struct zprobe_record': 'record_a',
    }[typ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('header', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    methods = re.findall(r'^  (\w+(?: \*)?) (zprobe_\w+)\(([^)]*)\);$', args.header.read_text(), re.M)
    assert len(methods) >= 109, len(methods)
    out = [
        '{',
        '  lbits wide_input, wide_output;',
        '  CREATE(lbits)(&wide_input);',
        '  CREATE(lbits)(&wide_output);',
        '  model::zprobe_record record_a, record_output;',
        '  CREATE(lbits)(&record_a.zraw);',
        '  CREATE(lbits)(&record_output.zraw);',
        '  record_a.zraw.len = 128;',
        '  mpz_set_ui(*record_a.zraw.bits, 0);',
        '  record_a.zvalue = float32_t{0x3f800000};',
        '  wide_input.len = 128;',
        '  mpz_set_str(*wide_input.bits, "3fff0000000000000000000000000000", 16);',
        *[f'  lbits wide_{width}; CREATE(lbits)(&wide_{width}); wide_{width}.len = {width}; mpz_set_ui(*wide_{width}.bits, 42);'
          for width in (65, 113, 129, 1024)],
        '  int actual_generated_calls = 0;',
    ]
    for ret, name, argspec in methods:
        types = [x.strip() for x in argspec.split(',') if x.strip()]
        call = f'model.{name}(' + ', '.join(argument(x, name) for x in types) + ')'
        out.append(f'  // {name}: {argspec} -> {ret}')
        out.append(f'  {call};')
        out.append('  ++actual_generated_calls;')
        out.append('  sentinel();')
    out += [
        f'  assert(actual_generated_calls == {len(methods)});',
        '  KILL(lbits)(&wide_input);',
        '  KILL(lbits)(&wide_output);',
        *[f'  KILL(lbits)(&wide_{width});' for width in (65, 113, 129, 1024)],
        '  KILL(lbits)(&record_a.zraw);',
        '  KILL(lbits)(&record_output.zraw);',
        '  std::printf("actual generated wrapper calls: %d\\n", actual_generated_calls);',
        '}',
    ]
    args.output.write_text('\n'.join(out) + '\n')
    print(f'{len(methods)} generated calls')


if __name__ == '__main__':
    main()
