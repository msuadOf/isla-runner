#!/usr/bin/env python3
"""按实际IR的失败边与顺序核五条RNE专映射及其generic后继。"""
from pathlib import Path
import re,json,hashlib
R=Path.cwd();O=R/'agents/float_review_closure_20261102/review/model';G=R/'agents/float_review_closure_20261102/validation/generation/model-21418d0'
ops={'zFCVT_D_S':('zF_UN_RM_FF_TYPE_D','fcvt.d.s'),'zFCVT_D_W':('zF_UN_RM_XF_TYPE_D','fcvt.d.w'),'zFCVT_D_WU':('zF_UN_RM_XF_TYPE_D','fcvt.d.wu'),'zFCVT_S_H':('zF_UN_RM_FF_TYPE_H','fcvt.s.h'),'zFCVT_D_H':('zF_UN_RM_FF_TYPE_H','fcvt.d.h')}
rows=[]
for config in ('rv64d_v128_e64','rv32d','rv64d_v256_e64','rv64d_v512_e64'):
 p=G/config/(config+'.ir');text=p.read_text();functions={n:[l.strip() for l in b.splitlines() if l.strip()] for n,b in re.findall(r'(?ms)^fn ([^(\n]+)\([^\n]*\) \{\n(.*?)^\}',text)}
 for name in ('zassembly_forwards','zassembly_forwards_infallible','zassembly_forwards_matches'):
  ls=functions[name]
  for op,(ctor,mnemonic) in ops.items():
   pcs=[i for i,l in enumerate(ls) if l.startswith('jump @neq('+op+', ')];assert len(pcs)==1
   pc=pcs[0];fail=int(re.search(r'goto (\d+)',ls[pc])[1]);start=pc-2
   assert ls[start].startswith('jump zargz3 is '+ctor+' goto '+str(fail)+' ')
   assert ls[pc-1].startswith('jump @neq(zRM_RNE, zargz3 as '+ctor+'.') and int(re.search(r'goto (\d+)',ls[pc-1])[1])==fail
   assert '.ztuplez3z5bv5_z5enumz0zzrounding_mode_z5bv5_z5enumz0' in ls[pc]
   body=ls[pc+1:fail];assert body[-1].startswith('goto ') and int(body[-1].split()[1].rstrip(';'))>fail
   if name.endswith('_matches'):assert any(' = true ' in l for l in body)
   else:
    assert any('zstring_append("'+mnemonic+'", ' in l for l in body)
    assert not any('%enum zrounding_mode' in l or 'zfrm_mnemonic_forwards(' in l for l in body)
   # Failed op/RM checks enter the next specific case, then the original generic.
   generic=fail
   while ls[generic+1].startswith('jump @neq(zRM_RNE, '):
    assert ls[generic].startswith('jump zargz3 is '+ctor+' goto ')
    generic=int(re.search(r'goto (\d+)',ls[generic])[1])
   assert generic>start and ls[generic].startswith('jump zargz3 is '+ctor+' goto ')
   generic_end=int(re.search(r'goto (\d+)',ls[generic])[1]);gb=ls[generic:generic_end]
   assert any('%enum zrounding_mode' in l for l in gb)
   if not name.endswith('_matches'):assert any('zfrm_mnemonic_forwards(' in l for l in gb)
   rows.append({'config':config,'function':name,'op':op,'rm':'RM_RNE','specific_pc':start,'failure_pc':fail,'generic_pc':generic,'no_rm_specific':True,'generic_rm_preserved':True})
report={'status':'PASS actual IR specific-first ordering','model_commit':'21418d0b0d4942fae20061ed580ee04aff4a8a61','checks':len(rows),'rows':rows,'scope':'实际IR三函数中五个具体RM_RNE模式先于同构造器generic；失败边保留非零RM和其他op。实际执行probe另见assembly-source-review.json。'}
(O/'assembly-ir-order-21418d0.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS',len(rows),'actual IR ordering checks')
