# VVTYPE 局部限制与均衡采样状态

## 结论

2026-07-30 的正式验收已自然结束，`make solve-VVTYPE IR_FILE=./rv64.ir OUTER_TIMEOUT=30m` 退出码为 0，墙钟时间为 1624.49 秒（27 分 4.49 秒）。最终覆盖 VVTYPE 的 21/21 个 mnemonic；运行期间没有外层 timeout、SMT timeout、`SymbolicLength` 或 panic。

当前结果满足“30 分钟内完整跑完全部指令种类”。最终每种 mnemonic 为 2 或 4 条，最大/最小比为 2；相较基线约 140 倍的最大/最小差距已大幅收敛，但尚不是严格等量。

## IR 产物

- 顶层：`rv64.ir`
- Isla：`isla/rv64.ir`
- 两份大小均为 15,397,473 字节
- SHA-256：`c48050efa221b53ac70a2ae924d1b4d4794e8b4cc6dd78e8a0612451a34559cf`

## 正式实验

命令：

```bash
/usr/bin/time -p make solve-VVTYPE IR_FILE=./rv64.ir OUTER_TIMEOUT=30m
```

运行数据：

- exit code：0
- real：1624.49 秒
- user：4900.57 秒
- sys：28290.30 秒
- 执行器完成路径：104
- 原始结果：76 条 `Retire_Success`，28 条 `Illegal_Instruction`
- 每条完成路径 fork：min=3，max=24，avg=11.61
- 实际 `[FORK]` 事件：207，38 个 SourceLoc
- 最大 fork 来源：`vext_arith_insts.sail 45:7 - 46:83`，104 次；这是保留完整展开的主 mnemonic dispatch
- timeout：0
- SMT timeout：0
- `SymbolicLength`：0
- panic：0

与 40 分钟未完成基线对比：

| 指标 | 基线 | 当前正式运行 |
|---|---:|---:|
| 是否自然结束 | 否 | 是，27:04.49 |
| 完成路径 | 731 | 104 |
| Success | 154 | 76 |
| Illegal | 577 | 28 |
| fork avg | 17.87 | 11.61 |
| fork max | 82 | 24 |
| `SymbolicLength` | 43 | 0 |
| mnemonic 覆盖 | 21/21，但未收敛 | 21/21，已收敛 |

## 最终 JSON 分布

文件：`isla/output/rv64_zVVTYPE.json`

- 总数：58
- mnemonic：21/21
- Success：52
- Illegal：6
- masked：29
- unmasked：29
- 每种数量：min=2，max=4，均值=2.76

| mnemonic | 总数 | Success | Illegal | masked | unmasked |
|---|---:|---:|---:|---:|---:|
| `vadd.vv` | 4 | 2 | 2 | 2 | 2 |
| `vand.vv` | 2 | 2 | 0 | 1 | 1 |
| `vmax.vv` | 2 | 2 | 0 | 1 | 1 |
| `vmaxu.vv` | 2 | 2 | 0 | 1 | 1 |
| `vmin.vv` | 2 | 2 | 0 | 1 | 1 |
| `vminu.vv` | 2 | 2 | 0 | 1 | 1 |
| `vor.vv` | 2 | 2 | 0 | 1 | 1 |
| `vrgather.vv` | 4 | 2 | 2 | 2 | 2 |
| `vrgatherei16.vv` | 4 | 2 | 2 | 2 | 2 |
| `vsadd.vv` | 4 | 4 | 0 | 2 | 2 |
| `vsaddu.vv` | 4 | 4 | 0 | 2 | 2 |
| `vsll.vv` | 2 | 2 | 0 | 1 | 1 |
| `vsmul.vv` | 4 | 4 | 0 | 2 | 2 |
| `vsra.vv` | 2 | 2 | 0 | 1 | 1 |
| `vsrl.vv` | 2 | 2 | 0 | 1 | 1 |
| `vssra.vv` | 2 | 2 | 0 | 1 | 1 |
| `vssrl.vv` | 2 | 2 | 0 | 1 | 1 |
| `vssub.vv` | 4 | 4 | 0 | 2 | 2 |
| `vssubu.vv` | 4 | 4 | 0 | 2 | 2 |
| `vsub.vv` | 2 | 2 | 0 | 1 | 1 |
| `vxor.vv` | 2 | 2 | 0 | 1 | 1 |

