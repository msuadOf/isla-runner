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
jobs = []
for tactic, cpu in [('qffp', 114), ('default', 115), ('smt', 116)]:
    dest = here / 'compare-685' / tactic
    dest.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        LD_PRELOAD=f'{here / "capture_raw_v5.so"}:{official / "bin/seed_control.so"}',
        ISLA_ABLATION_SEED='17', ISLA_ABLATION_SEED_LOG=str(dest / 'seed.log'),
        ISLA_CAPTURE_QUERY='685', ISLA_CAPTURE_PATH=str(dest / 'raw.smt2'),
        ISLA_COMPARE_LOG=str(dest / 'compare.tsv'), ISLA_COMPARE_ONE=tactic,
        ISLA_COMPARE_ONLY='1',
    )
    command = [
        'timeout', '--signal=TERM', '--kill-after=10s', '9000s',
        'taskset', '-c', str(cpu), str(official / 'bin/isarch'),
        '-A', str(official / 'inputs/flags-arithmetic/B.ir'),
        '-C', str(official / 'inputs/flags-arithmetic/config.toml'),
        '-T', '1', '--tastic', 'qffp', '--smt-timeout', '7200s',
        'solve-state', '--clause=F_BIN_RM_TYPE_S',
    ]
    output = (dest / 'run.log').open('w')
    started = time.monotonic()
    process = subprocess.Popen(command, env=env, cwd=dest, stdout=output, stderr=subprocess.STDOUT)
    launch = {'query': 685, 'comparison_tactic': tactic, 'cpu': cpu, 'seed': 17,
              'command': command, 'started_monotonic': started, 'pid': process.pid,
              'note': 'Outer 9000s includes reaching query 685; each fresh solver has explicit 7200s SMT timeout.'}
    (dest / 'launch.json').write_text(json.dumps(launch, indent=2))
    jobs.append((launch, process, output, dest))

def wait_one(launch, process, output, dest):
    _, status, usage = os.wait4(process.pid, 0)
    output.close()
    raw = dest / 'raw.smt2'
    result = {**launch, 'exit_code': os.waitstatus_to_exitcode(status),
              'elapsed_s': time.monotonic() - launch['started_monotonic'],
              'user_s': usage.ru_utime, 'sys_s': usage.ru_stime,
              'captured': raw.exists(),
              'raw_sha256': hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None,
              'raw_bytes': raw.stat().st_size if raw.exists() else None,
              'seed_log': (dest / 'seed.log').read_text() if (dest / 'seed.log').exists() else None}
    (dest / 'result.json').write_text(json.dumps(result, indent=2))
    return result

with ThreadPoolExecutor(max_workers=3) as pool:
    results = [future.result() for future in as_completed([pool.submit(wait_one, *job) for job in jobs])]
(here / 'compare-685-results.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
