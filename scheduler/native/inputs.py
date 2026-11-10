"""从已展开的 argv 提取输入、输出和 CPU 需求；不重新拆 shell 字符串。"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tomllib

INPUTS = {'-A', '--arch', '-C', '--config', '--execution-limits-config',
          '--encoding-slices-config', '--check-samples'}
OUTPUTS = {'--itrace', '--trace-output', '--timeout-smt-dir', '--check-samples-report',
           '--check-samples-judge'}


NONFILES = {'--timeout', '--smt-timeout', '--tastic', '--clause', '--debug',
            '--timeout-smt-output', '--instruction-bits', '--witness-randomization'}
VALUES = INPUTS | OUTPUTS | (NONFILES - {'--witness-randomization'}) | {'-T', '--threads'}


def options(argv, start):
    """每个值只消费一次，避免把文件名或普通参数值再次识别成选项。"""
    i = start
    while i < len(argv):
        token = argv[i]
        if token == '--':
            return
        key, sep, value = token.partition('=')
        index = i
        if not sep and token[:2] in ('-A', '-C', '-T') and len(token) > 2:
            key, value, sep = token[:2], token[2:], 'short'
        if not sep and key in VALUES:
            if i + 1 >= len(argv):
                raise ValueError(f'{key} 缺少值')
            index = i + 1
            value = argv[index]
            i += 1
        elif not sep and key.startswith('--') and i + 1 < len(argv) and not argv[i + 1].startswith('-'):
            index = i + 1
            value = argv[index]
            i += 1
        yield index, key, value, sep
        i += 1


def rewritten(key, value, sep):
    return key + ('=' if sep == '=' else '') + value if sep else value


def describe(argv, cwd):
    """仅识别监督器、CPU 与原 cwd；不读输入内容，也不重定位路径。"""
    cwd = Path(cwd).resolve()
    if len(argv) < 5 or Path(argv[0]).name not in ('python3', 'python') or argv[2] != 'run':
        raise ValueError('只接受 python3 solve_process.py run')
    supervisor = (cwd / argv[1]).resolve(strict=True)
    if supervisor != (cwd / 'scripts/solve_process.py').resolve(strict=True):
        raise ValueError('监督器身份不匹配')
    divider = argv.index('--', 3)
    if Path(argv[divider + 1]).name != 'timeout':
        raise ValueError('监督器后必须是原 timeout 命令')
    # timeout 的 flags / duration 保留；程序必须具有 Make 的 isarch 身份。
    candidates = [i for i in range(divider + 2, len(argv)) if Path(argv[i]).name == 'isarch']
    if len(candidates) != 1:
        raise ValueError('无法唯一识别 isarch 可执行文件')
    binary_index = candidates[0]
    clause_index = argv.index('--clause', 3)
    clause = argv[clause_index + 1]
    if not re.fullmatch(r'[A-Za-z0-9_]+', clause):
        raise ValueError('clause 必须是安全名称')
    cores = None
    for index, key, value, sep in options(argv, binary_index + 1):
        if key in ('-T', '--threads'):
            if cores is not None:
                raise ValueError('重复的线程数声明，无法唯一确定 CPU 请求')
            cores = int(value)
    if cores is None or cores <= 0:
        raise ValueError('缺少有效的 -T/--threads；无法预约 CPU')
    return dict(original_argv=list(argv), cwd=str(cwd), cores=cores, clause=clause, binary_index=binary_index)


def sniff(argv, cwd, workspace, log_path=None):
    cwd, workspace = Path(cwd).resolve(), Path(workspace).resolve()
    cwd_relative = cwd.relative_to(workspace).as_posix()
    description = describe(argv, cwd)
    binary_index, clause = description['binary_index'], description['clause']
    effective = list(argv)
    effective[0] = 'python3'
    files = {}
    outputs = ['output', 'outputs']
    output_directories = ['output', 'outputs']
    required = set()
    config_sources = set()

    def add(name):
        absolute = Path(os.path.abspath(cwd / name))
        source = absolute.resolve(strict=True)
        if not source.is_file():
            raise ValueError(f'不支持目录输入：{name}')
        if absolute.is_relative_to(workspace):
            logical = absolute.relative_to(workspace).as_posix()
        else:
            parent = hashlib.sha256(str(source.parent).encode()).hexdigest()[:20]
            logical = f'_external/{parent}/{source.name}'
        files[logical] = str(source)
        return os.path.relpath(logical, cwd_relative)

    effective[1] = add(argv[1])
    effective[binary_index] = add(argv[binary_index])
    cores = description['cores']
    for index, key, value, sep in options(argv, binary_index + 1):
        if key in INPUTS:
            required.add(key)
            mapped = add(value)
            effective[index] = rewritten(key, mapped, sep)
            if key in ('-C', '--config', '--execution-limits-config', '--encoding-slices-config'):
                config_sources.add(str((cwd / value).resolve(strict=True)))
        elif key in OUTPUTS:
            path = Path(value)
            if not value or path.is_absolute() or '..' in path.parts:
                raise ValueError(f'输出必须在 attempt 的 cwd 内：{key}={value}')
            outputs.append(value)
            if key == '--timeout-smt-dir':
                output_directories.append(value)
        elif key not in NONFILES | {'-T', '--threads'}:
            candidate = value if key.startswith('-') else key
            if candidate and (cwd / candidate).is_file():
                mapped = add(candidate)
                effective[index] = rewritten(key, mapped, sep) if key.startswith('-') else mapped
            elif candidate and key.startswith('-') and (cwd / candidate).is_dir():
                raise ValueError(f'不支持目录输入：{key} {candidate}')
            elif candidate and key.startswith('-') and ('/' in candidate or Path(candidate).suffix in ('.toml', '.ir', '.irx', '.json')):
                raise ValueError(f'未知参数的文件角色或路径无法确认：{key} {candidate}')
    if not required.intersection({'-A', '--arch'}) or not required.intersection({'-C', '--config'}):
        raise ValueError('缺少模型 IR 或 ISA 配置参数')
    if cores is None or cores <= 0:
        raise ValueError('缺少有效的 -T/--threads；无法预约 CPU')
    for directory in (cwd / 'configs', workspace / 'sail-riscv/configs/isla/workarounds'):
        if directory.is_dir():
            for path in sorted(directory.rglob('*.toml')):
                add(str(path))
    # 只解释已核实的输出字段；workaround.file 是 IR 源位置，不能当输入。
    for source in sorted(config_sources):
        if Path(source).suffix == '.toml':
            with open(source, 'rb') as stream:
                config = tomllib.load(stream)
            entries = config.get('execution_limits', {}).get('merge_enumeration', {}).get('outputs', [])
            for entry in entries:
                value = entry['path']
                if Path(value).is_absolute() or '..' in Path(value).parts:
                    raise ValueError(f'无法重定位 TOML 输出：{source}: {value}')
                outputs.append(value)
    if log_path:
        if Path(log_path).is_absolute() or '..' in Path(log_path).parts:
            raise ValueError('日志输出越界')
        outputs.append(log_path)
    for logical in files:
        for output in outputs:
            destination = Path(cwd_relative) / output
            if Path(logical) == destination or destination in Path(logical).parents:
                raise ValueError(f'输入与可写输出目录冲突：{logical}')
    return dict(original_argv=list(argv), effective_argv=effective, cwd=cwd_relative,
                files=files, outputs=outputs, output_directories=output_directories, cores=cores, clause=clause,
                binary_index=binary_index)


def runtime_files(binary):
    """冻结 ELF 的 loader 与传递依赖，不依赖远端绝对 Z3 RPATH。"""
    with Path(binary).open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            return {}, None
    result = subprocess.run(['ldd', str(binary)], capture_output=True, text=True, check=False, timeout=30)
    if 'statically linked' in result.stdout or 'not a dynamic executable' in result.stderr:
        return {}, None
    if result.returncode or 'not found' in result.stdout:
        raise ValueError(f'ELF 依赖解析失败：{result.stdout}{result.stderr}')
    files = {}
    loader = None
    for line in result.stdout.splitlines():
        match = re.search(r'(?:=>\s+)?(/\S+)', line)
        if match:
            path = Path(match[1])
            if path.name in files and Path(files[path.name]).resolve() != path.resolve():
                raise ValueError(f'运行库同名冲突：{path.name}')
            files[path.name] = str(path.resolve(strict=True))
            if path.name.startswith('ld-linux'):
                loader = path.name
    if not loader:
        raise ValueError('不支持的 ELF loader')
    return files, loader
