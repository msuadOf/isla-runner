# zSTORE / zLOAD 路径爆炸后续计划

本计划面向当前议题：对 `sail-riscv` 建模的 RISC-V ISA 做符号执行，尽量遍历 ISA 规定的真实语义分支，同时避免 Sail/Rust 实现方式额外引入的路径爆炸。

旧的长篇执行记录已归档到 `deprecated/`。当前目录下的文档以能指导下一步工作为准：

- `principles.md`：后续优化必须遵守的语义和取舍原则。
- `review.md`：对旧文档是否还能指导工作的审核结论。
- `suggest.md`：当前候选热点函数的优先级。
- `deprecated/`：历史计划、review 和建议的原始副本，暂不删除。

## 当前上下文

- `isla/` 当前分支为 `fix-memory-sym-pathboomb-semantics`。
- `isla/` 当前 HEAD 是 `9bb7395fe2efce124117a548d8f8892643eaaf97`，该提交引入了把一批 IR 函数塞到 Isla/Rust 侧的粗粒度实现。
- 用户已经把后续若干次语义修正改动放入暂存区；这些改动还不能默认视为已接受方案，下一步应先审核 staged diff，再决定保留、重写或丢弃。
- staged diff 当前集中在 `Makefile`、`isla-lib/src/executor.rs`、`isla-lib/src/isarch_exec.rs`、`isla-lib/src/primop.rs`、`isla-lib/src/smt.rs`。

## 总目标

在 `zSTORE` / `zLOAD` 以及后续更多 RISC-V 指令上：

1. 保留 ISA 规范要求的语义分支，例如异常、权限、翻译、PMP/PMA/MMIO、misaligned split、LR/SC 等。
2. 消除由实现写法造成的分支，例如纯布尔/区间计算被编译成多层短路 `jump` 后导致 executor fork。
3. 优先把可等价表达的复杂度下沉为 SMT AST 关系，让 Z3 承担组合条件，而不是让 executor 枚举路径。
4. 如果无法等价覆盖，按 fail-closed 处理：返回原语义允许的 `Err(...)`，或回退 IR，或显式 panic/internal error；不能静默返回近似成功结果。

## Phase 0：文档收敛

状态：已完成当前轮整理。

- 归档旧文档原文到 `deprecated/`。
- 提炼通用原则到 `principles.md`。
- 将可执行计划收敛到本文件。
- 将旧内容可用性审核写入 `review.md`。
- 将候选函数优先级收敛到 `suggest.md`。

后续如果继续发现代码逻辑，应按仓库规则同步更新 `agents/findings.md`。

## Phase 1：审核 staged 语义修正

目标：不要在不满意的 staged 改动上继续堆新逻辑；先判断哪些改动是可保留框架，哪些是语义近似或历史包袱。

审核对象：

- `executor.rs`
  - `call_isla_implemented_function(...)` 或同类拦截入口是否仍然过粗。
  - `vmem_read_addr` / `vmem_write_addr` 的 gate 是否逐函数、逐模式可控。
  - 对齐、translation、PMP/PMA/MMIO、plain RAM 假设是否显式检查或显式要求外部前提。
  - 普通 store 是否避免暴露原 Sail 不会观察到的 unconstrained `Ok(false)`。
- `isarch_exec.rs`
  - 测试入口、固定 instruction 字段、输出路径是否只是测试辅助。
  - 是否混入影响正式执行语义的改动。
- `primop.rs` / `smt.rs`
  - 动态 bitvector 操作的 SMT 化是否是通用能力，还是只服务某个不完整近似。
  - 是否符合已有 primop 的错误处理风格。
- `Makefile`
  - 是否只是本地测试便利；若会覆盖日志或产物，需要避免把它当推荐测试入口。

审核输出格式：

```text
- file/function:
  keep | rewrite | drop | undecided:
  reason:
  semantic risk:
  path-explosion evidence:
  next action:
```

## Phase 2：建立可重复的对照基线

目标：所有优化都必须能回答两个问题：是否真的减少路径爆炸；是否仍与同一外部配置下的 IR/Sail 语义等价。

需要保留的对照模式：

- builtin off：全部走 IR，用于语义参考和路径爆炸确认。
- legacy/fast baseline：仅作为“可压路径”的性能参考，不能作为等价目标。
- semantic mode：只在显式前提满足时接管，其他情况 fail closed 或回退 IR。

测试要求：

