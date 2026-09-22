"""Freeze selected evidence and inventory an already completed local raw tar.

Run from the workspace root after tar creation and inspection of tar --compare.
Existing snapshots are never overwritten with different source bytes.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


source = Path('difftest-xiangshan')
dest = Path('archives/xiangshan/2026-09-21-harness')
selected = []
selected.append(source / 'work/rerun-c8d7b3a/shards/monitor.log')
for folder in ('inputs', 'poc-final'):
    selected.extend(p for p in (source / folder).rglob('*') if p.is_file())
for directory, subdirs, files in os.walk(source / 'work'):
    subdirs[:] = [d for d in subdirs if not d.startswith('case-')]
    selected.extend(Path(directory) / f for f in files
                    if Path(f).suffix in ('.json', '.ndjson', '.md'))

entries = []
for path in sorted(selected):
    target = dest / path.relative_to(source)
    sha = digest(path)
    if target.exists():
        assert digest(target) == sha, f'Existing snapshot differs: {target}'
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    assert digest(target) == sha and digest(path) == sha, path
    entries.append(dict(source=str(path), archive=str(target), bytes=target.stat().st_size,
                        sha256=sha, source_mtime_ns=path.stat().st_mtime_ns))

raw = Path('archives/_raw/xiangshan/2026-09-21-harness/work-and-baseline.tar')
manifest = dict(
    snapshot_utc=datetime.now(timezone.utc).isoformat(),
    note='Snapshot date is not execution date. Original data retained. Raw tar is local only.',
    selection='All inputs and poc-final files; work JSON/NDJSON/Markdown outside case-* directories; latest monitor.log.',
    consistency='Non-atomic collection. tar --compare exit 1: only work/rerun-c8d7b3a/shards/monitor.log changed size/mtime after packing. All other members compared equal. A separately hashed newer monitor.log is included in curated work/. No writer was stopped.',
    checkout_heads_not_proof_of_historical_builds={
        'isla': '97390b0a5f05896a3255af72939e314eb5feaab5',
        'sail-riscv': '5f1a0de0d8219537f27680d325b7adcac5db3478',
        'xiangshan': 'c8d7b3a5c1abf3f42c954e61abba20dd27e02a21'},
    files=entries,
    local_raw=dict(path=str(raw), bytes=raw.stat().st_size, sha256=digest(raw),
                   sources=['difftest-xiangshan/work', 'difftest-xiangshan/emu-baseline-7bf51a8']),
    baseline_emulator=dict(bytes=(source / 'emu-baseline-7bf51a8').stat().st_size,
                           sha256=digest(source / 'emu-baseline-7bf51a8'),
                           build_recipe='Not established; filename identifies 7bf51a8 only.'))
output = dest / 'manifest.json'
with output.open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(f'{len(entries)} evidence files, {sum(e["bytes"] for e in entries)} bytes')
print(f'Local raw tar: {raw.stat().st_size} bytes')
