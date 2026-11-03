#!/usr/bin/env python3
"""Apply only the activity gate to the frozen 9c339044 overflow-if model."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = ROOT / "agents/branch_ablation_20261031/classification/sat_f16_i16_if/model/extensions/V/vext_fp_insts.sail"
CURRENT = ROOT / ".worktree/runner-float/sail-riscv/model/extensions/V/vext_fp_insts.sail"
TARGET = HERE / "model/extensions/V/vext_fp_insts.sail"
START = "function clause execute VFUNARY0(vm, vs2, vfunary0, vd) = {"
END = "\n}\n\n$else"
BLOCK_START = "  var result = initial_result;"
BLOCK_END = "  accrue_fflags(combined_flags);"


def clause(text):
    i = text.index(START)
    j = text.index(END, i) + 2
    return text[i:j]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


old_full = OLD.read_text()
current_full = CURRENT.read_text()
assert TARGET.read_text() == old_full
old_clause = clause(old_full)
current_clause = clause(current_full)
old_prefix = old_clause[:old_clause.index(BLOCK_START)]
cur_prefix = current_clause[:current_clause.index(BLOCK_START)]
old_suffix = old_clause[old_clause.index(BLOCK_END)+len(BLOCK_END):]
cur_suffix = current_clause[current_clause.index(BLOCK_END)+len(BLOCK_END):]
assert old_prefix == cur_prefix and old_suffix == cur_suffix
assert "var candidates = initial_result" in old_clause
assert "if mask[i] == 0b1 then {" in current_clause
replacement = old_prefix + current_clause[current_clause.index(BLOCK_START):current_clause.index(BLOCK_END)+len(BLOCK_END)] + old_suffix
assert old_full.count(old_clause) == 1
TARGET.write_text(old_full.replace(old_clause, replacement, 1))
manifest = {"base_model_commit": "9c339044b07e235fe48d5bc585cbd3975ceeba5a",
            "old_overflow_if_model": str(OLD.relative_to(ROOT)),
            "changed_file": "model/extensions/V/vext_fp_insts.sail",
            "change": "Only the SYMBOLIC VFUNARY0 activity-gate block is replaced; prelude, epilogue and all other files remain old B.",
            "sha256": {"old_source": digest(OLD), "gate_source": digest(TARGET)},
            "prefix_equal": True, "suffix_equal": True}
(HERE / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
