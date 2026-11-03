#!/usr/bin/env python3
"""Second independent source review. Does not import owner or first reviewer code."""
import hashlib,itertools,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TREE=ROOT/'.worktree/sail-riscv-general-float-by-model-20261022'
FROZEN=ROOT/'.worktree/runner-float/sail-riscv'
REL='model/core/ieee_fp_exceptions.sail'
BASE='21418d0b0d4942fae20061ed580ee04aff4a8a61'
EXPECTED='866f85a607b112d57a0ea8c6d9a85c1befb36ef11ea39b7058a252606df257cd'
def cmd(*argv):return subprocess.check_output(argv,text=True)
def sha(data):return hashlib.sha256(data).hexdigest()
original=cmd('git','-C',str(TREE),'show',BASE+':'+REL)
candidate=(TREE/REL).read_text();assert sha(candidate.encode())==EXPECTED
assert cmd('git','-C',str(TREE),'diff','--name-only').splitlines()==[REL]
assert cmd('git','-C',str(TREE),'ls-files','--others','--exclude-standard').splitlines()==[]
assert (FROZEN/REL).read_bytes()==original.encode()

# Build expected complete text independently from the immutable Git object.
expected=original
old='''  if overflow then
    ieee_exception_facts(false, false, true, underflow, inexact)
  else if underflow then
    ieee_exception_facts(false, false, false, true, inexact)
  else if inexact then
    ieee_exception_facts(false, false, false, false, true)
  else
    ieee_empty_exceptions(false)'''
assert expected.count(old)==4
expected=expected.replace(old,'  ieee_exception_facts(false, false, overflow, underflow, inexact)')
for invalid,indent,count in [('invalid_nan','    ',3),('false','      ',1)]:
 old=f'''{indent}if inexact then
{indent}  ieee_exception_facts({invalid}, false, false, false, true)
{indent}else
{indent}  ieee_empty_exceptions({invalid})'''
 assert expected.count(old)==count
 expected=expected.replace(old,f'{indent}ieee_exception_facts({invalid}, false, false, false, inexact)')
for one in ['0x0001','0x00000001']:
 old=f'''  if ieee_has_inexact(flags) then
    (flags, base_bits | {one})
  else
    (flags, base_bits)'''
 assert expected.count(old)==1
 expected=expected.replace(old,f'  (flags, ite(ieee_has_inexact(flags), base_bits | {one}, base_bits))')
assert expected.count('ieee_mask_exact_exceptions(invalid_nan, true, facts)')==6
expected=expected.replace('ieee_mask_exact_exceptions(invalid_nan, true, facts)','facts')
mask_start=expected.index('function ieee_mask_exact_exceptions(')
mask_end=expected.index('function ieee_fp_to_int_core(',mask_start)
expected=expected[:mask_start]+expected[mask_end:]
assert expected==candidate,'Complete candidate bytes differ from authorized reconstruction'

def funcs(s):
 matches=list(re.finditer(r'^function (\w+)',s,re.M))
 return {m[1]:s[m.start():matches[i+1].start() if i+1<len(matches) else len(s)] for i,m in enumerate(matches)}
a,b=funcs(original),funcs(candidate)
removed=set(a)-set(b);assert removed=={'ieee_mask_exact_exceptions'} and not(set(b)-set(a))
changed={n for n in b if a[n]!=b[n]}
expected_changed={'ieee_f16_rounded_exceptions','ieee_f32_rounded_exceptions','ieee_f64_rounded_exceptions','ieee_exact_threshold_exceptions','ieee_fp_to_int_core','ieee_round16_exceptions','ieee_round32_exceptions','ieee_round64_exceptions','ieee_convert32_to_16_exceptions','ieee_convert64_to_16_exceptions','ieee_convert64_to_32_exceptions','ieee_bf16_from_f32_exceptions','ieee_rod32_to_16','ieee_rod64_to_32'}
assert changed==expected_changed,(changed,expected_changed)
lets=lambda s:re.findall(r'^\s*let\b[^\n]*',s,re.M)
assert lets(original)==lets(candidate) and len(lets(original))==371
# All remaining if conditions must occur in identical order, removing only
# the exact, approved output selectors and the deleted mask's own gate.
conditions=lambda s:re.findall(r'\bif\s+([^\n]+?)\s+then',s)
oldconds=conditions(original);newconds=conditions(candidate)
assert len(oldconds)-len(newconds)==19
assert newconds.count('finite')==oldconds.count('finite')-1 # removed mask only
assert newconds.count('valid')==oldconds.count('valid')
assert newconds.count('ieee_is_nan(raw)')==oldconds.count('ieee_is_nan(raw)')

for o,u,n in itertools.product([False,True],repeat=3):
 old=(False,False,True,u,n) if o else (False,False,False,True,n) if u else (False,False,False,False,True) if n else (False,False,False,False,False)
 assert old==(False,False,o,u,n)
for invalid,nx in itertools.product([False,True],repeat=2):
 assert ((invalid,False,False,False,True) if nx else (invalid,False,False,False,False))==(invalid,False,False,False,nx)
for bits in range(1<<16):
 for nx in [False,True]:assert ((bits|1) if nx else bits)==(bits|(1 if nx else 0))
# NaN/sNaN use exponent-all-ones; finite uses its negation. Representative
# mantissas cover zero, signaling payload, and quiet payload for both sources.
finite_checks=0
for expwidth,fracwidth in [(8,23),(11,52)]:
 for exp in range(1<<expwidth):
  for frac in [0,1,1<<(fracwidth-1),(1<<fracwidth)-1]:
   finite=exp!=(1<<expwidth)-1;nan=not finite and frac!=0;snan=nan and not(frac>>(fracwidth-1)&1)
   invalid=snan if nan else False
   if finite:assert not invalid;finite_checks+=1
for o,u,n in itertools.product([False,True],repeat=3):
 facts=(False,False,o,u,n)
 masked=(False,False,*facts[2:]);assert masked==facts

# Verify no stale direct calls in any tracked Sail source or test fixture.
refs=subprocess.run(['git','-C',str(TREE),'grep','-n','ieee_mask_exact_exceptions','--','model','test','preserve'],capture_output=True,text=True)
assert refs.returncode==1 and not refs.stdout
subprocess.run(['git','-C',str(TREE),'diff','--check'],check=True)
out={'scope':'Second Sol exact candidate source/Boolean equivalence only; no strict/IR/dynamic or performance PASS','base_commit':BASE,'candidate_sha256':EXPECTED,'base_sha256':sha(original.encode()),'complete_file_reconstruction':'byte-for-byte equal','changed_functions':sorted(changed),'deleted_functions':sorted(removed),'unchanged_let_start_expressions':len(lets(original)),'output_conditionals_removed':18,'deleted_mask_conditionals':1,'boolean_of_uf_nx_tuples':8,'boolean_invalid_nx_tuples':4,'jam16_cases':131072,'finite_classification_checks':finite_checks,'mask_identity_tuples':8,'mask_remaining_tracked_references':0,'frozen_214_core_unchanged':True,'source_pass':True}
(HERE/'control-candidate-review.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
