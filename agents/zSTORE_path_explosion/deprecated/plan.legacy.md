# RISC-V VMEM Builtin 修正计划

目标：在保留降低 `zSTORE` / `zLOAD` 路径爆炸收益的前提下，逐步恢复 `vmem_read_addr` / `vmem_write_addr` 与 `sail-riscv` 原始语义的重要等价性。计划按风险和收益分阶段推进。

## 当前判断

`isla/` 原始性能基线来自 `fix-memory-sym-pathboomb-unreviewed` 上的最新改动；当前语义修正工作分支是 `fix-memory-sym-pathboomb-semantics`。这些改动已经证明一件事：把部分 VMEM/MEM 热路径改到 Isla/Rust 侧实现，确实可以消除当前 `zSTORE` 的路径爆炸。因此后续不应该简单回到“全部走 IR”的方向，而应该把当前新增函数当作性能基线和实现载体，在其上逐步补齐语义等价。

从提交记录看，当前可复用的关键改动是：

- `dd64248 unrewview: 支持了内存符号化和多线程的尽可能的占用`
  - 引入显式 symbolic memory region、`execute_ir_function_with_checkpoint_and_memory*`、多线程执行路径和 memory-events 收集。
  - 这部分主要是执行环境和产物收集能力，是后续对照测试的基础。
- `9bb7395 unreview: codex一通改，把一堆ir的函数塞进了isla，但是行为简化了`
  - 引入 `isla-lib/src/executor.rs::call_isla_implemented_function(...)`，在普通函数调用前拦截 `vmem_read_addr` / `vmem_write_addr`。
  - 引入 `isla-lib/src/primop.rs` 中对动态 `subrange_internal(...)` 的 SMT 化支持，以及 `isla-lib/src/smt.rs::simplify_exp_to_u64(...)`。
  - 这部分是“无路径爆炸”的直接来源，但当前语义过于简化，需要保留框架、修正语义。

我的建议是：

- 不把 `9bb7395` 整体回退。
- 以 `call_isla_implemented_function(...)` 为统一入口，给每个候选函数加独立 gate。
- 对已经证明能消除路径爆炸的 builtin，先保留，再按 fail-closed 规则补异常、翻译、misaligned、PMP/PMA 等语义。
- 对不确定是否需要 builtin 的函数，临时关 gate 回到 IR 跑一次，只作为诊断对照；如果不爆，就保持 IR；如果爆，就恢复 builtin 并记录证据。
- 后续可以直接在当前分支上新建小提交；为了减少误改当前未 review commit 的风险，也可以新建安全分支，例如 `fix-memory-sym-pathboomb-semantics`，完成后再 merge 回当前分支。

## 外部配置与语义边界

可以通过外部配置收窄系统环境来降低路径爆炸，但这必须是显式配置导致的语义收窄，不能由 builtin 隐式偷换语义。

允许的方向包括：

- PTW / address translation：
  - 可以通过外部配置或测试环境把地址翻译约束成 one-shot 的一对一映射。
  - 在这种配置下，builtin 可以依赖“虚拟地址等于物理地址”这个前提。
  - 但 builtin 必须显式检查或显式依赖该配置；不能在 VM/translation 仍可能非 identity 时默认把 `vaddr` 当 `paddr`。
- PMP：
  - 虽然 IR 生成时默认可能包含 16 个 PMP entry 的逻辑，但可以通过 config TOML 覆写 PMP 个数，把 PMP 关闭，例如将 PMP count 配成 0。
  - 在 PMP 关闭的配置下，builtin 可以不展开 `pmpCheck`，因为原 IR 在同一配置下也应表现为无 PMP 限制。
  - 但如果配置中 PMP 是开启的，builtin 必须和 IR 的 PMP 检查等价；做不到就不能假设通过。
- PMA / MMIO：
  - 可以通过外部配置让目标地址范围只落在普通 RAM、全权限 PMA、非 MMIO 区域。
  - 在这种配置下，builtin 可以走普通 memory event 快速路径。
  - 但如果配置允许 MMIO 或复杂 PMA，builtin 必须等价处理，或返回 `Err(...)` / 回退 IR / panic。

关键原则：

- 内置函数的语义必须和“同一外部配置下的 IR 语义”等价。
- 如果等价依赖 PTW identity、PMP disabled、普通 RAM region 等前提，这些前提必须来自外部配置或调用前约束，并在 gate 中检查。
- 如果当前 builtin 做不到覆盖某类配置，不要在 builtin 内部放松语义；应当要求外部配置放松条件，或者按 fail-closed 规则处理。
- 外部配置可以减少 IR 原本要考虑的状态空间；builtin 只能利用这些已经存在的配置事实，不能制造新的事实。

## 总体原则

- 语义等价是最高优先级，高于路径数、性能、结果数量和 builtin 覆盖范围。
- 对任何没有完整考虑、无法证明等价、或当前实现暂不支持的情况，必须 fail closed：
  - 首选返回与原语义兼容的 `Err(...)`
  - 如果无法构造正确 `Err(...)`，再回退到原 IR 函数体继续执行
  - 如果既无法构造正确 `Err(...)`，也无法安全回退，允许直接 panic / internal error，不能静默产生近似的 `Ok(...)`
- 不把 `vmem_*_addr` 做成无条件 `Ok(...)` 的粗粒度跳过。
- 能以 SMT 公式表达的分支条件，优先留给 solver，而不是在 executor 中枚举路径。
- 对无法安全内置的语义，保守回退到原 IR 函数体。
- 先覆盖普通 `Load(Data)` / `Store(Data)`，再扩展 LR/SC、AMO、MMIO 和虚拟内存。
- 每个阶段都需要有对照测试：原 IR 执行结果、builtin 执行结果、trace memory events、异常返回。

## Phase 0：建立语义开关和基线测试

### 任务

- 为 `vmem_read_addr` / `vmem_write_addr` builtin 增加明确开关，例如：
  - 完全关闭 builtin
  - 仅普通 aligned bare-memory 模式
  - 完整检查模式
- 加入 debug trace，记录 builtin 为什么接管或为什么回退原 IR。
- 建立最小对照样例：
  - aligned `lb/lh/lw/ld`
  - aligned `sb/sh/sw/sd`
  - misaligned store
  - misaligned load
  - 地址越界或不在 symbolic memory region

### 验收

- 可以一键比较 builtin on/off 的结果。
- 普通 aligned load/store 的 `memory-events` 地址、宽度、数据与原路径一致。
- misaligned case 在当前阶段允许先回退原 IR，不允许错误地产生成功 `Ok(...)`。

## Phase 0.5：逐函数确认路径爆炸来源

### 目标

不要一次性把整条 VMEM/MEM 链路都内置化。当前 `isla/` 新增函数已经构成“无路径爆炸”的基线；接下来要以这个基线为起点，逐个确认哪些函数必须保留 builtin，哪些函数可以回到 IR。只有有证据会造成路径爆炸的函数，才值得继续投入等价 builtin。

### 确认协议

