"""Pure category/flag equivalence for the unimplemented 33-cause candidate."""

from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
BASE = (ROOT / ".worktree/sail-riscv-general-float-by-model-20261022/model/core/ieee_fp_exceptions.sail").read_text()
CAND = (HERE / "candidate-ieee_fp_exceptions.sail").read_text()
assert sha256(BASE.encode()).hexdigest() == "866f85a607b112d57a0ea8c6d9a85c1befb36ef11ea39b7058a252606df257cd"


def function(source, name):
    start = source.index("function " + name + "(")
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def operand(name):
    return {"sign": name.startswith("-"), "zero": name.endswith("zero"),
            "inf": name.endswith("inf"), "nan": name.endswith("nan") or name.endswith("snan"),
            "snan": name.endswith("snan"),
            "finite": not (name.endswith("inf") or name.endswith("nan") or name.endswith("snan"))}


categories = [operand(sign + kind) for sign in ("+", "-")
              for kind in ("zero", "normal", "subnormal", "inf", "qnan", "snan")]


def facts(op, a, b, c, rounded):
    invalid_nan = any(v["snan"] for v in (a, b, c) if v is not None)
    if op in ("add", "sub"):
        causes = (a["inf"] and b["inf"] and (a["sign"] != b["sign"] if op == "add" else a["sign"] == b["sign"]),)
        divide = False
        valid = a["finite"] and b["finite"]
    elif op == "mul":
        causes = (a["zero"] and b["inf"], a["inf"] and b["zero"])
        divide = False
        valid = a["finite"] and b["finite"]
    elif op == "div":
        causes = (a["zero"] and b["zero"], a["inf"] and b["inf"])
        divide = a["finite"] and not a["zero"] and b["zero"]
        valid = a["finite"] and b["finite"] and not b["zero"]
    elif op == "sqrt":
        negative_nonzero = a["sign"] and not a["zero"]
        causes = (not a["nan"] and negative_nonzero,)
        divide = False
        valid = (a["finite"] and not negative_nonzero) or a["zero"]
    else:
        assert op == "fma"
        product_inf = ((a["inf"] and not b["nan"] and not b["zero"])
                       or (b["inf"] and not a["nan"] and not a["zero"]))
        cancel = product_inf and c["inf"] and (a["sign"] != b["sign"]) != c["sign"]
        causes = (a["zero"] and b["inf"], a["inf"] and b["zero"], cancel)
        divide = False
        valid = a["finite"] and b["finite"] and c["finite"]
    old = (True, False, False, False, False) if any(causes) else (
        (False, True, False, False, False) if divide else
        (invalid_nan, False, *rounded) if valid else (invalid_nan, False, False, False, False)
    )
    new_invalid = invalid_nan or any(causes)
    new = (new_invalid, divide, *(rounded if valid else (False, False, False)))
    return old, new


results = {}
cause_if_reduction = 0
expected_cause_ifs = {"add": 1, "sub": 1, "mul": 2, "div": 3, "sqrt": 1, "fma": 3}
for width in (16, 32, 64):
    for op in ("add", "sub", "mul", "div", "sqrt", "fma"):
        name = f"ieee_{op}{width}_exceptions"
        original = function(BASE, name)
        proposed = function(CAND, name)
        # Directed-bound and native FP computation lines are unchanged,
        # including the fused FMA operation and its number of calls.
        fp_lines = lambda body: [line.strip() for line in body.splitlines()
                                 if re.match(r"\s*let (?:x|y|z|lo|hi|rounded) = ", line)]
        assert fp_lines(original) == fp_lines(proposed), name
        assert original.count("let invalid_nan = ") == proposed.count("let invalid_nan = ")
        assert proposed.count("if valid then {") + proposed.count("if finite then {") == 1
        assert proposed.count("if invalid_") == 0 and proposed.count("if divide_by_zero") == 0
        removed = len(re.findall(r"\bif ", original)) - len(re.findall(r"\bif ", proposed))
        assert removed == expected_cause_ifs[op], (name, removed)
        cause_if_reduction += removed
        if op == "fma":
            assert original.count("fp32_fma(") == proposed.count("fp32_fma(")
            assert original.count("fp64_fma(") == proposed.count("fp64_fma(")
            assert original.count("fp128_fma(") == proposed.count("fp128_fma(")
        groups = [categories] * (3 if op == "fma" else 1 if op == "sqrt" else 2)
        count = 0
        for operands in product(*groups):
            a = operands[0]
            b = operands[1] if len(operands) > 1 else None
            c = operands[2] if len(operands) > 2 else None
            for rounded in product((False, True), repeat=3):
                old, new = facts(op, a, b, c, rounded)
                assert old == new, (name, operands, rounded, old, new)
                count += 1
        results[name] = count

assert cause_if_reduction == 33
out = {"scope": "read-only candidate; not a production implementation or dynamic result",
       "baseline_sha256": sha256(BASE.encode()).hexdigest(),
       "candidate_sha256": sha256(CAND.encode()).hexdigest(),
       "cause_ifs_reverted": cause_if_reduction, "functions": len(results),
       "category_flag_cases": sum(results.values()), "per_function_cases": results,
       "native_fp_and_directed_bound_lines_identical": True}
(HERE / "exceptions-source-audit.json").write_text(json.dumps(out, indent=2) + "\n")
print({key: out[key] for key in ("candidate_sha256", "functions", "category_flag_cases")})
