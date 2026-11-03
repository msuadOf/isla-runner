#!/usr/bin/env python3
"""Independently bind final directed results to actual inputs and complete state."""
import hashlib,json,re,sys,tomllib
from pathlib import Path
from collections import Counter
from audit_actual_json import number
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
TOPIC=ROOT/'agents/float_review_closure_20261102'
V=TOPIC/'validation'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
INPUT=V/'inputs.model-21418d0-itrace.json'
MODEL='21418d0b0d4942fae20061ed580ee04aff4a8a61'
IR='5514e98ee5566dbbcfa4f6dbafa9dbb1851c72dce4b52ca0c0a95a1c7fafff4a'
BIN='acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d'
PARTIAL=['errors','execution-timeouts','smt-timeouts','unfinished-paths','assertion-filtered-paths','omitted-cases','model-query-timeouts','encoding-filtered-paths','pending-batches','sampled-paths']
def output_contract(p,reconstructed=None):
 d=read(p);s=d['summary'];assert s['status']=='finished'
 for k in PARTIAL:assert k in s and s[k]==0,(p,k)
 for v in d['provenance']['inputs'].values():assert (sha(v['path']) if Path(v['path']).exists() else reconstructed)==v['sha256']
 return d

def seed(path):
 lines=path.read_text().splitlines();assert lines and all('fixed=17' in x for x in lines)
 return len(lines)

def exception_evidence():
 b=V/'exceptions/runs-model-21418d0-itrace';launch=read(b/'launch.json');summary=read(b/'summary.json')
 assert launch['model_commit']==MODEL and launch['inputs_sha256']==sha(INPUT)
 for key,file in [('ir','base.ir'),('binary','isarch'),('base_config','base-config.toml'),('seed_preload','seed_control.so')]:
  assert sha(b/file)==launch['frozen_hashes'][key]==sha(launch['source_paths'][key])
 assert sha(launch['source_paths']['z3'])==launch['z3_sha256']
 assert summary['count']==summary['completed']==summary['pass']==315
 source=(b/'base.ir').read_text();seen=set();rows=[];preserved=0;initials=0;owner_assertions=0
 for sr in summary['results']:
  name=sr['name'];assert name not in seen;seen.add(name);job=b/'runs'/name;r=read(job/'result.json');c=read(job/'command.json');assert sr==r
  constructor='z'+c['job']['clause'];struct=re.search(r'  '+constructor+r': %struct (\w+),',source)[1]
  fields=re.findall(r'\n  (\w+): ([^,\n]+)',re.search(r'struct '+struct+r' \{(.*?)\n\}',source,re.S)[1]);assert len(fields)==len(c['job']['fields'])
  lines=[]
  for i,((field,ty),value) in enumerate(zip(fields,c['job']['fields'])):
   literal=('0b'+format(value,'0'+ty[3:]+'b')) if isinstance(value,int) else value
   lines.extend([f'  exception_cond{i} : %bool;',f'  exception_unit{i} : %unit;',f'  exception_cond{i} = @eq(zmergez3var as {constructor}.{field}, {literal});',f'  exception_unit{i} = $zsail_assume(exception_cond{i});'])
  marker='fn zexecute(zmergez3var) {\n';assert source.count(marker)==1
  replacement='val zexception_original_execute : (%union zinstruction) -> %union zExecutionResult\n\n'+marker+'\n'.join(lines)+'\n  return = zexception_original_execute(zmergez3var);\n  end;\n}\n\nfn zexception_original_execute(zmergez3var) {\n'
  rebuilt=hashlib.sha256(source.replace(marker,replacement,1).encode()).hexdigest();assert rebuilt==c['constrained_ir_sha256']
  files=list((job/'output').glob('*.json'));assert len(files)==1;d=output_contract(files[0],rebuilt);assert len(d['gen'])==1
  assert r['exit_code']==0 and r['status']=='PASS' and r['output_sha256']==sha(files[0])
  assert c['binary_sha256']==BIN and c['base_ir_sha256']==IR and c['config_sha256']==sha(job/'config.toml')
  argv=c['argv'];assert argv[argv.index('-T')+1]=='1' and argv[argv.index('--tastic')+1]=='qffp' and argv[argv.index('--smt-timeout')+1]=='600s'
  assert c['environment']['ISLA_ABLATION_SEED']=='17' and sha(c['environment']['LD_PRELOAD'])==launch['frozen_hashes']['seed_preload']
  seed(job/'seed-intercept.log');assert sha(job/'seed-intercept.log')==r['seed_log_sha256']
  item=d['gen'][0];assert 'Retire_Success' in item['ret_val'];pre=item['isa-state-complete'];post=item['isa-state-post'];word=number(item['test-ins-encdec']);rd=word>>7&31;opc=word&127
  initial=tomllib.loads((job/'config.toml').read_text())['initial_state']
  for k,v in c['job']['initial'].items():assert number(pre[k])==number(v)==number(initial[k]);initials+=1
  dest=('vr' if opc==0x57 else 'x' if opc==0x53 and (word>>25&~3)==96 else 'f')+str(rd)
  for k in pre:
   if k in (dest,'mstatus','fcsr','vstart'):continue
   assert post[k]==pre[k],(name,k,post[k],pre[k]);preserved+=1
  assert number(post['mstatus'])==number(pre['mstatus'])|0x6000|(1<<63)
  if opc==0x57:assert number(post['vstart'])==0
  else:assert post['vstart']==pre['vstart']
  for a in r['inspection']['assertions']:assert a['pass'] is True and a['actual']==a['expected'];owner_assertions+=1
  rows.append({'name':name,'output_sha256':sha(files[0]),'command_sha256':sha(job/'command.json'),'actual_word':hex(word)})
 assert len(rows)==315 and owner_assertions==33566
 return {'scope':'315 new outputs; actual input/provenance/seed/complete-state checks independent of numerical oracle','launch_sha256':sha(b/'launch.json'),'summary_sha256':sha(b/'summary.json'),'jobs':len(rows),'initial_values_checked':initials,'unchanged_state_fields_checked':preserved,'owner_assertions_also_rechecked':owner_assertions,'rows':rows}

