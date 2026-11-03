# Sail 类型约束 memo 复用独立审查

允许在同一 Sail 二进制、标准库、Isla 插件、编译期 Z3 及对应配置下，将上一轮成功生成的 memo **独立复制**给新批次各配置，再完整运行原严格检查与生成。它缓存相同类型约束查询的结果，不是跳过模型解析、类型检查、严格选项或 IR 生成。不得共用一个可写 memo 路径。

核查入口为当前实际工具树 `sail-src/src/lib/constraint.ml` 与 `src/bin/sail.ml`：

- `constraint.ml:252-272` 的 `smtlib_of_constraints` 构造实际 SMT-LIB 文本，包含 solver header/footer、abstract/变量声明、extra 断言、当前完整约束、check-sat，求值查询另有 get-model。变量按 v0…编号以复用 alpha 等价查询（`:161-175`）。
- `call_smt'` 在 `:367` 对上述整个文本 `Digest.string smt_file`，在 `:370-373` 精确查 key；未命中才调用求解器并保存该结果。SAT/UNSAT/UNKNOWN分别缓存，不把UNKNOWN改为证明成功；其指数后备查询会生成自身的完整文本和另一key。
- 唯一值缓存在 `:587` 使用 `Digest.string (smt_file ^ 求解目标变量表达式)`，避免相同约束不同目标变量混用；只有另一次排除该值的查询得到UNSAT才缓存正的唯一值（`:600-608`）。当前五份来源缓存均未含此类条目。
- 缓存文件只有16字节digest、结果tag与可选整数，**不存**模型commit、配置、Sail/标准库/插件/Z3版本。因此不能从缓存自身推断来源。配置与源变化须最终反映在查询中；本次仍要求严格固定全部工具与对应配置，并保留独立来源manifest。
- `load_digests_err/save_digests` 在 `:280-322` 读/写整个文件，无锁、无并发合并，保存用 `open_out_bin` 直接截断重写。`sail.ml:760/768` 在编译前加载、编译后保存；错误退出也可能保存（`:806`）。来源必须选已完成成功批次，并按配置复制到独立路径。

[缓存来源审计](memo-cache-audit.json)检查 `8ad5e8e` 的 ordinary、RV64 V128、RV32、V256、V512 五份文件：二进制记录完整、tag合法、各表无重复digest，全部来源进程退出0且源码未变。分别有9522、18762、18772、18857、18864条记录；含46/134/137/134/135条UNKNOWN，复用它们不会将未证明变成证明，旧输入的可复用回答及后备流程保持。文件内不保留原SMT文本，本次没有从digest反求或重放全部旧查询，不能宣称重新验证了每个缓存答案。

新一轮每个配置应记录：来源批次/模型commit、对应config与工具manifest、来源路径/SHA-256、独立目的路径、复制后执行前SHA-256与独立文件身份、完整实际命令与strict选项、结束后cache SHA-256、源cache未变、源文件未变、退出码及生成IR哈希。普通严格检查用上一轮ordinary cache，四份SYMBOLIC各用同配置来源；保持同编译期Z3命令/参数与环境。不合并不同配置缓存，不修改tag或新增假条目，不因cache命中就继承旧PASS；新commit仍以实际新命令/IR/完整退出结果重新签收。

工具源文件哈希：`constraint.ml` = `e3623f1c5d5c7fc0d613dac80e9320e641d12f8c05c023560779a4db6f598c30`；`sail.ml` = `1218a4fad073ced354609f5fbfbf76681e7d15fd157eff75ded3aa1e4090711b`。实际Sail binary SHA-256 `373a37c2…`、149工具文件与编译期 Z3 4.16.0 `a7eac84c…` 已在旧批次来源审计固定；新批次须逐项一致。本结论不涉及 Isla 运行时浮点求解、其官方 Z3 共享库或7200秒预算的缓存。
