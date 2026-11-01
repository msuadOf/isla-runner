from pathlib import Path
import json,re,difflib,tomllib
root=Path('.worktree/runner-float/sail-riscv');out=Path('agents/special_control_restore_20261102/implementation');old=json.loads((out/'original.json').read_text());records=[]
for p in (root/'configs/isla/workarounds').glob('*.toml'):
 text=p.read_text();cfg=tomllib.loads(text)['execution_limits']
 for region in cfg.get('region_fork_limits',[]):
  rel=region['file']
  if rel not in old:continue
  a=old[rel].splitlines();b=(root/'model'/rel).read_text().splitlines();maps={}
  for block in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_matching_blocks():
   for i in range(block.size):maps[block.a+i+1]=block.b+i+1
  for endpoint in ('start','end'):
   key=endpoint+'_line';line=region[key];assert line in maps,(p,key,line)
   new=maps[line];text=re.sub(r'(?m)^'+key+r' = '+str(line)+r'$',key+' = '+str(new),text)
   text=re.sub(r'(?m)^(# Sail '+endpoint+r')\s+'+str(line)+r':',r'\g<1> '+str(new)+':',text)
   records.append({'config':p.name,'file':rel,'endpoint':endpoint,'old':line,'new':new,'line_text':a[line-1],'unchanged_text':a[line-1]==b[new-1]})
 p.write_text(text)
(out/'region-migration.json').write_text(json.dumps(records,indent=2))
