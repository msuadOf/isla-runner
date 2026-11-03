#!/usr/bin/env python3
"""Stage the 12 FP-to-integer ITE selections without editing production trees."""

import difflib
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REPO = ROOT / "sail-riscv"
CURRENT = "e9d69d2f28586c089244c8e37ee4c904c5114458"
BASELINE = "6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a"
KINDS = ("I32", "Ui32", "I64", "Ui64")
LIMITS = {
    "I32": (0x7FFFFFFF, 0x80000000),
    "Ui32": (0xFFFFFFFF, 0x00000000),
    "I64": (0x7FFFFFFFFFFFFFFF, 0x8000000000000000),
    "Ui64": (0xFFFFFFFFFFFFFFFF, 0x0000000000000000),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source(commit, path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{commit}:{path}"])


def function(text, name):
    pattern = rf"^function {name}\([^\n]+ = \{{.*?^\}}"
    found = re.search(pattern, text, re.M | re.S)
    assert found is not None, name
    return found.group(0)


assert subprocess.check_output(["git", "-C", str(REPO), "rev-parse", CURRENT], text=True).strip() == CURRENT
assert subprocess.check_output(["git", "-C", str(REPO), "rev-parse", BASELINE], text=True).strip() == BASELINE
audit = {"candidate_base_commit": CURRENT, "selection_source_commit": BASELINE,
         "scope": "12 FP-to-integer wrapper result selections only; ROD mode guards unchanged",
         "files": [], "functions": [], "rod_mode_functions_unchanged": [], "truth_table_cases": 0}
patch_parts = []
for fmt in (16, 32, 64):
    path = f"model/extensions/FD/softfloat_symbolic_f{fmt}.sail"
    original_bytes = source(CURRENT, path)
    baseline_bytes = source(BASELINE, path)
    original = original_bytes.decode()
    baseline = baseline_bytes.decode()
    candidate = original
    reverse = []
    for kind in KINDS:
        name = f"riscv_f{fmt}To{kind}"
        before = function(original, name)
        after = function(baseline, name)
        old_lines, new_lines = after.splitlines(), before.splitlines()
        assert old_lines[:5] == new_lines[:5], (name, "FP rounding/facts/candidate changed")
        assert old_lines[-1] == new_lines[-1] == "}"
        assert len(old_lines) == 9 and len(new_lines) == 12, name
        assert ("ite(ieee_has_invalid(" in after and
                ("ite(ieee_is_nan(a)," in after or
                 (fmt == 64 and "strict_or_bool(ieee_is_nan(a)," in after))), name
        assert "let result = if ieee_has_invalid(" in before
        assert "if ieee_is_nan(a) then" in before
        assert f"eq_anything(a[{fmt - 1}], 0b1)" in before
        assert candidate.count(before) == 1, name
        candidate = candidate.replace(before, after, 1)
        reverse.append((after, before))
        positive, negative = LIMITS[kind]
        for invalid, nan, sign, value, flags in itertools.product(
            (False, True), (False, True), (False, True), (0, 1, positive, negative), range(32)
        ):
            baseline_result = (positive if nan or not sign else negative) if invalid else value
            current_result = (positive if nan else negative if sign else positive) if invalid else value
            assert (baseline_result, flags) == (current_result, flags), name
            audit["truth_table_cases"] += 1
        audit["functions"].append({"name": name, "format": f"f{fmt}",
                                   "baseline_function_sha256": sha(after.encode()),
                                   "current_function_sha256": sha(before.encode()),
                                   "positive_invalid": hex(positive),
                                   "negative_invalid": hex(negative),
                                   "negative_nan_result": hex(positive),
                                   "valid_result": "unchanged candidate",
                                   "flags": "unchanged packed exceptions"})
    # Replacing the selected twelve functions back must recover every other byte.
    restored = candidate
    for after, before in reverse:
        assert restored.count(after) == 1
        restored = restored.replace(after, before, 1)
    assert restored == original, path
    if fmt in (32, 64):
        rod_name = "riscv_f32ToF16" if fmt == 32 else "riscv_f64ToF32"
        rod_body = function(original, rod_name)
        assert function(candidate, rod_name) == rod_body
        audit["rod_mode_functions_unchanged"].append({"name": rod_name,
                                                        "sha256": sha(rod_body.encode())})
    candidate_bytes = candidate.encode()
    filename = f"wrappers-softfloat_symbolic_f{fmt}.sail"
    (HERE / filename).write_bytes(candidate_bytes)
    patch_parts.append("".join(difflib.unified_diff(
        original.splitlines(True), candidate.splitlines(True),
        fromfile=f"a/{path}", tofile=f"b/{path}")))
    audit["files"].append({"source_path": path, "candidate_path": filename,
                           "current_sha256": sha(original_bytes),
                           "baseline_sha256": sha(baseline_bytes),
                           "candidate_sha256": sha(candidate_bytes),
                           "non_target_bytes_equal_current": True})

assert len(audit["functions"]) == 12 and audit["truth_table_cases"] == 12288
patch = "".join(patch_parts)
assert patch.count("diff --git") == 0 and patch.count("--- a/") == 3
(HERE / "wrappers-source.diff").write_text(patch)
audit["patch_sha256"] = sha(patch.encode())
(HERE / "wrappers-audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
print(f"PASS: staged 3 files, 12 functions, {audit['truth_table_cases']} truth-table cases")
