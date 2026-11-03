from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

root = Path(__file__).resolve().parents[3]
here = Path(__file__).resolve().parent
official = root / 'agents/branch_ablation_official_z3_20261102'
seed_hook = official / 'bin/seed_control.so'
capture_hook = here / 'capture_raw.so'
jobs = []
for workload, query, cpu, clause in [
    ('flags-arithmetic', 47, 100, 'F_BIN_RM_TYPE_S'),
    ('sat', 235, 101, 'VFUNARY0'),
]:
    dest = here / workload
    dest.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(
        LD_PRELOAD=f'{capture_hook}:{seed_hook}',
        ISLA_ABLATION_SEED='17',
        ISLA_ABLATION_SEED_LOG=str(dest / 'seed.log'),
        ISLA_CAPTURE_QUERY=str(query),
        ISLA_CAPTURE_PATH=str(dest / 'raw.smt2'),
    )
    command = [
        'timeout', '--signal=TERM', '--kill-after=10s', '180s',
        'taskset', '-c', str(cpu), str(official / 'bin/isarch'),
        '-A', str(official / 'inputs' / workload / 'B.ir'),
        '-C', str(official / 'inputs' / workload / 'config.toml'),
        '-T', '1', '--tastic', 'qffp', '--smt-timeout', '7200s',
        'solve-state', f'--clause={clause}',
    ]
    output = (dest / 'run.log').open('w')
    started = time.monotonic()
    process = subprocess.Popen(command, env=env, cwd=dest, stdout=output, stderr=subprocess.STDOUT)
    jobs.append((workload, query, command, process, output, started, dest))

results = []
for workload, query, command, process, output, started, dest in jobs:
    code = process.wait()
    elapsed = time.monotonic() - started
    output.close()
    raw = dest / 'raw.smt2'
    results.append({
        'workload': workload, 'query': query, 'command': command,
        'exit_code': code, 'elapsed_s_upper_bound': elapsed,
        'captured': raw.exists(),
        'raw_sha256': hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None,
        'raw_bytes': raw.stat().st_size if raw.exists() else None,
        'seed_log': (dest / 'seed.log').read_text() if (dest / 'seed.log').exists() else None,
    })
(here / 'capture-results.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
