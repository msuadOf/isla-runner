"""proxy 直接启动本地监督器：继承原日志文件和环境，不建立输入副本。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scheduler.native.common import atomic_json, process_identity


def run(task, directory, cancelled, controller_alive):
    manifest = task['manifest']
    cwd = Path(manifest['cwd'])
    command = [sys.executable, *manifest['original_argv'][1:]]
    result = dict(job_id=task['job_id'], attempt_id=task['attempt_id'], node=task['node'],
                  local=True, cwd=str(cwd), effective_argv=command, outputs_in_place=True,
                  retrieval='in_place', cancelled=False)
    if cancelled() or not controller_alive():
        result.update(return_code=130, execution_confirmed=True, cancelled=True)
        atomic_json(directory / 'local-result.json', result)
        return result
    try:
        # 不指定 env/stdout/stderr/TMPDIR，完整继承 proxy 的原生环境和 recipe 重定向。
        child = subprocess.Popen(command, cwd=cwd, start_new_session=True)
    except OSError as error:
        result.update(return_code=125, execution_confirmed=True, infrastructure_error=str(error))
        atomic_json(directory / 'local-result.json', result)
        return result
    started = time.monotonic()
    identity = process_identity(child.pid)
    stopping = False
    try:
        atomic_json(directory / 'local-running.json', {'supervisor_pid': child.pid, 'supervisor_start': identity, 'cwd': str(cwd)})
        while child.poll() is None:
            if cancelled() or not controller_alive():
                try:
                    ready = bool(Path(f'/proc/{child.pid}/task/{child.pid}/children').read_text().strip())
                except FileNotFoundError:
                    ready = False
                if not stopping and (ready or time.monotonic() - started > 2):
                    try:
                        child.terminate()  # 由原监督器清理 timeout 的独立进程组。
                    except ProcessLookupError:
                        pass
                    stopping = True
            time.sleep(.02)
        code = child.wait()
    finally:
        if child.poll() is None:
            try:
                child.terminate()
            except ProcessLookupError:
                pass
            child.wait(timeout=30)
    code = code if code >= 0 else 128 - code
    evidence = {}
    path = cwd / 'output/process' / f"{manifest['clause']}-{child.pid}.json"
    if path.is_file():
        evidence[path.name] = json.loads(path.read_text())
    confirmed = (len(evidence) == 1 and next(iter(evidence.values())).get('return_code') == code
                 and next(iter(evidence.values())).get('supervisor_pid') == child.pid
                 and next(iter(evidence.values())).get('clause') == manifest['clause']
                 and next(iter(evidence.values())).get('cwd') == str(cwd))
    category = 'intime' if code == 0 else 'timeout' if code == 124 else 'failed'
    status = f"{manifest['clause']} {category}" + (f' ({code})' if category == 'failed' else '') + '\n'
    result.update(return_code=code if confirmed else 125, execution_confirmed=confirmed,
                  cancelled=stopping, elapsed_seconds=time.monotonic() - started, evidence=evidence,
                  statuses={f'status.{category}.log': status} if confirmed else {})
    if not confirmed:
        result['infrastructure_error'] = '本地监督器退出证据缺失或不一致，不能确认后代结束'
    atomic_json(directory / 'local-result.json', result)
    return result


def recover(task, directory):
    """proxy 意外死亡后主控接管清理；只给启动身份匹配的监督器发送信号。"""
    manifest = task['manifest']
    running = directory / 'local-running.json'
    result = dict(job_id=task['job_id'], local=True, node=task['node'], return_code=125,
                  cancelled=True, execution_confirmed=False,
                  infrastructure_error='本地 proxy 已退出，监督器状态须核对')
    if not running.exists():
        return result
    info = json.loads(running.read_text())
    pid = info['supervisor_pid']
    if process_identity(pid) == info['supervisor_start']:
        cwd = Path(f'/proc/{pid}/cwd').resolve()
        argv = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
        if cwd != Path(manifest['cwd']) or len(argv) < 3 or argv[2] != b'run':
            return result
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and process_identity(pid) == info['supervisor_start']:
            try:
                if Path(f'/proc/{pid}/task/{pid}/children').read_text().strip():
                    break
            except FileNotFoundError:
                break
            time.sleep(.02)
        # 部分主控 Python（例如 Conda 构建）未暴露 pidfd；与原监督器一样使用系统 Python。
        helper = r"""
import os, signal, sys
from pathlib import Path
pid, expected = int(sys.argv[1]), sys.argv[2]
try:
    fd = os.pidfd_open(pid)
except ProcessLookupError:
    sys.exit(0)
try:
    try:
        current = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()[19]
    except FileNotFoundError:
        sys.exit(0)
    if current != expected:
        sys.exit(0)
    try:
        signal.pidfd_send_signal(fd, signal.SIGTERM)
    except ProcessLookupError:
        pass
finally:
    os.close(fd)
"""
        stopped = subprocess.run(['/usr/bin/python3', '-c', helper, str(pid), info['supervisor_start']],
                                 capture_output=True, timeout=5)
        if stopped.returncode:
            result['infrastructure_error'] = stopped.stderr.decode(errors='replace')
            return result
        deadline = time.monotonic() + 25
        while process_identity(pid) == info['supervisor_start']:
            if time.monotonic() >= deadline:
                return result
            time.sleep(.02)
    path = Path(manifest['cwd']) / 'output/process' / f"{manifest['clause']}-{pid}.json"
    if path.is_file():
        evidence = json.loads(path.read_text())
        if (evidence.get('supervisor_pid') == pid and evidence.get('cwd') == manifest['cwd']
                and evidence.get('clause') == manifest['clause']):
            result.update(execution_confirmed=True, evidence={path.name: evidence},
                          infrastructure_error='本地 proxy 已退出，主控已接管清理并取得完成证据')
    atomic_json(directory / 'local-result.json', result)
    return result
