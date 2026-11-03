#!/usr/bin/env python3
"""只读冻结 Isla 共同祖先到受测提交的生产源码差异与必要性依据。"""
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path.cwd()
BASE = '0008fae76f4cff86dae1a036d889f0414c228e9d'
HEAD = '42000be47596ec088623881d03c0eadc5cf0ba27'
OUT = ROOT / 'agents/float_review_closure_20261102/baseline-0008fae/isla-review.json'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT / 'isla'), *args], text=True)


def source(revision, name):
    return git('show', f'{revision}:{name}')


assert git('merge-base', BASE, HEAD).strip() == BASE
changed = git('diff', '--numstat', BASE, HEAD).splitlines()
files = []
for row in changed:
    added, removed, name = row.split('\t', 2)
    production_path = (
        name.endswith('.rs') and name.startswith(('isla-lib/src/', 'src/', 'isla-axiomatic/src/', 'web/server/src/'))
        or name in ('Cargo.toml', 'isla-lib/Cargo.toml')
        or name.startswith('configs/') and name.endswith('.toml')
        or name in ('scripts/run.mk', 'scripts/run_ctrl_c.mk', 'scripts/solve_process.py')
    )
    if production_path:
        text = source(HEAD, name) if git('ls-tree', HEAD, '--', name).strip() else None
        files.append({'path': name, 'added_including_inline_tests': int(added),
                      'removed_including_inline_tests': int(removed),
                      'head_sha256': hashlib.sha256(text.encode()).hexdigest() if text is not None else None})

before = re.split(r'#\[cfg\(test\)\]\s*mod tests', source('cf1aa14', 'isla-lib/src/smt.rs'))[0].splitlines()
after = re.split(r'#\[cfg\(test\)\]\s*mod tests', source(HEAD, 'isla-lib/src/smt.rs'))[0].splitlines()
enum_added = enum_removed = 0
for tag, i, j, k, l in difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes():
    if tag in ('insert', 'replace'):
        enum_added += l-k
    if tag in ('delete', 'replace'):
        enum_removed += j-i

evidence_paths = [
    'agents/float_review_closure_20261102/review/enum/baseline-independent.json',
    'agents/float_review_closure_20261102/review/enum/green-independent.json',
    'agents/float_review_closure_20261102/review/enum/old-binary-timeout-audit.json',
    'agents/float_review_closure_20261102/review/enum/watchdog-itrace-result.json',
    'agents/explicit_branch_timeout_diagnosis_20261102/collector-cost/report.md',
    'agents/encoding_constraint_isolation_20261102/review/final-report.md',
    'agents/float_review_completion_20261102/executeas/status.md',
    'agents/float_support_review/solve-fix-mixed-bits.md',
    'agents/float_support_review/solve-fix-model-cache.md',
    'agents/float_only_review/report.md',
]
result = {
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'repository': 'isla', 'base': BASE, 'current_reviewed': HEAD,
    'base_is_ancestor': True,
    'current_worktree_head': git('rev-parse', 'HEAD').strip(),
    'preserved_worktree_status': git('status', '--short'),
    'method': '只读比较提交对象；不读取未提交IR测试修改作为受测实现，不修改77条长跑源码/inputs/进程。文件增删含内联测试，不等于生产逻辑增删。',
    'production_path_count': len(files), 'files': files,
    'closure_round_delta': {
        'base': git('rev-parse', 'cf1aa14').strip(), 'head': HEAD,
        'changed_paths': git('diff', '--name-only', 'cf1aa14', HEAD).splitlines(),
        'smt_production_prefix_added': enum_added,
        'smt_production_prefix_removed': enum_removed,
        'prefix_boundary': 'smt.rs #[cfg(test)] mod tests 之前；末尾不变re-export不计入差异',
    },
    'evidence': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in evidence_paths},
    'new_dynamic_tests': False,
    'recommended_no_immediate_mutation': True,
}
if OUT.exists():
    previous = json.loads(OUT.read_text())
    if 'documentation_correction_20261103' in previous:
        result['documentation_correction_20261103'] = previous['documentation_correction_20261103']
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(f'{BASE}..{HEAD}: {len(files)} 个生产路径；本轮枚举生产前段 +{enum_added}/-{enum_removed}')
