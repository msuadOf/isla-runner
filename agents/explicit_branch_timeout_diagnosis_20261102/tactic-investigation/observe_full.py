from pathlib import Path
import json
import os
import time

here = Path(__file__).resolve().parent
jobs = json.loads((here / 'full-launch.json').read_text())
seen = {}
while len(seen) < len(jobs):
    for job in jobs:
        key = f'{job["workload"]}/{job["tactic"]}'
        if key in seen:
            continue
        pid = job['pid']
        try:
            stat = Path(f'/proc/{pid}/stat').read_text()
            state = stat.rsplit(')', 1)[1].split()[0]
            if state != 'Z':
                continue
        except FileNotFoundError:
            pass
        seen[key] = {
            'workload': job['workload'], 'tactic': job['tactic'],
            'timeout_pid': pid, 'started_monotonic': job['started_monotonic'],
            'exit_seen_monotonic': time.monotonic(),
            'elapsed_s_observed': time.monotonic() - job['started_monotonic'],
            'precision_s': 0.2,
        }
        (here / 'full-exit-observed.json').write_text(json.dumps(seen, indent=2))
    time.sleep(0.1)
