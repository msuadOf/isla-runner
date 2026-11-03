#!/usr/bin/env python3
"""独立复核四份生成记录、同源关系与目标IR控制分支。"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GEN = HERE.parent / 'implementation/generation'
MODEL = ROOT / '.worktree/runner-float/sail-riscv'
TEST = ROOT / 'isla/test/float_ir/check_explicit_semantic_branches.py'
KINDS = ['rv64d_v128_e64', 'rv32d', 'rv64d_v256_e64', 'rv64d_v512_e64']
NAMES = ['zfp_min_pure', 'zfp_max_pure', 'zfp_minm_pure', 'zfp_maxm_pure',
         'zriscv_f32_symbolic_bits', 'zfp_class_onehot_pure', 'zvalid_fp_op',
         'zillegal_fp_normal', 'zillegal_fp_reduction', 'zexecute']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def normalized_functions(text):
    result = {}
    for name, formals, body in re.findall(r'(?ms)^fn ([^(\n]+)\(([^\n]*)\) \{\n(.*?)^\}', text):
        body = re.sub(r'`\d+(?: \d+:\d+(?:-\d+:\d+)?)?', '', body)
        body = re.sub(r'([\w./-]+\.sail):\d+\.\d+-\d+\.\d+', r'\1:LOC', body)
        replacements = {formal.strip(): '__arg' + str(index) for index, formal in enumerate(formals.split(',')) if formal.strip()}
        def rename(match):
            token = match.group()
            if token not in replacements:
                replacements[token] = '__local' + str(len(replacements))
            return replacements[token]
        tokens = '|'.join(re.escape(token) for token in replacements)
        pattern = r'(?<![A-Za-z0-9_$])(?:zz[0-9]+' + ('|' + tokens if tokens else '') + r')(?![A-Za-z0-9_$])'
        body = re.sub(pattern, rename, body)
        result[name] = body
    return result


def main():
    expected = json.loads((HERE / 'source-evidence.json').read_text())
    assert all(sha(MODEL / name) == digest for name, digest in expected['source_sha256'].items())
    result = {'model_commit': subprocess.check_output(['git', '-C', str(MODEL), 'rev-parse', 'HEAD'], text=True).strip(),
              'test_sha256': sha(TEST), 'configurations': {}}
    source_sets = []
    baseline = normalized_functions((ROOT / 'agents/branch_ablation_official_z3_20261102/inputs/minmax/A.ir').read_text())
    for kind in KINDS:
        directory = GEN / kind
        record = json.loads((directory / 'generation.json').read_text())
        driver = json.loads((directory / 'driver.json').read_text())
        ir = directory / (kind + '.ir')
        assert record['exit_code'] == driver['exit_code'] == 0
        assert driver['source_unchanged']
        assert record['model_commit'] == driver['model_commit'] == result['model_commit']
        assert record['model_files'] == driver['model_files']
        assert all(sha(MODEL / 'model' / name) == digest for name, digest in record['model_files'].items())
        source_sets.append(record['model_files'])
        command = record['command']
        for flag in ['-isla', 'SYMBOLIC', '--strict-var', '--strict-bitvector', '--strict-exponentials', '--all-modules']:
            assert flag in command
        for flag, key in [('--config', 'config_sha256'), ('-plugin', 'plugin_sha256')]:
            assert sha(Path(command[command.index(flag) + 1])) == record[key] == driver[key]
        assert sha(Path(command[0])) == record['sail_launcher_sha256'] == driver['sail_launcher_sha256']
        assert sha(ir) == record['ir_sha256'] == driver['ir_sha256']
        text = ir.read_text()
        candidate = normalized_functions(text)
        changed = sorted(name for name in baseline.keys() | candidate.keys() if baseline.get(name) != candidate.get(name)) if kind == 'rv64d_v128_e64' else None
        functions = dict(re.findall(r'(?ms)^fn ([^(\n]+)\([^\n]*\) \{\n(.*?)^\}', text))
        files = shlex.split(re.search(r'(?m)^files (.*)$', text).group(1))
        stdlib = {}
        for name in files:
            if name.startswith('/') and '/lib/' in name:
                path = Path(name)
                assert path.exists(), name
                stdlib[name] = sha(path)
        command_test = ['python3', str(TEST), '--ir', str(ir)]
        checked = subprocess.run(command_test, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert checked.returncode == 0, checked.stdout
        mask = {}
        instructions = [line.strip() for line in functions['zexecute'].splitlines() if line.strip()]
        for source, start_line, label in [('extensions/V/vext_fp_insts.sail', 67, 'FVVTYPE'),
                                           ('extensions/V/vext_fp_red_insts.sail', 62, 'RFVVTYPE')]:
            sid = files.index(source)
            entries = [(pc, line) for pc, line in enumerate(instructions)
                       if re.search(r'`' + str(sid) + ' ' + str(start_line) + r':4-\d+:\d+;', line)
                       and re.match(r'jump \w+ goto \d+', line)]
            assert len(entries) == 1
            pc, line = entries[0]
            active = int(re.search(r'goto (\d+)', line).group(1))
            join = int(re.search(r'goto (\d+)', instructions[pc + 2]).group(1))
            mask[label] = {'branch_pc': pc, 'instruction': line, 'active_pc': active, 'join_pc': join,
                           'condition_definition': instructions[pc - 1],
                           'inactive_path': instructions[pc + 1:pc + 3],
                           'active_operation_calls': [{'pc': i, 'instruction': instruction}
                                                      for i, instruction in enumerate(instructions[active:join], active)
                                                      if re.search(r'= zfp_\w+_pure\(', instruction)]}
        result['configurations'][kind] = {'ir': relative(ir), 'ir_sha256': sha(ir), 'model_source_count': len(record['model_files']),
            'record': relative(directory / 'generation.json'), 'config_sha256': record['config_sha256'],
            'plugin_sha256': record['plugin_sha256'], 'actual_stdlib_filetable_sha256': stdlib,
            'normalized_changed_functions_from_old_v128': changed,
            'target_jump_counts': {n: len(re.findall(r'(?m)^\s*jump\b', functions[n])) for n in NAMES},
            'mask_cfg': mask, 'test_command': command_test, 'test_exit_code': checked.returncode, 'test_output': checked.stdout}
    assert all(source == source_sets[0] for source in source_sets)
    ordinary = json.loads((GEN / 'ordinary-strict/driver.json').read_text())
    assert ordinary['exit_code'] == 0 and ordinary['source_unchanged']
    assert ordinary['model_files'] == source_sets[0]
    result['ordinary_strict'] = {'exit_code': ordinary['exit_code'], 'record': relative(GEN / 'ordinary-strict/driver.json')}
    result['pass'] = True
    (HERE / 'ir-artifact-audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print('PASS: 四配置来源/哈希/同源和真实分支CFG，普通strict均通过')


if __name__ == '__main__':
    main()
