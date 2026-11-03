#!/usr/bin/env python3
"""Assemble strings emitted by the isolated real Sail mappings."""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe-final/current"
EXACT_WORD_RNE_F0_F1 = {
    "FCVT_D_S": 0x42008053,
    "FCVT_D_H": 0x42208053,
    "FCVT_S_H": 0x40208053,
    "FCVT_D_W": 0xD2008053,
    "FCVT_D_WU": 0xD2108053,
}
CONTROLS = {"FCVT_D_L", "FCVT_D_LU", "FCVT_S_W"}
RM_BITS = {"RNE": 0, "RTZ": 1, "RDN": 2, "RUP": 3, "RMM": 4, "DYN": 7}
COMPILERS = {
    "gcc": ["riscv64-unknown-elf-gcc", "-march=rv64gcv_zfh", "-mabi=lp64d"],
    "clang": ["clang", "--target=riscv64-unknown-elf", "-march=rv64gcv_zfh", "-mabi=lp64d"],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_one(driver, text, folder):
    obj = folder / "one.o"
    command = [*COMPILERS[driver], "-c", "-x", "assembler", "-", "-o", str(obj)]
    result = subprocess.run(command, input=".text\n.option norelax\n" + text + "\n",
                            text=True, capture_output=True)
    bits = None
    if result.returncode == 0:
        raw = folder / "one.bin"
        copied = subprocess.run(["riscv64-unknown-elf-objcopy", "-O", "binary", "-j", ".text",
                                 str(obj), str(raw)], text=True, capture_output=True)
        assert copied.returncode == 0, copied.stderr
        payload = raw.read_bytes()
        assert len(payload) == 4, (driver, text, payload.hex())
        bits = int.from_bytes(payload, "little")
    return {"exit": result.returncode, "word": hex(bits) if bits is not None else None,
            "stderr": result.stderr, "command": [*COMPILERS[driver], "-c", "-x", "assembler", "-"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cases = json.loads((PROBE / "cases.json").read_text())
    emitted = [line.split("\t", 1)[1] for line in (PROBE / "run.log").read_text().splitlines()
               if line.startswith("CASE\t")]
    assert len(cases) == len(emitted) == 1104
    chosen = {}
    for case, text in zip(cases, emitted):
        assert text == case["expected"]
        if case["op"] in EXACT_WORD_RNE_F0_F1 or case["op"] in CONTROLS:
            chosen.setdefault((case["op"], case["rm"]), (case, text))
    assert len(chosen) == (5 + 3) * 6
    rows = []
    with tempfile.TemporaryDirectory(dir=output) as temp:
        folder = Path(temp)
        for (op, rm), (case, text) in chosen.items():
            expected = None
            if op in EXACT_WORD_RNE_F0_F1:
                expected = (EXACT_WORD_RNE_F0_F1[op] & ~((31 << 15) | (7 << 12) | (31 << 7)))
                expected |= case["rs"] << 15 | RM_BITS[rm] << 12 | case["rd"] << 7
            gcc = compile_one("gcc", text, folder)
            clang = compile_one("clang", text, folder)
            substitute = None
            if op in EXACT_WORD_RNE_F0_F1 and rm != "RNE":
                substitute = compile_one("gcc", f".insn 4, 0x{expected:08x}", folder)
                assert gcc["exit"] != 0 and gcc["word"] is None, (op, rm, gcc)
                assert substitute["exit"] == 0 and int(substitute["word"], 16) == expected
            else:
                assert gcc["exit"] == 0, (op, rm, gcc)
            assert clang["exit"] == 0, (op, rm, clang)
            if expected is not None:
                assert int(clang["word"], 16) == expected, (op, rm, clang, hex(expected))
                if rm == "RNE":
                    assert int(gcc["word"], 16) == expected
                    assert text.count(",") == 1
            else:
                assert gcc["word"] == clang["word"] and text.count(",") == 2
            rows.append({"op": op, "rm": rm, "sail_text": text, "source_rs": case["rs"],
                         "destination_rd": case["rd"], "expected_word": hex(expected) if expected is not None else gcc["word"],
                         "gcc": gcc, "clang": clang, "gcc_exact_substitute": substitute})
    record = {"scope": "48 actual Sail forward strings: five exact operations and three rounding controls, six RM values each",
              "probe_cases_sha256": sha(PROBE / "cases.json"), "probe_run_sha256": sha(PROBE / "run.log"),
              "tool_versions": {name: subprocess.check_output([cmd[0], "--version"], text=True).splitlines()[0]
                                for name, cmd in COMPILERS.items()},
              "rows": rows, "passed": len(rows)}
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"{len(rows)} actual Sail strings checked with GCC, Clang, and exact .insn substitution")


if __name__ == "__main__":
    main()
