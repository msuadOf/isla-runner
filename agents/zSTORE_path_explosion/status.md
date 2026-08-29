# 当前状态

日期：2026-04-27

本轮范围：先整理 `agents/zSTORE_path_explosion/` 文档；用户确认后继续执行 Phase 1，审核 `isla/` staged diff，并对 `isla/isla-lib/src/executor.rs` / `isla/isla-lib/src/isarch_exec.rs` 做了低风险工作区修正。用户随后已把前一轮改动提交到 `isla/`，当前继续完整语义路线，处理 PMP 配置/循环层。

## 已完成

- 阅读了 `agents/findings.md`。
- 阅读并审核了本议题旧文档：
  - `plan.md`
  - `review.md`
  - `suggest.md`
- 将旧原文归档到：
  - `deprecated/plan.legacy.md`
  - `deprecated/review.legacy.md`
  - `deprecated/suggest.legacy.md`
- 新增 `deprecated/README.md`，说明旧文档不是当前权威计划。
- 新增 `principles.md`，提炼后续路径爆炸优化原则。
- 重写 `plan.md`，把下一步收敛为先审核 staged diff，再逐函数确认爆炸来源和语义边界。
- 重写 `review.md`，给出旧文档能否指导后续工作的审核结论。
- 重写 `suggest.md`，保留候选热点函数优先级。
- 新增 `audit.md`，记录 `isla/` staged diff 的逐项审核结论。
- 发现 staged diff 中 VMEM builtin 调用入口被删除，已在工作区恢复。
- 发现 staged diff 中 `start_multi` 生命周期改动导致 `cargo check -p isla-lib` 失败，已在工作区恢复可编译形态。
- 发现 `isarch_exec.rs` 中 `zSTORE` / `zLOAD` width 仍会默认覆写为 `4`，已改为只通过显式 `ISLA_RISCV_TEST_*_WIDTH` env 覆写。
- 恢复 `Makefile run` 的 working-tree 配置为 `riscv64_difftest.toml`。
- 将 `plain-ram` VMEM builtin 中的 concrete misaligned exception 收紧为显式 gate：只有在 `validate_plain_vmem_read/write` 已确认 plain-RAM 其它前提、且设置 `ISLA_RISCV_VMEM_ASSUME_MISALIGNED_FAULTS=1` 时，才直接返回 alignment exception；否则回退 Sail/IR。
- 将 VMEM builtin 成功路径的 `zOk...` ctor 查找改为 required lookup，避免 IR symbol 缺失或改名时静默 intern 新 symbol。
- 恢复 `primop.rs` / `smt.rs` 中动态 `subrange_internal(...)` 的 SMT helper；但验证显示 `vmem_utils.sail:224` 的剩余错误来自动态结果宽度，需要在 `split_misaligned` 或 alignment guard 层处理。
- 增加 `range_subset` 的 SMT summary gate：`ISLA_RISCV_BUILTIN_RANGE_SUBSET` 默认开启，设为 `0` 可回退 IR；summary 对四个同宽 bitvector 保持 Sail 的模加减和 unsigned 比较语义。
- 增加 `split_misaligned` 的 alignment guard：`ISLA_RISCV_BUILTIN_SPLIT_MISALIGNED` 默认开启，设为 `0` 可回退 IR；只在 concrete aligned 或显式 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 时返回 `(1,width)`，concrete misaligned / symbolic width / zero width 仍回退 IR。
- 增加 `ISLA_RISCV_PROFILE_FORKS=1` 诊断 hook，在 `isarch` 测试入口为每条完成路径打印 `fork_profile=<json>`，用于定位剩余 fork 热点；不开启该 env 时不影响执行。
- 增加 `pmpRangeMatch` 的 SMT summary gate：`ISLA_RISCV_BUILTIN_PMP_RANGE_MATCH` 默认开启，设为 `0` 可回退 IR；summary 保留现有 Isla 整数比较和 `PMP_NoMatch` / `PMP_PartialMatch` / `PMP_Match` 三值返回语义。
- 增加小粒度 PMP summary：`pmpAddrMatchType_encdec_backwards`、`pmpCheckRWX`、`pmpLocked` 默认开启，可分别通过 `ISLA_RISCV_BUILTIN_PMP_ADDR_MATCH_TYPE=0`、`ISLA_RISCV_BUILTIN_PMP_CHECK_RWX=0`、`ISLA_RISCV_BUILTIN_PMP_LOCKED=0` 回退 IR。
- 修正 enum SMT 构造：summary 返回 Sail enum 时先通过 `solver.get_enum(enum_name, enum_size)` 注册 enum sort，再构造同 sort 的 `EnumMember`，避免旧 profile 中 `smt.rs` enum 表缺项 panic。
- 增加实验性 `pmpMatchAddr` summary gate：`ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR` 只有显式设置时启用。早期 75 秒 profile 无完成路径；enum sort 修正和小粒度 PMP summary 后，45 秒 profile 可完成 142 条路径、`max_fork_events=12`，但吞吐仍低于默认路线，因此继续保持默认关闭。
- 增加完整语义 `pmpCheck` exact summary gate：`ISLA_RISCV_BUILTIN_PMP_CHECK=1` 时启用，按 PMP entry 优先级合成 `pmpMatchAddr`、partial match、RWX、locked、Machine privilege 和 no-match 规则；不设置该 env 时默认回退 IR。
- 增加显式诊断用 `pmpCheck` PMP-off gate：`ISLA_RISCV_ASSUME_PMP_OFF=1` 且 privilege 为 concrete `Machine` 时返回 `None()`；其它情况回退 IR。该 gate 只能用于定位下一层热点，不能作为默认语义方案。

## 当前观察

- `isla/` 分支：`fix-memory-sym-pathboomb-semantics`。
- `isla/` HEAD：`7fd0b06`（`Ignore local worktrees`，只提交了 `isla/.gitignore` 中的 `.worktrees/` 忽略规则）。
- 新增隔离工作区：`isla/.worktrees/zstore-pma-mmio`，分支 `zstore-pma-mmio`，从 `7fd0b06` 创建。
- 用户已提交前一轮改动；当前 `isla/` 工作区的新增代码修改集中在 `isla-lib/src/executor.rs`，另有既有本地 `log` 改动未处理。
- 已将原 `isla/` 工作区的未提交改动移植到新 worktree：跟踪文件修改包括 `isla-lib/src/executor.rs` 和 `log`；未跟踪的 profile/output/solver/xlsx 等证据产物也已原样复制。
- 审核结论见 `audit.md`。

## 验证

