## 背景
当前 `zC_ADD` 的问题不是没有执行路径，而是路径先执行完，再在导出阶段用 `get_assembly_name/get_assembly_encdec` 反推汇编与编码；如果求解器给出的模型落在不满足 mapping guard 的点（例如 `rs2 = zreg`），这条路径就会因为 `当前汇编：None` 被丢弃。`C_ADD` 的合法性条件定义在 Sail mapping 上，而不在 `execute` 子句里：`sail-riscv/model/extensions/C/zca_insts.sail:542-551`。

相关事实：
- `C_ADD` 的约束在 Sail 中是：`rs2 != zreg & currentlyEnabled(Ext_Zca)`，位置：`sail-riscv/model/extensions/C/zca_insts.sail:542-551`
- 这些 guard 在 IR 中仍然存在，但已经 lowering 成布尔判断与跳转，不再是可直接读取的结构化约束对象，位置：`isla/rv64d.ir:255611-255628`
- 当前执行入口在 Rust 中直接构造符号 ctor 参数，然后调用 `zexecute`，位置：`isla/isla-lib/src/isarch_exec.rs:176-275`
- 仓库已有可复用的前向映射/编码接口：
  - `get_assembly_encdec` / `get_assembly_encdec_forwards`：`isla/isla-lib/src/isarch.rs:72-115`
  - `get_symbolic_arg_all`：`isla/isla-lib/src/isarch.rs:440-469`
  - `ir_assembly_names_to_InstructionMap_step1_symbolic_exec`：`isla/isla-lib/src/isarch.rs:557-676`
- Sail 侧已有 `isla_` 风格符号执行入口先 decode 再 execute 的模式：`isla_footprint_no_init` / `isla_footprint`，位置：`sail-riscv/model/main/main.sail:31-59`；这些入口会被 isla plugin 作为初始调用保留：`isla/isla-sail/sail_plugin_isla.ml:356-362`

目标是把“是否合法 encdec/mapping”的判定前移到 `zexecute` 之前，并把可选路线都列出，供后续筛选。

---

## 方案一：Rust 侧预筛候选参数
### 核心思路
在 Rust 里复用现有 encdec/mapping 执行逻辑，先生成候选参数，再在进入 `zexecute` 前做 pre-check；只有能通过 `zencdec_forwards/zencdec_compressed_forwards` 或对应 mapping 的候选，才继续真正的符号执行。

### 实现切入点
- 现有执行入口：`isla/isla-lib/src/isarch_exec.rs:176-275`
- 候选参数生成：`isla/isla-lib/src/isarch.rs:440-469`
- 编码前向检查：`isla/isla-lib/src/isarch.rs:72-115`
- 参考已有“先前向跑一遍再保留 checkpoint”的模式：`isla/isla-lib/src/isarch.rs:557-676`

### 复用点
- `get_symbolic_arg_all`
- `get_assembly_encdec`
- `get_assembly_encdec_forwards`
- `ir_assembly_names_to_InstructionMap_step1_symbolic_exec`

### 优点
- 不需要改 Sail 源语义
- 不需要从 IR 逆向提取 guard
- 直接复用现有 encdec/mapping 逻辑，语义贴近 Sail
- 改动范围主要在 Rust，构建链最稳定

### 缺点
- 更像“前置过滤”而不是“真正把约束压进最初的 solver”
- 如果候选空间很大，可能引入枚举成本

### 适用范围
- 先解决 `C_ADD`
- 可自然推广到 `C_MV / C_JR / C_JALR / C_EBREAK` 这类共享编码点的压缩指令

### 推荐度
高。最务实，适合先落地验证。

---

## 方案二：新增 Sail 的 opcode 级符号执行入口
### 核心思路
仿照 `isla_footprint_no_init(opcode)` 新增一个 `isla_...` 风格入口，让符号输入不是 clause 参数，而是 16-bit/32-bit opcode。这样约束先经 `encdec_compressed/encdec` + mapping guard 生效，再进入 `execute`。也就是说，合法性由 Sail 自己的 decode/mapping 机制决定，而不是 Rust 在外部猜测。

