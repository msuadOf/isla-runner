#!/usr/bin/env python3
"""E2 Sv39/Sv48 LOAD/STORE 成员复验及 emu/独立 NEMU 回放；最多八路 emu。"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import time

import paging_fuzz as fuzz
import paging_replay as replay


def read_json(path):
    return json.loads(path.read_text())


def scenario_profile(original, scenario, *, va_values=None, va_domain=None, instructions=None):
    mode, access = scenario.split('-')
    assert scenario in fuzz.SCENARIOS
    profile = copy.deepcopy(original)
    domain = dict(privilege_domain=['User', 'Supervisor'],
                  mstatus_mask='0xfffffffffff3ffff', mstatus_value='0x0000000a00000000',
                  satp_modes=[{'sv39': 8, 'sv48': 9}[mode]], access=access)
    previous = original['isla'].get('scenario', {})
    if isinstance(previous, dict):
        for key in ('va', 'va_values', 'va_domain', 'instructions'):
            if key in previous:
                domain[key] = copy.deepcopy(previous[key])
    if va_values is not None or va_domain is not None:
        for key in ('va', 'va_values', 'va_domain'):
            domain.pop(key, None)
        if va_values is not None:
            domain['va_values'] = list(va_values)
        if va_domain is not None:
            domain['va_domain'] = copy.deepcopy(va_domain)
    if instructions is not None:
        domain['instructions'] = list(instructions)
    profile['isla']['scenario'] = domain
    profile['csr_init'].pop('mstatus', None)
    profile['csr_init'].update(mstatus_mask=domain['mstatus_mask'],
                              mstatus_value=domain['mstatus_value'], entry_mode='mprv')
    return profile


def bound_template(template, files, scenario, scenario_config=None):
    """绑定 IR/config/指令；地址前态由 check-samples 的具体样本绑定。"""
    command = list(template)
    mode, access = scenario.split('-')
    for flag, key in [('-A', 'ir'), ('-C', 'config')]:
        if Path(command[command.index(flag)+1]).resolve() != files[key].resolve():
            raise ValueError(f'成员检查 {flag} 与本场景 {key} 不符')
    domain = scenario_config or {}
    word = int(command[command.index('--instruction-bits')+1], 0)
    if (not 0 <= word < 1 << 32 or word & 0x707f != {'load': 0x3003, 'store': 0x3023}[access]
            or ('instructions' in domain and word not in
                [replay.integer(value) for value in domain['instructions']])):
        raise ValueError('成员检查指令与本场景不符')
    if [arg for arg in command if arg.startswith('--clause=')] != [f'--clause={access.upper()}']:
        raise ValueError('成员检查 clause 与本场景不符')
    prestate = dict(command[i+1].split('=', 1) for i, arg in enumerate(command)
                    if arg == '--prestate')
    if {'cur_privilege', 'mstatus'} & prestate.keys():
        raise ValueError('符号前态不能送回固定特权或 mstatus 命令')
    if 'satp' in prestate and int(prestate['satp'], 0) >> 60 != {'sv39': 8, 'sv48': 9}[mode]:
        raise ValueError('成员检查 SATP 与本场景不符')
    base = (word >> 15) & 31
    immediate = word >> 20 if access == 'load' else ((word >> 25) << 5) | ((word >> 7) & 31)
    offset = immediate - 4096 if immediate & 2048 else immediate
    if base == 0 or f'x{base}' in prestate:
        value = 0 if base == 0 else int(prestate[f'x{base}'], 0)
        replay.validate_address((value + offset) & ((1 << 64)-1), domain)
    # 旧模板保存的是上一轮的生成约束；复验必须恢复符号地址前态，
    # 具体的 GPR、SATP 和页表字节由 samples v1 输入提供。
    return replay.symbolic_address_template(command)


def scenario_inputs(experiment, scenario):
    # 保留上一轮 sym-prestate 布局；新批次显式选择 serial64 的完整 Sv48 LOAD。
    if (experiment/'E2/samples.jsonl').exists() and scenario == 'sv39-load':
        return experiment/'E2/samples.jsonl', experiment/'E2-check/done.json', experiment/'E2.toml'
    group = experiment/'serial64' if scenario == 'sv48-load' else experiment
    return (group/f'{scenario}-export/samples.jsonl', group/f'{scenario}-check/done.json',
            group/'E2.toml')


def observer_source(original, symbols):
    ranges = {}
    for name in ('read_symbolic', 'write_symbolic'):
        matches = [line.split() for line in symbols.splitlines()
                   if line.endswith('isla_lib::memory::Memory<B>::'+name)]
        if len(matches) != 1:
            raise ValueError(f'必须有唯一的 Memory::{name} 符号，拒绝猜测观察地址')
        address, size = (int(value, 16) for value in matches[0][:2])
        assert size > 0
        ranges[name] = [address, address+size]
    conditions = ' || '.join(f'(offset >= {low:#x} && offset < {high:#x})'
                            for low, high in ranges.values())
    updated, count = re.subn(r'if \(\(offset >= .*?\)\) return 1;',
                            f'if ({conditions}) return 1;', original)
    assert count == 1
    return updated, ranges


def membership_observer(source, isarch, directory):
    """仅适配查询观察地址；不修改 Z3 查询或排除区证明条件。"""
    directory.mkdir()
    symbols = subprocess.run(['nm', '-S', '-C', str(isarch)], check=True,
                             capture_output=True, text=True).stdout
    code, ranges = observer_source((source/'observe.c').read_text(), symbols)
    (directory/'observe.c').write_text(code)
    command = ['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-o',
               str(directory/'observe.so'), str(directory/'observe.c'), '-ldl']
    subprocess.run(command, check=True, capture_output=True, text=True)
    fuzz.write_json(directory/'build.json', dict(command=command, isarch=str(isarch),
        ranges=ranges, source=str(source/'observe.c'),
        change='only read_symbolic/write_symbolic function address ranges'))
    return directory/'observe.so'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, required=True, help='sym-prestate 产物根目录，只读')
    parser.add_argument('--platform-source', type=Path, required=True, help='ecfg4b 产物根目录，只读')
    parser.add_argument('--decoder', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=8, choices=range(1, 9))
    parser.add_argument('--scenario', choices=fuzz.SCENARIOS, default='sv39-load')
    parser.add_argument('--va', action='append', type=lambda v: int(v, 0),
                        help='允许的 VA，可重复；省略时沿用 profile 地址域')
    parser.add_argument('--va-domain', type=json.loads,
                        help='JSON 地址域：base/size 和/或 mask/value')
    args = parser.parse_args()
    experiment, source, out = (p.resolve() for p in
                               (args.experiment, args.platform_source, args.output))
    out.mkdir(parents=True, exist_ok=False)
    for name in ('tmp', 'cache'):
        (out/name).mkdir()
    os.environ.update(TMPDIR=str(out/'tmp'), XDG_CACHE_HOME=str(out/'cache'),
                      PYTHONDONTWRITEBYTECODE='1')
    start = time.monotonic()
    decoder, decoder_record = replay.load_decoder(args.decoder, standard_paging=True)
    profile = scenario_profile(read_json(source/'profile.json'), args.scenario,
                               va_values=args.va, va_domain=args.va_domain)
    scenario = profile['isla']['scenario']
    corpus, template_path, config = scenario_inputs(experiment, args.scenario)
    template = read_json(template_path)['command']
    files = {k: Path(v) for k, v in read_json(source/'files.json').items()}
    ir = experiment/'rv64d-us.ir' if template_path.parent.name == 'E2-check' else files['ir']
    files.update(config=config, ir=ir, isarch=Path(template[0]))
    template = bound_template(template, files, args.scenario, scenario)
    # 已知 IR 身份沿用来源记录；新配置只记录一次，不用哈希代替成员复验。
    if template_path.parent.name == 'E2-check':
        profile['ir']['ir_sha256'] = replay.sha256(files['ir'])
    profile['ir']['input_constraint'] = 'cur_privilege in {User,Supervisor}; SUM/MXR symbolic in E2.toml'
    # 本轮 isarch 来自实际模板；不能将 ecfg4b 的旧二进制身份写成它的身份。
    profile['isla'].pop('isarch_sha256', None)
    profile['isla']['config_toml_sha256'] = replay.sha256(files['config'])
    profile['env'].update(pt_decode_sha256=decoder_record['sha256'],
        paging_replay_sha256=replay.sha256(Path(replay.__file__)))
    gen, env_hash = replay.platform_hashes(profile)
    lock = dict(schema_version=2, platform_gen_sha256=gen, platform_env_sha256=env_hash,
        ir_sha256=profile['ir']['ir_sha256'], config_toml_sha256=profile['isla']['config_toml_sha256'],
        emu_sha256=profile['env']['emu_sha256'], nemu_sha256=profile['env']['nemu_sha256'])
    for name, value in [('profile.json', profile), ('profile.lock.json', lock),
                        ('files.json', {k: str(v) for k, v in files.items()})]:
        fuzz.write_json(out/name, value)
    samples = [json.loads(line) for line in corpus.read_text().splitlines()]
    assert samples, '场景语料不能为空'
    assert len({s['sample_id'] for s in samples}) == len(samples)
    fuzz.write_json(out/'manifest.json', dict(lock=lock, scenario=args.scenario,
        samples_file=str(corpus), count=len(samples), judge_source=str(template_path),
        binary_provenance='emu/NEMU hashes from ecfg4b; actual isarch path from judge template; no binary hash gate',
        semantic_gates=['U/S domain', 'mstatus mask/value (only SUM/MXR free)',
            'scenario SATP mode/instruction/effective VA; root from sample SATP',
            'empty TLB', 'PTE/PMA/memory/harness checks',
            'C3 result/post_registers/post_memory equality', 'unique consistent membership',
            'exact emu exit and independent unguided NEMU exit']))
    cases, c3, contexts = [], [], Counter()
    for sample in samples:
        memory = decoder.memory_bytes(sample['pre_memory'], allow_unknown=True)
        predicted, decoded = fuzz.predict_sample(sample, memory, decoder, profile, sample['sample_id'])
        # 按字段比较预测结果；不以文件身份代替语义检查。
        differences = [key for key in ('result', 'post_registers')
                       if predicted[key] != sample[key]]
        if decoder.memory_bytes(predicted['post_memory']) != decoder.memory_bytes(sample['post_memory']):
            differences.append('post_memory')
        if differences:
            c3.append(dict(sample_id=sample['sample_id'], fields=differences))
        case = replay.platform_case(sample, decoder, profile, gen)
        case['source'] = dict(sample_id=sample['sample_id'], class_id=sample['class_id'],
                             path_signature=sample['path_signature'], experiment='E2')
        context = case['prestate_context']
        contexts[(context['privilege'], context['sum'], context['mxr'])] += 1
        cases.append(case)
    fuzz.write_json(out/'c3.json', dict(total=len(samples), differences=c3,
        contexts=[dict(privilege=p, sum=s, mxr=m, count=n) for (p, s, m), n in contexts.items()]))
    assert not c3, 'C3 逐字段结果不同，保留输入并停止'
    fuzz.write_json(out/'judge-template.json', dict(command=template))
    proof_observer = membership_observer(source, files['isarch'], out/'membership-observer')
    print(f'C3 {len(samples)}/{len(samples)}；开始实际 E2 IR/config 的具体输入成员复验', flush=True)
    checks, batch = fuzz.check_batch([c['sample'] for c in cases], out/'membership', source, args.scenario,
        judge_template=out/'judge-template.json', scenario_config=scenario,
        proof_observer=proof_observer)
    assert all(fuzz.membership_reason(checks[s['sample_id']]) is None for s in samples)
    fuzz.write_json(out/'membership-summary.json', dict(total=len(checks), accepted=len(checks),
        raw_returncode=batch['returncode'], excluded_filtered_paths=batch['excluded_filtered_paths']))
    print(f'成员复验 {len(checks)}/{len(samples)}；开始 {args.jobs} 路 emu/独立 NEMU', flush=True)
    observer = source/'nemu_native_observer.so'
    files.update(nemu_sha256=profile['env']['nemu_sha256'], observer_sha256=replay.sha256(observer))
    results, mismatches, failures = [], [], []
    table = fuzz.MismatchTable(fuzz.KNOWN_MISMATCH_RULES)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(fuzz.replay_one, (case, out/'replay'/f"entry-{case['source']['sample_id']:04d}",
                    files, observer)): case for case in cases}
        for future in as_completed(futures):
            case = futures[future]
            try:
                result = future.result()
            except Exception as error:
                failures.append(dict(sample_id=case['source']['sample_id'], error=repr(error)))
                fuzz.write_json(out/'failures.json', failures)
                print(f"基础设施失败 {case['source']['sample_id']}: {error}", flush=True)
                continue
            results.append(result)
            observation = result['observation']
            agree = result['agree'] and observation['isla_consistent_side'] == 'both'
            if not agree:
                classified = table.record(case, observation, result['id'])
                row = dict(sample_id=case['source']['sample_id'], isla_cause=case['expected']['cause'],
                    xs_cause=observation['xs_cause'], nemu_cause=observation['nemu_cause'],
                    bucket=result['bucket'], **classified,
                    input=str(out/'replay'/result['id']/'case.json'))
                mismatches.append(row)
                fuzz.write_json(out/'mismatches.json', mismatches)
            if len(results) % 50 == 0 or not agree:
                progress = dict(completed=len(results), total=len(samples), mismatch=len(mismatches),
                                failures=len(failures), seconds=time.monotonic()-start)
                fuzz.write_json(out/'progress.json', progress)
                print(f"{args.scenario} 完成 {len(results)}/{len(samples)}；mismatch={len(mismatches)}；失败={len(failures)}", flush=True)
    results.sort(key=lambda r: r['source']['sample_id'])
    mismatches.sort(key=lambda r: r['sample_id'])
    summary = dict(scenario=args.scenario, total=len(samples), completed=len(results), agree=len(results)-len(mismatches),
        mismatch=len(mismatches), classified=sum(m['filtered'] for m in mismatches),
        new_differences=sum(not m['filtered'] for m in mismatches), infrastructure_failures=failures,
        buckets=dict(Counter(r['bucket'] for r in results)), seconds=time.monotonic()-start,
        jobs=args.jobs, rules=table.summary())
    for name, value in [('results.json', results), ('mismatches.json', mismatches),
                        ('summary.json', summary)]:
        fuzz.write_json(out/name, value)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
