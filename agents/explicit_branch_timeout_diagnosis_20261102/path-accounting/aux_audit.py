#!/usr/bin/env python3
"""逐条主路径核算增强版 A 对照的编码辅助任务。"""

import json
from pathlib import Path
import re
from collections import Counter

HERE = Path(__file__).resolve().parent


def audit(name):
    path = HERE / f"aux-{name}-A/run.log"
    groups = []
    prelude = Counter()
    current = None
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("PATH_ACCOUNT "):
            kind = " ".join(line.split()[2:])
            if kind == "run_begin":
                assert current is None
                current = Counter()
            elif kind == "task_done":
                assert current is not None
                groups.append(dict(current))
                current = None
            elif current is None and kind.startswith("aux_"):
                prelude[kind] += 1
            elif current is None:
                continue
            else:
                current[kind] += 1
        elif current is not None and "执行好一条路径，fork=" in line:
            match = re.search(r"ret_val=([^\s]+)", line)
            assert match
            current["ret_val"] = match.group(1)
    assert current is None
    class_counts = Counter()
    for group in groups:
        key = (group["ret_val"], group.get("aux_initial_task", 0), group.get("aux_fork_child", 0),
               group.get("aux_task_done", 0))
        class_counts[key] += 1
        assert group.get("aux_initial_task", 0) + group.get("aux_fork_child", 0) == group.get("aux_task_done", 0)
    return {"main_completed": len(groups), "prelude": dict(prelude),
            "classes": [{"ret_val": kind, "aux_initial_tasks": initial, "aux_forks": forks,
                         "aux_completed": done, "main_paths": count}
                        for (kind, initial, forks, done), count in sorted(class_counts.items())]}


if __name__ == "__main__":
    result = {name: audit(name) for name in ("flags-arithmetic", "sat")}
    (HERE / "aux-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
