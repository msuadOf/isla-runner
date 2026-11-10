# Isla 对 Sail 模型通用：模型语义迁出（状态摘要）

| 项 | 状态 |
| --- | --- |
| 原则 | 用户 2026-11-10 明确：“通用”指对 Sail 模型通用。PTE、MMU、特权级、CSR 字段合法值、模型函数名等限制做成配置或在模型侧实现，不能硬编码进 Isla（含 isarch） |
| 审查 | [review-20261110.md](review-20261110.md)（Codex 只读审查集成分支 c1559ad8） |
| 阶段 | 合法初态域、RVV 初态规则已迁到配置并提交（集成分支 `31a36d2f`）；随机数待模型侧实现；映射名后续 |
| 验证 | 求解器等价证明：新配置约束与旧规则双向等价（4 个反例查询都是 unsat）；回归 RTYPE、C_LD、CSRReg、JALR、C_FLW、FLI_S、VSETVLI 的状态和用例数与改前一致；`make solve-MRET` 通过；isla-lib 单元测试 845 通过 |

## 取舍（Claude，2026-11-10）

| 写死的模型语义 | 处理 |
| --- | --- |
| `Rv64Domain`：特权枚举、`hartSupports(Ext_*)`、SXL/UXL/MPP 的位置和取值 | 新增通用的初态阶段约束配置项（复用 SMT 表达式解析器）；特权集合用现有 `symbolic_registers.allowed`；不做能力探测，配置直接写允许值；先用求解器证明新旧等价，再删旧代码 |
| RVV `vtype`/`vl` 初态规则（既有） | 用同一配置项迁出，VLEN/ELEN 在配置里写具体数 |
| `get_16_random_bits`（`src/isarch/platform.rs`） | 用户提议：sail-riscv 用 `$ifdef SYMBOLIC` 把它定义成 `undefined_bitvector(16)`；重新生成 IR 后删掉 `platform.rs` |
| 编码/译码/汇编映射名（`encdec_forwards`、`ext_decode`、`assembly_forwards`，既有） | 后续再做，本轮不动 |

## 实现（`31a36d2f`）

- 新增配置项 `[constraints].initial`：一组 SMT 表达式，复用 reset 约束的解析器；在全部初态注入之后、首次可满足性检查和编码预检之前施加。
- 特权集合用现有的 `symbolic_registers.cur_privilege.allowed`。
- 16 份 `configs/riscv64*.toml` 加入等价约束，并注明对应的 Sail 源位置。
- 删除 `Rv64Domain`、能力探测、`initial_state_rv64_domain` 以及 RVV 推导代码。生产代码里不再出现 `zMachine`、`zhartSupports` 等模型名字，测试夹具中仍保留。
- 正在跑的 226 clause 实测用的是改前的二进制 c1559ad8；由于新旧约束等价，结果同样适用于新代码。
