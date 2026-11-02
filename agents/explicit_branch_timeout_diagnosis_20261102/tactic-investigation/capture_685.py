from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

root = Path(__file__).resolve().parents[3]
here = Path(__file__).resolve().parent
official = root / 'agents/branch_ablation_official_z3_20261102'
dest = here / 'flags-685-capture'
dest.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(
    LD_PRELOAD=f'{here / "capture_raw_v4.so"}:{official / "bin/seed_control.so"}',
    ISLA_ABLATION_SEED='17', ISLA_ABLATION_SEED_LOG=str(dest / 'seed.log'),
    ISLA_CAPTURE_QUERY='685', ISLA_CAPTURE_PATH=str(dest / 'raw.smt2'),
    ISLA_CAPTURE_ONLY='1',
)
command = [
    'timeout', '--signal=TERM', '--kill-after=10s', '1800s',
    'taskset', '-c', '106', str(official / 'bin/isarch'),
    '-A', str(official / 'inputs/flags-arithmetic/B.ir'),
    '-C', str(official / 'inputs/flags-arithmetic/config.toml'),
    '-T', '1', '--tastic', 'qffp', '--smt-timeout', '7200s',
    'solve-state', '--clause=F_BIN_RM_TYPE_S',
]
started = time.monotonic()
launch = {'query': 685, 'command': command, 'started_monotonic': started,
          'note': '1800s external bound is only for reaching the check; capture exits before Z3 solves query 685'}
(dest / 'launch.json').write_text(json.dumps(launch, indent=2))
with (dest / 'run.log').open('w') as f:
    code = subprocess.run(command, env=env, cwd=dest, stdout=f, stderr=subprocess.STDOUT).returncode
raw = dest / 'raw.smt2'
result = {**launch, 'exit_code': code, 'elapsed_s': time.monotonic() - started,
          'captured': raw.exists(), 'raw_sha256': hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None,
          'raw_bytes': raw.stat().st_size if raw.exists() else None,
          'seed_log': (dest / 'seed.log').read_text() if (dest / 'seed.log').exists() else None}
(dest / 'result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
