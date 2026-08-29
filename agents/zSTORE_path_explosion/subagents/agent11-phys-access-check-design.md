# agent11: phys_access_check summary 取舍设计

日期：2026-04-27

范围：只设计 `sail-riscv/model/sys/mem.sail::phys_access_check` 层 summary 的语义和路线，不写生产代码。

已读依据：

- `agents/findings.md`
- `agents/zSTORE_path_explosion/status.md`
- `agents/zSTORE_path_explosion/principles.md`
- `sail-riscv/model/sys/mem.sail`
- `sail-riscv/model/sys/pma.sail`
- `sail-riscv/model/pmp/pmp_control.sail`
- `isla/isla-lib/src/executor.rs` 中现有 PMP summary helper
- `isla/rv64d.ir` 中 `zpmaCheck` / `zphys_access_check` 生成形态

## 结论摘要

推荐路线是 **pmaCheck first、phys_access_check later**。

理由：

1. 当前 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 后，PMP 已不是热点；profile 热点转到 `matching_pma_bits_range`、MMIO/CLINT 和 `phys_access_check` 的 option 合并层。
2. `pmaCheck` 是更小的等价边界，能先解决 `matching_pma_bits_range` / PMA 属性判断的主要 fork，并能单独验证 PMA 错误语义。
3. `phys_access_check` summary 可以进一步消掉 PMP/PMA 两个 `option(ExceptionType)` 的四象限 match，但它必须组合 PMP summary 与 PMA summary 的 fault predicate，证据需求更高。
4. 直接先做 `phys_access_check` 会把 PMP/PMA/MMIO 前置热点归因混在一起，容易隐藏 `pmaCheck` 本身的语义缺口。

因此：先实现并验证 `pmaCheck` exact summary；若 profile 中 `phys_access_check` 的 option merge 仍是稳定热点，再把 `pmaCheck` 的内部结果抽成可复用 predicate，做 `phys_access_check` 层合成。

## 1. phys_access_check 合并 PMP/PMA 错误的精确语义

源码语义在 `mem.sail` 中是：

```sail
let pmpError = pmpCheck(paddr, width, access, priv);
let pmaError = pmaCheck(paddr, width, access, res_or_con);
match (pmpError, pmaError) {
  (None(), None())     => None(),
  (Some(e), None())    => Some(e),
  (None(), Some(e))    => Some(e),
  (Some(e0), Some(e1)) => Some(highestPriorityAlignmentOrAccessFault(e0, e1)),
}
```

关键点：

- `pmpCheck` 和 `pmaCheck` 都会执行；这不是 short-circuit 语义。
- `pmpCheck` 只产生 `accessFaultFromAccessType(access)` 或 `None()`。
- `pmaCheck` 可能产生：
  - PMA 未匹配：`accessFaultFromAccessType(access)`
  - PMA misaligned policy 为 `AccessFault` 且地址不对齐：`accessFaultFromAccessType(access)`
  - PMA misaligned policy 为 `AlignmentFault` 且地址不对齐：`alignmentFaultFromAccessType(access)`
  - 权限/属性不允许：`accessFaultFromAccessType(access)`
  - 否则 `None()`
- 当 PMP/PMA 同时报错时，`highestPriorityAlignmentOrAccessFault(e0, e1)` 决定最终异常。

在当前 `phys_access_check` 调用形态下，可以把结果等价化为三个条件：

```text
pmp_access_fault : PMP 拒绝访问
pma_access_fault : PMA 未匹配、PMA AccessFault misaligned、或 PMA canAccess=false
pma_align_fault  : PMA AlignmentFault misaligned

final_access_fault = pmp_access_fault || pma_access_fault
final_align_fault  = !final_access_fault && pma_align_fault
final_none         = !final_access_fault && !pma_align_fault
```

最终 `ExceptionType` 是：

- `final_access_fault` 为真：`accessFaultFromAccessType(access)`
- 否则 `final_align_fault` 为真：`alignmentFaultFromAccessType(access)`
- 否则：`None()`

这个化简成立的前提是：PMP 子结果只可能是 access fault，PMA 子结果只可能是 access fault / alignment fault / none，并且两边使用同一个 `access` 入参。若未来把该 helper 泛化为合并任意两个 `option(ExceptionType)`，不能使用这个简化，必须按 `highestPriorityAlignmentOrAccessFault(l, r)` 的通用规则处理。

## 2. 是否应在 PMP summary 已有前提下 summary phys_access_check 而不是 pmaCheck

不建议第一步直接 summary `phys_access_check`，建议先 summary `pmaCheck`。

证据：

- `agents/findings.md` 记录的 `pmpCheck` exact summary profile 已显示 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 后 PMP 不再是热点。
- 最新 profile 中剩余热点排序包含：
  - `matching_pma_bits_range=150`
  - `get_X=120`
  - `clint_store=80`
  - `phys_access_check=76`
  - `clint_load=65`
