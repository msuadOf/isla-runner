# Staged Diff 审核记录

日期：2026-04-26

范围：审核 `isla/` 中基于 `9bb7395fe2efce124117a548d8f8892643eaaf97` 的 staged diff。审核后只对 `isla/isla-lib/src/executor.rs` 和 `isla/isla-lib/src/isarch_exec.rs` 做了低风险工作区修正；未改动 `sail-riscv/`。

## 验证结果

- 初始 `cargo check -p isla-lib` 失败：
  - `start_multi` 的 lifetime 改动导致 `E0621`，`shared_state` 和 `collector` 需要显式 `'ir`。
  - staged diff 中还删除了 `Instr::Call` 分派处对 `call_isla_implemented_function(...)` 的调用，使新增 VMEM builtin 变成死代码。
- 已在工作区修正：
  - 在 `Instr::Call` 参数求值后恢复 `call_isla_implemented_function(...)` 调用。
  - 恢复 `start_multi` 的 `'ir, 'task` 生命周期签名，并修正两个 multi-thread call site。
  - 删除 `isarch_exec.rs` 中对 `zSTORE` / `zLOAD` width 的无条件默认 `4` 覆写；固定 width 现在必须显式设置测试 env。
  - 恢复 `Makefile run` 的 working-tree 配置为 `riscv64_difftest.toml`，避免默认 target 指向与本议题对照前提不一致的 `riscv64.toml`。
  - 删除 `plain-ram` VMEM builtin 中在显式前提校验前直接返回 concrete misaligned exception 的早返回逻辑；misaligned、translation、PMP/PMA/MMIO 等未明确覆盖场景先回退 Sail/IR。
  - 将 VMEM builtin 成功路径的 `zOk...` ctor 查找也改为 required lookup；IR symbol 缺失时返回 `ExecError`，不再静默 intern 新 symbol。
  - 恢复动态 `subrange_internal(...)` 的 SMT 化支持和 `simplify_exp_to_u64(...)`，避免丢掉已有的“动态偏移、固定结果宽度”能力。
- 修正后 `cargo check -p isla-lib` 通过；仍有大量既有 warning。

注意：上述修正当前是工作区修改，不自动代表用户原 staged diff 已被接受。

## 逐项判断

### `isla-lib/src/executor.rs::call_isla_implemented_function`

