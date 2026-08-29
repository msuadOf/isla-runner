# agent12: executor helper audit for PMA summary

日期：2026-04-27

范围：审计 `isla/.worktrees/zstore-pma-mmio/isla-lib/src/executor.rs` 里已有 helper 是否足够构造 PMA / PMA option / enum / struct summary。已阅读：

- `agents/findings.md`
- `agents/zSTORE_path_explosion/status.md`
- `isla/.worktrees/zstore-pma-mmio/isla-lib/src/executor.rs`
- `isla/.worktrees/zstore-pma-mmio/isla-lib/src/ir.rs`
- `isla/.worktrees/zstore-pma-mmio/isla-lib/src/smt.rs`
- `isla/.worktrees/zstore-pma-mmio/isla-lib/src/primop_util.rs`
- PMA 相关 IR / Sail 定义：`rv64d.ir`、`sail-riscv/model/sys/pma.sail`、`sail-riscv/model/sys/mem.sail`

只写本审计文件，未修改生产 Rust。`agents/overview.md` 在当前仓库不存在。

## 结论

现有 helper 足够支撑 PMA summary 的一部分基础构造：required symbol lookup、enum SMT 常量、bitvector 提取、读取寄存器、固定 payload 的 `option(ExceptionType)`、access-fault 构造都已经有可复用实现。

但它们还不足以直接构造完整 PMA / `option(PMA_Region)` / `pmaCheck` exact summary。主要缺口是：

- PMA region 列表是 `Val::List`，现有 `vector_entry` 只覆盖 PMP 的 `Val::Vector`。
- 缺少通用 struct field typed accessor，当前只有 `pmpcfg_a_bits` / `pmpcfg_bit_is_set` 这种针对 `zbits` 的局部字段读取。
- 缺少 enum-valued field 转 SMT 表达式的 helper，尤其 `zmisaligned_fault`、`zreservability`。
- 缺少 `alignmentFaultFromAccessType` 对应 helper；`pmaCheck` 的 misaligned `AlignmentFault` 分支不能只复用 access fault。
- `option_exception_from_fault_cond` 只适合 `Some(fixed_exception)` vs `None()`，不适合一个 summary 内按条件选择 access fault / alignment fault / None 的多 payload 场景。
- 直接 summary `matching_pma_bits_range -> option(PMA_Region)` 需要在多个 `Some(PMA_Region)` payload 之间构造 symbolic struct selection，现有 `primop_util::build_ite` 对 `Some(struct)` payload 不够直接可靠。

建议第一阶段优先做 `pmaCheck` 层 summary，避免把 `matching_pma_bits_range` 作为独立外部 summary 暴露 `option(PMA_Region)` payload。

## 1. 已有可复用 helper

`lookup_required_symbol` / `lookup_required_vmem_symbol`

- 位置：`executor.rs:1887` 附近。
- 作用：按 IR symbol 名查 `Name`，缺失时返回 `ExecError`，不会静默 intern 新 symbol。
- PMA 可直接复用：查 `zpma_regions`、`zbase`、`zsizze`、`zattributes`、`zmisaligned_fault`、`zreservability`、`zSomezIUExceptionTypezK` 等。

`enum_symbol_exp`

- 位置：`executor.rs:1788` 附近。
- 作用：通过 `type_info.enum_members` 找 enum 所属 sort 和 member index，并调用 `solver.get_enum(enum_name, enum_size)` 注册 enum sort，返回 `SmtExp::Enum(...)`。
- PMA 可直接复用：构造 `zAccessFault`、`zAlignmentFault`、`zNoFault`、`zRsrvNone`、`zRsrvNonEventual`、`zRsrvEventual` 等 enum 常量。

`option_exception_from_fault_cond`

- 位置：`executor.rs:1613` 附近。
- 作用：构造 `fault_cond ? Some(fault) : None()` 的 `Val::SymbolicCtor`。
- PMA 可部分复用：适合 `canAccess` 失败这种固定 access-fault payload。不能直接表达 `misaligned_fault == AccessFault` 时 Some(access fault)、`misaligned_fault == AlignmentFault` 时 Some(alignment fault)、否则继续权限检查的多 payload 选择。

