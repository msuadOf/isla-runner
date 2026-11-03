#!/usr/bin/env python3
"""Independent fork trace for the explicit arm; qualitative only."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPERIMENT = ROOT / "agents/branch_ablation_official_z3_20261102"
DIAG = ROOT / "agents/explicit_branch_timeout_diagnosis_20261102"
OUT = HERE / "B-forks"
OUT.mkdir(exist_ok=False)
cmd = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
       "-o", str(OUT / "time.txt"), "timeout", "--signal=TERM", "--kill-after=10s",
       "7200s", "taskset", "-c", "99", str(EXPERIMENT / "bin/isarch"),
       "-A", str(HERE / "B.ir"), "-C", str(HERE / "config.toml"), "-T", "1",
       "--tastic", "qffp", "--smt-timeout", "7200s", "solve-state",
       "--clause=VFUNARY0", "-D", "f"]
env = os.environ.copy()
env.update(LD_PRELOAD=f"{DIAG / 'probe.so'}:{EXPERIMENT / 'bin/seed_control.so'}",
           ISLA_ABLATION_SEED="17", ISLA_ABLATION_SEED_LOG=str(OUT / "seed.log"),
           ISLA_QUERY_LOG=str(OUT / "queries.tsv"))
record = {"command": cmd, "cpu": 99, "utc_start": dt.datetime.now(dt.timezone.utc).isoformat(),
          "input_sha256": hashlib.sha256((HERE / "B.ir").read_bytes()).hexdigest()}
start = time.monotonic()
with (OUT / "run.log").open("w") as log:
    proc = subprocess.Popen(cmd, cwd=OUT, env=env, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    record["pid"] = proc.pid
    (OUT / "command.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"pid": proc.pid, "cpu": 99}), flush=True)
    record["exit_code"] = proc.wait()
record.update(elapsed_s=time.monotonic() - start,
              utc_end=dt.datetime.now(dt.timezone.utc).isoformat())
(OUT / "result.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"exit_code": record["exit_code"], "elapsed_s": record["elapsed_s"]}), flush=True)
