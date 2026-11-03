#!/usr/bin/env python3
"""Bind a selected directed exception batch to its own frozen inputs and complete state."""
import argparse,hashlib,json,re,subprocess,sys,tomllib
from pathlib import Path
from collections import Counter
from audit_actual_json import number
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
TOPIC=ROOT/'agents/float_review_closure_20261102'
V=TOPIC/'validation'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
INPUT=None
MODEL=None
ISLA=None
MODEL_TREE=None
IR=None
BIN=None
RUN=None
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
 b=RUN;launch=read(b/'launch.json');summary=read(b/'summary.json')
 assert launch['model_commit']==MODEL and launch['isla_commit']==ISLA and launch['inputs_sha256']==sha(INPUT)
 assert launch['frozen_hashes']['ir']==IR and launch['frozen_hashes']['binary']==BIN
 assert launch['script_sha256']==sha(V/'exceptions/run_directed.py')
 assert launch['expected_sha256']==sha(V/'exceptions/expected.json')
 assert launch['expected_source_commit']=='8ad5e8e9e0fc2a567a3b989a3738698f5c520bde'
 if launch.get('model_delta_base_commit'):
  delta=subprocess.check_output(['git','-C',str(MODEL_TREE),'diff','--no-ext-diff',launch['model_delta_base_commit'],MODEL])
  assert hashlib.sha256(delta).hexdigest()==launch['model_delta_sha256']
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
 return {'scope':'315 new outputs; actual input/provenance/seed/complete-state checks independent of numerical oracle','launch_sha256':sha(b/'launch.json'),'summary_sha256':sha(b/'summary.json'),'model_delta_base_commit':launch.get('model_delta_base_commit'),'model_delta_sha256':launch.get('model_delta_sha256'),'jobs':len(rows),'initial_values_checked':initials,'unchanged_state_fields_checked':preserved,'owner_assertions_also_rechecked':owner_assertions,'rows':rows}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--model',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 INPUT=args.inputs.resolve(strict=True);RUN=args.run.resolve(strict=True);frozen=read(INPUT);MODEL=args.model
 assert frozen['model_commit']==MODEL
 IR=frozen['irs']['rv64-v128']['sha256'];BIN=frozen['binary']['sha256'];ISLA=frozen['isla_commit'];MODEL_TREE=ROOT/frozen['model_tree']['path']
 assert frozen['threads']==1 and frozen['tactic']=='qffp' and frozen['seed']==17
 out={'inputs_sha256':sha(INPUT),'model_commit':MODEL,'isla_commit':frozen['isla_commit'],'ir_sha256':IR,'binary_sha256':BIN,'exceptions':exception_evidence()}
 args.output.write_text(json.dumps(out,indent=2)+'\n');print({k:v if k!='exceptions' else {kk:vv for kk,vv in v.items() if kk!='rows'} for k,v in out.items()})