- 初始 `cargo check -p isla-lib`：失败，错误为 `start_multi` lifetime `E0621`。
- 修正 `executor.rs` 后再次运行 `cargo check -p isla-lib`：通过；仍有大量既有 warning。
- 收紧 `isarch_exec.rs` 默认 width 覆写后再次运行 `cargo check -p isla-lib`：通过；仍有大量既有 warning。
- Phase 2 smoke 对照目录：`/tmp/isla-vmem-phase2-smoke-20260426-203634`
  - `legacy`: exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
  - `plain-ram-fixed`: exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`，未出现 VMEM builtin fallback。
  - `off`: exit `124`，120 秒超时，未生成 JSON，run log 已出现大量 access fault 路径和 `57..65` fork。
- 单函数 gate 对照目录：
  - `/tmp/isla-vmem-phase2-gates-20260426-205253-write`: `write-off` exit `124`，90 秒超时，暴露 `sys/vmem_utils.sail:224` 的 `subrange_internal` dynamic width 问题。
  - `/tmp/isla-vmem-phase2-gates-20260426-205253-read`: `read-off` exit `124`，90 秒超时，`zSTORE` 先完成，`zLOAD` 回 IR 后 fork 约 `53..61`。
  - `/tmp/isla-vmem-subrange-check-20260426-205639`: 恢复 dynamic subrange helper 后短跑，`sys/vmem_utils.sail:224` 错误仍存在，说明需要处理 `split_misaligned` / alignment。
- subagent 后重跑 plain-RAM：
  - `/tmp/isla-vmem-plainram-postfix-20260426-210201`: exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`，未出现 VMEM builtin fallback。
- concrete misaligned 显式 fault gate：
  - `/tmp/isla-vmem-misaligned-faults-20260426-210707`: `x1=#x0000000080400002`，设置 `ISLA_RISCV_VMEM_ASSUME_MISALIGNED_FAULTS=1`。
  - `zSTORE` 返回 `Memory_Exception(... E_SAMO_Addr_Align ... #x0000000080400002)`，`memory_event_count=0`。
  - `zLOAD` 返回 `Memory_Exception(... E_Load_Addr_Align ... #x0000000080400002)`，`memory_event_count=0`。
- aligned 回归：
  - `/tmp/isla-vmem-aligned-postfault-20260426-210750`: `x1=#x0000000080400000`，设置 plain-RAM/aligned 显式前提。
  - `zSTORE` / `zLOAD` 均 exit `0`，`Retire_Success(())`，每条路径 `memory_event_count=1`。
- required lookup 回归：
  - `/tmp/isla-vmem-misaligned-required-20260426-210931`: exit `0`，仍返回 `E_SAMO_Addr_Align` / `E_Load_Addr_Align`，无 memory event。
  - `/tmp/isla-vmem-aligned-required-20260426-210954`: exit `0`，仍返回 `Retire_Success(())`，每条路径 1 个 memory event。
  - `/tmp/isla-vmem-legacy-required-20260426-211157`: legacy baseline exit `0`，仍返回 `Retire_Success(())`，每条路径 1 个 memory event。
- `range_subset` Phase 3：
  - `/tmp/isla-range-subset-wrapper-on-20260426-214121`: `range_subset_equals _:8 _:8 _:8 _:8`，summary 开启，exit `0`，5 条最终路径。
  - `/tmp/isla-range-subset-wrapper-off-20260426-214134`: summary 关闭，exit `0`，7 条最终路径，日志中出现 10 次 `range_subset` 返回和 23 次 `operator <=_u` 返回。
  - `/tmp/isla-range-subset-on-20260426-213801` / `/tmp/isla-range-subset-off-20260426-213910`: VMEM `off` 的 zSTORE/zLOAD 链路仍被 `sys/vmem_utils.sail:224` 的 `subrange_internal` dynamic width 阻断，不能单独评价 PMA 链路收益。
  - `/tmp/isla-range-subset-regression-20260426-214205`: 默认开启 summary 后，plain-RAM/aligned fixed `zSTORE` / `zLOAD` 仍 exit `0`，`Retire_Success(())`，每条路径 1 个 memory event。
