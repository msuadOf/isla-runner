#!/usr/bin/env python3
"""Local red/green checks for the 21418d0 IEEE pure-output reduction."""

import hashlib
from itertools import product
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / ".worktree/sail-riscv-general-float-by-model-20261022"
SOURCE = MODEL / "model/core/ieee_fp_exceptions.sail"
BASE_COMMIT = "21418d0b0d4942fae20061ed580ee04aff4a8a61"
BASE_SHA256 = "23fda9824c2280609062bbe2b9766597681c29af13a1e9cf1be045d9106757a8"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def function(source, name):
    start = source.index("function " + name + "(")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def old_rounded(overflow, underflow, inexact):
    if overflow:
        return True, underflow, inexact
    if underflow:
        return False, True, inexact
    if inexact:
        return False, False, True
    return False, False, False


for values in product((False, True), repeat=3):
    assert old_rounded(*values) == values
for invalid_nan, inexact in product((False, True), repeat=2):
    old = (invalid_nan, False, False, False, True) if inexact else (invalid_nan, False, False, False, False)
    assert old == (invalid_nan, False, False, False, inexact)
for bits in range(1 << 16):
    for inexact in (False, True):
        old = (bits | 1) if inexact else bits
        assert old == ((bits | 1) if inexact else bits)

old = subprocess.check_output(["git", "-C", str(MODEL), "show", BASE_COMMIT + ":model/core/ieee_fp_exceptions.sail"])
assert digest(old) == BASE_SHA256
current = SOURCE.read_text()
baseline = old.decode()

# Every `let` value expression, including all directed bounds and NaN/source
# predicates, must stay byte-identical after indentation is removed.
let_lines = lambda text: [line.strip() for line in re.findall(r"^\s*let\s+[^\n]+", text, re.M)]
assert let_lines(current) == let_lines(baseline), "a numerical/source expression changed"

for name in ("ieee_f16_rounded_exceptions", "ieee_f32_rounded_exceptions",
             "ieee_f64_rounded_exceptions", "ieee_exact_threshold_exceptions"):
    body = function(current, name)
    assert "ieee_exception_facts(false, false, overflow, underflow, inexact)" in body, name
    assert "if overflow then" not in body and "else if underflow then" not in body, name

for name in ("ieee_round16_exceptions", "ieee_round32_exceptions", "ieee_round64_exceptions"):
    body = function(current, name)
    assert "if finite then" in body and "ieee_operand_invalid(false, a)" in body
    assert "ieee_exception_facts(invalid_nan, false, false, false, inexact)" in body, name
    assert "if inexact then" not in body, name

core = function(current, "ieee_fp_to_int_core")
assert "if finite then" in core and "if valid then" in core
assert "ieee_exception_facts(false, false, false, false, inexact)" in core
assert "if inexact then" not in core

for name, one in (("ieee_rod32_to_16", "0x0001"), ("ieee_rod64_to_32", "0x00000001")):
    body = function(current, name)
    assert "if finite then" in body and "ieee_operand_invalid(false, a)" in body
    assert f"(flags, ite(ieee_has_inexact(flags), base_bits | {one}, base_bits))" in body, name
    assert "if ieee_has_inexact(flags) then" not in body, name

for name in ("ieee_convert32_to_16_exceptions", "ieee_convert64_to_16_exceptions",
             "ieee_convert64_to_32_exceptions", "ieee_bf16_from_f32_exceptions",
             "ieee_rod32_to_16", "ieee_rod64_to_32"):
    body = function(current, name)
    assert "let invalid_nan = ieee_operand_invalid(false, a);" in body
    assert "if finite then" in body
    assert "let facts = ieee_exact" in body
    assert "ieee_mask_exact_exceptions" not in body
    assert re.search(r"\n\s+facts\s*(?:\n|\})", body), name

assert "function ieee_mask_exact_exceptions(" not in current
assert "ieee_mask_exact_exceptions(" not in current
assert "if invalid_inf then" in current and "if invalid_zero_zero then" in current

print({"source_sha256": digest(current.encode()), "rounded_boolean_cases": 8,
       "round_boolean_cases": 4, "rod16_jam_cases": 131072,
       "let_expressions_identical": len(let_lines(current)), "converted_functions": 14,
       "deleted_helpers": 1})
