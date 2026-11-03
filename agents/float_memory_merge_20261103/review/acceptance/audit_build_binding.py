#!/usr/bin/env python3
"""核正式 Release、其依赖 feature 指纹、实际库及独立 watchdog 短探针。"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
Z3_HASH = "899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--isla-source-manifest", type=Path)
    parser.add_argument("--release-log", type=Path)
    parser.add_argument("--sealed-isla-commit")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validation = args.validation.resolve()
    build, target = validation / "build", validation / "build/target/release"
    binary = target / "isarch"
    sources = []
    for path in (args.isla_source_manifest or build / "isla-source-stage-final.json", validation / "generation/merge-bf861b3e-20261104/model_source_manifest.json"):
        record = read(path)
        root = Path(record["root"])
        assert all(sha(root / relative) == digest for relative, digest in record["files"].items())
        actual_head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if actual_head != record["head"]:
            assert args.sealed_isla_commit == actual_head and root.name == "isla"
            parents = subprocess.check_output(["git", "-C", str(root), "show", "-s", "--format=%P", "HEAD"], text=True).split()
            assert parents == [record["head"], "591693df2bc32019ea300511509ed683df09522e"]
            assert not subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], text=True)
        sources.append({"manifest_sha256": sha(path), "head_at_build": record["head"], "actual_sealed_head": actual_head,
                        "all_snapshot_files_equal_actual_commit": True, "files": len(record["files"])})
    bin_fingerprints = list((target / ".fingerprint").glob("isla-*/bin-isarch.json"))
    assert len(bin_fingerprints) == 1
    bin_path = bin_fingerprints[0]
    bin_record = read(bin_path)
    required = {"smt-thread-interrupt", "tracetool"}
    assert required <= set(json.loads(bin_record["features"]))
    library_id = next(row[3] for row in bin_record["deps"] if row[1] == "isla_lib")
    libraries = []
    for path in (target / ".fingerprint").glob("isla-lib-*/lib-isla_lib.json"):
        fingerprint = int.from_bytes(bytes.fromhex(path.with_suffix("").read_text()), "little")
        if fingerprint == library_id:
            libraries.append(path)
    assert len(libraries) == 1
    lib_path = libraries[0]
    lib_record = read(lib_path)
    assert required <= set(json.loads(lib_record["features"]))
    assert lib_record["rustflags"] == bin_record["rustflags"]
    rlib = target / "deps" / ("libisla_lib-" + lib_path.parent.name.removeprefix("isla-lib-") + ".rlib")
    ldd = subprocess.check_output(["ldd", str(binary)], text=True)
    library = Path(re.search(r"libz3\.so\S*\s+=>\s+(\S+)", ldd)[1])
    assert sha(library) == Z3_HASH
    elf = subprocess.check_output(["readelf", "-d", str(binary)], text=True)
    assert "libz3.so.5.3" in elf and str(library.parent) in elf
    symbols = subprocess.check_output(["nm", "-D", str(binary)], text=True)
    assert " Z3_interrupt" in symbols
    version = subprocess.check_output([str(binary), "--version"], text=True, stderr=subprocess.STDOUT).strip()
    assert "1fd1d3613c1f34c4dff36cba3209b2234f6c6d2b" in version
    release_log = args.release_log or build / "release-final.log"
    log = release_log.read_text()
    assert "--features tracetool --features smt-thread-interrupt" in log
    assert "Finished `release`" in log
    environment = dict(os.environ)
    environment.pop("LD_LIBRARY_PATH", None)
    scratch = Path("tmp:/fm-acceptance-20261104")
    scratch.mkdir(exist_ok=True)
    probe_binary, delay_binary = scratch / "watchdog_probe", scratch / "watchdog_delay.so"
    compile_probe = ["rustc", "--edition=2021", "-C", "panic=abort", str(HERE / "watchdog_probe.rs"),
                     "--extern", "isla_lib=" + str(rlib), "-L", "dependency=" + str(target / "deps"),
                     "-L", "native=" + str(library.parent), "-C", "link-arg=-Wl,-rpath," + str(library.parent),
                     "-o", str(probe_binary)]
    compile_delay = ["cc", "-shared", "-fPIC", "-I", str(library.parent.parent / "include"),
                     str(HERE / "watchdog_delay.c"), "-ldl", "-o", str(delay_binary)]
    subprocess.run(compile_probe, check=True)
    subprocess.run(compile_delay, check=True)
    environment["LD_PRELOAD"] = str(delay_binary)
    probe = subprocess.run([str(probe_binary)], env=environment, text=True, capture_output=True)
    assert probe.returncode == 0 and probe.stderr.count("watchdog_called_Z3_interrupt") == 1
    assert re.fullmatch(r"watchdog_timeout=true limit_ms=10 wall_ms=\d+\n", probe.stdout)
    output = {"scope": "实际源码快照/正式release feature指纹与依赖绑定/官方库/延迟真实check短探针触发watchdog；不证明所有查询性能",
              "binary_sha256": sha(binary), "version": version, "source_manifests": sources,
              "build_log_sha256": sha(release_log), "bin_fingerprint_sha256": sha(bin_path),
              "lib_fingerprint_sha256": sha(lib_path), "features": json.loads(bin_record["features"]),
              "rlib_sha256": sha(rlib), "z3_sha256": sha(library), "ldd": ldd,
              "watchdog": {"probe_source_sha256": sha(HERE / "watchdog_probe.rs"),
                           "compile_probe": compile_probe, "compile_delay": compile_delay,
                           "delay_source_sha256": sha(HERE / "watchdog_delay.c"),
                           "probe_binary_sha256": sha(probe_binary),
                           "delay_binary_sha256": sha(Path(environment["LD_PRELOAD"])),
                           "stdout": probe.stdout, "stderr": probe.stderr, "exit": probe.returncode}, "pass": True}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
