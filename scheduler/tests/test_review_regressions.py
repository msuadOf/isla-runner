"""本轮评审发现的故障、取消、输入与资源释放回归。"""
import base64
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from scheduler.native.common import SCHEDULER, process_identity, load_config
from scheduler.native.controller import Controller
from scheduler.native import transport, data
from scheduler.scripts.make_solve import make_context


class ReviewControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=SCHEDULER / 'runtime')
        self.base = Path(self.tmp.name)
        self.run = self.base / 'native/runs/review'
        self.run.mkdir(parents=True)
        self.cwd = self.base / 'isla'
        for directory in ('scripts', 'target/release', 'configs'):
            (self.cwd / directory).mkdir(parents=True)
        for name in ('scripts/solve_process.py', 'target/release/isarch', 'model.ir'):
            (self.cwd / name).write_text('')
        (self.cwd / 'configs/isa.toml').write_text('name="test"')
        self.node = dict(name='node', local=True, work_dir=str(self.base / 'node'), cpus=128,
                         weight=1, priority=100)
        self.controller = Controller(self.run, {'nodes': [self.node]}, self.base)
        self.argv = ['python3', 'scripts/solve_process.py', 'run', '--clause', 'TEST', '--',
                     'timeout', '1m', './target/release/isarch', '-A', 'model.ir', '-C', 'configs/isa.toml', '-T', '32']

    def tearDown(self):
        self.controller.close()
        self.tmp.cleanup()

    def job(self, local=True):
        self.controller.qos.nodes['node']['local'] = local
        job = dict(job_id='a' * 32, attempt_id='b' * 32, node='node',
                   manifest=self.controller.prepare(dict(argv=self.argv, cwd=str(self.cwd))))
        self.controller.jobs[job['job_id']] = job
        self.controller.qos.reserve(job['job_id'], 32)
        self.controller.state(job, 'RESERVED')
        return job

    def test_preflight_launch_error_only_marks_that_node_offline(self):
        with patch.object(transport, 'start', side_effect=FileNotFoundError('ssh')):
            name, report = self.controller.preflight(self.node)
        self.assertEqual(name, 'node')
        self.assertIn('ssh', report['error'])
        self.assertFalse(self.controller.qos.nodes['node']['online'])

    def test_local_exception_finishes_request_instead_of_hanging_proxy(self):
        job = self.job()
        with patch.object(self.controller, 'perform_local', side_effect=RuntimeError('failed before start')):
            self.controller.perform(job)
        self.assertEqual(job['state'], 'FAILED')
        self.assertEqual(self.controller.qos.nodes['node']['reserved'], 0)
        self.assertTrue((self.run / 'jobs' / job['job_id'] / 'result.json').exists())

    def test_local_uncertain_exception_keeps_reservation_and_blocks_reuse(self):
        job = self.job()
        directory = self.run / 'jobs' / job['job_id']
        (directory / 'local.json').write_text('{}')
        with patch.object(self.controller, 'perform_local', side_effect=RuntimeError('started but unconfirmed')):
            self.controller.perform(job)
        self.assertEqual(job['state'], 'UNKNOWN')
        self.assertEqual(self.controller.qos.nodes['node']['reserved'], 32)
        self.assertTrue((self.base / 'node/native/local-unknown' / (job['job_id'] + '.json')).exists())

    def test_staging_failure_releases_and_requeues_without_duplicate_execution(self):
        job = self.job(local=False)
        manifest = dict(generation='gen', entries={})
        with patch.object(self.controller, 'prepare_remote', return_value=manifest), \
             patch.object(transport, 'stage', side_effect=RuntimeError('staging failed')), \
             patch.object(transport, 'execute') as execute:
            self.controller.perform(job)
        self.assertEqual(job['state'], 'WAITING')
        self.assertEqual(self.controller.qos.nodes['node']['reserved'], 0)
        self.assertFalse(self.controller.qos.nodes['node']['online'])
        execute.assert_not_called()

    def test_cancelled_staging_releases_without_offlining_healthy_node(self):
        job = self.job(local=False)
        (self.run / 'cancel' / job['job_id']).touch()
        with patch.object(self.controller, 'prepare_remote', return_value=dict(generation='gen', entries={})), \
             patch.object(transport, 'stage', side_effect=RuntimeError('cancelled transport')):
            self.controller.perform(job)
        self.assertEqual(job['state'], 'CANCELLED')
        self.assertEqual(self.controller.qos.nodes['node']['reserved'], 0)
        self.assertTrue(self.controller.qos.nodes['node']['online'])

    def test_confirmed_result_releases_even_if_tail_retrieval_fails(self):
        job = self.job(local=False)
        result = dict(return_code=7, execution_confirmed=True, tail=base64.b64encode(b'log').decode())
        with patch.object(Path, 'write_bytes', side_effect=OSError('cannot store tail')):
            self.controller.collect_result(job, result)
        self.assertEqual(self.controller.qos.nodes['node']['reserved'], 0)
        self.assertEqual(job['return_code'], 7)
        self.assertEqual(result['retrieval'], 'pending')

    def test_freezing_inputs_does_not_hold_scheduler_transaction_lock(self):
        entered = threading.Event()
        leave = threading.Event()
        errors = []
        def freeze(source):
            entered.set()
            leave.wait(3)
            return dict(digest='a' * 64 + '-r', size=0, mode=0o444, source=str(source))
        def prepare():
            try:
                self.controller.prepare_remote(self.controller.prepare(dict(argv=self.argv, cwd=str(self.cwd))))
            except Exception as error:
                errors.append(error)
        with patch('scheduler.native.controller.Cache') as cache:
            cache.return_value.freeze.side_effect = freeze
            thread = threading.Thread(target=prepare)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                acquired = self.controller.lock.acquire(timeout=.2)
                if acquired:
                    self.controller.lock.release()
                self.assertTrue(acquired)
            finally:
                leave.set()
                thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_malformed_request_becomes_failed_job(self):
        path = self.run / 'requests' / ('a' * 32 + '.json')
        path.write_text('{invalid')
        self.controller.ingest()
        self.assertEqual(self.controller.jobs[path.stem]['state'], 'FAILED')


