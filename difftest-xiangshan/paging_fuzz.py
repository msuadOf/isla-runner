#!/usr/bin/env python3
"""P1 页表变异：J2 预测、J1 批量确认、原址重放和只记录的形状反馈。"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import time

import paging_replay as replay

FLAG_BITS = tuple(range(10)) + tuple(range(54, 64))
OPERATORS = ('M1', 'M2', 'M5')
SCENARIOS = ('sv39-load', 'sv39-store', 'sv48-load', 'sv48-store')
KNOWN_MISMATCH_RULES = (dict(
    rule='xs_leaf_ppn_af_over_permission_pf',
    reason='已上报的 XiangShan 真发现：规范按遍历顺序应报 PF；'
           'XiangShan TLB.scala 的 !af 掩码使第 6-9 步的权限/A/D PF '
           '让位于叶 PPN 溢出 AF，已上报。'),)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def input_digest(sample):
    return hashlib.sha256(canonical({key: sample[key] for key in
        ('pre_registers', 'pre_memory', 'isa_state')}).encode()).hexdigest()


def load_corpus(path, manifest, lock, decoder):
    """只接受清单绑定的 class_cap=1 语料；重复输入保留最小 sample_id。"""
    if manifest['lock'] != lock or replay.sha256(path) != manifest['samples_sha256']:
        raise ValueError('R0: 种子与生成清单或 lock 不一致')
    if manifest['scenario'] not in SCENARIOS:
        raise ValueError('不支持的种子场景')
    unique, classes, ids = {}, {}, {}
    total = 0
    for line in Path(path).read_text().splitlines():
        s = json.loads(line, object_pairs_hook=decoder.unique_object,
                       parse_constant=decoder.reject_constant)
        decoder.exact(s, decoder.SAMPLE_FIELDS, 'samples v1')
        assert s['schema_version'] == 1 and s['mode'] == 'merge'
        assert type(s['class_id']) is int and type(s['path_signature']) is int
        for section in ('pre_registers', 'post_registers'):
            for value in s[section].values():
                decoder.validate_concrete(value)
        decoder.validate_concrete(s['result'])
        access = decoder.decode_instruction(s)[0]
        translation = decoder.parse_satp(decoder.bit_value(s['pre_registers']['satp'], 64))
        if translation['mode'].lower()+'-'+access != manifest['scenario']:
            raise ValueError('种子实际场景与清单不符')
        decoder.memory_bytes(s['pre_memory'], allow_unknown=access == 'store')
        decoder.memory_bytes(s['post_memory'])
        digest = input_digest(s)
        if s['sample_id'] in ids:
            assert ids[s['sample_id']] == canonical(s), '同一 sample_id 内容冲突'
        ids[s['sample_id']] = canonical(s)
        key = (s['path_signature'], s['class_id'])
        if key in classes:
            assert classes[key] == digest, '种子不是每个守卫类一个代表'
        classes[key] = digest
        identity = (*key, digest)
        if identity not in unique or s['sample_id'] < unique[identity]['sample_id']:
            unique[identity] = s
        total += 1
    assert total > 0
    seeds = sorted(unique.values(), key=lambda s: s['sample_id'])
    return seeds, dict(input_samples=total, unique_samples=len(seeds),
                       duplicates=total-len(seeds), guard_classes=len(classes),
                       samples_sha256=manifest['samples_sha256'])


class MutationRejected(ValueError):
    """只用于已有平台边界拒绝；语义或内部不变量错误不能转成丢弃。"""


def put_word(memory, address, value):
    assert address % 8 == 0 and 0 <= value < 1 << 64
    for i in range(8):
        memory[address+i] = (value >> (8*i)) & 255


def cells(memory):
    return [dict(address=a, value=v, bytes=1) for a, v in sorted(memory.items())]


def region_kind(address, profile):
    matches = [r['kind'] for r in profile['regions']
               if r['base'] <= address and address+8 <= r['base']+r['size']]
    assert len(matches) <= 1, '平台区域重叠'
    return matches[0] if matches else None


def check_read_address(address, profile):
    low, high = profile['harness']['reserved']
    if low <= address < high or region_kind(address, profile) in {None, 'device'}:
        raise MutationRejected(f'R9: 访问 harness/device/未描述区域 {address:#x}')


def predict_sample(parent, memory, decoder, profile, sample_id):
    """补齐新读取并生成 J2 提案；随后用严格 pt_decode 核对足迹和预测。"""
    registers = parent['pre_registers']
    access, offset, base = decoder.decode_instruction(parent)
    assert access in {'load', 'store'} and (offset, base) == (0, 1)
    assert decoder.effective_address(parent) == 0x20000000
    translation = decoder.parse_satp(decoder.bit_value(registers['satp'], 64))
    assert translation['mode'] in {'Sv39', 'Sv48'}
    assert translation['root_paddr'] == 0x80200000
    page_fault, access_fault = (13, 5) if access == 'load' else (15, 7)
    assert registers['cur_privilege']['enum'] == 'Supervisor'
    status = decoder.bit_value(registers['mstatus']['struct']['bits'], 64)
    assert not status & (1 << 17), 'P1 不改变权限场景'
    assert profile['isa']['standard_paging'] and not profile['isa']['svrsw60t59b']
    config = decoder.Config(False, False, False)
    pool, footprint = dict(memory), {}
    va, table, cause, rd = 0x20000000, 0x80200000, 0, None

    def read(address, default):
        check_read_address(address, profile)
        assert region_kind(address, profile) == 'ram'
        assert decoder.pma_permitted(registers, address, 'load') is True
        # 新页表槽填0，新数据填固定标记；这是本次输入，而不是对未知语义的猜测。
        for i in range(8):
            if address+i not in pool:
                pool[address+i] = (default >> (8*i)) & 255
            assert type(pool[address+i]) is int
            footprint[address+i] = pool[address+i]
        return decoder.read_word(pool, address)

    for level in reversed(range(translation['levels'])):
        address = table + ((va >> (12+9*level)) & 511)*8
        check_read_address(address, profile)
        if region_kind(address, profile) == 'hole':
            assert decoder.pma_permitted(registers, address, 'load') is False
            cause = access_fault
            break
        value = read(address, 0)
        entry = decoder.classify_pte(value, level, config)
        fields = entry['fields']
        if entry['failure_reason']:
            cause = page_fault
            break
        if entry['role'] == 'pointer':
            table = fields['PPN'] << 12
            continue
        assert entry['role'] == 'leaf'
        if ((fields['U'] and not status & (1 << 18))
                or not (fields['W'] if access == 'store' else
                        (fields['R'] or (fields['X'] and status & (1 << 19))))
                or not fields['A'] or (access == 'store' and not fields['D'])):
            cause = page_fault
            break
        size = entry['page_size']
        physical = ((fields['PPN'] << 12) & ~(size-1)) | (va & (size-1))
        check_read_address(physical, profile)
        if region_kind(physical, profile) == 'hole':
            assert decoder.pma_permitted(registers, physical, access) is False
            cause = access_fault
        else:
            rd = read(physical, 0x5a17c0de12345678)
        break
    else:
        raise AssertionError('页表遍历没有终点')
    derived = copy.deepcopy(parent)
    derived.update(sample_id=sample_id, path_signature=0, class_id=None, truncated=False,
                   pre_memory=cells(footprint), post_memory=cells(footprint))
    for key in derived['post_registers']:
        assert key in registers, f'尚未定义的后态寄存器 {key}'
        derived['post_registers'][key] = copy.deepcopy(registers[key])
    if not cause:
        assert rd is not None
        if access == 'load':
            derived['post_registers']['x2'] = {'bits': f'{rd:064b}'}
        else:
            post = dict(footprint)
            put_word(post, physical, decoder.bit_value(registers['x2'], 64))
            derived['post_memory'] = cells(post)
        derived['result'] = {'ctor': 'Retire_Success', 'value': {'unit': True}}
        derived['ret_val'] = '(|Retire_Success| (_ unit))'
    else:
        exception = {5: 'E_Load_Access_Fault', 13: 'E_Load_Page_Fault',
                     7: 'E_SAMO_Access_Fault', 15: 'E_SAMO_Page_Fault'}[cause]
        derived['result'] = {'ctor': 'Memory_Exception', 'value': {'struct': {
            decoder.EXCEPTION_FIELDS[0]: {'bits': f'{va:064b}'},
            decoder.EXCEPTION_FIELDS[1]: {'ctor': exception, 'value': {'unit': True}}}}}
        derived['ret_val'] = (f'(|Memory_Exception| (_ struct '
            f'(|{decoder.EXCEPTION_FIELDS[0]}| #x{va:016x}) '
            f'(|{decoder.EXCEPTION_FIELDS[1]}| (|{exception}| (_ unit)))))')
    decoded = decoder.decode_sample(derived, config)
    # translate_TLB_miss 在最终数据 PMA 检查前调用 add_to_TLB。
    # 按冻结模型 vmem_tlb.sail 的字段、掩码和槽位原样预测，仍由 J1 确认。
    if decoded['translated_paddr'] is not None:
        leaf = next(e for e in decoded['entries'] if e['role'] == 'leaf')
        mask = (1 << (9*leaf['level']))-1
        vpn = (va >> 12) & ~mask
        ppn = (decoded['translated_paddr'] >> 12) & ~mask
        tlb = derived['post_registers']['tlb']['vector']
        assert len(tlb) == 64 and all(e['ctor'] == 'None<RTLB_Entry>' for e in tlb)
        def bits(value, width):
            assert 0 <= value < 1 << width
            return {'bits': f'{value:0{width}b}'}
        tlb[vpn & 63] = dict(ctor='Some<RTLB_Entry>', value={'struct': dict(
            asid=bits(0, 16), vpn=bits(vpn, 45), ppn=bits(ppn, 44),
            levelMask=bits(mask, 45), pte=bits(int(leaf['value'], 16), 64),
            pteAddr=bits(leaf['paddr'], 64),
            global_value={'bool': any(e['fields']['G'] for e in decoded['entries']
                                      if e['role'] != 'data')})})
        fields = tlb[vpn & 63]['value']['struct']
        fields['global'] = fields.pop('global_value')
    return derived, decoded


def mutate(parent, operator, rng, decoder, profile, sample_id, *, m2_mode=None):
    assert operator in OPERATORS
    decoded = decoder.decode_sample(parent, decoder.Config(False, False, False))
    entries = [e for e in decoded['entries'] if e['role'] != 'data']
    assert entries
    entry = rng.choice(entries)
    memory = decoder.memory_bytes(parent['pre_memory'], allow_unknown=True)
    post = decoder.memory_bytes(parent['post_memory'])
    memory = {a: post[a] ^ 255 if byte is None else byte for a, byte in memory.items()}
    address, value = entry['paddr'], int(entry['value'], 16)
    change = dict(operator=operator, parent_sample_id=parent['sample_id'],
                  parent_path_signature=parent['path_signature'], parent_class_id=parent['class_id'],
                  source_only=True, address=address, old_value=value)
    if operator == 'M1':
        changed_bits = rng.sample(FLAG_BITS, rng.choice((1, 2)))
        for bit in changed_bits:
            value ^= 1 << bit
        change['bits'] = changed_bits
    elif operator == 'M5':
        # G 和 RSW[9:8] 不改变 result 或形状；PTE/数据别名时仍须重算 rd。
        mask = rng.randint(1, 7)
        for i, bit in enumerate((5, 8, 9)):
            if mask & (1 << i):
                value ^= 1 << bit
        change['free_mask'] = mask
    else:
        pointers = [e for e in entries if e['role'] == 'pointer' and e['level'] > 0]
        modes = ('move', 'alias', 'boundary') if pointers else ('alias', 'boundary')
        mode = rng.choice(modes) if m2_mode is None else m2_mode
        assert mode in modes, '该种子没有可搬迁的子树'
        if mode == 'move':
            entry = rng.choice(pointers)
            address, value = entry['paddr'], int(entry['value'], 16)
            old_page = entry['fields']['PPN'] << 12
            target = 0x81000000 + rng.randrange(256)*4096
            assert not any(target <= a < target+4096 for a in memory)
            for a, byte in list(memory.items()):
                if old_page <= a < old_page+4096:
                    memory[target+a-old_page] = byte
            ppn = target >> 12
            change.update(old_page=old_page, new_page=target)
        elif mode == 'alias':
            ppn = rng.choice([e['paddr'] >> 12 for e in entries])
        else:
            ppn = rng.choice((0x80100, 0x80200, 0x80300, (1 << 31)-1,
                              1 << 31, (1 << 31)+1, (1 << 36)-1,
                              1 << 36, (1 << 36)+1))
        change.update(address=address, old_value=value, m2_mode=mode, ppn=ppn)
        value = (value & ~replay.PPN_MASK) | (ppn << 10)
    put_word(memory, address, value)
    change['new_value'] = value
    derived, new_decoded = predict_sample(parent, memory, decoder, profile, sample_id)
    if operator == 'M5':
        assert derived['result'] == parent['result'], 'M5 改变 result'
        assert decoder.shape_key(new_decoded) == decoder.shape_key(decoded), 'M5 改变形状'
    return derived, new_decoded, change


def membership_reason(row):
    accepted, consistent, inconsistent = (row[k] for k in
        ('accepted_paths', 'consistent_paths', 'inconsistent_paths'))
    assert all(type(v) is int and v >= 0 for v in (accepted, consistent, inconsistent))
    assert accepted == consistent+inconsistent
    if not accepted:
        return 'not_accepted'
    if accepted > 1:
        return 'multiple_paths'
    return 'inconsistent' if inconsistent else None


def ppn_bucket(ppn):
    address = ppn << 12
    if address >= 1 << 48:
        return 'ge_2p48'
    if address >= 1 << 43:
        return 'ge_2p43'
    if address == 0x80200000:
        return 'root_table'
    if 0x80200000 <= address < 0x80203000:
        return 'page_tables'
    if 0x80000000 <= address < 0x80100000:
        return 'harness'
    if address < 0x80000000:
        return 'below_dram'
    if address >= (1 << 43)-(1 << 20):
        return 'dram_top'
    return 'dram_low' if address < 1 << 32 else 'dram_middle'


class Coverage:
    """P1 只登记形状与字段桶，不把反馈送给种子选择器。"""
    def __init__(self):
        self.keys = set()
        self.shapes = set()

    def observe(self, decoded, mismatch=False):
        shape = canonical({k: decoded[k] for k in ('access', 'mode', 'sequence', 'leaf_level',
                                                  'result', 'exception_type', 'failure_reason')})
        keys = set()
        for entry in decoded['entries']:
            if entry['role'] == 'data':
                continue
            fields = entry['fields']
            for name in ('V', 'R', 'W', 'X', 'U', 'G', 'A', 'D', 'N', 'PBMT', 'RSW',
                         'RSW_60t59b', 'reserved', 'PPN'):
                value = ppn_bucket(fields[name]) if name == 'PPN' else fields[name]
                keys.add((shape, entry['level'], name, value))
        added = keys-self.keys
        new_shape = shape not in self.shapes
        self.keys.update(keys)
        self.shapes.add(shape)
        return dict(would_admit=bool(added) or mismatch, new_shape=new_shape,
                    new_slice_buckets=len(added), mismatch=mismatch)

    def summary(self):
        return dict(shapes=len(self.shapes), shape_slice_buckets=len(self.keys),
                    scope='形状 × 切片桶；父种子守卫类仅作为来源；无反馈调度')

    def export(self):
        return dict(**self.summary(), keys=sorted(self.keys, key=canonical))


def mismatch_key(case, observation):
    """精确键保留 PTE 级别、地址和值，禁止用整个守卫类作键。

    另支持已上报问题的窄规则：叶 PTE[53:46]、遍历失败步骤及三方 cause
    必须同时满足；规则不以守卫类为键，也不删除原始计数或代表样本。
    """
    return dict(ptes=[dict(level=e['level'], address=e['paddr'], value=e['value'])
                      for e in case['decoded']['entries'] if e['role'] != 'data'],
                xs_cause=observation['xs_cause'], nemu_cause=observation['nemu_cause'],
                isla_consistent_side=observation['isla_consistent_side'])


def reported_xs_ppn_fault(case, observation):
    """仅归类叶 PPN 超宽 AF 抢占遍历第 6-9 步 PF 的已上报发现。"""
    decoded = case['decoded']
    causes = {'load': (5, 13, 13), 'store': (7, 15, 15), 'fetch': (1, 12, 12)}
    expected = causes.get(decoded['access'])
    if (expected is None or observation['isla_consistent_side'] != 'nemu'
            or (observation['xs_cause'], observation['nemu_cause'],
                case.get('expected', {}).get('cause')) != expected):
        return False
    reasons = {'privilege_permission', f"{decoded['access']}_permission",
               'accessed_update_disabled'}
    if decoded['access'] == 'store':
        reasons.add('dirty_update_disabled')
    if decoded['failure_reason'] not in reasons:
        return False
    ptes = [e for e in decoded['entries'] if e['role'] != 'data']
    # pt_decode 先判结构异常和超级页对齐；这些 PF 不能归入权限优先级问题。
    if any(e['role'] not in {'pointer', 'leaf'} or
           e['failure_reason'] not in reasons | {None} for e in ptes):
        return False
    leaves = [e for e in ptes if e['role'] == 'leaf']
    if len(leaves) != 1 or leaves[0] is not ptes[-1]:
        return False
    value, level = int(leaves[0]['value'], 16), leaves[0]['level']
    return bool(value & (0xff << 46)) and not (
        (value >> 10) & ((1 << (9*level))-1))


class MismatchTable:
    def __init__(self, known=()):
        self.known, self.rules, self.groups = {}, {}, {}
        for item in known:
            if 'rule' in item:
                assert set(item) == {'rule', 'reason'} and item['reason']
                assert item['rule'] in {r['rule'] for r in KNOWN_MISMATCH_RULES}
                assert item['rule'] not in self.rules
                self.rules[item['rule']] = item['reason']
                continue
            assert set(item) == {'key', 'reason'} and item['reason']
            key = item['key']
            assert set(key) == {'ptes', 'xs_cause', 'nemu_cause', 'isla_consistent_side'}
            assert key['ptes'] and key['xs_cause'] is not None and key['nemu_cause'] is not None
            assert key['isla_consistent_side'] in {'xs', 'nemu', 'both', 'neither'}
            for pte in key['ptes']:
                assert set(pte) == {'level', 'address', 'value'}
                assert type(pte['level']) is int and type(pte['address']) is int
                assert re.fullmatch(r'0x[0-9a-f]{16}', pte['value'])
            identity = canonical(key)
            assert identity not in self.known
            self.known[identity] = item['reason']

    def record(self, case, observation, sample_ref):
        key = mismatch_key(case, observation)
        identity = canonical(key)
        rule = next((name for name in self.rules if reported_xs_ppn_fault(case, observation)), None)
        reason = self.rules[rule] if rule else self.known.get(identity)
        filtered = reason is not None
        if identity not in self.groups:
            self.groups[identity] = dict(key=key, count=0, filtered_samples=0,
                representative=sample_ref, known_reason=reason)
            if rule:
                self.groups[identity]['known_rule'] = rule
        group = self.groups[identity]
        group['count'] += 1
        group['filtered_samples'] += int(filtered)
        return dict(filtered=filtered, group_key=key, known_rule=rule)

    def summary(self):
        groups = list(self.groups.values())
        return dict(groups=groups, mismatch_samples=sum(g['count'] for g in groups),
                    filtered_samples=sum(g['filtered_samples'] for g in groups),
                    known_entries=len(self.known)+len(self.rules))


def check_command(template, inputs, report):
    command = list(template)
    assert command[command.index('-T')+1] == '32'
    command[command.index('--check-samples')+1] = str(inputs)
    command[command.index('--check-samples-report')+1] = str(report)
    return command


def check_batch(samples, directory, source, scenario='sv39-load'):
    """沿 ecfg3 的 J1 命令与逐查询 excluded 证明；后端不内嵌求解器。"""
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'badread').mkdir()
    inputs, report = directory/'input.jsonl', directory/'check.json'
    ids = {s['sample_id'] for s in samples}
    assert len(ids) == len(samples) > 0
    inputs.write_text(''.join(canonical(s)+'\n' for s in samples))
    template = json.loads((source/f'{scenario}-e3/done.json').read_text())['command']
    command = check_command(template, inputs, report)
    env = os.environ.copy()
    env.update(LD_PRELOAD=str(source/'observe.so'), BADREAD_DUMP=str(directory/'badread'),
               ISLA_STATS='1', PYTHONDONTWRITEBYTECODE='1')
    record = dict(command=command, input_sha256=replay.sha256(inputs), count=len(samples),
                  observer_sha256=replay.sha256(source/'observe.so'))
    write_json(directory/'running.json', record)
    start = time.monotonic()
    with (directory/'stdout.txt').open('w') as stdout, (directory/'stderr.txt').open('w') as stderr:
        proc = subprocess.Popen(command, cwd=directory, env=env, stdout=stdout,
                                stderr=stderr, start_new_session=True)
        try:
            returncode = proc.wait(timeout=895)
        except BaseException:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise
    record.update(returncode=returncode, seconds=time.monotonic()-start)
    write_json(directory/'done.json', record)
    assert returncode == 0, 'J1 未正常退出，查看 stderr.txt'
    rows = json.loads(report.read_text())
    assert rows['sample_total'] == len(samples)
    assert len(rows['samples']) == len(samples)
    assert {r['sample_id'] for r in rows['samples']} == ids
    summary = json.loads((directory/f'output/rv64_z{scenario.split("-")[1].upper()}.json').read_text())['summary']
    assert all(summary[k] == 0 for k in ('execution-timeouts', 'smt-timeouts',
        'unfinished-paths', 'model-query-timeouts', 'pending-batches'))
    # 保留 raw partial；每个执行错误都须有独立 excluded 证明。
    proofs = []
    for query in sorted((directory/'badread').glob('query-*.smt2')):
        if not query.stem.removeprefix('query-').isdigit():
            continue
        completed = subprocess.run([str(source/'check_badread'), str(query),
            str(query.with_name(query.stem+'-without-excluded.smt2'))],
            capture_output=True, text=True, check=True, timeout=60)
        proof = json.loads(completed.stdout)
        assert proof['original_unsat'] and proof['without_current_excluded_sat']
        assert not proof['overlap_sat_by_excluded_index'][0], 'harness 不能当作设备过滤'
        proofs.append(dict(query=query.name, **proof))
    assert summary['errors'] == len(proofs), '存在未解释的执行错误'
    assert summary['status'] == ('partial' if proofs else 'finished')
    record.update(raw_summary=summary, excluded_filtered_paths=len(proofs),
                  proofs=proofs, check_sha256=replay.sha256(report),
                  seconds_per_sample=record['seconds']/len(samples))
    write_json(directory/'done.json', record)
    return {r['sample_id']: r for r in rows['samples']}, record


def observe_run(case, result, trace, log):
    """NEMU 独立子进程的退出与 C1 同步参考分开记录。"""
    assert re.search(r'ECFG3_NATIVE child_status=0\b', log), '独立 NEMU 子进程未正常完成'
    starts = [s for s in trace if s['event'] == 'start']
    assert len(starts) == 1 and starts[0]['pc'] == case['symbols']['payload_ins']
    assert starts[0]['guided_exec'] is False
    last = trace[-1]
    assert last['event'] == 'step'
    names = [name for name, pc in case['symbols'].items() if pc == last['pc']]
    assert len(names) == 1 and (names[0] == 'good_trap_ins' or
        names[0] in {f'fail_{reason}_trap' for reason in replay.FAILURE_REASONS}), 'NEMU 未到登记出口'
    nemu_agrees = names[0] == 'good_trap_ins'
    xs_agrees = (True if result['agree'] else False if result['bucket'] == 'xs!=expected' else None)
    xs_cause = None
    if result['abort']:
        difference = re.search(r'mcause different at pc = 0x[0-9a-f]+, '
                               r'right = 0x[0-9a-f]+, wrong = 0x([0-9a-f]+)', log)
        if difference:
            xs_cause = int(difference[1], 16)
    else:
        refs = re.findall(r'ECFG3_REF pc=0x[0-9a-f]+ mcause=(\d+)', log)
        assert refs, '缺少参考寄存器观测'
        xs_cause = int(refs[-1])
    # 页异常 force=1 中的 cause 来自 DUT，不能用它推断独立 NEMU。
    guides = re.findall(r'ECFG3_GUIDE force=1 cause=(\d+)', log)
    if guides:
        xs_cause = int(guides[-1])
    if xs_cause is not None and xs_cause != case['expected']['cause']:
        xs_agrees = False
    side = ('unobserved' if xs_agrees is None else
            'both' if xs_agrees and nemu_agrees else 'xs' if xs_agrees else
            'nemu' if nemu_agrees else 'neither')
    return dict(xs_cause=xs_cause, nemu_cause=last['mcause'], isla_consistent_side=side,
                native_exit_symbol=names[0], native_guided_exec=False,
                native_result=last, xs_result_observed=result['bucket'] in {'agree', 'xs!=expected'})


def replay_one(task):
    """每个 worker 独立设置观察器环境，避免并发交叉污染。"""
    case, directory, files, observer = task
    built = replay.build_case(case, directory)
    os.environ.update(XIANGSHAN_DIFF_SO=str(files['nemu']),
        PAYLOAD_PC=hex(built['symbols']['payload_ins']),
        EXIT_LOW=hex(built['symbols']['good_trap_ins']),
        EXIT_HIGH=hex(built['symbols']['fail_memory_trap']))
    result = replay.run_probe(built, files['emu'], observer, timeout=120)
    if result['bucket'] in {'timeout', 'limit', 'framework-abort', 'other-failure'}:
        raise RuntimeError(f'重放基础设施失败：{directory} {result["bucket"]}')
    trace_path = directory/'native-nemu-trace.jsonl'
    trace = [json.loads(line) for line in trace_path.read_text().splitlines()]
    observation = observe_run(built, result, trace, Path(result['log']).read_text(errors='replace'))
    result.update(observation=observation, native_trace_sha256=replay.sha256(trace_path),
                  original_nemu_sha256=replay.sha256(files['nemu']),
                  observer_sha256=replay.sha256(observer), source=case['source'])
    write_json(directory/'result.json', result)
    return result


def snapshot(paths):
    """不把访问时间当作内容变化；记录旧证据的内容身份。"""
    return {str(p): replay.sha256(p) for base in paths for p in sorted(base.rglob('*'))
            if p.is_file()}


def campaign(args):
    source, out = args.source.resolve(), args.out.resolve()
    output_root = Path(__file__).resolve().parents[1]/'output'
    assert any(out.is_relative_to(output_root/name) for name in ('fuzz-p1', 'fuzz-p1b'))
    scenario = args.scenario
    assert scenario in SCENARIOS
    out.mkdir(parents=True, exist_ok=False)
    for name in ('tmp', 'cache'):
        (out/name).mkdir()
    os.environ.update(TMPDIR=str(out/'tmp'), XDG_CACHE_HOME=str(out/'cache'),
                      PYTHONDONTWRITEBYTECODE='1')
    assert 1 <= args.workers <= 8 and 0 < args.count <= 2000
    profile = json.loads((source/'profile.json').read_text())
    lock = json.loads((source/'profile.lock.json').read_text())
    files = {k: Path(v) for k, v in json.loads((source/'files.json').read_text()).items()}
    replay.verify_platform_lock(profile, lock, files)
    assert replay.sha256(Path(replay.__file__)) == profile['env']['paging_replay_sha256']
    decoder, decoder_identity = replay.load_decoder(args.pt_decode_dir, standard_paging=True)
    assert decoder_identity['sha256'] == profile['env']['pt_decode_sha256']
    manifest = json.loads((source/scenario/'samples.manifest.json').read_text())
    seeds, seed_stats = load_corpus(source/scenario/'samples.jsonl', manifest, lock, decoder)
    assert seed_stats['guard_classes'] == len(seeds), '本批要求每个来源守卫类一个代表'
    identities = snapshot([source])
    write_json(out/'readonly-before.json', identities)
    known = list(KNOWN_MISMATCH_RULES)
    if args.known_mismatches is not None:
        supplied = json.loads(args.known_mismatches.read_text())
        known = [item for item in known if not any(
            entry.get('rule') == item['rule'] for entry in supplied)] + supplied
    mismatch_table = MismatchTable(known)
    write_json(out/'known-mismatches.json', known)
    write_json(out/'manifest.json', dict(lock=lock, files={k: str(v) for k, v in files.items()},
        scenario=scenario, seeds=seed_stats, random_seed=args.seed, target=args.count, workers=args.workers,
        paging_fuzz_sha256=replay.sha256(__file__), pt_decode=decoder_identity,
        judge_template_sha256=replay.sha256(source/f'{scenario}-e3/done.json'),
        native_observer_sha256=replay.sha256(source/'nemu_native_observer.so'),
        judge_observer_sha256=replay.sha256(source/'observe.so'),
        excluded_checker_sha256=replay.sha256(source/'check_badread')))
    print('种子清单、lock 与只读快照已核对', flush=True)
    # 原样重判全部种子，外加故意错误的 rd 期望；不把负对照计入正常丢弃。
    success = next(s for s in seeds if s['result']['ctor'] == 'Retire_Success')
    negative = copy.deepcopy(success)
    negative['sample_id'] = max(s['sample_id'] for s in seeds)+1
    negative['post_registers']['x2']['bits'] = f'{decoder.bit_value(success["post_registers"]["x2"], 64)^1:064b}'
    checks, seed_batch = check_batch(seeds+[negative], out/'judge-seeds', source, scenario)
    assert all(membership_reason(checks[s['sample_id']]) is None for s in seeds), '种子原样重判失败'
    assert membership_reason(checks[negative['sample_id']]) == 'inconsistent', 'J1 负对照未检出'
    print(f'种子{len(seeds)}/{len(seeds)}一致；J1错误期望负对照已检出；{seed_batch["seconds"]:.3f}秒', flush=True)
    coverage = Coverage()
    for s in seeds:
        coverage.observe(decoder.decode_sample(s, decoder.Config(False, False, False)))
    seed_coverage = coverage.summary()
    rng = random.Random(args.seed)
    parents = list(seeds)
    rng.shuffle(parents)
    seen = {input_digest(s) for s in seeds}
    accepted, discard_rows, mutation_rows, batches = [], [], [], [seed_batch]
    attempts, generated, batch_number = 0, 0, 0
    while len(accepted) < args.count:
        candidates = []
        while len(candidates) < args.count-len(accepted):
            assert attempts < args.count*20, '变异尝试耗尽；停止而非继续无进展循环'
            parent = parents[attempts % len(parents)]
            operator = OPERATORS[attempts % len(OPERATORS)]
            attempts += 1
            started = time.monotonic()
            try:
                s, decoded, change = mutate(parent, operator, rng, decoder, profile, generated)
            except MutationRejected as error:
                discard_rows.append(dict(operator=operator, stage='platform', reason=str(error),
                                         parent_sample_id=parent['sample_id']))
                continue
            digest = input_digest(s)
            if digest in seen:
                discard_rows.append(dict(operator=operator, stage='dedup', reason='duplicate_input',
                                         parent_sample_id=parent['sample_id']))
                continue
            seen.add(digest)
            change.update(sample_id=generated, input_sha256=digest,
                          prediction_seconds=time.monotonic()-started)
            candidates.append((s, decoded, change))
            mutation_rows.append(change)
            generated += 1
        write_json(out/'mutations.json', mutation_rows)
        write_json(out/'discarded.json', discard_rows)
        checks, batch = check_batch([s for s, decoded, change in candidates],
                                   out/f'judge-mutants-{batch_number:02d}', source, scenario)
        batches.append(batch)
        batch_number += 1
        for s, decoded, change in candidates:
            reason = membership_reason(checks[s['sample_id']])
            if reason is not None:
                discard_rows.append(dict(**change, stage='judge', reason=reason,
                                         membership=checks[s['sample_id']]))
                assert change['operator'] != 'M5', 'M5 蜕变契约失败，停止并保留 C3'
                continue
            case = replay.platform_case(s, decoder, profile, lock['platform_gen_sha256'])
            case['source'] = dict(**change, generation_sha256=lock['platform_gen_sha256'],
                                  seed_samples_sha256=seed_stats['samples_sha256'])
            accepted.append(case)
        print(f'判官批{batch_number}：{len(candidates)}例，累计接纳{len(accepted)}，'
              f'{batch["seconds"]:.3f}秒', flush=True)
    write_json(out/'discarded.json', discard_rows)
    write_json(out/'judge-batches.json', batches)
    write_json(out/'accepted.json', accepted)
    tasks = [(case, out/'replay'/f'mutant-{i:04d}', files, source/'nemu_native_observer.so')
             for i, case in enumerate(accepted)]
    results, feedback = [], []
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for case, result in zip(accepted, pool.map(replay_one, tasks)):
            mismatch = not result['agree'] or result['observation']['isla_consistent_side'] != 'both'
            record = coverage.observe(case['decoded'], mismatch=mismatch)
            record.update(sample_id=case['sample']['sample_id'], source=case['source'])
            if mismatch:
                record['mismatch'] = mismatch_table.record(case, result['observation'], result['id'])
            feedback.append(record)
            results.append(result)
            write_json(out/'replay-results.json', results)
            write_json(out/'feedback.json', feedback)
            write_json(out/'mismatches.json', mismatch_table.summary())
            if len(results) % 20 == 0:
                print(f'重放{len(results)}/{args.count}；桶{dict(Counter(r["bucket"] for r in results))}', flush=True)
    replay_seconds = time.monotonic()-started
    # N3 型重放负对照：成功样本仅翻转 ELF 的 rd 或写后内存期望一位。
    negative_case = replay.platform_case(success, decoder, profile, lock['platform_gen_sha256'])
    negative_reason = 'rd' if negative_case['access'] == 'load' else 'memory'
    if negative_reason == 'rd':
        negative_case['expected']['rd'] ^= 1
    else:
        physical = negative_case['decoded']['paddr_if_success']
        word = next(w for w in negative_case['writes'] if w['address'] == physical)
        word['expected_value'] ^= 1
    negative_case['source'] = dict(negative_control='N3', parent_sample_id=success['sample_id'])
    n3 = replay_one((negative_case, out/'negative-N3', files, source/'nemu_native_observer.so'))
    assert n3['bucket'] == 'xs!=expected' and n3['reason'] == negative_reason, 'N3 型负对照未检出'
    replay.verify_platform_lock(profile, lock, files)
    assert snapshot([source]) == identities, '旧产物发生变化'
    write_json(out/'coverage.json', coverage.export())
    summary = dict(status='完成', scenario=scenario, seeds=seed_stats, target=args.count, attempts=attempts,
        generated=generated, replayed=len(results), operators=dict(Counter(
            c['source']['operator'] for c in accepted)),
        judge_discards=dict(Counter(r['reason'] for r in discard_rows if r['stage'] == 'judge')),
        discards=dict(Counter(r['stage']+':'+r['reason'] for r in discard_rows)),
        discard_total=len(discard_rows), seed_coverage=seed_coverage,
        final_coverage=coverage.summary(), would_admit=sum(r['would_admit'] for r in feedback),
        buckets=dict(Counter(r['bucket'] for r in results)), mismatch=mismatch_table.summary(),
        judge_batches=[dict(count=b['count'], seconds=b['seconds'],
                           seconds_per_sample=b['seconds_per_sample'],
                           excluded_filtered_paths=b['excluded_filtered_paths']) for b in batches],
        replay_seconds=replay_seconds, replay_samples_per_second=len(results)/replay_seconds,
        replay_elapsed_sum=sum(r['elapsed'] for r in results),
        negative_judge='inconsistent', negative_replay=dict(bucket=n3['bucket'], reason=n3['reason']),
        readonly_unchanged=True)
    write_json(out/'summary.json', summary)
    print(canonical(summary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('output/ecfg3'))
    parser.add_argument('--out', type=Path, required=True, help='output/fuzz-p1 或 output/fuzz-p1b 下的新目录')
    parser.add_argument('--pt-decode-dir', type=Path, required=True)
    parser.add_argument('--known-mismatches', type=Path)
    parser.add_argument('--scenario', choices=SCENARIOS, default='sv39-load')
    parser.add_argument('--count', type=int, default=500)
    parser.add_argument('--seed', type=int, default=20261107)
    parser.add_argument('--workers', type=int, default=8)
    campaign(parser.parse_args())


if __name__ == '__main__':
    main()
