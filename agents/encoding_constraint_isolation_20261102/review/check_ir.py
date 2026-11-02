#!/usr/bin/env python3
"""独立核对四配置来源、函数改动、overflow CFG 和永久回归。"""
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MODEL = ROOT / '.worktree/runner-float/sail-riscv'
GEN = ROOT / 'agents/encoding_constraint_isolation_20261102/saturation/generation'
OLD = ROOT / 'agents/special_control_restore_20261102/implementation/generation'
COMMIT = '6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a'
SCRIPT = ROOT / 'isla/test/float_ir/check_special_semantic_branches.py'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def functions(text):
    result = {}
    for name, args, body in re.findall(r'(?ms)^fn ([^\n(]+)\(([^\n]*)\) \{\n(.*?)^\}', text):
        body = re.sub(r'`\d+(?: \d+:\d+(?:-\d+:\d+)?)?', '', body)
        body = re.sub(r'([\w./-]+\.sail):\d+\.\d+-\d+\.\d+', r'\1:LOC', body)
        formal_names=[arg.strip() for arg in args.split(',') if arg.strip()]
        variables = {arg:'arg'+str(i) for i,arg in enumerate(formal_names)}
        def rename(match):
            token=match[0]
            if token not in variables: variables[token]='tmp'+str(len(variables))
            return variables[token]
        pattern=r'(?<![A-Za-z0-9_$])(?:zz\d+'+''.join('|'+re.escape(arg) for arg in formal_names)+r')(?![A-Za-z0-9_$])'
        body = re.sub(pattern, rename, body)
        result[name] = (len(formal_names), body)
    return result

spec=importlib.util.spec_from_file_location('permanent_ir_review', SCRIPT)
permanent=importlib.util.module_from_spec(spec); spec.loader.exec_module(permanent)
records = {}
for name in ['rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64']:
    directory = GEN/name
    generation=json.loads((directory/'generation.json').read_text())
    driver=json.loads((directory/'driver.json').read_text())
    ir=directory/(name+'.ir')
    assert generation['exit_code']==driver['exit_code']==0
    assert generation['model_commit']==driver['model_commit']==driver['model_commit_at_start']==COMMIT
    assert driver['source_unchanged'] and not driver['model_dirty']
    assert generation['model_files']==driver['model_files']
    assert generation['ir_sha256']==driver['ir_sha256']==sha(ir)
    assert all(flag in generation['command'] for flag in ['SYMBOLIC','--strict-var','--strict-bitvector','--strict-exponentials'])
    for filename, digest in generation['model_files'].items():
        data=subprocess.check_output(['git','-C',str(MODEL),'show',COMMIT+':model/'+filename])
        assert hashlib.sha256(data).hexdigest()==digest, filename
        assert sha(MODEL/'model'/filename)==digest, filename
    command=generation['command']
    for flag,key in [('--config','config_sha256'),('-plugin','plugin_sha256')]:
        assert sha(Path(command[command.index(flag)+1]))==generation[key]
    assert sha(Path(command[0]))==generation['sail_launcher_sha256']
    before=functions((OLD/name/(name+'.ir')).read_text())
    after=functions(ir.read_text())
    changes=[fn for fn in before.keys()|after.keys() if before.get(fn)!=after.get(fn)]
    assert changes==['zriscv_f16ToI16_pure'], changes
    body=after[changes[0]][1]
    assert len(re.findall(r'(?m)^\s*jump ',body))==1
    output=io.StringIO()
    with contextlib.redirect_stdout(output): permanent.check(ir.read_text(),ir.relative_to(ROOT))
    (HERE/(name+'-ir.log')).write_text(output.getvalue())
    records[name]={'ir_sha256':sha(ir),'source_files_verified':len(generation['model_files']),'normalized_changed_functions':changes,'permanent_cfg_checks':'passed'}
ordinary=json.loads((GEN/'ordinary-strict/driver.json').read_text())
initial=json.loads((GEN/'ordinary-strict/driver.initial.json').read_text())
assert ordinary['exit_code']==initial['exit_code']==0
assert ordinary['source_unchanged'] and ordinary['source_matches_model_commit']
assert ordinary['model_files']==initial['model_files']==generation['model_files']
assert ordinary['model_commit_at_start']=='a9fd9476fc1bf471070a38e01ee9233d10d742d3' and ordinary['model_dirty_at_start']
assert ordinary['model_commit']==COMMIT and not ordinary['model_dirty']
records['ordinary']={'exit_code':0,'source_files_verified':len(ordinary['model_files']),'note':'检查以a9fd947+未提交补丁启动；全部源码字节与最终6202e23提交一致，初始记录已保留'}
records['regression_script_sha256']=sha(SCRIPT)
(HERE/'ir-checks.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(records,ensure_ascii=False,indent=2))
