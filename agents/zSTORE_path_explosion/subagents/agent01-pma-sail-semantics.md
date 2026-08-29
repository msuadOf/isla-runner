# agent01: PMA/PMA check Sail 语义梳理

## 范围与输入

- agent: agent01
- 议题目录: `agents/zSTORE_path_explosion/`
- 只读源码范围:
  - `sail-riscv/model/sys/pma.sail`
  - `sail-riscv/model/sys/mem.sail`
  - `sail-riscv/model/sys/platform.sail`
  - 辅助核对: `sail-riscv/model/core/range_util.sail`, `sail-riscv/model/core/mem_type_utils.sail`, `sail-riscv/model/core/types.sail`
  - Isla worktree: `isla/.worktrees/zstore-pma-mmio`
- 按顶层 `AGENTS.md` 要求，代码分析前已读取 `agents/findings.md`。
- `agents/overview.md` 当前不存在；本报告基于源码、已有 `agents/findings.md` 和 Isla worktree 中 IR/profile 线索整理。

## 1. 源码级语义摘要

### PMA 数据模型

`pma.sail` 定义的 PMA 是平台物理内存属性，不是标准 CSR 可查询状态。核心结构为:

- `PMA`: 包含 `cacheable/coherent/executable/readable/writable/read_idempotent/write_idempotent/misaligned_fault/reservability/supports_cbo_zero`。
- `misaligned_fault`: `NoFault | AccessFault | AlignmentFault`，描述某 PMA region 内 misaligned access 是否直接导致 access fault 或 alignment fault。
- `Reservability`: `RsrvNone | RsrvNonEventual | RsrvEventual`，当前 `pmaCheck` 只区分是否为 `RsrvNone`，没有细分 eventual guarantee。
- `PMA_Region`: `(base, size, attributes, include_in_device_tree)`。`include_in_device_tree` 不影响 Sail 执行语义。
- `pma_regions`: `register pma_regions : list(PMA_Region) = config memory.regions`。源码注释要求该列表已排序且不重叠。

当前 `rv64d_v256_e64.json` 里主要有 3 个 region:

| Region | Range | 关键 PMA |
| --- | --- | --- |
| ROM | `0x1000 + 0x1000` | readable, not writable, not executable, `NoFault`, `RsrvNone` |
| MMIO | `0x02000000 + 0x02000000` | readable/writable, not executable, `AlignmentFault`, `RsrvNone` |
| RAM | `0x80000000 + 0x80000000` | readable/writable/executable, `NoFault`, `RsrvEventual`, `supports_cbo_zero` |

### `matching_pma_bits_range`

源码位置: `sail-riscv/model/sys/pma.sail:107-117`

语义:

```sail
matching_pma_bits_range(pmas, base, size)
```

- 输入是 `list(PMA_Region)`、64-bit `base`、64-bit `size`。
- 空列表返回 `None()`。
- 非空列表取表头 `pma`:
  - 若 `range_subset(base, size, pma.base, pma.size)` 为真，返回 `Some(pma)`。
  - 否则递归检查剩余列表。
- 结果是“第一个完整包含 `[base, base + size)` 的 PMA region”。
- 它检查的是完整包含，不是任意 overlap；跨 PMA 边界或只部分落入某 region 都会继续找下一项，最后可能返回 `None()`。
- `range_subset` 是 bitvector wrap-aware 的右开区间包含判断。其公式在 `range_util.sail` 中是:
  - `a_end = (a_begin + a_size) - b_begin`
  - `b_end = (b_begin + b_size) - b_begin`
  - `a_begin = a_begin - b_begin`
  - 返回 `a_begin <=u b_end & a_end <=u b_end & a_begin <=u a_end`

### `matching_pma`

源码位置: `sail-riscv/model/sys/pma.sail:119-123`

语义:

```sail
matching_pma(pmas, addr, width)
```