- decision: `rewrite / keep with fixes`
- reason: 逐函数 gate、`legacy/off/plain-ram` 模式、alignment exception、plain RAM 前提检查，方向符合“等价优先、显式前提、fail closed”。
- semantic risk:
  - `legacy` 仍是不等价快速路径，只能作为性能基线，不能作为最终语义目标。
  - `plain-ram` 依赖 `ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION`、`ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS`、`ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM`，这些是外部声明，不是 executor 证明。
  - symbolic alignment unknown 默认回退 IR；如果显式设置 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`，builtin 会加入低位对齐 SMT 约束并继续，这是受信前提，不是默认语义。
  - concrete misaligned 不再绕过外部前提校验直接由 builtin 构造 Err；只有在 plain-RAM 其它 gate 已通过、且显式设置 `ISLA_RISCV_VMEM_ASSUME_MISALIGNED_FAULTS=1` 时，才返回 alignment exception，否则回退 Sail/IR。
  - `Ok` / `Err` result ctor 均通过 required lookup 查找；symbol 缺失会 fail closed。
- path-explosion evidence: 旧记录显示 `vmem_write_addr` / `vmem_read_addr` 回 IR 会导致 `zSTORE` / `zLOAD` 超时或 fork 激增。
- next action: 保留框架，但后续必须用 fixed `zSTORE` / `zLOAD` 样例重新跑 builtin on/off 对照。

### `isla-lib/src/executor.rs::Instr::Call` 拦截入口

- decision: `keep after local fix`
- reason: staged diff 删除了调用入口，导致 VMEM builtin 完全不会执行。
- semantic risk: 如果只提交原 staged diff，会退回 IR 路径，路径爆炸问题重新出现；同时新增 gate 代码没有运行价值。
- path-explosion evidence: 与 `vmem_*_addr` 回 IR 的旧记录一致。
- next action: 保留当前工作区恢复的调用入口；如果接受该修正，需要把它纳入最终 diff。

### `isla-lib/src/executor.rs::start_multi`

- decision: `drop staged lifetime simplification`
- reason: staged diff 把 `'task` 和 `&'ir` 信息省掉后不能编译。
- semantic risk: 无直接 ISA 语义风险，但阻塞所有验证。
- path-explosion evidence: 无。
- next action: 保留当前工作区恢复的原生命周期形态。

### `isla-lib/src/isarch_exec.rs::apply_instruction_arg_overrides`

- decision: `keep after local fix`
- reason: 结构化 env override 比旧的调试 hook 清楚，适合作为固定样例测试入口。
- semantic risk:
  - 原 staged diff 对 `zSTORE` / `zLOAD` 无条件把 width 默认为 `4`，会改变普通 symbolic instruction generation 的覆盖面；当前工作区已删除这两个默认覆写。
  - 剩余 override 只在对应 `ISLA_RISCV_TEST_*` env 存在时生效，语义边界更清楚。
- path-explosion evidence: 固定 width 有助于稳定对照样例，但不是路径爆炸优化本体。
- next action: 保留解析/设置字段的实现；对固定样例测试显式设置 `ISLA_RISCV_TEST_ZSTORE_WIDTH=4` 或 `ISLA_RISCV_TEST_ZLOAD_WIDTH=4`。

### `isla-lib/src/primop.rs` / `isla-lib/src/smt.rs`

- decision: `keep restored SMT helper, still needs higher-level split strategy`
- reason: staged diff 删除了动态 `subrange_internal(...)` 的 SMT 化和 `simplify_exp_to_u64(...)`。
- semantic risk:
  - 动态 subrange SMT 只适合“动态偏移、结果宽度可化简为常量”的情况。
  - `vmem_utils.sail:224` 的 `data[...]` 在 misaligned split 路径上可能让结果宽度本身动态；这不是 SMT bitvector sort 能直接表示的形态。
- path-explosion evidence:
  - `write-off` / `off` 日志中稳定出现 `SymbolicLength("subrange_internal")`，位置是 `sys/vmem_utils.sail:224`。
  - 恢复动态 subrange 后，45 秒 `write-off` 短跑仍能复现该错误，说明剩余问题是动态宽度/`split_misaligned`，不是单纯缺少动态偏移 SMT。
- next action: 保留 restored helper；后续优先在 `check_misaligned` / `split_misaligned` / alignment guard 层面处理，不要继续扩大 `subrange_internal` 来假装支持动态 bitvector 宽度。

### `Makefile`

- decision: `drop / rewrite; working tree restored to difftest`
- reason: staged diff 把 `make run` 配置从 `riscv64_difftest.toml` 改成 `riscv64.toml`，同时该 target 本身会 `cargo fmt`、复制并覆盖 `log`。
- semantic risk: 容易让测试前提变化但记录不清；也可能覆盖用户已有产物。
- path-explosion evidence: 无。
- next action: 不把 `make run` 作为推荐验证入口；继续使用 `/tmp` 独立 cwd 的手写命令。当前 working tree 已恢复 `riscv64_difftest.toml`，但 staged index 仍需最终选择性 staging。

## 下一步建议

1. 接受或手动 stage 当前 `Makefile`、`executor.rs`、`isarch_exec.rs`、`primop.rs`、`smt.rs` 的 working-tree 修正；否则 staged diff 本身仍有死代码、编译失败、默认 width 覆写、Makefile 配置漂移和动态 subrange 能力删除问题。
2. 不继续在 `subrange_internal` 上追动态 bitvector 宽度；`split_misaligned` alignment guard 已解除显式 aligned 前提下的动态宽度阻断。
3. `range_subset`、`split_misaligned` guard、`pmpRangeMatch` 已按 Phase 3 增加独立 gate 并验证局部收益，建议保留。
4. 早期 `pmpMatchAddr` 大 summary 显式开启后 75 秒没有完成 path；enum sort 修复后可完成路径并降低 fork 深度，但吞吐仍下降，因此单函数 gate 仍应默认关闭。
5. `pmpCheck` exact summary 是当前 PMP 配置/循环层的正结果：它不使用 PMP-off 假设，显式开启后 120 秒内跑通当前 VMEM `off` 样例，PMP 不再是热点。
6. `ISLA_RISCV_ASSUME_PMP_OFF=1` 能让 VMEM `off` 完成并暴露 PMA/MMIO 热点，但它是诊断假设，不是默认语义方案。PMP-off 与 exact PMP summary 的结果共同说明下一层应转向 PMA/MMIO。

## Phase 5 后续审核补充

- `phys_access_check` wrapper 的原始 staged/早期实现不能再按“干净整体回退”描述；当前工作区已改成 `pmp_check_compute` / `pma_check_compute` compute-only，再由 wrapper 最终统一提交 pending event/assert。
- `ISLA_RISCV_ASSUME_CLINT_OFF=1` 的可接受配置必须同时开启 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1`。如果只让 `within_clint=false` 而 `within_mmio_*` 走旧 IR，CLINT range 可能被当成 non-MMIO/RAM；当前工作区已在该组合下返回 `ExecError` fail closed。
- review 后进一步收紧：即使 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` 已开启，CLINT-off 下 `within_mmio_*` 因 HTIF、symbolic width、unsupported address、缺 CLINT base/size 等原因 miss 时，也返回 `ExecError`，不能回退 IR。
- `clint_load` concrete exact-hit unsupported 不是全部“回退 IR”：symbolic paddr 等边界回退，但 exact-hit 后如果需要读取的 CLINT register shape 缺失或不符合预期，会 `ExecError` fail closed。
- Phase 5 smoke 和语义验证目录分别为 [subagents/phase5-smoke-matrix-20260428.md](subagents/phase5-smoke-matrix-20260428.md#L1) 与 [subagents/phase5-semantic-validation-20260428.md](subagents/phase5-semantic-validation-20260428.md#L1)。当前没有新的 blocker，但仍不足以把显式 gate 默认开启。

## Phase 2 Smoke 对照

测试目录：`/tmp/isla-vmem-phase2-smoke-20260426-203634`

公共前提：

- 从 `/tmp` case 子目录运行，未使用 `make run`。
- `cargo run --manifest-path /home/baiyifan/workplace-local/isla-runner/isla/Cargo.toml --bin isarch --`
- `-A /home/baiyifan/workplace-local/isla-runner/isla/rv64d.ir`
- `-C /home/baiyifan/workplace-local/isla-runner/isla/configs/riscv64_difftest.toml`
- `--verbose --probe-all --trace-all -I cur_privilege=Machine list-instructions`
- 显式固定测试 width：
  - `ISLA_RISCV_TEST_ZSTORE_WIDTH=4`
  - `ISLA_RISCV_TEST_ZLOAD_WIDTH=4`

结果：

- `legacy`
  - exit `0`
  - 产物：`legacy/output/rv64d_zSTORE.json`、`legacy/output/rv64d_zLOAD.json`
  - `zSTORE`: 4 条结果，全部 `Retire_Success(())`，memory event count 分布 `{0: 2, 1: 2}`
  - `zLOAD`: 8 条结果，全部 `Retire_Success(())`，memory event count 分布 `{0: 4, 1: 4}`
- `plain-ram-fixed`
  - env：`ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram`，并显式设置 identity translation、PMP permits、plain RAM、aligned 四个假设。
  - exit `0`
  - 产物：`plain-ram-fixed/output/rv64d_zSTORE.json`、`plain-ram-fixed/output/rv64d_zLOAD.json`
  - `zSTORE`: 4 条结果，全部 `Retire_Success(())`，memory event count 分布 `{0: 2, 1: 2}`
  - `zLOAD`: 8 条结果，全部 `Retire_Success(())`，memory event count 分布 `{0: 4, 1: 4}`
  - run log 中未出现 VMEM builtin fallback。
- `off`
  - exit `124`，120 秒超时。
  - 未生成 `output/` JSON。
  - run log 中已经出现大量 `E_SAMO_Access_Fault` 路径，fork 数约 `57..65`。
- `write-off`
  - env：`ISLA_RISCV_VMEM_BUILTIN_MODE=legacy`、`ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=0`、`ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1`
  - exit `124`，90 秒超时。
  - 未生成 JSON；日志中出现 `E_SAMO_Access_Fault`，fork 约 `57`。
  - 同时暴露 `SymbolicLength("subrange_internal")` at `sys/vmem_utils.sail:224`。
- `read-off`
  - env：`ISLA_RISCV_VMEM_BUILTIN_MODE=legacy`、`ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1`、`ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=0`
  - exit `124`，90 秒超时。
  - `zSTORE` 先完成并生成 JSON；`zLOAD` 回 IR 后进入大量 `E_Load_Access_Fault` 路径，fork 约 `53..61`。
  - 日志中还出现 `SymbolicLength("zeros")`，位置是 `prelude/prelude.sail:93`。
- `subrange-check`
  - 恢复动态 subrange SMT 后，用 `write-off` 45 秒短跑验证。
  - 仍然出现 `sys/vmem_utils.sail:224` 的 `SymbolicLength("subrange_internal")`。
  - 判断：剩余错误来自动态结果宽度/`split_misaligned`，不是动态偏移 helper 缺失。
- `plainram-postfix`
  - 目录：`/tmp/isla-vmem-plainram-postfix-20260426-210201`
  - 在 subagent 删除 misaligned early return、恢复 dynamic subrange helper 后重跑。
  - exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
  - 未出现 VMEM builtin fallback，fork 形态仍是 `zSTORE: 2,1,1,0`，`zLOAD: 3,2,2,2,1,1,1,0`。
- `misaligned-faults`
  - 目录：`/tmp/isla-vmem-misaligned-faults-20260426-210707`
  - env：plain-RAM 三个外部前提加 `ISLA_RISCV_VMEM_ASSUME_MISALIGNED_FAULTS=1`，固定 `x1=#x0000000080400002`。
  - exit `0`。
  - `zSTORE` 返回 `Memory_Exception(... E_SAMO_Addr_Align ... #x0000000080400002)`，`memory_event_count=0`。
  - `zLOAD` 返回 `Memory_Exception(... E_Load_Addr_Align ... #x0000000080400002)`，`memory_event_count=0`。
