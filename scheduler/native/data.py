"""无容器节点结果管理；取数只读已有 attempt，不重新求解。"""
import argparse
import json
from pathlib import Path
import re
import uuid

from scheduler.native.common import SCHEDULER, load_config
from scheduler.native import transport


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['native', 'condor'], default='native')
    parser.add_argument('--config')
    parser.add_argument('--node', required=True)
    parser.add_argument('--job-id')
    parser.add_argument('--destination')
    parser.add_argument('action', choices=['list', 'summary', 'fetch', 'delete'])
    args = parser.parse_args(argv)
    if args.action != 'list' and not re.fullmatch(r'[a-f0-9]{32}', args.job_id or ''):
        raise ValueError('summary/fetch/delete 必须提供 32 位 --job-id')
    config = load_config(args.config)
    node = next((n for n in config['nodes'] if n['name'] == args.node), None)
    if node is None:
        raise ValueError('node 不在配置中')
    request = dict(action=args.action, job_id=args.job_id)
    child = transport.start(node, request)
    try:
        if args.action == 'fetch':
            target = Path(args.destination) if args.destination else (
                SCHEDULER / 'runtime/native/retrieved' / node['name'] /
                f'{args.job_id}-{uuid.uuid4().hex}.tar.gz')
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + '.partial-' + uuid.uuid4().hex)
            try:
                with partial.open('wb') as output:
                    for chunk in iter(lambda: child.stdout.read(1024 * 1024), b''):
                        output.write(chunk)
                child.stdin.close()
                if child.wait() != 0:
                    raise RuntimeError(transport.errors(child))
                partial.replace(target)
            finally:
                partial.unlink(missing_ok=True)
            print(target)
        else:
            result = transport.response(child)
            child.stdin.close()
            if child.wait() != 0:
                raise RuntimeError(transport.errors(child))
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        transport.close(child)
