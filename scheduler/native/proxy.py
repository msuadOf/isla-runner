#!/usr/bin/env python3
"""阻塞到任务结束，stdout 继承原 recipe 的日志重定向。"""
import json
import os
from pathlib import Path
import signal
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scheduler.native.common import ENVIRONMENT, atomic_json
from scheduler.native.local import run as run_local


def main():
    run = Path(os.environ['ISLA_SCHEDULER_RUN'])
    argv = sys.argv[1:]
    if argv[:1] == ['--']:
        argv = argv[1:]
    job_id = uuid.uuid4().hex
    directory = run / 'jobs' / job_id
    directory.mkdir(parents=True)
    cancelled = []
    def cancel(number, frame):
        cancelled.append(number)
        (run / 'cancel' / job_id).touch()
    signal.signal(signal.SIGINT, cancel)
    signal.signal(signal.SIGTERM, cancel)
    request = {'argv': argv, 'cwd': str(Path.cwd()), 'proxy_pid': os.getpid(),
               'proxy_start': Path('/proc/self/stat').read_text().rsplit(') ', 1)[1].split()[19],
               'environment': {k: os.environ[k] for k in ENVIRONMENT
                               if k in os.environ}}
    try:
        fd_path = Path('/proc/self/fd/1').resolve()
        if fd_path.is_relative_to(Path.cwd()):
            request['log_path'] = fd_path.relative_to(Path.cwd()).as_posix()
    except OSError:
        pass
    atomic_json(run / 'requests' / (job_id + '.json'), request)
    offset = 0
    remote_header = False
    local_started = False
    def controller_alive():
        if (run / 'ended.json').exists():
            return False
        pid = json.loads((run / 'ready.json').read_text())['pid']
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True
    while True:
        if not local_started and (directory / 'local.json').exists():
            task = json.loads((directory / 'local.json').read_text())
            run_local(task, directory, lambda: bool(cancelled) or (run / 'stop').exists()
                      or (run / 'cancel' / job_id).exists(), controller_alive)
            local_started = True
        stream = directory / 'stream.log'
        if not remote_header and stream.exists():
            print(f'[scheduler] job={job_id}；本文件含有界实时片段，完整日志保留在执行节点', flush=True)
            remote_header = True
        if stream.exists():
            with stream.open('rb') as source:
                source.seek(offset)
                chunk = source.read(65536)
            if chunk:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                offset += len(chunk)
        result_path = directory / 'result.json'
        if result_path.exists():
            result = json.loads(result_path.read_text())
            if result.get('local'):
                if result.get('infrastructure_error'):
                    print('[scheduler] ' + result['infrastructure_error'], file=sys.stderr, flush=True)
                return 128 + cancelled[0] if cancelled else result['return_code']
            tail = directory / 'tail.log'
            print('\n[scheduler] 以下为最终 64 KiB 尾部（可能与实时片段重叠）', flush=True)
            if tail.exists():
                sys.stdout.buffer.write(tail.read_bytes())
                sys.stdout.buffer.flush()
            print(f'\n[scheduler] node={result.get("node")} attempt={result.get("attempt")} '
                  f'exit={result["return_code"]}', flush=True)
            if result.get('infrastructure_error'):
                print('[scheduler] ' + result['infrastructure_error'], file=sys.stderr, flush=True)
            return 128 + cancelled[0] if cancelled else result['return_code']
        if (run / 'ended.json').exists():
            print('[scheduler] 主控已退出，远端状态须核对', file=sys.stderr)
            return 125
        # 主控意外死亡时，proxy 不永久等待；worker 的 EOF/租约负责取消。
        pid = json.loads((run / 'ready.json').read_text())['pid']
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            print('[scheduler] 主控失联，远端状态须核对', file=sys.stderr)
            return 125
        time.sleep(.05)


if __name__ == '__main__':
    raise SystemExit(main())
