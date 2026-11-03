#!/usr/bin/env python3
"""Read-only independent asset, manifest, and committed-tree hash binding."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_tree(entry,commit):
 tree=ROOT/entry['path'];manifest=ROOT/entry['manifest']['path'];assert sha(manifest)==entry['manifest']['sha256'];d=read(manifest);assert d['commit']==commit
 assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==commit
 objects={}
 raw=subprocess.check_output(['git','-C',str(tree),'ls-tree','-rz',commit])
 for item in raw.split(b'\0'):
  if not item:continue
  meta,path=item.split(b'\t',1);mode,kind,oid=meta.decode().split()
  if kind=='blob':objects[path.decode()]=(mode,oid)
 for name,want in d['files'].items():
  path=tree/name;data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==want,(name,'working file')
  mode,oid=objects[name];blob=os.readlink(path).encode() if mode=='120000' else data
  got=hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()
  assert got==oid,(name,'committed blob')
 return {'commit':commit,'manifest_sha256':sha(manifest),'manifest_scope':d.get('scope'),'verified_files':len(d['files']),'unlisted_blobs':len(set(objects)-set(d['files']))}

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();inputs=a.inputs.resolve(strict=True);d=read(inputs)
 assert d['model_commit']==a.model and d['threads']==1 and d['seed']==17 and d['tactic']=='qffp'
 assets=[]
 def walk(x,prefix=''):
  if isinstance(x,dict):
   if set(['path','sha256'])<=x.keys():
    q=Path(x['path']);q=q if q.is_absolute() else ROOT/q
    assert sha(q)==x['sha256'],prefix
    assets.append({'entry':prefix,'sha256':x['sha256']})
   for k,v in x.items():walk(v,prefix+'.'+k)
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,prefix+f'[{i}]')
 walk(d)
 trees={k:check_tree(d[k],d[c]) for k,c in [('model_tree','model_commit'),('isla_tree','isla_commit')]}
 out={'scope':'Independent frozen assets and source manifests; no generated-run PASS inferred','inputs_sha256':sha(inputs),'model_commit':d['model_commit'],'isla_commit':d['isla_commit'],'verified_assets':assets,'source_trees':trees,'pass':True}
 a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
