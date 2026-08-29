# RISC-V VMEM Builtin 语义一致性 Review

本文档记录 `isla/isla-lib/src/executor.rs` 中对 `vmem_read_addr` / `vmem_write_addr` 的 Isla 侧直接实现，与 `sail-riscv` 原始 Sail 语义之间的差异。

## Review 范围

- Isla 侧实现入口：
  - `isla/isla-lib/src/executor.rs::call_isla_implemented_function(...)`
  - 当前拦截 `vmem_read_addr` 和 `vmem_write_addr`
- Sail 原始语义：
  - `sail-riscv/model/sys/vmem_utils.sail::vmem_read_addr`
  - `sail-riscv/model/sys/vmem_utils.sail::vmem_write_addr`
  - `sail-riscv/model/sys/mem.sail::{mem_read, mem_write_ea, mem_write_value}`
- 主要关注：
  - `zSTORE` / `zLOAD` 这类普通访存指令
  - 对齐检查、地址翻译、权限检查、MMIO、LR/SC、misaligned split 等内存相关语义

## 当前 Isla 侧 builtin 行为

`call_isla_implemented_function(...)` 在进入 IR 函数体前识别函数名：

- `vmem_write_addr(vaddr, width, data, access, aq, rl, res)`
  - 若 `res == true`，使用 `WriteOpts::exclusive()`，否则使用默认写选项
  - 直接执行 `frame.memory_mut().write(access, vaddr, data, solver, None, opts)`
  - 返回 `zOkzIozCUExecutionResultzK(write_success)`
- `vmem_read_addr(vaddr, offset, width, access, aq, rl, res)`
  - 若 `res == true`，使用 `ReadOpts::exclusive()`，否则使用默认读选项
  - 直接执行 `frame.memory().read(access, vaddr, width, solver, false, opts)`
  - 返回 `zOkzIbzCUExecutionResultzK(value)`

这会把原本由 Sail 执行的 VMEM 和 MEM 链路替换成一次 Isla memory event。

## 不等价点

### 1. 异常路径被吞掉

原 Sail 语义会在多个位置返回 `Err(Memory_Exception(...))`：

- `vmem_read_addr`：
  - LR 或普通 load 的地址对齐异常
  - `translateAddr(...)` 返回页错误或访问错误
  - `mem_read(...)` 返回访问错误
- `vmem_write_addr`：
  - store 地址对齐异常
  - `translateAddr(...)` 返回页错误或访问错误
  - `mem_write_ea(...)` 或 `mem_write_value(...)` 返回访问错误

当前 Isla builtin 总是构造 `Ok(...)` 返回。因此以下情况会被错误地视为成功访存：

- 未对齐 load/store
- page fault / guest page fault
- access fault
- PMP / PMA 拒绝访问
- MMIO 后端返回错误

对 `zSTORE` 来说，最直接的不等价是：原模型中可返回 `E_SAMO_Addr_Align` 或 `E_SAMO_Access_Fault` 的路径，在 builtin 中会继续生成 `WriteMem` 并退休成功。

### 2. 虚拟地址到物理地址的翻译被绕过

原 Sail 语义在每次实际访存前调用：

- `translateAddr(Virtaddr(vaddr), access)`

成功后使用返回的 `paddr` 调用 `mem_read` / `mem_write_ea` / `mem_write_value`。

当前 Isla builtin 直接把 `vaddr` 当作 Isla memory address 使用。因此：

- trace 中的 `ReadMem` / `WriteMem` 地址是虚拟地址，不是原语义中的物理地址
- 页表遍历、权限检查、A/D 位更新等副作用都不会发生
- page fault / access fault 不会发生
- 与 page table memory events 相关的行为会消失

只有在地址翻译恒等、VM 关闭或明确不关心翻译语义时，这一点才可以被视作近似。

### 3. Misaligned split 语义丢失

原 Sail 语义通过 `split_misaligned(vaddr, width)` 把允许的 misaligned 访问拆成多个更小的 single-copy-atomic memory operations：

- load 会循环读取每个子访问，并把结果拼回 `data`
- store 会循环切分 `data`，分别写入每个子地址
- 子访问顺序由 `misaligned_order(n)` 决定

