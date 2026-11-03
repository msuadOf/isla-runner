#!/usr/bin/env python3
"""Independently decode generated FCVT and VCVT instruction words and groups."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def hexint(value):
    return int(value, 16)


def check_scalar(case):
    word = hexint(case["word"])
    fields = case["expected_fields"]
    assert word & 0x7f == 0x53, case["name"]
    assert (word >> 7) & 31 == hexint(fields["2"]) == 3, case["name"]
    assert (word >> 15) & 31 == hexint(fields["0"]) == 1, case["name"]
    assert (word >> 12) & 7 == ("RM_RNE", "RM_RTZ", "RM_RDN", "RM_RUP", "RM_RMM").index(fields["1"]), case["name"]
    raw = hexint(case["source_bits"])
    source_width = {"H": 16, "S": 32, "D": 64}[case["clause"][-1]]
    mask = (1 << source_width) - 1
    assert hexint(case["initial"]["f1"]) & mask == raw, case["name"]
    if source_width < 64:
        assert hexint(case["initial"]["f1"]) >> source_width == (1 << (64 - source_width)) - 1, case["name"]
    assert case["expected_fields"]["3"].startswith("FCVT_"), case["name"]
    assert set(case["observe"]) == {"x3", "x2", "f1", "fcsr", "mstatus"}, case["name"]
    assert case["expected"]["x2"] == case["initial"]["x2"], case["name"]
    assert case["expected"]["f1"] == case["initial"]["f1"], case["name"]


def check_vector(case):
    word = hexint(case["word"])
    fields = case["expected_fields"]
    assert word & 0x7f == 0x57, case["name"]
    assert (word >> 25) & 1 == hexint(fields["0"]), case["name"]
    source_reg = (word >> 20) & 31
    dest_reg = (word >> 7) & 31
    assert source_reg == hexint(fields["1"]), case["name"]
    assert dest_reg == hexint(fields["3"]), case["name"]
    assert (word >> 12) & 7 == 1, case["name"]
    assert (word >> 26) & 63 == 0b010010, case["name"]
    dest_width = 16 if hexint(case["initial"]["vtype"]) & 8 else 8
    source_width = dest_width if case["clause"] == "VFUNARY0" else 2 * dest_width
    source_bits = [hexint(item) for item in case["source_bits"]]
    source_value = hexint(case["initial"][f"vr{source_reg}"])
    assert source_value & ((1 << source_width) - 1) == source_bits[0], case["name"]
    assert (source_value >> source_width) & ((1 << source_width) - 1) == source_bits[1], case["name"]
    lmul2 = hexint(case["initial"]["vtype"]) & 7 == 1
    source_emul = (2 if lmul2 else 1) if case["clause"] == "VFUNARY0" else (4 if lmul2 else 2)
    source_group = {f"vr{reg}" for reg in range(source_reg, source_reg + source_emul)}
    if lmul2:
        assert source_reg % source_emul == 0, case["name"]
        assert dest_reg % 2 == 0, case["name"]
        assert not (set(range(source_reg, source_reg + source_emul)) & set(range(dest_reg, dest_reg + 2))), case["name"]
        assert {f"vr{dest_reg}", f"vr{dest_reg + 1}"} <= set(case["observe"]), case["name"]
    else:
        assert f"vr{dest_reg}" in case["observe"], case["name"]
    expected_observe = ({f"vr{dest_reg}", f"vr{dest_reg + 1}"} if lmul2 else {f"vr{dest_reg}"})
    expected_observe |= source_group | {"vr0", "vr10"}
    assert set(case["observe"]) - {"fcsr", "vstart", "mstatus"} == expected_observe, case["name"]
    for reg in source_group | {"vr0", "vr10"}:
        assert case["expected"][reg] == case["initial"][reg], case["name"]


def main():
    scalar = json.loads((HERE / "scalar-cases.json").read_text())
    vector = json.loads((HERE / "vector-cases.json").read_text())
    for case in scalar:
        check_scalar(case)
    for case in vector:
        check_vector(case)
    print(f"decoded {len(scalar)} scalar and {len(vector)} vector fixtures")


if __name__ == "__main__":
    main()