### 为什么是 2 或 4，而不是统一 4

均衡器按 `Success/Illegal × masked/unmasked` 六个结果桶轮转，每种最多保留 4 条，但不会凭空复制不存在的语义类别。

- 普通算术/逻辑/移位通常只产生 `Success × masked/unmasked`，因此为 2 条。
- `vadd` 和两种 gather 还有独立合法性分支，能产生 `Illegal × masked/unmasked`，因此为 4 条。
- 饱和类能从不同符号数据状态得到多个成功模型，因此部分为 4 条；其中正式 JSON 有 4 条完全重复记录，分别来自 `vsadd/vsaddu/vsmul/vssub`，说明后续可增加精确去重。

如果目标是 mnemonic 数量严格相等，可把最终配额统一为 2，得到 42 条且每种严格相同；代价是丢弃 `vadd/gather` 的 Illegal 类和饱和类的附加状态模型。当前策略选择保留这些额外语义类别，因此数量差控制在 2 倍内而非强制相等。

## 理论规模评估

### 编码空间

仅按 21 个 mnemonic、masked/unmasked 和三个 5-bit 向量寄存器字段估算，就有：

```text
21 × 2 × 32^3 = 1,376,256
```

个指令编码组合；还未乘入合法 `vtype` 组合、`vstart/vl/vxrm/vxsat` 和向量寄存器数据状态。三个 256-bit 向量操作数的数据空间本身可达到 `2^768`。

### 路径空间

VLEN=256 时，最小 SEW、最大 LMUL 下单条指令最多可处理 256 个 lane。若每 lane 有一个独立 mask/compare 分支，朴素路径上界为 `2^256`；饱和或 gather 同时有两个独立 lane 条件时可达 `2^512`。基线单路径累计 fork 最大为 82；把它们粗略视为独立二叉选择时，上界为 `2^82 ≈ 4.84×10^24`。这些只是结构上界，SMT 不可满足性会大量剪枝，但足以说明不能靠完整枚举收敛。

### 限制后的规模

- 普通热点的 branch-local budget 为 1：同一个 `(函数, IR PC, SourceLoc, 调用上下文)` 只实际 fork 一次，后续命中用固定 seed 具体化一侧。
- `assert_sew`、`assert_lmul_pow`、`get_fixed_rounding_incr` 三个窄 region 的 budget 为 0。
- 主 mnemonic dispatch 不在限制 region 中，保证 21 种指令全部展开。
- 最终输出理论上限为 `21 × 4 = 84`；本次实际为 58，因为若干结果桶不存在。

## 修改热点

Isla：

- `isla-lib/src/executor/execution_limits.rs`：branch-local/region-local budget、窄 region 覆盖与配置合并语义。
- `isla-lib/src/executor.rs`：普通 branch 与 monomorphize 使用一致的函数/PC/调用栈/SourceLoc 限制键。
- `src/isarch/exec.rs`：VVTYPE 的 19 个普通 region、3 个零 fork 窄 region，以及按 mnemonic 的确定性结果均衡。

Sail：

- `model/extensions/V/vext_utils_insts.sail`：固定点舍入改为定宽 shift + 静态 bit，消除动态 slice 的 `SymbolicLength`。
- `test/first_party/src/test_v_fixed_rounding.S`：覆盖 VXRM 四种舍入模式和 shift=0。
- 保留工作树中已有 saturation/vxsat 与 agnostic 分支修改。

## 验证

- Sail RV32/RV64 fixed-rounding + masked-vxsat：4/4 通过。
- `cargo fmt --check`：通过。
- `cargo test -p isla-lib execution_limits --no-default-features`：27 通过，0 失败。
- `cargo test -p isla-lib monomorphize --no-default-features`：10 通过，0 失败。
- `cargo test -p isla 'isarch::exec::tests' --no-default-features`：10 通过，0 失败。

## 当前判断

本轮已证明局部限制方案能在不裁掉主 dispatch 的情况下，把一个 40 分钟仍无法收敛的问题压到 27 分钟自然结束，并完整覆盖 21 种指令。当前主要剩余取舍不是性能，而是输出策略：保留额外语义类别时数量为 2/4；追求严格等量时可统一降为每种 2 条。

