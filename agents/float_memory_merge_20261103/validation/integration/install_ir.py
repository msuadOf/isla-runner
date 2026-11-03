#!/usr/bin/env python3
"""核对合流模型与四组生成记录，再将五份 IR 和 provenance 安装到候选 Isla。"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
ISLA = ROOT / "isla"
CONFIGS = {
    "rv64d_v128_e64": ("rv64d.json", ("rv64d.ir", "ir/rv64d_v128_e64.ir")),
    "rv32d": ("rv32d.json", ("rv32d.ir",)),
    "rv64d_v256_e64": ("rv64d_v256_e64.json", ("ir/rv64d_v256_e64.ir",)),
    "rv64d_v512_e64": ("rv64d_v512_e64.json", ("ir/rv64d_v512_e64.ir",)),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def check_workarounds(model, ir_hash):
    config_dir = model / "configs/isla/workarounds"
    configs = sorted(config_dir.glob("*.toml"))
    assert len(configs) == 79, len(configs)
    regions = anchors = hash_warnings = 0
    for path in configs:
        raw = path.read_text()
        limits = tomllib.loads(raw)["execution_limits"]
        assert limits["strict"] is False, path
        hash_warnings += limits["ir_sha256"] != ir_hash
        for region in limits.get("region_fork_limits", []):
            source = model / "model" / region["file"]
            lines = source.read_text().splitlines()
            start = (region["start_line"], region["start_column"])
            end = (region["end_line"], region["end_column"])
            assert 1 <= start[0] <= len(lines) and 1 <= end[0] <= len(lines), (path, region)
            assert start < end, (path, region)
            assert 1 <= start[1] <= len(lines[start[0] - 1]) + 1, (path, region)
            assert 1 <= end[1] <= len(lines[end[0] - 1]) + 1, (path, region)
            regions += 1
        for match in re.finditer(r"(?m)^# Sail (?:start|end)\s+(\d+):\s*(.*)$", raw):
            following = raw[match.end():]
            source_match = re.search(r'(?m)^file = "([^"]+)"', following)
            assert source_match is not None, path
            source = model / "model" / source_match.group(1)
            line = int(match.group(1))
            lines = source.read_text().splitlines()
            assert 1 <= line <= len(lines) and lines[line - 1].strip() == match.group(2).strip(), (path, source, line)
            anchors += 1
    return {"configs": len(configs), "regions": regions, "anchors": anchors,
            "old_ir_hash_warnings": hash_warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    stage = ROOT / "agents/float_memory_merge_20261103/validation/generation" / args.batch
    model = args.model.resolve(strict=True)
    assert stage.is_relative_to(ROOT) and model.is_relative_to(ROOT)
    assert git(model, "rev-parse", "HEAD") == args.commit
    assert not git(model, "status", "--porcelain"), "模型树有未提交修改"
    source_path = stage / "source.json"
    source = json.loads(source_path.read_text())
    assert source["commit"] == args.commit
    assert (ROOT / source["model_tree"]).resolve(strict=True) == model
    names = [name.removeprefix("model/") for name in git(model, "ls-files", "model").splitlines()]
    assert names and set(names) == set(source["model_files"])
    assert all(sha(model / "model" / name) == source["model_files"][name] for name in names)
    audit_path = stage / "independent-input-audit.json"
    audit = json.loads(audit_path.read_text())
    assert audit["model_commit"] == args.commit
    assert audit["tracked_model_count"] == len(names) and audit["tracked_model_files"] == source["model_files"]
    assert audit["tool_file_count"] == len(audit["tool_files"])
    assert audit["tool_ctime_precedes_generation_start"] is True
    assert audit["source_unchanged_now"] is True
    assert audit["tool_files"] == source["tool_files_pre"]
    assert audit["generation_start_source_manifest_sha256"] == sha(source_path)
    assert audit["model_tree"] == source["model_tree"]
    assert all(sha(Path(name)) == value for name, value in audit["tool_files"].items())
    ordinary = json.loads((stage / "ordinary-strict/driver.json").read_text())
    assert ordinary["exit_code"] == 0 and ordinary["model_commit"] == args.commit
    assert ordinary["source_unchanged"] is True and ordinary["model_files"] == source["model_files"]
    strict_flags = {'--strict-var', '--strict-bitvector', '--strict-exponentials',
                    '--require-version', '0.20.1', '--all-modules'}
    assert strict_flags.issubset(ordinary['command'])
    assert {'--just-check', '--config', '--memo-z3-path'}.issubset(ordinary['command'])
    assert '-D' not in ordinary['command'] and '-isla' not in ordinary['command']
    assert ordinary['tool_files_unchanged'] and ordinary['compile_z3_unchanged']
    assert ordinary['actual_sail_binary'] in ordinary['live_executables']
    assert ordinary['compile_z3_live_hash_matches'] is True or ordinary['memo_copy'] is not None
    expected_paths = {path for _, paths in CONFIGS.values() for path in paths}
    old_manifest = json.loads(subprocess.check_output(
        ["git", "-C", str(ISLA), "show", "HEAD:ir/provenance/manifest.json"], text=True))
    assert old_manifest["schema"] == 1
    artifacts = []
    inputs = {}
    command_template = None
    for kind, (config_name, paths) in CONFIGS.items():
        output = stage / kind / (kind + ".ir")
        driver = json.loads((stage / kind / "driver.json").read_text())
        generation = json.loads((stage / kind / "generation.json").read_text())
        config_hash = sha(ISLA / "ir/provenance" / config_name)
        ir_hash = sha(output)
        assert driver["exit_code"] == generation["exit_code"] == 0
        assert driver["source_unchanged"] is True
        assert driver['tool_files_unchanged'] and driver['compile_z3_unchanged']
        assert driver['actual_sail_binary'] in driver['live_executables']
        assert driver['compile_z3_live_hash_matches'] is True or driver['memo_copy'] is not None
        assert driver["model_commit"] == generation["model_commit"] == args.commit
        assert driver["model_files"] == generation["model_files"] == source["model_files"]
        assert driver["config_sha256"] == generation["config_sha256"] == config_hash
        assert driver["ir_sha256"] == generation["ir_sha256"] == ir_hash
        assert generation["sail_launcher_sha256"] == source["sail_sha256"]
        assert generation["plugin_sha256"] == source["plugin_sha256"]
        assert strict_flags.issubset(generation['command'])
        assert {'-plugin', '-isla', '-D', 'SYMBOLIC', '--isla-output-dir',
                '--config', '--memo-z3-path'}.issubset(generation['command'])
        assert generation['command'][generation['command'].index('-D') + 1] == 'SYMBOLIC'
        assert driver['command'][1] == str(ISLA / 'scripts/regenerate_ir.py')
        assert driver['command'][driver['command'].index('--name') + 1] == kind
        assert generation["command"][0] == str(Path(source["sail_path"]).resolve(strict=True))
        assert generation["command"][2] == str(Path(source["plugin_path"]).resolve(strict=True))
        template = ["SAIL" if word == generation["command"][0] else
                    "PLUGIN" if word == generation["command"][2] else
                    "MEMO" if word == str(stage / kind / 'sail_smt_cache') else
                    "OUT" if word == str(stage / kind) else
                    "CONFIG" if word == str(ISLA / 'ir/provenance' / config_name) else
                    "NAME" if word == kind else word for word in generation["command"]]
        if command_template is None:
            command_template = template
        else:
            assert template == command_template
        artifacts.append({"paths": list(paths), "sha256": ir_hash,
                          "config": config_name, "config_sha256": config_hash,
                          "model_files": {name: {"sha256": value} for name, value in source["model_files"].items()},
                          "generation_seconds": generation["seconds"]})
        inputs[kind] = {"ir_sha256": ir_hash, "config_sha256": config_hash,
                        "paths": list(paths), "driver_sha256": sha(stage / kind / "driver.json"),
                        "generation_sha256": sha(stage / kind / "generation.json")}
    workarounds = check_workarounds(model, inputs["rv64d_v128_e64"]["ir_sha256"])
    new_manifest = dict(old_manifest)
    sail_reported_commit = re.search(r'@\s+([0-9a-f]{7,40})', source['sail_version'])
    assert sail_reported_commit, 'Sail版本未报告源码标识'
    new_manifest.update(model_commit=args.commit, model_dirty=False, sail_version=source["sail_version"],
                        sail_binary_sha256=audit["tool_files"][audit["actual_sail_binary"]],
                        sail_launcher_sha256=source["sail_sha256"], plugin_sha256=source["plugin_sha256"],
                        command_template=command_template,
                        sail_source_commit='工具链源码以本轮launcher/bin/标准库哈希清单固定',
                        sail_reported_commit=sail_reported_commit.group(1),
                        artifacts=artifacts, model_source_tree=source["model_tree"],
                        generation_audit={"path": str(audit_path.relative_to(ROOT)), "sha256": sha(audit_path),
                                          "model_file_count": len(names), "tool_file_count": len(audit["tool_files"])},
                        change="float 向 memory 合流：从合并模型生成并安装四配置 IR")
    candidate = HERE / "candidate-manifest.json"
    candidate.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n")
    report = {"model_commit": args.commit, "model_tree": str(model.relative_to(ROOT)),
              "stage": str(stage.relative_to(ROOT)), "source_sha256": sha(source_path),
              "audit_sha256": sha(audit_path), "model_files": len(names), "tool_files": len(audit["tool_files"]),
              "ordinary_strict": "PASS", "inputs": inputs, "workarounds": workarounds,
              "old_manifest_sha256": sha(ISLA / "ir/provenance/manifest.json"),
              "candidate_manifest_sha256": sha(candidate), "installed": args.install}
    if args.install:
        for kind, (_, paths) in CONFIGS.items():
            output = stage / kind / (kind + ".ir")
            for relative in paths:
                shutil.copy2(output, ISLA / relative)
                assert sha(ISLA / relative) == inputs[kind]["ir_sha256"]
        shutil.copy2(candidate, ISLA / "ir/provenance/manifest.json")
        assert sha(ISLA / "ir/provenance/manifest.json") == sha(candidate)
        subprocess.run(["git", "-C", str(ISLA), "add", "--", *sorted(expected_paths),
                        "ir/provenance/manifest.json"], check=True)
        report["installed_manifest_sha256"] = sha(ISLA / "ir/provenance/manifest.json")
    (HERE / ("installed.json" if args.install else "preflight.json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"model_commit": args.commit, "ir": {name: row["ir_sha256"] for name, row in inputs.items()},
                      "workarounds": workarounds, "installed": args.install}, ensure_ascii=False))


if __name__ == "__main__":
    main()