- 把 `physaddr` 转成 bits 后 `zero_extend` 到 64 bit。
- 把 `mem_access_width` 用 `to_bits(width)` 转成 64-bit size。
- 委托给 `matching_pma_bits_range`。

因此 `matching_pma` 没有额外权限语义，只是 `physaddr + width` 到 `PMA_Region option` 的适配层。

### `pmaCheck`

源码位置: `sail-riscv/model/sys/mem.sail:75-152`

语义:

```sail
pmaCheck(paddr, width, access, res_or_con) -> option(ExceptionType)
```

1. 先调用 `matching_pma(pma_regions, paddr, width)`。
2. 若没有匹配 region，返回 `Some(accessFaultFromAccessType(access))`。
3. 若有匹配 region:
   - 计算 `misaligned = not(is_aligned_addr(paddr, width))`。
   - 若 `attributes.misaligned_fault == AccessFault` 且 misaligned，立即返回 access fault。
   - 若 `attributes.misaligned_fault == AlignmentFault` 且 misaligned，立即返回 alignment fault。
   - 其它情况进入 access permission 检查。
4. access permission 检查按 `MemoryAccessType` 计算 `canAccess`。
5. 若 `canAccess` 为真，返回 `None()`；否则返回 `Some(accessFaultFromAccessType(access))`。

注意:

- misaligned fault 检查早于 readable/writable/executable 权限检查。
- `res_or_con` 主要是对调用约定的断言输入，不是异常类型选择:
  - plain `Load(_)` 要求 `not(res_or_con)`。
  - `LoadReserved(_)`、`StoreConditional(_)`、`Atomic(_)` 要求 `res_or_con`。
  - `Store(_)` 当前不 assert `not(res_or_con)`，源码 TODO 说明这是因为 `mem_write_*` API 默认 `Store` access 和传入 `aq/rl/con` flags 有冲突。
- `get_config_print_pma() & not(canAccess)` 时会打印 PMA failure log；这是 permission failure 分支的副作用。

### `phys_access_check`

源码位置: `sail-riscv/model/sys/mem.sail:169-186`

语义:

```sail
phys_access_check(access, priv, paddr, width, res_or_con) -> option(ExceptionType)
```

- 先计算 `pmpError = pmpCheck(paddr, width, access, priv)`。
- 再计算 `pmaError = pmaCheck(paddr, width, access, res_or_con)`。
- 合并规则:

| `pmpError` | `pmaError` | 返回 |
| --- | --- | --- |
| `None()` | `None()` | `None()` |
| `Some(e)` | `None()` | `Some(e)` |
| `None()` | `Some(e)` | `Some(e)` |
| `Some(e0)` | `Some(e1)` | `Some(highestPriorityAlignmentOrAccessFault(e0, e1))` |

`highestPriorityAlignmentOrAccessFault` 只接受 access fault 和 alignment fault，priority 为:

- access fault: priority 1
- alignment fault: priority 0

因此 PMP 和 PMA 同时报错时，access fault 高于 alignment fault；同优先级时实现返回右侧 `e1`，也就是 PMA error。

`checked_mem_read` / `checked_mem_write` 在 `phys_access_check` 返回 `None()` 后才做 `within_mmio_readable/writable` 与 `mmio_read/mmio_write` 或 RAM read/write。PMA check 成功不等于直接 RAM 访问，MMIO dispatch 仍是后续可观察语义。

## 2. `pmaCheck` 完整分支表

### 2.1 Exception 映射

`pmaCheck` 本身只在需要报错时调用 `accessFaultFromAccessType` 或 `alignmentFaultFromAccessType`。映射位于 `sail-riscv/model/core/mem_type_utils.sail`。

