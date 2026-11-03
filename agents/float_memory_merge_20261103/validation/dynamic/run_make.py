#!/usr/bin/env python3
"""逐 Clause 调用合流候选真正的 run.mk 并按完整 summary 记账。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import shutil

HERE = Path(__file__).resolve().parent
PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
           "omitted-cases", "model-query-timeouts", "pending-batches", "sampled-paths",
           "assertion-filtered-paths", "encoding-filtered-paths")
TARGETS = {"FLEQ_S": "qffp", "LOAD_FP": "qfaufbv", "STORE_FP": "qfaufbv",
           "LOAD": "qfaufbv", "STORE": "qfaufbv", "AMO": "qfaufbv", "C_LD": "qfaufbv"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(row):
    path = Path(row["path"]).resolve(strict=True)
    if sha(path) != row["sha256"]:
        raise ValueError(f"冻结哈希不符：{path}")
    return path


def verify_source(row):
    manifest_path = checked(row)
    manifest = json.loads(manifest_path.read_text())
    root = Path(manifest["root"]).resolve(strict=True)
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if head != manifest["head"] or not manifest.get("files"):
        raise ValueError("源码清单不符")
    for name, expected in manifest["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or sha(root / relative) != expected:
            raise ValueError(f"源码字节漂移：{root}/{name}")
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--clause", choices=TARGETS, required=True)
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--domain", choices=("full", "directed"), required=True)
    parser.add_argument("--config", choices=("fd", "memory", "mixed-directed"), required=True)
    parser.add_argument("--word", help="仅定向域：4/8位十六进制机器字")
    parser.add_argument("--prestate", action="append", default=[], help="仅定向域：额外前态覆盖")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch) or args.cpu not in os.sched_getaffinity(0):
        parser.error("无效批次名或 CPU")
    if args.domain == "directed":
        if not args.word or not re.fullmatch(r"0x(?:[0-9a-fA-F]{4}|[0-9a-fA-F]{8})", args.word):
            parser.error("定向域须有精确4/8位机器字")
    elif args.word or args.prestate:
        parser.error("完整域不能注入机器字或前态")
    inputs = json.loads(args.inputs.read_text())
    if inputs.get("seed") != 17 or inputs.get("threads") != 1:
        raise ValueError("真实 Make 验收须 seed17/T1")
    isla = verify_source(inputs["isla_source_manifest"])
    model = verify_source(inputs["model_source_manifest"])
    if isla != Path(inputs["isla_tree"]).resolve() or model != Path(inputs["model_tree"]).resolve():
        raise ValueError("候选源码清单路径不符")
    binary = checked(inputs["binary"])
    ir = checked(inputs["ir"])
    config_entry = inputs["configs"][args.config]
    if not str(config_entry.get("domain", "")).startswith(args.domain):
        raise ValueError("配置标注域与命令域不符")
    config = checked(config_entry)
    if args.domain == "full":
        expected = {"fd": isla / "configs/riscv64_difftest_fd.toml",
                    "memory": isla / "configs/riscv64_difftest_mem.toml"}.get(args.config)
        if expected is None or config != expected.resolve():
            raise ValueError("完整域必须使用候选正式配置")
    elif args.config == "mixed-directed":
        if "directed_config_provenance" not in inputs:
            raise ValueError("混合定向配置缺少双母本 provenance")
        provenance_path = checked(inputs["directed_config_provenance"])
        provenance = json.loads(provenance_path.read_text())
        if (provenance.get("domain") != "directed"
                or provenance.get("output", {}).get("sha256") != sha(config)
                or provenance.get("fd", {}).get("sha256") != sha(isla / "configs/riscv64_difftest_fd.toml")
                or provenance.get("memory", {}).get("sha256") != sha(isla / "configs/riscv64_difftest_mem.toml")):
            raise ValueError("混合定向配置双母本不符")
    preload = checked(inputs["seed_preload"])
    makefile = isla / "scripts/run.mk"
    if not makefile.is_file():
        raise ValueError("真实 run.mk 缺失")
    out = HERE / "runs" / args.batch / "make" / args.clause
    if out.exists():
        raise ValueError(f"批次已存在：{out}")
    out.mkdir(parents=True)
    model_link = out.parent / "sail-riscv"
    if not model_link.exists():
        model_link.symlink_to(model, target_is_directory=True)
    elif model_link.resolve() != model:
        raise ValueError("workaround 模型符号链接指向错误")
    (out / "scripts").symlink_to(isla / "scripts", target_is_directory=True)
    (out / "target/release").mkdir(parents=True)
    wrapper = HERE / "make_isarch_wrapper.py"
    if args.domain == "directed":
        shutil.copy2(wrapper, out / "target/release/isarch")
        (out / "target/release/isarch").chmod(0o755)
    else:
        (out / "target/release/isarch").symlink_to(binary)
    params = ("IR_FILE=" + str(ir), "SOLVE_CONFIG=" + str(config), "THREADS=1",
              "OUTER_TIMEOUT=7200s", "SOLVE_TIMEOUT=7200s", "SMT_TIMEOUT=7200s", "ITRACE=0")
    core = ["make", "-C", str(out), "-f", str(makefile), "-o", "build-isarch",
            "solve-" + args.clause, *params]
    dry_run = subprocess.run([*core[:1], "-n", *core[1:]], capture_output=True, text=True)
    (out / "make-dry-run.log").write_text(dry_run.stdout + dry_run.stderr)
    if dry_run.returncode or not re.search(r"--tastic\s+" + TARGETS[args.clause] + r"\b", dry_run.stdout):
        raise ValueError("run.mk 的生产求解策略与预期不符")
    command = ["taskset", "-c", str(args.cpu), *core]
    seed_log = out / "seed-intercept.log"
    env = dict(os.environ, LD_PRELOAD=str(preload), ISLA_ABLATION_SEED="17",
               ISLA_ABLATION_SEED_LOG=str(seed_log))
    if args.domain == "directed":
        prestates = ["cur_privilege=Machine", "mstatus={bits=0x0000000a00006600}", *args.prestate]
        env.update(FM_REAL_ISARCH=str(binary), FM_REAL_ISARCH_SHA256=sha(binary),
                   FM_MACHINE_WORD=args.word, FM_PRESTATES_JSON=json.dumps(prestates),
                   FM_WRAPPER_RECEIPT=str(out / "wrapper-argv.json"))
    receipt = {"domain": args.domain, "clause": args.clause, "command": command,
               "dry_run_sha256": sha(out / "make-dry-run.log"),
               "actual_recipe_tactic": TARGETS[args.clause], "seed": 17, "threads": 1,
               "binary_sha256": sha(binary), "ir_sha256": sha(ir), "config_sha256": sha(config),
               "makefile_sha256": sha(makefile), "solve_process_sha256": sha(isla / "scripts/solve_process.py"),
               "preload_sha256": sha(preload), "input_sha256": sha(args.inputs),
               "isla_source_manifest_sha256": sha(checked(inputs["isla_source_manifest"])),
               "model_source_manifest_sha256": sha(checked(inputs["model_source_manifest"])),
               "runner_sha256": sha(Path(__file__)), "cpu": args.cpu}
    if args.domain == "directed":
        receipt.update(wrapper_sha256=sha(wrapper), machine_word=args.word,
                       inserted_prestates=prestates,
                       wrapper_role="original run.mk recipe and solve_process; wrapper only appends fixed instruction/prestate before solve-state")
    (out / "launch.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    if args.dry_run:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return
    start = time.monotonic()
    with (out / "make.log").open("w") as log:
        rc = subprocess.run(command, env=env, cwd=out, stdout=log, stderr=subprocess.STDOUT).returncode
    receipt["exit"] = rc
    receipt["seconds"] = round(time.monotonic() - start, 3)
    receipt["make_log_sha256"] = sha(out / "make.log")
    receipt["clause_log_sha256"] = sha(out / "output/log" / (args.clause + ".log")) if (out / "output/log" / (args.clause + ".log")).exists() else None
    receipt["seed_log_sha256"] = sha(seed_log) if seed_log.exists() else None
    if args.domain == "directed":
        argv_path = out / "wrapper-argv.json"
        receipt["wrapper_argv_sha256"] = sha(argv_path) if argv_path.exists() else None
        if argv_path.exists():
            argv_receipt = json.loads(argv_path.read_text())
            receipt["injected_argv_verified"] = (argv_receipt.get("inserted") ==
                ["--instruction-bits", args.word, *[part for state in prestates for part in ("--prestate", state)]]
                and argv_receipt.get("real_binary_sha256") == sha(binary))
        else:
            receipt["injected_argv_verified"] = False
    receipt["seed_fixed_17"] = (seed_log.exists() and bool(seed_log.read_text().strip()) and
        all(re.fullmatch(r"parameter=(?:seed|random_seed) original=\d+ fixed=17", row)
            for row in seed_log.read_text().splitlines()))
    files = list((out / "output").glob("*.json"))
    receipt["output_count"] = len(files)
    if len(files) == 1:
        data = json.loads(files[0].read_text())
        summary = data.get("summary", {})
        receipt["summary"] = summary
        receipt["gen"] = len(data.get("gen", []))
        receipt["output_sha256"] = sha(files[0])
        receipt["finished"] = (summary.get("status") == "finished" and
            summary.get("target-clause") == "z" + args.clause and
            all(type(summary.get(key)) is int and summary[key] == 0 for key in PARTIAL))
    else:
        receipt["finished"] = False
    receipt["pass"] = (rc == 0 and receipt["seed_fixed_17"] and receipt["finished"]
                       and receipt.get("gen", 0) > 0
                       and (args.domain == "full" or receipt["injected_argv_verified"]))
    verify_source(inputs["isla_source_manifest"])
    verify_source(inputs["model_source_manifest"])
    if sha(binary) != inputs["binary"]["sha256"] or sha(ir) != inputs["ir"]["sha256"] or sha(config) != inputs["configs"][args.config]["sha256"]:
        raise ValueError("运行期间 Make 输入字节漂移")
    (out / "result.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: receipt.get(key) for key in ("clause", "exit", "gen", "finished", "pass")}, ensure_ascii=False))
    raise SystemExit(0 if receipt["pass"] else 1)


if __name__ == "__main__":
    main()
