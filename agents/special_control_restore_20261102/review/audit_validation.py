#!/usr/bin/env python3
"""独立核对本轮定向结果、原始位值、包装保真与SoftFloat预期。"""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;V=HERE.parent/'validation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bits(v):return v if isinstance(v,int) else int(re.fullmatch(r"\d+'h([0-9a-fA-F_]+)",v)[1].replace('_',''),16)
launch=json.loads((V/'launch.json').read_text());summary=json.loads((V/'summary.json').read_text());base=(V/'inputs/model.ir').read_text();base_hash=sha(V/'inputs/model.ir')
assert summary['state']=='completed' and len(summary['jobs'])==56
assert sha(V/'bin/isarch')==launch['binary_sha256']
ORACLE=ROOT/'.tmp/unified-backend-crosscheck/oracle-build/oracle';assert sha(ORACLE)==launch['oracle_sha256']
rows=[];total=0;all_pairs={};fused_cases=set();mask_cases=set();wrapped_count=0;retire_count=0
for name,entry in summary['jobs'].items():
 d=V/'runs'/name;record=json.loads((d/'result.json').read_text());cmd=json.loads((d/'command.json').read_text());job=cmd['job'];check=job['check'];jsons=list((d/'output').glob('*.json'));assert len(jsons)==1
 assert entry['state']==record['state']=='PASS' and entry['exit']==record['exit']==0 and record['partial'] is False
 assert sha(jsons[0])==record['output_sha256']==entry['output_sha256']
 assert cmd['binary_sha256']==launch['binary_sha256'] and cmd['base_ir_sha256']==base_hash
 assert sha(d/'config.toml')==cmd['config_sha256']
 argv=cmd['argv'];assert argv[argv.index('--smt-timeout')+1]=='7200s' and '7200s' in argv and argv[argv.index('-T')+1]=='1' and argv[argv.index('--tastic')+1]=='qffp'
 ir=Path(argv[argv.index('-A')+1]);assert sha(ir)==cmd['ir_sha256']
 if job['fields'] is not None:
  t=ir.read_text();intro='val zvalidation_original_execute : (%union zinstruction) -> %union zExecutionResult\n\n';start=t.index(intro);end=t.index('fn zvalidation_original_execute(zmergez3var) {\n',start)
  restored=t[:start]+t[end:].replace('fn zvalidation_original_execute(zmergez3var) {\n','fn zexecute(zmergez3var) {\n',1);assert restored==base
  wrapper=t[start:end];assert wrapper.count('= $zsail_assume(')==len(job['fields']);wrapped_count+=1
 else:assert ir.read_text()==base
 data=json.loads(jsons[0].read_text());assert data['summary']['status']=='finished'
 for k in ['sampled-paths','errors','execution-timeouts','smt-timeouts','unfinished-paths','omitted-cases','model-query-timeouts','pending-batches']:assert data['summary'][k]==0
 total+=len(data['gen']);assert len(data['gen'])==record['gen']==entry['gen']
 seen=set();successes=0
 for case in data['gen']:
  if 'Retire_Success' not in case['ret_val']:continue
  successes+=1;retire_count+=1;pre=case['isa-state-complete'];post=case['isa-state-post'];assert bits(pre['fcsr'])&31==0
  if check['kind']=='scalar-pairs':
   fmt=check['format'];w,e,m={'H':(16,5,10),'S':(32,8,23),'D':(64,11,52)}[fmt]
   regs=re.findall(r'f\d+',case['test-ins']);assert len(regs)==2;classes=[]
   for r in regs:
    raw=bits(pre[r]);assert w==64 or raw>>w==(1<<(64-w))-1
    exp=(raw>>m)&((1<<e)-1);fraction=raw&((1<<m)-1)
    classes.append('sNaN' if exp==(1<<e)-1 and fraction and not(fraction>>(m-1)&1) else 'qNaN' if exp==(1<<e)-1 and fraction else 'normal')
   pair=tuple(classes);seen.add(pair);assert bits(post['fcsr'])&31==(16 if 'sNaN' in pair else 0)
   rd=re.search(r' x(\d+),',case['test-ins'])[1]
   if rd!='0':assert bits(post['x'+rd])==int(pair==('normal','normal'))
   for r in regs:assert bits(post[r])==bits(pre[r])
  elif check['kind']=='bf16':
   flags=0;expected=bits(pre['vr8']);mask=check['mask'];vl=int(job['initial']['vl'],16);rm=check['rm']
   for lane in range(2):
    if lane>=vl or not(mask>>lane&1):continue
    a=check['source_a'][lane]<<16;b=check['source_b'][0 if check['form']=='VF' else lane]<<16;c=check['acc'][lane]
    answer=json.loads(subprocess.check_output([str(ORACLE),'--op','fma','--fmt','f32','--rm',str(rm),'--a',hex(a),'--b',hex(b),'--c',hex(c)],text=True))
    expected=(expected&~(0xffffffff<<(32*lane)))|(int(answer['result_bits'],16)<<(32*lane));flags|=int(answer['flags'],16)
   assert bits(post['vr8'])==expected and bits(post['fcsr'])&31==flags and bits(post['fcsr'])>>5==rm
   for r in range(32):
    if r!=8:assert bits(post['vr'+str(r)])==bits(pre['vr'+str(r)])
   assert bits(post['vstart'])==0
   if check['case'] in ['fused','tiny']:fused_cases.add((check['form'],check['case'],rm))
   if check['case'].startswith('multi'):mask_cases.add((check['form'],mask,flags))
  else:
   assert bits(post['fcsr'])&31==check.get('expected_flags',bits(post['fcsr'])&31)
 assert successes>0
 if check['kind']=='scalar-pairs':
  nan=check['nan'];assert all(p in seen for p in [(nan,'normal'),('normal',nan),('normal','normal'),(nan,nan)]);all_pairs[name]=sorted(map(list,seen))
 rows.append({'job':name,'gen':len(data['gen']),'retire':successes,'wrapper_reversed_exactly':job['fields'] is not None,'exit':0})
assert len(fused_cases)==20
assert mask_cases=={(form,mask,flags) for form in ['VV','VF'] for mask,flags in [(0,0),(1,16),(2,5),(3,21)]}
result={'pass':True,'jobs':len(rows),'json_cases':total,'retire_cases':retire_count,'exact_wrapper_reverse_count':wrapped_count,'base_ir_sha256':base_hash,'independent_pair_classes':all_pairs,'fused_boundary_rm_form_count':len(fused_cases),'multi_lane_or_cases':sorted(mask_cases),'rows':rows,'scope':'固定初态、字段约束及vl≤2的定向域；不证明默认全域及全部20循环动态覆盖'}
(HERE/'validation-final-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('PASS',len(rows),total,'JSON',wrapped_count,'exact wrappers',len(fused_cases),'fusion',len(mask_cases),'multi-mask')
