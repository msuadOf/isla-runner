"""Apply only the independently approved pure-output reductions to 21418d0."""

from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / ".worktree/sail-riscv-general-float-by-model-20261022/model/core/ieee_fp_exceptions.sail"
text = SOURCE.read_text()
assert sha256(text.encode()).hexdigest() == "23fda9824c2280609062bbe2b9766597681c29af13a1e9cf1be045d9106757a8"


def replace(old, new, count):
    global text
    assert text.count(old) == count, (count, text.count(old), old)
    text = text.replace(old, new)


replace(
    """  if overflow then
    ieee_exception_facts(false, false, true, underflow, inexact)
  else if underflow then
    ieee_exception_facts(false, false, false, true, inexact)
  else if inexact then
    ieee_exception_facts(false, false, false, false, true)
  else
    ieee_empty_exceptions(false)""",
    "  ieee_exception_facts(false, false, overflow, underflow, inexact)",
    4,
)

replace(
    """    if inexact then
      ieee_exception_facts(invalid_nan, false, false, false, true)
    else
      ieee_empty_exceptions(invalid_nan)""",
    "    ieee_exception_facts(invalid_nan, false, false, false, inexact)",
    3,
)

replace(
    """      if inexact then
        ieee_exception_facts(false, false, false, false, true)
      else
        ieee_empty_exceptions(false)""",
    "      ieee_exception_facts(false, false, false, false, inexact)",
    1,
)

replace(
    """  if ieee_has_inexact(flags) then
    (flags, base_bits | 0x0001)
  else
    (flags, base_bits)""",
    "  (flags, ite(ieee_has_inexact(flags), base_bits | 0x0001, base_bits))",
    1,
)

replace(
    """  if ieee_has_inexact(flags) then
    (flags, base_bits | 0x00000001)
  else
    (flags, base_bits)""",
    "  (flags, ite(ieee_has_inexact(flags), base_bits | 0x00000001, base_bits))",
    1,
)

replace("ieee_mask_exact_exceptions(invalid_nan, true, facts)", "facts", 6)

replace(
    """function ieee_mask_exact_exceptions(invalid : bool, finite : bool, rounded : ieee_fp_exceptions) -> ieee_fp_exceptions =
  if finite then
    ieee_exception_facts(
      invalid,
      false,
      ieee_has_overflow(rounded),
      ieee_has_underflow(rounded),
      ieee_has_inexact(rounded)
    )
  else
    ieee_empty_exceptions(invalid)

""",
    "",
    1,
)

SOURCE.write_text(text)
print(sha256(text.encode()).hexdigest())