- `split_misaligned` Phase 3：
  - `/tmp/isla-split-misaligned-direct-20260426-220039`: `split_misaligned _:64 4`，设置 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`，trace 中 `Final result` 为 `(1,4)`；命令本身 exit `1`，但无运行时 `SymbolicLength`。
  - `/tmp/isla-split-guard-vmem-off-20260426-215924`: VMEM `off` 加 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 后 60 秒仍超时，未生成 JSON；日志不再出现运行时 `SymbolicLength("subrange_internal")`，只剩编译 warning 中的同名字源码文本。
  - `/tmp/isla-split-regression-20260426-215831`: plain-RAM/aligned 和 legacy baseline 均 exit `0`；`zSTORE` 4 条、`zLOAD` 8 条，全部 `Retire_Success(())`，memory event count 分布分别为 `{0: 2, 1: 2}` 和 `{0: 4, 1: 4}`。
- PMP/PMA post-split profile：
  - `/tmp/isla-split-profile-vmem-off-20260426-221839`: split guard + VMEM `off` baseline，exit `124`，完成 11 条 profile path；`total_fork_events=659`、`max_fork_events=62`；热点为 `pmpAddrMatchType_encdec_backwards=480`、`pmpRangeMatch=147`、`get_X=22`、`pmpMatchAddr=10`。
  - `/tmp/isla-pmpmatch-profile-vmem-off-20260426-222455`: 显式开启 `ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR=1`，exit `124`，profile 数为 0；该 summary 当前不适合默认启用。
  - `/tmp/isla-pmprange-profile-vmem-off-20260426-222825`: 默认开启 `pmpRangeMatch` summary，exit `124`，完成 707 条 profile path；`total_fork_events=10230`、`max_fork_events=23`；热点为 `pmpAddrMatchType_encdec_backwards=5788`、`pmpCheck=1799`、`get_X=1414`、`pmpMatchAddr=955`、`matching_pma_bits_range=274`。该旧 profile 中有 enum sort 相关线程 panic，只作为趋势证据。
  - `/tmp/isla-pmpoff-profile-vmem-off-20260426-223102`: 显式 `ISLA_RISCV_ASSUME_PMP_OFF=1` 诊断，exit `0`，完成 61 条 profile path；`total_fork_events=490`、`max_fork_events=11`；下一层热点为 `matching_pma_bits_range`、`clint_store`、`clint_load`、`within_mmio_*`。
- PMP 配置/循环 exact summary:
  - `/tmp/isla-pmp-small-profile-vmem-off-20260426-continue2`: 小粒度 PMP summary 后，75 秒超时，完成 713 条 profile path；`total_fork_events=9780`、`max_fork_events=21`；热点转为 `pmpMatchAddr=6239`、`pmpCheck=1873`、`get_X=1426`、`matching_pma_bits_range=242`；无运行时 panic/fallback/SymbolicLength。
  - `/tmp/isla-pmpmatch-small-profile-vmem-off-20260426-continue`: enum sort 修复后显式开启 `ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR=1`，45 秒超时，完成 142 条 profile path；`total_fork_events=1223`、`max_fork_events=12`；热点为 `pmpCheck=708`、`get_X=284`、`matching_pma_bits_range=231`；无运行时 panic/fallback/SymbolicLength。
  - `/tmp/isla-pmpcheck-profile-vmem-off-20260426-continue`: 显式开启 `ISLA_RISCV_BUILTIN_PMP_CHECK=1`，45 秒超时，完成 18 条 profile path；`total_fork_events=86`、`max_fork_events=6`；PMP 不再是热点。
  - `/tmp/isla-pmpcheck-profile-vmem-off-20260426-continue-120`: 同样开启 `ISLA_RISCV_BUILTIN_PMP_CHECK=1`，120 秒内生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`；完成 76 条 profile path，JSON path 为 `zSTORE` 46 条、`zLOAD` 40 条；`total_fork_events=618`、`max_fork_events=12`；热点为 `matching_pma_bits_range=150`、`get_X=120`、`clint_store=80`、`phys_access_check=76`、`clint_load=65`、`within_mmio_writable=26`、`clint_dispatch=24`、`within_mmio_readable=21`；无运行时 panic/fallback/SymbolicLength。
  - `/tmp/isla-pmpcheck-profile-vmem-off-20260427-postfix`: 修正 fallback/width/read-reg event 后重跑同一 120 秒场景，exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`；完成 76 条 profile path，JSON path 仍为 `zSTORE` 46 条、`zLOAD` 40 条；`total_fork_events=618`、`max_fork_events=12`；热点排序保持 `matching_pma_bits_range=150`、`get_X=120`、`clint_store=80`、`phys_access_check=76`、`clint_load=65`；无运行时 panic/fallback/SymbolicLength。
- worktree 基线：
  - 在 `isla/.worktrees/zstore-pma-mmio` 运行 `cargo check -p isla-lib`：通过；仍有既有 warning。

## 关键发现

- 当前 `rv64d.ir` 中 `zplat_enable_misaligned_access` 固化为 `true`，虽然 `configs/riscv64_difftest.toml` 写了 `plat_enable_misaligned_access = false`。
- 原因是 `rv64d.ir` 由 `sail-riscv` 的 CMake target `generated_isla_rv64d` 生成，生成期使用 `sail-riscv/build/config/rv64d_v256_e64.json`；该 JSON 的 `memory.misaligned.supported` 当前为 `true`。
- `configs/riscv64_difftest.toml` 里的 `plat_enable_misaligned_access = false` 属于 Isla 运行时 `[const_primops]` 配置，只能替换 extern call；当前 IR 里 `zplat_enable_misaligned_access` 是 top-level `let`，不是 extern call，因此运行时 TOML 不能覆盖。
- 这会让 IR 回退路径允许进入 `split_misaligned`，并触发 `vmem_utils.sail:224` 一类动态结果宽度问题。
- 因此 `off` / 单函数关闭 gate 不是“misaligned disabled”语义参考，只能作为路径爆炸和 IR 热点诊断。
- `split_misaligned` guard 只移除了显式 aligned 前提下的动态宽度阻断；VMEM `off` 仍会在 PMA/PMP/translation 相关链路上超时，因此下一轮要重新 profile 剩余热点，而不是继续扩大 `subrange_internal`。
- `split_misaligned` 后的 profile 表明首要剩余热点是 PMP：`pmpAddrMatchType_encdec_backwards`、`pmpRangeMatch`、`pmpCheck` / `pmpMatchAddr`，不是 PTW。
- `pmpRangeMatch` summary 是正结果：完成路径从 split 后 baseline 的 11 条提升到 707 条，单路径最大 fork 从 62 降到 23；但早期证据中存在 enum sort panic，已通过 enum sort 注册修正。
- 小粒度 PMP summary 可以消掉配置位解码、RWX、locked 这类局部实现分支，但仍会把热点集中到 `pmpMatchAddr` / `pmpCheck`。
- 大而全的单函数 `pmpMatchAddr` summary 不能默认开启：早期 75 秒没有完成路径；enum sort 修正后虽可完成 142 条路径并降低 fork 深度，但吞吐仍明显下降。
- `pmpCheck` exact summary 是当前 PMP 配置/循环层的正结果：在不默认关闭 PMP 的前提下，显式 gate 120 秒内跑通当前 VMEM `off` 样例，且 PMP 不再出现在热点列表。
- `ISLA_RISCV_ASSUME_PMP_OFF=1` 仍只是诊断/保底假设，不能替代 PMP exact summary 或默认语义。
- PMP summary 命中时会绕过 `Instr::Call` 后续的函数级 trace/probe/stop/function-assumption 逻辑；PMP helper 本身未见 ISA 状态副作用丢失，但诊断可观察性边界需要记录。
- PMP exact summary 后，完整语义路线的下一层热点已经转到 PMA/MMIO：`matching_pma_bits_range`、`pmaCheck` / `phys_access_check`、CLINT load/store、`within_mmio_readable/writable`。

## 下一步

下一步转向 PMA/MMIO。`range_subset`、`split_misaligned` alignment guard、`pmpRangeMatch`、小粒度 PMP summary 和显式 `pmpCheck` exact summary 可作为当前局部结果保留；`pmpMatchAddr` 单函数 summary 继续保持显式实验 gate、默认关闭。后续优先评估 `pmaCheck` 层 summary，而不是直接返回 `matching_pma_bits_range` 的 `option(PMA_Region)`；随后再看 `within_mmio_readable/writable` 和 CLINT/MMIO。当前不应把 `ISLA_RISCV_VMEM_ASSUME_MISALIGNED_FAULTS=1` 或 `ISLA_RISCV_ASSUME_PMP_OFF=1` 当默认语义，它们只是显式诊断/保守 fault gate。

## 2026-04-27 20 个 subagent PMA/MMIO 结果

本轮按用户要求创建并分配了 20 个 subagent；main agent 只做调度、汇总和交互。所有报告已写入 `agents/zSTORE_path_explosion/subagents/`，汇总见 `agents/zSTORE_path_explosion/subagents/summary.md`。

### 已完成的分析结论

- PMA/MMIO 阶段的第一优先级仍是 `pmaCheck` exact summary。理由是它返回 `option(ExceptionType)`，可以直接压缩 `matching_pma_bits_range`、misaligned fault 和权限判断；不建议优先 summary `matching_pma_bits_range -> option(PMA_Region)`。
- `phys_access_check` summary 应放在 `pmaCheck` 验证之后。它能消掉 PMP/PMA option 合并层，但如果先做，会把 PMP exact formula 与 PMA formula 合成更大的 SMT 表达式，难以归因 solver 成本。
- 当前 PMA region 为 ROM、MMIO PMA、RAM 三项；fixed `width=4` 时 `pmaCheck` 的 region 循环规模很小，理论上比 PMP 16-entry exact summary 更可控。
- `within_mmio_readable/writable` 是可行 predicate summary 候选，但第一版应显式 gate、默认关闭，因为它直接决定 RAM 与 MMIO 分派边界。
- `clint_load` 可做 concrete exact-hit-only 小 summary；symbolic addr/width 首版应回退 IR。
- `clint_store` / `clint_dispatch` 涉及 `mip`、`mtimecmp`、`mtime` 写入和 callback/interrupt side effect，不建议作为下一优先级宽 summary。
- HTIF load/store 当前应延后；HTIF predicate 可在 `htif_tohost_base=None()` 或 concrete `Some(base)` 且保留 wrapping BV 语义时再考虑。
- 当前 `normalize_vmem_output.py` 不足以单独支撑 PMA/MMIO 语义等价结论；后续至少需要增加 `address`、exception 解析、未知字段报告，并补 callback/MMIO/path constraint 的输出来源。

### 原型实现状态

- agent05 在 `isla/.worktrees/zstore-pma-mmio/isla-lib/src/executor.rs` 中加入默认关闭的 `ISLA_RISCV_BUILTIN_PMA_CHECK` 原型。
  - 读取 `zpma_regions`，使用 `range_subset` wrap 语义合成 first-match、misaligned access/alignment fault 和 access permission fault。
  - unsupported 情况回退 IR。
  - 已在 worktree 中运行 `cargo check -p isla-lib`，exit `0`；仍有既有 warning。
  - 尚未跑 on/off 行为对照或 zSTORE/zLOAD profile。
- agent19 在同一 worktree 中加入默认关闭的 `ISLA_RISCV_BUILTIN_WITHIN_MMIO` 最小原型。
  - 当前只支持 `get_config_rvfi=false`、`htif_tohost_base=None()`、concrete width、concrete CLINT base/size 时把 `within_mmio_*` summary 成 `within_clint` predicate。
  - `cargo check -p isla-lib` exit `0`，`diff --check` 通过。
  - 尚未做 wrapper/runtime profile 对照。

### 新验证记录

- agent16 在 `isla/.worktrees/zstore-pma-mmio` 运行 `cargo check -p isla-lib`：exit `0`，`isla-lib` 仍有既有 `65 warnings`，无 Rust error。
- agent16 profile smoke 目录 `/tmp/isla-agent16-current-smoke-20260427-rerun`：
  - 45 秒 timeout，exit `124`。
  - 完成 22 条 `fork_profile`，`total_fork_events=118`，`max_fork_events=8`。
  - 热点为 `get_X=44`、`matching_pma_bits_range=40`、`phys_access_check=22`、`within_mmio_writable/clint_store/clint_dispatch=4`。
  - 未生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`，因此只能作为健康检查和热点趋势证据，不能作为语义回归。
