# 审查修复交付（2026-10-08）

> 后续扩大复审：同一 `4b141eb` 又发现三个 P1 和一个 P2，见[最新复审](rereview-20261008.md)。本文记录三个既有修复及其限定验证，不代表整个分支无回归。

用户授权修复，并要求后续提交采用 `fix(scope): 中文说明`。修复已接入 Isla `refactor/general-support-20261007`，从 `2792afd` 快进至 `4b141eb05572783a9f3877fd4d80aa2ee63ca986`，未 push、未移动父仓库 gitlink。

| 提交 | 内容 |
| --- | --- |
| `3074b7b` | `fix(mixedbits): 修复拼接位向量的算术与转换兼容性` |
| `a906c7a` | `fix(smt): 支持超出宿主位宽的模型值物化` |
| `4b141eb` | `fix(riscv): 排除未实现的 MPP 模式并保留模型复位态` |

## 实现与语义

整数加减、原生 IEEE/整数到浮点转换、旧 SoftFloat helper 入口复用 `replace_mixed_bits`，保留 append 的具体字段切片优化。只有位向量消费者增加表示兼容性，普通 FP 运算的类型接受域保持。

`Val::from_bits_slice` 以低位在前的位数组构造具体值：宿主宽度内仍返回 Bits，超宽返回高位在前的 Concrete MixedBits。它同时供字面量解析和 Model 物化使用，分段顺序与原长字面量解析器相同，避免额外字符串往返。Model 对 Symbolic、MixedBits 与复合值递归使用此表示；Arbitrary 仍选择原来的零值，不因此开启 model completion。mapping 继续使用同一模型物化完整前态，没有跳过宽寄存器或固定向量状态。

MPP 字段域为：0 保留、1 仅在支持 S 时允许、2 排除、3 保留。独立复核指出当前 Sail 从全零初始化 mstatus，无 U 时也存在 MPP=0 的 reset 初态；因此不把 CSR legalize 的写后域当作完整可达状态域。manifest 用 `mstatus-mpp-reset-exception` 标记无 U 时保留 0 的例外，原 reset fixture 仍直接测试 0。第三项初始草稿曾错误排除该状态，已在接入分支前修订；草稿不是交付版本。本修复不宣称完整 mstatus 组合的可达性或硬件 WARL 等价。

独立 gpt-6-astra high 对两个 P1 修复静态复核无阻塞，指出并复核解决了上述 reset 边界。审查没有代替动态验证。

## TDD 与验证

实施前的有效红灯：拼接后整数加减 8 例 Type；IEEE、整数转 FP、旧 helper 消费者 Type；Model 的 B64 65 位、B129 130 位转换失败与 512 位 arbitrary 宿主断言失败；实际 collector 在 256 位丢失用例；MPP 能力域矩阵失败。新增测试先暴露问题再修改生产代码。探针初次编译/类型准备失败日志保留，不归因为生产代码问题。

精确提交树的验证通过：

- isla 库 81＋isarch bin 25；其中真实 collector 在 128/129/256/512 位下检查用例非空，验证 not_bits 执行后的逐位前后态关系。
- 持久集成测试 8 项算术、2 项原生 FP 转换、3 项模型物化。模型测试覆盖 B64/B129、1 至 512 位、三类非零模式、高位与段序、MixedBits/结构体/list/vector/ctor，以及 completion 开关下的 arbitrary 值。
- 旧 helper 组合测试 1、既有 primop 67、位向量 47、executor 85、fmtval 2、模型缓存 3。
- 默认 `cargo check`、`cargo fmt --all -- --check`。
- V128 和 V256 的实际 `make solve ALL=MRET` 均退出 0，各 4 gen＝3 Retire＋1 Illegal；完整状态各 101 个字段，vr0 前后态位宽与 IR 相符。

带入原浮点剩余的组合版本亦通过：库 85＋bin 25、同一套集成测试 8＋2＋3、fmt；V128/V256 MRET 各退出 0、4 gen，状态各 102 个字段（包含已有浮点层的 fcsr）。精确树与组合使用各自 IR，不将不同 IR 的输出作为跨版本等价证明。

测试统一离线、`-j 8`、`--test-threads=1`，特性 `itrace,smt-thread-interrupt`，独立缓存为 `.worktree/general-review-20261007/cargo`。MRET 命令：

```sh
CARGO_TARGET_DIR=../general-review-20261007/cargo CARGO_BUILD_JOBS=8 CARGO_NET_OFFLINE=true \
  make solve ALL=MRET THREADS=1 ITRACE=1 OUTER_TIMEOUT=60s SOLVE_TIMEOUT=50s TASTIC=qfaufbv
```

V256 再加 `IR_FILE=./ir/rv64d_v256_e64.ir`。单测用系统 Z3 4.13.3，Make 用 Homebrew Z3 4.16.0；命令、源版本、二进制/IR/配置哈希见 [版本证据](fix-evidence/provenance.json)，四组输出见 [smoke 汇总](fix-evidence/smoke-summary.json)，定向命令见 [最终检查](fix-evidence/final-checks.json)与[组合检查](fix-evidence/combined-checks.json)。

本轮没有重跑全 clause、全库或硬件差分；审查轮两版全库的既有 Z3 enum sort 重名失败没有修复，也未迁为全量 PASS。此前缓存局部性能证据保持其原受测范围，本轮没有新的端到端性能结论。

## 工作树与提交边界

修复在 `.worktree/isla-general-fix-20261007` 干净候选中实施。组合先在 `.worktree/isla-general-fix-combined-20261007` 验证，再带入原通用工作树；两者 995 个跟踪文件/链接逐项一致，原通用索引归于新 HEAD 且无暂存内容。其未提交浮点实现仍保留。

原浮点 float.rs 已支持 MixedBits 并移除旧 helper，最终内容原样保留；新通用 legacy 回归附在对应旧实现文件中，不造成完整浮点组合的测试编译依赖。smt.rs/target.rs 三方合并保留 scalar_sort、fcsr 等浮点剩余；exec.rs 两方在同一位置新增测试，已保留双方测试块，浮点生产逻辑未改。原始剩余补丁随基线变化而重定位，不声称 diff 字节仍相同。

原 `isla/` 的 HEAD、完整索引及所有原 dirty/untracked 文件哈希保持不变，其他浮点分支没有移动；核验见 [工作树证明](fix-evidence/after.json)、[合并说明](fix-evidence/migration-prepared.json)。精确修复补丁见 [fixes.patch](fix-evidence/fixes.patch)。

审查发现已按以上范围修复并复验；历史 [审查报告](report.md) 与原失败证据仍按 `2792afd` 保留。
