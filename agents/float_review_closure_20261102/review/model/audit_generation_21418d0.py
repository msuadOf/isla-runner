#!/usr/bin/env python3
"""独立复核21418d0严格生成来源与每配置memo副本。"""
from pathlib import Path
from collections import Counter
import hashlib,json,subprocess
ROOT=Path.cwd(); O=ROOT/'agents/float_review_closure_20261102/review/model'; V=ROOT/'agents/float_review_closure_20261102/validation'; G=V/'generation/model-21418d0'; OLD=V/'generation/model-8ad5e8e'; M=ROOT/'.worktree/runner-float/sail-riscv'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((G/'independent-input-audit.json').read_text());s=json.loads((G/'source.json').read_text());prior=json.loads((OLD/'independent-input-audit.json').read_text());audit_path=O/'memo-cache-audit.json';audit=json.loads(audit_path.read_text());inputs_path=V/'inputs.model-21418d0-itrace.json';inputs=json.loads(inputs_path.read_text())
commit='21418d0b0d4942fae20061ed580ee04aff4a8a61'
assert a['model_commit']==s['commit']==inputs['model_commit']==commit
assert subprocess.check_output(['git','-C',str(M),'rev-parse','HEAD'],text=True).strip()==commit
assert len(a['tracked_model_files'])==166
for n,v in a['tracked_model_files'].items(): assert h(M/'model'/n)==v==s['model_files'][n],n
assert a['tool_files']==prior['tool_files'] and len(a['tool_files'])==149
for n,v in a['tool_files'].items():assert h(ROOT/n)==v,n
assert a['tool_ctime_precedes_generation_start'] and a['source_unchanged_now']
assert a['generation_start_source_manifest_sha256']==h(G/'source.json')
z3=json.loads((OLD/'compile-z3-audit.json').read_text()); assert h(Path(z3['observed_live_grandchild']['exe']))==z3['actual_z3_sha256']
rows=[];inodes=set()
for r in audit['rows']:
 kind=r['config'];p=G/kind;d=json.loads((p/'driver.json').read_text());memo=d['memo_copy'];src=ROOT/memo['source'];dest=p/'sail_smt_cache';raw=dest.read_bytes();ss=src.stat();ds=dest.stat()
 assert d['model_commit']==commit and d['exit_code']==0 and d['source_unchanged'] and d['model_files']==a['tracked_model_files']
 assert d['memo_source_batch']=='model-8ad5e8e' and d['memo_source_audit_sha256']==h(audit_path) and d['memo_compile_z3_sha256']==z3['actual_z3_sha256']
 assert src==OLD/kind/'sail_smt_cache' and (ss.st_dev,ss.st_ino)!=(ds.st_dev,ds.st_ino) and (ds.st_dev,ds.st_ino) not in inodes
 inodes.add((ds.st_dev,ds.st_ino));assert not src.is_symlink() and not dest.is_symlink()
 assert h(src)==r['sha256']==memo['source_sha256']==memo['copied_sha256']==memo['output_sha256']==h(dest)
 assert memo['source_unchanged'] and memo['distinct_inode'] and memo['source_records']==r['records']
 # Binary records are digest[16] + result tag; unique-integer tag 4 additionally has an integer payload.
 assert len(raw)%17==0 and len(raw)//17==r['records']
 tags=Counter(raw[i] for i in range(16,len(raw),17));assert set(tags)<={0,1,2,3} and {str(k):v for k,v in tags.items()}=={k:v for k,v in r['result_tags'].items() if v}
 config='rv64d.json' if kind in ('ordinary-strict','rv64d_v128_e64') else kind+'.json'
 assert h(ROOT/'isla/ir/provenance'/config)==d['config_sha256']
 for key in ('sail_sha256','sail_version','plugin_sha256','driver_sha256'):assert d[key]==s[key]
 if kind=='ordinary-strict':cmd=d['command'];assert '--just-check' in cmd and 'SYMBOLIC' not in cmd
 else:
  q=json.loads((p/'generation.json').read_text());cmd=q['command'];assert q['exit_code']==0 and q['model_commit']==commit and all(q['model_files'].get(n)==v for n,v in d['model_files'].items()) and set(q['model_files'])-set(d['model_files'])=={'sail_smt_cache'}
  assert h(p/(kind+'.ir'))==d['ir_sha256']==q['ir_sha256'];assert 'SYMBOLIC' in cmd and '-D' in cmd
 for opt in ('--strict-var','--strict-bitvector','--strict-exponentials','--all-modules'):assert opt in cmd
 assert cmd[cmd.index('--require-version')+1]=='0.20.1'
 rows.append({'config':kind,'exit_code':0,'memo_sha256':h(dest),'records':len(raw)//17,'source_unchanged':True,'different_inode':True,'ir_sha256':d.get('ir_sha256'),'seconds':d['seconds']})
irs={}
for n,r in inputs['irs'].items():
 p=Path(r['path']);p=p if p.is_absolute() else ROOT/p;assert h(p)==r['sha256'];irs[n]=r['sha256']
assert len(irs)==5 and irs['rv64-default']==irs['rv64-v128']
report={'status':'PASS provenance and independent memo copies','model_commit':commit,'inputs_sha256':h(inputs_path),'model_files':166,'tool_files':149,'actual_sail_binary_sha256':a['tool_files'][a['actual_sail_binary']],'compile_z3_sha256':z3['actual_z3_sha256'],'rows':rows,'five_ir_hashes':irs,'scope':'严格生成与来源/memo复用审计；不包含动态验证或永久CFG检查器签字。'}
(O/'memo-reuse-21418d0.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
