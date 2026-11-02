#!/usr/bin/env python3
"""实验专用：当前插桩程序的完整 A 臂对照。"""

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
CLAUSE = {"flags-arithmetic": "F_BIN_RM_TYPE_S", "sat": "VFUNARY0"}


def main():
    result = {"started_utc": datetime.now(timezone.utc).isoformat(), "cpu": 110, "runs": {}}
    for name, clause in CLAUSE.items():
        directory = HERE / ("final-" + name + "-A")
        directory.mkdir(exist_ok=True)
        (directory / "output").mkdir(exist_ok=True)
        env = os.environ.copy()
        env.update(LD_LIBRARY_PATH="/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib", LD_PRELOAD=str(SEED),
                   ISLA_ABLATION_SEED="17", ISLA_ABLATION_SEED_LOG=str(directory / "seed.log"))
        command = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M", "-o", str(directory / "time.txt"),
                   "timeout", "--signal=TERM", "--kill-after=10s", "7200s", "taskset", "-c", "110", str(BIN),
                   "-A", str(INPUTS / name / "A.ir"), "-C", str(INPUTS / name / "config.toml"), "-T", "1",
                   "--tastic", "qffp", "--smt-timeout", "7200s", "solve-state", "--clause=" + clause]
        with (directory / "run.log").open("w") as log:
            process = subprocess.run(command, cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)
        result["runs"][name] = {"exit_code": process.returncode, "command": command}
        (HERE / "final-a-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (HERE / "final-a-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