- 给每个候选 builtin 单独加 gate，支持按函数独立启用/禁用。
- 一次只改变一个函数的 gate，其他函数保持当前“无路径爆炸”基线状态。
- 对不确定是否造成路径爆炸的函数，不是直接删除当前新增函数，而是临时禁用该函数 gate，让它回到原 IR 路径跑一遍。
- 如果回到 IR 后没有明显 fork 增长、超时或热点转移，则该函数标记为“不确认会爆炸”，优先保持 IR，不继续做 builtin。
- 如果回到 IR 后出现明显路径爆炸，则恢复该函数 builtin，并把函数名、触发指令、fork 数、耗时、热点 IR/source 位置记录到本计划或同目录 review 记录中。
- 如果某函数虽然会爆炸，但等价 builtin 暂时做不完整，也不能返回近似 `Ok(...)`；按 fail-closed 规则处理。
- `9bb7395` 中新增的 `call_isla_implemented_function(...)` 和动态 `subrange_internal(...)` SMT 化支持，是可修改和扩展的实现基础；后续不要绕开它们重新做一套分散的拦截逻辑。

### 判定标准

一个函数可标记为“会路径爆炸”，需要至少满足一项：

- 禁用该函数 builtin 后，`zSTORE` / `zLOAD` 的 fork 数显著增加。
- 禁用该函数 builtin 后，执行超时或 solver 调用数量显著增加。
- profile 中热点稳定落在该函数对应 source line 或 IR PC。
- trace 显示大量 fork 发生在该函数内部，而不是其调用者或被调用者。

一个函数可标记为“不会明显路径爆炸”，需要满足：

- 禁用该函数 builtin 后，`ret_val` / `memory-events` 可正常产出。
- fork 数和耗时没有显著劣化。
- profile 热点没有稳定落在该函数内部。

### 需要测试的函数

| 函数 | 位置 | 初始判断 | 测试动作 |
| --- | --- | --- | --- |
| `vmem_write_addr` | `sail-riscv/model/sys/vmem_utils.sail` | 已知是大聚合热点，但内部包含多类语义 | 必测；先拆成子函数确认，不应长期只做粗粒度整体 builtin |
| `vmem_read_addr` | `sail-riscv/model/sys/vmem_utils.sail` | 已知是大聚合热点，但内部包含多类语义 | 必测；与 `vmem_write_addr` 分开确认 |
| `check_misaligned` | `sail-riscv/model/sys/vmem_utils.sail` | 不确定，函数本身较小 | 先回 IR 跑；若不爆，不做 builtin |
| `split_misaligned` | `sail-riscv/model/sys/vmem_utils.sail` | 高风险，历史 profile 指向其短路条件 | 必测；禁用 builtin 后若 fork 激增，记录为爆炸来源 |
| `misaligned_order` | `sail-riscv/model/sys/vmem_utils.sail` | 当前判断不值得，配置分支通常已固化 | 仍需一次确认；若不爆，明确记录“不做 builtin” |
| `translateAddr` | `sail-riscv/model/sys/vmem.sail` | 高风险，可能引入 page walk 和权限分支 | 必测；VM 关闭和 VM 开启分别测试 |
| `translate` / `pt_walk` | `sail-riscv/model/sys/vmem.sail` | 高风险，仅在 VM 开启时相关 | VM 开启场景必测；VM 关闭时应确认不会进入 |
| `check_PTE_permission` | `sail-riscv/model/sys/vmem_pte.sail` | 高风险，页权限分支多 | VM 开启场景必测 |
| `update_PTE_Bits` | `sail-riscv/model/sys/vmem_pte.sail` | 高风险，可能带来 page table write side effect | VM 开启场景必测 |
| `mem_read` | `sail-riscv/model/sys/mem.sail` | wrapper，可能爆在 callee | 必测；若热点在 callee，不给 wrapper 做 builtin |
| `mem_write_ea` | `sail-riscv/model/sys/mem.sail` | 函数较小，但含对齐和 write kind | 必测；确认是否需要单独 builtin |
| `mem_write_value` | `sail-riscv/model/sys/mem.sail` | wrapper，可能爆在 callee | 必测；若热点在 callee，不给 wrapper 做 builtin |
| `mem_read_priv_meta` | `sail-riscv/model/sys/mem.sail` | 中风险，含 aligned、aq/rl、checked read | 必测 |
| `mem_write_value_priv_meta` | `sail-riscv/model/sys/mem.sail` | 中风险，含 aligned、checked write、callback | 必测 |
| `checked_mem_read` | `sail-riscv/model/sys/mem.sail` | 高风险，含 PMP/PMA/MMIO 分支 | 必测 |
| `checked_mem_write` | `sail-riscv/model/sys/mem.sail` | 高风险，含 PMP/PMA/MMIO 分支 | 必测 |
| `phys_access_check` | `sail-riscv/model/sys/mem.sail` | 高风险，合并 PMP/PMA | 必测 |
| `pmpCheck` | `sail-riscv/model/pmp/pmp_control.sail` | 高风险，遍历 PMP entries | 必测；PMP disabled/enabled 分别测 |
| `pmpCheckRWX` | `sail-riscv/model/pmp/pmp_control.sail` | 对当前 `Store(Data)` 收益可能有限 | 先回 IR 跑；若不爆，不做 builtin |
| `pmpMatchAddr` | `sail-riscv/model/pmp/pmp_control.sail` | 中高风险，地址匹配分支多 | PMP enabled 场景必测 |
| `range_subset` | `sail-riscv/model/core/range_util.sail` | 已有证据适合 SMT 化 | 必测；确认禁用后是否稳定导致 fork 增长 |
| `pmaCheck` | `sail-riscv/model/sys/mem.sail` | 中高风险，PMA 属性分支多 | 必测；PMA 简单/复杂配置分别测 |
| `within_mmio_readable` | `sail-riscv/model/sys/platform.sail` | 不确定 | 先回 IR 跑；若不爆，不做 builtin |
| `within_mmio_writable` | `sail-riscv/model/sys/platform.sail` | 不确定 | 先回 IR 跑；若不爆，不做 builtin |
| `mmio_read` | `sail-riscv/model/sys/platform.sail` | 只在 MMIO 地址相关 | MMIO 场景测试；普通 RAM 场景不应进入 |
| `mmio_write` | `sail-riscv/model/sys/platform.sail` | 只在 MMIO 地址相关 | MMIO 场景测试；普通 RAM 场景不应进入 |
| `ext_data_get_addr` | `sail-riscv` extension hooks | `vmem_read/write` 到 `vmem_*_addr` 前的地址计算 | 必测；确认 zSTORE 的地址计算阶段是否有 fork |

### 记录格式

每确认一个函数，在本节下方追加记录：

```text
- function:
  instruction:
  gate state:
  result: explodes | no-obvious-explosion | unsupported
  fork count:
  elapsed:
  hot source/IR:
  decision: keep IR | restore builtin | add precise Err | panic until implemented
  notes:
```

## Phase 1：修正普通 aligned `Load(Data)` / `Store(Data)`

### 任务

- 在 builtin 接管前检查参数形态：
  - `access == Load(Data)` 或 `Store(Data)`
  - `aq == false`
  - `rl == false`
  - `res == false`
  - `width` 是 concrete memory width