- main agent 在 worktree 中先运行 `cargo build --manifest-path isla/.worktrees/zstore-pma-mmio/Cargo.toml --bin isarch`：exit `0`；仍为既有 warning。
- PMA on/off 验证目录 `/tmp/isla-pma-mmio-20260428-rl4B0N`：
  - `pma-off-short`: `ISLA_RISCV_BUILTIN_PMA_CHECK=0`，45 秒 timeout，exit `124`；完成 24 条 profile，`total_fork_events=136`，`max_fork_events=9`；热点为 `get_X=48`、`matching_pma_bits_range=44`、`phys_access_check=24`。
  - `pma-on-short`: `ISLA_RISCV_BUILTIN_PMA_CHECK=1`，45 秒 timeout，exit `124`；完成 38 条 profile，`total_fork_events=288`，`max_fork_events=11`；`matching_pma_bits_range` 从热点消失，热点转为 `clint_store=80`、`get_X=76`、`phys_access_check=72`、`within_mmio_writable=28`。
  - `pma-off-long`: 180 秒窗口内自然完成，exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`；完成 76 条 profile，`total_fork_events=618`，`max_fork_events=12`；热点为 `matching_pma_bits_range=150`、`get_X=120`、`clint_store=80`、`phys_access_check=76`、`clint_load=65`。
  - `pma-on-long`: 180 秒窗口内自然完成，exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`；完成 68 条 profile，`total_fork_events=539`，`max_fork_events=12`；`matching_pma_bits_range` 不再出现，热点转为 `phys_access_check=130`、`get_X=106`、`clint_store=80`、`clint_load=65`、`within_mmio_*` / `within_clint`。
  - 两个 long case 的 `run.log` 均未检出 panic、`ExecError`、运行时 `SymbolicLength(...)` 或 builtin fallback 文本。
  - normalized JSON 对照尚未通过：`zSTORE` 为 off 46 条、on 38 条，`zLOAD` 为 off 40 条、on 34 条；on 侧出现 `SymCtor(... Access_Fault | Addr_Align ...)`，而 off 侧是已分裂的具体 exception ctor。当前只能说明 PMA summary 有性能趋势，不能声明语义等价验收完成。
  - 现有 `normalize_vmem_output.py` 还不能证明“合并后的符号 constructor + path constraints”等价于 baseline 多条具体路径；后续需要增强 comparator 读取 path constraints，或让 summary 在 final observable 前重新分裂 exception ctor。
