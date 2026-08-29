# agent18: HTIF MMIO summary risk

日期：2026-04-27

输入依据：

- 已读 `agents/findings.md`、`agents/zSTORE_path_explosion/status.md`、`agents/zSTORE_path_explosion/principles.md`。
- 源码重点为 [platform.sail](../../../sail-riscv/model/sys/platform.sail#L18) 中的 `htif_tohost_base`、`within_htif_readable/writable`、`htif_load`、`htif_store`。
- 相关 PMA/MMIO 链路参考 [mem.sail::pmaCheck](../../../sail-riscv/model/sys/mem.sail#L75)、[phys_access_check](../../../sail-riscv/model/sys/mem.sail#L171)、[checked_mem_read/write](../../../sail-riscv/model/sys/mem.sail#L194)。

## 结论

HTIF 的谓词部分可以作为低风险 predicate summary 候选，但 HTIF load/store 不是当前 PMA/MMIO 阶段应优先 summary 的对象。当前应先延后 HTIF load/store summary：`htif_tohost_base = None()` 时可以精确把 `within_htif_*` 视为 false；一旦 HTIF enabled 或状态不确定，HTIF 路径应回退 IR，直到有专门测试覆盖 HTIF state、exit、terminal extern 和 memory callback 边界。

这不是语义上忽略 HTIF，也不是把 HTIF 地址当普通 RAM；只是 PMA/MMIO 优化顺序上先不手写 HTIF 设备行为。

## 1. `htif_tohost_base` option 对 `within_htif` 的影响

[platform.sail](../../../sail-riscv/model/sys/platform.sail#L18) 中 `htif_tohost_base : option(physaddrbits)` 初始为 `None()`，`enable_htif(tohost_addr)` 才会写成 `Some(trunc(tohost_addr))`。

`within_htif_writable(Physaddr(addr), width)` 的语义是：

- `None()`：恒为 `false`，HTIF 不参与 MMIO 分派。
- `Some(base)`：判断访问范围 `[addr, addr + width)` 是否与 HTIF tohost 窗口 `[base, base + 8)` 重叠，即 `(addr <_u base + 8) & (addr + width >_u base)`。
- `within_htif_readable` 只是调用 `within_htif_writable`。

注意这里是“重叠谓词”，不是“合法 HTIF 访问谓词”。`htif_load/store` 后面只接受 `base` 处 8-byte、`base` 处 4-byte、`base + 4` 处 4-byte 的精确访问；其它重叠访问会走 HTIF 分派后返回 access fault。

当前 `rv64d.ir` 中 `zhtif_tohost_base` 初始同样是 concrete `None()`，因此未显式调用 `enable_htif` 的 zSTORE/zLOAD 场景里，HTIF predicate 应精确为 false。

## 2. `htif_load/store` 的 state/callback/extern 行为

`htif_load(access, Physaddr(paddr), width)`：

- 可选 `print_log`，受 `get_config_print_htif()` 控制。
- 如果 `htif_tohost_base = None()`，调用 `internal_error`；正常入口依赖 `within_htif_*` 先保证 HTIF 已启用。
- 只支持三种读：8-byte at `base` 返回 `htif_tohost`，4-byte at `base` 返回低 32 位，4-byte at `base + 4` 返回高 32 位。
- 其它情况返回 `Err(accessFaultFromAccessType(access))`。
- 自身不修改 HTIF state，也不调用 terminal extern；但上层 `mem_read_priv_meta` 会根据 `Ok/Err` 调用 `mem_read_callback` 或 `mem_exception_callback`。

`htif_store(Physaddr(paddr), width, data)` 风险明显更高：

- 可选 `print_log`。
- 如果 HTIF 未启用，`internal_error`。
- 有效写会更新 `htif_cmd_write`、`htif_payload_writes`、`htif_tohost`。低/高 32-bit 分片写还会根据新旧 payload 是否相同决定计数器递增还是重置。
- 无效地址/宽度返回 `Err(E_SAMO_Access_Fault())`。
- 写入后可能解析 `Mk_htif_cmd(htif_tohost)` 并产生设备行为：
  - device `0x00` syscall-proxy：payload bit 0 为 1 时设置 `htif_done = true`、`htif_exit_code = payload >> 1`。
  - device `0x01` terminal：cmd `0x01` 调用 impure extern `plat_term_write(payload[7..0])`；之后 `reset_htif()` 清空 command state。
  - 其它 device/cmd 会 `print`。
- 上层 `mem_write_value_priv_meta` 还会在 `Ok/Err` 后调用 `mem_write_callback` 或 `mem_exception_callback`。

因此 `htif_store` 不是纯函数 summary。手写 builtin 若绕过 IR，必须等价保留寄存器写、data-dependent 分支、终端 extern、exit state、print/log、上层 memory callback 和异常路径；否则很容易把测试退出或终端 I/O 静默丢掉。

## 3. 对 zSTORE/zLOAD 当前热点是否可能相关

当前证据显示 HTIF 不是 zSTORE/zLOAD 的主要热点。

- `status.md` 中 PMP exact summary 后的热点是 `matching_pma_bits_range`、`get_X`、`clint_store`、`phys_access_check`、`clint_load`、`within_mmio_writable/readable`，没有 `htif_load` 或 `htif_store`。
- `rv64d.ir` 的 `htif_tohost_base` 初始为 `None()`；未启用 HTIF 时 `within_htif_*` 精确返回 false。
- `within_mmio_readable/writable` 确实会在 CLINT 谓词之后检查 HTIF 谓词，所以 HTIF 可能贡献少量 predicate 判断成本；但在当前默认 `None()` 状态下，这部分不是设备行为热点。

只有在后续场景显式启用 HTIF，且符号地址可能与 `[tohost, tohost + 8)` 重叠时，HTIF 才可能变成 MMIO 分派相关热点。即便如此，优先处理也应限于 `within_htif_*` 谓词，而不是直接 summary `htif_store`。

## 4. 可 summary 的 predicate 与应回退 IR 的 load/store

可作为 summary 候选：

- `within_htif_writable/readable`：可在 `htif_tohost_base` tag concrete 时精确 summary。`None` 返回 false；`Some(base)` 构造原始 bitvector unsigned overlap 公式，不改写成非回绕整数区间。
- `within_mmio_readable/writable` 中的 HTIF predicate 部分：可在 `get_config_rvfi()` 和 `htif_tohost_base` 可判定时下沉为布尔表达式；必须保留 CLINT 与 HTIF 的 OR 分派边界，以及 readable 的 `1 <= 'n`、writable 的 `'n <= 8` 宽度 guard。
- non-HTIF 快速路径的 disjoint guard：若外部前提或 solver 约束能证明访问范围与 HTIF tohost 窗口不重叠，可以把 HTIF 分派排除；不能证明时回退 IR。

应回退 IR 或延后：

- `htif_store`：默认回退 IR。它有多寄存器状态更新、data-dependent command 解析、`htif_done/exit_code`、`reset_htif()`、`plat_term_write` impure extern 和 `print` 行为。
- `htif_load`：第一阶段也建议回退 IR。虽然它比 store 低风险，但仍读取 HTIF state、构造访问异常，并依赖上层 callback 边界；当前没有证据说明它是瓶颈。
- `mmio_read/mmio_write` 的 HTIF 分支：应先由 IR 执行设备行为。predicate summary 只能决定是否进入 HTIF，不应手写替代 HTIF 设备逻辑。

如果未来必须做 HTIF load/store summary，最低支持边界应是 concrete `base/paddr/width`、明确 `get_config_print_htif=false` 或等价保留 print、能按 executor 现有规则记录寄存器读写事件，并有专门测试覆盖 8-byte 写、低/高 4-byte 写、重复 payload 写、exit command、terminal write、invalid access fault。

## 5. PMA/MMIO 阶段是否应先忽略 HTIF

建议：先忽略 HTIF load/store summary，延后到 CLINT/PMA predicate 收敛之后。

理由：

- 当前热点证据不指向 `htif_load/store`；PMP exact summary 后仍应优先处理 `pmaCheck`、`phys_access_check`、`matching_pma_bits_range`、CLINT 和 `within_mmio_*`。
- HTIF 默认未启用时，`within_htif_*` 是可精确处理的 false 分支；这已经足以避免把默认 zSTORE/zLOAD 热点误归因到 HTIF。
- HTIF store 的可观察行为比 CLINT store 更偏向外部设备：它能结束测试、设置 exit code、写宿主终端、打印 unknown command，并修改多组 HTIF state。没有专门证据前手写 summary 风险高、收益低。
- PMA/MMIO 优化原则要求不能把 non-MMIO/plain RAM 当隐式默认。若 summary 需要跳过 MMIO，必须显式证明地址不落入 CLINT/HTIF，或者在不确定时回退 IR。

阶段性决策：

- `within_htif_*`：可作为小 predicate summary 或 disjoint guard。
- `htif_load/store`：当前阶段延后，回退 IR。
- PMA/MMIO 主线：先做 `pmaCheck` 层 summary，再看 `within_mmio_*` 与 CLINT；HTIF 只保留精确 predicate 处理和 IR fallback。