- 在 `/tmp` 独立目录运行，避免覆盖 `isla/log`、`output/`、`solver.dump`。
- 使用固定 `zSTORE` / `zLOAD` instruction 字段，减少 generator 非确定性。
- 用 `normalize_vmem_output.py` 或等价工具比较 `ret_val`、memory event kind/address/bytes/data、success constraint。
- 每次记录 fork 数、耗时、热点函数、是否超时、输出文件位置。

## Phase 3：逐函数确认爆炸来源

原则：不因为某函数在 VMEM 链路上就内置化；只对有证据导致路径爆炸、且可以等价表达的函数投入 builtin/primop。

确认协议：

- 给每个候选函数独立 gate。
- 一次只改变一个 gate，其余保持当前性能基线。
- 回 IR 后如果 fork 数、耗时、solver 调用没有明显劣化，优先保持 IR。
- 回 IR 后如果稳定超时或热点落在该函数内部，才进入等价 builtin 设计。
- 如果函数会爆但等价 builtin 暂时做不完整，不能返回近似 `Ok(...)`；应回退、返回合法 `Err(...)`，或 panic/internal error。

记录格式：

```text
- function:
  instruction:
  gate state:
  result: explodes | no-obvious-explosion | unsupported
  fork count:
  elapsed:
  hot source/IR:
  decision: keep IR | restore builtin | add SMT summary | add precise Err | panic until implemented
  notes:
```

## Phase 4：实现取舍规则

优先顺序：

1. Isla/Rust 侧做等价 SMT summary 或 primop，把实现分支变成 AST 关系。
2. 如果 Isla 侧等价表达代价过高，且分支明显来自 `sail-riscv` 的实现写法而不是 ISA 语义，再考虑修改 `sail-riscv` 建模方式。
3. 如果两边都可行，优先改 Isla，尽量不动 `sail-riscv`。
4. 如果 SMT 没有合适表达，先评估是否能用更小的等价摘要、惰性约束、或回退 IR 解决。
5. 全局假设只能作为保底，例如 PMP 数量强制为 0、PTW one-shot/identity translation；这些必须显式来自 init/config/test 前提，并在文档中标明语义边界。

禁止事项：

- 不允许 builtin 隐式把虚拟地址当物理地址。
- 不允许隐式关闭 PMP/PMA/MMIO。
- 不允许把 misaligned split 近似成单次整宽访问。
- 不允许把 page fault/access fault 静默改成成功 memory event。
- 不允许用“当前样例没观察到”替代语义证明。

## Phase 5：zSTORE / zLOAD 近期路线

推荐顺序：

1. 审核并收紧当前 staged VMEM builtin，决定哪些 gate 和测试辅助可保留。
2. 固定普通 aligned `Load(Data)` / `Store(Data)` 的 plain-RAM 快速路径：
   - `aq=false`
   - `rl=false`
   - `res=false`
   - concrete width
   - data width 匹配
   - alignment 被证明或被显式 SMT 约束
   - identity translation、PMP permits、plain RAM、non-MMIO 都是显式外部前提
3. concrete misaligned 默认应回退 IR；只有当本次 plain-RAM 场景显式声明“不支持 misaligned split”时，才能返回原语义允许的 alignment exception；在允许 split 的配置下必须实现 split 或回退，不能成功整宽写入/读取。
4. `range_subset` 这类纯公式函数先做独立 gate 和局部验证；完成后不要继续在同一层堆子公式，应转向更高收益的调用层。
5. `split_misaligned` 当前只做 alignment guard：
   - 已对齐或显式 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 时返回 `(1,width)`，解除 VMEM `off` 链路的动态结果宽度阻断。
   - concrete misaligned、symbolic width、零 width 仍回退 IR。
   - 它不是完整 misaligned split summary，不能作为允许 misaligned 访问时的最终语义方案。
