#!/usr/bin/env python3
"""Launch full-budget paired runs and record every exit in this directory."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EXPERIMENT = ROOT / "agents/branch_ablation_official_z3_20261102"
DIAG = ROOT / "agents/explicit_branch_timeout_diagnosis_20261102"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(arm, cpu):
    directory = HERE / arm
    directory.mkdir(exist_ok=False)
    env = os.environ.copy()
    env.update(
        LD_PRELOAD=f"{DIAG / 'probe.so'}:{EXPERIMENT / 'bin/seed_control.so'}",
        ISLA_ABLATION_SEED="17",
        ISLA_ABLATION_SEED_LOG=str(directory / "seed.log"),
        ISLA_QUERY_LOG=str(directory / "queries.tsv"),
    )
    cmd = [
        "/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
        "-o", str(directory / "time.txt"), "timeout", "--signal=TERM",
        "--kill-after=10s", "7200s", "taskset", "-c", str(cpu),
        str(EXPERIMENT / "bin/isarch"), "-A", str(HERE / f"{arm}.ir"),
        "-C", str(HERE / "config.toml"), "-T", "1", "--tastic", "qffp",
        "--smt-timeout", "7200s", "solve-state", "--clause=VFUNARY0",
    ]
    record = {
        "arm": arm,
        "cpu": cpu,
        "utc_start": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command": cmd,
        "cwd": str(directory.relative_to(ROOT)),
        "sha256": {name: sha(path) for name, path in {
            "ir": HERE / f"{arm}.ir", "config": HERE / "config.toml",
            "isarch": EXPERIMENT / "bin/isarch", "probe": DIAG / "probe.so",
            "seed_control": EXPERIMENT / "bin/seed_control.so",
        }.items()},
    }
    begin = time.monotonic()
    with (directory / "run.log").open("w") as log:
        proc = subprocess.Popen(cmd, cwd=directory, env=env, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        record["pid"] = proc.pid
        (directory / "command.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"arm": arm, "cpu": cpu, "pid": proc.pid,
                          "utc_start": record["utc_start"]}), flush=True)
        rc = proc.wait()
    record.update(exit_code=rc, elapsed_s=time.monotonic() - begin,
                  utc_end=dt.datetime.now(dt.timezone.utc).isoformat(),
                  log_sha256=sha(directory / "run.log"),
                  query_log_sha256=sha(directory / "queries.tsv"),
                  time_sha256=sha(directory / "time.txt"))
    (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"arm": arm, "exit_code": rc,
                      "elapsed_s": record["elapsed_s"]}), flush=True)


if __name__ == "__main__":
    threads = [threading.Thread(target=run, args=("B", 99)),
               threading.Thread(target=run, args=("A", 98))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
