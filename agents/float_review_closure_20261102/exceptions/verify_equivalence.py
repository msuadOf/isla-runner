"""Finite exhaustive flag algebra and IEEE category-boundary checks.

The rounded tuple stands for the unchanged directed-bound calculation; all
eight possible Boolean outputs are included, including non-IEEE combinations.
"""

from itertools import product
import struct


def decode(bits, width):
    exponent_bits, fraction_bits = {16: (5, 10), 32: (8, 23), 64: (11, 52)}[width]
    sign = bool(bits >> (width - 1))
    exponent = (bits >> fraction_bits) & ((1 << exponent_bits) - 1)
    fraction = bits & ((1 << fraction_bits) - 1)
    special = exponent == (1 << exponent_bits) - 1
    return {
        "sign": sign,
        "zero": exponent == 0 and fraction == 0,
        "inf": special and fraction == 0,
        "nan": special and fraction != 0,
        "snan": special and fraction != 0 and (fraction >> (fraction_bits - 1)) == 0,
        "finite": not special,
    }


def samples(width):
    exponent_bits, fraction_bits = {16: (5, 10), 32: (8, 23), 64: (11, 52)}[width]
    inf = ((1 << exponent_bits) - 1) << fraction_bits
    one = ((1 << (exponent_bits - 1)) - 1) << fraction_bits
    qnan = inf | (1 << (fraction_bits - 1))
    snan = inf | 1
    sign = 1 << (width - 1)
    return [value | sign_bit for value in (0, one, inf, qnan, snan) for sign_bit in (0, sign)]


def reasons(op, a, b=None, c=None):
    if op == "add":
        return (a["inf"] and b["inf"] and a["sign"] != b["sign"],)
    if op == "sub":
        return (a["inf"] and b["inf"] and a["sign"] == b["sign"],)
    if op == "mul":
        return (a["zero"] and b["inf"], a["inf"] and b["zero"])
    if op == "div":
        return (
            a["zero"] and b["zero"],
            a["inf"] and b["inf"],
            a["finite"] and not a["zero"] and b["zero"],
        )
    if op == "sqrt":
        return (a["sign"] and not a["zero"] and not a["nan"],)
    assert op == "fma"
    valid_inf_product = (
        (a["inf"] and not b["nan"] and not b["zero"])
        or (b["inf"] and not a["nan"] and not a["zero"])
    )
    product_negative = a["sign"] != b["sign"]
    return (
        a["zero"] and b["inf"],
        a["inf"] and b["zero"],
        valid_inf_product and c["inf"] and product_negative != c["sign"],
    )


def valid(op, a, b=None, c=None):
    if op in ("add", "sub", "mul"):
        return a["finite"] and b["finite"]
    if op == "div":
        return a["finite"] and b["finite"] and not b["zero"]
    if op == "sqrt":
        negative_nonzero = a["sign"] and not a["zero"]
        return (a["finite"] and not negative_nonzero) or a["zero"]
    assert op == "fma"
    return a["finite"] and b["finite"] and c["finite"]


def old_flags(op, a, b, c, rounded):
    rs = reasons(op, a, b, c)
    invalid_nan = any(x["snan"] for x in (a, b, c) if x is not None)
    invalid = invalid_nan or any(rs[:2] if op == "div" else rs)
    dz = rs[2] if op == "div" else False
    gate = valid(op, a, b, c)
    return (invalid, dz, *(gate and flag for flag in rounded))


def new_flags(op, a, b, c, rounded):
    rs = reasons(op, a, b, c)
    invalid_nan = any(x["snan"] for x in (a, b, c) if x is not None)
    if op == "div":
        if rs[0] or rs[1]:
            return (True, False, False, False, False)
        if rs[2]:
            return (False, True, False, False, False)
    elif any(rs):
        return (True, False, False, False, False)
    if valid(op, a, b, c):
        return (invalid_nan, False, *rounded)
    return (invalid_nan, False, False, False, False)


def old_rounded(overflow, tiny, inexact):
    return (overflow, inexact and tiny, inexact)


def new_rounded(overflow, tiny, inexact):
    underflow = inexact and tiny
    if overflow:
        return (True, underflow, inexact)
    if underflow:
        return (False, True, inexact)
    if inexact:
        return (False, False, True)
    return (False, False, False)


counts = {op: 0 for op in ("add", "sub", "mul", "div", "sqrt", "fma")}
for width in (16, 32, 64):
    values = [decode(bits, width) for bits in samples(width)]
    for op in counts:
        groups = [values] * (3 if op == "fma" else 1 if op == "sqrt" else 2)
        for args in product(*groups):
            a = args[0]
            b = args[1] if len(args) > 1 else None
            c = args[2] if len(args) > 2 else None
            for rounded in product((False, True), repeat=3):
                old = old_flags(op, a, b, c, rounded)
                new = new_flags(op, a, b, c, rounded)
                assert old == new, (width, op, args, rounded, old, new)
                counts[op] += 1

for overflow, tiny, inexact in product((False, True), repeat=3):
    assert old_rounded(overflow, tiny, inexact) == new_rounded(overflow, tiny, inexact)

def round_toward_zero_bits(value, target_format):
    target_width = 16 if target_format == "e" else 32
    encoded = struct.pack(">" + target_format, value)
    nearest = struct.unpack(">" + target_format, encoded)[0]
    bits = int.from_bytes(encoded, "big")
    if abs(nearest) > abs(value):
        magnitude = bits & ((1 << (target_width - 1)) - 1)
        bits = (bits & (1 << (target_width - 1))) | (magnitude - 1)
    return bits


rod_examples = (
    (32, 16, 0x3F800000, 0x3C00),  # exact, even
    (32, 16, 0x3F802000, 0x3C01),  # exact, odd
    (32, 16, 0x3F800001, 0x3C01),  # inexact, RTZ even -> odd
    (32, 16, 0xBF800001, 0xBC01),  # negative inexact
    (64, 32, 0x3FF0000000000000, 0x3F800000),
    (64, 32, 0x3FF0000020000000, 0x3F800001),
    (64, 32, 0x3FF0000000000001, 0x3F800001),
    (64, 32, 0xBFF0000000000001, 0xBF800001),
)
for source_width, target_width, raw, expected in rod_examples:
    source_format = "f" if source_width == 32 else "d"
    target_format = "e" if target_width == 16 else "f"
    value = struct.unpack(">" + source_format, raw.to_bytes(source_width // 8, "big"))[0]
    base = round_toward_zero_bits(value, target_format)
    base_value = struct.unpack(">" + target_format, base.to_bytes(target_width // 8, "big"))[0]
    inexact = base_value != value
    jammed = base | 1 if inexact else base
    assert jammed == expected, (source_width, raw, base, jammed, expected)

print({"arithmetic_flag_cases": counts, "rounded_boolean_cases": 8, "rod_oracle_examples": len(rod_examples)})