6. split guard 后的 VMEM `off` profile 已确认剩余首要热点是 PMP，而不是 PTW：
   - `pmpRangeMatch` 已完成等价 SMT summary，`ISLA_RISCV_BUILTIN_PMP_RANGE_MATCH` 默认开启，可设为 `0` 回退 IR；75 秒 profile 中完成路径从 11 条提升到 707 条，单路径最大 fork 从 62 降到 23。
   - 小粒度 PMP summary 已覆盖 `pmpAddrMatchType_encdec_backwards`、`pmpCheckRWX`、`pmpLocked`，用于把配置位解码和权限位判断下沉到 SMT。
   - 大而全的单函数 `pmpMatchAddr` summary 不能默认启用：早期显式开启后 75 秒没有完成 path；enum sort 修复后可完成 142 条 path 并降低单路径 fork，但吞吐仍明显下降。`ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR` 必须保持默认关闭，只能作为实验 gate 或 `pmpCheck` 内部子表达式。
   - 完整语义 `pmpCheck` exact summary 已作为显式 gate 加入：`ISLA_RISCV_BUILTIN_PMP_CHECK=1` 时按 PMP entry 优先级合成 partial match、RWX、locked、Machine privilege 和 no-match 规则；120 秒 profile 已生成 `zSTORE` / `zLOAD` JSON，PMP 不再是热点。
   - `ISLA_RISCV_ASSUME_PMP_OFF=1` 只能作为诊断/保底假设；它能让 VMEM `off` 完成并暴露 `matching_pma_bits_range`、CLINT/MMIO 等下一层热点，但不能替代 PMP 语义。
   - `pmpCheck` exact summary 目前仍是显式 gate，不是默认开启；边界包括 `sys_pmp_count <= 64`、`sys_pmp_grain = 0`、可读 `pmpcfg_n` / `pmpaddr_n` vector、支持的 access ctor、可构造 width bitvector。unsupported 情况回退 IR。
   - builtin 命中会绕过函数级 trace/probe/stop/function-assumption 逻辑；这不改变 PMP helper 的 ISA 状态语义，但不是 trace 等价。
   - 完整语义路线的下一步应转向 PMA/MMIO：优先评估 `pmaCheck` 层 summary，而不是直接 summary `matching_pma_bits_range` 的 `option(PMA_Region)` 返回；随后再看 `within_mmio_readable/writable` 和 CLINT read/write。
7. `pmaCheck` exact summary 已合入主工作区，但必须保持显式 gate、默认关闭：
   - gate：`ISLA_RISCV_BUILTIN_PMA_CHECK=1`。
   - 语义内容：读取 `zpma_regions`，按 PMA list head-first first-match 和 `range_subset` wrap 语义合成 no-match access fault、misaligned access/alignment fault、权限检查和 `option(ExceptionType)`。
   - 可观察边界：只有能证明 `zget_config_print_pma` 是 literal `false` 时接管，否则回退 IR，避免吞掉 PMA failure 的 `print_log`。
   - alignment 前提：符号地址且显式 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 时加入 alignment assert 并把 `misaligned=false`，避免最终 JSON 中出现 access/alignment 二选一 `SymCtor`。
   - unsupported access、非 concrete PMA list、unsupported width/region shape 均回退 IR。
   - 主工作区 profile `/tmp/isla-pma-main-20260428-131406/pma-on`：`zSTORE=38`、`zLOAD=34`、`SymCtor=0/0`，68 条 profile，`total_fork_events=539`，`max_fork_events=12`，`matching_pma_bits_range` 已从热点消失。
   - 当前仍不能默认开启：off/on path 数不同，现有 JSON 不带 path constraints，不能自动证明合并路径等价于 IR 分裂路径。
8. `within_mmio_readable/writable` predicate summary 已合入主工作区，但必须保持显式 gate、默认关闭：
   - gate：`ISLA_RISCV_BUILTIN_WITHIN_MMIO=1`。
   - 首版只支持 `get_config_rvfi=false` 且当前 `htif_tohost_base=None()` 的 CLINT-only exact predicate。
   - `within_clint` 用 128-bit zero-extend 表达 Sail 的 unbounded unsigned integer 范围判断，不使用 64-bit wrapping。
   - 不接管 `mmio_read/write`、`clint_load/store`、RAM event 或 callback。
   - 主工作区 profile `/tmp/isla-within-mmio-main-20260428-134152/within-on`：`zSTORE=38`、`zLOAD=30`、`SymCtor=0/0`，68 条 profile，`total_fork_events=514`，`max_fork_events=11`；`within_mmio_*` / `within_clint` 已从热点消失。
   - 当前仍不能默认开启：与 PMA-only 对照存在 path shape 和 memory event address sample 差异，且 `zLOAD` path 数从 34 降到 30；现有 JSON 不带 path constraints，不能自动证明等价。
