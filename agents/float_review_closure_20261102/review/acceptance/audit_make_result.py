#!/usr/bin/env python3
"""Independent fixed-input Make FLEQ.S numerical, provenance, and byte audit."""
import argparse,json,struct
from pathlib import Path
from collections import Counter
from audit_actual_json import number,effective
from audit_representation_results import audit
from audit_model214_evidence import sha,read,seed,output_contract
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
b=a.run;r=read(b/'result.json');f=read(a.inputs);j=b/'output/rv64_zFLEQ_S.json';d=output_contract(j)
assert r['model_commit']==f['model_commit'] and r['isla_commit']==f['isla_commit'] and r['inputs_sha256']==sha(a.inputs)
for key,item in [('binary_sha256','binary'),('ir_sha256',None),('preload_sha256','seed_preload'),('z3_sha256','z3')]:assert r[key]==(f[item]['sha256'] if item else f['irs']['rv64-v128']['sha256'])
assert r['exit_code']==0 and r['output_sha256']==sha(j) and r['gen']==len(d['gen'])==8
assert sha(b/'target/release/isarch')==r['binary_sha256'] and sha(b/'config.toml')==r['config_sha256']
for rel,key in [('make.log','make_log_sha256'),('output/log/FLEQ_S.log','clause_log_sha256'),('seed-intercept.log','seed_log_sha256')]:assert sha(b/rel)==r[key]
seed(b/'seed-intercept.log');assert '[1/] solve-FLEQ_S' in (b/'make.log').read_text()
assert 'solve-state' in d['provenance']['command']
assert all(s in r['command'] for s in ['THREADS=1','TASTIC=qffp','SOLVE_TIMEOUT=7200s','SMT_TIMEOUT=7200s','OUTER_TIMEOUT=7200s'])
pairs=Counter();observable=0
for c in d['gen']:
 w=number(c['test-ins-encdec']);assert w&127==0x53 and w>>25==0x50 and w>>12&7==4 and 'Retire_Success' in c['ret_val']
 pre,post=c['isa-state-complete'],c['isa-state-post'];rd=w>>7&31;x=effective(number(pre[f'f{w>>15&31}']),32);y=effective(number(pre[f'f{w>>20&31}']),32)
 def cls(v):
  if v>>23&255==255 and v&0x7fffff:assert v&0x400000;return 'qnan'
  assert v>>23&255!=255;return 'finite'
 pairs[cls(x),cls(y)]+=1
 value=int(struct.unpack('>f',x.to_bytes(4,'big'))[0]<=struct.unpack('>f',y.to_bytes(4,'big'))[0])
 assert post['fcsr']==pre['fcsr'] and post['mstatus']==pre['mstatus']
 if rd:assert number(post[f'x{rd}'])==value;observable+=1
 for k in pre:
  if k==f'x{rd}':continue
  assert post[k]==pre[k],k
assert pairs==Counter({(x,y):2 for x in ['finite','qnan'] for y in ['finite','qnan']})
result={'scope':'Actual fixed-state Make FLEQ.S only, not complete-domain Clause','model_commit':f['model_commit'],'inputs_sha256':sha(a.inputs),'result_sha256':sha(b/'result.json'),'output_sha256':sha(j),'gen':8,'observable_destinations':observable,'source_pairs':{'/'.join(k):v for k,v in pairs.items()},'elapsed_s':r['elapsed_s'],'byte_checks':audit(j,b/'toolchains'),'pass':True}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
