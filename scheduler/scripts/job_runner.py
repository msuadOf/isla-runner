#!/usr/bin/env python3
"""执行节点入口：先落盘，执行后按策略生成回传目录。兼容 Python 3.10。"""

import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import time
import uuid


def unpack(archive, destination):
    destination = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination) or not (member.isdir() or member.isfile()):
                raise ValueError(f"不支持的归档条目：{member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                target.chmod(member.mode & 0o777)


def tail(source, target, limit):
    with source.open("rb") as stream:
        stream.seek(max(0, source.stat().st_size - limit))
        target.write_bytes(stream.read(limit))


def execute(archive, data_root, returned):
    scratch = returned.parent
    stage = scratch / "unpacked"
    stage.mkdir()
    unpack(archive, stage)
    spec = json.loads((stage / "manifest.json").read_text())
    job_id = spec["job_id"]
    if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("非法 job_id")
    attempt = Path(data_root) / "jobs" / job_id / f"attempt-{uuid.uuid4().hex}"
    work = attempt / "work"
    work.parent.mkdir(parents=True)
    shutil.move(str(stage), str(work))
    (work / "results").mkdir(exist_ok=True)
    returned.mkdir(parents=True, exist_ok=True)
    started = time.time()
    summary = {"job_id": job_id, "hostname": socket.gethostname(), "attempt": str(attempt),
               "policy": spec["policy"], "started_unix": started, "command": spec["command"]}
    code = 125
    try:
        env = os.environ.copy()
        env.update(spec["environment"])
        # 防止每个单 CPU 任务中的数值库默认占满整台节点。
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            env.setdefault(name, str(spec["cpus"]))
        with (work / "stdout.log").open("wb") as out, (work / "stderr.log").open("wb") as err:
            process = subprocess.Popen(spec["command"], cwd=work, env=env, stdout=out, stderr=err, start_new_session=True)

            def forward(signum, frame):
                try:
                    os.killpg(process.pid, signum)
                except ProcessLookupError:
                    pass

            old = {s: signal.signal(s, forward) for s in (signal.SIGTERM, signal.SIGINT)}
            try:
                code = process.wait()
            finally:
                for signum, handler in old.items():
                    signal.signal(signum, handler)
        summary["exit_code"] = code
    except Exception as error:
        summary.update(exit_code=code, error=f"{type(error).__name__}: {error}")
    summary["finished_unix"] = time.time()
    summary["elapsed_seconds"] = summary["finished_unix"] - started
    # 即使任务失败，也在节点保存状态和日志。
    (attempt / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if spec["policy"] != "none":
        (returned / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        for name in ("stdout.log", "stderr.log"):
            source = work / name
            if source.exists():
                tail(source, returned / name, spec["log_tail_bytes"])
        remaining = spec["summary_limit_bytes"]
        for number, name in enumerate(spec["summary_files"]):
            source = (work / name).resolve()
            # 不跟随指向工作目录外的数据链接。
            if source.is_relative_to(work.resolve()) and source.is_file() and source.stat().st_size <= remaining:
                target = returned / "summaries" / str(number) / Path(name).name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                remaining -= source.stat().st_size
            else:
                summary.setdefault("omitted_summaries", []).append(name)
        if spec["policy"] == "all":
            # 包含工作目录内全部文件，符号链接作为链接存储，不遍历外部目录。
            with tarfile.open(returned / "full.tar.gz", "w:gz", dereference=False) as archive_out:
                archive_out.add(work, arcname="work", recursive=True)
        (returned / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        (attempt / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    # 负返回码表示信号；以常用的 128+signal 反馈给 Condor。
    return min(255, code if code >= 0 else 128 - code)


def main():
    try:
        return execute(Path("payload.tar.gz"), "/srv/isla", Path.cwd() / "return")
    except Exception as error:
        # 包装器自身失败也必须产生可回传的摘要，避免永久卡在缺少 output 的状态。
        returned = Path.cwd() / "return"
        returned.mkdir(exist_ok=True)
        (returned / "summary.json").write_text(json.dumps({"exit_code": 125, "runner_error": str(error)}) + "\n")
        print(f"任务包装器失败：{error}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    sys.exit(main())
