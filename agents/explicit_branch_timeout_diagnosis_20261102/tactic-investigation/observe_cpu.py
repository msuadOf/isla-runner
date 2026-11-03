from pathlib import Path
import json
import os
import time

here = Path(__file__).resolve().parent
jobs = json.loads((here / 'full-launch.json').read_text())
ticks = os.sysconf('SC_CLK_TCK')
last = {}
while True:
    exits = here / 'full-exit-observed.json'
    if exits.exists() and len(json.loads(exits.read_text())) == len(jobs):
        break
    for job in jobs:
        key = f'{job["workload"]}/{job["tactic"]}'
        children = Path(f'/proc/{job["pid"]}/task/{job["pid"]}/children')
        try:
            taskset_pid = children.read_text().split()[0]
            taskset_children = Path(f'/proc/{taskset_pid}/task/{taskset_pid}/children').read_text().split()
            isarch_pid = taskset_children[0] if taskset_children else taskset_pid
            stat = Path(f'/proc/{isarch_pid}/stat').read_text().rsplit(')', 1)[1].split()
            last[key] = {
                'pid': int(isarch_pid), 'user_s': int(stat[11]) / ticks,
                'sys_s': int(stat[12]) / ticks,
                'sample_monotonic': time.monotonic(),
            }
        except (FileNotFoundError, IndexError):
            pass
    (here / 'full-cpu-sampled.json').write_text(json.dumps(last, indent=2))
    time.sleep(1)
