#!/usr/bin/env python3
"""Freeze independent SoftFloat expected values for exception and ROD probes."""

import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORACLE = ROOT / ".tmp/unified-backend-crosscheck/oracle-build/oracle"
SOFTFLOAT = ORACLE.parent / "softfloat/libsoftfloat.a"
ORACLE_SOURCE = ROOT / "agents/float_support_review/oracle/oracle.cpp"
FORMATS = {
    "H": {"fmt": "f16", "width": 16, "zero": 0, "negzero": 0x8000,
          "one": 0x3C00, "two": 0x4000, "three": 0x4200,
          "negone": 0xBC00, "inf": 0x7C00, "neginf": 0xFC00,
          "snan": 0x7C01, "qnan": 0x7E00, "max": 0x7BFF,
          "minnormal": 0x0400, "minsub": 1,
          "fused_a": 0x3C01, "fused_c": 0xBC02},
    "S": {"fmt": "f32", "width": 32, "zero": 0, "negzero": 0x80000000,
          "one": 0x3F800000, "two": 0x40000000, "three": 0x40400000,
          "negone": 0xBF800000, "inf": 0x7F800000, "neginf": 0xFF800000,
          "snan": 0x7F800001, "qnan": 0x7FC00000, "max": 0x7F7FFFFF,
          "minnormal": 0x00800000, "minsub": 1,
          "fused_a": 0x3F800001, "fused_c": 0xBF800002},
    "D": {"fmt": "f64", "width": 64, "zero": 0, "negzero": 0x8000000000000000,
          "one": 0x3FF0000000000000, "two": 0x4000000000000000,
          "three": 0x4008000000000000, "negone": 0xBFF0000000000000,
          "inf": 0x7FF0000000000000, "neginf": 0xFFF0000000000000,
          "snan": 0x7FF0000000000001, "qnan": 0x7FF8000000000000,
          "max": 0x7FEFFFFFFFFFFFFF, "minnormal": 0x0010000000000000,
          "minsub": 1, "fused_a": 0x3FF0000000000001,
          "fused_c": 0xBFF0000000000002},
}
NV, DZ, OF, UF, NX = 16, 8, 4, 2, 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def query(op, fmt, rm, a, b=None, c=None, dst=None):
    argv = [str(ORACLE), "--op", op, "--fmt", fmt, "--rm", str(rm), "--a", hex(a)]
    if b is not None:
        argv += ["--b", hex(b)]
    if c is not None:
        argv += ["--c", hex(c)]
    if dst is not None:
        argv += ["--dst", dst]
    result = json.loads(subprocess.check_output(argv, text=True))
    return {"argv": argv[1:], "bits": int(result["result_bits"], 16),
            "flags": int(result["flags"], 16), "raw": result}


def canonical(bits, width):
    shift = {16: 10, 32: 23, 64: 52}[width]
    exp_bits = {16: 5, 32: 8, 64: 11}[width]
    exponent = (bits >> shift) & ((1 << exp_bits) - 1)
    mantissa = bits & ((1 << shift) - 1)
    return {16: 0x7E00, 32: 0x7FC00000, 64: 0x7FF8000000000000}[width] if exponent == (1 << exp_bits) - 1 and mantissa else bits


cases = []
def add(name, family, width, op, fmt, rm, a, b=None, c=None, dst=None,
        required=0, forbidden=0, reason=""):
    value = query(op, fmt, rm, a, b, c, dst)
    assert value["flags"] & required == required, (name, value)
    assert value["flags"] & forbidden == 0, (name, value)
    cases.append({"name": name, "family": family, "width": width, "op": op,
                  "fmt": fmt, "dst": dst, "rm": rm, "a": hex(a),
                  "b": None if b is None else hex(b),
                  "c": None if c is None else hex(c),
                  "reason": reason, "expected_bits": hex(canonical(value["bits"], width)),
                  "oracle_raw_bits": hex(value["bits"]), "expected_flags": hex(value["flags"]),
                  "oracle_argv": value["argv"]})


