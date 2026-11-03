#!/usr/bin/env python3
"""Exercise scheduler failure accounting with fake jobs, never run Isla."""
import fcntl,hashlib,importlib.util,json,tempfile
from pathlib import Path
import time
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]/'validation/full_batch/scheduler.py'
spec=importlib.util.spec_from_file_location('closure_scheduler_audit',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REAL_SLEEP=time.sleep
m.time.sleep=lambda _:REAL_SLEEP(.01)
m.ps_snapshot=lambda:([],[])
m.memory_available_kb=lambda:10**12

def scenario(root,name,jobs,drift=False):
    base=root/name;base.mkdir();m.HERE=base/'fullbatch';m.HERE.mkdir();m.VALIDATION=base
    inp=base/'inputs.json';inp.write_text('{}')
    affected=base/'affected.json';affected.write_text('{}');m.AFFECTED=affected
    harness=base/'fake_harness.py'
    harness.write_text('''import argparse,json,sys\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument('--inputs');p.add_argument('--batch');p.add_argument('--job');p.add_argument('--cpu');a=p.parse_args();base=Path(__file__).parent;plan=json.loads((base/'fullbatch/batches'/a.batch/'plan.json').read_text());dest=base/'runs'/a.batch/a.job;dest.mkdir(parents=True);out=dest/'result.json'\nif a.job=='bad_json':out.write_text('{')\nelse:\n r={'job':a.job,'batch':a.batch,'input_manifest_sha256':plan['inputs_sha256'],'model_commit':'model','isla_commit':'isla','domain':'full','seed':17,'pass':True,'exit_code':0,'gen_count':1,'elapsed_s':0.01,'summary':{'status':'finished'}}\n if a.job=='bad_identity':r['job']='wrong'\n out.write_text(json.dumps(r))\nif a.job=='drift':Path(__file__).write_text(Path(__file__).read_text()+'\\n# drift\\n')\nif a.job=='bad_exit':sys.exit(9)\n''')
    m.HARNESS=harness;batch='fake';batchdir=m.HERE/'batches'/batch;batchdir.mkdir(parents=True)
    plan={'inputs':str(inp),'inputs_sha256':m.digest(inp),'harness_sha256':m.digest(harness),'affected_manifest_sha256':m.digest(affected),'model_commit':'model','isla_commit':'isla','ordered_jobs':jobs,'count':len(jobs),'affected_clauses':jobs[:2],'affected_count':2,'compatibility_count':len(jobs)-2,'cpus':[0,1],'cpu_detail':[{'siblings':[0]},{'siblings':[1]}]}
    (batchdir/'plan.json').write_text(json.dumps(plan));(batchdir/'control.json').write_text('{"max_parallel":2}')
    m.supervise(batch);result=json.loads((batchdir/'summary.json').read_text())
    assert result['task_conservation_valid'] and result['task_conservation_total']==len(jobs)
    if drift:
        assert result['blocked']>0 and not result['batch_complete'] and result['completed']+result['blocked']==len(jobs),result
    else:
        assert result['completed']==4 and result['passed']==1 and result['failed']==3 and result['batch_complete'],result
        for key in ('bad_json','bad_exit','bad_identity'):assert not result['results'][key]['pass'],result
    return {'name':name,'total':len(jobs),'completed':result['completed'],'passed':result['passed'],'failed':result['failed'],'blocked':result['blocked'],'conservation':result['task_conservation_valid'],'batch_complete':result['batch_complete']}

def main():
    with tempfile.TemporaryDirectory(prefix='float-scheduler-review-') as tmp:
        lockdir=Path(tmp)/'locktest'/'batches'/'fake';lockdir.mkdir(parents=True);m.HERE=lockdir.parents[1]
        with (lockdir/'supervisor.lock').open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:m.supervise('fake')
            except RuntimeError:locked=True
            else:raise AssertionError('duplicate supervisor accepted')
        result=[scenario(Path(tmp),'failure-accounting',['bad_json','bad_exit','bad_identity','good']),scenario(Path(tmp),'drift-blocking',['drift','good1','good2','good3','good4'],True)]
    data={'scope':'Mock job scheduler control tests only; zero Isla or real Clause executions','scheduler_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'duplicate_supervisor_refused':locked,'checks':result}
    (HERE/'scheduler-independent.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
if __name__=='__main__':main()
