#!/usr/bin/env python3
"""Run the old overflow-if base with only the activity gate added."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPERIMENT = ROOT / "agents/branch_ablation_official_z3_20261102"
DIAG = ROOT / "agents/explicit_branch_timeout_diagnosis_20261102"
IR = HERE / "generation-cached/rv64d_v128_e64.ir"
CONFIG = EXPERIMENT / "inputs/sat/config.toml"
OUT = HERE / os.environ.get("ISLA_OLD_GATE_RUN", "run")
OUT.mkdir(exist_ok=False)
CPU = int(os.environ.get("ISLA_OLD_GATE_CPU", "98"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


env = os.environ.copy()
env.update(LD_PRELOAD=f"{DIAG / 'probe.so'}:{EXPERIMENT / 'bin/seed_control.so'}",
           ISLA_ABLATION_SEED="17", ISLA_ABLATION_SEED_LOG=str(OUT / "seed.log"),
           ISLA_QUERY_LOG=str(OUT / "queries.tsv"))
cmd = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
       "-o", str(OUT / "time.txt"), "timeout", "--signal=TERM", "--kill-after=10s",
       "7200s", "taskset", "-c", str(CPU), str(EXPERIMENT / "bin/isarch"),
       "-A", str(IR), "-C", str(CONFIG), "-T", "1", "--tastic", "qffp",
       "--smt-timeout", "7200s", "solve-state", "--clause=VFUNARY0"]
if os.environ.get("ISLA_OLD_GATE_FORK") == "1":
    cmd += ["-D", "f"]
record = {"command": cmd, "cpu": CPU, "utc_start": dt.datetime.now(dt.timezone.utc).isoformat(),
          "sha256": {"ir": sha(IR), "config": sha(CONFIG),
                     "isarch": sha(EXPERIMENT / "bin/isarch"),
                     "probe": sha(DIAG / "probe.so"),
                     "seed": sha(EXPERIMENT / "bin/seed_control.so")}}
start = time.monotonic()
with (OUT / "run.log").open("w") as log:
    proc = subprocess.Popen(cmd, cwd=OUT, env=env, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    record["pid"] = proc.pid
    (OUT / "command.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"pid": proc.pid, "cpu": CPU}), flush=True)
    record["exit_code"] = proc.wait()
record.update(elapsed_s=time.monotonic() - start,
              utc_end=dt.datetime.now(dt.timezone.utc).isoformat(),
              run_log_sha256=sha(OUT / "run.log"),
              queries_sha256=sha(OUT / "queries.tsv"))
(OUT / "result.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"exit_code": record["exit_code"],
                  "elapsed_s": record["elapsed_s"]}), flush=True)
