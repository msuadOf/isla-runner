#!/usr/bin/env python3
"""独立核窄化、整数包装、ROD和转换/round门控的实际CFG。"""
import argparse,re,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ir',type=Path,required=True);p.add_argument('--inspection',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
t=args.ir.read_text();fs=dict(re.findall(r'(?ms)^fn ([^\n(]+)\([^\n]*\) \{\n(.*?)^\}',t));r=json.loads(args.inspection.read_text());assert hashlib.sha256(args.ir.read_bytes()).hexdigest()==r['ir_sha256']
def ls(n):return [x.strip() for x in fs[n].splitlines() if x.strip()]
def su(a,i):
 q=a[i];m=re.search(r'goto (\d+)',q)
 return [i+1,int(m[1])] if q.startswith('jump ') else [int(m[1])] if q.startswith('goto ') else [] if q=='end;' else [i+1] if i+1<len(a) else []
def reach(a,s,stop=None):
 todo=[s];done=set()
 while todo:
  i=todo.pop()
  if i==stop or i in done:continue
  assert 0<=i<len(a);done.add(i);todo+=su(a,i)
 return done
def arms(a,j):
 f,tr=su(a,j['pc']);f,t=reach(a,f),reach(a,tr);return f-t,t-f

def expand(a,pc,v):
 d={m[1]:m[2] for q in a[:pc] if (m:=re.match(r'(\w+) = (.*?) `',q))}
 def ex(x,seen):
  return re.sub(r'\bzz\d+\b',lambda m: ex(d[m[0]],seen|{m[0]}) if m[0] in d and m[0] not in seen else m[0],x)
 return ex(v,set())
def tuples(a):
 out=[]
 for i,q in enumerate(a):
  if ' = struct ' in q:
   fields=re.findall(r'\w+ = ([^,}]+)',q.split('{',1)[1])
   assert len(fields)==2
   out.append((i,[expand(a,i,x.strip()) for x in fields]))
 return out
def ix(x):return f'zz5i64zDzKz5i({x})'
def sub(x,hi,lo):return f'zsubrange_bits({x}, {ix(hi)}, {ix(lo)})'
checks=[]
for fmt,width,signed in [(16,16,True),(16,8,True),(32,16,True),(16,16,False),(16,8,False),(32,16,False)]:
 n=f'zriscv_f{fmt}To'+('I' if signed else 'Ui')+str(width)+'_pure';a=ls(n);js=r['functions'][n]['jumps'];assert len(js)==(2 if signed else 1)
 candidate=f'zriscv_f{fmt}To'+('I32' if signed else 'Ui32')+'(zrm, zv).ztuplez3z5bv5_z5bv321'
 if signed:
  predicate=f'znot_bool(zeq_anythingzIB32zK({candidate}, zsign_extend({ix(32)}, {sub(candidate,width-1,0)})))'
 else:
  predicate=f'znot_bool(zeq_anythingzIB{32-width}zK({sub(candidate,31,width)}, zzzeros({ix(32-width)})))'
 assert js[0]['condition']==predicate,(n,js[0]['condition'])
 normal,saturated=arms(a,js[0]);ts=tuples(a);normal_t=[(i,v) for i,v in ts if i in normal];sat_t=[(i,v) for i,v in ts if i in saturated]
 assert len(normal_t)==1 and len(sat_t)==(2 if signed else 1)
 flags=candidate[:-1]+'0';assert normal_t[0][1]==[flags,sub(candidate,width-1,0)],(n,normal_t)
 assert all(v[0]=='znvFlag(())' for i,v in sat_t)
 if signed:
  assert js[1]['pc'] in saturated
  assert js[1]['condition']==f'zeq_anythingzIB1zK(zbitvector_access({candidate}, {ix(31)}), 0b1)'
  pos,neg=arms(a,js[1]);maximum=f'0x{(1<<(width-1))-1:0{width//4}X}';minimum=f'0x{1<<(width-1):0{width//4}X}'
  assert any(i in pos and v[1]==maximum for i,v in sat_t)
  assert any(i in neg and v[1]==minimum for i,v in sat_t)
 else:assert sat_t[0][1][1]==f'zones({ix(width)})',(n,sat_t)
 checks.append({'function':n,'exact_predicate_and_width':True,'true_NV_and_limits_false_original_pair':True})
