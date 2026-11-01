#!/usr/bin/env python3
"""核对真实IR行为分界增加Jump；不把已有类型检查Jump当作恢复成功。"""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path);a=p.parse_args()
names=('zfp_min_pure','zfp_max_pure','zfp_minm_pure','zfp_maxm_pure','zriscv_f32_symbolic_bits','zvalid_fp_op','zillegal_fp_normal','zillegal_fp_reduction','zfp_class_onehot_pure','zexecute')
def counts(path):
 text=path.read_text();out={}
 for name in names:
  body=re.search(r'(?ms)^fn '+name+r'\([^\n]*\) \{\n.*?^\}',text)
  assert body,name
  out[name]=len(re.findall(r'\bjump\b',body[0]))
 return out
old,new=counts(a.baseline),counts(a.candidate)
r={n:{'baseline':old[n],'candidate':new[n],'increased':new[n]>old[n]} for n in names}
print(json.dumps(r,indent=2))
raise SystemExit(not all(x['increased'] for x in r.values()))
