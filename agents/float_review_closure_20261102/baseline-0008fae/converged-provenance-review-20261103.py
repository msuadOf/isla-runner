#!/usr/bin/env python3
"""独立核named e9严格生成、memo副本与冻结214未变。"""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path.cwd();O=ROOT/'agents/float_review_closure_20261102/baseline-0008fae';V=ROOT/'agents/float_review_closure_20261102/validation';G=V/'generation/model-converged-0f7b8fb';OLD=V/'generation/model-e9d69d2';M=ROOT/'.worktree/sail-riscv-float-converged-20261103'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((G/'independent-input-audit.json').read_text());s=json.loads((G/'source.json').read_text());prior=json.loads((OLD/'independent-input-audit.json').read_text());audit_path=ROOT/'agents/float_review_closure_20261102/review/model/memo-reuse-e9d69d2.json';audit=json.loads(audit_path.read_text());commit='0f7b8fbc6724103f91f929ef6918f123df75d6c9'
assert a['model_commit']==s['commit']==commit and s['model_tree']==str(M.relative_to(ROOT))
assert subprocess.check_output(['git','-C',str(M),'rev-parse','HEAD'],text=True).strip()==commit
assert len(a['tracked_model_files'])==166
for n,v in a['tracked_model_files'].items(): assert h(M/'model'/n)==v==s['model_files'][n]
assert a['tool_files']==prior['tool_files'] and len(a['tool_files'])==149
for n,v in a['tool_files'].items():assert h(ROOT/n)==v,n
assert a['tool_ctime_precedes_generation_start'] and a['source_unchanged_now'] and a['generation_start_source_manifest_sha256']==h(G/'source.json')
z3=json.loads((V/'generation/model-8ad5e8e/compile-z3-audit.json').read_text());assert h(Path(z3['observed_live_grandchild']['exe']))==z3['actual_z3_sha256']
rows=[];inodes=set()
for r in audit['rows']:
 kind=r['config'];p=G/kind;d=json.loads((p/'driver.json').read_text());memo=d['memo_copy'];src=ROOT/memo['source'];dest=p/'sail_smt_cache';raw=dest.read_bytes();ss=src.stat();ds=dest.stat()
 assert d['model_commit']==commit and d['exit_code']==0 and d['source_unchanged'] and d['model_files']==a['tracked_model_files'] and d['model_tree']==s['model_tree']
 assert d['memo_source_batch']=='model-e9d69d2' and d['memo_source_audit_sha256']==h(audit_path) and d['memo_compile_z3_sha256']==z3['actual_z3_sha256']
 assert src==OLD/kind/'sail_smt_cache' and (ss.st_dev,ss.st_ino)!=(ds.st_dev,ds.st_ino) and (ds.st_dev,ds.st_ino) not in inodes
 inodes.add((ds.st_dev,ds.st_ino));assert not src.is_symlink() and not dest.is_symlink()
 assert h(src)==r['sha256']==memo['source_sha256']==memo['copied_sha256']
 assert memo['output_sha256']==h(dest) and memo['source_unchanged'] and memo['distinct_inode'] and memo['source_records']==r['records']
 assert len(raw)%17==0 and set(raw[16::17])<={0,1,2,3}
 config='rv64d.json' if kind in ('ordinary-strict','rv64d_v128_e64') else kind+'.json';assert h(ROOT/'isla/ir/provenance'/config)==d['config_sha256']
 for key in ('sail_sha256','sail_version','plugin_sha256','driver_sha256'):assert d[key]==s[key]
 if kind=='ordinary-strict':cmd=d['command'];assert '--just-check' in cmd and 'SYMBOLIC' not in cmd
 else:
  assert d['command'][d['command'].index('--model')+1]==str(M)
  q=json.loads((p/'generation.json').read_text());cmd=q['command'];assert q['exit_code']==0 and q['model_commit']==commit
  assert all(q['model_files'][n]==v for n,v in d['model_files'].items())
  assert set(q['model_files'])-set(d['model_files'])<= {'sail_smt_cache'}
  assert h(p/(kind+'.ir'))==d['ir_sha256']==q['ir_sha256'];assert 'SYMBOLIC' in cmd and '-D' in cmd
 for opt in ('--strict-var','--strict-bitvector','--strict-exponentials','--all-modules'):assert opt in cmd
 assert cmd[cmd.index('--require-version')+1]=='0.20.1'
 assert cmd[cmd.index('--memo-z3-path')+1]==str(dest)
 rows.append({'config':kind,'exit_code':0,'memo_source_sha256':h(src),'memo_output_sha256':h(dest),'memo_output_records':len(raw)//17,'source_unchanged':True,'different_inode':True,'ir_sha256':d.get('ir_sha256'),'seconds':d['seconds']})
frozen=ROOT/'.worktree/sail-riscv-general-float-by-model-20261022';fs=json.loads((OLD/'source.json').read_text());assert subprocess.check_output(['git','-C',str(frozen),'rev-parse','HEAD'],text=True).strip()==fs['commit'];assert all(h(frozen/'model'/n)==v for n,v in fs['model_files'].items())
# Old214 generation IR assets are unchanged too.
old_signed=json.loads((O/'model-review.provenance-e9d69d2.json').read_text())
for row in old_signed['rows']:
 if row['ir_sha256']:assert h(OLD/row['config']/(row['config']+'.ir'))==row['ir_sha256']
report={'status':'PASS new strict provenance and memo copies','commit':commit,'model_tree':s['model_tree'],'model_files':166,'tool_files':149,'actual_sail_binary_sha256':a['tool_files'][a['actual_sail_binary']],'compile_z3_sha256':z3['actual_z3_sha256'],'source_manifest_sha256':h(G/'source.json'),'rows':rows,'frozen_e9_model_and_IR_unchanged':True,'scope':'普通/四SYMBOLIC严格生成来源及memo审计，不含CFG或动态签字'}
(O/'converged-provenance-review-20261103.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