| Access | Access fault | Alignment fault |
| --- | --- | --- |
| `InstructionFetch()` | `E_Fetch_Access_Fault()` | `E_Fetch_Addr_Align()` |
| `Load(_)` | `E_Load_Access_Fault()` | `E_Load_Addr_Align()` |
| `LoadReserved(_)` | `E_Load_Access_Fault()` | `E_Load_Addr_Align()` |
| `Store(_)` | `E_SAMO_Access_Fault()` | `E_SAMO_Addr_Align()` |
| `StoreConditional(_)` | `E_SAMO_Access_Fault()` | `E_SAMO_Addr_Align()` |
| `Atomic(_)` | `E_SAMO_Access_Fault()` | `E_SAMO_Addr_Align()` |
| `CacheAccess(CB_manage(_))` | `E_SAMO_Access_Fault()` | `E_SAMO_Addr_Align()` |
| `CacheAccess(CB_zero())` | `E_SAMO_Access_Fault()` | `E_SAMO_Addr_Align()` |
| `CacheAccess(CB_prefetch(PREFETCH_R))` | nominal `E_Load_Access_Fault()` | nominal `E_Load_Addr_Align()` |
| `CacheAccess(CB_prefetch(PREFETCH_W))` | nominal `E_SAMO_Access_Fault()` | nominal `E_SAMO_Addr_Align()` |
| `CacheAccess(CB_prefetch(PREFETCH_I))` | nominal `E_Fetch_Access_Fault()` | nominal `E_Fetch_Addr_Align()` |

Prefetch 的 fault 在 helper 中是 nominal value；`Zicbop` 调用侧会把 `phys_access_check` 的 `Some(_e)` 当作 no-op，不退休异常。

### 2.2 PMA match 与 misaligned gate

| `matching_pma(...)` | `misaligned` | `attributes.misaligned_fault` | 后续 access permission? | `pmaCheck` 返回 |
| --- | --- | --- | --- | --- |
| `None()` | 任意 | 任意 | 否 | `Some(accessFaultFromAccessType(access))` |
| `Some(region)` | `true` | `AccessFault` | 否 | `Some(accessFaultFromAccessType(access))` |
| `Some(region)` | `true` | `AlignmentFault` | 否 | `Some(alignmentFaultFromAccessType(access))` |
| `Some(region)` | `true` | `NoFault` | 是 | 见 2.3 |
| `Some(region)` | `false` | `NoFault` | 是 | 见 2.3 |
| `Some(region)` | `false` | `AccessFault` | 是 | 见 2.3 |
| `Some(region)` | `false` | `AlignmentFault` | 是 | 见 2.3 |

要点:

- 未匹配任何 PMA region 时，即使地址 misaligned，也直接是 access fault，不会返回 alignment fault。
- `AccessFault/AlignmentFault` 只有在 `misaligned == true` 时触发早返回。
- 早返回路径不计算 `canAccess`，也不会触发 `res_or_con` 相关 assert。

### 2.3 Access permission 与 `res_or_con`

以下表格只适用于 2.2 中进入 permission 检查的情况。统一规则是:

- 若 `canAccess == true`，返回 `None()`。
- 若 `canAccess == false`，返回 `Some(accessFaultFromAccessType(access))`。

| Access | `res_or_con` 处理 | `canAccess` 条件 |
| --- | --- | --- |
| `InstructionFetch()` | 不检查 | `attributes.executable` |
| `Load(_)` | `assert(not(res_or_con))` | `attributes.readable` |
| `Store(_)` | 不检查；源码 TODO 暂未 assert | `attributes.writable` |
| `LoadReserved(_)` | `assert(res_or_con)` | `attributes.readable & attributes.reservability != RsrvNone` |
| `StoreConditional(_)` | `assert(res_or_con)` | `attributes.writable & attributes.reservability != RsrvNone` |
| `Atomic(_, _, _)` | `assert(res_or_con)` | `attributes.readable & attributes.writable` |
| `CacheAccess(CB_zero())` | 不检查 | `attributes.writable & attributes.supports_cbo_zero` |
| `CacheAccess(CB_manage(_))` | 不检查 | `attributes.readable | attributes.writable` |
| `CacheAccess(CB_prefetch(PREFETCH_R))` | 不检查 | `attributes.readable` |
| `CacheAccess(CB_prefetch(PREFETCH_W))` | 不检查 | `attributes.writable` |
| `CacheAccess(CB_prefetch(PREFETCH_I))` | 不检查 | `attributes.executable` |

