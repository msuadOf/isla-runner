# agent04: pmaCheck exact summary design

日期：2026-04-27

目标：设计 Isla/Rust 侧 `pmaCheck` exact summary 的 SMT 公式。只总结设计，不写生产代码。设计依据是 `sail-riscv/model/sys/pma.sail`、`sail-riscv/model/sys/mem.sail` 和当前 `isla/isla-lib/src/executor.rs` 中 PMP exact summary 的风格。

## 结论

优先 summary `pmaCheck(paddr, width, access, res_or_con) -> option(ExceptionType)`，不要优先 summary `matching_pma_bits_range(...) -> option(PMA_Region)`。

原因是 `pmaCheck` 的可观察返回已经收敛到 `None()` 或少数几类 `ExceptionType`，可以用布尔谓词和一个符号 ctor payload 表达；而 `matching_pma_bits_range` 需要返回 `Some(PMA_Region)`，符号地址跨多个 region 时会产生多个 struct payload 选择，随后 `pmaCheck` 仍要继续拆 `attributes`、`misaligned_fault`、权限字段和 reservability，容易把分支推迟而不是消掉。

建议第一版 gate 为显式开启，例如 `ISLA_RISCV_BUILTIN_PMA_CHECK=1`。等回归覆盖 PMA no-match、ROM/RAM/CLINT、misaligned 和 CBO/prefetch 后再考虑默认策略。

## 支持边界

`pma_regions`：

- 从 `zpma_regions` register 读取，保持现有 register 读事件风格，类似 `pmpCheck` exact summary 对 `pmpcfg_n` / `pmpaddr_n` 的处理。
- 要求 list shape concrete、有限、按 Sail list 顺序遍历。不能依赖 region 已排序或不重叠；即使配置有重叠，也必须按 first-match 语义处理。
- 每个 entry 必须是 `PMA_Region` struct，并有 `zbase`、`zsizze`、`zattributes`。`zbase` / `zsizze` 要能转成 64-bit BV 表达式。`attributes` 必须包含 `zexecutable`、`zreadable`、`zwritable`、`zmisaligned_fault`、`zreservability`、`zsupports_cbo_zzero`。
- 第一版可以要求 attributes 为 concrete bool/enum；如果字段本身已经是 SMT bool，也可以自然接入公式。enum 字段至少要能比较 `zNoFault` / `zAccessFault` / `zAlignmentFault` 和 `zRsrvNone`。

`paddr`：

- 要求 64-bit bitvector，允许 concrete 或 symbolic。
- 其它宽度、非 bitvector、无法取 SMT 表达式时回退 IR。

`width`：

- 主支持路径：concrete positive int，范围满足 Sail 类型 `0 < width <= max_mem_access`。当前 `pmaCheck` IR 签名是 `%i64`，这应覆盖普通 load/store/AMO/CBO 调用。
- 将 concrete width 转成 BV64 作为 `range_subset` 的 `size`。
- BV width 扩展路径：如果调用点已经给出 BV width，则只支持可零扩展到 BV64 且有显式非零/范围前提的情况。否则不要对除零 modulo 或非法 width 做近似，直接回退 IR。
- 不支持无法转成 BV64 的 symbolic integer width。

`access`：

- 支持 concrete union ctor：
  - `InstructionFetch()`
  - `Load(_)`
  - `Store(_)`
  - `LoadReserved(_)`
  - `StoreConditional(_)`
  - `Atomic(_, _, _)`
  - `CacheAccess(CB_zero())`
  - `CacheAccess(CB_manage(_))`
  - `CacheAccess(CB_prefetch(PREFETCH_R|PREFETCH_W|PREFETCH_I))`
- `Load` / `Store` / LR / SC / Atomic 的 payload 不影响 PMA 公式。
- unsupported ctor、symbolic ctor、unknown cache op、unknown prefetch enum 回退 IR。

`res_or_con`：

- 支持 concrete bool。
- 对 Sail 中有 assertion 的 ctor 保持边界：
  - `Load(_)` 要求 `res_or_con == false`，否则回退 IR，让原 `$zsail_assert` 处理。
  - `LoadReserved(_)`、`StoreConditional(_)`、`Atomic(_,_,_)` 要求 `res_or_con == true`，否则回退 IR。
  - `Store(_)` 当前 Sail TODO 没有 `assert(not(res_or_con))`，公式中不使用该参数。
  - `InstructionFetch()` 和 `CacheAccess(_)` 公式中不使用该参数。
- 对 symbolic `res_or_con`，只有在 access ctor 完全不依赖该 assertion 时才可继续；否则回退 IR。

其它边界：

- `zget_config_print_pma(())` 在当前 IR 中固定为 `false`。如果未来配置允许 PMA failure log 为 true，summary 会跳过 `print_log`，应回退 IR 或显式记录诊断可观察性差异。
- summary 只覆盖 `pmaCheck`，不产生 memory event，不做 RAM/MMIO 分派。`pmaCheck` 返回 `None()` 后仍由 `checked_mem_read/write` 继续执行 `within_mmio_*`、`mmio_read/write` 或 `read_ram/write_ram`。

