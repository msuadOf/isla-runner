from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[3]
here = Path(__file__).resolve().parent
official = root / 'agents/branch_ablation_official_z3_20261102'
workload = sys.argv[1]
query, clause = {'flags-arithmetic': (47, 'F_BIN_RM_TYPE_S'), 'sat': (235, 'VFUNARY0')}[workload]
dest = here / ('probe-only' if os.environ.get('ISLA_PROBE_ONLY') else 'compare') / workload
dest.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env.update(
    LD_PRELOAD=f'{here / os.environ.get("ISLA_CAPTURE_SO", "capture_raw_v2.so")}:{official / "bin/seed_control.so"}',
    ISLA_ABLATION_SEED='17', ISLA_ABLATION_SEED_LOG=str(dest / 'seed.log'),
    ISLA_CAPTURE_QUERY=str(query), ISLA_CAPTURE_PATH=str(dest / 'raw.smt2'),
    ISLA_COMPARE_LOG=str(dest / 'compare.tsv'), ISLA_COMPARE_STOP='1',
    ISLA_PROBE_ONLY=os.environ.get('ISLA_PROBE_ONLY', ''),
)
command = [
    'timeout', '--signal=TERM', '--kill-after=10s', '7200s',
    'taskset', '-c', '106', str(official / 'bin/isarch'),
    '-A', str(official / 'inputs' / workload / 'B.ir'),
    '-C', str(official / 'inputs' / workload / 'config.toml'),
    '-T', '1', '--tastic', 'qffp', '--smt-timeout', '7200s',
    'solve-state', f'--clause={clause}',
]
manifest = {'workload': workload, 'query': query, 'command': command, 'started_monotonic': time.monotonic()}
(dest / 'launch.json').write_text(json.dumps(manifest, indent=2))
with (dest / 'run.log').open('w') as f:
    code = subprocess.run(command, env=env, cwd=dest, stdout=f, stderr=subprocess.STDOUT).returncode
manifest.update(
    exit_code=code, elapsed_s=time.monotonic() - manifest['started_monotonic'],
    captured=(dest / 'raw.smt2').exists(),
    raw_sha256=hashlib.sha256((dest / 'raw.smt2').read_bytes()).hexdigest() if (dest / 'raw.smt2').exists() else None,
    seed_log=(dest / 'seed.log').read_text() if (dest / 'seed.log').exists() else None,
)
(dest / 'result.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
