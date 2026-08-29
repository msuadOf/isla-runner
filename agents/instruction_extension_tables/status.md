# Instruction Extension Tables Status

## 当前状态

- 目标文件：`isla/isla-lib/src/isarch_exec.rs`
- 目标函数：`test_exec_main`
- 当前已有样例：
  - `ext_m_instruction_table`：用未编码指令名数组经 `zencode::encode(...)` 生成 `zMUL` / `zDIV` 等构造子名。
  - `ext_c_instruction_table`：同样用未编码压缩指令名数组生成 `zC_*` 构造子名。
- 当前实际执行集合仍是 `["zSTORE", "zLOAD"]`，多数扩展表尚未接入执行。

## 代码理解

- Sail 指令构造子按扩展分散在 `sail-riscv/model/extensions/*/*_insts.sail`，形式为 `union clause instruction = NAME : ...`。
- `isarch_exec.rs` 中 `run_symbolic_execute` 需要传入 z-encoded constructor 名，例如 Sail `LOAD` 对应 Rust 字符串 `"zLOAD"`。
- 现有样例偏向手写分组数组，再通过 `zencode::encode(name)` 统一加 `z` 和转义，而不是直接写全部 `z...` 名称。

## 待确认

- 用户已确认直接实现。

## 实现结果

- 已新增 `encoded_instruction_table` 和 `riscv_instruction_tables`，在 `debug_exec` 或测试构建下可用。
- 已补齐常见指令集扩展分组：`I`、`M`、`A`、`C`、`FD`、`B`、`K`、`V`、`vector_crypto`、`Zic`、`Zawrs`、`Zimop_Zcmop`、`Svinval`、`Zvabd`、`bfloat16`、`cfi`、`rmem`、`sys`。
- `test_exec_main` 默认行为保持原样：未设置环境变量时仍只执行 `zSTORE` / `zLOAD`。
- 新增可选入口：设置 `ISLA_RISCV_TEST_EXTENSIONS=I,M,C` 这类逗号分隔扩展名时，按表追加对应构造子执行。

## 验证

- `cargo test -p isla-lib riscv_instruction_tables_group_common_extensions` 通过。
- `cargo check -p isla-lib` 通过；剩余 warning 为仓库既有 warning。
