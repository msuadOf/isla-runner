#!/usr/bin/env python3
"""读取 nodes.conf；在 Ubuntu 宿主机部署统一的 HTCondor 容器。"""

import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import time

from common import (ROOT, RUNTIME, atomic_json, cli, docker, fail_main, load_config,
                    manager, python_on, run, runtime_path, transport)


def render(config, node):
    cluster = config["cluster"]
    values = {
        "MANAGER_ADDRESS": manager(config)["address"], "ADDRESS": node["address"],
        "NAME": node["name"], "PORT": cluster["port"], "LOWPORT": cluster["transfer_port_low"],
        "HIGHPORT": cluster["transfer_port_high"], "UID_DOMAIN": cluster["uid_domain"],
        "SUBMIT_USER": cluster["submit_user"], "CPUS": node["cpus"],
        "GPU_CONFIG": ("use feature : GPUs\nNUM_GPUS = %s" % node["hardware_gpus"])
                       if node.get("enable_gpus") else "NUM_GPUS = 0",
    }
    role = "master" if node["name"] == cluster["manager"] else "worker"
    result = (ROOT / "config/condor_config.common").read_text() + "\n"
    result += (ROOT / f"config/condor_config.{role}").read_text()
    for name, value in values.items():
        result = result.replace(f"@{name}@", str(value))
    return result


def probe(node):
    source = """import json, os, platform, shutil, subprocess
from pathlib import Path
release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
sudo = subprocess.run(['sudo', '-n', 'true'], capture_output=True)
print(json.dumps({'hostname': platform.node(), 'os': release.get('PRETTY_NAME', '').strip(chr(34)),
 'cpus': os.cpu_count(), 'architecture': platform.machine(), 'docker': shutil.which('docker'),
 'sudo_ok': sudo.returncode == 0, 'sudo_error': sudo.stderr.decode().strip()}))
"""
    return json.loads(python_on(node, source).stdout)


def ensure_engine(config, node):
    info = probe(node)
    if not info["sudo_ok"]:
        raise RuntimeError(f'{node["name"]}: sudo 失败：{info["sudo_error"]}')
    if info["architecture"] != "x86_64":
        raise RuntimeError("当前镜像和可执行文件分发限定 x86_64")
    if info["cpus"] < node["cpus"]:
        raise RuntimeError(f'{node["name"]} 实际 CPU 少于配置的 {node["cpus"]}')
    if not info["docker"]:
        run(node, ["sudo", "-n", "apt-get", "update"], capture=False)
        run(node, ["sudo", "-n", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "docker.io"], capture=False)
    run(node, ["sudo", "-n", "systemctl", "enable", "--now", "docker"], capture=False)
    docker(config, node, ["info"])
    return info


def build_image(config):
    c = config["cluster"]
    args = ["build", "-t", c["image"]]
    for key, value in {"APT_REPOSITORY": c["apt_repository"], "APT_KEY": c["apt_key"],
                       "SUBMIT_USER": c["submit_user"], "SUBMIT_UID": c["submit_uid"],
                       "SUBMIT_GID": c["submit_gid"]}.items():
        args.extend(["--build-arg", f"{key}={value}"])
    args.append(str(ROOT / "config"))
    docker(config, manager(config), args, capture=False)
    version = docker(config, manager(config), ["run", "--rm", "--entrypoint", "condor_version", c["image"]]).stdout.decode()
    if f'$CondorVersion: {c["version_prefix"]}' not in version:
        raise RuntimeError(f"包版本不符合 version_prefix：{version}")
    return docker(config, manager(config), ["image", "inspect", "--format", "{{.Id}}", c["image"]]).stdout.decode().strip(), version


