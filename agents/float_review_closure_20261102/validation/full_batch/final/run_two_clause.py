#!/usr/bin/env python3
"""以冻结清单运行单个完整 Clause；定向固定值须使用另一类批次。"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import tomllib

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parents[2]
PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
           "omitted-cases", "model-query-timeouts", "pending-batches", "sampled-paths")
OFFICIAL_FD_CONFIG_SHA256 = "20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(root, item):
    path = (root / item["path"]).resolve(strict=True)
    actual = digest(path)
    if actual != item["sha256"]:
        raise ValueError(f"哈希不符 {path}: {actual} != {item['sha256']}")
    return path


def git_head(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def verify_tree(tree, expected_commit):
    base = (ROOT / tree["path"]).resolve(strict=True)
    manifest_path = checked(ROOT, tree["manifest"])
    manifest = json.loads(manifest_path.read_text())
    if git_head(base) != expected_commit or manifest.get("commit") != expected_commit:
        raise ValueError(f"源码提交不符：{base}")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"源码清单为空：{manifest_path}")
    for name, expected in files.items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError(f"清单路径越界：{name}")
        actual = digest(base / name)
        if actual != expected:
            raise ValueError(f"源码文件漂移：{name}")
    return manifest_path


def seed_record(path):
    if not path.exists():
        return {"valid": False, "lines": []}
    lines = path.read_text().splitlines()
    parsed = [re.fullmatch(r"parameter=(seed|random_seed) original=\d+ fixed=(\d+)", line)
              for line in lines]
    valid = (bool(lines) and all(parsed) and
             any(match.group(1) == "random_seed" for match in parsed) and
             all(int(match.group(2)) == 17 for match in parsed))
    return {"valid": valid, "lines": lines}


def inspect_output(path, clause, ir, config):
    data = json.loads(path.read_text())
    summary = data.get("summary")
    if not isinstance(summary, dict) or not isinstance(data.get("gen"), list):
        return None, None, None, False
    required = (*PARTIAL, "status", "target-clause")
    schema = (all(key in summary for key in required) and
              all(type(summary[key]) is int and summary[key] >= 0 for key in PARTIAL) and
              isinstance(summary["status"], str) and
              summary["target-clause"] == "z" + clause)
    provenance = data.get("provenance")
    inputs = provenance.get("inputs") if isinstance(provenance, dict) else None
    if not isinstance(inputs, dict):
        schema = False
    else:
        for flag, expected in (("-A", ir), ("-C", config)):
            item = inputs.get(flag)
            if (not isinstance(item, dict) or item.get("path") != str(expected)
                    or item.get("sha256") != digest(expected)):
                schema = False
    kinds = {"Retire_Success": 0, "Illegal_Instruction": 0, "other": 0}
    for item in data["gen"]:
        ret = item.get("ret_val") if isinstance(item, dict) else None
        if not isinstance(ret, str):
            schema = False
            kinds["other"] += 1
        elif ret.startswith("Retire_Success"):
            kinds["Retire_Success"] += 1
        elif ret.startswith("Illegal_Instruction"):
            kinds["Illegal_Instruction"] += 1
        else:
            kinds["other"] += 1
    return summary, len(data["gen"]), kinds, schema


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, help="新批次名称，不复用旧输出")
    parser.add_argument("--job", required=True, help="jobs.json 中的 Clause 名称")
    parser.add_argument("--inputs", type=Path, required=True, help="冻结输入 JSON")
    parser.add_argument("--cpu", type=int, required=True, help="独占物理核的一个逻辑 CPU")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch):
        parser.error("batch 只能含字母、数字、下划线和连字符")
    data = json.loads(args.inputs.read_text())
    if data.get("domain") != "full":
        raise ValueError("本入口仅接受完整域；固定值定向批次须单列")
    if data.get("seed") != 17 or data.get("tactic") != "qffp" or data.get("threads") != 1:
        raise ValueError("正式批次必须 seed17/T1/qffp")
    if data.get("model_commit") is None or data.get("isla_commit") is None:
        raise ValueError("缺少最终源码 commit")
    affected_path = checked(ROOT, data["affected_manifest"])
    closure = json.loads(affected_path.read_text())
    affected = set(closure["affected_clauses"])
    if (closure.get("source_mode") != "committed_component_heads" or
            closure.get("model_commit") != data["model_commit"] or
            closure.get("isla_commit") != data["isla_commit"] or
            closure.get("model_dirty") is not False or closure.get("isla_dirty") is not False or
            closure.get("affected_count") != len(affected)):
        raise ValueError("静态调用闭包版本、clean状态或分母不符")
    jobs = data["jobs"]
    if len(affected) != 64 or set(jobs) != {"FLEQ_S", "C_ADDI4SPN"}:
        raise ValueError("最终两入口仅允许FLEQ_S/C_ADDI4SPN，静态受影响分母须64")
    if "FLEQ_S" not in affected or "C_ADDI4SPN" in affected:
        raise ValueError("最终两入口与64条静态影响清单不符")
    if any(row.get("scope") != ("affected" if clause in affected else "compatibility")
           for clause, row in jobs.items()):
        raise ValueError("Clause 受影响/兼容标签与静态闭包不符")
    for key, worktree in (("model_commit", "model_tree"), ("isla_commit", "isla_tree")):
        verify_tree(data[worktree], data[key])
    binary = checked(ROOT, data["binary"])
    binary_manifest_path = checked(ROOT, data["binary_manifest"])
    binary_manifest = json.loads(binary_manifest_path.read_text())
    watchdog_path = checked(ROOT, data["watchdog_evidence"])
    watchdog = json.loads(watchdog_path.read_text())
    if (binary_manifest.get("source_commit") != data["isla_commit"] or
            binary_manifest.get("binary_sha256") != digest(binary) or
            binary_manifest.get("source_clean") is not True or
            "smt-thread-interrupt" not in binary_manifest.get("features", []) or
            "itrace" not in binary_manifest.get("features", []) or
            "smt-thread-interrupt" not in binary_manifest.get("isla_lib_features", []) or
            "tracetool" not in binary_manifest.get("isla_lib_features", [])):
        raise ValueError("正式程序缺少同源 smt-thread-interrupt/itrace 构建证据")
    if (watchdog.get("formal_binary_sha256") != digest(binary) or
            watchdog.get("formal_imports_Z3_interrupt") is not True or
            watchdog.get("Z3_interrupt_call_count", 0) < 1 or
            watchdog.get("exit") != 0 or "watchdog_timeout=true" not in watchdog.get("stdout", "")):
        raise ValueError("正式程序缺少已核 watchdog 中断证据")
    z3 = checked(ROOT, data["z3"])
    seedlib = checked(ROOT, data["seed_preload"])
    job = jobs[args.job]
    ir = checked(ROOT, data["irs"][job["ir"]])
    config = checked(ROOT, data["configs"][job["config"]])
    official_config = ROOT / "isla/configs/riscv64_difftest_fd.toml"
    if digest(config) != OFFICIAL_FD_CONFIG_SHA256 or digest(official_config) != OFFICIAL_FD_CONFIG_SHA256:
        raise ValueError("完整域必须使用正式 FD 母本配置的精确字节；禁止附加缩域键")
    parsed = tomllib.loads(config.read_text())
    if "initial_state" in parsed:
        raise ValueError("完整域配置含 initial_state 固定值")
    if b"zvalidation_original_execute" in ir.read_bytes():
        raise ValueError("完整域 IR 含定向 wrapper")
    linked = subprocess.check_output(["ldd", str(binary)], text=True)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    if len(matches) != 1 or Path(matches[0]).resolve() != z3.resolve():
        raise ValueError("Release binary 未链接指定官方 Z3")
    dest = HERE / "runs" / args.batch / args.job
    command = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
               "-o", "time.txt", "timeout", "--signal=TERM", "--kill-after=10s", "7200s",
               "taskset", "-c", str(args.cpu), str(binary), "-A", str(ir), "-C", str(config),
               "-T", "1", "--tastic", "qffp", "--smt-timeout", "7200s",
               "--timeout-smt-output", "file", "--timeout-smt-dir", "output/smt-timeouts",
               "--verbose", "--debug=fmlgcsra", "--probe-all", "--trace-all",
               "--itrace=output/trace/itrace_" + args.job + ".txt",
               "solve-state", "--clause=" + args.job]
    record = {"batch": args.batch, "job": args.job, "scope": job["scope"],
              "affected_manifest_sha256": digest(affected_path), "domain": "full", "cpu": args.cpu,
              "command": command, "input_manifest": str(args.inputs.resolve()),
              "input_manifest_sha256": digest(args.inputs), "model_commit": data["model_commit"],
              "isla_commit": data["isla_commit"], "ir_sha256": digest(ir),
              "config_sha256": digest(config), "binary_sha256": digest(binary),
              "binary_manifest_sha256": digest(binary_manifest_path),
              "watchdog_evidence_sha256": digest(watchdog_path),
              "z3_sha256": digest(z3), "seed_preload_sha256": digest(seedlib),
              "seed": 17, "ldd": linked}
    if args.dry_run:
        print(json.dumps(record, indent=2, ensure_ascii=False))
        return
    dest.mkdir(parents=True, exist_ok=False)
    (dest / "output" / "trace").mkdir(parents=True)
    (dest / "output" / "smt-timeouts").mkdir(parents=True)
    (dest / "command.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(seedlib)
    env["ISLA_ABLATION_SEED"] = "17"
    env["ISLA_ABLATION_SEED_LOG"] = str(dest / "seed-intercept.log")
    start = time.monotonic()
    with (dest / "run.log").open("wb") as log:
        code = subprocess.run(command, cwd=dest, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    outputs = sorted((dest / "output").glob("*.json"))
    summary, gen_count, kinds, schema = (inspect_output(outputs[0], args.job, ir, config)
                                          if len(outputs) == 1 else (None, None, None, False))
    seed_log = dest / "seed-intercept.log"
    seed = seed_record(seed_log)
    itrace = dest / "output" / "trace" / ("itrace_" + args.job + ".txt")
    itrace_size = itrace.stat().st_size if itrace.exists() else 0
    result = {**record, "exit_code": code, "elapsed_s": round(time.monotonic() - start, 3),
              "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "summary": summary, "summary_schema_valid": schema, "json_count": len(outputs),
              "gen_count": gen_count, "return_kinds": kinds,
              "output_sha256": digest(outputs[0]) if len(outputs) == 1 else None,
              "itrace_bytes": itrace_size,
              "itrace_sha256": digest(itrace) if itrace_size else None,
              "run_log_sha256": digest(dest / "run.log"),
              "seed_intercepted": seed["valid"], "seed_log_lines": seed["lines"],
              "seed_log_sha256": digest(seed_log) if seed_log.exists() else None}
    result["pass"] = (code == 0 and itrace_size > 0 and result["seed_intercepted"] and schema and
                      gen_count is not None and gen_count > 0 and summary is not None
                      and summary.get("status") == "finished"
                      and all(summary.get(key, 0) == 0 for key in PARTIAL))
    (dest / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: result[key] for key in ("job", "exit_code", "elapsed_s", "pass")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