`read_register_cloned`

- 位置：`executor.rs:1543` 附近。
- 作用：从 frame register state 读取寄存器并补 `Event::ReadReg`。
- PMA 可直接复用：读取 `zpma_regions`，并保留 register read event。

`vector_entry`

- 位置：`executor.rs:1557` 附近。
- 作用：从 `Val::Vector` 按 index clone entry。
- PMA 不能直接复用：`pma_regions` 的 IR type 是 `%list(%struct zPMA_Region)`，runtime value 对应 `Val::List`，需要新增 list helper。

`access_fault_from_access_type_value`

- 位置：`executor.rs:1564` 附近。
- 作用：按 `MemoryAccessType` ctor 构造 `E_Fetch_Access_Fault` / `E_Load_Access_Fault` / `E_SAMO_Access_Fault`，含 cache access 的 prefetch R/W/I 处理。
- PMA 可直接复用：无匹配 region、权限失败、misaligned `AccessFault` 都需要它。

`bitvector_exp_and_width` / `bitvector_width`

- 位置：`executor.rs:1649` 附近。
- 作用：把 concrete/symbolic bitvector 转成 `SmtExp` 并带宽度。
- PMA 可直接复用：`paddr`、`width` 转 bits、region `zbase` / `zsizze`、range-subset 子式都需要。

`range_subset_builtin`

- 位置：`executor.rs:1072` 附近。
- 作用：已有正确的 wrap-around bitvector 公式。
- PMA 可借鉴但不够好用：当前返回 `Option<Val<B>>`，`pmaCheck` 内部更需要可组合的 `range_subset_exp(...) -> SmtExp<Sym>`。

## 2. PMA_Region / PMA struct 字段读取需要的新 helper

IR 中 struct 形状：

- `zPMA`：`zcacheable`、`zcoherent`、`zexecutable`、`zmisaligned_fault`、`zread_idempotent`、`zreadable`、`zreservability`、`zsupports_cbo_zzero`、`zwritable`、`zwrite_idempotent`。
- `zPMA_Region`：`zattributes`、`zbase`、`zinclude_in_device_tree`、`zsizze`。注意 Sail 的 `size` 在 IR 中 mangled 为 `zsizze`。

`pmaCheck` 第一版实际会用到：

- Region：`zbase`、`zsizze`、`zattributes`。
- Attributes：`zmisaligned_fault`、`zexecutable`、`zreadable`、`zwritable`、`zreservability`、`zsupports_cbo_zzero`。
- `zcacheable`、`zcoherent`、`zread_idempotent`、`zwrite_idempotent`、`zinclude_in_device_tree` 当前不参与 `pmaCheck`，但如果构造 `option(PMA_Region)` summary，必须保留原 struct payload，不能丢字段重建成不完整 region。

建议新增 typed field helper，而不是在 PMA summary 里反复手写 HashMap lookup：

```rust
fn struct_field_cloned<B: BV>(
    value: &Val<B>,
    field: &str,
    shared_state: &SharedState<B>,
    info: SourceLoc,
) -> Result<Option<Val<B>>, ExecError>;

fn bool_exp<B: BV>(
    value: &Val<B>,
    info: SourceLoc,
) -> Result<Option<SmtExp<Sym>>, ExecError>;

fn enum_value_exp<B: BV>(
    value: &Val<B>,
    info: SourceLoc,
) -> Result<Option<SmtExp<Sym>>, ExecError>;

fn list_entry<B: BV>(value: &Val<B>, index: usize) -> Option<Val<B>>;
```

然后再包一层 PMA 专用解析：