- 用户已明确语义等价不能由算法自动判定，只能由 main agent 或 subagent 这类大模型基于证据判断；comparator 只用于暴露 observable 差异和风险信号。
- 已按用户同意的第二条路线修正 `pmaCheck` final observable 形态：
  - `pmaCheck` builtin 现在在 concrete aligned 时直接使用 `misaligned=false`，concrete misaligned 时保留 `misaligned=true`，符号地址且显式 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 时加入 alignment assert 并使用 `misaligned=false`。
  - `option_exception_from_fault_conds` 在 access/alignment 任一 fault 条件为常量 false 时，不再构造二选一的 inner `SymbolicCtor`。
  - RED 证据：旧 `/tmp/isla-pma-mmio-20260428-rl4B0N/pma-on-long` 中 `rv64d_zSTORE.json` 有 8 个 `SymCtor`，`rv64d_zLOAD.json` 有 4 个。
  - 首次只改 `misaligned` 后复跑 `/tmp/isla-pma-mmio-postalign-20260428-yCeQyU/pma-on-long`，`SymCtor` 仍为 8/4，说明根因还包括返回 ctor helper 不折叠常量 false。
  - 最终复跑 `/tmp/isla-pma-mmio-postalign-20260428-yCeQyU/pma-on-long-2`：exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`，`SymCtor` 计数为 0/0；profile 仍为 68 条、`total_fork_events=539`、`max_fork_events=12`，热点保持 `phys_access_check`、`get_X`、`clint_*`、`within_mmio_*`。
  - 新 on 输出与旧 off baseline 的 normalized 对照仍有路径数量和 memory event address sample 差异；该差异不能由 comparator 直接裁决为等价或不等价，下一步应由 main/subagent 结合 PMA 条件、generator 非确定性和输出语义做人工/大模型判断。

### 下一步收敛

1. 由 main agent 或 subagent 对新的 PMA on/off 证据做语义判断：重点看剩余差异是否只是 generator/path sampling 非确定性，还是 `pmaCheck` summary 仍改变了异常或 memory event 语义。
2. 在该判断完成前，不把 `ISLA_RISCV_BUILTIN_PMA_CHECK` 设为默认开启。
3. PMA 验证稳定后，再评估 `phys_access_check` wrapper 或 `within_mmio_*` predicate summary。

## 2026-04-28 主工作区 PMA 合入与验证

- 已把 `ISLA_RISCV_BUILTIN_PMA_CHECK` 从 `isla/.worktrees/zstore-pma-mmio` 原型合入主工作区 `isla/isla-lib/src/executor.rs`，但保持默认关闭。
- 合入时新增 `get_config_print_pma=false` guard：如果当前 IR 不能证明 `zget_config_print_pma` 是 literal false，`pmaCheck` builtin 回退 IR，避免丢失 `print_log` 可观察行为。
- 只合入 `pmaCheck`，没有合入 `within_mmio_*` 原型，也没有改 CLINT/HTIF 行为。
- 新增 `range_subset_exp` wrap-around 单测；`cargo test -p isla-lib range_subset_exp_matches_sail_wraparound_cases` 通过。
- `cargo check -p isla-lib` 通过；`git diff --check` 和 `git -C isla diff --check` 通过。
- 主工作区 profile 目录 `/tmp/isla-pma-main-20260428-131406/pma-on`：
  - exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
  - JSON：`zSTORE=38`、`zLOAD=34`，`SymCtor=0/0`。
  - profile：68 条，`total_fork_events=539`，`max_fork_events=12`。
  - 热点：`phys_access_check=130`、`get_X=106`、`clint_store=80`、`clint_load=65`、`within_mmio_writable=28`、`within_mmio_readable=25`、`within_clint=25`、`clint_dispatch=24`。
  - 运行阶段未检出 `pmaCheck builtin fallback`、runtime panic、`ExecError` 或运行时 `SymbolicLength(...)`。
- 当前判断：PMA summary 可作为显式 gate 保留；默认开启仍需要更多语义证据，因为 off/on path 数不同且 JSON 不携带 path constraints。下一步应优先评估 `phys_access_check` option 合并层和 `within_mmio_readable/writable` predicate，但 `clint_store` 仍不应做宽 summary。

## 2026-04-28 within_mmio predicate 合入与验证

- 已在主工作区加入默认关闭的 `ISLA_RISCV_BUILTIN_WITHIN_MMIO`，只拦截 `within_mmio_readable` / `within_mmio_writable`。
- 首版是 CLINT-only predicate summary：
  - `zget_config_rvfi` 必须可证明为 literal false。
  - 当前 `zhtif_tohost_base` 必须为 `None()`；否则回退 IR。
  - `addr`、CLINT base/size 必须是 <=64-bit bitvector，`width` 必须 concrete positive。
  - 使用 128-bit zero-extend 模拟 Sail 的 unbounded unsigned integer 范围判断，不使用 64-bit wrapping。
  - 不接管 `mmio_read/write`、`clint_load/store`、RAM memory event 或 callback。
- 新增 `unbounded_range_contains_exp_does_not_wrap` 单测，确认 CLINT 范围判断不会在接近 `u64::MAX` 时 wrap。
- 验证：
  - `cargo test -p isla-lib executor::tests` 通过。
  - `cargo check -p isla-lib` 通过。
  - `/tmp/isla-within-mmio-main-20260428-134152/within-on` exit `0`，`zSTORE=38`、`zLOAD=30`，`SymCtor=0/0`，68 条 profile，`total_fork_events=514`，`max_fork_events=11`。
  - 与 PMA-only `/tmp/isla-pma-main-20260428-131406/pma-on` 相比，`within_mmio_*` / `within_clint` 热点消失，`total_fork_events` 从 539 降到 514，`max_fork_events` 从 12 降到 11。
  - normalized 对照仍有 path shape 和 memory event address sample 差异；`zLOAD` path 数从 34 降到 30。当前只能视为显式性能 gate，不能默认开启。
- 下一步候选：
  - `phys_access_check` 薄 wrapper：只复用现有 PMP/PMA summary 并合并 option，硬要求不引入 final `SymCtor`；否则回退。
  - 或继续向 CLINT body 做更小的 concrete exact-hit summary，优先 `clint_load`，暂不做宽 `clint_store`。

## 2026-04-28 phys_access_check 薄 wrapper 合入与验证

- 已在主工作区加入默认关闭的 `ISLA_RISCV_BUILTIN_PHYS_ACCESS_CHECK`，只拦截 `phys_access_check`。
- 实现边界：
  - 要求 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 与 `ISLA_RISCV_BUILTIN_PMA_CHECK=1` 同时开启，否则回退 IR。
  - 不复制 PMP/PMA 公式；内部复用 `pmp_check_builtin` 和 `pma_check_builtin`，再合并 Sail 的四象限 option 语义。
  - 新增 `alignment_or_access_fault_priority_name` / `highest_priority_alignment_or_access_fault_name`，按 Sail `highestPriorityAlignmentOrAccessFault` 的 `>` 规则：access fault priority 1，alignment fault priority 0，平级取右侧。
  - review 后曾判断 unsupported 边界会整体回退 IR；Phase 5 审计修正该判断：如果一个子 summary 已完整命中并提交 `ReadReg`，wrapper 后续回退 IR 时没有 event 回滚。
  - `pmaCheck` / `pmpCheck` 直接调用时的 fallback 边界较干净：内部先读取寄存器值但不记事件，完整命中后再补 `ReadReg`；`pmaCheck` 的 alignment assert 也延迟到完整命中后再加入。但这不等于 wrapper 回退干净。
- 验证：
  - RED：`cargo test -p isla-lib phys_access_priority_prefers_access_and_right_tie` 先因缺少 priority helper 失败。
  - GREEN：同一单测通过。
  - `cargo test -p isla-lib executor::tests` 通过；当前 6 个 executor 单测覆盖 `range_subset`、CLINT unbounded range、phys access priority、CLINT exact-hit 表、子 summary miss 回退、symbolic exception 回退。
  - `cargo check -p isla-lib` 通过；仍有既有 `65 warnings`。
  - profile 目录 `/tmp/isla-phys-main-20260428-continue/phys-on`：exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`；`zSTORE=32`、`zLOAD=27`，`SymCtor=0/0`。
  - profile：59 条，`total_fork_events=425`，`max_fork_events=10`。与 within-on 的 68 条、`total_fork_events=514`、`max_fork_events=11` 相比，`phys_access_check` 从热点消失。
  - 新热点为 `get_X=91`、`clint_store=80`、`clint_load=65`、`checked_mem_write=58`、`checked_mem_read=51`、`clint_dispatch=24`。
  - 运行阶段未检出 `phys_access_check builtin fallback`、`pmaCheck builtin fallback`、`within_mmio builtin fallback`、runtime panic、`ExecError` 或运行时 `SymbolicLength(...)`；日志中相关文本只出现在编译 warning 源码引用。
  - 与 within-on 的 normalized 对照仍有 path shape 和 memory event address sample 差异；该 gate 仍不能默认开启。
