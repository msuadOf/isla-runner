#!/usr/bin/env python3
"""Build a byte-level inventory for the local scalar FP results backup."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone


here = Path(__file__).resolve().parent
root = here.parents[1]
stage_rel = Path("isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/stage-v3")
evidence_rel = stage_rel.parent / "evidence"
work_rel = Path("difftest-xiangshan/work/float-v3-20260929")
archive_rel = Path("archives/_raw/float-scalar-73df-20260929.tar.zst")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


launch = json.loads((root / evidence_rel / "batch-v3-scalar-launch.json").read_text())
targets = launch["targets"]
assert len(targets) == len(set(targets)) == 51
paths: set[Path] = set()
generated = 0
for target in targets:
    json_rel = stage_rel / "output" / f"rv64_z{target}.json"
    log_rel = stage_rel / "output/log" / f"{target}.log"
    trace_rel = stage_rel / "output/trace" / f"itrace_{target}.txt"
    for path in (json_rel, log_rel, trace_rel):
        assert (root / path).is_file(), path
        paths.add(path)
    data = json.loads((root / json_rel).read_text())
    assert data["summary"]["complete"] is True
    generated += len(data["gen"])
assert generated == 1344

for name in ("status.intime.log", "status.failed.log", ".solve_progress_counter"):
    paths.add(stage_rel / "output" / name)
for name in ("manifest.json", "batch-v3-scalar-launch.json", "batch-v3-scalar-make.log", "batch-v3-scalar-audit.json"):
    paths.add(evidence_rel / name)
for name in ("rv64d.ir", "configs/riscv64_difftest_fd.toml", "target/release/isarch", "src/isarch/exec.rs", "src/isarch/target.rs"):
    paths.add(stage_rel / name)

for name in ("all-input.json", "supported-input.json", "unsupported-input.json", "negative-input.json", "smoke-input.json", "scope-correction.json", "prepare-current-r2.py", "prepare-current-r3.py"):
    paths.add(work_rel / name)
for path in (root / work_rel).iterdir():
    if not path.name.startswith("current-"):
        continue
    if path.is_file() or path.is_symlink():
        paths.add(path.relative_to(root))
    elif path.is_dir():
        for child in path.rglob("*"):
            if child.is_file() or child.is_symlink():
                paths.add(child.relative_to(root))

for name in (
    "difftest-xiangshan/xiangshan/build/emu",
    "difftest-xiangshan/xiangshan/build/verilator-compile/emu",
    "difftest-xiangshan/xiangshan/ready-to-run/riscv64-nemu-interpreter-so",
    "difftest-xiangshan/audit_current_float_campaign.py",
    "agents/difftest_xiangshan_v/status.md",
    "agents/float_support_review/status.md",
    "archives/float-scalar-2026-09-29/pipeline-used.py",
):
    paths.add(Path(name))

files = []
for rel in sorted(paths):
    path = root / rel
    assert path.exists() or path.is_symlink(), rel
    if path.is_symlink():
        files.append({"path": rel.as_posix(), "kind": "symlink", "target": os.readlink(path)})
    else:
        assert path.is_file(), rel
        files.append({"path": rel.as_posix(), "kind": "file", "size": path.stat().st_size, "sha256": digest(path)})

manifest = {
    "schema": "float-scalar-local-backup-v1",
    "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "archive": archive_rel.as_posix(),
    "scope": "51 complete scalar solve JSONs with matching logs/traces, v3 solve identities, current-workspace XiangShan DiffTest inputs/ELFs/results/logs/retries, tested emu and NEMU",
    "note": "The original files remain in place. Current-workspace DiffTest manifests contain absolute paths, so replay after relocation requires path adjustment. The archive is local and is not a remote backup.",
    "counts": {"scalar_targets": len(targets), "scalar_generated": generated, "files": len(files)},
    "identity": {
        "isla_head_now": git_head(root / "isla"),
        "sail_riscv_head_now": git_head(root / "sail-riscv"),
        "xiangshan_head": git_head(root / "difftest-xiangshan/xiangshan"),
        "ir_sha256": digest(root / stage_rel / "rv64d.ir"),
        "isarch_sha256": digest(root / stage_rel / "target/release/isarch"),
        "config_sha256": digest(root / stage_rel / "configs/riscv64_difftest_fd.toml"),
        "pipeline_used_sha256": digest(here / "pipeline-used.py"),
        "current_workspace_audit_sha256": digest(root / work_rel / "current-workspace-audit.json"),
        "emu_sha256": digest(root / "difftest-xiangshan/xiangshan/build/verilator-compile/emu"),
        "nemu_so_sha256": digest(root / "difftest-xiangshan/xiangshan/ready-to-run/riscv64-nemu-interpreter-so"),
    },
    "files": files,
}
manifest_path = here / "manifest.json"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
all_paths = sorted(paths | {Path("archives/float-scalar-2026-09-29/manifest.json"), Path("archives/float-scalar-2026-09-29/make_manifest.py")})
(here / "paths.nul").write_bytes(b"".join(os.fsencode(path.as_posix()) + b"\0" for path in all_paths))
print(f"targets={len(targets)} gen={generated} files={len(files)} total_bytes={sum(x.get('size', 0) for x in files)}")
