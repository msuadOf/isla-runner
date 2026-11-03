#!/usr/bin/env python3
"""Red/green Sail forward mapping and reverse clause typechecks."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MODEL = ROOT / ".worktree/sail-riscv-float-converged-20261103"
SAIL = ROOT / "isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src/sail"
FILES = {
    "dext": "model/extensions/FD/dext_insts.sail",
    "zfh": "model/extensions/FD/zfh_insts.sail",
    "fext": "model/extensions/FD/fext_insts.sail",
    "types": "model/extensions/FD/freg_type.sail",
}
MAPPINGS = {
    "dext": ("F_UN_RM_FF_TYPE_D", "F_UN_RM_XF_TYPE_D"),
    "zfh": ("F_UN_RM_FF_TYPE_H",),
    "fext": ("F_UN_RM_XF_TYPE_S",),
}
MNEMONIC_MAPPINGS = {
    "dext": ("f_un_rm_ff_type_mnemonic_D", "f_un_rm_xf_type_mnemonic_D"),
    "zfh": ("f_un_rm_ff_type_mnemonic_H",),
    "fext": ("f_un_rm_xf_type_mnemonic_S",),
}
OPS = [
    ("F_UN_RM_FF_TYPE_D", "FCVT_D_S", "fcvt.d.s", "ff", True),
    ("F_UN_RM_FF_TYPE_H", "FCVT_D_H", "fcvt.d.h", "ff", True),
    ("F_UN_RM_FF_TYPE_H", "FCVT_S_H", "fcvt.s.h", "ff", True),
    ("F_UN_RM_XF_TYPE_D", "FCVT_D_W", "fcvt.d.w", "xf", True),
    ("F_UN_RM_XF_TYPE_D", "FCVT_D_WU", "fcvt.d.wu", "xf", True),
    ("F_UN_RM_XF_TYPE_D", "FCVT_D_L", "fcvt.d.l", "xf", False),
    ("F_UN_RM_XF_TYPE_D", "FCVT_D_LU", "fcvt.d.lu", "xf", False),
    ("F_UN_RM_XF_TYPE_S", "FCVT_S_W", "fcvt.s.w", "xf", False),
    ("F_UN_RM_FF_TYPE_D", "FSQRT_D", "fsqrt.d", "ff", False),
    ("F_UN_RM_FF_TYPE_D", "FCVT_S_D", "fcvt.s.d", "ff", False),
    ("F_UN_RM_FF_TYPE_H", "FSQRT_H", "fsqrt.h", "ff", False),
    ("F_UN_RM_FF_TYPE_H", "FCVT_H_S", "fcvt.h.s", "ff", False),
    ("F_UN_RM_FF_TYPE_H", "FCVT_H_D", "fcvt.h.d", "ff", False),
]
RMS = ("RNE", "RTZ", "RDN", "RUP", "RMM", "DYN")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def block(text, pattern):
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"missing source definition: {pattern}")
    return match.group(0)


def definition(text, name, kind="mapping"):
    return block(text, rf"^{kind} {re.escape(name)}\b[^\n]*\n(?:[^\n]+\n)*")


def enum_definition(text, name):
    return block(text, rf"^enum {re.escape(name)}\s*=\s*\{{[^}}]+\}}")


def source_for(mode):
    result = {}
    for key, path in FILES.items():
        if mode == "baseline" and key in ("dext", "zfh"):
            result[key] = subprocess.check_output(
                ["git", "-C", str(MODEL), "show", f"8ad5e8e9e0fc2a567a3b989a3738698f5c520bde:{path}"],
                text=True)
        else:
            result[key] = (MODEL / path).read_text()
    return result


def mapping_clauses(text, constructor):
    blocks = re.findall(r"^mapping clause assembly[ \t]*=[ \t]*[^\n]*(?:\n[^\n]+)*", text, re.MULTILINE)
    selected = [item for item in blocks if constructor in item]
    if not selected:
        raise AssertionError(f"missing clauses for {constructor}")
    return selected


def test_cases():
    cases = []
    for ctor, op, mnemonic, kind, exact in OPS:
        for rm in RMS:
            for reg in (range(32) if exact else (0, 3, 31)):
                src, dest = reg, (reg * 7 + 3) % 32
                rs = f"Fregidx(0b{src:05b})" if kind == "ff" else f"Regidx(0b{src:05b})"
                rd = f"Fregidx(0b{dest:05b})"
                source_name = f"f{src}" if kind == "ff" else f"x{src}"
                expected = f"{mnemonic} f{dest}, {source_name}"
                if not exact or rm != "RNE":
                    expected += f", {rm.lower()}"
                cases.append({"ctor": f"{ctor}({rs}, RM_{rm}, {rd}, {op})",
                              "expected": expected, "legacy_rne": exact and rm == "RNE",
                              "op": op, "rm": rm, "rs": src, "rd": dest, "exact": exact})
    return cases


def probe_source(source, cases):
    parts = ["union fregidx = { Fregidx : bits(5) }\n",
             "union regidx = { Regidx : bits(5) }\n"]
    for name in ("rounding_mode", "f_un_rm_ff_op_D", "f_un_rm_ff_op_H",
                 "f_un_rm_xf_op_D", "f_un_rm_xf_op_S"):
        parts.append(enum_definition(source["types"], name) + "\n")
    parts.append(definition(source["fext"], "frm_mnemonic"))
    for constructor, prefix in (("Fregidx", "f"), ("Regidx", "x")):
        mapping_name = "freg_or_reg_name" if prefix == "f" else "reg_name"
        parts.append(f"mapping {mapping_name} : {'fregidx' if prefix == 'f' else 'regidx'} <-> string = {{\n")
        parts.extend(f"  {constructor}(0b{i:05b}) <-> \"{prefix}{i}\"{',' if i < 31 else ''}\n"
                     for i in range(32))
        parts.append("}\n")
    parts += ["scattered union instruction\n", "val assembly : instruction <-> string\n",
              "scattered mapping assembly\n"]
    for key, constructors in MAPPINGS.items():
        for name in constructors:
            union = block(source[key], rf"^union clause instruction = {name}\s*:[^\n]*")
            parts.append(union + "\n")
        for name in MNEMONIC_MAPPINGS[key]:
            parts.append(definition(source[key], name))
        for name in constructors:
            parts.extend(item + "\n" for item in mapping_clauses(source[key], name))
    parts += ["end instruction\n", "end assembly\n"]
    parts += ["""
