#!/usr/bin/env python3
"""新模型特殊值与活动 lane 的定向验收；不是全域性能或全路径证明。"""
from pathlib import Path
from collections import Counter
import concurrent.futures,hashlib,json,os,re,shutil,subprocess,threading,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
GEN=HERE.parent/'implementation/generation/rv64d_v128_e64'
CPUS=[34,35,37,38,39,40,41,42]
BIN=HERE/'bin/isarch';BASE=ROOT/'isla/configs/riscv64_difftest_fd.toml'
ORACLE=ROOT/'.tmp/unified-backend-crosscheck/oracle-build/oracle'
LOCK=threading.Lock();STATE={'state':'preparing','jobs':{}}
FORMATS={'H':(16,5,10,0x3c00,0x7c01,0x7e13),'S':(32,8,23,0x3f800000,0x7f800001,0x7fc00013),'D':(64,11,52,0x3ff0000000000000,0x7ff0000000000001,0x7ff8000000000013)}
PARTIAL=('errors','execution-timeouts','smt-timeouts','unfinished-paths','omitted-cases','model-query-timeouts','pending-batches','sampled-paths')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n');tmp.replace(p)
def snapshot():
 with LOCK:
  STATE['updated_epoch']=time.time();write(HERE/'summary.json',STATE)
  rows=['# 特殊值与活动 lane 定向验收\n','定向域：固定寄存器值及SEW，vl≤2；qffp，T1，完整Clause与单次SMT外限均7200秒。不是全域运行或净性能消融。\n','|任务|状态|秒|JSON|实际检查|','|---|---|---:|---:|---|']
  for n,r in STATE['jobs'].items():rows.append(f'|{n}|{r.get("state")}|{r.get("seconds","")}|{r.get("gen","")}|{r.get("checks","")}|')
  (HERE/'report.md').write_text('\n'.join(rows)+'\n')
def bits(v):
 if isinstance(v,int):return v
 m=re.fullmatch(r"\d+'h([0-9a-fA-F_]+)",v);assert m,v
 return int(m[1].replace('_',''),16)
def box(v,w):return ((1<<64)-(1<<w))|v if w<64 else v
def fpclass(v,w,e,f):
 if w<64 and v>>w!=(1<<(64-w))-1:return 'invalid-box'
 v&=(1<<w)-1;exp=v>>f&((1<<e)-1);frac=v&((1<<f)-1)
 return ('sNaN' if not frac>>(f-1)&1 else 'qNaN') if exp==(1<<e)-1 and frac else 'normal' if exp not in (0,(1<<e)-1) else 'other'
