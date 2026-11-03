#!/usr/bin/env python3
"""AB/BA repetitions on paired physical cores, with each pair on one core."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import subprocess
import threading
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPERIMENT = ROOT / "agents/branch_ablation_official_z3_20261102"
DIAG = ROOT / "agents/explicit_branch_timeout_diagnosis_20261102"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(pair, arm, cpu):
    directory = HERE / "repeat" / f"pair{pair}" / arm
    directory.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(LD_PRELOAD=f"{DIAG / 'probe.so'}:{EXPERIMENT / 'bin/seed_control.so'}",
               ISLA_ABLATION_SEED="17",
               ISLA_ABLATION_SEED_LOG=str(directory / "seed.log"),
               ISLA_QUERY_LOG=str(directory / "queries.tsv"))
    cmd = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
           "-o", str(directory / "time.txt"), "timeout", "--signal=TERM",
           "--kill-after=10s", "7200s", "taskset", "-c", str(cpu),
           str(EXPERIMENT / "bin/isarch"), "-A", str(HERE / f"{arm}.ir"),
           "-C", str(HERE / "config.toml"), "-T", "1", "--tastic", "qffp",
           "--smt-timeout", "7200s", "solve-state", "--clause=VFUNARY0"]
    record = {"pair": pair, "arm": arm, "cpu": cpu,
              "utc_start": dt.datetime.now(dt.timezone.utc).isoformat(),
              "command": cmd, "ir_sha256": sha(HERE / f"{arm}.ir")}
    start = time.monotonic()
    with (directory / "run.log").open("w") as log:
        proc = subprocess.Popen(cmd, cwd=directory, env=env, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        record["pid"] = proc.pid
        (directory / "command.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"pair": pair, "arm": arm, "cpu": cpu,
                          "pid": proc.pid}), flush=True)
        record["exit_code"] = proc.wait()
    record.update(elapsed_s=time.monotonic() - start,
                  utc_end=dt.datetime.now(dt.timezone.utc).isoformat(),
                  log_sha256=sha(directory / "run.log"),
                  queries_sha256=sha(directory / "queries.tsv"))
    (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"pair": pair, "arm": arm, "exit_code": record["exit_code"],
                      "elapsed_s": record["elapsed_s"]}), flush=True)


def pairs(plan):
    for pair, cpu, order in plan:
        for arm in order:
            run(pair, arm, cpu)


if __name__ == "__main__":
    plans = [[(2, 98, "BA"), (4, 98, "AB")],
             [(3, 99, "AB"), (5, 99, "BA")]]
    threads = [threading.Thread(target=pairs, args=(plan,)) for plan in plans]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
