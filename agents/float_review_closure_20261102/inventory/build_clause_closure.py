#!/usr/bin/env python3
"""Build a conservative Sail call closure intersected with run.mk FD_FLOAT.

This is source inventory, not reachability or dynamic coverage. Conditional
ordinary/SYMBOLIC definitions are unioned so the result cannot silently omit a
caller solely because a preprocessor branch was selected elsewhere.
"""

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / ".worktree/runner-float/sail-riscv/model"
RUN_MK = ROOT / ".worktree/runner-float/isla/scripts/run.mk"
OUTPUT = Path(__file__).with_name("affected-clauses.json")


def git_text(path, *args):
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True
    ).strip()

HEAD = re.compile(
    r"^function\s+(?:clause\s+execute\s+\(?\s*)?([A-Za-z][A-Za-z0-9_]*)\s*\(",
    re.MULTILINE,
)
CALL = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\(")

functions = defaultdict(set)
clauses = defaultdict(set)
locations = defaultdict(set)
model_files = git_text(MODEL.parent, "ls-tree", "-r", "--name-only", "HEAD", "model").splitlines()
for model_file in model_files:
    if not model_file.endswith(".sail"):
        continue
    source = git_text(MODEL.parent, "show", f"HEAD:{model_file}")
    path = MODEL.parent / model_file
    heads = list(HEAD.finditer(source))
    for index, head in enumerate(heads):
        name = head.group(1)
        end = heads[index + 1].start() if index + 1 < len(heads) else len(source)
        body = source[head.end() : end]
        calls = set(CALL.findall(body))
        kind = clauses if "clause execute" in head.group(0) else functions
        kind[name].update(calls)
        locations[name].add(
            f"{path.relative_to(ROOT)}:{source.count(chr(10), 0, head.start()) + 1}"
        )

text = git_text(RUN_MK.parent.parent, "show", "HEAD:scripts/run.mk")
match = re.search(r"^FD_FLOAT=(.*?)(?=\n\n)", text, re.MULTILINE | re.DOTALL)
if match is None:
    raise SystemExit("FD_FLOAT not found")
fd_float = set(match.group(1).replace("\\\n", " ").split())

seeds = {
    "fflags_changed": {"accrue_fflags"},
    "five_narrow_adapters": {
        "riscv_f16ToI8_pure",
        "riscv_f16ToUi8_pure",
        "riscv_f16ToUi16_pure",
        "riscv_f32ToI16_pure",
        "riscv_f32ToUi16_pure",
    },
    "twelve_integer_wrappers": {
        f"riscv_f{width}To{target}"
        for width in (16, 32, 64)
        for target in ("I32", "Ui32", "I64", "Ui64")
    },
    "arithmetic_exception_causes": {
        f"ieee_{operation}{width}_exceptions"
        for width in (16, 32, 64)
        for operation in ("add", "sub", "mul", "div", "sqrt", "fma")
    },
    "rod_mode_and_jam": {
        "riscv_f32ToF16",
        "riscv_f64ToF32",
        "ieee_rod32_to_16",
        "ieee_rod64_to_32",
    },
}

categories = {}
all_affected = set()
for category, targets in seeds.items():
    missing = targets - functions.keys()
    if missing:
        raise SystemExit(f"missing source functions in {category}: {sorted(missing)}")
    reached = set(targets)
    while True:
        new = {name for name, calls in functions.items() if calls & reached} - reached
        if not new:
            break
        reached.update(new)
    callers = {name for name, calls in clauses.items() if calls & reached}
    outside_fd = callers - fd_float
    if outside_fd:
        raise SystemExit(f"source callers absent from FD_FLOAT: {sorted(outside_fd)}")
    categories[category] = {
        "seed_functions": sorted(targets),
        "clauses": sorted(callers),
        "count": len(callers),
    }
    all_affected.update(callers)

output = {
    "kind": "conservative_static_sail_call_closure",
    "source_mode": "committed_component_heads",
    "model_commit": git_text(MODEL.parent, "rev-parse", "HEAD"),
    "model_dirty": bool(git_text(MODEL.parent, "status", "--short")),
    "isla_commit": git_text(RUN_MK.parent.parent, "rev-parse", "HEAD"),
    "isla_dirty": bool(git_text(RUN_MK.parent.parent, "status", "--short")),
    "fd_float_source": str(RUN_MK.relative_to(ROOT)),
    "fd_float_count": len(fd_float),
    "affected_count": len(all_affected),
    "affected_clauses": sorted(all_affected),
    "unaffected_fd_float_clauses": sorted(fd_float - all_affected),
    "categories": categories,
    "full_clause_run_list": [
        {
            "clause": name,
            "make_target": f"solve-{name}",
            "categories": sorted(
                category
                for category, entry in categories.items()
                if name in entry["clauses"]
            ),
            "isa_config": "configs/riscv64_difftest_fd.toml",
            "thread_count": 1,
            "tactic": "qffp",
            "outer_timeout_s": 7200,
            "smt_timeout_s": 7200,
            "seed": 17,
            "status": "not_run_on_final_model",
        }
        for name in sorted(all_affected)
    ],
    "clause_source_locations": {
        name: sorted(locations[name]) for name in sorted(all_affected)
    },
    "method_note": (
        "Union ordinary and SYMBOLIC source definitions; recursively find callers "
        "of changed functions, then intersect the 89 FD_FLOAT entries. This is "
        "a conservative static scope, not proof that every enum or format reaches "
        "the changed behavior. Run-list fields are intended targets, not results; "
        "the standard Make target has no fixed-Z3-seed option, so the launch "
        "manifest must document its tested seed mechanism."
    ),
}
OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
print(f"FD_FLOAT={len(fd_float)} affected={len(all_affected)} excluded={len(fd_float-all_affected)}")
for category, entry in categories.items():
    print(f"{category}: {entry['count']}")