def representations_evidence():
 b=V/'representations/model-21418d0-exact';p=read(b/'provenance.json');assert p['model_commit']==MODEL and p['inputs_sha256']==sha(INPUT) and p['binary_sha256']==BIN and p['ir_sha256']==IR
 rows=[];int_modes=Counter()
 for job in sorted(b.iterdir()):
  if not (job/'result.json').exists():continue
  r=read(job/'result.json');c=read(job/'run/command.json');files=list((job/'run/output').glob('*.json'));assert len(files)==1;d=output_contract(files[0]);argv=c['command']
  assert r['exit_code']==0 and r['output_sha256']==sha(files[0]);assert c['model_commit']==MODEL and c['inputs_sha256']==sha(INPUT) and c['binary_sha256']==BIN and c['source_ir_sha256']==IR
  assert sha(argv[argv.index('-A')+1])==c['run_ir_sha256'] and sha(argv[argv.index('-C')+1])==c['config_sha256']
  assert argv[argv.index('-T')+1]=='1' and argv[argv.index('--tastic')+1]=='qffp' and argv[argv.index('--smt-timeout')+1]=='7200s'
  log=job/'run/seed-intercept.log';seed(log);assert sha(log)==r['seed_log_sha256']
  if job.name=='exact-int-to-D':
   for item in d['gen']:
    w=number(item['test-ins-encdec']);assert w&127==0x53 and w>>25==0x69 and w>>15&31==1 and w>>7&31==0
    assert number(item['isa-state-complete']['x1'])==1 and number(item['isa-state-post']['f0'])==0x3ff0000000000000 and number(item['isa-state-post']['fcsr'])==0
    int_modes[(w>>20&31,w>>12&7)]+=1
  rows.append({'job':job.name,'gen':len(d['gen']),'output_sha256':sha(files[0])})
 assert len(rows)==12 and sum(r['gen'] for r in rows)==135 and int_modes==Counter({(op,rm):1 for op in range(4) for rm in [0,1,2,3,4,7]})
 for driver in p['toolchains']['drivers'].values():assert sha(driver['path'])==driver['sha256']
 assert sha(p['toolchains']['objcopy']['path'])==p['toolchains']['objcopy']['sha256']
 make=V/'make/model-21418d0-exact/smoke';m=read(make/'result.json');output_contract(make/'output/rv64_zFLEQ_S.json')
 assert m['exit_code']==0 and m['inputs_sha256']==sha(INPUT) and m['model_commit']==MODEL and m['binary_sha256']==BIN and m['ir_sha256']==IR
 assert sha(make/'config.toml')==m['config_sha256'] and sha(make/'target/release/isarch')==BIN
 assert sha(make/'make.log')==m['make_log_sha256'] and sha(make/'output/log/FLEQ_S.log')==m['clause_log_sha256']
 seed(make/'seed-intercept.log');assert sha(make/'seed-intercept.log')==m['seed_log_sha256']
 assert 'solve-FLEQ_S' in m['command'] and all(x in m['command'] for x in ['THREADS=1','TASTIC=qffp','SOLVE_TIMEOUT=7200s','SMT_TIMEOUT=7200s','OUTER_TIMEOUT=7200s'])
 assert '[1/] solve-FLEQ_S' in (make/'make.log').read_text()
 assert 'solve-state' in read(make/'output/rv64_zFLEQ_S.json')['provenance']['command']
 return {'scope':'12 directed jobs plus actual Make recipe; no complete-domain claim','provenance_sha256':sha(b/'provenance.json'),'jobs':rows,'int_to_D_actual_combinations':24,'make_result_sha256':sha(make/'result.json'),'make_elapsed_s':m['elapsed_s']}

if __name__=='__main__':
 out={'inputs_sha256':sha(INPUT),'exceptions':exception_evidence(),'representations_make':representations_evidence()}
 (HERE/'model214-evidence-independent.json').write_text(json.dumps(out,indent=2)+'\n')
 print('PASS',out['exceptions']['jobs'],'exceptions;',len(out['representations_make']['jobs']),'representation jobs; Make')
