#!/usr/bin/env python3
"""只读复制历史浮点工具链，核对关键工具字节，不修改历史目录。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'output/memory-enum-20261107/toolchain'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prior-workspace', type=Path, required=True)
args = parser.parse_args()
prior = args.prior_workspace.resolve(strict=True)
snapshot = 'isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src'
plugin = '.tmp/float-full-trace-20260929/fvv-branch-candidate/sail_plugin_isla.cmxs'
shutil.copytree(prior/snapshot, OUT/'sail-src', symlinks=False, ignore=shutil.ignore_patterns('.git'))
shutil.copy2(prior/plugin, OUT/'sail_plugin_isla.cmxs')
expected = {'sail-src/sail':'2e89d5f5467195ea0a2fb4b072133a0ee73933db3e8808b8a6518c7ef59ec807',
            'sail-src/_build/install/default/bin/sail':'373a37c268779bad65381b98c3dc13d56c3db9db90102d28d6f410278b23d45a',
            'sail_plugin_isla.cmxs':'c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6'}
for name, value in expected.items():
    assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==value, name
(OUT/'copy.json').write_text(json.dumps({'snapshot':snapshot,'plugin':plugin,'files_sha256':expected},indent=2)+'\n')