- 对 `vaddr % width == 0` 添加 SMT 约束或在不能证明时回退。
- 对普通 store 的 `Ok(bool)` payload 做收紧：
  - 如果目标语义是普通 RAM 成功写入，返回 concrete `true`
  - 如果保留 Isla memory model 的 symbolic write success，则必须同步加入上层不会观察 false 的约束，或者只在上层忽略 payload 的场景启用

### 验收

- 普通 aligned `zSTORE` 不再出现原模型没有的 `Ok(false)` 分支。
- 普通 aligned `zLOAD` / `zSTORE` 与原 Sail 在数据宽度和 event 生成上匹配。
- 非普通访问类型全部回退原 IR。

## Phase 2：恢复 misaligned fault 与 split 语义

### 任务

- 内置 `check_misaligned(vaddr, width)` 的结果：
  - 当配置禁止 misaligned access 时，生成 `Err(Memory_Exception(vaddr, E_Load_Addr_Align/E_SAMO_Addr_Align))`
  - 当配置允许 misaligned access 时，进入 split 处理
- 实现或复用 `split_misaligned(vaddr, width)` 的等价逻辑。
- 对允许的 misaligned 访问：
  - load：生成多个子 `ReadMem`，再用 concat/extract 拼回原宽度结果
  - store：把 `data` 按子访问切片，生成多个子 `WriteMem`
  - 顺序遵循 `misaligned_order(n)`
- 对跨 region、跨 page、跨权限边界的 case，在未实现检查前回退原 IR。

### 验收

- 禁止 misaligned 时，builtin 返回与 Sail 相同的 exception 构造子。
- 允许 misaligned 时，event 数量和每个 event 的地址、宽度、数据切片与 Sail 一致。
- 跨边界 case 不被错误简化成单次整宽访问。

## Phase 3：处理地址翻译策略

### 任务

选择一种策略并实现：

1. Bare-only 策略
   - 仅在能证明 VM 关闭或 `translateAddr` 恒等时启用 builtin
   - 否则回退原 IR

2. 内置 translation summary 策略
   - 把 `translateAddr` 的关键结果建成 SMT 约束
   - 输出物理地址 `paddr`
   - 保留必要的 translation/page-table events

建议先做 Bare-only 策略，因为实现范围小、风险低，能先保证 `zSTORE` 普通生成路径正确。

### 验收

- builtin 产生的 `ReadMem` / `WriteMem` 地址必须明确是物理地址，或文档和字段名明确标识为 virtual-only approximation。
- 当 VM 打开且无法证明 identity translation 时，不能直接使用 `vaddr` 作为物理访存地址。
- page fault 场景不会被错误退休成功。

## Phase 4：恢复 PMP / PMA / MMIO 检查

### 任务

- 对普通 `Load(Data)` / `Store(Data)` 实现 `phys_access_check` 的等价 SMT 版本，或在配置复杂时回退原 IR。
- 最小优先级：
  - PMP disabled / PMA 全可访问时允许快速路径
  - 其他情况回退
- 后续扩展：
  - `pmpCheck`
  - `pmaCheck`
  - `within_mmio_readable`
  - `within_mmio_writable`
  - MMIO read/write custom region

### 验收

- PMP/PMA 拒绝访问时返回对应 access fault，而不是生成成功 memory event。
- 普通 RAM 与 MMIO 的 event 或 callback 行为可区分。
- 不支持的 PMA/MMIO 配置不会误走快速路径。

## Phase 5：支持 LR/SC、AMO、aq/rl

### 任务

- 对 `LoadReserved`：
  - 保留 aligned fault 行为
  - 生成 exclusive read event
  - 建模 `load_reservation`
- 对 `StoreConditional`：
  - 建模 `match_reservation`
  - reservation 失败时先执行 PMP/PMA 检查，再返回 `Ok(false)`
  - reservation 成功时执行 exclusive write event
- 对 `aq` / `rl`：
  - 正确映射 read/write kind
  - 对原 Sail 中 not implemented 或 internal error 的组合保持一致
- AMO 可单独作为后续阶段，不要混入普通 store 快速路径。

### 验收

- LR/SC 的 `Ok(false)` 只来自 reservation 语义，而不是普通 write 的 unconstrained symbolic bool。
- exclusive event 标记与原 Sail concurrency interface 的 access kind 对齐。
- aq/rl 组合不会静默降级成普通访存。

## Phase 6：测试矩阵和回归

### 必测场景

- RV64:
  - `lb/lh/lw/ld`
  - `sb/sh/sw/sd`
  - aligned symbolic address
  - misaligned concrete address
  - symbolic address with stride constraint
- RV32:
  - `lb/lh/lw`
  - `sb/sh/sw`
  - width 等于 xlen 和小于 xlen 的 case
- 异常：
  - load address align
  - store/AMO address align
  - load access fault
  - store/AMO access fault
  - page fault，如果 builtin 开始覆盖 translation
- 事件：
  - read/write event 数量
  - event address
  - event bytes
  - write data slice
  - read returned data concat
  - exclusive flag

### 对照方式

- 对同一条指令分别运行：
  - builtin disabled
  - builtin enabled
- 比较：
  - `ret_val`
  - `isa_state`
  - `memory-events`
  - solver sat/unsat
  - fork 数和执行时间

## 推荐实施顺序

1. 以 `isla/` 当前 HEAD 作为“无路径爆炸”性能基线，不整体回退 `9bb7395`。
2. 在 `call_isla_implemented_function(...)` 周围加开关、gate 和 fail-closed 机制。
3. 逐函数临时回 IR 做对照，确认路径爆炸来源，并记录会爆炸和不会明显爆炸的函数。
4. 限定 builtin 只处理已经确认需要 builtin、且可以等价覆盖的普通 aligned `Load(Data)` / `Store(Data)`。
5. 修正普通 store 的 `Ok(bool)` payload。
6. 加 misaligned fault；允许的 misaligned split 暂时可返回 `Err(...)`、回退 IR 或 panic，不能近似成单次整宽 event。
7. 做 bare-only translation guard。
8. 再逐步加入 split、PMP/PMA、LR/SC。

## 执行记录

### 2026-04-25：Phase 0 / Phase 1 起步

代码位置：`isla/isla-lib/src/executor.rs`

已完成：

- 从 `fix-memory-sym-pathboomb-unreviewed` 新建工作分支 `fix-memory-sym-pathboomb-semantics`，用于语义修正。
- 给 `vmem_write_addr` / `vmem_read_addr` 加了逐函数 gate：
  - `ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=0|false|off`：只关闭 `vmem_write_addr` builtin，回退原 IR。
  - `ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=0|false|off`：只关闭 `vmem_read_addr` builtin，回退原 IR。
- 新增全局模式 `ISLA_RISCV_VMEM_BUILTIN_MODE`：
  - `legacy`：保持当前 `9bb7395` 的粗粒度快速路径，作为“无路径爆炸”基线；当前已改成必须显式 opt-in。
  - `off`：两个 VMEM builtin 都不接管，完全回退 IR。
  - `plain-ram` / `plain_ram`：只允许普通 RAM 快速路径；不满足条件时回退 IR。当前默认是这个模式。
