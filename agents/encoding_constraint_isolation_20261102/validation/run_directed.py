#!/usr/bin/env python3
"""New Release/new IR directed semantics and three representation checks."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPECIAL = ROOT / "agents/special_control_restore_20261102/validation/run.py"
CHECK_JSON = ROOT / "agents/float_review_completion_20261102/assembly/check_json.py"
ORACLE = ROOT / ".tmp/unified-backend-crosscheck/oracle-build/oracle"
CASE_CONFIGS = {
    "bf16-vl0": ("VFWMACCBF16_VF", "664ee76481ce5630514b88a21a5b5102e797053dbac6ffafd56d38ec353b6913"),
    "bf16-vl1": ("VFWMACCBF16_VF", "574cff99572f86721bf185f548c98f53d514685890ca7759b505ae6e408dfc25"),
    "c-addi4spn": ("C_ADDI4SPN", "f90b927cbf728e3f016e894bf633ccaeddcf4eea623923442e121611f9c85d06"),
}
PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths", "omitted-cases", "model-query-timeouts", "pending-batches")


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


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def timed_run(name, binary, ir, config, clause, cpu, output):
    output.mkdir(parents=True, exist_ok=False)
    command = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M", "-o", "time.txt",
               "timeout", "--signal=TERM", "--kill-after=10s", "7200s", "taskset", "-c", str(cpu),
               str(binary), "-A", str(ir), "-C", str(config), "-T", "1", "--tastic", "qffp",
               "--smt-timeout", "7200s", "solve-state", "--clause=" + clause]
    record = {"name": name, "command": command, "binary_sha256": sha(binary), "ir_sha256": sha(ir),
              "config_sha256": sha(config), "cpu": cpu,
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(output / "command.json", record)
    start = time.monotonic()
    with (output / "run.log").open("wb") as log:
        code = subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT).returncode
    record.update(exit_code=code, elapsed_s=round(time.monotonic() - start, 3),
                  finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  run_log_sha256=sha(output / "run.log"))
    for line in (output / "time.txt").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            record[key] = int(value) if key == "maxrss_kb" else float(value)
    json_files = sorted((output / "output").glob("*.json")) if (output / "output").exists() else []
    if len(json_files) == 1:
        record["output_sha256"] = sha(json_files[0])
        record["summary"] = json.loads(json_files[0].read_text()).get("summary")
    record["pass_complete"] = code == 0 and len(json_files) == 1 and record["summary"].get("status") == "finished" and not any(record["summary"].get(k, 0) for k in PARTIAL)
    write(output / "result.json", record)
    return record, json_files[0] if len(json_files) == 1 else None


def bits(value):
    match = re.fullmatch(r"(\d+)'([hbd])([0-9a-fA-F_]+)", value)
    if match:
        return int(match[3].replace("_", ""), {"h": 16, "b": 2, "d": 10}[match[2]])
    return int(value, 16)


def check_executeas(data):
    checks = []
    for item in data["gen"]:
        enc = bits(item["test-ins-encdec"])
        assert enc & 0xe003 == 0, item["test-ins-encdec"]
        rd = 8 + ((enc >> 2) & 7)
        imm = (((enc >> 11) & 3) << 4) | (((enc >> 7) & 15) << 6) | (((enc >> 6) & 1) << 2) | (((enc >> 5) & 1) << 3)
        if imm == 0:
            continue
        pre = bits(item["isa-state-complete"]["x2"])
        post = bits(item["isa-state-post"][f"x{rd}"])
        expected = (pre + imm) & ((1 << 64) - 1)
        checks.append({"encoding": hex(enc), "x2": pre, "rd": rd, "immediate": imm,
                       "expected": expected, "actual": post, "return": item["ret_val"]})
        assert "ExecuteAs" not in item["ret_val"] and post == expected, checks[-1]
    assert checks, "no legal C_ADDI4SPN witness"
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("semantic", "representations"))
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--z3", type=Path, required=True)
    parser.add_argument("--z3-sha256", required=True)
    parser.add_argument("--ir", type=Path, required=True)
    parser.add_argument("--ir-sha256", required=True)
    parser.add_argument("--cpu", type=int, default=103, choices=(100, 101, 102, 103))
    parser.add_argument("--batch", help="Optional version label; writes <batch>/<mode>")
    args = parser.parse_args()
    if args.batch and not re.fullmatch(r"[a-zA-Z0-9_-]+", args.batch):
        parser.error("--batch must contain only letters, digits, underscores, or hyphens")
    binary = verify(args.binary, args.binary_sha256)
    z3 = verify(args.z3, args.z3_sha256)
    linked = subprocess.check_output(["ldd", str(binary)], text=True)
    z3_lines = [line for line in linked.splitlines() if "libz3.so" in line]
    linked_z3 = Path(z3_lines[0].split("=>", 1)[1].strip().split(" (", 1)[0]).resolve() if len(z3_lines) == 1 and "=>" in z3_lines[0] else None
    if linked_z3 != z3:
        raise RuntimeError(f"new binary does not link requested Z3 {z3}:\n{linked}")
    ir = verify(args.ir, args.ir_sha256)
    output = HERE / args.batch / args.mode if args.batch else HERE / args.mode
    output.mkdir(parents=True, exist_ok=False)
    provenance = {"mode": args.mode, "binary_sha256": sha(binary), "z3_sha256": sha(z3), "ldd": linked,
                  "ir_sha256": sha(ir),
                  "special_harness_sha256": sha(SPECIAL), "check_json_sha256": sha(CHECK_JSON),
                  "base_config_sha256": sha(ROOT / "isla/configs/riscv64_difftest_fd.toml"),
                  "oracle_sha256": sha(ORACLE),
                  "cpu": args.cpu}
    write(output / "provenance.json", provenance)
    results = []
    if args.mode == "semantic":
        special = load(SPECIAL, "special_directed")
        special.ORACLE = verify(ORACLE, sha(ORACLE))
        source = ir.read_text()
        for job in special.jobs():
            verify(binary, args.binary_sha256)
            verify(ir, args.ir_sha256)
            name = job["name"]
            dest = output / name
            config = dest / "config.toml"
            dest.mkdir(parents=True, exist_ok=False)
            config.write_text(special.BASE.read_text() + "\n[initial_state]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in job["initial"].items()))
            job_ir = ir
            if job["fields"] is not None:
                job_ir = dest / "constrained.ir"
                job_ir.write_text(special.wrapper(source, job))
            run, path = timed_run(name, binary, job_ir, config, job["clause"], args.cpu, dest / "run")
            if path:
                passed, detail = special.inspect(job, json.loads(path.read_text()))
                run.update(semantic_pass=passed, semantic_detail=detail)
            else:
                run["semantic_pass"] = False
            run["pass"] = run["pass_complete"] and run["semantic_pass"]
            write(dest / "result.json", run)
            results.append({"name": name, "pass": run["pass"], "exit_code": run["exit_code"],
                            "wall_s": run.get("wall_s"), "user_s": run.get("user_s"), "sys_s": run.get("sys_s")})
            write(output / "summary.json", {"provenance": provenance, "results": results, "complete": False})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    else:
        checker = load(CHECK_JSON, "check_json")
        for name, (clause, expected_sha) in CASE_CONFIGS.items():
            verify(binary, args.binary_sha256)
            verify(ir, args.ir_sha256)
            config = verify(ROOT / "agents/independent_topic_review_20261030/float" / name / "config.toml", expected_sha)
            dest = output / name
            run, path = timed_run(name, binary, ir, config, clause, args.cpu, dest / "run")
            if path and run["pass_complete"]:
                representation = checker.check(path, dest / "toolchains")
                run["representation"] = representation
                if name == "c-addi4spn":
                    run["executeas"] = check_executeas(json.loads(path.read_text()))
            run["pass"] = run["pass_complete"] and run.get("representation", {}).get("all_pass", False) and (name != "c-addi4spn" or bool(run.get("executeas")))
            write(dest / "result.json", run)
            results.append({"name": name, "pass": run["pass"], "exit_code": run["exit_code"],
                            "wall_s": run.get("wall_s"), "user_s": run.get("user_s"), "sys_s": run.get("sys_s"),
                            "representations": run.get("representation", {}).get("gen")})
            write(output / "summary.json", {"provenance": provenance, "results": results, "complete": False})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    write(output / "summary.json", {"provenance": provenance, "results": results,
                                    "complete": True, "all_pass": all(item["pass"] for item in results)})


if __name__ == "__main__":
    main()
