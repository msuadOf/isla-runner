# 模型e9d69d2验收独审

模型固定为`e9d69d2f28586c089244c8e37ee4c904c5114458`，Isla `42000be47596ec088623881d03c0eadc5cf0ba27`。本页与[214版动态签收](model214-results-review.md)分账，不迁移旧PASS。新冻结inputs SHA-256 `eb830e77f6d31e88574e018ef08e1eb1d5f47f2e9369169d9fd4613877e6973a`、V128 IR `661fd6e443a690f5b1c2a0ccfd1a5b84c908baba5e1b6cea786a1e0696a022ad`、正式程序 `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`。

已独核全部冻结资产hash及源码清单中的实际文件/提交blob，见[新输入独审](input-e9d69d2-independent.json)：模型all-tracked 1,011文件，Isla编译源1,021文件（明确排除8个生成IR/provenance/fixture）。这是输入一致性，不代表新程序运行结果已通过。

## 验收脚本准备

[独立脚本](audit_e9_harness_guards.py)逐字逆改各项许可变更，精确恢复214受签runner，同时核实际Git对象和原独立oracle/fixture，结果见[机器证据](e9-harness-guards-independent.json)：

| 范围 | 新runner SHA-256前缀 | 受签改动与边界 |
| --- | --- | --- |
| flags300 | `96deaef2` | 只新增固定e9提交allowlist；Rust probe `26225f7c`与oracle `ebf9424c`未变，来源树和资产hash校验保留。 |
| 转换819+282+183 | `0e33851c` | 冻结snapshot `c39116cb`；14输入中13个与214逐字相同，仅run.py新增必填`--model-tree`，改用该路径核HEAD/源码清单并记元数据。819预期另用独立Fraction全量重算，无差异。 |
| 异常315 | `8475d90d` | 固定e9提交、父提交214和唯一core文件差异；214→e9实际Git diff SHA `9dbf13575b7b32f48adb05f40c392bdbd520f77a980cea4d7594946808a1e9dd`。expected仍明确属于8ad，实际model和delta基线另记；原315预期/oracle准备脚本未变。 |

源码候选的两位Sol只读签收见[第二审查](../../baseline-0008fae/control-candidate-review.md)。18处纯flags/jam选择恢复数据流，特殊值/finite/valid/饱和/changed等控制保留；这不等于新IR或动态验收。后续只按新实际inputs、IR、程序和结果哈希追加签收。

转换runner初次移到frozen子目录时未调整ROOT深度，启动即失败且未执行fixture；旧准备签不构成动态PASS。修正为`HERE.parents[4]`后重新冻结runner `1a7e5ed98e27a6b37f92b03f80a6d29187a6417ba2d7f726883f34cb6d805e08`，snapshot `66639cfa23cf2c0415912ff3b951c5b4145fbf6e61ef9635426ffbc801d4372e`。第二次[独立预签](e9-harness-guards-attempt2-independent.json)将ROOT修正与model-tree增量逆改后精确恢复214旧runner，其余13文件和819Fraction预期仍相同；attempt1失败记录应保留。

## flags changed：新批300项限定通过

新[原始result](../../validation/flags/runs/model-e9d69d2/result.json) SHA `a67da52b9801a7d181acce8156f7beb9113112aa36ed308dbc2304621db28b03`。CPU15/qffp/官方Z3/seed17，五逻辑入口各60项，四份不同IR（rv64-default为V128别名）。实际Rust probe仍`ded63f43…`；正式isarch `acda0dce…`只绑定来源，本批不冒称由正式isarch执行。

独立从实际old/incoming/初态重算300条fcsr和mstatus，全部相符，各入口changed真36/假24，见[数值状态重算](flags-modele9-independent.json)。另核实际命令IR路径/新hash、配置/probe/oracle/seed归档hash与本次inputs，见[来源核验](flags-modele9-provenance-independent.json)。不读owner expected字段求值。callback仍只有静态IR合同，未记录动态callback事件；Ext_F/人工初态helper结果不扩大为Zfinx、所有调用点或完整Clause。

## 六窄与十二整数包装：新批819+282+183限定通过

实际新批[run.json](../../validation/conversions/runs/rv64d-v128-model-e9d69d2-attempt2/run.json) SHA `7a2a5e9bd0c72630ee3e2fcd13953696fc33bec4b71d60f2a23725a129c044f9`。五阶段exit0，三求解阶段seed17有效；819 helper逐例PASS序列与已独立重算的819项预期对应。scalar SHA `060b013eee462f18e73f947c8d7e3c7e23232fb1af14f8ff81f7b42eb2cf3780`、vector `7e93d9f89289068c54bbef5c3db3ec641bc97967f19cce7fa6cfa7e6e5f41383`。