- `plain-ram` 模式当前只接管：
  - `Load(Data)` / `Store(Data)`
  - `aq == false`
  - `rl == false`
  - `res == false`
  - 显式设置 `ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1`
  - 显式设置 `ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1`
  - 显式设置 `ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1`
  - concrete width
  - concrete aligned address，或显式设置 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`
  - `Store(Data)` 的 data bit length 必须等于 `width * 8`
- `plain-ram` 下普通 store 不再把 symbolic write success 直接作为 `Ok(bool)` payload 返回：
  - 生成 `WriteMem` event 后，对 event success symbol 添加 `assert(success)`。
  - 返回 `Ok(true)`，避免普通 store 出现原 Sail 没有的 `Ok(false)` 可行路径。
- 不满足 `plain-ram` gate 的情况当前按处理顺序第 2 项回退原 IR；还没有手写构造 `Err(Memory_Exception(...))`。

当前有意保留的限制：

- 默认模式已经从 `legacy` 改为 `plain-ram`。`legacy` 仅作为显式 opt-in 的路径爆炸诊断基线，不再作为语义等价默认值。
- `plain-ram` 仍依赖外部环境保证 identity translation、PMP disabled 或等价全允许、PMA 普通 RAM、非 MMIO。当前代码还不能从 TOML/config 中证明这些条件，所以必须在测试记录中把这些配置前提写清楚。
- symbolic address 的 alignment 当前不自动分叉；设置 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 时，executor 会添加低位为 0 的 SMT 约束后再放行。

验证：

- 已运行 `cargo fmt`。
- 已运行 `cargo check -p isla-lib`，结果通过；输出只有仓库既有 warning。

下一步需要测试：

- `vmem_write_addr`：
  - `legacy` 基线：确认仍保持无路径爆炸。
  - `plain-ram + ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`：在外部 plain RAM / identity / PMP disabled 配置下，对比 `zSTORE` 的 `ret_val` 和 `memory-events`。
  - `ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=0`：单独回退写路径 IR，记录是否路径爆炸。
- `vmem_read_addr`：
  - 同样做 `legacy`、`plain-ram`、单独关闭 gate 三组测试。
- misaligned concrete address：
  - `plain-ram` 目前应回退 IR；后续要改为优先构造原语义允许的 alignment `Err(...)`。
- symbolic address without aligned external constraint：
  - `plain-ram` 目前应回退 IR；如果这导致路径爆炸，需要记录，并决定是加强外部 aligned 约束，还是做 SMT alignment summary。

### 2026-04-25：concrete misaligned 的优先 `Err(...)`

代码位置：`isla/isla-lib/src/executor.rs`

已完成：

- 在 `plain-ram` 模式下，concrete misaligned 不再回退 IR，而是优先构造原语义允许的 alignment exception：
  - `vmem_read_addr` 返回 `Err(Memory_Exception(vaddr, E_Load_Addr_Align()))`
  - `vmem_write_addr` 返回 `Err(Memory_Exception(vaddr, E_SAMO_Addr_Align()))`
- `Err` 构造器使用当前 IR 中的实际名字：
  - read: `zErrzIbzCUExecutionResultzK`
  - write: `zErrzIozCUExecutionResultzK`
  - memory exception: `zMemory_Exception`
  - exception type: `zE_Load_Addr_Align` / `zE_SAMO_Addr_Align`
- exception tuple 字段名按地址位宽选择：
  - RV32: `ztuplez3z5bv32_z5unionz0zzExceptionType0/1`
  - RV64: `ztuplez3z5bv64_z5unionz0zzExceptionType0/1`
  - 这样避免只支持 `rv64d.ir` 而在 `rv32d.ir` 下找不到字段。

验证：

- 已运行 `cargo fmt`。
- 已运行 `cargo check -p isla-lib`，结果通过；输出只有仓库既有 warning。

后续仍需处理：

- symbolic misaligned / alignment unknown 当前仍按处理顺序第 2 项回退原 IR，不能直接返回 alignment fault，因为原语义可能同时包含 aligned 和 misaligned 路径。
- 允许 misaligned split 的配置还没有实现；不能把它近似成单次整宽 memory event。

### 2026-04-25：安全测试入口与配置事实调查

只读调查结论：

- 不建议用 `make run` 做 gate 对照测试：
  - `make run` 会硬编码覆盖 `isla/log`，并先复制 `log -> log.1`。
  - `make run` 会先运行 `cargo fmt`，不适合当纯测试命令。
  - `run_symbolic_execute` 当前硬编码写 `output/rv64d_zSTORE.json`、`output/rv64d_zLOAD.json` 和 `solver.dump`。
  - 当前没有 `--output-dir` / `--log-file` / `--solver-dump` 参数。
- 安全测试方案：
  - 在 `/tmp` 下为每个 case 建独立 cwd。
  - 用 `cargo run --manifest-path "$SRC/Cargo.toml"` 从原源码构建运行。
  - 进入每个 case 的 cwd 后再运行，这样硬编码的 `output/`、`solver.dump`、`run.log` 都落在 `/tmp` case 目录，不覆盖用户已有产物。
  - 设置 `CARGO_TARGET_DIR` 到 `/tmp` 下，避免污染当前工作区 target。

推荐命令骨架：

```bash
SRC=/home/baiyifan/workplace-local/isla-runner/isla
RUN=/tmp/isla-vmem-gate-$(date +%Y%m%d-%H%M%S)
mkdir -p "$RUN"/{legacy,off,write-off,read-off,plain-ram}

cd "$RUN/legacy"
env RUST_BACKTRACE=1 \
  CARGO_TARGET_DIR="$RUN/target" \
  ISLA_RISCV_VMEM_BUILTIN_MODE=legacy \
  ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1 \
  ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1 \
  timeout 30m cargo run --locked --manifest-path "$SRC/Cargo.toml" --bin isarch --release -- \
    -A "$SRC/rv64d.ir" -C "$SRC/configs/riscv64_difftest.toml" \
    --verbose --probe-all --trace-all \
    -I cur_privilege=Machine \
    list-instructions >run.log 2>&1
```

gate 对照矩阵：

```bash
# legacy：当前无路径爆炸基线
ISLA_RISCV_VMEM_BUILTIN_MODE=legacy
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1

# off：全部回退 IR
ISLA_RISCV_VMEM_BUILTIN_MODE=off

# write-off：只关 vmem_write_addr
ISLA_RISCV_VMEM_BUILTIN_MODE=legacy
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=0
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1

# read-off：只关 vmem_read_addr
ISLA_RISCV_VMEM_BUILTIN_MODE=legacy
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=0

