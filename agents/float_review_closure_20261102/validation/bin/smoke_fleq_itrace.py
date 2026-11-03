#!/usr/bin/env python3
"""用完整 Clause harness 的参数启动新二进制，检查 FLEQ_S 输出。"""

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
VALIDATION = HERE.parent
sys.path.insert(0, str(VALIDATION))
import run_clause


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs = json.loads((VALIDATION / "inputs.model-8ad5e8e.json").read_text())
    job = inputs["jobs"]["FLEQ_S"]
    ir = run_clause.checked(run_clause.ROOT, inputs["irs"][job["ir"]])
    config = run_clause.checked(run_clause.ROOT, inputs["configs"][job["config"]])
    seedlib = run_clause.checked(run_clause.ROOT, inputs["seed_preload"])
    binary = HERE / "isarch-42000be-interrupt-itrace"
    dest = HERE / "smoke-FLEQ_S-interrupt-itrace"
    dest.mkdir(parents=True, exist_ok=False)
    (dest / "output" / "trace").mkdir(parents=True)
    (dest / "output" / "smt-timeouts").mkdir(parents=True)
    command = [
        "/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
        "-o", "time.txt", "timeout", "--signal=TERM", "--kill-after=10s", "7200s",
        "taskset", "-c", "99", str(binary), "-A", str(ir), "-C", str(config),
        "-T", "1", "--tastic", "qffp", "--smt-timeout", "7200s",
        "--timeout-smt-output", "file", "--timeout-smt-dir", "output/smt-timeouts",
        "--verbose", "--debug=fmlgcsra", "--probe-all", "--trace-all",
        "--itrace=output/trace/itrace_FLEQ_S.txt", "solve-state", "--clause=FLEQ_S",
    ]
    (dest / "command.json").write_text(json.dumps(command, ensure_ascii=False, indent=2) + "\n")
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(seedlib)
    env["ISLA_ABLATION_SEED"] = "17"
    env["ISLA_ABLATION_SEED_LOG"] = str(dest / "seed-intercept.log")
    started = time.monotonic()
    with (dest / "run.log").open("wb") as log:
        code = subprocess.run(command, cwd=dest, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    outputs = sorted((dest / "output").glob("*.json"))
    summary, gen_count, kinds, schema = (
        run_clause.inspect_output(outputs[0], "FLEQ_S", ir, config)
        if len(outputs) == 1 else (None, None, None, False)
    )
    trace = dest / "output" / "trace" / "itrace_FLEQ_S.txt"
    seed = run_clause.seed_record(dest / "seed-intercept.log")
    result = {
        "source_commit": "42000be47596ec088623881d03c0eadc5cf0ba27",
        "binary_sha256": digest(binary),
        "ir_sha256": digest(ir),
        "config_sha256": digest(config),
        "seed_preload_sha256": digest(seedlib),
        "exit_code": code,
        "elapsed_s": round(time.monotonic() - started, 3),
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "json_count": len(outputs),
        "json_sha256": digest(outputs[0]) if len(outputs) == 1 else None,
        "summary": summary,
        "summary_schema_valid": schema,
        "gen_count": gen_count,
        "return_kinds": kinds,
        "itrace_bytes": trace.stat().st_size if trace.exists() else 0,
        "itrace_sha256": digest(trace) if trace.exists() else None,
        "seed_intercepted": seed["valid"],
        "seed_log_lines": seed["lines"],
    }
    result["pass"] = (
        code == 0 and len(outputs) == 1 and schema and summary["status"] == "finished"
        and all(summary[key] == 0 for key in run_clause.PARTIAL)
        and gen_count > 0 and result["itrace_bytes"] > 0 and seed["valid"]
    )
    (dest / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
