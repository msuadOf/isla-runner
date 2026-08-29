# 候选热点函数建议

本建议只给优先级，不替代 profile 证据。每个函数都需要按 `plan.md` 的逐函数 gate 协议重新确认。

## 优先级

1. `range_subset`
   - 已完成第一轮 Phase 3 处理，当前建议保留。
   - 原语义接近纯 bitvector 区间包含公式，适合直接改写成 SMT AST。
   - 独立 wrapper 样例确认能减少短路条件编译成 IR jump 后造成的 executor fork。
   - 对 zSTORE/zLOAD 整体爆炸只有局部收益；后续 profile 已确认剩余热点主要转到 PMP 配置/循环层。

2. `split_misaligned`
   - 已完成第一轮 alignment guard，当前建议保留。
   - guard 只在 concrete aligned 或显式 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 时返回 `(1,width)`；concrete misaligned、symbolic width、zero width 回退 IR。
   - 它解除的是 VMEM `off` 链路的动态结果宽度阻断，不是完整 misaligned split 实现。
   - 如果 misaligned 被禁止，应返回对应 alignment exception。
   - 如果 misaligned 被允许，必须保留 split 后多个 memory events、顺序、数据切片、跨页/跨权限边界语义。

3. `pmpRangeMatch`
   - 已完成第一轮 Phase 3 处理，当前建议保留。
   - 75 秒 profile 中完成路径从 split 后 baseline 的 11 条提升到 707 条，单路径最大 fork 从 62 降到 23。
   - 这是纯公式、小枚举返回的正例；适合默认开启并保留独立 gate。
   - 它不能单独解决 PMP 循环和配置位分支，后续不要继续在这一层堆更复杂逻辑。

4. PMP 配置/循环层：`pmpAddrMatchType_encdec_backwards` / `pmpMatchAddr` / `pmpCheck`
   - 已完成当前轮处理，建议保留显式 gate 和语义边界记录。
   - `pmpAddrMatchType_encdec_backwards`、`pmpCheckRWX`、`pmpLocked` 这类小 summary 是正结果，可以消掉配置位解码和权限位短路分支。
   - 早期大而全的单函数 `pmpMatchAddr` summary 是负结果；enum sort 修复后可完成路径并降低 fork 深度，但吞吐仍下降，因此 `ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR` 继续默认关闭。
   - `pmpCheck` exact summary 是当前完整语义路线的正结果：显式开启后保留 PMP entry 优先级、partial match、RWX、locked、Machine privilege 和 no-match 规则，并把下一层热点推到 PMA/MMIO。
   - `ISLA_RISCV_ASSUME_PMP_OFF=1` 仍只能作为诊断或显式 init 前提，不能静默假设 PMP off。

5. `matching_pma` / `matching_pma_bits_range` / `pmaCheck`
   - 当前性能原型方向成立，但语义验收尚未完成。
   - PMP-off 诊断和 `pmpCheck` exact summary 后都显示下一层热点是 `matching_pma_bits_range`、`phys_access_check`、CLINT/MMIO 和 `within_mmio_*`。
   - 不建议直接优先 summary `matching_pma_bits_range` 的 `option(PMA_Region)` 返回；符号地址跨多个 region 时会出现多个 `Some(region)` payload。优先在 `pmaCheck` 层返回 `option(ExceptionType)`。
   - `pmaCheck` summary 必须保留 PMA first-match、`range_subset` wrap 语义、MMIO region alignment fault、ROM/RAM/MMIO 权限差异；返回 `None` 后仍交给上层继续 RAM/MMIO 分派。
   - 20 个 subagent 的结论一致支持该排序：`pmaCheck` 是推荐实验粒度，`phys_access_check` wrapper 和 `within_mmio_*` predicate 都应等 `pmaCheck` on/off 证据稳定后再评估。
   - `/tmp/isla-pma-mmio-20260428-rl4B0N` 的 on/off profile 显示 `pmaCheck` summary 能消掉 `matching_pma_bits_range` 热点，并把 long profile 的 `total_fork_events` 从 618 降到 539，`max_fork_events` 持平 12。
   - 已按“修 final observable 形态”路线消掉 on 侧 access/alignment `SymCtor`：`/tmp/isla-pma-mmio-postalign-20260428-yCeQyU/pma-on-long-2` 中 `zSTORE` / `zLOAD` 的 `SymCtor` 计数为 0/0，profile 仍保持 68 条、`total_fork_events=539`、`max_fork_events=12`。
   - 主工作区已合入 `ISLA_RISCV_BUILTIN_PMA_CHECK`，但仍默认关闭；新增 `get_config_print_pma=false` guard 后，`/tmp/isla-pma-main-20260428-131406/pma-on` 复现 `zSTORE=38`、`zLOAD=34`、`SymCtor=0/0`、68 条 profile、`total_fork_events=539`、`max_fork_events=12`。
   - 该原型仍不能默认开启：剩余 path count 和 memory event address sample 差异不能由 comparator 自动判定等价；下一步需要 main/subagent 基于 PMA 语义和 generator/path sampling 证据做语义判断。