# plain-ram：普通 RAM 语义 gate
ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1
ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1
ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1
ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
```

配置事实：

- `configs/riscv64_difftest.toml` 中 `satp=0`、`mstatus=0`，有利于 identity / bare translation 对照。
- `symbolic_addrs` 当前范围 `0x80310000..0x80410000`、stride `0x10`，对当前对齐测试有利，且应落在普通 RAM 区间。
- `configs/riscv64_difftest.toml` 有 `sys_pmp_count = "0 : %i64"` 和 `plat_enable_pmp = false`，但当前 `rv64d.ir` 中 `zsys_pmp_count` 仍可见为编译期 `16`。因此在证明 TOML 覆写确实生效前，不能把 PMP disabled 当作已经由 IR 等价保证的事实。
- 对这组测试建议显式加 `-I cur_privilege=Machine`，使原 IR 在 PMP 未命中时按 Machine 模式允许访问，更接近 plain-RAM 对照前提。不要写成 `zMachine`；命令行初始化会再做 z-encoding，`zMachine` 会被解析成不存在的 `zzzMachine`。
- 结论：`plain-ram` 的外部边界目前应写成“Machine + bare/identity + 普通 RAM symbolic range + 非 aq/rl/res + aligned + 非 MMIO”，PMP disabled 需要单独验证，不应默认由 builtin 偷换。

### 2026-04-25：gate 对照测试结果

测试目录：`/tmp/isla-vmem-gate-ZdANPQ`

公共命令前提：

- 从每个 case 的 `/tmp` 子目录运行，避免覆盖 `isla/log`、`isla/output/`、`isla/solver.dump`。
- `CARGO_TARGET_DIR=/tmp/isla-vmem-gate-ZdANPQ/target`
- `cargo run --locked --manifest-path /home/baiyifan/workplace-local/isla-runner/isla/Cargo.toml --bin isarch --release --`
- `-A /home/baiyifan/workplace-local/isla-runner/isla/rv64d.ir`
- `-C /home/baiyifan/workplace-local/isla-runner/isla/configs/riscv64_difftest.toml`
- `--verbose --probe-all --trace-all -I cur_privilege=Machine list-instructions`

先试过 `-I cur_privilege=zMachine`，结果 panic：

- `Failed to find enumeration member zzzMachine`
- 原因是命令行初始化会对枚举值做 z-encoding，所以这里必须传 `Machine`。

#### baseline：`legacy`

gate state:

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=legacy
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
```

结果：

- 退出码 `0`。
- 产物：
  - `legacy/output/rv64d_zSTORE.json`
  - `legacy/output/rv64d_zLOAD.json`
  - `legacy/solver.dump`
- `wc -l`：
  - `rv64d_zSTORE.json`: 149
  - `rv64d_zLOAD.json`: 295
  - `run.log`: 1143
- `zSTORE` 完成路径 fork 形态：`2,1,1,0`。
- `zLOAD` 完成路径 fork 形态：`3,2,2,2,1,1,1,0`。
- 完成路径均为 `Retire_Success(())`。
- `memory_event_count` 为 `1`。

判定：

- 当前 `legacy` builtin 仍是“无路径爆炸”性能基线。
- 该模式保留用于后续逐函数禁用 gate 的对照，但不能作为最终语义等价目标，因为它仍包含简化语义。

#### semantic gate：`plain-ram`

gate state:

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1
ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1
ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1
ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
```

结果：

- 退出码 `0`。
- 产物：
  - `plain-ram/output/rv64d_zSTORE.json`
  - `plain-ram/output/rv64d_zLOAD.json`
  - `plain-ram/solver.dump`
- `wc -l`：
  - `rv64d_zSTORE.json`: 149
  - `rv64d_zLOAD.json`: 295
  - `run.log`: 1143
- fork 形态与 `legacy` 相同：
  - `zSTORE`: `2,1,1,0`
  - `zLOAD`: `3,2,2,2,1,1,1,0`
- `memory_event_count` 为 `1`。
- `zSTORE` 前几个 trace 的长度比 `legacy` 多 `1`，来源是新增的 `assert(write_success)`，符合预期。
- 文件级 diff 不稳定，因为输出里的 instruction/model 选择存在非确定性；后续对照不能依赖整文件 byte diff，应改用规范化比较 `ret_val`、event kind、address、width、data、success constraint。

语义观察：

- `plain-ram` 下普通 store 的 memory event success 被 assert 为 true，返回 `Ok(true)`。
- 这比旧 `legacy` 中把 write success 作为 unconstrained-like payload 暴露给 `Ok(bool)` 更接近普通 RAM store 原语义。
- `plain-ram` 仍依赖外部前提：Machine、bare/identity、普通 RAM symbolic range、aligned、非 aq/rl/res、非 MMIO；PMP disabled 还需要单独验证 TOML 覆写是否真的生效。

判定：

- 在当前外部前提下，`plain-ram` 没有重新引入路径爆炸。
- `plain-ram` 应作为后续语义修正的主要实现模式继续推进。

### 2026-04-25：plain-ram 外部前提显式 gate

代码位置：`isla/isla-lib/src/executor.rs`

已完成：

- `plain-ram` 不再隐式假设 translation/PMP/PMA/MMIO 条件已经满足。
- 普通 `Load(Data)` / `Store(Data)` 除了原有 `aq=false`、`rl=false`、`res=false`、width concrete、alignment 条件外，还必须显式设置：
  - `ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1`
  - `ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1`
  - `ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1`
- 任一外部前提没有显式声明时，builtin 回退原 IR；不允许在 Rust builtin 内部偷偷把虚拟地址当物理地址、偷偷忽略 PMP、或偷偷把 MMIO/PMA 当普通 RAM。

语义含义：

- 这三个 env 不是在 builtin 内部放松语义，而是要求调用者确认当前 TOML/config/测试约束已经把原 IR 语义收窄到同一前提。
- 对 PMP 特别要注意：`configs/riscv64_difftest.toml` 里虽然写了 `sys_pmp_count = "0 : %i64"`，但当前 `rv64d.ir` 仍能看到编译期 `zsys_pmp_count=16`。因此 `ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1` 只能表示“本次外部测试环境确认 PMP 不会拒绝该普通 RAM 访问”，不能替代后续对 TOML 覆写是否生效的验证。

验证：

- 已运行 `cargo fmt`。
- 已运行 `cargo check -p isla-lib`，结果通过；输出只有仓库既有 warning。
- 已在安全目录 `/tmp/isla-vmem-gate-next/plain-ram` 运行：
  - `ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram`
  - `ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1`
  - `ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1`
  - `ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1`
  - `ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1`
  - `ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1`
  - `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`
- 结果退出码 `0`，产物：
  - `output/rv64d_zSTORE.json`
  - `output/rv64d_zLOAD.json`
  - `solver.dump`
- `wc -l`：
  - `run.log`: 1269
  - `rv64d_zSTORE.json`: 149
  - `rv64d_zLOAD.json`: 295
- fork 形态仍为：
  - `zSTORE`: `2,1,1,0`
  - `zLOAD`: `3,2,2,2,1,1,1,0`
- `memory_event_count` 仍为 `1`。

下一步：

- 之后用规范化比较确认 `legacy` 与 `plain-ram` 在普通 aligned `zSTORE` / `zLOAD` 的 `ret_val`、memory event kind/address/width/data/success constraint 上是否一致或是有意修正。

### 2026-04-25：规范化 VMEM 输出比较工具

新增文件：

- `agents/zSTORE_path_explosion/normalize_vmem_output.py`

目的：

- 不再用整文件 diff 比较 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
- 忽略会随 generator 变化的 `test-ins`、寄存器选择和路径顺序。
- 聚焦可观察语义：
  - `ret_val`
  - 每条路径的 `memory-events` 数量
  - event `kind`
  - `region`
  - `bytes`
  - `address_model`
  - `value`
  - `data`
  - `is_ifetch`
  - `is_exclusive`

用法：

```bash
agents/zSTORE_path_explosion/normalize_vmem_output.py path/to/rv64d_zSTORE.json
agents/zSTORE_path_explosion/normalize_vmem_output.py legacy.json plain-ram.json
```

已验证：

- 单文件 summary 可正常输出 `ret_val_counts`、`memory_event_count_counts`、`path_shape_counts`、`event_counts`。
- 对比 `legacy/output/rv64d_zSTORE.json` 与新的 `plain-ram/output/rv64d_zSTORE.json` 时，能稳定暴露已知差异：
  - `legacy` 的 write event `value` 是 `{1'h0, 1'b0}`。
  - `plain-ram` 的 write event `value` 是 `1'h1`。
  - 这是有意修正：普通 RAM store 不应保留原模型没有的 `Ok(false)` 可行路径。
