#!/usr/bin/env python3
"""独立重算五入口、配置和来源sidecar哈希，可选核对根仓版本记录。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ISLA = ROOT/'isla'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check-topic', action='store_true')
args = parser.parse_args()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


manifest_path = ISLA/'ir/provenance/manifest.json'
manifest = json.loads(manifest_path.read_text())
model_commit = subprocess.check_output(['git','-C',str(ROOT/'sail-riscv'),'rev-parse','HEAD'],text=True).strip()
assert model_commit == manifest['model_commit']
rows = []
for artifact in manifest['artifacts']:
    config = ISLA/'ir/provenance'/artifact['config']
    assert sha(config) == artifact['config_sha256']
    receipt_path = ISLA/'ir/provenance'/artifact['provenance']
    assert sha(receipt_path) == artifact['provenance_sha256']
    receipt = json.loads(receipt_path.read_text())
    generation = receipt['generation']
    assert generation['ir_sha256'] == artifact['sha256']
    assert generation['config_sha256'] == sha(config)
    assert generation['model_commit'] == model_commit and generation['exit_code'] == 0
    for name, value in generation['model_files'].items():
        assert sha(ROOT/'sail-riscv/model'/name) == value == artifact['model_files'][name]['sha256']
    for relative in artifact['paths']:
        actual = sha(ISLA/relative)
        assert actual == artifact['sha256'], relative
        rows.append({'path':'isla/'+relative,'sha256':actual,'config':artifact['config']})
assert len(rows) == 5 and len({r['path'] for r in rows}) == 5
assert (ISLA/'rv64d.ir').read_bytes() == (ISLA/'ir/rv64d_v128_e64.ir').read_bytes()
audit = manifest['generation_audit']
assert sha(ROOT/audit['path']) == audit['sha256']
if args.check_topic:
    topic = json.loads((ROOT/'specs/topic-version.json').read_text())
    assert topic['components']['sail-riscv']['commit'] == model_commit
    # 清单记录生成时的 Isla 源码基准；topic 固定的是随后提交了 IR 与来源记录的 Isla 提交，
    # 清单不可能包含自己所在提交的哈希，所以要求基准是固定提交的祖先（或相等）。
    pinned = topic['components']['isla']['commit']
    subprocess.run(['git','-C',str(ISLA),'merge-base','--is-ancestor',manifest['isla_commit'],pinned],check=True)
    assert subprocess.run(['git','-C',str(ISLA),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip() == pinned
    assert topic['ir']['sha256'] == sha(ROOT/topic['ir']['path'])
    assert sha(manifest_path) in topic['ir']['provenance']
    assert topic['publication']['status'] == '待发布'
report = {'pass':True,'model_commit':model_commit,'manifest_sha256':sha(manifest_path),
          'artifacts':rows,'topic_checked':args.check_topic}
out = ROOT/'output/memory-enum-20261107/final-provenance-check.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report,indent=2,ensure_ascii=False))
