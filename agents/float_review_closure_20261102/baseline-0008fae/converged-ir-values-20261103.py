#!/usr/bin/env python3
"""不导入生产checker，逐指令执行旧/新IR，核实际facts与整数结果选择。"""
from pathlib import Path
import hashlib,itertools,json,re
R=Path.cwd();G=R/'agents/float_review_closure_20261102/validation/generation';O=R/'agents/float_review_closure_20261102/baseline-0008fae'
def functions(s):return {n:[l.strip() for l in b.splitlines() if l.strip()] for n,b in re.findall(r'(?ms)^fn ([^(\n]+)\([^\n]*\) \{\n(.*?)^\}',s)}
def args(s):
 out=[];start=0;depth=0
 for i,c in enumerate(s):
  depth+=(c=='(')-(c==')')
  if c==',' and depth==0:out.append(s[start:i].strip());start=i+1
 assert depth==0;return out+[s[start:].strip()]
def cls(v,w):
 eb={16:5,32:8,64:11}[w];fb=w-eb-1;e=(v>>fb)&((1<<eb)-1);f=v&((1<<fb)-1);nan=e==((1<<eb)-1) and f!=0
 return dict(nan=nan,snan=nan and not(f&(1<<(fb-1))),inf=e==((1<<eb)-1) and f==0,zzero=e==0 and f==0,finite=e!=((1<<eb)-1))
def reps(w):
 eb={16:5,32:8,64:11}[w];fb=w-eb-1;inf=((1<<eb)-1)<<fb;normal=((1<<(eb-1))-1)<<fb
 return [v|(sign<<(w-1)) for v in (normal,1,0,inf,inf|1,inf|(1<<(fb-1))) for sign in (0,1)]
def run(lines,initial,w,context):
 env=initial.copy();pc=0;seen=0
 def ev(x):
  x=x.strip()
  if x in env:return env[x]
  if x in ('true','false'):return x=='true'
  if x=='()':return ()
  if re.fullmatch(r'0[xb][0-9A-Fa-f]+',x):return int(x,0)
  if x.startswith('struct '):return tuple(ev(v) for v in re.findall(r'\w+ = ([^,}]+)',x.split('{',1)[1]))
  field=re.fullmatch(r'(\w+)\.ztuple\w+([01])',x)
  if field:return env[field[1]][int(field[2])]
  call=re.fullmatch(r'(\w+)\((.*)\)',x);assert call,(pc,x)
  op=call[1]
  if op=='zz5i64zDzKz5i':return int(call[2])
  aa=[ev(y) for y in args(call[2])]
  if op.startswith('zeq_'):return aa[0]==aa[1]
  if op=='znot_bool':return not aa[0]
  if op=='zstrict_and_bool':return bool(aa[0]) and bool(aa[1])
  if op=='zstrict_or_bool':return bool(aa[0]) or bool(aa[1])
  if op=='zbitvector_access':return (aa[0]>>aa[1])&1
  if op=='zsubrange_bits':return (aa[0]>>aa[2])&((1<<(aa[1]-aa[2]+1))-1)
  if op=='zsign_extend':
   # Only narrow low8/16 extended back to32 occur in this review.
   low=context['narrow'];v=aa[1];return (v|(((1<<aa[0])-1)^((1<<low)-1))) if v&(1<<(low-1)) else v
  if op=='zzzeros':return 0
  if op=='zones':return (1<<aa[0])-1
  if op.startswith('zitez'):return aa[1] if aa[0] else aa[2]
  if op=='zieee_operand_invalid':return bool(cls(aa[1],w)['snan'] or aa[0] and cls(aa[1],w)['nan'])
  if op.startswith('zieee_is_'):return bool(cls(aa[0],w)[op[len('zieee_is_'):]])
  if op=='zieee_empty_exceptions':return (aa[0],False,False,False,False)
  if op=='zieee_exception_facts':return tuple(aa)
  if op.startswith('zieee_has_'):return aa[0][('invalid','divbyzero','overflow','underflow','inexact').index(op[len('zieee_has_'):])]
  if op=='zriscv_pack_ieee_flags':return sum(int(v)<<i for i,v in enumerate(reversed(aa[0])))
  if op=='znvFlag':return 16
  if op.endswith('_rounded_exceptions'):return context['rounded']
  if re.fullmatch(r'zieee_fp\d+_to_int_exceptions',op):return context['exc']
  if re.fullmatch(r'zriscv_f\d+To(?:Ui|I)32',op):return context['upstream']
  if re.fullmatch(r'zfp\d+_to_(?:un)?signed\d+',op):return context['candidate']
  if op.startswith(('zfp','zround_')) or op=='zriscv_valid_rm_to_ieee':return ('opaque',op,tuple(aa))
  raise AssertionError((pc,op))
 while pc<len(lines):
  seen+=1;assert seen<1000
  l=lines[pc].split('`',1)[0].strip().rstrip(';')
  j=re.fullmatch(r'jump (\w+) goto (\d+)',l)
  if j:pc=int(j[2]) if ev(j[1]) else pc+1;continue
  j=re.fullmatch(r'goto (\d+)',l)
  if j:pc=int(j[1]);continue
  a=re.fullmatch(r'(\w+) = (.*)',l)
  if a:
   v=ev(a[2]);env[a[1]]=v
   if a[1]=='return':return v
  pc+=1
 raise AssertionError('no return')
