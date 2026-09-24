from pathlib import Path
import subprocess,json,re,time,sys

from prepare import prepare

root=Path(__file__).resolve().parent
prepare(('base','new','history'))
if '--prepare-only' in sys.argv[1:]:
 print('基准测试输入已准备')
 raise SystemExit(0)

def run(kind,clause,rep):
 if (root/'results.jsonl').exists():
  previous=[json.loads(x) for x in (root/'results.jsonl').read_text().splitlines()]
  if any(x['kind']==kind and x['clause']==clause and x['rep']==rep for x in previous):return
 d=root/'runs'/f'{clause}-{rep}-{kind}';d.mkdir(parents=True,exist_ok=True)
 (d/'output').mkdir(exist_ok=True)
 args=[str(root/'isarch'),'-A',str(root/kind/'rv64d.ir'),'-C',str(root/'isa.toml'),'--verbose','--debug=fmlgcsra','--probe-all','--trace-all','-T','8','--timeout','60s','--smt-timeout','60s','--tastic','qfaufbv']
 if clause in ['MASKTYPEI','VREV8_V','VIMCTYPE']:args+=['--execution-limits-config',str(root/kind/(clause.lower()+'.toml'))]
 args+=['solve-state','--clause='+clause]
 (d/'command.json').write_text(json.dumps(args))
 start=time.monotonic()
 with (d/'run.log').open('w') as log:
  r=subprocess.run(['/usr/bin/time','-f','%e %U %S %M','-o',str(d/'time.txt'),'timeout','--signal=TERM','--kill-after=5s','60s',*args],cwd=d,stdout=log,stderr=subprocess.STDOUT)
 elapsed=time.monotonic()-start
 log=(d/'run.log').read_text(errors='replace')
 paths=re.findall(r'执行好一条路径，fork=(\d+)，ret_val=([^\n]+)',log)
 js=list((d/'output').glob('*.json'))
 result={'kind':kind,'clause':clause,'rep':rep,'exit':r.returncode,'wall':round(elapsed,3),'time':(d/'time.txt').read_text().strip(),'paths':len(paths),'success':sum('Retire_Success' in p[1] for p in paths),'fork_max':max([int(p[0]) for p in paths],default=0),'json_files':[str(p) for p in js],'errors':len(re.findall(r'SymbolicLength|panicked at|ExecError',log))}
 with (root/'results.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
 print(json.dumps(result),flush=True)
for clause in sys.argv[1:] or ['MOVETYPEV','MASKTYPEI','VREV8_V','VIMCTYPE']:
 for rep in range(3):
  for kind in (['base','new'] if rep%2==0 else ['new','base']):run(kind,clause,rep)
 run('history',clause,0)
