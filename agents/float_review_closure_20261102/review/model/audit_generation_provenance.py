#!/usr/bin/env python3
"""独立核四配置严格生成、普通检查及五IR别名的来源和哈希。"""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path.cwd();OUT=ROOT/'agents/float_review_closure_20261102/review/model';G=ROOT/'agents/float_review_closure_20261102/validation/generation/model-8ad5e8e';MODEL=ROOT/'.worktree/runner-float/sail-riscv'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((G/'independent-input-audit.json').read_text());source=json.loads((G/'source.json').read_text());manifest=json.loads((ROOT/'isla/ir/provenance/manifest.json').read_text());inputs_path=ROOT/'agents/float_review_closure_20261102/validation/inputs.model-8ad5e8e.json';inputs=json.loads(inputs_path.read_text())
assert a['model_commit']==source['commit']==inputs['model_commit']=='8ad5e8e9e0fc2a567a3b989a3738698f5c520bde'
assert subprocess.check_output(['git','-C',str(MODEL),'rev-parse','HEAD'],text=True).strip()==a['model_commit']
assert len(a['tracked_model_files'])==166
for n,v in a['tracked_model_files'].items():assert h(MODEL/'model'/n)==v==source['model_files'][n],n
for n,v in a['tool_files'].items():assert h(ROOT/n)==v,n
assert len(a['tool_files'])==149 and a['tool_ctime_precedes_generation_start'] and a['source_unchanged_now']
assert a['generation_start_source_manifest_sha256']==h(G/'source.json')
for row in manifest['artifacts']:assert h(ROOT/'isla/ir/provenance'/row['config'])==row['config_sha256']
assert a['tool_files'][a['actual_sail_binary']]==manifest['sail_binary_sha256']
z3=json.loads((G/'compile-z3-audit.json').read_text());assert h(Path(z3['observed_live_grandchild']['exe']))==z3['actual_z3_sha256'] and z3['ctime_precedes_generation_start']
rows=[]
for kind in ('ordinary-strict','rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64'):
 d=json.loads((G/kind/'driver.json').read_text());assert d['exit_code']==0 and d['source_unchanged'] and d['model_commit']==a['model_commit']
 for n,v in a['tracked_model_files'].items():assert d['model_files'][n]==v
 if kind=='ordinary-strict':
  cmd=d['command'];assert '--just-check' in cmd and 'SYMBOLIC' not in cmd
 else:
  q=json.loads((G/kind/'generation.json').read_text());cmd=q['command'];assert q['exit_code']==0 and q['model_commit']==a['model_commit']
  for n,v in a['tracked_model_files'].items():assert q['model_files'][n]==v
  assert h(G/kind/(kind+'.ir'))==q['ir_sha256']==d['ir_sha256']
  assert '-D' in cmd and 'SYMBOLIC' in cmd
 for opt in ('--strict-var','--strict-bitvector','--strict-exponentials','--all-modules'):assert opt in cmd
 assert cmd[cmd.index('--require-version')+1]=='0.20.1'
 rows.append({'kind':kind,'exit_code':0,'source_unchanged':True,'ir_sha256':d.get('ir_sha256'),'seconds':d['seconds']})
irs={}
for name,row in inputs['irs'].items():
 p=Path(row['path']);p=p if p.is_absolute() else ROOT/p
 assert h(p)==row['sha256'];irs[name]=row['sha256']
assert len(irs)==5 and irs['rv64-default']==irs['rv64-v128']
report={'status':'PASS generation provenance only','model_commit':a['model_commit'],'inputs_sha256':h(inputs_path),'tracked_model_inputs':166,'verified_tool_files':149,'actual_sail_binary_sha256':a['tool_files'][a['actual_sail_binary']],'compile_z3':z3,'generated':rows,'five_ir_hashes':irs,'scope':'严格生成和来源通过，不包含永久CFG检查器或动态结果。'}
(OUT/'generation-provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('PASS ordinary + 四SYMBOLIC + 五IR别名，166模型/149工具哈希')
