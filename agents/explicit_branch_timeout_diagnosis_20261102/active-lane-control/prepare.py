#!/usr/bin/env python3
"""Freeze the same active-lane IR with ITE and explicit f16->i16 overflow."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CURRENT = ROOT / "agents/special_control_restore_20261102/implementation/generation/rv64d_v128_e64/rv64d_v128_e64.ir"
OLD_B = ROOT / "agents/branch_ablation_official_z3_20261102/inputs/sat/B.ir"
CONFIG = ROOT / "agents/branch_ablation_official_z3_20261102/inputs/sat/config.toml"
START = "fn zriscv_f16ToI16_pure(zrm, zv) {"


def extract(ir: str) -> str:
    begin = ir.index(START)
    end = ir.index("\n}\n", begin) + 3
    return ir[begin:end]


def normalize(fragment: str) -> str:
    return re.sub(r" `[^;]+;", ";", fragment)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    current = CURRENT.read_text()
    prior = OLD_B.read_text()
    cur_fn = extract(current)
    old_fn = extract(prior)
    cur_prefix = cur_fn[: cur_fn.index("  zz420 : %bv5")]
    old_prefix = old_fn[: old_fn.index("  jump zz44")]
    assert normalize(cur_prefix) == normalize(old_prefix)
    assert "zitezIB5zK(zz44" in cur_fn
    assert "jump zz44 goto 52" in old_fn
    assert current.count(cur_fn) == 1
    HERE.mkdir(exist_ok=True)
    (HERE / "A.ir").write_text(current)
    # Keep the current function prelude and all of the current IR. Only the
    # overflow branch tail comes from the previously verified explicit IR.
    branch_tail = old_fn[old_fn.index("  jump zz44") :]
    modified_fn = cur_prefix + branch_tail
    (HERE / "B.ir").write_text(current.replace(cur_fn, modified_fn, 1))
    shutil.copyfile(CONFIG, HERE / "config.toml")
    binary = ROOT / "agents/branch_ablation_official_z3_20261102/bin/isarch"
    seed = ROOT / "agents/branch_ablation_official_z3_20261102/bin/seed_control.so"
    manifest = {
        "base_model_commit": "a9fd947",
        "base_isla_commit": "99a83bb",
        "current_ir": str(CURRENT.relative_to(ROOT)),
        "old_explicit_ir": str(OLD_B.relative_to(ROOT)),
        "modified_function": START,
        "change": "The single helper's suffix from jump zz44 onward is from old B; the prefix, all other functions and active-lane gate remain byte-identical to current A.",
        "sha256": {str(p.relative_to(ROOT)): digest(p) for p in (CURRENT, OLD_B, CONFIG, binary, seed, HERE / "A.ir", HERE / "B.ir", HERE / "config.toml")},
        "function_normalized_prefix_equal": True,
        "outside_function_byte_equal": True,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
