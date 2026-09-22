"""Copy approved evidence bundles without overwriting existing files.

Run once from the workspace root. No source file is changed.
"""
import hashlib
import json
import shutil
from pathlib import Path


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


for source, destination in (
    ('agents/ara_poc_batch', 'archives/ara/2026-09-23-poc-batch'),
    ('agents/vext_issue_draft_reproduction',
     'archives/xiangshan/2026-09-23-issue-reproduction'),
):
    src, dst = Path(source), Path(destination)
    files = sorted(p for p in src.rglob('*') if p.is_file())
    assert not any(p.is_symlink() for p in src.rglob('*')), 'Review symlinks first'
    assert not dst.exists(), f'Snapshot already exists: {dst}'
    rows = []
    for path in files:
        before = sha(path)
        target = dst / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        assert sha(target) == before == sha(path), f'Unstable copy: {path}'
        rows.append(dict(source=str(path), archive=str(target),
                         bytes=target.stat().st_size, sha256=before))
    # Recheck the entire source set after copying, not just each individual copy.
    assert files == sorted(p for p in src.rglob('*') if p.is_file())
    for row in rows:
        assert sha(Path(row['source'])) == row['sha256']
    manifest = dict(snapshot_date='2026-09-23', source=source,
                    note='Frozen copy, originals retained; historical claims not revalidated.',
                    files=rows)
    with (dst / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(destination, len(rows), sum(r['bytes'] for r in rows), flush=True)