- `required-lookup-regression`
  - 目录：`/tmp/isla-vmem-misaligned-required-20260426-210931` 和 `/tmp/isla-vmem-aligned-required-20260426-210954`
  - 将 `zOk...` success ctor 改成 required lookup 后复跑。
  - concrete misaligned fault gate 仍 exit `0` 并返回对应 alignment exception。
  - aligned plain-RAM 路径仍 exit `0`，`zSTORE` / `zLOAD` 均为 `Retire_Success(())`，每条路径 `memory_event_count=1`。
  - legacy baseline 目录 `/tmp/isla-vmem-legacy-required-20260426-211157` 也 exit `0`，`zSTORE` / `zLOAD` 均为 `Retire_Success(())`，每条路径 `memory_event_count=1`。

说明：

- 第一次 `plain-ram` 尝试因 zsh 环境变量拆分问题无效，几个 assume env 没有实际设置，导致 builtin fallback 后超时；有效结果以 `plain-ram-fixed` 为准。
- 该 smoke 只说明 gate 能实际触发且 `off` 会快速回到爆炸趋势；还不是最终性能 profile。

## Misaligned 关键发现

- `sail-riscv/model/sys/vmem_utils.sail::check_misaligned` 在 `plat_enable_misaligned_access` 为真时直接返回 `false`，否则才检查 `not(is_aligned_addr(...))`。
- 当前 `isla/rv64d.ir` 中 `zplat_enable_misaligned_access` 固化为 `true`。这和 `configs/riscv64_difftest.toml` 里的 `plat_enable_misaligned_access = false` 不一致，说明当前 IR 不能直接当作“misaligned disabled”的语义参考。
- 该不一致不是运行时参数没传进去，而是生成期配置不同：`rv64d.ir` 来自顶层 `repo-sail-riscv` 调用 `cmake --build build --target generated_isla_rv64d`，`sail-riscv/model/CMakeLists.txt` 对 `rv64d` 使用 `${CMAKE_BINARY_DIR}/config/rv64d_v256_e64.json` 作为 `isla-sail --config` 输入。该 JSON 的 `memory.misaligned.supported` 为 `true`，所以 `platform_config.sail` 中 `config memory.misaligned.supported` 被固化成 IR 里的 top-level `let true`。
- `configs/riscv64_difftest.toml` 的 `[const_primops] plat_enable_misaligned_access = false` 只会在 IR 中存在对应 extern call、并被 `insert_instr_primops` 替换为 `PrimopReset` 时生效；当前 `zplat_enable_misaligned_access` 是 top-level `let`，初始化时直接执行 IR setup 写入 `lets`，因此不能由 `-I` 或 TOML 覆盖。
- 因此当 `vmem_write_addr` / `vmem_read_addr` 回 IR 时，IR 会允许进入 `split_misaligned`，随后在 misaligned split 的动态 `bytes` 上碰到动态结果宽度：
  - write: `sys/vmem_utils.sail:224`
  - read: `sys/vmem_utils.sail:139` / `160` 以及 `zeros(...)`