def distribute_image(config, node, image_id):
    current = docker(config, node, ["image", "inspect", "--format", "{{.Id}}", config["cluster"]["image"]], check=False)
    if current.returncode == 0 and current.stdout.decode().strip() == image_id:
        return
    # docker save 的字节直接走 SSH；不经远端上行回传，也不写大体积中间包。
    source = subprocess.Popen(transport(manager(config), ["sudo", "-n", "docker", "save", config["cluster"]["image"]]), stdout=subprocess.PIPE)
    try:
        sink = subprocess.run(transport(node, ["sudo", "-n", "docker", "load"]), stdin=source.stdout, check=False)
    finally:
        source.stdout.close()
        source.wait()
    if sink.returncode or source.returncode:
        raise RuntimeError(f'{node["name"]} 镜像分发失败')


def prepare_paths(config, node, path):
    c = config["cluster"]
    source = """import os, pathlib, sys
base = pathlib.Path(sys.argv[1]); uid, gid = map(int, sys.argv[2:])
base.mkdir(parents=True, exist_ok=True)
for name in ('config', 'auth', 'condor', 'data', 'submissions', 'rendered', 'retrieved'):
 p = base / name; p.mkdir(exist_ok=True)
 os.chmod(p, 0o700 if name == 'auth' else 0o755)
 if name in ('data', 'submissions', 'rendered', 'retrieved'): os.chown(p, uid, gid)
for name in ('log', 'spool', 'execute', 'lock', 'run'):
 (base / 'condor' / name).mkdir(exist_ok=True)
"""
    run(node, ["sudo", "-n", "python3", "-c", source, path, str(c["submit_uid"]), str(c["submit_gid"])])


def upload_root(node, path, data, mode="0600"):
    source = """import os, pathlib, sys
p = pathlib.Path(sys.argv[1]); tmp = p.with_name(p.name + '.new')
with open(tmp, 'wb') as out: out.write(sys.stdin.buffer.read())
os.chmod(tmp, int(sys.argv[2], 8)); os.replace(tmp, p)
"""
    run(node, ["sudo", "-n", "python3", "-c", source, path, mode], data=data)


def ensure_password(config, path):
    node, c = manager(config), config["cluster"]
    exists = run(node, ["sudo", "-n", "test", "-s", f"{path}/auth/pool_password"], check=False)
    if exists.returncode:
        # 口令只经 stdin 传入容器，不写命令日志。工具本身短暂使用 argv。
        source = """import os, subprocess, sys
password = sys.stdin.read().strip()
subprocess.run(['condor_store_cred', '-f', '/auth/pool_password', '-p', password], check=True,
               stdout=subprocess.DEVNULL)
os.chmod('/auth/pool_password', 0o600)
"""
        docker(config, node, ["run", "--rm", "-i", "--entrypoint", "python3", "-v", f"{path}/auth:/auth", c["image"], "-c", source], data=secrets.token_urlsafe(64).encode())
    return run(node, ["sudo", "-n", "cat", f"{path}/auth/pool_password"]).stdout


def inspect_container(config, node):
    name = config["cluster"]["container"]
    # API/SSH 故障必须报错，不能把“无法查询”当成“容器不存在”。
    listing = docker(config, node, ["container", "ls", "-a", "--filter", f"name=^/{name}$", "--format", "{{.ID}}"])
    if not listing.stdout.strip():
        return None
    result = docker(config, node, ["inspect", name])
    info = json.loads(result.stdout)[0]
    if info["Config"].get("Labels", {}).get("org.isla.scheduler") != config["cluster"]["name"]:
        raise RuntimeError(f'{node["name"]}: 同名容器不属于本系统；保留原容器')
    return info


def peaceful_stop(config, node, timeout):
    c = config["cluster"]
    info = inspect_container(config, node)
    if not info:
        return
    if info["State"]["Running"]:
        docker(config, node, ["update", "--restart=no", c["container"]])
        docker(config, node, ["exec", c["container"], "condor_off", "-peaceful", "-master"])
        deadline = time.monotonic() + timeout
        while inspect_container(config, node)["State"]["Running"]:
            if time.monotonic() >= deadline:
                raise TimeoutError(f'{node["name"]} 正在排空任务；未强制停止。任务结束后重跑部署')
            time.sleep(2)
    docker(config, node, ["rm", c["container"]])


