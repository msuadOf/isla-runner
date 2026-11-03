#!/usr/bin/env python3
"""Check migration manifests/links, all sizes, and all non-trace SHA values."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
BASE=Path('/home/baiyifan/.cache/isla-runner-float-closure-20261103')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
prior=read(H/'historical-full77-failures-independent.json');rows=[]
for old in prior['batches']:
 batch=old['batch'];m=BASE/(batch+'.migration.json');manifest=BASE/(batch+'.sha256-manifest.json');moved=read(m);data=read(manifest);logical=ROOT/moved['original_path'];archive=Path(moved['archive_path'])
 assert logical.is_symlink() and logical.resolve()==archive.resolve() and Path(moved['symlink_target']).resolve()==archive.resolve()
 assert moved['source_and_destination_sha256_size_equal'] and moved['verified_file_count']==data['file_count'] and moved['verified_bytes']==data['total_file_bytes']
 actual={str(p.relative_to(archive)) for p in archive.rglob('*') if p.is_file()};assert actual==set(data['files']) and len(actual)==data['file_count']
 hashed=0;trace=0
 for rel,want in data['files'].items():
  p=logical/rel;assert p.stat().st_size==want['size']
  if '/output/trace/' in '/'+rel:trace+=1
  else:assert sha(p)==want['sha256'];hashed+=1
 for fail in old['failures']:assert sha(logical/fail['job']/'result.json')==fail['result_sha256']
 assert sum(v['size'] for v in data['files'].values())==data['total_file_bytes']
 rows.append({'batch':batch,'migration_record_sha256':sha(m),'source_manifest_sha256':sha(manifest),'logical_path_symlink_correct':True,'files_and_sizes_checked':len(actual),'total_file_bytes':data['total_file_bytes'],'all_non_trace_files_sha256_verified':hashed,'trace_files_size_and_presence_only':trace,'pre_migration_failed_results_sha256_preserved':len(old['failures'])})
out={'scope':'Migration links/exact file sets/all sizes/all metadata+JSON+logs SHA checked; large trace SHA already checked by migration owner, not rehashed here','batches':rows,'pass':True}
(H/'historical-migration-independent.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
