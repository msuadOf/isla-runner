#!/usr/bin/env python3
"""Check the single helper edit and activity-gate dominance in both IRs."""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
START = "fn zriscv_f16ToI16_pure(zrm, zv) {"


def extract_function(ir, name):
    start = ir.index(name)
    end = ir.index("\n}\n", start) + 3
    return ir[start:end]


text_a = (HERE / "A.ir").read_text()
text_b = (HERE / "B.ir").read_text()
fn_a = extract_function(text_a, START)
fn_b = extract_function(text_b, START)
assert text_a.replace(fn_a, "<helper>", 1) == text_b.replace(fn_b, "<helper>", 1)
assert fn_a[:fn_a.index("  zz420 : %bv5")] == fn_b[:fn_b.index("  jump zz44")]
assert "zitezIB5zK(zz44, zz421, zz42)" in fn_a
assert "jump zz44 goto 52" in fn_b

result = {"only_changed_function": START, "outside_function_byte_equal": True,
          "helper_prefix_byte_equal": True, "arms": {}}
for arm, ir in (("A", text_a), ("B", text_b)):
    lines = extract_function(ir, "fn zexecute(zmergez3var) {").splitlines()
    # PC zero is the first line after the fn header, including declarations.
    code = lines[1:-1]
    gate = next(i for i, line in enumerate(code)
                if re.search(r"jump zz410921 goto 25881", line))
    calls = [i for i, line in enumerate(code)
             if "= zriscv_f16ToI16_pure(" in line]
    assert len(calls) == 2
    assert "= zeq_bits(zz410924, zz410925)" in code[gate-1]
    assert any("zbitvector_access(zz410908, zz410923)" in line
               for line in code[gate-12:gate])

    def reachable(start, blocked):
        todo = [start]
        seen = set()
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

    assert calls[0] in reachable(0, set())
    assert calls[1] in reachable(0, set())
    assert all(pc not in reachable(0, {gate}) for pc in calls)
    assert all(pc not in reachable(gate + 1, {gate}) for pc in calls)
    assert all(pc in reachable(25881, {gate}) for pc in calls)
    result["arms"][arm] = {"gate_pc": gate, "active_target_pc": 25881,
                           "inactive_next_pc": gate + 1,
                           "conversion_call_pcs": calls,
                           "conversion_calls_dominated_by_gate": True,
                           "inactive_path_bypasses_calls": True}

(HERE / "ir-audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