def common(sew=32,vl=2,mask=3):return {'mstatus':0x6600,'fcsr':0,'vtype':hex({16:8,32:16,64:24}[sew]),'vl':hex(vl),'vstart':'0x0',**{f'vr{i}':f'0x{(mask if i==0 else 0):032x}' for i in range(32)}}
def pack(values,w):return sum(v<<(w*i) for i,v in enumerate(values))
def setvr(st,reg,values,w):st[f'vr{reg}']=f'0x{pack(values,w):032x}'
def mkjob(name,clause,state,fields=None,check=None):return {'name':name,'clause':clause,'initial':state,'fields':fields,'check':check}
def jobs():
 out=[]
 for fmt,(w,e,f,normal,snan,qnan) in FORMATS.items():
  for cls,nan in [('sNaN',snan),('qNaN',qnan)]:
   st=common();st.update({f'f{i}':f'0x{box(normal if i<16 else nan,w):016x}' for i in range(32)})
   out.append(mkjob(f'fleq-{fmt}-{cls}',f'FLEQ_{fmt}',st,check={'kind':'scalar-pairs','format':fmt,'nan':cls}))
 # 半、双精度 sqrt：负数 -> canonical NaN，正数 -> 具体非NaN出口。
 for fmt,w,neg,normal in [('H',16,0xbc00,0x3c00),('D',64,0xbff0000000000000,0x3ff0000000000000)]:
  st=common();st.update({f'f{i}':f'0x{box(neg if i<16 else normal,w):016x}' for i in range(32)})
  out.append(mkjob(f'sqrt-{fmt}',f'F_UN_RM_FF_TYPE_{fmt}',st,check={'kind':'sqrt','format':fmt}))
 # fixed operation + fixed source/destination, vm=0 exposes mask lanes without opcode enumeration.
 for clause,fields in [('VFUNARY0',[0,2,'zFV_CVT_X_F',8]),('FVVMTYPE',['zFVVM_VMFEQ',0,2,4,8]),('FVFMTYPE',['zVFM_VMFEQ',0,2,4,8]),('RFWVVTYPE',['zFVV_VFWREDOSUM',0,2,4,8])]:
  for mask in [1,2]:
   st=common(32,2,mask);setvr(st,2,[0x3f800000,0x7f800001],32);setvr(st,4,[0x3f800000]*2,32);st['f4']='0xffffffff3f800000'
   if clause=='RFWVVTYPE':setvr(st,4,[0x3ff0000000000000],64)
   out.append(mkjob(f'gate-{clause}-mask{mask}',clause,st,fields,{'kind':'gate','expected_flags':0 if mask==1 else 16,'mask':mask}))
 # 每个 BF16 FMA 源单独 sNaN，活动/不活动；融合数值反例保持真FMA。
 for form in ['VV','VF']:
  clause='VFWMACCBF16_'+form
  for case in ['fused','tiny','vector-snan','other-snan','acc-snan','vl0','multi-mask1','multi-mask2','multi-mask3','multi-mask0']:
   mask=int(case[-1]) if case.startswith('multi') else 3
   st=common(16,0 if case=='vl0' else 2,mask)
   a=[0x5f80]*2 if case=='fused' else [0x3f80]*2
   b=a.copy();c=[0xff7fffff]*2 if case=='fused' else [0]*2
   if case=='tiny':a=[0x1780]*2;b=a.copy();c=[0x3f800000]*2
   if case=='vector-snan':a[0]=0x7f81
   if case=='other-snan':b[0]=0x7f81
   if case=='acc-snan':c[0]=0x7f800001
   if case=='vl0':a=[0x7f81]*2;b=[0x7f81]*2;c=[0x7f800001]*2
   if case.startswith('multi'):
    a=[0x7f81,0x7f7f];b=[0x7f7f]*2;c=[0]*2
   setvr(st,2,a,16);setvr(st,4,b,16);setvr(st,8,c,32)
   st['f4']=f'0x{box(b[0],16):016x}'
   expected=1 if case=='tiny' else 0 if case in ('fused','vl0','multi-mask0') else 5 if case=='multi-mask2' else 21 if case=='multi-mask3' else 16
   for rm in (range(5) if case in ('fused','tiny') else [0]):
    current=dict(st);current['fcsr']=rm<<5
    out.append(mkjob(f'bf16-{form}-{case}-rm{rm}',clause,current,[0,2,4,8],{'kind':'bf16','case':case,'form':form,'rm':rm,'expected_flags':expected,'mask':mask,'source_a':a,'source_b':b,'acc':c}))
 for clause in ['VFNCVTBF16_F_F_W','VFWCVTBF16_F_F_V']:
  for mask in [1,2]:
   st=common(16,2,mask);setvr(st,2,[0x3f800000,0x7f800001],32) if clause.startswith('VFN') else setvr(st,2,[0x3f80,0x7f81],16)
   out.append(mkjob(f'bf16-{clause}-mask{mask}',clause,st,[0,2,8],{'kind':'gate','expected_flags':0 if mask==1 else 16,'mask':mask}))
 return out

