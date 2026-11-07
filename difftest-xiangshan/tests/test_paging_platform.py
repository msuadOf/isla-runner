"""平台绑定与原址具体化的回归；不使用硬件模拟器。"""
import copy,json,os,sys,tempfile,unittest
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