def start_node(config, node, path, image_id, password, timeout):
    c = config["cluster"]
    text = render(config, node)
    # 摘要仅用于发现服务配置变化，不判断任何任务数据的语义有效性。
    generation = hashlib.sha256((text + image_id + path + str(c["submit_uid"]) + str(c["submit_gid"])).encode()).hexdigest()
    info = inspect_container(config, node)
    if info and info["State"]["Running"] and info["Config"].get("Labels", {}).get("org.isla.generation") == generation:
        print(f'{node["name"]}: 配置一致，保持服务运行', flush=True)
        return
    peaceful_stop(config, node, timeout)
    upload_root(node, f"{path}/config/condor.conf", text.encode(), "0644")
    upload_root(node, f"{path}/auth/pool_password", password)
    # 包内 condor UID 不写死；守护进程降权后仍可写 spool 并读取口令。
    ownership = """import os, pathlib, pwd
user = pwd.getpwnam('condor')
for p in pathlib.Path('/var/lib/condor').rglob('*'):
 os.chown(p, user.pw_uid, user.pw_gid, follow_symlinks=False)
os.chown('/var/lib/condor', user.pw_uid, user.pw_gid)
os.chown('/auth/pool_password', user.pw_uid, user.pw_gid)
"""
    docker(config, node, ["run", "--rm", "--entrypoint", "python3", "-v", f"{path}/condor:/var/lib/condor",
                         "-v", f"{path}/auth:/auth", c["image"], "-c", ownership])
    args = ["run", "-d", "--name", c["container"], "--hostname", node["name"],
            "--network", "host", "--restart", "unless-stopped", "--init=false",
            "--label", f'org.isla.scheduler={c["name"]}', "--label", f"org.isla.generation={generation}",
            "-v", f"{path}/config/condor.conf:/etc/condor/isla.conf:ro",
            "-v", f"{path}/auth/pool_password:/etc/condor/isla-auth/pool_password:ro", "-v", f"{path}/condor:/var/lib/condor",
            "-v", f"{path}/data:/srv/isla", "-v", f"{path}/submissions:/srv/submit"]
    for peer in config["nodes"]:
        args.extend(["--add-host", f'{peer["name"]}:{peer["address"]}'])
    if node.get("enable_gpus"):
        args.extend(["--gpus", "all"])
    args.append(c["image"])
    docker(config, node, args)


def check_existing_paths(previous, config):
    """兼容旧字段和缺省值；实际目录变化仍须先迁移已有数据。"""
    current = {n["name"]: n for n in config["nodes"]}
    for old in previous["nodes"]:
        new = current.get(old["name"])
        if new is not None and old["address"] == new["address"]:
            if old["ssh_user"] != new["ssh_user"] or runtime_path(old) != runtime_path(new):
                raise ValueError(f'{old["name"]}: SSH 用户或 work_dir 涉及现有数据位置，须单独迁移')


