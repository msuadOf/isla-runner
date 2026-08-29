# Phase 5 semantic validation 2026-04-28

本文件汇总 Phase 5 smoke 后的语义验证子任务。子任务均为只读验证；主 agent 另行补了 CLINT-off 配置保护和本地回归。

## A. `clint_load` gate 对照

- 对照目录：`/tmp/isla-phase5-taskA-p0-p1-clint-load/`。
- P0 和 P1 的 `zSTORE` / `zLOAD` 数量相同：`32/27`。
- `ret_val` 计数和 memory event count 分布相同：
  - `zSTORE`: `{0:30, 1:2}`
  - `zLOAD`: `{0:23, 1:4}`
- 差异只出现在 path shape、exception 字段顺序/`Sym` 噪声，以及 memory event address sample。
- P1 只有 1 次预期 fallback：`clint_load builtin fallback: symbolic paddr`。
- 判断：concrete exact-hit `clint_load` 对当前 workload 没有性能收益，但在当前 smoke 粒度下没有观察到 ret/memory-event 可观察差异；它不是 strict byte-for-byte normalizer zero-diff。

## B. CLINT-off full gates 边界

- 对照报告：`/tmp/isla-phase5-taskB-p2-clint-off-observable-boundary.txt`。
- `zSTORE`: 8 条，6 条 `Memory_Exception`，2 条 `Retire_Success`。
- `zLOAD`: 7 条，3 条 `Memory_Exception`，4 条 `Retire_Success`。
- 所有异常分别为 `E_SAMO_Access_Fault` / `E_Load_Access_Fault`。
- memory event 分布：
  - `zSTORE`: `{0:6, 1:2}`
  - `zLOAD`: `{0:3, 1:4}`
- 所有 `Memory_Exception` path 的 memory event 数为 0；所有 `Retire_Success` path 的 memory event 数为 1。
- CLINT effective address sample 覆盖到 3 条 path，均为 `Memory_Exception` 且 memory event 数为 0，未观察到 CLINT range 静默走 RAM。
- 局限：当前 JSON 不带完整 path constraints，因此这是 smoke/sample 证据，不是全输入形式化证明。

## C. `phys_access_check` fail-closed negative

- 对照目录：`/tmp/isla-phase5-task-c-phys-fallback-negative/`。
- 当 `ISLA_RISCV_BUILTIN_PHYS_ACCESS_CHECK=1` 但 `ISLA_RISCV_BUILTIN_PMA_CHECK=0` 时，出现 6 次预期 fallback，原因均为 `PMP/PMA summaries are not both enabled`。
- 未观察到 runtime panic、运行时 `SymbolicLength(...)`、timeout 或非预期 `ExecError`。
- 聚合结果：
  - `zSTORE`: 22 条，18 条 `Memory_Exception` 且 memory event 数均为 0；4 条 `Retire_Success`，其中 2 条有 write event。
  - `zLOAD`: 20 条，8 条 `Memory_Exception` 且 memory event 数均为 0；12 条 `Retire_Success`，其中 4 条有 read event。
- 判断：wrapper 在子 summary 未同时启用时按预期回退 IR，没有观察到先提交子 summary event 后再 fallback 的副作用泄漏。

## D. gate / default 审计

- full-gates 组合未发现新的代码级 blocker。
- 默认值边界：
  - `ISLA_RISCV_BUILTIN_PMP_CHECK`、`ISLA_RISCV_BUILTIN_PMA_CHECK`、`ISLA_RISCV_BUILTIN_WITHIN_MMIO`、`ISLA_RISCV_BUILTIN_PHYS_ACCESS_CHECK`、`ISLA_RISCV_BUILTIN_CLINT_LOAD`、`ISLA_RISCV_ASSUME_CLINT_OFF`、`ISLA_RISCV_ASSUME_PMP_OFF` 默认关闭。
  - `ISLA_RISCV_BUILTIN_PMP_RANGE_MATCH`、`ISLA_RISCV_BUILTIN_PMP_ADDR_MATCH_TYPE`、`ISLA_RISCV_BUILTIN_PMP_CHECK_RWX`、`ISLA_RISCV_BUILTIN_PMP_LOCKED` 默认开启。
  - `ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR` 默认关闭。
- `ISLA_RISCV_ASSUME_CLINT_OFF=1` 的 unmapped-MMIO fault 语义依赖 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1`。如果只让 `within_clint` 返回 false，而 `within_mmio_*` 仍走 IR，则 CLINT range 可能被判成 non-MMIO 并进入 RAM 路径。
- 主工作区已据此增加保护：`ISLA_RISCV_ASSUME_CLINT_OFF=1` 且 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=0` 时，`within_clint` 侧 fail closed 为 `ExecError`，避免静默 RAM。
- review 后进一步收紧：`ISLA_RISCV_ASSUME_CLINT_OFF=1` 且 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` 时，`within_mmio_*` summary 的任何 miss/fallback 也必须 `ExecError`，不能回退 IR。否则 fallback IR 会调用 `within_clint=false`，仍可能把 CLINT range 判为 RAM。
- `clint_load` unsupported 情况通常回退 IR；但 exact-hit 时若 CLINT register shape 缺失或不符合预期，会返回 `ExecError` fail closed，而不是构造近似值。

## Main-agent rerun after CLINT-off guard

- 重新跑 full-gates P2：`/tmp/isla-phase5-validation-p2-rerun-20260428`。
- exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
- `zSTORE=8`，memory event count `{0:6, 1:2}`。
- `zLOAD=7`，memory event count `{0:3, 1:4}`。
- profile 数 15；未观察到 runtime fallback 或 CLINT-off 配置错误。
- 重新跑 fixed load-kind：
  - signed `lw`: `/tmp/isla-phase5-validation-p3-final-20260428`，`zSTORE=8`、`zLOAD=5`、`SymCtor=0/0`、13 profiles、`total_fork_events=40`、`max_fork_events=4`，无 runtime fallback/timeout/`ExecError`/`SymbolicLength`。
  - unsigned `lwu`: `/tmp/isla-phase5-validation-p4-final-20260428`，`zSTORE=8`、`zLOAD=5`、`SymCtor=0/0`、13 profiles、`total_fork_events=40`、`max_fork_events=4`，无 runtime fallback/timeout/`ExecError`/`SymbolicLength`。
- 负向配置验证：`ISLA_RISCV_ASSUME_CLINT_OFF=1` 且 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=0` 时，相关 path 报 `Type error: ISLA_RISCV_ASSUME_CLINT_OFF=1 requires ISLA_RISCV_BUILTIN_WITHIN_MMIO=1 to avoid treating CLINT range as RAM`。测试 harness 进程仍可能 exit `0`，但 per-path 已 fail closed。

## Phase 5 conclusion

- 当前路径爆炸在显式 full-gates + CLINT-off 平台假设下已压到可控范围：mixed load kind `max_fork_events=5`，fixed signed/unsigned load kind `max_fork_events=4`。
- 语义风险已从“明显 blocker”收敛到“显式 gate 的外部前提和 path-constraint 证明不足”。
- 这些 gate 仍不能默认开启；下一阶段如果继续推进，应补 path constraints / targeted function tests，或进入更广的 ISA 指令 smoke，而不是继续压缩 `get_X`、`checked_mem_*`、`extend_value` 这些小 fork。
