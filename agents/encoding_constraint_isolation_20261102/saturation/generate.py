#!/usr/bin/env python3
"""独立 memo 生成四配置严格 IR，并记录普通严格检查与源码来源。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "generation"
MODEL = ROOT / ".worktree/runner-float/sail-riscv"
SAIL = ROOT / "isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src/sail"
PLUGIN = ROOT / ".tmp/float-full-trace-20260929/fvv-branch-candidate/sail_plugin_isla.cmxs"
CONFIGS = (
    ("rv64d_v128_e64", "rv64d.json"),
    ("rv32d", "rv32d.json"),
    ("rv64d_v256_e64", "rv64d_v256_e64.json"),
    ("rv64d_v512_e64", "rv64d_v512_e64.json"),
)
CPUS = {"rv64d_v128_e64": 108, "rv32d": 109,
        "rv64d_v256_e64": 110, "rv64d_v512_e64": 111,
        "ordinary-strict": 112}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(MODEL), *args], text=True).strip()


def run(kind, config, sources, ordinary):
    out = OUTPUT / kind
    out.mkdir(parents=True, exist_ok=True)
    cfg = ROOT / "isla/ir/provenance" / config
    if ordinary:
        command = [str(SAIL), "--strict-var", "--strict-bitvector",
                   "--strict-exponentials", "--require-version", "0.20.1",
                   "--memo-z3-path", str(OUTPUT / "sail_smt_cache_ordinary-strict"),
                   "--all-modules", "--just-check", "--config", str(cfg),
                   "riscv.sail_project"]
    else:
        command = ["/usr/bin/python3", str(ROOT / "isla/scripts/regenerate_ir.py"),
                   "--model", str(MODEL), "--sail", str(SAIL), "--plugin", str(PLUGIN),
                   "--config", str(cfg), "--output", str(out), "--name", kind]
    executed_command = ["taskset", "-c", str(CPUS[kind]), *command]
    record = {
        "model_commit_at_start": git("rev-parse", "HEAD"),
        "model_dirty": bool(git("status", "--porcelain")),
        "model_files": sources,
        "source_file_sha256": sources["extensions/V/vext_fp_utils_insts.sail"],
        "source_patch_sha256": sha(HERE / "model.patch"),
        "plugin_sha256": sha(PLUGIN),
        "sail_launcher_sha256": sha(SAIL),
        "sail_version": subprocess.check_output([str(SAIL), "--version"], text=True).strip(),
        "config_sha256": sha(cfg),
        "command": command,
        "executed_command": executed_command,
        "cpu": CPUS[kind],
        "cwd": str(MODEL / "model"),
    }
    started = time.monotonic()
    with (out / "driver.log").open("w") as log:
        result = subprocess.run(executed_command, cwd=MODEL / "model", stdout=log, stderr=subprocess.STDOUT)
    record.update(exit_code=result.returncode, seconds=time.monotonic() - started,
                  model_commit=git("rev-parse", "HEAD"),
                  source_unchanged=all(sha(MODEL / "model" / name) == digest
                                       for name, digest in sources.items()))
    ir = out / (kind + ".ir")
    if ir.exists():
        record["ir_sha256"] = sha(ir)
    (out / "driver.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(kind, result.returncode, flush=True)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ordinary-only", action="store_true")
    args = parser.parse_args()
    if not args.ordinary_only:
        assert not git("status", "--porcelain"), "四配置 IR 需要干净源码提交"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sources = {str(path.relative_to(MODEL / "model")): sha(path)
               for path in (MODEL / "model").rglob("*") if path.is_file()}
    jobs = [("ordinary-strict", "rv64d.json", True)] if args.ordinary_only else [
        (kind, config, False) for kind, config in CONFIGS
    ]
    with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        codes = list(executor.map(lambda item: run(item[0], item[1], sources, item[2]), jobs))
    raise SystemExit(any(codes))


if __name__ == "__main__":
    main()
