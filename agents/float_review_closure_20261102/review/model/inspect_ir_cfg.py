#!/usr/bin/env python3
"""独立导出每个目标 Jump 的条件与两臂独占调用，供语义审查。"""
import argparse,re,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
text=args.ir.read_text();fs=dict(re.findall(r'(?ms)^fn ([^\n(]+)\([^\n]*\) \{\n(.*?)^\}',text))
def succ(ls,pc):
 s=ls[pc];target=re.search(r'\bgoto (\d+)',s)
 if s.startswith('jump '):return [pc+1,int(target[1])]
 if s.startswith('goto '):return [int(target[1])]
 return [] if s=='end;' else [pc+1] if pc+1<len(ls) else []
def reach(ls,start,stop=None):
 seen=set();todo=[start]
 while todo:
  n=todo.pop()
  if n in seen or n==stop:continue
  assert 0<=n<len(ls),(start,n,len(ls))
  seen.add(n);todo+=succ(ls,n)
 return seen
def expand(s,defs,seen=None):
 seen=set() if seen is None else seen
 def one(m):
  k=m[0]
  if k not in defs or k in seen:return k
  return expand(defs[k],defs,seen|{k})
 return re.sub(r'\bzz\d+\b',one,s)
results={}
for name,body in fs.items():
 if not (re.fullmatch(r'zieee_(?:add|sub|mul|div|sqrt|fma)(?:16|32|64)_exceptions',name) or name in ['zaccrue_fflags','zriscv_f16ToI16_pure','zriscv_f16ToI8_pure','zriscv_f32ToI16_pure','zriscv_f16ToUi16_pure','zriscv_f16ToUi8_pure','zriscv_f32ToUi16_pure','zriscv_f32ToF16','zriscv_f64ToF32','zieee_f16_rounded_exceptions','zieee_f32_rounded_exceptions','zieee_f64_rounded_exceptions','zieee_exact_threshold_exceptions','zieee_rod32_to_16','zieee_rod64_to_32','zieee_fp_to_int_core','zieee_mask_exact_exceptions','zieee_round16_exceptions','zieee_round32_exceptions','zieee_round64_exceptions','zieee_convert32_to_16_exceptions','zieee_convert64_to_16_exceptions','zieee_convert64_to_32_exceptions','zieee_bf16_from_f32_exceptions'] or re.fullmatch(r'zriscv_f(?:16|32|64)To(?:I|Ui)(?:32|64)',name)):continue
 ls=[l.strip() for l in body.splitlines() if l.strip()];defs={};assigned=set();rows=[]
 for pc,l in enumerate(ls):
  m=re.match(r'(\w+) = (.*?) `',l)
  if m:
   if m[1] in assigned:defs[m[1]]='MULTIDEF_'+m[1]
   else:defs[m[1]]=m[2]
   assigned.add(m[1])
  if not l.startswith('jump '):continue
  cond=re.match(r'jump (\w+) goto',l)[1];f,t=succ(ls,pc);fr,tr=reach(ls,f),reach(ls,t)
  def calls(nodes):
   return [{'pc':i,'call':ls[i].split(' `')[0]} for i in sorted(nodes) if re.search(r'= (?:z\w+\(|\$zsail_assert\()',ls[i])]
  rows.append({'pc':pc,'condition':expand(cond,defs),'true_only_calls':calls(tr-fr),'false_only_calls':calls(fr-tr),'dominates_true_only':not bool((tr-fr)&reach(ls,0,pc)),'dominates_false_only':not bool((fr-tr)&reach(ls,0,pc))})
 results[name]={'instructions':len(ls),'jumps':rows}
args.out.write_text(json.dumps({'ir_sha256':hashlib.sha256(args.ir.read_bytes()).hexdigest(),'functions':results,'scope':'真实CFG条件和独占调用；多次赋值变量标MULTIDEF，条件扩展只作数据来源阅读，不宣称SSA/SMT证明；不证明SMT可达性或动态预算'},ensure_ascii=False,indent=2)+'\n')
print(len(results),'函数CFG已导出')
