#!/usr/bin/env python3
"""通过 SSH 发送的独立标准库 worker；stdin/stdout 是结构化协议。"""
import base64
import fcntl
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import select
import time
import uuid


DISCONNECTED = False
ACTIVE_CHILD = None
PENDING = b''


def read_line():
    global PENDING
    while b'\n' not in PENDING:
        chunk = os.read(0, 65536)
        if not chunk:
            if PENDING:
                raise EOFError('不完整的协议消息')
            return b''
        PENDING += chunk
    line, PENDING = PENDING.split(b'\n', 1)
    return line


def read_bytes(size):
    global PENDING
    if PENDING:
        chunk, PENDING = PENDING[:size], PENDING[size:]
        return chunk
    return os.read(0, size)


def emit(value):
    global DISCONNECTED
    try:
        print(json.dumps(value, ensure_ascii=False), flush=True)
    except BrokenPipeError:
        DISCONNECTED = True
        # 仍完成定向清理并写 result.json；断线不能让 worker 提前遗留监督器。
        sys.stdout = open(os.devnull, 'w')


def save(path, value):
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    os.replace(temp, path)


def safe(root, name):
    path = root / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('路径越界')
    return path


def object_path(cache, key):
    if len(key) != 66 or key[-2:] not in ('-x', '-r') or any(c not in '0123456789abcdef' for c in key[:64]):
        raise ValueError('非法对象标识')
    return cache / 'objects' / key