- 这个问题不应靠继续扩大 `subrange_internal` 解决，因为 SMT bitvector sort 不能表达动态宽度。下一步应优先：
  - 在 plain-RAM builtin 成功路径上继续要求显式 aligned 约束；
  - 逐函数确认 `check_misaligned` / `split_misaligned` 是否需要小 summary；
  - 或在 Sail JSON config 层提供 `memory.misaligned.supported=false` 的 IR 变体并重新生成 `rv64d.ir`，使 misaligned-disabled 的外部前提真实进入 IR。

## Phase 3：`range_subset`

- implementation:
  - `executor.rs::call_isla_implemented_function` 增加 `range_subset` 分支。
  - gate：`ISLA_RISCV_BUILTIN_RANGE_SUBSET`，默认开启，`0/false/off` 关闭。
  - 支持边界：4 个参数必须都是同宽 bitvector；宽度未知、不一致或零宽时回退 IR。
  - SMT 公式保持 Sail 定义的模 bitvector 语义：
    - `a_end = (a_begin + a_size) - b_begin`
    - `b_end = (b_begin + b_size) - b_begin`
    - `a_begin = a_begin - b_begin`
    - `a_begin <=u b_end && a_end <=u b_end && a_begin <=u a_end`
- direct evidence:
  - `/tmp/isla-range-subset-wrapper-on-20260426-214121`: `range_subset_equals _:8 _:8 _:8 _:8`，summary 开启，exit `0`，5 条最终路径。
  - `/tmp/isla-range-subset-wrapper-off-20260426-214134`: summary 关闭，exit `0`，7 条最终路径，内部出现 10 次 `range_subset` 返回和 23 次 `operator <=_u` 返回。
- zSTORE/zLOAD evidence:
  - `/tmp/isla-range-subset-on-20260426-213801` 与 `/tmp/isla-range-subset-off-20260426-213910` 都在 VMEM `off` 下命中 `sys/vmem_utils.sail:224` 的 `SymbolicLength("subrange_internal")`。
  - 判断：当前 zSTORE/zLOAD 链路被更早的 `split_misaligned` 动态宽度阻断，不能用它单独评价 `range_subset` 对 PMA 的收益。
- regression:
  - `/tmp/isla-range-subset-regression-20260426-214205`: summary 开启后，显式 plain-RAM/aligned fixed `zSTORE` / `zLOAD` 仍 exit `0`，`Retire_Success(())`，每条路径 1 个 memory event。
- decision:
  - `keep`。这是一个低风险、局部有效、等价的 SMT summary。
  - 但不要期待它单独解决 zSTORE/zLOAD 路径爆炸；下一步应处理 `split_misaligned` 阻断，或做 `matching_pma` / `pmaCheck` 级别 summary。

## Phase 3：`split_misaligned`

- implementation:
  - `executor.rs::call_isla_implemented_function` 增加 `split_misaligned` 分支。
  - gate：`ISLA_RISCV_BUILTIN_SPLIT_MISALIGNED`，默认开启，`0/false/off` 关闭。
  - 支持边界：第二个参数必须是 concrete width，且 width 非零。
  - concrete aligned address 返回 `(1,width)`。
  - symbolic alignment 只有在显式 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 时加入低位对齐 SMT 约束并返回 `(1,width)`。
  - concrete misaligned address、symbolic width、zero width 均回退 IR。
- semantic boundary:
  - 这是 alignment guard，不是完整 misaligned split 实现。
  - 不会把具体 misaligned 访问近似成一次整宽访问。
  - 允许 misaligned 时的多段 memory event、数据切片、跨页/跨权限边界仍由 IR 负责；如果后续要内置化，必须完整建模这些可观察行为。
