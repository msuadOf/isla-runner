#!/usr/bin/env python3
"""对新IR施加仅结构变异，确认永久检查拒绝活动运算泄漏。"""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SCRIPT = ROOT / 'isla/test/float_ir/check_special_semantic_branches.py'
spec = importlib.util.spec_from_file_location('permanent', SCRIPT)
permanent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permanent)
path = Path(sys.argv[1])
text = path.read_text()
functions = permanent.parse_functions(text)
body = functions['zexecute']
raw = body.splitlines()
nonblank = [i for i, line in enumerate(raw) if line.strip()]
instructions = [raw[i].strip() for i in nonblank]
files = shlex.split(re.search(r'(?m)^files (.*)$', text).group(1))
results = []
for name in ['FVVMATYPE', 'FVVMTYPE', 'VFWMACCBF16_VF']:
    gate = next(gate for gate in permanent.GATES if gate[0] == name)
    source_id = files.index(gate[1])
    location = re.compile(r'`' + str(source_id) + ' ' + str(gate[2]) + r':\d+-' + str(gate[3]) + r':\d+;')
    branch = next(pc for pc, line in enumerate(instructions) if line.startswith('jump ') and location.search(line))
    active = re.search(r'goto (\d+)', instructions[branch]).group(1)
    operation = next(pc for pc, instruction in enumerate(instructions)
                     if pc > int(active) and re.search(r'= z(?:fp_\w+_pure|bf16_to_f32)\(', instruction)
                     and (match := re.search(r'`' + str(source_id) + r' (\d+):', instruction))
                     and gate[2] < int(match.group(1)) < gate[3])
    before = next(pc for pc in range(branch - 1, max(branch - 15, 0), -1)
                  if re.match(r'\w+ : ', instructions[pc]))
    variants = []
    moved = raw.copy()
    moved[nonblank[before]], moved[nonblank[operation]] = moved[nonblank[operation]], moved[nonblank[before]]
    variants.append(('把活动运算提前到mask判断之前', moved, name + '活动出口漏运算'))
    leaked = raw.copy()
    leaked[nonblank[branch + 1]] = '  goto ' + active + ';'
    variants.append(('将非活动出口改到活动运算体', leaked, name + '不活动出口仍执行运算'))
    for mutation, changed, expected_error in variants:
        candidate = text.replace(body, '\n'.join(changed), 1)
        try:
            with redirect_stdout(io.StringIO()):
                permanent.check(candidate, 'negative-' + name)
        except AssertionError as error:
            reason = str(error)
            assert expected_error in reason, (mutation, expected_error, reason)
            results.append({'name': name, 'mutation': mutation, 'rejected': True, 'reason': reason})
        else:
            raise AssertionError(name + '变异未被拒绝')
(HERE / 'mask-cfg-negative-checks.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print('PASS: 三个gate的运算前移及假出口泄漏共六变异全部被永久检查拒绝')
