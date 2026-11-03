#!/usr/bin/env python3
"""独立审查新IR的来源、独立NaN角色和真实活动gate。"""
from pathlib import Path
import hashlib,json,re,shlex,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
MODEL=ROOT/'.worktree/runner-float/sail-riscv'
GEN=HERE.parent/'implementation/generation'
KINDS=['rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def functions(text):return dict(re.findall(r'(?ms)^fn ([^(\n]+)\([^\n]*\) \{\n(.*?)^\}',text))
def mask_sites():
 diff=subprocess.check_output(['git','-C',str(MODEL),'diff','fd71c9a','HEAD','--unified=0','--','model'],text=True)
 f=None;line=None;sites=[]
 for s in diff.splitlines():
  if s.startswith('+++ b/'):f=s[6:]
  elif s.startswith('@@ '):line=int(re.search(r'\+(\d+)',s)[1])
  elif s.startswith('+'):
   if re.match(r'\+\s*if mask\[i\] == 0b1 then \{',s):
    content=(MODEL/f).read_text();lines=content.splitlines();depth=0;end=None
    for i in range(line-1,len(lines)):
     depth+=lines[i].count('{')-lines[i].count('}')
     if depth==0:end=i+1;break
    assert end
    prior='\n'.join(lines[:line]);name=re.findall(r'function clause execute\s*\(?([A-Za-z0-9_]+)',prior)[-1]
    body='\n'.join(lines[line:end-1]);calls=re.findall(r'\b((?:fp_\w+_pure|riscv_f\w+|riscv_[ui]\w+ToF\w+|bf16_to_f32))\(',body)
    sites.append({'name':name,'source':f.removeprefix('model/'),'start':line,'end':end,'source_calls':calls})
   line+=1
  elif s.startswith('-'):pass
  elif line is not None:line+=1
 assert len(sites)==20,len(sites)
 return sites

def inspect(ir,sites):
 text=ir.read_text();fs=functions(text);files=shlex.split(re.search(r'(?m)^files (.*)$',text)[1]);ins=[s.strip() for s in fs['zexecute'].splitlines() if s.strip()]
 def successors(pc):
  s=ins[pc];m=re.search(r'\bgoto (\d+)',s)
  if s.startswith('jump '):return [pc+1,int(m[1])]
  if s.startswith('goto '):return [int(m[1])]
  if s=='end;':return []
  return [pc+1] if pc+1<len(ins) else []
 def reachable(start,stop):
  seen=set();pending=[start]
  while pending:
   pc=pending.pop()
   if pc in seen or pc==stop:continue
   seen.add(pc);pending.extend(successors(pc))
  return seen
 gates=[]
 for site in sites:
  sid=files.index(site['source']);location=re.compile(r'`'+str(sid)+r' (\d+):\d+-(\d+):\d+;')
  branches=[pc for pc,s in enumerate(ins) if s.startswith('jump ') and (m:=location.search(s)) and int(m[1])==site['start'] and int(m[2])==site['end']]
  assert len(branches)==1,(site,branches)
  branch=branches[0];active=int(re.search(r'goto (\d+)',ins[branch])[1]);assert ins[branch+2].startswith('goto ')
  merge=int(re.search(r'goto (\d+)',ins[branch+2])[1]);on=reachable(active,merge);off=reachable(branch+1,merge);bypass=reachable(0,branch)
  calls=[]
  for pc,s in enumerate(ins):
   m=location.search(s)
   if m and site['start']<int(m[1])<site['end'] and re.search(r'= z(?:fp_\w+_pure|riscv_f\w+|riscv_[ui]\w+ToF\w+|bf16_to_f32)\(',s):calls.append(pc)
  assert len(calls)==len(site['source_calls']),(site,len(calls))
  assert all(pc in on and pc not in off and pc not in bypass for pc in calls),site
  assert calls,site
  gates.append(dict(site,branch_pc=branch,active_pc=active,merge_pc=merge,operation_count=len(calls),operation_calls=[ins[pc] for pc in calls]))
 helper=fs['zieee_operand_invalid'];assert len(re.findall(r'(?m)^\s*jump ',helper))==2
 operand_calls={}
 for width in [16,32,64]:
  for op,nargs in [('eq',2),('lt',2),('add',2),('sub',2),('mul',2),('div',2),('sqrt',1),('fma',3)]:
   name='zieee_'+op+str(width)+'_exceptions';b=fs[name];calls=re.findall(r'= zieee_operand_invalid\([^\n]*',b)
   assert len(calls)==nargs,(name,calls)
   operand_calls[name]=calls
 assert len(re.findall(r'= zfp32_fma\(',fs['zriscv_f32MulAdd']))==1
 assert not re.search(r'= zfp32_(?:add|mul)\(',fs['zriscv_f32MulAdd'])
 return {'ir_sha256':sha(ir),'mask_gates':gates,'operand_calls':operand_calls,'operand_helper_jumps':2,'f32_fma_single_call':True,'function_count':len(fs)}

def normalized_functions(text):
 result={}
 for name,formals,body in re.findall(r'(?ms)^fn ([^(\n]+)\(([^\n]*)\) \{\n(.*?)^\}',text):
  body=re.sub(r'`\d+(?: \d+:\d+(?:-\d+:\d+)?)?','',body)
  body=re.sub(r'([\w./-]+\.sail):\d+\.\d+-\d+\.\d+',r'\1:LOC',body)
  replacements={formal.strip():'__arg'+str(i) for i,formal in enumerate(formals.split(',')) if formal.strip()}
  def rename(match):
   token=match.group()
   if token not in replacements:replacements[token]='__local'+str(len(replacements))
   return replacements[token]
  tokens='|'.join(re.escape(token) for token in replacements)
  pattern=r'(?<![A-Za-z0-9_$])(?:zz[0-9]+'+('|' + tokens if tokens else '')+r')(?![A-Za-z0-9_$])'
  result[name]=re.sub(pattern,rename,body)
 return result


def main():
 kinds=sys.argv[1:] or KINDS;sites=mask_sites();out={'configurations':{},'scope':'来源与静态CFG核查，不替代动态Clause'}
 expected=json.loads((HERE/'source-evidence.json').read_text())
 commit=subprocess.check_output(['git','-C',str(MODEL),'rev-parse','HEAD'],text=True).strip()
 assert commit==expected['model_commit']
 assert not subprocess.check_output(['git','-C',str(MODEL),'status','--porcelain'])
 assert all(sha(MODEL/f)==digest for f,digest in expected['source_sha256'].items())
 source_sets=[]
 out['model_commit']=commit
 out['reviewed_patch_sha256']=hashlib.sha256(subprocess.check_output(['git','-C',str(MODEL),'diff','fd71c9a',commit])).hexdigest()
 assert out['reviewed_patch_sha256']==expected['reviewed_patch_sha256']
 for kind in kinds:
  directory=GEN/kind;ir=directory/(kind+'.ir');out['configurations'][kind]=inspect(ir,sites)
  record=json.loads((directory/'generation.json').read_text());driver=json.loads((directory/'driver.json').read_text())
  assert record['exit_code']==driver['exit_code']==0 and driver['source_unchanged']
  assert record['model_commit']==driver['model_commit']==commit
  assert record['model_files']==driver['model_files']
  assert all(sha(MODEL/'model'/f)==digest for f,digest in record['model_files'].items())
  source_sets.append(record['model_files'])
  command=record['command']
  for flag in ['-isla','SYMBOLIC','--strict-var','--strict-bitvector','--strict-exponentials','--all-modules']:assert flag in command
  for flag,key in [('--config','config_sha256'),('-plugin','plugin_sha256')]:assert sha(Path(command[command.index(flag)+1]))==record[key]==driver[key]
  launcher=Path(command[0]);assert sha(launcher)==record['sail_launcher_sha256']==driver['sail_launcher_sha256']
  assert sha(ir)==record['ir_sha256']==driver['ir_sha256']
  tools={'launcher':sha(launcher),'binary':sha(launcher.parent/'_build/install/default/bin/sail'),'jib_compile':sha(launcher.parent/'src/lib/jib_compile.ml')}
  filetable=shlex.split(re.search(r'(?m)^files (.*)$',ir.read_text())[1]);stdlib={f:sha(Path(f)) for f in filetable if f.startswith('/') and '/lib/' in f}
  old_ir=ROOT/'agents/explicit_branch_restore_20261102/implementation/generation'/kind/(kind+'.ir')
  before=normalized_functions(old_ir.read_text());after=normalized_functions(ir.read_text())
  changed=sorted(name for name in before.keys()|after.keys() if before.get(name)!=after.get(name))
  allowed={'zexecute','zieee_operand_invalid','zbf16_to_f32'}
  allowed.update('zieee_'+op+str(w)+'_exceptions' for op in ['eq','lt','add','sub','mul','div','sqrt','fma','round'] for w in [16,32,64])
  allowed.update('zieee_'+name for name in ['convert32_to_16_exceptions','convert64_to_16_exceptions','convert64_to_32_exceptions','widen16_to_32_exceptions','widen16_to_64_exceptions','widen32_to_64_exceptions','bf16_from_f32_exceptions','rod32_to_16','rod64_to_32'])
  allowed.update('zriscv_f16'+name for name in ['Add','Sub','Mul','Div','MulAdd','Sqrt','roundToInt','ToF32','ToF64'])
  allowed.update(['zriscv_f64_result_bits','zriscv_f64ToF16','zriscv_f64ToF32','zriscv_f32ToF64','zriscv_f32ToF16','zriscv_f32ToBF16'])
  assert set(changed)==allowed,(kind,sorted(set(changed)-allowed),sorted(allowed-set(changed)))
  out['configurations'][kind]['normalized_changed_functions_from_fd71c9a']=changed
  out['configurations'][kind].update(model_source_count=len(record['model_files']),command=command,toolchain_sha256=tools,stdlib_sha256=stdlib,config_sha256=record['config_sha256'],plugin_sha256=record['plugin_sha256'])
  print('PASS',kind,20,'活动gate，24个异常helper全部源角色调用，单次f32_fma')
 assert all(source==source_sets[0] for source in source_sets)
 ordinary=json.loads((GEN/'ordinary-strict/driver.json').read_text())
 assert ordinary['exit_code']==0 and ordinary['source_unchanged'] and ordinary['model_files']==source_sets[0]
 assert 'SYMBOLIC' not in ordinary['command'] and '--just-check' in ordinary['command']
 out['ordinary_strict']={'exit_code':0,'source_count':len(source_sets[0])}
 (HERE/'ir-cfg-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