function check_case(ins : instruction, expected : string, old_rne : bool) -> unit = {
  let actual : string = assembly(ins);
  assert(actual == expected, "forward assembly changed");
"""]
    parts += ["""
  print_endline("CASE\\t" ^ actual)
}
val main : unit -> unit
function main() = {
"""]
    for i, case in enumerate(cases):
        expected = case["expected"].replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'  check_case({case["ctor"]}, "{expected}", {str(case["legacy_rne"]).lower()});\n')
    parts.append("  ()\n}\n")
    return "\n".join(parts)


def command(args, cwd, log):
    result = subprocess.run([str(item) for item in args], cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_text(result.stdout)
    return result.returncode, result.stdout


def run_mode(mode, output):
    target = output / mode
    target.mkdir(parents=True, exist_ok=False)
    source = source_for(mode)
    cases = test_cases()
    (target / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    reverse_probe = target / "probe-mapping-typecheck.sail"
    reverse_probe.write_text(probe_source(source, cases))
    code, _ = command([SAIL, "--strict-var", "--strict-bitvector", "--strict-exponentials",
                       "--require-version", "0.20.1", "--memo-z3-path", target / "memo",
                       "--just-check", MODEL / "model/prelude/prelude.sail", reverse_probe],
                      target, target / "mapping-typecheck.log")
    if code:
        return {"mode": mode, "stage": "mapping-typecheck", "exit": code,
                "source_sha256": {key: hashlib.sha256(text.encode()).hexdigest() for key, text in source.items()}}
    probe = target / "probe-forward.sail"
    probe.write_text(probe_source(source, cases))
    prefix = target / "probe"
    code, _ = command([SAIL, "--strict-var", "--strict-bitvector", "--strict-exponentials",
                       "--require-version", "0.20.1", "--memo-z3-path", target / "memo",
                       "-c", "-o", prefix, MODEL / "model/prelude/prelude.sail", probe],
                      target, target / "sail.log")
    if code:
        return {"mode": mode, "stage": "sail", "exit": code, "source_sha256": {key: hashlib.sha256(text.encode()).hexdigest() for key, text in source.items()}}
    sail_lib = Path(subprocess.check_output([str(SAIL), "--dir"], text=True).strip()) / "lib"
    code, _ = command(["cc", "-O1", "-I", sail_lib, prefix.with_suffix(".c"),
                       *(sail_lib / name for name in ("sail.c", "sail_failure.c", "rts.c", "elf.c", "sail_config.c", "cJSON.c")),
                       "-lgmp", "-lz", "-o", prefix], target, target / "cc.log")
    if code:
        return {"mode": mode, "stage": "cc", "exit": code}
    code, text = command([prefix], target, target / "run.log")
    printed = [line for line in text.splitlines() if line.startswith("CASE\t")]
    if mode == "current":
        assert code == 0, (mode, code, text[-1000:])
        assert len(printed) == len(cases), (len(printed), len(cases))
        for line, case in zip(printed, cases):
            actual = line.split("\t", 1)[1]
            assert actual == case["expected"]
    else:
        assert code != 0 and len(printed) == 0, "baseline should fail at first exact RNE case"
    return {"mode": mode, "stage": "run", "exit": code, "cases": len(cases),
            "passed_cases": len(printed), "probe_sha256": sha(probe),
            "mapping_typecheck_probe_sha256": sha(reverse_probe),
            "mapping_typecheck_log_sha256": sha(target / "mapping-typecheck.log"),
            "log_sha256": sha(target / "run.log"),
            "source_sha256": {key: hashlib.sha256(body.encode()).hexdigest() for key, body in source.items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    rows = [run_mode(mode, output) for mode in ("baseline", "current")]
    (output / "result.json").write_text(json.dumps(rows, indent=2) + "\n")
    if rows[0]["stage"] != "run" or rows[1]["stage"] != "run" or rows[1]["exit"] != 0:
        raise SystemExit(1)
    print(f"baseline red, current {rows[1]['passed_cases']} forward cases passed")


if __name__ == "__main__":
    main()
