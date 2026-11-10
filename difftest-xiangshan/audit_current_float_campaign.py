#!/usr/bin/env python3
"""Audit the local XiangShan/NEMU replay of the frozen scalar FP batch."""

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess


EXCEPTION = re.compile(r"exception pc ([0-9a-f]+) inst ([0-9a-f]+) cause ([0-9a-f]+)")
COMMIT = re.compile(r"commit pc ([0-9a-f]+)")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read(path: Path):
    return json.loads(path.read_text())


def key(entry: dict) -> tuple[str, int]:
    return entry["source_file"], entry["case-id"]


def symbol(elf: Path, name: str) -> int:
    output = subprocess.check_output(["riscv64-unknown-elf-nm", str(elf)], text=True)
    matches = [int(parts[0], 16) for line in output.splitlines()
               if (parts := line.split()) and len(parts) == 3 and parts[2] == name]
    require(len(matches) == 1, f"{elf}: symbol {name} missing or ambiguous")
    return matches[0]


def raw64(value: str) -> int:
    return int(value.split("'h", 1)[1].replace("_", ""), 16)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--emulator", required=True, type=Path)
    parser.add_argument("--diff-so", required=True, type=Path)
    parser.add_argument("--xiangshan-source", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work, stage = args.work.resolve(), args.stage.resolve()
    emulator, diff_so = args.emulator.resolve(), args.diff_so.resolve()
    xiangshan = args.xiangshan_source.resolve()
    for path in (work, stage, emulator, diff_so, xiangshan):
        require(path.is_relative_to(root), f"path outside current workspace: {path}")

    all_data = read(work / "all-input.json")
    all_input = all_data["gen"]
    require(all_data["metadata"]["vlen_bits"] == 128 and
            all_data["metadata"]["selection_count"] == 1344,
            "input VLEN/selection metadata mismatch")
    supported = read(work / "supported-input.json")["gen"]
    unsupported = read(work / "unsupported-input.json")["gen"]
    all_keys = [key(entry) for entry in all_input]
    supported_keys = {key(entry) for entry in supported}
    unsupported_keys = {key(entry) for entry in unsupported}
    require((len(all_input), len(supported), len(unsupported)) == (1344, 1322, 22), "input count mismatch")
    require(len(set(all_keys)) == len(all_keys), "duplicate input key")
    require(supported_keys.isdisjoint(unsupported_keys) and
            supported_keys | unsupported_keys == set(all_keys), "input partition mismatch")
    source_files = sorted({entry["source_file"] for entry in all_input})
    require(len(source_files) == 51, "target count mismatch")
    frozen_rows = {}
    frozen_hashes = {}
    for name in source_files:
        path = stage / "output" / name
        source = read(path)
        require(source["summary"]["complete"] is True and
                source["summary"]["emitted"] == len(source["gen"]),
                f"{name}: frozen solve JSON incomplete")
        frozen_hashes[name] = digest(path)
        for entry in source["gen"]:
            row_key = (name, entry["case-id"])
            require(row_key not in frozen_rows, f"{name}: duplicate frozen case ID")
            frozen_rows[row_key] = entry
    require(len(frozen_rows) == len(all_input), "frozen output/input count mismatch")
    for entry in all_input:
        original = frozen_rows.get(key(entry))
        require(original is not None and
                {name: value for name, value in entry.items() if name != "source_file"} == original,
                f"{key(entry)}: input differs from frozen solve JSON")

    primary = work / "current-supported-elf"
    manifest = read(primary / "manifest.json")
    r1 = [json.loads(line) for line in (work / "current-supported-r1.ndjson").read_text().splitlines()]
    r2 = read(work / "current-supported-r2-elf" / "results.json")
    r3 = read(work / "current-supported-r3-elf" / "results.json")
    require(len(manifest) == len(r2) == 1322 and len(r3) == 5, "supported result count mismatch")
    r1_success = {record["id"]: record for record in r1 if record["category"] == "success"}
    r2_by_id = {record["id"]: record for record in r2}
    r3_by_id = {record["id"]: record for record in r3}
    require(len(r1_success) == 104 and len(r2_by_id) == 1322 and len(r3_by_id) == 5,
            "retry ID count mismatch")
    require({record["id"] for record in r2 if record["category"] != "success"} == set(r3_by_id),
            "r3 does not exactly cover r2 failures")
    require(all(r2_by_id[case_id] == record for case_id, record in r1_success.items()),
            "r1 successes were changed during r2")
    r1_summary = read(work / "current-supported-r1-summary.json")
    require(r1_summary["record_sha256"] == digest(work / "current-supported-r1.ndjson"),
            "r1 record archive changed")
    for case_id, expected in r1_summary["failed_log_sha256"].items():
        require(digest(work / "current-supported-r1-fail-logs" / f"{case_id}.log") == expected,
                f"{case_id}: r1 failure log archive changed")
    r2_summary = read(work / "current-supported-r2-timeout-summary.json")
    require(r2_summary["r2_results_sha256"] == digest(work / "current-supported-r2-elf" / "results.json") and
            set(r2_summary["retry_ids"]) == set(r3_by_id), "r2 retry archive mismatch")
    for case_id, expected in r2_summary["timeout_log_sha256"].items():
        require(digest(work / "current-supported-r2-timeout-logs" / f"{case_id}.log") == expected,
                f"{case_id}: r2 timeout log archive changed")

    ledger = []
    for index, (entry, case) in enumerate(zip(supported, manifest)):
        case_id = f"case-{index:03d}"
        require(case["id"] == case_id and case["source_file"] == entry["source_file"],
                f"{case_id}: source mismatch")
        require(case["instruction"] == entry["test-ins"] and
                case["encoding"] == entry["test-ins-encdec"], f"{case_id}: payload mismatch")
        elf = Path(case["elf"]).resolve()
        require(elf.is_relative_to(root) and elf.is_file() and digest(elf) == case["sha256"],
                f"{case_id}: ELF hash mismatch")
        record = r3_by_id.get(case_id, r2_by_id[case_id])
        require(record["category"] == "success" and record["returncode"] == 0,
                f"{case_id}: no final success")
        require(record["id"] == case_id and record["elf"] == case["elf"] and
                record["sha256"] == case["sha256"], f"{case_id}: result/ELF mismatch")
        log = Path(record["log"]).resolve()
        require(log.is_relative_to(root) and "HIT GOOD TRAP" in log.read_text(),
                f"{case_id}: GOODTRAP log missing")
        assembly = (primary / case_id / "program.S").read_text()
        require(len(re.findall(r"(?m)^\s+fmv\.d\.x f\d+, t0$", assembly)) == 32 and
                len(re.findall(r"(?m)^\s+fmv\.x\.d t0, f\d+$", assembly)) == 32,
                f"{case_id}: incomplete raw FPR load/check")
        require("csrw fcsr, t0" in assembly and "csrr t0, fcsr" in assembly,
                f"{case_id}: incomplete fcsr load/check")
        ledger.append({"id": case_id, "source_file": entry["source_file"],
                       "case_id": entry["case-id"], "encoding": case["encoding"],
                       "elf_sha256": case["sha256"], "result_origin": "r3" if case_id in r3_by_id else "r2"})

    unsupported_dir = work / "current-unsupported-elf"
    unsupported_manifest = read(unsupported_dir / "manifest.json")
    unsupported_results = read(unsupported_dir / "results.json")
    require(len(unsupported_manifest) == len(unsupported_results) == 22, "BF16 result count mismatch")
    unsupported_by_id = {record["id"]: record for record in unsupported_results}
    traces = []
    for index, (entry, case) in enumerate(zip(unsupported, unsupported_manifest)):
        case_id = f"case-{index:03d}"
        require(case["id"] == case_id and case["source_file"] == entry["source_file"],
                f"{case_id}: BF16 source mismatch")
        require(case["instruction"] == entry["test-ins"] and
                case["encoding"] == entry["test-ins-encdec"] and
                digest(Path(case["elf"])) == case["sha256"],
                f"{case_id}: BF16 payload/ELF mismatch")
        require(entry["ret_val"].startswith("Retire_Success") and entry["source_file"] in
                {"rv64_zFCVT_BF16_S.json", "rv64_zFCVT_S_BF16.json"},
                f"{case_id}: BF16 partition mismatch")
        result = unsupported_by_id[case_id]
        require(result["category"] == "failure", f"{case_id}: BF16 unexpectedly passed")
        log = Path(result["log"]).resolve()
        match = EXCEPTION.search(log.read_text(errors="replace"))
        expected_word = int(entry["test-ins-encdec"].split("h", 1)[1].replace("_", ""), 16)
        require(match is not None and int(match.group(2), 16) == expected_word and
                int(match.group(3), 16) == 2 and
                int(match.group(1), 16) == symbol(Path(case["elf"]), "payload_ins"),
                f"{case_id}: no payload Illegal trace")
        traces.append({"id": case_id, "source_file": entry["source_file"],
                       "case_id": entry["case-id"], "word": f"{expected_word:08x}",
                       "pc": match.group(1), "cause": 2, "log_sha256": digest(log)})

    smoke = read(work / "smoke-input.json")["gen"][0]
    negative_input = read(work / "negative-input.json")["gen"][0]
    expected_negative = copy.deepcopy(smoke)
    expected_negative["isa-state-post"]["f0"] = negative_input["isa-state-post"]["f0"]
    require(expected_negative == negative_input and
            raw64(smoke["isa-state-post"]["f0"]) ^
            raw64(negative_input["isa-state-post"]["f0"]) == 1,
            "negative control is not a one-bit f0 post change")
    negative = read(work / "current-negative-elf" / "results.json")
    require(len(negative) == 1 and negative[0]["category"] == "failure", "negative did not fail")
    negative_log = Path(negative[0]["log"]).read_text(errors="replace")
    negative_elf = Path(read(work / "current-negative-elf" / "manifest.json")[0]["elf"])
    park = symbol(negative_elf, "fp_post_park_f0")
    require("HIT GOOD TRAP" not in negative_log and
            sum(int(pc, 16) == park for pc in COMMIT.findall(negative_log)) >= 2,
            "negative did not park at f0 post check")

    artifacts = ["all-input.json", "supported-input.json", "unsupported-input.json",
                 "current-supported-elf/manifest.json", "current-supported-r1.ndjson",
                 "current-supported-r2-elf/results.json", "current-supported-r3-elf/results.json",
                 "current-unsupported-elf/results.json", "current-negative-elf/results.json",
                 "current-workspace-build-r2.log"]
    report = {
        "schema": "xiangshan-float-json-difftest-current-workspace-v1",
        "input": {"targets": 51, "cases": 1344, "supported_cases": 1322,
                  "supported_retire": sum(entry["ret_val"].startswith("Retire_Success") for entry in supported),
                  "supported_illegal": sum(entry["ret_val"].startswith("Illegal_Instruction") for entry in supported)},
        "supported": {"final_pass": len(ledger),
                      "r2_pass": sum(record["category"] == "success" for record in r2),
                      "r3_recovered": len(r3),
                      "post_check": "32 raw FPR values and fcsr checked after payload",
                      "cases": ledger},
        "unsupported_bf16": {"cases": len(traces), "traces": traces},
        "negative_control": {"expected_failure": True, "park_symbol": "fp_post_park_f0",
                             "park_pc": f"{park:016x}", "log_sha256": digest(Path(negative[0]["log"]))},
        "provenance": {
            "ir_sha256": digest(stage / "rv64d.ir"),
            "isla_binary_sha256": digest(stage / "target/release/isarch"),
            "config_sha256": digest(stage / "configs/riscv64_difftest_fd.toml"),
            "isla_exec_sha256": digest(stage / "src/isarch/exec.rs"),
            "frozen_solve_output_sha256": frozen_hashes,
            "xiangshan_source_head": subprocess.check_output(
                ["git", "-C", str(xiangshan), "rev-parse", "HEAD"], text=True).strip(),
            "xiangshan_build_config": "MinimalConfig",
            "emu_build_threads": 4,
            "elf_vlen_bits": 128,
            "xiangshan_emu_sha256": digest(emulator),
            "nemu_diffso_sha256": digest(diff_so),
            "pipeline_sha256": digest(Path(__file__).with_name("pipeline.py")),
            "compiler_version": subprocess.check_output(
                ["riscv64-unknown-elf-gcc", "--version"], text=True).splitlines()[0],
        },
        "artifacts_sha256": {name: digest(work / name) for name in artifacts},
    }
    output = work / "current-workspace-audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"核账通过：{len(ledger)}/1322 GOODTRAP，22/22 BF16 payload cause 2，负对照停在 f0")


if __name__ == "__main__":
    main()
