#!/usr/bin/env python3
"""Run the direct flags state probe against five frozen generated IR files."""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
KEYS = ("rv64-v128", "rv64-v256", "rv64-v512", "rv64-default", "rv32-default")
ISLA_OMITTED_TRACKED = {
    "ir/provenance/manifest.json",
    "ir/rv64d_v128_e64.ir",
    "ir/rv64d_v256_e64.ir",
    "ir/rv64d_v512_e64.ir",
    "isla-lib/tests/fixtures/ir_cache_assumption.ir",
    "isla-lib/tests/fixtures/source_region_foreach_match.ir",
    "rv32d.ir",
    "rv64d.ir",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(entry: dict) -> Path:
    path = (ROOT / entry["path"]).resolve(strict=True)
    if sha(path) != entry["sha256"]:
        raise ValueError(f"hash mismatch: {path}")
    return path


def git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def verify_tree(root: Path, entry: dict, commit: str, kind: str) -> None:
    if git_head(root) != commit:
        raise ValueError(f"tree is not at frozen commit {commit}: {root}")
    manifest = json.loads(checked(entry["manifest"]).read_text())
    if manifest.get("commit") != commit or not manifest.get("files"):
        raise ValueError(f"invalid source manifest: {root}")
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).split(b"\0")
    names = {name.decode() for name in tracked if name}
    listed = set(manifest["files"])
    if not listed.issubset(names):
        raise ValueError(f"source manifest lists unknown files: {root}")
    omitted = names - listed
    if kind == "isla_tree":
        if manifest.get("scope") != "isla-source-excluding-generated-ir" or omitted != ISLA_OMITTED_TRACKED:
            raise ValueError(f"unexpected Isla source manifest scope: {sorted(omitted)}")
    elif omitted:
        raise ValueError(f"model source manifest omitted tracked files: {sorted(omitted)}")
    for name, expected in manifest["files"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or sha(root / path) != expected:
            raise ValueError(f"source manifest file changed: {name}")
    # The eight excluded Isla files are old IR/provenance/test fixtures. Check
    # their bytes against the frozen commit too, so the entire tracked tree is fixed.
    for name in omitted:
        committed = subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{name}"])
        if hashlib.sha256(committed).hexdigest() != sha(root / name):
            raise ValueError(f"omitted tracked file changed: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--rv32-config", type=Path, required=True)
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch):
        parser.error("invalid batch name")
    inputs = json.loads(args.inputs.read_text())
    if inputs["model_commit"] not in {
        "8ad5e8e9e0fc2a567a3b989a3738698f5c520bde",
        "21418d0b0d4942fae20061ed580ee04aff4a8a61",
        "e9d69d2f28586c089244c8e37ee4c904c5114458",
        "0f7b8fbc6724103f91f929ef6918f123df75d6c9",
    }:
        raise ValueError("unexpected final model commit")
    for field, commit in (("model_tree", "model_commit"), ("isla_tree", "isla_commit")):
        tree = (ROOT / inputs[field]["path"]).resolve(strict=True)
        verify_tree(tree, inputs[field], inputs[commit], field)
    if inputs["seed"] != 17 or inputs["tactic"] != "qffp":
        raise ValueError("expected seed17/qffp")
    z3 = checked(inputs["z3"])
    seed = checked(inputs["seed_preload"])
    isarch = checked(inputs["binary"])
    rv32 = args.rv32_config.resolve(strict=True)
    rv64 = checked(inputs["configs"]["rv64-fd-full"])
    irs = {key: checked(inputs["irs"][key]) for key in KEYS}
    worktree = (ROOT / inputs["isla_tree"]["path"]).resolve(strict=True)
    manifest = HERE / "Cargo.toml"
    target = HERE / "target"
    binary = target / "release/float-flags-state-probe"
    dest = HERE / "runs" / args.batch
    if dest.exists():
        raise ValueError(f"output exists: {dest}")
    build = ["taskset", "-c", str(args.cpu), "cargo", "build", "--offline", "--release",
             "--manifest-path", str(manifest)]
    commands = {key: ["taskset", "-c", str(args.cpu), str(binary), str(ir),
                      str(rv32 if key == "rv32-default" else rv64)]
                for key, ir in irs.items()}
    record = {
        "scope": "direct concrete zaccrue_fflags helper; not whole Clause",
        "probe_binary_role": "independent Rust helper runner, separate from frozen isarch",
        "batch": args.batch,
        "cpu": args.cpu,
        "model_commit": inputs["model_commit"],
        "isla_commit": inputs["isla_commit"],
        "inputs_sha256": sha(args.inputs),
        "runner_source_sha256": sha(HERE / "src/main.rs"),
        "runner_manifest_sha256": sha(manifest),
        "oracle_sha256": sha(HERE / "oracle.py"),
        "ir_sha256": {key: sha(path) for key, path in irs.items()},
        "config_sha256": {"rv64": sha(rv64), "rv32": sha(rv32)},
        "z3_sha256": sha(z3),
        "frozen_isarch_sha256": sha(isarch),
        "seed_preload_sha256": sha(seed),
        "seed": 17,
        "tactic": "qffp",
        "build": build,
        "commands": commands,
        "cwd": str(worktree),
    }
    if args.dry_run:
        print(json.dumps(record, indent=2, ensure_ascii=False))
        return
    dest.mkdir(parents=True)
    (dest / "inputs.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    z3_lib_dir = str(z3.parent)
    env = dict(os.environ, CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(target),
               CARGO_BUILD_JOBS="1",
               LIBRARY_PATH=z3_lib_dir + os.pathsep + os.environ.get("LIBRARY_PATH", ""),
               LD_LIBRARY_PATH=z3_lib_dir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
    record["z3_library_dir"] = z3_lib_dir
    with (dest / "build.log").open("w") as log:
        built = subprocess.run(build, cwd=worktree, env=env, stdout=log, stderr=subprocess.STDOUT)
    record["build_exit"] = built.returncode
    if built.returncode:
        (dest / "result.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        raise SystemExit(built.returncode)
    record["binary_sha256"] = sha(binary)
    linked = subprocess.check_output(["ldd", str(binary)], text=True, env=env)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    if len(matches) != 1 or Path(matches[0]).resolve() != z3:
        raise ValueError("runner did not link the frozen official Z3 library")
    record["ldd"] = linked
    runs = {}
    for key, command in commands.items():
        seed_log = dest / f"{key}.seed.log"
        run_env = dict(env, LD_PRELOAD=str(seed), ISLA_ABLATION_SEED="17",
                       ISLA_ABLATION_SEED_LOG=str(seed_log))
        with (dest / f"{key}.log").open("w") as log:
            code = subprocess.run(command, cwd=worktree, env=run_env, stdout=log,
                                  stderr=subprocess.STDOUT).returncode
        oracle = subprocess.run([sys.executable, str(HERE / "oracle.py"),
                                 str(dest / f"{key}.log")], capture_output=True, text=True)
        (dest / f"{key}.oracle.json").write_text(oracle.stdout)
        (dest / f"{key}.oracle.stderr").write_text(oracle.stderr)
        output = (dest / f"{key}.log").read_text()
        expected_xlen = 32 if key == "rv32-default" else 64
        runs[key] = {
            "exit": code,
            "log_sha256": sha(dest / f"{key}.log"),
            "callback_contract": "CALLBACK_CONTRACT fflags,fcsr; no mstatus callback" in output,
            "pass_count": len(re.findall(r"^PASS (?!total=)", output, re.M)),
            "final_marker": f"PASS total=60 xlen={expected_xlen}" in output,
            "seed_intercepted": (seed_log.exists() and re.search(
                r"parameter=random_seed original=\d+ fixed=17(?:\n|$)",
                seed_log.read_text()) is not None),
            "seed_log_sha256": sha(seed_log) if seed_log.exists() else None,
            "oracle_exit": oracle.returncode,
            "oracle_sha256": sha(dest / f"{key}.oracle.json"),
        }
        print(key, runs[key], flush=True)
    record["runs"] = runs
    record["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    record["pass"] = all(
        run["exit"] == 0 and run["callback_contract"] and run["pass_count"] == 60
        and run["final_marker"] and run["seed_intercepted"]
        and run["oracle_exit"] == 0 for run in runs.values())
    (dest / "result.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    raise SystemExit(0 if record["pass"] else 1)


if __name__ == "__main__":
    main()
