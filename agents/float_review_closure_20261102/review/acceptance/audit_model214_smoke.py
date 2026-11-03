#!/usr/bin/env python3
"""Audit completed final full-domain startup smoke, without 77-job inference."""
import json,struct
from pathlib import Path
from audit_actual_json import number,effective
from audit_model214_evidence import V,HERE,sha,read,output_contract,seed,INPUT,MODEL,BIN,IR
p=V/'runs/float-closure-21418d0-itrace-smoke-20261103/FLEQ_S';r=read(p/'result.json');output=p/'output/rv64_zFLEQ_S.json';d=output_contract(output)
assert r['model_commit']==MODEL and r['input_manifest_sha256']==sha(INPUT) and r['binary_sha256']==BIN and r['ir_sha256']==IR
assert r['domain']=='full' and r['exit_code']==0 and r['pass'] and r['output_sha256']==sha(output)
assert len(d['gen'])==r['gen_count']==48
trace=p/'output/trace/itrace_FLEQ_S.txt';assert trace.stat().st_size==r['itrace_bytes'] and sha(trace)==r['itrace_sha256']
assert sha(p/'run.log')==r['run_log_sha256'];seed(p/'seed-intercept.log');assert sha(p/'seed-intercept.log')==r['seed_log_sha256']
rows=[];observed=0
for i,c in enumerate(d['gen']):
 w=number(c['test-ins-encdec']);assert w&127==0x53 and w>>25==0x50 and w>>12&7==4 and 'Retire_Success' in c['ret_val']
 pre,post=c['isa-state-complete'],c['isa-state-post'];rd=w>>7&31;a=effective(number(pre[f'f{w>>15&31}']),32);b=effective(number(pre[f'f{w>>20&31}']),32)
 snan=lambda x:x>>23&255==255 and x&0x7fffff and not x&0x400000
 flags=16 if snan(a) or snan(b) else 0
 expected=int(struct.unpack('>f',a.to_bytes(4,'big'))[0]<=struct.unpack('>f',b.to_bytes(4,'big'))[0])
 assert number(post['fcsr'])==number(pre['fcsr'])|flags
 if rd:assert number(post[f'x{rd}'])==expected;observed+=1
 rows.append({'index':i,'word':hex(w),'result':expected,'flags':flags,'destination_observable':bool(rd)})
out={'scope':'Final 21418 full-domain FLEQ_S startup smoke only; separate from active 77 job batch','result_sha256':sha(p/'result.json'),'output_sha256':sha(output),'trace_bytes':trace.stat().st_size,'gen':48,'observable_destinations':observed,'rows':rows}
(HERE/'model214-smoke-independent.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='rows'})