```rust
struct PmaRegionParts<B> {
    base: Val<B>,
    size: Val<B>,
    attributes: Val<B>,
    include_in_device_tree: Val<B>,
}

fn pma_region_parts<B: BV>(
    region: &Val<B>,
    shared_state: &SharedState<B>,
    info: SourceLoc,
) -> Result<Option<PmaRegionParts<B>>, ExecError>;

struct PmaAttrParts<B> {
    executable: Val<B>,
    readable: Val<B>,
    writable: Val<B>,
    misaligned_fault: Val<B>,
    reservability: Val<B>,
    supports_cbo_zero: Val<B>,
}

fn pma_attr_parts<B: BV>(
    attrs: &Val<B>,
    shared_state: &SharedState<B>,
    info: SourceLoc,
) -> Result<Option<PmaAttrParts<B>>, ExecError>;
```

`pma_attr_parts` 可以只返回 `pmaCheck` 需要的字段；如果后续要做 `option(PMA_Region)` summary，另加完整 field-wise struct merge helper。

## 3. misaligned_fault / Reservability enum 比较的 SmtExp 表示

不要把 enum member 当 union constructor `Name::to_smt()` 比较。`Name::to_smt()` 是 `SymbolicCtor` 判别用的 32-bit constructor id；Sail enum 应使用 enum sort。

推荐模式：

```rust
let Some(fault) = enum_value_exp(misaligned_fault_value, info)? else {
    return Ok(None);
};
let access_fault = enum_symbol_exp("zAccessFault", shared_state, solver, info)?;
let alignment_fault = enum_symbol_exp("zAlignmentFault", shared_state, solver, info)?;

let is_access_fault = SmtExp::Eq(Box::new(fault.clone()), Box::new(access_fault));
let is_alignment_fault = SmtExp::Eq(Box::new(fault), Box::new(alignment_fault));
```

`Reservability != RsrvNone`：

```rust
let Some(reservability) = enum_value_exp(reservability_value, info)? else {
    return Ok(None);
};
let rsrv_none = enum_symbol_exp("zRsrvNone", shared_state, solver, info)?;
let has_reservation = SmtExp::Not(Box::new(SmtExp::Eq(
    Box::new(reservability),
    Box::new(rsrv_none),
)));
```

`enum_value_exp` 应允许：

- `Val::Enum(member)`：走 `smt_value(value, info)` 得到 `SmtExp::Enum(member)`。
- `Val::Symbolic(sym)`：走 `smt_value(value, info)` 得到 `SmtExp::Var(sym)`，前提是该 symbol 原本声明为对应 enum sort。

如果字段既不是 concrete enum 也不是 symbolic enum，应 fail closed，返回 `Ok(None)` 让 summary 回退 IR。

## 4. 构造 SymbolicCtor option(ExceptionType) 的注意事项

`option(ExceptionType)` 是 union，不是 enum。外层 `Val::SymbolicCtor` 的 discriminant 应该是 constructor id，即 `zSomezIUExceptionTypezK.to_smt()` / `zNonezIUExceptionTypezK.to_smt()`，不是 `enum_symbol_exp`。

已有 `option_exception_from_fault_cond` 的结构是正确的：

- `discrim = define_const(Ite(fault_cond, some_ctor.to_smt(), none_ctor.to_smt()))`
- `possibilities[some_ctor] = fault`
- `possibilities[none_ctor] = Val::Unit`

但这个 helper 只适合固定 `fault`。PMA 至少有三类选择：

- no matching PMA region：`Some(accessFaultFromAccessType(access))`
- matched region 且 misaligned_fault 为 `AccessFault` 且地址 misaligned：`Some(accessFaultFromAccessType(access))`
- matched region 且 misaligned_fault 为 `AlignmentFault` 且地址 misaligned：`Some(alignmentFaultFromAccessType(access))`
- matched region、misalignment 不触发 fault、权限失败：`Some(accessFaultFromAccessType(access))`
- 成功：`None()`

因此需要能表达 `Some` payload 本身也是条件选择。两条安全路线：

1. 对 `pmaCheck` 直接构造外层 option：外层 Some 条件为 `any_fault_cond`，Some payload 是一个 inner `Val::SymbolicCtor`，在 `ExceptionType` 的 ctor id 上用条件选择 access fault vs alignment fault。
2. 写专用 helper，输入 `Vec<(SmtExp<Sym>, Val<B>)>` 和 default None，生成外层 option 和必要的 inner exception symbolic ctor。

