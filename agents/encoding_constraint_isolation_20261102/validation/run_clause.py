#!/usr/bin/env python3
"""Run one frozen complete Clause using an explicitly supplied new Release binary."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUTS = json.loads((HERE / "inputs.json").read_text())
TIME_FORMAT = "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path, expected):
    path = path.resolve(strict=True)
    actual = sha(path)
    if actual != expected:
        raise ValueError(f"SHA mismatch {path}: expected {expected}, got {actual}")
    return path


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("job", choices=("old_flags", "old_sat", "new_sat", "new_flags"))
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--z3", required=True, type=Path)
    parser.add_argument("--z3-sha256", required=True)
    parser.add_argument("--new-ir", type=Path)
    parser.add_argument("--new-ir-sha256")
    parser.add_argument("--batch", help="Optional version label; writes runs/<batch>/<job>")
    parser.add_argument("--cpu", type=int, choices=(100, 101, 102, 103))
    args = parser.parse_args()
    if args.batch and not re.fullmatch(r"[a-zA-Z0-9_-]+", args.batch):
        parser.error("--batch must contain only letters, digits, underscores, or hyphens")
    if args.job.startswith("new_") and not (args.new_ir and args.new_ir_sha256):
        parser.error("new workloads require --new-ir and --new-ir-sha256")
    if args.job.startswith("old_") and (args.new_ir or args.new_ir_sha256):
        parser.error("old workloads use only frozen input IR")
    spec = INPUTS[args.job]
    cpu = args.cpu if args.cpu is not None else spec["cpu"]
    binary = verify(args.binary, args.binary_sha256)
    z3 = verify(args.z3, args.z3_sha256)
    ir = verify(args.new_ir, args.new_ir_sha256) if args.job.startswith("new_") else verify(ROOT / spec["ir"], spec["ir_sha256"])
    config = verify(ROOT / spec["config"], spec["config_sha256"])
    preload = verify(ROOT / INPUTS["seed_preload"], INPUTS["seed_preload_sha256"])
    linked = subprocess.check_output(["ldd", str(binary)], text=True)
    z3_lines = [line for line in linked.splitlines() if "libz3.so" in line]
    linked_z3 = Path(z3_lines[0].split("=>", 1)[1].strip().split(" (", 1)[0]).resolve() if len(z3_lines) == 1 and "=>" in z3_lines[0] else None
    if linked_z3 != z3:
        raise RuntimeError(f"new binary does not link requested Z3 {z3}:\n{linked}")
    output = HERE / "runs" / args.batch / args.job if args.batch else HERE / "runs" / args.job
    output.mkdir(parents=True, exist_ok=False)
    command = ["/usr/bin/time", "-f", TIME_FORMAT, "-o", "time.txt",
               "timeout", "--signal=TERM", "--kill-after=10s", "7200s",
               "taskset", "-c", str(cpu), str(binary),
               "-A", str(ir), "-C", str(config), "-T", "1",
               "--tastic", "qffp", "--smt-timeout", "7200s",
               "solve-state", "--clause=" + spec["clause"]]
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(preload)
    env["ISLA_ABLATION_SEED"] = "17"
    env["ISLA_ABLATION_SEED_LOG"] = str(output / "seed-intercept.log")
    provenance = {"job": args.job, "command": command, "cpu": cpu,
                  "seed": 17, "ir_sha256": sha(ir), "config_sha256": sha(config),
                  "binary_sha256": sha(binary), "z3_sha256": sha(z3),
                  "preload_sha256": sha(preload), "ldd": linked,
                  "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(output / "command.json", provenance)
    start = time.monotonic()
    with (output / "run.log").open("wb") as log:
        code = subprocess.run(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    elapsed = time.monotonic() - start
    timings = {}
    for line in (output / "time.txt").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            timings[key] = float(value) if key != "maxrss_kb" else int(value)
    json_files = sorted((output / "output").glob("*.json")) if (output / "output").is_dir() else []
    summary = json.loads(json_files[0].read_text()).get("summary") if len(json_files) == 1 else None
    seed_log = output / "seed-intercept.log"
    result = {**provenance, "exit_code": code, "outer_timeout": code == 124,
              "elapsed_s": round(elapsed, 3), **timings,
              "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "seed_intercepted": seed_log.exists() and "random_seed" in seed_log.read_text(),
              "seed_log_sha256": sha(seed_log) if seed_log.exists() else None,
              "run_log_sha256": sha(output / "run.log"),
              "output_json": str(json_files[0].relative_to(ROOT)) if len(json_files) == 1 else None,
              "output_sha256": sha(json_files[0]) if len(json_files) == 1 else None,
              "summary": summary}
    result["pass"] = code == 0 and result["seed_intercepted"] and summary is not None and summary.get("status") == "finished" and not any(summary.get(key, 0) for key in ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths", "omitted-cases", "model-query-timeouts", "pending-batches"))
    write(output / "result.json", result)
    print(json.dumps({key: result[key] for key in ("job", "exit_code", "elapsed_s", "user_s", "sys_s", "pass")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
