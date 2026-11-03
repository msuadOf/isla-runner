#!/usr/bin/env python3
"""Prepare independent FP-input expectations for integer conversion helpers and instructions."""

import argparse
import copy
import hashlib
import json
import struct
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORACLE_DEFAULT = ROOT / ".tmp/unified-backend-crosscheck/oracle-build/oracle"
FORMATS = {16: (">e", 0x7bff, 0x7c00, 0x7e00, 0x7c01),
           32: (">f", 0x7f7fffff, 0x7f800000, 0x7fc00000, 0x7f800001),
           64: (">d", 0x7fefffffffffffff, 0x7ff0000000000000,
                0x7ff8000000000000, 0x7ff0000000000001)}
NARROW = [
    ("riscv_f16ToI16_pure", 16, "i32", 16),
    ("riscv_f16ToI8_pure", 16, "i32", 8),
    ("riscv_f32ToI16_pure", 32, "i32", 16),
    ("riscv_f16ToUi16_pure", 16, "u32", 16),
    ("riscv_f16ToUi8_pure", 16, "u32", 8),
    ("riscv_f32ToUi16_pure", 32, "u32", 16),
]
WIDE = [(f"riscv_f{width}To{kind}{target}", width,
         ("i" if kind == "I" else "u") + str(target), target)
        for width in (16, 32, 64) for kind in ("I", "Ui") for target in (32, 64)]
SPECS = NARROW + WIDE
RM_NAMES = ("RM_RNE", "RM_RTZ", "RM_RDN", "RM_RUP", "RM_RMM")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(number, width):
    try:
        return int.from_bytes(struct.pack(FORMATS[width][0], float(number)), "big")
    except OverflowError:
        return None


def finite(raw, width):
    exp_bits = {16: 5, 32: 8, 64: 11}[width]
    frac_bits = {16: 10, 32: 23, 64: 52}[width]
    return ((raw >> frac_bits) & ((1 << exp_bits) - 1)) != (1 << exp_bits) - 1


