#!/usr/bin/env python3
"""独立重核全部定向产物、初态约束、来源和实际汇编字节。"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
VALID_ROOT=ROOT/'agents/encoding_constraint_isolation_20261102/validation'
parser=argparse.ArgumentParser()
parser.add_argument('--batch',choices=['original','selective'],default='original')
parser.add_argument('--semantic-only',action='store_true')
parser.add_argument('--representations-only',action='store_true')
args=parser.parse_args()
assert not (args.semantic_only and args.representations_only)
VALID=VALID_ROOT/'selective' if args.batch=='selective' else VALID_ROOT
PREFIX='selective-' if args.batch=='selective' else ''

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
special=module(ROOT/'agents/special_control_restore_20261102/validation/run.py','special_results_review')
ready=json.loads((VALID_ROOT.parent/('binary-selective-ready.json' if args.batch=='selective' else 'binary-ready.json')).read_text())
assert sha(Path(ready['binary']))==ready['binary_sha256']
assert sha(Path(ready['libz3']))==ready['libz3_sha256']
new_ir=ROOT/'agents/encoding_constraint_isolation_20261102/saturation/generation/rv64d_v128_e64/rv64d_v128_e64.ir'
source=new_ir.read_text();count=0;initial_checks=0;semantic_checks=0;rows=[]
for job in ([] if args.representations_only else special.jobs()):
    dest=VALID/'semantic'/job['name'];record=json.loads((dest/'result.json').read_text());cmd=record['command']
    ir=Path(cmd[cmd.index('-A')+1]);config=Path(cmd[cmd.index('-C')+1])
    assert record['binary_sha256']==ready['binary_sha256'] and sha(ir)==record['ir_sha256'] and sha(config)==record['config_sha256']
    assert ir.read_text()==(source if job['fields'] is None else special.wrapper(source,job))
    assert record['exit_code']==0 and record['pass_complete'] and record['semantic_pass']
    paths=list((dest/'run/output').glob('*.json'));assert len(paths)==1
    data=json.loads(paths[0].read_text());assert sha(paths[0])==record['output_sha256'];assert record['summary']==data['summary']
    assert data['summary']['status']=='finished' and all(data['summary'][key]==0 for key in special.PARTIAL)
    for case in data['gen']:
        for key,value in job['initial'].items():
            assert key in case['isa-state-complete'],(job['name'],key)
            expected=value if isinstance(value,int) else int(value,16)
            assert special.bits(case['isa-state-complete'][key])==expected,(job['name'],key)
            initial_checks+=1
    passed,detail=special.inspect(job,data);assert passed and detail==record['semantic_detail']
    count+=len(data['gen']);semantic_checks+=detail['check_count']
    rows.append({'job':job['name'],'gen':len(data['gen']),'semantic_checks':detail['check_count'],'json_sha256':sha(paths[0])})
representations=[];checks=0;illegal_rejections=0
for name in ([] if args.semantic_only else ['bf16-vl0','bf16-vl1','c-addi4spn','make-smoke']):
    dest=VALID/name if name=='make-smoke' else VALID/'representations'/name;record=json.loads((dest/'result.json').read_text());raw=json.loads((dest/'toolchains/results.json').read_text())
    paths=list((dest/('output' if name=='make-smoke' else 'run/output')).glob('*.json'));assert len(paths)==1;data=json.loads(paths[0].read_text())
    assert record['pass'] and record['exit_code']==0 and record['binary_sha256']==ready['binary_sha256']
    assert record['ir_sha256']==sha(new_ir)
    command=record['command']
    if name=='make-smoke':
        config=Path(next(arg.split('=',1)[1] for arg in command if arg.startswith('ISA_CONFIG=')))
    else:
        config=Path(command[command.index('-C')+1])
    assert sha(config)==record['config_sha256']
    assert sha(paths[0])==record['output_sha256']==raw['sha256']
    assert data['summary']['status']=='finished' and all(data['summary'][key]==0 for key in special.PARTIAL)
    for check in raw['checks']:
        assert check['pass_']
        case=data['gen'][check['index']];bits=case['instruction-representations']['encoding']['bytes-le']
        assert check['expected']==bits
        if check['expected_rejection']:
            assert check['exit']!=0 and check['driver']=='clang' and check['kind']=='mnemonic' and 'Illegal_Instruction' in case['ret_val']
            illegal_rejections+=1
        else:
            assert check['exit']==0 and check['actual']==bits
            binary=dest/'toolchains'/f"{check['index']}-{check['driver']}-{check['kind']}.bin"
            assert binary.read_bytes()==bytes.fromhex(bits)
        checks+=1
    if name=='make-smoke':
        job=next(job for job in special.jobs() if job['name']=='fleq-S-qNaN')
        passed,detail=special.inspect(job,data);assert passed and detail==record['semantic_detail']
        assert record['seed_intercepted'] and sha(dest/'make.log')==record['make_log_sha256']
    if name=='c-addi4spn':
        assert len(data['gen'])==1
        item=data['gen'][0];encoding=int(item['instruction-representations']['encoding']['hex'],16)
        rd=8+((encoding>>2)&7);imm=(((encoding>>11)&3)<<4)|(((encoding>>7)&15)<<6)|(((encoding>>6)&1)<<2)|(((encoding>>5)&1)<<3)
        assert imm>0 and 'Retire_Success' in item['ret_val'] and special.bits(item['isa-state-post']['x'+str(rd)])==(special.bits(item['isa-state-complete']['x2'])+imm)&((1<<64)-1)
    representations.append({'job':name,'gen':len(data['gen']),'checks':len(raw['checks']),'json_sha256':sha(paths[0])})
result={'batch':args.batch,'source_commit':ready['source_commit'],'semantic_requested':not args.representations_only,'representation_requested':not args.semantic_only,'semantic_jobs':len(rows),'semantic_gen':count,'semantic_assertions_repeated':semantic_checks,'initial_values_verified':initial_checks,'representation_jobs':representations,'toolchain_checks':checks,'expected_illegal_clang_rejections':illegal_rejections,'semantic_rows':rows,'pass':True}
(HERE/(PREFIX+('representation-results-checks.json' if args.representations_only else 'directed-results-checks.json'))).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='semantic_rows'},ensure_ascii=False,indent=2))
