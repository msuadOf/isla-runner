"""Construct a read-only evidence candidate; never writes a model worktree."""

from hashlib import sha256
from pathlib import Path
import difflib


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / ".worktree/sail-riscv-general-float-by-model-20261022/model/core/ieee_fp_exceptions.sail"
EXPECTED = "866f85a607b112d57a0ea8c6d9a85c1befb36ef11ea39b7058a252606df257cd"
source = SOURCE.read_text()
assert sha256(source.encode()).hexdigest() == EXPECTED
candidate = source


def function_span(text, name):
    start = text.index("function " + name + "(")
    opening = text.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return start, end


reason_counts = {"add": 1, "sub": 1, "mul": 2, "div": 3, "sqrt": 1, "fma": 3}
for width in (16, 32, 64):
    for op in reason_counts:
        name = f"ieee_{op}{width}_exceptions"
        start, end = function_span(candidate, name)
        body = candidate[start:end]
        if op in ("add", "sub"):
            first = "  if invalid_inf then\n"
            formula = "strict_or_bool(invalid_nan, invalid_inf)"
        elif op == "mul":
            first = "  if invalid_zero_inf_a then\n"
            formula = "strict_or_bool(invalid_nan, invalid_zero_inf)"
        elif op == "div":
            first = "  if invalid_zero_zero then\n"
            formula = "strict_or_bool(invalid_nan, strict_or_bool(invalid_zero_zero, invalid_inf_inf))"
        elif op == "sqrt":
            first = "  if invalid_negative then\n"
            formula = "strict_or_bool(invalid_nan, invalid_negative)"
        else:
            first = "  if invalid_zero_inf_a then\n"
            formula = "strict_or_bool(invalid_nan, strict_or_bool(invalid_zero_inf, invalid_inf_cancel))"
        gate = "finite" if op in ("add", "sub") else "valid"
        gate_start = f"  else if {gate} then {{\n"
        assert body.count(first) == 1 and body.count(gate_start) == 1, name
        prefix, cause_and_tail = body.split(first, 1)
        _, tail = cause_and_tail.split(gate_start, 1)
        assert tail.count("ieee_exception_facts(\n      invalid_nan,\n      false,") == 1, name
        dz = "divide_by_zero" if op == "div" else "false"
        tail = tail.replace(
            "ieee_exception_facts(\n      invalid_nan,\n      false,",
            f"ieee_exception_facts(\n      invalid,\n      {dz},",
            1,
        )
        assert tail.count("ieee_empty_exceptions(invalid_nan)") == 1, name
        tail = tail.replace(
            "ieee_empty_exceptions(invalid_nan)",
            f"ieee_exception_facts(invalid, {dz}, false, false, false)",
            1,
        )
        if op in ("mul", "fma"):
            split_reason = (
                "  let invalid_zero_inf_a = strict_and_bool(ieee_is_zero(a), ieee_is_inf(b));\n"
                "  let invalid_zero_inf_b = strict_and_bool(ieee_is_inf(a), ieee_is_zero(b));\n"
            )
            combined_reason = (
                "  let invalid_zero_inf = strict_or_bool(\n"
                "    strict_and_bool(ieee_is_zero(a), ieee_is_inf(b)),\n"
                "    strict_and_bool(ieee_is_inf(a), ieee_is_zero(b))\n"
                "  );\n"
            )
            assert prefix.count(split_reason) == 1, name
            prefix = prefix.replace(split_reason, combined_reason)
        replacement = prefix + f"  let invalid = {formula};\n  if {gate} then {{\n" + tail
        candidate = candidate[:start] + replacement + candidate[end:]

assert sum(reason_counts.values()) * 3 == 33
out = HERE / "candidate-ieee_fp_exceptions.sail"
out.write_text(candidate)
diff = difflib.unified_diff(source.splitlines(True), candidate.splitlines(True),
                            fromfile="e9d69d2/model/core/ieee_fp_exceptions.sail",
                            tofile="new-policy/candidate-ieee_fp_exceptions.sail")
(HERE / "exceptions-source.diff").write_text("".join(diff))
print({"baseline_sha256": EXPECTED, "candidate_sha256": sha256(candidate.encode()).hexdigest(),
       "functions": 18, "cause_ifs_reverted": 33})