- `matching_pma_bits_range` 和 `pmaCheck` 是 PMA 层内部实现分支；`phys_access_check` 的 76 次更像 PMP/PMA 两个 symbolic option 在 IR 中做四象限 match 产生的合并层分支。

取舍：

- `pmaCheck` summary first：
  - 优点：边界小；能独立验证 PMA region 匹配、misaligned policy、canAccess、access/alignment fault；失败时可回退 IR。
  - 缺点：即使 `pmaCheck` 返回 symbolic option，`phys_access_check` 的外层 match 仍可能继续 fork。
- `phys_access_check` summary first：
  - 优点：理论上能一次性消掉 `pmpCheck`/`pmaCheck` 调用后的 option merge fork。
  - 缺点：必须同时复用/内联 PMP exact predicate 和 PMA exact predicate；验证范围更大；一旦结果有偏差，难以判断是 PMP、PMA 还是 merge priority 出错。

因此当前不应把 `phys_access_check` 作为第一落点。更稳的做法是先把 `pmaCheck` 做成返回结构化 predicate 的 exact summary，然后在第二步用这些 predicate 合成 `phys_access_check`。

## 3. highestPriorityAlignmentOrAccessFault 的优先级保持方式

源码优先级：

```sail
access fault    => 1
alignment fault => 0

if priority(l) > priority(r) then l else r
```

必须保留两个细节：

1. access fault 优先级高于 alignment fault。
2. 同优先级时返回右操作数 `r`，因为比较是 `>`，不是 `>=`。

通用 symbolic 组合可写成：

```text
l_is_access = l in {E_Fetch_Access_Fault, E_Load_Access_Fault, E_SAMO_Access_Fault}
r_is_access = r in {E_Fetch_Access_Fault, E_Load_Access_Fault, E_SAMO_Access_Fault}
choose_l = l_is_access && !r_is_access
result = ite(choose_l, l, r)
```

在当前 `phys_access_check` 中，由于 `pmpError` 只可能是 access fault，`pmaError` 只可能是 access/alignment fault：

- PMP access + PMA alignment：返回 PMP access fault。
- PMP access + PMA access：按 tie 规则返回 PMA access fault；但两者由同一 `access` 产生，构造器相同，观测上等价。
- PMP none + PMA alignment/access：返回 PMA。
- PMP/PMA 都 none：返回 none。

若 summary 中出现不属于这六个 alignment/access fault ctor 的 `ExceptionType`，应回退 IR 或报错；不能静默套用该 priority。

## 4. option(ExceptionType) symbolic ctor 构造建议

现有 `pmpCheck` summary 的 `option_exception_from_fault_cond(...)` 只支持 “一个 fault 条件 + 一个 concrete fault ctor”：

```text
outer discrim = ite(fault_cond, Some, None)
Some payload  = concrete ExceptionType ctor
None payload  = Unit
```

`pmaCheck` / `phys_access_check` 需要更一般的构造：外层 `option` 是 symbolic ctor，内层 `ExceptionType` 也可能是 symbolic ctor。

建议构造方式：

1. 所有 ctor 必须用 required lookup：
   - `zSomezIUExceptionTypezK`
   - `zNonezIUExceptionTypezK`
   - `zE_Fetch_Access_Fault`
   - `zE_Load_Access_Fault`
   - `zE_SAMO_Access_Fault`
   - `zE_Fetch_Addr_Align`
   - `zE_Load_Addr_Align`
   - `zE_SAMO_Addr_Align`
2. 外层 option discriminant 用 `solver.define_const(Ite(...))`，不要只 `declare_const + assert(member in set)`；否则会丢失条件与 ctor 的相关性。
3. 当结果只有一个 fault ctor 时，沿用现有 helper：

```text
option = SymbolicCtor(
  discrim = ite(fault_cond, Some, None),
  possibilities = {
    Some -> Ctor(access_fault_ctor, Unit),
    None -> Unit,
  }
)
```

4. 当结果可能是 access fault 或 alignment fault 时：

```text
has_fault = access_fault_cond || align_fault_cond
exception_discrim =
  ite(access_fault_cond, access_fault_ctor, align_fault_ctor)

exception = SymbolicCtor(
  discrim = exception_discrim,
  possibilities = {
    access_fault_ctor -> Unit,
    align_fault_ctor  -> Unit,
  }
)

option = SymbolicCtor(
  discrim = ite(has_fault, Some, None),
  possibilities = {
    Some -> exception,
    None -> Unit,
  }
)
```

5. 若 access/alignment fault ctor 相同路径被多次来源触发，应先在 SMT 条件上合并，不要为同一个 ctor 构造多个不相关 payload。
6. 对当前 `phys_access_check` 可直接构造：

