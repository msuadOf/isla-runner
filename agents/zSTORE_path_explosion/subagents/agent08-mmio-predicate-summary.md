# agent08: MMIO predicate summary feasibility

日期：2026-04-27

范围：只分析 `within_mmio_readable` / `within_mmio_writable`、`within_clint`、`within_htif_readable` / `within_htif_writable` 的 summary 可行性；不修改生产代码。

## 读取依据

- 已先读 `agents/findings.md`、`agents/zSTORE_path_explosion/principles.md`、`agents/zSTORE_path_explosion/status.md`。
- 主要源码：
  - `sail-riscv/model/sys/platform.sail:18-41`
  - `sail-riscv/model/sys/platform.sail:333-355`
  - `sail-riscv/model/sys/mem.sail:75-185`
  - `sail-riscv/model/sys/mem.sail:189-275`
- 主要 IR：
  - `rv64d.ir:43573-43675` (`zhtif_tohost_base`, `zwithin_clint`, `zwithin_htif_writable/readable`)
  - `rv64d.ir:45624-45682` (`zwithin_mmio_readable/writable`)
  - `rv64d.ir:46742-47032` (`zphys_access_check` 后的 read/write 分派)

## 1. exact 条件公式

记号：

- 当前 `rv64d.ir` 中 `physaddrbits = 64`，地址为 `BV64`。
- `U(x)` 表示 Sail `unsigned(x)` 的数学非负整数值。源码注释明确要求 CLINT 边界用 unsigned unbounded integer，避免物理地址范围靠近地址空间末尾时的 bitvector overflow。
- `bvadd64(x, k)` 表示 64-bit bitvector 加法，结果按 `2^64` 取模。
- `ULT/UGT` 表示 64-bit unsigned bitvector 比较。
- `n` 是 `width : int('n)` 对应的字节宽度。函数类型约束为 `0 < n <= max_mem_access`，而 `max_mem_access = 4096`。

### `within_clint`

Sail 定义：

```sail
let addr_int       = unsigned(addr);
let clint_base_int = unsigned(plat_clint_base);
let clint_size_int = unsigned(plat_clint_size);
  clint_base_int <= addr_int
& (addr_int + sizeof('n)) <= (clint_base_int + clint_size_int)
```

当前 `rv64d.ir` 常量：

- `plat_clint_base = 0x0000000002000000`
- `plat_clint_size = 0x00000000000c0000`
- `plat_clint_end = 0x00000000020c0000`

exact 公式：

```text
within_clint(addr, n) =
  0x0000000002000000 <= U(addr)
  &&
  U(addr) + n <= 0x00000000020c0000
```

这里的 `+` 是 unbounded integer 加法，不是 BV64 加法；不能写成 `addr + n <=u base + size` 这类可能 wrap 的公式。对当前 rv64d 常量和 `n <= 4096` 来说，可实现为 zero-extend 到 128-bit 后 signed/non-negative 比较，因为所有中间值都远小于 `2^127`，不会在 128-bit 表达内溢出；但文档语义仍应按 unbounded integer 理解。

### `within_htif_writable`

Sail 定义：

```sail
match htif_tohost_base {
  None() => false,
  Some(base) => (addr <_u base + htif_tohost_size) & (addr + width >_u base)
}
```

`htif_tohost_size = 8`。exact 公式：

```text
within_htif_writable(addr, n) =
  false                                             if htif_tohost_base = None()

  ULT(addr, bvadd64(base, 8))
  &&
  UGT(bvadd64(addr, n), base)                       if htif_tohost_base = Some(base)
```

这里必须保留 bitvector overflow 语义。`base + 8` 和 `addr + width` 都是按 `physaddrbits` 宽度取模的 bitvector 加法，不是 unbounded integer 加法。只有在额外证明 `base + 8` 和 `addr + n` 都不会 wrap 时，才可解释为普通半开区间 overlap：

```text
[U(addr), U(addr) + n) overlaps [U(base), U(base) + 8)
```