class ReviewBoundaryTests(unittest.TestCase):
    def test_make_context_rejects_shell_variants_and_stdin_makefiles(self):
        for value in ('SHELL:=bash', 'SHELL+=bash', '.SHELLFLAGS?=-c', '-f-', '--file=-',
                      '--makefile=-', '--', '-Eabc'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                make_context([value], SCHEDULER)

    def test_invalid_job_id_is_rejected_before_opening_transport(self):
        with patch.object(transport, 'start', side_effect=AssertionError('should not connect')):
            for value in ('../escape', '', 'not-a-job'):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    data.main(['--node', 'preston', '--job-id', value, 'fetch'])

    def test_worker_diagnostics_cannot_fill_stderr_pipe(self):
        source = 'import os,json; os.read(0,65536); os.write(2,b"x"*262144); print(json.dumps({"ready":True}),flush=True)'
        with patch.object(transport, 'command', return_value=[sys.executable, '-u', '-c', source]):
            child = transport.start({'local': True, 'work_dir': 'unused'}, {})
        try:
            with selectors.DefaultSelector() as ready:
                ready.register(child.stdout, selectors.EVENT_READ)
                self.assertTrue(ready.select(3))
            self.assertTrue(transport.response(child)['ready'])
            child.wait(timeout=3)
            self.assertEqual(len(transport.errors(child)), 65536)
        finally:
            transport.close(child)

    def test_zombie_controller_is_not_reported_alive(self):
        child = subprocess.Popen([sys.executable, '-c', 'pass'])
        try:
            deadline = time.monotonic() + 3
            while process_identity(child.pid) is not None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertIsNone(process_identity(child.pid))
        finally:
            child.wait()

    def test_stage_waiting_for_single_flight_lock_is_cancellable(self):
        import fcntl
        with tempfile.TemporaryDirectory(dir=SCHEDULER / 'runtime') as directory:
            base = Path(directory)
            cache = base / 'native/cache/ws'
            cache.mkdir(parents=True)
            with (cache / 'stage.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                started = time.monotonic()
                with self.assertRaises(RuntimeError):
                    transport.stage(dict(local=True, work_dir=str(base)), 'ws', 'gen', {},
                                    cancelled=lambda: time.monotonic() - started >= .2)
                self.assertLess(time.monotonic() - started, 2)

    def test_invalid_lease_and_external_reservation_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=SCHEDULER / 'runtime') as directory:
            path = Path(directory) / 'nodes.conf'
            node = '[[nodes]]\nname="node"\nlocal=false\naddress="localhost"\nssh_user="test"\ncpus=32\nweight=1\npriority=1\n'
            for external in (-1, 33, 1.5, True):
                with self.subTest(external=external):
                    value = str(external).lower()
                    path.write_text(node + f'external_cores={value}\n')
                    with self.assertRaises(ValueError):
                        load_config(path)
            for lease in ('nan', 'inf', 'true', '0', '-1'):
                with self.subTest(lease=lease):
                    path.write_text('[native]\nlease_seconds=' + lease + '\n' + node)
                    with self.assertRaises(ValueError):
                        load_config(path)
