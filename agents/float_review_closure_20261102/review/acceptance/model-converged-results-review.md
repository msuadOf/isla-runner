# 浮点最终收敛版验收独审

受审模型`0f7b8fbc6724103f91f929ef6918f123df75d6c9`，新树`.worktree/sail-riscv-float-converged-20261103`。本轮按主agent确认的[限定终验矩阵](final-exit-scope.md)退出：仅已批77纯数据回退，NaN/trap语义保持，OPEN冻结延期memory，不以旧77全域预算完成作为前置。新strict/IR/动态/两正式入口结果仍须按实际新hash独签，不能迁用[e9结果](modele9-results-review.md)。

## 已完成的准备签收

- [实际源码绑定](converged-source-binding-independent.json)：新提交的5文件逐字等于已签new-policy候选；33异常原因+8窄+36wrapper源码if回数据流，共77个源码条件（不等于77个独立fork）。非目标模型字节、源NaN调用顺序、原trap/合法性文件、changed与29 finite/valid及两ROD mode控制保持。局部等价的独立源码主签另由model reviewer归档，本页只补实际应用到提交的binding。
- flags runner `2d79b3bc…`只新增固定0f提交许可，逆改恢复e9受签`96deaef2…`；fdext_regs与e9逐字相同，见[guard](converged-flags-guard-independent.json)。
- 315 runner `12ea69e3…`只新增固定最终提交、e9→final三提交链与5文件/diff校验，逆改精确恢复`8475d90d…`；差异SHA `01ad2e7f97de170aa7e400979b5c00af49e3f473e8b65946d16faa2fe39c74ae`，expected来源仍8ad、预期`6ed44d0a…`未动，见[guard](converged-exceptions-guard-independent.json)。
- 旧完整预算失败已逐项独核：[历史分类账](historical-full77-failures-independent.json)。214为49PASS/28FAIL，e9为52PASS/25FAIL，53项失败全为外限124、约7200秒、无完整JSON/summary；没有其它失败类别。未产出不证明所有语义都无bug，亦不算新版本PASS。

## 最终新资产与已完成动态

源码/strict/IR主审已完成，见[实际源码签收](../../baseline-0008fae/converged-source-review-20261103.md)、[新IR独审](../../baseline-0008fae/converged-ir-review-20261103.md)、[永久checker独审](../../baseline-0008fae/converged-checker-review-20261103.md)。来源核166模型源/149工具文件、ordinary及四配置严格检查/独立memo；四IR变化限于批准目标，FP/舍入表达式DAG不变，独立旧新IR解释276,672组返回值全符。checker `9ebd0d93…`四配置×两检查器8项正控、104项负变异全部符合预期，安装后五逻辑IR入口再次通过；不把这些静态证明冒称全域动态覆盖。

定向inputs SHA-256 `5147af93ecd9cfb5cd6c0607d8073fa997b608dc9993f8c81dee8e739f1e631e`、V128 IR `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786`、程序`acda0dce…`已独核全部冻结资产和提交源码blob。模型1,011受控文件，Isla编译源1,021文件（另8个生成IR/provenance/fixture不在此source manifest），见[独立输入](input-converged-independent.json)。

| 新批范围 | 独立结果与实际边界 | 证据 |
| --- | --- | --- |
| flags300 | actual old/incoming/pre-state重算300全符；每入口changed真36/假24，四份IR+rv64别名。CPU15/qffp/官方库/seed17，实际helper probe `ded63f43…`；callback仅静态IR合同 | [数值](flags-converged-independent.json)、[来源](flags-converged-provenance-independent.json) |
| 转换819+282+183 | 新819 helper序列与独立预期对应，actual word/观察寄存器/归档pre-state以Fraction重算465条全符，Retire/编码/SAT与差异UNSAT及所列保持字段均核。14归档/driver/source/seed与新inputs相符。直接helper `669c727e…`、instruction `9e1bc98f…`、Qfaufbv/配置`8247c8d4…`，不冒称正式isarch/qffp/FD配置 | [数值](conversions-converged-independent.json)、[来源](conversions-converged-provenance-independent.json) |
| 异常315 | 新单批315实际word/pre-state SoftFloat数值/flags全符，无skip；315临时约束IR从base+字段独立重建hash与command/provenance同，6,566初态/30,870保持字段/mstatus/vstart相符，owner33,566记录断言另核。CPU17/29/T1/qffp/seed17，定向600秒预算 | [数值](exceptions-converged-independent.json)、[账本](exceptions-converged-evidence-independent.json) |
| assembly | 新归档C重新执行基线红、前向1104通过；实际新输出独立重新汇编5,824条指令字节全符。owner48原始记录另核，25次GNU非零exact拒绝仍保留，精确.insn/Clang原助记符保字；仅隔离映射，不称动态反解析通过 | [新执行](assembly-converged-probe-independent.json)、[字节](assembly-toolchains-converged-independent.json)、[来源记录](assembly-converged-records-independent.json) |
| 真实Make | 原recipe新执行exit0/3.725秒，8新JSON/48字节检查全符，四种有限/qNaN左右角色各2例；4目的可观察+4x0。actual word/pre-state、全部非目的状态、seed/input/IR/config/program/recipe均独核；固定初态，不计完整域 | [独审](make-converged-independent.json) |

