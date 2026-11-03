#!/usr/bin/env python3
"""重跑合流 nat 适配的 VFMERGE 与 VLSEGTYPE 三类 vstart。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import tomllib

HERE = Path(__file__).resolve().parent
PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
           "omitted-cases", "model-query-timeouts", "pending-batches", "sampled-paths",
           "assertion-filtered-paths", "encoding-filtered-paths")
CASES = (("vfmerge", "VFMERGE", 0x5C005FD7),
         ("vector-load", "VLSEGTYPE", 0x02008087))
STARTS = (("active", 0), ("equal", 1), ("greater", 2), ("large", (1 << 64) - 1))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(row):
    path = Path(row["path"]).resolve(strict=True)
    if sha(path) != row["sha256"]:
        raise ValueError(f"输入字节漂移：{path}")
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


def number(value):
    match = re.fullmatch(r"\d+'h([0-9a-fA-F_]+)", value)
    if not match:
        raise ValueError(f"非具体位串：{value}")
    return int(match[1].replace("_", ""), 16)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch) or args.cpu not in os.sched_getaffinity(0):
        parser.error("批次名或 CPU 无效")
    if not 1 <= args.timeout <= 7200:
        parser.error("超时不在 1..7200 秒")
    inputs = json.loads(args.inputs.read_text())
    verify_source(inputs["model_source_manifest"])
    verify_source(inputs["isla_source_manifest"])
    binary, ir, config, z3, preload = [checked(inputs[key]) for key in
                                       ("binary", "ir", "config", "z3", "seed_preload")]
    if "initial_state" in tomllib.loads(config.read_text()):
        raise ValueError("基础配置已含初态")
    linked = subprocess.check_output(["ldd", str(binary)], text=True)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    if len(matches) != 1 or Path(matches[0]).resolve() != z3:
        raise ValueError("实际 Z3 不符")
    out = HERE / "runs" / args.batch / "vstart"
    if out.exists():
        raise ValueError(f"批次已存在：{out}")
    receipt = {"scope": "nat adapter directed, not whole Clause", "input_sha256": sha(args.inputs),
               "binary_sha256": sha(binary), "ir_sha256": sha(ir), "config_sha256": sha(config),
               "z3_sha256": sha(z3), "preload_sha256": sha(preload), "ldd": linked,
               "runner_sha256": sha(Path(__file__)), "cpu": args.cpu,
               "cases": len(CASES) * len(STARTS), "timeout_seconds": args.timeout}
    if args.dry_run:
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return
    out.mkdir(parents=True)
    (out / "launch.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    results = []
    for family, clause, word in CASES:
        for label, start in STARTS:
            name = family + "-" + label
            dest = out / name
            dest.mkdir()
            state = {"mstatus": "0x0000000a00006600", "fcsr": "0x0",
                     "vtype": "0x10" if family == "vfmerge" else "0x0", "vl": "0x1",
                     "vstart": hex(start), "vr0": "0x1", "vr1": "0x12345678",
                     "vr31": "0x12345678", "f0": "0xffffffff3f800000",
                     "x1": "0x80000000"}
            case_config = dest / "config.toml"
            case_config.write_text(config.read_text() + "\n[initial_state]\n" +
                                   "".join(f"{key} = {json.dumps(value)}\n" for key, value in state.items()))
            command = ["timeout", "--signal=TERM", "--kill-after=10s", f"{args.timeout}s",
                       "taskset", "-c", str(args.cpu), str(binary), "-A", str(ir), "-C", str(case_config),
                       "-T", "1", "--timeout", f"{args.timeout}s", "--smt-timeout", f"{args.timeout}s",
                       "--tastic", "qffp" if family == "vfmerge" else "qfaufbv",
                       "--instruction-bits", f"0x{word:08x}", "--prestate", "cur_privilege=Machine",
                       "--prestate", "mstatus={bits=0x0000000a00006600}",
                       "--prestate", "vtype={bits=0x0000000000000010}" if family == "vfmerge" else "vtype={bits=0x0000000000000000}",
                       "--prestate", "vl=0x0000000000000001", "--prestate", f"vstart=0x{start:016x}",
                       "--prestate", "fcsr={bits=0x00000000}",
                       "--prestate", "x1=0x0000000080000000",
                       "solve-state", "--clause=" + clause]
            seed_log = dest / "seed-intercept.log"
            env = dict(os.environ, LD_PRELOAD=str(preload), ISLA_ABLATION_SEED="17",
                       ISLA_ABLATION_SEED_LOG=str(seed_log))
            begun = time.monotonic()
            with (dest / "run.log").open("w") as log:
                exit_code = subprocess.run(command, cwd=dest, env=env, stdout=log,
                                           stderr=subprocess.STDOUT).returncode
            files = list((dest / "output").glob("*.json"))
            result = {"name": name, "command": command, "exit": exit_code,
                      "seconds": round(time.monotonic() - begun, 3), "config_sha256": sha(case_config),
                      "seed_fixed_17": (seed_log.exists() and bool(seed_log.read_text().strip()) and
                          all(re.fullmatch(r"parameter=(?:seed|random_seed) original=\d+ fixed=17", row)
                              for row in seed_log.read_text().splitlines())),
                      "seed_log_sha256": sha(seed_log) if seed_log.exists() else None,
                      "output_count": len(files), "pass": False}
            if len(files) == 1:
                data = json.loads(files[0].read_text())
                summary = data.get("summary", {})
                generated = data.get("gen", [])
                result["output_sha256"] = sha(files[0])
                result["summary"] = summary
                result["gen"] = len(generated)
                finished = (summary.get("status") == "finished" and summary.get("target-clause") == "z" + clause
                            and all(type(summary.get(key)) is int and summary[key] == 0 for key in PARTIAL))
                matching = [entry for entry in generated if number(entry["test-ins-encdec"]) == word
                            and "Retire_Success" in entry.get("ret_val", "")]
                result["retire_matching_word"] = len(matching)
                if matching:
                    entry = matching[0]
                    pre = entry.get("isa-state-complete", {})
                    post = entry.get("isa-state-post", {})
                    dest_reg = "vr31" if family == "vfmerge" else "vr1"
                    result["pre_dest"] = pre.get(dest_reg)
                    result["post_dest"] = post.get(dest_reg)
                    result["post_vstart"] = post.get("vstart")
                    result["active_changed"] = (pre.get(dest_reg) != post.get(dest_reg))
                    events = entry.get("memory-events", [])
                    result["memory_events"] = events
                    expected_events = (len(events) == 1 and events[0].get("kind") == "read") if family == "vector-load" and start == 0 else (not events)
                    result["pass"] = (exit_code == 0 and result["seed_fixed_17"] and finished
                        and len(matching) == 1 and number(post["vstart"]) == 0
                        and expected_events
                        and (result["active_changed"] if start == 0 else not result["active_changed"]))
            (dest / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
            results.append(result)
            print(name, "PASS" if result["pass"] else "FAIL", flush=True)
    verify_source(inputs["model_source_manifest"])
    verify_source(inputs["isla_source_manifest"])
    if any(sha(path) != inputs[key]["sha256"] for key, path in (("binary", binary), ("ir", ir), ("config", config))):
        raise ValueError("运行期间输入字节漂移")
    (out / "summary.json").write_text(json.dumps({"pass": all(row["pass"] for row in results),
                                                     "results": results}, indent=2, ensure_ascii=False) + "\n")
    raise SystemExit(0 if all(row["pass"] for row in results) else 1)


if __name__ == "__main__":
    main()
