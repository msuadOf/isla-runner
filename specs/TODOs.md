# TODOs — 当前协作状态

本文件是根仓库动态议题状态总表。目标与验收口径见 [GOAL.md](GOAL.md)，逐次验证与历史证据见 [RESULTS.md](../docs/RESULTS.md)及保持原位的 `agents/` 专题记录。下表从议题状态提炼，历史实验的“已完成”不自动代表当前工作树的 PASS。

## 更新规则

- 每项分别写**实施**和**验证**。验证用 `PASS`、`FAIL`、`未测`、`待复验`、`阻塞` 或 `待核实`；PASS 必须有可追溯证据。
- 修改实现、IR 或关键配置后，受影响的旧 PASS 退回待复验；历史结果保留在 `docs/RESULTS.md` 或专题文件。
- 本表给当前判断和下一步，实验过程、完整命令及日志分析写入专题文件。修改细节后同步本表对应行。
- 对仅有历史记录、无法判定现行版本的议题，标“历史/待核实”，不要推测为已验收。

| ID | 议题 | 实施 | 验证 | 证据与下一步 |
| --- | --- | --- | --- | --- |
| DOC-01 | 按 nacc_boom 方案重构项目级文档 | 已完成 | PASS（原路径、链接与静态检查） | [议题摘要](../agents/agent_collaboration_rules/status.md)、[实施与修正记录](../agents/agent_collaboration_rules/migration.md)；`agents/` 文件留在原位。 |
| INIT-01 | 依赖仓库初始化 | 已实现 | PASS（入口静态验证） | [历史状态](../agents/init_repositories/status.md)、[提交整理](../agents/commit_workspace_audit/status.md)；当前 `init.sh --help` 已核对，动态 checkout 结果以原记录和现工作树为准。 |
| INST-01 | 指令扩展分组表 | 已记录实现 | 待核实 | [状态](../agents/instruction_extension_tables/status.md)；复用前核对当前 Isla 代码和测试。 |
| ZSTORE-01 | zSTORE 路径爆炸与 PMA/PMP | 历史多阶段实现 | 待复验 | [状态](../agents/zSTORE_path_explosion/status.md)、[审查](../agents/zSTORE_path_explosion/audit.md)；先确认当前 IR/配置，再决定 Phase 5 结论能否复用。 |
| VMASK-01 | read_vmask A/B 迭代 | 历史研究 | 待核实 | [状态](../agents/read_vmask_ab_iterate/status.md)、[报告](../agents/read_vmask_ab_iterate/report.md)。 |
| VINIT-01 | V 扩展上下文初始化 | 历史实现 | 待复验 | [状态](../agents/v-ext-init/status.md)；原记录的测试结果只对应当时 assembly-gen 版本。 |
| VDEDUP-01 | V 扩展 SYMBOLIC 去重 | 历史实现 | 待复验 | [状态](../agents/v_symbolic_dedup/status.md)、[性能](../agents/v_symbolic_dedup_perf/report.md)。 |
| VDEDUP-02 | V 去重性能对照 | 已完成历史实验 | PASS（所记四类样本） | [状态](../agents/v_symbolic_dedup_perf/status.md)、[报告](../agents/v_symbolic_dedup_perf/report.md)；不代表全量 V 扩展性能。 |
| VWORK-01 | V IR 与 workaround 绑定 | 已记录同步 | PASS（哈希与坐标校验） | [状态](../agents/v_symbolic_ir_workarounds/status.md)；现行 IR 再变更须重验。 |
| VVTYPE-01 | saturation qfaufbv | 历史实现 | PASS（所记定向测试） | [状态](../agents/vvtype_saturation_qfaufbv/status.md)；性能差异只有单轮信号。 |
| VVTYPE-02 | 局部限制与均衡采样 | 历史实验 | PASS（当时 30 分钟验收） | [状态](../agents/vvtype_balanced_local_limits/status.md)；对应旧 IR/配置。 |
| ARA-01 | Ara 批量 PoC | 历史实验已归档 | 待核实 | [状态](../agents/ara_poc_batch/status.md)、[冻结证据](../archives/ara/2026-09-23-poc-batch/README.md)。 |
| XS-01 | XiangShan RVV DiffTest | 历史 harness 实现 | 待复验 | [状态](../agents/difftest_xiangshan_v/status.md)；区分 fake smoke 与真实 DUT 回归。 |
| XS-02 | XiangShan Issue 草稿复现 | 历史实验已归档 | 待核实 | [状态](../agents/vext_issue_draft_reproduction/status.md)、[冻结证据](../archives/xiangshan/2026-09-23-issue-reproduction/README.md)。 |
| XS-03 | XiangShan/NutShell fuzzing | 隔离 worktree 历史实现 | 阻塞（真实 smoke） | [状态](../agents/xiangshan_nutshell_fuzzing/status.md)；需匹配 emulator 与 diff-so。 |
| SAIL-01 | Sail-RISC-V 符号执行改进研究 | 研究完成，方案待定 | 未测 | [状态](../agents/sail_riscv_improvement/status.md)、[报告](../agents/sail_riscv_improvement/report.md)。 |
| FLOAT-01 | Isla 浮点分支静态审查 | 审查完成 | 未测（动态） | [状态](../agents/float_support_review/status.md)；符号 rm、Eq/qNaN、FMA NV 三项需修复和动态验证。 |
| REPO-01 | 旧仓库 agent 重构提案 | 仅计划，未实施 | 未测 | [历史方案](../agents/repo_agent_restructure/plan.md)；其更大范围目录/子模块方案未获确认，不并入 DOC-01。 |
| PREEXEC-01 | C ADD pre-exec constraints | 仅见计划 | 未测 | [计划原文](../agents/c_add_pre_exec_constraints/plan.md)；待核对实施状态。 |
| COMMIT-01 | 工作区提交审计 | 历史批次完成 | 待核实 | [状态](../agents/commit_workspace_audit/status.md)；仅描述 2026-09-23 批次。 |

没有独立 `status.md` 的专题仍以其计划或报告作为证据入口。新增议题先在本表登记，再按根 `AGENTS.md` 的要求建立可审阅方案。
