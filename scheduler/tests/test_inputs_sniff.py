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

    def test_nonfile_values_are_not_rewritten_as_inputs(self):
        (self.cwd / 'default').write_text('unrelated')
        result = sniff(self.argv + ['--tastic', 'default'], self.cwd, self.root)
        self.assertNotIn('isla/default', result['files'])
        self.assertEqual(result['effective_argv'][-1], 'default')

    def test_file_value_is_not_reparsed_as_a_thread_option(self):
        (self.cwd / '-T64').write_text('name="configuration"')
        argv = self.argv.copy()
        argv[13] = '-T64'
        result = sniff(argv, self.cwd, self.root)
        self.assertEqual(result['cores'], 32)

    def test_config_symlink_keeps_its_logical_tree_path(self):
        actual = self.root / 'actual.toml'
        actual.write_text('name="linked"')
        config = self.cwd / 'configs/isa.toml'
        config.unlink()
        config.symlink_to(actual)
        result = sniff(self.argv, self.cwd, self.root)
        self.assertIn('isla/configs/isa.toml', result['files'])
        self.assertEqual(result['files']['isla/configs/isa.toml'], str(actual))
        self.assertEqual(result['effective_argv'][13], 'configs/isa.toml')

    def test_unused_mirrored_toml_does_not_change_task_output_roles(self):
        (self.cwd / 'configs/unused.toml').write_text(
            '[[execution_limits.merge_enumeration.outputs]]\npath="/unused/absolute.json"\n')
        result = sniff(self.argv, self.cwd, self.root)
        self.assertNotIn('/unused/absolute.json', result['outputs'])

    def test_unknown_missing_path_and_writable_input_conflict_are_rejected(self):
        (self.cwd / 'output').mkdir()
        (self.cwd / 'output/input.ir').write_text('IR')
        for argv in (self.argv + ['--extra-input', './missing.ir'],
                     self.argv + ['--arch', 'output/input.ir']):
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                sniff(argv, self.cwd, self.root)

    def test_optional_nonfile_flag_does_not_require_a_value(self):
        result = sniff(self.argv + ['--witness-randomization'], self.cwd, self.root)
        self.assertEqual(result['effective_argv'][-1], '--witness-randomization')
        self.assertEqual(result['cores'], 32)
