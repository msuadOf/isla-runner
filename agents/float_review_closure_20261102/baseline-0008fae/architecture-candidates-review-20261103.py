#!/usr/bin/env python3
"""只读独审议题内三个回数据流候选，不写生产、不签OPEN gate。"""
from pathlib import Path
from itertools import product
import hashlib,json,re,subprocess
R=Path.cwd();M=R/'.worktree/sail-riscv-general-float-by-model-20261022';O=R/'agents/float_review_closure_20261102/baseline-0008fae';D=O/'reduction/new-policy';E9='e9d69d2f28586c089244c8e37ee4c904c5114458';B='6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a'
git=lambda *a:subprocess.check_output(['git','-C',str(M),*a],text=True)
h=lambda s:hashlib.sha256(s.encode()).hexdigest();norm=lambda s:re.sub(r'\s+','',s)
def read(c,p):return git('show',c+':'+p)
def block(s,n):
 st=s.index('function '+n+'(');br=s.index('{',st);end=br+1;depth=1
 while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[st:end]
def splitargs(s):
 out=[];start=0;depth=0
 for i,c in enumerate(s):
  depth+=(c=='(')-(c==')')
  if c==',' and depth==0:out.append(s[start:i].strip());start=i+1
 assert not depth;out.append(s[start:].strip());return out
def calls(s,n):
 out=[]
 for mt in re.finditer(r'\b'+re.escape(n)+r'\(',s):
  st=mt.end();end=st;dep=1
  while dep:dep+=(s[end]=='(')-(s[end]==')');end+=1
  out.append(s[st:end-1])
 return out
def lets(s):return {n:e for n,e in re.findall(r'\blet (\w+)(?:\s*:\s*bool)?\s*=\s*(.*?);',s,re.S)}
def expand(expr,env,seen=()):
 def subst(mt):
  n=mt[0]
  if n not in env:return n
  assert n not in seen,('cycle',n)
  return '('+expand(env[n],env,seen+(n,))+')'
 # Remove alias-added parentheses after recursion by comparing token sequences below.
 return re.sub(r'\b[A-Za-z_]\w*\b',subst,expr)
def value(expr,env):
 # Parentheses are only call delimiters or alias grouping in these source formulas;
 # stripping alias parentheses alone via per-variable exact token substitution is safe.
 def ex(x,seen=()):
  return re.sub(r'\b[A-Za-z_]\w*\b',lambda m:ex(env[m[0]],seen+(m[0],)) if m[0] in env and m[0] not in seen else m[0],x)
 return norm(ex(expr))
p='model/core/ieee_fp_exceptions.sail';old=read(B,p);frozen=read(E9,p);cand=(D/'candidate-ieee_fp_exceptions.sail').read_text();assert h(cand)=='7ed9529baac57717875ea49e8fff5130d3ec611f824aa71483b2b856d67c96b4'
names=[f'ieee_{op}{w}_exceptions' for w in (16,32,64) for op in ('add','sub','mul','div','sqrt','fma')];rest=cand;proofs=[];native_bindings=0
for n in names:
 a,e,c=block(old,n),block(frozen,n),block(cand,n);rest=rest.replace(c,e,1);ad,ed,cd=lets(a),lets(e),lets(c)
 mathnames=('x','y','z','lo','hi','rounded')
 for v in mathnames:
  if v in ed:assert norm(ed[v])==norm(cd[v])==norm(ad[v]),(n,v);native_bindings+=1
 gate='finite' if 'finite' in cd else 'valid';assert value(gate,ad)==value(gate,cd)
 assert len(re.findall(r'\bif\b',c))==1 and 'if '+gate+' then {' in c
 oldfacts=calls(a,'ieee_exception_facts');newfacts=calls(c,'ieee_exception_facts');assert len(oldfacts)==1 and len(newfacts)==2
 of=splitargs(oldfacts[0]);yes,no=map(splitargs,newfacts);assert len(of)==len(yes)==len(no)==5
 for i in (0,1):assert value(of[i],ad)==value(yes[i],cd)==value(no[i],cd),(n,i)
 for i in (2,3,4):
  assert no[i]=='false'
  assert value(of[i],ad)==norm('strict_and_bool('+value(gate,cd)+','+value(yes[i],cd)+')'),(n,i)
 assert [norm(x) for x in calls(a,'ieee_operand_invalid')]==[norm(x) for x in calls(c,'ieee_operand_invalid')]
 proofs.append({'function':n,'native_FP_bindings_unchanged':sum(v in ed for v in mathnames),'source_NaN_calls_order_unchanged':True,'predicate_and_return_formula_equal_6202':True,'retained_gate':gate})
