#!/usr/bin/env python3
"""独立读取两个工具链的实际 ELF .text，不信任汇编检查器的 expected/actual 字段。"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from audit_schema_union_json import number


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def text_section(path):
    raw = path.read_bytes()
    assert raw[:6] == b"\x7fELF\x02\x01"
    assert struct.unpack_from("<H", raw, 18)[0] == 243
    offset = struct.unpack_from("<Q", raw, 40)[0]
    size, count, string_index = struct.unpack_from("<HHH", raw, 58)
    headers = [struct.unpack_from("<IIQQQQIIQQ", raw, offset + index * size) for index in range(count)]
    strings_header = headers[string_index]
    strings = raw[strings_header[4]:strings_header[4] + strings_header[5]]
    matches = [header for header in headers if strings[header[0]:].split(b"\0", 1)[0] == b".text"]
    header, = matches
    return raw[header[4]:header[4] + header[5]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-checks", type=int, default=54)
    args = parser.parse_args()
    receipt = read(args.run / "result.json")
    for tool in receipt["toolchains"].values():
        assert sha(Path(tool["binary"])) == tool["sha256"]
    rows = []
    for case in receipt["cases"]:
        source = Path(case["source"])
        assert sha(source) == case["source_sha256"]
        actual = read(source)["gen"]
        directory = args.run / case["case"]
        checks = read(directory / "results.json")
        assert checks["sha256"] == sha(source)
        for check in checks["checks"]:
            entry = actual[check["index"]]
            encoding = entry["instruction-representations"]["encoding"]
            expected = number(entry["test-ins-encdec"]).to_bytes(encoding["bit-length"] // 8, "little")
            assert check["exit"] == 0 and check["expected_rejection"] is False
            name = f'{check["index"]}-{check["driver"]}-{check["kind"]}'
            obj = directory / (name + ".o")
            assert text_section(obj) == expected
            assert (directory / (name + ".bin")).read_bytes() == expected
            text = (directory / (name + ".s")).read_text()
            assert text == ".text\n.option " + ("rvc" if encoding["bit-length"] == 16 else "norvc") + "\n" + check["text"] + "\n"
            if check["kind"] == "mnemonic":
                assert check["text"] == entry["test-ins"]
            elif check["kind"] == "insn":
                assert check["text"] == entry["instruction-representations"]["insn"]["text"]
            else:
                assert check["text"] == ".byte " + ", ".join("0b" + format(byte, "08b") for byte in expected)
            rows.append({"case": case["case"], "driver": check["driver"], "kind": check["kind"],
                         "object_sha256": sha(obj), "json_sha256": sha(source), "text_bytes": expected.hex()})
    assert len(rows) == args.expected_checks
    output = {"scope": "实际JSON × GCC/Clang × 三表示的ELF .text独立字节核对",
              "checks": len(rows),
              "receipt_sha256": sha(args.run / "result.json"), "toolchains": receipt["toolchains"], "rows": rows, "pass": True}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
