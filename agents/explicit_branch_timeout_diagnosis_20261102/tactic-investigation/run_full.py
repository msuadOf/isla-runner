from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import subprocess
import time

root = Path(__file__).resolve().parents[3]
here = Path(__file__).resolve().parent
official = root / 'agents/branch_ablation_official_z3_20261102'
seed_hook = official / 'bin/seed_control.so'
library = Path('/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3.4.0')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, data):
    path.write_text(json.dumps(data, indent=2))

jobs = []
for workload, clause, offset in [
    ('flags-arithmetic', 'F_BIN_RM_TYPE_S', 0),
    ('sat', 'VFUNARY0', 3),
]:
    for index, tactic in enumerate(('qffp', 'default', 'smt')):
        cpu = 100 + offset + index
        dest = here / 'full' / workload / tactic
        dest.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(
            LD_PRELOAD=str(seed_hook),
            ISLA_ABLATION_SEED='17',
            ISLA_ABLATION_SEED_LOG=str(dest / 'seed.log'),
        )
        command = [
            'timeout', '--signal=TERM', '--kill-after=10s', '7200s',
            'taskset', '-c', str(cpu), str(official / 'bin/isarch'),
            '-A', str(official / 'inputs' / workload / 'B.ir'),
            '-C', str(official / 'inputs' / workload / 'config.toml'),
            '-T', '1', '--tastic', tactic, '--smt-timeout', '7200s',
            'solve-state', f'--clause={clause}',
        ]
        output = (dest / 'run.log').open('w')
        started = time.monotonic()
        process = subprocess.Popen(command, env=env, cwd=dest, stdout=output, stderr=subprocess.STDOUT)
        job = {
            'workload': workload, 'tactic': tactic, 'seed': 17,
            'cpu': cpu, 'pid': process.pid, 'started_monotonic': started,
            'command': command, 'isarch_sha256': sha(official / 'bin/isarch'),
            'ir_sha256': sha(official / 'inputs' / workload / 'B.ir'),
            'config_sha256': sha(official / 'inputs' / workload / 'config.toml'),
            'seed_hook_sha256': sha(seed_hook), 'library_sha256': sha(library),
            'state': 'running',
        }
        write(dest / 'launch.json', job)
        jobs.append((job, process, output, dest))
write(here / 'full-launch.json', [job for job, _, _, _ in jobs])

def wait_one(job, process, output, dest):
    _, status, usage = os.wait4(process.pid, 0)
    ended = time.monotonic()
    process.returncode = os.waitstatus_to_exitcode(status)
    output.close()
    result_file = next((dest / 'output').glob('*.json'), None) if (dest / 'output').exists() else None
    result = {
        **job, 'state': 'done', 'exit_code': process.returncode,
        'elapsed_s': ended - job['started_monotonic'],
        'user_s': usage.ru_utime, 'sys_s': usage.ru_stime,
        'seed_log': (dest / 'seed.log').read_text() if (dest / 'seed.log').exists() else None,
        'json_sha256': sha(result_file) if result_file else None,
    }
    if result_file:
        data = json.loads(result_file.read_text())
        result['summary'] = data.get('summary')
        result['gen'] = len(data.get('gen', []))
    write(dest / 'result.json', result)
    return result

with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
    futures = [pool.submit(wait_one, *item) for item in jobs]
    for future in as_completed(futures):
        future.result()
        write(here / 'full-results.json', [
            json.loads((d / 'result.json').read_text()) if (d / 'result.json').exists() else j
            for j, _, _, d in jobs
        ])