### 已有模式
- 现成入口：`sail-riscv/model/main/main.sail:31-59`
  - `isla_footprint_no_init(opcode)`：`reset` → `decode` → `execute`
  - `isla_footprint(opcode)`：`init_model` → `isla_footprint_no_init`
- 对应 IR：`isla/rv64d.ir:382268-382334`
- plugin 保留入口：`isla/isla-sail/sail_plugin_isla.ml:356-362`
- decode 路径：`sail-riscv/model/postlude/decode_ext.sail:13-15`

### 可能的入口设计
- `isla_exec_opcode_no_init(opcode)`：`isla_reset_registers()` → `decode` → `execute`
- `isla_exec_opcode(opcode)`：`init_model("")` → `isla_exec_opcode_no_init(opcode)`
- 如需只关注 compressed，可提供仅接收 `bits(16)` 的专用入口

### 优点
- 约束来源最“正宗”：直接走 Sail `encdec_compressed` / `encdec` 的 mapping guard
- 不需要在 Rust 手工重建 `rs2 != zreg & currentlyEnabled(Ext_Zca)`
- 对所有类似“先 decode 再 execute”的场景都通用，而不仅是 `C_ADD`

### 缺点
- 需要改 Sail 源，并重新生成 `.ir`
- 现有 `isarch_exec` 以 clause ctor 为输入，若切到 opcode 模式，需要在 Rust 侧增加新的调用路径
- 输出会从“给定 clause 参数求一个模型”变成“给定 symbolic opcode，求所有可 decode 的指令模型”，与当前数据流有结构差异

### 适用范围
- 你想让“合法性”完全由 Sail decode/mapping 定义
- 你接受入口从“按 clause 名称枚举”部分切换到“按 opcode 驱动”

### 推荐度
高。语义最干净，但工程改动比方案一大。

---

## 方案三：新增 Sail 的 clause 级预检入口
### 核心思路
仍然以 `C_ADD(rsd, rs2)` 这类 clause 参数为入口，但在 Sail 里新增一个 `isla_...` 风格函数，先对该 instruction 走 `assembly_forwards_matches` / `encdec_compressed_forwards_matches` 或直接尝试 `encdec_compressed_forwards`，只有通过预检的 instruction 才调用 `execute`。

### 依据
- IR 中已有：
  - `zassembly_forwards` / `zassembly_forwards_matches`
  - `zencdec_compressed_forwards` / `zencdec_compressed_forwards_matches`
  见：`isla/rv64d.ir:50417-50431`
- Sail 侧已有 `assembly_forwards_matches` 的使用模式：`sail-riscv/model/postlude/insts_end.sail:41-42`

### 可能入口设计
- `isla_exec_clause_if_mappable(insn : instruction)`：
  - 若 `assembly_forwards_matches(insn)` 或 `encdec_compressed_forwards_matches(insn)` 成功，则 `execute(insn)`
  - 否则直接返回失败/false/option-like 结果
- 对 `C_ADD` 可先作为特例从 clause ctor 传入，再逐步推广

### 优点
- 依然保留“从 clause 参数直接起步”的工作流
- 预检逻辑被放在 Sail/IR 这一层，而不是全放到 Rust
- 比 opcode 入口更贴近当前 `zC_ADD` 的调用方式

### 缺点
- 本质仍然是“先检查是否可映射，再 execute”，不是直接读取原始 `when` guard
- 需要确认 Sail 源层是否能直接方便地使用这些 `*_forwards_matches` 接口；若源层不可直接写，可能仍需依赖编译后的 IR 调用路径
- 相比方案二，语义仍然不是“先 decode 再 execute”，而是“先验证 instruction 是否可编码/可汇编，再 execute”

### 适用范围
- 你希望保留当前 clause 驱动的数据流
- 但又想把前置合法性检查从 Rust 下沉到 Sail/IR 入口层

