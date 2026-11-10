# Isla 语义约束变异议题状态

2026-10-23 接续：针对“RTL／CSR 以外还有什么反馈量”，补充[微架构反馈与创新性边界](microarchitecture-feedback.md)及[来源证据等级](microarchitecture-feedback-sources.json)。核实 DRVFuzz 2026 的相邻语义转移及消融，结合 DiveFuzz、SurgeFuzz、DejaVuzz、SCD 与事件时序前史，提出语义条件下的实际事件关系、来源转发、生命周期及向量子事务反馈。明确 Sail 生成不自动等于 ISA corner 完整覆盖；传统 cross／transition／压力指标不能直接宣称创新。仅文献与候选设计，无新增实现或实验，下一步继续讨论指标定义及可观测性。

2026-10-22 再接续：用户将当前重点转为知识准备，明确本地CPU功能验证与bug检测定位，先系统梳理反馈指标再谈选型；本阶段未开发或运行新实验。[反馈综述](coverage-feedback-review.md)覆盖CPU／软件的结构、数据、语义、目标及加权反馈，另比较FuSS／SysFuSS／S²F／ColorGo／FuzzRDUCC的符号执行接入位置，HyPFuzz作为2023技术前史单列。[来源与阅读范围](coverage-feedback-sources.json)。本轮已取得FuSS作者公开全文，补全此前仅摘要的证据；强调反馈／评测指标分离、收益归因与统计范围。下一步是讨论文献和概念，不沿用下段“立即开发E0/E2/E3”的历史顺序。

2026-10-22 接续：用户要求多实验评估，已制定 [E0–E7 矩阵](experiments.md)，分别测量重放、取值多样化、种子、操作类型、约束修复、反馈、求解调度和泛化。已完成 E1 生成侧小 pilot：两个目标、开关各三次、共 12 次退出 0／168 条记录；vl 并集 VFMVFS 5→13、VSETIVLI 1→8，中位命令耗时分别约 +10.11%／+6.43%。仅证明本负载记录值域扩大；旧导出 schema 随开关变化，VSETIVLI 覆盖旧 vl，不能推定 RTL／检错改善。首次分析器缺字段错误已保留，修正后全量重跑；[结果和证据](pilot-results.md)。E0、E2–E7 尚未实施；下一步固定完整可重放种子与负对照，再开发共同变异器。

以下为第一轮调查历史范围：

2026-10-22：第一轮论文调查与设计讨论完成；未实现、未运行 fuzzing，也没有新增功能 PASS。

- 核实 GenHuzz、Encarsia（USENIX Security 2025）、GoldenFuzz、ReFuzz（NDSS 2026）的官方论文入口。
- 阅读 GoldenFuzz、ReFuzz、SimFuzz、HiFuzz、DejaVuzz、TargetFuzz 的公开 HTML 全文相关章节；FuSS 仅核实出版元数据和出版方摘要。
- 结论：参考模型辅助生成、历史种子变异与符号执行辅助 fuzzing 均有先例。候选研究问题是 ISA 约束如何保持目标条件、联合修复相关输入，并由实际 DUT 收益指导后续求解。
- 项目能力分布在不同工作树；路径签名只散列 fork 方向，不足以充当静态分支覆盖标识。
- 下一步候选：固定一套版本，在向量访存上比较普通变异、语义约束变异与双反馈调度，报告检错和求解成本。此项尚未启动。

详细来源、证据范围与建议见 [报告](report.md)；目标和步骤见 [计划](plan.md)。

2026-10-29 种子交付候选抽检：整理 W19 内存调查 45 个 JSON（35 非空，4124 条）和当前精简重放工具至本地 `.tmp/seed-handoff-20261029/`，逐文件 SHA-256 检查通过。VSETIVLI smoke 和调查中一个 STORE 例各本机 1/1 success；并非全量或迁移验收。LOAD/STORE 宽度与结果抽查发现 STORE sh 无成功样本、LOAD 含 ldu 且退出非零；不能由此认定模型源码分支覆盖。版本、缺口与命令见包内 README；目录为本地 ignored 产物，不自动进入 Git。
