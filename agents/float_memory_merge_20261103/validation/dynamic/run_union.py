#!/usr/bin/env python3
"""在合流版本运行浮点、普通、原子及压缩访存的混合 JSON 探针。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib

HERE = Path(__file__).resolve().parent
PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
           "omitted-cases", "model-query-timeouts", "pending-batches", "sampled-paths",
           "assertion-filtered-paths", "encoding-filtered-paths")
BASE = "0x0000000080000000"
CASES = (
    ("fld", "LOAD_FP", "0x0000b187", ("x1=" + BASE,)),
    ("fsd", "STORE_FP", "0x0020b027", ("x1=" + BASE,)),
    ("flw", "LOAD_FP", "0x0000a187", ("x1=" + BASE,)),
    ("fsw", "STORE_FP", "0x0020a027", ("x1=" + BASE,)),
    ("ld", "LOAD", "0x0000b183", ("x1=" + BASE,)),
    ("sd", "STORE", "0x0020b023", ("x1=" + BASE, "x2=0x1122334455667788")),
    ("amo", "AMO", "0x0060b1af", ("x1=" + BASE, "x6=0x1122334455667788")),
    ("c_ld", "C_LD", "0x6000", ("x8=" + BASE,)),
    ("c_sd", "C_SD", "0xe000", ("x8=" + BASE,)),
)


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
            raise ValueError(f"源码字节变化：{root}/{name}")
    return root


def bits(value):
    if not isinstance(value, str):
        raise ValueError(f"非具体位串：{value!r}")
    match = re.fullmatch(r"(\d+)'h([0-9a-fA-F_]+)", value)
    if not match:
        raise ValueError(f"非具体位串：{value!r}")
    width = int(match[1])
    number = int(match[2].replace("_", ""), 16)
    if width < 1 or number >= 1 << width:
        raise ValueError(f"位串超宽：{value}")
    return width, number


def inspect(data, name, clause, machine_word):
    failures = []
    summary = data.get("summary", {})
    if summary.get("status") != "finished" or summary.get("target-clause") != "z" + clause:
        failures.append("summary status/target")
    if any(type(summary.get(key)) is not int or summary[key] != 0 for key in PARTIAL):
        failures.append("partial counters")
    generated = data.get("gen")
    if not isinstance(generated, list) or not generated:
        failures.append("empty gen")
        generated = []
    for index, entry in enumerate(generated):
        prefix = f"gen[{index}]"
        required = ("isa-state-complete", "isa-state-post", "memory-events", "pre-memory",
                    "post-memory", "instruction-representations", "ret_val")
        for key in required:
            if key not in entry:
                failures.append(f"{prefix}.{key} missing")
        pre = entry.get("isa-state-complete", {})
        post = entry.get("isa-state-post", {})
        for label, state in (("pre", pre), ("post", post)):
            for reg_name in ("fcsr", *(f"f{i}" for i in range(32)), *(f"x{i}" for i in range(1, 32))):
                try:
                    bits(state[reg_name])
                except (KeyError, ValueError, TypeError) as exc:
                    failures.append(f"{prefix}.{label}.{reg_name}: {exc}")
        if "Retire_Success" not in entry.get("ret_val", ""):
            failures.append(f"{prefix}.ret_val")
        try:
            width, value = bits(entry["test-ins-encdec"])
            if width not in (16, 32) or value != machine_word:
                failures.append(f"{prefix}.machine_word")
        except (KeyError, ValueError) as exc:
            failures.append(f"{prefix}.machine_word: {exc}")
        representations = entry.get("instruction-representations", {})
        encoding = representations.get("encoding", {}) if isinstance(representations, dict) else {}
        exact = representations.get("insn", {}) if isinstance(representations, dict) else {}
        if (not isinstance(representations, dict) or not representations.get("mnemonic")
                or encoding.get("status") != "complete" or exact.get("status") != "complete"
                or encoding.get("bit-length") not in (16, 32)
                or not encoding.get("bits") or not encoding.get("bytes-le") or not exact.get("text")):
            failures.append(f"{prefix}.representations")
        else:
            try:
                if int(encoding["bits"], 2) != machine_word or int(encoding["hex"], 16) != machine_word:
                    raise ValueError("encoding word")
                byte_count = encoding["bit-length"] // 8
                if encoding["bytes-le"].lower() != machine_word.to_bytes(byte_count, "little").hex():
                    raise ValueError("little endian bytes")
                if exact["text"] != f".insn {byte_count}, 0x{machine_word:0{byte_count * 2}x}":
                    raise ValueError(".insn")
            except (KeyError, ValueError, OverflowError) as exc:
                failures.append(f"{prefix}.encoding: {exc}")
        events = entry.get("memory-events", [])
        before = entry.get("pre-memory", [])
        after = entry.get("post-memory", [])
        if not isinstance(events, list) or not events:
            failures.append(f"{prefix}.memory-events empty")
        if not isinstance(before, list) or not isinstance(after, list):
            failures.append(f"{prefix}.memory snapshots")
        for j, event in enumerate(events):
            try:
                _, address = bits(event["address"])
                width = event["bytes"]
                if type(width) is not int or width not in (2, 4, 8):
                    raise ValueError("width")
                if address != int(BASE, 16):
                    raise ValueError("address")
                bits(event["value"] if event["kind"] == "read" else event["data"])
                expected_width = 4 if name in ("flw", "fsw") else 8
                if width != expected_width:
                    raise ValueError("instruction width")
                if name in ("fsd", "fsw") and event["kind"] == "write":
                    source = bits(pre["f2"])[1] & ((1 << (8 * width)) - 1)
                    if bits(event["data"])[1] != source:
                        raise ValueError("FP source/data")
                if name == "sd" and event["kind"] == "write" and bits(event["data"])[1] != bits(pre["x2"])[1]:
                    raise ValueError("GPR source/data")
                if name == "c_sd" and event["kind"] == "write" and bits(event["data"])[1] != bits(pre["x8"])[1]:
                    raise ValueError("compressed GPR source/data")
                if name in ("fld", "flw") and event["kind"] == "read":
                    loaded = bits(event["value"])[1]
                    boxed = loaded | (((1 << (64 - width * 8)) - 1) << (width * 8)) if width < 8 else loaded
                    if bits(post["f3"])[1] != boxed:
                        raise ValueError("FP load/post FPR")
                snapshot_before = [row for row in before if bits(row["address"])[1] == address and row["bytes"] == width]
                snapshot_after = [row for row in after if bits(row["address"])[1] == address and row["bytes"] == width]
                if not snapshot_before or not snapshot_after:
                    raise ValueError("memory snapshot missing")
                if event["kind"] == "read" and bits(snapshot_before[0]["value"])[1] != bits(event["value"])[1]:
                    raise ValueError("pre-memory/read")
                if event["kind"] == "write" and bits(snapshot_after[0]["value"])[1] != bits(event["data"])[1]:
                    raise ValueError("post-memory/write")
            except (KeyError, ValueError, TypeError) as exc:
                failures.append(f"{prefix}.event[{j}]: {exc}")
    return {"pass": not failures, "failures": failures, "gen": len(generated), "summary": summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--name", help="只运行指定案例，用例名精确匹配")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch) or args.cpu not in os.sched_getaffinity(0):
        parser.error("无效批次名或 CPU")
    if not 1 <= args.timeout <= 7200:
        parser.error("超时须在 1 至 7200 秒")
    inputs = json.loads(args.inputs.read_text())
    model = verify_source(inputs["model_source_manifest"])
    isla = verify_source(inputs["isla_source_manifest"])
    if model != Path(inputs["model_tree"]).resolve() or isla != Path(inputs["isla_tree"]).resolve():
        raise ValueError("源码清单与候选目录不符")
    binary, ir, config, z3, preload = [checked(inputs[key]) for key in
                                       ("binary", "ir", "config", "z3", "seed_preload")]
    config_provenance = json.loads(checked(inputs["directed_config_provenance"]).read_text())
    if (config_provenance.get("domain") != "directed"
            or config_provenance.get("output", {}).get("sha256") != sha(config)
            or config_provenance.get("fd", {}).get("sha256") != sha(isla / "configs/riscv64_difftest_fd.toml")
            or config_provenance.get("memory", {}).get("sha256") != sha(isla / "configs/riscv64_difftest_mem.toml")):
        raise ValueError("混合配置未绑定两个正式母本")
    if "initial_state" in tomllib.loads(config.read_text()):
        raise ValueError("基础配置已有初态")
    linked = subprocess.check_output(["ldd", str(binary)], text=True)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    if len(matches) != 1 or Path(matches[0]).resolve() != z3:
        raise ValueError("isarch 未链接冻结的官方 Z3")
    chosen = [row for row in CASES if args.name is None or args.name == row[0]]
    if not chosen:
        parser.error("未命中案例")
    out = HERE / "runs" / args.batch / "union"
    if out.exists():
        raise ValueError(f"输出批次已存在：{out}")
    receipt = {"scope": "mixed memory/FP directed; not whole Clause", "input_sha256": sha(args.inputs),
               "binary_sha256": sha(binary), "ir_sha256": sha(ir), "config_sha256": sha(config),
               "z3_sha256": sha(z3), "preload_sha256": sha(preload), "ldd": linked,
               "directed_config_provenance_sha256": sha(checked(inputs["directed_config_provenance"])),
               "model_source_manifest_sha256": sha(checked(inputs["model_source_manifest"])),
               "isla_source_manifest_sha256": sha(checked(inputs["isla_source_manifest"])),
               "runner_sha256": sha(Path(__file__)), "cpu": args.cpu,
               "timeout_seconds": args.timeout, "cases": [row[0] for row in chosen]}
    if args.dry_run:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return
    out.mkdir(parents=True)
    (out / "launch.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    all_pass = True
    for name, clause, word, prestates in chosen:
        dest = out / name
        dest.mkdir()
        case_config = dest / "config.toml"
        case_config.write_text(config.read_text() + "\n[initial_state]\n"
                               + 'f2 = "0x1122334455667788"\n')
        command = ["timeout", "--signal=TERM", "--kill-after=10s", f"{args.timeout}s",
                   "taskset", "-c", str(args.cpu), str(binary), "-A", str(ir), "-C", str(case_config),
                   "-T", "1", "--timeout", f"{args.timeout}s", "--smt-timeout", f"{args.timeout}s",
                   "--tastic", "qfaufbv", "--instruction-bits", word]
        for state in ("cur_privilege=Machine", "mstatus={bits=0x0000000a00006600}", *prestates):
            command.extend(("--prestate", state))
        command.extend(("solve-state", "--clause=" + clause))
        seed_log = dest / "seed-intercept.log"
        env = dict(os.environ, LD_PRELOAD=str(preload), ISLA_ABLATION_SEED="17",
                   ISLA_ABLATION_SEED_LOG=str(seed_log))
        start = time.monotonic()
        with (dest / "run.log").open("w") as log:
            code = subprocess.run(command, cwd=dest, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        files = list((dest / "output").glob("*.json"))
        result = {"name": name, "command": command, "exit": code,
                  "seconds": round(time.monotonic() - start, 3), "output_count": len(files),
                  "seed_log_sha256": sha(seed_log) if seed_log.exists() else None,
                  "seed_fixed_17": (seed_log.exists() and bool(seed_log.read_text().strip()) and
                    all(re.fullmatch(r"parameter=(?:seed|random_seed) original=\d+ fixed=17", row)
                        for row in seed_log.read_text().splitlines())),
                  "source": {"binary_sha256": sha(binary), "ir_sha256": sha(ir),
                             "config_sha256": sha(case_config)}, "pass": False}
        if len(files) == 1:
            data = json.loads(files[0].read_text())
            result["output_sha256"] = sha(files[0])
            result["inspection"] = inspect(data, name, clause, int(word, 16))
            result["pass"] = code == 0 and result["seed_fixed_17"] and result["inspection"]["pass"]
        (dest / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        all_pass &= result["pass"]
        print(name, "PASS" if result["pass"] else "FAIL", flush=True)
    verify_source(inputs["model_source_manifest"])
    verify_source(inputs["isla_source_manifest"])
    if any(sha(path) != inputs[key]["sha256"] for key, path in
           (("binary", binary), ("ir", ir), ("config", config))):
        raise ValueError("运行期间输入字节变化")
    raise SystemExit(0 if all_pass and len(chosen) == len(CASES) else 1)


if __name__ == "__main__":
    main()
