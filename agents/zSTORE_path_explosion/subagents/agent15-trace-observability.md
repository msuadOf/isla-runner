# agent15: builtin trace/probe/stop/function-assumption 可观察性审计

日期：2026-04-27

范围：审计 builtin 拦截对 trace/probe/stop/function-assumption 可观察性的影响，聚焦 PMP 后续的 PMA/MMIO/CLINT 路线。只分析，不改生产代码。

## 结论

PMA/MMIO summary 可以继续做，但必须把“ISA 状态语义等价”和“诊断 trace 等价”分开描述。当前 `Instr::Call` 分派会先调用 `call_isla_implemented_function(...)`；一旦 builtin 返回 `Some(result)`，执行器会直接 `assign` 返回值并 `continue`，不会进入后面的 probe、`trace_call`、stop condition、`UseFunAssumption` 和真实 IR 函数体。因此所有挂在 `call_isla_implemented_function` 的 summary 都不是函数级 trace 等价实现。

已有 PMP exact summary 的记录边界是：

- `pmpCheck` exact summary 在显式 `ISLA_RISCV_BUILTIN_PMP_CHECK=1` 下保留 PMP 配置/循环的返回语义，不再走 PMP-off 假设。
- 它通过 `read_register_cloned(...)` 读取 `zpmpcfg_n` / `zpmpaddr_n`，并手动补顶层 `ReadReg` event。
- 它仍会绕过 IR 内部 helper 的函数级观测：`pmpCheck`、`pmpMatchAddr`、`pmpRangeMatch`、`pmpCheckRWX`、`pmpLocked`、`pmpAddrMatchType_encdec_backwards` 等函数的 call/return trace、probe、stop 和 function-assumption 使用点都不会出现。
- 这在现有文档里已经被定义为“不是 trace 等价”，但当前 PMP helper 本身没有 ISA 状态副作用；只要补足直接读取的 PMP 寄存器，差异主要落在诊断可观察性，而不是执行结果语义。

## 会绕过的函数级事件

所有以下 summary 如果挂到 `call_isla_implemented_function(...)` 并命中，都会绕过目标函数自己的：

- `Event::Function { call: true/false }`
- probe call/return 输出
- stop condition 的 `Kill` / `Abstract`
- `UseFunAssumption`
- 目标函数体内进一步调用的 helper 函数级观测

具体到 PMA/MMIO：

- `pmaCheck` summary 会绕过 `pmaCheck` 本身，以及命中路径中的 `matching_pma`、`matching_pma_bits_range`、`range_subset`、`is_aligned_addr`、`accessFaultFromAccessType`、`alignmentFaultFromAccessType`、`get_config_print_pma`、`print_log` 等内部函数级事件。
- `phys_access_check` summary 会绕过 `phys_access_check` 本身，并整体绕过其中的 `pmpCheck`、`pmaCheck`、`highestPriorityAlignmentOrAccessFault`、`alignmentOrAccessFaultPriority` 等函数级事件。若它内部直接合成 PMP/PMA 结果，还会绕过这些子函数上配置的 function assumptions。
- `within_mmio_readable` / `within_mmio_writable` summary 会绕过目标函数本身，以及 `get_config_rvfi`、`within_clint`、`within_htif_readable` / `within_htif_writable` 的函数级事件。
- `clint_load` / `clint_store` / `clint_dispatch` summary 会绕过目标函数本身，以及 `get_config_print_clint`、`print_log`、`csr_name_write_callback`、`csr_full_write_callback`、`csr_name_map_backwards` 等回调/日志 helper 的函数级事件。
- 如果 summary 提升到 `mmio_read` / `mmio_write` 或 `checked_mem_read` / `checked_mem_write`，还会绕过 `mmio_*`、`within_mmio_*`、`clint_*` / `htif_*`、`read_ram` / `write_ram` 调用分界；这会同时影响函数 trace 和 memory event 边界，风险更高。

## 必须补的事件

必须补的是状态依赖和状态修改事件，不是所有 helper 函数事件。

