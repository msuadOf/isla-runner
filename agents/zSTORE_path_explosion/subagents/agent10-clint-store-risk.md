# agent10: CLINT store / clint_dispatch builtin 风险分析

日期：2026-04-27

范围：`sail-riscv/model/sys/platform.sail::clint_store`、`clint_dispatch`，以及 Isla executor 中 register write / callback 的可观察行为。只评估 builtin/summary 风险，不修改生产代码。

## 1. `clint_store` 精确地址、宽度分支和寄存器写行为

源码位置：`sail-riscv/model/sys/platform.sail:141-190`。函数入口先计算相对地址：

```sail
let addr = addr - plat_clint_base;
```

当前 rv64 配置中 `plat_clint_base = 0x0000000002000000`，所以绝对地址等于下表相对地址加 `0x02000000`。源码中宽度判断写成类型级 `'n == 4/8`；在 `rv64d.ir::zclint_store` 中被物化为 `zwidth == 4/8` 的分支。

| 相对地址 | 当前绝对地址 | 支持宽度 | 行为 |
| --- | --- | --- | --- |
| `MSIP_BASE = 0x0000` | `0x02000000` | `4` 或 `8` | `mip[MSI] = [data[0]]`; 然后 `clint_dispatch(true)`; 返回 `Ok(true)` |
| `MTIMECMP_BASE = 0x4000` | `0x02004000` | `8` | `mtimecmp = zero_extend(64, data)`; 然后 `clint_dispatch(false)`; 返回 `Ok(true)` |
| `MTIMECMP_BASE = 0x4000` | `0x02004000` | `4` | `mtimecmp[31..0] = zero_extend(32, data)`; 然后 `clint_dispatch(false)`; 返回 `Ok(true)` |
| `MTIMECMP_BASE_HI = 0x4004` | `0x02004004` | `4` | `mtimecmp[63..32] = zero_extend(32, data)`; 然后 `clint_dispatch(false)`; 返回 `Ok(true)` |
| `MTIME_BASE = 0xbff8` | `0x0200bff8` | `8` | `mtime = data`; 然后 `clint_dispatch(false)`; 返回 `Ok(true)` |
| `MTIME_BASE = 0xbff8` | `0x0200bff8` | `4` | `mtime[31..0] = data`; 然后 `clint_dispatch(false)`; 返回 `Ok(true)` |
| `MTIME_BASE_HI = 0xbffc` | `0x0200bffc` | `4` | `mtime[63..32] = data`; 然后 `clint_dispatch(false)`; 返回 `Ok(true)` |
| 其它 | 其它 | 任意 | 不写寄存器，不 dispatch，返回 `Err(E_SAMO_Access_Fault())` |

注意点：

- `within_clint` 只检查访问范围落在 CLINT 区间内；`clint_store` 本身仍只接受上面的精确 aligned 地址/宽度。落在 CLINT range 但不精确命中的 store 会返回 `E_SAMO_Access_Fault`。
- 所有成功路径都会调用 `clint_dispatch`，所以一次 `clint_store` 至少会写目标寄存器一次，随后还可能写 `mip` 一到两次。
- IR 中 subrange 写会先构造更新后的完整 bitvector，再执行完整寄存器赋值，例如 `zmtime = zz495`、`zmtimecmp = zz4144`、`zmip = zz4188`。executor 的 `assign_with_accessor` 对这种寄存器赋值会追加 `Event::WriteReg`。
- 直接读取 `mip`、`mtime`、`mtimecmp`、`stimecmp`、`menvcfg` 等寄存器时，executor 的 `get_id_and_initialize` 会追加 `Event::ReadReg`；summary 如果绕过 IR，也需要补齐等价读写事件，否则 trace 不等价。

## 2. `clint_dispatch` 的 interrupt / callback 副作用

源码位置：`sail-riscv/model/sys/platform.sail:128-138`。

`clint_dispatch(mip_was_written)` 的语义：

1. 保存 `old_mip = mip.bits`。
2. 总是更新 `mip[MTI] = bool_to_bit(mtimecmp <=_u mtime)`。
3. 如果 `currentlyEnabled(Ext_Sstc) & menvcfg[STCE] == 0b1`，再更新 `mip[STI] = bool_to_bit(stimecmp <=_u mtime)`。
4. 如果 `old_mip != mip.bits | mip_was_written`，调用 `csr_write_callback("mip", mip.bits)`。

扩展和配置影响：

- `Ext_Sstc` 的支持来自 `config extensions.Sstc.supported`，当前 `sail-riscv/build/config/rv64d_v256_e64.json` 中为 `true`。
- `menvcfg[STCE]` 是运行时 CSR 状态位；如果该位为 `0`，`STI` 不由 `clint_dispatch` 更新；如果为 `1`，`STI` 跟随 `stimecmp <=_u mtime`。
- `menvcfg.STCE` 写入本身受 `legalize_menvcfg` 限制：只有 `currentlyEnabled(Ext_Sstc)` 时才保留写入值，否则清零。

callback / interrupt 影响：

- `mip.MTI` 和可选的 `mip.STI` 是后续 interrupt pending 逻辑的输入；summary 若只返回 `Ok(true)` 或只写原 store 目标寄存器，会丢失未来中断状态。
- `MSIP_BASE` store 传入 `mip_was_written = true`，因此即使最终 `mip.bits` 没有变化，也应触发 `csr_write_callback("mip", mip.bits)`。
- `mtime` / `mtimecmp` store 传入 `false`，只有 dispatch 导致 `mip.bits` 变化时才触发 callback。
- 当前 `rv64d.ir` 中 `zcsr_name_write_callback("mip", value)` 会映射 CSR 名到 `0x344` 后调用 `zcsr_full_write_callback`；`zcsr_full_write_callback` 的默认 IR body 只是消费参数并返回 `unit`，不会生成 `Event::Abstract`。但它仍是 Sail 级 callback 语义边界；如果启用了 function trace/probe/stop，或者未来把 callback 接到外部观察者，直接跳过会不等价。
- 上层 `mem_write_value_priv_meta` 在 `checked_mem_write` 返回 `Ok(_)` 后还会调用 `mem_write_callback(...)`，返回 `Err(e)` 时调用 `mem_exception_callback(...)`。只替换 `clint_store` 时外层 callback 仍会执行；若在 `mmio_write` / `checked_mem_write` 更高层 summary，则必须额外保留这些 callback。

