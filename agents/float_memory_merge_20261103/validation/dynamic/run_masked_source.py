#!/usr/bin/env python3
"""在合流正式 IR 上直接执行 init_masked_source 的四个 nat 边界。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent


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
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch) or args.cpu not in os.sched_getaffinity(0):
        parser.error("无效批次名或 CPU")
    inputs = json.loads(args.inputs.read_text())
    isla = verify_source(inputs["isla_source_manifest"])
    model = verify_source(inputs["model_source_manifest"])
    if isla != Path(inputs["isla_tree"]).resolve() or model != Path(inputs["model_tree"]).resolve():
        raise ValueError("源码清单路径不符")
    ir, config, z3, preload = [checked(inputs[key]) for key in ("ir", "config", "z3", "seed_preload")]
    target = HERE / "flags/target"
    binary = target / "release/masked-source-probe"
    build = ["taskset", "-c", str(args.cpu), "cargo", "build", "--offline", "--locked", "--release",
             "--bin", "masked-source-probe", "--manifest-path", str(HERE / "flags/Cargo.toml")]
    command = ["taskset", "-c", str(args.cpu), str(binary), str(ir), str(config)]
    out = HERE / "runs" / args.batch / "masked-source"
    if out.exists():
        raise ValueError(f"输出批次已存在：{out}")
    receipt = {"scope": "direct IR helper, not instruction/whole Clause",
               "input_sha256": sha(args.inputs), "model_source_manifest_sha256": sha(checked(inputs["model_source_manifest"])),
               "isla_source_manifest_sha256": sha(checked(inputs["isla_source_manifest"])),
               "ir_sha256": sha(ir), "config_sha256": sha(config), "z3_sha256": sha(z3),
               "preload_sha256": sha(preload), "rust_source_sha256": sha(HERE / "flags/masked_source.rs"),
               "manifest_sha256": sha(HERE / "flags/Cargo.toml"), "runner_sha256": sha(Path(__file__)),
               "build": build, "command": command, "cpu": args.cpu}
    if args.dry_run:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return
    out.mkdir(parents=True)
    env = dict(os.environ, CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(target), CARGO_BUILD_JOBS="1",
               LIBRARY_PATH=str(z3.parent), LD_LIBRARY_PATH=str(z3.parent))
    with (out / "build.log").open("w") as log:
        rc = subprocess.run(build, cwd=isla, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    receipt["build_exit"] = rc
    if rc:
        (out / "result.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        raise SystemExit(rc)
    verify_source(inputs["isla_source_manifest"])
    verify_source(inputs["model_source_manifest"])
    receipt["binary_sha256"] = sha(binary)
    linked = subprocess.check_output(["ldd", str(binary)], text=True, env=env)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    if len(matches) != 1 or Path(matches[0]).resolve() != z3:
        raise ValueError("helper 实际 Z3 不符")
    receipt["ldd"] = linked
    seed_log = out / "seed-intercept.log"
    run_env = dict(env, LD_PRELOAD=str(preload), ISLA_ABLATION_SEED="17",
                   ISLA_ABLATION_SEED_LOG=str(seed_log))
    with (out / "run.log").open("w") as log:
        receipt["exit"] = subprocess.run(command, cwd=isla, env=run_env, stdout=log,
                                         stderr=subprocess.STDOUT).returncode
    lines = (out / "run.log").read_text().splitlines()
    expected_labels = ("active", "equal", "greater", "large")
    receipt["rows"] = [line for line in lines if line.startswith("PASS ")]
    receipt["seed_log_sha256"] = sha(seed_log) if seed_log.exists() else None
    receipt["seed_fixed_17"] = (seed_log.exists() and bool(seed_log.read_text().strip()) and
        all(re.fullmatch(r"parameter=(?:seed|random_seed) original=\d+ fixed=17", row)
            for row in seed_log.read_text().splitlines()))
    receipt["pass"] = (receipt["exit"] == 0 and receipt["seed_fixed_17"] and
        len(receipt["rows"]) == 5 and
        all(receipt["rows"][index].startswith("PASS " + label + " ") for index, label in enumerate(expected_labels))
        and receipt["rows"][-1] == "PASS total=4")
    verify_source(inputs["isla_source_manifest"])
    verify_source(inputs["model_source_manifest"])
    if sha(ir) != inputs["ir"]["sha256"] or sha(config) != inputs["config"]["sha256"]:
        raise ValueError("运行期间 IR/配置漂移")
    (out / "result.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    raise SystemExit(0 if receipt["pass"] else 1)


if __name__ == "__main__":
    main()
