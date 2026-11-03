#!/usr/bin/env python3
"""Bind a direct flags run to its actual frozen IR/config/probe commands."""
import argparse,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;T=H.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
f=json.loads(a.inputs.read_text());r=json.loads((a.run/'result.json').read_text());assert r['inputs_sha256']==sha(a.inputs) and r['model_commit']==f['model_commit'] and r['isla_commit']==f['isla_commit']
assert r['tactic']=='qffp' and r['seed']==17 and r['build_exit']==0
for field,key in [('frozen_isarch_sha256','binary'),('z3_sha256','z3'),('seed_preload_sha256','seed_preload')]:assert r[field]==f[key]['sha256']
for field,rel in [('runner_source_sha256','src/main.rs'),('oracle_sha256','oracle.py'),('runner_manifest_sha256','Cargo.toml')]:assert r[field]==sha(T/'validation/flags'/rel)
rows=[]
for key,cmd in r['commands'].items():
 binary,ir,config=map(Path,cmd[-3:]);meta=r['runs'][key]
 assert str(ir)==str((H.parents[3]/f['irs'][key]['path']).resolve())
 assert sha(ir)==r['ir_sha256'][key]==f['irs'][key]['sha256']
 assert sha(config)==r['config_sha256']['rv32' if key=='rv32-default' else 'rv64']
 assert sha(binary)==r['binary_sha256']
 assert 'CALLBACK_CONTRACT fflags,fcsr; no mstatus callback' in (a.run/(key+'.log')).read_text().splitlines()
 assert sha(a.run/(key+'.oracle.json'))==meta['oracle_sha256']
 rows.append({'ir_key':key,'ir_sha256':sha(ir),'config_sha256':sha(config),'probe_sha256':sha(binary)})
assert len(rows)==5
out={'scope':'Actual helper command/IR/config/probe source binding; callback only static IR contract','inputs_sha256':sha(a.inputs),'result_sha256':sha(a.run/'result.json'),'model_commit':r['model_commit'],'rows':rows,'pass':True}
a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
