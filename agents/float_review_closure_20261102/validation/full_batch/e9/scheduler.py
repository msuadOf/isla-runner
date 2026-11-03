#!/usr/bin/env python3
"""Schedule the frozen full-domain Clause batch using validation/run_clause.py."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
VALIDATION = HERE.parents[1]
TOPIC = VALIDATION.parent
ROOT = TOPIC.parents[1]
HARNESS = VALIDATION / "run_clause.py"
TEMPLATE = VALIDATION / "inputs.template.json"
PRIORITY = [
    "F_BIN_RM_TYPE_S", "VFUNARY0", "VFNUNARY0", "F_UN_RM_FX_TYPE_D",
    "VFUNARY1", "RFVVTYPE", "RFWVVTYPE", "VFWMACCBF16_VV",
    "VFWMACCBF16_VF", "VFNCVTBF16_F_F_W", "VFWCVTBF16_F_F_V",
]
POLL_SECONDS = 30
DISK_MIN_FREE_BYTES = 20 * 1024**3
DISK_FALLBACK_JOB_BYTES = 1024**3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_jobs(inputs):
    data = json.loads(inputs.read_text())
    template = json.loads(TEMPLATE.read_text())
    affected_item = data.get("affected_manifest")
    if not isinstance(affected_item, dict):
        if data.get("model_commit", "").startswith("<"):
            affected_path = HERE / "affected-clauses.json"
            affected_sha = digest(affected_path)
        else:
            raise ValueError("冻结inputs缺少affected_manifest")
    else:
        affected_path = (ROOT / affected_item["path"]).resolve(strict=True)
        affected_sha = affected_item["sha256"]
        if digest(affected_path) != affected_sha:
            raise ValueError("affected_manifest哈希不符")
    closure = json.loads(affected_path.read_text())
    jobs = set(data.get("jobs", {}))
    expected = set(template["jobs"])
    affected = set(closure["affected_clauses"])
    if jobs != expected or len(jobs) != 77:
        raise ValueError(f"jobs须等于模板77条，missing={sorted(expected-jobs)}, extra={sorted(jobs-expected)}")
    if not affected <= jobs or len(affected) != 64:
        raise ValueError("64条受影响Clause未完整纳入77条批次")
    if (closure.get("source_mode") != "committed_component_heads" or
            closure.get("model_dirty") is not False or closure.get("isla_dirty") is not False or
            closure.get("affected_count") != len(affected)):
        raise ValueError("静态闭包来源、clean或分母不符")
    if (not str(data.get("model_commit", "")).startswith("<") and
            (data.get("model_commit") != closure.get("model_commit") or
             data.get("isla_commit") != closure.get("isla_commit"))):
        raise ValueError("冻结inputs组件版本与64条影响闭包版本不一致")
    return (data, sorted(jobs, key=lambda name: (name not in PRIORITY, PRIORITY.index(name) if name in PRIORITY else 0, name)),
            sorted(affected), sorted(jobs - affected), affected_path, affected_sha)


def cpu_list(value):
    result = []
    for part in value.split(","):
        if "-" in part:
            left, right = map(int, part.split("-", 1))
            result.extend(range(left, right + 1))
        else:
            result.append(int(part))
    return sorted(set(result))


def sibling_group(cpu):
    path = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
    return tuple(cpu_list(path.read_text().strip()))


def cpu_snapshot():
    result = {}
    for line in Path("/proc/stat").read_text().splitlines():
        fields = line.split()
        if fields and re.fullmatch(r"cpu\d+", fields[0]):
            cpu = int(fields[0][3:])
            nums = [int(x) for x in fields[1:]]
            idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
            result[cpu] = (sum(nums), idle)
    return result


def cpu_load(delay=1.0):
    before = cpu_snapshot()
    time.sleep(delay)
    after = cpu_snapshot()
    return {
        cpu: round(1 - (after[cpu][1] - idle) / max(1, after[cpu][0] - total), 3)
        for cpu, (total, idle) in before.items() if cpu in after
    }


def select_cpus(requested):
    allowed = set(os.sched_getaffinity(0))
    loads = cpu_load()
    if requested:
        cpus = cpu_list(requested)
    else:
        groups = {}
        for cpu in sorted(allowed):
            siblings = sibling_group(cpu)
            available = [member for member in siblings if member in allowed]
            if available:
                groups[siblings] = min(available, key=lambda member: loads.get(member, 1.0))
        ranked = sorted(groups.items(), key=lambda pair: (max(loads.get(member, 1.0) for member in pair[0]), pair[1]))
        cpus = [representative for _, representative in ranked[:16]]
    if len(cpus) < 2 or len(cpus) > 16:
        raise ValueError("须提供2到16个不同物理核的逻辑CPU")
    if set(cpus) - allowed:
        raise ValueError(f"CPU不在当前affinity: {sorted(set(cpus)-allowed)}")
    groups = [sibling_group(cpu) for cpu in cpus]
    if len(set(groups)) != len(groups):
        raise ValueError("CPU列表含SMT同胞")
    detail = [
        {"cpu": cpu, "siblings": list(group),
         "initial_busy": max(loads.get(member, 1.0) for member in group)}
        for cpu, group in zip(cpus, groups)
    ]
    if not requested and sum(x["initial_busy"] <= 0.5 for x in detail) < 2:
        raise ValueError("当前未找到两个忙碌率≤50%的独立物理核；稍后重试或显式指定CPU")
    return cpus, detail


def ps_snapshot():
    try:
        output = subprocess.check_output(
            ["ps", "-eLo", "pid,ppid,psr,rss,pcpu,comm"], text=True
        )
    except subprocess.CalledProcessError:
        return [], []
    rows = []
    for line in output.splitlines()[1:]:
        fields = line.split(None, 5)
        if len(fields) == 6:
            try:
                rows.append({"pid": int(fields[0]), "ppid": int(fields[1]),
                             "cpu": int(fields[2]), "rss_kb": int(fields[3]),
                             "pcpu": float(fields[4]), "comm": fields[5]})
            except ValueError:
                continue
    emu = [row for row in rows if row["comm"] == "emu"]
    return rows, emu


def descendants(pid, rows):
    current = {pid}
    while True:
        more = {row["pid"] for row in rows if row["ppid"] in current}
        if more <= current:
            break
        current |= more
    return [row for row in rows if row["pid"] in current]


def memory_available_kb():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    return 0


def active_output_bytes(batch, job):
    dest = VALIDATION / "runs" / batch / job
    paths = (dest / "run.log", dest / "output" / "trace" / f"itrace_{job}.txt")
    total = 0
    for path in paths:
        try:
            total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def read_control(path):
    control = json.loads(path.read_text())
    parallel = control.get("max_parallel")
    if type(parallel) is not int or not 2 <= parallel <= 16:
        raise ValueError("control.max_parallel须为2..16")
    return parallel


def frozen_inputs_error(plan):
    for path, expected in ((Path(plan["inputs"]), plan["inputs_sha256"]),
                           (HARNESS, plan["harness_sha256"]),
                           (Path(plan["affected_manifest"]), plan["affected_manifest_sha256"])):
        try:
            if digest(path) != expected:
                return f"冻结文件漂移：{path}"
        except OSError as error:
            return f"冻结文件不可读：{path}: {error}"
    return None


def prepare_plan(args):
    inputs = args.inputs.resolve(strict=True)
    data, jobs, affected, compatible, affected_path, affected_sha = read_jobs(inputs)
    cpus, cpu_detail = select_cpus(args.cpus)
    if len(cpus) < 2:
        raise ValueError("初始至少需要两个CPU")
    if not args.dry_run:
        raw = inputs.read_text()
        if "<" in raw or data.get("model_commit", "").startswith("<"):
            raise ValueError("正式inputs仍有占位符")
        if data.get("domain") != "full" or data.get("seed") != 17 or data.get("tactic") != "qffp" or data.get("threads") != 1:
            raise ValueError("正式inputs必须full/seed17/qffp/T1")
    return {
        "batch": args.batch, "created_utc": utc_now(), "inputs": str(inputs),
        "inputs_sha256": digest(inputs), "affected_manifest": str(affected_path),
        "affected_manifest_sha256": affected_sha, "model_commit": data.get("model_commit"),
        "isla_commit": data.get("isla_commit"), "count": len(jobs),
        "affected_count": len(affected), "compatibility_count": len(compatible),
        "ordered_jobs": jobs, "affected_clauses": affected, "compatibility_clauses": compatible,
        "cpus": cpus, "cpu_detail": cpu_detail,
        "harness": str(HARNESS), "harness_sha256": digest(HARNESS),
        "policy": {"initial_parallel": 2, "max_parallel": min(16, len(cpus)),
                   "outer_timeout_s": 7200, "smt_timeout_s": 7200,
                   "thread_count": 1, "tactic": "qffp", "seed": 17,
                   "poll_seconds": POLL_SECONDS,
                   "minimum_disk_free_bytes": DISK_MIN_FREE_BYTES,
                   "disk_growth_horizon_s": 7200},
    }


def launch(args):
    plan = prepare_plan(args)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    if args.acceptance_review is None or args.enum_review is None:
        raise ValueError("启动前必须提供独立 acceptance_review 与 enum_review 签收文件")
    reviews = {}
    for key, path in (("acceptance", args.acceptance_review), ("enum", args.enum_review)):
        resolved = path.resolve(strict=True)
        if not resolved.is_file() or not resolved.read_text().strip():
            raise ValueError(f"{key}审查文件为空")
        reviews[key] = {"path": str(resolved), "sha256": digest(resolved)}
    plan["reviews"] = reviews
    if digest(Path(plan["affected_manifest"])) != plan["affected_manifest_sha256"]:
        raise ValueError("影响Clause清单漂移")
    first = plan["ordered_jobs"][0]
    preflight = [sys.executable, str(HARNESS), "--inputs", plan["inputs"],
                 "--batch", args.batch, "--job", first, "--cpu", str(plan["cpus"][0]), "--dry-run"]
    subprocess.run(preflight, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    batch_dir = HERE / "batches" / args.batch
    if batch_dir.exists() or (VALIDATION / "runs" / args.batch).exists():
        raise FileExistsError("批次目录已存在；不得覆盖旧结果")
    batch_dir.mkdir(parents=True)
    write_json(batch_dir / "plan.json", plan)
    write_json(batch_dir / "control.json", {"max_parallel": 2, "note": "观察两个任务RSS与磁盘后可手动调至4..16"})
    with (batch_dir / "supervisor.log").open("ab") as log:
        process = subprocess.Popen([sys.executable, str(__file__), "--supervise", "--batch", args.batch],
                                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    write_json(batch_dir / "supervisor.json",
               {"pid": process.pid, "started_utc": utc_now(), "command": [sys.executable, str(__file__), "--supervise", "--batch", args.batch]})
    print(json.dumps({"batch": args.batch, "supervisor_pid": process.pid,
                      "summary": str(batch_dir / "summary.json"), "count": plan["count"]}, ensure_ascii=False))


def supervise(batch):
    batch_dir = HERE / "batches" / batch
    lock_handle = (batch_dir / "supervisor.lock").open("a")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeError(f"批次{batch}已有监督器运行") from error
    plan = json.loads((batch_dir / "plan.json").read_text())
    if error := frozen_inputs_error(plan):
        raise ValueError(error)
    queue = list(plan["ordered_jobs"])
    running = {}
    completed = {}
    blocked_jobs = []
    peak_rss = 0
    started = time.monotonic()
    observed_milestones = set()
    last_requested = 2
    last_output_sample = {}
    peak_output_growth_bps = 0.0
    peak_job_output_bytes = 0
    while queue or running:
        frozen_error = frozen_inputs_error(plan)
        if frozen_error and queue:
            blocked_jobs.extend(queue)
            queue.clear()
        rows, emu = ps_snapshot()
        elapsed = time.monotonic() - started
        current_rss = [
            max((row["rss_kb"] for row in descendants(state["process"].pid, rows)), default=0)
            for state in running.values()
        ]
        peak_rss = max([peak_rss, *current_rss])
        now = time.monotonic()
        for job in running:
            size = active_output_bytes(batch, job)
            peak_job_output_bytes = max(peak_job_output_bytes, size)
            if job in last_output_sample:
                previous_time, previous_size = last_output_sample[job]
                if now > previous_time and size >= previous_size:
                    peak_output_growth_bps = max(
                        peak_output_growth_bps, (size - previous_size) / (now - previous_time)
                    )
            last_output_sample[job] = (now, size)
        disk_free_bytes = shutil.disk_usage(VALIDATION).free
        control_error = None
        try:
            requested = read_control(batch_dir / "control.json")
            last_requested = requested
        except (OSError, ValueError, json.JSONDecodeError) as error:
            requested = last_requested
            control_error = str(error)
        parallel = min(requested, len(plan["cpus"]))
        scale_guard = None
        if parallel > 2 and (elapsed < 300 or peak_rss == 0):
            parallel = 2
            scale_guard = "first_two_jobs_need_five_minutes_and_rss"
        available_kb = memory_available_kb()
        if parallel > 2 and peak_rss * parallel > available_kb * 0.7:
            parallel = 2
            scale_guard = "observed_rss_exceeds_memory_headroom"
        for job, state in list(running.items()):
            code = state["process"].poll()
            if code is None:
                continue
            result_path = VALIDATION / "runs" / batch / job / "result.json"
            result = None
            result_error = None
            if result_path.exists():
                try:
                    parsed = json.loads(result_path.read_text())
                    if isinstance(parsed, dict):
                        result = parsed
                    else:
                        result_error = "result.json不是对象"
                except (OSError, ValueError) as error:
                    result_error = f"result.json不可解析：{error}"
            else:
                result_error = "result.json缺失"
            time_path = VALIDATION / "runs" / batch / job / "time.txt"
            peak = None
            if time_path.exists():
                try:
                    match = re.search(r"(?m)^maxrss_kb=(\d+)$", time_path.read_text())
                    if match:
                        peak = int(match.group(1))
                        peak_rss = max(peak_rss, peak)
                except OSError as error:
                    result_error = f"time.txt不可读：{error}"
            identity_valid = bool(
                result and result.get("job") == job and result.get("batch") == batch
                and result.get("input_manifest_sha256") == plan["inputs_sha256"]
                and result.get("affected_manifest_sha256") == plan["affected_manifest_sha256"]
                and result.get("model_commit") == plan["model_commit"]
                and result.get("isla_commit") == plan["isla_commit"]
                and result.get("domain") == "full" and result.get("seed") == 17
                and result.get("scope") == ("affected" if job in plan["affected_clauses"] else "compatibility")
            )
            if result and not identity_valid:
                result_error = "result.json身份或冻结输入哈希不符"
            completed[job] = {
                "harness_exit_code": code,
                "result_path": str(result_path) if result_path.exists() else None,
                "result_error": result_error,
                "identity_valid": identity_valid,
                "pass": bool(code == 0 and identity_valid and result and result.get("pass") is True and result_error is None),
                "clause_exit_code": result.get("exit_code") if result else None,
                "status": result.get("summary", {}).get("status") if result and isinstance(result.get("summary"), dict) else None,
                "gen_count": result.get("gen_count") if result else None,
                "elapsed_s": result.get("elapsed_s") if result else None,
                "maxrss_kb": peak,
                "finished_utc": utc_now(),
            }
            state["launcher_log"].close()
            del running[job]
            last_output_sample.pop(job, None)
        used_cpus = {state["cpu"] for state in running.values()}
        disk_guard = None
        projected_job_bytes = max(
            DISK_FALLBACK_JOB_BYTES, peak_job_output_bytes,
            int(peak_output_growth_bps * 7200),
        )
        while queue and len(running) < parallel:
            disk_required = DISK_MIN_FREE_BYTES + projected_job_bytes * (len(running) + 1)
            disk_free_bytes = shutil.disk_usage(VALIDATION).free
            if disk_free_bytes < disk_required:
                disk_guard = "pause_new_jobs_for_disk_headroom"
                break
            cpu = next((cpu for cpu in plan["cpus"] if cpu not in used_cpus), None)
            if cpu is None:
                break
            job = queue.pop(0)
            if new_error := frozen_inputs_error(plan):
                frozen_error = new_error
                blocked_jobs.extend([job, *queue])
                queue.clear()
                break
            launcher_log = (batch_dir / f"{job}.launcher.log").open("ab")
            command = [sys.executable, str(HARNESS), "--inputs", plan["inputs"],
                       "--batch", batch, "--job", job, "--cpu", str(cpu)]
            try:
                proc = subprocess.Popen(command, cwd=ROOT, stdout=launcher_log,
                                        stderr=subprocess.STDOUT, start_new_session=True)
            except OSError as error:
                launcher_log.close()
                completed[job] = {"harness_exit_code": None, "result_path": None,
                                  "result_error": f"harness启动失败：{error}", "identity_valid": False,
                                  "pass": False, "clause_exit_code": None, "status": None,
                                  "gen_count": None, "elapsed_s": None, "maxrss_kb": None,
                                  "finished_utc": utc_now()}
                continue
            running[job] = {"process": proc, "cpu": cpu, "command": command,
                            "launcher_log": launcher_log, "started_utc": utc_now()}
            used_cpus.add(cpu)
        rows, emu = ps_snapshot()
        active = {}
        for job, state in running.items():
            members = descendants(state["process"].pid, rows)
            active[job] = {
                "launcher_pid": state["process"].pid, "cpu": state["cpu"],
                "started_utc": state["started_utc"], "command": state["command"],
                "descendant_pids": sorted(set(row["pid"] for row in members)),
                "rss_kb_current": max((row["rss_kb"] for row in members), default=0),
            }
        affected = set(plan["affected_clauses"])
        sibling_cpus = {member for entry in plan["cpu_detail"] for member in entry["siblings"]}
        conservation_total = len(queue) + len(running) + len(completed) + len(blocked_jobs)
        conservation_valid = conservation_total == plan["count"]
        if not conservation_valid and queue:
            blocked_jobs.extend(queue)
            queue.clear()
        summary = {
            "batch": batch, "updated_utc": utc_now(), "supervisor_pid": os.getpid(),
            "inputs_sha256": plan["inputs_sha256"], "total": plan["count"],
            "affected_total": plan["affected_count"], "compatibility_total": plan["compatibility_count"],
            "queued": len(queue), "running": len(running), "completed": len(completed),
            "blocked": len(blocked_jobs), "blocked_jobs": blocked_jobs,
            "frozen_error": frozen_error,
            "task_conservation_total": conservation_total,
            "task_conservation_valid": conservation_valid,
            "passed": sum(bool(v["pass"]) for v in completed.values()),
            "failed": sum(not v["pass"] for v in completed.values()),
            "affected_completed": sum(job in affected for job in completed),
            "affected_passed": sum(job in affected and bool(v["pass"]) for job, v in completed.items()),
            "compatibility_completed": sum(job not in affected for job in completed),
            "compatibility_passed": sum(job not in affected and bool(v["pass"]) for job, v in completed.items()),
            "max_parallel_requested": requested, "max_parallel_effective": parallel,
            "scale_guard": scale_guard,
            "control_error": control_error,
            "observed_peak_rss_kb": peak_rss, "mem_available_kb": available_kb,
            "disk_free_bytes": disk_free_bytes,
            "disk_min_free_bytes": DISK_MIN_FREE_BYTES,
            "disk_projected_job_bytes": projected_job_bytes,
            "disk_required_for_next_job_bytes": DISK_MIN_FREE_BYTES + projected_job_bytes * (len(running) + 1),
            "disk_guard": disk_guard,
            "peak_output_growth_bytes_per_s": round(peak_output_growth_bps, 2),
            "peak_active_job_output_bytes": peak_job_output_bytes,
            "external_emu_threads": len(emu),
            "external_emu_cpus": sorted(set(row["cpu"] for row in emu)),
            "external_emu_threads_on_selected_siblings": sum(row["cpu"] in sibling_cpus for row in emu),
            "active": active, "results": completed,
            "path_accounting": {"main_created": None, "main_completed": None,
                                "main_queued": None, "collector_pending": None,
                                "smt_check_pending": None,
                                "note": "正式harness尚无实时结构化路径/SMT阶段计数；留空，不从CPU或JSON缺失推断"},
        }
        write_json(batch_dir / "summary.json", summary)
        write_json(batch_dir / "pids.json",
                   {"supervisor_pid": os.getpid(), "active": {k: v["descendant_pids"] for k, v in active.items()},
                    "updated_utc": summary["updated_utc"]})
        for milestone in (0, 300, 900, 1800):
            if elapsed >= milestone and milestone not in observed_milestones:
                observation = {
                    "elapsed_s_at_least": milestone, "observed_elapsed_s": round(elapsed, 3),
                    "updated_utc": summary["updated_utc"], "active": active,
                    "observed_peak_rss_kb": peak_rss,
                    "mem_available_kb": available_kb,
                    "external_emu_threads": len(emu),
                    "external_emu_threads_on_selected_siblings": summary["external_emu_threads_on_selected_siblings"],
                    "completed": len(completed), "passed": summary["passed"],
                    "failed": summary["failed"],
                }
                with (batch_dir / "observations.jsonl").open("a") as output:
                    output.write(json.dumps(observation, ensure_ascii=False) + "\n")
                observed_milestones.add(milestone)
        print(f"{summary['updated_utc']} completed={len(completed)}/{plan['count']} running={len(running)} queued={len(queue)} pass={summary['passed']} fail={summary['failed']} emu_threads={len(emu)} rss_peak_kb={peak_rss}", flush=True)
        if queue or running:
            time.sleep(POLL_SECONDS)
    summary["supervision_finished"] = True
    summary["batch_complete"] = len(completed) == plan["count"] and not blocked_jobs
    summary["finished_utc"] = utc_now()
    write_json(batch_dir / "summary.json", summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=TEMPLATE)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpus", help="逗号/区间分隔；不同物理核，须属于当前affinity")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--supervise", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--acceptance-review", type=Path)
    parser.add_argument("--enum-review", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch):
        parser.error("batch名称只能含字母、数字、下划线和连字符")
    if args.supervise:
        supervise(args.batch)
    elif args.dry_run or args.launch:
        launch(args)
    else:
        parser.error("需指定--dry-run或--launch")


if __name__ == "__main__":
    main()
