#!/usr/bin/env python3
"""只读核用户授权的77回退实际提交、五hash及KEEP/OPEN保持。"""
from pathlib import Path
import hashlib,json,re,subprocess
R=Path.cwd();M=R/'.worktree/sail-riscv-float-converged-20261103';O=R/'agents/float_review_closure_20261102/baseline-0008fae';D=O/'reduction/new-policy';BASE='e9d69d2f28586c089244c8e37ee4c904c5114458'
expected={
'model/core/ieee_fp_exceptions.sail':('candidate-ieee_fp_exceptions.sail','7ed9529baac57717875ea49e8fff5130d3ec611f824aa71483b2b856d67c96b4'),
'model/extensions/V/vext_fp_utils_insts.sail':('candidate-vext_fp_utils_insts.sail','34191de93086708b44f552606b39878e1ad68be07c67fb2321eb7bec1b1172e1'),
'model/extensions/FD/softfloat_symbolic_f16.sail':('wrappers-softfloat_symbolic_f16.sail','715795790c0efb100806c0a82195e137c4de66c4a9614baac9ee2b0b333a0646'),
'model/extensions/FD/softfloat_symbolic_f32.sail':('wrappers-softfloat_symbolic_f32.sail','ffe71d8f99652a20f9c7c6d969648af75bdc575ee9f2ca34e459fdfa879c5e17'),
'model/extensions/FD/softfloat_symbolic_f64.sail':('wrappers-softfloat_symbolic_f64.sail','b5b8ea9e4723e647fa74ea8ebfa47129106993a3a99d9df80105f9b3eab545ce')}
git=lambda *a:subprocess.check_output(['git','-C',str(M),*a],text=True).strip()
h=lambda b:hashlib.sha256(b).hexdigest()
def block(s,n):
 st=s.index('function '+n+'(');br=s.index('{',st);en=br+1;dep=1
 while dep:dep+=(s[en]=='{')-(s[en]=='}');en+=1
 return s[st:en]
assert not git('status','--porcelain'),'actual tree not clean/frozen yet'
head=git('rev-parse','HEAD');commits=git('rev-list','--reverse',BASE+'..HEAD').splitlines();assert len(commits)==3,commits
expected_groups=[['model/core/ieee_fp_exceptions.sail'],['model/extensions/V/vext_fp_utils_insts.sail'],sorted(p for p in expected if '/FD/' in p)]
commit_rows=[]
for commit,files in zip(commits,expected_groups):
 got=sorted(git('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines());assert got==files,(commit,got,files)
 assert len(git('show','-s','--format=%P',commit).split())==1
 commit_rows.append({'commit':commit,'subject':git('show','-s','--format=%s',commit),'files':got})
assert sorted(git('diff','--name-only',BASE,'HEAD').splitlines())==sorted(expected)
files=git('ls-files','model').splitlines();assert len(files)==166
rows=[]
for p in files:
 actual=(M/p).read_bytes();base=subprocess.check_output(['git','-C',str(M),'show',BASE+':'+p]);assert actual==subprocess.check_output(['git','-C',str(M),'show','HEAD:'+p])
 if p in expected:
  candidate,sha=expected[p];assert h(actual)==sha and actual==(D/candidate).read_bytes();rows.append({'file':p,'sha256':sha,'signed_candidate':candidate})
 else:assert actual==base,p
# The still-OPEN write guard / mode guards / inner calculation gates are not opportunistically changed.
for fmt,n in ((32,'riscv_f32ToF16'),(64,'riscv_f64ToF32')):
 p=f'model/extensions/FD/softfloat_symbolic_f{fmt}.sail';assert block((M/p).read_text(),n)==block(git('show',BASE+':'+p),n)
core=(M/'model/core/ieee_fp_exceptions.sail').read_text();oldcore=git('show',BASE+':model/core/ieee_fp_exceptions.sail')
unchanged_core=['ieee_fp_to_int_core',*[f'ieee_round{w}_exceptions' for w in (16,32,64)],'ieee_convert32_to_16_exceptions','ieee_convert64_to_16_exceptions','ieee_convert64_to_32_exceptions','ieee_bf16_from_f32_exceptions','ieee_rod32_to_16','ieee_rod64_to_32']
for n in unchanged_core:assert block(core,n)==block(oldcore,n),n
for w in (16,32,64):
 for op in ('add','sub','mul','div','sqrt','fma'):
  n=f'ieee_{op}{w}_exceptions';b=block(core,n);assert len(re.findall(r'\bif\b',b))==1 and re.search(r'if (finite|valid) then \{',b)
v=(M/'model/extensions/V/vext_fp_utils_insts.sail').read_text();oldv=git('show',BASE+':model/extensions/V/vext_fp_utils_insts.sail')
for n in ('riscv_f16ToI16','riscv_f16ToI8','riscv_f32ToI16','riscv_f16ToUi16','riscv_f16ToUi8','riscv_f32ToUi16'):assert block(v,n)==block(oldv,n)
assert len(re.findall(r'\bif\b',block(v,'riscv_f16ToI16_pure')))==1 and 'if overflow then' in block(v,'riscv_f16ToI16_pure')
# All complete frozen source manifests remain intact.
for tree,batch in [(R/'.worktree/sail-riscv-general-float-by-model-20261022','model-e9d69d2'),(R/'.worktree/runner-float/sail-riscv','model-21418d0')]:
 a=json.loads((R/'agents/float_review_closure_20261102/validation/generation'/batch/'source.json').read_text());assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==a['commit'];assert all(h((tree/'model'/p).read_bytes())==sha for p,sha in a['model_files'].items())
removed=0
for p in expected:
 a=git('show',BASE+':'+p);b=(M/p).read_text();strip=lambda s:re.sub(r'//[^\n]*','',s);removed+=len(re.findall(r'\bif\b',strip(a)))-len(re.findall(r'\bif\b',strip(b)))
assert removed==77,removed
report={'status':'PASS actual converged source commits and signed contents','model_tree':str(M.relative_to(R)),'base':BASE,'head':head,'commits':commit_rows,'model_tracked_files':166,'unchanged_other_model_files':161,'changed_file_hashes':rows,'pure_if_sites_reverted':77,'KEEP_and_OPEN_preserved':['fdext_regs entire file, including changed/Ext_F','ROD two mode wrappers exact bytes','FPint/round/conversion/BF16/ROD inner helpers exact bytes','18 arithmetic finite/valid guards retained','existing f16-i16 overflow retained, other pure narrow dataflow6202','ordinary six narrow adapters exact bytes','all other 161 model files, including NaN/canonical/mappings unchanged'],'OPEN_disposition':'user explicitly deferred:29 calculation gates,changed1,RODmode2,existing6202 f16i16 outer overflow1; not this stage research blockers','frozen_e9_and214_166_sources_each_unchanged':True,'scope':'source/commit identity only; strict generation, new IR/CFG and dynamic budgets separately reviewed'}
(O/'converged-source-review-20261103.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