这个无 wrap 解释不能作为 exact summary 的默认公式。

### `within_htif_readable`

Sail 定义直接调用 writable：

```text
within_htif_readable(addr, n) = within_htif_writable(addr, n)
```

### `within_mmio_readable`

Sail 定义：

```sail
if get_config_rvfi()
then false
else within_clint(addr, width) | (within_htif_readable(addr, width) & 1 <= 'n)
```

exact 公式：

```text
within_mmio_readable(addr, n) =
  !get_config_rvfi()
  &&
  (
    within_clint(addr, n)
    ||
    (within_htif_writable(addr, n) && 1 <= n)
  )
```

在 well-typed Sail 调用中 `1 <= n` 已由 `0 < n` 保证，是 tautology；但 function-level builtin 只看到 `%i64` 参数，建议仍校验或保留 `1 <= n`，避免 direct execute-function 传入非法 width 时改变 IR 行为边界。

### `within_mmio_writable`

Sail 定义：

```sail
if get_config_rvfi()
then false
else within_clint(addr, width) | (within_htif_writable(addr, width) & 'n <= 8)
```

exact 公式：

```text
within_mmio_writable(addr, n) =
  !get_config_rvfi()
  &&
  (
    within_clint(addr, n)
    ||
    (within_htif_writable(addr, n) && n <= 8)
  )
```

注意 `n <= 8` 只限制 HTIF write 分支；CLINT 分支仍按 `within_clint` 的整个 CLINT range 判断，不额外限制 width 为 4/8。

## 2. `get_config_rvfi`、`htif_tohost_base`、width 约束的影响

### `get_config_rvfi`

- 源码 `prelude.sail` 默认 `get_config_rvfi() = false`。
- 当前 `rv64d.ir:7619-7621` 中 `zget_config_rvfi` 已编译为直接 `return = false`。
- `isla/configs/riscv64.toml` 和 `isla/configs/riscv64_difftest.toml` 也把 `get_config_rvfi = "false"` 写在 `[const_primops]`，但当前 IR 已有函数体返回 false；summary 不应依赖 TOML 覆盖来判断 RVFI。
- 如果未来 IR 或运行入口使 `get_config_rvfi()` 为 true，`within_mmio_readable/writable` 必须直接返回 false。summary 若不能解析该值，应回退 IR。

### `htif_tohost_base : option(physaddrbits)`

- `htif_tohost_base` 是寄存器，初始值为 `None()`。
- `enable_htif(tohost_addr)` 的源码语义是 `Some(trunc(tohost_addr))`；在 rv64d 下 `trunc(bits(64))` 到 `physaddrbits` 仍是 64-bit 值。
- 当前 `rv64d.ir` 中能看到 `zhtif_tohost_base` register 和 HTIF load/store 对它的读取，但 `rg enable_htif rv64d.ir` 没有找到对应 IR 函数。也就是说，当前 Isla IR 目标里 HTIF 是否启用主要取决于 register 初始化/外部写入，而不是 `plat_htif_tohost` / `plat_enable_htif` const primop。
- 当前 `riscv64*.toml` 有 `plat_htif_tohost = 0x0000000040001000` 和 `plat_enable_htif = "false"`，但 `platform.sail` 的这几个 predicate 不读取这两个名字。不能在 summary 里从它们推导 `htif_tohost_base = Some(...)`。
- summary 若直接读取 `zhtif_tohost_base`，需要保留与 IR 读寄存器一致的可观察边界。至少要像现有 PMP summary 读取 `pmpcfg_n` / `pmpaddr_n` 那样补顶层 `ReadReg` event；函数级 trace/probe/stop 仍会被 builtin 绕过，需要记录为 trace 边界。

### width 约束

