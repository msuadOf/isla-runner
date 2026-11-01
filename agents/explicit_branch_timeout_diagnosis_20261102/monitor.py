from pathlib import Path
import subprocess,sys,time,json,os
D=Path(__file__).resolve().parent
pids=[x['pid'] for x in json.loads((D/'dump-launch.json').read_text())]
started=time.monotonic()
while time.monotonic()-started<7350:
 subprocess.run([sys.executable,str(D/'summarize.py')],stdout=subprocess.DEVNULL,check=True)
 alive=[]
 for p in pids:
  try:
   s=Path(f'/proc/{p}/stat').read_text();alive.append(') Z ' not in s)
  except FileNotFoundError:alive.append(False)
 if not any(alive):break
 time.sleep(15)
(D/'monitor-finished.json').write_text(json.dumps({'finished_monotonic':time.monotonic(),'note':'raw query and fork logs retained; no formal benchmark results modified'},indent=2))
