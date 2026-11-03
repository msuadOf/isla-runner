#!/usr/bin/env python3
"""Build isolated direct-test runners against one frozen float Isla commit."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ISLA = ROOT / ".worktree/runner-float/isla"
SOURCES = {
    "helper": ROOT / "isla/test/softfloat_legacy/runner/src/main.rs",
    "instruction": ROOT / "agents/float_support_review/tools/e_nonmem/runner/main.rs",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--isla-commit", required=True)
    parser.add_argument("--z3-prefix", required=True, type=Path)
    args = parser.parse_args()
    commit = subprocess.check_output(["git", "-C", str(ISLA), "rev-parse", "HEAD"], text=True).strip()
    assert commit == args.isla_commit
    prefix = args.z3_prefix.resolve(strict=True)
    library = prefix / "lib/libz3.so.5.3"
    assert library.is_file()
    target = HERE / "target"
    env = dict(os.environ, CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(target),
               RUSTFLAGS=f"-L native={prefix / 'lib'} -C link-arg=-Wl,-rpath,{prefix / 'lib'}")
    source_before = {key: sha(path) for key, path in SOURCES.items()}
    record = {"isla_commit": commit, "linked_z3_sha256": sha(library),
              "imported_sources_sha256": source_before,
              "cargo_sources_sha256": {str(path.relative_to(HERE)): sha(path) for path in
                                      (HERE / "helper_runner/Cargo.toml", HERE / "helper_runner/src/main.rs",
                                       HERE / "instruction_runner/Cargo.toml", HERE / "instruction_runner/src/main.rs")},
              "rustflags": "official Z3 native library and matching rpath", "builds": []}
    for kind, crate in (("helper", "helper_runner"), ("instruction", "instruction_runner")):
        command = ["cargo", "build", "--offline", "--release", "--manifest-path", str(HERE / crate / "Cargo.toml")]
        with (HERE / f"build-{kind}.log").open("w") as log:
            code = subprocess.run(command, cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        binary = target / "release" / ("float-closure-conversion-helpers" if kind == "helper" else "float-closure-conversion-instructions")
        entry = {"kind": kind, "exit_code": code, "command": [*command[:-1], f"{crate}/Cargo.toml"],
                 "log_sha256": sha(HERE / f"build-{kind}.log")}
        if code == 0:
            entry.update(binary=str(binary.relative_to(ROOT)), binary_sha256=sha(binary))
        record["builds"].append(entry)
        (HERE / "runner-build.json").write_text(json.dumps(record, indent=2) + "\n")
        if code != 0:
            raise SystemExit(code)
    assert source_before == {key: sha(path) for key, path in SOURCES.items()}
    print(json.dumps({"isla_commit": commit, "builds": record["builds"]}, indent=2))


if __name__ == "__main__":
    main()
