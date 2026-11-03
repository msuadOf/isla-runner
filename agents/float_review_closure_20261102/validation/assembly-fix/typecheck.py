#!/usr/bin/env python3
"""Strict ordinary and SYMBOLIC typechecks with independent memo files."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MODEL = ROOT / ".worktree/runner-float/sail-riscv"
SAIL = ROOT / "isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src/sail"
CONFIG = ROOT / "isla/ir/provenance/rv64d.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_files():
    names = [item.decode().removeprefix("model/") for item in subprocess.check_output(
        ["git", "-C", str(MODEL), "ls-files", "-z", "model"]).split(b"\0") if item]
    return {name: sha(MODEL / "model" / name) for name in names}


def run_one(mode, cpu, output):
    command = [str(SAIL)]
    if mode == "symbolic":
        command += ["-D", "SYMBOLIC"]
    command += ["--strict-var", "--strict-bitvector", "--strict-exponentials",
                "--require-version", "0.20.1", "--memo-z3-path", str(output / f"{mode}-memo"),
                "--all-modules", "--just-check", "--config", str(CONFIG), "riscv.sail_project"]
    started = time.monotonic()
    with (output / f"{mode}.log").open("w") as log:
        code = subprocess.run(["taskset", "-c", str(cpu), *command], cwd=MODEL / "model",
                              stdout=log, stderr=subprocess.STDOUT).returncode
    return {"mode": mode, "cpu": cpu, "exit_code": code,
            "seconds": round(time.monotonic() - started, 3),
            "log_sha256": sha(output / f"{mode}.log"),
            "memo_sha256": sha(output / f"{mode}-memo") if (output / f"{mode}-memo").exists() else None,
            "command": ["taskset", "-c", str(cpu), *command]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = model_files()
    source = {"head": subprocess.check_output(["git", "-C", str(MODEL), "rev-parse", "HEAD"], text=True).strip(),
              "model_files": before, "sail_sha256": sha(SAIL), "config_sha256": sha(CONFIG),
              "sail_version": subprocess.check_output([str(SAIL), "--version"], text=True).strip(),
              "memo_source": "fresh separate files; no copied cache"}
    (output / "source.json").write_text(json.dumps(source, indent=2) + "\n")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda item: run_one(*item, output), (("ordinary", 7), ("symbolic", 9))))
    record = {"source_manifest_sha256": sha(output / "source.json"), "results": results,
              "source_unchanged": before == model_files()}
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print([(item["mode"], item["exit_code"], item["seconds"]) for item in results], record["source_unchanged"])
    if not record["source_unchanged"] or any(item["exit_code"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