## range_subset 与 first-match

对每个 PMA region `i`，令：

```text
base_i = region[i].base      : BV64
size_i = region[i].size      : BV64
addr   = paddr               : BV64
w      = width as BV64       : BV64
```

必须复用 Sail `range_subset` 的 wrap-around 语义，不改成普通整数区间：

```text
a_end_i   = (addr + w) - base_i
b_end_i   = (base_i + size_i) - base_i
a_begin_i = addr - base_i

match_i = bvule(a_begin_i, b_end_i)
        & bvule(a_end_i,   b_end_i)
        & bvule(a_begin_i, a_end_i)
```

first-match 通过 `no_match_so_far` 表示：

```text
no_match_so_far_0 = true
first_i           = no_match_so_far_i & match_i
no_match_so_far_{i+1} = no_match_so_far_i & not(match_i)
no_pma_match      = no_match_so_far_N
```

所有 per-region fault 都必须乘上 `first_i`，不能直接用 `match_i`。这保证重叠或未排序 PMA list 下仍等价于 Sail 的递归 first-match。

## misaligned_fault 编码

Sail 语义：

```sail
let misaligned = not(is_aligned_addr(paddr, width));
match attributes.misaligned_fault {
  AccessFault if misaligned => return Some(accessFaultFromAccessType(access)),
  AlignmentFault if misaligned => return Some(alignmentFaultFromAccessType(access)),
  _ => check canAccess
}
```

SMT 中：

```text
misaligned = bvurem(addr, w) != 0
```

如果 `w` 是 concrete power-of-two，可以优化成低位 mask 非零；但通用公式应保留 `bvurem`，因为 Sail 是 `unsigned(addr) % width == 0`，`width` 类型并不限于 power-of-two。

对每个 region：

```text
mf_access_i = (region[i].attributes.misaligned_fault == AccessFault)
mf_align_i  = (region[i].attributes.misaligned_fault == AlignmentFault)

alignment_fault_i =
  first_i & mf_align_i & misaligned

access_fault_i =
  first_i &
  (
    (mf_access_i & misaligned)
    | (not(misaligned & (mf_access_i | mf_align_i)) & not(canAccess_i))
  )
```

No-match 也是 access fault：

```text
access_fault_cond =
  no_pma_match | OR_i(access_fault_i)

alignment_fault_cond =
  OR_i(alignment_fault_i)

fault_cond =
  access_fault_cond | alignment_fault_cond
```

`access_fault_cond` 与 `alignment_fault_cond` 在 first-match 约束下应互斥。构造返回值时：

```text
access_exc = accessFaultFromAccessType(access)
align_exc  = alignmentFaultFromAccessType(access)

exception_payload =
  ite(alignment_fault_cond, align_exc, access_exc)

result =
  ite(fault_cond, Some(exception_payload), None())
```

Rust 表达上应构造 `option(ExceptionType)` 的 symbolic ctor：外层 ctor discriminator 是 `ite(fault_cond, Some, None)`；`Some` payload 是 `ExceptionType` symbolic ctor，discriminator 是 `ite(alignment_fault_cond, align_ctor, access_ctor)`。

## ExceptionType ctor 选择

access fault:

```text
InstructionFetch()          -> E_Fetch_Access_Fault()
Load(_)                     -> E_Load_Access_Fault()
LoadReserved(_)             -> E_Load_Access_Fault()
Store(_)                    -> E_SAMO_Access_Fault()
StoreConditional(_)         -> E_SAMO_Access_Fault()
Atomic(_,_,_)               -> E_SAMO_Access_Fault()
CacheAccess(CB_manage(_))   -> E_SAMO_Access_Fault()
CacheAccess(CB_zero())      -> E_SAMO_Access_Fault()
CacheAccess(CB_prefetch(R)) -> E_Load_Access_Fault()
CacheAccess(CB_prefetch(W)) -> E_SAMO_Access_Fault()
CacheAccess(CB_prefetch(I)) -> E_Fetch_Access_Fault()
```

alignment fault:

```text
InstructionFetch()          -> E_Fetch_Addr_Align()
Load(_)                     -> E_Load_Addr_Align()
LoadReserved(_)             -> E_Load_Addr_Align()
Store(_)                    -> E_SAMO_Addr_Align()
StoreConditional(_)         -> E_SAMO_Addr_Align()
Atomic(_,_,_)               -> E_SAMO_Addr_Align()
CacheAccess(CB_manage(_))   -> E_SAMO_Addr_Align()
CacheAccess(CB_zero())      -> E_SAMO_Addr_Align()
CacheAccess(CB_prefetch(R)) -> E_Load_Addr_Align()
CacheAccess(CB_prefetch(W)) -> E_SAMO_Addr_Align()
CacheAccess(CB_prefetch(I)) -> E_Fetch_Addr_Align()
```

Prefetch 的异常是 nominal exception，保持 `mem_type_utils.sail` 的返回，不在 `pmaCheck` 层改变调用方对 prefetch 的处理。

## canAccess 公式