9. `phys_access_check` 薄 wrapper 已合入主工作区，但必须保持显式 gate、默认关闭：
   - gate：`ISLA_RISCV_BUILTIN_PHYS_ACCESS_CHECK=1`，并要求 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 与 `ISLA_RISCV_BUILTIN_PMA_CHECK=1` 同时开启。
   - 实现边界：不复制 PMP/PMA 大公式，而是使用 compute-only 的 `pmp_check_compute` / `pma_check_compute`，再合并 Sail 的四象限 option 语义和 `highestPriorityAlignmentOrAccessFault` priority。
   - Phase 5 审计发现的 fallback side-effect 风险已修：子 summary 先只返回 pending `ReadReg` / alignment assert；wrapper 只有在最终合并成功时才统一提交。
   - 若 PMP/PMA summary 未同时开启、任一子 summary miss，或 symbolic option presence 下不同 fault 会产生 inner `SymbolicCtor`，wrapper 整体回退 IR。
   - 主工作区 profile `/tmp/isla-phys-main-20260428-continue/phys-on`：`zSTORE=32`、`zLOAD=27`、`SymCtor=0/0`，59 条 profile，`total_fork_events=425`，`max_fork_events=10`；`phys_access_check` 已从热点消失。
   - Phase 5 negative smoke `/tmp/isla-phase5-smoke-20260428-154603-p5-phys-fallback`：`PMA_CHECK=0` 时 exit `0`，有 6 次预期 wrapper fallback，无 runtime panic/`SymbolicLength`，异常输出没有 memory event。
   - 当前仍不能默认开启：相对 within-on 的 path 数继续下降，normalized 对照仍有 path shape 和 memory event address sample 差异，现有 JSON 缺 path constraints，不能自动证明等价。
10. `clint_load` concrete exact-hit 小 summary 已合入主工作区，但对当前 path explosion 没有实际收益：
   - 必须显式 gate、默认关闭。
   - `get_config_print_clint()` 必须可证明 literal false，否则回退 IR。
   - 首版只处理 concrete `paddr` / `width` 精确命中 MSIP、MTIMECMP、MTIME 的 load 分支；symbolic address 先回退 IR。
   - 每次只读取实际命中的设备寄存器并补对应 `ReadReg` event，不为了构造 ITE 无条件读取所有 CLINT register。
   - 主工作区 profile `/tmp/isla-clint-load-main-20260428-continue/clint-load-on` 与 phys-on 完全一致：`zSTORE=32`、`zLOAD=27`、`SymCtor=0/0`，59 条 profile，`total_fork_events=425`，`max_fork_events=10`；日志只有 1 次 `clint_load builtin fallback: symbolic paddr`。
   - 结论：当前 `clint_load=65` 热点来自 symbolic paddr 下的分支链，concrete exact-hit 只能作为低风险 fast path 保留，不能解决当前爆炸。
   - 用户已明确当前不继续处理 CLINT body summary；如果未来需要真实 CLINT 设备语义，再设计条件化 `ReadReg` / `WriteReg` / callback 保真的 symbolic CLINT load/store。
   - `clint_store` / `clint_dispatch` 涉及寄存器写、callback 和 interrupt pending，当前不做宽 summary；宽 `checked_mem_*` 也暂不接管。
11. `ISLA_RISCV_ASSUME_CLINT_OFF=1` 已作为显式平台假设合入主工作区：
   - 不改 `sail-riscv`，不改 IR，不改 IR 生成流程。
   - `within_clint` 直接返回 `false`。
   - `within_mmio_readable/writable` 在 `zget_config_rvfi=false` 且 `zhtif_tohost_base=None()` 时仍返回 CLINT range predicate；若 HTIF 不为 concrete `None()`，返回 `ExecError`，不能回退 IR。
   - 该假设必须配合 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` 使用；否则旧 IR `within_mmio_*` 可能通过 `within_clint=false` 把 CLINT range 判为 non-MMIO 并落入 RAM。当前实现已 fail closed：`ISLA_RISCV_ASSUME_CLINT_OFF=1` 且 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=0` 时返回 `ExecError`。
   - 即使 `ISLA_RISCV_BUILTIN_WITHIN_MMIO=1` 已开启，CLINT-off 下 `within_mmio` summary 也不能普通回退 IR；HTIF 不是 concrete `None()`、symbolic width、unsupported address、缺 CLINT base/size 等 miss 都返回 `ExecError`，避免 fallback IR 再次经过 `within_clint=false` 后走 RAM。
   - 语义目标已修正为 unmapped MMIO fault：CLINT 地址仍被判定为 MMIO，然后在 `mmio_read/write` 中因为 `within_clint=false` 且 HTIF 为 `None()` 返回 access fault，避免落入 `read_ram/write_ram`。
   - Phase 5 smoke `/tmp/isla-phase5-smoke-20260428-154629-p2-clint-off`：`zSTORE=8`、`zLOAD=7`、`SymCtor=0/0`，15 条 profile，`total_fork_events=52`，`max_fork_events=5`。
   - guard 后重跑 `/tmp/isla-phase5-validation-p2-rerun-20260428`：`zSTORE=8`、`zLOAD=7`、15 条 profile，memory event 分布保持 `{0:6,1:2}` / `{0:3,1:4}`。
   - fixed signed/unsigned load kind smoke 均为 `zSTORE=8`、`zLOAD=5`、`SymCtor=0/0`，13 条 profile，`total_fork_events=40`，`max_fork_events=4`。
   - guard 后 fixed load-kind 重跑目录为 `/tmp/isla-phase5-validation-p3-final-20260428` 与 `/tmp/isla-phase5-validation-p4-final-20260428`，结果仍为 `8/5`、13 条 profile、`max_fork_events=4`，无 runtime fallback/timeout/`ExecError`/`SymbolicLength`。
   - 旧 profile `/tmp/isla-clint-off-main-20260428-BtFXWr/clint-off` 的 `6/6` 路径数已过期；上涨来自修正 CLINT range 分派语义，而不是新的路径爆炸。
   - 该 gate 收益很大，但必须保持默认关闭，只能由测试/init 明确开启。
