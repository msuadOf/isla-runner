from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[3]
here = Path(__file__).resolve().parent
official = root / 'agents/branch_ablation_official_z3_20261102'
probe = root / 'agents/explicit_branch_timeout_diagnosis_20261102/probe.so'
seed_hook = official / 'bin/seed_control.so'
tactic = sys.argv[1] if len(sys.argv) > 1 else 'default'
assert tactic in ('default', 'smt')

jobs = []
for workload, clause, cpu in [
    ('flags-arithmetic', 'F_BIN_RM_TYPE_S', 114),
    ('sat', 'VFUNARY0', 115),
]:
    dest = here / f'{tactic}-sample' / workload
    dest.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        LD_PRELOAD=f'{probe}:{seed_hook}', ISLA_ABLATION_SEED='17',
        ISLA_ABLATION_SEED_LOG=str(dest / 'seed.log'),
        ISLA_QUERY_LOG=str(dest / 'queries.tsv'),
    )
    command = [
        'timeout', '--signal=TERM', '--kill-after=10s', '300s',
        'taskset', '-c', str(cpu), str(official / 'bin/isarch'),
        '-A', str(official / 'inputs' / workload / 'B.ir'),
        '-C', str(official / 'inputs' / workload / 'config.toml'),
        '-T', '1', '--tastic', tactic, '--smt-timeout', '7200s',
        'solve-state', f'--clause={clause}',
    ]
    output = (dest / 'run.log').open('w')
    started = time.monotonic()
    process = subprocess.Popen(command, env=env, cwd=dest, stdout=output, stderr=subprocess.STDOUT)
    launch = {
        'workload': workload, 'tactic': tactic, 'cpu': cpu,
        'seed': 17, 'command': command, 'pid': process.pid,
        'started_monotonic': started,
        'isarch_sha256': hashlib.sha256((official / 'bin/isarch').read_bytes()).hexdigest(),
        'ir_sha256': hashlib.sha256((official / 'inputs' / workload / 'B.ir').read_bytes()).hexdigest(),
        'config_sha256': hashlib.sha256((official / 'inputs' / workload / 'config.toml').read_bytes()).hexdigest(),
        'probe_sha256': hashlib.sha256(probe.read_bytes()).hexdigest(),
    }
    (dest / 'launch.json').write_text(json.dumps(launch, indent=2))
    jobs.append((launch, process, output, dest))

def wait_one(launch, process, output, dest):
    _, status, usage = os.wait4(process.pid, 0)
    output.close()
    result = {
        **launch, 'exit_code': os.waitstatus_to_exitcode(status),
        'elapsed_s': time.monotonic() - launch['started_monotonic'],
        'user_s': usage.ru_utime, 'sys_s': usage.ru_stime,
        'seed_log': (dest / 'seed.log').read_text() if (dest / 'seed.log').exists() else None,
    }
    if (dest / 'output').exists():
        files = list((dest / 'output').glob('*.json'))
        if files:
            data = json.loads(files[0].read_text())
            result['summary'] = data.get('summary')
            result['gen'] = len(data.get('gen', []))
    begins, ends, durations, codes = {}, {}, [], {}
    for line in (dest / 'queries.tsv').read_text().splitlines():
        fields = line.split('\t')
        stage, query = fields[0], int(fields[1])
        if stage == 'begin':
            begins[query] = float(fields[4])
        elif stage == 'end':
            ends[query] = float(fields[4])
            durations.append((float(fields[5]), query))
            codes[fields[6]] = codes.get(fields[6], 0) + 1
    result.update(
        checks_begun=len(begins), checks_finished=len(ends),
        pending=sorted(begins.keys() - ends.keys()),
        max_completed=sorted(durations, reverse=True)[:5],
        cumulative_completed_s=sum(x[0] for x in durations),
        result_codes=codes,
    )
    (dest / 'result.json').write_text(json.dumps(result, indent=2))
    return result

with ThreadPoolExecutor(max_workers=2) as pool:
    results = [future.result() for future in as_completed([pool.submit(wait_one, *job) for job in jobs])]
(here / f'{tactic}-sample-results.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
