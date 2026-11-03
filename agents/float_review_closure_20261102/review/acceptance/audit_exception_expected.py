#!/usr/bin/env python3
"""Replay every exception fixture oracle command; no Isla execution."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
INPUT=ROOT/'agents/float_review_closure_20261102/validation/exceptions/expected.json'
ORACLE=ROOT/'.tmp/unified-backend-crosscheck/oracle-build/oracle'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def query(args):
    r=json.loads(subprocess.check_output([str(ORACLE),*args],text=True))
    return int(r['result_bits'],16),int(r['flags'],16)
def canonical(raw,width):
    e,f={16:(5,10),32:(8,23),64:(11,52)}[width]
    return {16:0x7e00,32:0x7fc00000,64:0x7ff8000000000000}[width] if (raw>>f)&((1<<e)-1)==(1<<e)-1 and raw&((1<<f)-1) else raw
def main():
    data=json.loads(INPUT.read_text());assert digest(ORACLE)==data['oracle_binary_sha256'];checks=[]
    for row in data['cases']:
        raw,flags=query(row['oracle_argv']);ok=(raw,flags)==(int(row['oracle_raw_bits'],16),int(row['expected_flags'],16)) and canonical(raw,row['width'])==int(row['expected_bits'],16)
        checks.append({'name':row['name'],'match':ok})
    for row in data['bf16']+data.get('vectors',[]):
        flags=0;ok=True
        for lane in row['lanes']:
            if lane['active']:
                raw,oneflags=query(lane['oracle_argv']);flags|=oneflags
                ok&=canonical(raw,row.get('width',32))==int(lane['bits'],16) and oneflags==int(lane['flags'],16)
        checks.append({'name':row['name'],'match':ok and flags==int(row['expected_flags'],16)})
    out={'scope':'Independent replay of expected-value SoftFloat calls only; no new IR executed','input_sha256':digest(INPUT),'oracle_sha256':digest(ORACLE),'rows':len(checks),'failures':[c for c in checks if not c['match']],'checks':checks}
    (HERE/'expected-independent.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='checks'});assert not out['failures']
if __name__=='__main__':main()
