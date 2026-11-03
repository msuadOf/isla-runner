#!/usr/bin/env python3
"""核最终源码对应 Rust 全库/集成测试和五 IR 的26步及104负控日志。"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validation = args.candidate / "agents/float_memory_merge_20261103/validation"
    integration = validation / "integration"
    source = json.loads((validation / "build/isla-source-4d085b14.json").read_text())
    assert all(sha(Path(source["root"]) / name) == digest for name, digest in source["files"].items())
    logs = []
    for filename, count in (("isla-lib-4d085b14-default.log", 394), ("workspace-lib-4d085b14-default.log", 610),
                            ("workspace-tests-4d085b14-default.log", 665)):
        path = integration / filename
        text = path.read_text()
        assert "test result: FAILED" not in text and "SMT tactic 未初始化" not in text
        summaries = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;", text)
        assert summaries and sum(int(row[0]) for row in summaries) == count
        assert all(all(int(field) == 0 for field in row[1:]) for row in summaries)
        logs.append({"path": filename, "sha256": sha(path), "passed": count, "groups": len(summaries)})
    directory = integration / "ir-all-4d085b14"
    checks = json.loads((directory / "checks.json").read_text())
    expected = {"build", "migration-conflicts", "nan-unbox-branches", "explicit-semantic-branches", "special-semantic-branches", "float-closure-branches"}
    expected |= {name + "-" + stage for name in ("rv64d", "rv32d", "rv64d_v128_e64", "rv64d_v256_e64", "rv64d_v512_e64") for stage in ("wrap", "helpers", "state", "guard")}
    assert len(checks) == 26 and {row["label"] for row in checks} == expected
    irlogs = []
    for row in checks:
        assert row["exit"] == 0
        path = directory / (row["label"] + ".log")
        assert path.is_file()
        irlogs.append({"label": row["label"], "sha256": sha(path), "exit": 0})
    negatives = json.loads((integration / "negative-104-4d085b14.json").read_text())
    assert negatives["count"] == len(negatives["rows"]) == 104
    assert all(row["result"] == "rejected" and row["detail"] for row in negatives["rows"])
    assert negatives["ir_sha256"] == sha(args.candidate / "isla/ir/rv64d_v128_e64.ir")
    assert negatives["checker_sha256"] == sha(args.candidate / "isla/test/float_ir/check_float_closure_branches.py")
    output = {"scope": "最终源码快照与实际完整测试日志/26步/104负控核对；独立重跑104另留收据",
              "source_manifest_sha256": sha(validation / "build/isla-source-4d085b14.json"),
              "rust": logs, "ir_checks_sha256": sha(directory / "checks.json"), "ir_logs": irlogs,
              "negative104_sha256": sha(integration / "negative-104-4d085b14.json"), "pass": True}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "ir_logs"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
