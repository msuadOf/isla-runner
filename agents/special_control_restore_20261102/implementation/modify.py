#!/usr/bin/env python3
"""只恢复已识别的NaN行为边界和活动运算gate。"""
from pathlib import Path
import re,json
m=Path('.worktree/runner-float/sail-riscv/model');out=Path('agents/special_control_restore_20261102/implementation')
original={}
def read(p):
 original[p]=p.read_text();return original[p]
# 结果NaN规范化：仅匹配明确NaN选择，不触碰整数饱和条件。
for form in ('f16','f32','f64'):
 p=m/f'extensions/FD/softfloat_symbolic_{form}.sail';s=read(p)
 s,n=re.subn(r'ite\(((?:fp\d+_is_nan|ieee_is_nan)\([^()]+\)), (riscv_canonical_nan(?:16|32|64|_bf16)\(\)), (fp\d+_to_ieee\([^()]+\)|raw|rod_bits|bits)\)',r'(if \1 then \2 else \3)',s)
 p.write_text(s)
# 每个源分类是行为决定点；底层predicate不改。
p=m/'core/ieee_fp_exceptions.sail';s=read(p)
marker='// Shared Sail flag order is NV bit 0, DZ bit 1, OF bit 2, UF bit 3, NX bit 4.'
helper='''// NaN 类别决定当前操作数是否产生 invalid；各源分别求值后再合并。
val ieee_operand_invalid : forall 'n, is_fp_bits('n). (bool, bits('n)) -> bool
function ieee_operand_invalid(signaling, raw) =
  if ieee_is_nan(raw) then {
    if ieee_is_snan(raw) then true else signaling
  } else false

'''
assert marker in s;s=s.replace(marker,helper+marker)
# 仅异常事实函数中的实际sNaN行为调用点，不改predicate和新helper。
pos=s.index('function ieee_eq32_exceptions');s=s[:pos]+s[pos:].replace('ieee_is_snan(a)','ieee_operand_invalid(false, a)').replace('ieee_is_snan(b)','ieee_operand_invalid(false, b)').replace('ieee_is_snan(c)','ieee_operand_invalid(false, c)')
for width in (16,32,64):
 for kind in ('eq','lt'):
  pat=r'function ieee_'+kind+str(width)+r'_exceptions[^\n]*(?:\n(?!function |//)[^\n]*)*'
  old=re.search(pat,s)[0]
  signature=old.split(' =')[0]
  arg='false' if kind=='eq' else 'signaling'
  new=signature+' = {\n  let a_invalid = ieee_operand_invalid('+arg+', a);\n  let b_invalid = ieee_operand_invalid('+arg+', b);\n  ieee_empty_exceptions(strict_or_bool(a_invalid, b_invalid))\n}\n'
  s=s.replace(old,new)
p.write_text(s)
# BF16独立输入分类；NaN不是IEEE16，仍用原8/7字段。
p=m/'extensions/bfloat16/zfbfmin_utils.sail';s=read(p)
old='  (ite(is_snan, nvFlag(), zeros()), ite(is_nan, canonical_NaN_S(), v @ zeros(16)))'
new='  if is_nan then {\n    if is_snan then (nvFlag(), canonical_NaN_S())\n    else (zeros(), canonical_NaN_S())\n  } else (zeros(), v @ zeros(16))'
assert old in s;s=s.replace(old,new);p.write_text(s)
# 20真实运算循环：移动全部纯运算/写回/flags到活动分支，初始结果保留不活动lane。
counts={}
for name in ('V/vext_fp_insts.sail','V/vext_fp_vm_insts.sail','V/vext_fp_red_insts.sail','bfloat16/zvfbfmin_insts.sail','bfloat16/zvfbfwma_insts.sail'):
 p=m/'extensions'/name;s=read(p);count=0
 pat=r'  foreach \(i from 0 to \([^\n]+\)\) \{\n(?P<body>.*?)\n  \};'
 def loop(match):
  global count
  b=match['body']
  if 'ite(mask[i]' not in b:return match[0]
  count+=1
  # 删掩码选择只保留真分支，所有动作移入if。
  b=re.sub(r'ite\(mask\[i\] == 0b1, ([^,\n]+), 0b00000\)',r'\1',b)
  b=b.replace('sum = ite(mask[i] == 0b1, candidate, sum)','sum = candidate')
  b=b.replace('result[i] = masked_select(mask[i], isla_bool_to_bit(lane_value), initial_result[i]);','result[i] = isla_bool_to_bit(lane_value);')
  b=b.replace('candidates[i] = lane_value','result[i] = lane_value')
  assert 'ite(mask[i]' not in b and 'masked_select(mask[i]' not in b
  return match[0].split('\n')[0]+'\n    if mask[i] == 0b1 then {\n'+'\n'.join('  '+line for line in b.splitlines())+'\n    }\n  };'
 s=re.sub(pat,loop,s,flags=re.S)
 s=s.replace('  var candidates = initial_result;\n','')
 s=s.replace('  result = vector_select_masked(mask, initial_result, candidates);\n','')
 # BF16 own candidates are result.
 if 'bfloat16' in name:s=s.replace('  result = vector_select_masked(mask, initial_result, result);\n','')
 # BF16 VF scalar conversion only when an active lane actually uses it.
 if name.endswith('zvfbfwma_insts.sail'):
  old='  let (rs1_fflags, rs1_val) = bf16_to_f32(F_BF16(rs1));\n'
  assert old in s;s=s.replace(old,'')
  anchor='    if mask[i] == 0b1 then {\n      let (vs2_flags, vs2_elem) = bf16_to_f32(vs2_val[i]);\n      let (op_flags, elem) = riscv_f32MulAdd(rm_3b, vs2_elem, rs1_val, vd_val[i]);'
  assert anchor in s;s=s.replace(anchor,'    if mask[i] == 0b1 then {\n      let (rs1_fflags, rs1_val) = bf16_to_f32(F_BF16(rs1));\n      let (vs2_flags, vs2_elem) = bf16_to_f32(vs2_val[i]);\n      let (op_flags, elem) = riscv_f32MulAdd(rm_3b, vs2_elem, rs1_val, vd_val[i]);')
 p.write_text(s);counts[name]=count
assert sum(counts.values())==20,counts
# 保存原文供region迁移，按文件source映射，不猜行号。
(out/'original.json').write_text(json.dumps({str(p.relative_to(m)):s for p,s in original.items()}))
(out/'scope.json').write_text(json.dumps({'active_gates':counts,'source_files':list(str(p.relative_to(m)) for p in original)},indent=2))
