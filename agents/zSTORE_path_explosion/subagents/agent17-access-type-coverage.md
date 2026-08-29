# agent17: pmaCheck access type coverage audit

日期：2026-04-27

范围：审计 `sail-riscv/model/sys/mem.sail::pmaCheck` 对 `MemoryAccessType(mem_payload)` 的覆盖，重点关注 cache / LR / SC / atomic；只评估，不修改生产代码。

已读上下文：

- `agents/findings.md`
- `agents/zSTORE_path_explosion/principles.md`
- `agents/zSTORE_path_explosion/status.md`
- `agents/overview.md`：当前仓库不存在，无法加载

## 1. MemoryAccessType 覆盖与 canAccess 公式

`MemoryAccessType` 定义在 `sail-riscv/model/core/types.sail:100-113`。`pmaCheck` 的 `match access` 位于 `sail-riscv/model/sys/mem.sail:94-142`，对所有顶层 ctor 都有显式分支；`CacheAccess` 下还区分 `CB_zero` / `CB_manage` / `CB_prefetch(PREFETCH_*)`。

PMA 未命中时不进入 `canAccess`：`matching_pma(...) = None()` 直接返回 `Some(accessFaultFromAccessType(access))`，见 `mem.sail:82-85`。

PMA 命中后先处理 misalignment，见 `mem.sail:87-91`：

- `attributes.misaligned_fault = AccessFault` 且 `misaligned`：返回 `accessFaultFromAccessType(access)`
- `attributes.misaligned_fault = AlignmentFault` 且 `misaligned`：返回 `alignmentFaultFromAccessType(access)`
- 否则才计算 `canAccess`

`canAccess` 公式如下。未列出的 PMA 字段 `cacheable`、`coherent`、`read_idempotent`、`write_idempotent` 当前不参与 `pmaCheck` 的许可判断。

| access | assert / 前置约束 | canAccess |
| --- | --- | --- |
| `InstructionFetch()` | 无 | `attributes.executable` |
| `Load(_)` | `assert(not(res_or_con))` | `attributes.readable` |
| `Store(_)` | 当前无 assert；源码 TODO 说明默认 `Store` access 会和 `aq/rl/con` flags 冲突 | `attributes.writable` |
| `LoadReserved(_)` | `assert(res_or_con)` | `attributes.readable & attributes.reservability != RsrvNone` |
| `StoreConditional(_)` | `assert(res_or_con)` | `attributes.writable & attributes.reservability != RsrvNone` |
| `Atomic(_, _, _)` | `assert(res_or_con)` | `attributes.readable & attributes.writable` |
| `CacheAccess(CB_zero())` | 无 | `attributes.writable & attributes.supports_cbo_zero` |
| `CacheAccess(CB_manage(_))` | 无 | `attributes.readable | attributes.writable` |
| `CacheAccess(CB_prefetch(PREFETCH_R))` | 无 | `attributes.readable` |
| `CacheAccess(CB_prefetch(PREFETCH_W))` | 无 | `attributes.writable` |
| `CacheAccess(CB_prefetch(PREFETCH_I))` | 无 | `attributes.executable` |

关键边界：

- LR/SC 使用 `reservability != RsrvNone`，不区分 `RsrvNonEventual` 和 `RsrvEventual`，源码也有 TODO。
- Atomic 目前不看 AMO op 类型，也没有 `atomic_support` PMA 字段；源码注释说明当前假设所有 memory 支持所有 AMO operation，只要求 readable 且 writable。
- Cache management 的第二句规范语义，即“仅 executable 时是否允许 CB_manage 是 UNSPECIFIED”，当前未建模；源码 TODO 明确只实现 `readable | writable`。
- `CacheAccess(CB_prefetch(_))` 在 instruction 层通常是 no-op on fault，但 `pmaCheck` 仍返回名义 exception，供调用方决定是否忽略。

## 2. res_or_con assert 语义边界与 summary 处理