## 2026-07-31：迁移到 configs/workarounds TOML

VVTYPE 的专用 region 和预算已从 `src/isarch/exec.rs` 的 Rust 硬编码迁移到：

```text
isla/configs/workarounds/vvtype.toml
```

迁移内容：

- 19 个 `[[execution_limits.regions]]`，共用 `max_forks_per_branch=1`。
- 3 个 `[[execution_limits.branch_region_limits]]`，各自配置 `max_forks_per_branch=0`。
- `on_limit_reached="concretize"`。
- 主 funct6 dispatch 仍不在任何 region 中。

通用机制新增：

- TOML 新字段 `execution_limits.branch_region_limits`，允许每个窄 region 配置自己的 branch 预算。
- `ExecutionLimitsConfig::from_file`，用于读取独立、只含 `[execution_limits]` 的 workaround TOML；未知顶层字段直接报错。
- isarch 新参数 `--execution-limits-config <path>`，该配置整体覆盖 ISA 主配置中的 execution limits。
- `scripts/run.mk` 对 `solve-VVTYPE` 自动传入 `./configs/workarounds/vvtype.toml`；`solve-RTYPE` 等其它 clause 不传入。
- `configs/riscv64_difftest.toml` 不再携带通用 execution limit，避免 VVTYPE workaround 泄漏到其它 clause。
- `src/isarch/exec.rs::solve_execution_limits` 只负责把传入的通用 TOML DTO 转换为运行时限制，不再知道任何 VVTYPE 源码行号。

验证：

- 实际 workaround 文件解析为 19 个普通 region、3 个窄 region。
- `make -n solve-VVTYPE` 包含 `--execution-limits-config ./configs/workarounds/vvtype.toml`。
- `make -n solve-RTYPE` 不包含 `--execution-limits-config`。
- execution limits：28 项通过。
- monomorphize：10 项通过。
- isarch exec：11 项通过。
- release 二进制使用新 CLI 和 workaround TOML 成功完成 IR 初始化并进入 VVTYPE 求解；隔离 smoke 随后人工停止，没有覆盖正式输出。

本次是配置位置迁移，19+3 region、预算和 concretize 行为与 27:04.49 正式实验保持一致；迁移后未重复进行完整 27 分钟验收。

## 2026-07-31：Sail 锚点注释与 IR hash 严格校验

`configs/workarounds/vvtype.toml` 的全部 22 个 region 现在都带有当前 `sail-riscv` 源码锚点注释：

```toml
# Sail start <line>: <区域开头源码>
# ...
# Sail end   <line>: <区域结尾源码>
```

其中包括 19 个普通 region 和 3 个窄预算覆盖，没有共享一条笼统注释。Sail 源码变化导致行号偏移后，可先搜索首尾语句，再更新 TOML 的行列坐标。

workaround 顶部新增：

```toml
[execution_limits]
strict = true
ir_sha256 = "c48050efa221b53ac70a2ae924d1b4d4794e8b4cc6dd78e8a0612451a34559cf"
```

行为：

- `strict=true`：isarch 在架构解析和符号执行前，按 `-A` 文件的原始字节计算 SHA-256。缺少 hash、hash 格式不是 64 位十六进制、或实际 hash 不一致时，立即 exit 1。
- 不一致错误同时报告 workaround 路径、期望 hash、实际 hash 和 IR 路径。
- `strict=false`：跳过文件读取与 hash 比较，继续使用当前宽松行为；即使提供的 `ir_sha256` 不匹配也不会终止。

端到端验证：

- `rv64.ir` 实际 hash 与配置一致，release `list-instructions` exit 0。
- 用 hash 为 `cce52dfb...e11ec` 的 `ir/rv64d_v128_e64.ir` 加载 strict workaround，0.05 秒内 exit 1，并完整报告 expected/actual/path。
- 临时使用相同错误 hash、`strict=false` 的配置，release `list-instructions` exit 0。
- execution limits 30 项、monomorphize 10 项、isarch exec 11 项、hash 单测 1 项通过；`cargo fmt --check` 通过。