## 3. 默认 summary `clint_store` 风险为什么较高

`clint_store` 不是纯谓词或小枚举函数，风险高于 `range_subset` / `pmpRangeMatch`：

- 它有真实 ISA/model 状态副作用：写 `mip`、`mtimecmp`、`mtime`。
- `clint_dispatch` 会根据 `mtimecmp <= mtime`、`stimecmp <= mtime`、`Ext_Sstc`、`menvcfg.STCE` 进一步改写 interrupt pending 位。
- callback 是否发生依赖 `old_mip != new_mip | mip_was_written`；其中 `old_mip != new_mip` 在符号计时器状态下通常是符号条件。executor 事件没有天然的“条件 callback 事件”表示，盲目下沉成一个 ITE 状态更新容易漏掉可观察 callback 分支。
- 成功/失败路径副作用差异大：未映射分支必须无寄存器写、无 dispatch，并返回 `E_SAMO_Access_Fault`。
- 写事件顺序可能被 trace 观察：目标寄存器写在前，dispatch 写 `mip` 在后，callback 再后。
- 现有 builtin 命中位置在 `Instr::Call` 中早于 trace/probe/stop/function-assumption 逻辑；即使 ISA 状态等价，也不是完整函数级 trace 等价。

首版如果要做，只建议显式 gate，且只支持 concrete 情况：

- `paddr` concrete，`width` concrete，且 `paddr - plat_clint_base` 精确等于上表地址。
- `data` bit 宽度已知且等于 `8 * width`。
- 当前只针对 `rv64d` 的 64-bit `mip.bits` / callback value 形态，或者实现时必须按 IR 类型动态确认 xlen。
- `get_config_print_clint()` 为当前 IR 中的 `false`；如果未来该配置可为 true，首版应回退 IR，避免丢 `print_log`。
- 必须能按 executor 现有格式补齐相关 `ReadReg` / `WriteReg` 事件。
- 对 `MSIP_BASE` 的 concrete 4/8-byte store 相对最容易支持，因为 callback 必定发生；但仍必须执行 dispatch 对 `MTI` 和可选 `STI` 的更新。
- 对 `mtime` / `mtimecmp` concrete 地址写，只有在能精确处理 dispatch 和 callback 条件时才支持；否则先回退 IR。
- concrete unmapped CLINT offset 可以作为低风险 `Err(E_SAMO_Access_Fault)` 候选，但必须确认上层 `mem_exception_callback` 仍由 IR 执行。

## 4. 必须回退 IR 的情况

以下情况不应由首版 `clint_store` summary 接管：

- `paddr` 或 `width` 是符号值，或者无法证明命中唯一精确分支。
- `data` 长度未知，或不等于 `8 * width`。
- 目标寄存器不是预期 shape：`mip` 不是 `Minterrupts { zbits }`，或 `mtime` / `mtimecmp` / `stimecmp` / `menvcfg` 宽度与当前 IR 不一致。
- `menvcfg.STCE` 或 `old_mip != new_mip` 导致 callback 是否发生为符号条件，而 summary 没有等价事件策略。
- `Ext_Sstc` 支持状态、xlen、CSR callback symbol/ctor 名称与当前 `rv64d.ir` 不匹配。
- `get_config_print_clint()` 不是静态 false。
- 需要保持 function trace/probe/stop/function-assumption 观测的运行模式。
- summary 位于 `mmio_write`、`checked_mem_write` 或更高层，且还没有等价保留 `mem_write_callback` / `mem_exception_callback`。
- 任何无法构造正确 `Ok(bool)` / `Err(ExceptionType)` ctor 的情况。

## 5. 对 zSTORE 热点优先级的建议

不建议把默认 `clint_store` summary 作为下一优先级。

依据：

- 最新 `pmpCheck` exact summary profile 中，热点为 `matching_pma_bits_range=150`、`get_X=120`、`clint_store=80`、`phys_access_check=76`、`clint_load=65`、`within_mmio_writable=26`、`clint_dispatch=24`。CLINT 已经可见，但还不是最大热点。
- `clint_store` 的 80 次热点多半来自符号地址仍可能落入 MMIO/CLINT；优先在 `pmaCheck` / `within_mmio_writable` 层精确区分 RAM 与 MMIO，可能比直接内置 CLINT store 更有收益。
- `clint_store` 是有状态设备模型，不是纯公式 summary；默认开启的语义风险明显高于 PMA/PMP 中的纯比较或小枚举 summary。

建议路线：

1. 优先继续做 `pmaCheck` 层 summary，保留 PMA first-match、权限、MMIO alignment/access fault 分界。
2. 其次评估 `within_mmio_readable/writable` 的等价谓词 summary，目标是减少非 MMIO 地址误入 CLINT/HTIF dispatch 的 fork。
3. 只有在上述处理后 profile 仍稳定显示 `clint_store` / `clint_dispatch` 为主热点，再做显式 gate 的 concrete-only `clint_store` summary。
4. 不要默认启用符号地址版 `clint_store` summary；要么完整建模条件 callback/event，要么回退 IR。