当前 Isla builtin 永远只生成一次整宽 `ReadMem` 或 `WriteMem`。因此：

- 如果 misaligned 被禁止，原模型应 fault，builtin 不会 fault
- 如果 misaligned 被允许，原模型应产生多个 memory events，builtin 只产生一个
- 跨页、跨 PMP/PMA 区域、跨 MMIO/普通内存区域的访问不等价
- 内存模型观察到的原子粒度不等价

### 4. PMP / PMA / MMIO 语义丢失

原 `mem.sail` 中 `checked_mem_read` / `checked_mem_write` 会先调用：

- `phys_access_check(access, effectivePrivilege(...), paddr, width, res_or_con)`

该检查会合并 PMP 和 PMA 结果，并在通过后区分：

- MMIO read/write
- RAM read/write

当前 Isla builtin 只进入 `Memory::read/write`，不会执行：

- `pmpCheck`
- `pmaCheck`
- `within_mmio_readable`
- `within_mmio_writable`
- `mmio_read`
- `mmio_write`
- `mem_exception_callback`
- `mem_read_callback` / `mem_write_callback`

这对普通用户态裸机、只关心符号地址和数据流的生成路径可能可接受，但对系统级内存语义不等价。

### 5. LR/SC 与 aq/rl 语义不完整

当前 builtin 只根据 `res` 设置 exclusive opt：

- `res == true` -> exclusive
- 其他情况 -> default

原 Sail 语义还会处理：

- `load_reservation(bits_of(paddr), width)`
- `match_reservation(bits_of(paddr))`
- store-conditional 失败时先做 PMP/PMA 检查，再返回 `Ok(false)`
- `aq` / `rl` 对 read/write kind 的影响
- 非法的 aq/rl 组合触发 internal error 或 not implemented

因此当前实现不能覆盖 LR/SC、AMO 或未来 acquire/release 相关内存语义。

### 6. `Ok(bool)` payload 对普通 store 过松

Isla `Memory::write(...)` 会返回一个 symbolic bool，表示写事件的成功值。当前 builtin 将这个 bool 直接作为 `Ok(bool)` payload。

原 `vmem_write_addr` 中：

- 普通 store 的 `write_success` 初始为 `true`
- 对每个子写入执行 `write_success = write_success & s`
- store-conditional 可能因 reservation 失败返回 `false`

对 base `STORE` 来说，上层通常只匹配 `Ok(_)`，所以影响较小；但对检查 `Ok(false)` 的路径，当前 symbolic bool 会引入额外可行分支。

### 7. `access` 的具体构造子未参与语义判定

当前 builtin 把 `access` 原样作为 Isla memory event 的 `read_kind` / `write_kind`，但不根据 `access` 区分：

- `Load`
- `Store`
- `LoadReserved`
- `StoreConditional`
- `Atomic`
- `InstructionFetch`
- `CacheAccess`

原模型中这些构造子会影响异常类型、PMA 权限、PMP RWX 检查、read/write kind、reservation 和 cache-block 行为。

## 可以认为近似等价的条件

当前 builtin 只适合作为如下场景的近似：

- 普通 `Load(Data)` / `Store(Data)`
- `aq == false`
- `rl == false`
- `res == false`
- 地址已知或被约束为对齐
- VM 关闭，或虚拟地址等于物理地址
- 不触发 PMP / PMA / MMIO / page fault / access fault
- 不关心 misaligned split 的事件粒度
- 不关心 `mem_*_callback` 和 page table side effects
- 对普通 store 不观察 `Ok(bool)` 的具体 payload

在这些条件外，不能把当前 builtin 视为语义等价替换。

## 对 `zSTORE` 的判断

`zSTORE` 的顶层 Sail 语义在 `sail-riscv/model/extensions/I/base_insts.sail` 中大致是：

- 计算 `offset = sign_extend(imm)`
- 取 `data = X(rs2)[width * 8 - 1 .. 0]`
- 调用 `vmem_write(rs1, offset, width, data, Store(Data), false, false, false)`
- `vmem_write` 内部先通过 `ext_data_get_addr(...)` 计算 `vaddr`
- 再调用 `vmem_write_addr(...)`

