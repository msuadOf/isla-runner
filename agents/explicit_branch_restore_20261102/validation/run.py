#!/usr/bin/env python3
"""组合新模型七 Clause 验收；所有写入限制在本目录。"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import concurrent.futures, hashlib, importlib.util, json, os, queue, re, shutil, subprocess, sys, threading, time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT/'agents/branch_ablation_official_z3_20261102'
GEN = HERE.parent/'implementation/generation/rv64d_v128_e64'
CPUS = [98, 100, 116, 120, 121, 73]
JOBS = [('minmax','F_BIN_TYPE_F_S'), ('minm','FMINM_S'), ('maxm','FMAXM_S'),
        ('nan','F_UN_RM_FF_TYPE_S'), ('mask','FVVTYPE'), ('reduction','RFVVTYPE'), ('class','VFUNARY1')]
PARTIAL = ('errors','execution-timeouts','smt-timeouts','unfinished-paths','omitted-cases',
           'model-query-timeouts','pending-batches','sampled-paths')
LOCK = threading.Lock()
STATE = {'state':'waiting_generation', 'jobs':{n:{'state':'queued','clause':c} for n,c in JOBS}}

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def relative(p): return str(p.relative_to(ROOT))
def write(p, value):
    tmp = p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');tmp.replace(p)

def snapshot():
    with LOCK:
        STATE['updated_utc'] = now()
        write(HERE/'summary.json', STATE)
        lines=['# 显式分支组合 Clause 验证\n',f'状态：{STATE["state"]}；更新时间 {STATE["updated_utc"]}。\n',
               '单次组合正确性及预算验收，不是单变量性能实验。完整 Clause 外限和 SMT 均7200秒；qffp、T1、固定种子17。\n',
               '|Clause|状态|秒|JSON|Retire|非法|partial|目标类别|','|---|---|---:|---:|---:|---:|---|---|']
        for name,rec in STATE['jobs'].items():
            lines.append('|'+ '|'.join(str(rec.get(k,'')) for k in ('clause','state','elapsed_s','gen','retire','illegal','partial','categories'))+'|')
        lines += ['\n初态、flags、原始命令、返回值、错误及旧 A/单项 B 类别对照分别见各工作负载 result.json。',
                  '\n只有自然退出0、summary=finished且所有错误/截断计数为0才标为PASS；JSON条数不是fork数。',
                  '\n七Clause均采用新组合IR；历史A/B来自冻结的旧程序，故只比较见证类别，不能用于净性能归因。']
        (HERE/'report.md').write_text('\n'.join(lines)+'\n')

def load_coverage():
    spec=importlib.util.spec_from_file_location('prior_coverage',OLD/'coverage.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def evidence(name, output):
    data=json.loads(output.read_text()); gen=data.get('gen',[]); summary=data.get('summary',{})
    helper=load_coverage();cov=helper.summarize(name,output)
    initial={key:dict(Counter(str(x.get('isa-state-complete',{}).get(key,'absent')) for x in gen))
             for key in ('mstatus','fcsr','vtype','vl','vstart')}
    flags=Counter(); returns=Counter(); examples={};operand_pairs=Counter()
    def fp32_kind(value):
        n=helper.bits(value)
        if n>>32!=0xffffffff:return 'invalid_box_effective_qNaN'
        exp=(n>>23)&255;frac=n&0x7fffff;sign='-' if n>>31&1 else '+'
        if exp==255:return ('qNaN' if frac>>22 else 'sNaN') if frac else sign+'infinity'
        if exp==0:return sign+('subnormal' if frac else 'zero')
        return sign+'normal'
    for item in gen:
        ret=str(item.get('ret_val',''));returns[ret]+=1
        pre=item.get('isa-state-complete',{});post=item.get('isa-state-post',{})
        match=re.match(r'(f(?:min|max)m?\.s) f\d+, (f\d+), (f\d+)',item.get('test-ins',''))
        if match and 'Retire_Success' in ret:
            opcode,left,right=match.groups()
            operand_pairs[f'{opcode}:{fp32_kind(pre[left])}/{fp32_kind(pre[right])}']+=1
        if 'fcsr' in pre and 'fcsr' in post:
            before=helper.bits(pre['fcsr'])&31;after=helper.bits(post['fcsr'])&31
            flags[f'{before:#04x}->{after:#04x}']+=1
        cat=helper.category(name,item)
        if cat and cat not in examples:
            examples[cat]={'test-ins':item.get('test-ins'),'ret_val':ret,'pre':pre,'post':post}
    historical=json.loads((OLD/'live-summary.json').read_text())['workloads'][name]
    compare={arm:{'categories':historical['arms'][arm]['coverage_categories'],
                  'completed':historical['arms'][arm]['complete']} for arm in ('A','B')}
    for rec in compare.values():
        rec['new_categories']=sorted(set(cov['target_categories'])-set(rec['categories']))
        rec['missing_categories']=sorted(set(rec['categories'])-set(cov['target_categories']))
    return {'summary':summary,'gen':len(gen),'retire':sum('Retire_Success' in x.get('ret_val','') for x in gen),
            'illegal':sum('Illegal_Instruction' in x.get('ret_val','') for x in gen),
            'partial':summary.get('status')!='finished' or any(summary.get(k,0)>0 for k in PARTIAL),
            'categories':cov['target_categories'],'initial_values':initial,'fflags_transitions':dict(flags),
            'effective_fp32_operand_pairs':dict(operand_pairs),
            'return_values':dict(returns),'category_examples':examples,'historical_category_comparison':compare,
            'historical_comparison_limit':'旧A/B程序未含当前ExecuteAs/汇编修复；旧类别为三个seed并集，新模型单seed。missing仅表示本次未见证，不自动判回归；此处非净性能比较。'}

def run(name, clause, cpu):
    dest=HERE/'runs'/name;dest.mkdir(parents=True)
    config=HERE/'inputs'/f'{name}.toml'
    command=['/usr/bin/time','-f','wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M','-o','time.txt',
             'timeout','--signal=TERM','--kill-after=10s','7200s','taskset','-c',str(cpu),
             'env',f'LD_PRELOAD={HERE}/bin/seed_control.so','ISLA_ABLATION_SEED=17',
             f'ISLA_ABLATION_SEED_LOG={dest}/seed.log',str(HERE/'bin/isarch'),
             '-A',str(HERE/'inputs/combined.ir'),'-C',str(config),'-T','1','--tastic','qffp',
             '--smt-timeout','7200s','solve-state',f'--clause={clause}']
    write(dest/'command.json',{'command':command,'cwd':relative(dest),'config_sha256':sha(config),
                              'ir_sha256':sha(HERE/'inputs/combined.ir'),'binary_sha256':sha(HERE/'bin/isarch')})
    with LOCK: STATE['jobs'][name].update(state='running',cpu=cpu,started_utc=now())
    snapshot();start=time.monotonic()
    with (dest/'run.log').open('w') as log:
        proc=subprocess.Popen(command,cwd=dest,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        with LOCK: STATE['jobs'][name]['pid']=proc.pid
        code=proc.wait()
    result={'clause':clause,'exit_code':code,'elapsed_s':round(time.monotonic()-start,3),
            'outer_timeout':code in (124,137),'finished_utc':now(),'cpu':cpu}
    files=list((dest/'output').glob('rv64_z*.json'))
    if len(files)==1:
        result.update(evidence(name,files[0]));result.update(output=relative(files[0]),output_sha256=sha(files[0]))
    else: result.update(partial=True,output_count=len(files))
    result['seed_intercepted']=(dest/'seed.log').exists() and 'fixed=17' in (dest/'seed.log').read_text()
    result['state']='PASS' if code==0 and not result['partial'] and result['seed_intercepted'] else 'TIMEOUT' if result['outer_timeout'] else 'PARTIAL_OR_FAIL'
    write(dest/'result.json',result)
    brief={k:v for k,v in result.items() if k not in ('category_examples','initial_values','historical_category_comparison','return_values')}
    with LOCK: STATE['jobs'][name].update(brief)
    snapshot()

def main():
    if (HERE/'launch.json').exists(): raise RuntimeError('禁止重复启动')
    (HERE/'bin').mkdir(exist_ok=True);(HERE/'inputs').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'isla/target/release/isarch',HERE/'bin/isarch')
    shutil.copy2(OLD/'bin/seed_control.so',HERE/'bin/seed_control.so')
    write(HERE/'launch.json',{'pid':os.getpid(),'started_utc':now(),'cpus':CPUS,
                            'binary_sha256':sha(HERE/'bin/isarch'),
                            'binary_version':subprocess.check_output([str(HERE/'bin/isarch'),'--version'],text=True,stderr=subprocess.STDOUT).strip(),
                            'isla_commit':subprocess.check_output(['git','-C',str(ROOT/'isla'),'rev-parse','HEAD'],text=True).strip(),
                            'seed_shim_sha256':sha(HERE/'bin/seed_control.so'),'threads':1,'tactic':'qffp',
                            'outer_timeout_s':7200,'smt_timeout_s':7200,'path_timeout':None,
                            'official_z3_sha256':sha(Path.home()/'.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3')})
    snapshot()
    while not (GEN/'generation.json').exists():time.sleep(10)
    record=json.loads((GEN/'generation.json').read_text())
    if record['exit_code']!=0:raise RuntimeError('新IR生成失败')
    ir=GEN/'rv64d_v128_e64.ir'
    if sha(ir)!=record['ir_sha256']:raise RuntimeError('新IR hash不一致')
    shutil.copy2(ir,HERE/'inputs/combined.ir');write(HERE/'inputs/generation.json',record)
    for name,_ in JOBS:shutil.copy2(OLD/'inputs'/name/'config.toml',HERE/'inputs'/f'{name}.toml')
    STATE.update(state='running',ir_sha256=sha(ir),model_commit=record['model_commit'])
    snapshot()
    pending=queue.Queue()
    for item in JOBS:pending.put(item)
    def worker(cpu):
        while True:
            try:name,clause=pending.get_nowait()
            except queue.Empty:return
            run(name,clause,cpu)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures=[pool.submit(worker,cpu) for cpu in CPUS]
        while not all(f.done() for f in futures):
            time.sleep(30);snapshot()
        for f in futures:f.result()
    STATE['state']='complete';snapshot()

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        STATE.update(state='runner_failed',error=f'{type(exc).__name__}: {exc}');snapshot();raise
