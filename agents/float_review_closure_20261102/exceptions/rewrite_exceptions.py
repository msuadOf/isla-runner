"""One-time source rewrite of IEEE exception control boundaries.

This script asserts the exact 6202e23 function shapes before modifying them.
It is kept with the source evidence so the mechanical part is reviewable.
"""

from pathlib import Path
from hashlib import sha256
import re


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / ".worktree/runner-float/sail-riscv/model/core/ieee_fp_exceptions.sail"
source = SOURCE.read_text()
assert sha256(source.encode()).hexdigest() == "fdb105f1bf911b5d13fef2bfa2ee1f46b66a4ccca3c6d878bc31063937cedbc6"


def replace_function(name, transform):
    global source
    start = source.index(f"function {name}(")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    old = source[start:end]
    new = transform(old)
    assert new != old, name
    source = source[:start] + new + source[end:]


def rounded_transform(old):
    tail = re.search(
        r"  ieee_exception_facts\(\n    false,\n    false,\n    overflow,\n"
        r"    strict_and_bool\(inexact, tiny\),\n    inexact\n  \)\n}",
        old,
    )
    assert tail, old.splitlines()[0]
    replacement = """  let underflow = strict_and_bool(inexact, tiny);
  if overflow then
    ieee_exception_facts(false, false, true, underflow, inexact)
  else if underflow then
    ieee_exception_facts(false, false, false, true, inexact)
  else if inexact then
    ieee_exception_facts(false, false, false, false, true)
  else
    ieee_empty_exceptions(false)
}"""
    return old[: tail.start()] + replacement


for name in (
    "ieee_f16_rounded_exceptions",
    "ieee_f32_rounded_exceptions",
    "ieee_f64_rounded_exceptions",
    "ieee_exact_threshold_exceptions",
):
    replace_function(name, rounded_transform)


def arithmetic_transform(old, op):
    header, body = old.split("{\n", 1)
    prefix, arithmetic = body.split("  let x = ", 1)
    prefix = "  " + prefix if not prefix.startswith("  ") else prefix
    computation, final = ("  let x = " + arithmetic).split("  let valid = " if op in ("mul", "div", "sqrt", "fma") else "  let finite = ", 1)
    valid_name = "valid" if op in ("mul", "div", "sqrt", "fma") else "finite"
    valid_expression = final.split(";\n", 1)[0]
    assert valid_expression and computation.endswith(";\n"), header
    expected_tail = final.split(";\n", 1)[1]
    assert expected_tail.startswith("  ieee_exception_facts(\n") and expected_tail.endswith("\n}"), header
    if op in ("add", "sub"):
        prefix = prefix.replace("  let invalid = strict_or_bool(invalid_nan, invalid_inf);\n", "")
        assert "  let invalid_inf = " in prefix
        reasons = "  if invalid_inf then\n    ieee_empty_exceptions(true)\n"
    elif op == "mul":
        old_reason = """  let invalid_zero_inf = strict_or_bool(
    strict_and_bool(ieee_is_zero(a), ieee_is_inf(b)),
    strict_and_bool(ieee_is_inf(a), ieee_is_zero(b))
  );
"""
        new_reason = """  let invalid_zero_inf_a = strict_and_bool(ieee_is_zero(a), ieee_is_inf(b));
  let invalid_zero_inf_b = strict_and_bool(ieee_is_inf(a), ieee_is_zero(b));
"""
        assert old_reason in prefix
        prefix = prefix.replace(old_reason, new_reason)
        reasons = """  if invalid_zero_inf_a then
    ieee_empty_exceptions(true)
  else if invalid_zero_inf_b then
    ieee_empty_exceptions(true)
"""
    elif op == "div":
        prefix = prefix.replace("  let invalid = strict_or_bool(invalid_nan, strict_or_bool(invalid_zero_zero, invalid_inf_inf));\n", "")
        assert "  let divide_by_zero = " in prefix
        reasons = """  if invalid_zero_zero then
    ieee_empty_exceptions(true)
  else if invalid_inf_inf then
    ieee_empty_exceptions(true)
  else if divide_by_zero then
    ieee_exception_facts(false, true, false, false, false)
"""
    elif op == "sqrt":
        prefix = prefix.replace("  let invalid = strict_or_bool(ieee_operand_invalid(false, a), invalid_negative);\n", "  let invalid_nan = ieee_operand_invalid(false, a);\n")
        assert "  let invalid_negative = " in prefix
        reasons = "  if invalid_negative then\n    ieee_empty_exceptions(true)\n"
    else:
        assert op == "fma"
        old_reason = """  let invalid_zero_inf = strict_or_bool(
    strict_and_bool(ieee_is_zero(a), ieee_is_inf(b)),
    strict_and_bool(ieee_is_inf(a), ieee_is_zero(b))
  );
"""
        new_reason = """  let invalid_zero_inf_a = strict_and_bool(ieee_is_zero(a), ieee_is_inf(b));
  let invalid_zero_inf_b = strict_and_bool(ieee_is_inf(a), ieee_is_zero(b));
"""
        assert old_reason in prefix
        prefix = prefix.replace(old_reason, new_reason)
        prefix = prefix.replace("  let invalid = strict_or_bool(invalid_nan, strict_or_bool(invalid_zero_inf, invalid_inf_cancel));\n", "")
        assert "  let invalid_inf_cancel = " in prefix
        reasons = """  if invalid_zero_inf_a then
    ieee_empty_exceptions(true)
  else if invalid_zero_inf_b then
    ieee_empty_exceptions(true)
  else if invalid_inf_cancel then
    ieee_empty_exceptions(true)
"""
    assert "  let invalid_nan = " in prefix
    gate = f"  let {valid_name} = {valid_expression};\n"
    finite_return = """    ieee_exception_facts(
      invalid_nan,
      false,
      ieee_has_overflow(rounded),
      ieee_has_underflow(rounded),
      ieee_has_inexact(rounded)
    )
"""
    indented_computation = "".join("  " + line for line in computation.splitlines(keepends=True))
    return (
        header + "{\n" + prefix + gate + reasons + f"  else if {valid_name} then {{\n"
        + indented_computation + finite_return + "  } else\n    ieee_empty_exceptions(invalid_nan)\n}"
    )


for width in (16, 32, 64):
    for op in ("add", "sub", "mul", "div", "sqrt", "fma"):
        replace_function(
            f"ieee_{op}{width}_exceptions",
            lambda old, op=op: arithmetic_transform(old, op),
        )


old_mask = """function ieee_mask_exact_exceptions(invalid : bool, finite : bool, rounded : ieee_fp_exceptions) -> ieee_fp_exceptions =
  ieee_exception_facts(
    invalid,
    false,
    strict_and_bool(finite, ieee_has_overflow(rounded)),
    strict_and_bool(finite, ieee_has_underflow(rounded)),
    strict_and_bool(finite, ieee_has_inexact(rounded))
  )"""
new_mask = """function ieee_mask_exact_exceptions(invalid : bool, finite : bool, rounded : ieee_fp_exceptions) -> ieee_fp_exceptions =
  if finite then
    ieee_exception_facts(
      invalid,
      false,
      ieee_has_overflow(rounded),
      ieee_has_underflow(rounded),
      ieee_has_inexact(rounded)
    )
  else
    ieee_empty_exceptions(invalid)"""
assert source.count(old_mask) == 1
source = source.replace(old_mask, new_mask)

SOURCE.write_text(source)