- 正常 Sail 类型保证 `0 < n <= 4096`。
- summary 入口看到的是 `%i64` 参数；建议只支持 concrete width，且校验 `1 <= n <= 4096`。
- `within_htif_writable` 的 `addr + width` 是 BV64 加法。若 width 符号化，需要精确构造 `addr + extract64(width)` 这类表达；当前收益不值得扩大边界，建议 symbolic width 回退 IR。
- `within_mmio_writable` 的 `n <= 8` 是 HTIF gate，不是 CLINT gate。

## 3. 是否适合独立 predicate summary 与默认建议

结论：适合做独立 predicate summary，但优先级低于 `pmaCheck`，且第一版建议默认关闭。

理由：

- 这些函数返回 bool，主体是纯条件组合，典型适合把 IR 短路 `jump` 转成 SMT 布尔表达式。
- `within_clint` 本身无寄存器副作用，只依赖 concrete platform let 和参数；它是最适合的子项。
- `within_htif_readable/writable` 只额外读取 `htif_tohost_base`。当 option tag 为 concrete `None` 或 concrete `Some(base)` 时，summary 可 exact；tag 或 payload 形态不支持时回退 IR。
- `within_mmio_readable/writable` 是组合谓词，summary 后可以减少 `checked_mem_read/write` 在 RAM/MMIO 分派处的短路 fork。

默认建议：

- `within_clint`：实现后可考虑默认 on，但仍应先有 wrapper 对照测试。公式简单，语义风险低。
- `within_htif_readable/writable`：建议随 MMIO predicate gate 实现，strict fallback；当前配置 HTIF 默认 disabled，收益有限。默认 on 只有在 None/Some concrete option 测过后才合适。
- `within_mmio_readable/writable`：第一版建议 `ISLA_RISCV_BUILTIN_MMIO_PREDICATES=1` 显式开启、默认 off。原因是它决定 RAM/MMIO 分派边界，且当前 profile 中 `within_mmio_*` 只是 PMP/PMA 之后的次级热点：`within_mmio_writable=26`、`within_mmio_readable=21`，低于 `matching_pma_bits_range=150`、`get_X=120`、`clint_store=80`、`phys_access_check=76`、`clint_load=65`。
- 如果后续 wrapper、HTIF on/off、zSTORE/zLOAD 回归都通过，再把 `within_clint` 或整个 MMIO predicate gate 改为默认 on。

## 4. 对 `pmaCheck` / `phys_access_check` 后 RAM/MMIO 分派的影响

调用顺序很关键：

```text
checked_mem_read/write
  -> phys_access_check
       -> pmpCheck
       -> pmaCheck
  -> if within_mmio_readable/writable then mmio_read/write else read_ram/write_ram
```

影响结论：

- MMIO predicate summary 不会减少 `phys_access_check`、`pmaCheck`、`matching_pma_bits_range` 的前置成本；它只影响 PMA/PMP 均允许之后的 RAM/MMIO 分派。
- `pmaCheck` 返回 `None()` 后仍必须继续执行 RAM/MMIO 分派，不能在 PMA summary 中默认走 RAM，也不能把 non-MMIO/plain RAM 当隐含前提。
- predicate 必须保持“宽分派”语义：
  - `within_clint` 对整个 CLINT range 为 true，不只是真正实现的 MSIP/MTIMECMP/MTIME 寄存器 offset。进入 `clint_load/store` 后，未映射 offset 会由设备函数返回 access fault。
  - `within_htif_writable` 是 overlap predicate，不要求 exact aligned 4/8 byte access。进入 `htif_load/store` 后，才检查 `width == 4/8` 和 `paddr == base/base+4`。
  - `within_mmio_writable` 只对 HTIF 分支加 `n <= 8`，不能误加到 CLINT。
- summary 若误判 false，会把设备访问落到 RAM，丢失 CLINT/HTIF register update、callback、interrupt side effect，memory event 也会变成 RAM event。
- summary 若误判 true，会把 RAM 访问送入 `mmio_read/write`，可能产生错误的 access fault 或设备副作用。
- 因此该 summary 的收益是减少分派谓词 fork，不是替代 `mmio_read/write`、`clint_load/store` 或 `pmaCheck`。

