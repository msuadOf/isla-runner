#!/usr/bin/env python3
"""Audit old-base gate generation against the frozen eager overflow-if IR."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORIGINAL_MODEL = ROOT / "agents/branch_ablation_20261031/classification/sat_f16_i16_if/model"
MODEL = HERE / "model"
OLD = ROOT / "agents/branch_ablation_official_z3_20261102/inputs/sat/B.ir"
NEW = HERE / "generation-cached/rv64d_v128_e64.ir"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


source_files = [path.relative_to(ORIGINAL_MODEL) for path in ORIGINAL_MODEL.rglob("*") if path.is_file()]
changed_sources = [str(path) for path in source_files if sha(ORIGINAL_MODEL / path) != sha(MODEL / path)]
assert changed_sources == ["extensions/V/vext_fp_insts.sail"]
old_ir, new_ir = OLD.read_text(), NEW.read_text()
fn_pat = re.compile(r"(?m)^fn ([^(]+)\(")


def functions(text):
    matches = list(fn_pat.finditer(text))
    return {match.group(1): text[match.start():matches[index+1].start()
                                      if index+1 < len(matches) else len(text)]
            for index, match in enumerate(matches)}


old_functions, new_functions = functions(old_ir), functions(new_ir)
assert list(old_functions) == list(new_functions)
assert old_ir[:fn_pat.search(old_ir).start()] == new_ir[:fn_pat.search(new_ir).start()]
assert old_ir[:old_ir.index("fn zexecute(")] == new_ir[:new_ir.index("fn zexecute(")]
helper = "zriscv_f16ToI16_pure"
assert old_functions[helper] == new_functions[helper]


def alpha(text):
    mapping = {}

    def replace(match):
        name = match.group()
        if name not in mapping:
            mapping[name] = f"E{len(mapping)}"
        return mapping[name]

    return re.sub(r"z3zE\d+", replace, text)


changed = [name for name in old_functions if old_functions[name] != new_functions[name]]
assert "zexecute" in changed
assert all(alpha(old_functions[name]) == alpha(new_functions[name])
           for name in changed if name != "zexecute")

body = new_functions["zexecute"].splitlines()
code = body[1:body.index("}")]
gate = next(i for i, line in enumerate(code)
            if re.search(r"jump zz\d+ goto \d+ `93 746:4-799:5", line))
active_target = int(re.search(r"goto (\d+)", code[gate]).group(1))
calls = [i for i, line in enumerate(code) if "= zriscv_f16ToI16_pure(" in line]
assert len(calls) == 2


def reachable(start, blocked):
    todo, seen = [start], set()
    while todo:
        pc = todo.pop()
        if pc in seen or pc in blocked or not (0 <= pc < len(code)):
            continue
        seen.add(pc)
        line = code[pc].strip()
        match = re.search(r"\bgoto (\d+)", line)
        if line.startswith("goto "):
            if match:
                todo.append(int(match.group(1)))
        elif line.startswith("jump "):
            todo.append(pc + 1)
            if match:
                todo.append(int(match.group(1)))
        elif not (line.startswith("return ") or line == "end;"):
            todo.append(pc + 1)
    return seen


assert all(pc in reachable(0, set()) for pc in calls)
assert all(pc not in reachable(0, {gate}) for pc in calls)
assert all(pc not in reachable(gate + 1, {gate}) for pc in calls)
assert all(pc in reachable(active_target, {gate}) for pc in calls)
result = {"source_changed_files": changed_sources, "original_ir_sha256": sha(OLD),
          "gate_ir_sha256": sha(NEW), "helper_byte_equal": True,
          "pre_zexecute_ir_byte_equal": True, "function_count": len(old_functions),
          "raw_changed_functions": changed,
          "other_changed_functions_alpha_equivalent": len(changed) - 1,
          "gate_pc": gate, "active_target_pc": active_target,
          "inactive_next_pc": gate + 1, "conversion_call_pcs": calls,
          "conversion_calls_dominated_by_gate": True,
          "inactive_path_bypasses_calls": True}
(HERE / "ir-audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
