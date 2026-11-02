#!/usr/bin/env python3
"""独立以精确有理数核对新完整 VFUNARY0 的 f16→i16 见证。"""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import json
import re
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--batch',choices=['original','selective'],default='original')
args=parser.parse_args()
BASE=ROOT/'agents/encoding_constraint_isolation_20261102'
FOLDER=BASE/'validation/runs/selective/new_sat' if args.batch=='selective' else BASE/'validation/runs/new_sat'
PATH=FOLDER/'output/rv64_zVFUNARY0.json'
PREFIX='selective-' if args.batch=='selective' else ''
def bits(s):
    width, base, digits=re.fullmatch(r"(\d+)'([hbd])([0-9a-fA-F_]+)",s).groups()
    return int(digits.replace('_',''),{'h':16,'b':2,'d':10}[base])
def rounded(v,rm):
    floor=v.numerator//v.denominator
    ceil=-((-v.numerator)//v.denominator)
    if rm==1:return int(v)
    if rm==2:return floor
    if rm==3:return ceil
    assert rm in (0,4)
    delta=v-floor
    if delta<Fraction(1,2):return floor
    if delta>Fraction(1,2):return ceil
    return (floor if floor%2==0 else ceil) if rm==0 else (ceil if v>=0 else floor)
def convert(raw,rm):
    sign=raw>>15; exp=raw>>10&31; fraction=raw&1023
    if exp==31:
        return (0x7fff if fraction or not sign else 0x8000),16,('nan' if fraction else 'infinity')
    mantissa=fraction if exp==0 else 1024+fraction
    value=Fraction(mantissa,1<<24) if exp==0 else Fraction(mantissa)*Fraction(2)**(exp-25)
    if sign:value=-value
    value_int=rounded(value,rm)
    if value_int>32767:return 0x7fff,16,'positive-overflow'
    if value_int< -32768:return 0x8000,16,'negative-overflow'
    return value_int&65535,int(value_int!=value),'in-range'

record=json.loads((FOLDER/'result.json').read_text())
ready=json.loads((BASE/('binary-selective-ready.json' if args.batch=='selective' else 'binary-ready.json')).read_text())
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert record['exit_code']==0 and not record['outer_timeout'] and record['seed']==17 and record['seed_intercepted']
assert record['binary_sha256']==ready['binary_sha256'] and record['z3_sha256']==ready['libz3_sha256']
command=record['command']
assert sha(Path(command[command.index('-A')+1]))==record['ir_sha256']
assert sha(Path(command[command.index('-C')+1]))==record['config_sha256']
assert sha(PATH)==record['output_sha256'] and sha(FOLDER/'seed-intercept.log')==record['seed_log_sha256']
data=json.loads(PATH.read_text());assert data['summary']==record['summary'] and data['summary']['status']=='finished'
assert not any(data['summary'][key] for key in ['sampled-paths','errors','execution-timeouts','smt-timeouts','unfinished-paths','omitted-cases','model-query-timeouts','pending-batches'])
counts=Counter();checks=0;rows=[]
for index,item in enumerate(data['gen']):
    pre=item['isa-state-complete'];post=item['isa-state-post'];word=bits(item['test-ins-encdec'])
    for reg,expected in [('vtype',8),('vl',1),('vstart',0)]:assert bits(pre[reg])==expected;checks+=1
    enc=item['instruction-representations']['encoding'];assert int(enc['hex'],16)==word;assert int(enc['bits'],2)==word
    assert bytes.fromhex(enc['bytes-le'])==word.to_bytes(4,'little');checks+=3
    mnemonic=item['test-ins']; op=mnemonic.split()[0]
    selector={'vfcvt.xu.f.v':0,'vfcvt.x.f.v':1,'vfcvt.f.xu.v':2,'vfcvt.f.x.v':3,'vfcvt.rtz.xu.f.v':6,'vfcvt.rtz.x.f.v':7}[op]
    assert word&0x7f==0x57 and word>>26==0x12 and (word>>12)&7==1 and (word>>15)&31==selector;checks+=1
    if 'Retire_Success' not in item['ret_val']:counts['illegal']+=1;continue
    counts['retired']+=1
    if op not in ['vfcvt.x.f.v','vfcvt.rtz.x.f.v']:continue
    vd=word>>7&31; vs2=word>>20&31; vm=word>>25&1
    active=bool(vm or bits(pre['vr0'])&1)
    old=bits(pre['vr'+str(vd)]);raw=bits(pre['vr'+str(vs2)])&65535;rm=1 if op.startswith('vfcvt.rtz.') else bits(pre['fcsr'])>>5&7
    expected,flags,category=convert(raw,rm) if active else (old&65535,0,'inactive')
    assert bits(post['vr'+str(vd)])==(old&~65535)|expected;checks+=1
    assert bits(post['fcsr'])==bits(pre['fcsr'])|flags;checks+=1
    assert bits(post['vstart'])==0;checks+=1
    for reg in range(32):
        if reg!=vd:assert bits(post['vr'+str(reg)])==bits(pre['vr'+str(reg)]);checks+=1
    counts[category]+=1
    rows.append({'index':index,'instruction':mnemonic,'active':active,'input':hex(raw),'rounding_mode':rm,'category':category,'expected':hex(expected),'flags_added':flags})
assert all(counts[k]>0 for k in ['positive-overflow','negative-overflow','in-range','inactive'])
result={'batch':args.batch,'source_commit':ready['source_commit'],'binary_sha256':record['binary_sha256'],'wall_s':record['wall_s'],'json_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'gen':len(data['gen']),'checks':checks,'counts':dict(counts),'f16_to_i16_rows':rows,'pass':True}
(HERE/(PREFIX+'sat-json-checks.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='f16_to_i16_rows'},ensure_ascii=False,indent=2))