def stage(base, request):
    cache = safe(base / 'cache', request['workspace'])
    (cache / 'objects').mkdir(parents=True, exist_ok=True)
    with (cache / 'stage.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        unique = {entry['digest']: entry for entry in request['entries'].values()}
        missing = []
        for key, entry in unique.items():
            target = object_path(cache, key)
            if target.is_file() and target.stat().st_size == entry['size']:
                continue
            if request.get('local') and entry.get('source'):
                source = Path(entry['source'])
                if source.is_file() and source.stat().st_size == entry['size']:
                    # source 是主控已冻结的只读对象，绝不链接原始工作文件。
                    if target.exists():
                        raise RuntimeError('缓存对象大小冲突')
                    try:
                        os.link(source, target)
                    except OSError as error:
                        if error.errno != errno.EXDEV:
                            raise
                        temporary = target.with_name('.partial-' + uuid.uuid4().hex)
                        try:
                            shutil.copy2(source, temporary)
                            os.replace(temporary, target)
                        finally:
                            temporary.unlink(missing_ok=True)
                    continue
            missing.append(key)
        emit({'missing': missing})
        for key in missing:
            entry = unique[key]
            fd, temporary = tempfile.mkstemp(dir=cache / 'objects', prefix='.partial-')
            digest = hashlib.sha256()
            try:
                remaining = entry['size']
                with os.fdopen(fd, 'wb') as stream:
                    while remaining:
                        chunk = read_bytes(min(1024 * 1024, remaining))
                        if not chunk:
                            raise EOFError('缓存传输中断')
                        remaining -= len(chunk)
                        digest.update(chunk)
                        stream.write(chunk)
                if digest.hexdigest() != key[:64]:
                    raise RuntimeError('缓存内容校验失败')
                os.chmod(temporary, entry['mode'])
                os.replace(temporary, object_path(cache, key))
            finally:
                Path(temporary).unlink(missing_ok=True)
        generation = safe(cache / 'generations', request['generation'])
        generation.mkdir(parents=True, exist_ok=True)
        save(generation / 'manifest.json', request['entries'])
        (generation / 'READY').touch()
        emit({'ready': True, 'transferred_bytes': sum(unique[k]['size'] for k in missing)})


def owner(base, request):
    with (base / 'owner.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        unfinished = [str(p.parent) for p in (base / 'jobs').glob('*/attempt-*/running.json')
                      if not (p.parent / 'result.json').is_file()
                      or not json.loads((p.parent / 'result.json').read_text()).get('execution_confirmed', False)]
        if unfinished:
            raise RuntimeError('存在未确认的旧 attempt，须先取回证据：' + ', '.join(unfinished[:5]))
        cpus = min(os.cpu_count() or 1, len(os.sched_getaffinity(0)))
        for tool in ('bash', 'timeout', 'python3'):
            if not shutil.which(tool):
                raise RuntimeError('缺少原生工具：' + tool)
        emit({'ready': True, 'cpus': cpus, 'machine': platform.machine(), 'python': sys.version,
              'kernel': platform.release(), 'base': str(base)})
        # run 结束前持续持锁；断线时等待 attempt 的租约清理完成。
        while True:
            line = read_line()
            if not line or json.loads(line).get('close'):
                break
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline:
            pending = [p for p in (base / 'jobs').glob('*/attempt-*/running.json')
                       if not (p.parent / 'result.json').exists()]
            if not pending:
                return
            time.sleep(.2)


def execute(base, request):
    global ACTIVE_CHILD
    job = safe(base / 'jobs', request['job_id'])
    attempt = safe(job, 'attempt-' + request['attempt_id'])
    job.mkdir(parents=True, exist_ok=True)
    with (job / 'start.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if attempt.exists():
            if (attempt / 'result.json').exists():
                emit({'result': json.loads((attempt / 'result.json').read_text())})
                return
            raise RuntimeError('相同 lease 已启动，拒绝重复运行')
        attempt.mkdir()
    work = attempt / 'work'
    root = work / 'root'
    root.mkdir(parents=True)
    manifest = request['manifest']
    cache = safe(base / 'cache', request['workspace'])
    generation = safe(cache / 'generations', request['generation'])
    if not (generation / 'READY').is_file():
        raise RuntimeError('generation 尚未 READY')
    for logical, entry in manifest['entries'].items():
        destination = safe(root, logical)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(object_path(cache, entry['digest']))
    cwd = safe(root, manifest['cwd'])
    cwd.mkdir(parents=True, exist_ok=True)
    for name in ('output/log', 'output/trace', 'output/process', 'outputs'):
        (cwd / name).mkdir(parents=True, exist_ok=True)
    for name in manifest['outputs']:
        output = safe(cwd, name)
        if name in manifest.get('output_directories', ['output', 'outputs']) or name.endswith('/'):
            output.mkdir(parents=True, exist_ok=True)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
    save(attempt / 'task.json', request)
    command = list(manifest['effective_argv'])
    loader = manifest.get('loader')
    if loader:
        i = manifest['binary_index']
        library_dir = os.path.relpath(root / '_runtime', cwd)
        command[i:i] = [library_dir + '/' + loader, '--library-path', library_dir,
                         '--argv0', command[i]]
    # 使用远端已预检的 timeout/Python，保留全部业务参数。
    command[0] = sys.executable
    (work / 'tmp').mkdir()
    with (work / 'stdout.log').open('wb') as log:
        child = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                 env=dict(os.environ, **manifest['environment'], TMPDIR=str(work / 'tmp')))
    ACTIVE_CHILD = child
    save(attempt / 'running.json', {'supervisor_pid': child.pid, 'worker_pid': os.getpid(),
                                   'started': time.time(), 'effective_argv': command})
    emit({'state': 'RUNNING', 'attempt': str(attempt), 'pid': child.pid})
    control = {'last': time.monotonic(), 'cancel': False}
    signal.signal(signal.SIGTERM, lambda number, frame: control.update(cancel=True))
    signal.signal(signal.SIGINT, lambda number, frame: control.update(cancel=True))
    # 同一事件循环读取控制通道，避免守护线程在 Python 退出时持有 stdin 锁。
    global PENDING
    controls, PENDING = PENDING, b''
    control_closed = False
    stopping = False
    sent = 0
    offset = 0
    next_log = 0
    started = time.monotonic()
    while child.poll() is None:
        if not control_closed and select.select([0], [], [], 0)[0]:
            chunk = os.read(0, 65536)
            if chunk:
                controls += chunk
            else:
                control_closed = True
                control['cancel'] = True
        while b'\n' in controls:
            line, controls = controls.split(b'\n', 1)
            message = json.loads(line)
            control['last'] = time.monotonic()
            if message.get('cancel'):
                control['cancel'] = True
        if DISCONNECTED or control['cancel'] or time.monotonic() - control['last'] > request.get('lease_seconds', 60):
            try:
                supervisor_ready = bool(Path(f'/proc/{child.pid}/task/{child.pid}/children').read_text().strip())
            except FileNotFoundError:
                supervisor_ready = False
            if not stopping and (supervisor_ready or time.monotonic() - started > 2):
                child.terminate()  # 原监督器负责其另建 session 的 timeout 与后代。
                stopping = True
        if time.monotonic() >= next_log and sent < 1024 * 1024:
            with (work / 'stdout.log').open('rb') as stream:
                stream.seek(offset)
                chunk = stream.read(min(4096, 1024 * 1024 - sent))
            if chunk:
                emit({'log': base64.b64encode(chunk).decode(), 'offset': offset})
                offset += len(chunk)
                sent += len(chunk)
            next_log = time.monotonic() + 1
        time.sleep(.05)
    # 快任务可能在第一次定时 tail 前退出，仍回传首块实时日志。
    if sent == 0:
        with (work / 'stdout.log').open('rb') as stream:
            chunk = stream.read(4096)
        if chunk:
            emit({'log': base64.b64encode(chunk).decode(), 'offset': 0})
    code = child.wait()
    code = code if code >= 0 else 128 - code
    with (work / 'stdout.log').open('rb') as stream:
        stream.seek(max(0, (work / 'stdout.log').stat().st_size - 65536))
        tail = stream.read(65536)
    evidence = {}
    for path in sorted((cwd / 'output/process').glob('*.json')):
        if path.stat().st_size <= 1024 * 1024:
            evidence[path.name] = json.loads(path.read_text())
    statuses = {p.name: p.read_text()[:65536] for p in (cwd / 'output').glob('status.*.log')}
    artifacts = []
    for path in work.rglob('*'):
        if path.is_file() and not path.is_symlink():
            artifacts.append({'path': path.relative_to(attempt).as_posix(), 'size': path.stat().st_size,
                              'partial': code != 0})
    result = {'job_id': request['job_id'], 'attempt_id': request['attempt_id'],
              'node': request['node'], 'attempt': str(attempt), 'return_code': code,
              'cancelled': stopping, 'elapsed_seconds': time.monotonic() - started,
              'tail': base64.b64encode(tail).decode(), 'evidence': evidence, 'statuses': statuses,
              'artifacts': artifacts, 'effective_argv': command, 'retrieval': 'complete',
              'execution_confirmed': len(evidence) == 1 and next(iter(evidence.values())).get('return_code') == code}
    if not result['execution_confirmed']:
        result['infrastructure_error'] = '监督器退出证据缺失或不一致，不能确认后代结束'
        result['remote_state'] = 'unknown'
        result['return_code'] = 125
    save(attempt / 'result.json', result)
    emit({'result': result})


def data(base, request):
    if request['action'] == 'list':
        emit([{'job_id': p.name, 'attempts': [a.name for a in sorted(p.glob('attempt-*'))]}
              for p in sorted((base / 'jobs').iterdir())] if (base / 'jobs').exists() else [])
        return
    job_id = request['job_id']
    if len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
        raise ValueError('非法 job-id')
    job = safe(base / 'jobs', job_id)
    attempts = sorted(job.glob('attempt-*'))
    if not attempts or any(not (p / 'result.json').is_file() for p in attempts):
        raise RuntimeError('任务不存在或 attempt 未确认结束')
    if request['action'] == 'summary':
        emit([json.loads((p / 'result.json').read_text()) for p in attempts])
    elif request['action'] == 'delete':
        if any(not json.loads((p / 'result.json').read_text()).get('execution_confirmed', False) for p in attempts):
            raise RuntimeError('执行退出证据未确认，拒绝删除')
        # start 与 delete 使用同一锁，活动任务无 result 时拒绝删除。
        with (job / 'start.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if any(not (p / 'result.json').is_file() for p in job.glob('attempt-*')):
                raise RuntimeError('存在活动 attempt')
            shutil.rmtree(job)
        emit({'deleted': job_id})
    elif request['action'] == 'fetch':
        with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz', dereference=False) as archive:
            archive.add(job, arcname=job_id)
    else:
        raise ValueError('未知数据操作')


def main():
    request = json.loads(read_line())
    base = Path(request['work_dir']).expanduser().resolve() / 'native'
    base.mkdir(parents=True, exist_ok=True)
    action = request['action']
    if action == 'stage':
        stage(base, request)
    elif action == 'owner':
        owner(base, request)
    elif action == 'execute':
        execute(base, request)
    elif action == 'inspect':
        path = safe(safe(base / 'jobs', request['job_id']), 'attempt-' + request['attempt_id'])
        if (path / 'result.json').is_file():
            emit({'result': json.loads((path / 'result.json').read_text())})
        else:
            emit({'unknown': True, 'exists': path.exists()})
    else:
        data(base, request)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('native worker: ' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(125)
    finally:
        if ACTIVE_CHILD is not None and ACTIVE_CHILD.poll() is None:
            ACTIVE_CHILD.terminate()
            ACTIVE_CHILD.wait(timeout=30)
