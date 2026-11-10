#!/usr/bin/env python3
"""在有限且明确的 shell 语法内安装 exec 函数；不接受未知 recipe。"""
import argparse
import os
from pathlib import Path
import shlex
import sys

SCHEDULER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCHEDULER.parent))


def tokens(source):
    parser = shlex.shlex(source.replace('\\\n', ' '), posix=False, punctuation_chars='();<>&|')
    parser.commenters = ''
    return list(parser)


def literal(token):
    if token.startswith("'") and token.endswith("'"):
        return shlex.split(token)[0]
    if any(c in token for c in '$`*?[]~'):
        raise ValueError('exec 参数不接受动态 shell 展开')
    result = shlex.split(token)
    if len(result) != 1:
        raise ValueError('不是单个参数')
    return result[0]


def validate(recipe, target):
    parts = tokens(recipe)
    if parts == ['mkdir', '-p', 'output/log', 'output/trace', 'outputs']:
        return 'prepare'
    clause = target.removeprefix('solve-')
    if not clause or not all(c.isascii() and (c.isalnum() or c == '_') for c in clause):
        raise ValueError('无法识别 solve 目标')
    # 只接受原 runner 的完整计数器语法；引号由 shlex 识别，不按行/正则切命令。
    if len(parts) < 25 or parts[:4] != ['n=', '$', '(', 'flock'] or parts[5:7] != ['sh', '-c']:
        raise ValueError('不支持的 recipe 结构：缺少原生 flock 计数器')
    counter = literal(parts[4])
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./-' for c in counter):
        raise ValueError('计数器路径含不支持字符')
    expected = f'v=$(cat {counter} 2>/dev/null || echo 0); v=$((v+1)); echo $v > {counter}; echo $v'
    if parts[7] != "'" + expected + "'" or parts[8:10] != [');', 'echo']:
        raise ValueError('不支持的计数器命令')
    progress = parts[10]
    if not (progress.startswith('"[$n/') and progress.endswith('] solve-' + clause + '"')):
        raise ValueError('不支持的原生进度命令')
    total = progress[len('"[$n/'):-(len('] solve-' + clause + '"'))]
    if total and not total.isdigit():
        raise ValueError('进度分母不是整数')
    if parts[11:14] != [';', 'RUST_BACKTRACE=1', 'exec']:
        raise ValueError('recipe 必须通过受管 exec 执行')
    if parts[-5] != '>' or parts[-3:] != ['2', '>&', '1']:
        raise ValueError('必须保留 stdout/stderr 日志重定向')
    if literal(parts[-4]) != f'output/log/{clause}.log':
        raise ValueError('日志路径与 clause 不匹配')
    body = parts[14:-5]
    if any(token in (';', '&', '&&', '|', '||', '(', ')', '>', '<', '>>', '>&') for token in body):
        raise ValueError('exec 中不接受额外 shell 命令')
    argv = [literal(token) for token in body]
    # sniff 还检查输入存在和路径角色；这里只核对监督器身份，输入冻结在编译之后由主控完成。
    if len(argv) < 6 or Path(argv[0]).name != 'python3' or argv[2] != 'run':
        raise ValueError('只接受 python3 solve_process.py run')
    if Path(argv[1]).resolve() != (Path.cwd() / 'scripts/solve_process.py').resolve():
        raise ValueError('监督脚本身份不匹配')
    if argv[3:5] != ['--clause', clause] or '--' not in argv[5:]:
        raise ValueError('监督器 clause 不匹配')
    return 'solve'


BOOTSTRAP = r'''
exec() {
    if [[ "$#" -ge 3 && "${2##*/}" == solve_process.py && "$3" == run ]]; then
        builtin exec "$ISLA_SCHEDULER_PYTHON" "$ISLA_SCHEDULER_PROXY" -- "$@"
    else
        echo 'scheduler: exec 身份不匹配' >&2
        return 125
    fi
}
eval -- "$1"
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True)
    parser.add_argument('-c', dest='recipe', required=True)
    args = parser.parse_args()
    try:
        validate(args.recipe, args.target)
    except (ValueError, IndexError) as error:
        print('scheduler 接入拒绝：' + str(error), file=sys.stderr)
        return 125
    if 'ISLA_SCHEDULER_RUN' not in os.environ:
        print('scheduler 接入缺少本轮 controller', file=sys.stderr)
        return 125
    env = dict(os.environ, ISLA_SCHEDULER_PYTHON=sys.executable,
               ISLA_SCHEDULER_PROXY=str(SCHEDULER / 'native/proxy.py'))
    # Bash 解释原文本；只有 exec 是函数，前置 mkdir/flock/echo 全留在本机。
    os.execve('/bin/bash', ['/bin/bash', '--noprofile', '--norc', '-c', BOOTSTRAP,
                             'scheduler-make-shell', args.recipe], env)


if __name__ == '__main__':
    raise SystemExit(main())
