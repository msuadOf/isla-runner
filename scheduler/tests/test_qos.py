"""优先级、权重与有限超售的独立资源例子。"""
import unittest
import tempfile
from pathlib import Path
from scheduler.native.common import SCHEDULER, load_config
from scheduler.native.qos import QoS


def nodes():
    return [dict(name='local', cpus=128, priority=100, weight=4),
            dict(name='preston', cpus=32, priority=100, weight=1),
            dict(name='4090', cpus=48, priority=50, weight=1)]


class QoSTests(unittest.TestCase):
    def test_smooth_four_to_one(self):
        qos = QoS(nodes())
        selected = []
        for i in range(50):
            selected.append(qos.reserve(str(i), 1))
            qos.release(str(i))
        self.assertEqual(selected.count('local'), 40)
        self.assertEqual(selected.count('preston'), 10)
        self.assertNotIn('4090', selected)

    def test_threshold_spill_wait_release(self):
        qos = QoS(nodes())
        selected = [qos.reserve(str(i), 32) for i in range(8)]
        self.assertEqual(selected.count('local'), 4)
        self.assertEqual(selected.count('preston'), 1)
        self.assertEqual(selected.count('4090'), 2)
        self.assertIsNone(selected[-1])
        self.assertEqual(qos.nodes['4090']['reserved'], 64)
        qos.release('0')
        self.assertEqual(qos.reserve('new', 32), 'local')
        qos.release('0')
        self.assertEqual(qos.nodes['local']['reserved'], 128)

    def test_small_jobs_and_exact_threshold(self):
        qos = QoS([nodes()[1]])
        self.assertEqual(qos.reserve('first', 16), 'preston')
        self.assertEqual(qos.reserve('oversell', 32), 'preston')
        self.assertEqual(qos.nodes['preston']['reserved'], 48)
        self.assertIsNone(qos.reserve('wait', 1))

    def test_offline_oversized_and_external(self):
        qos = QoS(nodes())
        qos.nodes['local']['online'] = False
        self.assertIsNone(qos.reserve('too-big', 64))
        qos.nodes['preston']['external'] = 20
        self.assertEqual(qos.reserve('spill', 32), '4090')
        self.assertFalse(qos.possible(129))

    def test_unsuccessful_probes_do_not_change_credits(self):
        qos = QoS(nodes())
        before = [n['credit'] for n in qos.nodes.values()]
        for i in range(10):
            self.assertIsNone(qos.reserve(str(i), 129))
        self.assertEqual(before, [n['credit'] for n in qos.nodes.values()])

    def test_dynamic_half_threshold_boundary_spill_and_wait(self):
        for cores, threshold in ((16, 8), (32, 16), (64, 32), (1, 1), (3, 1), (5, 2)):
            with self.subTest(cores=cores):
                peers = [dict(name='high', cpus=128, priority=100, weight=1,
                              external_cores=128 - threshold),
                         dict(name='low', cpus=128, priority=50, weight=1,
                              external_cores=128 - threshold)]
                qos = QoS(peers)
                self.assertEqual(qos.reserve('at-boundary', cores), 'high')
                self.assertEqual(qos.nodes['high']['reserved'], cores)
                self.assertEqual(qos.reserve('spill', cores), 'low')
                self.assertIsNone(qos.reserve('waiting', cores))
                self.assertNotIn('waiting', qos.leases)
                qos.release('at-boundary')
                self.assertEqual(qos.reserve('resume', cores), 'high')
                # 只差一核也应拒绝，失败试探不能消耗轮询额度。
                qos = QoS([dict(peers[0], external_cores=128 - threshold + 1)])
                self.assertIsNone(qos.reserve('below-boundary', cores))
                self.assertEqual(qos.nodes['high']['reserved'], 0)
                self.assertEqual(qos.nodes['high']['credit'], 0)

    def test_same_free_capacity_adapts_to_light_and_heavy_tasks(self):
        qos = QoS([dict(name='node', cpus=128, priority=100, weight=1, external_cores=112)])
        self.assertIsNone(qos.reserve('heavy-64', 64))
        self.assertEqual(qos.reserve('medium-32', 32), 'node')
        qos.release('medium-32')
        self.assertEqual(qos.reserve('light-16', 16), 'node')
        self.assertIsNone(qos.reserve('light-waiting', 16))
        qos.release('light-16')
        self.assertEqual(qos.reserve('light-resumed', 16), 'node')

    def test_legacy_stop_free_cores_does_not_affect_admission(self):
        for legacy in (1, 16, 128):
            with self.subTest(legacy=legacy):
                qos = QoS([dict(name='node', cpus=128, priority=100, weight=1,
                                external_cores=120, stop_free_cores=legacy)])
                self.assertIsNone(qos.reserve('heavy', 64))
                self.assertEqual(qos.reserve('light', 16), 'node')

    def test_native_config_without_stop_free_cores(self):
        with tempfile.TemporaryDirectory(dir=SCHEDULER / 'runtime') as directory:
            path = Path(directory) / 'nodes.conf'
            path.write_text('''[[nodes]]
name="node"
local=false
address="127.0.0.1"
ssh_user="test"
cpus=128
priority=100
weight=1
work_dir="~/runtime"
''')
            config = load_config(path)
            self.assertNotIn('stop_free_cores', config['nodes'][0])
            self.assertEqual(QoS(config['nodes']).reserve('job', 64), 'node')
