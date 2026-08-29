# Phase 5 gate audit summary

日期：2026-04-28

范围：按用户要求并行拆分 Phase 5 显式 gate 语义验证任务。所有 subagent 本轮均为只读审计，不修改生产代码。

## 总结

当前 `zSTORE` / `zLOAD` 路径爆炸已经降到可控量级，但 Phase 5 审计发现两个必须先处理的语义风险：

1. `phys_access_check` wrapper 不是干净的整体回退。
   - `pmpCheck` / `pmaCheck` 子 summary 在完整命中时会直接向 solver 提交 `ReadReg` event；如果之后 wrapper 因另一个子 summary miss 或最终 symbolic exception ctor 决定回退 IR，已经提交的 event 不会回滚。
   - `selected_phys_access_fault` 在某些 symbolic presence 条件下会重新构造 `Val::SymbolicCtor`，随后可能进入 final observable；现有“symbolic exception 回退”测试只覆盖子级 payload 已经是 `SymbolicCtor` 的情况。
2. `ISLA_RISCV_ASSUME_CLINT_OFF=1` 当前不能被描述为“CLINT 地址不会变 RAM”。
   - Sail `checked_mem_read/write` 在 `within_mmio_* == false` 时走 `read_ram/write_ram`，不是走 `mmio_read/write`。
   - 当前 CLINT-off 让 `within_clint=false`，并让 `within_mmio_*` 在 HTIF `None()` 时返回 false；如果 PMA 允许该地址范围，CLINT 地址会落入 RAM 路径，除非另有外部约束排除这些地址。

因此，本轮结论是：先修正或重新定义这两个 gate 的语义边界，再继续做 profile 验收或默认开启判断。

## 各任务结论

### A. PMP/PMA event 与 assert 边界

状态：RISK

- 直接调用 `pmpCheck` / `pmaCheck` 时，子 summary 自身的 fallback 边界基本干净：它们先用 `read_register_value_cloned` 读取值，不补 event；确认完整命中后才补 `ReadReg`，`pmaCheck` 的 alignment assert 也延迟到完整命中后。
- `phys_access_check` wrapper 有风险：它调用 `pmp_check_builtin` 后，如果 PMP 完整命中，`ReadReg` 已经提交；随后 PMA miss 或最终合并失败时整体回退 IR，会留下半截 trace。

建议：

- 将 PMP/PMA 子 summary 拆出“compute-only, no side effect”模式，由 wrapper 完整成功后统一补 event/assert。
- 或为 solver event/assert 增加事务式回滚点。
- 补单测：PMP hit 后 PMA miss、PMP/PMA hit 后最终 symbolic exception fallback，都应确认没有残留 event/assert。

### B. `pmaCheck` exact summary

状态：RISK

- 在声明边界内基本保持 Sail 语义：PMA list head-first first-match、`range_subset` wrap 语义、no-match access fault、misaligned fault、权限检查、`None` 后继续交给上层 RAM/MMIO 分派。
- `zget_config_print_pma=false` guard 能避免吞掉 PMA `print_log`，但不是函数级 trace/probe 等价。
- `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 的 assert 延迟到完整 summary 命中后加入；但该 assert 对整个已接管调用生效，不是只对 PMA success path 生效。
- 非 power-of-two width 下 alignment assert helper 可能报错而不是回退，需要后续单测确认。

结论：`pmaCheck` 可继续作为显式 gate 保留，但不能默认开启。

### C. `within_mmio_*` 与 CLINT-off

状态：RISK

- `within_mmio_readable/writable` summary 只在 `rvfi=false`、HTIF concrete `None()` 时接管；HTIF `Some(base)` 或不确定时回退 IR。
- `within_clint` 的 unbounded unsigned integer 范围判断使用 128-bit zero-extend，方向正确。
- HTIF 没有被 CLINT-off 静默关闭。
- 主要风险：当前 CLINT-off 会让 CLINT 地址在 `checked_mem_*` 中变成 non-MMIO，从而走 RAM 路径；“CLINT 地址经 `mmio_read/write` 返回 access fault”的文档描述不成立。

建议：

- 先明确目标语义：无 CLINT 是 unmapped MMIO fault，还是普通 RAM。
- 若目标是 unmapped MMIO fault，`within_mmio_*` 在 CLINT-off 下不能直接返回 false；应让 CLINT range 仍被识别为 MMIO hole，再由 `mmio_read/write` fault。
- 补 CLINT 地址精确命中测试：CLINT-off 开启、`paddr=plat_clint_base`、width 4/8，断言是否出现 RAM event。

### D. `phys_access_check` option 合并

状态：RISK

- 四象限 `None/None`、`Some/None`、`None/Some`、`Some/Some` 在 concrete exception ctor 情况下匹配 Sail。
- `highestPriorityAlignmentOrAccessFault` 的 priority 和平级取右侧规则匹配 Sail。
- 风险：`selected_phys_access_fault` 可在 symbolic option presence 条件下新构造 `Val::SymbolicCtor`，`combine_phys_access_options` 没有再阻止该 symbolic ctor 进入 `option(ExceptionType)` payload。

建议：

- 补四象限单测和 symbolic option 条件测试。
- 若 final observable 禁止 symbolic exception ctor，则在 `selected_phys_access_fault` 生成 symbolic ctor 后回退；同时要解决回退前子 summary event 已提交的问题。

### E. `clint_load` concrete exact-hit

状态：PASS

- exact-hit 表匹配 Sail 的 MSIP、MTIMECMP、MTIME load 成功分支。
- 命中后只读取实际需要的一个 register，不会为了 ITE 无条件读 `zmip`、`zmtimecmp`、`zmtime`。
- `get_config_print_clint=false` guard 合理；symbolic address/width、非 exact-hit、寄存器形态不符均回退或 fail-closed。
- 当前 workload 没收益，因为热点来自 symbolic paddr 下的 CLINT 分支链；concrete exact-hit fast path 不命中核心问题。

结论：保留为显式、默认关闭 fast path；不继续做 symbolic CLINT body summary。

### F. CLINT-off 后剩余热点

状态：PASS

- `get_X` / `set_X` 剩余 fork 是 x0 ISA 语义，且影响 register event shape，不是 32-way GPR 实现分支。
- `checked_mem_read/write` 剩余 fork 是 fault vs memory event 的真实语义边界；没有 guarded memory event 前不应合并。
- `extend_value` 来自 `lw` / `lwu` 指令变体；用 `ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED=0/1` 分开 profile。
- 当前没有值得立即继续优化的剩余热点。

### G. 后续验证矩阵

状态：RISK

- 轻量命令：`cargo check -p isla-lib`、`cargo test -p isla-lib executor::tests`。
- profile smoke：CLINT-off、固定 `lw/lwu`、CLINT load fallback、phys child summary negative。
- 当前工具缺口：JSON/comparator 缺 path constraints、完整 event trace、callback/MMIO side channel，不能自动证明 path 合并等价。

建议执行顺序：

1. 先修 `phys_access_check` wrapper 的副作用回退问题。
2. 重新定义或修正 CLINT-off 的地址分派语义。
3. 再跑 Phase 5 smoke 矩阵。
4. 最后做人工/大模型 path 合并语义判断。