### 推荐度
中。是折中方案，但实现边界要先确认。

---

## 方案四：Rust 侧直接给 solver 注入手工 guard
### 核心思路
继续从 `symbolic_args_from_TYPEs` 生成符号参数，但在这里按 `instruction_name` 手工写 guard 表，把 `zC_ADD => rs2 != zreg && Ext_Zca` 这类条件直接压入 solver 或通过字段覆写/约束实现。

### 切入点
- `isla/isla-lib/src/isarch_exec.rs:176-243`
  - 这里已经存在 `hook_overwrite_map` 风格的特判入口

### 优点
- 对 `C_ADD` 做 PoC 最快
- 不需要改 Sail，不需要大改当前执行框架

### 缺点
- 与 Sail 源重复维护，最容易漂移
- 每条压缩指令都要手工补表，扩展性差
- 一旦 guard 复杂，Rust 侧复刻容易出错

### 适用范围
- 仅用于快速验证思路
- 不适合作为长期方案

### 推荐度
低。只适合临时 PoC。

---

## 方案五：从 IR 中逆向抽取 mapping guard
### 核心思路
直接分析 `rv64d.ir` 中 `zC_ADD` 对应的 guard 跳转，把 lowering 后的布尔表达式重新恢复成结构化约束，再把这些约束前置到执行前。

### 依据
- `C_ADD` guard 在 IR 中可见：`isla/rv64d.ir:255611-255628`
- 其中包含 `zneq_anythingzIB5zK(..., zzzreg)` 和 `zcurrentlyEnabled(zExt_Zca)`

### 优点
- 一旦实现成功，理论上能统一处理大量 mapping guard
- 不依赖硬编码单条指令

### 缺点
- 当前仓库没有现成结构化 API
- 需要做 IR 模式识别/控制流回溯，工程复杂度最高
- 对 IR 生成细节高度敏感，后续维护风险大

### 适用范围
- 只有在你明确想做“通用 guard 提取框架”时才值得考虑
- 不适合作为先修复 `C_ADD` 的第一步

### 推荐度
低。长期研究向，不适合当前问题优先级。

---

## 建议排序
### 如果目标是“尽快落地修复 C_ADD”
1. 方案一：Rust 预筛候选参数
2. 方案四：Rust 手工 guard（仅 PoC）

### 如果目标是“语义上尽量尊重原始 Sail 设计”
1. 方案二：Sail opcode 入口
2. 方案三：Sail clause 预检入口

### 如果目标是“做成通用框架”
1. 方案二：Sail opcode 入口
2. 方案五：IR guard 抽取

---

## 关键文件
- `isla/isla-lib/src/isarch_exec.rs`
- `isla/isla-lib/src/isarch.rs`
- `sail-riscv/model/extensions/C/zca_insts.sail`
- `sail-riscv/model/main/main.sail`
- `sail-riscv/model/postlude/decode_ext.sail`
- `sail-riscv/model/postlude/insts_end.sail`
- `isla/isla-sail/sail_plugin_isla.ml`
- `isla/rv64d.ir`
- `isla/src/execute-function.rs`
- `isla/src/client.rs`

## 验证建议
### 公共验证
1. 重新生成/使用对应 `.ir`
2. 运行：`cd isla && make run`
3. 检查 `output/rv64d_zC_ADD.json`，确认不再只有空 `gen`
4. 对照日志确认无效模型是在 execute 前被过滤，或根本不会进入 execute

### 回归验证
- 同组压缩指令：`C_MV`、`C_JR`、`C_JALR`、`C_EBREAK`
- 检查 `rv32d` 与 `rv64d` 两套输出，避免只对单一 XLEN 生效

### 方案二/三额外验证
- 确认新增 `isla_...` 入口被保留到生成 IR 中
- 确认 Rust 侧可以通过函数名直接调用该入口，参考：`isla/src/execute-function.rs:110-170`
- 如走客户端式 opcode 驱动路径，可参考：`isla/src/client.rs:108-152`
