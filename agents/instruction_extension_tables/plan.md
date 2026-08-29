# Instruction Extension Tables Plan

## 目标

在 `isla/isla-lib/src/isarch_exec.rs` 中，仿照现有 `ext_m_instruction_table` / `ext_c_instruction_table` 的写法，按 RISC-V 指令集扩展补充其它 instruction table，让后续可以按扩展选择执行符号指令。

## 设计

推荐方案：补全扩展分组表，但暂不改变默认执行集合。

- 在 `test_exec_main` 内按扩展增加局部数组，例如 `ext_i_instruction_table`、`ext_a_instruction_table`、`ext_f_instruction_table`、`ext_d_instruction_table`、`ext_b_instruction_table`、`ext_k_instruction_table`、`ext_v_instruction_table`、`ext_zic...` 等。
- 每个表继续使用现有风格：未编码 Sail constructor 名数组 `.into_iter().map(|name| zencode::encode(name)).collect::<Vec<String>>()`。
- 默认 `instruction_table` 仍只加入现有 `execute_through_instruction_table = ["zSTORE", "zLOAD"]`，避免一次性启用大量路径爆炸或尚未验证的扩展。
- 对需要直接写 `z...` 的临时/已验证集合保持原状或清理为扩展表注释，不扩大行为面。

## 备选方案

1. 只补齐当前 `todo_instruction_table` 中已有构造子的扩展分组。
   - 优点：变更小。
   - 缺点：仍不能覆盖 Sail 中已定义但未列入 todo 的构造子。

2. 从 `sail-riscv/model/extensions` 自动生成分组表。
   - 优点：覆盖完整、减少手抄错误。
   - 缺点：引入生成流程或脚本，不符合当前文件中手写样例风格。

## 测试计划

- 先添加一个针对扩展表内容的单元测试或轻量 helper 测试，验证关键分组能编码出预期 `z...` 名称，并在生产修改前确认测试失败。
- 修改 `isarch_exec.rs` 后运行目标测试。
- 最后运行 `cargo check -p isla-lib`。

## 等待确认

用户已确认直接实现，当前计划已执行完成。
