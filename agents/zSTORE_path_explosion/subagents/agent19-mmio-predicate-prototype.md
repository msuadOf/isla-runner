# agent19: within_mmio predicate summary prototype

日期：2026-04-27

## 范围

- 目标文件：`isla/.worktrees/zstore-pma-mmio/isla-lib/src/executor.rs`
- 新增记录：`agents/zSTORE_path_explosion/subagents/agent19-mmio-predicate-prototype.md`
- 未依赖 agent08 结果。
- 未改动 `sail-riscv`、IR、配置、测试或其它 Rust 文件。

## 原型内容

在 `call_isla_implemented_function(...)` 中新增 `within_mmio_readable` / `within_mmio_writable` 分派。

启用方式：

```text
ISLA_RISCV_BUILTIN_WITHIN_MMIO=1
```

默认不启用，避免影响现有语义路径。

当前 prototype 只处理 `htif_tohost_base=None()` 的常见路径，把两个 predicate 都总结为 `within_clint(addr, width)` 的 SMT 布尔公式：

```text
unsigned(plat_clint_base) <= unsigned(addr)
&& unsigned(addr) + width <= unsigned(plat_clint_base) + unsigned(plat_clint_size)
```

实现细节：

- `get_config_rvfi` 必须在当前 IR 中可识别为 literal `false`，否则回退 IR。
- `htif_tohost_base` 必须是 concrete `None()`，否则回退 IR；不对 HTIF `Some(base)` 做近似。
- `width` 必须是 concrete 非零整数，symbolic width 回退 IR。
- `addr`、`zplat_clint_base`、`zplat_clint_sizze` 必须是同宽 bitvector，且宽度不超过 128，无法确认则回退 IR。
- 公式使用 128-bit zero-extend 后的 unsigned BV 比较，避免在原地址宽度上做 `addr + width` 溢出判断。

## 语义边界

这个 prototype 没有尝试支持 HTIF overlap：

- `within_htif_readable(addr, width) & 1 <= 'n`
- `within_htif_writable(addr, width) & 'n <= 8`

原因是 `htif_tohost_base` 是 `option(physaddrbits)` 寄存器，`Some(base)` 路径需要保留 `addr <_u base + 8` 和 `addr + width >_u base` 的 wrapping bitvector 语义，并且读写宽度条件不同。为了满足 fail-closed，当前遇到非 `None()` 直接回 IR。

`get_config_rvfi()` 为 true 时原 Sail 语义是直接返回 `false`。本原型按任务要求不支持 rvfi 配置路径：只在当前 IR 函数体可证明为 literal `false` 时启用，否则回退 IR。

## 验证

第一次运行：

```text
cargo check -p isla-lib
```

结果：失败。当时错误来自同一 `executor.rs` 中已有 PMA 原型缺少 helper：

```text
E0425 cannot find function `alignment_fault_from_access_type_value`
E0425 cannot find function `option_exception_from_fault_conds`
```

随后目标 worktree 中同一文件出现了对应 PMA helper 定义；我未修改那段并行 PMA 原型，只重新验证当前文件状态。

第二次运行：

```text
cargo check -p isla-lib
```

结果：通过；仍有既有 warnings。

## 后续 patch plan

若要把这个 prototype 推到更完整的 MMIO summary：

1. 为 HTIF `Some(base)` 增加 exact formula：
   - readable：`within_clint || (within_htif_writable && 1 <= width)`
   - writable：`within_clint || (within_htif_writable && width <= 8)`
   - `within_htif_writable` 必须保留原 Sail 的 unsigned wrapping bitvector 比较，不要改写成普通整数区间。
2. 明确是否要为 summary 内部读取 `htif_tohost_base` 记录 `ReadReg` event。当前 prototype 通过 `get_last_if_initialized` 做非修改检查，只在已知 `None()` 时绕过 HTIF 路径。
3. 增加直接 wrapper 验证：
   - HTIF `None()`、symbolic addr、concrete width：builtin on/off 结果等价，on 侧少 fork。
   - HTIF `Some(base)`：当前必须观察到 fallback。
   - symbolic width：必须 fallback。
   - rvfi true 或无法证明 false：必须 fallback。
4. 再做 zSTORE/zLOAD profile，对比 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 后开启/关闭 `ISLA_RISCV_BUILTIN_WITHIN_MMIO` 的 `fork_profile` 热点变化。
