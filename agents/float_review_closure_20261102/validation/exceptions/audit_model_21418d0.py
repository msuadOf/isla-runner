#!/usr/bin/env python3
"""Recheck the final 21418d0 directed run's recorded raw evidence."""

import hashlib
import json
from pathlib import Path
import re
from run_directed import constrained_ir


HERE = Path(__file__).resolve().parent
RUN = HERE / "runs-model-21418d0-itrace"
INPUT_SHA = "44641223d4541b042a337c9adab6ac902f34d3af82f3835213f28b39cc247b19"
EXPECTED_SHA = "6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891"
SCRIPT_SHA = "613e0441923a42650165da75a14bed730704bb16d08f09cda056c65008d12cd9"
MODEL = "21418d0b0d4942fae20061ed580ee04aff4a8a61"
ISLA = "42000be47596ec088623881d03c0eadc5cf0ba27"
IR_SHA = "5514e98ee5566dbbcfa4f6dbafa9dbb1851c72dce4b52ca0c0a95a1c7fafff4a"
BIN_SHA = "acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d"
Z3_SHA = "899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970"
DELTA_SHA = "305d826ee485b4803ffe8cb747cc9e20f815897c3b2714415a51c00867459bd7"
PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
           "omitted-cases", "model-query-timeouts", "pending-batches", "sampled-paths")


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


expected = load(HERE / "expected.json")
names = {row["name"] for group in ("cases", "vectors", "bf16") for row in expected[group]}
assert len(names) == 315 and sha(HERE / "expected.json") == EXPECTED_SHA
launch = load(RUN / "launch.json")
assert launch["inputs_sha256"] == INPUT_SHA and launch["expected_sha256"] == EXPECTED_SHA
assert launch["script_sha256"] == SCRIPT_SHA
assert launch["model_commit"] == MODEL and launch["isla_commit"] == ISLA
assert launch["expected_source_commit"] == expected["model_commit"]
assert launch["model_delta_sha256"] == DELTA_SHA
assert launch["frozen_hashes"]["ir"] == IR_SHA and sha(RUN / "base.ir") == IR_SHA
assert launch["frozen_hashes"]["binary"] == BIN_SHA and sha(RUN / "isarch") == BIN_SHA
assert launch["z3_sha256"] == Z3_SHA
assert launch["cpus"] == [17, 29] and launch["workers"] == 2
assert launch["threads"] == 1 and launch["tactic"] == "qffp"
assert launch["timeout_seconds"] == 600
base_ir_text = (RUN / "base.ir").read_text()
summary = load(RUN / "summary.json")
assert (summary["count"], summary["completed"], summary["pass"]) == (315, 315, 315)
assert {row["name"] for row in summary["results"]} == names
assert all(row["status"] == "PASS" for row in summary["results"])

rows = []
assertions = 0
for name in sorted(names):
    dest = RUN / "runs" / name
    result = load(dest / "result.json")
    command = load(dest / "command.json")
    files = list((dest / "output").glob("*.json"))
    assert result["name"] == name and result["status"] == "PASS"
    assert result["exit_code"] == 0 and result["output_count"] == 1 and len(files) == 1
    assert result["output_sha256"] == sha(files[0])
    assert command["binary_sha256"] == BIN_SHA and command["base_ir_sha256"] == IR_SHA
    assert command["job"]["name"] == name and command["cpu"] in (17, 29)
    reconstructed = constrained_ir(base_ir_text, command["job"]["clause"], command["job"]["fields"])
    assert hashlib.sha256(reconstructed.encode()).hexdigest() == command["constrained_ir_sha256"]
    assert command["environment"]["ISLA_ABLATION_SEED"] == "17"
    seed_file = dest / "seed-intercept.log"
    seed_lines = seed_file.read_text().splitlines()
    assert result["seed"]["valid"] and result["seed_log_sha256"] == sha(seed_file)
    assert seed_lines and all(re.fullmatch(r"parameter=(seed|random_seed) original=\d+ fixed=17", line)
                              for line in seed_lines)
    assert any(line.startswith("parameter=random_seed ") for line in seed_lines)
    data = load(files[0])
    shown = data["summary"]
    assert shown["status"] == "finished" and shown["target-clause"] == "z" + command["job"]["clause"]
    assert all(key in shown and type(shown[key]) is int and shown[key] == 0 for key in PARTIAL)
    assert len(data["gen"]) == 1 and data["gen"][0]["ret_val"].startswith("Retire_Success")
    provenance = data["provenance"]["inputs"]
    assert provenance["-A"]["path"] == command["argv"][command["argv"].index("-A") + 1]
    assert provenance["-A"]["sha256"] == command["constrained_ir_sha256"]
    assert provenance["-C"]["path"] == command["argv"][command["argv"].index("-C") + 1]
    assert provenance["-C"]["sha256"] == sha(dest / "config.toml") == command["config_sha256"]
    inspection = result["inspection"]
    assert inspection["pass"] and inspection["summary"] == shown
    assert all(item["pass"] for item in inspection["assertions"])
    assert inspection["representations"]["encoding"]["status"] == "complete"
    assert inspection["representations"]["encoding"]["bit-length"] == 32
    assertions += len(inspection["assertions"])
    rows.append({"name": name, "output_sha256": result["output_sha256"],
                 "seed_log_sha256": result["seed_log_sha256"],
                 "config_sha256": command["config_sha256"],
                 "constrained_ir_sha256": command["constrained_ir_sha256"],
                 "assertions": len(inspection["assertions"]),
                 "seconds": result["seconds"]})

assert assertions == 33566
audit = {"scope": "21418d0 fixed-input directed oracle; not complete Clause coverage",
         "model_commit": MODEL, "isla_commit": ISLA, "inputs_sha256": INPUT_SHA,
         "expected_sha256": EXPECTED_SHA, "script_sha256": SCRIPT_SHA,
         "model_delta_sha256": DELTA_SHA, "ir_sha256": IR_SHA,
         "binary_sha256": BIN_SHA, "z3_sha256": Z3_SHA,
         "case_count": len(rows), "reconstructed_constraint_ir_count": len(rows),
         "assertions": assertions, "cases": rows}
(HERE / "audit-model-21418d0.json").write_text(json.dumps(audit, indent=2) + "\n")
print(f"PASS: {len(rows)} new-IR/new-binary cases and {assertions} recorded assertions")