独立从新批实际机器字、观察源寄存器和归档初态，用精确有理数FP解码/整数舍入重新计算282 scalar+183 vector的结果、flags及所列后态，465条全符；另核Retire、反编码、SAT/差异UNSAT及所列未写寄存器，见[新数值重算](conversions-modele9-independent.json)。归档14文件与attempt2冻结snapshot逐hash一致，实际IR/配置/二进制/seed/源清单/driver/正式inputs绑定另见[来源独核](conversions-modele9-provenance-independent.json)。未以214结果相同代替本次重算。

本批仍是直接runner：helper `669c727e…`、instruction `9e1bc98f…`，Qfaufbv、配置`8247c8d4…`；与正式isarch/qffp/FD配置不同。166模型源文件、1,021 Isla编译源（排除8个生成文件）的清单范围明确。固定样例、vl≤2/LMUL1或2、列明观察域不外推全输入/全向量配置或全部无关寄存器，也不计完整Clause。

## H/S/D异常、ROD与BF16：e9新单批315项限定通过

实际新批[summary.json](../../validation/exceptions/runs-model-e9d69d2-itrace/summary.json) SHA `749406003b9eedb6eae34c8a5004c641836ebd09428d188a7dd76d095724173d`；CPU17/29、T1/qffp、seed17，315项全新执行，exit0且每份summary.finished/全部partial计数0。定向预算600秒，不能计作7200秒完整Clause。

[独立数值重算](exceptions-modele9-independent.json)从新实际机器字及JSON初态调用独立SoftFloat核315条，覆盖259 scalar/ROD/普通转换、30 H/S/D vector、26 BF16；315全符，无跳过、无flags或数值差异，不读owner expected fixture。另[来源与状态独核](exceptions-modele9-evidence-independent.json)从新base.ir+每条clause/fields重建315个临时IR hash，与command及JSON provenance均符；6,566初态配置值、30,870保持状态字段、mstatus/FS/SD及vstart、seed/实际来源逐项一致，owner33,566条断言另逐项重核。

launch明确实际model=e9、expected_source=8ad、delta_base=214及core delta `9dbf1357…`；runner为已预签`8475d90d…`、expected仍`6ed44d0a…`。本签只适用于该新输入/新IR/程序和列明定向样例，不继承214结果，也不扩大为全异常原因、所有FMA变体、全SEW/LMUL/VLEN/vl或硬件差异测试。

## 新汇编探针与真实Make：限定通过

e9命名源码树的四个汇编输入文件hash已与实际提交内容核对，映射提取源码与既有独立审查版本逐字相同。对新归档C程序再次实际执行：基线仍在首条canonical断言退出1，当前前向输出1,104/1,104成功；见[独立重新执行](assembly-e9-probe-independent.json)及[来源/48项记录审计](assembly-e9-records-independent.json)。这是隔离映射提取程序，不是完整模型动态反解析；反向string mapping依然只有类型/源码合同，旧解释器P_string_append限制未变。

独立重新汇编这1,104条实际Sail输出：Clang全部助记符、GNU canonical/控制助记符及两工具链全部`.insn`/字节形式，共5,824条指令字节检查全部相同，见[新实际工具链产物](assembly-toolchains-e9-independent.json)。另核owner原48探针，五exact+三负对照各六RM，25次GNU非零exact助记符拒绝保持原失败，精确`.insn`及Clang原助记符都保留原word；不能称GNU所有助记符通过。

新真实Make的solve-FLEQ_S recipe退出0，3.305秒、8新JSON、48工具链检查严格通过；输出SHA `21179058ed1f8f97932e86febf0cc76c44d18f82fde4e4ad08c7e66f5feedcfb`。独立核新inputs/IR/程序/配置、原recipe日志、seed17、summary、实际word及初态，四类有限/qNaN源角色各两例，fcsr/mstatus与所有非目的状态保持；4条目的可观察、4条x0丢弃，见[独立审计](make-e9-independent.json)。固定初态Make不计完整域Clause完成数。

这里没有迁用214版12job/135JSON三表示结论；目前e9上述工具链全量探针和Make是列明的新动态范围。

## 完整Clause准备

e9调度器`3ecd0ebc…`及冻结77=64+13来源门已独立准备签收，见[调度器审查](scheduler-e9-review.md)。mock只证明控制/失败/身份/磁盘队列守恒，不证明任何完整预算结果；正式主批最终结果待另签。
