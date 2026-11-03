#!/usr/bin/env python3
"""从实际 JSON 复算并集字段、精确表示、访存顺序和选定指令语义。"""
import argparse
import hashlib
import json
import re
from pathlib import Path

COUNTERS = (
    "errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
    "assertion-filtered-paths", "omitted-cases", "model-query-timeouts",
    "encoding-filtered-paths", "pending-batches", "sampled-paths",
)
REQUIRED = ({f"x{i}" for i in range(1, 32)} | {f"f{i}" for i in range(32)}
            | {f"vr{i}" for i in range(32)} | {"fcsr", "mstatus", "vcsr", "vl", "vstart", "vtype"})


def number(value):
    if isinstance(value, int):
        return value
    match = re.fullmatch(r"\d+'h([0-9a-fA-F_]+)", value)
    return int(match[1].replace("_", ""), 16) if match else int(value, 0)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed(value, width):
    return value - (1 << width) if value >> (width - 1) else value


def memory_map(rows, modulus):
    result = {}
    for row in rows:
        address, size = number(row["address"]), row["bytes"]
        value = None if row["value"] is None else number(row["value"])
        for i in range(size):
            one = None if value is None else (value >> (8 * i)) & 255
            key = (address + i) % modulus
            if key in result and one is not None and result[key] is not None:
                assert result[key] == one, ("overlapping memory disagrees", key)
            result[key] = one
    return result


