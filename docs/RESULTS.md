# RESULTS — 验证与历史证据索引

本文件汇总已有的逐次验证记录，保留其当时的版本与限制。**当前任务状态以 [specs/TODOs.md](../specs/TODOs.md) 为准。**详细命令、逐条结果和原始分析继续保存在原位 `agents/` 专题文件或 `archives/`；这里不把历史结果重写成当前工作树的 PASS。

| 日期 / 范围 | 原记录的结果 | 证据入口与限制 |
| --- | --- | --- |
| 2026-09-25，项目级文档重构 | 原 101 个 agent 文件留在原位；新规范链接与 Python 静态检查通过 | [实施与修正记录](../agents/agent_collaboration_rules/migration.md)；历史缺失目标和基准 binary 门槛单独记录。 |
| 2026-09-25，浮点分支静态审查 | 找到符号 rm、Eq/qNaN、FMA NV 三类问题 | [审查状态](../agents/float_support_review/status.md)；未在该分支重新构建或动态测试。 |
| 2026-09-25，V IR/workaround | 新 RV64 IR 哈希与 79 份严格配置绑定，67 个 region 坐标校验通过 | [验证状态](../agents/v_symbolic_ir_workarounds/status.md)；适用所记源码和 IR 哈希。 |
| 2026-09-23/25，V 去重性能 | 四类样本、三轮 A/B 与 helper 对照；未见明显性能退化 | [报告](../agents/v_symbolic_dedup_perf/report.md)、[原数据](../agents/v_symbolic_dedup_perf/results-final.json)；不能外推全量指令。 |
| 2026-09-23，依赖初始化 | `init.sh` 静态与隔离验证通过，脏子模块保留 | [提交批次状态](../agents/commit_workspace_audit/status.md)、[初始化状态](../agents/init_repositories/status.md)；现行行为仍需以脚本和工作树核对。 |
| 2026-09-19，XiangShan 草稿复现 | 三项 PoC 有历史运行；Issue 1 的限时超时不能证明永久挂死 | [冻结档案](../archives/xiangshan/2026-09-23-issue-reproduction/README.md)、[状态](../agents/vext_issue_draft_reproduction/status.md)。 |
| 2026-09-18，Isla→XiangShan 回放 | 历史差异测试及覆盖缺口已记录 | [专题验证记录](../isla/agents/validation/Vext-test-9-16-difftest-xiangshan/验证报告.md)；不代表新版本 DUT。 |
| 2026-09-17，Ara 合法配置复验 | 部分 bug 家族在合法配置复现，部分早期结论被修订 | [Ara 冻结档案](../archives/ara/2026-09-23-poc-batch/README.md)、[缺陷表](../agents/ara_poc_batch/bugs.md)；先看后续修订。 |
| 2026-07-30，VVTYPE 局部限制 | 当时 30 分钟目标内完成 21/21 mnemonic | [状态与运行参数](../agents/vvtype_balanced_local_limits/status.md)；绑定当时 IR 与限制配置。 |
| 2026-07-30，VVTYPE saturation | 定向语义与 qfaufbv 测试通过，性能差异仅为单轮信号 | [状态](../agents/vvtype_saturation_qfaufbv/status.md)。 |
| 2026-07-16，XiangShan VLEN128 smoke | 当时真实 NEMU DiffTest 小样本链路通过 | [专题状态](../agents/difftest_xiangshan_v/status.md)；reset-zero 模式不等同完整 Isla 状态重放。 |
| 2026-07-10，assembly-gen V 初始化 | 单测与集成、Spike 定向验证通过 | [状态](../agents/v-ext-init/status.md)；仅适用当时 assembly-gen 版本。 |
| 2026-04，zSTORE 路径爆炸 | PMA/PMP 原型、smoke 与语义核对分阶段进行 | [状态原文](../agents/zSTORE_path_explosion/status.md)、[审计](../agents/zSTORE_path_explosion/audit.md)；不同阶段的开关和配置不能混作一次验收。 |

其他议题的计划、状态和报告均保持在 [agents/](../agents/)；[代码发现](../agents/findings.md)保留全部发现与历史修订。新增结果应注明日期、源码/IR/配置版本、命令或产物、判定范围与限制，再更新 `specs/TODOs.md` 对应状态。
