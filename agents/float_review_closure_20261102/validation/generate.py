#!/usr/bin/env python3
"""在独立目录完成普通严格检查和四配置 SYMBOLIC 严格 IR 生成。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from itertools import cycle
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / ".worktree/runner-float/sail-riscv"
MODEL = DEFAULT_MODEL
SAIL = ROOT / "isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src/sail"
PLUGIN = ROOT / ".tmp/float-full-trace-20260929/fvv-branch-candidate/sail_plugin_isla.cmxs"
DRIVER = ROOT / "isla/scripts/regenerate_ir.py"
CONFIGS = (("rv64d_v128_e64", "rv64d.json"), ("rv32d", "rv32d.json"),
           ("rv64d_v256_e64", "rv64d_v256_e64.json"),
           ("rv64d_v512_e64", "rv64d_v512_e64.json"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(MODEL), *args], text=True).strip()


def cpu_usage():
    result = {}
    for line in Path("/proc/stat").read_text().splitlines():
        if line.startswith("cpu") and line[3:4].isdigit():
            fields = line.split()
            values = [int(x) for x in fields[1:]]
            result[int(fields[0][3:])] = (sum(values), values[3] + values[4])
    return result


def check_cpus(cpus):
    topology = {}
    for line in subprocess.check_output(["lscpu", "-e=CPU,CORE,SOCKET,ONLINE"], text=True).splitlines()[1:]:
        cpu, core, socket, online = line.split()
        if online == "yes":
            topology[int(cpu)] = (int(socket), int(core))
    if not 1 <= len(cpus) <= 4 or any(cpu not in topology for cpu in cpus):
        raise ValueError("须给1至4个在线逻辑 CPU")
    if len({topology[cpu] for cpu in cpus}) != len(cpus):
        raise ValueError("所选 CPU 不能共享物理核")
    before = cpu_usage()
    time.sleep(1)
    after = cpu_usage()
    usage = {}
    for cpu in cpus:
        siblings = [other for other, core in topology.items() if core == topology[cpu]]
        usage[cpu] = {other: round(100 * (1 - (after[other][1] - before[other][1]) /
                                    (after[other][0] - before[other][0])), 1)
                      for other in siblings}
    return {"physical": {cpu: topology[cpu] for cpu in cpus}, "usage_percent": usage}


def run(kind, config_name, ordinary, cpu, output, sources, commit, metadata, memo_sources):
    out = output / kind
    out.mkdir(parents=True, exist_ok=False)
    memo_record = None
    if memo_sources:
        old = memo_sources[kind]
        src = old['path']
        dest = out / 'sail_smt_cache'
        shutil.copyfile(src, dest)
        memo_record = {'source': str(src.relative_to(ROOT)), 'source_sha256': old['sha256'],
                       'source_records': old['records'], 'copied_sha256': sha(dest),
                       'distinct_inode': src.stat().st_ino != dest.stat().st_ino}
        assert memo_record['copied_sha256'] == old['sha256'] and memo_record['distinct_inode']
    config = ROOT / "isla/ir/provenance" / config_name
    if ordinary:
        command = [str(SAIL), "--strict-var", "--strict-bitvector", "--strict-exponentials",
                   "--require-version", "0.20.1", "--memo-z3-path",
                   str(out / "sail_smt_cache"), "--all-modules", "--just-check",
                   "--config", str(config), "riscv.sail_project"]
    else:
        command = ["/usr/bin/python3", str(DRIVER), "--model", str(MODEL),
                   "--sail", str(SAIL), "--plugin", str(PLUGIN), "--config", str(config),
                   "--output", str(out), "--name", kind]
    executed = ["taskset", "-c", str(cpu), *command]
    record = {"kind": kind, "model_commit": commit, "model_files": sources,
              "config_sha256": sha(config), "cpu": cpu, "command": command,
              "executed_command": executed, "memo_copy": memo_record, **metadata}
    started = time.monotonic()
    with (out / "driver.log").open("w") as log:
        code = subprocess.run(executed, cwd=MODEL / "model", stdout=log, stderr=subprocess.STDOUT).returncode
    record.update(exit_code=code, seconds=round(time.monotonic() - started, 3),
                  source_unchanged=git("rev-parse", "HEAD") == commit and
                  all(sha(MODEL / "model" / name) == value for name, value in sources.items()))
    if memo_record:
        record['memo_copy']['output_sha256'] = sha(out / 'sail_smt_cache')
        record['memo_copy']['source_unchanged'] = sha(memo_sources[kind]['path']) == memo_record['source_sha256']
    ir = out / (kind + ".ir")
    if ir.exists():
        record["ir_sha256"] = sha(ir)
    (out / "driver.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(kind, "exit", code, "seconds", record["seconds"], flush=True)
    return (code == 0 and record["source_unchanged"] and (ordinary or ir.exists()) and
            (memo_record is None or record['memo_copy']['source_unchanged']))


def validate_memo(batch, metadata):
    if not batch:
        return None
    base = HERE / 'generation' / batch
    audit_name = ('memo-cache-audit.json' if batch == 'model-8ad5e8e'
                  else 'memo-reuse-21418d0.json' if batch == 'model-21418d0'
                  else 'memo-reuse-e9d69d2.json' if batch == 'model-e9d69d2' else None)
    assert audit_name, f'未审定memo来源批次 {batch}'
    audit_path = ROOT / 'agents/float_review_closure_20261102/review/model' / audit_name
    audit = json.loads(audit_path.read_text())
    assert audit.get('source_model', audit.get('model_commit')) == json.loads(
        (base / 'source.json').read_text())['commit']
    source = json.loads((base / 'source.json').read_text())
    assert source['sail_sha256'] == metadata['sail_sha256']
    assert source['plugin_sha256'] == metadata['plugin_sha256']
    assert source['driver_sha256'] == metadata['driver_sha256']
    assert source['sail_version'] == metadata['sail_version']
    tools = json.loads((base / 'independent-input-audit.json').read_text())['tool_files']
    assert all(sha(ROOT / name) == value for name, value in tools.items()), 'Sail工具链变化'
    compile_z3_path = ROOT / 'agents/float_review_closure_20261102/validation/generation/model-8ad5e8e/compile-z3-audit.json'
    compile_z3 = json.loads(compile_z3_path.read_text())
    compile_z3_sha = audit.get('compile_z3_sha256', compile_z3['actual_z3_sha256'])
    assert sha(Path(compile_z3['observed_live_grandchild']['exe'])) == compile_z3_sha
    records = {}
    for row in audit['rows']:
        kind = row['config']
        path = base / kind / 'sail_smt_cache'
        expected_sha = row.get('sha256', row.get('memo_sha256'))
        assert path.exists() and sha(path) == expected_sha
        if 'format_valid_and_complete' in row:
            assert row['format_valid_and_complete'] is True and row['source_generation_exit'] == 0
        else:
            assert row['exit_code'] == 0
        prior = json.loads((base / kind / 'driver.json').read_text())
        config_name = 'rv64d.json' if kind in ('ordinary-strict', 'rv64d_v128_e64') else kind + '.json'
        assert prior['config_sha256'] == sha(ROOT / 'isla/ir/provenance' / config_name)
        records[kind] = {'path': path, 'sha256': expected_sha, 'records': row['records']}
    assert set(records) == {'ordinary-strict', *(kind for kind, _ in CONFIGS)}
    metadata['memo_source_batch'] = batch
    metadata['memo_source_audit_sha256'] = sha(audit_path)
    metadata['memo_compile_z3_sha256'] = compile_z3_sha
    return records


def main():
    global MODEL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=DEFAULT_MODEL,
                        help='干净的模型工作树；默认runner-float模型')
    parser.add_argument("--commit", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpus", required=True, help="1至4个独立物理核的逻辑 CPU，如 31,60")
    parser.add_argument("--memo-from", help="同工具/配置下按配置复制已审成功批次memo")
    args = parser.parse_args()
    MODEL = args.model.resolve(strict=True)
    assert MODEL.is_relative_to(ROOT), '模型工作树必须位于本仓工作区'
    if git("rev-parse", "HEAD") != args.commit or git("status", "--porcelain"):
        raise ValueError("模型提交不符或模型工作树未清洁")
    cpus = [int(x) for x in args.cpus.split(",")]
    topology = check_cpus(cpus)
    output = HERE / "generation" / args.batch
    tracked = [name.removeprefix('model/') for name in subprocess.check_output(
        ['git', '-C', str(MODEL), 'ls-files', '-z', 'model']).decode().split('\0') if name]
    sources = {name: sha(MODEL / 'model' / name) for name in tracked}
    metadata = {"sail_sha256": sha(SAIL), "sail_version": subprocess.check_output(
                    [str(SAIL), "--version"], text=True).strip(),
                "plugin_sha256": sha(PLUGIN), "driver_sha256": sha(DRIVER),
                "model_tree": str(MODEL.relative_to(ROOT)),
                "cpu_topology": topology}
    memo_sources = validate_memo(args.memo_from, metadata)
    output.mkdir(parents=True, exist_ok=False)
    (output / "source.json").write_text(json.dumps({"commit": args.commit,
        "model_files": sources, **metadata}, indent=2, ensure_ascii=False) + "\n")
    if not run("ordinary-strict", "rv64d.json", True, cpus[0], output, sources,
               args.commit, metadata, memo_sources):
        raise SystemExit("普通严格检查失败，未启动 SYMBOLIC 生成")
    with ThreadPoolExecutor(max_workers=len(cpus)) as executor:
        futures = [executor.submit(run, kind, config, False, cpu, output, sources,
                                   args.commit, metadata, memo_sources)
                   for (kind, config), cpu in zip(CONFIGS, cycle(cpus))]
        passed = [future.result() for future in futures]
    raise SystemExit(0 if all(passed) else 1)


if __name__ == "__main__":
    main()
