#!/usr/bin/env python3
"""核对浮点 JSON → ELF → XiangShan/NEMU 批次的输入与实际退出。"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess


EXCEPTION = re.compile(r"exception pc ([0-9a-f]+) inst ([0-9a-f]+) cause ([0-9a-f]+)")


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--emulator", required=True, type=Path)
    parser.add_argument("--diff-so", required=True, type=Path)
    parser.add_argument("--xiangshan-source", required=True, type=Path)
    args = parser.parse_args()
    work, stage = args.work.resolve(), args.stage.resolve()
    all_input = read(work / "all-input.json")["gen"]
    supported = read(work / "supported-input.json")["gen"]
    unsupported = read(work / "unsupported-input.json")["gen"]
    require(len(all_input) == 1344 and len(supported) == 1322 and len(unsupported) == 22, "输入分母变化")
    all_keys = [key(entry) for entry in all_input]
    supported_keys = {key(entry) for entry in supported}
    unsupported_keys = {key(entry) for entry in unsupported}
    require(len(set(all_keys)) == len(all_keys), "输入 case-id 重复")
    require(supported_keys.isdisjoint(unsupported_keys) and supported_keys | unsupported_keys == set(all_keys), "输入分区不守恒")
    require(len({entry["source_file"] for entry in all_input}) == 51, "标量目标数不是 51")
    require(all(entry["ret_val"].startswith("Retire_Success") and entry["source_file"] in {
        "rv64_zFCVT_BF16_S.json", "rv64_zFCVT_S_BF16.json"
    } for entry in unsupported), "不支持集混入其它指令")

    elf_dir = work / "supported-elf"
    manifest = read(elf_dir / "manifest.json")
    results = read(elf_dir / "results.json")
    result_by_id = {record["id"]: record for record in results}
    require(len(manifest) == len(supported) == len(results) == len(result_by_id), "ELF/结果数量不守恒")
    for index, (entry, case) in enumerate(zip(supported, manifest)):
        case_id = f"case-{index:03d}"
        require(case["id"] == case_id and case["source_file"] == entry["source_file"], f"{case_id} 来源错配")
        require(case["encoding"] == entry["test-ins-encdec"] and case["instruction"] == entry["test-ins"], f"{case_id} 指令错配")
        require(case.get("elf") and digest(Path(case["elf"])) == case["sha256"], f"{case_id} ELF 哈希错配")
        result = result_by_id[case_id]
        require(result["category"] == "success" and result["returncode"] == 0, f"{case_id} 未成功")
        assembly = (elf_dir / case_id / "program.S").read_text()
        fp_loads = re.findall(r"(?m)^\s+fmv\.d\.x f\d+, t0$", assembly)
        fp_checks = re.findall(r"(?m)^\s+fmv\.x\.d t0, f\d+$", assembly)
        require(len(fp_loads) == 32 and len(fp_checks) == 32, f"{case_id} FPR 前后检查不完整")
        require("csrw fcsr, t0" in assembly and "csrr t0, fcsr" in assembly, f"{case_id} fcsr 前后检查不完整")

    primary = work / "unsupported-elf"
    retry = work / "unsupported-retry-elf"
    retry_entries = read(work / "unsupported-retry-input.json")["gen"]
    retry_index = {key(entry): index for index, entry in enumerate(retry_entries)}
    causes = Counter()
    confirmation = []
    for index, entry in enumerate(unsupported):
        name = f"case-{index:03d}"
        log = primary / name / "difftest.log"
        match = EXCEPTION.search(log.read_text(errors="replace"))
        source = "primary"
        if match is None:
            require(key(entry) in retry_index, f"{name} 无可用异常 trace")
            name = f"case-{retry_index[key(entry)]:03d}"
            log = retry / name / "difftest.log"
            match = EXCEPTION.search(log.read_text(errors="replace"))
            source = "retry"
        require(match is not None, f"{name} 未取得异常 trace")
        expected_word = f"{int(entry['test-ins-encdec'].split('h')[1].replace('_', ''), 16):08x}"
        require(match.group(2) == expected_word and int(match.group(3), 16) == 2, f"{name} 不是 BF16 payload Illegal Instruction")
        causes[expected_word] += 1
        confirmation.append({"source_file": entry["source_file"], "case_id": entry["case-id"],
                             "word": expected_word, "pc": match.group(1), "cause": 2,
                             "trace_source": source, "log_sha256": digest(log)})
    require(len(confirmation) == 22, "BF16 异常数不守恒")

    negative = read(work / "negative-elf/results.json")
    require(len(negative) == 1 and negative[0]["category"] == "failure", "故意改错的 FPR 期望没有失败")
    artifacts = {name: digest(work / name) for name in [
        "all-input.json", "supported-input.json", "unsupported-input.json", "unsupported-bf16.json",
        "supported-elf/manifest.json", "supported-elf/results.json", "unsupported-elf/results.json",
        "unsupported-retry-elf/results.json", "negative-elf/results.json",
    ]}
    report = {
        "schema": "xiangshan-float-json-difftest-v1",
        "input": {"targets": 51, "cases": 1344, "supported_cases": 1322,
                  "supported_retire": sum(entry["ret_val"].startswith("Retire_Success") for entry in supported),
                  "supported_illegal": sum(entry["ret_val"].startswith("Illegal_Instruction") for entry in supported)},
        "supported": {"elf_built": len(manifest), "difftest_pass": len(results),
                      "emulator_exit_codes": dict(Counter(str(result["returncode"]) for result in results)),
                      "post_check": "32 raw FPR values and fcsr checked against Isla after payload"},
        "unsupported_bf16": {"cases": len(confirmation), "words": dict(causes), "traces": confirmation},
        "negative_control": {"expected_failure": True, "result": negative[0]["category"]},
        "provenance": {"ir_sha256": digest(stage / "rv64d.ir"),
                       "isla_binary_sha256": digest(stage / "target/release/isarch"),
                       "config_sha256": digest(stage / "configs/riscv64_difftest_fd.toml"),
                       "isla_exec_sha256": digest(stage / "src/isarch/exec.rs"),
                       "xiangshan_source_head": subprocess.check_output([
                           "git", "-C", str(args.xiangshan_source), "rev-parse", "HEAD"
                       ], text=True).strip(),
                       "xiangshan_emu_sha256": digest(args.emulator),
                       "nemu_diffso_sha256": digest(args.diff_so),
                       "compiler_version": subprocess.check_output([
                           "riscv64-unknown-elf-gcc", "--version"
                       ], text=True).splitlines()[0],
                       "pipeline_sha256": digest(Path(__file__).with_name("pipeline.py"))},
        "artifacts_sha256": artifacts,
    }
    output = work / "audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"核账通过：{len(results)}/1322 可支持用例；22/22 BF16 payload 均 cause 2；负对照失败")


if __name__ == "__main__":
    main()
