#!/usr/bin/env python3
"""检查特殊行为分类和真实活动gate的源码边界；实际IR由独立审查另核。"""
from pathlib import Path
import re,json,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.worktree/runner-float/sail-riscv/model')
fail=[]
def need(ok,msg):
 if not ok: fail.append(msg)
s=(root/'core/ieee_fp_exceptions.sail').read_text()
need('function ieee_operand_invalid' in s,'缺少独立操作数NaN行为分类')
for width in (16,32,64):
 for kind in ('eq','lt'):
  b=re.search(r'function ieee_'+kind+str(width)+r'_exceptions.*?(?=\nfunction |\n//|\Z)',s,re.S)[0]
  need('ieee_operand_invalid(' in b and 'a_invalid' in b and 'b_invalid' in b,f'{kind}{width}缺独立两源分类')
for name in ('V/vext_fp_insts.sail','V/vext_fp_vm_insts.sail','V/vext_fp_red_insts.sail','bfloat16/zvfbfmin_insts.sail','bfloat16/zvfbfwma_insts.sail'):
 s=(root/'extensions'/name).read_text()
 need(not re.search(r'ite\(mask\[i\]',s),name+'仍以ITE聚合活动异常')
for name in ('f16','f32','f64'):
 s=(root/f'extensions/FD/softfloat_symbolic_{name}.sail').read_text()
 need(not re.search(r'ite\((?:fp\d+_is_nan|ieee_is_nan)\([^()]*\), riscv_canonical_nan',s),name+'仍以ITE规范化NaN')
print(json.dumps({'pass':not fail,'failures':fail},ensure_ascii=False,indent=2))
sys.exit(bool(fail))
