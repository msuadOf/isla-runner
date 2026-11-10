# 初态 TOML 配置

目标：按用户要求，在 solve-state 中用具体值固定整寄存器或字段，用 `"?"` / `"x"` 保留符号值；未配置字段不额外限制。

范围：在基于通用修复 09fe582 的独立分支 `feat/initial-state-toml-20261029` 实施，工作树 `.worktree/isla-initial-state-20261029`。保留原工作区、索引及父仓 gitlink。不合并浮点/内存分支。

步骤：先写解析与 SMT 行为测试；复用现有 symbolic、pre_state 和 SMT Extract/Assert；通过 ISAConfig 传递配置。支持 mstatus 字段别名及通用显式位范围；配置错误明确失败。RV64 privilege/SXL/UXL/MPP 域改为显式选择，原 RVV 约束保留。

验证：解析错误、字段边界/重叠、具体/符号混合和重复读取一致性；cargo fmt、库测试与 make solve-MRET 配置 smoke。只在具体命令通过后记录 PASS。

语义：`?` 与 `x` 暂时具有相同求解语义，不引入关注度框架或改变见证输出格式。执行语义仍可约束这些值。

2026-10-29 用户纠正：Isla 不应知道 VS/FS 字段含义。最终取消字段别名和字段表；只接收整寄存器值或 `0b` 部分符号化位模式，具体实现与验证见 [status.md](status.md)。
