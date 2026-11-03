#!/usr/bin/env python3
"""独立读取最终三个提交、五 IR 来源和原 dirty 文件；不写生产仓库。"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PARENTS = {
    "root": ["31ef3b9a8aa3a9db4c03a1d99c191cadf1aadaef", "0665526d7e14a207eb9928e282e627584b5635fe"],
    "isla": ["bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57", "591693df2bc32019ea300511509ed683df09522e"],
    "sail-riscv": ["c70482a73be2a67c5a89d88b1e6c2bbea224940c", "0f7b8fbc6724103f91f929ef6918f123df75d6c9"],
}
ISLA_MERGE = "7cce7834b6f1376293dfce1d52b7e944fa237941"
IR_PATHS = {"rv64d.ir", "rv32d.ir", "ir/rv64d_v128_e64.ir", "ir/rv64d_v256_e64.ir", "ir/rv64d_v512_e64.ir"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-promoted-original-heads", action="store_true")
    args = parser.parse_args()
    candidate = args.candidate.resolve(strict=True)
    rows = {}
    for key, parents in PARENTS.items():
        repo = candidate if key == "root" else candidate / key
        head = git(repo, "rev-parse", "HEAD")
        actual_parents = git(repo, "show", "-s", "--format=%P", "HEAD").split()
        merge_head, followup = head, None
        if key == "isla" and actual_parents != parents:
            assert actual_parents == [ISLA_MERGE], (key, actual_parents)
            assert git(repo, "show", "-s", "--format=%P", ISLA_MERGE).split() == parents
            changed = git(repo, "diff", "--name-only", ISLA_MERGE, head).splitlines()
            expected = {"src/isarch/exec.rs", "src/isarch/memory_model.rs", "src/isarch/mod.rs", "src/isarch/target.rs"}
            assert set(changed) == expected
            for name in changed:
                old = subprocess.check_output(["git", "-C", str(repo), "show", ISLA_MERGE + ":" + name])
                new = subprocess.check_output(["git", "-C", str(repo), "show", head + ":" + name])
                marker = b"#[cfg(test)]\nmod tests"
                assert old.count(marker) == new.count(marker) == 1
                assert old.split(marker)[0] == new.split(marker)[0]
            merge_head = ISLA_MERGE
            followup = {"commit": head, "test_only_paths": changed, "production_prefixes_equal_merge": True}
        else:
            assert actual_parents == parents, (key, actual_parents, parents)
        assert not git(repo, "ls-files", "-u"), (key, "unresolved conflicts")
        assert not git(repo, "status", "--porcelain", "--untracked-files=no"), (key, "tracked files differ from sealed commit")
        rows[key] = {"head": head, "parents": actual_parents, "tree": git(repo, "rev-parse", "HEAD^{tree}"),
                     "merge_commit": merge_head, "merge_parents": parents, "followup": followup,
                     "status": git(repo, "status", "--short")}
    links = {}
    for line in git(candidate, "ls-tree", "HEAD", "isla", "sail-riscv").splitlines():
        meta, name = line.split("\t")
        mode, kind, commit = meta.split()
        assert mode == "160000" and kind == "commit" and commit == rows[name]["head"]
        links[name] = commit
    assert links.keys() == {"isla", "sail-riscv"}
    metadata_path = candidate / "specs/topic-version.json"
    metadata = read(metadata_path)
    assert metadata["topic"] == "memory"
    assert "pending" not in metadata.get("validation", {}).get("status", "").lower()
    for key in links:
        assert metadata["components"][key]["commit"] == links[key]
    exclusions = " ".join(metadata.get("excluded_isla_branches", []))
    assert "float" not in exclusions and "general-support" not in exclusions, exclusions
    isla, model = candidate / "isla", candidate / "sail-riscv"
    manifest_path = isla / "ir/provenance/manifest.json"
    manifest = read(manifest_path)
    assert manifest["model_commit"] == links["sail-riscv"] and manifest["model_dirty"] is False
    artifacts, seen = [], set()
    for item in manifest["artifacts"]:
        for path in item["paths"]:
            assert path not in seen and sha(isla / path) == item["sha256"], path
            seen.add(path)
        assert sha(manifest_path.parent / item["config"]) == item["config_sha256"]
        for path, expected in item["model_files"].items():
            assert sha(model / "model" / path) == expected["sha256"], path
        artifacts.append({"paths": item["paths"], "sha256": item["sha256"],
                          "config": item["config"], "model_files": len(item["model_files"])})
    assert seen == IR_PATHS
    assert metadata["ir"]["sha256"] == sha(isla / "rv64d.ir")
    original = read(ROOT / "agents/float_memory_merge_20261103/preflight/state-before.json")
    preserved = {}
    for key, record in original["repositories"].items():
        repo = ROOT / record["path"]
        head = git(repo, "rev-parse", "HEAD")
        files = {name: sha(repo / name) for name in record["changed_regular_files"]}
        for name, digest in files.items():
            assert digest == record["changed_regular_files"][name]["sha256"], (key, name)
        if not args.allow_promoted_original_heads or key.startswith("float-"):
            assert head == record["head"], key
            patch = subprocess.check_output(["git", "-C", str(repo), "diff", "--binary", "HEAD", "--"])
            assert hashlib.sha256(patch).hexdigest() == record["patch_sha256"], key
        preserved[key] = {"head": head, "original_head": record["head"], "dirty_file_sha256": files}
    output = {"verified_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "实际双亲提交/gitlinks/metadata/五IR与源文件/原dirty；不代表远端可获取或全域覆盖",
              "repositories": rows, "gitlinks": links, "metadata_sha256": sha(metadata_path),
              "manifest_sha256": sha(manifest_path), "artifacts": artifacts,
              "original_inputs": preserved, "pass": True}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
