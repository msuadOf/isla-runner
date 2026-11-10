"""原生后端的配置与原子文件。"""
import json
import os
import math
from pathlib import Path
import re
import tomllib
import uuid

SCHEDULER = Path(__file__).resolve().parents[1]
ROOT = SCHEDULER.parent
ENVIRONMENT = ('RUST_BACKTRACE', 'RUST_LOG', 'OMP_NUM_THREADS', 'LC_ALL', 'LANG', 'TZ',
               'ISLA_RISCV_ALLOW_RESERVED_ENCODINGS', 'ISLA_RISCV_MODEL_TIMEOUT_MS')


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def process_identity(pid):
    """排除 zombie，并用启动时刻区分 PID 复用。"""
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
        return None if fields[0] in ('Z', 'X') else fields[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def load_config(path=None):
    from scheduler.scripts.common import validate_work_dir
    with Path(path or SCHEDULER / 'nodes.conf').open('rb') as stream:
        config = tomllib.load(stream)
    native = config.get('native', {})
    lease = native.get('lease_seconds', 60)
    if (native.get('backend', 'ssh') != 'ssh' or type(lease) not in (int, float)
            or not math.isfinite(lease) or lease <= 0):
        raise ValueError('native 后端必须为 ssh，租约必须为正数')
    nodes = config['nodes']
    names = set()
    for node in nodes:
        name = node['name']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in names:
            raise ValueError('节点名非法或重复')
        names.add(name)
        for key in ('cpus', 'weight'):
            if type(node.get(key)) is not int or node[key] <= 0:
                raise ValueError(f'{name}.{key} 必须为正整数')
        if type(node.get('priority')) is not int:
            raise ValueError('priority 必须为整数')
        external = node.get('external_cores', 0)
        if type(external) is not int or not 0 <= external <= node['cpus']:
            raise ValueError('external_cores 必须是节点容量范围内的整数')
        for key in ('address', 'ssh_user'):
            if not re.fullmatch(r'[A-Za-z0-9_.:-]+', node[key]) or node[key].startswith('-'):
                raise ValueError(f'非法 {key}')
        node['work_dir'] = node.get('work_dir', node.get('remote_runtime', 'scheduler/runtime'))
        validate_work_dir(node['work_dir'])
        if node.get('local'):
            resolved = (ROOT / Path(node['work_dir']).expanduser()).resolve()
            validate_work_dir(str(resolved))
            if resolved in (ROOT, SCHEDULER, Path.home().resolve()):
                raise ValueError('work_dir 必须使用独立的数据目录')
            node['work_dir'] = str(resolved)
    if not nodes:
        raise ValueError('节点列表为空')
    return config
