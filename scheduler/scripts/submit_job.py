#!/usr/bin/env python3
"""打包可执行文件和输入，提交任务并选择数据回传策略。"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid

from common import ROOT, atomic_json, cli, fail_main, load_config, manager, runtime_path


def quote(value):
    value = str(value)
    if any(c in value for c in ('\n', '\r', '"', '\\')) or "$(" in value or "$$(" in value:
        raise ValueError(f"submit 字段含不支持的特殊字符：{value!r}")
    return f'"{value}"'


def copy_input(source, destination):
    source = Path(source).absolute()
    if source.is_symlink() or (source.is_dir() and any(p.is_symlink() for p in source.rglob("*"))):
        raise ValueError(f"输入包含符号链接，请先建立自包含副本：{source}")
    if source.is_dir():
        shutil.copytree(source, destination)
    elif source.is_file():
        shutil.copy2(source, destination)
    else:
        raise ValueError(f"输入不是普通文件或目录：{source}")


def bundle_libraries(executable, stage, program):
    with executable.open("rb") as stream:
        magic = stream.read(4)
    if magic != b"\x7fELF":
        raise ValueError("--bundle-libs 只支持 x86_64 ELF 可执行文件")
    # ldd 列出启动时依赖及其递归依赖；只对用户自己构建的二进制使用。
    result = subprocess.run(["ldd", str(executable)], capture_output=True, text=True)
    if result.returncode or "not found" in result.stdout:
        raise ValueError(f"本机依赖解析失败：{result.stdout}{result.stderr}")
    libraries = {}
    loader = None
    for line in result.stdout.splitlines():
        match = re.search(r"(?:=>\s+)?(/\S+)", line)
        if not match:
            continue
        source = Path(match.group(1))
        if source.name in libraries and source.resolve() != libraries[source.name].resolve():
            raise ValueError(f"依赖存在同名冲突：{source.name}")
        libraries[source.name] = source
        if source.name.startswith("ld-linux-x86-64"):
            loader = source.name
    if loader is None:
        raise ValueError("未找到 x86_64 glibc loader；静态程序不需要 --bundle-libs")
    target = stage / "runtime-libs"
    target.mkdir()
    for name, source in libraries.items():
        shutil.copy2(source.resolve(), target / name)
    return [f"./runtime-libs/{loader}", "--library-path", "./runtime-libs", "--argv0", program, program]


def make_bundle(args, config, job_id, directory):
    c = config["cluster"]
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        stage = Path(tmp)
        executable = Path(args.executable).resolve(strict=True)
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError("executable 必须是可执行的普通文件")
        program = f"./bin/{Path(args.executable).name}"
        (stage / "bin").mkdir()
        shutil.copy2(executable, stage / program)
        inputs = stage / "inputs"
        inputs.mkdir()
        for name in args.input:
            path = Path(name).absolute()
            if (inputs / path.name).exists():
                raise ValueError(f"输入 basename 重复：{path.name}")
            copy_input(path, inputs / path.name)
        environment = {}
        for value in args.env:
            name, sep, value = value.partition("=")
            if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                raise ValueError("--env 使用 NAME=VALUE")
            environment[name] = value
        for name in args.summary:
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("--summary 必须是任务工作目录内的相对文件路径")
        command = bundle_libraries(executable, stage, program) if args.bundle_libs else [program]
        command += args.arguments
        manifest = {"job_id": job_id, "command": command, "environment": environment,
                    "policy": args.policy, "cpus": args.cpus,
                    "summary_files": args.summary, "summary_limit_bytes": c["summary_limit_bytes"],
                    "log_tail_bytes": c["log_tail_bytes"]}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        with tarfile.open(directory / "payload.tar.gz", "w:gz", dereference=False) as archive:
            for item in sorted(stage.iterdir()):
                archive.add(item, arcname=item.name)
    return manifest


def submit_text(args, config, job_id):
    base = f"/srv/submit/{job_id}"
    requirement = "True"
    if args.node:
        if args.node not in {n["name"] for n in config["nodes"]}:
            raise ValueError("--node 不在 nodes.conf 中")
        requirement = f"TARGET.IslaNode == {quote(args.node)}"
    if args.gpus:
        requirement += " && TARGET.Gpus >= %d" % args.gpus
    lines = ["universe = vanilla", f"initialdir = {quote(base)}",
             f"executable = {quote(base + '/job_runner.py')}",
             "arguments =", "should_transfer_files = YES", "when_to_transfer_output = ON_EXIT",
             f"transfer_input_files = {quote(base + '/payload.tar.gz')}",
             "transfer_executable = True", f"request_cpus = {args.cpus}",
             f"request_memory = {args.memory}", f"request_disk = {args.disk}",
             f"request_gpus = {args.gpus}", f"requirements = {requirement}",
             "getenv = False", "notification = Never", "on_exit_hold = False",
             "leave_in_queue = False", 'log = "events.log"',
             '+IslaJobId = ' + quote(job_id), '+IslaRetrievePolicy = ' + quote(args.policy)]
    if args.policy == "none":
        lines += ['transfer_output_files = ""', "output = /dev/null", "error = /dev/null"]
    else:
        lines += ['transfer_output_files = "return"', 'output = "runner.out"', 'error = "runner.err"']
    # 同一任务失败不盲目重提；被抢占后重调度会在节点产生独立 attempt。
    lines += ["queue 1", ""]
    return "\n".join(lines)


def wait_for(config, cluster_id, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        queued = json.loads(cli(config, ["condor_q", str(cluster_id), "-json"]).stdout)
        if queued:
            ad = queued[0]
            if ad.get("JobStatus") == 5:
                raise RuntimeError(f"任务 {cluster_id}.0 Held：{ad.get('HoldReason')}；使用 condor_q -better-analyze 排查")
        else:
            history = json.loads(cli(config, ["condor_history", str(cluster_id), "-limit", "1", "-json"]).stdout)
            if history:
                ad = history[0]
                if ad.get("JobStatus") != 4:
                    raise RuntimeError(f"任务未正常完成：{ad.get('RemoveReason', ad.get('JobStatus'))}")
                return ad
        time.sleep(2)
    raise TimeoutError(f"等待 {cluster_id}.0 超时；任务仍保留在队列，不自动取消")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--executable", required=True)
    parser.add_argument("--input", action="append", default=[], help="复制到任务 inputs/<basename>")
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("--bundle-libs", action="store_true", help="打包 ELF loader 和 ldd 启动时依赖")
    parser.add_argument("--summary", action="append", default=None, help="工作目录内摘要文件，可重复")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--retrieve-data", dest="policy", action="store_const", const="all")
    mode.add_argument("--summary-only", dest="policy", action="store_const", const="summary")
    mode.add_argument("--no-retrieve", dest="policy", action="store_const", const="none")
    parser.set_defaults(policy="summary")
    parser.add_argument("--node")
    parser.add_argument("--cpus", type=int, default=1)
    parser.add_argument("--memory", default="1GB")
    parser.add_argument("--disk", default="2GB", help="包含输入、持久工作副本及完整回传临时包所需空间")
    parser.add_argument("--gpus", type=int, default=0)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--dry-run", action="store_true", help="只生成包和 submit 文件")
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="在 -- 后给任务参数")
    args = parser.parse_args()
    if args.arguments[:1] == ["--"]:
        args.arguments = args.arguments[1:]
    if args.cpus < 1 or args.gpus < 0 or args.timeout < 1:
        parser.error("资源或 timeout 数值非法")
    for value in (args.memory, args.disk):
        if not re.fullmatch(r"[1-9][0-9]*(?:[KMGTP]B?|B)?", value, re.IGNORECASE):
            parser.error("memory/disk 使用正整数和可选 KB/MB/GB/TB 单位")
    if args.summary is None:
        args.summary = ["results/summary.json"]
    return args


def main():
    args = parse_args()
    config = load_config(args.config)
    job_id = uuid.uuid4().hex
    directory = Path(runtime_path(manager(config))) / "submissions" / job_id
    directory.mkdir(parents=True)
    manifest = make_bundle(args, config, job_id, directory)
    shutil.copy2(ROOT / "scripts/job_runner.py", directory / "job_runner.py")
    (directory / "job_runner.py").chmod(0o755)
    text = submit_text(args, config, job_id)
    (directory / "job.sub").write_text(text)
    record = {"job_id": job_id, "policy": args.policy, "directory": str(directory),
              "manifest": manifest, "submitted": False}
    atomic_json(directory / "submission.json", record)
    if args.dry_run:
        print(json.dumps(record))
        return
    result = cli(config, ["condor_submit", "-terse", f"/srv/submit/{job_id}/job.sub"])
    match = re.search(rb"(\d+)\.\d+", result.stdout)
    if match is None:
        raise RuntimeError(f"无法解析 condor_submit 的任务号：{result.stdout!r}")
    cluster_id = int(match.group(1))
    record.update(cluster_id=cluster_id, submitted=True)
    atomic_json(directory / "submission.json", record)
    if args.wait:
        history = wait_for(config, cluster_id, args.timeout)
        atomic_json(directory / "history.json", history)
        record["exit_code"] = 128 + history.get("ExitSignal", 0) if history.get("ExitBySignal") else history.get("ExitCode", 125)
        record["execution_host"] = history.get("LastRemoteHost") or history.get("RemoteHost")
        atomic_json(directory / "submission.json", record)
        print(json.dumps(record))
        if record["exit_code"]:
            raise RuntimeError(f"任务退出码 {record['exit_code']}；详情见 {directory}")
    else:
        print(json.dumps(record))


if __name__ == "__main__":
    fail_main(main)
