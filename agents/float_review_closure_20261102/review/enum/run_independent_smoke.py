#!/usr/bin/env python3
"""只在独立审查目录执行正式 runner 已构造的完整 FLEQ_S 命令。"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parents[1] / 'validation' / 'run_clause.py'
record = json.loads((HERE / 'itrace-smoke-preflight.json').read_text())
namespace = {'__file__': str(RUNNER), '__name__': 'reviewed_runner'}
exec(compile(RUNNER.read_text(), str(RUNNER), 'exec'), namespace)
dest = HERE / 'harness-smoke-itrace'
dest.mkdir(exist_ok=False)
(dest / 'output' / 'trace').mkdir(parents=True)
(dest / 'output' / 'smt-timeouts').mkdir(parents=True)
inputs = json.loads((HERE / 'inputs.itrace-smoke.json').read_text())
seedlib = namespace['checked'](namespace['ROOT'], inputs['seed_preload'])
env = dict(os.environ, LD_PRELOAD=str(seedlib), ISLA_ABLATION_SEED='17',
           ISLA_ABLATION_SEED_LOG=str(dest / 'seed-intercept.log'), LD_DEBUG='libs')
env.pop('LD_LIBRARY_PATH', None)
started = time.monotonic()
with (dest / 'run.log').open('wb') as log:
    status = subprocess.run(record['command'], cwd=dest, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
ir = namespace['checked'](namespace['ROOT'], inputs['irs']['rv64-v128'])
config = namespace['checked'](namespace['ROOT'], inputs['configs']['rv64-fd-full'])
outputs = sorted((dest / 'output').glob('*.json'))
assert len(outputs) == 1
summary, count, kinds, schema = namespace['inspect_output'](outputs[0], 'FLEQ_S', ir, config)
trace = dest / 'output' / 'trace' / 'itrace_FLEQ_S.txt'
seed = namespace['seed_record'](dest / 'seed-intercept.log')
result = {**record, 'exit': status, 'elapsed_s': round(time.monotonic() - started, 3),
          'runner_sha256': hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
          'json_count': len(outputs), 'gen_count': count, 'return_kinds': kinds,
          'summary': summary, 'schema': schema, 'seed': seed,
          'itrace_bytes': trace.stat().st_size,
          'itrace_sha256': hashlib.sha256(trace.read_bytes()).hexdigest(),
          'json_sha256': hashlib.sha256(outputs[0].read_bytes()).hexdigest(),
          'loaded_z3': [line.strip() for line in (dest / 'run.log').read_text().splitlines()
                        if 'calling init:' in line and 'libz3' in line]}
result['pass'] = (status == 0 and schema and seed['valid'] and count > 0
                  and summary['status'] == 'finished' and trace.stat().st_size > 0
                  and all(summary[key] == 0 for key in namespace['PARTIAL']))
(dest / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
assert result['pass']
