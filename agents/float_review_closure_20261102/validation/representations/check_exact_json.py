"""Validate JSON representations and select exact GNU fallback for five FP conversions.

The generic checker still assembles all six driver/form combinations. This
consumer records its original failures, then selects its already assembled
`.insn` plus byte form only for the five exact conversions with raw RM != 0.
"""

import importlib.util
import json
from pathlib import Path
import re

from common import ROOT, dump, sha

GENERIC = ROOT / "agents/float_review_completion_20261102/assembly/check_json.py"
spec = importlib.util.spec_from_file_location("generic_check_json_for_exact", GENERIC)
generic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generic)
DRIVERS = generic.DRIVERS

# Keys are the actual funct7 and rs2 fields, not text prefixes. Other FCVTs
# have different rounding semantics and must retain the ordinary check.
EXACT = {
    (0x21, 0): "fcvt.d.s",
    (0x21, 2): "fcvt.d.h",
    (0x20, 2): "fcvt.s.h",
    (0x69, 0): "fcvt.d.w",
    (0x69, 1): "fcvt.d.wu",
}
NEGATIVE = {
    (0x69, 2): "fcvt.d.l",
    (0x69, 3): "fcvt.d.lu",
    (0x68, 0): "fcvt.s.w",
}
ROUND = {0: "rne", 1: "rtz", 2: "rdn", 3: "rup", 4: "rmm", 7: "dyn"}


def decoded(item):
    encoded = item["test-ins-encdec"]
    match = re.fullmatch(r"32'h([0-9a-fA-F_]{8,})", encoded)
    if not match:
        return None
    word = int(match[1].replace("_", ""), 16)
    if word & 0x7f != 0x53:
        return None
    key = ((word >> 25) & 0x7f, (word >> 20) & 0x1f)
    if key not in EXACT and key not in NEGATIVE:
        return None
    return {"word": word, "rm": (word >> 12) & 7, "key": key,
            "op": EXACT.get(key, NEGATIVE.get(key)), "exact": key in EXACT}


def evaluate(data, raw):
    checks = {(row["index"], row["driver"], row["kind"]): row for row in raw["checks"]}
    expected_keys = {(index, driver, kind) for index in range(len(data["gen"]))
                     for driver in DRIVERS for kind in ("mnemonic", "insn", "binary")}
    if set(checks) != expected_keys:
        raise ValueError("generic assembler check matrix is incomplete")
    selected = []
    errors = []
    accepted = set()
    for index, item in enumerate(data["gen"]):
        op = decoded(item)
        if op is None:
            continue
        name = op["op"]
        rm = op["rm"]
        text = item["instruction-representations"]["mnemonic"]
        parts = [part.strip() for part in text.split(",")]
        if not parts[0].startswith(name + " ") or rm not in ROUND:
            errors.append({"index": index, "reason": "opcode or RM text mismatch", "word": hex(op["word"]), "text": text})
            continue
        if op["exact"] and rm == 0:
            # The new Sail mapping must print the portable two-operand form.
            if len(parts) != 2:
                errors.append({"index": index, "reason": "exact RM0 must omit RM", "text": text})
            for driver in DRIVERS:
                mnemonic = checks[index, driver, "mnemonic"]
                if not mnemonic["pass_"] or mnemonic["actual"] != mnemonic["expected"]:
                    errors.append({"index": index, "reason": driver + " exact RM0 mnemonic failed", "text": text})
                selected.append({"index": index, "op": name, "raw_rm": rm, "driver": driver,
                                 "form": "mnemonic", "expected_bytes": mnemonic["expected"],
                                 "actual_bytes": mnemonic["actual"]})
        else:
            # All nonzero RMs, and the inexact negative controls including
            # RM0, must retain an explicit round-mode operand.
            if len(parts) != 3 or parts[-1] != ROUND[rm]:
                errors.append({"index": index, "reason": "explicit RM lost", "text": text, "raw_rm": rm})
            clang = checks[index, "clang", "mnemonic"]
            if not clang["pass_"] or clang["actual"] != clang["expected"]:
                errors.append({"index": index, "reason": "Clang mnemonic does not preserve exact bytes", "text": text})
            if not op["exact"]:
                gcc = checks[index, "gcc", "mnemonic"]
                if not gcc["pass_"] or gcc["actual"] != gcc["expected"]:
                    errors.append({"index": index, "reason": "negative-control GNU mnemonic failed", "text": text})
                continue
            gcc = checks[index, "gcc", "mnemonic"]
            if gcc["pass_"] and gcc["actual"] == gcc["expected"]:
                selected.append({"index": index, "op": name, "raw_rm": rm, "driver": "gcc",
                                 "form": "mnemonic", "expected_bytes": gcc["expected"],
                                 "actual_bytes": gcc["actual"]})
                continue
            insn = checks[index, "gcc", "insn"]
            byte = checks[index, "gcc", "binary"]
            if not all(row["pass_"] and row["exit"] == 0 and row["actual"] == gcc["expected"]
                       for row in (insn, byte)):
                errors.append({"index": index, "reason": "GNU exact fallback did not assemble original bytes", "text": text})
                continue
            if not insn["text"].startswith(".insn 4, ") or not byte["text"].startswith(".byte "):
                errors.append({"index": index, "reason": "GNU exact fallback source is not .insn/.byte", "text": text})
                continue
            accepted.add((index, "gcc", "mnemonic"))
            selected.append({"index": index, "op": name, "word": hex(op["word"]), "raw_rm": rm,
                             "driver": "gcc", "form": "insn", "mnemonic_exit": gcc["exit"],
                             "mnemonic_text": text, "insn_text": insn["text"],
                             "insn_command": insn["command"], "byte_command": byte["command"],
                             "expected_bytes": gcc["expected"], "insn_actual_bytes": insn["actual"],
                             "byte_actual_bytes": byte["actual"]})
    effective_failures = [row for row in raw["checks"] if not row["pass_"]
                          and (row["index"], row["driver"], row["kind"]) not in accepted]
    return {"source": raw["source"], "source_sha256": raw["sha256"], "gen": raw["gen"],
            "generic_checker_sha256": sha(GENERIC), "raw_all_pass": raw["all_pass"],
            "raw_failures": sum(not row["pass_"] for row in raw["checks"]),
            "accepted_gnu_exact_fallbacks": len(accepted), "selected": selected,
            "contract_errors": errors, "unhandled_failures": effective_failures,
            "all_pass": not errors and not effective_failures}


def check(path, out, simulation=False):
    try:
        generic.check(path, out, simulation=simulation)
    except AssertionError:
        if not (out / "results.json").exists():
            raise
    raw = json.loads((out / "results.json").read_text())
    if raw["all_pass"] and "VFWMACCBF16" in path.name and (raw["illegal"] == 0 or raw["clang_mnemonic_rejections"] == 0):
        raise AssertionError("BF16 illegal-layout rejection contract failed")
    data = json.loads(path.read_text())
    result = evaluate(data, raw)
    dump(out / "selection.json", result)
    if not result["all_pass"]:
        raise AssertionError(out / "selection.json")
    return {key: result[key] for key in ("source_sha256", "gen", "raw_all_pass",
                                         "raw_failures", "accepted_gnu_exact_fallbacks", "all_pass")}
