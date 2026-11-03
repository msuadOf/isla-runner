#!/usr/bin/env python3
"""使用合流 Isla lib 和五份新 IR 重新验 300 组 flags 状态。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
KEYS = ("rv64-v128", "rv64-v256", "rv64-v512", "rv64-default", "rv32-default")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(row):
    path = Path(row["path"]).resolve(strict=True)
    if sha(path) != row["sha256"]:
        raise ValueError(f"输入哈希不符：{path}")
    return path


def verify_source(row):
    manifest_path = checked(row)
    manifest = json.loads(manifest_path.read_text())
    root = Path(manifest["root"]).resolve(strict=True)
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if head != manifest["head"] or not manifest.get("files"):
        raise ValueError("源码清单提交或文件列表不符")
    for name, expected in manifest["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or sha(root / relative) != expected:
            raise ValueError(f"源码字节漂移：{root}/{name}")
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch):
        parser.error("无效批次名")
    if args.cpu not in os.sched_getaffinity(0):
        parser.error("CPU 不在当前亲和性内")
    inputs = json.loads(args.inputs.read_text())
    if inputs.get("seed") != 17 or inputs.get("tactic") != "qffp" or inputs.get("threads") != 1:
        raise ValueError("清单须固定 seed17/T1/qffp")
    isla = Path(inputs["isla_tree"]).resolve(strict=True)
    commit = subprocess.check_output(["git", "-C", str(isla), "rev-parse", "HEAD"], text=True).strip()
    if commit != inputs["isla_commit"]:
        raise ValueError("合流 Isla HEAD 与清单不符")
    if verify_source(inputs["isla_source_manifest"]) != isla:
        raise ValueError("Isla 源码清单目录不符")
    model = Path(inputs["model_tree"]).resolve(strict=True)
    if verify_source(inputs["model_source_manifest"]) != model:
        raise ValueError("模型源码清单目录不符")
    z3 = checked(inputs["z3"])
    preload = checked(inputs["seed_preload"])
    binary_source = checked(inputs["binary"])
    configs = {"rv64": checked(inputs["configs"]["rv64"]),
               "rv32": checked(inputs["configs"]["rv32"])}
    irs = {key: checked(inputs["irs"][key]) for key in KEYS}
    destination = HERE / "runs" / args.batch / "flags-300"
    if destination.exists():
        raise ValueError(f"批次已存在：{destination}")
    manifest = HERE / "flags/Cargo.toml"
    source = HERE / "flags/main.rs"
    oracle = HERE / "flags/oracle.py"
    target = HERE / "flags/target"
    binary = target / "release/float-flags-state-probe"
    build = ["taskset", "-c", str(args.cpu), "cargo", "build", "--offline", "--locked",
             "--release", "--bin", "float-flags-state-probe", "--manifest-path", str(manifest)]
    commands = {key: ["taskset", "-c", str(args.cpu), str(binary), str(ir),
                      str(configs["rv32" if key == "rv32-default" else "rv64"])]
                for key, ir in irs.items()}
    receipt = {"scope": "direct accrue_fflags state probe; not whole Clause",
               "input_sha256": sha(args.inputs), "isla_commit": commit,
               "isla_tree": str(isla), "cpu": args.cpu, "seed": 17,
               "hashes": {"source": sha(source), "manifest": sha(manifest),
                          "lock": sha(HERE / "flags/Cargo.lock"), "oracle": sha(oracle),
                          "z3": sha(z3), "preload": sha(preload),
                          "isarch": sha(binary_source),
                          "model_source_manifest": sha(checked(inputs["model_source_manifest"])),
                          "isla_source_manifest": sha(checked(inputs["isla_source_manifest"])),
                          "rv64_config": sha(configs["rv64"]), "rv32_config": sha(configs["rv32"]),
                          "irs": {key: sha(path) for key, path in irs.items()}},
               "build": build, "commands": commands}
    if args.dry_run:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return
    destination.mkdir(parents=True)
    (destination / "launch.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    env = dict(os.environ, CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(target), CARGO_BUILD_JOBS="1",
               LIBRARY_PATH=str(z3.parent), LD_LIBRARY_PATH=str(z3.parent))
    with (destination / "build.log").open("w") as log:
        build_rc = subprocess.run(build, cwd=isla, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    receipt["build_exit"] = build_rc
    if build_rc:
        (destination / "result.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        raise SystemExit(build_rc)
    receipt["binary_sha256"] = sha(binary)
    verify_source(inputs["isla_source_manifest"])
    verify_source(inputs["model_source_manifest"])
    linked = subprocess.check_output(["ldd", str(binary)], text=True, env=env)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    if len(matches) != 1 or Path(matches[0]).resolve() != z3:
        raise ValueError("Rust helper 没有链接冻结的官方 Z3")
    receipt["ldd"] = linked
    sys.path.insert(0, str(HERE / "flags"))
    from oracle import check
    runs = {}
    for key, command in commands.items():
        seed_log = destination / f"{key}.seed.log"
        run_env = dict(env, LD_PRELOAD=str(preload), ISLA_ABLATION_SEED="17",
                       ISLA_ABLATION_SEED_LOG=str(seed_log))
        with (destination / f"{key}.log").open("w") as log:
            rc = subprocess.run(command, cwd=isla, env=run_env, stdout=log,
                                stderr=subprocess.STDOUT).returncode
        try:
            oracle_result = check(destination / f"{key}.log")
        except Exception as exc:
            oracle_result = {"pass": False, "error": repr(exc)}
        runs[key] = {"exit": rc, "oracle": oracle_result,
                     "log_sha256": sha(destination / f"{key}.log"),
                     "seed_log_sha256": sha(seed_log) if seed_log.exists() else None,
                     "seed_fixed_17": (seed_log.exists() and bool(seed_log.read_text().strip()) and
                         all(re.fullmatch(r"parameter=(?:seed|random_seed) original=\d+ fixed=17", row)
                             for row in seed_log.read_text().splitlines()))}
        receipt["runs"] = runs
        (destination / "result.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    verify_source(inputs["isla_source_manifest"])
    verify_source(inputs["model_source_manifest"])
    for key, path in irs.items():
        if sha(path) != inputs["irs"][key]["sha256"]:
            raise ValueError(f"300 运行期间 IR 漂移：{key}")
    receipt["pass"] = len(runs) == 5 and all(row["exit"] == 0 and row["oracle"].get("pass")
                                               and row["seed_fixed_17"] for row in runs.values())
    (destination / "result.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    raise SystemExit(0 if receipt["pass"] else 1)


if __name__ == "__main__":
    main()
