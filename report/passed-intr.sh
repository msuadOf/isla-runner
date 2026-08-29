#!/usr/bin/env bash
# Isla symbolic execution output -> assembly-gen -> ELF -> difftest -> report.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ISLA_OUTPUT="$ROOT_DIR/isla/output"
ISLA_LOG_DIR="$ROOT_DIR/isla/logs_todo"
ISLA_CLAUSE_REPORT="$ROOT_DIR/isla/report_clause.md"
ASMGEN_DIR="$ROOT_DIR/assembly-gen"
ASMGEN_INPUT="$ASMGEN_DIR/input"
ASMGEN_OUTPUT="$ASMGEN_DIR/assembly_output"
BUILD_DIR="$ASMGEN_DIR/build"
DIFFTEST_DIR="$ROOT_DIR/difftest"
ELF_DIR="$DIFFTEST_DIR/elfs"
DIFFTEST_RESULT="$DIFFTEST_DIR/difuzz-rtl/run_difftest/out/results.txt"
REPORT_FILE="$ROOT_DIR/report/passed-intr-report.md"

count_glob() {
    local pattern="$1"
    find "$(dirname "$pattern")" -maxdepth 1 -type f -name "$(basename "$pattern")" 2>/dev/null | wc -l
}

step0_check_isla() {
    echo "========================================="
    echo "[Step 0] Check Isla output"
    echo "========================================="

    local json_count testcase_count
    json_count="$(count_glob "$ISLA_OUTPUT/*.json")"
    if [ "$json_count" -eq 0 ]; then
        echo "error: no JSON files under $ISLA_OUTPUT; run Isla symbolic execution first" >&2
        exit 1
    fi

    testcase_count="$(
        python3 - "$ISLA_OUTPUT" <<'PY'
import glob
import json
import os
import sys

total = 0
for path in glob.glob(os.path.join(sys.argv[1], "*.json")):
    try:
        with open(path, "r", encoding="utf-8") as f:
            total += len(json.load(f).get("gen", []))
    except Exception:
        pass
print(total)
PY
    )"
    echo "Isla JSON files: $json_count"
    echo "Isla testcases: $testcase_count"
    echo
}

step1_copy_json() {
    echo "========================================="
    echo "[Step 1] Copy Isla JSON -> assembly-gen/input"
    echo "========================================="

    mkdir -p "$ASMGEN_INPUT"
    find "$ASMGEN_INPUT" -maxdepth 1 -type f -name '*.json' -delete
    find "$ISLA_OUTPUT" -maxdepth 1 -type f -name '*.json' -exec cp -t "$ASMGEN_INPUT" {} +
    echo "Copied $(count_glob "$ASMGEN_INPUT/*.json") JSON files"
    echo
}

step2_gen_asm() {
    echo "========================================="
    echo "[Step 2] Generate assembly with assembly-gen"
    echo "========================================="

    make -C "$ASMGEN_DIR" gen

    echo "Generated $(count_glob "$ASMGEN_OUTPUT/*.S") assembly files"
    echo
}

step3_compile() {
    echo "========================================="
    echo "[Step 3] Compile assembly -> ELF"
    echo "========================================="

    rm -rf "$BUILD_DIR"
    make -C "$ASMGEN_DIR/resource/riscv"
    if ! make -k -C "$ASMGEN_DIR" compile; then
        echo "warning: some assembly files failed to compile; continuing with generated ELF files" >&2
    fi

    rm -rf "$ELF_DIR"
    mkdir -p "$ELF_DIR"
    find "$BUILD_DIR" -maxdepth 1 -type f -name '*.elf' -exec cp -t "$ELF_DIR" {} +

    local elf_count
    elf_count="$(count_glob "$ELF_DIR/*.elf")"
    if [ "$elf_count" -eq 0 ]; then
        echo "error: no ELF files were compiled successfully" >&2
        exit 1
    fi
    echo "Compiled $elf_count ELF files"
    echo
}

step4_difftest() {
    echo "========================================="
    echo "[Step 4] Run difftest through difftest/run.sh"
    echo "========================================="

    local elf_count
    elf_count="$(count_glob "$ELF_DIR/*.elf")"
    if [ "$elf_count" -eq 0 ]; then
        echo "error: no ELF files under $ELF_DIR; run compile first" >&2
        exit 1
    fi

    local container_mount
    container_mount="$(
        docker inspect diffuzzrtl \
            --format '{{range .Mounts}}{{if eq .Destination "/home/host/difftest"}}{{.Source}}{{end}}{{end}}' \
            2>/dev/null || true
    )"
    if [ -n "$container_mount" ] && [ "$container_mount" != "$DIFFTEST_DIR" ]; then
        echo "Existing diffuzzrtl container is mounted from $container_mount; recreating for $DIFFTEST_DIR"
        docker rm -f diffuzzrtl >/dev/null
    fi

    rm -rf "$DIFFTEST_DIR/difuzz-rtl/run_difftest/out"
    (
        cd "$DIFFTEST_DIR"
        ./run.sh
    )
    echo
}

step5_report() {
    echo "========================================="
    echo "[Step 5] Generate report"
    echo "========================================="

    python3 - "$ROOT_DIR" <<'PY'
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

root = sys.argv[1]
isla_dir = os.path.join(root, "isla/output")
log_dir = os.path.join(root, "isla/logs_todo")
clause_report = os.path.join(root, "isla/report_clause.md")
asm_dir = os.path.join(root, "assembly-gen/assembly_output")
build_dir = os.path.join(root, "assembly-gen/build")
elf_dir = os.path.join(root, "difftest/elfs")
difftest_result = os.path.join(root, "difftest/difuzz-rtl/run_difftest/out/results.txt")
report_file = os.path.join(root, "report/passed-intr-report.md")


def instr_from_json_name(path):
    name = os.path.basename(path)
    if name.startswith("rv64_") and name.endswith(".json"):
        return name[len("rv64_") : -len(".json")]
    if name.endswith(".json"):
        return name[:-len(".json")]
    return name


def sanitize_filename(name, max_length=200):
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", str(name))
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:max_length]


def generate_output_filename(pretty_name, test_ins, ret_val=""):
    max_part_length = 200
    sanitized_pretty = sanitize_filename(pretty_name, max_part_length)
    sanitized_test = sanitize_filename(test_ins, max_part_length)
    if ret_val:
        sanitized_ret = sanitize_filename(ret_val, max_part_length)
        base = f"{sanitized_pretty}_{sanitized_test}_{sanitized_ret}"
        if len(base) > 245:
            total_len = len(sanitized_pretty) + len(sanitized_test) + len(sanitized_ret)
            pretty_len = int(245 * len(sanitized_pretty) / total_len)
            test_len = int(245 * len(sanitized_test) / total_len)
            ret_len = 245 - pretty_len - test_len - 2
            sanitized_pretty = sanitize_filename(pretty_name, pretty_len)
            sanitized_test = sanitize_filename(test_ins, test_len)
            sanitized_ret = sanitize_filename(ret_val, ret_len)
            base = f"{sanitized_pretty}_{sanitized_test}_{sanitized_ret}"
        return f"{base}.S"

    base = f"{sanitized_pretty}_{sanitized_test}"
    if len(base) > 246:
        total_len = len(sanitized_pretty) + len(sanitized_test)
        pretty_len = int(246 * len(sanitized_pretty) / total_len)
        test_len = 246 - pretty_len - 1
        sanitized_pretty = sanitize_filename(pretty_name, pretty_len)
        sanitized_test = sanitize_filename(test_ins, test_len)
        base = f"{sanitized_pretty}_{sanitized_test}"
    return f"{base}.S"


def expected_filenames(json_path, items):
    counter = {}
    out = []
    for item in items:
        arch = item.get("arch", {})
        base = generate_output_filename(
            arch.get("pretty-name", "unknown"),
            item.get("test-ins", "test"),
            item.get("ret_val", ""),
        )
        counter[base] = counter.get(base, 0) + 1
        if counter[base] == 1:
            final_name = base
        else:
            final_name = f"{base[:-2]}_{counter[base]}.S"
        out.append(final_name)
    return out


def read_isla_jsons():
    records = {}
    testcase_to_instr = {}
    for path in sorted(glob.glob(os.path.join(isla_dir, "*.json"))):
        instr = instr_from_json_name(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                items = json.load(f).get("gen", [])
        except Exception as exc:
            records[instr] = {"items": [], "json_error": str(exc), "asm": []}
            continue

        asm_names = expected_filenames(path, items)
        for asm_name in asm_names:
            testcase_to_instr[asm_name[:-2] + ".elf"] = instr
        records[instr] = {"items": items, "json_error": "", "asm": asm_names}
    return records, testcase_to_instr


def read_difftest_results():
    results = {}
    if not os.path.exists(difftest_result):
        return results

    with open(difftest_result, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            status = parts[0].strip()
            elf_name = os.path.basename(parts[1].strip())
            detail = parts[2].strip() if len(parts) > 2 else "-"
            results[elf_name] = (status, detail)
    return results


def read_log_status(instr):
    path = os.path.join(log_dir, f"{instr}.log")
    if not os.path.exists(path):
        return "NO_LOG", "missing Isla log"

    text = open(path, "r", encoding="utf-8", errors="replace").read()
    issues = []
    status = "UNKNOWN"
    if f"[DONE] {instr}" in text:
        status = "DONE"
    elif f"[TIMEOUT] {instr}" in text:
        status = "TIMEOUT"
        issues.append("timeout/path explosion")
    elif f"[ERROR] {instr}" in text:
        status = "ERROR"
        issues.append("execution error")

    if "执行错误:" in text:
        issue_counter = Counter()
        for line in text.splitlines():
            if "执行错误:" in line:
                issue_counter[line.split("执行错误:", 1)[1].strip()] += 1
        for msg, count in issue_counter.most_common(3):
            issues.append(f"{msg} ({count}x)")
    if "SymbolicLength" in text:
        issues.append("SymbolicLength limitation")
    if "NoFunction" in text:
        issues.append("missing Sail/primop function")
    if "Type(" in text and not any("Type(" in item for item in issues):
        issues.append("type conversion failure")
    if not issues and status == "DONE":
        issues.append("-")
    elif not issues:
        issues.append("see Isla log")
    return status, "; ".join(dict.fromkeys(issues))


def parse_clause_problem_groups():
    if not os.path.exists(clause_report):
        return {}

    text = open(clause_report, "r", encoding="utf-8", errors="replace").read()
    groups = {}
    problem_sections = {
        "有执行路径但含 subrange_internal 错误": "SymbolicLength/subrange_internal engine limitation",
        "浮点 stub 成功": "floating-point semantic stub; symbolic result only",
        "向量/配置类": "vector/config path executes, semantics may still need validation",
    }

    current = None
    for line in text.splitlines():
        if line.startswith("### "):
            title = line[4:].strip()
            current = problem_sections.get(title)
            continue
        if current and line.strip() and not line.startswith("#") and not line.startswith("-"):
            for token in re.findall(r"\bz[A-Za-z0-9_]+\b", line):
                groups[token] = current
    return groups


def summarize_instruction(instr, rec, results, issue_hint):
    generated = len(rec["items"])
    asm_names = rec["asm"]
    asm_present = sum(os.path.exists(os.path.join(asm_dir, name)) for name in asm_names)
    elf_names = [name[:-2] + ".elf" for name in asm_names]
    elf_present = sum(os.path.exists(os.path.join(elf_dir, name)) for name in elf_names)
    dt_entries = [(name, results[name]) for name in elf_names if name in results]
    dt_pass = sum(1 for _, (status, _) in dt_entries if status == "PASS")
    dt_fail_entries = [(name, status, detail) for name, (status, detail) in dt_entries if status != "PASS"]
    log_status, log_issue = read_log_status(instr)

    if issue_hint:
        isla_issue = issue_hint
    elif rec["json_error"]:
        isla_issue = rec["json_error"]
    elif log_status == "DONE" and log_issue == "-":
        isla_issue = "-"
    else:
        isla_issue = log_issue

    return {
        "instr": instr,
        "generated": generated,
        "asm_present": asm_present,
        "elf_present": elf_present,
        "dt_total": len(dt_entries),
        "dt_pass": dt_pass,
        "dt_fail_entries": dt_fail_entries,
        "dt_missing": max(0, generated - len(dt_entries)),
        "log_status": log_status,
        "isla_issue": isla_issue,
    }


records, testcase_to_instr = read_isla_jsons()
results = read_difftest_results()
clause_issues = parse_clause_problem_groups()

summaries = {
    instr: summarize_instruction(instr, rec, results, clause_issues.get(instr, ""))
    for instr, rec in sorted(records.items())
}

asm_files = glob.glob(os.path.join(asm_dir, "*.S"))
build_elf_files = glob.glob(os.path.join(build_dir, "*.elf"))
elf_files = glob.glob(os.path.join(elf_dir, "*.elf"))

dt_pass = sum(1 for status, _ in results.values() if status == "PASS")
dt_fail = sum(1 for status, _ in results.values() if status != "PASS")

clean = []
problem = []
not_difftested = []
for summary in summaries.values():
    isla_clean = summary["log_status"] == "DONE" and summary["isla_issue"] == "-"
    fully_difftest_passed = (
        summary["generated"] > 0
        and summary["dt_total"] == summary["generated"]
        and not summary["dt_fail_entries"]
        and summary["elf_present"] == summary["generated"]
    )
    if isla_clean and fully_difftest_passed:
        clean.append(summary)
    else:
        if summary["dt_total"] == 0 and summary["generated"] > 0:
            not_difftested.append(summary)
        problem.append(summary)

extra_dt = sorted(name for name in results if name not in testcase_to_instr)

lines = []
lines.append("# Isla Symbolic Execution + Difftest Report")
lines.append("")
lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append("")
lines.append("Pipeline: `isla/output/*.json` -> `assembly-gen` -> ELF -> `difftest/run.sh` -> this report.")
lines.append("")
lines.append("## Overview")
lines.append("")
lines.append("| Stage | Count |")
lines.append("| --- | ---: |")
lines.append(f"| Isla JSON files | {len(records)} |")
lines.append(f"| Isla generated testcases | {sum(len(r['items']) for r in records.values())} |")
lines.append(f"| assembly-gen .S files | {len(asm_files)} |")
lines.append(f"| assembly-gen build ELF files | {len(build_elf_files)} |")
lines.append(f"| difftest ELF input files | {len(elf_files)} |")
lines.append(f"| difftest executed entries | {len(results)} |")
lines.append(f"| difftest PASS | {dt_pass} |")
lines.append(f"| difftest non-PASS | {dt_fail} |")
lines.append("")

lines.append("## Isla Clean And Difftest PASS")
lines.append("")
if clean:
    lines.append("| Instruction | Testcases | Difftest |")
    lines.append("| --- | ---: | --- |")
    for item in clean:
        lines.append(f"| {item['instr']} | {item['generated']} | all PASS |")
else:
    lines.append("(none)")
lines.append("")

lines.append("## Isla Issues Or Difftest Findings")
lines.append("")
lines.append("| Instruction | Isla status | Isla issue | Generated | ELF | Difftest | Difftest finding |")
lines.append("| --- | --- | --- | ---: | ---: | --- | --- |")
for item in problem:
    finding = "-"
    if item["dt_fail_entries"]:
        finding = "; ".join(
            f"{name}: {status} {detail}".strip()
            for name, status, detail in item["dt_fail_entries"][:3]
        )
        if len(item["dt_fail_entries"]) > 3:
            finding += f"; ... +{len(item['dt_fail_entries']) - 3} more"
    elif item["dt_total"] > 0:
        finding = "no bug found by difftest"
    elif item["generated"] == 0:
        finding = "no testcase generated"
    else:
        finding = "not run in difftest"

    difftest_summary = f"{item['dt_pass']}/{item['dt_total']} PASS"
    if item["dt_missing"]:
        difftest_summary += f", {item['dt_missing']} missing"
    lines.append(
        f"| {item['instr']} | {item['log_status']} | {item['isla_issue']} | "
        f"{item['generated']} | {item['elf_present']} | {difftest_summary} | {finding} |"
    )
lines.append("")

lines.append("## Difftest Non-PASS Details")
lines.append("")
fail_rows = [(name, status, detail) for name, (status, detail) in sorted(results.items()) if status != "PASS"]
if fail_rows:
    lines.append("| ELF | Owner instruction | Result | Detail |")
    lines.append("| --- | --- | --- | --- |")
    for name, status, detail in fail_rows:
        lines.append(f"| {name} | {testcase_to_instr.get(name, '(external/manual)')} | {status} | {detail} |")
else:
    lines.append("No difftest failures were reported.")
lines.append("")

lines.append("## Difftest Inputs Outside Isla Output")
lines.append("")
if extra_dt:
    lines.append("| ELF | Difftest result |")
    lines.append("| --- | --- |")
    for name in extra_dt:
        status, detail = results[name]
        lines.append(f"| {name} | {status}: {detail} |")
else:
    lines.append("(none)")
lines.append("")

lines.append("## Notes")
lines.append("")
lines.append(f"- Isla clause report source: `{os.path.relpath(clause_report, root)}`")
lines.append(f"- Difftest result source: `{os.path.relpath(difftest_result, root)}`")
lines.append("- `Isla issue` combines `report_clause.md` known limitation sections and per-instruction `logs_todo/*.log` status.")
lines.append("- `Difftest finding` reports processor/difftest-visible failures separately from Isla execution limitations.")
lines.append("")

os.makedirs(os.path.dirname(report_file), exist_ok=True)
with open(report_file, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Report written: {report_file}")
PY
    echo
    echo "========================================="
    echo "Done"
    echo "========================================="
}

usage() {
    echo "Usage: $0 [step]"
    echo
    echo "  all           run check -> copy -> asm -> compile -> difftest -> report (default)"
    echo "  check         only check Isla JSON output"
    echo "  copy          only copy Isla JSON into assembly-gen/input"
    echo "  asm           only run assembly-gen"
    echo "  compile       only compile assembly to ELF and copy into difftest/elfs"
    echo "  difftest      only run difftest/run.sh"
    echo "  report        only regenerate report from existing outputs"
    echo "  from-asm      run asm -> compile -> difftest -> report"
    echo "  from-compile  run compile -> difftest -> report"
    echo "  from-dt       run difftest -> report"
}

case "${1:-all}" in
    all) step0_check_isla; step1_copy_json; step2_gen_asm; step3_compile; step4_difftest; step5_report ;;
    check) step0_check_isla ;;
    copy) step1_copy_json ;;
    asm) step2_gen_asm ;;
    compile) step3_compile ;;
    difftest) step4_difftest ;;
    report) step5_report ;;
    from-asm) step2_gen_asm; step3_compile; step4_difftest; step5_report ;;
    from-compile) step3_compile; step4_difftest; step5_report ;;
    from-dt) step4_difftest; step5_report ;;
    -h|--help) usage ;;
    *) echo "unknown step: $1" >&2; usage; exit 1 ;;
esac
