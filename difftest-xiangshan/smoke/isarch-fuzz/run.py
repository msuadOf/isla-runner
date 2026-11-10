#!/usr/bin/env python3
"""实测动态前态回归和 Isla 原生 fuzz；日志写入新目录。"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    assets = Path(__file__).resolve().parent
    root = assets.parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isla-dir', type=Path, default=root / 'isla')
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--ir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['all', 'python', 'native'], default='all')
    parser.add_argument('--threads', type=int, default=32)
    args = parser.parse_args()
    isla = args.isla_dir.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for name in ['tmp', 'cache', 'process', 'elf']:
        (out / name).mkdir()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(out / 'tmp'),
               XDG_CACHE_HOME=str(out / 'cache'), ISLA_STATS='1',
               PT_DECODE_DIR=str(isla / 'agents/path_merge_call_support/pt_decode'),
               PAGING_TEST_OUTPUT_DIR=str(out / 'elf'))
    env.pop('ISLA_EXPORT_SAMPLES', None)
    results = []

    def run(name, command, cwd):
        with (out / (name + '.log')).open('w') as log:
            result = subprocess.run(command, cwd=cwd, env=env,
                                    stdout=log, stderr=subprocess.STDOUT)
        results.append(dict(name=name, command=command, cwd=str(cwd), exit_code=result.returncode))
        (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f'{name}: exit {result.returncode}', flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)

    if args.mode in ['all', 'python']:
        run('python', [sys.executable, '-m', 'pytest', '-q',
                       str(root / 'difftest-xiangshan/tests')], root)
    if args.mode in ['all', 'native']:
        binary = (args.binary or isla / 'target/release/isarch').resolve()
        ir = (args.ir or isla / 'rv64d.ir').resolve()
        run('native', ['timeout', '--signal=TERM', '--kill-after=3s', '360s',
            str(binary), '--tastic', 'qfaufbv', '-D', 'sr', '--smt-timeout', '5',
            '-A', str(ir), '-C', str(assets / 'isa.toml'), '-T', str(args.threads),
            '--timeout', '60', '--execution-limits-config', str(assets / 'campaign.toml'),
            '--path-merging', '--prestate', 'satp=0x8000000000080200',
            '--prestate', 'menvcfg={bits=0x0000000000000000}',
            '--prestate', 'senvcfg={bits=0x0000000000000000}',
            '--prestate', 'mseccfg={bits=0x0000000000000000}',
            '--fuzz-mode', 'campaign', '--fuzz-scenario', 'generic-sv39-store-smoke',
            '--fuzz-corpus', str(assets / 'corpus.jsonl'), '--fuzz-output', str(out / 'campaign'),
            '--fuzz-budget', '20', '--fuzz-control-percent', '0', '--fuzz-feedback', 'none',
            '--fuzz-batch-size', '20', '--fuzz-seed', '42', '--fuzz-certify-all',
            '--executor', 'model', 'fuzz', '--clause=STORE'], out / 'process')
        certification = json.loads((out / 'campaign/reconfirm.json').read_text())
        assert certification['certified'] and certification['corpus_entries'] == 20
        for name in ['mutants.jsonl', 'judged.jsonl']:
            assert len((out / 'campaign' / name).read_text().splitlines()) == 20
        print('corpus: 20/20 certified; mutants: 20 generated and judged', flush=True)


if __name__ == '__main__':
    main()