`res_or_con` 由 `phys_access_check(access, priv, paddr, width, res_or_con)` 传入 `pmaCheck`，见 `mem.sail:172-179`。读路径传的是 `res`，见 `checked_mem_read` 的 `phys_access_check(..., res)`；写路径传的是 `con`，见 `checked_mem_write` 的 `phys_access_check(..., con)`。

实际含义不是 PMA permission bit，而是：

- 普通 load：必须 `res_or_con = false`
- LR：必须 `res_or_con = true`
- SC：必须 `res_or_con = true`
- Atomic：在 AMO read/check 路径必须 `res_or_con = true`
- 普通 Store：当前 Sail 没有 assert；因此 builtin 不能擅自要求 `res_or_con = false`

调用点证据：

- base `LOAD` 使用 `vmem_read(..., Load(Data), false, false, false)`，见 `base_insts.sail:291`
- base `STORE` 使用 `vmem_write(..., Store(Data), false, false, false)`，见 `base_insts.sail:323`
- LR 使用 `LoadReserved(Data)` 且 `res=true`，见 `zalrsc_insts.sail:43`
- SC 使用 `StoreConditional(Data)` 且 `res=true`，见 `zalrsc_insts.sail:71`
- AMO 构造 `Atomic(op, Data, Data)`，后续 `mem_read(..., true)`，见 `zaamo_insts.sail:72` 和 `zaamo_insts.sail:96`

summary 处理建议：

- 对 unsupported / malformed access ctor、symbolic union ctor、未知 cache 子 ctor、未知 prefetch enum：返回 `Ok(None)` 回退 IR，不能把它当作 `canAccess=false`。
- 对带 assert 的 access，如果 assert 条件不是 concrete/provably satisfied，首版应回退 IR。这样由原 `$zsail_assert` 按当前 assertion mode 处理。
- 对 assert 条件 concrete false，首版也应回退 IR 或直接产生等价 `AssertionFailure`；不要返回 PMA access fault，因为 Sail 语义先在 `canAccess` 分支里触发 assert。
- 如果未来要在 summary 内处理 symbolic assert，只能在明确匹配当前 assertion mode 时做：optimistic mode 需要加入同等 SMT assertion 并继续；pessimistic mode 需要在可失败时报告 assertion failure。首版不建议承担这个边界。
- 只有在决定合成返回值之后，缺失必要 exception / option ctor 才应报 `ExecError`；否则应优先 fallback，让 IR 保留原语义。

## 3. accessFault / alignmentFault ctor 映射

映射定义在 `sail-riscv/model/core/mem_type_utils.sail:9-52`。`CacheAccess(CB_prefetch(_))` 的 exception 是名义值：prefetch instruction 本身可在调用层忽略 fault。

| access | `accessFaultFromAccessType` | `alignmentFaultFromAccessType` |
| --- | --- | --- |
| `InstructionFetch()` | `E_Fetch_Access_Fault()` / `zE_Fetch_Access_Fault` | `E_Fetch_Addr_Align()` / `zE_Fetch_Addr_Align` |
| `Load(_)` | `E_Load_Access_Fault()` / `zE_Load_Access_Fault` | `E_Load_Addr_Align()` / `zE_Load_Addr_Align` |
| `LoadReserved(_)` | `E_Load_Access_Fault()` / `zE_Load_Access_Fault` | `E_Load_Addr_Align()` / `zE_Load_Addr_Align` |
| `Store(_)` | `E_SAMO_Access_Fault()` / `zE_SAMO_Access_Fault` | `E_SAMO_Addr_Align()` / `zE_SAMO_Addr_Align` |
| `StoreConditional(_)` | `E_SAMO_Access_Fault()` / `zE_SAMO_Access_Fault` | `E_SAMO_Addr_Align()` / `zE_SAMO_Addr_Align` |
| `Atomic(_)` | `E_SAMO_Access_Fault()` / `zE_SAMO_Access_Fault` | `E_SAMO_Addr_Align()` / `zE_SAMO_Addr_Align` |
| `CacheAccess(CB_manage(_))` | `E_SAMO_Access_Fault()` / `zE_SAMO_Access_Fault` | `E_SAMO_Addr_Align()` / `zE_SAMO_Addr_Align` |
| `CacheAccess(CB_zero())` | `E_SAMO_Access_Fault()` / `zE_SAMO_Access_Fault` | `E_SAMO_Addr_Align()` / `zE_SAMO_Addr_Align` |
| `CacheAccess(CB_prefetch(PREFETCH_R))` | `E_Load_Access_Fault()` / `zE_Load_Access_Fault` | `E_Load_Addr_Align()` / `zE_Load_Addr_Align` |
| `CacheAccess(CB_prefetch(PREFETCH_W))` | `E_SAMO_Access_Fault()` / `zE_SAMO_Access_Fault` | `E_SAMO_Addr_Align()` / `zE_SAMO_Addr_Align` |
| `CacheAccess(CB_prefetch(PREFETCH_I))` | `E_Fetch_Access_Fault()` / `zE_Fetch_Access_Fault` | `E_Fetch_Addr_Align()` / `zE_Fetch_Addr_Align` |

