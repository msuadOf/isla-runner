#!/usr/bin/env python3
"""核对候选，并在 --apply 时将 Isla isarch 仅快进到已验证的提交。"""
import argparse
import json
from pathlib import Path
import subprocess


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=root / "isla")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name("delivery.json").read_text())
    candidate = root / manifest["candidate_path"]
    commit = manifest["candidate_commit"]
    base = manifest["base_commit"]
    assert git(candidate, "rev-parse", "feat/cow-local-frame") == commit, "候选分支已变化"
    assert not git(candidate, "status", "--porcelain"), "候选有未提交修改"
    assert git(candidate, "rev-parse", commit + "^") == base, "候选基线不符"
    assert git(args.repo, "branch", "--show-current") == "isarch", "目标必须检出 isarch"
    assert not git(args.repo, "status", "--porcelain"), "目标有未提交修改，请保留并处理后重试"
    current = git(args.repo, "rev-parse", "HEAD")
    assert current in (base, commit), "主线已变化，须重新评估，不能覆盖"
    if current == commit:
        print(json.dumps({"status": "already_integrated", "commit": commit}))
        return
    probe = subprocess.run(["git", "-C", str(args.repo), "rev-parse", "--verify", "refs/heads/feat/cow-local-frame"], capture_output=True, text=True)
    if probe.returncode == 0:
        assert probe.stdout.strip() == commit, "目标同名 feature 分支不同，不能覆盖"
    if not args.apply:
        print(json.dumps({"status": "preflight_pass", "base": base, "candidate": commit}))
        return
    subprocess.run(["git", "-C", str(args.repo), "fetch", "--no-tags", str(candidate), commit], check=True)
    if probe.returncode != 0:
        subprocess.run(["git", "-C", str(args.repo), "branch", "feat/cow-local-frame", commit], check=True)
    subprocess.run(["git", "-C", str(args.repo), "merge", "--ff-only", commit], check=True)
    assert git(args.repo, "rev-parse", "HEAD") == commit
    assert not git(args.repo, "status", "--porcelain")
    print(json.dumps({"status": "complete", "commit": commit, "parent_gitlink": "unchanged", "pushed": False}))


if __name__ == "__main__":
    main()
