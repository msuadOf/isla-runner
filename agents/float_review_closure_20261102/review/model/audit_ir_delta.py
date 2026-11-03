#!/usr/bin/env python3
"""独立核对同配置新旧 IR 的函数变化范围，不能代替 CFG 检查。"""
import argparse,hashlib,json,re
from pathlib import Path

def funcs(text):
 result={}
 for name,args,body in re.findall(r'(?ms)^fn ([^\n(]+)\(([^\n]*)\) \{\n(.*?)^\}',text):
  gensyms={arg.strip():f'PARAM{n}' for n,arg in enumerate(args.split(',')) if re.fullmatch(r'z3zE\d+',arg.strip())}
  body=re.sub(r'\bz3zE\d+\b',lambda m:gensyms.get(m.group(),m.group()),body)
  result[name]=body
 return result
def norm(s):
 s=re.sub(r'`[^;\n]*','',s)
 s=re.sub(r'(\"[^\"\n]+\.sail):\d+\.\d+-\d+\.\d+\"',r'\1:<location>\"',s)
 return re.sub(r'\s+','',s)
def expected():
 names={'zaccrue_fflags'}
 names|={'zriscv_'+n+'_pure' for n in ('f16ToI16','f16ToI8','f16ToUi8','f16ToUi16','f32ToI16','f32ToUi16')}
 names|={f'zriscv_f{fmt}To{target}' for fmt in (16,32,64) for target in ('I32','Ui32','I64','Ui64')}
 names|={'zriscv_f32ToF16','zriscv_f64ToF32'}
 names|={f'zieee_{op}{fmt}_exceptions' for fmt in (16,32,64) for op in ('add','sub','mul','div','sqrt','fma')}
 names|={f'zieee_f{fmt}_rounded_exceptions' for fmt in (16,32,64)}
 names|={'zieee_exact_threshold_exceptions','zieee_mask_exact_exceptions','zieee_fp_to_int_core'}
 names|={f'zieee_round{fmt}_exceptions' for fmt in (16,32,64)}
 names|={'zieee_convert32_to_16_exceptions','zieee_convert64_to_16_exceptions','zieee_convert64_to_32_exceptions','zieee_bf16_from_f32_exceptions','zieee_rod32_to_16','zieee_rod64_to_32'}
 return names
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--old',type=Path,required=True);p.add_argument('--new',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
a,b=funcs(args.old.read_text()),funcs(args.new.read_text())
removed=sorted(a.keys()-b.keys());added=sorted(b.keys()-a.keys())
changed={n for n in a.keys()&b.keys() if norm(a[n])!=norm(b[n])}
selected=expected()&a.keys()&b.keys()
r={'normalization':'去源位置，按签名位置重命名生成参数；保留其他表达式；normal_rm helper在主项目无调用后不进入IR、独立probe仍可使用源码定义','old_sha256':hashlib.sha256(args.old.read_bytes()).hexdigest(),'new_sha256':hashlib.sha256(args.new.read_bytes()).hexdigest(),'old_functions':len(a),'new_functions':len(b),'added':added,'removed':removed,'changed':sorted(changed),'expected_count':len(selected),'target_functions_absent_in_both':sorted(expected()-a.keys()-b.keys()),'unexpected_changes':sorted(changed-expected()),'expected_not_changed':sorted(selected-changed),'scope':'仅函数变化范围。CFG/语义与预算独立检查。'}
args.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
assert not added and removed==['zriscv_f32_to_f16_normal_rm_bits'] and changed==selected,r
print(f'PASS {len(a)}函数中仅{len(changed)}个目标变化，zexecute与所有其他调用者保持')