for tag, f in FORMATS.items():
    fmt, width = f["fmt"], f["width"]
    special = [
        ("add-inf-cancel", "add", "inf", "neginf", NV, DZ, "opposite infinities"),
        ("add-inf-valid", "add", "inf", "inf", 0, NV, "same-sign infinity"),
        ("sub-inf-cancel", "sub", "inf", "inf", NV, DZ, "same-sign infinities"),
        ("sub-inf-valid", "sub", "inf", "neginf", 0, NV, "opposite infinities"),
        ("mul-zero-inf", "mul", "zero", "inf", NV, DZ, "zero times infinity, left zero"),
        ("mul-inf-zero", "mul", "inf", "zero", NV, DZ, "zero times infinity, right zero"),
        ("mul-negzero-neginf", "mul", "negzero", "neginf", NV, DZ, "negative zero times negative infinity"),
        ("mul-neginf-negzero", "mul", "neginf", "negzero", NV, DZ, "negative infinity times negative zero"),
        ("mul-inf-valid", "mul", "inf", "one", 0, NV, "infinity times finite nonzero"),
        ("div-zero-zero", "div", "zero", "zero", NV, DZ, "zero over zero"),
        ("div-inf-inf", "div", "inf", "inf", NV, DZ, "infinity over infinity"),
        ("div-one-poszero", "div", "one", "zero", DZ, NV, "finite nonzero over positive zero"),
        ("div-one-negzero", "div", "one", "negzero", DZ, NV, "finite nonzero over negative zero"),
        ("div-inf-zero", "div", "inf", "zero", 0, DZ | NV, "infinity over zero"),
        ("div-inf-one", "div", "inf", "one", 0, DZ | NV, "infinity over finite nonzero"),
        ("div-zero-one", "div", "zero", "one", 0, DZ | NV, "zero over finite nonzero"),
        ("add-snan-left", "add", "snan", "one", NV, 0, "signaling NaN left source"),
        ("add-snan-right", "add", "one", "snan", NV, 0, "signaling NaN right source"),
        ("add-qnan-left", "add", "qnan", "one", 0, NV, "quiet NaN left source"),
        ("add-qnan-right", "add", "one", "qnan", 0, NV, "quiet NaN right source"),
    ]
    for label, op, left, right, required, forbidden, reason in special:
        add(f"{tag}-{label}", "scalar", width, op, fmt, 0,
            f[left], f[right], required=required, forbidden=forbidden, reason=reason)
    for label, operand, required, forbidden in [
        ("sqrt-negone", "negone", NV, 0),
        ("sqrt-neginf", "neginf", NV, 0),
        ("sqrt-negzero", "negzero", 0, NV),
        ("sqrt-poszero", "zero", 0, NV),
        ("sqrt-one", "one", 0, NV),
        ("sqrt-snan", "snan", NV, 0),
        ("sqrt-qnan", "qnan", 0, NV),
    ]:
        add(f"{tag}-{label}", "scalar", width, "sqrt", fmt, 0,
            f[operand], required=required, forbidden=forbidden, reason=label)
    for label, a, b, c, required, forbidden in [
        ("fma-zero-inf", "zero", "inf", "one", NV, DZ),
        ("fma-inf-zero", "inf", "zero", "one", NV, DZ),
        ("fma-inf-cancel", "inf", "one", "neginf", NV, DZ),
        ("fma-inf-valid", "inf", "one", "inf", 0, NV),
        ("fma-snan-a", "snan", "one", "one", NV, 0),
        ("fma-snan-b", "one", "snan", "one", NV, 0),
        ("fma-snan-c", "one", "one", "snan", NV, 0),
        ("fma-qnan-c", "one", "one", "qnan", 0, NV),
    ]:
        add(f"{tag}-{label}", "scalar", width, "fma", fmt, 0,
            f[a], f[b], f[c], required=required, forbidden=forbidden, reason=label)
    for rm in range(5):
        add(f"{tag}-mul-overflow-rm{rm}", "scalar", width, "mul", fmt, rm,
            f["max"], f["two"], required=OF | NX, forbidden=NV | DZ,
            reason="finite rounded overflow")
        add(f"{tag}-mul-underflow-rm{rm}", "scalar", width, "mul", fmt, rm,
            f["minnormal"], f["minnormal"], required=UF | NX, forbidden=NV | DZ,
            reason="finite rounded underflow")
        add(f"{tag}-div-inexact-rm{rm}", "scalar", width, "div", fmt, rm,
            f["one"], f["three"], required=NX, forbidden=NV | DZ | OF | UF,
            reason="finite inexact")
        add(f"{tag}-fma-fused-rm{rm}", "scalar", width, "fma", fmt, rm,
            f["fused_a"], f["fused_a"], f["fused_c"], forbidden=NV | DZ,
            reason="single fused multiply-add witness")
        fused = cases[-1]
        mul = query("mul", fmt, rm, f["fused_a"], f["fused_a"])
        split = query("add", fmt, rm, mul["bits"], f["fused_c"])
        fused["split_bits"] = hex(canonical(split["bits"], width))
        fused["split_accumulated_flags"] = hex(mul["flags"] | split["flags"])
        assert (int(fused["expected_bits"], 16), int(fused["expected_flags"], 16)) != (
            int(fused["split_bits"], 16), int(fused["split_accumulated_flags"], 16)), fused

