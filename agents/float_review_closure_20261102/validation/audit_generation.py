#!/usr/bin/env python3
"""核生成输入的166个已跟踪模型文件和patched Sail实际可执行/标准库。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL = ROOT / ".worktree/runner-float/sail-riscv"
SAIL = ROOT / "isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src/sail"
PLUGIN = ROOT / ".tmp/float-full-trace-20260929/fvv-branch-candidate/sail_plugin_isla.cmxs"
DRIVER = ROOT / "isla/scripts/regenerate_ir.py"
CONFIGS = ("rv64d.json", "rv32d.json", "rv64d_v256_e64.json", "rv64d_v512_e64.json")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--model", type=Path,
                        help="模型工作树；须与生成记录中的 model_tree 一致")
    args = parser.parse_args()
    out = ROOT / "agents/float_review_closure_20261102/validation/generation" / args.batch
    source_path = out / "source.json"
    source = json.loads(source_path.read_text())
    recorded_model = ROOT / source.get("model_tree", str(DEFAULT_MODEL.relative_to(ROOT)))
    model = recorded_model.resolve(strict=True)
    if args.model is not None and args.model.resolve(strict=True) != model:
        raise ValueError("--model 与生成记录的 model_tree 不一致")
    if not model.is_relative_to(ROOT):
        raise ValueError("模型工作树不在本仓工作区")
    assert source["commit"] == subprocess.check_output(
        ["git", "-C", str(model), "rev-parse", "HEAD"], text=True).strip()
    names = [name.removeprefix("model/") for name in subprocess.check_output(
        ["git", "-C", str(model), "ls-files", "-z", "model"]).decode().split("\0") if name]
    assert len(names) == 166
    files = {name: sha(model / "model" / name) for name in names}
    assert all(source["model_files"].get(name) == value for name, value in files.items())
    excluded = sorted(set(source["model_files"]) - set(files))
    assert excluded in ([], ["sail_smt_cache"]), excluded
    install = SAIL.parent / "_build/install/default"
    actual_sail = (install / "bin/sail").resolve(strict=True)
    standard = install / "share/sail/lib"
    libraries = install / "share/libsail/plugins"
    tool_files = [SAIL, actual_sail, PLUGIN, DRIVER,
                  *sorted(path for path in standard.rglob("*") if path.is_file()),
                  *sorted(path for path in libraries.rglob("*") if path.is_file()),
                  *(ROOT / "isla/ir/provenance" / name for name in CONFIGS)]
    tool_hashes = {str(path.relative_to(ROOT)): sha(path) for path in tool_files}
    start_ns = source_path.stat().st_mtime_ns
    ctime_precedes_start = all(path.stat().st_ctime_ns < start_ns for path in tool_files)
    result = {"model_commit": source["commit"],
              "model_tree": str(model.relative_to(ROOT)), "tracked_model_count": len(files),
              "tracked_model_files": files, "excluded_ignored_cache": excluded,
              "tool_file_count": len(tool_hashes), "tool_files": tool_hashes,
              "actual_sail_binary": str(actual_sail.relative_to(ROOT)),
              "tool_ctime_precedes_generation_start": ctime_precedes_start,
              "generation_start_source_manifest_sha256": sha(source_path),
              "source_unchanged_now": all(sha(model / "model" / name) == value
                                          for name, value in files.items())}
    target = out / "independent-input-audit.json"
    with target.open("x") as file:
        json.dump(result, file, indent=2, ensure_ascii=False)
        file.write("\n")
    print(json.dumps({key: result[key] for key in ("tracked_model_count", "tool_file_count",
                                                   "tool_ctime_precedes_generation_start",
                                                   "source_unchanged_now")}, ensure_ascii=False))
    if not ctime_precedes_start or not result["source_unchanged_now"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
