# VVTYPE saturation qfaufbv 修复状态

- 状态：已回退专用 primop，改为纯 Sail 实现，并完成显式 `qfaufbv` 验收。
- 根因：`elem != extended` 编译为 `neq_bits`；`neq_bits` 使用 `binary_primop!`，会进入 `try_concretize_bool_exp` 并立即触发正反两次 `check_sat_with`。复杂 VSMUL/vreg/vtype 约束使该 eager 查询在 `qfaufbv` 下出现 2 次 600 秒 SMT timeout。
- 最终修改：不再构造 symbolic `bool`。signed/unsigned SYMBOLIC saturation 先计算 `difference = elem ^ extended`，再用定宽二补数恒等式 `(difference | (0 - difference))[n - 1]` 直接得到 `bits(1)`。生成 IR 只使用既有 `xor_bits`、`sub_bits`、`or_bits` 和 `vector_access`，不需要新增 Isla primop。
- 回退：`isla-lib/src/primop.rs` 中的 `isla_neq_bits_to_bit` 实现、注册和测试均已删除，文件相对 HEAD 无本次差异；Sail 中的 `isla_bool_to_bit`/`isla_neq_bits_to_bit` extern 已删除。
- TDD/语义验证：先建立“不得引用专用 primop、helper IR 只能使用既有位向量操作”的结构测试，初始版本失败；修改后通过。另对 2～8 位所有输入穷举验证 nonzero、unsigned saturation、signed saturation 标志，全部通过。
- IR 验证：隔离副本和原工作区的 `generated_isla_rv64d` 均成功生成；当前 VLEN=128 IR 仅最小同步两个 saturation helper，保留其它既有 IR 改动。
- 修复前显式 `qfaufbv`：`/tmp/isla-vvtype-saturation-qfaufbv-run-20260730`，193 条 Retire_Success、71 条 CLI timeout、2 条 SMT timeout、2 个 timeout SMT dump。
- 专用 primop 对照：`/tmp/isla-vvtype-neq-primop-qfaufbv-run-20260730`，287 条 Retire_Success、5 条 CLI timeout、0 条 SMT timeout、0 个 dump。
- 纯 Sail 最终实验：`/tmp/isla-vvtype-sail-only-qfaufbv-20260730/isla`，40m outer / 30m CLI / 10m SMT / 64 threads / thread interrupt，并明确设置 `TASTIC=qfaufbv`；306 条 Retire_Success、85 条 CLI timeout、0 条 SMT timeout、0 个 dump，最终 `VVTYPE timeout`。
- 结论：纯 Sail 实现同样消除了原 saturation 的 600 秒 SMT timeout。该轮 CLI timeout 多于专用 primop 对照，说明位向量非零公式可能增加完整路径成本；由于未设置 random seed、路径调度有随机性，该数量差异只能作为性能信号，不能单轮定量归因。
- `scripts/run.mk` 支持可选 `TASTIC` 变量；`TASTIC=qfaufbv` 会透传 `--tastic qfaufbv`。