当前 builtin 拦截的是 `vmem_write_addr`，所以 `rs1 + offset` 的地址计算仍由 Sail 执行；但 `vmem_write_addr` 之后的全部 VMEM/MEM 语义被替换。

因此，对 `zSTORE` 的结论是：

- 地址计算和写入数据宽度大体保留
- 单次普通 aligned symbolic write event 大体保留
- 对齐异常、地址翻译、权限检查、MMIO、misaligned split、物理地址事件等语义丢失
- 不能声明与原始 `zSTORE` 内存语义整体等效

## 验证情况

已执行：

```sh
cd isla
cargo check -p isla-lib
```

结果：编译通过，但工作区存在较多 warning。该检查只能证明 Rust 类型层面可编译，不能证明语义等价。

## 2026-04-25 修正状态

当前 `isla/` 语义修正分支：`fix-memory-sym-pathboomb-semantics`

新增提交：

- `f3989e1 Add gated RISC-V vmem builtin modes`
- `71f60d3 Return alignment errors for misaligned vmem builtins`
- `1634fb0 Require explicit plain-RAM vmem assumptions`

已经修正或收紧的点：

- `vmem_read_addr` / `vmem_write_addr` 增加逐函数 gate，可以单独关闭某一个 builtin 回退 IR。
- 增加 `ISLA_RISCV_VMEM_BUILTIN_MODE`：
  - `legacy`：保留旧快速路径作为无路径爆炸基线，但必须显式 opt-in。
  - `off`：两个 VMEM builtin 全部回退 IR。
  - `plain-ram` / `plain_ram`：只处理显式声明外部前提的普通 RAM 快速路径；当前默认使用该模式。
- `plain-ram` 只接管普通 `Load(Data)` / `Store(Data)`，并要求：
  - `aq == false`
  - `rl == false`
  - `res == false`
  - width concrete
  - write data length 等于 `width * 8`
  - concrete aligned，或显式 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`
  - 显式 `ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1`
  - 显式 `ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1`
  - 显式 `ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1`
- concrete misaligned 在 `plain-ram` 下不再被错误简化为成功访存：
  - load 返回 `Err(Memory_Exception(vaddr, E_Load_Addr_Align()))`
  - store 返回 `Err(Memory_Exception(vaddr, E_SAMO_Addr_Align()))`
- 普通 store 不再把 Isla memory event 的 symbolic success 直接暴露为 `Ok(bool)`：
  - 对 event success 加 `assert(success)`
  - 返回 `Ok(true)`

仍未完全等价的点：

- `ISLA_RISCV_VMEM_ASSUME_IDENTITY_TRANSLATION=1`、`ISLA_RISCV_VMEM_ASSUME_PMP_PERMITS=1`、`ISLA_RISCV_VMEM_ASSUME_PLAIN_RAM=1` 目前是外部前提声明，不是 executor 自动从 TOML/IR 证明出来的事实。
- symbolic alignment unknown 仍然回退 IR；不能直接返回 alignment fault，因为原语义可能同时包含 aligned 和 misaligned 路径。
- 允许 misaligned access 的 split 语义尚未实现。
- page walk、PTE permission、A/D bit update、PMP/PMA/MMIO、callback、LR/SC、AMO、aq/rl 仍未由 builtin 等价覆盖。
- 当前 `plain-ram` 只能在外部配置确实收窄到 identity translation、PMP 不拒绝、普通 RAM、非 MMIO 时视为等价快速路径。

路径爆炸测试结论：

- `vmem_write_addr` 单独回退 IR 后，`zSTORE` 在 5 分钟内超时，fork 约 `57-70`，确认会路径爆炸。
- `vmem_read_addr` 单独回退 IR 后，`zLOAD` 在 5 分钟内超时，fork 约 `50-70`，确认会路径爆炸。
- 因此后续方向不是整体回退这两个函数，而是在 builtin 框架内按 fail-closed 规则补语义。

当前可接受处理顺序仍是：

1. 返回原语义允许的 `Err(...)`。
2. 回退原 IR。
3. panic / internal error，暴露未覆盖语义。

## 2026-04-25 固定样例验证

为避免 generator 非确定性影响 `address_model` / `data` 对比，当前分支增加了固定 instruction 字段的测试入口。

新增 env：

- `ISLA_RISCV_TEST_ZSTORE_IMM`
- `ISLA_RISCV_TEST_ZSTORE_RS1`
- `ISLA_RISCV_TEST_ZSTORE_RS2`
- `ISLA_RISCV_TEST_ZSTORE_WIDTH`
- `ISLA_RISCV_TEST_ZLOAD_IMM`
- `ISLA_RISCV_TEST_ZLOAD_RS1`
- `ISLA_RISCV_TEST_ZLOAD_RD`
- `ISLA_RISCV_TEST_ZLOAD_IS_UNSIGNED`
- `ISLA_RISCV_TEST_ZLOAD_WIDTH`

固定 aligned 样例结果：

- `sw x0, 0x0(x1)`，`x1 = #x0000000080400000`
  - `Retire_Success(())`
  - 1 个 write event
  - address/address_model 都是 `#x0000000080400000`
  - bytes `4`
  - data `#x00000000`
  - write success `1'h1`
