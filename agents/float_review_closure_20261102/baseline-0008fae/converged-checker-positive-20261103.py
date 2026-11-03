#!/usr/bin/env python3
"""单次冻结永久检查器，独立核最终四IR及特殊控制。"""
from pathlib import Path
import contextlib,hashlib,io,json,sys,types
R=Path.cwd();O=R/'agents/float_review_closure_20261102/baseline-0008fae';D=R/'isla/test/float_ir'
raw=(D/'check_float_closure_branches.py').read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha=='9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf'
(O/('converged-checker-'+sha+'.py')).write_bytes(raw)
m=types.ModuleType('check_float_closure_branches');m.__file__=str(D/'check_float_closure_branches.py');exec(compile(raw,m.__file__,'exec'),m.__dict__);sys.modules[m.__name__]=m
sb=(D/'check_special_semantic_branches.py').read_bytes();sp=types.ModuleType('special');sp.__file__=str(D/'check_special_semantic_branches.py');exec(compile(sb,sp.__file__,'exec'),sp.__dict__)
rows=[]
for config in ('rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64'):
 p=R/'agents/float_review_closure_20261102/validation/generation/model-converged-0f7b8fb'/config/(config+'.ir');s=p.read_text()
 for name,mod in [('closure',m),('special',sp)]:
  out=io.StringIO()
  with contextlib.redirect_stdout(out):results=mod.check(s,p)
  if mod is m:assert len(results)==(51 if config=='rv32d' else 53)
  rows.append(dict(config=config,checker=name,status='PASS',ir_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),stdout=out.getvalue()))
reds=[]
for p in (R/'.worktree/runner-float/isla/rv64d.ir',R/'agents/float_review_closure_20261102/validation/generation/model-e9d69d2/rv64d_v128_e64/rv64d_v128_e64.ir'):
 try:m.check(p.read_text(),p)
 except AssertionError as ex:reds.append(dict(path=str(p.relative_to(R)),reason=str(ex)))
 else:raise AssertionError('old IR unexpectedly green')
assert (D/'check_float_closure_branches.py').read_bytes()==raw
report=dict(status='PASS four final IR x two checkers; old a877/e9 red',checker_sha256=sha,special_sha256=hashlib.sha256(sb).hexdigest(),run_sha256=hashlib.sha256((D/'run.py').read_bytes()).hexdigest(),rows=rows,old_reds=reds)
(O/'converged-checker-positive-20261103.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['status'])
