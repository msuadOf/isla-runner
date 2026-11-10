"""proxy 直接启动本地监督器：继承原日志文件和环境，不建立输入副本。"""
import json
from pathlib import Path
import subprocess
import sys
import time

from scheduler.native.common import atomic_json


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
    atomic_json(directory / 'local-running.json', {'supervisor_pid': child.pid, 'cwd': str(cwd)})
    stopping = False
    try:
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
    confirmed = len(evidence) == 1 and next(iter(evidence.values())).get('return_code') == code
    category = 'intime' if code == 0 else 'timeout' if code == 124 else 'failed'
    status = f"{manifest['clause']} {category}" + (f' ({code})' if category == 'failed' else '') + '\n'
    result.update(return_code=code if confirmed else 125, execution_confirmed=confirmed,
                  cancelled=stopping, elapsed_seconds=time.monotonic() - started, evidence=evidence,
                  statuses={f'status.{category}.log': status} if confirmed else {})
    if not confirmed:
        result['infrastructure_error'] = '本地监督器退出证据缺失或不一致，不能确认后代结束'
    atomic_json(directory / 'local-result.json', result)
    return result
