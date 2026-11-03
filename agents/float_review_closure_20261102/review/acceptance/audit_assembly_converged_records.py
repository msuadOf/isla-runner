#!/usr/bin/env python3
"""Validate e9 mapping provenance and raw toolchain records independently."""
import hashlib,json,subprocess
from pathlib import Path
from audit_assembly_toolchains import SPEC,RMS
H=Path(__file__).resolve().parent;ROOT=H.parents[3];V=H.parents[1]/'validation';A=V/'assembly-fix';M=ROOT/'.worktree/sail-riscv-float-converged-20261103'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
result=read(A/'probe-converged-20261103/result.json');current=result[1]
assert result[0]['mode']=='baseline' and result[0]['exit']==1 and current['mode']=='current' and current['exit']==0 and current['passed_cases']==1104
files={'dext':'model/extensions/FD/dext_insts.sail','zfh':'model/extensions/FD/zfh_insts.sail','fext':'model/extensions/FD/fext_insts.sail','types':'model/extensions/FD/freg_type.sail'}
for k,path in files.items():
 assert sha(M/path)==current['source_sha256'][k]
 assert subprocess.check_output(['git','-C',str(M),'show','0f7b8fbc:'+path])==(M/path).read_bytes()
for mode,row in zip(['baseline','current'],result):
 b=A/'probe-converged-20261103'/mode
 for rel,key in [('probe-forward.sail','probe_sha256'),('probe-mapping-typecheck.sail','mapping_typecheck_probe_sha256'),('mapping-typecheck.log','mapping_typecheck_log_sha256'),('run.log','log_sha256')]:assert sha(b/rel)==row[key]
assert (A/'probe-converged-20261103/current/probe-forward.sail').read_bytes()==(H/'assembly-independent/current/probe-forward.sail').read_bytes()
cases=read(A/'probe-converged-20261103/current/cases.json');emitted=[x.split('\t',1)[1] for x in (A/'probe-converged-20261103/current/run.log').read_text().splitlines() if x.startswith('CASE\t')]
assert len(cases)==len(emitted)==1104
first={}
for c,s in zip(cases,emitted):first.setdefault((c['op'],c['rm']),(c,s))
r=read(A/'toolchains-converged-20261103/result.json');assert r['probe_cases_sha256']==sha(A/'probe-converged-20261103/current/cases.json') and r['probe_run_sha256']==sha(A/'probe-converged-20261103/current/run.log')
exact={'FCVT_D_S','FCVT_D_H','FCVT_S_H','FCVT_D_W','FCVT_D_WU'};controls={'FCVT_D_L','FCVT_D_LU','FCVT_S_W'}
seen=set();fallbacks=0
for row in r['rows']:
 op,rm=row['op'],row['rm'];seen.add((op,rm));c,text=first[op,rm];assert row['sail_text']==text
 fn,rs2=SPEC[op];word=(fn<<25)|(rs2<<20)|(c['rs']<<15)|(RMS[rm]<<12)|(c['rd']<<7)|0x53
 assert int(row['expected_word'],16)==word and row['clang']['exit']==0 and int(row['clang']['word'],16)==word
 if op in exact and rm!='RNE':
  assert row['gcc']['exit']!=0 and row['gcc']['word'] is None and row['gcc_exact_substitute']['exit']==0 and int(row['gcc_exact_substitute']['word'],16)==word;fallbacks+=1
 else:assert row['gcc']['exit']==0 and int(row['gcc']['word'],16)==word
assert seen=={(op,rm) for op in exact|controls for rm in RMS} and fallbacks==25
for key in ['cases_sha256','forward_log_sha256']:
 x=read(H/'assembly-toolchains-converged-independent.json')
 assert x[key]==sha(A/'probe-converged-20261103/current'/('cases.json' if key=='cases_sha256' else 'run.log'))
out={'scope':'New final converged isolated forward/C and actual string toolchains; no dynamic reverse parsing or full-model assembly coverage','model_commit':'0f7b8fbc6724103f91f929ef6918f123df75d6c9','source_hashes':current['source_sha256'],'probe_result_sha256':sha(A/'probe-converged-20261103/result.json'),'new_probe_reexecution':read(H/'assembly-converged-probe-independent.json'),'raw_toolchain_result_sha256':sha(A/'toolchains-converged-20261103/result.json'),'raw_toolchain_rows':len(seen),'raw_gnu_nonzero_exact_rejections':fallbacks,'independent_full_output_byte_checks':x['toolchain_instruction_checks'],'pass':True}
(H/'assembly-converged-records-independent.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ['source_hashes','new_probe_reexecution']})
