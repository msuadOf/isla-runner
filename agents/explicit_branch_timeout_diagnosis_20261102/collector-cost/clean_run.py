#!/usr/bin/env python3
"""只跑首个collector诊断case，并等待整个进程树自然退出。"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUT = ROOT / 'agents/branch_ablation_official_z3_20261102/inputs/flags-arithmetic'
BIN = HERE / 'isla-probe/target/release/isarch'
Z3 = Path('/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def live_probe_pids():
    result=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            raw=(proc/'cmdline').read_bytes()
        except (OSError, PermissionError):
            continue
        if str(BIN).encode() in raw:
            result.append(int(proc.name))
    return sorted(result)

def main():
    assert not live_probe_pids(), f'existing probe processes: {live_probe_pids()}'
    env=os.environ.copy()
    env.update({'LD_PRELOAD': str(ROOT/'agents/explicit_branch_timeout_diagnosis_20261102/probe.so')+':'+str(ROOT/'agents/branch_ablation_official_z3_20261102/bin/seed_control.so'),
        'ISLA_QUERY_LOG': str(HERE/'clean-queries.tsv'),
        'ISLA_ABLATION_SEED': '17',
        'ISLA_ABLATION_SEED_LOG': str(HERE/'clean-seed.log'),
        'LD_LIBRARY_PATH': str(Z3.parent),
        'ISLA_COLLECTOR_CONTROL': '1', 'ISLA_COLLECTOR_CONTROL_ONLY': '1'})
    cmd=['/usr/bin/time','-f','wall_s=%e\nuser_s=%U\nsys_s=%S\nmaxrss_kb=%M','-o',str(HERE/'clean-time.txt'),
         'timeout','--signal=TERM','--kill-after=10s','7200s','taskset','-c','112',str(BIN),
         '-A',str(INPUT/'B.ir'),'-C',str(INPUT/'config.toml'),'-T','1','--tastic','qffp','--smt-timeout','7200s',
         'solve-state','--clause=F_BIN_RM_TYPE_S']
    result={'started_utc':datetime.now(timezone.utc).isoformat(), 'command':cmd,
            'source_head':'09ffa91', 'binary_sha256':sha(BIN), 'ir_sha256':sha(INPUT/'B.ir'),
            'config_sha256':sha(INPUT/'config.toml'), 'z3_sha256':sha(Z3),
            'preexisting_probe_pids':live_probe_pids()}
    (HERE/'clean-launch.json').write_text(json.dumps(result,indent=2)+'\n')
    started=time.monotonic()
    with (HERE/'clean-run.log').open('w') as out:
        proc=subprocess.Popen(cmd,cwd=HERE,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
        result['pid']=proc.pid
        (HERE/'clean-launch.json').write_text(json.dumps(result,indent=2)+'\n')
        result['returncode']=proc.wait(timeout=7205)
    result['measured_wall_s']=time.monotonic()-started
    result['finished_utc']=datetime.now(timezone.utc).isoformat()
    result['time_txt']=(HERE/'clean-time.txt').read_text()
    result['remaining_probe_pids']=live_probe_pids()
    result['first_case_exit_marker']='control_only_exit' in (HERE/'clean-run.log').read_text(errors='replace')
    (HERE/'clean-result.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['returncode']==87 and result['first_case_exit_marker'] and not result['remaining_probe_pids'], result

if __name__=='__main__':
    main()