- 下一步候选：
  - 优先 `clint_load` concrete exact-hit summary。
  - `clint_store` / `clint_dispatch` 涉及 register write、callback 和 interrupt pending，暂不做宽 summary。
  - `checked_mem_read/write` 太靠近 RAM/MMIO 分派和 memory event 边界，暂不直接接管。

## 2026-04-28 clint_load concrete exact-hit 结果

- 已在主工作区加入默认关闭的 `ISLA_RISCV_BUILTIN_CLINT_LOAD`，只拦截 `clint_load`。
- 首版支持范围：
  - `zget_config_print_clint` 必须可证明为 literal false，否则回退 IR。
  - `paddr` 与 `zplat_clint_base` 必须是 concrete bitvector，`width` 必须 concrete。
  - 只处理 Sail 中 exact hit 的成功分支：MSIP `0x0000` width 4/8、MTIMECMP `0x4000` width 4/8、MTIMECMP_HI `0x4004` width 4、MTIME `0xbff8` width 4/8、MTIME_HI `0xbffc` width 4。
  - 命中后只读取实际需要的一个寄存器：`zmip`、`zmtimecmp` 或 `zmtime`，并通过 `read_register_cloned` 补 `ReadReg` event。
  - symbolic address、symbolic width、unmapped concrete offset 首版均回退 IR，不构造条件化寄存器读取。
- 验证：
  - RED：`cargo test -p isla-lib clint_load_exact_hit_table_matches_sail_branches` 先因缺少 `clint_load_exact_hit` / `ClintLoadHit` 失败。
  - GREEN：同一单测通过。
  - `cargo test -p isla-lib executor::tests` 通过；当前 6 个 executor 单测覆盖 `range_subset`、CLINT unbounded range、phys access priority、CLINT exact-hit 表、子 summary miss 回退、symbolic exception 回退。
  - `cargo check -p isla-lib` 通过；仍有既有 `65 warnings`。
  - profile 目录 `/tmp/isla-clint-load-main-20260428-continue/clint-load-on`：exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`；`zSTORE=32`、`zLOAD=27`，`SymCtor=0/0`。
  - profile 与 phys-on 完全一致：59 条、`total_fork_events=425`、`max_fork_events=10`，热点仍为 `get_X=91`、`clint_store=80`、`clint_load=65`、`checked_mem_write=58`、`checked_mem_read=51`。
  - 日志只有 1 次 `clint_load builtin fallback: symbolic paddr`；没有 runtime panic、`ExecError` 或运行时 `SymbolicLength(...)`。
- 结论：
  - concrete exact-hit 版本语义边界清楚，可以作为显式 gate 保留。
  - 它没有解决当前 `clint_load=65` 热点，因为当前 workload 进入 `clint_load` 时地址仍是 symbolic。
  - 若继续处理 `clint_load`，需要先设计条件化 `ReadReg` / symbolic CLINT load summary；否则无条件读取 `zmip` / `zmtimecmp` / `zmtime` 会改变 trace event。

## 2026-04-28 CLINT-off 显式平台假设

注意：本小节记录的是 Phase 5 审计前的旧实现和旧 profile，已被后文“Phase 5 blocker 修复与 smoke 矩阵”替代。

- 用户明确要求当前不继续考虑 CLINT body summary，可以在 Isla 侧尝试关闭 CLINT，但不要动 `sail-riscv` 或从 `sail-riscv` 到 IR 的编译流程。
- 已在主工作区加入 `ISLA_RISCV_ASSUME_CLINT_OFF=1`：
  - `within_clint(addr,width)` 直接返回 `false`。
  - `within_mmio_readable/writable` 在 `zget_config_rvfi=false` 且 `zhtif_tohost_base=None()` 时直接返回 `false`，避免已有 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` 绕过 `within_clint` 继续计算 CLINT predicate。
  - 如果 HTIF 不是 concrete `None()`，`within_mmio_*` 仍回退 IR，不能把 HTIF 也静默关闭。
- 语义边界：
  - 这不是默认平台等价优化，而是“当前符号执行平台没有 CLINT 设备”的显式假设。
  - Phase 5 审计修正：当前实现不能保证 CLINT 地址范围不会落入普通 RAM。`within_mmio_* == false` 后，`checked_mem_read/write` 会走 `read_ram/write_ram`，不是 `mmio_read/write` access fault。
  - 不执行 `clint_load/store`、`clint_dispatch`、CLINT register read/write 或 callback/interrupt side effect。
- TDD/回归：
  - RED：`cargo test -p isla-lib clint_off_predicates_return_false_only_when_safe` 先因缺少 helper 失败。
  - GREEN：同一单测通过。
  - `cargo test -p isla-lib executor::tests` 通过；当前 7 个 executor 单测覆盖 CLINT-off predicate、range_subset、CLINT unbounded range、phys access priority、CLINT exact-hit 表、子 summary miss 回退、symbolic exception 回退。
  - `cargo check -p isla-lib` 通过；仍有既有 warning。
- profile 目录 `/tmp/isla-clint-off-main-20260428-BtFXWr/clint-off`：
  - 开启 PMP/PMA/within/phys 显式 gates，关闭 `ISLA_RISCV_BUILTIN_CLINT_LOAD`，开启 `ISLA_RISCV_ASSUME_CLINT_OFF=1`。
  - 180 秒窗口内自然完成，exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
  - JSON：`zSTORE=6`、`zLOAD=6`、`SymCtor=0/0`。
  - profile：12 条，`total_fork_events=35`，`max_fork_events=4`。
  - 热点：`get_X=18`、`checked_mem_read=5`、`checked_mem_write=4`、`extend_value=4`、`set_X=4`。
  - `clint_load`、`clint_store`、`clint_dispatch`、`within_clint` 和 `within_mmio_*` 不再出现在运行期热点里。
  - 运行期未检出 runtime panic、`ExecError`、运行时 `SymbolicLength(...)`、builtin fallback 或 CLINT 热点文本；相关源码名只在编译 warning 中出现。
- 当前判断：
  - 该 gate 对当前 zSTORE/zLOAD path explosion 收益最大，但只能作为显式平台假设。
  - 不能把它默认开启，也不能用它证明真实 CLINT 设备路径等价。
  - 后续若需要覆盖真实 CLINT 语义，需要重新设计条件化 register event / callback 保真的 CLINT load/store summary；当前路线先不做。

## 2026-04-28 CLINT-off 后剩余热点收敛

- 本轮继续分析了 CLINT-off 后的剩余热点：`get_X`、`set_X`、`checked_mem_read/write`、`extend_value`。
- `get_X` / `set_X`：
  - Sail 源码在 `__isla_vector_gpr=true` 时仍有 x0 特判。`get_X(0)` 返回 zero register，`set_X(0)` 无效果，非零寄存器才读写 vector GPR。
  - `rv64d.ir` 中对应 `r == 0` 的 branch；Isla vector register primitive 已把符号 index 编成 SMT ITE，不会出现 32-way executor fork。
  - 因此剩余 fork 是 x0 ISA 语义，不是实现方式路径爆炸。由于 x0 分支还影响 register event shape，当前不建议默认 summary。
