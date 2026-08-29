# RISC-V ISA 符号执行路径爆炸处理原则

## 目标

目标不是简单减少路径数，而是在符号执行 `sail-riscv` 建模的 RISC-V ISA 时，尽量遍历 ISA 规定的真实细节，同时避免 Sail/Rust 实现方式额外制造的分支。

`zSTORE` / `zLOAD` 当前暴露出的 VMEM、PTW、PMP、PMA、MMIO、misaligned 复杂度，是后续处理同类 ISA 语义的试点。

## 最高优先级：语义等价

- 优化后的行为必须等价于同一外部配置下的原 Sail/IR 语义。
- 如果不能证明等价，不能静默返回近似成功结果。
- 不支持的情况必须 fail closed：
  - 优先返回原语义允许的 `Err(...)`。
  - 其次回退原 IR。
  - 如果既不能构造正确错误也不能安全回退，允许 panic/internal error。
- 行为应学习 Isla 现有 primop 的风格：遇到无法覆盖的语义边界时显式暴露问题，而不是吞掉问题。

## 优化方向

优先把实现分支转化为 SMT AST 关系表达式：

- 纯布尔公式、区间关系、位向量比较、小枚举选择，适合下沉到 SMT。
- executor 不应因为短路 `if` / `match` / `jump` 枚举所有实现路径。
- 对 Z3 不擅长或没有直接表达的操作，先评估是否可拆成更小的等价 summary；仍不可行时再考虑回退 IR、改 Sail 模型或显式假设。

## Isla 与 sail-riscv 的取舍

- 如果 Isla 和 `sail-riscv` 两边都能解决，优先改 Isla，尽量不动 `sail-riscv`。
- 如果路径爆炸来自 `sail-riscv` 的实现写法，而不是 ISA 语义本身，并且 Isla 侧等价 summary 代价过高，可以考虑修改 Sail 建模方式。
- 修改 Sail 模型时仍必须保持规范语义等价，不能为了少 fork 改变 ISA 行为。
- 不应把大块 Sail 函数粗暴搬到 Rust 后简化语义；应拆成小的、可证明等价的 summary 或 primop。

## 外部假设的使用

全局假设只能作为保底，不是首选方案。

允许的假设示例：

- PMP 数量在符号执行 init 时显式设为 0，从而关闭 PMP。
- PTW 使用 one-shot 或 identity translation 前提。
- symbolic memory range 显式限制在普通 RAM、非 MMIO、aligned 地址范围。
- 对 concrete misaligned 访问，只有在外部明确声明本场景不支持 misaligned split 时，才允许直接返回规范允许的 alignment fault。
- `ISLA_RISCV_ASSUME_PMP_OFF=1` 这类开关属于诊断或显式 init 前提，不能替代完整 PMP summary，也不能作为默认语义。

要求：

- 假设必须来自显式配置、init 约束或测试前提。
- 假设必须写入文档和测试记录。
- 如果假设影响 solver 可见状态，应添加对应 SMT 约束。
- builtin 不能在内部偷偷制造这些事实。

## 证据要求

每个优化都需要记录：

- 爆炸来源：函数名、调用链、IR/source 位置、fork 数、耗时、profile 证据。
- 语义边界：支持哪些 access/config，哪些情况回退或报错。
- 对照结果：builtin on/off 的 `ret_val`、memory events、solver sat/unsat、fork 数。
- 取舍理由：为什么改 Isla、改 Sail、回退 IR，或使用显式假设。

没有证据的函数先保持 IR。
