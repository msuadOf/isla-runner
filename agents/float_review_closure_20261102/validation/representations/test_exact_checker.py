"""Static checker red/green probes; no final-IR execution."""

import json
from pathlib import Path

from check_exact_json import EXACT, NEGATIVE, decoded, evaluate
from common import ROOT


def row(index, driver, kind, expected, actual, passed, text):
    return {"index": index, "driver": driver, "kind": kind, "expected": expected,
            "actual": actual, "exit": 0 if passed else 1, "pass_": passed,
            "text": text, "command": ["assembler", text]}


def matrix(word, text, gcc_mnemonic=False):
    expected = word.to_bytes(4, "little").hex()
    source = {"test-ins-encdec": f"32'h{word:08x}",
              "instruction-representations": {"mnemonic": text}}
    checks = []
    for driver in ("gcc", "clang"):
        checks.append(row(0, driver, "mnemonic", expected,
                          expected if driver == "clang" or gcc_mnemonic else None,
                          driver == "clang" or gcc_mnemonic, text))
        checks.append(row(0, driver, "insn", expected, expected, True, f".insn 4, 0x{word:08x}"))
        checks.append(row(0, driver, "binary", expected, expected, True, ".byte ..."))
    return {"gen": [source]}, {"source": "synthetic", "sha256": "synthetic",
                             "gen": 1, "checks": checks, "all_pass": gcc_mnemonic}


probe = json.loads((ROOT / "agents/float_review_closure_20261102/review/acceptance/exact-conversion-syntax-independent.json").read_text())
seen = set()
for item in probe["rows"]:
    if item["bytes_le"] is None:
        continue
    word = int.from_bytes(bytes.fromhex(item["bytes_le"]), "little")
    classified = decoded({"test-ins-encdec": f"32'h{word:08x}"})
    assert classified is not None
    assert classified["op"] == item["op"]
    assert classified["exact"] is item["exact"]
    seen.add(item["op"])
assert seen == set(EXACT.values()) | set(NEGATIVE.values())

# A nonzero exact conversion can use actual GNU .insn/.byte output while the
# original GNU mnemonic failure remains visible in the raw record.
data, raw = matrix(0x42002053, "fcvt.d.s f0, f0, rdn")
green = evaluate(data, raw)
assert green["all_pass"] and green["accepted_gnu_exact_fallbacks"] == 1
assert green["raw_failures"] == 1 and green["selected"][-1]["form"] == "insn"

broken = json.loads(json.dumps(raw))
next(item for item in broken["checks"] if item["driver"] == "gcc" and item["kind"] == "insn")["actual"] = "00000000"
assert not evaluate(data, broken)["all_pass"]

broken = json.loads(json.dumps(raw))
next(item for item in broken["checks"] if item["driver"] == "clang" and item["kind"] == "mnemonic")["pass_"] = False
assert not evaluate(data, broken)["all_pass"]

# RM0 must use the canonical two-operand spelling on both toolchains.
data, raw = matrix(0x42000053, "fcvt.d.s f0, f0, rne", gcc_mnemonic=True)
assert not evaluate(data, raw)["all_pass"]
data, raw = matrix(0x42000053, "fcvt.d.s f0, f0", gcc_mnemonic=True)
assert evaluate(data, raw)["all_pass"]

# The inexact controls must keep the RM parameter and get no GNU fallback.
for word, text in ((0xd2202053, "fcvt.d.l f0, x0, rdn"),
                   (0xd2302053, "fcvt.d.lu f0, x0, rdn"),
                   (0xd0002053, "fcvt.s.w f0, x0, rdn")):
    data, raw = matrix(word, text)
    result = evaluate(data, raw)
    assert not result["all_pass"] and result["accepted_gnu_exact_fallbacks"] == 0, text

round_modes = {0: "rne", 1: "rtz", 2: "rdn", 3: "rup", 4: "rmm", 7: "dyn"}
exact_cases = 0
negative_cases = 0
for table, exact in ((EXACT, True), (NEGATIVE, False)):
    for (funct7, rs2), op in table.items():
        source = "x1" if op in ("fcvt.d.w", "fcvt.d.wu", "fcvt.d.l", "fcvt.d.lu", "fcvt.s.w") else "f1"
        for rm, suffix in round_modes.items():
            word = (funct7 << 25) | (rs2 << 20) | (1 << 15) | (rm << 12) | 0x53
            text = f"{op} f0, {source}"
            if rm or not exact:
                text += ", " + suffix
            data, raw = matrix(word, text, gcc_mnemonic=rm == 0 or not exact)
            result = evaluate(data, raw)
            assert result["all_pass"], (op, rm, result)
            assert result["accepted_gnu_exact_fallbacks"] == int(exact and rm != 0)
            if exact:
                exact_cases += 1
            else:
                negative_cases += 1

print({"syntax_probe_rows": len(probe["rows"]), "classified_operations": sorted(seen),
       "exact_mode_cases": exact_cases, "negative_mode_cases": negative_cases,
       "fallback_positive": 1, "negative_controls": 3, "red_cases": 4})
