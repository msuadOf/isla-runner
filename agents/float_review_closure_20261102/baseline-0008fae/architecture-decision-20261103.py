#!/usr/bin/env python3
"""只读产生逐站点架构裁决：正确性证据不作性能证据。"""
from pathlib import Path
from collections import Counter
import hashlib,json,re,subprocess
R=Path.cwd();M=R/'.worktree/sail-riscv-general-float-by-model-20261022';O=R/'agents/float_review_closure_20261102/baseline-0008fae';rows=[]
def blocks(path):
 text=(M/path).read_text();clean=re.sub(r'//[^\n]*',lambda m:' '*len(m[0]),text);starts=list(re.finditer(r'^function (\w+)\b',clean,re.M));return text,[(m[1],m.start(),starts[i+1].start() if i+1<len(starts) else len(clean),clean[m.start():starts[i+1].start() if i+1<len(starts) else len(clean)]) for i,m in enumerate(starts)]
def add(path,name,line,condition,role,origin,decision,semantic,why):
 rows.append({'file':'sail-riscv/'+path,'function':name,'line_e9':line,'condition':condition,'role':role,'origin':origin,'decision':decision,'semantic_gate':semantic,'evidence_gate':'not established for added/restored fork' if decision=='OPEN' else 'not satisfied and pure data semantics' if decision=='REVERT' else 'baseline preservation or proven functional repair; not new solver optimization','reason':why,'implemented_by_this_review':False})
paths=['model/core/ieee_fp_exceptions.sail','model/extensions/FD/fdext_regs.sail','model/extensions/V/vext_fp_utils_insts.sail','model/extensions/FD/softfloat_symbolic_f16.sail','model/extensions/FD/softfloat_symbolic_f32.sail','model/extensions/FD/softfloat_symbolic_f64.sail']
for path in paths:
 text,bs=blocks(path);seen=Counter()
 for name,start,end,body in bs:
  ordinal=seen[name];seen[name]+=1
  for mt in re.finditer(r'\bif ([^\n]+?) then\b',body):
   condition=mt[1].strip();line=text[:start+mt.start()].count('\n')+1
   if path.endswith('ieee_fp_exceptions.sail'):
    if name=='ieee_operand_invalid':add(path,name,line,condition,'source_NaN_classification','present in6202; pre-round addition','KEEP','baseline special classification','本轮未改；不借纯flags回改删除既有每源NaN语义。')
    elif re.fullmatch(r'ieee_(add|sub|mul|div|sqrt|fma)(16|32|64)_exceptions',name):
     gate=condition in ('finite','valid');add(path,name,line,condition,'pure_calculation_gate' if gate else 'cause_flags_only','new control after6202','OPEN' if gate else 'REVERT','evaluation of pure numeric constraints; needs separate justification' if gate else 'pure returned NV/DZ facts; native result already computed','缺相应A/B瓶颈/时间下界；冻结保持并另审gate。' if gate else '恢复Bool原因合并，保留所有谓词/flags；无trap/状态副作用。')
    elif name=='ieee_fp_to_int_core' or name.startswith(('ieee_round','ieee_convert','ieee_bf16_from','ieee_rod')):add(path,name,line,condition,'pure_calculation_gate','new control after6202','OPEN','evaluation of pure numeric facts; no architecture writes','有限性/范围标签不足；待逐位置瓶颈证据，不改冻结。')
   elif path.endswith('fdext_regs.sail') and name=='accrue_fflags':
    if ordinal==0 and condition=='changed':add(path,name,line,condition,'architectural_write_guard','restored original4f2 control; folded in6202 SYMBOLIC','OPEN','yes: guards FS/SD and extension assertion','原ITE按changed选择状态也正确；缺新增fork必要性证据。')
    else:add(path,name,line,condition,'original_native_guard','present in6202/original control','KEEP','baseline native state/control','本轮保留，非新增求解优化。')
   elif path.endswith('vext_fp_utils_insts.sail') and re.fullmatch(r'riscv_f(?:16|32)To(?:I|Ui)(?:8|16)(?:_pure)?',name):
    if not name.endswith('_pure'):decision='KEEP';origin='original4f2 ordinary adapter';reason='原生控制未改，不能把另一纯适配器新增fork视为天然必需。'
    elif name=='riscv_f16ToI16_pure' and condition=='overflow':decision='OPEN';origin='present in6202; restored by prior6202 commit';reason='旧显式eager超时并非当前ITE瓶颈；本轮没有新增，单独审架构门。'
    else:decision='REVERT';origin='added after6202 to SYMBOLIC pure adapter';reason='只返回clamped bits/NV/原flags，不跳过架构操作；恢复6202数据流。'
    add(path,name,line,condition,'narrow_saturation_bits',origin,decision,'pure value selection in _pure; original ordinary code preserved',reason)
   elif re.fullmatch(r'riscv_f(?:16|32|64)To(?:I|Ui)(?:32|64)',name):add(path,name,line,condition,'integer_result_bits','new ITE-to-if after6202','REVERT','pure candidate/clamped integer selection; no trap or state call','candidate/异常已先算；回6202 ITE，完整保留NaN饱和正端点规则。')
   elif name in ('riscv_f32ToF16','riscv_f64ToF32'):
    mode='0b110' in condition;add(path,name,line,condition,'ROD_mode' if mode else 'canonical_NaN','new mode guard after6202' if mode else 'present canonical policy; text duplicated by mode split','OPEN' if mode else 'KEEP','yes: algorithm mode choice' if mode else 'actual special result propagation','6202已安全规范RM6；未证明新guard修复非法RM或严重求解。' if mode else '保留NaN canonical语义，不能同纯NV事实分支一起删除。')
