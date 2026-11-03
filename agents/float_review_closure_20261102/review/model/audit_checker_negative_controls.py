#!/usr/bin/env python3
"""对永久候选检查器施加定向语义错误，记录其是否错误放过。"""
from pathlib import Path
import hashlib,json,re,types
ROOT=Path.cwd();checker=ROOT/'isla/test/float_ir/check_float_closure_branches.py'
checker_bytes=checker.read_bytes();checker_sha=hashlib.sha256(checker_bytes).hexdigest()
snapshots=ROOT/'agents/float_review_closure_20261102/review/model/checker-candidates';snapshots.mkdir(exist_ok=True)
(snapshots/(checker_sha+'.py')).write_bytes(checker_bytes)
m=types.ModuleType('closure_checker_candidate');m.__file__=str(checker);exec(compile(checker_bytes,str(checker),'exec'),m.__dict__)
ir=ROOT/'agents/float_review_closure_20261102/validation/generation/model-8ad5e8e/rv64d_v128_e64/rv64d_v128_e64.ir';text=ir.read_text()
f=m.functions(text);rows=[]
def tryit(label,name,mutate):
 original=f[name];modified=mutate(original[:]);assert modified!=original
 old='\n'.join('  '+x for x in original) # Use direct function checker to avoid indentation dependence.
 try:
  if name=='zaccrue_fflags':m.check_flags(modified)
  elif name.startswith('zieee_div'):m.check_exception(name,modified,2,4)
  elif name.startswith('zieee_mul'):m.check_exception(name,modified,2,3)
  elif name.startswith('zieee_add'):m.check_exception(name,modified,2,2)
  elif name.startswith('zieee_fma'):m.check_exception(name,modified,3,4)
  elif name.startswith('zieee_sqrt'):m.check_exception(name,modified,1,2)
  elif 'rounded' in name:m.check_rounded(name,modified)
  elif name.startswith('zieee_rod'):m.check_rod_helper(name,modified,32,16)
  else:m.check_narrow(name,modified,8,True)
 except (AssertionError,StopIteration,KeyError,AttributeError) as e:
  rows.append({'mutation':label,'result':'rejected','detail':str(e)})
 else:rows.append({'mutation':label,'result':'ACCEPTED_INVALID'})
def replace_first_reason(ls):
 js=[i for i,s in enumerate(ls) if s.startswith('jump ')];cond=re.match(r'jump (\w+)',ls[js[1]])[1]
 ls[js[0]]=re.sub(r'jump \w+','jump '+cond,ls[js[0]],count=1);return ls
def replace_finite_gate(ls):
 js=[i for i,s in enumerate(ls) if s.startswith('jump ')];cond=re.match(r'jump (\w+)',ls[js[0]])[1]
 ls[js[-1]]=re.sub(r'jump \w+','jump '+cond,ls[js[-1]],count=1);return ls
def destroy_overflow(ls):
 d=m.defs(ls);ov=next(v for v,r in d.items() if r.startswith('znot_bool('));eq=re.fullmatch(r'znot_bool\((\w+)\)',d[ov])[1]
 rhs=d[eq];first=re.fullmatch(r'(zeq_anything\w*)\((\w+), (\w+)\)',rhs)
 assert first
 for i,s in enumerate(ls):
  if s.startswith(eq+' = '):ls[i]=s.replace(rhs,f'{first[1]}({first[2]}, {first[2]})');break
 return ls
def destroy_changed(ls):
 d=m.defs(ls);eq=next(v for v,q in d.items() if q.startswith('zeq_anythingzIB5zK('));rhs=d[eq];c=re.fullmatch(r'(zeq_anything\w*)\((\w+), (\w+)\)',rhs)
 for i,q in enumerate(ls):
  if q.startswith(eq+' = '):ls[i]=q.replace(rhs,f'{c[1]}({c[2]}, {c[2]})');break
 return ls
def destroy_changed_joined(ls):
 d=m.defs(ls);eq=next(v for v,q in d.items() if q.startswith('zeq_anythingzIB5zK('));rhs=d[eq];c=re.fullmatch(r'(zeq_anything\w*)\((\w+), (\w+)\)',rhs)
 for i,q in enumerate(ls):
  if q.startswith(eq+' = '):ls[i]=q.replace(rhs,f'{c[1]}({c[3]}, {c[3]})');break
 return ls
def clear_sd(ls):
 for i,q in enumerate(ls):
  if '= z_update_Mstatus_SD(' in q:ls[i]=q.replace(', 0b1)',', 0b0)')
 return ls
