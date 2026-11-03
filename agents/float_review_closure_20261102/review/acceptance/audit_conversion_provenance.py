#!/usr/bin/env python3
"""Audit direct conversion archives and actual new-version identities."""
import argparse,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
r=read(a.run/'run.json');f=read(a.inputs);s=read(a.snapshot);archive=a.run/'input-archive'
assert r['model_commit']==f['model_commit'] and r['isla_commit']==f['isla_commit']
assert r['inputs']['ir']['sha256']==f['irs']['rv64-v128']['sha256']
assert sha(a.snapshot.parent/'formal-inputs.json')==sha(a.inputs)
for name,want in s['files'].items():assert sha(archive/name)==sha(a.snapshot.parent/name)==want
assert len(s['files'])==14
for name,want in r['source_sha256'].items():assert sha(archive/name)==want
for v in r['inputs'].values():assert sha(ROOT/v['path'])==v['sha256']
assert sha(ROOT/r['seed_preload']['path'])==r['seed_preload']['sha256']==f['seed_preload']['sha256']
assert sha(a.run/'wrapped.ir')==r['wrapped_ir_sha256']
ir=ROOT/r['inputs']['ir']['path'];driver=ir.parent/'driver.json';d=read(driver)
assert sha(driver)==r['generation_driver_sha256'] and d['model_commit']==r['model_commit'] and d['ir_sha256']==sha(ir) and d['source_unchanged'] and d['exit_code']==0
source=ir.parents[1]/'source.json';sd=read(source);assert sha(source)==r['model_source']['manifest_sha256'] and sd['commit']==r['model_commit']
for name,want in sd['model_files'].items():assert sha(ROOT/r['model_tree']/'model'/name)==want
assert len(sd['model_files'])==r['model_source']['verified_files']==166
for stage in r['stages']:
 assert stage['exit_code']==0 and sha(a.run/(stage['label']+'.log'))==stage['log_sha256']
 if 'seed_log_sha256' in stage:
  seed=a.run/(stage['label']+'-seed.log');assert sha(seed)==stage['seed_log_sha256']
  assert seed.read_text().splitlines() and all(x.endswith('fixed=17') for x in seed.read_text().splitlines())
for dep in r['linked_z3']:
 assert dep['linked_z3_sha256']==f['z3']['sha256']
binding=read(a.run/'formal-input-binding.json');assert binding['formal_inputs_sha256']==sha(a.inputs) and binding['formal_model_commit']==r['model_commit']
assert binding['direct_helper_binary_sha256']==r['inputs']['helper_bin']['sha256'] and binding['direct_instruction_binary_sha256']==r['inputs']['instruction_bin']['sha256']
assert binding['shared_v128_ir_sha256']==sha(ir) and binding['shared_official_z3_sha256']==f['z3']['sha256']
assert binding['direct_config_sha256']==r['inputs']['config']['sha256'] and binding['formal_full_clause_config_sha256']==f['configs']['rv64-fd-full']['sha256']
assert binding['formal_binary_sha256']==f['binary']['sha256'] and binding['direct_runner_tactic']==r['tactic']
out={'scope':'New direct-runner archived inputs/provenance only; Qfaufbv, different config/binaries from formal qffp Clause','inputs_sha256':sha(a.inputs),'run_sha256':sha(a.run/'run.json'),'snapshot_sha256':sha(a.snapshot),'model_commit':r['model_commit'],'isla_commit':r['isla_commit'],'ir_sha256':sha(ir),'direct_config_sha256':r['inputs']['config']['sha256'],'direct_helper_binary_sha256':r['inputs']['helper_bin']['sha256'],'direct_instruction_binary_sha256':r['inputs']['instruction_bin']['sha256'],'archived_files_verified':14,'model_files_verified':166,'isla_manifest_source_files':r['isla_source']['verified_files'],'pass':True}
a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
