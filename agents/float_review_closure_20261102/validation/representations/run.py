#!/usr/bin/env python3
"""Generate fresh final-model JSON and check GCC/Clang's three encodings."""

import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time

from common import HERE, ROOT, dump, finished_summary, fixed_seed, frozen_inputs, sha, toolchain_identity
from check_exact_json import decoded

SPECIAL = ROOT / "agents/special_control_restore_20261102/validation/run.py"
CHECK_JSON = HERE / "check_exact_json.py"
EXECUTEAS = ROOT / "agents/encoding_constraint_isolation_20261102/validation/run_directed.py"
FIXTURES = ROOT / "agents/independent_topic_review_20261030/float"
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cases(special):
    jobs = {job["name"]: job for job in special.jobs()}
    result = [(name, "directed", jobs[name]) for name in (
        "fleq-H-qNaN", "fleq-S-qNaN", "fleq-D-qNaN",
        "sqrt-H", "sqrt-D")]
    state = special.common()
    state.update({f"f{i}": f"0x{special.box(0xbf800000 if i < 16 else 0x3f800000, 32):016x}" for i in range(32)})
    result.append(("sqrt-S", "directed", special.mkjob(
        "sqrt-S", "F_UN_RM_FF_TYPE_S", state, check={"kind": "sqrt", "format": "S"})))

    # SEW8 is legal here because the source is f16 and the destination is i8/ui8.
    for signed, op in ((True, "zFNV_CVT_X_F"), (False, "zFNV_CVT_XU_F")):
        state = special.common(16, 2, 3)
        state["vtype"] = "0x0"
        special.setvr(state, 2, [0x3c00, 0xbc00], 16)
        name = "vfncvt-i8" if signed else "vfncvt-ui8"
        result.append((name, "directed", special.mkjob(
            name, "VFNUNARY0", state, [0, 2, op, 8],
            {"kind": "sew8-convert", "opcode": op})))

    state = special.common()
    state.update({f"x{i}": "0x1" for i in range(1, 32)})
    result.append(("exact-int-to-D", "directed", special.mkjob(
        "exact-int-to-D", "F_UN_RM_XF_TYPE_D", state,
        check={"kind": "exact-int-to-D"})))

    for name, clause in (("bf16-vl0", "VFWMACCBF16_VF"),
                         ("bf16-vl1", "VFWMACCBF16_VF"),
                         ("c-addi4spn", "C_ADDI4SPN")):
        result.append((name, "fixture", {"clause": clause, "config": FIXTURES / name / "config.toml"}))
    return result


def directed_config(base, job, special, destination):
    if "[initial_state]" in base.read_text():
        raise ValueError("base full-domain config already has initial_state")
    config = destination / "config.toml"
    config.write_text(base.read_text() + "\n[initial_state]\n" +
                      "".join(f"{key} = {json.dumps(value)}\n" for key, value in job["initial"].items()))
    return config


def check_sqrt_s(data, special):
    seen = set()
    checks = []
    for item in data["gen"]:
        if "Retire_Success" not in item["ret_val"] or not item["test-ins"].startswith("fsqrt.s"):
            continue
        rd, rs = re.findall(r"f\d+", item["test-ins"])[:2]
        raw = special.bits(item["isa-state-complete"][rs]) & 0xffffffff
        negative = bool(raw >> 31)
        seen.add("negative" if negative else "normal")
        result = special.bits(item["isa-state-post"][rd]) & 0xffffffff
        flags = special.bits(item["isa-state-post"]["fcsr"]) & 31
        checks.append(result == (0x7fc00000 if negative else 0x3f800000))
        checks.append(flags == (16 if negative else 0))
    return all(checks) and bool(checks) and seen == {"negative", "normal"}, {"seen": sorted(seen), "assertions": len(checks)}


def exact_int_to_d_wrapper(source):
    constructor = "zF_UN_RM_XF_TYPE_D"
    match = re.search(r"  " + constructor + r": %struct (\w+),", source)
    if match is None:
        raise ValueError("final IR lacks F_UN_RM_XF_TYPE_D constructor")
    struct = match[1]
    body = re.search(r"struct " + struct + r" \{(.*?)\n\}", source, re.S)
    fields = re.findall(r"\n  (\w+): ([^,\n]+)", body[1]) if body else []
    if len(fields) != 4 or fields[0][1] != "%bv5" or fields[2][1] != "%bv5":
        raise ValueError("unexpected F_UN_RM_XF_TYPE_D field layout")
    constraints = []
    for index, value in ((0, 1), (2, 0)):
        name = fields[index][0]
        constraints.extend((
            f"  validation_cond{index} : %bool;",
            f"  validation_unit{index} : %unit;",
            f"  validation_cond{index} = @eq(zmergez3var as {constructor}.{name}, 0b{value:05b});",
            f"  validation_unit{index} = $zsail_assume(validation_cond{index});",
        ))
    intro = "fn zexecute(zmergez3var) {\n"
    if source.count(intro) != 1:
        raise ValueError("unexpected zexecute definition count")
    return source.replace(
        intro,
        "val zvalidation_original_execute : (%union zinstruction) -> %union zExecutionResult\n\n"
        + intro + "\n".join(constraints)
        + "\n  return = zvalidation_original_execute(zmergez3var);\n  end;\n}\n\n"
        + "fn zvalidation_original_execute(zmergez3var) {\n",
        1,
    )