## 5. fallback 条件与测试建议

### fallback 条件

建议遇到以下情况返回 `Ok(None)` 回 IR：

- 函数名或参数数量不匹配。
- 地址参数不是 64-bit bitvector，或无法取得 bitvector 宽度。
- width 不是 concrete integer，或不满足 `1 <= width <= 4096`。
- `zplat_clint_base` / `zplat_clint_size` 不能解析为同宽 concrete bitvector let。
- `get_config_rvfi()` 不能解析为 concrete bool 或当前已知 false 函数。
- `zhtif_tohost_base` 读不到、option tag 不是 concrete `None/Some`、`Some` payload 不是 64-bit bitvector。
- 无法按原语义表达 CLINT 的 unbounded integer 比较，或无法按原语义表达 HTIF 的 BV64 wrapping add/unsigned compare。

可接受的局部 short-circuit：

- `get_config_rvfi() == true` 时，`within_mmio_*` 可直接返回 false。
- `htif_tohost_base == None()` 时，`within_htif_*` 可直接返回 false。
- `within_clint` 已能证明 concrete true 时，`within_mmio_*` 可直接返回 true；但如果只是 symbolic CLINT 条件，仍需要 HTIF 分支表达式，否则回退。

### 测试建议

1. wrapper 级 direct tests：
   - `within_clint`：symbolic addr + concrete width 1/4/8/4096；比较 summary on/off 的最终 path、SAT 条件和返回值。
   - CLINT 边界：`base-1`、`base`、`end-width`、`end-width+1`。
   - CLINT overflow guard：构造临时 wrapper 或替代配置，验证不能把 unbounded 公式退化成 wrapping BV 公式。

2. HTIF option tests：
   - `htif_tohost_base = None()`：`within_htif_*` 恒 false。
   - `Some(0x0000000040001000)`：测试 `addr=base-1,width=1` false、`addr=base,width=4/8` true、`addr=base+4,width=4` true、`addr=base+8,width=1` false、overlap 宽访问按源码公式判断。
   - `Some(0xfffffffffffffffc)` 这类靠近 `2^64` 的 base：验证 `base+8` wrap 后仍匹配 IR 的 BV64 语义，而不是普通整数区间语义。

3. `within_mmio_readable/writable` tests：
   - RVFI false/true 两组；RVFI true 必须恒 false。
   - HTIF write width：`n=8` 可走 HTIF，`n=9` 不可走 HTIF；CLINT 不受 `n <= 8` 限制。
   - readable 的 `1 <= n`：正常 width 下 tautology；非法 direct-call width 建议回退而不是静默优化。

4. 分派级回归：
   - `checked_mem_read/write` 或 zLOAD/zSTORE，地址分别约束到 plain RAM、CLINT range 内已映射 offset、CLINT range 内未映射 offset、HTIF Some base、HTIF None。
   - 对比 summary on/off 的 `ret_val`、`memory_event_count`、`mem_read_callback` / `mem_write_callback` / `mem_exception_callback`、CLINT `mip/mtime/mtimecmp` side effect。

5. profile 对照：
   - 在已有 `ISLA_RISCV_BUILTIN_PMP_CHECK=1`、VMEM off/aligned 场景下重跑 120s profile。
   - 预期只降低 `within_mmio_*` 及其短路子调用 fork；不应期待 `matching_pma_bits_range`、`phys_access_check`、`clint_load/store` 大幅下降。

## 总体结论

`within_clint` / `within_htif_*` / `within_mmio_*` 可以做 exact predicate summary，但第一收益不在 PMA/PMP 前置检查，而在 `phys_access_check` 成功后的 RAM/MMIO 分派短路。实现上必须同时保留 CLINT 的 unbounded integer 边界语义和 HTIF 的 BV64 wrapping 语义。由于它直接决定 RAM 与 MMIO 设备路径，建议第一版严格 fallback、显式 gate 默认 off；有 wrapper 和 zSTORE/zLOAD 回归证据后，再考虑默认开启。
