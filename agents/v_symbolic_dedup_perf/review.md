# 独立符号执行性能审查

独立子智能体：/root/review_symbolic_performance。

## 结论

SYMBOLIC 预处理后，MASKTYPEI 和寄存器读写、掩码初始化、vrev8 的实现保持；MOVETYPEV 新增 vector_select_masked 包装调用。生成的 IR 未内联该调用，但它没有 jump、长度运算或额外 SMT 运算。isla_vector_select 仍逐 lane 构造 ITE，不产生 executor fork。

潜在开销是两份参数向量的克隆与一次调用栈切换；每条指令发生一次。Instr::Call 计入控制流深度，若使用 max_path_depth 且恰好到边界，可能提前截断；本次测试所用限制配置没有该深度上限。

## 部署与可比性

- 正式 workaround 配置 strict=true，绑定旧 IR hash 与 Sail 行列。部署新 IR 前必须一起更新；本次仅生成独立临时配置，不修改 ../isla 正式配置。
- MASKTYPEI region 从 1448:4–1458:5 映射到 1367:4–1377:5。其他本次控制组的 region 位于未改动文件。
- ControlFlowScope Hash 包含源码位置、函数 Name ID、PC/调用上下文。源码行号变化可改变 concretize 采样选择，即使限制策略相同也不保证路径集合逐项相同。
- 本轮生成 HEAD baseline 与历史 rv64d.ir：去除源位置和断言位置后整个 IR 文件一致；MASKTYPEI/execute 原始函数连源码位置也一致。
- 本轮 HEAD baseline 与新 IR：1902→1903 个函数；剔除位置后仅 execute 的一处调用改变，新增 vector_select_masked。

## 测试边界

使用当前已有 release 二进制的固定副本，未将 ../isla 脏工作树重新编译，也未将旧台账的执行器版本等同于当前二进制。模型差异以同机交替测试归因；旧台账用于背景。所有测试输出在本目录，不覆盖历史 output。
