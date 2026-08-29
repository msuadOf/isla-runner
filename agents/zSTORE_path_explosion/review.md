# 文档审核结论

本文件审核 `agents/zSTORE_path_explosion/` 旧文档是否还能指导后续工作。旧原文已保存在 `deprecated/`，当前目录只保留可执行摘要。

## 归档内容

- `deprecated/plan.legacy.md`：旧计划和大量 2026-04-25 执行记录。
- `deprecated/review.legacy.md`：旧 VMEM builtin 语义一致性 review，以及后续修正状态。
- `deprecated/suggest.legacy.md`：旧候选函数排序和实现建议。

这些文件暂时不删除，供人工判断是否还有保留价值。

## 可继续复用的信息

旧文档中仍有价值的部分：

- `vmem_read_addr` / `vmem_write_addr` 粗粒度 builtin 曾显著缓解 `zLOAD` / `zSTORE` 路径爆炸。
- 旧 builtin 的主要语义风险已经识别清楚：对齐异常、地址翻译、PMP/PMA/MMIO、misaligned split、LR/SC、AMO、`aq/rl`、callback、副作用等可能被跳过。
- `plain-ram` 这类模式只有在外部显式保证 identity translation、PMP permits、普通 RAM、非 MMIO、aligned、非 aq/rl/res 时才可能作为等价快速路径。
- `range_subset`、`pmpRangeMatch` 这类纯公式或小枚举返回函数，适合优先尝试 SMT summary。
- `misaligned_order` 本身不应是优先目标；如果继续追 misaligned 相关热点，应优先看 `split_misaligned` 和它的短路条件。

## 不能直接沿用的问题

旧文档不能直接作为后续工作计划，原因是：

- 历史执行记录太长，混杂了已完成、临时测试、命令细节和当时的判断。
- 多处写法默认承接 staged 语义修正，但用户已经明确对之前修改不满意，不能把这些改动视为已接受基线。
- 一些 commit 名称和“新增提交”在当前 `isla/` 状态下表现为 staged diff，而不是当前 HEAD 之后的正式提交。
- 旧文档强调 VMEM builtin 框架，但没有足够突出当前新的最高原则：遍历 ISA 真实细节，避免实现方式引入的路径；无法等价时 fail closed。
- 对“改 `sail-riscv` 还是改 `isla`”的 trade-off 写得不够明确；当前应明确优先改 Isla，只有实现方式本身造成不可接受爆炸且 Isla 侧摘要代价过高时再改 Sail 模型。

## 对后续工作的指导性判断

当前目录经整理后可以指导下一步，但必须按以下方式使用：

- 以 `principles.md` 作为语义红线。
- 本文件是旧文档审核结论，不再代表当前执行进度。
- 当前执行状态以 `status.md` 和 `audit.md` 的 Phase 3+ PMP/PMA 记录为准。
- 以 `suggest.md` 作为候选函数优先级，但每个函数仍要重新 profile 和 gate 对照。
- 以 `deprecated/` 作为证据库，不作为当前权威计划。

当前最新结论：PMP 配置/循环层已经有显式 `pmpCheck` exact summary 正结果；下一步转向 PMA/MMIO，优先评估 `pmaCheck` 层 summary。