- 同一次 summary 中 `plain-ram` 的 `zSTORE` 仍为 4 条路径，`ret_val` 全部是 `Retire_Success(())`，其中 2 条有一个 write event。
- `plain-ram` 的 `zLOAD` 仍为 8 条路径，`ret_val` 全部是 `Retire_Success(())`，其中 4 条有一个 read event。

限制：

- 当前工具仍不能证明两次 run 选择了同一条具体 instruction，因为 generator 会非确定性选择寄存器和立即数。
- 更严格的等价测试需要后续固定 instruction input，或让工具按 instruction class / event shape 做分组，而不是把两次随机 generator 输出当作一一对应。

### 2026-04-25：当前 HEAD 复测

测试目录：`/tmp/isla-vmem-current-3f2rou`

代码状态：

- `isla/` 分支：`fix-memory-sym-pathboomb-semantics`
- 当前相关提交：
  - `f3989e1 Add gated RISC-V vmem builtin modes`
  - `71f60d3 Return alignment errors for misaligned vmem builtins`
  - `1634fb0 Require explicit plain-RAM vmem assumptions`

已运行：

- `cargo check -p isla-lib`
  - 结果通过。
  - 仍有仓库既有 warning。

#### current legacy

gate state:

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=legacy
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
```

结果：

- 退出码 `0`。
- 产物：
  - `legacy/output/rv64d_zSTORE.json`
  - `legacy/output/rv64d_zLOAD.json`
  - `legacy/solver.dump`
- `wc -l`：
  - `run.log`: 1269
  - `rv64d_zSTORE.json`: 149
  - `rv64d_zLOAD.json`: 295
- fork 形态：
  - `zSTORE`: `2,1,1,0`
  - `zLOAD`: `3,2,2,2,1,1,1,0`
- `memory_event_count` 仍为 `1`。

判定：

- 最新提交没有破坏 `legacy` 无路径爆炸基线。

#### current plain-ram with explicit assumptions

gate state:

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1
ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1
ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1
ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
```

结果：

- 退出码 `0`。
- 产物：
  - `plain-ram/output/rv64d_zSTORE.json`
  - `plain-ram/output/rv64d_zLOAD.json`
  - `plain-ram/solver.dump`
- `wc -l`：
  - `run.log`: 1143
  - `rv64d_zSTORE.json`: 149
  - `rv64d_zLOAD.json`: 295
- fork 形态：
  - `zSTORE`: `2,1,1,0`
  - `zLOAD`: `3,2,2,2,1,1,1,0`
- `memory_event_count` 仍为 `1`。
- 日志中没有 `vmem_* fallback`。

判定：

- 显式外部前提 gate 没有误挡已经声明前提的快速路径。
- `plain-ram` 在这组前提下仍保持无路径爆炸。

#### current plain-ram missing assumptions

gate state:

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
# 未设置 ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION
# 未设置 ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS
# 未设置 ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM
```

结果：

- `timeout 120s` 后退出码 `124`。
- 产物只有：
  - `plain-ram-missing-assumptions/run.log`
  - `plain-ram-missing-assumptions/solver.dump`
- 没有生成最终 `output/rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
- 日志明确出现：
  - `vmem_write_addr builtin fallback: identity translation is not explicitly assumed`
  - `Symbolic (bit)vector length in subrange_internal ... [sys/vmem_utils.sail 224:30 - 224:88]`
- 观察到 fork 约 `54-66`，trace 长度约 `1100-1248`，大量 `E_SAMO_Access_Fault` 路径，`memory_event_count=0`。

判定：

- 新 gate 生效：缺少外部前提时不会偷偷走 `plain-ram` 快速路径。
- 回退原 IR 后会重新暴露已知路径爆炸，这符合设计：语义前提不完整时宁可回退/超时，也不能隐式放松语义。

#### normalized compare

已生成：

- `/tmp/isla-vmem-current-3f2rou/compare_zSTORE.json`
- `/tmp/isla-vmem-current-3f2rou/compare_zLOAD.json`

`zSTORE` 规范化结果：

- `legacy` 和 `plain-ram` 都有 4 条 path。
- `ret_val` 都是 4 个 `Retire_Success(())`。
- event 数量分布一致：
  - 2 条 path 无 event
  - 2 条 path 有 1 个 write event
- 主要差异：
  - `legacy` write event `value` 是 `{1'h0, 1'b0}`。
  - `plain-ram` write event `value` 是 `1'h1`。
  - 这是预期修正，普通 RAM store 不应保留原模型没有的 `Ok(false)` 可行路径。
- 具体 `address_model` / `data` 仍会因 generator 非确定性选例不同而变化，不能当作语义差异直接判定。

`zLOAD` 规范化结果：

- `legacy` 和 `plain-ram` 都有 8 条 path。
- `ret_val` 都是 8 个 `Retire_Success(())`。
- event 数量分布一致：
  - 4 条 path 无 event
  - 4 条 path 有 1 个 read event
- read event 的 `kind`、`region`、`bytes`、`value`、`is_ifetch`、`is_exclusive` 形态一致。
- 具体 `address_model` 会因 generator 非确定性选例不同而变化。

下一步测试改进：

- 固定输入 instruction / register assignment，减少 generator 非确定性，才能对 `address_model` 和 `data` 做一一比较。
- 在固定样例下补 concrete misaligned load/store，验证 `Err(Memory_Exception(... Align))` 的输出构造子和地址字段。

### 2026-04-25：固定 instruction 字段与 misaligned 回归

代码位置：`isla/isla-lib/src/isarch_exec.rs`

已完成：

