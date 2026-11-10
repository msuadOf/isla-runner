"""local 只用原 cwd、argv 与运行环境；输入冻结必须延后到远端选定。"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scheduler.native.common import SCHEDULER
from scheduler.native.controller import Controller


class LocalDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=SCHEDULER / 'runtime')
        self.base = Path(self.tmp.name)
        self.cwd = self.base / 'isla'
        (self.cwd / 'scripts').mkdir(parents=True)
        (self.cwd / 'scripts/solve_process.py').write_text('')
        self.run = self.base / 'native/runs/test'
        self.run.mkdir(parents=True)
        self.node = dict(name='local', local=True, cpus=128, weight=4, priority=100)
        self.config = {'nodes': [self.node]}
        self.controller = Controller(self.run, self.config, self.base)
        self.request = dict(cwd=str(self.cwd), argv=['python3', 'scripts/solve_process.py', 'run', '--clause', 'TEST',
            '--', 'timeout', '1m', './target/release/isarch', '-A', './model.ir', '-C', './config.toml', '-T', '32'])

    def tearDown(self):
        self.controller.close()
        self.tmp.cleanup()

    def test_prepare_does_not_create_or_read_cache_or_runtime(self):
        with patch('scheduler.native.controller.Cache', side_effect=AssertionError('local 不应建立缓存')), \
             patch('scheduler.native.controller.runtime_files', side_effect=AssertionError('local 不应解析运行库')):
            manifest = self.controller.prepare(self.request)
        self.assertEqual(manifest['cwd'], str(self.cwd))
        self.assertEqual(manifest['original_argv'], self.request['argv'])
        self.assertEqual(manifest['cores'], 32)
        self.assertFalse(list(self.base.rglob('objects')))

    def test_local_dispatch_skips_transport_and_keeps_reservation_until_completion(self):
        manifest = self.controller.prepare(self.request)
        job = dict(job_id='a' * 32, attempt_id='b' * 32, manifest=manifest, node='local')
        self.controller.jobs[job['job_id']] = job
        self.assertEqual(self.controller.qos.reserve(job['job_id'], 32), 'local')
        directory = self.run / 'jobs' / job['job_id']
        directory.mkdir()
        (directory / 'local-result.json').write_text(json.dumps({
            'return_code': 0, 'local': True, 'execution_confirmed': True}))
        with patch('scheduler.native.controller.transport.stage', side_effect=AssertionError('local 不应 stage')), \
             patch('scheduler.native.controller.transport.execute', side_effect=AssertionError('local 不应经过 worker')):
            self.controller.perform(job)
        self.assertEqual(job['state'], 'SUCCEEDED')
        self.assertEqual(self.controller.qos.nodes['local']['reserved'], 0)
        self.assertEqual(json.loads((directory / 'local.json').read_text())['manifest']['cwd'], str(self.cwd))
        self.assertFalse(list(self.base.rglob('objects')))
        self.assertFalse(list(self.base.rglob('work/root')))