- direct evidence:
  - `/tmp/isla-split-misaligned-direct-20260426-220039`: `split_misaligned _:64 4` 在显式 aligned 假设下 trace 返回 `(1,4)`；命令 exit `1`，但无运行时 `SymbolicLength`。
- zSTORE/zLOAD evidence:
  - `/tmp/isla-split-guard-vmem-off-20260426-215924`: VMEM `off` 加 split guard 和 aligned 假设后 60 秒超时，未生成 JSON；不再出现运行时 `SymbolicLength("subrange_internal")`。
  - 该结果说明之前的 `sys/vmem_utils.sail:224` 动态结果宽度阻断已被移开，但剩余路径爆炸仍存在。
- regression:
  - `/tmp/isla-split-regression-20260426-215831`: plain-RAM/aligned 与 legacy baseline 均 exit `0`。
  - `zSTORE` 4 条、`zLOAD` 8 条，全部 `Retire_Success(())`，memory event count 分布分别为 `{0: 2, 1: 2}` 和 `{0: 4, 1: 4}`。
- decision:
  - `keep with explicit boundary`。这是低风险的显式前提 guard，适合为后续 PMA/PMP profiling 排除动态宽度干扰。
  - 不应继续在 `subrange_internal` 上尝试支持动态 bitvector result sort；下一步应 profile split guard 后的 VMEM `off` 剩余热点。

## Phase 3：PMP/PMA post-split profile

- instrumentation:
  - `isarch_exec.rs` 增加 `ISLA_RISCV_PROFILE_FORKS=1` 诊断 hook，为每条完成路径打印 `fork_profile=<json>`。
  - 该 hook 只读 solver trace 并输出聚合信息，不改变 executor 语义；不开启 env 时不运行。
- baseline after split:
  - `/tmp/isla-split-profile-vmem-off-20260426-221839`: VMEM `off`、split guard、显式 aligned 前提、固定 zSTORE/zLOAD width。
  - exit `124`，完成 11 条 profile path；`total_fork_events=659`、`max_fork_events=62`。
  - 热点：`pmpAddrMatchType_encdec_backwards=480`、`pmpRangeMatch=147`、`get_X=22`、`pmpMatchAddr=10`。
  - 判断：动态宽度阻断移开后，首要剩余热点是 PMP。
- `pmpRangeMatch`:
  - implementation：`executor.rs::call_isla_implemented_function` 增加 `pmpRangeMatch` 分支。
  - gate：`ISLA_RISCV_BUILTIN_PMP_RANGE_MATCH`，默认开启，`0/false/off` 关闭。
  - 语义边界：四个参数按现有 Isla 整数表达处理，返回 `PMP_NoMatch` / `PMP_PartialMatch` / `PMP_Match` 的 SMT ITE；不删除 partial match 或异常路径。
  - evidence：`/tmp/isla-pmprange-profile-vmem-off-20260426-222825` exit `124`，完成 707 条 profile path；`max_fork_events` 从 baseline 的 62 降到 23。该旧 profile 中有 enum sort 相关线程 panic，只作为趋势证据。
  - decision：`keep`。这是正结果，但只能解决 `pmpRangeMatch` 内部短路，PMP 配置位和循环仍会爆。
- PMP small summaries:
  - implementation：`executor.rs::call_isla_implemented_function` 增加 `pmpAddrMatchType_encdec_backwards` / `pmpCheckRWX` / `pmpLocked` 分支。
  - gates：`ISLA_RISCV_BUILTIN_PMP_ADDR_MATCH_TYPE`、`ISLA_RISCV_BUILTIN_PMP_CHECK_RWX`、`ISLA_RISCV_BUILTIN_PMP_LOCKED`，默认开启，`0/false/off` 关闭。
  - 语义边界：`pmpAddrMatchType` 只接受 2-bit bitvector；`pmpCheckRWX` 先按 access ctor 选择所需 R/W/X 位，unsupported access 或非标准 `Pmpcfg_ent` shape 回退 IR；`pmpLocked` 只读取 L 位，unsupported shape 回退 IR。
  - enum sort fix：summary 返回 enum 时通过 `solver.get_enum(enum_name, enum_size)` 注册并构造同 sort `EnumMember`，避免旧写法在 SMT enum 表缺项时 panic。
  - evidence：`/tmp/isla-pmp-small-profile-vmem-off-20260426-continue2` 75 秒超时但完成 713 条 profile path；`total_fork_events=9780`、`max_fork_events=21`，无运行时 panic/fallback/SymbolicLength；热点转到 `pmpMatchAddr=6239` 和 `pmpCheck=1873`。
  - decision：`keep`。这些是低粒度纯计算 summary，可以保留；但只能把热点推到 PMP 地址匹配和循环层。
- `pmpMatchAddr`:
  - implementation：`executor.rs::call_isla_implemented_function` 增加 `pmpMatchAddr` 分支。
  - gate：`ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR`，默认关闭，只能显式开启。
  - 支持边界：当前只处理 `zsys_pmp_grain=0`、addr/width/pmpaddr/prev 同宽且不超过 128-bit、可提取的 `pmpcfg.A` bits；其它情况回退 IR。
  - evidence：早期 `/tmp/isla-pmpmatch-profile-vmem-off-20260426-222455` 75 秒内 profile 数为 0；enum sort 修复后 `/tmp/isla-pmpmatch-small-profile-vmem-off-20260426-continue` 45 秒完成 142 条 profile path，`total_fork_events=1223`、`max_fork_events=12`。
  - decision：`keep experimental / default off`。该方向能降低 executor fork 深度，但会增加 solver 负担，不能默认启用。
