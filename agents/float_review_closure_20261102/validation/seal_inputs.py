#!/usr/bin/env python3
"""由四份真实生成记录封存64受影响/13兼容完整域批次输入。"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NAMES = ('rv64d_v128_e64', 'rv32d', 'rv64d_v256_e64', 'rv64d_v512_e64')


def entry(path):
    return {'path': str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True)
    parser.add_argument('--generation', default='model-8ad5e8e')
    parser.add_argument('--template', type=Path, default=HERE / 'inputs.template.json')
    parser.add_argument('--affected', type=Path,
                        help='候选模型独立静态调用闭包；不复用旧模型清单')
    args = parser.parse_args()
    output = HERE / ('inputs.' + args.batch + '.json')
    generation = HERE / 'generation' / args.generation
    data = json.loads(args.template.read_text())
    source = json.loads((generation / 'source.json').read_text())
    data['model_commit'] = source['commit']
    data['model_tree']['path'] = source.get('model_tree', data['model_tree']['path'])
    for key, name in (('model_tree', 'model-tree.json'), ('isla_tree', 'isla-source-tree.json')):
        data[key]['manifest'] = entry(generation / name)
    if args.affected is not None:
        closure = json.loads(args.affected.read_text())
        affected = set(closure['affected_clauses'])
        assert closure['model_commit'] == data['model_commit']
        assert closure['isla_commit'] == data['isla_commit']
        assert closure['affected_count'] == len(affected)
        assert affected <= set(data['jobs'])
        for clause, row in data['jobs'].items():
            row['scope'] = 'affected' if clause in affected else 'compatibility'
        data['affected_manifest'] = entry(args.affected.resolve(strict=True))
    data['configs']['rv64-fd-full'] = entry(ROOT / '.worktree/runner-float/isla/configs/riscv64_difftest_fd.toml')
    for name in NAMES:
        folder = generation / name
        record = json.loads((folder / 'driver.json').read_text())
        assert record['exit_code'] == 0 and record['source_unchanged'] is True
        assert record['model_commit'] == data['model_commit']
        ir = folder / (name + '.ir')
        item = entry(ir)
        assert item['sha256'] == record['ir_sha256']
        key = {'rv64d_v128_e64': 'rv64-v128', 'rv32d': 'rv32-default',
               'rv64d_v256_e64': 'rv64-v256', 'rv64d_v512_e64': 'rv64-v512'}[name]
        data['irs'][key] = item
    # 正式默认rv64d使用同一rv64d.json配置，当前生产五IR中的两份原本同字节。
    data['irs']['rv64-default'] = dict(data['irs']['rv64-v128'])
    data['ir_aliases'] = {'rv64-default': 'rv64-v128'}
    data['z3'] = entry(Path('/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3.4.0'))
    assert data['z3']['sha256'] == '899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970'
    for key in ('binary', 'binary_manifest', 'watchdog_evidence', 'affected_manifest', 'seed_preload'):
        old = data[key]
        item = entry(ROOT / old['path'])
        assert item['sha256'] == old['sha256'], key
    assert len(data['jobs']) == 77 and sum(x['scope'] == 'affected' for x in data['jobs'].values()) == 64
    with output.open('x') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write('\n')
    print(output, hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