ROD = [
    ("S-to-H", "f32", "f16", 16, {
        "exact-even": 0x3F800000, "exact-odd": 0x3F802000,
        "inexact-even": 0x3F800001, "inexact-odd": 0x3F802001,
        "negative-inexact": 0xBF800001, "tiny": 0x00000001,
        "overflow": 0x47800000, "poszero": 0x00000000,
        "negzero": 0x80000000, "inf": 0x7F800000,
        "snan": 0x7F800001, "qnan": 0x7FC00000}),
    ("D-to-S", "f64", "f32", 32, {
        "exact-even": 0x3FF0000000000000, "exact-odd": 0x3FF0000020000000,
        "inexact-even": 0x3FF0000000000001, "inexact-odd": 0x3FF0000020000001,
        "negative-inexact": 0xBFF0000000000001, "tiny": 0x0000000000000001,
        "overflow": 0x47F0000000000000, "poszero": 0,
        "negzero": 0x8000000000000000, "inf": 0x7FF0000000000000,
        "snan": 0x7FF0000000000001, "qnan": 0x7FF8000000000000}),
]
for label, src, dst, width, values in ROD:
    for kind, a in values.items():
        required = NX if kind.startswith("inexact") or kind in ("negative-inexact", "tiny", "overflow") else NV if kind == "snan" else 0
        forbidden = NV if kind != "snan" else 0
        add(f"{label}-rod-{kind}", "rod", width, "fp_to_fp", src, 6, a,
            dst=dst, required=required, forbidden=forbidden, reason=kind)
        if kind in ("exact-even", "exact-odd", "inexact-even", "inexact-odd", "tiny", "overflow",
                    "poszero", "negzero", "inf", "snan", "qnan"):
            for rm in (range(5) if kind not in ("poszero", "negzero", "inf", "snan", "qnan") else (0,)):
                add(f"{label}-ordinary-{kind}-rm{rm}", "ordinary-convert", width,
                    "fp_to_fp", src, rm, a, dst=dst, reason=kind)

vectors = []
for tag, f in FORMATS.items():
    scenarios = [
        ("add-inf-cancel", "add", ["inf", "one"], ["neginf", "one"], (1, 2, 3)),
        ("mul-invalid-overflow", "mul", ["zero", "max"], ["inf", "two"], (1, 2, 3)),
        ("div-nv-dz", "div", ["zero", "one"], ["zero", "zero"], (0, 1, 2, 3)),
    ]
    for label, op, aa, bb, masks in scenarios:
        for mask in masks:
            flags, lanes = 0, []
            for lane in range(2):
                active = bool(mask & (1 << lane))
                if active:
                    expected = query(op, f["fmt"], 0, f[aa[lane]], f[bb[lane]])
                    bits = canonical(expected["bits"], f["width"])
                    flags |= expected["flags"]
                else:
                    expected, bits = None, 0
                lanes.append({"lane": lane, "active": active,
                              "bits": hex(bits),
                              "flags": None if expected is None else hex(expected["flags"]),
                              "oracle_argv": None if expected is None else expected["argv"]})
            vectors.append({"name": f"V{tag}-{label}-mask{mask}", "format": tag,
                            "width": f["width"], "op": op, "rm": 0,
                            "a": [hex(f[x]) for x in aa], "b": [hex(f[x]) for x in bb],
                            "vl": 2, "mask": mask, "lanes": lanes,
                            "expected_flags": hex(flags)})

