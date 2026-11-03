#!/usr/bin/env python3
"""Run the real make solve-FLEQ_S entry against the frozen new artifacts."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time

from run_clause import sha, verify, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPECIAL = ROOT / "agents/special_control_restore_20261102/validation/run.py"
CHECK_JSON = ROOT / "agents/float_review_completion_20261102/assembly/check_json.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--z3", type=Path, required=True)
    parser.add_argument("--z3-sha256", required=True)
    parser.add_argument("--ir", type=Path, required=True)
    parser.add_argument("--ir-sha256", required=True)
    parser.add_argument("--batch", help="Optional version label; writes <batch>/make-smoke")
    parser.add_argument("--cpu", type=int, default=102, choices=(100, 101, 102, 103))
    args = parser.parse_args()
    if args.batch and not re.fullmatch(r"[a-zA-Z0-9_-]+", args.batch):
        parser.error("--batch must contain only letters, digits, underscores, or hyphens")
    binary = verify(args.binary, args.binary_sha256)
    z3 = verify(args.z3, args.z3_sha256)
    ir = verify(args.ir, args.ir_sha256)
    linked = subprocess.check_output(["ldd", str(binary)], text=True)
    z3_lines = [line for line in linked.splitlines() if "libz3.so" in line]
    linked_z3 = Path(z3_lines[0].split("=>", 1)[1].strip().split(" (", 1)[0]).resolve() if len(z3_lines) == 1 and "=>" in z3_lines[0] else None
    if linked_z3 != z3:
        raise RuntimeError("Release binary did not link frozen Z3")
    output = HERE / args.batch / "make-smoke" if args.batch else HERE / "make-smoke"
    output.mkdir(parents=True, exist_ok=False)
    (output / "scripts").symlink_to(ROOT / "isla/scripts", target_is_directory=True)
    (output / "target").symlink_to(ROOT / "isla/target", target_is_directory=True)
    semantic_dir = HERE / args.batch / "semantic" if args.batch else HERE / "semantic"
    config = verify(semantic_dir / "fleq-S-qNaN/config.toml", sha(semantic_dir / "fleq-S-qNaN/config.toml"))
    preload = verify(ROOT / "agents/branch_ablation_official_z3_20261102/bin/seed_control.so", "8b26e6567f153ec28f35dfaddc15e9dfa3d53dcfa7fb1fe23d4922452bf429ae")
    command = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M", "-o", "time.txt",
               "taskset", "-c", str(args.cpu), "make", "-C", str(output), "-f", str(ROOT / "isla/scripts/run.mk"),
               "-o", "build-isarch", "solve-FLEQ_S", "IR_FILE=" + str(ir), "ISA_CONFIG=" + str(config),
               "THREADS=1", "SOLVE_TIMEOUT=", "SMT_TIMEOUT=7200s", "OUTER_TIMEOUT=7200s", "TASTIC=qffp", "ITRACE=0"]
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(preload)
    env["ISLA_ABLATION_SEED"] = "17"
    env["ISLA_ABLATION_SEED_LOG"] = str(output / "seed-intercept.log")
    provenance = {"command": command, "binary_sha256": sha(binary), "ir_sha256": sha(ir),
                  "config_sha256": sha(config), "z3_sha256": sha(z3), "preload_sha256": sha(preload),
                  "ldd": linked, "cpu": args.cpu,
                  "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(output / "command.json", provenance)
    start = time.monotonic()
    with (output / "make.log").open("wb") as log:
        code = subprocess.run(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    result = {**provenance, "exit_code": code, "elapsed_s": round(time.monotonic() - start, 3),
              "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "make_log_sha256": sha(output / "make.log")}
    for line in (output / "time.txt").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = int(value) if key == "maxrss_kb" else float(value)
    path = output / "output/rv64_zFLEQ_S.json"
    result["seed_intercepted"] = "random_seed" in (output / "seed-intercept.log").read_text() if (output / "seed-intercept.log").exists() else False
    if path.exists():
        data = json.loads(path.read_text())
        result.update(output_sha256=sha(path), summary=data["summary"], gen=len(data["gen"]))
        special = load(SPECIAL, "special_make_smoke")
        job = next(item for item in special.jobs() if item["name"] == "fleq-S-qNaN")
        result["semantic_pass"], result["semantic_detail"] = special.inspect(job, data)
        checker = load(CHECK_JSON, "check_make_json")
        if code == 0 and data["summary"].get("status") == "finished":
            result["representation"] = checker.check(path, output / "toolchains")
    result["pass"] = code == 0 and result.get("seed_intercepted", False) and result.get("summary", {}).get("status") == "finished" and result.get("semantic_pass", False) and result.get("representation", {}).get("all_pass", False)
    write(output / "result.json", result)
    print(json.dumps({k: result.get(k) for k in ("exit_code", "wall_s", "user_s", "sys_s", "gen", "pass")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
