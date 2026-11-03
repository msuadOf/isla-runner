# 浮点收敛版终验范围

主agent依据用户最新授权已确认本页为本轮限定退出矩阵。目标是在新树`.worktree/sail-riscv-float-converged-20261103`仅应用已签77处纯数据回退，证明其等价、NaN/trap保持及OPEN字节冻结，然后按新提交/IR/程序/inputs完成下列回归与集成。旧214/e9全77实验只作历史，不作为本轮前置，也不改署新版本PASS。真实新bug必须修复；延期OPEN转memory后续议题，不阻断本轮限定结项。

| 义务 | 最小充分执行与证据 | 退出条件 |
| --- | --- | --- |
| 精确源码回退 | 从e9 Git对象独立重建已签候选，核33异常原因+8窄转换+36整数包装共77源码条件回数据流；无额外生产变化 | 完整候选字节与批准内容相符，局部Bool/BV等价；原NaN真实结果传播、trap/合法性、changed/29 finite-valid/2ROD mode等OPEN位置逐字不变 |
| 严格检查与IR | ordinary strict，RV64 V128/V256/V512及RV32四配置SYMBOLIC完整严格IR；源码/工具/缓存/配置/IR来源全绑定 | 实际命令exit0、来源不漂移；新版永久checker四配置正控及必要负控通过，只要求批准控制/数据流关系，不重建77分支数门 |
| flags | 新300 helper，五逻辑入口/四不同IR；独立重算actual old/incoming/pre-state | fcsr/mstatus 300全符，seed/来源相符；callback仅静态IR合同 |
| 窄与整数转换 | 新819 helper、282 scalar、183 vector；使用受签独立runner与原fixture，独立Fraction从actual word/观察寄存器重算 | 所列定向数值/flags/后态/编码全符；直接Qfaufbv与正式qffp/config/binary范围明确 |
| 异常/ROD/BF16 | 新315实际JSON；独立SoftFloat从actual word/pre-state重算并核约束IR重建/后态/seed | 315无数值/flags差异，无静默跳过或来源漂移；不扩大固定样例覆盖 |
| assembly与Make | 新1104隔离Sail前向输出、实际GNU/Clang助记符/精确字节/.insn，真实Make solve-FLEQ_S 8JSON/48检查 | 五canonical/非零保字与负对照成立；GNU能力拒绝保留，精确替代有实际字节；Make语义及来源正确；动态反解析仍未验 |
| 正式完整入口集成 | **FLEQ_S、C_ADDI4SPN两Clause**，原完整配置，不约束寄存器/初态、不采样，T1/qffp/seed17，整Clause及单次SMT各7200秒 | 每项自然exit0、完整JSON/finished与所有partial计数0、完整gen/编码/Retire或Illegal合同及来源正确；分别验证32位浮点与16位兼容通路，不能外推77全域 |
| 历史FAIL分类与证据保存 | 旧21449PASS/28FAIL、e952PASS/25FAIL逐项核exit/结果；确认超时与语义bug分账，迁移证据有hash及逻辑路径 | 不删失败，不将外限124冒称语义错误或PASS；若存在真实新bug回修。旧批搬迁只转存原始自产物，保留symlink及逐文件清单 |
| 集成 | 最终源commit、五逻辑IR入口/四不同IR、isarch/库/seed/永久检查、父gitlink/manifest及文档来源一致 | 独审按实际新hash签字；OPEN冻结转memory，最终只称本页范围限定通过 |

## 正式两Clause运行合同

由inventory冻结唯一新inputs、独立harness副本与新批次，先dry-run后实际运行两项。沿用受签`run_clause.py`参数：`python3 <新harness> --inputs <新inputs> --batch <新唯一批次> --job FLEQ_S --cpu <空闲核>`，另一项替换`--job C_ADDI4SPN`。harness保持原完整FD配置、`-T 1 --tastic qffp --smt-timeout 7200s`及外层`timeout ... 7200s`，seed17通过preload拦截核验。

为节省磁盘，可对新harness仅移除`--itrace`、`--trace-all`、`--probe-all`、verbose/debug等诊断输出开关；必须提交具体新diff/SHA独审后才能使用。不得改指令/状态域或抽样预算。结果元数据明确trace未请求，不把缺trace记为失败，也不与旧trace墙钟作纯源码性能比较。

不可删的证据：实际argv/env及起止/exit/time/RSS，源码/IR/config/binary/Z3/seed/inputs哈希，完整实际JSON（summary各partial、全部gen、编码/ret_val/pre/post/provenance），seed拦截原日志，简洁运行及错误/timeout诊断。旧完整轨迹可迁存，不静默截断或改hash；永久测试与失败账保留。

本矩阵是主agent确认的本轮限定验收，不承诺全77Clause预算、全输入/调用点、全向量配置、所有FMA变体、Zfinx、硬件差异测试或动态反解析。不得因这些延期范围扩大当前实施；如本矩阵发现真实bug，按最小修复并复验受影响项。
