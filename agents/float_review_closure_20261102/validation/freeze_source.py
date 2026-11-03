#!/usr/bin/env python3
"""最终提交后记录一个源码树的全部已跟踪文件哈希。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def git(tree, *args):
    return subprocess.check_output(["git", "-C", str(tree), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--isla-source", action="store_true",
                        help="排除另行冻结的五份IR与其provenance清单")
    args = parser.parse_args()
    tree = args.tree.resolve(strict=True)
    head = git(tree, "rev-parse", "HEAD").decode().strip()
    if head != args.commit:
        raise ValueError(f"HEAD 不符：{head}")
    if subprocess.run(["git", "-C", str(tree), "diff", "--quiet", "HEAD", "--"], check=False).returncode:
        raise ValueError("已跟踪源码有未提交改动，不能冻结")
    names = [p.decode() for p in git(tree, "ls-files", "-z").split(b"\0") if p]
    if args.isla_source:
        names = [name for name in names if not (name.endswith(".ir") or
                                                name == "ir/provenance/manifest.json")]
    files = {name: hashlib.sha256((tree / name).read_bytes()).hexdigest() for name in names}
    result = {"commit": head, "scope": "isla-source-excluding-generated-ir" if args.isla_source
              else "all-tracked", "files": files}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as out:
        json.dump(result, out, indent=2, ensure_ascii=False)
        out.write("\n")
    print(f"{head}: {len(files)} 个已跟踪文件；{args.output}")


if __name__ == "__main__":
    main()
