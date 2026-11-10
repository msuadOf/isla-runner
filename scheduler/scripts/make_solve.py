#!/usr/bin/env python3
"""保持 GNU Make 的 DAG 与进度，通过附加 -include 安装分布式 exec 接点。"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scheduler.native.common import ROOT, SCHEDULER, atomic_json, load_config


def make_context(argv, cwd):
    cwd = Path(cwd).resolve()
    has_file = False
    i = 0
    while i < len(argv):
        value = argv[i]
        if value.startswith(('SHELL=', '.SHELLFLAGS=', 'SCHEDULER_', '--eval')):
            raise ValueError('不支持显式 SHELL/.SHELLFLAGS/接入变量覆盖或 --eval')
        if value in ('-C', '--directory'):
            i += 1
            cwd = (cwd / argv[i]).resolve(strict=True)
        elif value.startswith('--directory='):
            cwd = (cwd / value.split('=', 1)[1]).resolve(strict=True)
        elif value.startswith('-C'):
            cwd = (cwd / value[2:]).resolve(strict=True)
        elif value in ('-f', '--file', '--makefile'):
            has_file = True
            i += 1
            if argv[i] == '-':
                raise ValueError('不支持从 stdin 加载 Makefile')
        elif value.startswith(('-f', '--file=', '--makefile=')):
            has_file = True
        i += 1
    return cwd, has_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(SCHEDULER / 'nodes.conf'))
    parser.add_argument('--workspace', default=str(ROOT))
    parser.add_argument('make_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.make_args
    if argv[:1] == ['--']:
        argv = argv[1:]
    cwd, has_file = make_context(argv, Path.cwd())
    cwd.relative_to(Path(args.workspace).resolve())
    if any(x.startswith(('SHELL=', '.SHELLFLAGS=')) for x in os.environ.get('MAKEFLAGS', '').split()):
        raise ValueError('MAKEFLAGS 中含不兼容的 shell 覆盖')
    config = load_config(args.config)
    native = SCHEDULER / 'runtime/native'
    locks = native / 'locks'
    locks.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(cwd).encode()).hexdigest()[:24]
    with (locks / (key + '.lock')).open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f'scheduler：等待同一工作目录的 Make 结束：{cwd}', file=sys.stderr, flush=True)
            fcntl.flock(lock, fcntl.LOCK_EX)
        run = native / 'runs' / uuid.uuid4().hex
        run.mkdir(parents=True)
        print('scheduler run: ' + str(run), file=sys.stderr, flush=True)
        attach = run / 'attach.mk'
        include = str(SCHEDULER / 'integration/solve.mk').replace(' ', '\\ ')
        attach.write_text('-include ' + include + '\n')
        if not has_file:
            default = next((p for p in ('GNUmakefile', 'makefile', 'Makefile') if (cwd / p).is_file()), None)
            if default is None:
                raise ValueError('没有找到原生 Makefile')
            argv = [*argv, '-f', default]
        argv = [*argv, '-f', str(attach), 'SCHEDULER_SHELL=' + str(SCHEDULER / 'integration/make_shell.py')]
        atomic_json(run / 'invocation.json', {'argv': argv, 'cwd': str(cwd), 'workspace': args.workspace,
                                              'config': config, 'started': time.time()})
        with (run / 'controller.log').open('wb') as log:
            controller = subprocess.Popen([sys.executable, str(SCHEDULER / 'native/controller.py'),
                            '--run', str(run), '--config', str(Path(args.config).resolve()),
                            '--workspace', str(Path(args.workspace).resolve())], stdout=log, stderr=log,
                            start_new_session=True)
        make = None
        received = []
        def cancel(number, frame):
            received.append(number)
            (run / 'stop').touch()
            if make is not None and make.poll() is None:
                os.killpg(make.pid, number)
        previous = {s: signal.signal(s, cancel) for s in (signal.SIGINT, signal.SIGTERM)}
        code = 125
        try:
            deadline = time.monotonic() + 35
            while not (run / 'ready.json').exists():
                if controller.poll() is not None or time.monotonic() >= deadline or received:
                    raise RuntimeError('controller 启动失败，详见 ' + str(run / 'controller.log'))
                time.sleep(.05)
            ready = json.loads((run / 'ready.json').read_text())
            if 'error' in ready:
                raise RuntimeError(ready['error'] + '，详见 ' + str(run / 'preflight.json'))
            for name, report in json.loads((run / 'preflight.json').read_text()).items():
                if 'error' in report:
                    print(f'scheduler：节点 {name} 未接单：{report["error"].strip()}', file=sys.stderr, flush=True)
            env = dict(os.environ, ISLA_SCHEDULER_RUN=str(run))
            make = subprocess.Popen(['make', *argv], env=env, start_new_session=True)
            code = make.wait()
            code = code if code >= 0 else 128 - code
        finally:
            (run / 'stop').touch()
            if make is not None and make.poll() is None:
                os.killpg(make.pid, signal.SIGTERM)
                make.wait()
            try:
                controller.wait(timeout=100)
            except subprocess.TimeoutExpired:
                controller.terminate()
                controller.wait(timeout=10)
            atomic_json(run / 'ended.json', {'make_return_code': code,
                                             'controller_return_code': controller.returncode})
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        return 128 + received[0] if received else code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, IndexError) as error:
        print('scheduler: ' + str(error), file=sys.stderr)
        raise SystemExit(125)
