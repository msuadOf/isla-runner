"""P1 契约：先运行失败测试，再实现变异、判官门槛和反馈。"""
import copy
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paging_fuzz as fuzz
import paging_replay as replay
from test_paging_replay import bits, cells, sample


class FuzzTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder, cls.decoder_identity = replay.load_decoder(
            os.environ['PT_DECODE_DIR'], standard_paging=True)

    def profile(self):
        return dict(regions=[dict(base=0x80000000, size=2**43-0x80000000, kind='ram'),
                             dict(base=2**43, size=2**64-2**43, kind='hole')],
                    isa=dict(svrsw60t59b=False, standard_paging=True),
                    harness=dict(reserved=[0x80000000, 0x80100000],
                                 root_tables=[0x80200000, 0x80203000]),
                    csr_init={}, ir={}, isla={}, env={})

    def seed(self):
        s = sample()
        s['pre_registers']['tlb'] = {'vector': [dict(ctor='None<RTLB_Entry>', value={'unit': True})
                                              for index in range(64)]}
        s['post_registers']['tlb'] = copy.deepcopy(s['pre_registers']['tlb'])
        s['pre_registers']['pma_regions']['list'] = [
            s['pre_registers']['pma_regions']['list'][0]]
        words = {0x80200000: ((0x80300000 >> 12) << 10) | 1,
                 0x80300800: ((0x80301000 >> 12) << 10) | 1,
                 0x80301000: ((0x80400000 >> 12) << 10) | 0xc7,
                 0x80400000: 0x1234}
        s['pre_memory'] = cells(words)
        s['post_memory'] = cells(words)
        s['post_registers']['x2'] = bits(0x1234)
        return s

    def predict(self, s, memory=None):
        if memory is None:
            memory = self.decoder.memory_bytes(s['pre_memory'])
        return fuzz.predict_sample(s, memory, self.decoder, self.profile(), 100)

    def scenario_seed(self, mode, access):
        s = self.seed()
        s['isa_state']['$instruction'] = ('ld' if access == 'load' else 'sd')+' x2, 0(x1)'
        s['pre_registers']['x2'] = bits(0xdeadbeef)
        if access == 'store':
            s['post_registers']['x2'] = bits(0xdeadbeef)
            memory = self.decoder.memory_bytes(s['post_memory'])
            fuzz.put_word(memory, 0x80400000, 0xdeadbeef)
            s['post_memory'] = fuzz.cells(memory)
        if mode == 'sv48':
            s['pre_registers']['satp'] = bits(0x9000000000080200)
            memory = self.decoder.memory_bytes(s['pre_memory'])
            fuzz.put_word(memory, 0x80200000, ((0x80302000 >> 12) << 10) | 1)
            fuzz.put_word(memory, 0x80302000, ((0x80300000 >> 12) << 10) | 1)
            s['pre_memory'] = fuzz.cells(memory)
            post = self.decoder.memory_bytes(s['post_memory'])
            fuzz.put_word(post, 0x80200000, ((0x80302000 >> 12) << 10) | 1)
            fuzz.put_word(post, 0x80302000, ((0x80300000 >> 12) << 10) | 1)
            s['post_memory'] = fuzz.cells(post)
        return s

    def test_prediction_supports_four_scenarios_and_store_post_memory(self):
        for mode in ('sv39', 'sv48'):
            for access in ('load', 'store'):
                with self.subTest(mode=mode, access=access):
                    s = self.scenario_seed(mode, access)
                    derived, decoded = self.predict(s)
                    self.assertEqual(decoded['mode'].lower(), mode)
                    self.assertEqual(decoded['access'], access)
                    self.assertEqual(derived['post_memory'], fuzz.cells(
                        self.decoder.memory_bytes(s['post_memory'])))
                    self.assertEqual(derived['post_registers']['x2'], s['post_registers']['x2'])
                    self.assertEqual(derived['post_registers']['tlb']['vector'][0]['ctor'],
                                     'Some<RTLB_Entry>')

    def test_store_dirty_permission_faults_and_data_access_fault(self):
        for flags, exception in ((0x47, 'E_SAMO_Page_Fault'),
                                 (0xc3, 'E_SAMO_Page_Fault'),
                                 (0x87, 'E_SAMO_Page_Fault'),
                                 (0xc7, 'E_SAMO_Access_Fault')):
            with self.subTest(flags=flags):
                s = self.scenario_seed('sv48', 'store')
                memory = self.decoder.memory_bytes(s['pre_memory'])
                fuzz.put_word(memory, 0x80301000, (1 << 46) | flags)
                derived, decoded = self.predict(s, memory)
                self.assertEqual(decoded['exception_type'], exception)
                self.assertEqual(derived['pre_memory'], derived['post_memory'])
                self.assertEqual(derived['post_registers']['x2'], s['pre_registers']['x2'])

    def test_store_unknown_initial_bytes_and_pte_data_alias(self):
        s = self.scenario_seed('sv39', 'store')
        for cell in s['pre_memory']:
            if cell['address'] >= 0x80400000:
                cell['value'] = None
        derived, decoded, change = fuzz.mutate(
            s, 'M5', random.Random(5), self.decoder, self.profile(), 101)
        self.assertEqual(self.decoder.read_word(self.decoder.memory_bytes(
            derived['post_memory']), 0x80400000), 0xdeadbeef)
        s = self.scenario_seed('sv39', 'store')
        memory = self.decoder.memory_bytes(s['pre_memory'])
        fuzz.put_word(memory, 0x80301000, ((0x80301000 >> 12) << 10) | 0xc7)
        derived, decoded = self.predict(s, memory)
        self.assertEqual(decoded['paddr_if_success'], 0x80301000)
        self.assertEqual(self.decoder.read_word(self.decoder.memory_bytes(
            derived['post_memory']), 0x80301000), 0xdeadbeef)
        self.assertEqual(int(derived['post_registers']['tlb']['vector'][0][
            'value']['struct']['pte']['bits'], 2), ((0x80301000 >> 12) << 10) | 0xc7)

    def test_corpus_binds_scenario_to_actual_instruction_and_satp(self):
        for mode in ('sv39', 'sv48'):
            for access in ('load', 'store'):
                s = self.scenario_seed(mode, access)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory)/'seeds.jsonl'
                    path.write_text(json.dumps(s)+'\n')
                    lock = {'platform_gen_sha256': 'gen'}
                    manifest = dict(lock=lock, samples_sha256=replay.sha256(path),
                                    scenario=mode+'-'+access)
                    seeds, stats = fuzz.load_corpus(path, manifest, lock, self.decoder)
                    self.assertEqual(len(seeds), 1)
                    manifest['scenario'] = mode+('-store' if access == 'load' else '-load')
                    with self.assertRaisesRegex(ValueError, '场景'):
                        fuzz.load_corpus(path, manifest, lock, self.decoder)

    def test_corpus_dedup_binds_manifest_and_preserves_class_sources(self):
        s = self.seed()
        t = copy.deepcopy(s)
        t['sample_id'] += 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'seeds.jsonl'
            path.write_text('\n'.join(json.dumps(x) for x in [t, s])+'\n')
            lock = {'platform_gen_sha256': 'gen'}
            manifest = dict(lock=lock, samples_sha256=replay.sha256(path), scenario='sv39-load')
            seeds, stats = fuzz.load_corpus(path, manifest, lock, self.decoder)
            self.assertEqual([x['sample_id'] for x in seeds], [s['sample_id']])
            self.assertEqual(stats['duplicates'], 1)
            self.assertEqual(stats['guard_classes'], 1)
            manifest['samples_sha256'] = 'wrong'
            with self.assertRaisesRegex(ValueError, 'R0'):
                fuzz.load_corpus(path, manifest, lock, self.decoder)

    def test_prediction_rebuilds_result_post_and_only_actual_footprint(self):
        s = self.seed()
        memory = self.decoder.memory_bytes(s['pre_memory'])
        memory[0x80200000] ^= 1
        derived, decoded = self.predict(s, memory)
        self.assertEqual(decoded['exception_type'], 'E_Load_Page_Fault')
        self.assertEqual(len(derived['pre_memory']), 8)
        self.assertEqual(derived['post_registers']['x2'], s['pre_registers']['x2'])
        self.assertEqual(derived['class_id'], None)
        self.assertEqual(derived['path_signature'], 0)
        self.assertEqual(s['result']['ctor'], 'Retire_Success')

    def test_new_pointer_read_is_concrete_before_judge(self):
        s = self.seed()
        memory = self.decoder.memory_bytes(s['pre_memory'])
        fuzz.put_word(memory, 0x80200000, ((0x81000000 >> 12) << 10) | 1)
        derived, decoded = self.predict(s, memory)
        self.assertEqual(decoded['failure_reason'], 'v_zero')
        self.assertEqual(len(derived['pre_memory']), 16)
        self.assertEqual(self.decoder.read_word(self.decoder.memory_bytes(
            derived['pre_memory']), 0x81000800), 0)

    def test_m1_keeps_nonleaf_reserved_n_and_priority_combinations(self):
        s = self.seed()
        for bit in (4, 6, 7, 63):
            memory = self.decoder.memory_bytes(s['pre_memory'])
            memory[0x80200000+bit//8] ^= 1 << (bit % 8)
            derived, decoded = self.predict(s, memory)
            self.assertEqual(decoded['exception_type'], 'E_Load_Page_Fault')
            self.assertTrue(self.decoder.read_word(self.decoder.memory_bytes(
                derived['pre_memory']), 0x80200000) & (1 << bit))
        memory = self.decoder.memory_bytes(s['pre_memory'])
        fuzz.put_word(memory, 0x80301000, (1 << 46) | 0x83)
        derived, decoded = self.predict(s, memory)
        self.assertEqual(decoded['exception_type'], 'E_Load_Page_Fault')
        self.assertEqual(self.decoder.read_word(self.decoder.memory_bytes(
            derived['pre_memory']), 0x80301000), (1 << 46) | 0x83)

    def test_napot_and_high_ppn_prediction_use_current_standard_decoder(self):
        s = self.seed()
        memory = self.decoder.memory_bytes(s['pre_memory'])
        fuzz.put_word(memory, 0x80301000, (1 << 63) | ((0x80408 << 10) | 0xc7))
        derived, decoded = self.predict(s, memory)
        self.assertEqual(decoded['paddr_if_success'], 0x80400000)
        fuzz.put_word(memory, 0x80301000, (1 << 46) | 0xc7)
        derived, decoded = self.predict(s, memory)
        self.assertEqual(decoded['exception_type'], 'E_Load_Access_Fault')

    def test_m2_subtree_copy_keeps_result_and_new_addresses(self):
        s = self.seed()
        derived, decoded, change = fuzz.mutate(
            s, 'M2', random.Random(3), self.decoder, self.profile(), 101,
            m2_mode='move')
        self.assertEqual(derived['post_registers']['x2'], s['post_registers']['x2'])
        self.assertEqual(change['operator'], 'M2')
        self.assertEqual(decoded['result'], 'Retire_Success')
        self.assertNotEqual(derived['pre_memory'], s['pre_memory'])
        self.assertEqual(change['parent_class_id'], s['class_id'])

    def test_m5_is_metamorphic_for_flags_and_software_bits(self):
        s = self.seed()
        original = self.decoder.decode_sample(s, self.decoder.Config(False, False, False))
        for seed_number in range(12):
            derived, decoded, change = fuzz.mutate(
                s, 'M5', random.Random(seed_number), self.decoder, self.profile(), seed_number)
            self.assertEqual(derived['result'], s['result'])
            self.assertEqual(derived['post_registers']['x2'], s['post_registers']['x2'])
            self.assertEqual(self.decoder.shape_key(decoded), self.decoder.shape_key(original))
            self.assertNotEqual(derived['pre_memory'], s['pre_memory'])
            self.assertEqual(change['operator'], 'M5')

    def test_no_harness_or_device_initialization(self):
        s = self.seed()
        for target in (0x80000000, 0x30000000):
            memory = self.decoder.memory_bytes(s['pre_memory'])
            fuzz.put_word(memory, 0x80200000, ((target >> 12) << 10) | 1)
            with self.assertRaisesRegex(fuzz.MutationRejected, 'R9'):
                self.predict(s, memory)

    def test_m5_pte_data_alias_recomputes_rd_but_keeps_result_and_shape(self):
        s = self.seed()
        words = {0x80200000: ((0x80300000 >> 12) << 10) | 1,
                 0x80300800: ((0x80301000 >> 12) << 10) | 1,
                 0x80301000: ((0x80301000 >> 12) << 10) | 0xc7}
        s['pre_memory'] = cells(words)
        s['post_memory'] = cells(words)
        s['post_registers']['x2'] = bits(words[0x80301000])
        derived, decoded, change = fuzz.mutate(
            s, 'M5', random.Random(5), self.decoder, self.profile(), 101)
        self.assertEqual(change['address'], 0x80301000)
        self.assertEqual(derived['result'], s['result'])
        self.assertNotEqual(derived['post_registers']['x2'], s['post_registers']['x2'])
        self.assertEqual(derived['post_registers']['x2'], bits(change['new_value']))
        self.assertEqual(decoded['paddr_if_success'], change['address'])

    def test_prediction_includes_tlb_fill_before_final_data_access_fault(self):
        s = self.seed()
        derived, decoded = self.predict(s)
        entry = derived['post_registers']['tlb']['vector'][0]
        self.assertEqual(entry['ctor'], 'Some<RTLB_Entry>')
        fields = entry['value']['struct']
        self.assertEqual(fields['pteAddr'], bits(0x80301000))
        self.assertEqual(fields['pte'], bits(((0x80400000 >> 12) << 10) | 0xc7))
        self.assertEqual(len(fields['vpn']['bits']), 45)
        self.assertEqual(len(fields['ppn']['bits']), 44)
        memory = self.decoder.memory_bytes(s['pre_memory'])
        fuzz.put_word(memory, 0x80301000, (1 << 46) | 0xc7 | (1 << 5))
        derived, decoded = self.predict(s, memory)
        self.assertEqual(decoded['exception_type'], 'E_Load_Access_Fault')
        fields = derived['post_registers']['tlb']['vector'][0]['value']['struct']
        self.assertEqual(fields['global'], {'bool': True})
        self.assertEqual(int(fields['ppn']['bits'], 2), 1 << 36)
        memory[0x80301000] &= ~(1 << 6)
        derived, decoded = self.predict(s, memory)
        self.assertEqual(decoded['exception_type'], 'E_Load_Page_Fault')
        self.assertEqual(derived['post_registers']['tlb'], s['pre_registers']['tlb'])

    def test_membership_gate_rejects_zero_multiple_and_wrong_expectation(self):
        for counts, reason in [((1, 1, 0), None), ((0, 0, 0), 'not_accepted'),
                               ((2, 2, 0), 'multiple_paths'), ((1, 0, 1), 'inconsistent')]:
            row = dict(zip(['accepted_paths', 'consistent_paths', 'inconsistent_paths'], counts))
            self.assertEqual(fuzz.membership_reason(row), reason)
        with self.assertRaises(AssertionError):
            fuzz.membership_reason(dict(accepted_paths=1, consistent_paths=1, inconsistent_paths=1))

    def test_coverage_uses_shape_not_inherited_class_and_never_schedules(self):
        s, decoded = self.predict(self.seed())
        coverage = fuzz.Coverage()
        first = coverage.observe(decoded)
        self.assertTrue(first['would_admit'])
        self.assertFalse(coverage.observe(decoded)['would_admit'])
        other = copy.deepcopy(decoded)
        other['class_id'] = 999
        other['path_signature'] = 999
        self.assertFalse(coverage.observe(other)['would_admit'])
        other['entries'][0]['fields']['G'] ^= 1
        self.assertTrue(coverage.observe(other)['would_admit'])
        self.assertEqual(coverage.summary()['shapes'], 1)

    def test_filter_is_exact_and_never_ignores_a_guard_class(self):
        s, decoded = self.predict(self.seed())
        case = {'decoded': decoded}
        observation = dict(xs_cause=13, nemu_cause=0, isla_consistent_side='nemu')
        key = fuzz.mismatch_key(case, observation)
        table = fuzz.MismatchTable([dict(key=key, reason='定向确认的具体输入差异')])
        self.assertTrue(table.record(case, observation, 'a')['filtered'])
        self.assertTrue(table.record(case, observation, 'b')['filtered'])
        changed = copy.deepcopy(case)
        changed['decoded']['entries'][0]['value'] = '0x0000000000000001'
        self.assertFalse(table.record(changed, observation, 'c')['filtered'])
        observation['xs_cause'] = 5
        self.assertFalse(table.record(case, observation, 'd')['filtered'])
        groups = table.summary()
        self.assertEqual(groups['filtered_samples'], 2)
        self.assertEqual(groups['groups'][0]['representative'], 'a')
        self.assertEqual(groups['groups'][0]['count'], 2)
        with self.assertRaises(AssertionError):
            fuzz.MismatchTable([dict(class_id=0, reason='禁止整类忽略')])

    def rule_case(self, value, access='load', level=0):
        s = self.scenario_seed('sv39', access)
        memory = self.decoder.memory_bytes(s['pre_memory'])
        address = {0: 0x80301000, 1: 0x80300800, 2: 0x80200000}[level]
        fuzz.put_word(memory, address, value)
        derived, decoded = self.predict(s, memory)
        cause = {None: 0, 'E_Load_Page_Fault': 13, 'E_SAMO_Page_Fault': 15,
                 'E_Load_Access_Fault': 5, 'E_SAMO_Access_Fault': 7}[decoded['exception_type']]
        observation = dict(xs_cause=5 if access == 'load' else 7,
                           nemu_cause=cause, isla_consistent_side='nemu')
        return dict(decoded=decoded, expected=dict(cause=cause)), observation

    def test_reported_rule_accepts_permission_and_ad_faults_with_wide_leaf_ppn(self):
        examples = [(0x000040000000000b, 'load', 'accessed_update_disabled'),
                    (0x0000400000000009, 'load', 'load_permission'),
                    (0x0000400000000003, 'store', 'store_permission'),
                    (0x0000400000000019, 'store', 'privilege_permission'),
                    (0x0000400000000047, 'store', 'dirty_update_disabled'),
                    (0x002000000000000b, 'load', 'accessed_update_disabled')]
        for value, access, failure in examples:
            for level in (0, 1, 2):
                with self.subTest(value=hex(value), access=access, level=level):
                    case, observation = self.rule_case(value, access, level)
                    self.assertEqual(case['decoded']['failure_reason'], failure)
                    table = fuzz.MismatchTable(fuzz.KNOWN_MISMATCH_RULES)
                    recorded = table.record(case, observation, 'representative')
                    self.assertTrue(recorded['filtered'])
                    self.assertEqual(recorded['known_rule'], fuzz.KNOWN_MISMATCH_RULES[0]['rule'])
                    self.assertIn('已上报', table.summary()['groups'][0]['known_reason'])

    def test_reported_rule_rejects_nonwide_structural_and_successful_walks(self):
        examples = [(0xb, 0, 'accessed_update_disabled'),
                    ((1 << 45) | 0xb, 0, 'accessed_update_disabled'),
                    ((1 << 46) | (1 << 10) | 0xb, 1, 'superpage_misaligned'),
                    ((1 << 46) | (1 << 54) | 0xb, 0, 'reserved_nonzero'),
                    ((1 << 46) | 0xc7, 0, 'data_read_pma_access_fault')]
        for value, level, failure in examples:
            with self.subTest(value=hex(value), level=level):
                case, observation = self.rule_case(value, level=level)
                self.assertEqual(case['decoded']['failure_reason'], failure)
                # 真实的两边 PF / 两边 AF 均不命中；伪造 AF/PF 也不能绕过失败原因检查。
                for xs_cause in (case['expected']['cause'], 5):
                    observation['xs_cause'] = xs_cause
                    table = fuzz.MismatchTable(fuzz.KNOWN_MISMATCH_RULES)
                    self.assertFalse(table.record(case, observation, 'negative')['filtered'])

    def test_reported_rule_requires_exact_causes_access_and_nemu_agreement(self):
        case, observation = self.rule_case(0x000040000000000b)
        for field, value in [('xs_cause', 7), ('xs_cause', None), ('nemu_cause', 15),
                             ('isla_consistent_side', 'neither'), ('isla_consistent_side', 'both')]:
            with self.subTest(field=field, value=value):
                changed = dict(observation, **{field: value})
                self.assertFalse(fuzz.MismatchTable(fuzz.KNOWN_MISMATCH_RULES).record(
                    case, changed, 'wrong-observation')['filtered'])
        for changed in (dict(case, expected=dict(cause=15)),
                        dict(case, decoded=dict(case['decoded'], access='store'))):
            self.assertFalse(fuzz.MismatchTable(fuzz.KNOWN_MISMATCH_RULES).record(
                changed, observation, 'wrong-case')['filtered'])

    def test_reported_rule_supports_fetch_cause_tuple_without_claiming_fetch_replay(self):
        # 当前 pt_decode 仅支持 LOAD/STORE；这里只检验规则的取指 cause 分支。
        case, observation = self.rule_case(0x0000400000000009)
        case['decoded'].update(access='fetch', failure_reason='fetch_permission')
        case['decoded']['entries'][-1]['failure_reason'] = 'fetch_permission'
        case['expected']['cause'] = 12
        observation.update(xs_cause=1, nemu_cause=12)
        self.assertTrue(fuzz.MismatchTable(fuzz.KNOWN_MISMATCH_RULES).record(
            case, observation, 'fetch')['filtered'])
        observation['xs_cause'] = 5
        self.assertFalse(fuzz.MismatchTable(fuzz.KNOWN_MISMATCH_RULES).record(
            case, observation, 'wrong-fetch')['filtered'])

    def test_reported_rule_keeps_raw_groups_counts_and_representatives(self):
        case, observation = self.rule_case(0x000040000000000b)
        exact = dict(key=fuzz.mismatch_key(case, observation), reason='历史精确输入')
        table = fuzz.MismatchTable([exact, *fuzz.KNOWN_MISMATCH_RULES])
        before = copy.deepcopy(case)
        table.record(case, observation, 'first')
        table.record(case, observation, 'second')
        other, other_observation = self.rule_case(0x0000400000000009)
        table.record(other, other_observation, 'other')
        summary = table.summary()
        self.assertEqual(case, before)
        self.assertEqual(summary['mismatch_samples'], 3)
        self.assertEqual(summary['filtered_samples'], 3)
        self.assertEqual(len(summary['groups']), 2)
        self.assertEqual(summary['groups'][0]['count'], 2)
        self.assertEqual(summary['groups'][0]['representative'], 'first')
        self.assertEqual(summary['groups'][0]['known_rule'], fuzz.KNOWN_MISMATCH_RULES[0]['rule'])
        with self.assertRaises(AssertionError):
            fuzz.MismatchTable([dict(rule='whole_guard_class', reason='禁止整类忽略')])

    def test_observation_keeps_native_nemu_separate_from_guided_reference(self):
        case = {'expected': {'cause': 0}, 'symbols': dict(payload_ins=0x100, good_trap_ins=0x200,
                                fail_unexpected_trap_trap=0x204)}
        result = dict(agree=False, abort=False, bucket='xs!=expected',
                      trap_symbol='fail_unexpected_trap_trap')
        trace = [dict(event='start', pc=0x100, guided_exec=False),
                 dict(event='step', pc=0x200, mcause=0, x2=7)]
        log = ('ECFG3_NATIVE child_status=0\nECFG3_GUIDE force=1 cause=13 mtval=0x20000000\n'
               'ECFG3_REF pc=0x204 mcause=13 mtval=0x20000000 mepc=0x100 x2=0\n')
        observation = fuzz.observe_run(case, result, trace, log)
        self.assertEqual(observation['xs_cause'], 13)
        self.assertEqual(observation['nemu_cause'], 0)
        self.assertEqual(observation['isla_consistent_side'], 'nemu')
        self.assertFalse(observation['native_guided_exec'])
        trace[-1]['pc'] = 0x204
        self.assertEqual(fuzz.observe_run(case, result, trace, log)[
            'isla_consistent_side'], 'neither')
        with self.assertRaises(AssertionError):
            fuzz.observe_run(case, result, trace, log.replace('child_status=0', 'child_status=9'))
        result.update(abort=True, bucket='xs!=nemu')
        # ABORT 未到 C2，且没有 DUT cause 证据时，不猜测哪边与 Isla 一致。
        unknown = fuzz.observe_run(case, result, trace,
                                  'ECFG3_NATIVE child_status=0\n')
        self.assertEqual(unknown['isla_consistent_side'], 'unobserved')
        self.assertIsNone(unknown['xs_cause'])

    def test_check_command_pins_threads_and_replaces_only_sample_paths(self):
        template = ['isarch', '-T', '32', '--check-samples', '/old/input',
                    '--check-samples-report', '/old/report', '--clause=LOAD']
        command = fuzz.check_command(template, Path('/new/input'), Path('/new/report'))
        self.assertEqual(command[command.index('-T')+1], '32')
        self.assertEqual(command[command.index('--check-samples')+1], '/new/input')
        self.assertEqual(template[template.index('--check-samples')+1], '/old/input')
        template[template.index('-T')+1] = '64'
        with self.assertRaises(AssertionError):
            fuzz.check_command(template, Path('/new/input'), Path('/new/report'))


if __name__ == '__main__':
    unittest.main()
