import os
from pathlib import Path
import tempfile
import unittest
from scheduler.native.inputs import sniff


class InputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'runtime')
        self.root = Path(self.tmp.name)
        self.cwd = self.root / 'isla'
        for name in ('scripts', 'target/release', 'configs'):
            (self.cwd / name).mkdir(parents=True)
        for name in ('scripts/solve_process.py', 'target/release/isarch', 'model space.ir', 'configs/isa.toml'):
            (self.cwd / name).write_text('')
        (self.root / 'limit.toml').write_text('file = "extensions/model.sail"')
        self.argv = ['python3', 'scripts/solve_process.py', 'run', '--clause', 'MRET', '--',
                     'timeout', '--signal=TERM', '2m', './target/release/isarch', '-A', './model space.ir',
                     '-C', './configs/isa.toml', '--execution-limits-config=../limit.toml',
                     '-T', '32', '--timeout', '1m', 'solve-state', '--clause=MRET']

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_argv_roles_paths_and_limits(self):
        result = sniff(self.argv, self.cwd, self.root, 'output/log/MRET.log')
        self.assertEqual(result['cores'], 32)
        self.assertIn('isla/model space.ir', result['files'])
        self.assertIn('limit.toml', result['files'])
        self.assertIn('--execution-limits-config=../limit.toml', result['effective_argv'])
        self.assertEqual(result['original_argv'], self.argv)
        self.assertIn('output/log/MRET.log', result['outputs'])
        self.assertNotIn('extensions/model.sail', result['files'])

    def test_declared_threads_are_used_as_cpu_request(self):
        for cores in (16, 32, 64):
            for declaration in (['-T', str(cores)], ['--threads', str(cores)],
                                [f'--threads={cores}']):
                with self.subTest(cores=cores, declaration=declaration):
                    argv = self.argv[:15] + declaration + self.argv[17:]
                    self.assertEqual(sniff(argv, self.cwd, self.root)['cores'], cores)

    def test_long_equals_and_output_not_uploaded(self):
        argv = self.argv.copy()
        argv[10:14] = ['--arch=./model space.ir', '--config=./configs/isa.toml']
        (self.cwd / 'output').mkdir()
        (self.cwd / 'output/old.log').write_text('old output')
        result = sniff(argv + ['--trace-output=output/old.log'], self.cwd, self.root)
        self.assertNotIn('isla/output/old.log', result['files'])
        self.assertIn('output/old.log', result['outputs'])

    def test_external_file_is_relocated(self):
        with tempfile.TemporaryDirectory(dir=self.root.parent) as directory:
            path = Path(directory) / 'external.ir'
            path.write_text('IR')
            self.argv[11] = str(path)
            result = sniff(self.argv, self.cwd, self.root)
            self.assertTrue(any(n.startswith('_external/') for n in result['files']))
            self.assertIn('../_external/', result['effective_argv'][11])

    def test_missing_threads_missing_input_and_absolute_output_rejected(self):
        for argv in (self.argv[:15] + self.argv[17:],
                     self.argv + ['--config', 'missing.toml'],
                     self.argv + ['--trace-output=/tmp/unisolated']):
            with self.subTest(argv=argv), self.assertRaises((ValueError, FileNotFoundError)):
                sniff(argv, self.cwd, self.root)
