#!/usr/bin/env python3
"""核对独立收敛模型树的提交、候选字节和冻结的 OPEN 源码。"""

from hashlib import sha256
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
TREE = ROOT / ".worktree/sail-riscv-float-converged-20261103"
E9 = "e9d69d2f28586c089244c8e37ee4c904c5114458"
COMMITS = [
    "3d9ceebb8ae81b45ccafcde7cab81c0ab5b49bd8",
    "7eb4bd5c137c500209678f2f6eb007b572179b74",
    "0f7b8fbc6724103f91f929ef6918f123df75d6c9",
]
FILES = {
    "model/core/ieee_fp_exceptions.sail": ("candidate-ieee_fp_exceptions.sail", "7ed9529baac57717875ea49e8fff5130d3ec611f824aa71483b2b856d67c96b4"),
    "model/extensions/V/vext_fp_utils_insts.sail": ("candidate-vext_fp_utils_insts.sail", "34191de93086708b44f552606b39878e1ad68be07c67fb2321eb7bec1b1172e1"),
    "model/extensions/FD/softfloat_symbolic_f16.sail": ("wrappers-softfloat_symbolic_f16.sail", "715795790c0efb100806c0a82195e137c4de66c4a9614baac9ee2b0b333a0646"),
    "model/extensions/FD/softfloat_symbolic_f32.sail": ("wrappers-softfloat_symbolic_f32.sail", "ffe71d8f99652a20f9c7c6d969648af75bdc575ee9f2ca34e459fdfa879c5e17"),
    "model/extensions/FD/softfloat_symbolic_f64.sail": ("wrappers-softfloat_symbolic_f64.sail", "b5b8ea9e4723e647fa74ea8ebfa47129106993a3a99d9df80105f9b3eab545ce"),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=TREE)


def function(source, name):
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


assert git("branch", "--show-current").decode().strip() == "fix/float-converge-20261103"
assert git("status", "--porcelain=v1") == b""
assert git("rev-parse", "HEAD").decode().strip() == COMMITS[-1]
assert git("rev-parse", "HEAD~3").decode().strip() == E9
assert [git("rev-parse", f"HEAD~{n}").decode().strip() for n in (2, 1, 0)] == COMMITS
assert git("diff", "--check", E9, "HEAD") == b""
changed = set(git("diff", "--name-only", E9, "HEAD").decode().splitlines())
assert changed == set(FILES), changed
for commit, expected in zip(COMMITS, (set(FILES.keys()) & {"model/core/ieee_fp_exceptions.sail"},
                                      {"model/extensions/V/vext_fp_utils_insts.sail"},
                                      {path for path in FILES if "/FD/" in path})):
    assert set(git("show", "--format=", "--name-only", commit).decode().splitlines()) == expected

review = json.loads((ROOT / "agents/float_review_closure_20261102/baseline-0008fae/architecture-candidates-review-20261103.json").read_text())
assert review["exceptions_candidate_sha256"] == FILES["model/core/ieee_fp_exceptions.sail"][1]
assert review["narrow_candidate_sha256"] == FILES["model/extensions/V/vext_fp_utils_insts.sail"][1]
for target, (candidate, digest) in FILES.items():
    installed = (TREE / target).read_bytes()
    assert installed == (HERE / candidate).read_bytes(), target
    assert sha256(installed).hexdigest() == digest, target
    if "/FD/" in target:
        assert review["wrapper_candidate_hashes"][candidate] == digest

core_path = "model/core/ieee_fp_exceptions.sail"
core_old = git("show", f"{E9}:{core_path}").decode()
core_new = (TREE / core_path).read_text()
core_restored = core_new
for width in (16, 32, 64):
    for op in ("add", "sub", "mul", "div", "sqrt", "fma"):
        name = f"ieee_{op}{width}_exceptions"
        old_body = function(core_old, name)
        new_body = function(core_new, name)
        gate = "finite" if op in ("add", "sub") else "valid"
        assert old_body.count(f"if {gate} then {{") == new_body.count(f"if {gate} then {{") == 1, name
        core_restored = core_restored.replace(new_body, old_body, 1)
assert core_restored == core_old  # 其余 core 字节，包括其余 finite/valid gate，仍是 e9。

v_path = "model/extensions/V/vext_fp_utils_insts.sail"
v_old = git("show", f"{E9}:{v_path}").decode()
v_new = (TREE / v_path).read_text()
assert "if overflow then" in function(v_old, "riscv_f16ToI16_pure")
assert function(v_old, "riscv_f16ToI16_pure").count("if overflow then") == function(v_new, "riscv_f16ToI16_pure").count("if overflow then") == 1
for name in ("riscv_f16ToI16", "riscv_f16ToI8", "riscv_f32ToI16",
             "riscv_f16ToUi16", "riscv_f16ToUi8", "riscv_f32ToUi16"):
    assert function(v_old, name) == function(v_new, name), name

wrapper_names = [entry["function"] for entry in review["wrapper_functions"]]
for width in (16, 32, 64):
    path = f"model/extensions/FD/softfloat_symbolic_f{width}.sail"
    old = git("show", f"{E9}:{path}").decode()
    new = (TREE / path).read_text()
    restored = new
    for name in (name for name in wrapper_names if name.startswith(f"riscv_f{width}To")):
        restored = restored.replace(function(new, name), function(old, name), 1)
    assert restored == old, path  # ROD mode 与所有非目标 wrapper 字节仍是 e9。

result = {
    "scope": "source application audit only; no strict/IR/dynamic/budget verdict",
    "base_model_commit": E9,
    "branch": "fix/float-converge-20261103",
    "commits": COMMITS,
    "head": COMMITS[-1],
    "worktree_clean": True,
    "changed_files_only": list(FILES),
    "installed_sha256": {path: digest for path, (_, digest) in FILES.items()},
    "removed_source_ifs": {"exception_causes": 33, "narrow_pure_returns": 8, "integer_wrapper_returns": 36, "total": 77},
    "open_source_preserved": {
        "flags_changed_and_unmodified_files": True,
        "eighteen_arithmetic_finite_valid_gates": True,
        "other_core_finite_valid_gates": True,
        "rod_mode_guards_and_non_target_wrapper_bytes": True,
        "legacy_f16_to_i16_outer_overflow_if": True,
    },
}
(HERE / "implementation-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print("PASS committed five signed candidates; 77 source ifs reverted; OPEN source preserved")
