#!/usr/bin/env python3
"""短时独立对照：区分主执行树和收集器辅助执行树。"""

import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUTS = ROOT / "agents/branch_ablation_official_z3_20261102/inputs"
BIN = HERE / "isla-frozen-src/target/release/isarch"
SEED = ROOT / "agents/branch_ablation_official_z3_20261102/bin/seed_control.so"
JOBS = [("flags-arithmetic", "A", 110, 300, "F_BIN_RM_TYPE_S"),
        ("sat", "A", 109, 300, "VFUNARY0"),
        ("flags-arithmetic", "B", 110, 180, "F_BIN_RM_TYPE_S"),
        ("sat", "B", 109, 180, "VFUNARY0")]


def launch(job):
    name, arm, cpu, budget, clause = job
    directory = HERE / f"aux-{name}-{arm}"
    directory.mkdir(exist_ok=True)
    (directory / "output").mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(LD_LIBRARY_PATH="/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib", LD_PRELOAD=str(SEED),
               ISLA_ABLATION_SEED="17", ISLA_ABLATION_SEED_LOG=str(directory / "seed.log"))
    command = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M", "-o", str(directory / "time.txt"),
               "timeout", "--signal=TERM", "--kill-after=10s", f"{budget}s", "taskset", "-c", str(cpu), str(BIN),
               "-A", str(INPUTS / name / f"{arm}.ir"), "-C", str(INPUTS / name / "config.toml"), "-T", "1",
               "--tastic", "qffp", "--smt-timeout", "7200s", "solve-state", "--clause=" + clause, "-D", "r"]
    log = (directory / "run.log").open("w")
    process = subprocess.Popen(command, cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)
    return directory, command, process, log


def main():
    result = {"started_utc": datetime.now(timezone.utc).isoformat(), "binary": str(BIN), "jobs": []}
    for pair in (JOBS[:2], JOBS[2:]):
        running = [launch(job) for job in pair]
        for directory, command, process, log in running:
            code = process.wait()
            log.close()
            result["jobs"].append({"directory": str(directory), "command": command, "exit_code": code})
            (HERE / "aux-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (HERE / "aux-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
