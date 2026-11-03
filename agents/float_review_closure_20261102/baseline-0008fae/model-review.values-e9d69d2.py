#!/usr/bin/env python3
"""从旧IR分支条件独立核新IR的flags/JAM值流，赋值按指令顺序处理。"""
from pathlib import Path
import re,json,hashlib
R=Path.cwd();G=R/'agents/float_review_closure_20261102/validation/generation';O=R/'agents/float_review_closure_20261102/baseline-0008fae'
def fs(s):return {n:[l.strip() for l in b.splitlines() if l.strip()] for n,b in re.findall(r'(?ms)^fn ([^(\n]+)\([^\n]*\) \{\n(.*?)^\}',s)}
def args(s):
 out=[];start=0;depth=0
 for i,c in enumerate(s):
  depth+=(c=='(')-(c==')')
  if c==',' and depth==0:out.append(s[start:i].strip());start=i+1
 assert depth==0;out.append(s[start:].strip());return out

def value(x,env):
 x=x.strip()
 if re.fullmatch(r'\w+',x):return env.get(x,x)
 expanded=re.sub(r'\bzz\d+\b',lambda m:env.get(m[0],m[0]),x)
 return 'EXPR_'+hashlib.sha256(re.sub(r'\s+','',expanded).encode()).hexdigest()
def analyze(ls):
 env={};before=[];assign=[];jumps=[]
 for pc,l in enumerate(ls):
  before.append(env.copy());clean=l.split('`',1)[0].rstrip(';').strip()
  match=re.fullmatch(r'(zz\d+)(?: : [^=]+)? = (.*)',clean)
  if match:
   var,rhs=match.groups();v=value(rhs,env);assign.append((pc,var,rhs,v));env[var]=v
  jump=re.match(r'jump (\w+) goto ',l)
  if jump:jumps.append((pc,jump[1],value(jump[1],env)))
 return {'before':before,'assign':assign,'jumps':jumps,'lines':ls}
def facts(a):
 out=[]
 for pc,l in enumerate(a['lines']):
  m=re.match(r'return = zieee_exception_facts\(([^`]+)\) `',l)
  if m:out.append((pc,[value(x,a['before'][pc]) for x in args(m[1])]))
 return out

def tuplefields(l):return [x.strip() for x in re.findall(r'\w+ = ([^,}]+)',l.split('{',1)[1])]
def aliases(x,a,opaque=None):
 d={var:rhs for pc,var,rhs,v in a['assign']};seen=set()
 while x in d and x!=opaque and x not in seen:seen.add(x);x=d[x]
 return x