- `lw x2, 0x0(x1)`，`x1 = #x0000000080400000`
  - `Retire_Success(())`
  - 1 个 read event
  - address/address_model 都是 `#x0000000080400000`
  - bytes `4`
  - value `#x00000000`

固定 concrete misaligned 样例结果：

- `sw x0, 0x0(x1)`，`x1 = #x0000000080400002`
  - `Memory_Exception(... E_SAMO_Addr_Align ... #x0000000080400002)`
  - `memory-events = []`
  - fork `0`
- `lw x2, 0x0(x1)`，`x1 = #x0000000080400002`
  - `Memory_Exception(... E_Load_Addr_Align ... #x0000000080400002)`
  - `memory-events = []`
  - fork `0`

因此，截至当前分支，普通 aligned `Load(Data)` / `Store(Data)` 在显式 plain-RAM 前提下可以用固定样例观察到稳定 memory event；concrete misaligned 不再被错误简化成成功访存。

## 2026-04-25 默认行为

当前默认模式已经改成等价优先：

- 未设置 `ISLA_RISCV_VMEM_BUILTIN_MODE` 时使用 `plain-ram`。
- 未知 `ISLA_RISCV_VMEM_BUILTIN_MODE` 也使用 `plain-ram`。
- 只有显式设置 `ISLA_RISCV_VMEM_BUILTIN_MODE=legacy` 才会启用旧的不等价快速路径。

默认模式下已复测：

- aligned `sw x0, 0x0(x1)` / `lw x2, 0x0(x1)`，`x1 = #x0000000080400000`：
  - 两者都 `Retire_Success(())`
  - 各产生 1 个对应 memory event
  - address/model 固定为 `#x0000000080400000`
- misaligned `sw x0, 0x0(x1)` / `lw x2, 0x0(x1)`，`x1 = #x0000000080400002`：
  - store 返回 `E_SAMO_Addr_Align`
  - load 返回 `E_Load_Addr_Align`
  - 两者都不产生 memory event

## 2026-04-25 aligned 假设修正

之前的 `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 只是 gate 放行，没有向 solver 添加约束；这会让 symbolic address 仍可能在模型中取 misaligned 值，却返回成功访存。

当前已修正：

- symbolic address + `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1` 会添加 SMT 约束。
- 对 width=4 的 load/store，约束形式为低两位等于 0：
  - `(assert (= ((_ extract 1 0) addr) #b00))`
- concrete misaligned 仍不走该假设路径，而是直接返回 alignment exception。

固定 symbolic address 样例已验证：

- 未初始化 `x1`。
- 固定 `sw x0, 0x0(x1)` 与 `lw x2, 0x0(x1)`。
- 模型选择的地址分别为：
  - store: `#x0000000080380000`
  - load: `#x0000000080320000`
- 两者低两位均为 0。
- `solver.dump` 中可见低位对齐断言。

这修掉了一个明确的不等价点：plain-RAM 成功路径现在不会允许 misaligned symbolic model。
