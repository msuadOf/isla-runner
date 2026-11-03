#!/usr/bin/env python3
"""按实际 JSON 独立复算 VFMERGE/向量访存的 vstart 四边界。"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from audit_schema_union_json import audit_entry, number, COUNTERS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    labels = {"active": 0, "equal": 1, "greater": 2, "large": (1 << 64) - 1}
    launch = read(args.run / "launch.json")
    assert launch["cases"] == 8 and launch["timeout_seconds"] == 7200
    rows = []
    for family in ("vfmerge", "vector-load"):
        for label, start in labels.items():
            directory = args.run / (family + "-" + label)
            receipt = read(directory / "result.json")
            paths = list((directory / "output").glob("*.json"))
            assert len(paths) == 1 and receipt["exit"] == 0 and sha(paths[0]) == receipt["output_sha256"]
            data = read(paths[0])
            assert data["summary"]["status"] == "finished" and all(data["summary"][key] == 0 for key in COUNTERS)
            assert len(data["gen"]) == 1
            entry = data["gen"][0]
            audit_entry(entry, check_instruction=False)
            assert entry["ret_val"] == "Retire_Success(())"
            pre, post = entry["isa-state-complete"], entry["isa-state-post"]
            assert pre["cur_privilege"] == "Machine" and number(pre["vstart"]) == start and number(pre["vl"]) == 1
            assert number(post["vstart"]) == 0
            word = number(entry["test-ins-encdec"])
            rd, rs1, rs2 = word >> 7 & 31, word >> 15 & 31, word >> 20 & 31
            dest = "vr" + str(rd)
            initial = number(pre[dest])
            if family == "vfmerge":
                assert word == 0x5c005fd7 and number(pre["vtype"]) == 0x10
                source = number(pre["f" + str(rs1)]) if number(pre["vr0"]) & 1 else number(pre["vr" + str(rs2)])
                expected = (initial & ~0xffffffff) | (source & 0xffffffff) if start == 0 else initial
                assert not entry["memory-events"]
            else:
                assert word == 0x02008087 and number(pre["vtype"]) == 0
                if start == 0:
                    event, = entry["memory-events"]
                    assert event["kind"] == "read" and event["bytes"] == 1
                    assert number(event["address"]) == number(pre["x" + str(rs1)]) == 0x80000000
                    expected = (initial & ~255) | number(event["value"])
                else:
                    assert not entry["memory-events"]
                    expected = initial
            assert number(post[dest]) == expected
            assert number(post["mstatus"]) == number(pre["mstatus"]) | (1 << 63)
            for key in pre:
                if key not in (dest, "vstart", "mstatus"):
                    assert pre[key] == post[key], (family, label, key)
            argv = receipt["command"]
            assert argv[argv.index("--timeout") + 1] == argv[argv.index("--smt-timeout") + 1] == "7200s"
            assert "cur_privilege=Machine" in argv and any(value.startswith("vtype={bits=") for value in argv)
            for row in data["provenance"]["inputs"].values():
                assert sha(Path(row["path"])) == row["sha256"]
            seedlog = directory / "seed-intercept.log"
            assert sha(seedlog) == receipt["seed_log_sha256"]
            lines = seedlog.read_text().splitlines()
            assert lines and all(re.fullmatch(r"parameter=(?:seed|random_seed) original=\d+ fixed=17", line) for line in lines)
            rows.append({"family": family, "label": label, "start": hex(start), "word": hex(word),
                         "post_dest": hex(expected), "events": len(entry["memory-events"]), "json_sha256": sha(paths[0])})
    output = {"scope": "实际VFMERGE和VLSEG指令8定向边界；不改变reduction非零vstart非法约定，不声称全域覆盖",
              "binary_sha256": launch["binary_sha256"], "launch_sha256": sha(args.run / "launch.json"), "rows": rows, "pass": True}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