- `pmpCheck` exact summary:
  - implementation：`executor.rs::call_isla_implemented_function` 增加 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 路线，不设置该 env 时回退 IR。
  - 语义边界：要求 `sys_pmp_count` concrete 且不超过 64、`sys_pmp_grain=0`、`pmpcfg_n` / `pmpaddr_n` 可读为 vector、privilege concrete、width 可按 `pmpaddr_n` entry 宽度构造、access fault ctor 可映射；其它情况回退 IR。
  - 语义内容：按 Sail `pmpCheck` 的 entry 优先级合成 `no_match_so_far` 和 `fault_cond`，保留 partial match 直接 access fault、first full match 后 RWX/locked/Machine 判断、Machine no-match allow、非 Machine no-match fault。
  - trace boundary：summary 直接读取 `pmpcfg_n` / `pmpaddr_n`，会补顶层 ReadReg event，但不会复现 IR 内部每次 `pmpReadAddrReg` / helper call 的函数级 trace/probe/stop 观测。
  - evidence：`/tmp/isla-pmpcheck-profile-vmem-off-20260426-continue-120` 120 秒内生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`；完成 76 条 profile path，JSON path 为 86 条；`total_fork_events=618`、`max_fork_events=12`；热点为 `matching_pma_bits_range`、`get_X`、CLINT/MMIO 和 `phys_access_check`，PMP 不再是热点。
  - postfix evidence：`/tmp/isla-pmpcheck-profile-vmem-off-20260427-postfix` 在 fallback/width/read-reg event 修正后仍 exit `0`，JSON path 仍为 86 条，profile 仍为 76 条；`total_fork_events=618`、`max_fork_events=12`，热点排序保持在 PMA/MMIO。
  - decision：`keep explicit / default off for now`。这是完整语义路线下处理 PMP 配置/循环层的正结果；默认是否开启需要更多对照测试和 trace 边界接受。
- `pmpCheck` PMP-off diagnostic:
  - implementation：`executor.rs::call_isla_implemented_function` 增加 `pmpCheck` 分支。
  - gate：`ISLA_RISCV_ASSUME_PMP_OFF`，默认关闭；只有 privilege 参数是 concrete `Machine` 时直接返回 `None()`，否则回退 IR。
  - evidence：`/tmp/isla-pmpoff-profile-vmem-off-20260426-223102` exit `0`，完成 61 条 profile path；下一层热点是 `matching_pma_bits_range`、CLINT load/store 和 `within_mmio_*`。
  - decision：`diagnostic only`。这能定位 PMP 之后的 PMA/MMIO 热点，但不是等价默认语义，不应代替 PMP 语义处理。

## Phase 4 候选：PMA/MMIO

- `pmaCheck`:
  - status：已合入主工作区，仍显式 gate、默认关闭。
  - gate：`ISLA_RISCV_BUILTIN_PMA_CHECK`。
  - reason：PMP exact summary 后热点集中到 `matching_pma_bits_range`、`phys_access_check` 和 MMIO/CLINT。直接 summary `matching_pma_bits_range` 会遇到多个 `Some(PMA_Region)` payload；提升到 `pmaCheck` 层返回 `option(ExceptionType)` 更贴近可观察结果。
  - semantic boundary：保留 PMA first-match、`range_subset` wrap 语义、MMIO region 的 alignment fault、ROM/RAM/MMIO 权限差异。返回 `None` 后仍让 `checked_mem_read/write` 继续做 RAM/MMIO 分派，不提前产生 memory event。
  - observable guard：只有 `zget_config_print_pma` 可证明为 literal false 时接管，否则回退 IR，避免吞掉 `print_log`。
  - evidence：`/tmp/isla-pma-main-20260428-131406/pma-on` exit `0`，`zSTORE=38`、`zLOAD=34`，`SymCtor=0/0`，68 条 profile，`total_fork_events=539`，`max_fork_events=12`；`matching_pma_bits_range` 从热点消失。
  - decision：`keep explicit / default off`。方向正确，但 off/on path 数不同且 JSON 缺 path constraints，不能默认开启。
- `within_mmio_readable` / `within_mmio_writable`:
  - status：已合入主工作区，仍显式 gate、默认关闭。
  - gate：`ISLA_RISCV_BUILTIN_WITHIN_MMIO`。
  - reason：它们决定走 RAM 还是 `mmio_read/write`，影响 memory event 与 MMIO callback/device side effect 分界。
  - semantic boundary：只替换 bool predicate，不能默认 non-MMIO/plain RAM；不接管 `mmio_read/write`、`clint_load/store`、RAM event 或 callback。
  - first version：只支持 `get_config_rvfi=false` 且 `htif_tohost_base=None()` 的 CLINT-only exact predicate；HTIF `Some(base)` 在普通 CLINT-on 下回退 IR，在 CLINT-off 下 fail closed 为 `ExecError`。
  - range semantics：`within_clint` 用 unbounded unsigned integer 公式，当前在 executor 中用 128-bit zero-extend 表达；不使用 64-bit wrapping。
  - evidence：`/tmp/isla-within-mmio-main-20260428-134152/within-on` exit `0`，`zSTORE=38`、`zLOAD=30`，`SymCtor=0/0`，68 条 profile，`total_fork_events=514`，`max_fork_events=11`；`within_mmio_*` / `within_clint` 从热点消失。
  - decision：`keep explicit / default off`。性能正向，但 zLOAD path 数与 normalized shape 仍变化，缺 path constraints 前不能默认开启。
- `phys_access_check`:
  - status：已合入主工作区，仍显式 gate、默认关闭。
  - gate：`ISLA_RISCV_BUILTIN_PHYS_ACCESS_CHECK`，并要求 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 与 `ISLA_RISCV_BUILTIN_PMA_CHECK=1`。
  - reason：它可减少 PMP/PMA option 合并层 fork，但容易把 PMP/PMA 大公式混到一个 wrapper 中。
  - semantic boundary：当前实现只复用 `pmp_check_builtin` 和 `pma_check_builtin`，再合并四象限 option 与 access/alignment fault priority；不复制 PMP/PMA 大公式。
  - fail-closed boundary：Phase 5 审计发现当前 wrapper 还不干净。PMP/PMA 子 summary 完整命中后会提交 `ReadReg` event；若 wrapper 后续因另一子 summary miss 或最终合并失败而回退 IR，没有回滚这些 event。`selected_phys_access_fault` 还可能新构造 inner `SymbolicCtor`。
  - evidence：`/tmp/isla-phys-main-20260428-continue/phys-on` exit `0`，`zSTORE=32`、`zLOAD=27`，`SymCtor=0/0`，59 条 profile，`total_fork_events=425`，`max_fork_events=10`；热点转为 `get_X=91`、`clint_store=80`、`clint_load=65`、`checked_mem_write=58`、`checked_mem_read=51`。
  - decision：`keep explicit / default off`。性能正向且 `phys_access_check` 从热点消失，但 path count 和 normalized shape 继续变化，缺 path constraints 前不能默认开启。
- `clint_load` / `clint_store`:
  - status：`clint_load` concrete exact-hit 首版已合入主工作区，仍显式 gate、默认关闭；`clint_store` 未接管。
  - gate：`ISLA_RISCV_BUILTIN_CLINT_LOAD`。
  - reason：`clint_load` 主要是 offset/width dispatch；`clint_store` 有 guarded register update、`clint_dispatch` 和 callback/interrupt side effect，风险更高。
  - semantic boundary：`clint_load` 首版要求 `get_config_print_clint()` literal false、`paddr` / `width` concrete、精确命中 MSIP/MTIMECMP/MTIME load 分支；每次只读取实际命中的寄存器并补对应 `ReadReg` event。symbolic address、unmapped concrete address、unsupported register shape 均不静默近似。
  - evidence：`/tmp/isla-clint-load-main-20260428-continue/clint-load-on` exit `0`，`zSTORE=32`、`zLOAD=27`，`SymCtor=0/0`，59 条 profile，`total_fork_events=425`，`max_fork_events=10`；与 phys-on 完全一致。日志只有 1 次 `clint_load builtin fallback: symbolic paddr`。
  - decision：`keep explicit / default off, no performance win for current workload`。当前热点中的 `clint_load` 仍是 symbolic paddr 分支链；要继续降低它，需要条件化 `ReadReg` 的 symbolic summary 设计。`clint_store` 第一版只应在 concrete addr/width 精确命中时启用，符号地址先回退 IR。

## Phase 5：显式 gate 语义验证矩阵

语义修正后的 CLINT-off 组合 profile 为 15 条 profile、`total_fork_events=52`、`max_fork_events=5`；fixed signed/unsigned load kind 为 13 条 profile、`total_fork_events=40`、`max_fork_events=4`。下一步不应继续优先压缩剩余小 fork，而应审查每个显式 gate 是否能在其声明前提内作为语义保持的 summary 使用。

| gate | 当前用途 | 外部前提 / 命中条件 | unsupported 行为 | 主要 observable 风险 | 当前结论 |
| --- | --- | --- | --- | --- | --- |
| `ISLA_RISCV_BUILTIN_PMP_CHECK=1` | PMP exact summary | `sys_pmp_count<=64`、`sys_pmp_grain=0`、可读 `pmpcfg_n` / `pmpaddr_n`、privilege concrete、access ctor 支持 | 回退 IR | 函数级 trace/probe/stop 与 helper call 观测不同；顶层 `ReadReg` event 需要保持 | 性能正向，PMP 不再热点；仍默认关闭 |
| `ISLA_RISCV_BUILTIN_PMA_CHECK=1` | PMA exact summary | `zget_config_print_pma=false`、concrete PMA list、width concrete positive、access/res_or_con 支持；aligned 前提可来自 concrete 或 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` | 回退 IR | PMA `None` 后仍必须交给上层 RAM/MMIO 分派；不能产生 memory event；path count 合并需人工判断 | 性能正向，`SymCtor=0/0`；仍默认关闭 |
| `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` | MMIO bool predicate summary | `zget_config_rvfi=false`、`zhtif_tohost_base=None()`、CLINT base/size/address <=64-bit、width concrete positive | 普通 CLINT-on 下回退 IR；CLINT-off 下 `ExecError` fail closed | 直接决定 RAM vs MMIO 分派；不能默认 non-MMIO；HTIF `Some(base)` 不能静默关闭 | 性能正向；仍默认关闭 |
| `ISLA_RISCV_BUILTIN_PHYS_ACCESS_CHECK=1` | PMP/PMA option wrapper | 同时开启 PMP/PMA summary；子 summary 都完整命中；最终 exception ctor 不能是 symbolic ctor | 整体回退 IR；pending event/assert 不提交 | path 合并和 exception observable 仍需人工验证；默认开启仍未批准 | smoke 通过；仍默认关闭 |
| `ISLA_RISCV_BUILTIN_CLINT_LOAD=1` | CLINT concrete exact-hit fast path | `get_config_print_clint=false`、`paddr` / `width` concrete、精确命中 MSIP/MTIMECMP/MTIME load | 回退 IR | 只能读取实际命中的 CLINT register；不能为了 ITE 无条件读多个设备寄存器 | 语义边界清楚但当前无性能收益 |
| `ISLA_RISCV_ASSUME_CLINT_OFF=1` | 显式平台假设 | 测试/init 明确声明当前平台没有 CLINT；`within_mmio_*` 还要求 `rvfi=false` 且 HTIF 为 `None()` | HTIF 非 `None()` 或其它 `within_mmio` miss 时 `ExecError` | CLINT range 保持 MMIO 并在 `mmio_read/write` 中 fault；仍是平台假设，不是真实 CLINT 设备等价 summary | smoke 通过；仍默认关闭 |

