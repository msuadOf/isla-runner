#!/usr/bin/env python3
"""冻结最终checker，用实际新IR施加独立定向语义负控。"""
from pathlib import Path
import ast,hashlib,json,re,types,sys
assert len(sys.argv) == 2, '用法: check_negative_104.py OUTPUT_JSON'
output=Path(sys.argv[1]);assert not output.exists(),output
R=Path.cwd();MAIN=R.parents[1];O=MAIN/'agents/float_review_closure_20261102/baseline-0008fae';C=R/'isla/test/float_ir/check_float_closure_branches.py';raw=C.read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha=='9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf'
m=types.ModuleType('final_checker');m.__file__=str(C);exec(compile(raw,str(C),'exec'),m.__dict__)
ir=R/'isla/ir/rv64d_v128_e64.ir';f=m.functions(ir.read_text());rows=[]
# Only import independent mutation helper definitions; never old report runners.
old=O/'model-review.checker-negative-e9d69d2.py';tree=ast.parse(old.read_text());skip={'check','run'};env=dict(m=m,re=re);helpers=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name not in skip];exec(compile(ast.Module(body=helpers,type_ignores=[]),str(old),'exec'),env)
legacy=MAIN/'agents/float_review_closure_20261102/review/model/audit_checker_negative_controls.py';tree=ast.parse(legacy.read_text());helpers=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name!='tryit'];exec(compile(ast.Module(body=helpers,type_ignores=[]),str(legacy),'exec'),env)
def check(n,ls):
 if n=='zaccrue_fflags':return m.check_flags(ls)
 a=re.fullmatch(r'zieee_(add|sub|mul|div|sqrt|fma)(16|32|64)_exceptions',n)
 if a:return m.check_exception(n,ls,3 if a[1]=='fma' else 1 if a[1]=='sqrt' else 2,dict(add=2,sub=2,mul=3,div=4,sqrt=2,fma=4)[a[1]])
 if n in m.NARROW:return m.check_narrow(n,ls,*m.NARROW[n])
 a=re.fullmatch(r'zriscv_f(16|32|64)To(Ui|I)(32|64)',n)
 if a:return m.check_integer_wrapper(n,ls,int(a[1]),int(a[3]),a[2]=='Ui')
 if 'rounded_exceptions' in n:return m.check_rounded(n,ls)
 if n=='zieee_exact_threshold_exceptions':return m.check_exact_threshold(ls)
 if n=='zieee_fp_to_int_core':return m.check_fp_to_int_core(ls)
 if n=='zieee_round16_exceptions':return m.check_round(n,ls,16)
 if n=='zieee_convert32_to_16_exceptions':return m.check_conversion_gate(n,ls,32,'zieee_exact16_exceptions')
 if n=='zieee_rod32_to_16':return m.check_rod_helper(n,ls,32,16)
 raise AssertionError(n)
def run(label,n,mut):
 ls=mut(f[n][:]);assert ls!=f[n],label
 try:check(n,ls)
 except (AssertionError,KeyError,StopIteration,AttributeError) as ex:rows.append(dict(mutation=label,function=n,result='rejected',detail=str(ex)))
 else:rows.append(dict(mutation=label,function=n,result='ACCEPTED_INVALID'))
def replace(ls,p,r):return env['replace_first'](ls,p,r)
def facts_field(ls,field,v):
 for i,l in enumerate(ls):
  a=re.search(r'zieee_exception_facts\(([^)]+)\)',l)
  if a:
   vals=a[1].split(', ');vals[field]=v;ls[i]=l.replace(a[0],'zieee_exception_facts('+', '.join(vals)+')')
 return ls
def swapite(ls,width,index):
 matches=[(i,re.search(r'zitezIB'+str(width)+r'zK\((\w+), (\w+), (\w+)\)',l)) for i,l in enumerate(ls)];i,a=[(i,a) for i,a in matches if a][index];ls[i]=ls[i].replace(a[0],f'zitezIB{width}zK({a[1]}, {a[3]}, {a[2]})');return ls