def widen_mul_reason(ls):
 pc=next(i for i,q in enumerate(ls) if q.startswith('jump '));cond=re.match(r'jump (\w+)',ls[pc])[1]
 for i,q in enumerate(ls):
  if q.startswith(cond+' = '):ls[i]=q.replace('zstrict_and_bool','zstrict_or_bool');break
 return ls
def flip_inf_sign(ls):
 for i,q in enumerate(ls):
  z=re.fullmatch(r'(\w+) = znot_bool\((\w+)\)(.*)',q)
  if z:ls[i]=z[1]+' = '+z[2]+z[3];break
 return ls
def swap_of_nx(ls):
 js=[i for i,q in enumerate(ls) if q.startswith('jump ')];a=re.match(r'jump (\w+)',ls[js[0]])[1];b=re.match(r'jump (\w+)',ls[js[2]])[1]
 ls[js[0]]=ls[js[0]].replace('jump '+a,'jump '+b,1);ls[js[2]]=ls[js[2]].replace('jump '+b,'jump '+a,1);return ls
def destroy_jam_base(ls):
 for i,q in enumerate(ls):
  z=re.search(r'zor_vec\((\w+), (\w+)\)',q)
  if z:ls[i]=q.replace(z[0],f'zor_vec({z[2]}, {z[2]})');break
 return ls
def flip_fma_product_sign(ls):
 d=m.defs(ls)
 for i,q in enumerate(ls):
  z=re.fullmatch(r'(\w+) = znot_bool\((\w+)\)(.*)',q)
  if z and d.get(z[2],'').startswith('zeq_anythingzIB1zK('):
   ls[i]=z[1]+' = '+z[2]+z[3];return ls
 raise AssertionError('未找到FMA积符号')
def sqrt_zero_is_invalid(ls):
 d=m.defs(ls)
 for i,q in enumerate(ls):
  z=re.fullmatch(r'(\w+) = znot_bool\((\w+)\)(.*)',q)
  if z and d.get(z[2],'').startswith('zieee_is_zzero('):
   ls[i]=z[1]+' = '+z[2]+z[3];return ls
 raise AssertionError('未找到sqrt非零')
def clear_reason_nv(ls):
 return [line.replace('return = zieee_empty_exceptions(true)', 'return = zieee_empty_exceptions(false)') for line in ls]
for name in ('zieee_add16_exceptions', 'zieee_mul16_exceptions', 'zieee_sqrt16_exceptions', 'zieee_fma16_exceptions'):
 tryit(name+': 特殊原因出口清除NV',name,clear_reason_nv)
tryit('FMA积符号反转，Inf抵消方向错误','zieee_fma16_exceptions',flip_fma_product_sign)
tryit('sqrt把负非零改负零，-0错误NV','zieee_sqrt16_exceptions',sqrt_zero_is_invalid)
tryit('mul零×Inf原因AND改OR，合法Inf乘法错误置NV','zieee_mul16_exceptions',widen_mul_reason)
tryit('add Inf抵消符号反转，同号Inf错误NV','zieee_add16_exceptions',flip_inf_sign)
tryit('rounded OF/NX条件互换，错误异常类别','zieee_f16_rounded_exceptions',swap_of_nx)
tryit('ROD jam丢原base，恒取1','zieee_rod32_to_16',destroy_jam_base)
tryit('changed比较改成old==old，状态更新臂不可达','zaccrue_fflags',destroy_changed)
tryit('changed比较改成joined==joined，状态更新臂不可达','zaccrue_fflags',destroy_changed_joined)
tryit('Dirty更新链把SD写0','zaccrue_fflags',clear_sd)
tryit('div16: 0/0原因改成Inf/Inf条件，0/0见证丢失','zieee_div16_exceptions',replace_first_reason)
tryit('div16: finite gate改成0/0条件，普通有限异常路径丢失','zieee_div16_exceptions',replace_finite_gate)
tryit('f16→i8: overflow比较改成sig32==sig32，饱和真臂不可达','zriscv_f16ToI8_pure',destroy_overflow)
report={'checker_sha256':checker_sha,'ir_sha256':hashlib.sha256(ir.read_bytes()).hexdigest(),'rows':rows,'status':'BLOCKED' if any(x['result']=='ACCEPTED_INVALID' for x in rows) else 'PASS tested negatives'}
(ROOT/'agents/float_review_closure_20261102/review/model/checker-negative-controls.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
