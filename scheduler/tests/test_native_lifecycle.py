"""真实进程验证租约、重复 START、共享节点互斥与缓存 ELF 运行库。"""
import base64
import fcntl
import time
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

from scheduler.native.cache import Cache
from scheduler.native.common import ROOT, SCHEDULER
from scheduler.native.inputs import runtime_files
from scheduler.native import transport


class WorkerLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=SCHEDULER / 'runtime')
        self.base = Path(self.tmp.name)
        self.node = dict(name='test', local=True, work_dir=str(self.base / 'node'))
        self.cache = Cache(self.base / 'cache')
        self.supervisor = self.base / 'supervisor.py'
        shutil.copy2(ROOT / 'isla/scripts/solve_process.py', self.supervisor)
        self.program = self.base / 'isarch'
        self.program.write_text('#!/usr/bin/env python3\nimport time\nprint("started", flush=True)\ntime.sleep(15)\n')
        self.program.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, elf=False):
        files = {'isla/scripts/solve_process.py': self.cache.freeze(self.supervisor),
                 'isla/target/release/isarch': self.cache.freeze(self.program)}
        loader = None
        args = []
        if elf:
            binary = Path('/usr/bin/getconf')
            if not binary.exists():
                self.skipTest('没有 getconf ELF fixture')
            files['isla/target/release/isarch'] = self.cache.freeze(binary)
            libraries, loader = runtime_files(binary)
            files.update({'_runtime/' + name: self.cache.freeze(source) for name, source in libraries.items()})
            args = ['GNU_LIBC_VERSION']
        argv = ['python3', 'scripts/solve_process.py', 'run', '--clause', 'TEST', '--',
                'timeout', '--signal=TERM', '--kill-after=1s', '20s', './target/release/isarch', *args]
        manifest = dict(entries=files, cwd='isla', effective_argv=argv, original_argv=argv,
                        binary_index=10, outputs=['output', 'outputs'], environment={}, loader=loader)
        transport.stage(self.node, 'ws', 'gen', files)
        return dict(action='execute', node='test', job_id=uuid.uuid4().hex, attempt_id=uuid.uuid4().hex,
                    workspace='ws', generation='gen', manifest=manifest, lease_seconds=.25)

    def collect(self, child):
        result = None
        try:
            for line in child.stdout:
                event = json.loads(line)
                if 'result' in event:
                    result = event['result']
            self.assertEqual(child.wait(timeout=5), 0, child.stderr.read().decode())
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            for stream in (child.stdin, child.stdout, child.stderr):
                if not stream.closed:
                    stream.close()
        self.assertIsNotNone(result)
        return result

    def test_expired_lease_cleans_supervisor_and_records_exit(self):
        request = self.request()
        result = self.collect(transport.start(self.node, request))
        self.assertEqual(result['return_code'], 143)
        self.assertTrue(result['cancelled'])
        evidence = next(iter(result['evidence'].values()))
        with self.assertRaises(ProcessLookupError):
            os.kill(evidence['timeout_pid'], 0)

    def test_closed_stdin_cancels_and_repeated_start_does_not_run_again(self):
        request = self.request()
        child = transport.start(self.node, request)
        first = transport.response(child)
        self.assertEqual(first['state'], 'RUNNING')
        child.stdin.close()
        result = self.collect(child)
        self.assertEqual(result['return_code'], 143)
        duplicate = self.collect(transport.start(self.node, request))
        self.assertEqual(result, duplicate)
        self.assertEqual(len(list((self.base / 'node/native/jobs' / request['job_id']).glob('attempt-*'))), 1)

    def test_cached_loader_executes_real_elf(self):
        request = self.request(elf=True)
        request['lease_seconds'] = 5
        result = self.collect(transport.start(self.node, request))
        self.assertEqual(result['return_code'], 0, result)
        self.assertIn('glibc', base64.b64decode(result['tail']).decode())
        self.assertIn('--library-path', result['effective_argv'])

    def test_missing_supervisor_evidence_stays_unconfirmed(self):
        self.supervisor.write_text('import sys; sys.exit(0)\n')
        request = self.request()
        result = self.collect(transport.start(self.node, request))
        self.assertEqual(result['return_code'], 125)
        self.assertFalse(result['execution_confirmed'])
        self.assertEqual(result['remote_state'], 'unknown')
        owner = transport.start(self.node, {'action': 'owner'})
        try:
            with self.assertRaises(RuntimeError):
                transport.response(owner)
        finally:
            owner.communicate()

    def test_node_owner_rejects_second_controller(self):
        first = transport.start(self.node, {'action': 'owner'})
        try:
            self.assertTrue(transport.response(first)['ready'])
            second = transport.start(self.node, {'action': 'owner'})
            try:
                with self.assertRaises(RuntimeError):
                    transport.response(second)
            finally:
                second.communicate()
        finally:
            first.communicate(b'{"close":true}\n', timeout=5)

    def test_worker_rejects_manifest_path_escape(self):
        request = self.request()
        request['manifest']['entries']['../outside'] = request['manifest']['entries']['isla/scripts/solve_process.py']
        child = transport.start(self.node, request)
        try:
            with self.assertRaises(RuntimeError):
                transport.response(child)
        finally:
            child.communicate()
        self.assertFalse((self.base / 'node/native/jobs' / request['job_id'] / 'outside').exists())

    def test_short_lease_heartbeat_keeps_task_alive_until_explicit_cancel(self):
        request = self.request()
        started = time.monotonic()
        result = transport.execute(self.node, request, lambda: time.monotonic() - started > .7,
                                   lambda message: None)
        self.assertEqual(result['return_code'], 143)
        self.assertGreaterEqual(time.monotonic() - started, .7)
        self.assertTrue(result['execution_confirmed'])

    def test_blocked_log_reader_does_not_prevent_eof_cleanup(self):
        self.program.write_text('#!/usr/bin/env python3\nimport time\nprint("x"*100000,flush=True)\ntime.sleep(15)\n')
        request = self.request()
        request['lease_seconds'] = 5
        child = transport.start(self.node, request)
        fcntl.fcntl(child.stdout.fileno(), fcntl.F_SETPIPE_SZ, 4096)
        try:
            event = transport.response(child)
            self.assertEqual(event['state'], 'RUNNING')
            child.stdin.close()
            child.wait(timeout=7)
            result = json.loads((Path(event['attempt']) / 'result.json').read_text())
            self.assertEqual(result['return_code'], 143)
            self.assertTrue(result['execution_confirmed'])
        finally:
            transport.close(child)

    def test_owner_rejects_start_intent_without_running_record(self):
        attempt = self.base / 'node/native/jobs' / ('a' * 32) / ('attempt-' + 'b' * 32)
        attempt.mkdir(parents=True)
        (attempt / 'task.json').write_text('{}')
        child = transport.start(self.node, {'action': 'owner'})
        try:
            with self.assertRaises(RuntimeError):
                transport.response(child)
        finally:
            transport.close(child)

    def test_cancel_cleans_descendants_that_ignore_term(self):
        from scheduler.native.common import process_identity
        grandchild = (
            'import os,signal,time; from pathlib import Path; '
            'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
            'Path("output/grandchild.pid").write_text(str(os.getpid())); time.sleep(20)')
        self.program.write_text('#!/usr/bin/env python3\nimport signal,subprocess,sys,time\n'
                                'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                                + 'subprocess.Popen([sys.executable,"-c",' + repr(grandchild) + '])\n'
                                + 'time.sleep(20)\n')
        request = self.request()
        request['lease_seconds'] = 5
        paths = []
        def event(message):
            if message.get('state') == 'RUNNING':
                paths.append(Path(message['attempt']) / 'work/root/isla/output/grandchild.pid')
        result = transport.execute(self.node, request, lambda: bool(paths and paths[0].exists()), event)
        self.assertEqual(result['return_code'], 143)
        self.assertTrue(result['execution_confirmed'])
        self.assertIsNone(process_identity(int(paths[0].read_text())))