6. `translateAddr` / `pt_walk` / `check_PTE_permission` / `update_PTE_Bits`
   - 高风险，暂不建议在没有明确策略前手写完整 builtin。
   - 可先做 bare/identity translation guard。
   - VM 开启、page walk、A/D bit update、page fault 需要独立计划。

7. MMIO 相关函数
   - 高风险，普通 RAM 快速路径只能在外部显式保证 non-MMIO 和 PMA 全允许时启用。
   - 复杂 PMA/MMIO 应回退 IR 或实现等价 callback/event 行为。
   - `within_mmio_readable/writable` 已作为显式 gate 合入主工作区，仍默认关闭：`ISLA_RISCV_BUILTIN_WITHIN_MMIO=1`。
   - 首版只覆盖 `get_config_rvfi=false` 且 `htif_tohost_base=None()` 的 CLINT-only predicate，使用 unbounded unsigned integer 范围公式，不使用 BV wrapping。
   - `/tmp/isla-within-mmio-main-20260428-134152/within-on` 中 `zSTORE=38`、`zLOAD=30`、`SymCtor=0/0`，68 条 profile，`total_fork_events=514`、`max_fork_events=11`；`within_mmio_*` / `within_clint` 从热点消失。
   - 该 gate 仍不能默认开启：zLOAD path 数和 normalized path shape/memory event sample 与 PMA-only 对照不同，需要 path constraints 或人工语义判断。
   - `clint_load` 风险低于 `clint_store`；`clint_store` 涉及 guarded register update、`clint_dispatch` 和 callback/interrupt side effect，第一版只应处理 concrete addr/width 精确命中。
   - HTIF load/store 当前延后；HTIF predicate 只在能精确保留 `htif_tohost_base` 和 wrapping overlap 语义时考虑。

8. `phys_access_check`
   - 已作为显式 gate 合入主工作区，仍默认关闭：`ISLA_RISCV_BUILTIN_PHYS_ACCESS_CHECK=1`。
   - 实现使用 compute-only 的 `pmp_check_compute` / `pma_check_compute`，再合并 Sail 四象限 option 和 access/alignment fault priority；没有复制 PMP/PMA 大公式。
   - Phase 5 审计发现的 wrapper 级回退不干净问题已修：PMP/PMA 子 summary 先只返回 pending `ReadReg` / alignment assert，wrapper 确认最终合并成功后才提交。
   - 若 PMP/PMA summary 未同时开启、任一子 summary miss，或 symbolic option presence 下不同 fault 会产生 inner `SymbolicCtor`，wrapper 整体回退 IR。
   - `/tmp/isla-phys-main-20260428-continue/phys-on` 中 `zSTORE=32`、`zLOAD=27`、`SymCtor=0/0`，59 条 profile，`total_fork_events=425`、`max_fork_events=10`；`phys_access_check` 从热点消失。
   - negative smoke `/tmp/isla-phase5-smoke-20260428-154603-p5-phys-fallback` 中 `PMA_CHECK=0` 时 exit `0`，有 6 次预期 fallback，无 runtime panic/`SymbolicLength`。
   - 该 gate 仍不能默认开启；下一步是语义验证 path 合并和 observable 边界。

9. `clint_load`
   - concrete exact-hit 首版已合入主工作区，仍默认关闭：`ISLA_RISCV_BUILTIN_CLINT_LOAD=1`。
   - 首版应只做 concrete exact-hit：`paddr` / `width` concrete，精确命中 MSIP、MTIMECMP、MTIME load 分支时才接管；symbolic address 回退 IR。
   - 必须证明 `get_config_print_clint()` literal false，否则回退，避免吞掉 `print_log`。
   - 只读取实际命中的寄存器并补 `ReadReg` event；不要为了 ITE 同时读取 `mip`、`mtimecmp`、`mtime`。
   - `/tmp/isla-clint-load-main-20260428-continue/clint-load-on` 与 phys-on profile 完全一致，只有 1 次 `symbolic paddr` fallback；说明当前 `clint_load=65` 热点并非 concrete exact-hit 能解决。
   - 用户已明确当前不继续考虑 CLINT body summary，因此后续暂不推进 symbolic CLINT load/store；若未来需要真实 CLINT 设备语义，再设计条件化 `ReadReg` / `WriteReg` / callback 保真方案。