rows=[]
for c in ('rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64'):
 af=fs((G/'model-21418d0'/c/(c+'.ir')).read_text());bf=fs((G/'model-e9d69d2'/c/(c+'.ir')).read_text());proof=[]
 for n in ['zieee_f16_rounded_exceptions','zieee_f32_rounded_exceptions','zieee_f64_rounded_exceptions','zieee_exact_threshold_exceptions']:
  a,b=analyze(af[n]),analyze(bf[n]);f=facts(b);assert len(a['jumps'])==3 and not b['jumps'] and len(f)==1
  assert f[0][1]==['false','false',*[j[2] for j in a['jumps']]],(c,n)
  proof.append({'function':n,'check':'new OF/UF/NX return fields equal all three old branch-condition DAGs'})
 for width in (16,32,64):
  n=f'zieee_round{width}_exceptions';a,b=analyze(af[n]),analyze(bf[n]);f=facts(b);assert len(a['jumps'])==2 and len(b['jumps'])==1 and len(f)==1
  assert a['jumps'][0][2]==b['jumps'][0][2] and f[0][1][1:]==['false','false','false',a['jumps'][1][2]]
  oldnv=next((pc,var,rhs,v) for pc,var,rhs,v in a['assign'] if rhs.startswith('zieee_operand_invalid('));assert f[0][1][0]==oldnv[3]
  proof.append({'function':n,'check':'same finite guard, same per-source NV and old NX condition returned directly'})
 n='zieee_fp_to_int_core';a,b=analyze(af[n]),analyze(bf[n]);f=facts(b);assert len(a['jumps'])==3 and len(b['jumps'])==2 and len(f)==1
 assert [j[2] for j in a['jumps'][:2]]==[j[2] for j in b['jumps']] and f[0][1]==['false']*4+[a['jumps'][-1][2]]
 proof.append({'function':n,'check':'same finite/valid guards, direct return of old NX condition'})
 for n in ('zieee_convert32_to_16_exceptions','zieee_convert64_to_16_exceptions','zieee_convert64_to_32_exceptions','zieee_bf16_from_f32_exceptions'):
  a,b=analyze(af[n]),analyze(bf[n]);assert len(a['jumps'])==len(b['jumps'])==1 and a['jumps'][0][2]==b['jumps'][0][2]
  oldcall=next((pc,l) for pc,l in enumerate(a['lines']) if 'return = zieee_mask_exact_exceptions(' in l);raw=re.search(r'zieee_mask_exact_exceptions\(([^`]+)\) `',oldcall[1])[1];oa=args(raw);assert oa[1]=='true'
  returns=[(pc,re.match(r'return = (\w+) `',l)[1]) for pc,l in enumerate(b['lines']) if re.match(r'return = (\w+) `',l)];assert len(returns)==1
  pc,ret=returns[0];assert value(ret,b['before'][pc])==value(oa[2],a['before'][oldcall[0]])
  proof.append({'function':n,'check':'same finite guard and actual exact facts returned unchanged'})
 for sw,tw in ((32,16),(64,32)):
  n=f'zieee_rod{sw}_to_{tw}';a,b=analyze(af[n]),analyze(bf[n]);assert len(a['jumps'])==2 and len(b['jumps'])==1 and a['jumps'][0][2]==b['jumps'][0][2]
  oldrets=[(pc,tuplefields(l)) for pc,l in enumerate(a['lines']) if l.startswith('return = struct ')];newrets=[(pc,tuplefields(l)) for pc,l in enumerate(b['lines']) if l.startswith('return = struct ')];assert len(oldrets)==2 and len(newrets)==1
  npc,(flags,result)=newrets[0];oldflags=oldrets[0][1][0];assert all(v[0]==oldflags for pc,v in oldrets)
  ite=aliases(result,b);im=re.fullmatch(r'zitezIB'+str(tw)+r'zK\((.*)\)',ite);assert im
  cond,jam,base=args(im[1]);cm=re.fullmatch(r'zieee_has_inexact\((\w+)\)',aliases(cond,b));assert cm and cm[1]==flags
  jamrhs=aliases(jam,b);jm=re.fullmatch(r'zor_vec\((.*)\)',jamrhs);assert jm
  ja=args(jm[1]);bv=value(base,b['before'][npc]);one='0x'+format(1,f'0{tw//4}X');assert {value(x,b['before'][npc]) for x in ja}=={bv,one}
  assert bv==value(oldrets[0][1][1],a['before'][oldrets[0][0]])
  # Both assignments of the non-SSA merged flags are checked separately.
  oa=[x for x in a['assign'] if x[1]==oldflags];na=[x for x in b['assign'] if x[1]==flags];assert len(oa)==len(na)==2
  assert oa[0][3]==na[0][3]
  mask=re.fullmatch(r'zieee_mask_exact_exceptions\((.*)\)',oa[1][2]);assert mask;ma=args(mask[1]);assert ma[1]=='true'
  assert value(ma[2],a['before'][oa[1][0]])==na[1][3]
  proof.append({'function':n,'check':'same finite guard/RTZ base, both merged flags assignments; jam ITE uses same flags NX and exact base|1/base'})
 rows.append({'config':c,'proofs':proof})
report={'status':'PASS actual IR pure values and retained gates','model':'e9d69d2f28586c089244c8e37ee4c904c5114458','comparison':'21418d0','rows':rows,'method':'每条赋值建立按时间的表达式DAG指纹；引用旧实际Jump条件对新返回字段，ROD非SSA flags两个赋值分别核；不以源码if数或关键字出现替代值合同'}
(O/'model-review.values-e9d69d2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS four configurations x14 actual IR value/guard contracts')
