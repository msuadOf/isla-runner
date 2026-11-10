# 浮点支持交接（更新至2026-09-27）

## 当前接续交付

当前任务已接续到 `1dcc8081…8180` 候选，官方77批已结束（50自然退出0、27外限124），全量输出重放和源码分支审计继续；同版9152定向结果以及列定helper/direct门槛通过，源码分支闭合仍未完成。新批原始入口为 `isla/target/float-solve-evidence/official-1dcc-20260927-002314/`，先核现有进程与结果，不重复启动。最新动态状态以[摘要](status.md)、[官方批记录](solve-fix-official.md)和[TODOs](../../specs/TODOs.md)为准。

用户进一步要求统一Sail模型的C++/SoftFloat与Isla/Z3后端：[具体方案](unified-backend-plan.md)已由Astra审定，隔离P0正在实施编译器native类型/返回/equality接线和共享数值链验证。原77目标仍保留；1dcc作为阶段基线，统一版本重新绑定验证。安装工具链与主d012 IR尚未切换。

## 2026-09-26 接续快照（历史）

当前主IR是 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，已同批更新79份严格配置。类型复用采用C1：共享格式分解与内建RM，内部局部五Bool事实，出口才转换已有共享异常类型。BF16 VF非法LMUL顺序、旧比较限制说明及smtperf测试已修。最终候选277未知入口、67 helper/估算/旧体/legacy、BF16十例和24组1509非访存样例通过；见[当前状态](status.md)、[最终IR与命令](ir-refresh.md)和[实施记录](implementation.md)。

旧c9e1bfe2官方77项已全部完成，39项退出0、37项外限124、1项SMT超时退出1，原35/44项“运行中”描述不再代表现状。无须按旧接手顺序续跑45–77。普通make solve仍未完成，不把既有失败转记为本轮PASS；10访存仍由独立议题负责，本任务未进入或集成该worktree。

后续重点是新IR上的完整官方入口资源收敛，必须保留原符号上下文；涉及模型/IR变化时按现有流程重验。A/B中间位串化性能失败和最终C1的选择均有记录，勿恢复已弃方案。当前两子仓与根仓库仍有未提交修改，未移动gitlink，不执行reset/clean。

## 前次交接快照（历史）

以下保留前次交接的时点、命令与限制；其中“当前”“正在运行”和接手顺序均仅适用于当时快照。

### 范围与当前判断

本任务只处理浮点支持。独立 `isla/.worktrees/memory-consistency` 不得由本任务进入、修改、集成或验收。此前把内存候选结果计入浮点 E 的说法已经撤回；10 个浮点访存 clause 均为**未验收**。已有内存专题文档属于另一议题，不据此宣布浮点 PASS。

A–D 在各自冻结候选、输入和差异证明范围内完成；E 已切换主 Isla 的通用浮点源码、V128 IR 与 79 份严格配置，但**E 全阶段未通过**。主 IR SHA-256 为 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`。主配置校验覆盖 79 份配置、132 个 region、22 个锚点；通用浮点单测 10/10，旧数值断言迁移 35/35。77 个 RV64 非访存 clause 各有至少一条真实编码的定向状态差异证明；两项 RV32 Zfa 非访存指令有隔离样例。上述定向结果不覆盖所有 enum、RM、SEW、VL 或输入域。详情见[实施记录](implementation.md)和[动态索引](e-coverage.md)。

普通 `make solve` 的 60 秒有界尝试退出 137，220 项未完成；全库 Z3 enum 单测失败已在干净基线复现。均不得写成全量 PASS。

### 正在运行的官方入口批次

[批次说明与复跑命令](tools/official_float/README.md)固定了 77 个 RV64 非访存 `make solve-X` 目标。副本在调用者设置的仓库外运行目录 `RUN_DIR`，排除 `.worktrees`；主、副本的 86 个受测浮点源码、IR、配置和脚本文件逐字节一致。参数为 `THREADS=2`、`OUTER_TIMEOUT=60s`、`SOLVE_TIMEOUT=50s`、`SMT_TIMEOUT=5s`、`TASTIC=qfaufbv`。

交接快照：前 35 项已有逐项退出码。1–24 项底层退出 0；25–35 项是向量目标，外限约 60 秒后底层退出 124、make 退出 2，均无最终 JSON，不计通过。第 36–44 项批次正在运行；接手时先检查进程与证据，勿并发重跑或覆盖；该批完成后从第 45 项继续。`evidence/summary.csv` 预列 77 行，**只有 `make_rc` 非空的行才已有结论**。逐项原始日志、命令、退出码、耗时与 RSS 在外部目录 `evidence/` 和 `stage/output/log/`；运行脚本为[run_range.sh](tools/official_float/run_range.sh)，汇总脚本为[summarize.py](tools/official_float/summarize.py)。仓库中的[批次摘要](tools/official_float/summary.md)随批次更新。

只读性能分析发现：向量目标的符号 `vtype`、LMUL、`vstart`、`vl`、寄存器号和 enum 产生大量路径；collector 在完成路径后再次译码，也增加成本。FMA 两项另出现 5 秒 `CheckSatAssuming` 超时，栈落在异常标志累计；仅切换 SMT tactic 尚无改善证据。`SOLVE_TIMEOUT=50s` 是每条活跃路径预算，而全局 60 秒外限可在写最终 JSON 前终止。下一轮先以独立证据目录对三个代表目标做 `THREADS=4`（至多 8）的同预算对照，记录查询耗时和超时 SMT 式；有收敛证据后再考虑 180 秒外限。若改用固定向量上下文或严格配置，应明确为覆盖收窄的新实验，不代替原入口验收。

### 接手顺序

1. 核对官方批次当前进程、`summary.csv` 中非空退出码和原始日志；完成第 33–44 项后决定是否继续第 45–77 项。超时、Unknown、非法路径分别记录；退出 0 和 `Retire_Success` 不单独证明数值与五种 flags 正确。
2. 对超时的纯浮点非访存目标做有界性能复验；语义判断继续使用已归档的结果位、flags 和状态差异 UNSAT 证据，不扩展到独立内存分支。
3. 有结论的批次写入[实施记录](implementation.md)与[全仓结果](../../docs/RESULTS.md)，同步[议题摘要](status.md)及[TODOs](../../specs/TODOs.md)。源码、IR 或关键配置变化后，把受影响的旧 PASS 退为待复验。

根仓库与两个子模块均有未提交内容；见各自 `git status --short`。不要为交接执行 reset、clean 或移动 gitlink。当前工作区状态并非单个可复现提交，动态证据须以所列版本、IR 和文件哈希为准。
