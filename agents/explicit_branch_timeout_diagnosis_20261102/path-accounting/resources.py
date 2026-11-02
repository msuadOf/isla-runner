#!/usr/bin/env python3
"""从 /proc/stat 定时快照计算指定核在实验期的非空闲比例。"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def usage(first, last):
    result = {}
    for cpu in ("cpu32", "cpu33", "cpu96", "cpu97"):
        a = first["cpu_stat"][cpu]
        b = last["cpu_stat"][cpu]
        total = sum(b[:8]) - sum(a[:8])
        idle = (b[3] + b[4]) - (a[3] + a[4])
        result[cpu] = {"busy_fraction": (total - idle) / total, "sampled_jiffies": total}
    return result


if __name__ == "__main__":
    rows = [json.loads(x) for x in (HERE / "final-monitor.jsonl").read_text().splitlines()]
    print(json.dumps({"first_elapsed_s": rows[0]["elapsed_s"], "last_elapsed_s": rows[-1]["elapsed_s"],
                      "cpu_usage": usage(rows[0], rows[-1])}, ensure_ascii=False, indent=2))
