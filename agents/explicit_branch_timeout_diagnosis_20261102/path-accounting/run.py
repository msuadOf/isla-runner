#!/usr/bin/env python3
"""实验专用：并行运行两项冻结输入并保留路径事件。"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUTS = ROOT / "agents/branch_ablation_official_z3_20261102/inputs"
BIN = HERE / "isla-src/target/release/isarch"
SEED = ROOT / "agents/branch_ablation_official_z3_20261102/bin/seed_control.so"
CPU = {"flags-arithmetic": 96, "sat": 97}
CLAUSE = {"flags-arithmetic": "F_BIN_RM_TYPE_S", "sat": "VFUNARY0"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cpu_stat():
    wanted = {32, 33, 96, 97}
    result = {}
    for line in Path("/proc/stat").read_text().splitlines():
        first = line.split(maxsplit=1)[0]
        if first.startswith("cpu") and first[3:].isdigit() and int(first[3:]) in wanted:
            result[first] = [int(x) for x in line.split()[1:]]
    return result


def counts(path):
    result = {}
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            if "PATH_ACCOUNT " in line:
                key = line.split("PATH_ACCOUNT ", 1)[1]
                result[key] = result.get(key, 0) + 1
    return result


def main():
    launch = {"started_utc": datetime.now(timezone.utc).isoformat(), "monotonic": time.monotonic(),
              "binary_sha256": sha(BIN), "seed_preload_sha256": sha(SEED),
              "z3_sha256": sha(Path("/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3")),
              "source_head": "99a83bb9b2b285fca7c2a06e62548831d950b12a", "runs": {}}
    jobs = {}
    for name in CPU:
        directory = HERE / name
        directory.mkdir(exist_ok=True)
        (directory / "output").mkdir(exist_ok=True)
        arch = INPUTS / name / "B.ir"
        config = INPUTS / name / "config.toml"
        env = os.environ.copy()
        env["LD_PRELOAD"] = str(SEED)
        env["ISLA_ABLATION_SEED"] = "17"
        env["ISLA_ABLATION_SEED_LOG"] = str(directory / "seed.log")
        env["LD_LIBRARY_PATH"] = "/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib"
        command = ["/usr/bin/time", "-f", "wall_s=%e\\nuser_s=%U\\nsys_s=%S\\nmaxrss_kb=%M", "-o", str(directory / "time.txt"),
                   "timeout", "--signal=TERM", "--kill-after=10s", "7200s", "taskset", "-c", str(CPU[name]),
                   str(BIN), "-A", str(arch), "-C", str(config), "-T", "1", "--tastic", "qffp", "--smt-timeout", "7200s",
                   "solve-state", "--clause=" + CLAUSE[name]]
        log = (directory / "run.log").open("w")
        process = subprocess.Popen(command, cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT)
        jobs[name] = (process, log)
        launch["runs"][name] = {"pid": process.pid, "cpu": CPU[name], "command": command,
                                "ir_sha256": sha(arch), "config_sha256": sha(config)}
    (HERE / "launch.json").write_text(json.dumps(launch, ensure_ascii=False, indent=2) + "\n")
    with (HERE / "monitor.jsonl").open("w", buffering=1) as monitor:
        while True:
            status = {"utc": datetime.now(timezone.utc).isoformat(), "elapsed_s": time.monotonic() - launch["monotonic"],
                      "cpu_stat": cpu_stat(), "runs": {name: {"exit_code": process.poll(),
                      "events": counts(HERE / name / "run.log")} for name, (process, _) in jobs.items()}}
            monitor.write(json.dumps(status, ensure_ascii=False) + "\n")
            if all(process.poll() is not None for process, _ in jobs.values()):
                break
            time.sleep(60)
    for name, (process, log) in jobs.items():
        launch["runs"][name]["exit_code"] = process.wait()
        log.close()
    launch["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (HERE / "finished.json").write_text(json.dumps(launch, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
