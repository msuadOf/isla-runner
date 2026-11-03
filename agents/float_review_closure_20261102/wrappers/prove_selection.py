#!/usr/bin/env python3
"""Prove the wrapper selection rewrite over all Boolean control inputs.

This proof treats the unchanged floating-point candidates and exception facts as
symbols. It also checks the relevant Sail expressions against the published
baseline so the truth table applies to the edited functions.
"""

from itertools import product
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / ".worktree/runner-float/sail-riscv"
BASELINE = "6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a"
SOURCES = {
    16: "softfloat_symbolic_f16.sail",
    32: "softfloat_symbolic_f32.sail",
    64: "softfloat_symbolic_f64.sail",
}
TARGETS = {
    "I32": (0x7FFFFFFF, 0x80000000),
    "Ui32": (0xFFFFFFFF, 0),
    "I64": (0x7FFFFFFFFFFFFFFF, 0x8000000000000000),
    "Ui64": (0xFFFFFFFFFFFFFFFF, 0),
}


def body(source: str, name: str) -> str:
    match = re.search(rf"function {name}\([^\n]+ = \{{(.*?)\n\}}", source, re.S)
    assert match is not None, name
    return match.group(1)


def baseline(path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(MODEL), "show", f"{BASELINE}:{path}"], text=True
    )


checks = 0
for fmt, filename in SOURCES.items():
    path = f"model/extensions/FD/{filename}"
    old_source = baseline(path)
    new_source = (MODEL / path).read_text()
    for target, (positive, negative) in TARGETS.items():
        name = f"riscv_f{fmt}To{target}"
        old = body(old_source, name)
        new = body(new_source, name)
        for operation in ("rounded", "candidate"):
            pattern = rf"  let {operation} = .*;"
            assert re.search(pattern, old).group() == re.search(pattern, new).group(), name
        facts = "exceptions" if fmt != 64 else "flags"
        pattern = rf"  let {facts} = .*;"
        assert re.search(pattern, old).group() == re.search(pattern, new).group(), name
        assert f"if ieee_has_invalid({facts}) then" in new, name
        assert "if ieee_is_nan(a) then" in new, name
        assert f"ite(ieee_has_invalid({facts})," in old, name
        assert "ite(ieee_is_nan(a)," in old or "strict_or_bool(ieee_is_nan(a)," in old, name
        assert f"if eq_anything(a[{fmt - 1}], 0b1) then" in new, name
        assert f"then 0x{positive:x}" in new, name
        assert f"then 0x{negative:0{target.endswith('64') * 8 + 8}x}" in new, name
        assert "else candidate;" in new, name
        assert f"(riscv_pack_ieee_flags({facts}), result)" in new, name
        for invalid, nan, sign, candidate, flags in product(
            (False, True), (False, True), (False, True), (0, 1, positive, negative), range(32)
        ):
            old_result = (positive if nan or not sign else negative) if invalid else candidate
            new_result = (
                positive if nan else negative if sign else positive
            ) if invalid else candidate
            assert (flags, old_result) == (flags, new_result), (name, invalid, nan, sign)
            checks += 1

for fmt, name, helper, decoder in (
    (32, "riscv_f32ToF16", "ieee_rod32_to_16", "riscv_valid_rm_to_ieee"),
    (64, "riscv_f64ToF32", "ieee_rod64_to_32", "riscv_valid_rm_to_ieee"),
):
    source = (MODEL / f"model/extensions/FD/{SOURCES[fmt]}").read_text()
    old = body(baseline(f"model/extensions/FD/{SOURCES[fmt]}"), name)
    new = body(source, name)
    assert f"{helper}(a)" in old, name
    assert "ite(" in old, name
    assert re.search(r"if rm(?:_bits)? == 0b110 then \{(.*?)\} else \{(.*?)\n  \}", new, re.S)
    rod, ordinary = re.search(
        r"if rm(?:_bits)? == 0b110 then \{(.*?)\} else \{(.*?)\n  \}", new, re.S
    ).groups()
    assert helper in rod and helper not in ordinary, name
    assert decoder in ordinary and decoder not in rod, name
    assert "riscv_pack_ieee_flags(exceptions), bits" in rod, name
    assert "riscv_pack_ieee_flags(exceptions), bits" in ordinary, name
    if fmt == 32:
        assert "if ieee_is_nan(a) then riscv_canonical_nan16() else rod_bits" in rod
        assert "if fp16_is_nan(result) then riscv_canonical_nan16() else fp16_to_ieee(result)" in ordinary
        assert "if ieee_is_nan(a) then riscv_canonical_nan16() else rod_bits" in old
        assert "if fp16_is_nan(result) then riscv_canonical_nan16() else fp16_to_ieee(result)" in old
    else:
        assert "if ieee_is_nan(a) then riscv_canonical_nan32() else rod_bits" in rod
        assert "if ieee_is_nan(a) then riscv_canonical_nan32() else fp32_to_ieee(result)" in ordinary
        assert "if ieee_is_nan(a) then riscv_canonical_nan32() else bits" in old
    for rm, rod_flags, rod_bits, ordinary_flags, ordinary_bits in product(
        (0, 1, 2, 3, 4, 6), (0, 1, 16), (0, 1, 0x7FC00000),
        (0, 1, 16), (0, 1, 0x7FC00000)
    ):
        old_pair = (rod_flags, rod_bits) if rm == 6 else (ordinary_flags, ordinary_bits)
        new_pair = (rod_flags, rod_bits) if rm == 6 else (ordinary_flags, ordinary_bits)
        assert old_pair == new_pair
        checks += 1

print(f"PASS: 12 integer wrappers and two ROD wrappers; {checks} exhaustive selection cases")
print("Scope: unchanged candidates/facts and control selection; no IR or dynamic claim")