- 给 `run_symbolic_execute` 的 RISC-V `zSTORE` / `zLOAD` 参数生成增加固定字段覆盖。
- 保留原有默认行为：`zSTORE` / `zLOAD` 的 width 默认仍覆写为 `4`，用于当前 zSTORE/zLOAD 回归。
- 新增 env 覆写：
  - `ISLA_RISCV_TEST_ZSTORE_IMM`
  - `ISLA_RISCV_TEST_ZSTORE_RS1`
  - `ISLA_RISCV_TEST_ZSTORE_RS2`
  - `ISLA_RISCV_TEST_ZSTORE_WIDTH`
  - `ISLA_RISCV_TEST_ZLOAD_IMM`
  - `ISLA_RISCV_TEST_ZLOAD_RS1`
  - `ISLA_RISCV_TEST_ZLOAD_RD`
  - `ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED`
  - `ISLA_RISCV_TEST_ZLOAD_WIDTH`
- bitvector 字段支持十进制，例如 `1`，也支持明确宽度的 `#b...` / `0b...` / `#x...` / `0x...`。带前缀格式的宽度必须和字段宽度一致。
- 字段映射按 Sail 原型：
  - `STORE(imm, rs2, rs1, width)`
  - `LOAD(imm, rs1, rd, is_unsigned, width)`

验证：

- 已运行 `cargo fmt`。
- 已运行 `cargo check -p isla-lib`，结果通过；输出只有仓库既有 warning。

固定 aligned 样例：

```text
ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram
ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1
ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1
ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1
ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1
ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
ISLA_RISCV_TEST_ZSTORE_IMM=0
ISLA_RISCV_TEST_ZSTORE_RS1=1
ISLA_RISCV_TEST_ZSTORE_RS2=0
ISLA_RISCV_TEST_ZSTORE_WIDTH=4
ISLA_RISCV_TEST_ZLOAD_IMM=0
ISLA_RISCV_TEST_ZLOAD_RS1=1
ISLA_RISCV_TEST_ZLOAD_RD=2
ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED=false
ISLA_RISCV_TEST_ZLOAD_WIDTH=4
-I cur_privilege=Machine
-I x1=#x0000000080400000
```

结果目录：`/tmp/isla-vmem-fixed-xIQIrt/aligned-corrected`

- `zSTORE` 输出 1 条路径：
  - instruction: `sw x0, 0x0(x1)`
  - `ret_val`: `Retire_Success(())`
  - memory event: 1 个 write
  - address/address_model: `#x0000000080400000`
  - bytes: `4`
  - data: `#x00000000`
  - write success value: `1'h1`
- `zLOAD` 输出 1 条路径：
  - instruction: `lw x2, 0x0(x1)`
  - `ret_val`: `Retire_Success(())`
  - memory event: 1 个 read
  - address/address_model: `#x0000000080400000`
  - bytes: `4`
  - value: `#x00000000`

固定 concrete misaligned 样例：

```text
同上，但不需要 ISLA_RISCV_VMEM_ASSUME_ALIGNED=1
-I x1=#x0000000080400002
```

结果目录：`/tmp/isla-vmem-fixed-xIQIrt/misaligned`

- `zSTORE` 输出 1 条路径：
  - instruction: `sw x0, 0x0(x1)`
  - `ret_val`: `Memory_Exception(... E_SAMO_Addr_Align ... #x0000000080400002)`
  - memory events: `[]`
  - fork: `0`
  - trace_len: `25`
- `zLOAD` 输出 1 条路径：
  - instruction: `lw x2, 0x0(x1)`
  - `ret_val`: `Memory_Exception(... E_Load_Addr_Align ... #x0000000080400002)`
  - memory events: `[]`
  - fork: `0`
  - trace_len: `20`

注意事项：

- 第一次固定 aligned 试跑没有设置 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`，`zLOAD` 因 alignment unknown 回退 IR 并进入已知路径爆炸；该进程已终止，不作为语义回归结果。
- 当前固定字段机制只覆盖 `zSTORE` / `zLOAD`。其他指令如果需要固定样例，应按各自 Sail 构造子顺序增加映射。

### 2026-04-25：默认模式改为等价优先

代码位置：`isla/isla-lib/src/executor.rs`

已完成：

- `ISLA_RISCV_VMEM_BUILTIN_MODE` 未设置时，默认不再走 `legacy`。
- 未知 `ISLA_RISCV_VMEM_BUILTIN_MODE` 也不再落到 `legacy`。
- 默认和未知模式都改为 `plain-ram`：
  - 满足显式外部前提、普通 Data load/store、width concrete、alignment 条件时才接管。
  - 不满足时回退原 IR。
  - concrete misaligned 仍优先返回原语义允许的 alignment `Err(...)`。
- `legacy` 仍保留，但必须显式设置 `ISLA_RISCV_VMEM_BUILTIN_MODE=legacy` 才会启用；它只作为路径爆炸诊断和旧性能基线，不应作为语义等价默认值。

验证：

- 已运行 `cargo fmt`。
- 已运行 `cargo check -p isla-lib`，结果通过；输出只有仓库既有 warning。

默认 aligned 固定样例：

测试目录：`/tmp/isla-vmem-equivalent-default-Dp1XRC/aligned-default`

- 未设置 `ISLA_RISCV_VMEM_BUILTIN_MODE`。
- 设置外部 plain-RAM 前提：
  - `ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1`
  - `ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1`
  - `ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1`
  - `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`
- 固定 instruction：
  - `sw x0, 0x0(x1)`
  - `lw x2, 0x0(x1)`
  - `x1 = #x0000000080400000`
- 结果：
  - `zSTORE`: 1 条路径，`Retire_Success(())`，1 个 write event，address/model `#x0000000080400000`，data `#x00000000`，success `1'h1`。
  - `zLOAD`: 1 条路径，`Retire_Success(())`，1 个 read event，address/model `#x0000000080400000`，value `#x00000000`。
  - 两者 fork 都为 `0`。

默认 concrete misaligned 固定样例：

测试目录：`/tmp/isla-vmem-equivalent-default-Dp1XRC/misaligned-default`

- 未设置 `ISLA_RISCV_VMEM_BUILTIN_MODE`。
- 设置外部 plain-RAM 前提，但不设置 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`。
- 固定 instruction：
  - `sw x0, 0x0(x1)`
  - `lw x2, 0x0(x1)`
  - `x1 = #x0000000080400002`
- 结果：
  - `zSTORE`: `Memory_Exception(... E_SAMO_Addr_Align ... #x0000000080400002)`，`memory-events = []`，fork `0`。
  - `zLOAD`: `Memory_Exception(... E_Load_Addr_Align ... #x0000000080400002)`，`memory-events = []`，fork `0`。

当前等价声明：

- 默认行为已从“不等价但快的 legacy”改成“等价优先的 plain-ram/fallback”。
- 在显式 plain-RAM 外部前提成立时，固定普通 aligned load/store 与 concrete alignment fault 样例已验证。
- 对未实现的大语义面，默认不会再静默走 `legacy` 近似成功；会按规则返回可构造的 `Err(...)` 或回退 IR。

### 2026-04-25：aligned 假设改为 SMT 约束

代码位置：`isla/isla-lib/src/executor.rs`

问题：

- 之前 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 只是让 `plain-ram` gate 放行 symbolic address。
- 这会导致模型里地址仍可能是 misaligned，但 builtin 返回成功访存；这不是等价语义。

已完成：

