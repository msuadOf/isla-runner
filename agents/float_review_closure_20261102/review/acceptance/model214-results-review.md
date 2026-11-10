# 最终模型21418d0动态独审

本页只签最终inputs `44641223d4541b042a337c9adab6ac902f34d3af82f3835213f28b39cc247b19` 上已实际完成的新批次；8ad5e8e结果保留历史署名。flags、整数转换、315异常、三表示和真实Make均已重新执行并独立限定签收；完整64受影响+13兼容Clause主批仍在运行，未签整体通过。

模型 `21418d0`、Isla `42000be`；V128 IR `5514e98e…`。正式isarch为带itrace的 `acda0dce…`，当前来源与资产哈希/dry-run见 [独立输入核验](input-21418d0-independent.json)；正式程序watchdog/itrace准备条件由enum reviewer另签，不能借旧fe4bdceb签名替代。

enum reviewer已对acda新构建补签，见 [新候选重新签收](../enum/runner-review.md)。其独立smoke绑定旧0e57 inputs；本目录另核214输入，并独立复核父执行的新214完整域FLEQ_S启动smoke：48条、exit0、summary.finished、所有partial计数0、seed17及17,956,382字节itrace哈希均符。实际机器字/初态重算48条比较结果与flags全符，其中24条rd≠x0结果可观察。见 [独立脚本](audit_model214_smoke.py)、[产物](model214-smoke-independent.json)。此单Clause启动证明单列，不代替77主批。

## flags changed：新批次300项限定通过

原始 [result.json](../../validation/flags/runs/model-21418d0-itrace/result.json) SHA `9b823e4f…`。实际probe仍为 `ded63f43…`，qffp、CPU15、官方Z3、seed17，五逻辑IR入口各60项（rv64-default仍与V128别名），没有执行正式isarch代替helper。

独立对新批次运行 [audit_flags_results.py](audit_flags_results.py)，见 [300项结果](flags-model214-independent.json)：按实际old/incoming与初态重算fcsr/mstatus全部相符，各入口36真/24假，FS Initial/Clean/Dirty、SD0/1、其他位哨兵取完整笛卡尔积；日志/seed/oracle哈希均匹配，五个实际IR路径及hash与最终inputs一致。脚本唯一版本适配为允许固定21418d0，逆替后精确恢复旧受审44156664。

仍仅签固定helper状态，callback只属静态IR合同，Ext_F和人工状态哨兵范围不扩大为Zfinx或完整指令可达域。

## 六窄与十二包装：新批次819+282+183限定通过

原始 [run.json](../../validation/conversions/runs/rv64d-v128-model-21418d0-attempt1/run.json) SHA `26cf6549…`。819 helper、282 scalar、183 vector均新执行；五阶段退出0，三求解段seed日志固定17。配置仍为直接runner母本 `8247c8d4…`，程序仍为`669c727e…`和`9e1bc98f…`、tactic Qfaufbv，不能算正式isarch/qffp或完整Clause。

独立对新输出执行 [audit_conversion_results.py](audit_conversion_results.py)，见 [新批次465条数值/状态重算](conversions-model214-independent.json)：从实际机器字和观察源寄存器/归档初态，以精确有理数解码与整数舍入重算结果和flags，全部相符；机器字/反编码、Retire、SAT/差异UNSAT、W/WU符号扩展、活动/屏蔽/前序/尾部、LMUL2目的组与所列保持寄存器均核。819 helper逐例日志名/次序对应归档TSV，归档14文件hash另逐项核对。

scalar结果SHA `74c2a8e1…`，vector `014b4f10…`；新IR与新sealed inputs的模型/Isla/IR/Z3/seed来源绑定明确保留。源清单为166模型文件及1021项Isla编译源（明确排除8项旧IR/provenance/fixture），不误称1029项全部由该source manifest哈希。范围仍是固定输入、vl≤2、所列LMUL及观察域；不外推所有无关寄存器、全输入或所有调用者。

## H/S/D异常、ROD与BF16：新单批315项限定通过

原始 [新批次](../../validation/exceptions/runs-model-21418d0-itrace/summary.json) SHA `3a69ff53…`，315项全部新执行；CPU17/29，T1/qffp、seed17，定向外层与单次SMT预算600秒。不能计作7200秒完整Clause验证。

独立 [实际数值审计](exceptions-model214-independent.json) 从每条实际机器字解码操作、格式、寄存器、RM，读取该JSON初态后调用独立SoftFloat；315条全部重算，无跳过、无数值或flags差异，不读owner expected fixture。覆盖本批259 scalar/ROD/普通转换、30 H/S/D vector、26 BF16。

另以 [独立证据脚本](audit_model214_evidence.py) 核实际输入/输出/配置/seed及完整后态，见 [账本](model214-evidence-independent.json)：6,566项配置初态值、30,870项未改写状态字段、mstatus/FS/SD与vstart均符；owner记录的33,566项断言也逐项重核。临时constrained.ir按受签runner合同在执行后删除，本审查从冻结base.ir及每条command的clause/fields独立重建315份文本哈希，全部同时匹配command与实际JSON provenance；不把已删文件写成在盘归档。

## 三表示和真实Make：修后新JSON限定通过

12个定向job共135条新JSON，summary.finished且列明partial字段逐项0；实际配置/IR、来源、seed17、退出0均独核。受签runner为 `e74431e8…`，checker `11ed4d4d…`，Make runner `40f6e03a…`。见 [三表示与Make字节独审](representations-make-model214-independent.json) 和 [来源账本](model214-evidence-independent.json)。

810项实际工具链检查中，25项GNU非零RM精确转换助记符仍为原始失败；独立审计从机器字限定到D.S/D.H/S.H/D.W/D.WU五操作，逐项核Clang原助记符、GNU `.insn` 与 `.byte` 已汇编的归档字节均精确等于原word，且selection选择相同实编译命令。因此按用户允许的精确表示合同签收，无未处理失败；不称810项原助记符全成功。4项非法BF16的Clang拒绝按原合同另记，未混为精确转换回退。

五操作各有RM0/1/2/3/4/7真实JSON，RM0五条无RM canonical文本在两工具链均保字。新增24条整数到D由 [实际word数值重算](int-to-D-model214-independent.json) 全部通过，并独核rs1=x1、rd=f0、x1=1、D.W/WU/L/LU×六RM完整集合、输出1.0D和flags0。D.L/LU各六RM保留显式RM并严格工具链通过；S.W仅源码审查112探针/合成checker负对照，不能称本批真实JSON覆盖。

真实Make调用当前run.mk的solve-FLEQ_S recipe，exit0、4.044秒；8新JSON、48项工具链检查严格通过。独核四种有限/qNaN左右组合各两条、fcsr与保持寄存器；4条rd≠x0目的结果可观察，另4条x0写入被丢弃。Make输出SHA `d17e3375…`，固定初态smoke不计正式完整Clause完成数。

## 仍未闭合的范围

2026-11-02 16:36:03 UTC主批实时summary为73排队、4运行、0完成/0通过/0失败，64+13任务守恒；这是运行中快照，不是最终结果。后续只能按最终逐项result重新签收，超时/未完成保留OPEN。

上述样例不证明全部输入或全部调用点、FMA变体、Zfinx、全SEW/LMUL/VLEN/vl域；Sail反向string mapping亦仅源码/类型合同，现有解释器P_string_append限制下动态反解析未验。assembly源码和5824工具链字节核验单列见 [源码独审](assembly-source-review.md)，不借其替代完整Clause预算。