for fmt in (16,32,64):
 for target in ('I32','Ui32','I64','Ui64'):
  n=f'zriscv_f{fmt}To{target}'
  if n not in fs:continue
  a=ls(n);js=r['functions'][n]['jumps'];assert len(js)==3
  assert js[0]['condition'].startswith(f'zieee_has_invalid(zieee_fp{fmt}_to_int_exceptions(')
  assert js[1]['condition']=='zieee_is_nan(za)'
  assert js[2]['condition']==f'zeq_anythingzIB1zK(zbitvector_access(za, {ix(fmt-1)}), 0b1)'
  good,bad=arms(a,js[0]);nonnan,nan=arms(a,js[1]);positive,negative=arms(a,js[2])
  assert js[1]['pc'] in bad and js[2]['pc'] in bad&nonnan
  resultvar=re.search(r'return = struct .*?, \w+ = (\w+)\}', '\n'.join(a))[1]
  assigns=[(i,expand(a,i,re.match(r'\w+ = (.*?) `',q)[1])) for i,q in enumerate(a) if q.startswith(resultvar+' = ')]
  w=int(re.search(r'\d+',target)[0]);unsigned=target.startswith('Ui')
  maximum=(1<<w)-1 if unsigned else (1<<(w-1))-1;minimum=0 if unsigned else 1<<(w-1)
  at=lambda nodes:[v for i,v in assigns if i in nodes]
  assert len(at(good))==1 and f'zfp{fmt}_to_'+('unsigned' if unsigned else 'signed')+str(w)+'(' in at(good)[0]
  assert at(nan)==[f'0x{maximum:0{w//4}X}']
  assert at(positive)==[f'0x{maximum:0{w//4}X}'] and at(negative)==[f'0x{minimum:0{w//4}X}']
  checks.append({'function':n,'invalid_NaN_sign_priority_and_constants':True})
for n in ('zieee_mask_exact_exceptions','zieee_round16_exceptions','zieee_round32_exceptions','zieee_round64_exceptions','zieee_convert32_to_16_exceptions','zieee_convert64_to_16_exceptions','zieee_convert64_to_32_exceptions','zieee_bf16_from_f32_exceptions'):
 a=ls(n);js=r['functions'][n]['jumps'];assert js[0]['condition'] in ('zfinite','zieee_is_finite(za)');skipped,active=arms(a,js[0])
 work=[i for i,q in enumerate(a) if re.search(r'= (?:zfp\d+_|zieee_exact|zieee_has_(?:overflow|underflow|inexact))',q)]
 assert work and set(work)<=active and not set(work)&reach(a,0,js[0]['pc'])
 assert any('zieee_empty_exceptions(' in a[i] for i in skipped)
 checks.append({'function':n,'finite_gate_dominates_exception_work':True})
n='zieee_fp_to_int_core';a=ls(n);js=r['functions'][n]['jumps'];assert len(js)==3 and js[0]['condition']=='zfinite'
assert js[1]['condition'].startswith('zstrict_and_bool(zfp128_gteq(zrounded,') and 'zfp128_lt(zrounded,' in js[1]['condition']
assert js[2]['condition']=='znot_bool(zfp128_eq(zx, zrounded))'
for j in js[:2]:
 invalid,valid=arms(a,j);assert any('zieee_empty_exceptions(true)' in a[i] for i in invalid)
 assert js[2]['pc'] in valid
no_nx,nx=arms(a,js[2]);assert any('zieee_exception_facts(false, false, false, false, true)' in a[i] for i in nx)
assert any('zieee_empty_exceptions(false)' in a[i] for i in no_nx)
checks.append({'function':n,'finite_and_range_NV_or_valid_NX_hierarchy':True})
for fmt,dst in [(32,16),(64,32)]:
 n=f'zriscv_f{fmt}ToF{dst}';a=ls(n);js=r['functions'][n]['jumps'];assert len(js)==3
 assert js[0]['condition']==f'zeq_bits(zrm'+('_bits' if fmt==32 else '')+', 0b110)'
 ordinary,rod=arms(a,js[0]);rod_call=f'= zieee_rod{fmt}_to_{dst}(';native=f'= zfp{fmt}_to_fp{dst}('
 assert sum(rod_call in a[i] for i in rod)==1 and not any(rod_call in a[i] for i in ordinary)
 assert sum('= zriscv_valid_rm_to_ieee(' in a[i] for i in ordinary)==1 and not any('= zriscv_valid_rm_to_ieee(' in a[i] for i in rod)
 assert any(native in a[i] for i in ordinary) and not any(native in a[i] for i in rod)
 ts=tuples(a);assert len([i for i,v in ts if i in ordinary])==1 and len([i for i,v in ts if i in rod])==1
 checks.append({'function':n,'mode_true_ROD_false_native_and_pair_arms':True})
 n=f'zieee_rod{fmt}_to_{dst}';a=ls(n);js=r['functions'][n]['jumps'];assert len(js)==2 and js[0]['condition']=='zieee_is_finite(za)' and js[1]['condition'].startswith('zieee_has_inexact(')
 skipped,finite=arms(a,js[0]);exact=[i for i,q in enumerate(a) if '= zieee_exact' in q];assert len(exact)==1 and exact[0] in finite
 plain,jam=arms(a,js[1]);ts=tuples(a);t0=[v for i,v in ts if i in plain];t1=[v for i,v in ts if i in jam];assert len(t0)==len(t1)==1
 assert t0[0][0]==t1[0][0] and t1[0][1]==f'zor_vec({t0[0][1]}, 0x'+('0001' if dst==16 else '00000001')+')'
 checks.append({'function':n,'finite_exact_work_and_same_flags_plain_or_jam':True})
args.out.write_text(json.dumps({'status':'PASS remaining CFG relationships','ir_sha256':r['ir_sha256'],'checks':checks,'scope':'不证明SMT可达性或动态预算；ROD字段同臂另结合源码与目标IR差异核实'},ensure_ascii=False,indent=2)+'\n')
print('PASS',len(checks),'组剩余实际CFG关系')
