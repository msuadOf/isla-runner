#!/usr/bin/env python3
"""按执行器任务事件核算路径，按阶段汇总原始 Z3 调用。"""

import json
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent


def events(path):
    result = []
    if not path.exists():
        return result
    for line in path.read_text(errors="replace").splitlines():
        if not line.startswith("PATH_ACCOUNT "):
            continue
        _, stamp, *parts = line.split()
        try:
            result.append((float(stamp), " ".join(parts)))
        except ValueError:
            continue
    return result


def queries(path):
    result = []
    if not path.exists():
        return result
    for line in path.read_text().splitlines():
        fields = line.split("\t")
        if len(fields) != 8:
            continue
        stage, ident, kind, _, stamp, duration, status, _ = fields
        result.append((stage, int(ident), kind, float(stamp), float(duration), int(status)))
    return result


def analyze(name):
    directory = HERE / ("final-" + name)
    ev = events(directory / "run.log")
    counts = {}
    for _, kind in ev:
        counts[kind] = counts.get(kind, 0) + 1
    initial = counts.get("initial_task", 0)
    forks = counts.get("fork_child", 0)
    returned = sum(v for k, v in counts.items() if k.startswith("run_return"))
    done = counts.get("task_done", 0)
    active = int(counts.get("run_begin", 0) > done)
    outstanding = initial + forks - done
    aux_initial = counts.get("aux_initial_task", 0)
    aux_forks = counts.get("aux_fork_child", 0)
    aux_done = counts.get("aux_task_done", 0)
    aux_returned = sum(v for k, v in counts.items() if k.startswith("aux_run_return"))
    aux_active = int(counts.get("aux_run_begin", 0) > aux_done)
    q = queries(directory / "queries.tsv")
    begun = {ident: (kind, stamp) for stage, ident, kind, stamp, _, _ in q if stage == "begin"}
    phases = {"executor": {"checks": 0, "seconds": 0.0, "max_seconds": 0.0},
              "collector": {"checks": 0, "seconds": 0.0, "max_seconds": 0.0},
              "other": {"checks": 0, "seconds": 0.0, "max_seconds": 0.0}}
    return_intervals = []
    current = None
    last_kind = None
    for stamp, kind in ev:
        if kind == "run_begin":
            current = stamp
            last_kind = "executor"
        elif kind.startswith("run_return"):
            if current is not None:
                return_intervals.append((current, stamp, "executor"))
            current = stamp
            last_kind = "collector"
        elif kind == "task_done":
            if current is not None:
                return_intervals.append((current, stamp, last_kind))
            current = None
            last_kind = None
    if current is not None:
        return_intervals.append((current, float("inf"), last_kind))
    path_times = {}
    for phase in ("executor", "collector"):
        times = [hi - lo for lo, hi, kind in return_intervals if kind == phase and hi != float("inf")]
        path_times[phase] = {"completed_intervals": len(times), "total_s": sum(times),
                             "median_s": median(times) if times else None, "max_s": max(times) if times else None}
    for stage, ident, _, stamp, duration, _ in q:
        if stage != "end" or ident not in begun:
            continue
        begin_stamp = begun[ident][1]
        phase = next((kind for lo, hi, kind in return_intervals if lo <= begin_stamp <= hi), "other")
        slot = phases[phase]
        slot["checks"] += 1
        slot["seconds"] += duration
        slot["max_seconds"] = max(slot["max_seconds"], duration)
    return {"event_counts": counts, "main_forks": forks, "main_run_returned": returned, "main_collector_done": done,
            "outstanding_queue_plus_active": outstanding, "active": active, "queued_estimate": outstanding - active,
            "aux_initial_tasks": aux_initial, "aux_forks": aux_forks, "aux_run_returned": aux_returned,
            "aux_collector_done": aux_done, "aux_outstanding_queue_plus_active": aux_initial + aux_forks - aux_done,
            "aux_active": aux_active,
            "queries_begun": len(begun), "queries_finished": sum(stage == "end" for stage, *_ in q), "phase_queries": phases,
            "path_times": path_times, "active_phase": last_kind if current is not None else None,
            "first_event": ev[0] if ev else None, "last_event": ev[-1] if ev else None}


if __name__ == "__main__":
    print(json.dumps({name: analyze(name) for name in ("flags-arithmetic", "sat")}, ensure_ascii=False, indent=2))