CLINT-off 后剩余热点的判断：

- `get_X` / `set_X`：x0 ISA 语义分支，且影响 register event shape；不作为下一步默认 summary。
- `checked_mem_read/write`：fault 路径与 memory event 路径的真实分界；没有 guarded memory event 前不做宽 summary。
- `extend_value`：来自 `lw` / `lwu` 指令变体；用 `ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED=0/1` 分开 profile。语义修正后的 fixed signed/unsigned smoke 均为 13 条 profile、`total_fork_events=40`、`max_fork_events=4`，`extend_value` 不再是主要问题。

后续验收应优先补足：

1. 对每个 gate 的 unsupported 单测：确认回退 IR 或 fail-closed 行为不会留下额外 event / assert。
2. 对 event 边界的抽样 trace：PMP/PMA 只补顶层 `ReadReg` 是否可接受；RAM memory event 与 MMIO callback 是否没有被提前产生或吞掉。
3. 对 path 合并的人工语义判断：当前 JSON 缺 path constraints，不能自动证明 builtin-on 合并路径等价于 IR-off 分裂路径。
4. 对平台假设的配置文档：`ISLA_RISCV_ASSUME_CLINT_OFF=1`、`ISLA_RISCV_ASSUME_PMP_OFF=1` 和 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 必须和等价 summary 区分开。

