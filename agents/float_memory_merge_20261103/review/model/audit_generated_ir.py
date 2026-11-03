#!/usr/bin/env python3
"""独立回读合流模型的 ordinary/四配置生成及五 IR 安装来源。"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
CANDIDATE = ROOT / '.worktree/merge-float-memory-20261104'
MODEL = CANDIDATE / 'sail-riscv'
ISLA = CANDIDATE / 'isla'
EXPECTED = 'bf861b3e687894480aec701a886a38d4e50b8a99'
KINDS = {
    'rv64d_v128_e64': ('rv64d.json', ['rv64d.ir', 'ir/rv64d_v128_e64.ir']),
    'rv32d': ('rv32d.json', ['rv32d.ir']),
    'rv64d_v256_e64': ('rv64d_v256_e64.json', ['ir/rv64d_v256_e64.ir']),
    'rv64d_v512_e64': ('rv64d_v512_e64.json', ['ir/rv64d_v512_e64.ir']),
}
STRICT = {'--strict-var', '--strict-bitvector', '--strict-exponentials', '--all-modules'}
PRESERVE = {'encdec_compressed_forwards', 'encdec_compressed_forwards_matches',
            'encdec_compressed_backwards', 'encdec_compressed_backwards_matches',
            'get_F', 'set_F', 'set_V', 'riscv_f16ToI16', 'riscv_f16ToUi16',
            'riscv_f32ToI16', 'riscv_f32ToUi16'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def functions(text):
    result = {}
    for name, args, body in re.findall(r'(?ms)^fn ([^\n(]+)\(([^\n]*)\) \{\n(.*?)^\}', text):
        parameters = {p.strip(): f'PARAM{i}' for i, p in enumerate(args.split(',')) if re.fullmatch(r'z3zE\d+', p.strip())}
        body = re.sub(r'\bz3zE\d+\b', lambda m: parameters.get(m[0], m[0]), body)
        body = re.sub(r'`[^;\n]*', '', body)
        result[name] = re.sub(r'\s+', '', body)
    return result

def check_ir_contract(ir, config_kind):
    old_path = ROOT / '.worktree/runner-float/isla' / KINDS[config_kind][1][0]
    old, new = functions(old_path.read_text()), functions(ir.read_text())
    memory_path = ROOT / '.worktree/runner-memory/isla' / KINDS[config_kind][1][0]
    memory = functions(memory_path.read_text())
    assert new['zget_start_element'] == memory['zget_start_element']
    assert re.search(r'^val zget_start_element : \(%unit\) ->\s+%i$', ir.read_text(), re.M)
    preserved = []
    source_paths = ['model/core/ieee_fp_exceptions.sail', 'model/extensions/V/vext_fp_utils_insts.sail',
                    *[f'model/extensions/FD/softfloat_symbolic_f{w}.sail' for w in (16, 32, 64)],
                    'model/extensions/FD/fdext_regs.sail']
    names = {name for p in source_paths for name in re.findall(r'^function (\w+)\(', (MODEL / p).read_text(), re.M)}
    for name in sorted(names):
        encoded = 'z' + name
        assert (encoded in old) == (encoded in new), name
        if encoded in new:
            assert old[encoded] == new[encoded], (config_kind, name)
            preserved.append(name)
    return {'get_start_element_equals_memory_direct_nat_helper': True,
            'float_pure_data_NaN_and_OPEN_helper_bodies_unchanged': preserved,
            'normalization': '仅删除源坐标、空白与按位置重命名生成参数；保留表达式及分支'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', default='merge-bf861b3e-20261104')
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args()
    stage = CANDIDATE / 'agents/float_memory_merge_20261103/validation/generation' / args.batch
    source = read(stage / 'source.json')
    signed = read(Path(__file__).with_name('source-union-independent.json'))
    assert source['commit'] == EXPECTED
    assert subprocess.check_output(['git', '-C', str(MODEL), 'rev-parse', 'HEAD'], text=True).strip() == EXPECTED
    files = {r['file'].removeprefix('model/'): r['sha256'] for r in signed['model_files']}
    assert len(files) == 166 and source['model_files'] == files
    assert all(sha(MODEL / 'model' / p) == h for p, h in files.items())
    tools = source['tool_files_pre']
    assert all(sha(Path(p)) == h for p, h in tools.items())
    assert sha(Path(source['compile_z3_path'])) == source['compile_z3_sha256']
    assert tools[source['sail_path']] == source['sail_sha256']
    assert tools[source['plugin_path']] == source['plugin_sha256']
    assert tools[str(ISLA / 'scripts/regenerate_ir.py')] == source['driver_sha256']
    rows = []
    installed = {}
    for kind in ['ordinary-strict', *KINDS]:
        directory = stage / kind
        driver = read(directory / 'driver.json')
        assert driver['exit_code'] == 0
        assert driver['model_commit'] == EXPECTED and driver['model_files'] == files
        assert driver['source_unchanged'] and driver['tool_files_unchanged'] and driver['compile_z3_unchanged']
        assert driver['tool_files_pre'] == tools
        assert driver['actual_sail_binary'] == source['actual_sail_binary']
        assert driver['live_executables'][source['actual_sail_binary']] == tools[source['actual_sail_binary']]
        assert driver['compile_z3_live_hash_matches'] is True, '本批未使用memo，须有实际编译Z3来源'
        assert driver['live_executables'][source['compile_z3_path']] == source['compile_z3_sha256']
        assert driver['memo_copy'] is None, '本批来源合同采用全新memo'
        config_name = 'rv64d.json' if kind == 'ordinary-strict' else KINDS[kind][0]
        config = ISLA / 'ir/provenance' / config_name
        assert driver['config_sha256'] == sha(config) == tools[str(config)]
        if kind == 'ordinary-strict':
            command = driver['command']
            assert '--just-check' in command and '-D' not in command and 'SYMBOLIC' not in command
            ir_hash = None
        else:
            gen = read(directory / 'generation.json')
            assert gen['exit_code'] == 0 and gen['model_commit'] == EXPECTED
            assert gen['model_files'] == files and gen['config_sha256'] == sha(config)
            assert gen['plugin_sha256'] == source['plugin_sha256'] and gen['sail_launcher_sha256'] == source['sail_sha256']
            command = gen['command']
            assert command[0] == source['sail_path'] and command[command.index('-plugin') + 1] == source['plugin_path']
            assert command[command.index('-D') + 1] == 'SYMBOLIC' and '-isla' in command
            assert {command[i + 1] for i, word in enumerate(command) if word == '--isla-preserve'} == PRESERVE
            assert command[command.index('--isla-output-dir') + 1] == str(directory)
            assert command[command.index('-o') + 1] == kind
            ir = directory / (kind + '.ir')
            ir_hash = sha(ir)
            assert driver['ir_sha256'] == gen['ir_sha256'] == ir_hash
            contract = check_ir_contract(ir, kind)
            if args.installed:
                for path in KINDS[kind][1]:
                    assert sha(ISLA / path) == ir_hash
                    installed[path] = ir_hash
        assert STRICT.issubset(command)
        assert command[command.index('--require-version') + 1] == '0.20.1'
        assert command[command.index('--config') + 1] == str(config)
        assert command[command.index('--memo-z3-path') + 1] == str(directory / 'sail_smt_cache')
        rows.append({'kind': kind, 'seconds': driver['seconds'], 'exit_code': 0,
                     'driver_sha256': sha(directory / 'driver.json'), 'ir_sha256': ir_hash,
                     'live_sail_and_compile_z3_hashes_verified': True,
                     'ir_helper_contract': contract if kind != 'ordinary-strict' else None})
    audit = read(stage / 'independent-input-audit.json')
    assert audit['model_commit'] == EXPECTED and audit['tracked_model_files'] == files
    assert audit['tool_files'] == tools and audit['source_unchanged_now'] and audit['tool_ctime_precedes_generation_start']
    assert audit['generation_start_source_manifest_sha256'] == sha(stage / 'source.json')
    if args.installed:
        manifest = read(ISLA / 'ir/provenance/manifest.json')
        assert manifest['model_commit'] == EXPECTED and manifest['model_dirty'] is False
        assert manifest['sail_binary_sha256'] == tools[source['actual_sail_binary']]
        assert manifest['sail_launcher_sha256'] == source['sail_sha256']
        assert manifest['plugin_sha256'] == source['plugin_sha256']
        assert manifest['generation_audit']['sha256'] == sha(stage / 'independent-input-audit.json')
        assert len(manifest['artifacts']) == 4
        manifest_paths = set()
        for artifact in manifest['artifacts']:
            assert artifact['model_files'] == {p: {'sha256': h} for p, h in files.items()}
            assert artifact['config_sha256'] == sha(ISLA / 'ir/provenance' / artifact['config'])
            for p in artifact['paths']:
                assert installed[p] == artifact['sha256']
                assert p not in manifest_paths
                manifest_paths.add(p)
        assert manifest_paths == set(installed)
        assert len(installed) == 5 and installed['rv64d.ir'] == installed['ir/rv64d_v128_e64.ir']
    result = {'status': 'PASS 本轮实际严格生成与来源' + ('及五IR安装' if args.installed else ''),
              'scope': '来源和严格生成；不含永久回归、动态预算或全域语义', 'model_commit': EXPECTED,
              'batch': str(stage.relative_to(ROOT)), 'source_manifest_sha256': sha(stage / 'source.json'),
              'model_files': len(files), 'tool_files': len(tools), 'generation': rows, 'installed_irs': installed}
    out = Path(__file__).with_name('generated-ir-independent' + ('-installed' if args.installed else '') + '.json')
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'generation'},
                      'generation': [{k: v for k, v in r.items() if k != 'ir_helper_contract'} |
                                     {'unchanged_float_helpers': len(r['ir_helper_contract']['float_pure_data_NaN_and_OPEN_helper_bodies_unchanged'])
                                      if r['ir_helper_contract'] else None} for r in rows]}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
