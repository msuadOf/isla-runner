#!/usr/bin/env python3
"""Run the scoped Release regressions against the official Z3 library."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "isla-official-tests"
OUTPUT = HERE / "official-tests"
LIB = HERE / "official-target/release/deps/isla_lib-40254dc657f5900d"
ISLA = HERE / "official-target/release/deps/isla-d7184cd15581d6ee"
OFFICIAL_Z3 = Path("/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3")
FLAGS = "-L native=/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib -C link-arg=-Wl,-rpath,/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linked_z3(binary):
    ldd = subprocess.check_output(["ldd", str(binary)], text=True)
    lines = [line for line in ldd.splitlines() if "libz3.so" in line]
    assert len(lines) == 1, lines
    path = Path(lines[0].split("=>", 1)[1].strip().split(" (", 1)[0]).resolve()
    return path, ldd


def main():
    OUTPUT.mkdir(exist_ok=False)
    expected = OFFICIAL_Z3.resolve()
    binaries = {}
    for name, binary in (("isla_lib", LIB), ("isla", ISLA)):
        path, ldd = linked_z3(binary)
        assert path == expected and sha(path) == "899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970"
        binaries[name] = {"path": str(binary), "sha256": sha(binary), "z3_path": str(path), "z3_sha256": sha(path), "ldd": ldd}
    cases = [
        ("checkpoint_old", LIB, "smt::tests::isolated_checkpoint_preserves_definitions_and_rebases_only_new_constraints", True),
        ("checkpoint_new", LIB, "smt::tests::instruction_checkpoint_keeps_only_instruction_derived_assertions", True),
        ("encoding", ISLA, "isarch::encoding::tests", False),
        ("collector", ISLA, "collector_", False),
        ("enum_context", LIB, "smt::tests::get_multi_member_enum_const_after_checkpoint_replay", True),
    ]
    metadata = {
        "source_head": subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip(),
        "rustflags": FLAGS, "features": "default (empty)", "profile": "release",
        "cpu": 122, "sibling_cpu": 58, "cargo_build_jobs": 1,
        "binaries": binaries, "cases": {},
    }
    for name, binary, test_filter, exact in cases:
        command = ["taskset", "-c", "122", str(binary), test_filter, "--test-threads=1"]
        if exact:
            command.append("--exact")
        start = time.monotonic()
        process = subprocess.run(command, cwd=OUTPUT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = process.stdout.decode(errors="replace")
        (OUTPUT / f"{name}.log").write_text(output)
        summary = re.search(r"test result: .*", output)
        metadata["cases"][name] = {
            "command": command, "exit_code": process.returncode, "elapsed_s": time.monotonic() - start,
            "test_result_line": summary.group() if summary else None,
        }
        (OUTPUT / "result.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    required = ["checkpoint_old", "checkpoint_new", "encoding", "collector"]
    assert all(metadata["cases"][name]["exit_code"] == 0 for name in required), metadata["cases"]


if __name__ == "__main__":
    main()