- `checked_mem_read/write`：
  - 剩余 fork 是 `phys_access_check` 的 `Some(exception)` / `None()` option 分派。
  - 这是异常返回与后续 RAM/MMIO memory event 的真实语义边界。当前没有 guarded memory event，不能安全合并成单个返回值。
  - 只做 concrete `Some`/`None` fast path 对当前符号地址 workload 收益很低，暂不作为下一优先级。
- `extend_value`：
  - fork 来自 `is_unsigned`，实际是在同一次 `zLOAD` profile 中同时覆盖 signed/unsigned load 变体。
  - 不建议为当前目标写 `extend_value` ITE summary；更合适的是用测试输入固定 load kind，分别跑 `lw` / `lwu`。
- 固定 load kind 实验：
  - 目录：`/tmp/isla-clint-off-load-kind-20260428-w1xJlg`。
  - `ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED=0` 与 `=1` 两个 case 均 exit `0`，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
  - 两个 case 均为 10 条 profile、`total_fork_events=25`、`max_fork_events=3`；`zSTORE=6`、`zLOAD=4`、`SymCtor=0/0`。
  - `extend_value` 从热点中消失，运行期未检出 runtime panic、`ExecError`、运行时 `SymbolicLength(...)`、builtin fallback 或 CLINT 热点。
- 当前结论：
  - 路径爆炸已经基本压到可控范围；CLINT-off 后剩余 fork 不再适合继续用宽 summary 压缩。
  - 下一步应转为语义验证与配置收敛：逐个确认 PMP/PMA/within/phys/CLINT-off gates 的前提、event 边界、exception 边界和 fail-closed 行为。
  - 除非新 profile 再显示超时或 `max_fork_events` 明显反弹，否则不继续优先优化 `get_X`、`set_X`、`checked_mem_*` 或 `extend_value`。

## 2026-04-28 Phase 5 subagent gate 审计

注意：本小节记录审计发现的问题和当时的修复顺序；两个 blocker 已在下一小节修复并完成 smoke。

