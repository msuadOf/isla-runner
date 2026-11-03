#!/usr/bin/env python3
"""独立核合并模型的普通 strict、四配置生成及五安装 IR 来源。"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    model, isla = args.candidate / "sail-riscv", args.candidate / "isla"
    source, manifest = read(args.generation / "source.json"), read(args.manifest)
    head = subprocess.check_output(["git", "-C", str(model), "rev-parse", "HEAD"], text=True).strip()
    assert head == source["commit"] == manifest["model_commit"]
    assert manifest["model_dirty"] is False
    assert subprocess.check_output(["git", "-C", str(model), "status", "--porcelain"], text=True) == ""
    tracked = subprocess.check_output(["git", "-C", str(model), "ls-tree", "-rz", "--name-only", head, "model/"])
    tracked = {name.decode()[6:] for name in tracked.split(b"\0") if name}
    assert source["model_files"].keys() == tracked
    for relative, expected in source["model_files"].items():
        current = model / "model" / relative
        assert sha(current) == expected
        blob = subprocess.check_output(["git", "-C", str(model), "show", f"{head}:model/{relative}"])
        assert hashlib.sha256(blob).hexdigest() == expected
    for path, expected in source["tool_files_pre"].items():
        assert sha(Path(path)) == expected, path
    assert sha(Path(source["compile_z3_path"])) == source["compile_z3_sha256"]
    assert sha(Path(source["actual_sail_binary"])) == manifest["sail_binary_sha256"]
    assert sha(Path(source["plugin_path"])) == manifest["plugin_sha256"]
    rows = []
    mapping = {"ordinary-strict": "rv64d.json", "rv64d_v128_e64": "rv64d.json", "rv32d": "rv32d.json",
               "rv64d_v256_e64": "rv64d_v256_e64.json", "rv64d_v512_e64": "rv64d_v512_e64.json"}
    actual = {}
    for name, config in mapping.items():
        directory = args.generation / name
        driver = read(directory / "driver.json")
        assert driver["exit_code"] == 0 and driver["kind"] == name and driver["model_commit"] == head
        assert driver["model_files"] == source["model_files"] and driver["tool_files_pre"] == source["tool_files_pre"]
        if name == "ordinary-strict":
            command = driver["executed_command"]
        else:
            generated = read(directory / "generation.json")
            assert generated["exit_code"] == 0 and generated["model_commit"] == head
            assert generated["model_files"] == source["model_files"]
            assert generated["plugin_sha256"] == source["plugin_sha256"]
            command = generated["command"]
        assert all(flag in command for flag in ("--strict-var", "--strict-bitvector", "--strict-exponentials", "--all-modules"))
        assert ("SYMBOLIC" in command) == (name != "ordinary-strict")
        assert ("--just-check" in command) == (name == "ordinary-strict")
        assert command[command.index("--config") + 1] == str((isla / "ir/provenance" / config).resolve())
        assert sha(isla / "ir/provenance" / config) == driver["config_sha256"]
        assert driver["compile_z3_path"] in driver["live_executables"]
        assert driver["live_executables"][driver["compile_z3_path"]] == source["compile_z3_sha256"]
        assert driver["actual_sail_binary"] in driver["live_executables"]
        for path, digest in driver["live_executables"].items():
            assert sha(Path(path)) == digest
        irhash = None
        if name != "ordinary-strict":
            irhash = sha(directory / (name + ".ir"))
            assert irhash == driver["ir_sha256"]
            actual[config] = irhash
        rows.append({"kind": name, "exit": 0, "seconds": driver["seconds"], "driver_sha256": sha(directory / "driver.json"),
                     "log_sha256": sha(directory / ("driver.log" if name == "ordinary-strict" else "generation.log")), "ir_sha256": irhash})
    paths = set()
    for artifact in manifest["artifacts"]:
        assert artifact["sha256"] == actual[artifact["config"]]
        assert artifact["config_sha256"] == sha(isla / "ir/provenance" / artifact["config"])
        assert {relative: value["sha256"] for relative, value in artifact["model_files"].items()} == source["model_files"]
        for relative in artifact["paths"]:
            assert relative not in paths and sha(isla / relative) == artifact["sha256"]
            paths.add(relative)
    assert paths == {"rv64d.ir", "rv32d.ir", "ir/rv64d_v128_e64.ir", "ir/rv64d_v256_e64.ir", "ir/rv64d_v512_e64.ir"}
    output = {"scope": "实际普通strict+四配置生成退出、合并提交全部模型文件、工具/配置和五安装IR独立哈希核对",
              "model_commit": head, "model_files": len(tracked), "tool_files": len(source["tool_files_pre"]),
              "compile_z3": source["compile_z3_version"], "compile_z3_sha256": source["compile_z3_sha256"],
              "sail_binary_sha256": manifest["sail_binary_sha256"], "manifest_sha256": sha(args.manifest),
              "source_sha256": sha(args.generation / "source.json"), "rows": rows, "pass": True}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
