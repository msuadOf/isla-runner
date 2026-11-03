#!/usr/bin/env python3
"""Summarize completed and pending diagnostic stages from the raw log."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
LOG = HERE / "run/run.log"
PATTERN = re.compile(r"^ENC_DIAG (check_start|check_end|start|end) id=(\d+) stage=(\S+)(.*)$")
VALUE = re.compile(r"(result|wall_s)=(\S+)")

pending = {}
completed = defaultdict(list)
statuses = defaultdict(Counter)
for line in LOG.read_text(errors="replace").splitlines():
    match = PATTERN.match(line)
    if not match:
        continue
    kind, number, stage, suffix = match.groups()
    key = (kind.startswith("check"), int(number))
    if kind in ("check_start", "start"):
        if key in pending:
            raise ValueError(f"duplicate start: {line}")
        pending[key] = stage
    else:
        if pending.pop(key, None) != stage:
            raise ValueError(f"unmatched end: {line}")
        fields = dict(VALUE.findall(suffix))
        completed[stage].append(float(fields["wall_s"]))
        if "result" in fields:
            statuses[stage][fields["result"]] += 1

summary = {
    "stages": {
        stage: {
            "completed": len(times), "wall_total_s": sum(times), "wall_max_s": max(times),
            "result_counts": dict(statuses[stage]),
        }
        for stage, times in sorted(completed.items())
    },
    "pending": [{"check": check, "id": number, "stage": stage} for (check, number), stage in pending.items()],
}
(HERE / "run/summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(summary, indent=2, ensure_ascii=False))