def status(config, timeout):
    deadline = time.monotonic() + timeout
    since = int(time.time())
    last = []
    last_error = ""
    while time.monotonic() < deadline:
        result = cli(config, ["condor_status", "-startd", "-json"], check=False)
        last_error = result.stderr.decode(errors="replace").strip()
        if result.returncode == 0:
            last = json.loads(result.stdout)
            parent = {ad.get("IslaNode"): ad for ad in last if ad.get("PartitionableSlot")}
            if all(n["name"] in parent and parent[n["name"]].get("TotalSlotCpus") == n["cpus"]
                   and parent[n["name"]].get("LastHeardFrom", 0) >= since
                   and (not n.get("enable_gpus") or parent[n["name"]].get("TotalSlotGpus", 0) == n["hardware_gpus"])
                   for n in config["nodes"]):
                live = [inspect_container(config, n) for n in config["nodes"]]
                if all(info and info["State"]["Running"] for info in live):
                    return last
        time.sleep(2)
    raise TimeoutError(f"condor_status 未满足 nodes.conf；最后广告：{json.dumps(last)}；错误：{last_error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--check", action="store_true", help="只检查 SSH、系统和 sudo")
    parser.add_argument("--render-only", action="store_true", help="离线生成配置，不安装服务")
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("timeout 必须大于零")
    config = load_config(args.config)
    if args.render_only:
        rendered = Path(runtime_path(manager(config))) / "rendered"
        for node in config["nodes"]:
            path = rendered / f'{node["name"]}.conf'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render(config, node))
        print(f"配置已生成：{rendered}/")
        return
    if args.status_only:
        print(json.dumps(status(config, args.timeout), indent=2))
        return
    if args.check:
        results = {}
        for node in config["nodes"]:
            try:
                results[node["name"]] = probe(node)
            except (OSError, subprocess.CalledProcessError) as error:
                results[node["name"]] = {"error": type(error).__name__, "detail": (getattr(error, "stderr", b"") or b"").decode() or str(error)}
        atomic_json(ROOT / "evidence/preflight.json", results)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        if any(not r.get("sudo_ok") for r in results.values()):
            raise RuntimeError("预检未通过，详见 scheduler/evidence/preflight.json")
        return
    # 管理记录由主控用户写入；自定义节点目录可由 sudo 初始化。
    RUNTIME.mkdir(parents=True, exist_ok=True)
    previous_path = RUNTIME / "deployed-nodes.json"
    managed_path = RUNTIME / "managed-nodes.json"
    state_path = managed_path if managed_path.exists() else previous_path
    previous = json.loads(state_path.read_text()) if state_path.exists() else {"nodes": []}
    for key in ("name", "manager", "container", "submit_uid", "submit_gid", "uid_domain"):
        if "cluster" in previous and previous["cluster"][key] != config["cluster"][key]:
            raise ValueError(f"已有集群的 {key} 不能直接更换；请先迁移旧服务和队列")
    current = {n["name"]: n for n in config["nodes"]}
    check_existing_paths(previous, config)
    # 所有节点先预检；外部源不通时不会停止现有 Condor 容器。
    observations = {n["name"]: ensure_engine(config, n) for n in config["nodes"]}
    image_id, version = build_image(config)
    for node in config["nodes"]:
        if not node.get("local"):
            distribute_image(config, node, image_id)
    paths = {n["name"]: runtime_path(n) for n in config["nodes"]}
    for node in config["nodes"]:
        prepare_paths(config, node, paths[node["name"]])
    password = ensure_password(config, paths[config["cluster"]["manager"]])
    managed = {n["name"]: n for n in previous["nodes"]}
    retired_path = RUNTIME / "retired-nodes.json"
    retired = json.loads(retired_path.read_text()) if retired_path.exists() else {}
    for old in previous["nodes"]:
        if old["name"] not in current or old["address"] != current[old["name"]]["address"]:
            peaceful_stop(config, old, args.timeout)
            retired[old["name"]] = dict(old, _image=previous.get("cluster", config["cluster"])["image"])
            atomic_json(retired_path, retired)
            managed.pop(old["name"], None)
            atomic_json(managed_path, {"nodes": list(managed.values()), "cluster": config["cluster"]})
            print(f'{old["name"]}: 已退出集群，节点数据保留')
    for node in config["nodes"]:
        start_node(config, node, paths[node["name"]], image_id, password, args.timeout)
        managed[node["name"]] = node
        atomic_json(managed_path, {"nodes": list(managed.values()), "cluster": config["cluster"]})
    ads = status(config, args.timeout)
    atomic_json(previous_path, {"nodes": config["nodes"], "cluster": config["cluster"]})
    atomic_json(ROOT / "evidence/deployment.json", {"version": version, "image_id": image_id,
                "observations": observations, "status": ads, "result": "PASS"})
    print("部署及 condor_status 检查通过；端到端任务验证请运行 test_cluster.sh")


if __name__ == "__main__":
    fail_main(main)
