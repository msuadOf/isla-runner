#!/usr/bin/env python3
"""Read-only installation, regression, and exact Isla candidate-tree seal."""
import hashlib,json,os,re,stat,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[3];T=H.parents[1];V=T/'validation';ISLA=ROOT/'isla';BASE='42000be47596ec088623881d03c0eadc5cf0ba27'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
git=lambda *args:subprocess.check_output(['git','-C',str(ISLA),*args])
allowed={'rv64d.ir','rv32d.ir','ir/rv64d_v128_e64.ir','ir/rv64d_v256_e64.ir','ir/rv64d_v512_e64.ir','ir/provenance/manifest.json','test/float_ir/README.md','test/float_ir/check_special_semantic_branches.py','test/float_ir/run.py','test/float_ir/check_float_closure_branches.py'}
changed=set(git('diff','--name-only',BASE).decode().splitlines())|set(git('ls-files','--others','--exclude-standard').decode().splitlines());assert changed==allowed,(changed-allowed,allowed-changed)
objects={}
for item in git('ls-tree','-rz',BASE).split(b'\0'):
 if not item:continue
 meta,name=item.split(b'\t',1);mode,kind,oid=meta.decode().split();objects[name.decode()]=(mode,oid)
def tree_hash(files):
 root={}
 for path,value in files.items():
  parts=path.split('/');node=root
  for name in parts[:-1]:node=node.setdefault(name,{})
  node[parts[-1]]=value
 def digest(node):
  raw=b''
  for name,value in sorted(node.items(),key=lambda x:(x[0]+('/' if isinstance(x[1],dict) else '')).encode()):
   mode,oid=('40000',digest(value)) if isinstance(value,dict) else value
   raw+=mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(oid)
  return hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 return digest(root)
assert tree_hash(objects)==git('rev-parse',BASE+'^{tree}').decode().strip()
production=[]
for name,(mode,oid) in objects.items():
 if name.endswith('.rs') or name.endswith('Cargo.toml') or name.endswith('Cargo.lock') or name.startswith('.cargo/'):
  p=ISLA/name;data=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert blob==oid,name
  production.append(name)
file_rows=[]
for name in sorted(allowed):
 p=ISLA/name;data=p.read_bytes();mode=objects[name][0] if name in objects else ('100755' if p.stat().st_mode&stat.S_IXUSR else '100644')
 objects[name]=(mode,hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest());file_rows.append({'path':name,'sha256':sha(p),'git_mode':mode,'git_blob':objects[name][1]})
manifest=read(ISLA/'ir/provenance/manifest.json');installed=read(V/'integration/installed.json');assert manifest['model_commit']==installed['model_commit']=='0f7b8fbc6724103f91f929ef6918f123df75d6c9'
assert sha(ISLA/'ir/provenance/manifest.json')==installed['installed_manifest_sha256']==sha(V/'integration/candidate-manifest.json')
for artifact in manifest['artifacts']:
 for path in artifact['paths']:assert sha(ISLA/path)==artifact['sha256']
 for path,want in artifact['model_files'].items():assert sha(ROOT/installed['model_tree']/'model'/path)==want['sha256']
checks=read(V/'integration/float-ir-all-0f7b8fb/checks.json');assert len(checks)==26 and all(x['exit']==0 for x in checks)
configs=['rv64d','rv32d','rv64d_v128_e64','rv64d_v256_e64','rv64d_v512_e64'];expected={'build','migration-conflicts','nan-unbox-branches','explicit-semantic-branches','special-semantic-branches','float-closure-branches'}|{f'{c}-{stage}' for c in configs for stage in ['wrap','helpers','state','guard']};assert {x['label'] for x in checks}==expected
logs=[]
for c in checks:
 p=V/'integration/float-ir-all-0f7b8fb'/(c['label']+'.log');assert p.exists();logs.append({'label':c['label'],'sha256':sha(p)})
linked=[]
for kind in ['helpers','state']:
 binary=V/'integration/target/debug'/('float-ir-'+kind);ldd=subprocess.check_output(['ldd',str(binary)],text=True);log=H/('final-integration-'+kind+'-ldd.log');log.write_text(ldd)
 library=Path(re.search(r'libz3\.so\S*\s+=>\s+(\S+)',ldd)[1]);assert sha(library)=='899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970'
 linked.append({'kind':kind,'binary_sha256':sha(binary),'official_z3_sha256':sha(library),'ldd_log_sha256':sha(log)})
head=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
if head!=BASE:assert tree==tree_hash(objects) and git('rev-parse','HEAD^').decode().strip()==BASE
out={'scope':'Installed final IR/provenance plus all26 regression and content-tree seal; no new runtime isarch rebuild claimed','model_commit':manifest['model_commit'],'runtime_isla_source_commit':BASE,'runtime_isarch_sha256':'acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d','candidate_isla_tree_sha1':tree_hash(objects),'actual_isla_head':head,'actual_head_tree_sha1':tree,'exact_changed_files':file_rows,'production_rust_cargo_files_equal_runtime_commit':len(production),'installed_manifest_sha256':sha(ISLA/'ir/provenance/manifest.json'),'regression_checks_sha256':sha(V/'integration/float-ir-all-0f7b8fb/checks.json'),'regression_checks':len(checks),'logs':logs,'regression_binaries':linked,'prebuild_log_sha256':sha(V/'integration/runner-prebuild.log'),'launch_log_sha256':sha(V/'integration/float-ir-all-launch.log'),'pass':True}
(H/'final-integration-independent.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ['exact_changed_files','logs']})
