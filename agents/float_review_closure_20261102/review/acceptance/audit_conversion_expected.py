#!/usr/bin/env python3
"""Check fixture bits/flags with exact rational FP decoding and integer rounding."""
from fractions import Fraction
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[4]
INPUT=ROOT/'agents/float_review_closure_20261102/validation/conversions/oracle-rows.json'
OUT=Path(__file__).resolve().parent/'conversions-expected-independent.json'

def expected(row):
    width=row['source_width']; raw=row['source_bits']; target=row['result_width']; rm=row['rm']
    expwidth,fracwidth={16:(5,10),32:(8,23),64:(11,52)}[width]
    sign=raw>>(width-1); exponent=(raw>>fracwidth)&((1<<expwidth)-1); fraction=raw&((1<<fracwidth)-1)
    signed=row['native_target'].startswith('i'); low=-(1<<(target-1)) if signed else 0; high=(1<<(target-int(signed)))-1
    if exponent==(1<<expwidth)-1:
        value=high if fraction or not sign else low
        return value&((1<<target)-1),16
    scale=(exponent or 1)-((1<<(expwidth-1))-1)-fracwidth
    value=Fraction(fraction+((1<<fracwidth) if exponent else 0))
    value=value*(1<<scale) if scale>=0 else value/(1<<-scale)
    if sign:value=-value
    lower=value.numerator//value.denominator; upper=lower+(value.denominator!=1)
    if rm==0:
        distance=value-lower
        rounded=lower if distance<Fraction(1,2) else upper if distance>Fraction(1,2) else lower if lower%2==0 else upper
    elif rm==1:rounded=lower if value>=0 else upper
    elif rm==2:rounded=lower
    elif rm==3:rounded=upper
    elif rm==4:
        distance=value-lower
        rounded=lower if distance<Fraction(1,2) else upper if distance>Fraction(1,2) else lower if value<0 else upper
    else:raise ValueError(rm)
    if rounded<low:return low&((1<<target)-1),16
    if rounded>high:return high,16
    return rounded&((1<<target)-1),int(value!=rounded)

def main():
    rows=json.loads(INPUT.read_text());bad=[]
    for row in rows:
        actual=expected(row);want=(row['result_bits'],row['flags'])
        if actual!=want:bad.append({'helper':row['helper'],'label':row['label'],'rm':row['rm'],'independent':actual,'fixture':want})
    out={'scope':'Exact rational independent expected-value check only; new IR not executed','input_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),'rows':len(rows),'failures':bad}
    OUT.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));assert not bad
if __name__=='__main__':main()
