"""SSH 只启动固定 worker；业务 argv 和路径通过 JSON / 二进制 stdin 传递。"""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import threading

SOURCE = (Path(__file__).with_name('worker.py')).read_text()


def command(node):
    argv = [sys.executable if node.get('local') else 'python3', '-u', '-c', SOURCE]
    if node.get('local'):
        return argv
    return ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=3',
            node['ssh_user'] + '@' + node['address'], shlex.join(argv)]


def start(node, request):
    child = subprocess.Popen(command(node), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    try:
        child.stdin.write((json.dumps(dict(request, work_dir=node['work_dir'])) + '\n').encode())
        child.stdin.flush()
        return child
    except Exception:
        child.kill()
        child.communicate()
        raise


def response(child):
    line = child.stdout.readline()
    if not line:
        code = child.wait()
        raise RuntimeError(f'worker 连接结束 ({code})：' + child.stderr.read(65536).decode(errors='replace'))
    return json.loads(line)


def stage(node, workspace, generation, entries):
    child = start(node, dict(action='stage', workspace=workspace, generation=generation,
                            entries=entries, local=node.get('local', False)))
    timer = threading.Timer(300, child.kill)
    timer.daemon = True
    timer.start()
    try:
        missing = response(child)['missing']
        objects = {e['digest']: e for e in entries.values()}
        for key in missing:
            with open(objects[key]['source'], 'rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    child.stdin.write(chunk)
        child.stdin.flush()
        result = response(child)
        child.stdin.close()
        if child.wait() != 0:
            raise RuntimeError(child.stderr.read().decode(errors='replace'))
        return result
    finally:
        timer.cancel()
        if child.poll() is None:
            child.kill()
            child.wait()
        child.stdout.close()
        child.stderr.close()
        if not child.stdin.closed:
            child.stdin.close()


def execute(node, request, cancelled, event):
    child = start(node, dict(request, action='execute'))
    finished = threading.Event()

    def heartbeat():
        while not finished.is_set():
            try:
                child.stdin.write((json.dumps({'cancel': cancelled()}) + '\n').encode())
                child.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                return
            finished.wait(2)

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        while True:
            message = response(child)
            event(message)
            if 'result' in message:
                return message['result']
    finally:
        finished.set()
        thread.join(timeout=3)
        child.stdin.close()  # EOF 也触发 worker 的定向取消。
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.terminate()
            child.wait(timeout=5)
        child.stdout.close()
        child.stderr.close()


def inspect(node, job_id, attempt_id):
    child = start(node, {'action': 'inspect', 'job_id': job_id, 'attempt_id': attempt_id})
    timer = threading.Timer(15, child.kill)
    timer.daemon = True
    timer.start()
    try:
        reply = response(child)
        child.stdin.close()
        child.wait(timeout=5)
        return reply.get('result')
    finally:
        timer.cancel()
        if child.poll() is None:
            child.kill()
            child.wait()
        for stream in (child.stdin, child.stdout, child.stderr):
            if not stream.closed:
                stream.close()