### Phase 5 subagent 审计补充

只读审计汇总见 [subagents/phase5-gate-audit-summary.md](subagents/phase5-gate-audit-summary.md#L1)。需要修正本文件前文的两个旧判断：

- `phys_access_check` 目前不能称为干净 fail-closed。`pmpCheck` / `pmaCheck` 子 summary 完整命中时会提交 `ReadReg` event；wrapper 后续因另一子 summary miss 或最终合并失败而回退 IR 时，没有回滚这些 event。`selected_phys_access_fault` 还可能在 symbolic option presence 条件下重新构造 inner `SymbolicCtor`。
- CLINT-off 目前不能称为“CLINT 地址不会落成 RAM”。`checked_mem_read/write` 在 `within_mmio_* == false` 时走 `read_ram/write_ram`；当前 CLINT-off 正是让 `within_mmio_*` 在 HTIF `None()` 时返回 false。若目标是 unmapped MMIO fault，需要修改实现；若目标允许 RAM，则必须改 gate 名称和文档语义。

### Phase 5 blocker 修复后补充

- `phys_access_check` fail-closed 风险已修：PMP/PMA 子逻辑拆成 compute-only 与 commit 两段，wrapper 先合并 option/fault，再提交 pending `ReadReg` event 与 alignment assert。若 PMP/PMA summary 没有同时开启、任一子 summary miss，或 symbolic option presence 下不同 fault 需要 inner `SymbolicCtor`，wrapper 直接整体回退 IR。
- CLINT-off 的目标语义已改为 unmapped MMIO fault：`within_clint=false`，但 `within_mmio_readable/writable` 在 HTIF `None()` 时保留 CLINT range predicate，所以 CLINT 地址不会被归为 RAM。
- smoke matrix 汇总见 [subagents/phase5-smoke-matrix-20260428.md](subagents/phase5-smoke-matrix-20260428.md#L1)：
  - CLINT-on P0/P1 仍为 `zSTORE=32`、`zLOAD=27`、59 profiles、`max_fork_events=10`。
  - CLINT-off full gates 为 `zSTORE=8`、`zLOAD=7`、15 profiles、`max_fork_events=5`。
  - fixed signed/unsigned load kind 均为 `zSTORE=8`、`zLOAD=5`、13 profiles、`max_fork_events=4`。
  - negative fallback (`PHYS_ACCESS_CHECK=1`, `PMA_CHECK=0`) exit `0`，有 6 次预期 wrapper fallback，无 runtime panic/`SymbolicLength`。
- 审计结论更新：两个 blocker 已解除到 smoke 级别；默认开启仍未批准，因为 path 合并与 observable 等价还需要后续语义验证。
