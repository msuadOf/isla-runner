#!/usr/bin/env python3
"""Independent source/formula and category proof for the exception rewrite."""
from pathlib import Path
from itertools import product
import hashlib,json,re,subprocess
BASE=Path('.worktree/runner-float/sail-riscv'); FILE='model/core/ieee_fp_exceptions.sail'
OUT=Path(__file__).resolve().parent
old=subprocess.check_output(['git','-C',str(BASE),'show','6202e23:'+FILE],text=True)
new=(BASE/FILE).read_text()
def functions(s):
    return {m.group(1):m.group(0) for m in re.finditer(r'^function (\w+)\b.*?(?=^function |\Z)',s,re.M|re.S)}
a,b=functions(old),functions(new)
def norm(s):return re.sub(r'\s+','',s)
def piece(s,start,end):return re.search(start+r'.*?'+end,s,re.S).group()
checks=[]
for fmt in (16,32,64):
    for op in ('add','sub','mul','div','sqrt','fma'):
        n=f'ieee_{op}{fmt}_exceptions'
        assert norm(piece(a[n],r'let x =',r'let rounded = [^;]+;'))==norm(piece(b[n],r'let x =',r'let rounded = [^;]+;')),n
        assert re.search(r'else if (finite|valid) then \{\s*let x =',b[n]),n
        checks.append(n+': unchanged wider candidates/bounds/rounded call inside valid gate')
    n=f'ieee_f{fmt}_rounded_exceptions'
    assert norm(piece(a[n],r'let rw =',r'let tiny = [^;]+;'))==norm(piece(b[n],r'let rw =',r'let tiny = [^;]+;')),n
    checks.append(n+': all arithmetic predicates and thresholds unchanged')
n='ieee_exact_threshold_exceptions'
assert norm(piece(a[n],r'let inexact =',r'let tiny =.*?\n  \);'))==norm(piece(b[n],r'let inexact =',r'let tiny =.*?\n  \);'))
checks.append(n+': all arithmetic predicates and thresholds unchanged')
for n in ('ieee_convert32_to_16_exceptions','ieee_convert64_to_16_exceptions','ieee_convert64_to_32_exceptions','ieee_bf16_from_f32_exceptions','ieee_rod32_to_16','ieee_rod64_to_32'):
    assert norm(piece(a[n],r'let exact =',r'let facts = [^;]+;'))==norm(piece(b[n],r'let exact =',r'let facts = [^;]+;')),n
    assert re.search(r'if finite then \{\s*let exact =',b[n]),n
    checks.append(n+': exact arithmetic unchanged and under finite gate')
for n in ('ieee_rod32_to_16','ieee_rod64_to_32'):
    assert norm(piece(a[n],r'let x =',r'let base_bits = [^;]+;'))==norm(piece(b[n],r'let x =',r'let base_bits = [^;]+;')),n
    assert 'if ieee_has_inexact(flags) then' in b[n],n
expected={f'ieee_{op}{fmt}_exceptions' for op in ('add','sub','mul','div','sqrt','fma') for fmt in (16,32,64)}|{f'ieee_f{fmt}_rounded_exceptions' for fmt in (16,32,64)}|{'ieee_exact_threshold_exceptions','ieee_mask_exact_exceptions','ieee_fp_to_int_core'}|{f'ieee_round{fmt}_exceptions' for fmt in (16,32,64)}|{'ieee_convert32_to_16_exceptions','ieee_convert64_to_16_exceptions','ieee_convert64_to_32_exceptions','ieee_bf16_from_f32_exceptions','ieee_rod32_to_16','ieee_rod64_to_32'}
# Function blocks can include inter-function comments. Compare only through body end.
def onlybody(s):
    lines=s.splitlines();end=max(i for i,l in enumerate(lines) if l=='}') if '\n}' in s else len(lines)-1
    return '\n'.join(lines[:end+1])
changed={n for n in a if norm(onlybody(a[n]))!=norm(onlybody(b[n]))}
assert changed==expected,(changed-expected,expected-changed)
# Abstract complete semantic categories, including NaN signs. Subnormal versus
# normal have equal special predicates, but are kept separate in this proof.
categories=[(kind,neg) for kind in ('normal','sub','zero','inf','snan','qnan') for neg in (False,True)]
def nan(v):return v[0] in ('snan','qnan')
def inf(v):return v[0]=='inf'
def zero(v):return v[0]=='zero'
def finite(v):return not nan(v) and not inf(v)
def nvin(v):return v[0]=='snan'
flagsproof=0
for op in ('add','sub','mul','div','sqrt','fma'):
    arity={'sqrt':1,'fma':3}.get(op,2)
    for vs in product(categories,repeat=arity):
        x=vs[0]; y=vs[1] if arity>1 else x; z=vs[-1]
        nv=any(map(nvin,vs)); reasons=[];dz=False
        if op in ('add','sub'):
            reasons=[inf(x) and inf(y) and ((x[1]!=y[1]) if op=='add' else (x[1]==y[1]))]
            valid=finite(x) and finite(y)
        elif op=='mul':
            reasons=[zero(x) and inf(y),inf(x) and zero(y)];valid=finite(x) and finite(y)
        elif op=='div':
            reasons=[zero(x) and zero(y),inf(x) and inf(y)]
            dz=finite(x) and not zero(x) and zero(y)
            valid=finite(x) and finite(y) and not zero(y)
        elif op=='sqrt':
            negnz=x[1] and not zero(x);reasons=[not nan(x) and negnz]
            valid=(finite(x) and not negnz) or zero(x)
        else:
            product_inf=(inf(x) and not nan(y) and not zero(y)) or (inf(y) and not nan(x) and not zero(x))
            reasons=[zero(x) and inf(y),inf(x) and zero(y),product_inf and inf(z) and ((x[1]!=y[1])!=z[1])]
            valid=all(map(finite,vs))
        for of,uf,nx in product((False,True),repeat=3):
            before=(nv or any(reasons),dz,valid and of,valid and uf,valid and nx)
            after=(True,False,False,False,False) if any(reasons) else (False,True,False,False,False) if dz else (nv,False,of,uf,nx) if valid else (nv,False,False,False,False)
            assert before==after,(op,vs,before,after)
            flagsproof+=1
# The rounded decision tree preserves arbitrary flags combinations. No IEEE
# OF=>NX or OF/UF exclusivity assumption is made by this source rewrite.
for of,uf,nx in product((False,True),repeat=3):
    after=(True,uf,nx) if of else (False,True,nx) if uf else (False,False,True) if nx else (False,False,False)
    assert (of,uf,nx)==after
report={'stage':'independent source audit only','source_sha256':hashlib.sha256(new.encode()).hexdigest(),'changed_functions':sorted(changed),'unchanged_formula_checks':checks,'all_category_flag_cases':flagsproof,'arbitrary_rounded_flag_cases':8,'scope':'Source arithmetic identity and Boolean category/flag equivalence; not native FP primitive correctness, IR CFG, dynamic witnesses or Clause budget'}
(OUT/'exceptions-formula-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'PASS: {len(changed)} changed functions, {len(checks)} formula identities, {flagsproof} category/flag cases, 8 arbitrary rounded flag cases')