- 已按 Phase 5 拆分并行只读审计，汇总写入 [subagents/phase5-gate-audit-summary.md](subagents/phase5-gate-audit-summary.md#L1)。
- 结论不是“可以直接验收”，而是发现两个需要先处理的 blocker：
  - `phys_access_check` wrapper fallback 不干净：PMP/PMA 子 summary 完整命中后会提交 `ReadReg` event；如果 wrapper 后续回退 IR，这些 event 不会回滚。另有 symbolic option presence 下重新构造 `Val::SymbolicCtor` 的 final observable 风险。
  - `ISLA_RISCV_ASSUME_CLINT_OFF=1` 当前会把 `within_mmio_*` 变成 false；Sail `checked_mem_read/write` 随后会走 `read_ram/write_ram`，所以不能声称 CLINT 地址不会变 RAM 或会经 `mmio_read/write` 返回 access fault。
- 其余结论：
  - `pmaCheck` exact summary 在声明边界内基本保持 Sail 语义，但仍默认关闭。
  - `within_mmio_*` 对 HTIF `Some(base)` 是回退，不会静默关闭 HTIF。
  - `clint_load` concrete exact-hit summary 可保留为显式 fast path，但当前 workload 没收益。
  - 剩余热点不建议继续优化。
- 当时的下一步是先修两个 blocker 再跑 smoke；该工作已在下一小节完成。

## 2026-04-28 Phase 5 blocker 修复与 smoke 矩阵

- 已修 `phys_access_check` wrapper 的副作用回退问题：
  - 新增 compute-only 路线：`pmp_check_compute` / `pma_check_compute` 只计算 option/fault 公式和 pending effects。
  - `ReadReg` event 与 alignment assert 只有在 wrapper 最终确认 summary 完整命中后才统一提交。
  - 若 PMP/PMA summary 未同时开启、任一子 summary miss，或 symbolic option presence 下不同 fault 会产生 inner `SymbolicCtor`，wrapper 整体回退 IR。
  - 新增/保留单测覆盖 symbolic fault choice fallback：`symbolic_phys_access_fault_choice_requests_fallback`。
- 已修 `ISLA_RISCV_ASSUME_CLINT_OFF=1` 的地址分派语义：
  - `within_clint` 仍返回 false。
  - `within_mmio_readable/writable` 在 HTIF 为 concrete `None()` 时返回 CLINT range predicate，而不是 false。
  - 因此 CLINT 地址仍走 `mmio_read/write`，再因无 CLINT/HTIF 命中返回 access fault，不会落入 RAM。
  - `clint_off_predicates_return_false_only_when_safe` 已更新为覆盖该语义。
- 验证：
  - `cargo test -p isla-lib clint_off_predicates_return_false_only_when_safe` 通过。
  - `cargo test -p isla-lib symbolic_phys_access_fault_choice_requests_fallback` 通过。
  - `cargo test -p isla-lib executor::tests` 通过 7 个 executor 单测。
  - `cargo check -p isla-lib` 通过；仍有仓库既有 warning。
- 并行 smoke 矩阵已完成，汇总见 [subagents/phase5-smoke-matrix-20260428.md](subagents/phase5-smoke-matrix-20260428.md#L1)。
  - P0 CLINT-on baseline：`zSTORE=32`、`zLOAD=27`、`SymCtor=0/0`、59 profiles、`total_fork_events=425`、`max_fork_events=10`。
  - P1 CLINT-on + `clint_load`：同 P0，只有 1 次 runtime `clint_load builtin fallback: symbolic paddr`。
  - P2 CLINT-off full gates：`zSTORE=8`、`zLOAD=7`、`SymCtor=0/0`、15 profiles、`total_fork_events=52`、`max_fork_events=5`。
  - P3/P4 fixed signed/unsigned load kind：均为 `zSTORE=8`、`zLOAD=5`、`SymCtor=0/0`、13 profiles、`total_fork_events=40`、`max_fork_events=4`。
  - P5 negative fallback：`PMA_CHECK=0` 时 exit `0`，`zSTORE=22`、`zLOAD=20`、32 profiles、`total_fork_events=157`、`max_fork_events=7`，6 次预期 `phys_access_check builtin fallback: PMP/PMA summaries are not both enabled`，无 runtime panic/`SymbolicLength`。
- 旧 CLINT-off 数字 `zSTORE=6` / `zLOAD=6`、fixed kind `zLOAD=4` 已被本轮替代。上涨原因是语义修正后 CLINT range 不再被错误归为 non-MMIO/RAM，而是保留 MMIO fault 分派。
- 当前下一步：进入语义验证与配置收敛，重点比较 CLINT-off on/off 的 fault/memory event observable，以及为 `phys_access_check` wrapper 的 fail-closed 行为补 targeted 单测；不优先继续压缩 `get_X`、`checked_mem_*`、`extend_value` 小 fork。

## 2026-04-28 Phase 5 语义验证与配置收敛

- 已完成 Phase 5 smoke 后的并行语义验证，汇总见 [subagents/phase5-semantic-validation-20260428.md](subagents/phase5-semantic-validation-20260428.md#L1)。
- `clint_load` concrete exact-hit gate 与 CLINT-on baseline 在当前 workload 下 `zSTORE=32` / `zLOAD=27` 一致，ret/memory-event 计数一致；差异只剩 path shape、字段顺序/`Sym` 噪声和 address sample。该 gate 可保留为显式 fast path，但对当前 symbolic paddr 热点没有收益。
- CLINT-off full-gates 的 observable 边界已复核：
  - `zSTORE=8`：6 条 `Memory_Exception`、2 条 `Retire_Success`。
  - `zLOAD=7`：3 条 `Memory_Exception`、4 条 `Retire_Success`。
  - 所有 exception path 的 memory event 数为 0，所有 success path 的 memory event 数为 1。
  - CLINT effective address sample 均返回 access fault 且 memory event 数为 0，未观察到 CLINT range 静默走 RAM。
- `phys_access_check` negative case 已复核：`PMA_CHECK=0` 时有 6 次预期 wrapper fallback，异常输出未观察到 memory event 泄漏；这支持 compute/commit 两段式修复。
- 根据 gate/default 审计，补了一个配置级 fail-closed 保护：`ISLA_RISCV_ASSUME_CLINT_OFF=1` 必须配合 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` 使用；否则 `within_clint` 直接返回 `ExecError`，避免旧 IR `within_mmio_*` 把 CLINT range 误分派到 RAM。
- 保护后重跑 full-gates P2：`/tmp/isla-phase5-validation-p2-rerun-20260428`，exit `0`，`zSTORE=8`、`zLOAD=7`、15 条 profile，memory event 分布保持 `{0:6,1:2}` / `{0:3,1:4}`，未观察到 runtime fallback 或配置错误。
- 保护后重跑 fixed load-kind：
  - signed `lw`：`/tmp/isla-phase5-validation-p3-final-20260428`，`zSTORE=8`、`zLOAD=5`、`SymCtor=0/0`、13 条 profile、`total_fork_events=40`、`max_fork_events=4`，无 runtime fallback/timeout/`ExecError`/`SymbolicLength`。
  - unsigned `lwu`：`/tmp/isla-phase5-validation-p4-final-20260428`，`zSTORE=8`、`zLOAD=5`、`SymCtor=0/0`、13 条 profile、`total_fork_events=40`、`max_fork_events=4`，无 runtime fallback/timeout/`ExecError`/`SymbolicLength`。
- 负向配置验证：`ISLA_RISCV_ASSUME_CLINT_OFF=1` 且 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=0` 时，相关 path 报 `Type error: ISLA_RISCV_ASSUME_CLINT_OFF=1 requires ISLA_RISCV_BUILTIN_WITHIN_MMIO=1 to avoid treating CLINT range as RAM`。测试 harness 进程可能仍 exit `0`，但 path 已 fail closed，不会静默继续。
- 当前 Phase 5 结论：两个 blocker 已修，smoke 矩阵无超时，语义验证未发现新的 blocker；剩余限制是 JSON 不带完整 path constraints，因此还不能声称默认等价或全输入形式化证明。

## 2026-04-28 review 修复：CLINT-off within_mmio miss 必须 fail closed

- review 指出一个剩余风险：即使 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` 已开启，`within_mmio_*` summary 仍可能因 HTIF 不是 concrete `None()`、symbolic width、unsupported address、缺 CLINT base/size 等条件 `Ok(None)` 回退 IR。CLINT-off 下回退 IR 会调用 `within_clint=false`，从而重新引入 CLINT range 落入 RAM 的风险。
- 已修正为：`ISLA_RISCV_ASSUME_CLINT_OFF=1` 时，`within_mmio` summary 任何 miss 都返回 `ExecError`，不能回退 IR。
- HTIF 不是 concrete `None()` 时也 fail closed；只有 `rvfi=false`、HTIF concrete `None()`、width/address/CLINT base/size 都可处理时，才返回 CLINT range predicate。
- 单测 `cargo test -p isla-lib clint_off_predicates_return_false_only_when_safe` 已按 TDD 先失败后通过。
- 收紧后重跑 CLINT-off full-gates smoke：`/tmp/isla-review-fix-p2-smoke-20260428`，`zSTORE=8`、`zLOAD=7`、`SymCtor=0/0`、15 条 profile、`total_fork_events=52`、`max_fork_events=5`；运行期未观察到 fallback、timeout、`ExecError` 或 `SymbolicLength`。
- P3 文档项按当前选择新增 [../overview.md](../overview.md)，补齐根 `AGENTS.md` 引用。

## 2026-04-28 `make run` 运行配置收敛

- 用户用 `timeout 100 make run` 复现大量运行期错误。复查后确认根因不是新的 CLINT-off fail-closed 逻辑，而是 `isla/Makefile::run` 仍按旧配置运行：未设置 Phase 5 gates、未固定 `zSTORE` / `zLOAD` width，也未固定 `cur_privilege`。
- 原始 target 会在 `zSTORE` 上触发 `base_insts.sail:322` 动态 `subrange_internal`，在 `zLOAD` 上触发 `prelude.sail:93` 动态 `zeros`；只加 env 但不加 `-I cur_privilege=Machine` 时又会因 `pmpCheck builtin fallback: symbolic privilege` 在 100 秒内超时。
- 已修改 [../../isla/Makefile](../../isla/Makefile#L3)：
  - `RUN_BASE_ENV`、`RUN_PROFILE_ENV`、`RUN_VMEM_ENV`、`RUN_ACCESS_ENV`、`RUN_MMIO_ENV`、`RUN_TEST_ENV` 按用途拆分通用项、profile、VMEM/alignment、PMP/PMA/phys、MMIO/CLINT 和测试输入固定。
  - 默认 `RUN_RISCV_ENV` 聚合当前 Phase 5 smoke 所需的 PMP/PMA/within/phys gates、CLINT-off、aligned 前提、`zSTORE` / `zLOAD` width=4。
  - `RUN_ISARCH_ARGS` 固定 `-I cur_privilege=Machine`；`RUSTFLAGS=-Awarnings` 仅用于 `run` target，减少既有 Rust warning 噪声。
- 最终验证：`timeout 100 make run` exit `0`；`rg "执行错误|SymbolicLength|builtin fallback|panicked at|ExecError|requires ISLA_RISCV|Terminated|Poison" isla/log` 无匹配；JSON 为 `zSTORE=8`、`zLOAD=7`、`SymCtor=0/0`，memory event 分布 `{0:6,1:2}` / `{0:3,1:4}`。
- 剩余终端输出中的 `Warning: Could not find register __isla_always_aligned` 和 `No primop ...` 是既有 init/config 警告；本轮未改这些警告。