## 4. 首版 pmaCheck builtin 支持范围

面向当前 zSTORE/zLOAD 路径爆炸治理，首版 `pmaCheck` builtin 建议只支持以下 access：

- `Load(Data)`，且 `res_or_con=false`
- `Store(Data)`；当前 zSTORE 为 `res_or_con=false`，但 Sail 对 `Store(_)` 本身没有 assert，因此泛化到 `res_or_con=true` 仍应按 `attributes.writable`，不能擅自 fault

首版应回退 IR 的 access：

- `InstructionFetch()`：公式简单，但当前 zSTORE/zLOAD 不需要；先避免扩大测试面
- `LoadReserved(Data)`：需要精确处理 `assert(res_or_con)` 和 `reservability != RsrvNone`
- `StoreConditional(Data)`：同上，并且 SC 失败路径会先做权限检查再报告 reservation cancelled
- `Atomic(_, Data, Data)`：需要精确处理 `assert(res_or_con)`，且必须保持 `readable & writable`，不能降级成 store-only
- 所有 `CacheAccess(...)`：需要区分 `CB_zero`、`CB_manage`、`PREFETCH_R/W/I`，且 prefetch 的 nominal exception 会被调用层忽略；首版不应混同为普通 load/store
- 任意非 `Data` payload、symbolic/malformed ctor、未知 enum payload

除 access 类型外，首版还应只在这些结构条件满足时命中：

- 能读取并解析当前 concrete `pma_regions` list / `PMA_Region` / `PMA` 字段
- `width` 可作为 concrete byte width 处理
- `paddr` 可构造成支持的 bitvector expression
- option / exception ctor 都能 required lookup
- 当前 IR 中 `get_config_print_pma()` 为 concrete `false`；若未来为 true，summary 会跳过 `print_log` side effect，应回退或明确记录诊断可观察性边界

## 5. zSTORE / zLOAD 的最小安全范围

当前 base 指令只需要普通 Data access：

- `zLOAD`：`Load(Data)`，`aq=false`、`rl=false`、`res=false`
- `zSTORE`：`Store(Data)`，`aq=false`、`rl=false`、`con=false`

因此最小安全 builtin 范围是：

1. 只拦截 `pmaCheck(paddr, width, Load(Data), false)` 和 `pmaCheck(paddr, width, Store(Data), false)`。
2. 保留完整 PMA miss / misaligned fault / canAccess 顺序：
   - PMA miss：按 access 返回 access fault
   - PMA hit 且 misaligned policy fault：优先返回对应 access/alignment fault
   - 否则 `Load(Data)` 用 `attributes.readable`
   - 否则 `Store(Data)` 用 `attributes.writable`
3. 任何 LR/SC/Atomic/Cache/InstructionFetch 先回退 IR，直到分别有专项测试覆盖。

结论：`pmaCheck` 源码覆盖了所有 `MemoryAccessType` ctor；首版 builtin 的风险不在“漏公式”，而在“过早支持复杂 access 时绕过 assert、reservability、cache 子语义或 prefetch 名义 fault”。针对当前 zSTORE/zLOAD，支持普通 `Load(Data)` / `Store(Data)` 已经是最小且安全的范围。
