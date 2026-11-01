import subprocess,os,json,hashlib,time
from pathlib import Path
R=Path('/data1/baiyifan/workplace/isla-runner');D=R/'agents/explicit_branch_timeout_diagnosis_20261102';E=R/'agents/branch_ablation_official_z3_20261102'
manifest={'budget_note':'300 seconds diagnostic observation only; production clause and SMT budget remains 7200 seconds','runs':[]}
for i,(w,a) in enumerate((('flags-arithmetic','A'),('flags-arithmetic','B'),('sat','A'),('sat','B'))):
 d=D/(w+'-'+a);d.mkdir(exist_ok=True)
 env=os.environ.copy();env.update(LD_PRELOAD=str(D/'probe.so')+':'+str(E/'bin/seed_control.so'),ISLA_ABLATION_SEED='17',ISLA_ABLATION_SEED_LOG=str(d/'seed.log'),ISLA_QUERY_LOG=str(d/'queries.tsv'))
 cmd=['timeout','--signal=TERM','--kill-after=10s','300s','taskset','-c',str(100+i),str(E/'bin/isarch'),'-A',str(E/'inputs'/w/(a+'.ir')),'-C',str(E/'inputs'/w/'config.toml'),'-T','1','--tastic','qffp','--smt-timeout','7200s','solve-state','--clause='+('F_BIN_RM_TYPE_S' if w=='flags-arithmetic' else 'VFUNARY0')]
 with (d/'run.log').open('w') as f:p=subprocess.Popen(cmd,env=env,cwd=d,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 manifest['runs'].append({'workload':w,'arm':a,'pid':p.pid,'cpu':100+i,'command':cmd,'started_monotonic':time.monotonic(),'sha256':{str(q.relative_to(R)):hashlib.sha256(q.read_bytes()).hexdigest() for q in (E/'bin/isarch',E/'inputs'/w/(a+'.ir'),E/'inputs'/w/'config.toml',D/'probe.so')}})
(D/'launch.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
