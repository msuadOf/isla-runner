#!/usr/bin/env python3
"""Recompute helper state from actual logs, ignoring owner expected fields."""
from pathlib import Path
import argparse,hashlib,itertools,json,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RUN=ROOT/'agents/float_review_closure_20261102/validation/flags/runs/model-8ad5e8e'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    global RUN
    parser=argparse.ArgumentParser();parser.add_argument("--run",type=Path);parser.add_argument("--output",type=Path);args=parser.parse_args()
    if args.run:RUN=args.run.resolve(strict=True)
    record=json.loads((RUN/'result.json').read_text());rows=[];batches=[]
    labels={'zero':(0,0),'same_nv':(16,16),'new_nv':(0,16),'old_nx_new_nv':(1,16),'new_multiple':(4,19)}
    for key,meta in record['runs'].items():
        path=RUN/(key+'.log');assert sha(path)==meta['log_sha256'] and meta['exit']==meta['oracle_exit']==0
        raw=[x for x in path.read_text().splitlines() if x.startswith('PASS ') and not x.startswith('PASS total=')];assert len(raw)==60
        seen=set();changed_count=0
        for line in raw:
            _,label,*items=line.split();d=dict(x.split('=',1) for x in items);num=lambda k:int(d[k],0)
            xlen=num('xlen');sd=1<<(xlen-1);fsmask=3<<13;old,incoming=labels[label];other=num('other');fs=num('fs');sdold=d['initial_sd']=='true'
            assert xlen==(32 if key=='rv32-default' else 64)
            assert num('old_fcsr')==0x123456a0|old and num('incoming')==incoming
            initial=other|(sd if sdold else 0)|(fs<<13);assert num('initial_mstatus')==initial
            changed=bool(incoming&~old);want_status=(initial|fsmask|sd) if changed else initial;want_fcsr=0x123456a0|old|incoming
            assert num('fcsr')==want_fcsr and num('mstatus')==want_status,(key,label,d)
            seen.add((label,fs,sdold,other));changed_count+=changed
            rows.append({'ir_key':key,'label':label,'changed':changed,'actual_fcsr':d['fcsr'],'actual_mstatus':d['mstatus'],'pass':True})
        sentinel=0xa000000a02000600&~sd&~fsmask
        assert seen==set(itertools.product(labels,[1,2,3],[False,True],[0,sentinel]))
        seed=RUN/(key+'.seed.log');assert sha(seed)==meta['seed_log_sha256'];assert re.fullmatch(r'parameter=random_seed original=\d+ fixed=17\n?',seed.read_text())
        batches.append({'ir_key':key,'rows':60,'changed_true':changed_count,'changed_false':60-changed_count})
    out={'scope':'Direct helper state audit; callback contract remains static IR only; rv64-default aliases rv64-v128','result_sha256':sha(RUN/'result.json'),'model':record['model_commit'],'isla':record['isla_commit'],'probe_binary_sha256':record['binary_sha256'],'rows':len(rows),'batches':batches,'checks':rows}
    (args.output or HERE/'flags-results-independent.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='checks'})
if __name__=='__main__':main()