for w in (16,32,64):
 for op in ('add','sub','mul','div','sqrt','fma'):
  n=f'zieee_{op}{w}_exceptions';run('清除返回NV',n,lambda ls:facts_field(ls,0,'false'))
 run('清除返回DZ',f'zieee_div{w}_exceptions',lambda ls:facts_field(ls,1,'false'))
 run('quiet源分类错误NV',f'zieee_add{w}_exceptions',lambda ls:replace(ls,r'zieee_operand_invalid\(false, ',r'zieee_operand_invalid(true, '))
for label,n,helper in [('FMA积符号反转','zieee_fma16_exceptions','flip_fma_product_sign'),('sqrt误判负零','zieee_sqrt16_exceptions','sqrt_zero_is_invalid'),('add Inf抵消符号反转','zieee_add16_exceptions','flip_inf_sign'),('ROD jam丢base','zieee_rod32_to_16','destroy_jam_base'),('changed old==old','zaccrue_fflags','destroy_changed'),('changed joined==joined','zaccrue_fflags','destroy_changed_joined'),('SD写0','zaccrue_fflags','clear_sd')]:run(label,n,env[helper])
run('mul零Inf原因AND变OR','zieee_mul16_exceptions',lambda ls:replace(ls,r'zstrict_and_bool\(',r'zstrict_or_bool('))
run('div gate恒真','zieee_div16_exceptions',lambda ls:replace(ls,r'jump \w+ goto',r'jump true goto'))
run('div DZ谓词AND变OR','zieee_div16_exceptions',lambda ls:replace(ls,r'(zz415 = )zstrict_and_bool',r'\1zstrict_or_bool'))
for n,(w,signed) in m.NARROW.items():
 run('overflow自比较',n,env['destroy_overflow'])
 if n!='zriscv_f16ToI16_pure':
  run('flags两臂互换',n,lambda ls:swapite(ls,5,0))
  run('bits两臂互换',n,lambda ls,w=w:swapite(ls,w,-1))
 if signed:run('正负端点互换',n,lambda ls,w=w:swapite(ls,w,0))
for sw in (16,32,64):
 for tw in (32,64):
  for u in (False,True):
   n=f'zriscv_f{sw}To{"Ui" if u else "I"}{tw}'
   run('invalid最终两臂互换',n,lambda ls,tw=tw:swapite(ls,tw,-1))
   run('NaN/正负端点互换',n,lambda ls,tw=tw:swapite(ls,tw,0))
   run('invalid由inexact替代',n,lambda ls:replace(ls,r'zieee_has_invalid\(',r'zieee_has_inexact('))
for label,n,helper in [('rounded OF/NX字段互换','zieee_f16_rounded_exceptions','swap_fact_fields'),('threshold OF/NX互换','zieee_exact_threshold_exceptions','swap_fact_fields'),('rounded比较lo==lo','zieee_f16_rounded_exceptions','self_eq'),('threshold比较x==x','zieee_exact_threshold_exceptions','self_eq'),('rounded UF丢tiny','zieee_f16_rounded_exceptions','duplicate_underflow_nx'),('round比较x==x','zieee_round16_exceptions','self_eq'),('fpint比较x==x','zieee_fp_to_int_core','self_eq'),('ROD由NV选择jam','zieee_rod32_to_16','wrong_rod_selector'),('ROD精确臂也jam','zieee_rod32_to_16','wrong_rod_false_base'),('ROD非finite丢NV','zieee_rod32_to_16','clear_nonfinite_nv'),('ROD finite丢flags','zieee_rod32_to_16','replace_finite_flags_empty'),('convert非finite丢NV','zieee_convert32_to_16_exceptions','clear_nonfinite_nv')]:run(label,n,env[helper])
for n in ('zieee_round16_exceptions','zieee_convert32_to_16_exceptions','zieee_rod32_to_16'):run('quiet分类误置signaling',n,lambda ls:replace(ls,r'zieee_operand_invalid\(false, ',r'zieee_operand_invalid(true, '))
assert C.read_bytes()==raw
report=dict(checker_sha256=sha,ir_sha256=hashlib.sha256(ir.read_bytes()).hexdigest(),count=len(rows),status='PASS targeted negatives' if all(x['result']=='rejected' for x in rows) else 'BLOCKED false green',rows=rows)
output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['status'],len(rows));print([x for x in rows if x['result']!='rejected'])
