#!/usr/bin/env python3
"""Exercise e9 scheduler with isolated fake jobs; never execute Isla."""
import contextlib,fcntl,hashlib,importlib.util,io,json,tempfile,time
from pathlib import Path
from types import SimpleNamespace
H=Path(__file__).resolve().parent
SOURCE=H.parents[1]/'validation/full_batch/e9/scheduler.py'
spec=importlib.util.spec_from_file_location('closure_scheduler_e9_audit',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REAL_SLEEP=time.sleep
m.ps_snapshot=lambda:([],[])
m.memory_available_kb=lambda:10**12
class EarlyStop(Exception):pass

def scenario(root,name,jobs,mode='normal'):
 b=root/name;b.mkdir();m.HERE=b/'fullbatch';m.HERE.mkdir();m.VALIDATION=b
 inp=b/'inputs.json';inp.write_text('{}');affected=b/'affected.json';affected.write_text('{}')
 harness=b/'fake_harness.py'
 harness.write_text('''import argparse,json,sys,time\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument('--inputs');p.add_argument('--batch');p.add_argument('--job');p.add_argument('--cpu');a=p.parse_args();base=Path(__file__).parent;plan=json.loads((base/'fullbatch/batches'/a.batch/'plan.json').read_text());dest=base/'runs'/a.batch/a.job;dest.mkdir(parents=True);out=dest/'result.json'\nif a.job=='bad_json':out.write_text('{')\nelse:\n r={'job':a.job,'batch':a.batch,'input_manifest_sha256':plan['inputs_sha256'],'affected_manifest_sha256':plan['affected_manifest_sha256'],'scope':'affected' if a.job in plan['affected_clauses'] else 'compatibility','model_commit':'model','isla_commit':'isla','domain':'full','seed':17,'pass':True,'exit_code':0,'gen_count':1,'elapsed_s':0.01,'summary':{'status':'finished'}}\n if a.job=='bad_identity':r['job']='wrong'\n if a.job=='bad_affected':r['affected_manifest_sha256']='wrong'\n if a.job=='bad_scope':r['scope']='wrong'\n time.sleep(0.08)\n out.write_text(json.dumps(r))\nif a.job=='drift':Path(__file__).write_text(Path(__file__).read_text()+'\\n# drift\\n')\nif a.job=='bad_exit':sys.exit(9)\n''')
 harness.write_text(harness.read_text().replace('time.sleep(0.08)','time.sleep(0.15 if a.job=="good2" else 0.08)'))
 harness.write_text(harness.read_text().replace(' time.sleep(0.15', ' while (base/"hold-jobs").exists() and not (base/("release-"+a.job)).exists():time.sleep(0.005)\n time.sleep(0.15'))
 if mode=='growth':(b/'hold-jobs').touch()
 m.HARNESS=harness;batch='fake';bd=m.HERE/'batches'/batch;bd.mkdir(parents=True)
 plan={'inputs':str(inp),'inputs_sha256':m.digest(inp),'harness_sha256':m.digest(harness),'affected_manifest':str(affected),'affected_manifest_sha256':m.digest(affected),'model_commit':'model','isla_commit':'isla','ordered_jobs':jobs,'count':len(jobs),'affected_clauses':jobs[:2],'affected_count':2,'compatibility_count':len(jobs)-2,'cpus':[0,1],'cpu_detail':[{'siblings':[0]},{'siblings':[1]}]}
 (bd/'plan.json').write_text(json.dumps(plan));(bd/'control.json').write_text('{"max_parallel":2}')
 state={'free':0 if mode=='disk_empty' else 40*1024**3 if mode=='growth' else 10**18,'guard_seen':False,'guard_with_active':False,'sleep_count':0,'samples':{}}
 m.shutil.disk_usage=lambda _:SimpleNamespace(free=state['free'])
 def sample(batch,job):
  n=state['samples'].get(job,0)+1;state['samples'][job]=n
  return n*1024**2 if mode=='growth' else 0
 m.active_output_bytes=sample
 def sleep(_):
  state['sleep_count']+=1
  assert state['sleep_count']<1000,'mock failed to terminate'
  r=json.loads((bd/'summary.json').read_text())
  if r['disk_guard']:
   state['guard_seen']=True;state['guard_with_active']|=bool(r['running'])
   assert r['queued']>0 and r['blocked']==0 and r['task_conservation_valid']
   if mode=='disk_empty':assert r['queued']==len(jobs) and r['running']==r['completed']==0
   state['free']=10**18
   if mode=='growth':
    for job in jobs:(b/('release-'+job)).touch()
  if mode=='growth' and state['samples'].get('good1',0)>=3:(b/'release-good1').touch()
  REAL_SLEEP(.01)
 m.time.sleep=sleep
 with contextlib.redirect_stdout(io.StringIO()):m.supervise(batch)
 r=json.loads((bd/'summary.json').read_text())
 assert r['task_conservation_valid'] and r['task_conservation_total']==len(jobs)
 if mode=='drift':assert r['blocked']>0 and not r['batch_complete'] and r['completed']+r['blocked']==len(jobs)
 else:
  assert r['completed']==len(jobs) and r['batch_complete']
  expected_failed=sum(x.startswith('bad_') for x in jobs);assert r['failed']==expected_failed and r['passed']==len(jobs)-expected_failed
 if mode.startswith('disk_') or mode=='growth':assert state['guard_seen'],(mode,state,r.get('disk_projected_job_bytes'),r.get('peak_output_growth_bytes_per_s'))
 if mode=='growth':assert state['guard_with_active'],'growth guard never exercised with active jobs'
 return {'scenario':name,'total':len(jobs),'completed':r['completed'],'passed':r['passed'],'failed':r['failed'],'blocked':r['blocked'],'batch_complete':r['batch_complete'],'disk_guard_seen':state['guard_seen'],'disk_guard_with_active':state['guard_with_active'],'conservation':True}

def main():
 inputs=H.parents[1]/'validation/inputs.model-e9d69d2-itrace.json'
 data,jobs,affected,compatible,path,affected_sha=m.read_jobs(inputs)
 assert (len(jobs),len(affected),len(compatible))==(77,64,13)
 assert data['model_commit']=='e9d69d2f28586c089244c8e37ee4c904c5114458' and data['isla_commit']=='42000be47596ec088623881d03c0eadc5cf0ba27'
 with tempfile.TemporaryDirectory(prefix='scheduler-e9-review-',dir=H) as tmp:
  root=Path(tmp);lock=root/'locked/batches/fake';lock.mkdir(parents=True);m.HERE=lock.parents[1]
  with (lock/'supervisor.lock').open('a') as handle:
   fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
   try:m.supervise('fake')
   except RuntimeError:locked=True
   else:raise AssertionError('duplicate supervisor accepted')
  control=root/'control.json';control.write_text('{"max_parallel":16}');assert m.read_control(control)==16
  control.write_text('{"max_parallel":17}')
  try:m.read_control(control)
  except ValueError:limit=True
  else:raise AssertionError('parallel 17 accepted')
  rows=[scenario(root,'failure-accounting',['bad_json','bad_exit','bad_identity','bad_affected','bad_scope','good']),scenario(root,'drift-blocking',['drift','good1','good2','good3','good4'],'drift'),scenario(root,'disk-empty-resume',['good1','good2','good3'],'disk_empty'),scenario(root,'growth-pause-resume',['good1','good2','good3'],'growth')]
 out={'scope':'Mock scheduler failure/identity/disk accounting plus real read-only input closure; zero Isla or real Clause executions','scheduler_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'inputs_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),'affected_manifest_sha256':affected_sha,'real_job_counts':[len(jobs),len(affected),len(compatible)],'duplicate_supervisor_refused':locked,'max_parallel_16_accepted_17_rejected':limit,'checks':rows}
 (H/'scheduler-e9-independent.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
