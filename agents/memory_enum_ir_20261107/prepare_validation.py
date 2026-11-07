#!/usr/bin/env python3
"""复制旧验收脚本到 output，并明确调整本轮路径和并发参数。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/memory-enum-20261107'
OLD = ROOT / 'agents/float_memory_merge_20261103/validation/dynamic'
DEST = OUT / 'dynamic'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior-workspace', type=Path, required=True,
                        help='只读历史工具和验收依赖所在根仓')
    prior = parser.parse_args().prior_workspace.resolve(strict=True)
    DEST.mkdir(exist_ok=False)
    deps = OUT / 'deps'
    deps.mkdir(exist_ok=False)
    for source, destination in (
        ('agents/branch_ablation_official_z3_20261102/bin/seed_control.so', 'seed_control.so'),
        ('agents/float_support_review/oracle/oracle.cpp', 'oracle.cpp'),
        ('.tmp/unified-backend-crosscheck/oracle-build/oracle', 'oracle'),
        ('.tmp/unified-backend-crosscheck/oracle-build/softfloat/libsoftfloat.a', 'softfloat/libsoftfloat.a')):
        target = deps / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prior / source, target)
    shutil.copy2(prior / 'agents/float_review_completion_20261102/assembly/check_json.py', DEST / 'check_json.py')
    changes = []
    for p in OLD.glob('*.py'):
        s = p.read_text()
        s = s.replace('ROOT = HERE.parents[3]', f'ROOT = Path({str(ROOT)!r})')
        s = s.replace('"-T", "1"', '"-T", "32"')
        s = s.replace('"THREADS=1"', '"THREADS=32"')
        if p.name == 'run_make.py':
            s = s.replace('7200s', '1200s')
        s = s.replace('inputs.get("threads") != 1', 'inputs.get("threads") != 32')
        s = s.replace('"threads": 1', '"threads": 32')
        s = s.replace('target = HERE / "flags/target"', 'target = HERE.parent / "target"')
        if p.name == 'run_assembly.py':
            s = s.replace('CHECKER = ROOT / "agents/float_review_completion_20261102/assembly/check_json.py"', 'CHECKER = HERE / "check_json.py"')
        if p.name == 'run_315.py':
            s = s.replace('LEGACY = ROOT / "agents/float_review_closure_20261102/validation/exceptions/run_directed.py"',
                          'LEGACY = HERE / "run_directed.py"')
            s = s.replace('ROOT / ".tmp/unified-backend-crosscheck/oracle-build/oracle"', 'HERE.parent / "deps/oracle"')
            s = s.replace('ROOT / "agents/float_support_review/oracle/oracle.cpp"', 'HERE.parent / "deps/oracle.cpp"')
        (DEST/p.name).write_text(s)
        changes.append({'source': str(p.relative_to(ROOT)), 'source_sha256': sha(p),
                        'copy': str((DEST/p.name).relative_to(ROOT)), 'copy_sha256': sha(DEST/p.name)})
    legacy = ROOT / 'agents/float_review_closure_20261102/validation/exceptions/run_directed.py'
    (DEST/'run_directed.py').write_text(legacy.read_text()
        .replace('"-T", "1"', '"-T", "32"')
        .replace('ROOT = HERE.parents[3]', f'ROOT = Path({str(ROOT)!r})')
        .replace('sys.path.insert(0, str(HERE.parent))',
                 'sys.path.insert(0, str(ROOT / "agents/float_review_closure_20261102/validation"))'))
    changes.append({'source': str(legacy.relative_to(ROOT)), 'source_sha256': sha(legacy),
                    'copy_sha256': sha(DEST/'run_directed.py')})
    shutil.copy2(OLD/'expected-315.json',DEST/'expected-315.json')
    shutil.copytree(OLD/'flags',DEST/'flags',ignore=shutil.ignore_patterns('target','__pycache__'))
    manifest=DEST/'flags/Cargo.toml'
    manifest.write_text(manifest.read_text().replace('../../../../../.worktree/merge-float-memory-20261104/isla/isla-lib',
                                                    '../../../../isla/isla-lib'))
    (OUT/'validation-script-copies.json').write_text(json.dumps(changes,indent=2,ensure_ascii=False)+'\n')

if __name__ == '__main__':
    main()