令 region attributes：

```text
X     = executable
R     = readable
W     = writable
RSRV  = reservability != RsrvNone
CBOZ  = supports_cbo_zero
```

则：

```text
InstructionFetch()          => X
Load(_)                     => R
Store(_)                    => W
LoadReserved(_)             => R & RSRV
StoreConditional(_)         => W & RSRV
Atomic(_,_,_)               => R & W
CacheAccess(CB_zero())      => W & CBOZ
CacheAccess(CB_manage(_))   => R | W
CacheAccess(CB_prefetch(R)) => R
CacheAccess(CB_prefetch(W)) => W
CacheAccess(CB_prefetch(I)) => X
```

这些公式只决定 PMA 是否返回 access fault；它们不决定 RAM/MMIO 的后续 dispatch，也不替代 CBO 指令自己的其它语义。

## fallback 条件

任一条件不满足时，builtin 返回 `Ok(None)` 回退 IR：

- env gate 未开启。
- 参数个数不匹配时直接 `ExecError::Type`。
- 无法读取 `zpma_regions`，或读取值不是 concrete finite list。
- region struct 缺字段、字段类型不匹配、`base/size` 不是 BV64。
- `paddr` 不是 BV64。
- `width` 不是 supported concrete int，也不是有显式合法域前提的 BV width。
- `width == 0`、`width > max_mem_access`、或 BV width 不能排除 zero divisor。
- access ctor / cache op / prefetch enum 不支持。
- `res_or_con` 与 Sail assertion 前提冲突，或该 assertion 依赖 symbolic bool。
- 需要的 `Some/None`、ExceptionType ctor、misaligned/reservability enum symbol 缺失。
- `get_config_print_pma()` 不能证明为 false，且需要保留 PMA failure log。

## fail-closed 行为

语义内的 fail-closed：

- 没有任何 PMA region first-match 时，公式返回 `Some(accessFaultFromAccessType(access))`，与 Sail `None() => Some(access fault)` 一致。
- region first-match 后，若 misaligned policy 是 `AccessFault` 或 `AlignmentFault`，优先返回对应 fault，不继续用权限结果覆盖它。
- `canAccess_i == false` 时返回 access fault；不会把 unknown/unsupported 当作 success。

实现边界上的 fail-closed：

- 不支持的情况回退 IR，而不是返回 `None()` 语义结果。
- 如果 required ctor/symbol lookup 缺失，暴露 `ExecError`，不要静默 intern 新 symbol。
- 不得隐式假设 PMA 全允许、普通 RAM、non-MMIO 或 aligned。
- 不得在 `pmaCheck` summary 中提前产生 memory event 或绕过 `within_mmio_*` / MMIO callback 分界。

## 为什么比 matching_pma_bits_range summary 稳

1. 返回域更小：`pmaCheck` 只需要 `None`、access fault、alignment fault。`matching_pma_bits_range` 要返回 `option(PMA_Region)`，`Some` payload 是整块 region struct。
2. 避免符号 struct payload：多个可匹配 region 会使 `Some(PMA_Region)` 的每个字段都变成选择表达式，后续仍要拆 `attributes` 做权限和 misaligned 判断。
3. first-match 更直接：`no_match_so_far` 可以直接约束 fault 条件，不需要先构造一个“被选中的 region”再从中投影字段。
4. 更贴近上层可观察语义：`phys_access_check` 消费的是 `option(ExceptionType)`；`matching_pma_bits_range` 是 `pmaCheck` 内部 helper。
5. 更容易 fail closed：unsupported access、width、res_or_con assertion、print_log 可在 `pmaCheck` 边界统一回退 IR。helper summary 一旦返回了错误 region payload，后续错误更隐蔽。
6. 不干扰 MMIO/RAM 分界：`pmaCheck` 返回 `None()` 只表示 PMA permit，后续 `checked_mem_read/write` 仍决定 MMIO callback 或 RAM memory event。

## 建议验证矩阵

- 当前 `rv64d.ir` concrete PMA list 下，`paddr` symbolic、width concrete 4，覆盖 no-match、ROM、CLINT、RAM 三类地址。
- CLINT region `misaligned_fault = AlignmentFault`：concrete/symbolic misaligned store/load 分别得到 `E_SAMO_Addr_Align` / `E_Load_Addr_Align`。
- RAM region `NoFault` 且 full permission：返回 `None()`，上层仍继续产生正常 RAM/MMIO 行为。
- ROM-like region `writable=false`：store 返回 `E_SAMO_Access_Fault`，load/fetch 按 attributes 返回。
- LR/SC：`reservability == RsrvNone` 时 access fault；`RsrvEventual` 时按 R/W 允许。
- CacheAccess：`CB_zero` 检查 `W & supports_cbo_zero`；`CB_manage` 检查 `R | W`；prefetch R/W/I 分别走 R/W/X 和 nominal exception ctor。
- 与 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 组合跑 zSTORE/zLOAD profile，确认 PMP 不回到热点，PMA fork 减少，且 `within_mmio_*` / CLINT 热点仍按后续阶段暴露。
