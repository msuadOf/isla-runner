#!/usr/bin/env python3
"""独立核e9 IR变化边界及FP数值计算的实际表达式签名。"""
from pathlib import Path
import hashlib,json,re
ROOT=Path.cwd();O=ROOT/'agents/float_review_closure_20261102/baseline-0008fae';G=ROOT/'agents/float_review_closure_20261102/validation/generation';targets={f'zieee_{op}{w}_exceptions' for op in ('add','sub','mul','div','sqrt','fma') for w in (16,32,64)}|{'zriscv_'+n+'_pure' for n in ('f16ToI16','f16ToI8','f16ToUi8','f16ToUi16','f32ToI16','f32ToUi16')}|{f'zriscv_f{w}To{dest}' for w in (16,32,64) for dest in ('I32','Ui32','I64','Ui64')}
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def funcs(text):
 return {name:(args,[line.strip() for line in body.splitlines() if line.strip()]) for name,args,body in re.findall(r'(?ms)^fn ([^(\n]+)\(([^\n]*)\) \{\n(.*?)^\}',text)}
def norm(f):
 args,ls=f;params={p.strip():f'PARAM{i}' for i,p in enumerate(args.split(',')) if re.fullmatch(r'z3zE\d+',p.strip())}
 body=re.sub(r'\bz3zE\d+\b',lambda m:params.get(m[0],m[0]),'\n'.join(ls))
 body=re.sub(r'("[^"\n]+\.sail):\d+\.\d+-\d+\.\d+"',r'\1:<source_location>"',body)
 return re.sub(r'\s+','',re.sub(r'`[^;\n]*','',body))
def numeric(f):
 args,ls=f;state={};events=[];params={p.strip():f'PARAM{i}' for i,p in enumerate(args.split(','))}
 def expand(rhs):
  rhs=re.sub(r'`.*','',rhs).rstrip(';').strip()
  return re.sub(r'\bzz\d+\b|\bz3zE\d+\b',lambda m:state.get(m[0],params.get(m[0],m[0])),rhs)
 for line in ls:
  declaration=re.fullmatch(r'(zz\d+) : [^=]+ = (.*)',line)
  assignment=re.match(r'(zz\d+) = (.*?) `',line)
  if declaration or assignment:
   lhs,rhs=(declaration or assignment).groups();expanded=expand(rhs)
   sig=hashlib.sha256(expanded.encode()).hexdigest();state[lhs]='HASH_'+sig
   call=re.match(r'(zfp\w+|zround_\w+|zieee_exact\w+|zieee_f(?:32|64)_bits_as_f128)\(',rhs)
   if call:events.append({'call':call[1],'expanded_expression_sha256':sig})
 return events
rows=[]
for c in ('rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64'):
 old=G/'model-e9d69d2'/c/(c+'.ir');new=G/'model-converged-0f7b8fb'/c/(c+'.ir');a,b=funcs(old.read_text()),funcs(new.read_text());removed=sorted(a.keys()-b.keys());added=sorted(b.keys()-a.keys());changed={n for n in a.keys()&b.keys() if norm(a[n])!=norm(b[n])}
 selected=targets-set(('zriscv_f16ToI64','zriscv_f16ToUi64')) if c=='rv32d' else targets
 assert not removed and not added and changed==selected,(c,removed,added,changed^targets)
 proofs=[]
 for n in sorted(changed):
  x,y=numeric(a[n]),numeric(b[n]);assert x==y,(c,n,x,y);proofs.append({'function':n,'numeric_operations':len(x),'sequence_sha256':hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest(),'old_jump_count':sum(l.startswith('jump ') for l in a[n][1]),'new_jump_count':sum(l.startswith('jump ') for l in b[n][1])})
 rows.append({'config':c,'old_ir_sha256':h(old),'new_ir_sha256':h(new),'old_function_count':len(a),'new_function_count':len(b),'changed':sorted(changed),'removed':removed,'zexecute_unchanged':norm(a['zexecute'])==norm(b['zexecute']),'unchanged_other_functions':len(set(a)&set(b)-changed),'numeric_expression_proofs':proofs})
report={'status':'PASS four IR function scope and numeric expressions','model_commit':'0f7b8fbc6724103f91f929ef6918f123df75d6c9','comparison_model':'e9d69d2f28586c089244c8e37ee4c904c5114458','normalization':'去源码坐标/断言位置字符串/空白/签名生成参数名；数值事件逐顺序追踪赋值依赖哈希，支持同变量多次赋值，比较每个FP/舍入/exact转换的完整上游表达式','rows':rows,'scope':'不单凭此报告签生成来源/纯返回flags和jam/动态；永久checker及负控另核。'}
(O/'converged-ir-review-20261103.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS four IR: expected36/34 changed; all numerical expression signatures unchanged')
