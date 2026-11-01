#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json,time,re
D=Path(__file__).resolve().parent
out={}
for d in D.iterdir():
 p=d/'queries.tsv'
 if not p.is_file():continue
 rows=[x.split('\t') for x in p.read_text().splitlines()];b=[x for x in rows if x[0]=='begin'];e=[x for x in rows if x[0]=='end'];forks=Counter(re.findall(r'\[[^\n]*?\]\[FORK\]: ([^\n]+)',(d/'run.log').read_text()))
 out[d.name]={'checks_begun':len(b),'checks_finished':len(e),'check_kinds':dict(Counter(x[2] for x in b)),'completed_z3_s':sum(float(x[5]) for x in e),'max_completed_check_s':max((float(x[5]) for x in e),default=0),'last_begin_monotonic':float(b[-1][4]) if b else None,'pending_query':int(b[-1][1]) if len(b)>len(e) else None,'fork_events':sum(forks.values()) if ('dump' in d.name or 'forks' in d.name or 'inactive-zero' in d.name) else None,'fork_events_by_location':dict(forks),'explicit_saturation_forks':sum(n for s,n in forks.items() if 'vext_fp_utils_insts.sail 544:' in s),'jsons':[]}
 for p in (d/'output').glob('*.json'):
  x=json.loads(p.read_text());out[d.name]['jsons'].append({'path':str(p.relative_to(D)),'gen':len(x.get('gen',[])),'summary':x.get('summary')})
(D/'snapshot.json').write_text(json.dumps({'monotonic':time.monotonic(),'runs':out},indent=2))
print(json.dumps(out,indent=2))
