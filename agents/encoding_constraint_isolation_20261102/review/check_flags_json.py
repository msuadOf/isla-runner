#!/usr/bin/env python3
"""对初版de00adb的完整新/旧flags Clause独立重核数值、boxing、flags及编码。"""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
TOPIC=ROOT/'agents/encoding_constraint_isolation_20261102'
parser=argparse.ArgumentParser()
parser.add_argument('--batch',choices=['original','selective'],default='original')
parser.add_argument('--jobs',choices=['old_flags','new_flags'],nargs='+',default=['old_flags','new_flags'])
args=parser.parse_args()
BASE=TOPIC/'validation/runs/selective' if args.batch=='selective' else TOPIC/'validation/runs'
PREFIX='selective-' if args.batch=='selective' else ''
READY=json.loads((TOPIC/('binary-selective-ready.json' if args.batch=='selective' else 'binary-ready.json')).read_text())
ORACLE=ROOT/'.tmp/unified-backend-crosscheck/oracle-build/oracle'
EXPECTED_BINARY=READY['binary_sha256']
PARTIAL=['sampled-paths','errors','execution-timeouts','smt-timeouts','unfinished-paths','omitted-cases','model-query-timeouts','pending-batches']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bits(s):return int(re.fullmatch(r"\d+'h([0-9a-fA-F_]+)",s)[1].replace('_',''),16)
def unbox(raw):return raw&0xffffffff if raw>>32==0xffffffff else 0x7fc00000
def canonical(raw):return 0x7fc00000 if raw&0x7f800000==0x7f800000 and raw&0x7fffff else raw
@lru_cache(None)
def calculate(op,rm,a,b):
    value=json.loads(subprocess.check_output([str(ORACLE),'--op',op,'--fmt','f32','--rm',str(rm),'--a',hex(a),'--b',hex(b)],text=True))
    return canonical(int(value['result_bits'],16)),int(value['flags'],16)
records={}
for job in args.jobs:
    folder=BASE/job;r=json.loads((folder/'result.json').read_text());command=r['command']
    ir=Path(command[command.index('-A')+1]);config=Path(command[command.index('-C')+1]);path=ROOT/r['output_json']
    assert r['binary_sha256']==EXPECTED_BINARY
    assert r['exit_code']==0 and not r['outer_timeout'] and r['seed']==17 and r['seed_intercepted']
    assert command[command.index('-T')+1]=='1' and command[command.index('--tastic')+1]=='qffp' and command[command.index('--smt-timeout')+1]=='7200s'
    assert sha(ir)==r['ir_sha256'] and sha(config)==r['config_sha256'] and sha(path)==r['output_sha256']
    assert sha(folder/'seed-intercept.log')==r['seed_log_sha256'] and sha(folder/'run.log')==r['run_log_sha256']
    data=json.loads(path.read_text());assert data['summary']==r['summary'] and data['summary']['status']=='finished'
    assert all(data['summary'][key]==0 for key in PARTIAL)
    counts=Counter();ops=Counter();checks=0;rows=[]
    for index,item in enumerate(data['gen']):
        pre=item['isa-state-complete'];post=item['isa-state-post'];word=bits(item['test-ins-encdec']);enc=item['instruction-representations']['encoding']
        assert int(enc['hex'],16)==word and int(enc['bits'],2)==word and bytes.fromhex(enc['bytes-le'])==word.to_bytes(4,'little');checks+=3
        mnemonic=item['test-ins'];name=mnemonic.split()[0];op={'fadd.s':'add','fsub.s':'sub','fmul.s':'mul','fdiv.s':'div'}[name]
        rd,rs1,rs2=map(int,re.findall(r'f(\d+)',mnemonic));mode=word>>12&7
        assert word&0x7f==0x53 and word>>25=={'add':0,'sub':4,'mul':8,'div':12}[op]
        assert (word>>7&31,word>>15&31,word>>20&31)==(rd,rs1,rs2);checks+=2;ops[op]+=1
        before=bits(pre['fcsr']);after=bits(post['fcsr'])
        if 'Illegal_Instruction' in item['ret_val']:
            counts['illegal']+=1
            assert before==after and all(bits(pre['f'+str(reg)])==bits(post['f'+str(reg)]) for reg in range(32));checks+=33
            continue
        assert item['ret_val']=='Retire_Success(())'
        rm=before>>5&7 if mode==7 else mode;assert rm in range(5);checks+=1
        a=unbox(bits(pre['f'+str(rs1)]));b=unbox(bits(pre['f'+str(rs2)]));expected,flags=calculate(op,rm,a,b)
        assert bits(post['f'+str(rd)])==0xffffffff00000000|expected,(job,index,mnemonic)
        assert after==before|flags,(job,index,mnemonic,hex(before),hex(flags),hex(after));checks+=2
        for reg in range(32):
            if reg!=rd:assert bits(pre['f'+str(reg)])==bits(post['f'+str(reg)]);checks+=1
        counts['retired']+=1;counts['changed' if before&31!=after&31 else 'same']+=1
        if after&16 and not before&16:counts['NV_new']+=1
        counts['invalid_box_input']+=int(bits(pre['f'+str(rs1)])>>32!=0xffffffff or bits(pre['f'+str(rs2)])>>32!=0xffffffff)
        rows.append({'index':index,'op':op,'rm':rm,'a':hex(a),'b':hex(b),'result':hex(expected),'flags_added':flags})
    records[job]={'binary_sha256':r['binary_sha256'],'ir_sha256':r['ir_sha256'],'config_sha256':r['config_sha256'],'json_sha256':sha(path),'wall_s':r['wall_s'],'user_s':r['user_s'],'sys_s':r['sys_s'],'gen':len(data['gen']),'counts':dict(counts),'operations':dict(ops),'checks':checks,'pass':True,'witnesses':rows}
(HERE/(PREFIX+'flags-json-checks.json')).write_text(json.dumps({'batch':args.batch,'source_commit':READY['source_commit'],'oracle_sha256':sha(ORACLE),'unique_oracle_calls':calculate.cache_info().currsize,'runs':records},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({job:{k:v for k,v in row.items() if k!='witnesses'} for job,row in records.items()},ensure_ascii=False,indent=2))
