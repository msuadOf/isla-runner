#!/usr/bin/env python3
"""保持 GNU Make 的 DAG 与进度，通过附加 -include 安装分布式 exec 接点。"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import shlex
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
        variable = value.split('=', 1)[0].rstrip(':+?!').strip()
        if variable in ('SHELL', '.SHELLFLAGS') or variable.startswith('SCHEDULER_') or value.startswith(('--eval', '-E')):
            raise ValueError('不支持显式 SHELL/.SHELLFLAGS/接入变量覆盖或 --eval')
        if value == '--':
            raise ValueError('包装入口不支持 Make 参数中的 --；目标与赋值请直接传入')
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
            if value in ('-f-', '--file=-', '--makefile=-'):
                raise ValueError('不支持从 stdin 加载 Makefile')
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
    for key in ('MAKEFLAGS', 'GNUMAKEFLAGS'):
        inherited = shlex.split(os.environ.get(key, ''))
        inherited = [x for x in inherited if x != '--']
        inherited_cwd, inherited_file = make_context(inherited, Path.cwd())
        if inherited_file or inherited_cwd != Path.cwd().resolve():
            raise ValueError(f'{key} 中不支持隐藏的 -C/-f 参数')
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
        make = None
        controller = None
        received = []
        def cancel(number, frame):
            received.append(number)
            (run / 'stop').touch()
            if make is not None and make.poll() is None:
                try:
                    os.killpg(make.pid, number)
                except ProcessLookupError:
                    pass
        previous = {s: signal.signal(s, cancel) for s in (signal.SIGINT, signal.SIGTERM)}
        code = 125
        try:
            print('scheduler run: ' + str(run), file=sys.stderr, flush=True)
            with (run / 'controller.log').open('wb') as log:
                controller = subprocess.Popen([sys.executable, str(SCHEDULER / 'native/controller.py'),
                                '--run', str(run), '--config', str(Path(args.config).resolve()),
                                '--workspace', str(Path(args.workspace).resolve())], stdout=log, stderr=log,
                                start_new_session=True)
            deadline = time.monotonic() + 35
            while not (run / 'ready.json').exists():
                if received:
                    return 128 + received[0]
                if controller.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('controller 启动失败，详见 ' + str(run / 'controller.log'))
                time.sleep(.05)
            if received:
                return 128 + received[0]
            ready = json.loads((run / 'ready.json').read_text())
            if 'error' in ready:
                raise RuntimeError(ready['error'] + '，详见 ' + str(run / 'preflight.json'))
            for name, report in json.loads((run / 'preflight.json').read_text()).items():
                if 'error' in report:
                    print(f'scheduler：节点 {name} 未接单：{report["error"].strip()}', file=sys.stderr, flush=True)
            env = dict(os.environ, ISLA_SCHEDULER_RUN=str(run))
            make = subprocess.Popen(['make', *argv], env=env, start_new_session=True)
            controller_failed = False
            while make.poll() is None:
                if controller.poll() is not None or received:
                    controller_failed = not received
                    (run / 'stop').touch()
                    try:
                        os.killpg(make.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        make.wait(timeout=35)
                    except subprocess.TimeoutExpired:
                        os.killpg(make.pid, signal.SIGKILL)
                        make.wait()
                    break
                time.sleep(.05)
            code = make.returncode
            code = 125 if controller_failed else code if code >= 0 else 128 - code
        finally:
            (run / 'stop').touch()
            if make is not None and make.poll() is None:
                try:
                    os.killpg(make.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    make.wait(timeout=35)
                except subprocess.TimeoutExpired:
                    os.killpg(make.pid, signal.SIGKILL)
                    make.wait()
            if controller is not None:
                try:
                    controller.wait(timeout=100)
                except subprocess.TimeoutExpired:
                    controller.terminate()
                    try:
                        controller.wait(timeout=35)
                    except subprocess.TimeoutExpired:
                        controller.kill()
                        controller.wait()
            atomic_json(run / 'ended.json', {'make_return_code': code,
                                             'controller_return_code': controller.returncode if controller is not None else None})
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        return 128 + received[0] if received else code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, IndexError) as error:
        print('scheduler: ' + str(error), file=sys.stderr)
        raise SystemExit(125)