bf16 = []
for form in ("VV", "VF"):
    for label, a, b, acc, vl, mask, modes in [
        ("fused", [0x5F80, 0x5F80], [0x5F80, 0x5F80], [0xFF7FFFFF, 0xFF7FFFFF], 2, 3, range(5)),
        ("snan-a", [0x7F81, 0x3F80], [0x3F80, 0x3F80], [0, 0], 2, 3, [0]),
        ("snan-b", [0x3F80, 0x3F80], [0x7F81, 0x3F80], [0, 0], 2, 3, [0]),
        ("snan-acc", [0x3F80, 0x3F80], [0x3F80, 0x3F80], [0x7F800001, 0], 2, 3, [0]),
        ("multi-mask0", [0x7F81, 0x7F7F], [0x7F7F, 0x7F7F], [0, 0], 2, 0, [0]),
        ("multi-mask1", [0x7F81, 0x7F7F], [0x7F7F, 0x7F7F], [0, 0], 2, 1, [0]),
        ("multi-mask2", [0x7F81, 0x7F7F], [0x7F7F, 0x7F7F], [0, 0], 2, 2, [0]),
        ("multi-mask3", [0x7F81, 0x7F7F], [0x7F7F, 0x7F7F], [0, 0], 2, 3, [0]),
        ("vl0", [0x7F81, 0x7F81], [0x7F81, 0x7F81], [0x7F800001, 0x7F800001], 0, 3, [0]),
    ]:
        for rm in modes:
            flags = 0
            lanes = []
            for lane in range(2):
                active = lane < vl and bool(mask & (1 << lane))
                if active:
                    operand_b = b[0] if form == "VF" else b[lane]
                    expected = query("fma", "f32", rm, a[lane] << 16, operand_b << 16, acc[lane])
                    flags |= expected["flags"]
                    bits = canonical(expected["bits"], 32)
                    if label == "fused":
                        mul = query("mul", "f32", rm, a[lane] << 16, operand_b << 16)
                        split = query("add", "f32", rm, mul["bits"], acc[lane])
                        assert (bits, expected["flags"]) != (
                            canonical(split["bits"], 32), mul["flags"] | split["flags"])
                else:
                    expected, bits = None, acc[lane]
                lanes.append({"lane": lane, "active": active, "bits": hex(bits),
                              "flags": None if expected is None else hex(expected["flags"]),
                              "oracle_argv": None if expected is None else expected["argv"]})
            bf16.append({"name": f"BF16-{form}-{label}-rm{rm}", "form": form,
                         "case": label, "rm": rm, "a": [hex(x) for x in a],
                         "b": [hex(x) for x in b], "acc": [hex(x) for x in acc],
                         "vl": vl, "mask": mask, "lanes": lanes,
                         "expected_flags": hex(flags)})

manifest = {"model_commit": "8ad5e8e9e0fc2a567a3b989a3738698f5c520bde",
            "oracle_binary_sha256": sha(ORACLE), "oracle_source_sha256": sha(ORACLE_SOURCE),
            "softfloat_archive_sha256": sha(SOFTFLOAT),
            "scalar_and_rod_cases": len(cases), "vector_cases": len(vectors),
            "bf16_cases": len(bf16), "cases": cases, "vectors": vectors, "bf16": bf16}
(HERE / "expected.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Prepared {len(cases)} scalar/ROD, {len(vectors)} vector, and {len(bf16)} BF16 cases via independent SoftFloat")