- `ReadReg pma_regions`：必须补。`pmaCheck` 通过 `matching_pma(pma_regions, paddr, width)` 读取 PMA region 列表；summary 若直接使用该寄存器，必须像 PMP 的 `read_register_cloned(...)` 一样添加 `Event::ReadReg(zpma_regions, [], value)`。否则 trace/footprint 看不到 PMA 配置依赖。
- `ReadReg htif_tohost_base`：如果 `within_mmio_*` summary 覆盖 HTIF 分支，必须补。`within_clint` 只依赖 platform let 常量，但 `within_htif_*` 会读取 `htif_tohost_base`。
- `ReadReg mtime/mip/mtimecmp`：只在 CLINT 真实读这些寄存器时补。`clint_load` 对 MSIP 读 `mip`，对 timer 读 `mtime` / `mtimecmp`；`clint_dispatch` 读旧 `mip.bits`、`mtimecmp`、`mtime`，且 Sstc 分支还可能读 `menvcfg` / `stimecmp`。32-bit 部分写 `mtime` / `mtimecmp` 时也需要读取旧寄存器值来合成新值。
- `WriteReg mip/mtime/mtimecmp`：CLINT store/dispatch 修改 ISA 状态，必须补。写 MSIP 会更新 `mip[MSI]` 并调用 `clint_dispatch`；写 `mtimecmp` / `mtime` 后也会重新计算 `mip[MTI]`，Sstc 开启时还可能更新 `mip[STI]`。
- callback：当前 IR 中 `mem_*_callback`、`csr_*_callback` 体是 pure no-op；省略它们通常只是不保留诊断 trace/stop/probe/function-assumption 可观察性。但如果使用者把 callback 函数本身作为 trace/stop/function-assumption 目标，summary 命中会改变该分析的可观察结果。文档必须显式说明这一点。
- memory events：纯 `pmaCheck`、`phys_access_check`、`within_mmio_*` 不应产生 memory event。CLINT MMIO 在 Sail 中通过寄存器模拟，不走 `read_ram` / `write_ram`，因此不应为了“看起来像 MMIO”额外合成 `ReadMem` / `WriteMem`。只有 summary 覆盖到普通 RAM `read_ram` / `write_ram` 时，才必须通过 `frame.memory().read(...)` / `frame.memory_mut().write(...)` 保留 `ReadMem` / `WriteMem`；access/alignment fault 路径不能产生 memory event。

## 可接受与不可接受的差异

可接受为诊断/trace 不等价的差异：

- summarized 函数及其 helper 的 `Function` call/return 边界消失。
- probe 输出、`print_log`、`get_config_print_*` 分支日志消失。
- stop condition 不再能停在 summarized 函数或其内部 helper。
- no-op callback 的函数级 trace 消失。
- helper 内部 fork 顺序、SMT 临时名、短路求值路径不同。
- 顶层 `ReadReg` 代替字段级 accessor 的 `ReadReg`，只要依赖的完整寄存器值被记录并且文档说明不是精确 trace 等价。

会影响 ISA 状态语义或分析语义的差异：

- PMA summary 不读或错误读取 `pma_regions`，导致 PMA 配置变化不可见。
- `pmaCheck` 忽略 no-match access fault、misaligned fault/align fault 优先级、read/write/execute/atomic/LRSC/CBO 权限、`res_or_con` 约束或 PMA reservability。
- `phys_access_check` 错误合成 PMP/PMA 双错误优先级，尤其 access fault 与 alignment fault 的优先级。
- `within_mmio_*` 错判 CLINT/HTIF 范围，导致 RAM 路径和 MMIO 路径互换。
- CLINT summary 不写回 `mip`、`mtime`、`mtimecmp`，或没有按 `clint_dispatch` 重新计算 MTI/STI。
- 普通 RAM 路径丢失 `ReadMem` / `WriteMem`，或异常路径错误地产生 memory event。
- function assumption 已配置在 `pmaCheck`、`phys_access_check`、`within_mmio_*`、`clint_*` 或其 callback/helper 上时，builtin 仍直接返回自己的结果。因为当前分派顺序是 builtin 早于 `UseFunAssumption`，这会改变该分析的语义。若要支持这类用法，summary 必须显式 honoring assumption，或在发现相关 assumption 时回退 IR。

## 文档要求

后续 PMA/MMIO summary 文档应按函数列出一张事件边界表：

| summary | 状态语义目标 | 手动补的事件 | 明确不会补的事件 | 回退条件 |
| --- | --- | --- | --- | --- |
| `pmaCheck` | PMA 匹配、misaligned、权限和异常选择等价 | `ReadReg pma_regions` | helper `Function`、probe、stop、function-assumption、print callback | unsupported PMA shape/access/width |
| `phys_access_check` | PMP/PMA 结果和异常优先级等价 | PMP/PMA 所需 `ReadReg` | nested helper 函数事件 | unsupported PMP/PMA 情形或相关 assumption |
| `within_mmio_*` | CLINT/HTIF 范围判断等价 | HTIF 分支的 `ReadReg htif_tohost_base` | `within_clint`/`within_htif_*` 函数事件 | rvfi/HTIF/width 不能证明等价 |
| `clint_*` | CLINT 寄存器读写和 dispatch 等价 | `ReadReg`/`WriteReg` for `mip`/`mtime`/`mtimecmp`/必要 CSR | no-op callback 函数事件、print trace | symbolic case 无法安全写回或 callback 需要可观察 |

文档措辞建议：

- 对默认开启的 summary，只能称为“ISA 状态语义等价，不保证函数级 trace 等价”。
- 对 `ISLA_RISCV_ASSUME_*` 这类开关，必须称为“诊断/显式前提”，不能写成默认语义。
- 每个 summary 的验证记录必须同时列出 `ret_val`、register events、memory events、fork profile 和 fallback 情况。
- 如果 summary 覆盖函数可能被 function assumption 命中，文档必须写清当前策略：回退 IR、拒绝启用，或显式不支持 assumption trace 等价。不能静默让 builtin 早于 assumption 改写结果。