def check_exact_int_to_d(data, special):
    expected = {(op, rm) for op in ("fcvt.d.w", "fcvt.d.wu", "fcvt.d.l", "fcvt.d.lu")
                for rm in (0, 1, 2, 3, 4, 7)}
    seen = set()
    checks = []
    for item in data["gen"]:
        op = decoded(item)
        if op is None or op["op"] not in {"fcvt.d.w", "fcvt.d.wu", "fcvt.d.l", "fcvt.d.lu"}:
            checks.append(False)
            continue
        word = op["word"]
        seen.add((op["op"], op["rm"]))
        checks.extend((
            "Retire_Success" in item["ret_val"],
            (word >> 15) & 31 == 1,
            (word >> 7) & 31 == 0,
            special.bits(item["isa-state-complete"]["x1"]) == 1,
            special.bits(item["isa-state-post"]["f0"]) == 0x3ff0000000000000,
            special.bits(item["isa-state-post"]["fcsr"]) & 31 == 0,
        ))
    return bool(checks) and all(checks) and seen == expected, {
        "seen": sorted([list(pair) for pair in seen]), "expected_modes_per_op": 6,
        "assertions": len(checks), "missing": sorted([list(pair) for pair in expected - seen]),
    }


def run_case(name, kind, job, frozen, batch, cpu, special, checker, executeas):
    destination = HERE / batch / name
    destination.mkdir(parents=True, exist_ok=False)
    run_dir = destination / "run"
    run_dir.mkdir()
    (run_dir / "output").mkdir()
    source_ir = frozen["ir"]
    ir = source_ir
    if kind == "directed":
        config = directed_config(frozen["base_config"], job, special, destination)
        if name == "exact-int-to-D":
            ir = destination / "constrained.ir"
            ir.write_text(exact_int_to_d_wrapper(source_ir.read_text()))
        elif job["fields"] is not None:
            ir = destination / "constrained.ir"
            ir.write_text(special.wrapper(source_ir.read_text(), job))
    else:
        fixture = job["config"].resolve(strict=True)
        if sha(fixture) != executeas.CASE_CONFIGS[name][1]:
            raise ValueError(f"fixed-state fixture changed: {fixture}")
        config = destination / "config.toml"
        config.write_bytes(fixture.read_bytes())
    command = ["/usr/bin/time", "-f", "wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M",
               "-o", "time.txt", "timeout", "--signal=TERM", "--kill-after=10s", "7200s",
               "taskset", "-c", str(cpu), str(frozen["binary"]), "-A", str(ir), "-C", str(config),
               "-T", "1", "--tastic", "qffp", "--smt-timeout", "7200s", "solve-state",
               "--clause=" + job["clause"]]
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(frozen["preload"])
    env["ISLA_ABLATION_SEED"] = "17"
    env["ISLA_ABLATION_SEED_LOG"] = str(run_dir / "seed-intercept.log")
    record = {
        "name": name, "kind": kind, "clause": job["clause"], "domain": "directed-fixed-state", "command": command,
        "environment": {key: env[key] for key in ("LD_PRELOAD", "ISLA_ABLATION_SEED", "ISLA_ABLATION_SEED_LOG")},
        "model_commit": frozen["data"]["model_commit"], "isla_commit": frozen["data"]["isla_commit"],
        "inputs_sha256": frozen["inputs_sha256"], "binary_sha256": sha(frozen["binary"]),
        "source_ir_sha256": sha(source_ir), "run_ir_sha256": sha(ir),
        "config_sha256": sha(config), "z3_sha256": sha(frozen["z3"]),
        "preload_sha256": sha(frozen["preload"]), "cpu": cpu,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if kind == "fixture":
        record["fixture_source"] = str(fixture)
        record["fixture_source_sha256"] = sha(fixture)
    dump(run_dir / "command.json", record)
    start = time.monotonic()
    with (run_dir / "run.log").open("wb") as log:
        code = subprocess.run(command, cwd=run_dir, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    record.update(exit_code=code, elapsed_s=round(time.monotonic() - start, 3),
                  finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  run_log_sha256=sha(run_dir / "run.log"))
    paths = sorted((run_dir / "output").glob("*.json"))
    record["json_count"] = len(paths)
    seed_log = run_dir / "seed-intercept.log"
    record["seed_fixed_17"] = fixed_seed(seed_log)
    record["seed_log_sha256"] = sha(seed_log) if seed_log.exists() else None
    if len(paths) == 1:
        output = paths[0]
        data = json.loads(output.read_text())
        record.update(output_sha256=sha(output), summary=data.get("summary"), gen=len(data.get("gen", [])))
        complete = code == 0 and finished_summary(data, job["clause"])
        if complete:
            try:
                record["representations"] = checker.check(output, destination / "toolchains")
                if name.startswith("bf16-"):
                    checks = json.loads((destination / "toolchains/results.json").read_text())
                    legal = sum(not item["ret_val"].startswith("Illegal_Instruction") for item in data["gen"])
                    record["bf16_contract"] = legal > 0 and checks["illegal"] > 0 and checks["clang_mnemonic_rejections"] > 0
                if name == "c-addi4spn":
                    record["executeas"] = executeas.check_executeas(data)
                if name.startswith("vfncvt-"):
                    record["sew8_legal"] = bool(data["gen"]) and all("Retire_Success" in item["ret_val"] and "vfncvt." in item["test-ins"] for item in data["gen"])
                if kind == "directed" and job["check"]["kind"] != "sew8-convert":
                    if name == "sqrt-S":
                        record["semantic_pass"], record["semantic_detail"] = check_sqrt_s(data, special)
                    elif name == "exact-int-to-D":
                        record["semantic_pass"], record["semantic_detail"] = check_exact_int_to_d(data, special)
                    else:
                        record["semantic_pass"], record["semantic_detail"] = special.inspect(job, data)
            except Exception as exc:
                record["validation_error"] = f"{type(exc).__name__}: {exc}"
    record["pass"] = ("validation_error" not in record and code == 0 and record["seed_fixed_17"]
                      and len(paths) == 1 and finished_summary(data, job["clause"])
                      and record.get("representations", {}).get("all_pass", False)
                      and record.get("bf16_contract", True) and record.get("sew8_legal", True)
                      and record.get("semantic_pass", True)
                      and (name != "c-addi4spn" or bool(record.get("executeas"))))
    dump(destination / "result.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpu", type=int, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch):
        parser.error("invalid batch name")
    frozen = frozen_inputs(args.inputs)
    special = load(SPECIAL, "special_representations")
    checker = load(CHECK_JSON, "check_final_json")
    executeas = load(EXECUTEAS, "check_final_executeas")
    batch_dir = HERE / args.batch
    batch_dir.mkdir(parents=True, exist_ok=False)
    provenance = {"inputs": str(frozen["inputs"]), "inputs_sha256": frozen["inputs_sha256"],
                  "model_commit": frozen["data"]["model_commit"], "isla_commit": frozen["data"]["isla_commit"],
                  "binary_sha256": sha(frozen["binary"]), "ir_sha256": sha(frozen["ir"]),
                  "z3_sha256": sha(frozen["z3"]), "preload_sha256": sha(frozen["preload"]),
                  "special_harness_sha256": sha(SPECIAL), "checker_sha256": sha(CHECK_JSON),
                  "generic_checker_sha256": sha(checker.GENERIC),
                  "executeas_checker_sha256": sha(EXECUTEAS),
                  "runner_sha256": sha(Path(__file__)), "common_sha256": sha(HERE / "common.py"),
                  "toolchains": toolchain_identity(checker), "ldd": frozen["ldd"], "cpu": args.cpu}
    dump(batch_dir / "provenance.json", provenance)
    results = []
    for name, kind, job in cases(special):
        try:
            result = run_case(name, kind, job, frozen, args.batch, args.cpu, special, checker, executeas)
        except Exception as exc:
            result = {"name": name, "exit_code": None, "elapsed_s": None, "gen": None,
                      "pass": False, "runner_error": f"{type(exc).__name__}: {exc}"}
            dump(batch_dir / name / "runner_error.json", result)
        results.append({key: result.get(key) for key in ("name", "exit_code", "elapsed_s", "gen", "pass")})
        dump(batch_dir / "summary.json", {"provenance": provenance, "results": results, "complete": False})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    dump(batch_dir / "summary.json", {"provenance": provenance, "results": results,
                                      "complete": True, "all_pass": all(row["pass"] for row in results)})


if __name__ == "__main__":
    main()
