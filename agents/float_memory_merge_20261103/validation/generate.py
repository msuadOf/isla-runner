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
from audit_generation import collect_tool_hashes

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "sail-riscv"
MODEL = DEFAULT_MODEL
SAIL = None
PLUGIN = None
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


def live_executables(pid):
    found = set()
    pending = [pid]
    seen = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        process = Path('/proc') / str(current)
        try:
            found.add(str((process / 'exe').resolve(strict=True)))
            children = (process / 'task' / str(current) / 'children').read_text()
            pending.extend(int(child) for child in children.split())
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return found


def run(kind, config_name, ordinary, cpu, output, sources, commit, metadata, memo_sources):
    out = output / kind
    out.mkdir(parents=True, exist_ok=False)
    memo_record = None
    if memo_sources:
        old = memo_sources[kind]
        src = old['path']
        dest = out / 'sail_smt_cache'
        shutil.copyfile(src, dest)
        memo_record = {'source': str(src), 'source_sha256': old['sha256'],
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
    observed = set()
    with (out / "driver.log").open("w") as log:
        process = subprocess.Popen(executed, cwd=MODEL / "model", stdout=log, stderr=subprocess.STDOUT)
        while process.poll() is None:
            observed.update(live_executables(process.pid))
            time.sleep(0.05)
        code = process.wait()
    observed = sorted(observed)
    live_hashes = {path: sha(Path(path)) for path in observed if Path(path).is_file()}
    z3_seen = metadata['compile_z3_path'] in live_hashes
    tool_files_after, actual_sail = collect_tool_hashes(SAIL, PLUGIN)
    record.update(exit_code=code, seconds=round(time.monotonic() - started, 3),
                  live_executables=live_hashes,
                  compile_z3_live_observed=z3_seen,
                  compile_z3_live_hash_matches=(live_hashes.get(metadata['compile_z3_path']) ==
                                                metadata['compile_z3_sha256']) if z3_seen else None,
                  actual_sail_binary=actual_sail,
                  tool_files_unchanged=tool_files_after == metadata['tool_files_pre'],
                  compile_z3_unchanged=sha(Path(metadata['compile_z3_path'])) == metadata['compile_z3_sha256'],
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
    return (code == 0 and record["source_unchanged"] and record['tool_files_unchanged'] and
            record['compile_z3_unchanged'] and actual_sail in live_hashes and
            (memo_sources is not None or record['compile_z3_live_hash_matches'] is True) and
            (ordinary or ir.exists()) and
            (memo_record is None or record['memo_copy']['source_unchanged']))


def validate_memo(directory, metadata):
    if directory is None:
        return None
    base = directory.resolve(strict=True)
    source = json.loads((base / 'source.json').read_text())
    for field in ('sail_sha256', 'plugin_sha256', 'sail_version'):
        assert source[field] == metadata[field], f'memo工具不符: {field}'
    records = {}
    for kind in ('ordinary-strict', *(name for name, _ in CONFIGS)):
        path = base / kind / 'sail_smt_cache'
        prior = json.loads((base / kind / 'driver.json').read_text())
        config_name = 'rv64d.json' if kind in ('ordinary-strict', 'rv64d_v128_e64') else kind + '.json'
        assert prior['exit_code'] == 0 and prior['config_sha256'] == sha(ROOT / 'isla/ir/provenance' / config_name)
        assert path.is_file() and prior['source_unchanged'] is True
        records[kind] = {'path': path, 'sha256': sha(path), 'records': None}
    metadata['memo_source_batch'] = str(base)
    metadata['memo_source_manifest_sha256'] = sha(base / 'source.json')
    return records


def main():
    global MODEL, SAIL, PLUGIN
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=DEFAULT_MODEL,
                        help='干净的模型工作树')
    parser.add_argument('--sail', type=Path, required=True)
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--cpus", required=True, help="1至4个独立物理核的逻辑 CPU，如 31,60")
    parser.add_argument("--memo-from", type=Path, help="同工具/配置下按配置独立复制已完成批次memo")
    args = parser.parse_args()
    MODEL = args.model.resolve(strict=True)
    SAIL = args.sail.resolve(strict=True)
    PLUGIN = args.plugin.resolve(strict=True)
    assert MODEL == DEFAULT_MODEL.resolve(strict=True), '本批只允许合流候选模型'
    if git("rev-parse", "HEAD") != args.commit or git("status", "--porcelain"):
        raise ValueError("模型提交不符或模型工作树未清洁")
    cpus = [int(x) for x in args.cpus.split(",")]
    topology = check_cpus(cpus)
    output = HERE / "generation" / args.batch
    tracked = [name.removeprefix('model/') for name in subprocess.check_output(
        ['git', '-C', str(MODEL), 'ls-files', '-z', 'model']).decode().split('\0') if name]
    sources = {name: sha(MODEL / 'model' / name) for name in tracked}
    metadata = {"sail_path": str(SAIL), "plugin_path": str(PLUGIN),
                "sail_sha256": sha(SAIL), "sail_version": subprocess.check_output(
                    [str(SAIL), "--version"], text=True).strip(),
                "plugin_sha256": sha(PLUGIN), "driver_sha256": sha(DRIVER),
                "model_tree": str(MODEL.relative_to(ROOT)),
                "cpu_topology": topology}
    metadata['tool_files_pre'], metadata['actual_sail_binary'] = collect_tool_hashes(SAIL, PLUGIN)
    z3 = shutil.which('z3')
    assert z3, '编译期Z3未找到'
    metadata['compile_z3_path'] = str(Path(z3).resolve(strict=True))
    metadata['compile_z3_sha256'] = sha(Path(z3).resolve(strict=True))
    metadata['compile_z3_version'] = subprocess.check_output([z3, '-version'], text=True).strip()
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