`assert(...)` 是 Sail 模型调用约定断言，不是架构异常返回。做 summary 时不能把 assertion violation 静默改成 `None()` 或 access fault。

## 3. 真实 ISA/PMA 语义 vs executor fork 来源

| 分支/条件 | 语义属性 | 判断 |
| --- | --- | --- |
| `matching_pma` 最终 `Some(region)` / `None()` | 真实 PMA/platform 语义 | 决定地址范围是否被某 PMA region 完整覆盖。`None()` 必须导致 access fault。 |
| `matching_pma_bits_range` 对 region list 的逐项递归 | 主要是实现形态导致的 executor fork | 对符号地址，每个 `range_subset` 的 `if` 都会 fork；但架构上只需要“第一个完整包含 region 或无匹配”这个结果。 |
| `range_subset` 的 wrap-aware 三条件公式 | 真实 range 语义 | 不能改成普通整数非回绕区间，也不能省略第三个条件。 |
| `range_subset` 内部 `<=_u` 和 `&` 的短路控制流 | executor fork | 条件本身要保留，但不要求保留为多条 IR 控制路径。 |
| `misaligned_fault == AccessFault/AlignmentFault && misaligned` | 真实 PMA 语义与异常优先级 | misaligned PMA fault 优先于 permission check。 |
| `return Some(...)` 的早返回形态 | 实现短路 | 可 summary 成 ITE/条件表达式，但返回值和是否绕过 permission/assert/log 要等价。 |
| access type 到 `canAccess` 的条件 | 真实 PMA 语义 | R/W/X、reservability、CBO zero、prefetch 类型都必须保留。 |
| `canAccess` 中 `&` / `|` 的短路跳转 | executor fork | 条件要保留，控制流可以下沉为 SMT boolean。 |
| `Load/LR/SC/Atomic` 的 `res_or_con` assert | 模型调用约定语义 | 不是 ISA exception，但 summary 不能隐藏违反调用约定的行为。 |
| `Store(_)` 不 assert `not(res_or_con)` | 当前源码语义 | 不能为了“看起来合理”补上断言；源码 TODO 明确当前 API 允许这种组合。 |
| `get_config_print_pma() & not(canAccess)` | 可观察日志副作用 | 若要求 trace/log 等价，print enabled 时应 fallback 或补同等 log。通常 fork 性能分析里配置是 concrete false。 |
| `phys_access_check` 同时计算 PMP 和 PMA 后合并 | 真实组合语义 | `None()` 只在 PMP/PMA 都允许时成立；双 fault 时 access fault 高于 alignment fault。 |
| `phys_access_check` option match 的产品分支 | executor fork | 可用等价条件合成返回 option/exception，避免展开为多条 executor 路径。 |
| `checked_mem_read/write` 的 MMIO vs RAM dispatch | 真实平台语义 | PMA success 后仍必须保留 `within_mmio_*`、`mmio_read/write`、CLINT/HTIF side effects、RAM memory event。 |

对当前 zSTORE path explosion 来说，`matching_pma_bits_range` 是典型“真实结果小、实现控制流多”的热点。PMA region 列表是 concrete config，但 `paddr` 可符号化，递归 list scan 会产生“ROM / MMIO / RAM / None”一类 executor path split。summary 的价值在于把这些控制分支变成一个返回 `option(ExceptionType)` 的条件表达式，而不是修改 PMA 语义。

## 4. `pmaCheck` summary 必须保留的语义红线

