#!/usr/bin/env python3
"""Audit actual JSON encoding fields against archived compiler byte outputs."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,struct
from audit_actual_json import number,effective
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
TOPIC=ROOT/'agents/float_review_closure_20261102'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(output,toolchains):
    data=json.loads(output.read_text());r=json.loads((toolchains/'results.json').read_text());assert sha(output)==r['sha256']
    cases=data['gen'];assert len(cases)==r['gen'];fail=[];fallbacks=[];coverage=Counter()
    exact={(0x21,0):'fcvt.d.s',(0x21,2):'fcvt.d.h',(0x20,2):'fcvt.s.h',(0x69,0):'fcvt.d.w',(0x69,1):'fcvt.d.wu'}
    controls={(0x69,2):'fcvt.d.l',(0x69,3):'fcvt.d.lu',(0x68,0):'fcvt.s.w'}
    modes={0:'rne',1:'rtz',2:'rdn',3:'rup',4:'rmm',7:'dyn'}
    matrix={(x['index'],x['driver'],x['kind']):x for x in r['checks']}
    assert set(matrix)=={(i,d,k) for i in range(len(cases)) for d in ('gcc','clang') for k in ('mnemonic','insn','binary')}
    for c in cases:
        raw=number(c['test-ins-encdec']);w=int(c['test-ins-encdec'].split("'")[0]);rep=c['instruction-representations'];enc=rep['encoding'];expected=raw.to_bytes(w//8,'little').hex()
        assert rep['mnemonic']==c['test-ins'] and enc['bytes-le']==expected and int(enc['hex'],16)==raw and int(enc['bits'],2)==raw and len(enc['bits'])==w
        assert rep['insn']['text']==f'.insn {w//8}, {enc["hex"]}'
        key=(raw>>25,raw>>20&31);rm=raw>>12&7
        if raw&127==0x53 and key in exact|controls:
            op=(exact|controls)[key];coverage[(op,rm)]+=1;parts=[x.strip() for x in rep['mnemonic'].split(',')]
            assert parts[0].startswith(op+' ') and rm in modes
            if key in exact and rm==0:assert len(parts)==2
            else:assert len(parts)==3 and parts[-1]==modes[rm]
    assert len(r['checks'])==len(cases)*6
    for row in r['checks']:
        case=cases[row['index']];word=number(case['test-ins-encdec']);w=int(case['test-ins-encdec'].split("'")[0]);expected=word.to_bytes(w//8,'little').hex();assert row['expected']==expected
        obj=Path(row['command'][row['command'].index('-o')+1]);source=Path(row['command'][row['command'].index('-c')+1]);assert row['text'] in source.read_text().splitlines()
        if row['exit']==0:
            actual=obj.with_suffix('.bin').read_bytes().hex();assert actual==row['actual']==expected
        elif row['expected_rejection']:
            assert row['driver']=='clang' and row['kind']=='mnemonic' and case['ret_val'].startswith('Illegal_Instruction') and row['text'].startswith('vfwmaccbf16')
        else:
            key=(word>>25,word>>20&31);rm=word>>12&7
            if word&127==0x53 and key in exact and rm!=0 and row['driver']=='gcc' and row['kind']=='mnemonic':
                for driver,kind in [('clang','mnemonic'),('gcc','insn'),('gcc','binary')]:
                    peer=matrix[row['index'],driver,kind];assert peer['exit']==0 and peer['actual']==expected
                selection=json.loads((toolchains/'selection.json').read_text())
                selected=[x for x in selection['selected'] if x['index']==row['index'] and x['driver']=='gcc'];assert len(selected)==1
                chosen=selected[0];assert chosen['form']=='insn' and chosen['raw_rm']==rm and chosen['expected_bytes']==chosen['insn_actual_bytes']==chosen['byte_actual_bytes']==expected
                assert chosen['insn_command']==matrix[row['index'],'gcc','insn']['command'] and chosen['byte_command']==matrix[row['index'],'gcc','binary']['command']
                fallbacks.append({'index':row['index'],'op':exact[key],'rm':rm,'raw_exit':row['exit'],'expected_bytes':expected})
            else:fail.append({k:row[k] for k in ['index','driver','kind','text','exit','expected','stderr']})
        assert row['pass_']==(row['exit']==0 or row['expected_rejection'])
    if (toolchains/'selection.json').exists():
        selection=json.loads((toolchains/'selection.json').read_text());assert selection['source_sha256']==sha(output) and selection['accepted_gnu_exact_fallbacks']==len(fallbacks) and selection['all_pass']==(not fail)
    return {'json_sha256':sha(output),'toolchain_results_sha256':sha(toolchains/'results.json'),'gen':len(cases),'compiler_checks':len(r['checks']),'raw_failures':sum(not x['pass_'] for x in r['checks']),'exact_gnu_fallbacks':fallbacks,'operation_rm_coverage':{f'{op}/rm{rm}':v for (op,rm),v in sorted(coverage.items())},'unexpected_failures':fail,'all_pass':not fail}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--representations-base',type=Path,default=TOPIC/'validation/representations/model-8ad5e8e');parser.add_argument('--make-base',type=Path,default=TOPIC/'validation/make/model-8ad5e8e/smoke');parser.add_argument('--output',type=Path,default=HERE/'representations-make-independent.json');args=parser.parse_args()
    base=args.representations_base;rows=[]
    for d in sorted(base.iterdir()):
        if not d.is_dir() or not (d/'toolchains/results.json').exists():continue
        files=list((d/'run/output').glob('*.json'));assert len(files)==1;rows.append({'job':d.name,**audit(files[0],d/'toolchains')})
    make=args.make_base;output=make/'output/rv64_zFLEQ_S.json';mr=json.loads((make/'result.json').read_text());md=json.loads(output.read_text());pairs=Counter();observed=0
    for c in md['gen']:
        word=number(c['test-ins-encdec']);assert word&127==0x53 and word>>25==0x50 and word>>12&7==4
        pre,post=c['isa-state-complete'],c['isa-state-post'];a=effective(number(pre['f'+str(word>>15&31)]),32);b=effective(number(pre['f'+str(word>>20&31)]),32)
        def classification(raw):return 'nan' if raw>>23&255==255 and raw&0x7fffff else 'finite'
        pairs[(classification(a),classification(b))]+=1
        snan=lambda raw:raw>>23&255==255 and raw&0x7fffff and not(raw&0x400000)
        flags=16 if snan(a) or snan(b) else 0
        av=struct.unpack('>f',a.to_bytes(4,'big'))[0];bv=struct.unpack('>f',b.to_bytes(4,'big'))[0];value=int(av<=bv);rd=word>>7&31
        assert number(post['fcsr'])==number(pre['fcsr'])|flags
        if rd:assert number(post['x'+str(rd)])==value;observed+=1
        for reg in [f'f{i}' for i in range(32)]+[f'x{i}' for i in range(1,32) if i!=rd]:assert post[reg]==pre[reg]
    assert set(pairs)=={('finite','finite'),('finite','nan'),('nan','finite'),('nan','nan')}
    makerow=audit(output,make/'toolchains');assert mr['exit_code']==0 and mr['pass'] is True and makerow['all_pass']
    out={'scope':'Archived compiler bytes and actual Make JSON independently audited; compiler behavior failure separately reproduced','jobs':rows,'representation_gen':sum(r['gen'] for r in rows),'representation_checks':sum(r['compiler_checks'] for r in rows),'representation_unexpected_failures':sum(len(r['unexpected_failures']) for r in rows),'make':{**makerow,'actual_result_observable_cases':observed,'actual_source_pairs':{'/'.join(k):v for k,v in pairs.items()},'result_sha256':sha(make/'result.json')}}
    args.output.write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ('jobs','make')});print('make',out['make']);assert all(r['all_pass'] for r in rows)
if __name__=='__main__':main()
