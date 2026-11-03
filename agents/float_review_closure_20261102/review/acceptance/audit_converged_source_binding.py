#!/usr/bin/env python3
"""Bind applied final model bytes to approved 77-data-condition candidates."""
import hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[3];T=H.parents[1];D=T/'baseline-0008fae/reduction/new-policy';M=ROOT/'.worktree/sail-riscv-float-converged-20261103'
BASE='e9d69d2f28586c089244c8e37ee4c904c5114458';HEAD='0f7b8fbc6724103f91f929ef6918f123df75d6c9'
git=lambda *x:subprocess.check_output(['git','-C',str(M),*x])
sha=lambda b:hashlib.sha256(b).hexdigest()
paths={
'model/core/ieee_fp_exceptions.sail':('candidate-ieee_fp_exceptions.sail','7ed9529baac57717875ea49e8fff5130d3ec611f824aa71483b2b856d67c96b4',33),
'model/extensions/V/vext_fp_utils_insts.sail':('candidate-vext_fp_utils_insts.sail','34191de93086708b44f552606b39878e1ad68be07c67fb2321eb7bec1b1172e1',8),
'model/extensions/FD/softfloat_symbolic_f16.sail':('wrappers-softfloat_symbolic_f16.sail','715795790c0efb100806c0a82195e137c4de66c4a9614baac9ee2b0b333a0646',12),
'model/extensions/FD/softfloat_symbolic_f32.sail':('wrappers-softfloat_symbolic_f32.sail','ffe71d8f99652a20f9c7c6d969648af75bdc575ee9f2ca34e459fdfa879c5e17',12),
'model/extensions/FD/softfloat_symbolic_f64.sail':('wrappers-softfloat_symbolic_f64.sail','b5b8ea9e4723e647fa74ea8ebfa47129106993a3a99d9df80105f9b3eab545ce',12)}
assert git('rev-parse','HEAD').decode().strip()==HEAD
assert not git('status','--porcelain')
assert set(git('diff','--name-only',BASE,HEAD).decode().splitlines())==set(paths)
def functions(s):
 matches=list(re.finditer(r'^function (\w+)',s,re.M))
 return {m[1]:s[m.start():matches[i+1].start() if i+1<len(matches) else len(s)] for i,m in enumerate(matches)}
def braced_body(s):
 start=s.find('{')
 if start<0:return s
 depth=0
 for i in range(start,len(s)):
  depth+=(s[i]=='{')-(s[i]=='}')
  if depth==0:return s[:i+1]
 return s
rows=[];before_core=after_core=None
for path,(candidate,want,count) in paths.items():
 before=git('show',BASE+':'+path);after=git('show',HEAD+':'+path)
 assert after==(M/path).read_bytes()==(D/candidate).read_bytes() and sha(after)==want
 a,b=before.decode(),after.decode();assert len(re.findall(r'\bif\b',a))-len(re.findall(r'\bif\b',b))==count
 af,bf=functions(a),functions(b);assert set(af)==set(bf)
 changed=[n for n in af if braced_body(af[n])!=braced_body(bf[n])]
 if path.endswith('ieee_fp_exceptions.sail'):before_core,after_core=af,bf;assert len(changed)==18
 elif 'softfloat_symbolic_' in path:
  assert len(changed)==4
  for n in af:
   if 'to_f16' in n.lower() or 'to_f32' in n.lower():assert af[n]==bf[n]
 rows.append({'path':path,'sha256':want,'removed_source_if_tokens':count,'changed_functions':changed})
assert sum(r['removed_source_if_tokens'] for r in rows)==77
# Every core function except the eighteen approved arithmetic helpers is
# unchanged, including all eleven other finite/valid gates and ROD jam.
for n in before_core:
 if before_core[n]!=after_core[n]:
  assert re.fullmatch(r'ieee_(add|sub|mul|div|sqrt|fma)(16|32|64)_exceptions',n)
  ca=Counter(re.findall(r'\bif\s+([^\n]+?)\s+then',before_core[n]));cb=Counter(re.findall(r'\bif\s+([^\n]+?)\s+then',after_core[n]))
  for gate in ['finite','valid']:assert ca[gate]==cb[gate]
  # Per-source operand classifications are evaluated in the original order.
  calls=lambda s:re.findall(r'ieee_operand_invalid\([^\n;]+?\)',s)
  assert calls(before_core[n])==calls(after_core[n])
for path in ['model/extensions/FD/fdext_regs.sail','model/extensions/FD/dext_insts.sail','model/extensions/FD/zfh_insts.sail']:
 assert git('show',BASE+':'+path)==git('show',HEAD+':'+path)
assert git('show',HEAD+':model/extensions/V/vext_fp_utils_insts.sail')==git('show','6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a:model/extensions/V/vext_fp_utils_insts.sail')
out={'scope':'Applied candidate bytes and OPEN/NaN/trap source preservation only; new strict/IR/dynamic separate','base_commit':BASE,'model_commit':HEAD,'files':rows,'removed_source_if_tokens':77,'source_if_count_is_not_independent_fork_count':True,'non_target_model_bytes_unchanged':True,'open_changed_state_file_unchanged':True,'open_core_gates_preserved':True,'nan_operand_calls_preserved':True,'rod_mode_functions_unchanged':True,'native_trap_legality_files_unchanged':True,'existing_narrow_outer_overflow_open_restored_to_6202_bytes':True,'pass':True}
(H/'converged-source-binding-independent.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
