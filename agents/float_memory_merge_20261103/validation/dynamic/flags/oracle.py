#!/usr/bin/env python3
"""Independently check direct IR state logs against ordinary Sail semantics."""

import argparse
import json
from pathlib import Path


CASES = {
    "zero": (0, 0),
    "same_nv": (0x10, 0x10),
    "new_nv": (0, 0x10),
    "old_nx_new_nv": (0x01, 0x10),
    "new_multiple": (0x04, 0x13),
}


def number(value: str) -> int:
    return int(value, 0)


def check(path: Path) -> dict:
    lines = path.read_text().splitlines()
    assert "CALLBACK_CONTRACT fflags,fcsr; no mstatus callback" in lines
    found = set()
    callback_counts = {"ordinary_mstatus": 0, "symbolic_mstatus": 0}
    for line in lines:
        if not line.startswith("PASS ") or line.startswith("PASS total="):
            continue
        _, label, *items = line.split()
        values = dict(item.split("=", 1) for item in items)
        xlen = number(values["xlen"])
        fs = number(values["fs"])
        sd_initial = values["initial_sd"] == "true"
        other = number(values["other"])
        old_fcsr = number(values["old_fcsr"])
        initial_status = number(values["initial_mstatus"])
        incoming = number(values["incoming"])
        assert xlen in (32, 64) and fs in (1, 2, 3) and label in CASES
        assert incoming < 32 and old_fcsr & ~31 == 0x123456a0
        assert (old_fcsr & 31, incoming) == CASES[label]
        sd = 1 << (xlen - 1)
        fs_mask = 3 << 13
        assert initial_status == (other | (sd if sd_initial else 0) | (fs << 13))
        assert not (other & (sd | fs_mask))
        # The ordinary Sail helper writes FCSR and calls dirty_fd_context_if_present
        # only when the OR adds a bit. The symbolic helper has the same state rule.
        old_flags = old_fcsr & 31
        new_flags = old_flags | incoming
        changed = new_flags != old_flags
        expected_fcsr = (old_fcsr & ~31) | new_flags
        expected_status = (initial_status & ~fs_mask) | fs_mask | sd if changed else initial_status
        assert values["changed"] == str(changed).lower()
        assert number(values["expected_fcsr"]) == expected_fcsr
        assert number(values["expected_mstatus"]) == expected_status
        assert number(values["fcsr"]) == expected_fcsr
        assert number(values["mstatus"]) == expected_status
        if changed:
            callback_counts["ordinary_mstatus"] += 1
        found.add((label, fs, sd_initial, other))
    assert len(found) == 60
    assert lines[-1] in ("PASS total=60 xlen=32", "PASS total=60 xlen=64")
    labels = {item[0] for item in found}
    assert labels == set(CASES)
    return {"pass": True, "rows": len(found), "labels": sorted(labels),
            "ordinary_callback_counts": {"mstatus": callback_counts["ordinary_mstatus"],
                                         "fflags": len(found), "fcsr": len(found)},
            "symbolic_callback_contract": ["fflags", "fcsr"],
            "scope": "ordinary/SYMBOLIC state equivalence for Ext_F configs; ordinary mstatus callback differs"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.log), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
