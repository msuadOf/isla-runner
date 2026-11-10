#!/usr/bin/env python3
"""列出、按需取回或显式删除节点上的任务结果。"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import uuid

from common import RUNTIME, cli, docker, fail_main, load_config, manager, runtime_path, transport


REMOTE = r'''
import io, json, pathlib, shutil, sys, tarfile
mode, job_id = sys.argv[1:]
base = pathlib.Path('/srv/isla/jobs')
if mode == 'list':
 result = []
 for job in sorted(base.iterdir()) if base.exists() else []:
  result.append({'job_id': job.name, 'attempts': [p.name for p in job.glob('attempt-*')]})
 print(json.dumps(result))
 sys.exit(0)
job = base / job_id
if not job.is_dir() or not job.resolve().is_relative_to(base.resolve()):
 raise RuntimeError('找不到任务目录')
attempts = sorted(job.glob('attempt-*'))
if not attempts or any(not (p / 'summary.json').is_file() for p in attempts):
 raise RuntimeError('存在未完成或中断的 attempt；请先核对队列及节点状态')
if mode == 'delete':
 shutil.rmtree(job)
 print(json.dumps({'deleted': job_id}))
 sys.exit(0)
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz', dereference=False) as archive:
 if mode == 'fetch':
  archive.add(job, arcname=job_id)
 else:
  for attempt in attempts:
   prefix = job_id + '/' + attempt.name
   archive.add(attempt / 'summary.json', arcname=prefix + '/summary.json')
   manifest = json.loads((attempt / 'work/manifest.json').read_text())
   for name in ('stdout.log', 'stderr.log'):
    path = attempt / 'work' / name
    if path.is_file():
     with path.open('rb') as stream:
      stream.seek(max(0, path.stat().st_size - manifest['log_tail_bytes']))
      data = stream.read(manifest['log_tail_bytes'])
     info = tarfile.TarInfo(prefix + '/' + name); info.size = len(data)
     archive.addfile(info, io.BytesIO(data))
   remaining = manifest['summary_limit_bytes']
   for index, name in enumerate(manifest['summary_files']):
    path = (attempt / 'work' / name).resolve()
    if path.is_relative_to((attempt / 'work').resolve()) and path.is_file() and path.stat().st_size <= remaining:
     archive.add(path, arcname=prefix + '/summaries/' + str(index) + '/' + path.name)
     remaining -= path.stat().st_size
'''


def condor_main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--node", required=True)
    parser.add_argument("--job-id")
    parser.add_argument("action", choices=["list", "fetch", "summary", "delete"])
    args = parser.parse_args()
    config = load_config(args.config)
    node = next((n for n in config["nodes"] if n["name"] == args.node), None)
    if node is None:
        retired = RUNTIME / "retired-nodes.json"
        node = json.loads(retired.read_text()).get(args.node) if retired.exists() else None
    if node is None:
        raise ValueError("node 不在 nodes.conf 或已退役节点记录中")
    if args.action != "list" and not re.fullmatch(r"[a-f0-9]{32}", args.job_id or ""):
        raise ValueError("fetch/summary/delete 必须给出 32 位 --job-id")
    c = config["cluster"]
    if args.action == "delete":
        ads = json.loads(cli(config, ["condor_q", "-constraint", f'IslaJobId == "{args.job_id}"', "-json"]).stdout)
        if ads:
            raise RuntimeError("任务仍在队列中；未删除数据")
    mount = f'{runtime_path(node)}/data:/srv/isla:' + ("rw" if args.action == "delete" else "ro")
    # 数据管理使用独立短命容器；退役节点不需要重新加入调度集群。
    command = ["run", "--rm", "--network", "none", "--user", f'{c["submit_uid"]}:{c["submit_gid"]}',
               "-v", mount, "--entrypoint", "python3", node.get("_image", c["image"]),
               "-c", REMOTE, args.action, args.job_id or ""]
    if args.action in ("list", "delete"):
        print(docker(config, node, command).stdout.decode().strip())
        return
    target = Path(runtime_path(manager(config))) / "retrieved" / args.node / f'{args.job_id}-{args.action}-{uuid.uuid4().hex}.tar.gz'
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    try:
        with partial.open("wb") as stream:
            subprocess.run(transport(node, ["sudo", "-n", "docker", *command]), stdout=stream, check=True)
        partial.replace(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    print(target)


def main():
    import sys
    if '--backend' in sys.argv and sys.argv.index('--backend') + 1 >= len(sys.argv):
        raise ValueError('--backend 缺少值')
    if '--backend' in sys.argv and sys.argv[sys.argv.index('--backend') + 1] == 'condor':
        index = sys.argv.index('--backend')
        del sys.argv[index:index + 2]
        return condor_main()
    if '--backend=condor' in sys.argv:
        sys.argv.remove('--backend=condor')
        return condor_main()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scheduler.native.data import main as native_main
    return native_main()


if __name__ == "__main__":
    fail_main(main)
