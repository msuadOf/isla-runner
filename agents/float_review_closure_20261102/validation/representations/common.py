"""Frozen final-artifact checks shared by directed representation and Make smoke."""

import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(item):
    path = (ROOT / item["path"]).resolve(strict=True)
    actual = sha(path)
    if actual != item["sha256"]:
        raise ValueError(f"SHA-256 mismatch: {path}: {actual} != {item['sha256']}")
    return path


def git_head(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def verify_tree(item, commit):
    tree = (ROOT / item["path"]).resolve(strict=True)
    manifest_path = checked(item["manifest"])
    manifest = json.loads(manifest_path.read_text())
    if git_head(tree) != commit or manifest.get("commit") != commit:
        raise ValueError(f"source commit mismatch: {tree}")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"empty source manifest: {manifest_path}")
    for name, expected in files.items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError(f"source manifest path escapes tree: {name}")
        if sha(tree / name) != expected:
            raise ValueError(f"source file changed after freeze: {name}")
    return tree, manifest_path


def frozen_inputs(path):
    path = path.resolve(strict=True)
    data = json.loads(path.read_text())
    if data.get("domain") != "full" or data.get("seed") != 17 or data.get("tactic") != "qffp" or data.get("threads") != 1:
        raise ValueError("expected full-domain source freeze with seed17/T1/qffp")
    model, model_manifest = verify_tree(data["model_tree"], data["model_commit"])
    isla, isla_manifest = verify_tree(data["isla_tree"], data["isla_commit"])
    binary = checked(data["binary"])
    ir = checked(data["irs"]["rv64-v128"])
    base_config = checked(data["configs"]["rv64-fd-full"])
    z3 = checked(data["z3"])
    preload = checked(data["seed_preload"])
    linked = subprocess.check_output(["ldd", str(binary)], text=True)
    matches = re.findall(r"libz3\.so\S* => (\S+)", linked)
    if len(matches) != 1 or Path(matches[0]).resolve() != z3:
        raise ValueError("frozen Release binary does not link frozen official Z3")
    return {
        "inputs": path, "inputs_sha256": sha(path), "data": data,
        "model": model, "model_manifest": model_manifest,
        "isla": isla, "isla_manifest": isla_manifest,
        "binary": binary, "ir": ir, "base_config": base_config,
        "z3": z3, "preload": preload, "ldd": linked,
    }


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
           "omitted-cases", "model-query-timeouts", "pending-batches", "sampled-paths")


def finished_summary(data, clause):
    summary = data.get("summary")
    if not isinstance(summary, dict) or summary.get("status") != "finished":
        return False
    if summary.get("target-clause") != "z" + clause:
        return False
    return all(key in summary and type(summary[key]) is int and summary[key] == 0 for key in PARTIAL)


def fixed_seed(path):
    if not path.exists():
        return False
    lines = [line for line in path.read_text().splitlines() if "random_seed" in line]
    if not lines:
        return False
    return all(re.fullmatch(r"parameter=random_seed original=\d+ fixed=17", line) for line in lines)


def toolchain_identity(checker):
    drivers = {}
    for name, command in checker.DRIVERS.items():
        binary = Path(command[0]).resolve(strict=True)
        version = subprocess.check_output([str(binary), "--version"], text=True).splitlines()[0]
        drivers[name] = {"path": str(binary), "sha256": sha(binary), "version": version,
                         "arguments": command[1:]}
    objcopy = Path("/usr/bin/riscv64-unknown-elf-objcopy").resolve(strict=True)
    return {"drivers": drivers, "objcopy": {"path": str(objcopy), "sha256": sha(objcopy)}}
