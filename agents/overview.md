# Agents Overview

本文件是根目录 `AGENTS.md` 引用的代码分析入口索引。

- 仓库和代码逻辑的持续发现记录在 [findings.md](findings.md)。
- 当前 `zSTORE` / `zLOAD` 路径爆炸议题记录在 [zSTORE_path_explosion/](zSTORE_path_explosion/)。
- Ara 历史 PoC 分析见 [ara_poc_batch/status.md](ara_poc_batch/status.md)，证据入口见 [根档案索引](../archives/README.md)。
- XiangShan 草稿复现见 [vext_issue_draft_reproduction/status.md](vext_issue_draft_reproduction/status.md)；V 扩展收敛见 [v_symbolic_dedup/status.md](v_symbolic_dedup/status.md)。
- 新议题应在 `agents/<议题名>/` 下维护 `plan.md` 和 `status.md`，并把可复用的代码理解同步回 [findings.md](findings.md)。
- Isla 浮点支持调查与实施计划见 [float_support_review/status.md](float_support_review/status.md)，现行计划见 [float_support_review/plan.md](float_support_review/plan.md)。
- Isla `origin/feat/memory-support` 内存支持调查见 [memory_support_review/status.md](memory_support_review/status.md)。
- workaround 描述归属与运行配置生成见 [workaround_ownership/status.md](workaround_ownership/status.md)。
- 内存 clause 分支覆盖对照（W19+G1-G8）见 [memsolve_branch_coverage/status.md](memsolve_branch_coverage/status.md)。

- 显式语义分支恢复、预算与GPT-6.1 Sol独审：[状态](explicit_branch_restore_20261102/status.md)。

- [剩余特殊值控制分支](special_control_restore_20261102/status.md)：每源NaN、其他格式及20个活动gate恢复，Sol及定向验收通过。
- [显式分支超时定位](explicit_branch_timeout_diagnosis_20261102/status.md)：区分flags的SMT成本与旧饱和循环的额外分叉。

- [flags/sat完整归因确认](explicit_branch_timeout_diagnosis_20261102/confirmation-report.md)：两小时主路径账、六策略臂、活动gate与collector因果诊断，生产未改。

- 2026-11-02 编码辅助约束分离与活动lane饱和分支完成，Sol独审及三完整Clause预算验收通过；[版本/证据/边界](encoding_constraint_isolation_20261102/status.md)。


- 2026-11-03 float纯数据回退收敛与Sol限定验收完成，OPEN冻结延期memory，见[最终交付](float_review_closure_20261102/final-report.md)。
- 2026-11-04 float→memory 合流候选：父仓文档冲突已处理，子仓提交、组合 IR 与联合验证待完成；见[合流状态](float_memory_merge_20261103/status.md)。
