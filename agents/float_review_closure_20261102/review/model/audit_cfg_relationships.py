#!/usr/bin/env python3
"""独立核实际 IR：异常原因/finite支配、格式同构、changed 状态写。"""
import argparse,re,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ir',type=Path,required=True);p.add_argument('--inspection',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
t=args.ir.read_text();fs=dict(re.findall(r'(?ms)^fn ([^\n(]+)\([^\n]*\) \{\n(.*?)^\}',t));r=json.loads(args.inspection.read_text());assert hashlib.sha256(args.ir.read_bytes()).hexdigest()==r['ir_sha256']
def lines(n):return [l.strip() for l in fs[n].splitlines() if l.strip()]
def succ(ls,pc):
 q=ls[pc];m=re.search(r'\bgoto (\d+)',q)
 return [pc+1,int(m[1])] if q.startswith('jump ') else [int(m[1])] if q.startswith('goto ') else [] if q=='end;' else [pc+1] if pc+1<len(ls) else []
def reach(ls,start,stop=None):
 out=set();todo=[start]
 while todo:
  i=todo.pop()
  if i in out or i==stop:continue
  assert 0<=i<len(ls);out.add(i);todo+=succ(ls,i)
 return out
def callname(q):
 m=re.search(r'= (z\w+|\$zsail_assert)\(',q);return m[1] if m else None
checks=[]
for fmt,wide,index in [(16,32,15),(32,64,31),(64,128,63)]:
 for op,count in [('add',2),('sub',2),('mul',3),('div',4),('sqrt',2),('fma',4)]:
  n=f'zieee_{op}{fmt}_exceptions';ls=lines(n);js=r['functions'][n]['jumps'];assert len(js)==count,n
  # 每源分类调用保持在首个原因分支之前，且不能由旁路绕过。
  sources=[i for i,q in enumerate(ls) if '= zieee_operand_invalid(' in q]
  arity=3 if op=='fma' else 1 if op=='sqrt' else 2
  assert len(sources)==arity and max(sources)<js[0]['pc'],n
  for j in js:assert j['dominates_true_only'] and j['dominates_false_only'],(n,j['pc'])
  # 各格式原因/valid谓词逐字同构，仅符号位15/31/63不同。
  if fmt!=16:
   ref=r['functions'][f'zieee_{op}16_exceptions']['jumps']
   for j,h in zip(js,ref):
    assert j['condition'].replace(f'zz5i64zDzKz5i({index})','SIGNINDEX')==h['condition'].replace('zz5i64zDzKz5i(15)','SIGNINDEX'),(n,j['condition'])
  # 每个特殊原因真臂返回独立 NV/DZ，不走后继原因或有限舍入。
  for k,j in enumerate(js[:-1]):
   f,tr=succ(ls,j['pc']);yes,no=reach(ls,tr),reach(ls,f);only=yes-no
   if k+1<len(js):assert js[k+1]['pc'] in no-yes,n
   expected='zieee_exception_facts(false, true, false, false, false)' if op=='div' and k==2 else 'zieee_empty_exceptions(true)'
   special=[ls[i] for i in only if '= zieee_exception_facts(' in ls[i] or '= zieee_empty_exceptions(' in ls[i]]
   assert len(special)==1 and expected in special[0],(n,k,special)
  gate=js[-1];f,tr=succ(ls,gate['pc']);yes,no=reach(ls,tr),reach(ls,f);bypass=reach(ls,0,gate['pc'])
  maths=[i for i,q in enumerate(ls) if re.search(r'= zfp\d+_',q)]
  assert maths and all(i in yes-no and i not in bypass for i in maths),n
  ops=[i for i,q in enumerate(ls) if f'= zfp{wide}_{op}(' in q]
  assert len(ops)==2,(n,ops)
  rounding=[i for i,q in enumerate(ls) if f'= zieee_f{fmt}_rounded_exceptions(' in q]
  assert len(rounding)==1 and rounding[0] in yes-no,n
  checks.append({'function':n,'reason_branches':len(js)-1,'source_classifications':len(sources),'finite_gate_pc':gate['pc'],'wide_arithmetic_calls':len(ops),'all_math_true_only_and_dominated':True})
# changed 真臂内的 Ext_F 真臂才可写 mstatus；两 callbacks 在分支合流后。
n='zaccrue_fflags';ls=lines(n);js=r['functions'][n]['jumps'];assert len(js)==2
assert 'znot_bool(zeq_anythingzIB5zK(' in js[0]['condition'] and 'zor_vec(' in js[0]['condition']
assert js[1]['condition']=='zhartSupports(zExt_F)'
writes={i for i,q in enumerate(ls) if re.match(r'zmstatus(?:\.\w+)? = ',q)};assert len(writes)==1
for j in js:
 f,tr=succ(ls,j['pc']);assert writes<=reach(ls,tr)-reach(ls,f);assert not writes&reach(ls,0,j['pc'])
callbacks=[i for i,q in enumerate(ls) if '= zcsr_name_write_callback(' in q];assert len(callbacks)==2
for j in js:
 f,tr=succ(ls,j['pc']);assert set(callbacks)<=reach(ls,tr)&reach(ls,f)
assert not any('zlong_csr_write_callback' in q for q in ls)
checks.append({'function':n,'changed_and_Ext_F_dominate_bits_write':True,'callbacks_after_merge':True})
# OF/UF/NX 的三层实际出口，每臂只把已证位写常量，保留其他原事实。
for n in ['zieee_f16_rounded_exceptions','zieee_f32_rounded_exceptions','zieee_f64_rounded_exceptions','zieee_exact_threshold_exceptions']:
 js=r['functions'][n]['jumps'];assert len(js)==3
 for k,j in enumerate(js):
  assert j['dominates_true_only'] and j['dominates_false_only']
  calls=[v['call'] for v in j['true_only_calls'] if '= zieee_exception_facts(' in v['call']]
  prefix=['zieee_exception_facts(false, false, true,','zieee_exception_facts(false, false, false, true,','zieee_exception_facts(false, false, false, false, true)'][k]
  assert len(calls)==1 and prefix in calls[0],(n,k,calls)
 checks.append({'function':n,'three_semantic_flag_exits':True})
args.out.write_text(json.dumps({'status':'PASS selected CFG relationships','ir_sha256':r['ir_sha256'],'checks':checks,'scope':'18实际helper、F1及4舍入出口的CFG；不代替剩余包装/窄化/ROD检查、SMT可达性或动态预算'},ensure_ascii=False,indent=2)+'\n')
print('PASS',len(checks),'组实际CFG关系')
