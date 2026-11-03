#!/usr/bin/env python3
"""从新 flags 实际探针日志复算全部 300 组，不读取 expected 字段。"""
import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads((args.run / "result.json").read_text())
    assert result["seed"] == 17 and result["build_exit"] == 0
    labels = {"zero": (0, 0), "same_nv": (16, 16), "new_nv": (0, 16), "old_nx_new_nv": (1, 16), "new_multiple": (4, 19)}
    keys = {"rv64-v128", "rv64-v256", "rv64-v512", "rv64-default", "rv32-default"}
    assert result["runs"].keys() == keys
    rows, batches = [], []
    for key in sorted(keys):
        meta = result["runs"][key]
        path = args.run / (key + ".log")
        assert meta["exit"] == 0 and sha(path) == meta["log_sha256"]
        seedlog = args.run / (key + ".seed.log")
        assert sha(seedlog) == meta["seed_log_sha256"]
        seedlines = seedlog.read_text().splitlines()
        assert seedlines and all(re.fullmatch(r"parameter=(?:seed|random_seed) original=\d+ fixed=17", line) for line in seedlines)
        seen = set()
        for line in path.read_text().splitlines():
            if not line.startswith("PASS ") or line.startswith("PASS total="):
                continue
            _, label, *fields = line.split()
            values = dict(field.split("=", 1) for field in fields)
            number = lambda name: int(values[name], 0)
            old, incoming = labels[label]
            xlen = 32 if key == "rv32-default" else 64
            assert number("xlen") == xlen
            sd, fsmask = 1 << (xlen - 1), 3 << 13
            fs, other, oldsd = number("fs"), number("other"), values["initial_sd"] == "true"
            initial = other | (sd if oldsd else 0) | (fs << 13)
            assert number("initial_mstatus") == initial
            assert number("old_fcsr") == 0x123456a0 | old and number("incoming") == incoming
            changed = bool(incoming & ~old)
            assert number("fcsr") == 0x123456a0 | old | incoming
            assert number("mstatus") == (initial | fsmask | sd if changed else initial)
            identity = (label, fs, oldsd, other)
            assert identity not in seen
            seen.add(identity)
            rows.append({"ir": key, "label": label, "fs": fs, "old_sd": oldsd, "other": hex(other), "changed": changed})
        sentinel = 0xa000000a02000600 & ~sd & ~fsmask
        assert seen == set(itertools.product(labels, [1, 2, 3], [False, True], [0, sentinel]))
        batches.append({"ir": key, "log_sha256": sha(path), "states": len(seen)})
    assert len(rows) == 300
    output = {"scope": "实际accrue_fflags探针数值300组；callback仅静态IR合同，非动态callback观测",
              "result_sha256": sha(args.run / "result.json"), "binary_sha256": result["binary_sha256"],
              "rows": rows, "batches": batches, "count": 300, "pass": True}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
