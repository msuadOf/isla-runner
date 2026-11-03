#!/usr/bin/env python3
"""Audit two immutable directed runs without overwriting first-run failures."""

from collections import Counter
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
FIRST = HERE / "runs-model-8ad5e8e"
RETRY = HERE / "runs-model-8ad5e8e-vd-retry"
INPUT_SHA = "25a1a624cb5dcac76a2261c470e198c64a75b20259322a1c7ee5d0572b83ec24"
EXPECTED_SHA = "6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891"
FIRST_SCRIPT_SHA = "6c24b0da54defa58cac14456b65ce1a313fffabab010e239924ed7938eafbfbd"
RETRY_SCRIPT_SHA = "43c967d0e212aedfea1b50b97e144440598b2dec99ad328dd38cb1596c8f1752"


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


expected = load(HERE / "expected.json")
cases = {row["name"]: row for group in ("cases", "vectors", "bf16") for row in expected[group]}
assert len(cases) == 315 and sha(HERE / "expected.json") == EXPECTED_SHA
first, retry = load(FIRST / "summary.json"), load(RETRY / "summary.json")
assert (first["completed"], first["count"], first["pass"]) == (315, 315, 305)
assert (retry["completed"], retry["count"], retry["pass"]) == (10, 10, 10)
first_status = {row["name"]: row["status"] for row in first["results"]}
retry_status = {row["name"]: row["status"] for row in retry["results"]}
assert set(first_status) == set(cases)
failures = {name for name, status in first_status.items() if status != "PASS"}
assert len(failures) == 10 and all(name.startswith("VD-") for name in failures)
assert set(retry_status) == failures and all(status == "PASS" for status in retry_status.values())
launches = [load(run / "launch.json") for run in (FIRST, RETRY)]
for launch, script_sha in zip(launches, (FIRST_SCRIPT_SHA, RETRY_SCRIPT_SHA)):
    assert launch["inputs_sha256"] == INPUT_SHA
    assert launch["expected_sha256"] == EXPECTED_SHA
    assert launch["script_sha256"] == script_sha
    assert launch["model_commit"] == expected["model_commit"]
    assert launch["workers"] == 2 and launch["cpus"] == [17, 29]
    assert launch["tactic"] == "qffp" and launch["threads"] == 1
assert launches[0]["frozen_hashes"] == launches[1]["frozen_hashes"]
assert launches[0]["z3_sha256"] == launches[1]["z3_sha256"]
assert sha(FIRST / "base.ir") == sha(RETRY / "base.ir") == launches[0]["frozen_hashes"]["ir"]
assert sha(FIRST / "isarch") == sha(RETRY / "isarch") == launches[0]["frozen_hashes"]["binary"]

assertion_count = 0
selected = []
status_counts = Counter()
for name in sorted(cases):
    run = RETRY if name in failures else FIRST
    row = load(run / "runs" / name / "result.json")
    assert row["name"] == name and row["status"] == "PASS" and row["exit_code"] == 0
    assert row["output_count"] == 1 and row["seed"]["valid"]
    seed_log = run / "runs" / name / "seed-intercept.log"
    assert row["seed_log_sha256"] == sha(seed_log)
    output_files = list((run / "runs" / name / "output").glob("*.json"))
    assert len(output_files) == 1 and row["output_sha256"] == sha(output_files[0])
    command = load(run / "runs" / name / "command.json")
    assert command["binary_sha256"] == launches[0]["frozen_hashes"]["binary"]
    assert command["base_ir_sha256"] == launches[0]["frozen_hashes"]["ir"]
    assert command["environment"]["ISLA_ABLATION_SEED"] == "17"
    assert command["cpu"] in (17, 29)
    inspection = row["inspection"]
    assert inspection["pass"] and inspection["summary"]["status"] == "finished"
    assert inspection["summary"]["target-clause"] == "z" + command["job"]["clause"]
    assert all(item["pass"] for item in inspection["assertions"])
    assertion_count += len(inspection["assertions"])
    status_counts["retry" if name in failures else "first"] += 1
    selected.append({"name": name, "batch": "retry" if name in failures else "first",
                     "output_sha256": row["output_sha256"],
                     "seed_log_sha256": row["seed_log_sha256"],
                     "assertions": len(inspection["assertions"])})

for name in sorted(failures):
    failed = load(FIRST / "runs" / name / "result.json")
    assert failed["exit_code"] == 1 and failed["output_count"] == 0
    assert not failed["seed"]["valid"]
    assert "Could not parse" in (FIRST / "runs" / name / "run.log").read_text()

report = {"scope": "directed fixed-input oracle, not complete Clause coverage",
          "model_commit": expected["model_commit"], "inputs_sha256": INPUT_SHA,
          "expected_sha256": EXPECTED_SHA,
          "first_script_sha256": FIRST_SCRIPT_SHA,
          "retry_script_sha256": RETRY_SCRIPT_SHA,
          "frozen_hashes": launches[0]["frozen_hashes"],
          "z3_sha256": launches[0]["z3_sha256"],
          "first_run": {"completed": 315, "pass": 305, "config_parse_failures": sorted(failures)},
          "retry_run": {"completed": 10, "pass": 10},
          "selected": dict(status_counts), "total_selected": len(selected),
          "total_assertions": assertion_count, "cases": selected}
(HERE / "combined-audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(f"PASS: {len(selected)} selected cases, {assertion_count} assertions; 305 first + 10 retry")
