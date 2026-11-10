# 内存协同审阅状态

2026-11-02：审阅完成，**结构方向可接受，整套实现需修改后接纳**。受审 Sail-RISC-V c70482a7 与 Isla bdd047bc；生产源码只读，已有未提交内容保留。

- 9个完整IR主探针退出0、16条JSON（8个finished，1个partial）；重现两个P1：concrete零快照被符号地址绕过、GPR初值缺失导致sd x6重放输入改变；异常返回值仍含Sym。字段求值错误传播另有静态P2缺口。
- segment越界、vstart最大/零、SC外部响应两路及压缩load有限行为符合预期；四配置各159个模型文件、5个IR路径和配置哈希一致，79预算/130region/22锚点有效。
- 最初三个VS=Off的向量探针被译码拒绝，日志保留；显式使能VS后在新目录复验，不作为模型回归。
- 自由地址store的partial另行debug复跑，确认一条路径在vmem_utils.sail:224报SymbolicLength，summary正确计错；未定位其历史引入点，不宣称全路径通过。
- Sail-RISC-V另有P2：全寄存器访存早退漏清零vstart。4次隔离IR后态断言确认全1仍保留，原函数体未改；非陷阱策略新增进入该成功域，需补退出清零。
- 下一步：沿现有MemoryCallbacks/SeqMemory统一concrete与数组状态，在同一最终Model补齐GPR和返回值，必需字段查询失败退出gen；全寄存器访存早退补vstart清零；然后重跑反例。未重新构建/全量回归/硬件验证，未生成生产IR、提交或移动分支。

[报告与接纳建议](report.md)、[计划](plan.md)、[探针](probe.py)、[证据断言](verify_evidence.py)、[版本](versions.json)。

后续现行修订：用户授权的F1–F5修复及独立Sol复审已完成，原反例适用于本报告的未修改基线；当前未提交候选通过限定验证和独审，详见[修复状态](../coordinated_memory_fixes_20261102/status.md)。本页保留原审阅结论作为修复前历史。