flags实际result SHA `0b5cb0e6…`，转换run `8343b7fc…`、scalar `7f6078af…`、vector `e9e90b0b…`，Make输出`e3e0e2c8…`。以上均重新执行并独立重算，没有按e9结果相同改署PASS。

## 两个正式完整入口

两入口inputs SHA `0a29115104b44f25924ddb37961b4dfd5967a42a8035bf9b33ac56cdecb7ae18`只改定向输入清单的jobs为FLEQ_S和C_ADDI4SPN，其他资产完全相同。受签harness `74a642d9…`仅改脚本目录定位及精确2jobs检查；逆改逐字恢复旧`b154941b…`。原完整FD/T1/qffp/seed17/双7200及trace均保持，64受影响分母未改；C_ADDI4SPN单列compatibility，见[独审](final-harness-independent.json)。

- **FLEQ_S完整入口限定通过**：自然exit0、27.67秒、finished及所有partial计数0，48条Retire。实际32位word、pre-state有效NaN-boxing、比较结果/NV、fcsr/mstatus及非目的状态独立重算全符；24条目的可观察、24条x0丢弃。seed、来源、17,956,384字节实际itrace及hash均核，见[独立结果](clause-FLEQ_S-converged-independent.json)。
- **C_ADDI4SPN完整入口限定通过**：自然exit0、2.038秒、finished及所有partial计数0，1条Retire。实际16位word独立解码rd/非零立即数，按pre.x2+imm模2^64核执行后的目的值，其余完整观察状态保持；核ExecuteAs续执行后的Retire，非停留在旧父指令状态。28,608字节trace及来源/seed/hash均符，见[独立结果](clause-C_ADDI4SPN-converged-independent.json)。

完整入口表示原符号域未缩减、自然完成，不表示所有输入值逐一列举或全77Clause预算通过。315最终异常与集成来源均已另核通过，最终[限定签收](final-signoff.md)绑定完整哈希；OPEN不改变为KEEP，不以延期项扩大或阻断本轮范围。

## 安装与最终Isla提交

根Isla提交`591693df2bc32019ea300511509ed683df09522e`的父提交为受测程序源码`42000be`，准确仅六个生成文件加四个测试文件；独立计算Git树`8ea0df2093dcd379b408154057ca391ee8ceb7cd`与实际提交树一致。146个生产Rust/Cargo/.cargo受控文件逐字等于420，所以正式isarch仍明确为420构建的`acda0dce…`，没有伪称591新构建。新安装IR与manifest模型提交/166模型来源相符，manifest SHA `6caab4ef6b1a2b95b2e78691dc6b23e6acecca708fca41f4f036834c866a7093`。

`test/float_ir/run.py --mode all`的26步完整label集合及日志逐核全exit0；五逻辑IR的helper/state/guard均完成，迁移/NaN/显式/special/closure检查亦通过。独立对新regression helper/state程序运行ldd，均链接官方Z3 `899cbc70…`。精确十文件SHA、Git blob/tree、26日志和程序hash见[集成独审](final-integration-independent.json)。父仓gitlink最终提交由主agent后续refseal，不改本页受测资产署名。

旧批迁移另外核逻辑symlink、清单完整文件集合/全部大小及871个非trace文件SHA（含全部JSON/命令/日志/时间/seed），53项旧失败结果与迁前独立账本SHA相同。154个大trace的SHA已由迁移owner逐文件前后核对，本审查只额外核其存在和大小，未重复读取约29GB轨迹；见[迁存独核](historical-migration-independent.json)。历史预算结论保留，不冒称新版本通过。