def wrapper(source,job):
 if job['fields'] is None:return source
 ctor='z'+job['clause'];typ=re.search(r'  '+ctor+r': %struct (\w+),',source)[1]
 body=re.search(r'struct '+typ+r' \{(.*?)\n\}',source,re.S)[1]
 types=[(n,t.strip()) for n,t in re.findall(r'\n  (\w+): ([^,\n]+)',body)]
 assert len(types)==len(job['fields']),(job['clause'],types)
 constraints=[]
 for i,((name,ty),value) in enumerate(zip(types,job['fields'])):
  literal=value if isinstance(value,str) else '0b'+format(value,'0'+str(int(ty[3:]))+'b')
  constraints += [f'  validation_cond{i} : %bool;',f'  validation_unit{i} : %unit;',f'  validation_cond{i} = @eq(zmergez3var as {ctor}.{name}, {literal});',f'  validation_unit{i} = $zsail_assume(validation_cond{i});']
 intro='fn zexecute(zmergez3var) {\n';assert source.count(intro)==1
 return source.replace(intro,'val zvalidation_original_execute : (%union zinstruction) -> %union zExecutionResult\n\n'+intro+'\n'.join(constraints)+'\n  return = zvalidation_original_execute(zmergez3var);\n  end;\n}\n\nfn zvalidation_original_execute(zmergez3var) {\n',1)