def audit_entry(entry):
    for key in ("isa-state", "isa-state-complete", "isa-state-post", "memory-events",
                "pre-memory", "post-memory", "ret_val", "instruction-representations"):
        assert key in entry, ("missing schema field", key)
    pre, post = entry["isa-state-complete"], entry["isa-state-post"]
    for key, value in entry["isa-state"].items():
        assert key in pre and pre[key] == value, ("assembly prestate differs from complete prestate", key, value, pre.get(key))
    for state in (pre, post):
        assert REQUIRED <= state.keys(), ("missing required register", REQUIRED - state.keys())
        assert "cur_privilege" in state
        for key in REQUIRED:
            number(state[key])
    assert not re.search(r"\b(?:Sym|Poison|Arbitrary)\b", entry["ret_val"]), entry["ret_val"]
    representations = entry["instruction-representations"]
    encoding, insn = representations["encoding"], representations["insn"]
    word = number(entry["test-ins-encdec"])
    bits = encoding["bit-length"]
    assert bits in (16, 32) and len(encoding["bits"]) == bits
    assert encoding["status"] == insn["status"] == "complete"
    assert int(encoding["bits"], 2) == int(encoding["hex"], 16) == word
    assert bytes.fromhex(encoding["bytes-le"]) == word.to_bytes(bits // 8, "little")
    assert re.fullmatch(r"\.insn\s+" + str(bits // 8) + r",\s*0x[0-9a-fA-F]+", insn["text"])
    assert int(insn["text"].split(",")[1].strip(), 16) == word
    assert representations["mnemonic"] == entry["test-ins"]
    xlen = int(entry["arch"]["xlen"])
    modulus, mask = 1 << xlen, (1 << xlen) - 1
    initial = memory_map(entry["pre-memory"], modulus)
    current = dict(initial)
    final = memory_map(entry["post-memory"], modulus)
    events = entry["memory-events"]
    reads, writes = [], []
    for event in events:
        address, size = number(event["address"]), event["bytes"]
        assert size > 0
        assert event["kind"] in ("read", "write"), event
        value = number(event["value"])
        if event["kind"] == "read":
            reads.append((address, size, value))
            for i in range(size):
                key, one = (address + i) % modulus, value >> (8 * i) & 255
                assert key in current and current[key] is not None, ("read initial byte absent", event, key)
                assert current[key] == one, ("event read differs from memory", event, key)
        else:
            data = number(event["data"])
            # 写回成功与写入数据分别编码，不能把响应的一位成功值当数据。
            assert value in (0, 1), event
            if not event["exclusive"] or value:
                writes.append((address, size, data))
                for i in range(size):
                    current[(address + i) % modulus] = data >> (8 * i) & 255
    assert current.keys() == final.keys(), ("pre/post footprint differs", current.keys(), final.keys())
    assert current == final, ("post-memory differs from event replay", current, final)

    semantic = None
    if "Retire_Success" in entry["ret_val"]:
        opcode, rd, rs1, rs2, funct3 = word & 127, word >> 7 & 31, word >> 15 & 31, word >> 20 & 31, word >> 12 & 7
        reg = lambda n: 0 if n == 0 else number(pre[f"x{n}"])
        if bits == 32 and opcode in (0x03, 0x07):
            size = 1 << (funct3 & 3)
            address = (reg(rs1) + signed(word >> 20, 12)) & mask
            assert len(reads) == 1 and reads[0][:2] == (address, size), (word, reads)
            value = reads[0][2]
            if opcode == 0x07:
                assert size in (4, 8)
                expected = value | (((1 << 64) - 1) ^ ((1 << (size * 8)) - 1))
                assert number(post[f"f{rd}"]) == expected
                assert pre["fcsr"] == post["fcsr"]
            elif rd:
                expected = (value if funct3 & 4 else signed(value, 8 * size)) & mask
                assert number(post[f"x{rd}"]) == expected
            semantic = "load-fp" if opcode == 7 else "load"
        elif bits == 32 and opcode in (0x23, 0x27):
            size = 1 << funct3
            immediate = (word >> 25 << 5) | (word >> 7 & 31)
            address = (reg(rs1) + signed(immediate, 12)) & mask
            value = (number(pre[f"f{rs2}"]) if opcode == 0x27 else reg(rs2)) & ((1 << (8 * size)) - 1)
            assert writes == [(address, size, value)], (word, writes, address, size, value)
            if opcode == 0x27:
                assert pre["fcsr"] == post["fcsr"]
            semantic = "store-fp" if opcode == 0x27 else "store"
        elif bits == 32 and opcode == 0x2f:
            size, operation, address = 1 << funct3, word >> 27, reg(rs1)
            widthmask = (1 << (8 * size)) - 1
            if operation == 3:
                assert len(writes) <= 1
                if rd:
                    assert number(post[f"x{rd}"]) == (0 if writes else 1)
                if writes:
                    assert writes == [(address, size, reg(rs2) & widthmask)]
            else:
                assert len(reads) == 1 and reads[0][:2] == (address, size)
                old, source = reads[0][2], reg(rs2) & widthmask
                if rd:
                    assert number(post[f"x{rd}"]) == signed(old, size * 8) & mask
                operations = {0: lambda: old + source, 1: lambda: source, 4: lambda: old ^ source,
                              8: lambda: old | source, 12: lambda: old & source,
                              16: lambda: min(signed(old, size * 8), signed(source, size * 8)),
                              20: lambda: max(signed(old, size * 8), signed(source, size * 8)),
                              24: lambda: min(old, source), 28: lambda: max(old, source)}
                if operation == 2:
                    assert not writes
                else:
                    assert operation in operations, operation
                    assert writes == [(address, size, operations[operation]() & widthmask)]
            semantic = "amo/lr/sc"
        elif bits == 16 and word & 3 == 0:
            compressed_op, base, dest = word >> 13, (word >> 7 & 7) + 8, (word >> 2 & 7) + 8
            if compressed_op in (3, 7):
                offset = (word >> 5 & 3) << 6 | (word >> 10 & 7) << 3
                address = (reg(base) + offset) & mask
                if compressed_op == 3:
                    assert len(reads) == 1 and reads[0][:2] == (address, 8)
                    assert number(post[f"x{dest}"]) == reads[0][2]
                else:
                    assert writes == [(address, 8, reg(dest))]
                semantic = "c-ld/sd-executeas"
            elif compressed_op == 0:
                offset = (word >> 6 & 1) << 2 | (word >> 5 & 1) << 3 | (word >> 11 & 3) << 4 | (word >> 7 & 15) << 6
                assert offset and number(post[f"x{dest}"]) == (reg(2) + offset) & mask
                semantic = "c-addi4spn-executeas"
    return {"word": hex(word), "bits": bits, "events": len(events), "semantic_check": semantic,
            "pre_null_bytes": sum(value is None for value in initial.values())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows, failures, partial = [], [], []
    files = sorted(args.root.rglob("output/*.json"))
    for path in files:
        data = json.loads(path.read_text())
        summary = data["summary"]
        clean = summary["status"] == "finished" and all(summary.get(key) == 0 for key in COUNTERS)
        if not clean:
            partial.append({"path": str(path), "summary": summary})
        for index, entry in enumerate(data["gen"]):
            try:
                row = audit_entry(entry)
                rows.append({"path": str(path), "sha256": sha(path), "index": index, **row})
            except Exception as error:
                failures.append({"path": str(path), "index": index, "error": repr(error)})
    out = {"scope": "实际JSON并集与顺序访存/选定机器字语义；partial单列，不推断全域覆盖",
           "files": len(files), "entries": len(rows), "failures": failures, "partial": partial, "rows": rows}
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: value for key, value in out.items() if key != "rows"}, ensure_ascii=False))
    assert rows and not failures


if __name__ == "__main__":
    main()
