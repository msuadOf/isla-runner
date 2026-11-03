#!/usr/bin/env python3
"""固定或复核候选子仓的全部已跟踪源码哈希。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

GENERATED = {'rv64d.ir', 'rv32d.ir', 'ir/rv64d_v128_e64.ir',
             'ir/rv64d_v256_e64.ir', 'ir/rv64d_v512_e64.ir',
             'ir/provenance/manifest.json'}


def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(tree, isla_source):
    if git(tree, 'ls-files', '-u'):
        raise ValueError('源码仍有未解决的合并项')
    names = [item.decode() for item in git(tree, 'ls-files', '-z').split(b'\0') if item]
    if isla_source:
        names = [name for name in names if name not in GENERATED]
    return {'root': str(tree), 'head': git(tree, 'rev-parse', 'HEAD').decode().strip(),
            'scope': 'isla-source-excluding-generated-ir' if isla_source else 'all-tracked',
            'files': {name: sha(tree / name) for name in names}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--isla-source', action='store_true')
    parser.add_argument('--compare', action='store_true')
    args = parser.parse_args()
    tree = args.tree.resolve(strict=True)
    current = snapshot(tree, args.isla_source)
    if args.compare:
        frozen = json.loads(args.output.read_text())
        assert current == frozen, '源码清单与当前工作树不一致'
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as out:
            json.dump(current, out, ensure_ascii=False, indent=2)
            out.write('\n')
    print(json.dumps({'root': str(tree), 'head': current['head'],
                      'files': len(current['files']), 'verified': args.compare}, ensure_ascii=False))


if __name__ == '__main__':
    main()
