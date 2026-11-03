#!/usr/bin/env python3
"""Prove the six narrow adapter return pairs for every 32-bit candidate and flag."""

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / ".worktree/runner-float/sail-riscv/model/extensions/V/vext_fp_utils_insts.sail"
Z3 = ROOT / ".tmp/z3-official-20261102/install/bin/z3"
NAMES = {
    "f16ToI16": (16, True),
    "f16ToI8": (8, True),
    "f32ToI16": (16, True),
    "f16ToUi16": (16, False),
    "f16ToUi8": (8, False),
    "f32ToUi16": (16, False),
}


def bv(value, width):
    return f"(_ bv{value} {width})"


def query(name, width, signed):
    low = f"((_ extract {width - 1} 0) sig32)"
    nv = bv(16, 5)
    if signed:
        sign = "(= ((_ extract 31 31) sig32) #b1)"
        overflow = f"(not (= sig32 ((_ sign_extend {32 - width}) {low})))"
        minimum = bv(1 << (width - 1), width)
        maximum = bv((1 << (width - 1)) - 1, width)
        old_value = f"(ite ov (ite neg {minimum} {maximum}) {low})"
        ordinary_value = f"(ite above {maximum} (ite below {minimum} {low}))"
        definitions = [
            f"(define-fun neg () Bool {sign})",
            f"(define-fun ov () Bool {overflow})",
            f"(define-fun above () Bool (bvsgt sig32 {bv((1 << (width - 1)) - 1, 32)}))",
            f"(define-fun below () Bool (bvslt sig32 {bv((1 << 32) - (1 << (width - 1)), 32)}))",
        ]
        witnesses = {
            "positive_overflow": f"(and ov (not neg) (= sig32 {bv(1 << (width - 1), 32)}))",
            "negative_overflow": f"(and ov neg (= sig32 {bv((1 << 32) - (1 << (width - 1)) - 1, 32)}))",
            "positive_boundary": f"(and (not ov) (= sig32 {bv((1 << (width - 1)) - 1, 32)}))",
            "negative_boundary": f"(and (not ov) (= sig32 {bv((1 << 32) - (1 << (width - 1)), 32)}))",
        }
    else:
        overflow = f"(not (= ((_ extract 31 {width}) sig32) {bv(0, 32 - width)}))"
        maximum = bv((1 << width) - 1, width)
        old_value = f"(ite ov {maximum} {low})"
        ordinary_value = f"(ite above {maximum} {low})"
        definitions = [
            f"(define-fun ov () Bool {overflow})",
            f"(define-fun above () Bool (bvugt sig32 {bv((1 << width) - 1, 32)}))",
        ]
        witnesses = {
            "positive_overflow": f"(and ov (= sig32 {bv(1 << width, 32)}))",
            "upper_boundary": f"(and (not ov) (= sig32 {bv((1 << width) - 1, 32)}))",
            "zero": f"(and (not ov) (= sig32 {bv(0, 32)}))",
        }

    # The old source constructs two independent ITEs. The new source returns
    # the two values together from an explicit branch. The ordinary helper's
    # upper/lower bound comparisons give an independent semantic specification.
    old_flag = f"(ite ov {nv} flags)"
    ordinary_flag = f"(ite {('(or above below)' if signed else 'above')} {nv} flags)"
    old_pair = f"(concat {old_flag} {old_value})"
    if signed:
        saturated = f"(ite neg {minimum} {maximum})"
    else:
        saturated = maximum
    new_pair = f"(ite ov (concat {nv} {saturated}) (concat flags {low}))"
    ordinary_pair = f"(concat {ordinary_flag} {ordinary_value})"
    header = [
        "(set-logic QF_BV)",
        "(declare-fun sig32 () (_ BitVec 32))",
        "(declare-fun flags () (_ BitVec 5))",
        *definitions,
    ]
    checks = {
        "old_vs_new": (f"(not (= {old_pair} {new_pair}))", "unsat"),
        "new_vs_ordinary": (f"(not (= {new_pair} {ordinary_pair}))", "unsat"),
        **{key: (condition, "sat") for key, condition in witnesses.items()},
    }
    lines = header[:]
    for key, (assertion, _) in checks.items():
        lines += [f"; {key}", "(push 1)", f"(assert {assertion})", "(check-sat)", "(pop 1)"]
    path = OUT / f"{name}.smt2"
    path.write_text("\n".join(lines) + "\n")
    result = subprocess.run([str(Z3), "-smt2", str(path)], text=True, capture_output=True, check=True)
    observed = result.stdout.splitlines()
    expected = [want for _, want in checks.values()]
    if observed != expected:
        raise RuntimeError(f"{name}: expected {expected}, got {observed}: {result.stderr}")
    return dict(name=name, width=width, signed=signed, checks=dict(zip(checks, observed)), smt2_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    rows = [query(name, width, signed) for name, (width, signed) in NAMES.items()]
    report = {
        "source_commit": "6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "z3_version": subprocess.check_output([str(Z3), "-version"], text=True).strip(),
        "scope": "All 2^32 candidate sig32 values and all 2^5 incoming flag values per adapter. Upstream FP-to-I32/Ui32 behavior is outside this proof.",
        "rows": rows,
    }
    (OUT / "equivalence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{sum(len(row['checks']) for row in rows)} Z3 checks passed across {len(rows)} adapters")


if __name__ == "__main__":
    main()
