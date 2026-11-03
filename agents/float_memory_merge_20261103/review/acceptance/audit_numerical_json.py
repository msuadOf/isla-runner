#!/usr/bin/env python3
"""用独立 SoftFloat 按实际机器字和 JSON 前态复算新输出。"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = ROOT / "agents/float_review_closure_20261102/review/acceptance/audit_actual_json.py"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("independent_actual_json", SOURCE)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    rows, skipped, failures = [], [], []
    paths = sorted(args.root.rglob("output/*.json"))
    for path in paths:
        data = json.loads(path.read_text())
        for index, entry in enumerate(data["gen"]):
            identity = {"path": str(path), "sha256": sha(path), "index": index}
            try:
                result = oracle.check_entry(entry)
                if result is None:
                    skipped.append({**identity, "instruction": entry["test-ins"]})
                else:
                    rows.append({**identity, **result})
                    if not result["pass"]:
                        failures.append({**identity, **result})
            except Exception as error:
                failures.append({**identity, "error": repr(error)})
    output = {"scope": "沿用既有独审算法，从实际机器字和前态调用独立SoftFloat；不读owner expected",
              "auditor_source_sha256": sha(SOURCE), "oracle_sha256": sha(oracle.ORACLE),
              "files": len(paths), "checked": len(rows), "skipped": skipped,
              "failures": failures, "rows": rows}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "rows"}, ensure_ascii=False))
    assert rows and not failures
    if args.expected_count is not None:
        assert len(rows) == args.expected_count and not skipped


if __name__ == "__main__":
    main()