```text
access_cond = pmp_access_fault || pma_access_fault
align_cond  = !access_cond && pma_align_fault
has_fault   = access_cond || align_cond

exception_discrim = ite(access_cond, access_fault_ctor, alignment_fault_ctor)
option_discrim    = ite(has_fault, Some, None)
```

7. `Some` payload 中的 `ExceptionType` symbolic ctor 只需要列出可达 ctor；不要把全部 `ExceptionType` ctor 放入 possibilities，否则会扩大后续 match 的可行空间。
8. 如果 `access` 是 unsupported 或 symbolic `MemoryAccessType`，不能猜 fault ctor，应回退 IR。

## 5. 推荐路线与证据需求

推荐路线：**pmaCheck first、phys_access_check later**。

### Phase A: pmaCheck exact summary

目标：把 PMA region scan、misaligned policy、canAccess 判断下沉到 SMT，返回精确 `option(ExceptionType)`。

支持边界建议：

- `pma_regions` 必须能读成 concrete list/vector 形态的 `PMA_Region`。
- `paddr` 支持 symbolic bitvector。
- `width` 必须是 concrete positive width，且能转为和 PMA range 公式一致的 bitvector/int。
- `access` 必须是 concrete ctor；`CacheAccess(CB_prefetch(_))` 的 payload 也必须 concrete。
- `res_or_con` 必须满足 Sail 中对应 assert：
  - `Load(_)` 需要 `res_or_con=false`
  - `LoadReserved(_)` / `StoreConditional(_)` / `Atomic(_)` 需要 `res_or_con=true`
  - 不满足时回退 IR 或显式报错，不要忽略 assert。
- `get_config_print_pma()` 为 true 且 failure 可发生时，应优先回退 IR，除非 summary 同步实现等价日志副作用。

需要证据：

- 单函数 `pmaCheck` wrapper：builtin on/off 的返回值可满足性一致。
- 覆盖 PMA 未匹配、read/write/execute deny、misaligned `AccessFault`、misaligned `AlignmentFault`、success。
- 覆盖 `Load`、`Store`、`InstructionFetch`，再扩展 LR/SC/Atomic/CacheAccess。
- `zSTORE` / `zLOAD` 在 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 下 profile 对照：
  - `matching_pma_bits_range` 是否下降或消失。
  - `phys_access_check` 是否成为新的稳定热点。
  - `ret_val`、memory event count、solver sat/unsat 与 baseline 对齐。

### Phase B: phys_access_check summary

触发条件：Phase A 后 `phys_access_check` 仍然在 profile 中贡献明显 fork，且错误类型/ret_val 对照已经稳定。

目标：把 `pmpCheck` exact predicate 和 `pmaCheck` exact predicate 合成一个 `option(ExceptionType)` symbolic ctor，消掉 IR 中 `(pmpError, pmaError)` 的四象限 match。

支持边界建议：

- 只在 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 且 PMP exact subformula 可构造时启用。
- PMA subformula 必须复用 Phase A 的 exact predicate，不要重新写一个近似 PMA。
- 任何 PMP/PMA 子公式不支持时，整个 `phys_access_check` 回退 IR，让现有 `pmpCheck` / `pmaCheck` 入口继续处理。
- 必须保留 PMP/PMA 都会执行这一点；不能因为 PMP 已经 fault 就跳过 PMA 的可观察行为。若 PMA summary 不能保留 `print_log` 等可观察行为，则对应配置下回退 IR。

需要证据：

- 和 Phase A 的结果做 A/B/C：
  - baseline IR
  - `pmaCheck` summary only
  - `pmaCheck + phys_access_check` summary
- 对比 `zphys_access_check` fork 是否显著下降。
- 对比同一路径上的最终 `Memory_Exception` ctor：
  - PMP access + PMA none
  - PMP none + PMA access
  - PMP none + PMA alignment
  - PMP access + PMA alignment，必须返回 access fault
  - PMP access + PMA access，必须仍为 access fault
- 对比 `checked_mem_read` / `checked_mem_write` 后续 MMIO/RAM 分界和 memory events，确认 summary 只改变检查层路径形态，不改变实际访存行为。

## 额外注意

- 不建议 summary `matching_pma_bits_range` 的 `option(PMA_Region)` 作为主路线。它返回结构体 option，后续 `pmaCheck` 仍会对 `Some/None`、属性和权限做多层 match；收益可能有限，且 symbolic `PMA_Region` payload 更难保持精确。
- `phys_access_check` summary 不应隐式引入 plain-RAM、PMP-off、aligned、non-MMIO 等假设；这些只能来自显式 env/init 约束。
- MMIO/CLINT 热点属于 `phys_access_check` 之后的分界，不能在这个 summary 中顺手吞掉。PMA 允许访问不等于最终一定走 RAM，后续仍必须由 `within_mmio_readable/writable` 与 `mmio_read/write` 决定。
