# Findings

## `__isla_vector_gpr` 与寄存器枚举

- 在当前 RISC-V 配置里，`__isla_vector_gpr` 默认开启：
  - `isla/configs/riscv64.toml:62`
  - `isla/configs/riscv32.toml:51`
- 当它开启时，Sail 中的 `get_X/get_X_bits/set_X/set_X_bits` 会走 GPR 向量化路径，而不是直接沿着 `x0..x31` 做显式寄存器分支匹配；相关定义见：
  - `sail-riscv/model/core/regs.sail:273-317`
  - `sail-riscv/model/core/regs.sail:229-233`
- 编译到 IR 后，对应表现为 `zget_X_bits` / `zset_X_bits` 先检查 `z__isla_vector_gpr`：
  - `isla/rv64d.ir:17700-17717`
  - `isla/rv64d.ir:17753-17770`
- 在执行器里，向量化寄存器访问最终会落到 `read_register_from_vector` / `write_register_from_vector`。当寄存器索引是符号值时，这里构造的是 SMT 的 ITE 选择链，而不是额外的控制流 fork：
  - `isla/isla-lib/src/executor.rs:187-266`
  - `isla/isla-lib/src/executor.rs:270-349`

