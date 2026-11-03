#!/usr/bin/env python3
"""Run the real solve-FLEQ_S Make recipe with frozen final artifacts."""

import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPRESENTATIONS = HERE.parent / "representations"
sys.path.insert(0, str(REPRESENTATIONS))
from common import ROOT, dump, finished_summary, fixed_seed, frozen_inputs, sha, toolchain_identity  # noqa: E402

SPECIAL = ROOT / "agents/special_control_restore_20261102/validation/run.py"
CHECK_JSON = REPRESENTATIONS / "check_exact_json.py"
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpu", type=int, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch):
        parser.error("invalid batch name")
    frozen = frozen_inputs(args.inputs)
    special = load(SPECIAL, "special_make_final")
    checker = load(CHECK_JSON, "check_make_final")
    job = next(item for item in special.jobs() if item["name"] == "fleq-S-qNaN")
    destination = HERE / args.batch / "smoke"
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "scripts").symlink_to(frozen["isla"] / "scripts", target_is_directory=True)
    (destination / "target" / "release").mkdir(parents=True)
    (destination / "target" / "release" / "isarch").symlink_to(frozen["binary"])
    config = destination / "config.toml"
    base_text = frozen["base_config"].read_text()
    if "[initial_state]" in base_text:
        raise ValueError("frozen base config already has initial_state")
    config.write_text(base_text + "\n[initial_state]\n" +
                      "".join(f"{key} = {json.dumps(value)}\n" for key, value in job["initial"].items()))
    makefile = frozen["isla"] / "scripts/run.mk"
    command = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
               "-o", "time.txt", "taskset", "-c", str(args.cpu), "make", "-C", str(destination),
               "-f", str(makefile), "-o", "build-isarch", "solve-FLEQ_S",
               "IR_FILE=" + str(frozen["ir"]), "ISA_CONFIG=" + str(config),
               "THREADS=1", "SOLVE_TIMEOUT=7200s", "SMT_TIMEOUT=7200s", "OUTER_TIMEOUT=7200s",
               "TASTIC=qffp", "ITRACE=0"]
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(frozen["preload"])
    env["ISLA_ABLATION_SEED"] = "17"
    env["ISLA_ABLATION_SEED_LOG"] = str(destination / "seed-intercept.log")
    record = {
        "domain": "directed-fixed-state-smoke",
        "command": command,
        "environment": {key: env[key] for key in ("LD_PRELOAD", "ISLA_ABLATION_SEED", "ISLA_ABLATION_SEED_LOG")},
        "model_commit": frozen["data"]["model_commit"], "isla_commit": frozen["data"]["isla_commit"],
        "inputs": str(frozen["inputs"]), "inputs_sha256": frozen["inputs_sha256"],
        "binary_sha256": sha(frozen["binary"]), "ir_sha256": sha(frozen["ir"]),
        "config_sha256": sha(config), "base_config_sha256": sha(frozen["base_config"]),
        "makefile_sha256": sha(makefile), "solve_process_sha256": sha(frozen["isla"] / "scripts/solve_process.py"),
        "z3_sha256": sha(frozen["z3"]), "preload_sha256": sha(frozen["preload"]),
        "special_harness_sha256": sha(SPECIAL), "checker_sha256": sha(CHECK_JSON),
        "generic_checker_sha256": sha(checker.GENERIC),
        "runner_sha256": sha(Path(__file__)), "common_sha256": sha(REPRESENTATIONS / "common.py"),
        "toolchains": toolchain_identity(checker),
        "target_isarch": str((destination / "target/release/isarch").resolve()),
        "ldd": frozen["ldd"], "cpu": args.cpu,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    dump(destination / "command.json", record)
    start = time.monotonic()
    with (destination / "make.log").open("wb") as log:
        code = subprocess.run(command, cwd=destination, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    record.update(exit_code=code, elapsed_s=round(time.monotonic() - start, 3),
                  finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  make_log_sha256=sha(destination / "make.log"))
    clause_log = destination / "output/log/FLEQ_S.log"
    record["recipe_ran"] = bool(re.search(r"\bsolve-FLEQ_S\b", (destination / "make.log").read_text())) and clause_log.exists()
    record["clause_log_sha256"] = sha(clause_log) if clause_log.exists() else None
    if (destination / "time.txt").exists():
        for line in (destination / "time.txt").read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                record[key] = int(value) if key == "maxrss_kb" else float(value)
    seed_log = destination / "seed-intercept.log"
    record["seed_fixed_17"] = fixed_seed(seed_log)
    record["seed_log_sha256"] = sha(seed_log) if seed_log.exists() else None
    output = destination / "output/rv64_zFLEQ_S.json"
    if output.exists():
        data = json.loads(output.read_text())
        record.update(output_sha256=sha(output), summary=data.get("summary"), gen=len(data.get("gen", [])))
        complete = code == 0 and finished_summary(data, "FLEQ_S")
        if complete:
            try:
                record["semantic_pass"], record["semantic_detail"] = special.inspect(job, data)
                record["representations"] = checker.check(output, destination / "toolchains")
            except Exception as exc:
                record["validation_error"] = f"{type(exc).__name__}: {exc}"
    record["pass"] = ("validation_error" not in record and code == 0 and record["recipe_ran"] and record["seed_fixed_17"]
                      and output.exists() and finished_summary(data, "FLEQ_S")
                      and record.get("semantic_pass", False) and record.get("representations", {}).get("all_pass", False))
    dump(destination / "result.json", record)
    print(json.dumps({key: record.get(key) for key in ("exit_code", "wall_s", "gen", "pass")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