12. CLINT-off 后剩余热点当前不再作为性能优化优先级：
   - `get_X` / `set_X` 的 fork 是 x0 ISA 语义，且影响 register event shape；不要默认用纯 ITE summary 接管。
   - `checked_mem_read/write` 的 fork 是 fault 路径和 memory event 路径的真实分界；没有 guarded memory event 前不要宽 summary。
   - `extend_value` 的 fork 来自 `lw` / `lwu` 变体；需要区分时用 `ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED=0/1` 分开 profile。
   - 语义修正后的固定 load kind profile 为 13 条、`total_fork_events=40`、`max_fork_events=4`，说明当前路线仍应转向语义验证。
13. Phase 5 显式 gate 的语义验证矩阵已完成初轮，汇总见 `subagents/phase5-semantic-validation-20260428.md`：
   - PMP/PMA/within/phys/CLINT-off 每个 gate 的外部前提。
   - unsupported 时是回退 IR、`ExecError`、还是显式 access fault。
   - 是否可能改变 `ReadReg` / `WriteReg` / RAM memory event / MMIO callback / exception ctor observable。
   - 哪些 gate 是等价 summary，哪些只是显式平台假设或诊断假设。
   - Phase 5 初审指出的两个 blocker 已修，smoke 矩阵已完成且无超时；语义验证未发现新的 blocker。
   - 当前剩余限制是 JSON 不带完整 path constraints，因此不能把这些显式 gate 升为默认开启，也不能声称全输入形式化等价。
   - 下一步若继续推进，应补 targeted function tests / path-constraint 证据，或扩大到更多 ISA 指令 smoke，而不是继续压缩 `get_X`、`checked_mem_*`、`extend_value` 小 fork。
14. 对 `translateAddr` / `pt_walk`、PMP、PMA/MMIO 建立单独测试，不要混入普通 aligned 快速路径。
15. 若需要把 misaligned-disabled 作为 IR 语义参考，必须在 `sail-riscv` 的 JSON 生成配置中设置 `memory.misaligned.supported=false` 并重新生成 `rv64d.ir`；`isla/configs/*.toml` 中的 `const_primops` 不能覆盖当前 IR 的 top-level `let`。
16. 每完成一个函数或显式平台假设，补 profile 记录和语义边界记录。
17. 当前 `isla/Makefile::run` 已作为本议题的 Phase 5 smoke 入口：默认带显式 gates、CLINT-off 平台假设、固定 `zSTORE` / `zLOAD` width=4 和 `-I cur_privilege=Machine`。后续若需要对照无假设 baseline，应另建独立 target，不要直接复用 `run` 的结果来声称默认语义等价。

## 验收标准

任一优化合入前至少满足：

- `cargo check -p isla-lib` 通过。
- 对应 fixed `zSTORE` / `zLOAD` 样例能比较 `ret_val` 和 memory events。
- builtin on/off 的差异有解释：路径数减少来自实现分支下沉到 SMT，而不是语义被删掉。
- 对不支持语义有明确 fail-closed 行为。
- 文档记录了外部前提、不可覆盖场景和下一步。
