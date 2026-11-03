#!/usr/bin/env python3
"""完整外限结束后汇总原始路径、SMT、CPU 和退出账。"""

import json
from pathlib import Path
from collections import Counter

from analyze import analyze
from resources import usage

HERE = Path(__file__).resolve().parent


def time_values(path):
    text = path.read_text().replace("\\n", "\n")
    result = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            try:
                result[key] = float(value)
            except ValueError:
                continue
    return result


def main():
    finished = json.loads((HERE / "final-finished.json").read_text())
    rows = [json.loads(x) for x in (HERE / "final-monitor.jsonl").read_text().splitlines()]
    result = {"launch": finished, "cpu_usage": usage(rows[0], rows[-1]), "runs": {}}
    for name in ("flags-arithmetic", "sat"):
        directory = HERE / ("final-" + name)
        metrics = analyze(name)
        wall = time_values(directory / "time.txt")
        metrics["time"] = wall
        metrics["cpu_time_fraction_of_wall"] = (wall["user_s"] + wall["sys_s"]) / wall["wall_s"]
        metrics["exit_code"] = finished["runs"][name]["exit_code"]
        metrics["json_paths"] = [str(p.relative_to(HERE)) for p in (directory / "output").glob("*.json")]
        metrics["seed_log"] = (directory / "seed.log").read_text().splitlines()
        query_rows = [line.split("\t") for line in (directory / "queries.tsv").read_text().splitlines()]
        query_status = Counter(int(row[6]) for row in query_rows if len(row) == 8 and row[0] == "end")
        metrics["query_status"] = {"sat": query_status[1], "unsat": query_status[-1], "unknown": query_status[0]}
        pending = query_rows[-1]
        assert pending[0] == "begin" and len(pending) == 8
        metrics["pending_query"] = {"id": int(pending[1]), "kind": pending[2],
                                     "begin_monotonic": float(pending[4]),
                                     "launch_plus_wall_minus_begin_s": finished["monotonic"] + wall["wall_s"] - float(pending[4])}
        result["runs"][name] = metrics
    (HERE / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
