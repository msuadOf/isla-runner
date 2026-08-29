# agent05 pmaCheck prototype

日期：2026-04-27

## 范围

- worktree: `isla/.worktrees/zstore-pma-mmio`
- 修改代码: `isla-lib/src/executor.rs`
- 新增 gate: `ISLA_RISCV_BUILTIN_PMA_CHECK`
- 默认状态: 关闭。只有显式设置为 `1/true/on` 时才尝试接管 `pmaCheck`，否则回退 IR。

## 实现摘要

- 在 `call_isla_implemented_function` 中新增 `pmaCheck` 分派。
- `pmaCheck` builtin 读取 `zpma_regions` register，并按 Isla `Val::List` 的 head 顺序用 `regions.iter().rev()` 遍历。
- 复用/抽出 `range_subset_exp`，用同一套模 bitvector 加减和 unsigned 比较表达 `matching_pma_bits_range`。
- 对 `paddr` 支持不超过 64 bit 的 bitvector；rv32 形态会 zero-extend 到 64 bit，rv64 保持 64 bit。
- `width` 当前要求 concrete positive byte width，并转换为 64-bit bitvector 参与 PMA range 和 misalignment 判断。
- fault 结果支持三态：
  - 没有 PMA region 完整覆盖访问范围时返回 `Some(accessFaultFromAccessType(access))`。
  - region 命中且 `misaligned_fault = AccessFault` 且访问未对齐时返回 access fault。
  - region 命中且 `misaligned_fault = AlignmentFault` 且访问未对齐时返回 alignment fault。
  - 其它情况下按 PMA access permission 返回 `None()` 或 access fault。
- 新增 `alignment_fault_from_access_type_value`，与既有 `access_fault_from_access_type_value` 保持同样的 access constructor 覆盖。
- 当 access fault 和 alignment fault 都可能出现时，构造 `Some(SymbolicCtor(...))`，避免把 alignment fault 近似成 access fault。

## 支持边界

当前 prototype 支持：

- concrete positive `width`
- `paddr` 为 concrete/symbolic bitvector，宽度 `1..=64`
- `zpma_regions` 为 concrete list，region/attributes 为标准 `zPMA_Region` / `zPMA` struct shape
- `InstructionFetch`、`Load`、`Store`、`LoadReserved`、`StoreConditional`、`Atomic`、`CacheAccess(CB_zero/CB_manage/CB_prefetch)`
- `Load` 必须看到 concrete `res_or_con=false`
- `LoadReserved` / `StoreConditional` / `Atomic` 必须看到 concrete `res_or_con=true`

以下情况 fail closed，返回 `Ok(None)` 回退 IR：

- `ISLA_RISCV_BUILTIN_PMA_CHECK` 未开启
- symbolic/zero width
- `paddr` 非 bitvector、零宽或大于 64 bit
- `zpma_regions` register 缺失、不是 list，或 region/attribute field shape 不匹配
- PMA base/size 不是 64-bit bitvector
- access constructor 或 cache op 不在当前支持集合内
- Sail assert 相关的 `res_or_con` 条件不是 concrete expected value
- PMA bool/enum field 无法表达为 SMT

## 验证

在 `isla/.worktrees/zstore-pma-mmio` 下运行：

```bash
cargo check -p isla-lib
```

结果：exit `0`，`isla-lib` 编译通过；仍有既有 warning（本次复跑为 65 个），未新增阻断性编译错误。

## 剩余风险

- 只做了编译验证，尚未跑 `pmaCheck` builtin on/off 的行为对照或 zSTORE/zLOAD profile。
- builtin 命中会绕过 `pmaCheck` IR 内部函数级 trace/probe/stop/function-assumption，可观察性边界与已有 PMP summary 类似，需要后续 profile/trace 记录。
- `get_config_print_pma()` 的失败日志打印没有在 summary 中复现；返回值语义保留，诊断输出不等价。
