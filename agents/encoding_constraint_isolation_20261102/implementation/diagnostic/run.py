#!/usr/bin/env python3
"""Run the isolated 300-second stage probe on the frozen old flags input."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INPUT = ROOT / "agents/branch_ablation_official_z3_20261102/inputs/flags-arithmetic"
Z3 = Path("/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3")
PRELOAD = ROOT / "agents/branch_ablation_official_z3_20261102/bin/seed_control.so"
BINARY = HERE / "target/release/isarch"
RUN = HERE / "run"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    RUN.mkdir(exist_ok=False)
    env = os.environ.copy()
    env.update({
        "LD_PRELOAD": str(PRELOAD),
        "LD_LIBRARY_PATH": str(Z3.parent),
        "ISLA_ABLATION_SEED": "17",
        "ISLA_ABLATION_SEED_LOG": str(RUN / "seed-intercept.log"),
    })
    command = [
        "/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
        "-o", str(RUN / "time.txt"),
        "timeout", "--signal=TERM", "--kill-after=10s", "300s",
        "taskset", "-c", "74", str(BINARY),
        "-A", str(INPUT / "B.ir"), "-C", str(INPUT / "config.toml"),
        "-T", "1", "--tastic", "qffp", "--smt-timeout", "7200s",
        "solve-state", "--clause=F_BIN_RM_TYPE_S",
    ]
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_head": subprocess.check_output(["git", "-C", str(HERE / "isla-src"), "rev-parse", "HEAD"], text=True).strip(),
        "instrument_patch_sha256": sha(HERE / "instrument.patch"),
        "binary_sha256": sha(BINARY), "ir_sha256": sha(INPUT / "B.ir"),
        "config_sha256": sha(INPUT / "config.toml"),
        "z3_sha256": sha(Z3), "seed_preload_sha256": sha(PRELOAD),
        "command": command, "cpu": 74, "sibling_cpu": 10,
        "ldd": subprocess.check_output(["ldd", str(BINARY)], text=True, env=env),
    }
    (RUN / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    start = time.monotonic()
    with (RUN / "run.log").open("wb") as output:
        process = subprocess.Popen(command, cwd=RUN, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        metadata["pid"] = process.pid
        (RUN / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
        metadata["returncode"] = process.wait()
    metadata["elapsed_wall_s"] = time.monotonic() - start
    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["time_txt"] = (RUN / "time.txt").read_text()
    (RUN / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