10. `ISLA_RISCV_ASSUME_CLINT_OFF`
   - 已按用户确认加入显式平台假设 gate，仍默认关闭：`ISLA_RISCV_ASSUME_CLINT_OFF=1`。
   - 语义是当前符号执行平台没有 CLINT 设备，不是默认 RISC-V 平台等价优化。
   - `within_clint` 直接返回 `false`；`within_mmio_readable/writable` 在 `zget_config_rvfi=false` 且 `zhtif_tohost_base=None()` 时仍返回 CLINT range predicate，否则在 CLINT-off 下返回 `ExecError`，不能回退 IR。
   - 必须配合 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` 使用；否则旧 IR `within_mmio_*` 可能通过 `within_clint=false` 把 CLINT range 判为 non-MMIO。当前实现已在该组合下返回 `ExecError` fail closed。
   - Phase 5 审计发现的 non-MMIO/RAM 风险已修：CLINT range 保持 MMIO，由 `mmio_read/write` 在无 CLINT/HTIF 命中时返回 access fault。
   - smoke `/tmp/isla-phase5-smoke-20260428-154629-p2-clint-off` 中 `zSTORE=8`、`zLOAD=7`、`SymCtor=0/0`，15 条 profile，`total_fork_events=52`、`max_fork_events=5`。
   - guard 后重跑 `/tmp/isla-phase5-validation-p2-rerun-20260428` 保持 `zSTORE=8`、`zLOAD=7`、15 条 profile，未观察到 runtime fallback 或配置错误。
   - fixed signed/unsigned load kind smoke 均为 `zSTORE=8`、`zLOAD=5`、13 条 profile、`total_fork_events=40`、`max_fork_events=4`；guard 后重跑目录为 `/tmp/isla-phase5-validation-p3-final-20260428` 和 `/tmp/isla-phase5-validation-p4-final-20260428`，无 runtime fallback/timeout/`ExecError`/`SymbolicLength`。
   - 该 gate 对当前样例收益很大，但仍是显式平台假设；不能作为真实 CLINT 设备路径的默认等价 summary。

11. CLINT-off 后剩余热点
   - 当前不建议继续作为性能优化优先级处理。
   - `get_X` / `set_X` 的 fork 是 x0 ISA 语义，并且影响 register read/write event shape；不是 32-way GPR 实现分支。除非后续 profile 再证明它是瓶颈，否则不要默认接管。
   - `checked_mem_read/write` 的 fork 是 fault 路径和 memory event 路径的真实分界。当前没有 guarded memory event，宽 summary 不安全。
   - `extend_value` 的 fork 来自 signed/unsigned load 变体；当前建议用 `ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED=0/1` 分开跑 `lw` / `lwu`，而不是把两个指令变体合并进一个 ITE summary。
   - 语义修正后的 fixed signed/unsigned load kind smoke 均为 13 条 profile、`total_fork_events=40`、`max_fork_events=4`，`zSTORE=8`、`zLOAD=5`、`SymCtor=0/0`；`extend_value` 不再是主要问题。
   - 下一步建议转向语义验证矩阵，而不是继续压缩这些剩余小 fork。

## Phase 5 后建议

- Phase 5 smoke 和初轮语义验证已经覆盖当前显式 gate 组合；没有观察到新的路径爆炸 blocker 或超时。
- 当前不建议继续投入 CLINT body summary、`get_X/set_X`、`checked_mem_*`、`extend_value` 宽 summary。
- 如果继续推进，应优先补证据而不是补性能：
  - 为 PMP/PMA/within/phys/CLINT-off 的 unsupported/fail-closed 路径补 targeted 单测。
  - 增强输出比较或 trace 记录，携带 path constraints，减少“path 合并是否等价”只能人工判断的问题。
  - 扩大到更多普通 load/store/amo 或其它 ISA 指令 smoke，确认这些显式 gate 没有只适配 `zSTORE` / `zLOAD`。

## 当前不建议优先做

- `misaligned_order`
  - 本身只是顺序选择，历史热点更可能来自 `split_misaligned` 的短路条件。
  - 除非新 profile 明确显示它稳定造成 fork，否则保持 IR。

- 大而全的 `vmem_read_addr` / `vmem_write_addr` 粗粒度 builtin
  - 可作为性能基线和拦截框架，但不应作为最终语义方案。
  - 应逐步把内部子问题拆成可证明等价的小 summary。

- 默认启用早期大而全的单函数 `pmpMatchAddr` summary
  - 当前实验显示它会把 executor 路径压力转移成 solver 压力；enum sort 修复后虽能完成路径，但吞吐仍下降。
  - 只能保留为显式实验 gate，或作为 `pmpCheck` exact summary 内部的受控子表达式。

- 默认 `ISLA_RISCV_ASSUME_PMP_OFF=1`
  - 该假设能暴露 PMA/MMIO 后续热点，但不是当前 IR 的默认等价语义。
  - 只有在测试/init 明确声明 PMP 被关闭时才能作为前提；否则应处理 PMP 本身或回退 IR。

- `get_X` / `set_X` 默认 summary
  - 剩余分支是 x0 ISA 语义，且会改变 register event shape；收益小、语义审计成本高。

- `checked_mem_read/write` 宽 summary
  - 它们跨越 fault 与 memory event 分界；没有 guarded memory event 支撑时，不应合并。

- `extend_value` summary
  - 纯函数上可行，但当前 profile 中的 fork 代表 `lw` / `lwu` 两个指令变体。优先固定 `ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED` 分别跑。

## 实现建议

- 优先选择纯函数、小返回域、无 side effect、能直接表达成 bitvector/boolean 公式的函数。
- summary 返回值应进入 solver 的 `DefineConst` / expression，而不是提前 fork。
- 需要额外前提时添加显式 `assert` 或要求显式外部配置；不要把前提写死在 builtin 里。
- 对含 memory event、callback、异常副作用的函数，先保守回退 IR，除非已完整建模这些可观察行为。