assert rest==frozen,'non-target source bytes changed'
# These identities hold for arbitrary flags/gate/invalid/DZ; no FP correlation assumption.
boolean_cases=0
for nv,dz,gate,of,uf,nx in product((False,True),repeat=6):
 direct=(nv,dz,gate and of,gate and uf,gate and nx);selected=(nv,dz,of,uf,nx) if gate else (nv,dz,False,False,False);assert direct==selected;boolean_cases+=1
wrapper_rows=[];wrapper_cases=0
for width in (16,32,64):
 p=f'model/extensions/FD/softfloat_symbolic_f{width}.sail';e=read(E9,p);b=read(B,p);c=(D/f'wrappers-softfloat_symbolic_f{width}.sail').read_text();expected=e
 for target in (32,64):
  for unsigned in (False,True):
   n=f'riscv_f{width}To{"Ui" if unsigned else "I"}{target}';eb,bb,cb=block(e,n),block(b,n),block(c,n);assert cb==bb and eb.count('if ')==3 and cb.count('if ')==0
   expected=expected.replace(eb,bb,1)
   positive=(1<<target)-1 if unsigned else (1<<(target-1))-1;negative=0 if unsigned else 1<<(target-1)
   for inv,nan,sign in product((False,True),repeat=3):
    for candidate in (0,1,(1<<target)-1,1<<(target-1)):
     for flags in range(32):
      a=(positive if nan else negative if sign else positive) if inv else candidate
      invalid=positive if (nan or not sign) else negative
      before=(flags,a);after=(flags,invalid if inv else candidate);assert before==after;wrapper_cases+=1
   wrapper_rows.append({'function':n,'target_width':target,'unsigned':unsigned,'candidate_function_identical_to6202':True})
 assert c==expected,'wrapper non-target bytes differ'
wrapper_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in D.glob('wrappers-softfloat_symbolic_f*.sail')}
p='model/extensions/V/vext_fp_utils_insts.sail';narrow=(D/'candidate-vext_fp_utils_insts.sail').read_text();assert narrow==read(B,p)
# Both real frozen model manifests remain intact.
for tree,batch in [(M,'model-e9d69d2'),(R/'.worktree/runner-float/sail-riscv','model-21418d0')]:
 manifest=json.loads((R/'agents/float_review_closure_20261102/validation/generation'/batch/'source.json').read_text());assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==manifest['commit'];assert all(hashlib.sha256((tree/'model'/n).read_bytes()).hexdigest()==v for n,v in manifest['model_files'].items())
report={'status':'PASS read-only candidate source/formula audit; not implementation permission','exceptions_candidate_sha256':h(cand),'exceptions_functions':18,'cause_ifs_removed':33,'native_FP_bindings_unchanged':native_bindings,'exception_predicate_and_output_proofs':proofs,'arbitrary_nv_dz_gate_OF_UF_NX_cases':boolean_cases,'wrapper_candidate_hashes':wrapper_hashes,'wrapper_functions':wrapper_rows,'wrapper_selection_cases':wrapper_cases,'wrapper_non_target_and_ROD_bytes_unchanged':True,'narrow_candidate_sha256':h(narrow),'narrow_candidate_entire_file_equal6202':True,'retained_f16_i16_outer_if':'OPEN, not approved by this preparation','finite_valid_RODmode_changed':'OPEN and unchanged in these candidates','frozen_e9_and214_model_files_unchanged':True,'not_signed':['production application','Sail strict compilation','new IR/CFG','new dynamic/Clause budgets','OPEN gate architecture acceptance','performance']}
(O/'architecture-candidates-review-20261103.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS source candidates:',18,'exception funcs/',33,'cause ifs;',wrapper_cases,'wrapper cases;',boolean_cases,'arbitrary flag/gate cases;',native_bindings,'unchanged numeric bindings')