def inspect(job,data):
 gen=data.get('gen',[]);success=[c for c in gen if 'Retire_Success' in c['ret_val']];check=job['check'];checks=[];detail={}
 if check['kind']=='scalar-pairs':
  w,e,f,*_=FORMATS[check['format']];seen=Counter()
  for c in success:
   regs=re.findall(r'f\d+',c['test-ins']);assert len(regs)==2
   pre=c['isa-state-complete'];pair=tuple(fpclass(bits(pre[r]),w,e,f) for r in regs);seen[pair]+=1
   expected=16 if check['nan']=='sNaN' and 'sNaN' in pair else 0
   checks.append((bits(c['isa-state-post']['fcsr'])&31)==expected)
   rd=re.search(r' x(\d+),',c['test-ins'])[1]
   if rd!='0':checks.append(bits(c['isa-state-post']['x'+rd])==(1 if pair==('normal','normal') else 0))
   else:detail['x0_result_not_observable']=detail.get('x0_result_not_observable',0)+1
  required=[('normal','normal'),(check['nan'],'normal'),('normal',check['nan'])]
  checks.extend(k in seen for k in required);detail['pairs']={'/'.join(k):v for k,v in seen.items()};detail['required_pairs']=[list(k) for k in required]
 elif check['kind']=='sqrt':
  fmt=check['format'];w,e,f,*_=FORMATS[fmt];seen=set()
  for c in success:
   if not c['test-ins'].startswith('fsqrt.'):continue
   rd,rs=re.findall(r'f\d+',c['test-ins'])[:2];v=bits(c['isa-state-complete'][rs]);positive=not(v>>(w-1)&1);seen.add('normal' if positive else 'negative')
   result=bits(c['isa-state-post'][rd])&((1<<w)-1);expected=FORMATS[fmt][3] if positive else (0x7e00 if w==16 else 0x7ff8000000000000)
   checks.append(result==expected);checks.append(bits(c['isa-state-post']['fcsr'])&31==(0 if positive else 16))
  checks.extend(k in seen for k in ['normal','negative']);detail['sqrt_cases']=sorted(seen)
 else:
  checks.append(bool(success));detail['successes']=len(success)
  for c in success:
   pre=c['isa-state-complete'];post=c['isa-state-post'];
   for key,expected in job['initial'].items():
    if key not in pre:continue
    expected=expected if isinstance(expected,int) else int(expected,16);checks.append(bits(pre[key])==expected)
   checks.append(bits(pre['fcsr'])&31==0);checks.append(bits(post['fcsr'])&31==check['expected_flags']);checks.append(bits(pre['vl'])==bits(job['initial']['vl']) if isinstance(job['initial']['vl'],int) else bits(pre['vl'])==int(job['initial']['vl'],16))
   if check['kind']=='gate':
    value=bits(post['vr8']);before=bits(pre['vr8'])
    if job['clause']=='VFUNARY0':
     expected=1 if check['mask']==1 else 0x7fffffff<<32;checks.append(value==expected)
    elif job['clause'] in ('FVVMTYPE','FVFMTYPE'):checks.append(value==(1 if check['mask']==1 else 0))
    elif job['clause']=='RFWVVTYPE':checks.append(value==(0x4000000000000000 if check['mask']==1 else 0x7ff8000000000000))
    elif job['clause']=='VFNCVTBF16_F_F_W':checks.append(value==(0x3f80 if check['mask']==1 else 0x7fc0<<16))
    elif job['clause']=='VFWCVTBF16_F_F_V':checks.append(value==(0x3f800000 if check['mask']==1 else 0x7fc00000<<32))
   if check['kind']=='bf16':
    result=bits(post['vr8']);before=bits(pre['vr8']);checks.append(bits(post['vstart'])==0)
    checks.append(bits(post['vr9'])==bits(pre['vr9']))
    checks.append(result>>64==before>>64)
    for reg in range(32):
     if reg not in (8,9):checks.append(bits(post['vr'+str(reg)])==bits(pre['vr'+str(reg)]))
    checks.append(bits(post['fcsr'])>>5==check['rm'])
    oracle_flags=0
    active=[i for i in range(2) if check['mask']>>i&1 and int(job['initial']['vl'],16)>i]
    for lane in range(2):
     value=result>>(32*lane)&0xffffffff
     if lane not in active:checks.append(value==(before>>(32*lane)&0xffffffff));continue
     a=check['source_a'][lane]<<16;b=(check['source_b'][0] if check['form']=='VF' else check['source_b'][lane])<<16;c0=check['acc'][lane]
     command=[str(ORACLE),'--op','fma','--fmt','f32','--rm',str(check['rm']),'--a',hex(a),'--b',hex(b),'--c',hex(c0)]
     oracle=json.loads(subprocess.check_output(command,text=True));oracle_flags|=int(oracle['flags'],16);checks.append(value==int(oracle['result_bits'],16));detail.setdefault('oracle',[]).append({'lane':lane,'command':command,'expected':oracle,'actual':hex(value)})
    checks.append(bits(post['fcsr'])&31==oracle_flags);detail['oracle_accumulated_flags']=oracle_flags
    if check['case'] in ('fused','tiny'):
     a=hex(check['source_a'][0]<<16);b=hex(check['source_b'][0]<<16);c0=hex(check['acc'][0]);rm=str(check['rm'])
     mul=json.loads(subprocess.check_output([str(ORACLE),'--op','mul','--fmt','f32','--rm',rm,'--a',a,'--b',b],text=True))
     split=json.loads(subprocess.check_output([str(ORACLE),'--op','add','--fmt','f32','--rm',rm,'--a',mul['result_bits'],'--b',c0],text=True))
     detail['split']={'mul':mul,'add':split,'combined_flags':int(mul['flags'],16)|int(split['flags'],16)}
     checks.append((int(split['result_bits'],16),detail['split']['combined_flags'])!=(int(oracle['result_bits'],16),int(oracle['flags'],16)))
 detail.update(check_count=len(checks),failed_checks=sum(not x for x in checks));return all(checks) and bool(checks),detail

