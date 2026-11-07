"""平台绑定与原址具体化的回归；不使用硬件模拟器。"""
import copy,hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import paging_replay as replay
from test_paging_replay import bits,cells,sample,fault

class PlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder,_=replay.load_decoder(os.environ['PT_DECODE_DIR'])

    def platform(self):
        return dict(regions=[dict(base=0x80100000,size=2**43-0x80100000,kind='ram')],
                    isa=dict(svrsw60t59b=False),harness={},csr_init={},ir={},isla={},env={})

    def source(self):
        s=sample(); words={0x80200000:((0x80400000>>12)<<10)|0xc7}
        # 1 GiB 叶要求 PPN 低18位为0，改为 2 GiB。
        words={0x80200000:((0x80000000>>12)<<10)|0xc7,0xa0000000:0x1234}
        s['pre_memory']=cells(words); s['post_memory']=cells(words);s['post_registers']['x2']=bits(0x1234)
        return s

    def test_lock_hash_ignores_env_but_checks_every_generation_input(self):
        p=self.platform(); h=replay.platform_hashes(p)
        q=copy.deepcopy(p);q['env']['emu']='new';self.assertEqual(h[0],replay.platform_hashes(q)[0]);self.assertNotEqual(h[1],replay.platform_hashes(q)[1])
        q['isa']['svrsw60t59b']=True;self.assertNotEqual(h[0],replay.platform_hashes(q)[0])
        with tempfile.TemporaryDirectory() as d:
            files={k:Path(d)/k for k in ['config','ir','isarch','emu','nemu']}
            for k,path in files.items():path.write_text(k)
            with self.assertRaisesRegex(ValueError,'R0'):
                replay.create_platform_lock(p,files)
            p['ir']['ir_sha256']=replay.sha256(files['ir'])
            p['isla'].update(config_toml_sha256=replay.sha256(files['config']),
                             isarch_sha256=replay.sha256(files['isarch']))
            p['env'].update(emu_sha256=replay.sha256(files['emu']),nemu_sha256=replay.sha256(files['nemu']))
            lock=replay.create_platform_lock(p,files)
            replay.verify_platform_lock(p,lock,files)
            files['config'].write_text('changed')
            with self.assertRaisesRegex(ValueError,'R0'):replay.verify_platform_lock(p,lock,files)

    def locked_platform(self, directory):
        p = self.platform()
        files = {k: Path(directory)/k for k in ('config', 'ir', 'isarch')}
        for name, path in files.items():
            path.write_text(name)
        p['ir']['ir_sha256'] = replay.sha256(files['ir'])
        p['isla'].update(config_toml_sha256=replay.sha256(files['config']),
                         isarch_sha256=replay.sha256(files['isarch']),
                         enumeration_sha256='enumeration', scenario='sv39-load')
        return p, files, replay.create_platform_lock(p, files)

    def test_isarch_identity_is_record_only(self):
        with tempfile.TemporaryDirectory() as directory:
            p, files, lock = self.locked_platform(directory)
            original = copy.deepcopy(p)
            for target in ('profile', 'lock', 'both'):
                with self.subTest(target=target):
                    q, changed_lock = copy.deepcopy(p), copy.deepcopy(lock)
                    if target in ('profile', 'both'):
                        q['isla']['isarch_sha256'] = 'recorded-other-binary'
                    if target in ('lock', 'both'):
                        changed_lock['isarch_sha256'] = 'recorded-other-binary'
                    self.assertEqual(replay.platform_hashes(p), replay.platform_hashes(q))
                    with self.assertLogs('paging_replay', level='WARNING') as logs:
                        replay.verify_platform_lock(q, changed_lock, files)
                    self.assertEqual(len(logs.output), 1)
                    self.assertIn('isarch', logs.output[0])
            files['isarch'].write_text('rebuilt-binary')
            with self.assertLogs('paging_replay', level='WARNING') as logs:
                replay.verify_platform_lock(p, lock, files)
            self.assertEqual(len(logs.output), 1)
            self.assertEqual(p, original)
            self.assertEqual(lock['schema_version'], 2)
            self.assertIn('isarch_sha256', lock)
            with self.assertLogs('paging_replay', level='WARNING'):
                new_lock = replay.create_platform_lock(p, files)
            self.assertEqual(new_lock['isarch_sha256'], replay.sha256(files['isarch']))
            self.assertEqual(new_lock['platform_gen_sha256'], lock['platform_gen_sha256'])
            self.assertEqual(p, original)

    def test_generation_inputs_remain_lock_requirements(self):
        with tempfile.TemporaryDirectory() as directory:
            p, files, lock = self.locked_platform(directory)
            changes = (('isla', 'config_toml_sha256'), ('ir', 'ir_sha256'),
                       ('isla', 'enumeration_sha256'), ('isla', 'scenario'),
                       ('regions', None), ('harness', 'code'), ('isa', 'svrsw60t59b'),
                       ('csr_init', 'menvcfg'))
            for section, key in changes:
                with self.subTest(section=section, key=key):
                    q = copy.deepcopy(p)
                    if key is None:
                        q[section][0]['size'] -= 4096
                    else:
                        q[section][key] = 'changed'
                    self.assertNotEqual(replay.platform_hashes(p)[0], replay.platform_hashes(q)[0])
                    with self.assertRaisesRegex(ValueError, 'R0'):
                        replay.verify_platform_lock(q, lock, files)
            for name in ('config', 'ir'):
                with self.subTest(file=name):
                    files[name].write_text('changed')
                    with self.assertRaisesRegex(ValueError, 'R0'):
                        replay.verify_platform_lock(p, lock, files)
                    files[name].write_text(name)

    def test_legacy_lock_keeps_original_hash_and_sample_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            p, files, lock = self.locked_platform(directory)
            # 独立重现旧算法；profile 的版本号与 lock 的版本号含义不同。
            p['schema_version'] = 2
            generation = {key: p[key] for key in
                          ('regions', 'harness', 'isa', 'csr_init', 'ir', 'isla')}
            legacy_gen = hashlib.sha256(json.dumps(
                generation, sort_keys=True, separators=(',', ':'),
                ensure_ascii=False).encode()).hexdigest()
            lock.update(schema_version=1, platform_gen_sha256=legacy_gen)
            replay.verify_platform_lock(p, lock, files)
            files['isarch'].write_text('rebuilt-binary')
            with self.assertLogs('paging_replay', level='WARNING'):
                replay.verify_platform_lock(p, lock, files)
            case = replay.platform_case(self.source(), self.decoder, p, legacy_gen)
            self.assertEqual(case['platform_gen_sha256'], legacy_gen)
            self.assertEqual(case['expected']['rd'], 0x1234)
            q = copy.deepcopy(p)
            q['isla']['isarch_sha256'] = 'changed-historical-record'
            with self.assertRaisesRegex(ValueError, 'R0'):
                replay.verify_platform_lock(q, lock, files)
            for version in (2, 999):
                with self.subTest(lock_schema=version):
                    changed_lock = dict(lock, schema_version=version)
                    with self.assertRaisesRegex(ValueError, 'R0'):
                        replay.verify_platform_lock(p, changed_lock, files)

    def test_concretization_preserves_pte_and_checks_source_binding(self):
        s=self.source();before=copy.deepcopy(s);p=self.platform();h=replay.platform_hashes(p)[0]
        c=replay.platform_case(s,self.decoder,p,h)
        self.assertEqual(s,before);self.assertEqual(c['expected']['rd'],0x1234)
        self.assertEqual(c['sample']['pre_memory'][:8],s['pre_memory'][:8])
        self.assertGreater(len(c['writes']),2)
        with self.assertRaisesRegex(ValueError,'R0'):replay.platform_case(s,self.decoder,p,'bad')

    def test_reserved_software_bits_are_page_fault_without_rewrite(self):
        s=self.source();s['pre_memory']=cells({0x80200000:(1<<59)|1});s['post_memory']=copy.deepcopy(s['pre_memory']);fault(s,13);s['post_registers']['x2']=bits(0)
        p=self.platform();c=replay.platform_case(s,self.decoder,p,replay.platform_hashes(p)[0]);self.assertEqual(c['expected']['cause'],13)
        self.assertEqual(c['writes'][0]['value'],(1<<59)|1)

    def test_standard_napot_keeps_original_pte_and_uses_replaced_ppn(self):
        decoder,_=replay.load_decoder(os.environ['PT_DECODE_DIR'],standard_paging=True)
        s=sample();pte=(1<<63)|((0x80408000>>12)<<10)|0xc7
        words={0x80200000:((0x80300000>>12)<<10)|1,
               0x80300800:((0x80301000>>12)<<10)|1,0x80301000:pte,0x80400000:0x1234}
        s['pre_memory']=cells(words);s['post_memory']=cells(words);s['post_registers']['x2']=bits(0x1234)
        p=self.platform();p['isa']['standard_paging']=True
        c=replay.platform_case(s,decoder,p,replay.platform_hashes(p)[0])
        self.assertEqual(c['decoded']['paddr_if_success'],0x80400000)
        self.assertEqual(c['expected']['cause'],0)
        self.assertTrue(any(w['address']==0x80301000 and w['value']==pte for w in c['writes']))
        # 相同 NAPOT 编码的低4位改为1001，保持页异常和原始 PTE。
        words.pop(0x80400000);words[0x80301000]=pte|(1<<10)
        s['pre_memory']=cells(words);s['post_memory']=cells(words);s['post_registers']['x2']=bits(0);fault(s,13)
        c=replay.platform_case(s,decoder,p,replay.platform_hashes(p)[0])
        self.assertEqual(c['decoded']['failure_reason'],'n_reserved')
        self.assertEqual(c['expected']['cause'],13)

    def test_standard_nonleaf_reserved_faults_before_next_read(self):
        decoder,_=replay.load_decoder(os.environ['PT_DECODE_DIR'],standard_paging=True)
        p=self.platform();p['isa']['standard_paging']=True
        for bit in (4,6,7):
            with self.subTest(bit=bit):
                s=self.source();s['pre_memory']=cells({0x80200000:(1<<bit)|1})
                s['post_memory']=copy.deepcopy(s['pre_memory']);s['post_registers']['x2']=bits(0);fault(s,13)
                c=replay.platform_case(s,decoder,p,replay.platform_hashes(p)[0])
                self.assertEqual(c['expected']['cause'],13)
                self.assertEqual(c['decoded']['failure_reason'],'nonleaf_reserved')

if __name__=='__main__':unittest.main()
