#!/usr/bin/env python3
"""检查饱和出口恢复仅改变已验证的 f16→i16 SYMBOLIC helper。"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / ".worktree/runner-float/sail-riscv"
SOURCE = MODEL / "model/extensions/V/vext_fp_utils_insts.sail"
BASE = "a9fd9476fc1bf471070a38e01ee9233d10d742d3"
OLD = """// The narrow integer adapters keep the original saturation rule while using
// bitvector ITEs, so an inactive lane never forks on its converted value.
function riscv_f16ToI16_pure(rm : bits_rm, v : bits_H) -> (bits_fflags, bits(16)) = {
  let (flag, sig32) = riscv_f16ToI32(rm, v);
  let overflow = not_bool(eq_anything(sig32, sign_extend(sig32[15 .. 0])));
  let limit = ite(eq_anything(sig32[31], 0b1), 0x8000, 0x7fff);
  (ite(overflow, nvFlag(), flag), ite(overflow, limit, sig32[15 .. 0]))
}
"""
NEW = """// The f16-to-i16 adapter branches on overflow after the active-lane gate.
// Other narrow integer adapters retain their bitvector ITE saturation rules.
function riscv_f16ToI16_pure(rm : bits_rm, v : bits_H) -> (bits_fflags, bits(16)) = {
  let (flag, sig32) = riscv_f16ToI32(rm, v);
  let overflow = not_bool(eq_anything(sig32, sign_extend(sig32[15 .. 0])));
  let limit = ite(eq_anything(sig32[31], 0b1), 0x8000, 0x7fff);
  if overflow then (nvFlag(), limit) else (flag, sig32[15 .. 0])
}
"""

base = subprocess.check_output(
    ["git", "-C", str(MODEL), "show", f"{BASE}:model/extensions/V/vext_fp_utils_insts.sail"],
    text=True,
)
assert base.count(OLD) == 1, "基线片段不匹配"
actual = SOURCE.read_text()
assert actual == base.replace(OLD, NEW, 1), "源码尚未精确恢复已测 overflow 分支"
print("PASS: 显式 overflow 且其余源码与 a9fd947 完全相同")
