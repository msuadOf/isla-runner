"""配置、SSH 和容器命令的公共入口；节点数据放在各自的 work_dir。"""

import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"


def work_dir(node):
    """work_dir 优先；remote_runtime 是旧配置的兼容别名。"""
    return node.get("work_dir", node.get("remote_runtime", "scheduler/runtime" if node.get("local")
                                        else "~/isla-runner/scheduler/runtime"))


def validate_work_dir(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("work_dir 必须是非空路径字符串")
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or ":" in value:
        raise ValueError("work_dir 不能包含控制字符或 Docker 卷分隔符 ':'")
    path = PurePosixPath(value)
    if ".." in path.parts or (value.startswith("~") and not value.startswith("~/")):
        raise ValueError("work_dir 不支持 '..' 或 ~user；用户目录请使用 ~/专用目录")
    # 只允许专用工作目录，避免部署向系统目录或用户主目录写入 config/auth 等文件。
    if str(path) in (".", "~", "/", "//") or path.parts == ("~",):
        raise ValueError("work_dir 必须是专用目录，不能是根目录、当前目录或用户主目录")
    if path.is_absolute():
        normalized = "/" + "/".join(path.parts[1:])
        protected = ("/bin", "/sbin", "/lib", "/lib64", "/boot", "/dev", "/proc", "/sys", "/etc", "/usr", "/run")
        if (normalized in ("/home", "/root", "/tmp", "/var", "/opt", "/srv", "/mnt", "/media")
                or any(normalized == p or normalized.startswith(p + "/") for p in protected)):
            raise ValueError("work_dir 不能是危险系统目录")


def load_config(path=None):
    path = Path(path or ROOT / "nodes.conf").resolve()
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    cluster, nodes = config["cluster"], config["nodes"]
    names = [node["name"] for node in nodes]
    if len(names) != len(set(names)) or cluster["manager"] not in names:
        raise ValueError("节点名重复，或 manager 不在 nodes 中")
    local = [n for n in nodes if n.get("local", False)]
    if len(local) != 1 or local[0]["name"] != cluster["manager"]:
        raise ValueError("必须且只能有一个 local=true 的 manager")
    for key in ("container", "submit_user", "uid_domain"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", cluster[key]):
            raise ValueError(f"非法 cluster.{key}")
    if not re.fullmatch(r"[A-Za-z0-9_./:-]+", cluster["image"]):
        raise ValueError("非法镜像名")
    if cluster["submit_uid"] <= 0 or cluster["submit_gid"] <= 0:
        raise ValueError("任务账户不能使用 root UID/GID")
    if cluster["submit_uid"] != os.getuid() or cluster["submit_gid"] != os.getgid():
        raise ValueError("submit_uid/gid 必须与运行脚本的主控用户一致")
    for key in ("port", "transfer_port_low", "transfer_port_high"):
        if not 1024 <= cluster[key] <= 65535:
            raise ValueError(f"非法端口 {key}")
    if cluster["transfer_port_low"] > cluster["transfer_port_high"]:
        raise ValueError("文件传输端口范围为空")
    if min(cluster["summary_limit_bytes"], cluster["log_tail_bytes"]) <= 0:
        raise ValueError("摘要和日志上限必须大于零")
    addresses = set()
    for node in nodes:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", node["name"]):
            raise ValueError("非法节点名")
        ipaddress.IPv4Address(node["address"])
        if node["address"] in addresses or node["cpus"] < 1:
            raise ValueError("节点 IP 重复或 cpus 小于 1")
        addresses.add(node["address"])
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", node["ssh_user"]):
            raise ValueError("非法 SSH 用户")
        validate_work_dir(work_dir(node))
        if node.get("local"):
            runtime_path(node)
    return config


def manager(config):
    return next(n for n in config["nodes"] if n["name"] == config["cluster"]["manager"])


def transport(node, argv):
    if node.get("local"):
        return list(map(str, argv))
    # 跳过本环境中权限异常的系统 ssh_config；仍严格校验 known_hosts。
    return ["ssh", "-F", "/dev/null", "-o", "BatchMode=yes", "-o",
            "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10",
            f'{node["ssh_user"]}@{node["address"]}', shlex.join(list(map(str, argv)))]


def run(node, argv, *, data=None, capture=True, check=True):
    return subprocess.run(transport(node, argv), input=data, stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None, check=check)


def python_on(node, source, *args, data=None):
    return run(node, ["python3", "-c", source, *map(str, args)], data=data)


def docker(config, node, args, **kwargs):
    return run(node, ["sudo", "-n", "docker", *map(str, args)], **kwargs)


def cli(config, args, *, root=False, check=True):
    cluster = config["cluster"]
    return docker(config, manager(config), ["exec", "--user",
                  "0" if root else f'{cluster["submit_uid"]}:{cluster["submit_gid"]}',
                  cluster["container"], *args], check=check)


def runtime_path(node):
    value = work_dir(node)
    validate_work_dir(value)
    if node.get("local"):
        path = Path(value).expanduser()
        path = (ROOT.parent / path).resolve()
        if path in (Path.home().resolve(), ROOT.parent, ROOT):
            raise ValueError("work_dir 必须使用专用目录")
        result = str(path)
    else:
        # 在 SSH 用户环境中展开 ~、相对路径和符号链接，不能使用主控的 home。
        source = """from pathlib import Path
import sys
path = Path(sys.argv[1]).expanduser().resolve()
if path == Path.home().resolve():
 raise ValueError('work_dir 不能是用户主目录')
print(path)
"""
        result = python_on(node, source, value).stdout.decode().strip()
        if not Path(result).is_absolute():
            raise ValueError("远端 work_dir 未解析为绝对路径")
    validate_work_dir(result)
    return result


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def fail_main(main):
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, TimeoutError, RuntimeError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            print(f"错误：命令执行失败，退出码 {error.returncode}", file=sys.stderr)
            if error.stderr:
                print(error.stderr.decode(errors="replace"), file=sys.stderr)
        else:
            print(f"错误：{error}", file=sys.stderr)
        sys.exit(1)
