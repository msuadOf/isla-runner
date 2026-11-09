"""E2 的 U/S、SUM/MXR 输入域和数据访问回放契约。"""
import copy
import os
from pathlib import Path
import unittest
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import paging_fuzz as fuzz
import paging_replay as replay
import replay_symbolic_prestate as campaign
import test_paging_fuzz as fixtures
from test_paging_replay import bits


class SymbolicPrestateTests(unittest.TestCase):
    corpus_entry = fixtures.FuzzTests.seed
    profile = fixtures.FuzzTests.profile

    @classmethod
    def setUpClass(cls):
        cls.decoder, _ = replay.load_decoder(os.environ['PT_DECODE_DIR'], standard_paging=True)

    def domain_profile(self):
        p = self.profile()
        p['isla']['scenario'] = dict(privilege_domain=['User', 'Supervisor'],
            mstatus_mask='0xfffffffffff3ffff', mstatus_value='0x0000000a00000000',
            satp_modes=[8], instructions=[0xb103], va=0x20000000)
        return p

    def proposal(self, privilege, u, sum_bit, mxr, read=True, mprv=False, mpp=0):
        s = self.corpus_entry()
        s['pre_registers']['cur_privilege']['enum'] = privilege
        status = 0xa00000000 | (sum_bit << 18) | (mxr << 19) | (mprv << 17) | (mpp << 11)
        s['pre_registers']['mstatus']['struct']['bits'] = bits(status)
        memory = self.decoder.memory_bytes(s['pre_memory'])
        flags = 0xc1 | (u << 4) | (2 if read else 8)
        fuzz.put_word(memory, 0x80301000, ((0x80400000 >> 12) << 10) | flags)
        return fuzz.predict_sample(s, memory, self.decoder, self.profile(), 100)

    def test_prediction_u_s_sum_mxr_truth_table(self):
        for privilege in ('User', 'Supervisor'):
            for u in (0, 1):
                for sum_bit in (0, 1):
                    for mxr in (0, 1):
                        for read in (False, True):
                            with self.subTest(privilege=privilege, u=u, sum=sum_bit, mxr=mxr, read=read):
                                _, decoded = self.proposal(privilege, u, sum_bit, mxr, read)
                                allowed = (u if privilege == 'User' else not u or sum_bit) and (read or mxr)
                                self.assertEqual(decoded['exception_type'], None if allowed else 'E_Load_Page_Fault')

    def test_prediction_uses_mpp_for_mprv(self):
        for privilege, mpp, u, allowed in [('Supervisor', 0, 0, False),
                                          ('Supervisor', 0, 1, True),
                                          ('User', 1, 0, True), ('User', 1, 1, False)]:
            with self.subTest(privilege=privilege, mpp=mpp, u=u):
                _, decoded = self.proposal(privilege, u, 0, 0, mprv=True, mpp=mpp)
                self.assertEqual(decoded['exception_type'], None if allowed else 'E_Load_Page_Fault')

    def test_platform_accepts_u_and_s_in_e2_domain(self):
        p = self.domain_profile()
        for privilege, u, sum_bit, mxr in [('User', 1, 0, 1), ('Supervisor', 1, 1, 0)]:
            s, _ = self.proposal(privilege, u, sum_bit, mxr)
            c = replay.platform_case(s, self.decoder, p, replay.platform_hashes(p)[0])
            self.assertEqual(c['expected']['cause'], 0)
            self.assertEqual(c['entry_mode'], 'mprv')

    def test_platform_rejects_machine_virtual_and_outside_config(self):
        p = self.domain_profile()
        s, _ = self.proposal('Supervisor', 0, 0, 0)
        for privilege in ('Machine', 'VirtualUser', 'VirtualSupervisor'):
            q = copy.deepcopy(s)
            q['pre_registers']['cur_privilege']['enum'] = privilege
            with self.subTest(privilege=privilege), self.assertRaisesRegex(ValueError, 'R1'):
                replay.platform_case(q, self.decoder, p, replay.platform_hashes(p)[0])
        for changed in (0xa00000000 | (1 << 17), 0xa00000000 | (1 << 3), 0):
            q = copy.deepcopy(s)
            q['pre_registers']['mstatus']['struct']['bits'] = bits(changed)
            with self.subTest(status=changed), self.assertRaisesRegex(ValueError, 'R1'):
                replay.platform_case(q, self.decoder, p, replay.platform_hashes(p)[0])
        p['isla']['scenario']['privilege_domain'] = ['User']
        with self.assertRaisesRegex(ValueError, 'R1'):
            replay.platform_case(s, self.decoder, p, replay.platform_hashes(p)[0])

    def test_assembly_preserves_sum_mxr_and_orders_mprv(self):
        p = self.domain_profile()
        for privilege, u, sum_bit, mxr in [('User', 1, 0, 1), ('Supervisor', 1, 1, 1)]:
            s, _ = self.proposal(privilege, u, sum_bit, mxr)
            c = replay.platform_case(s, self.decoder, p, replay.platform_hashes(p)[0])
            asm = replay.paging_assembly(c)
            status = 0xa00000000 | (sum_bit << 18) | (mxr << 19) | (1 << 17)
            status |= (privilege == 'Supervisor') << 11
            self.assertIn(f'li t0, {status:#x}\n    csrw mstatus, t0', asm)
            self.assertLess(asm.index('csrc mstatus, t0'), asm.index('sd t1, 0(t0)'))
            self.assertLess(asm.rindex('sd t1, 0(t0)'), asm.index('csrw mstatus, t0'))
            self.assertIn('trap_handler:\n    mv x31, x2\n    li t0, 0x20000\n    csrc mstatus, t0', asm)
            self.assertIn('ld x2, 0(x1)\n    mv x31, x2\n    li t0, 0x20000\n    csrc mstatus, t0', asm)

    def test_check_command_preserves_ir_config_and_removes_fixed_addresses(self):
        template = ['isarch', '-T', '32', '-A', '/E2/rv64d-us.ir', '-C', '/E2/E2.toml',
            '--prestate', 'x1=0x20000000', '--check-samples', 'old',
            '--check-samples-report', 'old-report', '--clause=LOAD']
        command = fuzz.check_command(template, Path('new'), Path('new-report'))
        expected = [value for value in template if value not in ('--prestate', 'x1=0x20000000')]
        expected[expected.index('--check-samples')+1] = 'new'
        expected[expected.index('--check-samples-report')+1] = 'new-report'
        self.assertEqual(command, expected)

    def test_address_domain_rejects_malformed_or_inconsistent_constraints(self):
        for domain in (dict(base=0), dict(mask=1), dict(base=1, size=-1),
                       dict(base=(1 << 64)-1, size=2), dict(mask=1, value=2),
                       dict(mask=1 << 64, value=0), dict(maks=0)):
            with self.subTest(domain=domain), self.assertRaisesRegex(ValueError, 'R1'):
                replay.validate_address(0, dict(va_domain=domain))

    def test_symbolic_batch_requires_explicit_template(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaisesRegex(ValueError, 'judge_template'):
                fuzz.check_batch([], path/'batch', path,
                    scenario_config=self.domain_profile()['isla']['scenario'])
            self.assertFalse((path/'batch').exists())

    def test_symbolic_check_command_rejects_old_fixed_prestate(self):
        template = ['isarch', '-T', '32', '--check-samples', 'old',
                    '--check-samples-report', 'report']
        for fixed in ('cur_privilege=Supervisor', 'mstatus={bits=0xa00040000}'):
            with self.subTest(fixed=fixed), self.assertRaises(AssertionError):
                fuzz.check_command(template+['--prestate', fixed], Path('new'), Path('report'),
                    scenario_config=self.domain_profile()['isla']['scenario'])

    def test_enum_snapshot_normalization_keeps_array_identifier(self):
        from paging_smt import normalize_enum_names
        text = ('(declare-datatypes ((P 0)) (((k!00) (k!10) (k!20) (k!30) (k!40))))\n'
                '(declare-fun p () P)\n'
                '(declare-fun k!0 () (Array (_ BitVec 64) (_ BitVec 8)))\n'
                '(assert (= p k!0))\n'
                '(assert (= (select k!0 #x0000000000000000) #x01))\n')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'query.smt2'
            source.write_text(text)
            normalized = normalize_enum_names(source).read_text()
            self.assertIn('(assert (= p k!00))', normalized)
            self.assertIn('(select k!0 #x0000000000000000)', normalized)
            self.assertEqual(source.read_text(), text)

    def test_coverage_distinguishes_effective_privilege_sum_mxr(self):
        coverage = fuzz.Coverage()
        _, decoded = self.proposal('Supervisor', 0, 0, 0)
        self.assertTrue(coverage.observe(decoded)['would_admit'])
        self.assertFalse(coverage.observe(decoded)['would_admit'])
        for key, value in [('effective_privilege', 'User'), ('sum', True), ('mxr', True)]:
            changed = dict(decoded, **{key: value})
            self.assertTrue(coverage.observe(changed)['would_admit'])

    def test_profiles_bind_each_mode_and_instruction(self):
        for mode, satp in [('sv39', 8), ('sv48', 9)]:
            for access, instruction in [('load', 0xb103), ('store', 0x20b023)]:
                with self.subTest(mode=mode, access=access):
                    original = self.profile()
                    p = campaign.scenario_profile(original, mode+'-'+access, instructions=[instruction])
                    self.assertEqual(original, self.profile())
                    self.assertEqual(p['isla']['scenario'], dict(
                        privilege_domain=['User', 'Supervisor'],
                        mstatus_mask='0xfffffffffff3ffff', mstatus_value='0x0000000a00000000',
                        access=access, satp_modes=[satp], instructions=[instruction]))
                    self.assertEqual(p['csr_init']['entry_mode'], 'mprv')
                    self.assertNotIn('mstatus', p['csr_init'])

    def test_template_binds_actual_ir_config_satp_and_instruction(self):
        files = dict(ir=Path('/actual/rv64d.ir'), config=Path('/actual/E2.toml'))
        template = ['isarch', '-A', str(files['ir']), '-C', str(files['config']),
                    '-T', '64', '--instruction-bits', '0x0020b023',
                    '--prestate', 'satp=0x9000000000080200',
                    '--prestate', 'x1=0x20000000', '--clause=STORE',
                    '--check-samples', 'old', '--check-samples-report', 'report']
        bound = campaign.bound_template(template, files, 'sv48-store')
        self.assertEqual(bound[bound.index('-T')+1], '64')
        self.assertNotIn('--prestate', bound)
        command = fuzz.check_command(bound, Path('new'), Path('report'),
                                     scenario_config=self.domain_profile()['isla']['scenario'])
        self.assertEqual(command[command.index('-T')+1], '64')
        changes = [('-A', '/wrong/rv64d-us.ir'), ('-C', '/old/config-xs.toml'),
                   ('--instruction-bits', '0x0000b103'),
                   ('--prestate', 'satp=0x8000000000080200')]
        for flag, value in changes:
            bad = list(template)
            bad[bad.index(flag)+1] = value
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                campaign.bound_template(bad, files, 'sv48-store')
        with self.assertRaises(ValueError):
            campaign.bound_template(template+['--prestate', 'cur_privilege=Supervisor'],
                                    files, 'sv48-store')
        with self.assertRaises(ValueError):
            campaign.bound_template([x.replace('--clause=STORE', '--clause=LOAD')
                                     for x in template], files, 'sv48-store')

    def test_profile_accepts_dynamic_address_list_or_domain_and_preserves_source(self):
        original = self.domain_profile()
        before = copy.deepcopy(original)
        values = [0x20000000 + slot*4096 for slot in range(8)]
        p = campaign.scenario_profile(original, 'sv39-load', va_values=values)
        self.assertNotIn('va', p['isla']['scenario'])
        self.assertEqual(p['isla']['scenario']['va_values'], values)
        self.assertEqual(original, before)
        domain = dict(base=0x20000000, size=0x8000, mask=0xfff, value=0)
        p = campaign.scenario_profile(original, 'sv39-load', va_domain=domain)
        self.assertEqual(p['isla']['scenario']['va_domain'], domain)
        self.assertNotIn('va', p['isla']['scenario'])
        self.assertEqual(campaign.scenario_profile(original, 'sv39-load')['isla']['scenario']['va'], 0x20000000)
        p = campaign.scenario_profile(self.profile(), 'sv39-load')
        self.assertNotIn('va', p['isla']['scenario'])
        self.assertNotIn('instructions', p['isla']['scenario'])

    def test_template_dynamic_base_offsets_address_domain_and_optional_symbolic_satp(self):
        files = dict(ir=Path('/actual/rv64d.ir'), config=Path('/actual/E2.toml'))
        fixture = fixtures.FuzzTests()
        fixture.decoder = self.decoder
        for access in ('load', 'store'):
            for slot in range(8):
                va = 0x20000000 + slot*4096
                s = fixture.dynamic_seed('sv48', access, va)
                instruction = replay.instruction_binding(s, self.decoder)
                template = ['isarch', '-A', str(files['ir']), '-C', str(files['config']),
                    '--instruction-bits', hex(instruction['word']), f'--clause={access.upper()}',
                    '--prestate', f'x11={va+24:#x}', '--prestate', 'x12=0xdeadbeef',
                    '--prestate', 'satp=0x9001200000080500']
                domain = dict(va_domain=dict(base=0x20000000, size=0x8000, mask=0xfff, value=0))
                with self.subTest(access=access, slot=slot):
                    before = list(template)
                    bound = campaign.bound_template(template, files, 'sv48-'+access, domain)
                    self.assertNotIn('--prestate', bound)
                    self.assertEqual(template, before)
                    self.assertIn(hex(instruction['word']), bound)
                    with self.assertRaisesRegex(ValueError, 'VA'):
                        campaign.bound_template(template, files, 'sv48-'+access, dict(va_values=[va+4096]))
                    with self.assertRaisesRegex(ValueError, '指令'):
                        campaign.bound_template(template, files, 'sv48-'+access, dict(instructions=[0xb103]))
        symbolic = ['isarch', '-A', str(files['ir']), '-C', str(files['config']),
                    '--instruction-bits', '0xb103', '--clause=LOAD']
        self.assertEqual(campaign.bound_template(symbolic, files, 'sv39-load'), symbolic)

    def test_platform_address_domains_validate_effective_address_and_actual_instruction(self):
        fixture = fixtures.FuzzTests()
        fixture.decoder = self.decoder
        s = fixture.dynamic_seed('sv39', 'load', 0x20007000)
        s['pre_registers']['mstatus']['struct']['bits'] = bits(0xa00000000)
        predicted, _ = fixture.predict(s)
        domain = dict(base='0x20000000', size='0x8000', mask='0xfff', value='0')
        p = campaign.scenario_profile(self.profile(), 'sv39-load', va_domain=domain)
        instruction = replay.instruction_binding(s, self.decoder)
        p['isla']['scenario']['instructions'] = [instruction['word']]
        c = replay.platform_case(predicted, self.decoder, p, replay.platform_hashes(p)[0])
        self.assertEqual(c['decoded']['va'], 0x20007000)
        self.assertEqual(c['expected']['rd'], 0x1234)
        for constraint in (dict(va=0x20000000), dict(va_values=[0x20000000]),
                           dict(va_domain=dict(base=0x20000000, size=0x7000)),
                           dict(va_domain=dict(mask=0xffff, value=0)),
                           dict(instructions=[0xb103])):
            q = self.profile()
            q['isla']['scenario'] = constraint
            with self.subTest(constraint=constraint), self.assertRaisesRegex(ValueError, 'R1'):
                replay.platform_case(predicted, self.decoder, q, replay.platform_hashes(q)[0])

    def test_prediction_store_unknown_bytes_in_both_modes(self):
        for mode in ('sv39', 'sv48'):
            fixture = fixtures.FuzzTests()
            fixture.decoder = self.decoder
            s = fixture.scenario_seed(mode, 'store')
            for cell in s['pre_memory']:
                if cell['address'] >= 0x80400000:
                    cell['value'] = None
            memory = self.decoder.memory_bytes(s['pre_memory'], allow_unknown=True)
            predicted, decoded = fuzz.predict_sample(s, memory, self.decoder, self.profile(), 100)
            self.assertEqual(decoded['exception_type'], None)
            self.assertEqual(self.decoder.memory_bytes(predicted['post_memory']),
                             self.decoder.memory_bytes(s['post_memory']))
            self.assertEqual(predicted['post_registers']['x2'], s['pre_registers']['x2'])
            self.assertTrue(all(c['value'] is None for c in s['pre_memory']
                                if c['address'] >= 0x80400000))

    def test_store_u_s_sum_mxr_permissions_and_sv48_walk(self):
        for mode in ('sv39', 'sv48'):
            for privilege, u, sum_bit, allowed in [('User', 0, 0, False),
                    ('User', 1, 0, True), ('Supervisor', 1, 0, False),
                    ('Supervisor', 1, 1, True), ('Supervisor', 0, 0, True)]:
                for mxr in (0, 1):
                    with self.subTest(mode=mode, privilege=privilege, u=u, sum=sum_bit, mxr=mxr):
                        fixture = fixtures.FuzzTests()
                        fixture.decoder = self.decoder
                        s = fixture.scenario_seed(mode, 'store')
                        s['pre_registers']['cur_privilege']['enum'] = privilege
                        s['pre_registers']['mstatus']['struct']['bits'] = bits(
                            0xa00000000 | (sum_bit << 18) | (mxr << 19))
                        memory = self.decoder.memory_bytes(s['pre_memory'])
                        fuzz.put_word(memory, 0x80301000, ((0x80400000 >> 12) << 10) | 0xc7 | (u << 4))
                        _, decoded = fuzz.predict_sample(s, memory, self.decoder, self.profile(), 100)
                        self.assertEqual(decoded['exception_type'], None if allowed else 'E_SAMO_Page_Fault')
                        # MXR cannot grant STORE permission to an X-only page.
                        fuzz.put_word(memory, 0x80301000, ((0x80400000 >> 12) << 10) | 0xc9 | (u << 4))
                        _, decoded = fuzz.predict_sample(s, memory, self.decoder, self.profile(), 100)
                        self.assertEqual(decoded['exception_type'], 'E_SAMO_Page_Fault')

    def test_membership_observer_uses_actual_read_write_symbol_ranges(self):
        symbols = ('00000100 00000020 t isla_lib::memory::Memory<B>::read_symbolic\n'
                   '00000300 00000040 t isla_lib::memory::Memory<B>::write_symbolic\n')
        original = 'if ((offset >= 0x1 && offset < 0x2) || (offset >= 0x3 && offset < 0x4)) return 1;'
        updated, ranges = campaign.observer_source(original, symbols)
        self.assertEqual(updated, 'if ((offset >= 0x100 && offset < 0x120) || '
                                  '(offset >= 0x300 && offset < 0x340)) return 1;')
        self.assertEqual(ranges, {'read_symbolic': [0x100, 0x120], 'write_symbolic': [0x300, 0x340]})
        with self.assertRaises(ValueError):
            campaign.observer_source(original, '')
