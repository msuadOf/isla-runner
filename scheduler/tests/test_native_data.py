import base64
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scheduler.native import data, transport
from scheduler.native.common import SCHEDULER


class DataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=SCHEDULER / 'runtime')
        self.base = Path(self.tmp.name)
        self.job_id = 'a' * 32
        self.attempt = self.base / 'node/native/jobs' / self.job_id / ('attempt-' + 'b' * 32)
        self.attempt.mkdir(parents=True)
        (self.attempt / 'work').mkdir()
        (self.attempt / 'work/result.json').write_text('large result')
        self.config = self.base / 'nodes.conf'
        self.config.write_text(f'''[[nodes]]
name="test"
local=true
address="localhost"
ssh_user="test"
cpus=2
priority=100
weight=1
work_dir={json.dumps(str(self.base / 'node'))}
''')

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, action, *extra):
        output = io.StringIO()
        with redirect_stdout(output):
            data.main(['--config', str(self.config), '--node', 'test', '--job-id', self.job_id,
                       action, *extra])
        return output.getvalue()

    def test_list_summary_fetch_delete(self):
        (self.attempt / 'result.json').write_text(json.dumps({'return_code': 0, 'execution_confirmed': True}))
        self.assertEqual(json.loads(self.call('list'))[0]['job_id'], self.job_id)
        self.assertEqual(json.loads(self.call('summary'))[0]['return_code'], 0)
        target = self.base / 'retrieved.tar.gz'
        self.call('fetch', '--destination', str(target))
        with tarfile.open(target) as archive:
            self.assertEqual(archive.extractfile(f'{self.job_id}/{self.attempt.name}/work/result.json').read(), b'large result')
        self.assertTrue(self.attempt.exists())
        self.assertEqual(json.loads(self.call('delete'))['deleted'], self.job_id)
        self.assertFalse(self.attempt.exists())

    def test_refuse_active_delete_and_path_escape(self):
        for action in ('delete', 'fetch', 'summary'):
            with self.subTest(action=action), self.assertRaises(RuntimeError):
                self.call(action)
        with self.assertRaises(RuntimeError):
            data.main(['--config', str(self.config), '--node', 'test', '--job-id', '../escape', 'delete'])
        self.assertTrue(self.attempt.exists())

    def test_remote_command_quotes_source_and_has_no_container_commands(self):
        node = dict(local=False, ssh_user='test', address='192.0.2.1')
        command = transport.command(node)
        self.assertEqual(command[0], 'ssh')
        self.assertIn('StrictHostKeyChecking=yes', command)
        import shlex
        remote = shlex.split(command[-1])
        self.assertEqual(remote[:3], ['python3', '-u', '-c'])
        self.assertEqual(remote[3], transport.SOURCE)
        self.assertNotIn('docker', command)
        self.assertNotIn('sudo', command)

    def test_mock_ssh_uses_remote_home_and_transfers_binary_once(self):
        # 模拟 SSH 的执行边界，仍用独立进程与真实 stdin/stdout 协议。
        home = self.base / 'remote home'
        home.mkdir()
        node = dict(local=False, address='test', ssh_user='test', work_dir='~/isla-runtime')
        original = transport.command
        def remote_command(node):
            return [sys.executable, '-u', '-c',
                    'import os; os.environ["HOME"]=' + repr(str(home)) + '; exec(' + repr(transport.SOURCE) + ')']
        from scheduler.native.cache import Cache
        source = self.base / 'IR with spaces.ir'
        source.write_bytes(bytes(range(256)) * 100)
        entry = Cache(self.base / 'cache').freeze(source)
        with patch.object(transport, 'command', side_effect=remote_command):
            first = transport.stage(node, 'workspace', 'generation', {'isla/model space.ir': entry})
            second = transport.stage(node, 'workspace', 'generation', {'isla/model space.ir': entry})
        self.assertEqual(first['transferred_bytes'], 25600)
        self.assertEqual(second['transferred_bytes'], 0)
        objects = home / 'isla-runtime/native/cache/workspace/objects'
        self.assertEqual(next(objects.glob('*-r')).read_bytes(), source.read_bytes())
