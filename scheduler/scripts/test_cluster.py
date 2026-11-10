#!/usr/bin/env python3
"""真实集群验收：每台节点执行三种回传策略，核对持久结果和传输内容。"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import uuid

from common import ROOT, RUNTIME, atomic_json, docker, fail_main, load_config
from deploy_cluster import status


PROGRAM = '''#!/usr/bin/env python3
import json, os
from pathlib import Path
text = Path('inputs/input.txt').read_text()
assert text == 'isla-condor-test\\n'
Path('results/payload.bin').write_bytes(os.urandom(2 * 1024 * 1024))
Path('results/summary.json').write_text(json.dumps({'input_ok': True, 'bytes': 2 * 1024 * 1024}))
print('input_ok bytes=2097152')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--timeout", type=int, default=300, help="每个任务的等待秒数")
    args = parser.parse_args()
    config = load_config(args.config)
    report = {"result": "RUNNING", "started_unix": time.time(), "cases": []}
    report_path = ROOT / "evidence" / f"e2e-{uuid.uuid4().hex}.json"
    atomic_json(report_path, report)
    try:
        report["status_before"] = status(config, args.timeout)
        fixtures = RUNTIME / "test-inputs"
        fixtures.mkdir(parents=True, exist_ok=True)
        program = fixtures / "task.py"
        program.write_text(PROGRAM)
        program.chmod(0o755)
        data = fixtures / "input.txt"
        data.write_text("isla-condor-test\n")
        for node in config["nodes"]:
            for policy, flag in (("all", "--retrieve-data"), ("summary", "--summary-only"), ("none", "--no-retrieve")):
                command = [sys.executable, str(ROOT / "scripts/submit_job.py"), "--executable", str(program),
                           "--input", str(data), "--node", node["name"], flag,
                           "--memory", "128MB", "--disk", "64MB", "--wait", "--timeout", str(args.timeout)]
                if args.config:
                    command += ["--config", args.config]
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    raise RuntimeError(f"提交或执行失败：{result.stdout}\n{result.stderr}")
                record = json.loads(result.stdout)
                directory = Path(record["directory"])
                returned = directory / "return"
                if policy == "none":
                    if returned.exists() or (directory / "runner.out").exists() or (directory / "runner.err").exists():
                        raise RuntimeError("--no-retrieve 意外回传任务文件")
                else:
                    summary = json.loads((returned / "summary.json").read_text())
                    if summary["exit_code"] != 0 or summary["hostname"] != node["name"]:
                        raise RuntimeError(f"错误的执行结果或节点：{summary}")
                    small = json.loads((returned / "summaries/0/summary.json").read_text())
                    if small != {"input_ok": True, "bytes": 2097152}:
                        raise RuntimeError("摘要或输入内容不符")
                    if policy == "all":
                        with tarfile.open(returned / "full.tar.gz") as archive:
                            if archive.getmember("work/results/payload.bin").size != 2097152:
                                raise RuntimeError("完整数据大小错误")
                    else:
                        size = sum(p.stat().st_size for p in returned.rglob("*") if p.is_file())
                        if (returned / "full.tar.gz").exists() or size > config["cluster"]["summary_limit_bytes"] + 2 * config["cluster"]["log_tail_bytes"] + 16384:
                            raise RuntimeError("摘要策略意外回传完整数据或超过上限")
                # 直接到指定节点核对数据；只回传 JSON 状态，不下载 payload。
                source = """import json, pathlib, sys
base = pathlib.Path('/srv/isla/jobs') / sys.argv[1]
attempts = list(base.glob('attempt-*'))
assert len(attempts) == 1, attempts
attempt = attempts[0]
summary = json.loads((attempt / 'summary.json').read_text())
assert summary['exit_code'] == 0, summary
assert (attempt / 'work/results/payload.bin').stat().st_size == 2097152
print(json.dumps({'retained': True, 'attempt': str(attempt)}))
"""
                retained = docker(config, node, ["exec", config["cluster"]["container"], "python3", "-c", source, record["job_id"]])
                case = {"node": node["name"], "policy": policy, "job_id": record["job_id"],
                        "cluster_id": record["cluster_id"], "result": "PASS", "retention": json.loads(retained.stdout),
                        "returned_bytes": sum(p.stat().st_size for p in returned.rglob("*") if p.is_file()) if returned.exists() else 0}
                report["cases"].append(case)
                atomic_json(report_path, report)
                print(f'{node["name"]} {policy}: PASS ({case["returned_bytes"]} bytes)', flush=True)
        report["status_after"] = status(config, args.timeout)
        report["result"] = "PASS"
    except Exception as error:
        report.update(result="FAIL", error=str(error))
        raise
    finally:
        report["finished_unix"] = time.time()
        atomic_json(report_path, report)
    print(f"全部通过；证据：{report_path}")


if __name__ == "__main__":
    fail_main(main)
