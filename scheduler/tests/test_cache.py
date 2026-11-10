from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from scheduler.native.cache import Cache
from scheduler.native import transport


class CacheTests(unittest.TestCase):
    def setUp(self):
        runtime = Path(__file__).resolve().parents[1] / 'runtime'
        runtime.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=runtime)
        self.base = Path(self.tmp.name)
        self.cache = Cache(self.base / 'cache')
        self.source = self.base / 'model.ir'
        self.source.write_bytes(b'A' * 50000)

    def tearDown(self):
        self.tmp.cleanup()

    def test_single_flight_and_immutable_copy(self):
        with ThreadPoolExecutor(max_workers=16) as pool:
            entries = list(pool.map(lambda i: self.cache.freeze(self.source), range(40)))
        self.assertEqual(len({e['digest'] for e in entries}), 1)
        self.assertEqual(len(list(self.cache.objects.glob('*-r'))), 1)
        self.source.write_bytes(b'B' * 50000)
        self.assertEqual(Path(entries[0]['source']).read_bytes(), b'A' * 50000)

    def test_ctime_detects_same_size_preserved_mtime(self):
        first = self.cache.freeze(self.source)
        stamp = self.source.stat()
        self.source.write_bytes(b'B' * stamp.st_size)
        os.utime(self.source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        second = self.cache.freeze(self.source)
        self.assertNotEqual(first['digest'], second['digest'])

    def test_worker_cache_concurrent_transfer_once_and_incremental_toml(self):
        # 用真实独立 worker、二进制流协议模拟远端；local=False 只影响上传策略。
        node = dict(name='test', local=True, work_dir=str(self.base / 'node'))
        entry = self.cache.freeze(self.source)
        original_start = transport.start
        def uploaded_start(node, request):
            return original_start(node, dict(request, local=False))
        from unittest.mock import patch
        with patch.object(transport, 'start', side_effect=uploaded_start):
            with ThreadPoolExecutor(max_workers=6) as pool:
                reports = list(pool.map(lambda i: transport.stage(node, 'ws', 'gen', {'model.ir': entry}), range(12)))
            self.assertEqual(sum(r['transferred_bytes'] for r in reports), 50000)
            small = self.base / 'config.toml'
            small.write_text('limit=1')
            entries = {'model.ir': entry, 'config.toml': self.cache.freeze(small)}
            report = transport.stage(node, 'ws', 'gen2', entries)
            self.assertEqual(report['transferred_bytes'], len('limit=1'))
        self.assertTrue((self.base / 'node/native/cache/ws/generations/gen2/READY').exists())
