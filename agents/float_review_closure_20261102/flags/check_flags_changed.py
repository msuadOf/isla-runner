#!/usr/bin/env python3
"""Check the local accrue_fflags branch against its previous state formula."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / ".worktree/runner-float/sail-riscv/model/extensions/FD/fdext_regs.sail"


def check_source() -> None:
    source = SOURCE.read_text()
    body = source.split("$ifdef SYMBOLIC\nfunction accrue_fflags", 1)[1].split("$else", 1)[0]
    expected = r"""
  let old = fcsr[FFLAGS];
  let f = old | flags;
  let changed = not_bool(eq_anything(old, f));
  fcsr[FFLAGS] = f;
  if changed then {
    assert(hartSupports(Ext_F) != hartSupports(Ext_Zfinx));
    if hartSupports(Ext_F) then {
      let dirty = [mstatus with FS = extStatus_to_bits(Dirty), SD = 0b1];
      mstatus.bits = dirty.bits;
    };
  };
  csr_write_callback("fflags", zero_extend(fcsr[FFLAGS]));
  csr_write_callback("fcsr", zero_extend(fcsr.bits));
"""
    assert re.sub(r"\s+", "", expected) in re.sub(r"\s+", "", body)
    assert "dirty_fd_context_if_present" not in body
    assert "long_csr_write_callback" not in body


def run(old: int, flags: int, fcsr_upper: int, mstatus: int,
        ext_f: bool, ext_zfinx: bool, xlen: int, explicit: bool):
    result_flags = old | flags
    result_fcsr = fcsr_upper | result_flags
    changed = result_flags != old
    events = []
    # Both versions first write the five FFLAGS bits inside the 32-bit FCSR.
    if changed and ext_f == ext_zfinx:
        return result_fcsr, mstatus, (("assertion failure",),)
    if ext_f:
        fs_mask = 0b11 << 13
        sd_mask = 1 << (xlen - 1)
        dirty = (mstatus & ~fs_mask) | fs_mask | sd_mask
        if explicit:
            if changed:
                mstatus = dirty
        else:
            mstatus = dirty if changed else mstatus
    events.extend((("fflags", result_flags), ("fcsr", result_fcsr)))
    return result_fcsr, mstatus, tuple(events)


def main() -> None:
    check_source()
    checked = 0
    cases = set()
    for xlen in (32, 64):
        all_bits = (1 << xlen) - 1
        other_bits = (1 << 7) | (1 << 12) | (1 << 25) | (1 << (xlen - 2))
        for old in range(32):
            for flags in range(32):
                changed = (old | flags) != old
                added = flags & ~old
                if old == flags == 0:
                    cases.add("zero")
                if old != 0 and flags != 0 and not changed:
                    cases.add("old contains same flag")
                if added.bit_count() == 1:
                    cases.add("one new flag")
                if added.bit_count() > 1:
                    cases.add("multiple new flags")
                if old != 0 and changed:
                    cases.add("other old flag plus new flag")
                for ext_f in (False, True):
                    for ext_zfinx in (False, True):
                        for fs in range(4):
                            for other in (0, other_bits, all_bits & ~(0b11 << 13)):
                                for fcsr_upper in (0, 0xa0, 0xabcdef00, 0xffffffe0):
                                    initial = (other & ~(0b11 << 13)) | (fs << 13)
                                    before = run(old, flags, fcsr_upper, initial,
                                                 ext_f, ext_zfinx, xlen, False)
                                    after = run(old, flags, fcsr_upper, initial,
                                                ext_f, ext_zfinx, xlen, True)
                                    assert before == after, (xlen, old, flags, initial,
                                                             ext_f, ext_zfinx, fcsr_upper)
                                    if not changed:
                                        assert after[1] == initial
                                    checked += 1
    assert cases == {"zero", "old contains same flag", "one new flag",
                     "multiple new flags", "other old flag plus new flag"}
    print(f"PASS: {checked} helper states; FFLAGS, mstatus, assertion, callback order")


if __name__ == "__main__":
    main()
