#!/usr/bin/env python3
"""新版值合同的独立定向负控，保留特殊控制旧负控。"""
from pathlib import Path
import ast,hashlib,json,re,types
R=Path.cwd();O=R/'agents/float_review_closure_20261102/baseline-0008fae';C=R/'isla/test/float_ir/check_float_closure_branches.py';raw=C.read_bytes();sha=hashlib.sha256(raw).hexdigest();(O/('model-review.checker-'+sha+'.py')).write_bytes(raw)
m=types.ModuleType('candidate');m.__file__=str(C);exec(compile(raw,str(C),'exec'),m.__dict__)
ir=R/'agents/float_review_closure_20261102/validation/generation/model-e9d69d2/rv64d_v128_e64/rv64d_v128_e64.ir';f=m.functions(ir.read_text());rows=[]
# Reuse only the reviewer's historical mutation functions, never its run/report code.
old=R/'agents/float_review_closure_20261102/review/model/audit_checker_negative_controls.py';tree=ast.parse(old.read_text());helpers=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name!='tryit'];env={'m':m,'re':re};exec(compile(ast.Module(body=helpers,type_ignores=[]),str(old),'exec'),env)
def check(name,ls):
 if name=='zaccrue_fflags':return m.check_flags(ls)
 match=re.fullmatch(r'zieee_(add|mul|div|sqrt|fma)16_exceptions',name)
 if match:
  op=match[1];return m.check_exception(name,ls,3 if op=='fma' else 1 if op=='sqrt' else 2,{'add':2,'mul':3,'div':4,'sqrt':2,'fma':4}[op])
 if 'rounded_exceptions' in name:return m.check_rounded(name,ls)
 if name=='zieee_exact_threshold_exceptions':return m.check_exact_threshold(ls)
 if name=='zieee_fp_to_int_core':return m.check_fp_to_int_core(ls)
 if name=='zieee_round16_exceptions':return m.check_round(name,ls,16)
 if name=='zieee_convert32_to_16_exceptions':return m.check_conversion_gate(name,ls,32,'zieee_exact16_exceptions')
 if name.startswith('zieee_rod'):return m.check_rod_helper(name,ls,32,16)
 return m.check_narrow(name,ls,8,True)
def run(label,name,mutator):
 ls=mutator(f[name][:]);assert ls!=f[name],label
 try:check(name,ls)
 except (AssertionError,KeyError,StopIteration,AttributeError) as ex:rows.append({'mutation':label,'function':name,'result':'rejected','detail':str(ex)})
 else:rows.append({'mutation':label,'function':name,'result':'ACCEPTED_INVALID'})
def replace_first(ls,pattern,replacement):
 for i,l in enumerate(ls):
  x,n=re.subn(pattern,replacement,l,count=1)
  if n:ls[i]=x;return ls
 raise AssertionError('negative template missing: '+pattern)
def swap_fact_fields(ls):
 for i,l in enumerate(ls):
  z=re.search(r'return = zieee_exception_facts\(([^)]+)\)',l)
  if z:
   a=z[1].split(', ');assert len(a)==5;a[2],a[4]=a[4],a[2];ls[i]=l.replace(z[0],'return = zieee_exception_facts('+', '.join(a)+')');return ls
 raise AssertionError('facts missing')
def self_eq(ls):return replace_first(ls,r'(zfp(?:16|32|64|128)_eq\()(\w+), (\w+)\)',r'\1\2, \2)')
def duplicate_underflow_nx(ls):
 # Locate returned UF variable rather than a random AND.
 factsline=next(l for l in ls if l.startswith('return = zieee_exception_facts('));a=re.search(r'facts\(([^)]+)\)',factsline)[1].split(', ');uf=a[3]
 return replace_first(ls,r'('+re.escape(uf)+r' = zstrict_and_bool\()(\w+), (\w+)\)',r'\1\2, \2)')
