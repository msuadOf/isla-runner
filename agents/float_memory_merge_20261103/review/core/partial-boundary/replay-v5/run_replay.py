#!/usr/bin/env python3
"""一次性诊断驱动：将捕获的模型前态钉给独立探针，不用于验收。"""

import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
NEW = WORKSPACE / ".worktree/merge-float-memory-20261104/isla/ir/rv64d_v128_e64.ir"
OLD = WORKSPACE / "agents/float_memory_merge_20261103/validation/dynamic/baseline-bdd/source/rv64d.ir"
CONFIG = WORKSPACE / ".worktree/merge-float-memory-20261104/isla/configs/riscv64_difftest_mem.toml"
PRELOAD = WORKSPACE / "agents/branch_ablation_official_z3_20261102/bin/seed_control.so"
DEBUG_REGS = json.loads((ROOT / "run-p3-v2/p3-poison.json").read_text())["concrete_registers"]


def values_for(mode):
    if mode == "p3":
        values = json.loads((ROOT / "run-p3-v3/p3-poison.json").read_text())["concrete_registers"]
        return {name: value for name, value in values.items()
                if value != "uninitialized" and not value.startswith("error:")}
    capture = "run-cld-main/main-poison.json" if mode == "cld" else "run-main-v2/main-poison.json"
    raw = json.loads((ROOT / capture).read_text())["prestate"]
    assert raw.startswith("Ok(") and raw.endswith(")")
    return ast.literal_eval(raw[3:-1])


def prestate_arg(name, value):
    if name == "cur_privilege":
        return f"{name}={value}"
    debug = DEBUG_REGS.get(name, "")
    if debug.startswith("Ok(Bool("):
        boolean = "true" if "Bool(true)" in debug else "false"
        return f"{name}={boolean}"
    match = re.fullmatch(r"(\d+)'h([0-9a-fA-F_]+)", value)
    if not match:
        raise ValueError((name, value))
    width = int(match.group(1))
    if width % 4:
        bits = "0b" + format(int(match.group(2).replace("_", ""), 16), f"0{width}b")
    else:
        bits = "0x" + match.group(2).replace("_", "")
    if debug.startswith("Ok(Struct(") or name in {"mstatus", "fcsr", "vcsr", "vtype"}:
        return f"{name}={{bits={bits}}}"
    return f"{name}={bits}"


def main():
    mode, version = sys.argv[1:]
    assert mode in {"p3", "main", "cld"} and version in {"new", "old"}
    run = ROOT / f"replay-{mode}-{version}-{os.environ.get('FM_REPLAY_TAG', 'v4')}"
    run.mkdir(exist_ok=False)
    state = values_for(mode)
    pins = [prestate_arg(name, value) for name, value in sorted(state.items())]
    ir = NEW if version == "new" else OLD
    binary = ROOT / ("target/release/isarch" if version == "new" else "target-bdd/release/isarch")
    command = ["timeout", "--signal=TERM", "--kill-after=10s", "180s", "taskset", "-c", "30",
               str(binary), "-A", str(ir), "-C", str(CONFIG), "--verbose", "--debug=fmlgcsra",
               "--probe-all", "--trace-all", "-T", "1", "--timeout", "7200s",
               "--smt-timeout", "7200s", "--tastic", "qfaufbv"]
    if mode == "p3":
        command.extend(["--instruction-bits", "0x01ffb023"])
    for pin in pins:
        command.extend(["--prestate", pin])
    command.extend(["solve-state", "--clause=" + ("C_LD" if mode == "cld" else "STORE")])
    env = dict(os.environ, LD_PRELOAD=str(PRELOAD), ISLA_ABLATION_SEED="17",
               ISLA_ABLATION_SEED_LOG=str(run / "seed.log"))
    if mode == "p3":
        env["FM_STORE_DIRECT_DECODE_OUT"] = str(run / "decode.json")
    elif mode == "main":
        env["FM_STORE_DIRECT_CTOR_WIDTH"] = "1"
        env["FM_STORE_MAIN_POISON_PROBE_OUT"] = str(run / "main-poison.json")
    else:
        env["FM_CLD_DIRECT_CTOR"] = "1"
        env["FM_STORE_MAIN_POISON_PROBE_OUT"] = str(run / "main-poison.json")
    (run / "input.json").write_text(json.dumps({"mode": mode, "version": version,
        "ir": str(ir), "config": str(CONFIG), "binary": str(binary),
        "prestate_pins": pins, "command": command}, ensure_ascii=False, indent=2) + "\n")
    with (run / "run.log").open("w") as log:
        result = subprocess.run(command, cwd=run, env=env, stdout=log, stderr=subprocess.STDOUT)
    (run / "exit-code.txt").write_text(f"{result.returncode}\n")
    print(f"{mode} {version} exit={result.returncode} pins={len(pins)} output={run}")


if __name__ == "__main__":
    main()
