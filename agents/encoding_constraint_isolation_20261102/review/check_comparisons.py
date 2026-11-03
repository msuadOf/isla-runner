#!/usr/bin/env python3
"""独立重算初版/修订版已完成产物的五字段多重集合比较。"""
from pathlib import Path
from collections import Counter
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
VALID=ROOT/'agents/encoding_constraint_isolation_20261102/validation'
FIELDS=['test-ins','test-ins-encdec','isa-state-complete','isa-state-post','ret_val']
OLD='e95fa84208f748fb00c96260910000a950634a9d2b35b35c4bfd8b83c1b533ab'
NEW='abce451a11e0e4a8a3c9658d4a8462634f284085f219cca79f439ca176853a1a'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def compare(first,second):
    a=json.loads(first.read_text());b=json.loads(second.read_text())
    counter=lambda data:Counter(json.dumps({field:case[field] for field in FIELDS},sort_keys=True,separators=(',',':')) for case in data['gen'])
    aa,bb=counter(a),counter(b)
    assert aa==bb
    return {'initial_json_sha256':sha(first),'selective_json_sha256':sha(second),'initial_count':len(a['gen']),'selective_count':len(b['gen']),'intersection':sum((aa&bb).values()),'initial_only':sum((aa-bb).values()),'selective_only':sum((bb-aa).values()),'same_multiset':aa==bb}
def sources(first,second):
    assert first['binary_sha256']==OLD and second['binary_sha256']==NEW
    assert first['ir_sha256']==second['ir_sha256'] and first['config_sha256']==second['config_sha256']
    assert first['exit_code']==second['exit_code']==0
    assert first['summary']['status']==second['summary']['status']=='finished'

path=VALID/'selective/semantic-comparison.json';provided=json.loads(path.read_text());assert provided['fields']==FIELDS and provided['jobs']==provided['same_jobs']==56
result={'fields':FIELDS,'compared_fields_scope':'只比较列出的五个具体语义字段；不比较运行来源、顺序或未生成的输入','semantic_jobs':{},'full_clauses':{},'all_same_multiset':True,'provided_comparison_sha256':{str(path.relative_to(ROOT)):sha(path)}}
for name,row in provided['results'].items():
    initial=VALID/'semantic'/name;selective=VALID/'selective/semantic'/name
    a=json.loads((initial/'result.json').read_text());b=json.loads((selective/'result.json').read_text());sources(a,b)
    pp=list((initial/'run/output').glob('*.json'));qq=list((selective/'run/output').glob('*.json'));assert len(pp)==len(qq)==1
    actual=compare(pp[0],qq[0]);assert actual==row
    result['semantic_jobs'][name]=actual
assert sum(row['initial_count'] for row in result['semantic_jobs'].values())==provided['initial_records']==156
assert sum(row['selective_count'] for row in result['semantic_jobs'].values())==provided['selective_records']==156
for name in ['new_sat','new_flags','old_flags']:
    initial=VALID/'runs'/name;selective=VALID/'runs/selective'/name
    a=json.loads((initial/'result.json').read_text());b=json.loads((selective/'result.json').read_text());sources(a,b)
    actual=compare(ROOT/a['output_json'],ROOT/b['output_json'])
    comparison_path=selective/'semantic-comparison.json'
    if comparison_path.exists():
        claimed=json.loads(comparison_path.read_text());assert claimed['fields']==FIELDS
        assert claimed['initial_source_json_sha256']==actual['initial_json_sha256'] and claimed['selective_source_json_sha256']==actual['selective_json_sha256']
        for supplied,key in [('initial_count','initial_count'),('selective_count','selective_count'),('intersection_count','intersection'),('initial_only','initial_only'),('selective_only','selective_only'),('same_multiset','same_multiset')]:assert claimed[supplied]==actual[key]
        result['provided_comparison_sha256'][str(comparison_path.relative_to(ROOT))]=sha(comparison_path)
    else:
        assert name=='old_flags'
    result['full_clauses'][name]=actual
result['total_records_per_version']=156+sum(row['initial_count'] for row in result['full_clauses'].values())
(HERE/'semantic-comparison-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'semantic_jobs':len(result['semantic_jobs']),'semantic_records':156,'full_clause_records':{name:row['initial_count'] for name,row in result['full_clauses'].items()},'total_records_per_version':result['total_records_per_version'],'all_same_multiset':True},ensure_ascii=False,indent=2))