1. 不允许把 `matching_pma == None()` 当成 plain RAM 或允许访问；源码要求返回 `Some(accessFaultFromAccessType(access))`。
2. PMA match 必须是整个 `[paddr, paddr + width)` 被单个 region 完整包含，且使用 `range_subset` 的 bitvector wrap-aware 语义；不能只检查起始地址，也不能用普通非回绕整数区间近似。
3. 必须保留 region 顺序的“first match”语义。虽然配置要求 sorted/non-overlap，summary 不应依赖非法配置下的任意化行为。
4. `misaligned_fault` 优先级必须保留: `AccessFault`/`AlignmentFault` 只在 `misaligned` 时早返回，且早于 permission check；`NoFault` 不因 misaligned 本身拒绝访问。
5. 未匹配 PMA region 的 misaligned access 仍是 access fault，不是 alignment fault。
6. access fault 与 alignment fault 必须按 `accessFaultFromAccessType` / `alignmentFaultFromAccessType` 精确映射，包括 CBO 与 prefetch 的 nominal exception。
7. access permission 必须逐项保留:
   - fetch 看 `executable`
   - load 看 `readable`
   - store 看 `writable`
   - LR 看 `readable & reservability != RsrvNone`
   - SC 看 `writable & reservability != RsrvNone`
   - AMO 看 `readable & writable`
   - CBO zero 看 `writable & supports_cbo_zero`
   - CBO manage 看 `readable | writable`
   - prefetch R/W/I 分别看 readable/writable/executable
8. `res_or_con` 的当前源码约定必须保留:
   - `Load(_)` assert `not(res_or_con)`
   - `LoadReserved(_)` / `StoreConditional(_)` / `Atomic(_)` assert `res_or_con`
   - `Store(_)` 当前不 assert，summary 不应擅自收紧
9. `phys_access_check` 级 summary 若覆盖 PMA/PMP 合并，必须保留:
   - PMP 和 PMA 都允许才返回 `None()`
   - 单侧 fault 直接返回该 fault
   - 双侧 fault 时 access fault 高于 alignment fault
   - 同优先级时源码实际选择 PMA 侧结果
10. PMA summary 只能回答“PMA 是否允许/报什么异常”，不能绕过后续 MMIO/RAM 行为。`within_mmio_readable/writable`、`mmio_read/mmio_write`、CLINT/HTIF 状态更新、callbacks、RAM `ReadMem/WriteMem` trace 都在 `pmaCheck` 之后。
11. 若 summary 命中路径中 `get_config_print_pma()` 可能为真，要么产生等价 `print_log`，要么回退 Sail IR；否则会改变日志可观察行为。
12. 对 unsupported symbolic shape、未知 enum ctor、非标准 PMA region 结构、无法构造精确 exception ctor 的情况，应回退 IR，不应用“默认 RAM 成功”或“默认 access fault”粗略替代。

## 5. 对后续实现方向的直接建议

- 优先做 `pmaCheck` 或 `phys_access_check` 小粒度 exact summary，而不是只 summary `matching_pma_bits_range` 的 `option(PMA_Region)`。原因是 `option(PMA_Region)` 会把大结构体 region 带回 IR，后续仍要在 Sail 控制流里展开 misalignment/access permission。
- 若从 `pmaCheck` 做起，当前 config concrete 时可以对每个 PMA region 构造:
  - `match_i = range_subset(paddr_bits64, width_bits64, region.base, region.size)`
  - `selected_i = match_i & no_previous_match`
  - `no_match = !any(match_i)`
  - 再按 `selected_i` 合成 exact exception option。
- 对 zSTORE 的窄场景，`access` 通常是 concrete `Store(_)`，`res_or_con` 可能来自 `con/res`。但 summary 设计不能只保留 Store 分支；通用入口需要覆盖所有 `MemoryAccessType` 或在非支持 access ctor 上回退。
- 若要跨到 `phys_access_check`，不能用 PMP-off 假设替代 PMP 语义；应与现有 `pmpCheck` exact summary 的返回条件合并，并保持双 fault priority。
