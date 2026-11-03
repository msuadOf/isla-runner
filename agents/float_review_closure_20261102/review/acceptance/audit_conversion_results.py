#!/usr/bin/env python3
"""Recompute actual direct-runner observations using exact FP/integer arithmetic."""
from pathlib import Path
import argparse,hashlib,json
from audit_conversion_expected import expected
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RUN=ROOT/'agents/float_review_closure_20261102/validation/conversions/runs/rv64d-v128-attempt2'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def n(x):return int(x,16)
def result(raw,sw,dw,signed,rm):return expected({'source_width':sw,'source_bits':raw,'result_width':dw,'native_target':'i' if signed else 'u','rm':rm})
def main():
    global RUN
    parser=argparse.ArgumentParser();parser.add_argument("--run",type=Path);parser.add_argument("--output",type=Path);args=parser.parse_args()
    if args.run:RUN=args.run.resolve(strict=True)
    record=json.loads((RUN/'run.json').read_text());archive=RUN/'input-archive';checks=[]
    assert record['status']=='PASS_DIRECTED_ONLY'
    for kind in ('scalar','vector'):
        fixture=json.loads((archive/f'{kind}-cases.json').read_text());observed=json.loads((RUN/f'{kind}-results.json').read_text())
        assert len(fixture)==len(observed)
        for c,r in zip(fixture,observed):
            assert r['name']==c['name'];word=n(r['word']);reg={k:n(v) for k,v in r['registers'].items()};initial={k:n(v) for k,v in c['initial'].items()};rd=word>>7&31;rs1=word>>15&31;rs2=word>>20&31
            assert n(c['word'])==word==n(r['reencoded']) and r['decoded_ctor']==c['clause'] and r['execute_result']=='Retire_Success'
            assert r['sat'] is True and r['difference_unsat'] is True and r['execute_paths']==1 and r['encode_paths']==1 and r['decode_paths']==2
            if kind=='scalar':
                assert word&127==0x53 and word>>25 in (96,97,98)
                sw={96:32,97:64,98:16}[word>>25];dw=64 if rs2&2 else 32;signed=not(rs2&1);rm=word>>12&7
                assert f'f{rs1}' in reg and reg[f'f{rs1}']==initial[f'f{rs1}']
                raw=initial[f'f{rs1}']&((1<<sw)-1)
                if sw<64:assert initial[f'f{rs1}']>>sw==(1<<(64-sw))-1
                bits,flags=result(raw,sw,dw,signed,rm)
                if dw==32 and bits>>31:bits|=0xffffffff00000000
                want={f'x{rd}':bits,'fcsr':initial['fcsr']|flags,'mstatus':initial['mstatus']|((1<<63) if flags&~initial['fcsr']&31 else 0)}
            else:
                assert word&127==0x57 and word>>26==18 and word>>12&7==1
                narrow=rs1>=16;signed=bool(rs1&1);dw=8<<((initial['vtype']>>3)&7);sw=dw*(2 if narrow else 1);rm=1 if rs1 in (6,7,22,23) else initial['fcsr']>>5&7
                source=f'vr{rs2}';assert reg[source]==initial[source]
                bits=initial[f'vr{rd}'];flags=0
                for lane in range(initial['vl']):
                    if lane<initial['vstart'] or not(word>>25&1 or initial['vr0']>>lane&1):continue
                    raw=initial[source]>>(sw*lane)&((1<<sw)-1);one,f=result(raw,sw,dw,signed,rm);flags|=f
                    bits=(bits&~(((1<<dw)-1)<<(lane*dw)))|(one<<(lane*dw))
                want={f'vr{rd}':bits,'fcsr':initial['fcsr']|flags,'mstatus':initial['mstatus']|(1<<63),'vstart':0}
            for k in reg:
                if k not in want:assert k in initial and reg[k]==initial[k],(c['name'],k,'unintended write')
            bad={k:{'actual':hex(reg[k]),'independent':hex(v)} for k,v in want.items() if reg[k]!=v}
            checks.append({'name':c['name'],'kind':kind,'pass':not bad,'mismatches':bad})
    logs=(RUN/'helpers.log').read_text().splitlines();fixture=(archive/'helpers.tsv').read_text().splitlines()
    assert [x for x in logs if x.startswith('PASS riscv_')]==['PASS '+x.split('\t')[0] for x in fixture]
    for stage in record['stages']:
        assert stage['exit_code']==0 and digest(RUN/(stage['label']+'.log'))==stage['log_sha256']
        if stage['label'] in ('helpers','scalar','vector'):
            text=(RUN/(stage['label']+'-seed.log')).read_text().splitlines();assert text and all('parameter=random_seed ' in x and x.endswith('fixed=17') for x in text)
    out={'scope':'Actual word and observed-register exact-rational replay; direct Qfaufbv runners, no isarch JSON/full Clause','model':record['model_commit'],'isla':record['isla_commit'],'ir_sha256':record['inputs']['ir']['sha256'],'config_sha256':record['inputs']['config']['sha256'],'run_sha256':digest(RUN/'run.json'),'scalar_sha256':digest(RUN/'scalar-results.json'),'vector_sha256':digest(RUN/'vector-results.json'),'helper_pass_lines':len(fixture),'instruction_rows':len(checks),'failures':[c for c in checks if not c['pass']],'checks':checks}
    (args.output or HERE/'conversions-results-independent.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ('checks','failures')});assert not out['failures'],out['failures']
if __name__=='__main__':main()