rows=[]
for config in ('rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64'):
 old=G/'model-e9d69d2'/config/(config+'.ir');new=G/'model-converged-0f7b8fb'/config/(config+'.ir');a,b=functions(old.read_text()),functions(new.read_text());checks=[]
 for w in (16,32,64):
  for op in ('add','sub','mul','div','sqrt','fma'):
   n=f'zieee_{op}{w}_exceptions';count=0
   for vals in itertools.product(reps(w),repeat=3 if op=='fma' else 1 if op=='sqrt' else 2):
    initial=dict(zip(('za','zb','zc'),vals),zrm='RM',zresult='RESULT')
    for flags in itertools.product((False,True),repeat=3):
     c=dict(rounded=(False,False,*flags));x,y=run(a[n],initial,w,c),run(b[n],initial,w,c);assert x==y,(config,n,vals,flags,x,y);count+=1
   checks.append(dict(function=n,cases=count))
 for n,(w,signed,sw) in {'zriscv_f16ToI16_pure':(16,True,16),'zriscv_f16ToI8_pure':(8,True,16),'zriscv_f16ToUi8_pure':(8,False,16),'zriscv_f16ToUi16_pure':(16,False,16),'zriscv_f32ToI16_pure':(16,True,32),'zriscv_f32ToUi16_pure':(16,False,32)}.items():
  points={0,1,0xffffffff,0x80000000,0x7fffffff,*[(v+d)&0xffffffff for v in (1<<(w-1),1<<w,0-(1<<(w-1))) for d in (-1,0,1)]};count=0
  for sig,flags in itertools.product(sorted(points),(0,1,16,31)):
   c=dict(upstream=(flags,sig),narrow=w);initial=dict(zrm='RM',zv='SRC');x,y=run(a[n],initial,sw,c),run(b[n],initial,sw,c);assert x==y,(config,n,sig,flags,x,y);count+=1
  checks.append(dict(function=n,cases=count))
 for sw,tw,u in itertools.product((16,32,64),(32,64),(False,True)):
  n=f'zriscv_f{sw}To{"Ui" if u else "I"}{tw}'
  if n not in b:continue
  count=0
  for raw,exc,candidate in itertools.product(reps(sw),itertools.product((False,True),repeat=5),(0,0x12345678,(1<<tw)-1)):
   c=dict(exc=exc,candidate=candidate);initial=dict(za=raw,zrm_bits='RM',zrm='RM');x,y=run(a[n],initial,sw,c),run(b[n],initial,sw,c);assert x==y,(config,n,raw,exc,candidate,x,y);count+=1
  checks.append(dict(function=n,cases=count))
 rows.append(dict(config=config,old_ir_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),new_ir_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),checks=checks))
report=dict(status='PASS independent old/new IR selected value-flow execution',model='0f7b8fbc6724103f91f929ef6918f123df75d6c9',rows=rows,total_cases=sum(x['cases'] for row in rows for x in row['checks']),scope='不导入永久checker；异常穷举每源12分类及任意OF/UF/NX八组合；窄化边界及0/1/16/31四种上游flags；包装穷举源12分类/全部五flags/三candidate。原生FP作为相同不透明值，数值表达式另有DAG签名证明；有限采样不等于全数值证明。')
(O/'converged-ir-values-20261103.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['status'],report['total_cases'])
