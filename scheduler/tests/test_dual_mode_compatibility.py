"""复制现有 run.mk 与监督器，用小程序验证真实 Make，不修改 isla/。"""
import json
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import signal
import sqlite3
from contextlib import closing
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from scheduler.integration.make_shell import validate
from scheduler.native.common import ROOT, SCHEDULER
from scheduler.scripts.make_solve import make_context


class DualModeTests(unittest.TestCase):
    def setUp(self):
        (SCHEDULER / 'runtime').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=SCHEDULER / 'runtime')
        self.base = Path(self.tmp.name)
        self.cwd = self.base / 'isla'
        for name in ('scripts', 'configs', 'target/release'):
            (self.cwd / name).mkdir(parents=True)
        for name in ('run.mk', 'run_ctrl_c.mk', 'solve_process.py'):
            shutil.copy2(ROOT / 'isla/scripts' / name, self.cwd / 'scripts' / name)
        (self.cwd / 'model.ir').write_text('model-data')
        (self.cwd / 'configs/isa.toml').write_text('name="config-data"')
        (self.base / 'limits.toml').write_text('file="model/source.sail"')
        self.fake = self.cwd / 'target/release/isarch'
        self.fake.write_text('''#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
args=sys.argv[1:]
assert Path(args[args.index('-A')+1]).read_text() == 'model-data'
assert 'config-data' in Path(args[args.index('-C')+1]).read_text()
if '--execution-limits-config' in args:
 assert 'source.sail' in Path(args[args.index('--execution-limits-config')+1]).read_text()
clause=next(x.split('=',1)[1] for x in args if x.startswith('--clause='))
print('task-start-'+clause, flush=True)
print('error-line-'+clause, file=sys.stderr, flush=True)
print('x'*70000, flush=True)
time.sleep(15 if clause == 'SLOW' else .1)
Path('output/trace/native-'+clause+'.txt').write_text('trace')
Path('outputs/native-'+clause+'.txt').write_text('output')
Path('output/result-'+clause+'.json').write_text(json.dumps({'cwd':str(Path.cwd()),'argv':args,
 'custom_env':os.environ.get('LOCAL_TEST_ENV'), 'tmpdir':os.environ.get('TMPDIR')}))
sys.exit(7 if clause == 'FAIL' else 0)
''')
        self.fake.chmod(0o755)
        bindir = self.base / 'bin'
        bindir.mkdir()
        (bindir / 'cargo').write_text('#!/bin/sh\nexit 0\n')
        (bindir / 'cargo').chmod(0o755)
        (bindir / 'ssh').write_text('#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n'
                                  + 'Path(' + repr(str(self.base / 'ssh-called')) + ').touch()\nsys.exit(99)\n')
        (bindir / 'ssh').chmod(0o755)
        (self.base / 'original-tmp').mkdir()
        self.env = dict(os.environ, LOCAL_TEST_ENV='preserve-me', TMPDIR=str(self.base / 'original-tmp'), PATH=str(bindir) + ':' + os.environ['PATH'], PYTHONDONTWRITEBYTECODE='1')
        self.config = self.base / 'nodes.conf'
        self.config.write_text(f'''[native]
backend="ssh"
[[nodes]]
name="test-local"
address="127.0.0.1"
ssh_user="test"
local=true
cpus=2
priority=100
weight=4
work_dir={json.dumps(str(self.base / 'node'))}
''')
        self.run_dirs = []

    def tearDown(self):
        for run in self.run_dirs:
            shutil.rmtree(run, ignore_errors=True)
        self.tmp.cleanup()

    def args(self, clauses='OK'):
        return ['-C', str(self.cwd), '-f', 'scripts/run.mk', 'solve', '-j4',
                'ACTIVE_ALL=' + clauses, 'IR_FILE=./model.ir', 'ISA_CONFIG=./configs/isa.toml',
                'EXECUTION_LIMITS_CONFIG=../limits.toml', 'THREADS=1', 'ITRACE=0']

    def wrapped(self, clauses='OK'):
        return [sys.executable, str(SCHEDULER / 'scripts/make_solve.py'), '--config', str(self.config),
                '--workspace', str(self.base), '--', *self.args(clauses)]

    def capture_run(self, result):
        line = next(x for x in result.stderr.splitlines() if x.startswith('scheduler run: '))
        run = Path(line[len('scheduler run: '):])
        self.run_dirs.append(run)
        return run

    def test_original_make_stays_local_and_has_no_scheduler_state(self):
        before = set((SCHEDULER / 'runtime/native/runs').glob('*'))
        result = subprocess.run(['make', *self.args()], env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('[1/1] solve-OK', result.stdout)
        data = json.loads((self.cwd / 'output/result-OK.json').read_text())
        self.assertEqual(data['cwd'], str(self.cwd))
        self.assertEqual(before, set((SCHEDULER / 'runtime/native/runs').glob('*')))
        self.assertNotIn('scheduler', (self.cwd / 'output/log/OK.log').read_text())

    def test_wrapped_parallel_jobs_inputs_progress_results_and_retained_output(self):
        result = subprocess.run(self.wrapped('OK OTHER'), env=self.env, capture_output=True, text=True, timeout=35)
        run = self.capture_run(result)
        self.assertEqual(result.returncode, 0, result.stderr + (run / 'controller.log').read_text())
        self.assertIn('[1/2] solve-', result.stdout)
        self.assertIn('[2/2] solve-', result.stdout)
        output = json.loads((self.cwd / 'output/result-OK.json').read_text())
        self.assertEqual(output['cwd'], str(self.cwd))
        self.assertEqual(output['custom_env'], 'preserve-me')
        self.assertEqual(output['tmpdir'], self.env['TMPDIR'])
        self.assertTrue((self.cwd / 'output/trace/native-OK.txt').exists())
        self.assertTrue((self.cwd / 'outputs/native-OK.txt').exists())
        self.assertIn('OK intime', (self.cwd / 'output/status.intime.log').read_text())
        reports = [json.loads(p.read_text()) for p in (run / 'jobs').glob('*/result.json')]
        self.assertEqual(len(reports), 2)
        for report in reports:
            self.assertEqual(report['return_code'], 0)
            self.assertEqual(len(report['evidence']), 1)
            self.assertEqual(report['node'], 'test-local')
            self.assertTrue(report['local'])
            self.assertEqual(report['cwd'], str(self.cwd))
            self.assertNotIn('--library-path', report['effective_argv'])
            self.assertEqual(report['effective_argv'][0], sys.executable)
            self.assertEqual(Path(next(iter(report['evidence'].values()))['cwd']), self.cwd)
        log = (self.cwd / 'output/log/OK.log').read_text()
        self.assertIn('task-start-OK', log)
        self.assertEqual(log.count('task-start-OK'), 1)
        self.assertEqual(log.count('error-line-OK'), 1)
        self.assertEqual(log.count('x'), 70000)
        self.assertNotIn('[scheduler]', log)
        self.assertFalse((self.base / 'node/native/cache').exists())
        self.assertFalse((self.base / 'ssh-called').exists())
        workspace_id = hashlib.sha256(str(self.base.resolve()).encode()).hexdigest()[:24]
        self.assertFalse((SCHEDULER / 'runtime/native/cache' / workspace_id).exists())
        self.assertFalse(list((self.base / 'node/native').glob('jobs/*/attempt-*/work/root')))
        self.assertFalse(list((run / 'jobs').glob('*/tail.log')))

    def test_worker_code_preserved_and_make_fails(self):
        result = subprocess.run(self.wrapped('FAIL'), env=self.env, capture_output=True, text=True, timeout=35)
        run = self.capture_run(result)
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(next((run / 'jobs').glob('*/result.json')).read_text())
        self.assertEqual(report['return_code'], 7)
        self.assertRegex(result.stderr, r'(Error|错误) 7')

    def test_wrapper_sigterm_cancels_only_this_run(self):
        process = subprocess.Popen(self.wrapped('SLOW'), env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        first = process.stderr.readline()
        self.assertTrue(first.startswith('scheduler run: '), first)
        run = Path(first.split(': ', 1)[1].strip())
        self.run_dirs.append(run)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            states = [json.loads(p.read_text()) for p in (run / 'jobs').glob('*/state.json')]
            if any(s['state'] == 'RUNNING' for s in states):
                break
            time.sleep(.05)
        else:
            process.terminate()
            output, error = process.communicate(timeout=20)
            self.fail('没有进入 RUNNING: ' + error + (run / 'controller.log').read_text())
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if 'task-start-SLOW' in (self.cwd / 'output/log/SLOW.log').read_text():
                break
            time.sleep(.02)
        self.assertIn('task-start-SLOW', (self.cwd / 'output/log/SLOW.log').read_text())
        self.assertIsNone(process.poll())
        process.send_signal(signal.SIGTERM)
        output, error = process.communicate(timeout=25)
        self.assertEqual(process.returncode, 143, error)
        report = json.loads(next((run / 'jobs').glob('*/result.json')).read_text())
        self.assertTrue(report['cancelled'])
        self.assertEqual(report['return_code'], 143)
        self.assertEqual(json.loads((run / 'status.json').read_text())['nodes'][0]['reserved'], 0)

    def test_mock_ssh_end_to_end_and_next_run_only_transfers_changed_toml(self):
        home = self.base / 'remote home'
        home.mkdir()
        ssh = self.base / 'bin/ssh'
        ssh.write_text('#!/usr/bin/env python3\nimport os, shlex, sys\n'
                       + 'argv=shlex.split(sys.argv[-1])\n'
                       + 'env=dict(os.environ, HOME=' + repr(str(home)) + ')\n'
                       + 'os.execvpe(argv[0], argv, env)\n')
        ssh.chmod(0o755)
        text = self.config.read_text().replace('local=true', 'local=false')
        text = text.replace(json.dumps(str(self.base / 'node')), json.dumps('~/native runtime'))
        self.config.write_text(text)
        first = subprocess.run(self.wrapped('OK OTHER'), env=self.env, capture_output=True, text=True, timeout=35)
        run1 = self.capture_run(first)
        self.assertEqual(first.returncode, 0, first.stderr + (run1 / 'controller.log').read_text())
        states1 = [json.loads(p.read_text()) for p in (run1 / 'jobs').glob('*/state.json')]
        self.assertGreater(sum(s['transferred_bytes'] for s in states1), 0)
        for path in (run1 / 'jobs').glob('*/result.json'):
            remote_report = json.loads(path.read_text())
            self.assertTrue(remote_report['attempt'].startswith(str(home)))
            self.assertTrue((Path(remote_report['attempt']) / 'work/root/isla').is_dir())
        self.assertFalse((self.cwd / 'output/result-OK.json').exists())
        changed = 'file="model/source.sail"\nlimit=2\n'
        (self.base / 'limits.toml').write_text(changed)
        second = subprocess.run(self.wrapped(), env=self.env, capture_output=True, text=True, timeout=35)
        run2 = self.capture_run(second)
        self.assertEqual(second.returncode, 0, second.stderr + (run2 / 'controller.log').read_text())
        state = json.loads(next((run2 / 'jobs').glob('*/state.json')).read_text())
        self.assertEqual(state['transferred_bytes'], len(changed.encode()))

    def test_capacity_waiting_jobs_complete_and_release_all_cores(self):
        result = subprocess.run(self.wrapped('A B C D'), env=self.env, capture_output=True, text=True, timeout=35)
        run = self.capture_run(result)
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads((run / 'status.json').read_text())
        self.assertEqual(status['counts'], {'SUCCEEDED': 4})
        self.assertEqual(status['nodes'][0]['reserved'], 0)
        states = [json.loads(p.read_text()) for p in (run / 'jobs').glob('*/state.json')]
        self.assertEqual(len(states), 4)
        with closing(sqlite3.connect(run / 'state.sqlite')) as db:
            events = db.execute('SELECT id,state FROM events ORDER BY rowid').fetchall()
        active = set()
        peak = 0
        for job_id, state in events:
            if state == 'RESERVED':
                active.add(job_id)
            elif state in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
                active.discard(job_id)
            peak = max(peak, len(active))
        self.assertEqual(peak, 2)

    def test_native_management_target_is_not_intercepted(self):
        command = self.wrapped()
        command[command.index('solve')] = 'solve-kill'
        result = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=35)
        run = self.capture_run(result)
        self.assertEqual(result.returncode, 2)
        self.assertIn('必须指定有效的 SOLVE_PID', result.stderr)
        self.assertFalse(list((run / 'jobs').glob('*/result.json')))

    def test_make_argv_and_shell_overrides(self):
        self.assertEqual(make_context(['-C', str(self.base), '-Cisla', '-fscripts/run.mk'], ROOT), (self.cwd, True))
        with self.assertRaises(ValueError):
            make_context(['SHELL=/bin/sh'], self.cwd)

    def test_unknown_recipe_is_rejected_before_execution(self):
        for recipe in ('exec ./target/release/isarch', 'command exec python3 scripts/solve_process.py run',
                       'echo bad; ./target/release/isarch', 'mkdir -p output; touch marker'):
            with self.subTest(recipe=recipe), self.assertRaises(ValueError):
                validate(recipe, 'solve-OK')
