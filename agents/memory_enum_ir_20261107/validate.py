#!/usr/bin/env python3
"""在本轮固定输入上复跑旧合流的本机定向检查，逐项保留退出码。"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/memory-enum-20261107'
DYNAMIC = OUT / 'dynamic'
OLD = ROOT / 'agents/float_memory_merge_20261103/validation'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def row(p, **kw):
    p = p.resolve(strict=True)
    return {'path': str(p), 'sha256': sha(p), **kw}


def main():
    z3_prefix = Path(os.environ.get('Z3_PREFIX', Path.home()/'.local/opt/z3-official-1fd1d3613'))
    z3 = (z3_prefix/'lib/libz3.so').resolve(strict=True)
    env = dict(os.environ, CARGO_TARGET_DIR=str(OUT/'target'), CARGO_NET_OFFLINE='true',
               CARGO_BUILD_JOBS='8', LIBRARY_PATH=str(z3.parent), LD_LIBRARY_PATH=str(z3.parent),
               RUSTFLAGS=f'-L native={z3.parent} -C link-arg=-Wl,-rpath,{z3.parent}')
    isla, model = ROOT/'isla', ROOT/'sail-riscv'
    git = lambda p: subprocess.check_output(['git', '-C', str(p), 'rev-parse', 'HEAD'], text=True).strip()
    config = row(isla/'configs/riscv64_difftest_fd.toml', domain='full-rv64-fd')
    mixed = row(OUT/'mixed-directed.toml', domain='directed-mixed')
    inputs = {'schema': 1, 'domain': 'directed-315', 'seed': 17, 'tactic': 'qffp', 'threads': 32,
              'model_tree': str(model), 'isla_tree': str(isla), 'model_commit': git(model), 'isla_commit': git(isla),
              'model_source_manifest': row(OUT/'model-source.json'),
              'isla_source_manifest': row(OUT/'isla-source.json'),
              'binary': row(OUT/'target/release/isarch'), 'ir': row(isla/'rv64d.ir'), 'config': config,
              'z3': row(z3), 'seed_preload': row(OUT/'deps/seed_control.so'),
              'directed_config_provenance': row(OUT/'mixed-directed.provenance.json'),
              'irs': {k: row(isla/p) for k,p in [('rv64-default','rv64d.ir'),('rv32-default','rv32d.ir'),
                         ('rv64-v128','ir/rv64d_v128_e64.ir'),('rv64-v256','ir/rv64d_v256_e64.ir'),
                         ('rv64-v512','ir/rv64d_v512_e64.ir')]},
              'configs': {'rv64': config, 'fd': config, 'rv32': row(isla/'test/float_ir/rv32_fd.toml'),
                          'memory': row(isla/'configs/riscv64_difftest_mem.toml',domain='full-memory'),
                          'mixed-directed': mixed}}
    path = OUT/'inputs.json'
    path.write_text(json.dumps(inputs, indent=2, ensure_ascii=False)+'\n')
    union = dict(inputs, config=mixed)
    union_path = OUT/'inputs-union.json'
    union_path.write_text(json.dumps(union, indent=2, ensure_ascii=False)+'\n')
    checks = []

    def run(label, command, timeout=2400, cwd=ROOT, extra_env=None):
        start = time.monotonic()
        with (OUT/(label+'.log')).open('w') as log:
            try:
                code = subprocess.run(list(map(str,command)), cwd=cwd, env=dict(env,**(extra_env or {})),
                                      stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
            except subprocess.TimeoutExpired:
                code = 124
        checks.append({'label':label,'command':list(map(str,command)),'exit':code,
                       'seconds':round(time.monotonic()-start,3),'log_sha256':sha(OUT/(label+'.log'))})
        (OUT/'validation-checks.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
        print(label,code,flush=True)
        return code

    py = sys.executable
    run('permanent-ir', [py,isla/'test/float_ir/run.py','--mode','all','--output',OUT/'permanent-ir'])
    # 仅改原脚本的根目录定位；负变异与检查逻辑原样沿用。
    negative = OUT/'check_negative_104.py'
    negative.write_text((OLD/'integration/check_negative_104.py').read_text().replace('MAIN=R.parents[1]','MAIN=R'))
    run('negative-104',[py,negative,OUT/'negative-104.json'])
    run('flags-300',[py,DYNAMIC/'run_300.py','--inputs',path,'--batch','flags','--cpu','28'])
    run('masked-source',[py,DYNAMIC/'run_masked_source.py','--inputs',path,'--batch','mask','--cpu','28'])
    run('schema-union',[py,DYNAMIC/'run_union.py','--inputs',union_path,'--batch','union','--cpu','28','--timeout','1200'])
    run('union-audit',[py,ROOT/'agents/float_memory_merge_20261103/review/acceptance/audit_schema_union_json.py',
                       '--root',DYNAMIC/'runs/union/union','--output',OUT/'union-audit.json'])
    run('union-assembly',[py,DYNAMIC/'run_assembly.py','--batch','union-assembly','--union',DYNAMIC/'runs/union/union'])
    run('vstart',[py,DYNAMIC/'run_vstart.py','--inputs',union_path,'--batch','vstart','--cpu','28','--timeout','1200'])
    # 旧 Make 四入口固定机器字与前态由历史收据读取，仍调用当前 run.mk。
    for clause in ('FLEQ_S','LOAD_FP','STORE','C_LD'):
        old = json.loads((OLD/f'dynamic/runs/directed-make-4d08/make/{clause}/result.json').read_text())
        command = [py,DYNAMIC/'run_make.py','--inputs',union_path,'--batch','make','--cpu','28',
                   '--clause',clause,'--domain','directed','--config','mixed-directed','--word',old['machine_word']]
        for state in old['inserted_prestates'][2:]:
            command += ['--prestate',state]
        run('make-'+clause,command)
    run('make-assembly',[py,DYNAMIC/'run_assembly.py','--batch','make-assembly','--union',DYNAMIC/'runs/make/make'])
    # ExecuteAs 压缩指令：与旧探针相同机器字、整数初态7，显式固定 Machine。
    dest = OUT/'executeas'
    dest.mkdir()
    execute_config=dest/'config.toml'
    execute_config.write_text(Path(config['path']).read_text()+'\n[initial_state]\n'+''.join(f'x{i} = 7\n' for i in range(1,32)))
    run('executeas',[OUT/'target/release/isarch','-A',isla/'rv64d.ir','-C',execute_config,'-T','64',
                     '--timeout','1200s','--smt-timeout','1200s','--tastic','qfaufbv','--instruction-bits','0x1fe0',
                     '--prestate','cur_privilege=Machine','--prestate','x2=0x0000000000000007','solve-state','--clause=C_ADDI4SPN'],
        cwd=dest,extra_env={'LD_PRELOAD':str(OUT/'deps/seed_control.so'),'ISLA_ABLATION_SEED':'17',
                             'ISLA_ABLATION_SEED_LOG':str(dest/'seed.log')})
    files=list((dest/'output').glob('*.json'))
    data=json.loads(files[0].read_text()) if len(files)==1 else None
    state_ok=(data is not None and bool(data['gen']) and all(
        int(e['isa-state-post']['x8'].split("'h")[1].replace("_", ""),16)==1027
        and 'Retire_Success' in e['ret_val'] for e in data['gen']))
    (dest/'inspection.json').write_text(json.dumps({'state_ok':state_ok,'output_count':len(files),
        'summary':data['summary'] if data else {},'gen':len(data['gen']) if data else 0},indent=2)+'\n')
    run('exceptions-315',[py,DYNAMIC/'run_315.py','--inputs',path,'--batch','numeric315','--cpus','28,29,30,31','--timeout','1200'],timeout=43200)
    # 验证过程中实际输入保持不变；IR来源sidecar不在旧源码清单排除表中，另作哈希检查。
    for entry in [inputs['binary'], inputs['ir'], *inputs['irs'].values()]:
        assert sha(Path(entry['path']))==entry['sha256']
    for name,tree,flag in [('isla',isla,True),('model',model,False)]:
        command=[py,OLD/'freeze_source.py','--tree',tree,'--output',OUT/(name+'-source.json'),'--compare']
        if flag:command+=['--isla-source']
        run(name+'-source-after',command)

if __name__=='__main__':
    main()
