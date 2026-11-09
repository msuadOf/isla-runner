#!/usr/bin/env python3
"""在新生成的真实 IR 上验证组界、vstart 策略和全寄存器早退后态。"""
import argparse
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--ir', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = []
    for register, fields, power, expected in [
        (31, 2, 0, False), (30, 2, 0, True),
        (31, 2, -1, False), (30, 2, -1, True),
        (28, 2, 1, True), (30, 2, 1, False),
    ]:
        cases.append(dict(name=f'group-r{register}-nf{fields}-p{power}',
            function='valid_segment_group_without_overflow',
            argv=[f'0b{register:05b}', str(fields), str(power)], expected=str(expected).lower()))
    for function in ['illegal_load', 'illegal_store', 'illegal_indexed_load', 'illegal_indexed_store']:
        for register, expected in [(31, 'true'), (30, 'false')]:
            argv = [f'0b{register:05b}']
            if 'load' in function:
                argv.append('0b1')
            argv += ['2', '8', '0']
            if 'indexed' in function:
                argv.append('0')
            cases.append(dict(name=f'{function}-r{register}', function=function,
                              argv=argv, initial=['vtype={bits=0x0000000000000000}'], expected=expected))
    for start in [0, 127, 128, 65535]:
        cases.append(dict(name=f'vstart-{start}', function='get_start_element', argv=['()'],
                          initial=[f'vstart=0x{start:016x}'], expected=str(start), integer_result=True))
    for function, argv in [('process_vlre', ['1', '0b00000', '8', '0b00001', '2']),
                           ('process_vsre', ['1', '8', '0b00001', '0b00000', '2'])]:
        for start in [2, 128]:
            cases.append(dict(name=f'{function}-early-{start}', function=function, argv=argv,
                              initial=[f'vstart=0x{start:016x}'], expected='(|Retire_Success| (_ unit))', clears_vstart=True))
    results = []
    for case in cases:
        command = ['timeout', '20s', str(args.binary.resolve()), '-A', str(args.ir.resolve()),
                   '-C', str(args.config.resolve()), '-T', '1', '--timeout', '10', '--traces', '-m']
        for initial in case.get('initial', []):
            command += ['-I', initial]
        command += ['--', case['function'], *case['argv']]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (args.output / (case['name'] + '.log')).write_text(result.stdout)
        observed = re.findall(r'^Result: (.*)$', result.stdout, re.MULTILINE)
        checked = dict(case, command=command, exit_code=result.returncode, observed=observed)
        results.append(checked)
        (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        assert result.returncode == 0, (case['name'], result.returncode)
        if case.get('integer_result'):
            assert len(observed) == 1
            literal = re.fullmatch(r'\(_ bv([0-9]+) 128\)', observed[0])
            assert literal is not None, (case['name'], observed)
            assert int(literal.group(1)) == int(case['expected'])
        else:
            assert observed == [case['expected']], (case['name'], observed, case['expected'])
        if case.get('clears_vstart'):
            assert '(write-reg |vstart| nil #x0000000000000000)' in result.stdout
            assert '(read-mem' not in result.stdout and '(write-mem' not in result.stdout
        print(case['name'] + ': PASS', flush=True)
    (args.output / 'summary.json').write_text(json.dumps(dict(exit_code=0, passed=len(results)), indent=2) + '\n')


if __name__ == '__main__':
    main()
