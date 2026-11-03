#!/usr/bin/env python3
"""Verify final315 ended before shared clone integration and preserve source origin."""
import datetime,hashlib,json,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[3];T=H.parents[1];run=T/'validation/exceptions/runs-model-converged-0f7b8fbc-itrace'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
summary=read(run/'summary.json');assert summary['count']==summary['completed']==summary['pass']==315
resultfiles=list((run/'runs').glob('*/result.json'));assert len(resultfiles)==315
last=max(p.stat().st_mtime for p in resultfiles);summary_time=(run/'summary.json').stat().st_mtime;assert last<=summary_time
rows=[]
for rel,new in [('.worktree/runner-float/isla','591693df2bc32019ea300511509ed683df09522e'),('.worktree/runner-float/sail-riscv','0f7b8fbc6724103f91f929ef6918f123df75d6c9'),('isla','591693df2bc32019ea300511509ed683df09522e')]:
 tree=ROOT/rel;g=Path(subprocess.check_output(['git','-C',str(tree),'rev-parse','--absolute-git-dir'],text=True).strip());entries=[]
 for line in (g/'logs/HEAD').read_text().splitlines():
  if '\t' not in line:continue
  fields,msg=line.split('\t',1);parts=fields.split()
  if parts[1]==new:entries.append((int(parts[-2]),parts[0],msg))
 assert entries;when,old,msg=entries[-1];assert summary_time<when,(rel,summary_time,when)
 rows.append({'clone':rel,'previous_head':old,'integrated_head':new,'reflog_epoch_s':when,'reflog_utc':datetime.datetime.fromtimestamp(when,datetime.timezone.utc).isoformat(),'seconds_after_final315_summary':round(when-summary_time,6),'operation':msg})
launch=read(run/'launch.json');assert launch['isla_commit']=='42000be47596ec088623881d03c0eadc5cf0ba27'
assert sha(run/'isarch')==launch['frozen_hashes']['binary'] and sha(run/'base.ir')==launch['frozen_hashes']['ir']
out={'scope':'Source/checkout temporal boundary for final315; no historical source-manifest relabel','final315_summary_sha256':sha(run/'summary.json'),'last_job_result_epoch_s':last,'summary_epoch_s':summary_time,'summary_utc':datetime.datetime.fromtimestamp(summary_time,datetime.timezone.utc).isoformat(),'launch_epoch_s':(run/'launch.json').stat().st_mtime,'launch_runtime_isla_commit':launch['isla_commit'],'all315_completed_before_any_listed_clone_head_change':True,'affected_by_clone_fast_forward_jobs':[],'rerun_due_to_clone_fast_forward_needed':False,'frozen_binary_and_base_ir_hashes_match_launch':True,'clone_transitions':rows,'pass':True}
(H/'final-execution-timeline-independent.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
