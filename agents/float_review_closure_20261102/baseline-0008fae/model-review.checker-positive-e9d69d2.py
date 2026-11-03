#!/usr/bin/env python3
"""冻结单次checker源码，核四新IR及旧a877，保留集成文件哈希。"""
from pathlib import Path
import argparse,contextlib,hashlib,io,json,sys,types
R=Path.cwd();O=R/'agents/float_review_closure_20261102/baseline-0008fae';D=R/'isla/test/float_ir'
p=argparse.ArgumentParser();p.add_argument('--checker-sha',required=True);args=p.parse_args()
raw=(D/'check_float_closure_branches.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha==args.checker_sha
m=types.ModuleType('check_float_closure_branches');m.__file__=str(D/'check_float_closure_branches.py');exec(compile(raw,m.__file__,'exec'),m.__dict__);sys.modules[m.__name__]=m
sp=D/'check_special_semantic_branches.py';sb=sp.read_bytes();special=types.ModuleType('special');special.__file__=str(sp);exec(compile(sb,str(sp),'exec'),special.__dict__)
rows=[]
for config in ('rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64'):
 ir=R/'agents/float_review_closure_20261102/validation/generation/model-e9d69d2'/config/(config+'.ir');text=ir.read_text()
 for checker,mod in [('check_float_closure_branches.py',m),('check_special_semantic_branches.py',special)]:
  output=io.StringIO()
  with contextlib.redirect_stdout(output):results=mod.check(text,ir)
  if mod is m:assert len(results)==(51 if config=='rv32d' else 53)
  rows.append({'config':config,'checker':checker,'exit_code':0,'ir_sha256':hashlib.sha256(ir.read_bytes()).hexdigest(),'stdout':output.getvalue()})
old=R/'.worktree/runner-float/isla/rv64d.ir';error=None
try:m.check(old.read_text(),old)
except AssertionError as e:error=str(e)
assert error and 'changed' in error
assert (D/'check_float_closure_branches.py').read_bytes()==raw and sp.read_bytes()==sb
report={'status':'PASS frozen new checker + special on four IR, old a877 red','closure_checker_sha256':sha,'special_checker_sha256':hashlib.sha256(sb).hexdigest(),'run_sha256':hashlib.sha256((D/'run.py').read_bytes()).hexdigest(),'readme_sha256':hashlib.sha256((D/'README.md').read_bytes()).hexdigest(),'execution':'同一冻结源码模块核全部配置，不把当前文件末次哈希误当每次命令版本','rows':rows,'old_ir':{'sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'rejected':True,'reason':error},'scope':'新生成目录的静态回归；未声称根目录安装IR默认run.py全套或动态通过'}
(O/'model-review.checker-positive-e9d69d2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS',sha,':8 new checks + old a877 red')
