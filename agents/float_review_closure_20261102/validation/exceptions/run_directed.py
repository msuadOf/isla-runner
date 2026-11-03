#!/usr/bin/env python3
"""Run fixed exception/ROD/BF16 probes on a frozen IR and isarch binary.

This is a directed numerical oracle check. It does not sign complete Clause
budgets or IR CFG coverage.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
from queue import Queue
import re
import shutil
import subprocess
import sys
import time
import tomllib


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
from run_clause import checked, verify_tree, seed_record, OFFICIAL_FD_CONFIG_SHA256
PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
           "omitted-cases", "model-query-timeouts", "pending-batches", "sampled-paths")
RM_NAMES = ("zRM_RNE", "zRM_RTZ", "zRM_RDN", "zRM_RUP", "zRM_RMM")
BASE_MODEL_COMMIT = "8ad5e8e9e0fc2a567a3b989a3738698f5c520bde"
ASSEMBLY_MODEL_COMMIT = "21418d0b0d4942fae20061ed580ee04aff4a8a61"
ASSEMBLY_DELTA_SHA256 = "305d826ee485b4803ffe8cb747cc9e20f815897c3b2714415a51c00867459bd7"
CORE_MODEL_COMMIT = "e9d69d2f28586c089244c8e37ee4c904c5114458"
CORE_DELTA_SHA256 = "9dbf13575b7b32f48adb05f40c392bdbd520f77a980cea4d7594946808a1e9dd"
CONVERGED_MODEL_COMMIT = "0f7b8fbc6724103f91f929ef6918f123df75d6c9"
CONVERGED_DELTA_SHA256 = "01ad2e7f97de170aa7e400979b5c00af49e3f473e8b65946d16faa2fe39c74ae"
CONVERGED_FILES = (
    "model/core/ieee_fp_exceptions.sail",
    "model/extensions/FD/softfloat_symbolic_f16.sail",
    "model/extensions/FD/softfloat_symbolic_f32.sail",
    "model/extensions/FD/softfloat_symbolic_f64.sail",
    "model/extensions/V/vext_fp_utils_insts.sail",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def value(x):
    if isinstance(x, int):
        return x
    match = re.fullmatch(r"\d+'h([0-9a-fA-F_]+)", x)
    if match:
        return int(match.group(1).replace("_", ""), 16)
    return int(x[2:], 2) if x.startswith("0b") else int(x, 16)


def box(bits, width):
    return bits | (((1 << (64 - width)) - 1) << width) if width < 64 else bits


def pack(values, width):
    return sum(x << (width * i) for i, x in enumerate(values))


def constrained_ir(source, clause, fields):
    constructor = "z" + clause
    match = re.search(r"  " + constructor + r": %struct (\w+),", source)
    assert match, f"missing clause {constructor}"
    struct = match.group(1)
    body = re.search(r"struct " + struct + r" \{(.*?)\n\}", source, re.S)
    assert body, f"missing struct {struct}"
    types = re.findall(r"\n  (\w+): ([^,\n]+)", body.group(1))
    assert len(types) == len(fields), (clause, types, fields)
    assumptions = []
    for index, ((field, ty), literal) in enumerate(zip(types, fields)):
        if isinstance(literal, int):
            assert ty.startswith("%bv"), (clause, ty, literal)
            literal = "0b" + format(literal, "0" + ty[3:] + "b")
        else:
            assert ty.startswith("%enum ") and literal.startswith("z"), (clause, ty, literal)
        assumptions += [f"  exception_cond{index} : %bool;",
                        f"  exception_unit{index} : %unit;",
                        f"  exception_cond{index} = @eq(zmergez3var as {constructor}.{field}, {literal});",
                        f"  exception_unit{index} = $zsail_assume(exception_cond{index});"]
    marker = "fn zexecute(zmergez3var) {\n"
    assert source.count(marker) == 1
    replacement = ("val zexception_original_execute : (%union zinstruction) -> %union zExecutionResult\n\n"
                   + marker + "\n".join(assumptions)
                   + "\n  return = zexception_original_execute(zmergez3var);\n  end;\n}\n\n"
                   + "fn zexception_original_execute(zmergez3var) {\n")
    return source.replace(marker, replacement, 1)


def scalar_job(case):
    tag = {16: "H", 32: "S", 64: "D"}[case["width"]]
    op, rm = case["op"], case["rm"]
    state = {"mstatus": 0x6600, "fcsr": 0,
             "f0": hex(box(int(case["a"], 16), case["width"])),
             "f1": hex(box(int(case["b"], 16), case["width"])) if case["b"] else "0x0",
             "f2": hex(box(int(case["c"], 16), case["width"])) if case["c"] else "0x0",
             "f3": "0x0"}
    if op == "sqrt":
        clause = f"F_UN_RM_FF_TYPE_{tag}"
        fields = [0, RM_NAMES[rm], 3, f"zFSQRT_{tag}"]
    elif op == "fma":
        clause = f"F_MADD_TYPE_{tag}"
        fields = [2, 1, 0, RM_NAMES[rm], 3, f"zFMADD_{tag}"]
    else:
        clause = f"F_BIN_RM_TYPE_{tag}"
        fields = [1, 0, RM_NAMES[rm], 3, f"zF{op.upper()}_{tag}"]
    return {"name": case["name"], "family": "scalar", "clause": clause,
            "fields": fields, "initial": state, "expected": case,
            "expected_full_bits": hex(box(int(case["expected_bits"], 16), case["width"]))}


def convert_job(case):
    src_width = {"f32": 32, "f64": 64}[case["fmt"]]
    dst_width = case["width"]
    opcode = "zFNV_CVT_ROD_F_F" if case["family"] == "rod" else "zFNV_CVT_F_F"
    state = {"mstatus": 0x6600, "fcsr": case["rm"] << 5 if case["family"] != "rod" else 0,
             "vtype": hex({16: 8, 32: 16}[dst_width]), "vl": "0x1", "vstart": "0x0",
             **{f"vr{i}": "0x" + "0" * 32 for i in range(32)}}
    state["vr2"] = f"0x{int(case['a'], 16):032x}"
    return {"name": case["name"], "family": case["family"],
            "clause": "VFNUNARY0", "fields": [1, 2, opcode, 8],
            "initial": state, "expected": case, "dest_width": dst_width,
            "source_width": src_width}


def bf16_job(case):
    state = {"mstatus": 0x6600, "fcsr": case["rm"] << 5,
             "vtype": "0x8", "vl": hex(case["vl"]), "vstart": "0x0",
             **{f"vr{i}": "0x" + "0" * 32 for i in range(32)}}
    state["vr0"] = f"0x{case['mask']:032x}"
    state["vr2"] = f"0x{pack([int(x, 16) for x in case['a']], 16):032x}"
    state["vr4"] = f"0x{pack([int(x, 16) for x in case['b']], 16):032x}"
    state["vr8"] = f"0x{pack([int(x, 16) for x in case['acc']], 32):032x}"
    state["f4"] = hex(box(int(case["b"][0], 16), 16))
    return {"name": case["name"], "family": "bf16",
            "clause": "VFWMACCBF16_" + case["form"],
            "fields": [0, 2, 4, 8], "initial": state, "expected": case}


def vector_job(case):
    width = case["width"]
    state = {"mstatus": 0x6600, "fcsr": case["rm"] << 5,
             "vtype": hex({16: 8, 32: 16, 64: 24}[width]),
             "vl": hex(case["vl"]), "vstart": "0x0",
             **{f"vr{i}": "0x" + "0" * 32 for i in range(32)}}
    state["vr0"] = f"0x{case['mask']:032x}"
    for reg, values in (("vr2", case["a"]), ("vr4", case["b"])):
        packed = pack([int(x, 16) for x in values], width)
        # TOML initial_state parses a hex value as u64; the bit-pattern form
        # supports all 128 bits of two f64 lanes in one vector register.
        state[reg] = "0b" + format(packed, "0128b") if width == 64 else f"0x{packed:032x}"
    return {"name": case["name"], "family": "vector", "clause": "FVVTYPE",
            "fields": ["zFVV_V" + case["op"].upper(), 0, 2, 4, 8],
            "initial": state, "expected": case, "dest_width": width}


def inspect(job, data, ir, config):
    summary = data.get("summary", {})
    assert isinstance(summary, dict) and all(key in summary for key in (*PARTIAL, "status", "target-clause")), summary
    assert all(type(summary[key]) is int and summary[key] >= 0 for key in PARTIAL), summary
    assert summary["target-clause"] == "z" + job["clause"], summary
    assert summary["status"] == "finished" and all(summary[key] == 0 for key in PARTIAL), summary
    provenance = data.get("provenance", {}).get("inputs", {})
    for flag, path in (("-A", ir), ("-C", config)):
        item = provenance.get(flag)
        assert isinstance(item, dict) and item.get("path") == str(path), (flag, item)
        assert item.get("sha256") == sha(path), (flag, item)
    generated = data.get("gen", [])
    success = [entry for entry in generated if "Retire_Success" in entry.get("ret_val", "")]
    assert len(generated) == 1 and len(success) == 1, (len(generated), len(success))
    entry = success[0]
    pre, post = entry["isa-state-complete"], entry["isa-state-post"]
    assertions = []
    def check(label, actual, expected):
        assertions.append({"name": label, "actual": hex(actual) if isinstance(actual, int) else actual,
                           "expected": hex(expected) if isinstance(expected, int) else expected,
                           "pass": actual == expected})
    for key, expected in job["initial"].items():
        assert key in pre and key in post, (job["name"], key)
        check("initial." + key, value(pre[key]), value(expected))
    check("mstatus.post", value(post["mstatus"]), value(pre["mstatus"]) | (1 << 63))
    check("mstatus.FS", (value(post["mstatus"]) >> 13) & 3, 3)
    check("mstatus.VS", (value(post["mstatus"]) >> 9) & 3, 3)
    flags = int(job["expected"]["expected_flags"], 16)
    check("fcsr.flags", value(post["fcsr"]) & 31,
          (value(job["initial"]["fcsr"]) & 31) | flags)
    check("fcsr.rm", value(post["fcsr"]) >> 5, value(job["initial"]["fcsr"]) >> 5)
    if job["family"] == "scalar":
        check("f3.full", value(post["f3"]), int(job["expected_full_bits"], 16))
        for index in range(32):
            if index != 3:
                reg = f"f{index}"
                assert reg in pre and reg in post, reg
                check("preserve." + reg, value(post[reg]), value(pre[reg]))
    elif job["family"] in ("rod", "ordinary-convert"):
        width = job["dest_width"]
        expected = int(job["expected"]["expected_bits"], 16)
        check("vr8.full", value(post["vr8"]),
              (value(pre["vr8"]) & ~((1 << width) - 1)) | expected)
        check("vstart", value(post["vstart"]), 0)
        for reg in range(32):
            if reg != 8:
                check(f"preserve.vr{reg}", value(post[f"vr{reg}"]), value(pre[f"vr{reg}"]))
    else:
        width = job["dest_width"] if job["family"] == "vector" else 32
        expected = pack([int(lane["bits"], 16) for lane in job["expected"]["lanes"]], width)
        check("vr8.full", value(post["vr8"]),
              (value(pre["vr8"]) & ~((1 << (2 * width)) - 1)) | expected)
        check("vstart", value(post["vstart"]), 0)
        for reg in range(32):
            if reg != 8:
                check(f"preserve.vr{reg}", value(post[f"vr{reg}"]), value(pre[f"vr{reg}"]))
    representation = entry.get("instruction-representations", {})
    encoding = representation.get("encoding", {})
    check("encoding.status", encoding.get("status"), "complete")
    check("encoding.bit-length", encoding.get("bit-length"), 32)
    for index in range(1, 32):
        reg = f"x{index}"
        assert reg in pre and reg in post, reg
        check("preserve." + reg, value(post[reg]), value(pre[reg]))
    if job["family"] != "scalar":
        for index in range(32):
            reg = f"f{index}"
            assert reg in pre and reg in post, reg
            check("preserve." + reg, value(post[reg]), value(pre[reg]))
    return {"pass": all(row["pass"] for row in assertions), "assertions": assertions,
            "instruction": entry.get("test-ins"), "representations": representation,
            "summary": summary, "ret_val": entry.get("ret_val")}


def execute(job, frozen, out, cpu, timeout_seconds):
    dest = out / "runs" / job["name"]
    dest.mkdir(parents=True, exist_ok=False)
    config = dest / "config.toml"
    config.write_text(frozen["base_config"].read_text() + "\n[initial_state]\n"
                      + "".join(f"{key} = {json.dumps(val)}\n" for key, val in job["initial"].items()))
    ir = dest / "constrained.ir"
    ir.write_text(constrained_ir(frozen["ir"].read_text(), job["clause"], job["fields"]))
    command = ["timeout", "--signal=TERM", "--kill-after=10s", f"{timeout_seconds}s"]
    if cpu is not None:
        command += ["taskset", "-c", str(cpu)]
    command += [str(frozen["binary"]), "-A", str(ir), "-C", str(config), "-T", "1",
                "--smt-timeout", f"{timeout_seconds}s", "--tastic", "qffp", "solve-state",
                "--clause=" + job["clause"]]
    write(dest / "command.json", {"argv": command, "job": job,
                                  "binary_sha256": sha(frozen["binary"]),
                                  "base_ir_sha256": sha(frozen["ir"]),
                                  "constrained_ir_sha256": sha(ir),
                                  "config_sha256": sha(config), "cpu": cpu,
                                  "environment": {"LD_PRELOAD": str(frozen["seed_preload"]),
                                                  "ISLA_ABLATION_SEED": "17",
                                                  "ISLA_ABLATION_SEED_LOG": str(dest / "seed-intercept.log")}})
    started = time.monotonic()
    environment = dict(os.environ)
    environment.pop("LD_LIBRARY_PATH", None)
    environment["LD_PRELOAD"] = str(frozen["seed_preload"])
    environment["ISLA_ABLATION_SEED"] = "17"
    environment["ISLA_ABLATION_SEED_LOG"] = str(dest / "seed-intercept.log")
    with (dest / "run.log").open("w") as log:
        exit_code = subprocess.run(command, cwd=dest, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT).returncode
    elapsed = time.monotonic() - started
    files = list((dest / "output").glob("*.json"))
    result = {"name": job["name"], "exit_code": exit_code,
              "seconds": round(elapsed, 3), "status": "FAIL", "output_count": len(files)}
    seed = seed_record(dest / "seed-intercept.log")
    result["seed"] = seed
    result["seed_log_sha256"] = sha(dest / "seed-intercept.log") if (dest / "seed-intercept.log").exists() else None
    if len(files) == 1:
        result["output_sha256"] = sha(files[0])
        try:
            result["inspection"] = inspect(job, json.loads(files[0].read_text()), ir, config)
            result["status"] = "PASS" if exit_code == 0 and seed["valid"] and result["inspection"]["pass"] else "FAIL"
        except Exception as error:
            result["inspection_error"] = repr(error)
    if exit_code in (124, 137):
        result["status"] = "TIMEOUT"
    write(dest / "result.json", result)
    ir.unlink()  # The frozen base IR and command/constraint fields reproduce this temporary file.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True, help="final frozen validation inputs JSON")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--family", choices=["scalar", "rod", "ordinary-convert", "vector", "bf16", "all"], default="all")
    parser.add_argument("--name", help="optional regex selecting names within family")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cpus", required=True, help="comma-separated exclusive physical CPU lanes")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--dry-run", action="store_true", help="verify freeze and selected cases without creating output")
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(HERE), "output must stay in validation/exceptions"
    assert not out.exists(), "output already exists; use a new run directory"
    assert args.workers > 0 and args.timeout > 0
    cpus = [int(x) for x in args.cpus.split(",")]
    assert len(cpus) == args.workers and len(set(cpus)) == len(cpus)
    siblings = [(Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
                 .read_text().strip()) for cpu in cpus]
    assert len(set(siblings)) == len(siblings), "allocated CPUs share SMT siblings"
    assert set(cpus) <= set(os.sched_getaffinity(0)), "allocated CPU outside process affinity"
    inputs = json.loads(args.inputs.read_text())
    assert inputs.get("domain") == "full" and inputs.get("seed") == 17
    assert inputs.get("tactic") == "qffp" and inputs.get("threads") == 1
    expected = json.loads((HERE / "expected.json").read_text())
    oracle = ROOT / ".tmp/unified-backend-crosscheck/oracle-build/oracle"
    oracle_source = ROOT / "agents/float_support_review/oracle/oracle.cpp"
    archive = oracle.parent / "softfloat/libsoftfloat.a"
    assert sha(oracle) == expected["oracle_binary_sha256"]
    assert sha(oracle_source) == expected["oracle_source_sha256"]
    assert sha(archive) == expected["softfloat_archive_sha256"]
    assert expected["model_commit"] == BASE_MODEL_COMMIT
    assert inputs["model_commit"] in (BASE_MODEL_COMMIT, ASSEMBLY_MODEL_COMMIT,
                                      CORE_MODEL_COMMIT, CONVERGED_MODEL_COMMIT)
    model_delta_sha256 = None
    model_delta_base_commit = None
    if inputs["model_commit"] == ASSEMBLY_MODEL_COMMIT:
        delta = subprocess.check_output(["git", "-C", str(ROOT / ".worktree/runner-float/sail-riscv"),
                                         "diff", BASE_MODEL_COMMIT, ASSEMBLY_MODEL_COMMIT])
        model_delta_sha256 = hashlib.sha256(delta).hexdigest()
        model_delta_base_commit = BASE_MODEL_COMMIT
        assert model_delta_sha256 == ASSEMBLY_DELTA_SHA256, "unexpected model delta"
    elif inputs["model_commit"] == CORE_MODEL_COMMIT:
        model_repo = ROOT / "sail-riscv"
        parent = subprocess.check_output(["git", "-C", str(model_repo), "rev-parse",
                                          CORE_MODEL_COMMIT + "^"], text=True).strip()
        assert parent == ASSEMBLY_MODEL_COMMIT, "unexpected candidate parent"
        changed = subprocess.check_output(["git", "-C", str(model_repo), "diff", "--name-only",
                                           ASSEMBLY_MODEL_COMMIT, CORE_MODEL_COMMIT], text=True).splitlines()
        assert changed == ["model/core/ieee_fp_exceptions.sail"], "unexpected candidate file scope"
        delta = subprocess.check_output(["git", "-C", str(model_repo), "diff", "--no-ext-diff",
                                         ASSEMBLY_MODEL_COMMIT, CORE_MODEL_COMMIT])
        model_delta_sha256 = hashlib.sha256(delta).hexdigest()
        model_delta_base_commit = ASSEMBLY_MODEL_COMMIT
        assert model_delta_sha256 == CORE_DELTA_SHA256, "unexpected core delta"
    elif inputs["model_commit"] == CONVERGED_MODEL_COMMIT:
        model_repo = ROOT / ".worktree/sail-riscv-float-converged-20261103"
        chain = subprocess.check_output(["git", "-C", str(model_repo), "rev-list", "--first-parent",
                                         CORE_MODEL_COMMIT + ".." + CONVERGED_MODEL_COMMIT],
                                        text=True).splitlines()
        assert chain == [CONVERGED_MODEL_COMMIT,
                         "7eb4bd5c137c500209678f2f6eb007b572179b74",
                         "3d9ceebb8ae81b45ccafcde7cab81c0ab5b49bd8"], "unexpected candidate ancestry"
        changed = subprocess.check_output(["git", "-C", str(model_repo), "diff", "--name-only",
                                           CORE_MODEL_COMMIT, CONVERGED_MODEL_COMMIT],
                                          text=True).splitlines()
        assert tuple(changed) == CONVERGED_FILES, "unexpected converged file scope"
        delta = subprocess.check_output(["git", "-C", str(model_repo), "diff", "--no-ext-diff",
                                         CORE_MODEL_COMMIT, CONVERGED_MODEL_COMMIT])
        model_delta_sha256 = hashlib.sha256(delta).hexdigest()
        model_delta_base_commit = CORE_MODEL_COMMIT
        assert model_delta_sha256 == CONVERGED_DELTA_SHA256, "unexpected converged delta"
    for commit, tree in (("model_commit", "model_tree"), ("isla_commit", "isla_tree")):
        verify_tree(inputs[tree], inputs[commit])
    binary = checked(ROOT, inputs["binary"])
    z3 = checked(ROOT, inputs["z3"])
    seedlib = checked(ROOT, inputs["seed_preload"])
    ir = checked(ROOT, inputs["irs"]["rv64-v128"])
    assert b"zvalidation_original_execute" not in ir.read_bytes()
    assert b"zexception_original_execute" not in ir.read_bytes()
    base_config = checked(ROOT, inputs["configs"]["rv64-fd-full"])
    official_config = ROOT / "isla/configs/riscv64_difftest_fd.toml"
    assert sha(base_config) == sha(official_config) == OFFICIAL_FD_CONFIG_SHA256
    assert "initial_state" not in tomllib.loads(base_config.read_text())
    assert sha(z3) == "899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970"
    link_env = dict(os.environ)
    link_env.pop("LD_LIBRARY_PATH", None)
    link_env.pop("LD_PRELOAD", None)
    linked = subprocess.check_output(["ldd", str(binary)], text=True, env=link_env)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    assert len(matches) == 1 and Path(matches[0]).resolve() == z3.resolve(), linked
    jobs = [scalar_job(c) if c["family"] == "scalar" else convert_job(c)
            for c in expected["cases"]]
    jobs += [vector_job(c) for c in expected["vectors"]]
    jobs += [bf16_job(c) for c in expected["bf16"]]
    jobs = [job for job in jobs if (args.family == "all" or job["family"] == args.family)
            and (args.name is None or re.search(args.name, job["name"]))]
    assert jobs, "no selected cases"
    for job in jobs:
        mapping = inputs["jobs"][job["clause"]]
        assert mapping["ir"] == "rv64-v128" and mapping["config"] == "rv64-fd-full", job["name"]
    if args.dry_run:
        print(json.dumps({"inputs_sha256": sha(args.inputs), "model_commit": inputs["model_commit"],
                          "isla_commit": inputs["isla_commit"], "ir_sha256": sha(ir),
                          "binary_sha256": sha(binary), "z3_sha256": sha(z3),
                          "seed_preload_sha256": sha(seedlib), "cases": len(jobs),
                          "cpu_lanes": cpus, "timeout_seconds": args.timeout}, indent=2))
        return
    out.mkdir(parents=True)
    frozen = {"ir": out / "base.ir", "binary": out / "isarch",
              "base_config": out / "base-config.toml", "seed_preload": out / "seed_control.so"}
    for key, src in (("ir", ir), ("binary", binary), ("base_config", base_config),
                     ("seed_preload", seedlib)):
        shutil.copy2(src.resolve(), frozen[key])
        assert sha(src) == sha(frozen[key]), key
    write(out / "launch.json", {"model_commit": inputs["model_commit"],
                                "expected_source_commit": expected["model_commit"],
                                "model_delta_sha256": model_delta_sha256,
                                "model_delta_base_commit": model_delta_base_commit,
                                "isla_commit": inputs["isla_commit"],
                                "inputs_path": str(args.inputs.resolve()),
                                "inputs_sha256": sha(args.inputs),
                                "source_paths": {"ir": str(ir), "binary": str(binary),
                                                 "base_config": str(base_config),
                                                 "seed_preload": str(seedlib), "z3": str(z3)},
                                "frozen_hashes": {key: sha(path) for key, path in frozen.items()},
                                "z3_sha256": sha(z3), "ldd": linked,
                                "expected_sha256": sha(HERE / "expected.json"),
                                "oracle_binary_sha256": expected["oracle_binary_sha256"],
                                "oracle_source_sha256": expected["oracle_source_sha256"],
                                "softfloat_archive_sha256": expected["softfloat_archive_sha256"],
                                "script_sha256": sha(Path(__file__)),
                                "expected_generator_sha256": sha(HERE / "prepare_expected.py"),
                                "freeze_verifier_sha256": sha(HERE.parent / "run_clause.py"),
                                "jobs": [job["name"] for job in jobs],
                                "timeout_seconds": args.timeout, "workers": args.workers,
                                "cpus": cpus, "tactic": "qffp", "threads": 1})
    results = []
    completed = Queue()
    def run_lane(index):
        for job in jobs[index::args.workers]:
            try:
                result = execute(job, frozen, out, cpus[index], args.timeout)
            except Exception as error:
                result = {"name": job["name"], "status": "HARNESS_ERROR", "error": repr(error)}
            completed.put(result)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_lane, index) for index in range(args.workers)]
        for _ in jobs:
            result = completed.get()
            results.append(result)
            print(result["name"], result["status"], flush=True)
            write(out / "summary.json", {"count": len(jobs), "completed": len(results),
                                         "pass": sum(r["status"] == "PASS" for r in results),
                                         "results": sorted(results, key=lambda r: r["name"])})
        for future in futures:
            future.result()
    raise SystemExit(0 if all(r["status"] == "PASS" for r in results) else 1)


if __name__ == "__main__":
    main()
