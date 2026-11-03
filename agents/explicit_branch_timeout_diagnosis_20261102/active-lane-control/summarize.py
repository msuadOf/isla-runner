#!/usr/bin/env python3
"""Audit completion and C-API solver checks from the frozen pair runs."""
from pathlib import Path
import hashlib
import json
import statistics

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(directory, pair, arm):
    record = json.loads((directory / "result.json").read_text())
    output_file = directory / "output/rv64_zVFUNARY0.json"
    output = json.loads(output_file.read_text())
    queries = [row.split("\t") for row in (directory / "queries.tsv").read_text().splitlines()]
    begins = [row for row in queries if row[0] == "begin"]
    ends = [row for row in queries if row[0] == "end"]
    times = dict(line.split("=", 1) for line in (directory / "time.txt").read_text().splitlines() if "=" in line)
    assert len(begins) == len(ends)
    assert record["exit_code"] == 0
    assert output["summary"]["status"] == "finished"
    assert all(output["summary"][key] == 0 for key in
               ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
                "omitted-cases", "model-query-timeouts", "pending-batches"))
    assert "fixed=17" in (directory / "seed.log").read_text()
    return {"pair": pair, "arm": arm, "cpu": record["cpu"],
            "exit_code": record["exit_code"], "status": output["summary"]["status"],
            "json_count": len(output["gen"]), "summary": output["summary"],
            "wall_s": float(times["wall_s"]), "user_s": float(times["user_s"]),
            "sys_s": float(times["sys_s"]), "maxrss_kb": int(times["maxrss_kb"]),
            "checks": len(ends), "unknown_checks": sum(row[6] == "0" for row in ends),
            "check_cumulative_s": sum(float(row[5]) for row in ends),
            "check_max_s": max(float(row[5]) for row in ends),
            "output_sha256": sha(output_file), "query_log_sha256": sha(directory / "queries.tsv")}


data = []
for pair in range(1, 6):
    for arm in "AB":
        directory = HERE / arm if pair == 1 else HERE / "repeat" / f"pair{pair}" / arm
        data.append(run(directory, pair, arm))

paired = []
for pair in range(2, 6):
    a = next(row for row in data if row["pair"] == pair and row["arm"] == "A")
    b = next(row for row in data if row["pair"] == pair and row["arm"] == "B")
    assert a["cpu"] == b["cpu"]
    paired.append({"pair": pair, "cpu": a["cpu"], "a_wall_s": a["wall_s"],
                   "b_wall_s": b["wall_s"], "b_over_a_wall": b["wall_s"] / a["wall_s"]})

summary = {"runs": data, "paired_same_core": paired,
           "paired_median_b_over_a_wall": statistics.median(row["b_over_a_wall"] for row in paired),
           "note": "Pair 1 used separate physical cores and is excluded from same-core ratios. Check count is not fork count."}
(HERE / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({"paired_median_b_over_a_wall": summary["paired_median_b_over_a_wall"],
                  "paired": paired}, indent=2))