counts=Counter((r['role'],r['decision']) for r in rows)
assert counts['cause_flags_only','REVERT']==33 and counts['narrow_saturation_bits','REVERT']==8 and counts['integer_result_bits','REVERT']==36 and counts['pure_calculation_gate','OPEN']==29,counts
numstat=subprocess.check_output(['git','-C',str(M),'diff','--numstat','6202e23','e9d69d2','--','model'],text=True)
stats=[line.split('\t') for line in numstat.splitlines()]
assert len(stats)==8 and sum(int(v[0]) for v in stats)==590 and sum(int(v[1]) for v in stats)==435
core_stat=next(v for v in stats if v[2]=='model/core/ieee_fp_exceptions.sail');assert core_stat[:2]==['452','360']
ws=subprocess.check_output(['git','-C',str(M),'diff','-w','--numstat','6202e23','e9d69d2','--','model/core/ieee_fp_exceptions.sail'],text=True).split()
assert ws[:2]==['300','208']
report={'status':'architecture decision under newest two gates; no production changes','isla_base':'0008fae76f4cff86dae1a036d889f0414c228e9d','model_original':'4f2ac293654a02db26dac5055be7f93fd6e3141e','model_round_base':'6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a','model_frozen':'e9d69d2f28586c089244c8e37ee4c904c5114458','source_core_sha256':hashlib.sha256((M/'model/core/ieee_fp_exceptions.sail').read_bytes()).hexdigest(),'rollup':[{ 'role':role,'decision':dec,'sites':n} for (role,dec),n in sorted(counts.items())],'sites':rows,'performance_proof_for_new33_causes_or29_gates_or36_wrapper_ifs':None,'evidence':['agents/explicit_branch_timeout_diagnosis_20261102/active-lane-control/report.md','agents/explicit_branch_timeout_diagnosis_20261102/path-accounting/theory.md','agents/branch_ablation_official_z3_20261102/live-report.md','agents/encoding_constraint_isolation_20261102/validation/selective-report.md'],'theory_bound_limit':'旧332/1033是结构上界而非耗时下界，不能推出7200秒不可完成','local_aliases':{'decision':'KEEP nonblocking text','underflow':4,'facts':6,'reason':'局部命名，不新增fork/helper/数学运算；facts绑定在6202已有'},'diff_audit':{'production_files':8,'additions':590,'deletions':435,'core_raw_diff_lines':812,'core_ignore_whitespace_lines':508,'whitespace_diff_reduction_lines':304,'whitespace_fraction':304/812,'raw_numstat':numstat},'not_approved':'OPEN不是KEEP；正确性PASS不是性能/架构接纳；REVERT只是下一候选建议，没有实施。'}
(O/'architecture-decision-20261103.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['rollup'],ensure_ascii=False));print('PASS site inventory and diff audit')