def run(job,cpu):
 name=job['name'];dest=HERE/'runs'/name;dest.mkdir(parents=True,exist_ok=False)
 config=dest/'config.toml';config.write_text(BASE.read_text()+'\n[initial_state]\n'+''.join(f'{k} = {json.dumps(v)}\n' for k,v in job['initial'].items()))
 ir=HERE/'inputs/model.ir'
 if job['fields'] is not None:
  ir=dest/'constrained.ir';ir.write_text(wrapper((HERE/'inputs/model.ir').read_text(),job))
 cmd=['timeout','--signal=TERM','--kill-after=10s','7200s','taskset','-c',str(cpu),str(BIN),'-A',str(ir),'-C',str(config),'-T','1','--smt-timeout','7200s','--tastic','qffp','solve-state','--clause='+job['clause']]
 write(dest/'command.json',{'argv':cmd,'binary_sha256':sha(BIN),'ir_sha256':sha(ir),'base_ir_sha256':sha(HERE/'inputs/model.ir'),'config_sha256':sha(config),'job':job,'constraint_only_wrapper':job['fields'] is not None})
 with LOCK:STATE['jobs'][name].update(state='running',cpu=cpu)
 snapshot();start=time.monotonic();env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None)
 with (dest/'run.log').open('w') as log:rc=subprocess.run(cmd,cwd=dest,stdout=log,stderr=subprocess.STDOUT,env=env).returncode
 rec={'seconds':round(time.monotonic()-start,3),'exit':rc,'state':'FAIL','checks':'no JSON'}
 files=list((dest/'output').glob('*.json'))
 if len(files)==1:
  data=json.loads(files[0].read_text());summ=data['summary'];partial=summ.get('status')!='finished' or any(summ.get(k,0)>0 for k in PARTIAL)
  ok,detail=inspect(job,data);rec.update(gen=len(data['gen']),summary=summ,partial=partial,detail=detail,checks=f'{detail["check_count"]-detail["failed_checks"]}/{detail["check_count"]}',output_sha256=sha(files[0]));rec['state']='PASS' if rc==0 and not partial and ok else 'TIMEOUT' if rc in (124,137) else 'FAIL'
 write(dest/'result.json',rec)
 with LOCK:STATE['jobs'][name].update({k:v for k,v in rec.items() if k not in ('detail','summary')})
 snapshot();print(name,rec['state'],rec['seconds'],flush=True)
 return rec

def main():
 assert not (HERE/'launch.json').exists(),'禁止重复启动'
 (HERE/'bin').mkdir(exist_ok=True);(HERE/'inputs').mkdir(exist_ok=True)
 shutil.copy2(ROOT/'isla/target/release/isarch',BIN)
 todo=jobs();STATE['jobs']={j['name']:{'state':'queued','clause':j['clause']} for j in todo}
 write(HERE/'launch.json',{'pid':os.getpid(),'epoch':time.time(),'cpu':CPUS,'binary_sha256':sha(BIN),'binary_version':subprocess.check_output([str(BIN),'--version'],text=True,stderr=subprocess.STDOUT).strip(),'max_parallel':len(CPUS),'budget':7200,'smt_budget':7200,'oracle_sha256':sha(ORACLE),'oracle_source_sha256':sha(ROOT/'agents/float_support_review/oracle/oracle.cpp'),'libsoftfloat_sha256':sha(ORACLE.parent/'softfloat/libsoftfloat.a'),'preparation':'等待driver exit0及hash，未开始求解'})
 STATE['state']='waiting-generation';snapshot()
 while not (GEN/'driver.json').exists():time.sleep(10)
 driver=json.loads((GEN/'driver.json').read_text());assert driver['exit_code']==0 and driver['source_unchanged']
 ir=GEN/'rv64d_v128_e64.ir';assert sha(ir)==driver['ir_sha256'];shutil.copy2(ir,HERE/'inputs/model.ir');write(HERE/'inputs/generation.json',driver)
 STATE['state']='running';snapshot()
 def lane(index):
  for job in todo[index::len(CPUS)]:
   try:run(job,CPUS[index])
   except Exception as exc:
    with LOCK:STATE['jobs'][job['name']].update(state='HARNESS_ERROR',error=repr(exc))
    snapshot();print(job['name'],repr(exc),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=len(CPUS)) as pool:list(pool.map(lane,range(len(CPUS))))
 STATE['state']='completed';snapshot()
if __name__=='__main__':main()
