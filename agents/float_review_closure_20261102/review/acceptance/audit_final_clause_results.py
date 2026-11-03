#!/usr/bin/env python3
"""Independent actual-word/state audit for the two authorized full entries."""
import argparse,json,struct
from pathlib import Path
from collections import Counter
from audit_actual_json import number,effective
from audit_model214_evidence import sha,read,seed,output_contract
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--job',choices=['FLEQ_S','C_ADDI4SPN'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
b=a.run;f=read(a.inputs);r=read(b/'result.json');assert r['job']==a.job and r['domain']=='full'
assert r['model_commit']==f['model_commit'] and r['isla_commit']==f['isla_commit'] and r['input_manifest_sha256']==sha(a.inputs)
assert r['scope']==f['jobs'][a.job]['scope'] and r['affected_manifest_sha256']==f['affected_manifest']['sha256']
assert r['binary_sha256']==f['binary']['sha256'] and r['ir_sha256']==f['irs']['rv64-v128']['sha256'] and r['config_sha256']==f['configs']['rv64-fd-full']['sha256']
assert r['z3_sha256']==f['z3']['sha256'] and r['seed_preload_sha256']==f['seed_preload']['sha256']
assert r['exit_code']==0 and r['pass'] and r['seed']==17
argv=r['command'];assert argv[argv.index('-T')+1]=='1' and argv[argv.index('--tastic')+1]=='qffp' and argv[argv.index('--smt-timeout')+1]=='7200s' and '7200s' in argv[:argv.index('-T')]
files=list((b/'output').glob('*.json'));assert len(files)==1;d=output_contract(files[0]);assert sha(files[0])==r['output_sha256'] and len(d['gen'])==r['gen_count'] and d['gen']
seed(b/'seed-intercept.log');assert sha(b/'seed-intercept.log')==r['seed_log_sha256'] and sha(b/'run.log')==r['run_log_sha256']
trace=b/'output/trace'/f'itrace_{a.job}.txt'
if 'itrace_sha256' in r:assert r['itrace_bytes']>0 and trace.stat().st_size==r['itrace_bytes'] and sha(trace)==r['itrace_sha256']
rows=[];retkinds=Counter();observable=0
for i,c in enumerate(d['gen']):
 w=number(c['test-ins-encdec']);pre,post=c['isa-state-complete'],c['isa-state-post'];ret=c['ret_val'];illegal='Illegal_Instruction' in ret;retire='Retire_Success' in ret;assert illegal or retire
 width=int(c['test-ins-encdec'].split("'")[0]);assert width==(32 if a.job=='FLEQ_S' else 16)
 enc=c['instruction-representations']['encoding'];assert len(enc['bits'])==width and int(enc['bits'],2)==int(enc['hex'],16)==w and enc['bytes-le']==w.to_bytes(width//8,'little').hex()
 retkinds['Illegal_Instruction' if illegal else 'Retire_Success']+=1
 want={};dest=None
 if a.job=='FLEQ_S':
  assert w&127==0x53 and w>>25==0x50 and w>>12&7==4
  if retire:
   rd=w>>7&31;x=effective(number(pre[f'f{w>>15&31}']),32);y=effective(number(pre[f'f{w>>20&31}']),32)
   snan=lambda z:z>>23&255==255 and z&0x7fffff and not(z&0x400000)
   flags=16 if snan(x) or snan(y) else 0
   value=int(struct.unpack('>f',x.to_bytes(4,'big'))[0]<=struct.unpack('>f',y.to_bytes(4,'big'))[0])
   want['fcsr']=number(pre['fcsr'])|flags
   want['mstatus']=number(pre['mstatus'])|(0x6000|(1<<63) if flags&~number(pre['fcsr'])&31 else 0)
   if rd:dest=f'x{rd}';want[dest]=value;observable+=1
 else:
  assert w<65536 and w&3==0 and w>>13==0
  imm=((w>>7&15)<<6)|((w>>11&3)<<4)|((w>>5&1)<<3)|((w>>6&1)<<2)
  if retire:
   assert imm!=0;dest=f'x{8+(w>>2&7)}';want[dest]=(number(pre['x2'])+imm)&((1<<64)-1);observable+=1
 for key,value in want.items():assert number(post[key])==value,(i,key,post[key],hex(value))
 for key in pre:
  if key not in want:assert post[key]==pre[key],(i,key,'unintended state change')
 rows.append({'index':i,'word':hex(w),'retire':retire,'destination':dest,'computed_fields':{k:hex(v) for k,v in want.items()},'pass':True})
for k,v in retkinds.items():assert r['return_kinds'][k]==v
out={'scope':'Two explicitly authorized full-domain entries only; no float77 whole-domain claim','model_commit':f['model_commit'],'inputs_sha256':sha(a.inputs),'result_sha256':sha(b/'result.json'),'output_sha256':sha(files[0]),'job':a.job,'gen':len(rows),'observable_destinations':observable,'return_kinds':dict(retkinds),'trace_bytes':r.get('itrace_bytes'),'trace_sha256':r.get('itrace_sha256'),'elapsed_s':r['elapsed_s'],'rows':rows,'pass':True}
a.output.write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='rows'})
