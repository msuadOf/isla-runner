#!/usr/bin/env python3
"""独立重建18site+6调用最小替代，精确比较下一模型源码；不修改生产。"""
from pathlib import Path
from itertools import product
import re,json,hashlib,subprocess
ROOT=Path.cwd();M=ROOT/'.worktree/sail-riscv-general-float-by-model-20261022';FROZEN=ROOT/'.worktree/runner-float/sail-riscv';OUT=ROOT/'agents/float_review_closure_20261102/baseline-0008fae';BASE='21418d0b0d4942fae20061ed580ee04aff4a8a61';FILE='model/core/ieee_fp_exceptions.sail'
git=lambda m,*args:subprocess.check_output(['git','-C',str(m),*args],text=True)
h=lambda b:hashlib.sha256(b).hexdigest()
a=git(M,'show',BASE+':'+FILE);expected=a
category='''  if overflow then
    ieee_exception_facts(false, false, true, underflow, inexact)
  else if underflow then
    ieee_exception_facts(false, false, false, true, inexact)
  else if inexact then
    ieee_exception_facts(false, false, false, false, true)
  else
    ieee_empty_exceptions(false)'''
assert expected.count(category)==4
expected=expected.replace(category,'  ieee_exception_facts(false, false, overflow, underflow, inexact)')
round_nx='''    if inexact then
      ieee_exception_facts(invalid_nan, false, false, false, true)
    else
      ieee_empty_exceptions(invalid_nan)'''
assert expected.count(round_nx)==3
expected=expected.replace(round_nx,'    ieee_exception_facts(invalid_nan, false, false, false, inexact)')
core_nx='''      if inexact then
        ieee_exception_facts(false, false, false, false, true)
      else
        ieee_empty_exceptions(false)'''
assert expected.count(core_nx)==1
expected=expected.replace(core_nx,'      ieee_exception_facts(false, false, false, false, inexact)')
for constant in ('0x0001','0x00000001'):
 old=f'''  if ieee_has_inexact(flags) then
    (flags, base_bits | {constant})
  else
    (flags, base_bits)'''
 assert expected.count(old)==1
 expected=expected.replace(old,f'  (flags, ite(ieee_has_inexact(flags), base_bits | {constant}, base_bits))')
assert expected.count('ieee_mask_exact_exceptions(invalid_nan, true, facts)')==6
expected=expected.replace('ieee_mask_exact_exceptions(invalid_nan, true, facts)','facts')
expected,count=re.subn(r'(?ms)^function ieee_mask_exact_exceptions\b.*?(?=^function ieee_fp_to_int_core\b)','',expected);assert count==1
p=M/FILE;b=p.read_bytes();actual=b.decode();norm=lambda text:re.sub(r'\s+','',re.sub(r'//[^\n]*','',text))
assert norm(actual)==norm(expected),'candidate不等于独立重建的18site+mask最小替代'
assert not re.search(r'ieee_mask_exact_exceptions',actual)
# Scope is checked against the frozen commit, including the candidate's uncommitted worktree.
paths=git(M,'diff','--name-only',BASE,'--','model').splitlines();assert paths==[FILE],paths
# Per-function changes, excluding removed mask.
def funcs(text):
 starts=list(re.finditer(r'^function (\w+)\b',text,re.M));return {m[1]:text[m.start():starts[i+1].start() if i+1<len(starts) else len(text)] for i,m in enumerate(starts)}
af,bf=funcs(a),funcs(actual);assert af.keys()-bf.keys()=={'ieee_mask_exact_exceptions'} and not bf.keys()-af.keys()
changed=[name for name in bf if norm(af[name])!=norm(bf[name])];assert len(changed)==14,changed
for of,uf,nx in product((False,True),repeat=3):
 old=(False,False,True,uf,nx) if of else ((False,False,False,True,nx) if uf else ((False,False,False,False,True) if nx else (False,)*5));assert old==(False,False,of,uf,nx)
for invalid,nx in product((False,True),repeat=2):assert ((invalid,False,False,False,True) if nx else (invalid,False,False,False,False))==(invalid,False,False,False,nx)
for base in range(1<<16):
 for nx in (False,True):assert (base|1 if nx else base)==base|int(nx)
# Every other tracked model input equals BASE byte-for-byte (git diff also catches tracked dirty input).
assert git(FROZEN,'rev-parse','HEAD').strip()==BASE and h((FROZEN/FILE).read_bytes())==h(a.encode())
frozen_inputs=json.loads((ROOT/'agents/float_review_closure_20261102/validation/generation/model-21418d0/source.json').read_text())['model_files']
assert len(frozen_inputs)==166 and all(h((FROZEN/'model'/name).read_bytes())==value for name,value in frozen_inputs.items())
assert p.read_bytes()==b,'candidate在审查期间变化'
report={'status':'PASS source-only independent exact transformation','base':BASE,'candidate_HEAD':git(M,'rev-parse','HEAD').strip(),'candidate_status':git(M,'status','--porcelain').splitlines(),'candidate_file':FILE,'source_sha256':h(b),'independent_expected_normalized_sha256':h(norm(expected).encode()),'actual_normalized_sha256':h(norm(actual).encode()),'changed_functions':changed,'removed_functions':['ieee_mask_exact_exceptions'],'numeric_if_sites_removed':18,'constant_true_calls_removed':6,'other_tracked_model_files_unchanged':True,'frozen_214_source_unchanged':True,'frozen_tracked_model_files_verified':166,'boolean_tuples':8,'invalid_NX_tuples':4,'jam16_cases':131072,'source_contract':'除列出的facts/ite和mask删除，全部数值公式、NaN/Inf/零/invalid原因、finite/valid和其他控制逐字规范化保持','not_signed':['Sail strict compilation','new IR','new dynamic campaign','runtime performance']}
(OUT/'model-review.candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
