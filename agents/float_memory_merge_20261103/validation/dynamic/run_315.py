#!/usr/bin/env python3
"""在合流后的二进制和 IR 上重新运行 315 个 SoftFloat 定向用例。"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LEGACY = ROOT / "agents/float_review_closure_20261102/validation/exceptions/run_directed.py"
spec = importlib.util.spec_from_file_location("float_exception_probe", LEGACY)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
EXPECTED_HASH = "6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891"
PARTIAL = probe.PARTIAL
EXTRA_PARTIAL = ("assertion-filtered-paths", "encoding-filtered-paths")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(row):
    path = Path(row["path"]).resolve(strict=True)
    if sha(path) != row["sha256"]:
        raise ValueError(f"输入哈希不符：{path}")
    return path


def git_head(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def verify_source(row):
    manifest_path = checked(row)
    manifest = json.loads(manifest_path.read_text())
    root = Path(manifest["root"]).resolve(strict=True)
    if git_head(root) != manifest["head"] or not manifest.get("files"):
        raise ValueError(f"源码清单提交或文件列表不符：{root}")
    for name, expected in manifest["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or sha(root / relative) != expected:
            raise ValueError(f"源码字节漂移：{root}/{name}")
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpus", required=True)
    parser.add_argument("--name", help="只选定向子集；不计 315 全量验收")
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch):
        parser.error("批次名只能含字母、数字、下划线、连字符")
    if args.timeout <= 0 or args.timeout > 7200:
        parser.error("单项外限必须在 1 至 7200 秒")
    cpus = [int(x) for x in args.cpus.split(",")]
    if len(set(cpus)) != len(cpus) or not set(cpus) <= set(os.sched_getaffinity(0)):
        parser.error("CPU 不可用或重复")
    siblings = [Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list").read_text().strip() for cpu in cpus]
    if len(set(siblings)) != len(siblings):
        parser.error("CPU 共用 SMT 物理核")
    inputs = json.loads(args.inputs.read_text())
    if (inputs.get("domain") != "directed-315" or inputs.get("seed") != 17
            or inputs.get("tactic") != "qffp" or inputs.get("threads") != 1):
        raise ValueError("须为新合流版 directed-315/seed17/T1/qffp 清单")
    model = Path(inputs["model_tree"]).resolve(strict=True)
    isla = Path(inputs["isla_tree"]).resolve(strict=True)
    if git_head(model) != inputs["model_commit"] or git_head(isla) != inputs["isla_commit"]:
        raise ValueError("候选源码 HEAD 与清单不符")
    if verify_source(inputs["model_source_manifest"]) != model or verify_source(inputs["isla_source_manifest"]) != isla:
        raise ValueError("源码清单目录与候选不符")
    binary, ir, config, z3, preload = [checked(inputs[key]) for key in
                                       ("binary", "ir", "config", "z3", "seed_preload")]
    if "initial_state" in tomllib.loads(config.read_text()):
        raise ValueError("基础配置已经包含初态")
    linked = subprocess.check_output(["ldd", str(binary)], text=True)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    if len(matches) != 1 or Path(matches[0]).resolve() != z3:
        raise ValueError("isarch 未链接冻结的官方 Z3")
    expected_path = HERE / "expected-315.json"
    if sha(expected_path) != EXPECTED_HASH:
        raise ValueError("315 固定期望值发生变化")
    expected = json.loads(expected_path.read_text())
    oracle = ROOT / ".tmp/unified-backend-crosscheck/oracle-build/oracle"
    oracle_src = ROOT / "agents/float_support_review/oracle/oracle.cpp"
    archive = oracle.parent / "softfloat/libsoftfloat.a"
    if any(sha(path) != expected[key] for path, key in
           ((oracle, "oracle_binary_sha256"), (oracle_src, "oracle_source_sha256"),
            (archive, "softfloat_archive_sha256"))):
        raise ValueError("独立 SoftFloat oracle 来源与已审期望值不符")
    jobs = [probe.scalar_job(c) if c["family"] == "scalar" else probe.convert_job(c)
            for c in expected["cases"]]
    jobs += [probe.vector_job(c) for c in expected["vectors"]]
    jobs += [probe.bf16_job(c) for c in expected["bf16"]]
    if len(jobs) != 315:
        raise ValueError("315 分母不符")
    if args.name:
        jobs = [job for job in jobs if re.search(args.name, job["name"])]
        if not jobs:
            raise ValueError("选项未命中用例")
    destination = HERE / "runs" / args.batch
    if destination.exists():
        raise ValueError(f"批次已存在：{destination}")
    receipt = {"scope": "315 SoftFloat directed; not full Clause", "input_sha256": sha(args.inputs),
               "source": {"model_commit": git_head(model), "isla_commit": git_head(isla),
                          "model_tree": str(model), "isla_tree": str(isla)},
               "hashes": {"binary": sha(binary), "ir": sha(ir), "config": sha(config),
                          "z3": sha(z3), "preload": sha(preload), "expected": sha(expected_path),
                          "runner": sha(Path(__file__)), "legacy_probe": sha(LEGACY),
                          "model_source_manifest": sha(checked(inputs["model_source_manifest"])),
                          "isla_source_manifest": sha(checked(inputs["isla_source_manifest"])),
                          "oracle": sha(oracle), "softfloat": sha(archive)},
               "ldd": linked, "count": len(jobs), "seed": 17, "tactic": "qffp",
               "threads": 1, "cpus": cpus, "timeout_seconds": args.timeout,
               "names": [job["name"] for job in jobs]}
    if args.dry_run:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return
    destination.mkdir(parents=True)
    frozen = {"ir": destination / "base.ir", "binary": destination / "isarch",
              "base_config": destination / "base-config.toml", "seed_preload": destination / "seed_control.so"}
    for name, path in (("ir", ir), ("binary", binary), ("base_config", config), ("seed_preload", preload)):
        shutil.copy2(path, frozen[name])
        if sha(path) != sha(frozen[name]):
            raise ValueError(f"冻结复制不符：{name}")
    probe.write(destination / "launch.json", receipt)
    results = []
    def run(index, job):
        result = probe.execute(job, frozen, destination, cpus[index % len(cpus)], args.timeout)
        files = list((destination / "runs" / job["name"] / "output").glob("*.json"))
        if len(files) == 1:
            summary = json.loads(files[0].read_text()).get("summary", {})
            extra_ok = all(type(summary.get(key)) is int and summary[key] == 0 for key in EXTRA_PARTIAL)
            result["extra_partial_zero"] = extra_ok
            if not extra_ok:
                result["status"] = "FAIL"
                probe.write(destination / "runs" / job["name"] / "result.json", result)
        return result
    # 每个 CPU 只分配一条顺序 lane，避免同核同时跑两个求解器。
    def lane(index):
        return [run(index, job) for job in jobs[index::len(cpus)]]
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
        for future in as_completed([pool.submit(lane, index) for index in range(len(cpus))]):
            results.extend(future.result())
            probe.write(destination / "summary.json", {"count": len(jobs), "completed": len(results),
                         "pass": sum(row["status"] == "PASS" for row in results),
                         "results": sorted(results, key=lambda row: row["name"])})
    verify_source(inputs["model_source_manifest"])
    verify_source(inputs["isla_source_manifest"])
    if any(sha(path) != inputs[key]["sha256"] for key, path in
           (("binary", binary), ("ir", ir), ("config", config))):
        raise ValueError("315 运行期间输入字节变化")
    raise SystemExit(0 if len(results) == 315 and all(row["status"] == "PASS" for row in results) else 1)


if __name__ == "__main__":
    main()