def inputs(width, target, result_width):
    _, maximum, infinity, qnan, snan = FORMATS[width]
    sign = 1 << (width - 1)
    candidates = {
        "positive_zero": 0, "negative_zero": sign,
        "positive_inf": infinity, "negative_inf": infinity | sign,
        "positive_qnan": qnan, "negative_qnan": qnan | sign,
        "positive_snan": snan, "negative_snan": snan | sign,
        "maximum_finite": maximum, "minimum_finite": maximum | sign,
    }
    for label, value in (("one", 1), ("negative_one", -1),
                         ("one_half", 1.5), ("negative_one_half", -1.5),
                         ("two_half", 2.5), ("negative_two_half", -2.5),
                         ("negative_half", -0.5), ("positive_half", 0.5)):
        candidates[label] = encoded(value, width)
    exponent = result_width if target.startswith("u") else result_width - 1
    signed_target = target.startswith("i")
    upper_integer = (1 << (result_width - 1)) - 1 if signed_target else (1 << result_width) - 1
    upper_raw = encoded(upper_integer, width)
    if upper_raw is not None and finite(upper_raw, width):
        upper_value = struct.unpack(FORMATS[width][0], upper_raw.to_bytes(width // 8, "big"))[0]
        if upper_value == upper_integer:
            candidates["exact_upper_integer"] = upper_raw
    if signed_target:
        lower_integer = -(1 << (result_width - 1))
        lower_raw = encoded(lower_integer, width)
        if lower_raw is not None and finite(lower_raw, width):
            lower_value = struct.unpack(FORMATS[width][0], lower_raw.to_bytes(width // 8, "big"))[0]
            if lower_value == lower_integer:
                candidates["exact_lower_integer"] = lower_raw
    anchor = encoded(1 << exponent, width)
    if anchor is not None and finite(anchor, width):
        candidates.update({"upper_boundary_below": anchor - 1,
                           "upper_boundary_at": anchor})
        fractional = encoded((1 << exponent) + 0.5, width)
        if fractional is not None and finite(fractional, width):
            actual = struct.unpack(FORMATS[width][0], fractional.to_bytes(width // 8, "big"))[0]
            if actual == (1 << exponent) + 0.5:
                candidates["upper_fractional_overflow"] = fractional
        if not target.startswith("u"):
            candidates.update({"lower_boundary_at": anchor | sign,
                               "lower_boundary_below": (anchor + 1) | sign})
    return {label: raw for label, raw in candidates.items() if raw is not None}


def narrow_result(wide_bits, wide_flags, target, result_width):
    mask = (1 << result_width) - 1
    if target.startswith("i"):
        signed = wide_bits if wide_bits < (1 << 31) else wide_bits - (1 << 32)
        lower, upper = -(1 << (result_width - 1)), (1 << (result_width - 1)) - 1
        if signed < lower:
            return lower & mask, 0x10, True
        if signed > upper:
            return upper, 0x10, True
    elif wide_bits > mask:
        return mask, 0x10, True
    return wide_bits & mask, wide_flags, False


def oracle_result(oracle, width, target, raw, rm):
    command = [str(oracle), "--op", "fp_to_int", "--fmt", f"f{width}",
               "--dst", target, "--rm", str(rm), "--a", hex(raw)]
    data = json.loads(subprocess.check_output(command, text=True))
    return int(data["result_bits"], 16), int(data["flags"], 16)


def fp_box(raw, width):
    return raw | (((1 << (64 - width)) - 1) << width) if width < 64 else raw


def vector_base(clause, enum):
    if clause == "VFUNARY0":
        path = ROOT / "agents/float_support_review/tools/e_vector_cases/expanded-cases.json"
    else:
        path = ROOT / "agents/float_support_review/tools/e_nonmem/inputs/vfnunary0-sew8.json"
    rows = json.loads(path.read_text())
    matches = [row for row in rows if row["clause"] == clause
               and row["expected_fields"]["2"] == enum]
    assert matches, (clause, enum)
    return path, matches[0]


def scalar_base(width, target):
    suffix = {16: "h", 32: "s", 64: "d"}[width]
    kind = {"i32": "w", "u32": "wu", "i64": "l", "u64": "lu"}[target]
    name = f"fcvt_{kind}_{suffix}"
    paths = [ROOT / "agents/float_support_review/tools/e_scalar_cases/enum-ops.json",
             ROOT / "agents/float_support_review/tools/e_scalar_cases/scalar-cases.json"]
    matches = [(path, row) for path in paths for row in json.loads(path.read_text())
               if row["name"] == name]
    assert len(matches) == 1, name
    return matches[0]


def vector_case(row, base, source_width, result_width, rm, *, fixed_rtz=False,
                active_mask=3, vl=2, vstart=0, lmul2=False, old_flags=0,
                lane1_raw=None):
    case = copy.deepcopy(base)
    enum = case["expected_fields"]["2"]
    dest = int(case["expected_fields"]["3"], 16)
    source_raw = row["source_bits"]
    lane0 = source_raw
    lane1 = encoded(1.0, source_width) if lane1_raw is None else lane1_raw
    assert lane1 is not None
    source = lane0 | (lane1 << source_width)
    sentinel = int("a5" * 16, 16)
    mask = (1 << result_width) - 1
    lane_result = []
    lane_flags = []
    for raw in (lane0, lane1):
        wide_bits, flags = oracle_result_cached(source_width, row["native_target"], raw,
                                                1 if fixed_rtz else rm)
        value, flags, _ = narrow_result(wide_bits, flags, row["native_target"], result_width)
        lane_result.append(value)
        lane_flags.append(flags)
    active = [i for i in range(2) if i >= vstart and i < vl and ((active_mask >> i) & 1)]
    expected_dest = sentinel
    for i in active:
        expected_dest &= ~(mask << (result_width * i))
        expected_dest |= lane_result[i] << (result_width * i)
    new_flags = 0
    for i in active:
        new_flags |= lane_flags[i]
    frm = rm if not fixed_rtz else 3
    fcsr = (frm << 5) | old_flags
    case["name"] = f"{row['helper']}_{row['label']}_rm{rm}_{'rtz' if fixed_rtz else 'dyn'}_m{active_mask}_vl{vl}_vs{vstart}_{'m2' if lmul2 else 'm1'}_old{old_flags}_lane1{lane1:x}"
    source_reg = 2
    if lmul2:
        dest = 4 if case["clause"] == "VFUNARY0" else 8
        source_reg = 2 if case["clause"] == "VFUNARY0" else 4
    case["initial"].update(vtype=hex(({8: 0, 16: 8}[result_width]) | (1 if lmul2 else 0)),
                           vl=hex(vl), vstart=hex(vstart), fcsr=hex(fcsr),
                           **{f"vr{source_reg}": hex(source), f"vr{dest}": hex(sentinel)},
                           vr0=hex(active_mask))
    source_emul = (1 if not lmul2 else 2) if case["clause"] == "VFUNARY0" else (2 if not lmul2 else 4)
    source_group = range(source_reg, source_reg + source_emul)
    for reg in source_group:
        case["initial"].setdefault(f"vr{reg}", "0x0")
    case["initial"]["vr10"] = hex(sentinel ^ 0x123456789abcdef0)
    if lmul2:
        case["initial"][f"vr{dest + 1}"] = hex(sentinel)
    case["observe"] = [f"vr{dest}"] + ([f"vr{dest + 1}"] if lmul2 else []) + [f"vr{reg}" for reg in source_group] + ["vr0", "vr10", "fcsr", "vstart", "mstatus"]
    case["expected"] = {f"vr{dest}": hex(expected_dest), "fcsr": hex((frm << 5) | old_flags | new_flags),
                        "vstart": "0x0", "mstatus": hex((1 << 63) | 0x6600)}
    if lmul2:
        case["expected"][f"vr{dest + 1}"] = hex(sentinel)
    for reg in source_group:
        case["expected"][f"vr{reg}"] = case["initial"][f"vr{reg}"]
    case["expected"].update(vr0=case["initial"]["vr0"], vr10=case["initial"]["vr10"])
    word = int(case["word"], 16)
    if active_mask != 3:
        word &= ~(1 << 25)
        case["expected_fields"]["0"] = "0x0"
    if lmul2:
        word = (word & ~(31 << 7)) | (dest << 7)
        word = (word & ~(31 << 20)) | (source_reg << 20)
        case["expected_fields"]["1"] = hex(source_reg)
        case["expected_fields"]["3"] = hex(dest)
    case["word"] = hex(word)
    case["source_bits"] = [hex(lane0), hex(lane1)]
    case["lane_expected"] = [hex(x) for x in lane_result]
    case["lane_flags"] = [hex(x) for x in lane_flags]
    case["active_lanes"] = active
    case["fixed_rtz"] = fixed_rtz
    return case


def scalar_case(row, base, source_width, result_width, rm, old_flags=0):
    case = copy.deepcopy(base)
    raw = row["source_bits"]
    bits = row["result_bits"]
    if result_width == 32 and (bits & (1 << 31)):
        bits |= 0xffffffff00000000  # RV64 FCVT.W and FCVT.WU both sign-extend.
    frm = 4
    case["name"] = f"{row['helper']}_{row['label']}_rm{rm}_old{old_flags}"
    case["word"] = hex((int(case["word"], 16) & ~(7 << 12)) | (rm << 12))
    case["expected_fields"]["1"] = RM_NAMES[rm]
    case["initial"].update(f1=hex(fp_box(raw, source_width)), fcsr=hex((frm << 5) | old_flags),
                           x3="0x0", x2="0x12345678")
    case["observe"] = ["x3", "f1", "x2", "fcsr", "mstatus"]
    case["expected"] = {"x3": hex(bits), "fcsr": hex((frm << 5) | old_flags | row["flags"]),
                        "mstatus": hex((1 << 63) | 0x6600) if row["flags"] & ~old_flags else "0x6600",
                        "f1": case["initial"]["f1"], "x2": case["initial"]["x2"]}
    case["source_bits"] = hex(raw)
    case["raw_result_width"] = result_width
    return case


ORACLE_CACHE = {}
ORACLE = None


def oracle_result_cached(width, target, raw, rm):
    key = (width, target, raw, rm)
    if key not in ORACLE_CACHE:
        ORACLE_CACHE[key] = oracle_result(ORACLE, *key)
    return ORACLE_CACHE[key]


def main():
    global ORACLE
    parser = argparse.ArgumentParser()
    parser.add_argument("--oracle", type=Path, default=ORACLE_DEFAULT)
    args = parser.parse_args()
    ORACLE = args.oracle.resolve()
    assert ORACLE.is_file()
    helpers = []
    rows = []
    scalar = []
    vector = []
    base_sources = set()
    reachability = []
    for helper, width, native_target, result_width in SPECS:
        is_narrow = helper.endswith("_pure")
        values = inputs(width, native_target, result_width)
        exponent = result_width if native_target.startswith("u") else result_width - 1
        finite_threshold = encoded(1 << exponent, width)
        reachable = finite_threshold is not None and finite(finite_threshold, width)
        reachability.append({"helper": helper, "finite_positive_overflow_input_exists": reachable,
                             "reason": "source exponent range" if not reachable else "power-of-two threshold is finite"})
        for label, raw in values.items():
            rounds = range(5) if label in ("one_half", "negative_one_half", "two_half",
                                            "negative_two_half", "negative_half", "positive_half") else (0,)
            for rm in rounds:
                wide_bits, wide_flags = oracle_result_cached(width, native_target, raw, rm)
                bits, flags, narrow_overflow = (narrow_result(wide_bits, wide_flags, native_target, result_width)
                                                if is_narrow else (wide_bits, wide_flags, False))
                row = dict(helper=helper, source_width=width, source_bits=raw, label=label,
                           rm=rm, native_target=native_target, result_width=result_width,
                           result_bits=bits, flags=flags, oracle_wide_bits=wide_bits,
                           oracle_wide_flags=wide_flags, narrow_overflow=narrow_overflow,
                           independent_rule="Berkeley SoftFloat plus RISC-V narrow saturation" if is_narrow else "Berkeley SoftFloat RISCV specialization")
                rows.append(row)
                helpers.append(f"{helper}\t3:{rm:x},{width}:{raw:x}\t0x{flags:02x}\t0x{bits:x}\t{result_width}")
        if is_narrow:
            target_kind = "XU" if native_target.startswith("u") else "X"
            clause, prefix = ("VFUNARY0", "FV") if helper == "riscv_f16ToI16_pure" or helper == "riscv_f16ToUi16_pure" else ("VFNUNARY0", "FNV")
            enum = f"{prefix}_CVT_{target_kind}_F"
            base_path, base = vector_base(clause, enum)
            base_sources.add(base_path)
            by_label = {row["label"]: row for row in rows if row["helper"] == helper and row["rm"] == 0}
            for label in ("exact_upper_integer", "exact_lower_integer",
                          "upper_boundary_below", "upper_boundary_at", "upper_fractional_overflow",
                          "lower_boundary_at", "lower_boundary_below", "maximum_finite",
                          "positive_qnan", "negative_qnan", "positive_inf", "negative_inf",
                          "negative_one"):
                if label not in by_label:
                    continue
                vector.append(vector_case(by_label[label], base, width, result_width, 0))
            for label in ("one_half", "negative_one_half"):
                for rm in range(5):
                    representative = next(row for row in rows if row["helper"] == helper
                                          and row["label"] == label and row["rm"] == rm)
                    vector.append(vector_case(representative, base, width, result_width, rm))
            representative = by_label["positive_qnan"]
            for kwargs in (dict(active_mask=0, vl=2), dict(active_mask=1, vl=2),
                           dict(active_mask=2, vl=2), dict(active_mask=3, vl=0),
                           dict(active_mask=3, vl=2, vstart=1),
                           dict(active_mask=3, vl=2, lmul2=True),
                           dict(active_mask=3, vl=2, old_flags=1),
                           dict(active_mask=3, vl=2, old_flags=16),
                           dict(active_mask=3, vl=2, lane1_raw=encoded(1.5, width))):
                vector.append(vector_case(representative, base, width, result_width, 0, **kwargs))
            rtz_path, rtz_base = vector_base(clause, f"{prefix}_CVT_RTZ_{target_kind}_F")
            base_sources.add(rtz_path)
            vector.append(vector_case(by_label["one_half"], rtz_base, width, result_width, 0,
                                      fixed_rtz=True))
        else:
            base_path, base = scalar_base(width, native_target)
            base_sources.add(base_path)
            by_label = {row["label"]: row for row in rows if row["helper"] == helper and row["rm"] == 0}
            for label in ("exact_upper_integer", "exact_lower_integer",
                          "upper_boundary_below", "upper_boundary_at",
                          "lower_boundary_at", "lower_boundary_below", "maximum_finite",
                          "minimum_finite", "positive_qnan", "negative_qnan", "positive_snan",
                          "negative_snan", "positive_inf", "negative_inf", "negative_one"):
                if label in by_label:
                    scalar.append(scalar_case(by_label[label], base, width, result_width, 0))
            for label in ("one_half", "negative_one_half"):
                for rm in range(5):
                    representative = next(row for row in rows if row["helper"] == helper
                                          and row["label"] == label and row["rm"] == rm)
                    scalar.append(scalar_case(representative, base, width, result_width, rm))
            scalar.append(scalar_case(by_label["positive_qnan"], base, width, result_width, 0,
                                      old_flags=16))
            scalar.append(scalar_case(by_label["positive_inf"], base, width, result_width, 0,
                                      old_flags=1))
    assert len({case["name"] for case in scalar}) == len(scalar)
    assert len({case["name"] for case in vector}) == len(vector)
    (HERE / "helpers.tsv").write_text("\n".join(helpers) + "\n")
    (HERE / "oracle-rows.json").write_text(json.dumps(rows, indent=2) + "\n")
    (HERE / "scalar-cases.json").write_text(json.dumps(scalar, indent=2) + "\n")
    (HERE / "vector-cases.json").write_text(json.dumps(vector, indent=2) + "\n")
    manifest = {"oracle_binary_sha256": digest(ORACLE),
                "oracle_source_sha256": digest(ROOT / "agents/float_support_review/oracle/oracle.cpp"),
                "source_cases": {str(path.relative_to(ROOT)): digest(path) for path in base_sources},
                "counts": {"helpers": len(helpers), "scalar": len(scalar), "vector": len(vector)},
                "reachability": reachability,
                "output_sha256": {name: digest(HERE / name) for name in
                                  ("helpers.tsv", "oracle-rows.json", "scalar-cases.json", "vector-cases.json")}}
    (HERE / "fixture-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(manifest["counts"])


if __name__ == "__main__":
    main()