注意事项：

- 必须 required lookup `Some` / `None` / exception ctor，不能 intern。
- `possibilities` 必须包含所有可达 ctor，否则后续 `Unwrap` / `Kind` 可能因缺 payload 报错。
- 不要把 alignment fault 简化成 access fault；`phys_access_check` 后续有 `highestPriorityAlignmentOrAccessFault`，fault ctor 会影响优先级。
- 如果使用多个 condition，discriminant 要由真实条件 `Ite` 或等价 assert 约束绑定，不能只声明一个“可能是 A 或 B”的 unconstrained ctor symbol。

## 5. 预计最小新增 helper 列表和签名建议

第一批只为 `pmaCheck` exact summary 服务，避免直接做 `option(PMA_Region)`：

```rust
fn list_entry<B: BV>(value: &Val<B>, index: usize) -> Option<Val<B>>;

fn struct_field_cloned<B: BV>(
    value: &Val<B>,
    field: &str,
    shared_state: &SharedState<B>,
    info: SourceLoc,
) -> Result<Option<Val<B>>, ExecError>;

fn bool_exp<B: BV>(
    value: &Val<B>,
    info: SourceLoc,
) -> Result<Option<SmtExp<Sym>>, ExecError>;

fn enum_value_exp<B: BV>(
    value: &Val<B>,
    info: SourceLoc,
) -> Result<Option<SmtExp<Sym>>, ExecError>;

fn alignment_fault_from_access_type_value<B: BV>(
    access: &Val<B>,
    shared_state: &SharedState<B>,
    info: SourceLoc,
) -> Result<Option<Val<B>>, ExecError>;

fn range_subset_exp<B: BV>(
    a_begin: &Val<B>,
    a_size: &Val<B>,
    b_begin: &Val<B>,
    b_size: &Val<B>,
    solver: &mut Solver<B>,
    info: SourceLoc,
) -> Result<Option<SmtExp<Sym>>, ExecError>;

fn pma_attr_parts<B: BV>(
    attrs: &Val<B>,
    shared_state: &SharedState<B>,
    info: SourceLoc,
) -> Result<Option<PmaAttrParts<B>>, ExecError>;

fn pma_region_parts<B: BV>(
    region: &Val<B>,
    shared_state: &SharedState<B>,
    info: SourceLoc,
) -> Result<Option<PmaRegionParts<B>>, ExecError>;

fn option_exception_from_cases<B: BV>(
    cases: Vec<(SmtExp<Sym>, Val<B>)>,
    shared_state: &SharedState<B>,
    solver: &mut Solver<B>,
    info: SourceLoc,
) -> Result<Val<B>, ExecError>;
```

第二批只有在坚持做 `matching_pma_bits_range -> option(PMA_Region)` 独立 summary 时才需要：

```rust
fn ite_val<B: BV>(
    cond: SmtExp<Sym>,
    then_value: Val<B>,
    else_value: Val<B>,
    shared_state: &SharedState<B>,
    solver: &mut Solver<B>,
    info: SourceLoc,
) -> Result<Option<Val<B>>, ExecError>;

fn option_pma_region_from_match_chain<B: BV>(
    regions: &[Val<B>],
    match_conds: Vec<SmtExp<Sym>>,
    shared_state: &SharedState<B>,
    solver: &mut Solver<B>,
    info: SourceLoc,
) -> Result<Val<B>, ExecError>;
```

`ite_val` 必须递归支持 `Struct`、same-ctor `Ctor` with struct payload、enum-valued fields、bool、bitvector。否则多个 `Some(PMA_Region)` payload 的 symbolic selection 会很容易丢字段或丢条件关联。

## 建议判定

`DONE_WITH_CONCERNS`

已有 executor helper 能覆盖 PMA summary 的基础件，但还不能直接安全地构造完整 PMA / `option(PMA_Region)` / 多 exception payload 的 `option(ExceptionType)`。建议先新增上面的最小 helper，并把第一版 summary 放在 `pmaCheck` 层，而不是独立 summary `matching_pma_bits_range`。
