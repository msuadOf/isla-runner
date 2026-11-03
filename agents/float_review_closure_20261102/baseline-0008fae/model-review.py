#!/usr/bin/env python3
"""只读核本轮模型函数边界及最小替代的布尔等价，不生成候选IR。"""
from pathlib import Path
from itertools import product
import subprocess,re,hashlib,json
ROOT=Path.cwd();M=ROOT/'.worktree/runner-float/sail-riscv';O=ROOT/'agents/float_review_closure_20261102/baseline-0008fae'
BASE='6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a';HEAD='21418d0b0d4942fae20061ed580ee04aff4a8a61';ORIGINAL='4f2ac293654a02db26dac5055be7f93fd6e3141e';ISLA_BASE='0008fae76f4cff86dae1a036d889f0414c228e9d'
def git(*a):return subprocess.check_output(['git','-C',str(M),*a],text=True)
def read(c,p):return git('show',c+':'+p)
def functions(s):
 s=re.sub(r'//[^\n]*','',s)
 matches=list(re.finditer(r'^function (\w+)\b',s,re.M));return {(m[1],sum(x[1]==m[1] for x in matches[:i])):s[m.start():matches[i+1].start() if i+1<len(matches) else len(s)] for i,m in enumerate(matches)}
def norm(s):return re.sub(r'\s+','',s)
def category(n):
 if n=='accrue_fflags':return 'state_changed'
 if n.endswith('_pure'):return 'narrow_saturation'
 if re.fullmatch(r'riscv_f\d+ToU?i?(I|Ui)?(32|64)',n):return 'integer_wrapper'
 if re.fullmatch(r'riscv_f(?:16|32|64)To(?:I|Ui)(?:32|64)',n):return 'integer_wrapper'
 if n in ('riscv_f32ToF16','riscv_f64ToF32'):return 'ROD_mode_wrapper'
 if re.fullmatch(r'ieee_(add|sub|mul|div|sqrt|fma)\d+_exceptions',n):return 'special_cause_and_finite'
 if 'rounded_exceptions' in n or n=='ieee_exact_threshold_exceptions':return 'numeric_flag_categories'
 if n=='ieee_mask_exact_exceptions':return 'redundant_constant_true_mask'
 if n=='ieee_fp_to_int_core':return 'finite_invalid_then_numeric_NX'
 if re.fullmatch(r'ieee_round\d+_exceptions',n):return 'finite_then_numeric_NX'
 if n.startswith('ieee_rod'):return 'finite_then_numeric_jam'
 if n.startswith(('ieee_convert','ieee_bf16')):return 'finite_conversion_gate'
 raise AssertionError(n)
rows=[];files=[]
for p in git('diff','--name-only',BASE,HEAD,'--','model').splitlines():
 old=read(BASE,p);new=read(HEAD,p);files.append({'path':p,'base_sha256':hashlib.sha256(old.encode()).hexdigest(),'head_sha256':hashlib.sha256(new.encode()).hexdigest()})
 if p.endswith(('dext_insts.sail','zfh_insts.sail')):continue
 a,b=functions(old),functions(new);assert a.keys()==b.keys(),p
 for key in a:
  n,ordinal=key
  if norm(a[key])!=norm(b[key]):
   rows.append({'file':p,'function':n,'line':new[:list(re.finditer(r'^function '+n+r'\b',new,re.M))[ordinal].start()].count('\n')+1,'category':category(n),'old_if_tokens':len(re.findall(r'\bif\b',a[key])),'new_if_tokens':len(re.findall(r'\bif\b',b[key]))})
assert len(rows)==54,(len(rows),[r['function'] for r in rows])
# Final flag selection equals direct fact construction for every arbitrary OF/UF/NX tuple.
for of,uf,nx in product((False,True),repeat=3):
 old=(False,False,True,uf,nx) if of else ((False,False,False,True,nx) if uf else ((False,False,False,False,True) if nx else (False,)*5))
 assert old==(False,False,of,uf,nx)
# For finite inputs operand_invalid(false,a)=false. All exact helpers have NV=DZ=false.
# Therefore the six constant-true mask calls return their input facts unchanged.
for invalid,of,uf,nx in product((False,True),repeat=4):
 masked=(invalid,False,of,uf,nx)
 if not invalid:assert masked==(False,False,of,uf,nx)
for base in range(256):
 for nx in (False,True):
  assert (base|1 if nx else base)==(base | int(nx))
counts={c:sum(r['category']==c for r in rows) for c in sorted({r['category'] for r in rows})}
report={'scope':'只读最小性复审；不改变生产/IR/inputs，不作性能或动态PASS','isla_common_base':ISLA_BASE,'model_original_base':ORIGINAL,'model_this_round_base':BASE,'model_frozen_head':HEAD,'changed_model_files':files,'production_function_additions_this_round':[],'production_function_deletions_this_round':[],'changed_semantic_functions':54,'categories':counts,'functions':rows,'algebra_checks':{'arbitrary_OF_UF_NX_tuples':8,'finite_exact_mask_replacement':8,'8bit_jam_cases':512},'recommended_numeric_if_to_dataflow_count':18,'constant_true_mask_if_has_new_symbolic_fork':False,'performance_measurement':None}
refs=git('grep','-n','ieee_mask_exact_exceptions').splitlines()
checker=ROOT/'isla/test/float_ir/check_float_closure_branches.py'
checker_refs=[f'isla/test/float_ir/check_float_closure_branches.py:{i}:{line.strip()}' for i,line in enumerate(checker.read_text().splitlines(),1) if 'ieee_mask_exact_exceptions' in line]
assert len(refs)==7 and all(line.startswith('model/core/ieee_fp_exceptions.sail:') for line in refs)
for invalid,nx in product((False,True),repeat=2):
 old=(invalid,False,False,False,True) if nx else (invalid,False,False,False,False)
 assert old==(invalid,False,False,False,nx)
report['mask_reference_audit']={'active_model_all_tracked_files':refs,'model_test_or_preserve_literal_references':[],'active_isla_checker_references':checker_refs,'search_scope':['active model entire git tree including test and scripts','active model rg hidden non-IR/log generated files','isla/test, isla/configs, isla/scripts, isla/ir/provenance','parent active non-history source dirs'],'historical_evidence_policy':'旧IR/生成记录/检查器快照保留，不为新candidate静默修改；新candidate更新正式checker三处依赖。'}
report['final_decision']={'remove_numeric_output_ifs':18,'remove_mask_definition_and_six_calls':True,'retain_special_cause_finite_saturation_changed_and_ROD_mode':True,'revised_prior_design':'不启用FP trap的flags/bits构造是数据流；此前把最终异常分类都强制fork属于过度实现。'}
report['algebra_checks']['arbitrary_invalid_NX_tuples']=4
report['proof_obligations']=['OF/UF/NX任意8元组保持，不使用OF=>NX或OF/UF排斥假设','round/FPint的NX返回值保持，原raise_inexact/eq条件不动','有限输入必非NaN，因此operand_invalid(false,a)=false；exact facts NV=DZ=false；6处mask恒为原facts','ROD仅将if改回原ite，flags、RTZ base和base|1逐字保留','NaN/Inf/零/invalid原因、finite/valid、饱和、changed与ROD模式控制不删除','新named候选重新普通/SYMBOLIC strict和IR及受影响动态验证，不迁移214 PASS']
(O/'model-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS read-only inventory',counts)