- `validate_plain_vmem_common(...)` 现在接收 `solver` 和 `SourceLoc`。
- 当地址不是 concrete、且设置 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 时，不再只放行，而是添加 SMT 断言：
  - width = 1：无需断言。
  - width 为 2/4/8/...：断言 `addr[log2(width)-1:0] == 0`。
  - 非 2 的幂 width：返回 `ExecError::Type(...)`，不近似处理。
- concrete aligned / concrete misaligned 的行为不变：
  - concrete aligned 直接放行。
  - concrete misaligned 优先返回 alignment `Err(...)`。

验证：

- 已运行 `cargo fmt`。
- 已运行 `cargo check -p isla-lib`，结果通过；输出只有仓库既有 warning。

symbolic aligned 固定样例：

测试目录：`/tmp/isla-vmem-align-assert-dVujUh`

- 未设置 `x1`，让地址由模型选择。
- 固定 instruction：
  - `sw x0, 0x0(x1)`
  - `lw x2, 0x0(x1)`
- 设置：
  - `ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1`
  - `ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1`
  - `ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1`
  - `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`

结果：

- `zSTORE`：
  - 1 条路径，fork `0`
  - `Retire_Success(())`
  - 1 个 write event
  - `address_model = #x0000000080380000`
- `zLOAD`：
  - 1 条路径，fork `0`
  - `Retire_Success(())`
  - 1 个 read event
  - `address_model = #x0000000080320000`
- 两个 address_model 低两位均为 0。
- `solver.dump` 中可见新增 alignment constraint：
  - `(assert (= ((_ extract 1 0) k!7) #b00))`

结论：

- `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 现在是实际 SMT 约束，不再只是未建模假设。
- 这消除了一个明确的不等价来源：symbolic address 在成功 plain-RAM 路径上不再允许 misaligned 模型。

#### function record：`vmem_write_addr`

```text
- function: vmem_write_addr
  instruction: zSTORE
  gate state: ISLA_RISCV_VMEM_BUILTIN_MODE=legacy, ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=0, ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=1
  result: explodes
  fork count: observed about 57-70 before 5m timeout
  elapsed: 5m timeout
  hot source/IR: sys/vmem_utils.sail 224:30-224:88, subrange_internal with symbolic vector length; many E_SAMO_Access_Fault paths
  decision: restore builtin / keep builtin; add precise Err and semantic summaries rather than leaving this path in raw IR for zSTORE
  notes: no final rv64d_zSTORE.json was produced; memory_event_count was mostly 0 on exploding paths
```

补充证据：

- `write-off` 退出码 `124`。
- 只有 `write-off/run.log` 和 `write-off/solver.dump`，没有最终 `output/rv64d_zSTORE.json`。
- 日志中多次出现：
  - `执行错误: Symbolic (bit)vector length in subrange_internal ... [sys/vmem_utils.sail 224:30 - 224:88]`
  - 大量 `Memory_Exception(... E_SAMO_Access_Fault ...)`
- trace 长度常见在约 `1100-1300`，显著高于 baseline。

判定：

- `vmem_write_addr` 是已确认路径爆炸来源。
- 不能为了语义完整性直接长期回退 raw IR；应保留 builtin，并按 fail-closed 规则逐步补齐：能构造原语义允许的 `Err(...)` 就返回 `Err(...)`，不能构造就回退 IR，回退会爆炸且语义又未实现时允许 panic 暴露 unsupported case。

#### function record：`vmem_read_addr`

```text
- function: vmem_read_addr
  instruction: zLOAD
  gate state: ISLA_RISCV_VMEM_BUILTIN_MODE=legacy, ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=1, ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=0
  result: explodes
  fork count: observed about 50-70 before 5m timeout
  elapsed: 5m timeout
  hot source/IR: prelude/prelude.sail 93:21-93:34, zeros with symbolic vector length; many E_Load_Access_Fault paths
  decision: restore builtin / keep builtin; add precise Err and semantic summaries rather than leaving this path in raw IR for zLOAD
  notes: zSTORE completed and produced output first; zLOAD timed out and did not produce final rv64d_zLOAD.json
```

补充证据：

- `read-off` 退出码 `124`。
- 产物包括 `read-off/output/rv64d_zSTORE.json`、`read-off/run.log`、`read-off/solver.dump`，但没有最终 `rv64d_zLOAD.json`。
- 日志中多次出现：
  - `执行错误: Symbolic (bit)vector length in zeros ... [prelude/prelude.sail 93:21 - 93:34]`
  - 大量 `Memory_Exception(... E_Load_Access_Fault ...)`
  - 少量 `Retire_Success(())`
- trace 长度常见在约 `1048-1136`，显著高于 baseline。

判定：

- `vmem_read_addr` 是已确认路径爆炸来源。
- 与 `vmem_write_addr` 一样，后续方向是保留 builtin 框架并修正语义，而不是把它整体恢复成 raw IR。

#### 尚未运行的 case

- `ISLA_RISCV_VMEM_BUILTIN_MODE=off` 尚未单独运行。
- 因为 `write-off` 和 `read-off` 两个单函数禁用 case 都已经在 5 分钟内超时，`off` 对“是否需要保留这两个 builtin”的证明价值较低。
- 若后续需要完整矩阵记录，可以再运行 `off`，预期结果是同样爆炸或更差；该预期不能替代实际记录。

## 当前阶段的保守规则

在完整语义修正前，`call_isla_implemented_function(...)` 应只在满足以下条件时接管：

- `access` 是普通 `Load(Data)` 或 `Store(Data)`
- `aq == false`
- `rl == false`
- `res == false`
- `width` concrete
- 能证明地址 aligned，或已添加等价 aligned 约束
- 能证明当前配置下不需要地址翻译、PMP/PMA/MMIO 检查

其他情况应优先返回与原语义兼容的 `Err(...)`。如果没有把握构造正确异常，再回退到原 IR 函数体；若因为调用点结构或中途状态导致无法回退，则允许 panic / internal error。这样可以保留 `zSTORE` 普通路径的主要性能收益，同时避免把异常路径和系统级内存语义错误地剪掉。

## 不完整覆盖的处理规则

实现 builtin 时不能为了覆盖更多指令而默认成功。每个新接管的 case 都必须先回答：

- 原 Sail 路径在该 case 下是否可能返回 `Err(Memory_Exception(...))`
- 是否可能触发 page walk、PMP、PMA、MMIO、callback 或 reservation side effect
- 是否可能拆分成多个 memory events
- 返回值 payload 是否会被上层观察
- trace 中地址应当是虚拟地址还是物理地址

只要其中任一项没有明确等价实现，就不能返回 `Ok(...)`。可接受的处理顺序是：

1. 返回原语义允许的 `Err(...)`。
2. 回退原 IR。
3. panic / internal error，暴露未覆盖语义。

不可接受的处理是：

- 把未知异常路径当成成功访存。
- 把未知翻译结果当作 identity translation。
- 把未知 PMP/PMA/MMIO 结果当作普通 RAM。
- 把未知 misaligned split 简化成单次整宽 event。
- 对普通 store 引入原模型没有的 `Ok(false)` 可行路径。