def wrong_rod_selector(ls):return replace_first(ls,r'zieee_has_inexact\(',r'zieee_has_invalid(')
def wrong_rod_false_base(ls):
 for i,l in enumerate(ls):
  z=re.search(r'zitezIB16zK\((\w+), (\w+), (\w+)\)',l)
  if z:ls[i]=l.replace(z[0],f'zitezIB16zK({z[1]}, {z[2]}, {z[2]})');return ls
 raise AssertionError('ITE missing')
def clear_nonfinite_nv(ls):return replace_first(ls,r'zieee_empty_exceptions\(zz\d+\)',r'zieee_empty_exceptions(false)')
def replace_finite_flags_empty(ls):
 ret=next(l for l in ls if l.startswith('return = struct '));flags=re.findall(r'\w+ = ([^,}]+)',ret.split('{',1)[1])[0].strip()
 return replace_first(ls,r'('+re.escape(flags)+r' = )zz\d+( `)',r'\1zieee_empty_exceptions(false)\2')
legacy=[('FMA积符号反转','zieee_fma16_exceptions','flip_fma_product_sign'),('sqrt误判负零','zieee_sqrt16_exceptions','sqrt_zero_is_invalid'),('mul原因AND改OR','zieee_mul16_exceptions','widen_mul_reason'),('add Inf抵消符号反转','zieee_add16_exceptions','flip_inf_sign'),('ROD jam丢base','zieee_rod32_to_16','destroy_jam_base'),('changed比较old==old','zaccrue_fflags','destroy_changed'),('changed比较joined==joined','zaccrue_fflags','destroy_changed_joined'),('SD写0','zaccrue_fflags','clear_sd'),('div 0/0换Inf/Inf','zieee_div16_exceptions','replace_first_reason'),('div finite gate换0/0','zieee_div16_exceptions','replace_finite_gate'),('窄化overflow自比较','zriscv_f16ToI8_pure','destroy_overflow')]
for label,name,helper in legacy:run(label,name,env[helper])
for name in ('zieee_add16_exceptions','zieee_mul16_exceptions','zieee_sqrt16_exceptions','zieee_fma16_exceptions'):run('原因出口清NV',name,env['clear_reason_nv'])
run('rounded返回OF/NX字段互换','zieee_f16_rounded_exceptions',swap_fact_fields)
run('threshold返回OF/NX字段互换','zieee_exact_threshold_exceptions',swap_fact_fields)
run('rounded NX比较lo==lo','zieee_f16_rounded_exceptions',self_eq)
run('threshold NX比较x==x','zieee_exact_threshold_exceptions',self_eq)
run('rounded UF由NX&&NX替代tiny','zieee_f16_rounded_exceptions',duplicate_underflow_nx)
run('round NX比较x==x','zieee_round16_exceptions',self_eq)
run('fpint NX比较x==x','zieee_fp_to_int_core',self_eq)
run('round raise_inexact合取改析取','zieee_round16_exceptions',lambda ls:replace_first(ls,r'zstrict_and_bool\(zraise_inexact, ',r'zstrict_or_bool(zraise_inexact, '))
run('ROD ITE改由NV选择','zieee_rod32_to_16',wrong_rod_selector)
run('ROD精确臂也jam','zieee_rod32_to_16',wrong_rod_false_base)
run('ROD非finite丢sNaN NV','zieee_rod32_to_16',clear_nonfinite_nv)
run('ROD finite丢exact flags','zieee_rod32_to_16',replace_finite_flags_empty)
run('convert非finite丢sNaN NV','zieee_convert32_to_16_exceptions',clear_nonfinite_nv)
for name in ('zieee_round16_exceptions','zieee_convert32_to_16_exceptions','zieee_rod32_to_16'):
 run('quiet源分类改成signaling，qNaN错误NV',name,lambda ls:replace_first(ls,r'zieee_operand_invalid\(false, ',r'zieee_operand_invalid(true, '))
report={'checker_sha256':sha,'ir_sha256':hashlib.sha256(ir.read_bytes()).hexdigest(),'count':len(rows),'status':'BLOCKED false green' if any(r['result']=='ACCEPTED_INVALID' for r in rows) else 'PASS targeted negatives','rows':rows}
(O/'model-review.checker-negative-e9d69d2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
