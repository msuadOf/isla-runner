"""SSH 只启动固定 worker；业务 argv 和路径通过 JSON / 二进制 stdin 传递。"""
import json
import os
from pathlib import Path
import select
import shlex
import subprocess
import sys
import tempfile
import threading
import time

SOURCE = (Path(__file__).with_name('worker.py')).read_text()


def command(node):
    argv = [sys.executable if node.get('local') else 'python3', '-u', '-c', SOURCE]
    if node.get('local'):
        return argv
    return ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=3',
            node['ssh_user'] + '@' + node['address'], shlex.join(argv)]


def errors(child):
    child.stderr.seek(0)
    return child.stderr.read(65536).decode(errors='replace')


def close(child):
    if child.poll() is None:
        child.kill()
    child.wait()
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def start(node, request):
    # SSH 诊断不占有限容量的 pipe；错误再从临时文件有界读取。
    stderr = tempfile.TemporaryFile()
    try:
        child = subprocess.Popen(command(node), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=stderr, bufsize=0)
    except Exception:
        stderr.close()
        raise
    child.stderr = stderr
    try:
        data = (json.dumps(dict(request, work_dir=node['work_dir'])) + '\n').encode()
        while data:
            data = data[child.stdin.write(data):]
        return child
    except Exception:
        close(child)
        raise


def response(child):
    buffer = getattr(child, '_response_buffer', b'')
    while b'\n' not in buffer:
        chunk = os.read(child.stdout.fileno(), 65536)
        if not chunk:
            code = child.wait()
            raise RuntimeError(f'worker 连接结束 ({code})：' + errors(child))
        buffer += chunk
    line, child._response_buffer = buffer.split(b'\n', 1)
    return json.loads(line)


def stage(node, workspace, generation, entries, cancelled=lambda: False):
    child = start(node, dict(action='stage', workspace=workspace, generation=generation,
                            entries=entries, local=node.get('local', False)))
    finished = threading.Event()

    def watchdog():
        deadline = time.monotonic() + 300
        while not finished.wait(.1):
            if cancelled() or time.monotonic() >= deadline:
                child.kill()
                return

    thread = threading.Thread(target=watchdog)
    thread.start()
    try:
        missing = response(child)['missing']
        objects = {e['digest']: e for e in entries.values()}
        for key in missing:
            with open(objects[key]['source'], 'rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    view = memoryview(chunk)
                    while view:
                        view = view[child.stdin.write(view):]
        result = response(child)
        child.stdin.close()
        if child.wait() != 0:
            raise RuntimeError(errors(child))
        return result
    finally:
        finished.set()
        thread.join()
        close(child)


def execute(node, request, cancelled, event):
    child = start(node, dict(request, action='execute'))
    # 单一 IO 循环：心跳写入不能把退出线程卡在 Python pipe 锁上。
    os.set_blocking(child.stdin.fileno(), False)
    os.set_blocking(child.stdout.fileno(), False)
    buffer = b''
    next_heartbeat = 0
    interval = min(2, request.get('lease_seconds', 60) / 3)
    try:
        while True:
            if time.monotonic() >= next_heartbeat:
                message = (json.dumps({'cancel': cancelled()}) + '\n').encode()
                try:
                    written = os.write(child.stdin.fileno(), message)
                    if written != len(message):
                        raise RuntimeError('控制消息未完整写入')
                except BlockingIOError:
                    pass  # 租约仍由 worker 在控制通道不可用时结束任务。
                except BrokenPipeError:
                    pass  # 继续读取已落盘的最终结果。
                next_heartbeat = time.monotonic() + interval
            if not select.select([child.stdout], [], [], min(interval, .1))[0]:
                continue
            chunk = os.read(child.stdout.fileno(), 65536)
            if not chunk:
                code = child.wait()
                raise RuntimeError(f'worker 连接结束 ({code})：' + errors(child))
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                message = json.loads(line)
                event(message)
                if 'result' in message:
                    return message['result']
    finally:
        child.stdin.close()  # EOF 由 worker 转发给原监督器；不提前终止清理。
        try:
            child.wait(timeout=25)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
        close(child)


def inspect(node, job_id, attempt_id):
    child = start(node, {'action': 'inspect', 'job_id': job_id, 'attempt_id': attempt_id})
    timer = threading.Timer(15, child.kill)
    timer.start()
    try:
        reply = response(child)
        child.stdin.close()
        child.wait(timeout=5)
        return reply.get('result')
    finally:
        timer.cancel()
        timer.join()
        close(child)
