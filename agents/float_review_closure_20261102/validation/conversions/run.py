#!/usr/bin/env python3
"""Run the frozen integer-conversion helper and real-instruction fixtures."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def display(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return path.name


def execute(label, command, output, timeout, env=None):
    with (output / f"{label}.log").open("w") as log:
        try:
            result = subprocess.run([str(item) for item in command], cwd=ROOT, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout, env=env)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
    record = {"label": label,
              "command": [display(item) if isinstance(item, Path) else item for item in command],
              "exit_code": code, "log_sha256": sha(output / f"{label}.log")}
    if env is not None:
        seed_log = output / f"{label}-seed.log"
        record["seed"] = 17
        lines = seed_log.read_text().splitlines() if seed_log.exists() else []
        parsed = [re.fullmatch(r"parameter=(seed|random_seed) original=\d+ fixed=(\d+)", line)
                  for line in lines]
        record["seed_intercepted"] = (bool(lines) and all(parsed) and
                                      any(item.group(1) == "random_seed" for item in parsed) and
                                      all(int(item.group(2)) == 17 for item in parsed))
        record["seed_log_sha256"] = sha(seed_log) if seed_log.exists() else None
    return record


def verify_source_manifest(path, tree, expected_commit):
    data = json.loads(path.read_text())
    assert data["commit"] == expected_commit == git_head(tree)
    files = data.get("model_files", data.get("files"))
    assert files and len(files) > 100
    if "model_files" in data:
        files = {name: value for name, value in files.items() if name != "sail_smt_cache"}
        base = tree / "model"
    else:
        base = tree
    mismatches = [name for name, expected in files.items() if not (base / name).is_file()
                  or sha(base / name) != expected]
    assert not mismatches, mismatches[:10]
    return {"manifest_sha256": sha(path), "commit": expected_commit, "verified_files": len(files)}


def verify_official_z3(binary, output, expected_sha):
    env = dict(os.environ)
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("LD_PRELOAD", None)
    result = subprocess.run(["ldd", "-r", str(binary)], text=True, capture_output=True,
                            check=True, env=env)
    path = output / f"{binary.name}-ldd.log"
    path.write_text(result.stdout + result.stderr)
    assert "not found" not in result.stdout + result.stderr
    matches = re.findall(r"libz3\.so\.5\.3\s+=>\s+(\S+)", result.stdout)
    assert len(matches) == 1, (binary, matches)
    library = Path(matches[0]).resolve(strict=True)
    assert sha(library) == expected_sha, library
    return {"binary": display(binary), "linked_z3": display(library),
            "linked_z3_sha256": sha(library), "ldd_sha256": sha(path)}


def verify_results(path, fixture):
    rows = json.loads(path.read_text())
    cases = json.loads(fixture.read_text())
    assert len(rows) == len(cases), (path, len(rows), len(cases))
    assert [row["name"] for row in rows] == [case["name"] for case in cases]
    bad = [row["name"] for row in rows if not (row.get("sat") is True and
           row.get("difference_unsat") is True and row.get("structural_ok") is True and
           row.get("execute_result") == "Retire_Success" and row.get("execute_paths") == 1 and
           row.get("encode_paths") == 1 and row.get("decode_paths") == 2 and
           row.get("reencoded") == row.get("word"))]
    assert not bad, bad[:10]
    for row, case in zip(rows, cases):
        assert int(row["word"], 16) == int(case["word"], 16), case["name"]
        assert row["decoded_ctor"] == case["clause"], case["name"]
        assert row["expected_fields"] == case["expected_fields"], case["name"]
        for reg, value in case["expected"].items():
            assert int(row["registers"][reg], 16) == int(value, 16), (case["name"], reg)
    return {"cases": len(rows), "sat": len(rows), "difference_unsat": len(rows),
            "results_sha256": sha(path)}


def main():
    parser = argparse.ArgumentParser()
    for item in ("ir", "config", "helper_bin", "instruction_bin", "output",
                 "model_source", "isla_source", "generation_driver", "seed_preload",
                 "runner_build"):
        parser.add_argument("--" + item.replace("_", "-"), required=True, type=Path)
    for item in ("ir_sha256", "config_sha256", "model_commit", "isla_commit",
                 "z3_lib_sha256", "seed_preload_sha256"):
        parser.add_argument("--" + item.replace("_", "-"), required=True)
    args = parser.parse_args()
    paths = {item: getattr(args, item).resolve() for item in
             ("ir", "config", "helper_bin", "instruction_bin")}
    assert sha(paths["ir"]) == args.ir_sha256
    assert sha(paths["config"]) == args.config_sha256
    assert git_head(ROOT / ".worktree/runner-float/sail-riscv") == args.model_commit
    assert git_head(ROOT / ".worktree/runner-float/isla") == args.isla_commit
    model_source = verify_source_manifest(args.model_source, ROOT / ".worktree/runner-float/sail-riscv", args.model_commit)
    isla_source = verify_source_manifest(args.isla_source, ROOT / ".worktree/runner-float/isla", args.isla_commit)
    driver = json.loads(args.generation_driver.read_text())
    assert driver["model_commit"] == args.model_commit and driver["exit_code"] == 0
    assert driver["source_unchanged"] and driver["ir_sha256"] == args.ir_sha256
    assert paths["ir"] == args.generation_driver.resolve().parent / (driver["kind"] + ".ir")
    assert sha(args.seed_preload) == args.seed_preload_sha256
    build = json.loads(args.runner_build.read_text())
    assert build["isla_commit"] == args.isla_commit
    assert build["linked_z3_sha256"] == args.z3_lib_sha256
    for kind, binary in (("helper", paths["helper_bin"]), ("instruction", paths["instruction_bin"])):
        entries = [row for row in build["builds"] if row["kind"] == kind]
        assert len(entries) == 1 and entries[0]["exit_code"] == 0
        assert entries[0]["binary_sha256"] == sha(binary)
    imported_sources = {
        "helper": ROOT / "isla/test/softfloat_legacy/runner/src/main.rs",
        "instruction": ROOT / "agents/float_support_review/tools/e_nonmem/runner/main.rs",
    }
    assert build["imported_sources_sha256"] == {key: sha(path) for key, path in imported_sources.items()}
    fixtures = json.loads((HERE / "fixture-manifest.json").read_text())
    for name, expected in fixtures["output_sha256"].items():
        assert sha(HERE / name) == expected, name
    assert sha(ROOT / ".tmp/unified-backend-crosscheck/oracle-build/oracle") == fixtures["oracle_binary_sha256"]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    record = {"model_commit": args.model_commit, "isla_commit": args.isla_commit,
              "model_source": model_source, "isla_source": isla_source,
              "generation_driver_sha256": sha(args.generation_driver),
              "runner_build_manifest_sha256": sha(args.runner_build),
              "inputs": {name: {"path": display(path), "sha256": sha(path)} for name, path in paths.items()},
              "tactic": "Qfaufbv (fixed in both imported direct runners)",
              "scope": "direct helper and zexecute/decode runner; not isarch solve-state JSON or full Clause",
              "seed_preload": {"path": display(args.seed_preload.resolve()), "sha256": args.seed_preload_sha256},
              "fixture_manifest_sha256": sha(HERE / "fixture-manifest.json"),
              "source_sha256": {name: sha(HERE / name) for name in
                                ("prepare.py", "check_fixture.py", "run.py",
                                 "helper_runner/Cargo.toml", "helper_runner/src/main.rs",
                                 "instruction_runner/Cargo.toml", "instruction_runner/src/main.rs")},
              "imported_runner_source_sha256": {
                  "helper": sha(ROOT / "isla/test/softfloat_legacy/runner/src/main.rs"),
                  "instruction": sha(ROOT / "agents/float_support_review/tools/e_nonmem/runner/main.rs")},
              "stages": []}
    def save():
        (output / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    save()
    record["linked_z3"] = [verify_official_z3(paths[name], output, args.z3_lib_sha256)
                           for name in ("helper_bin", "instruction_bin")]
    save()
    checks = ["python3", HERE / "check_fixture.py"]
    stage = execute("fixture-check", checks, output, 120)
    record["stages"].append(stage)
    save()
    if stage["exit_code"] != 0:
        raise RuntimeError(stage)
    wrapped = output / "wrapped.ir"
    stage = execute("wrap", ["python3", ROOT / "isla/test/softfloat_legacy/wrap.py",
                             "--ir", paths["ir"], "--cases", HERE / "helpers.tsv", "--output", wrapped],
                    output, 120)
    record["stages"].append(stage)
    save()
    if stage["exit_code"] != 0:
        raise RuntimeError(stage)
    record["wrapped_ir_sha256"] = sha(wrapped)
    def seeded_env(label):
        env = dict(os.environ)
        env.pop("LD_LIBRARY_PATH", None)
        env.update(LD_PRELOAD=str(args.seed_preload.resolve()), ISLA_ABLATION_SEED="17",
                   ISLA_ABLATION_SEED_LOG=str(output / f"{label}-seed.log"))
        return env
    stage = execute("helpers", [paths["helper_bin"], wrapped, HERE / "helpers.tsv"],
                    output, 7200, seeded_env("helpers"))
    record["stages"].append(stage)
    record["helpers"] = {"expected_cases": fixtures["counts"]["helpers"],
                         "pass_lines": sum(line.startswith("PASS riscv_") for line in
                                           (output / "helpers.log").read_text().splitlines())}
    save()
    if stage["exit_code"] != 0 or not stage["seed_intercepted"] or record["helpers"]["pass_lines"] != fixtures["counts"]["helpers"]:
        raise RuntimeError("helper fixture failed")
    for kind in ("scalar", "vector"):
        result = output / f"{kind}-results.json"
        stage = execute(kind, [paths["instruction_bin"], paths["ir"], paths["config"],
                               HERE / f"{kind}-cases.json", result], output, 7200, seeded_env(kind))
        record["stages"].append(stage)
        save()
        if stage["exit_code"] != 0 or not stage["seed_intercepted"]:
            raise RuntimeError(f"{kind} fixture failed")
        record[kind] = verify_results(result, HERE / f"{kind}-cases.json")
        save()
    record["status"] = "PASS_DIRECTED_ONLY"
    save()
    print(json.dumps({key: record[key] for key in ("status", "helpers", "scalar", "vector")}, indent=2))


if __name__ == "__main__":
    main()
