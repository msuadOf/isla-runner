# P2 helper 全套回归（2026-09-26）

本包只验证浮点 helper 普通 Sail 函数体的数值、五位 flags 与未知输入路径；不把 helper 样例替代指令状态或官方 77 项验收。输入、包装与 runner 源码沿用已归档的 D 回归体系，构建和运行脚本置于 `tools/solve_fix_helpers/`，所有大产物留在忽略的 `isla/target/float-solve-evidence/`。

## 受测版本与入口

- P2 冻结模型/Isla 源的 manifest SHA-256 为 `128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346`。额外保留四个被 DCE 的旧窄整数 helper 后，完整 helper 诊断 IR SHA-256 为 `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c`。它与 P2 正式候选 IR `d86655a4…` 使用同一冻结源码，但哈希不同；以下数值结论只对应完整 helper 诊断 IR。
- 历史基线 IR SHA-256 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`，未知入口小 IR SHA-256 `bde14b624d233ef9f841e661d05becc71c4aef9151a98b8033de566cb107bc4e`。调用包装器只附加 79 个 `zd_probe_*` 与 277 个未知入口函数到测试副本，wrapped IR SHA-256 `4ddbbb0d8872ae6591a6ad74ebc47a2056fd130536f1fa912c218ef6a242a031`；不改正式 IR。
- 三个 runner 均从本批 P2 冻结 `isla-lib` 新建 Cargo crate、离线构建，不复用历史二进制。D/未知/legacy 二进制 SHA-256 分别是 `105517d17d4d70d6ee8092fc7d2bd42b18acbb225958323148df13f8ca1717bc`、`838bb0c41cc41f255f3b385a596db64d3c50ec873bcdf86e81f3cd11d7c423f2`、`9536bc5b521b43efacf4f7b09ebecb63d5cbb5ad9d3c7afccb7b471a2a471ddd`。固定源码和输入哈希逐项见 `isla/target/float-solve-evidence/helper-p2-full-v1/reports/summary.json`，原始构建、执行日志与输入副本在同目录。

复跑入口：

```sh
python3 agents/float_support_review/tools/solve_fix_helpers/run.py \
  --repo . --p2 <P2 冻结目录> --candidate-ir <P2 full helper IR> \
  --baseline <6fc39efd 基线 IR> --unknown-ir <历史未知入口 IR> \
  --unknown-inputs <已归档未知输入目录> --out <空的忽略证据目录>
```

脚本要求输出目录为空，保存每个输入的原路径与 SHA-256，并在各组用不同文件名 staging；逐组 600 秒外限。每例的 runner 验证普通函数实际进入、SAT、恰好一条完成路径，以及完整结果 bits/五位 flags 与独立参考的差异 UNSAT。未知输入组验证普通体进入、SAT 和单完成路径，不把未知结果具体化为数值 oracle。

## 结果

| 组 | 实际/预期 | 退出 |
| --- | ---: | ---: |
| 未知 f16/f32/f64 | 90/90、96/96、91/91 | 各 0 |
| 67 原 helper | 67/67 | 0 |
| 估算定向/扫点/特殊值 | 350/350、1618/1618、420/420 | 各 0 |
| 原 12 体与窄化边界 | 39/39、24/24 | 各 0 |
| 旧 SoftFloat 测试迁移 | 35/35 | 0 |

完整报告 `status=PASS`，十组每项的输入/runner/日志哈希、命令与耗时在 `isla/target/float-solve-evidence/helper-p2-full-v1/reports/summary.json`。专属 [闭包检查器](tools/solve_fix_helpers/check_closure.py)确认旧 79 个声明与函数体全齐、原 12+新 67 的划分正确、当前 94 个 `riscv_*` 声明均有函数体且无缺体模型调用；新增 15 个中，九个是原有白名单，六个是本轮审定的 `_pure` 向量窄整数适配。报告位于同目录 `reports/static-closure.json`。旧 `check_d_ir.py` 固定九项新增白名单，因此对该版本只报告六个已审 `_pure` 名字为“多出”，不代表缺体或数值失败。

## 历史中间产物与限制

原 P2 IR `d86655a4…` 因调用树裁剪，没有 `riscv_f16ToI16/Ui16`、`riscv_f32ToI16/Ui16` 四个旧函数体；直接用原 79 包装器时在首个缺名处断言失败。对此保留 `helper-p2/reports/summary.partial.json`。在不改变该 IR 的诊断包装下，其余 277 未知、67、350+1618+420 和 legacy35 已先通过，报告为 `helper-p2-partial-r2/reports/summary.json` 的 `PARTIAL_PASS`，未把未跑的旧 12 体算 PASS。首次 partial 脚本曾把 legacy `cases.tsv` 覆盖 D 的同名输入，导致 35/67 计数不符；输入分名 staging 后在新目录重跑，首次失败仍保留于 `helper-p2-partial/`，不是模型反例。

## 最终 MixedBits runtime 复验

MixedBits 修复后的冻结 Isla 库以 `isla-lib/src/primop.rs` SHA-256 `6c6d5a4248d9874405bbc48f850f5c32b77e60f0762212244e1a173fa13f4a20` 与 `ir.rs` SHA-256 `d26e7923712ccf214b7b7dc47d817b66a49e70d11c8c7fdcb9ef171c832c2562` 标识，与最终官方 stage 的 `isla-lib` 逐文件相同。同一 c5cbb0… 完整 helper IR 和相同 wrapped IR/输入，用该库重新构建三个 runner。未知 f16/f32/f64 首次已分别 PASS 90/96/91；原归档 D runner 的首个 `riscv_f16Add` 在 SMT 结果及 flags 差异检查 UNSAT 之后，因具体化返回 `Val::MixedBits([Concrete 1b, Concrete 1b, Concrete 3b])` 而触发旧 runner 的“只接受 Val::Bits”断言。首次结果在 `helper-p2-full-mixedbits/`，这不是浮点值反例。

最终复跑只对 D/legacy runner 的**外部构建副本**加全 Concrete MixedBits 规约：按原片段顺序以 `BV::append` 拼成同宽 `Val::Bits`，若片段仍含 Symbolic 则明确 panic；SAT、普通函数 trace、单完成路径、完整 bits/flags 的 SMT 差异 UNSAT 和具体值断言仍全部保留。归档 runner 源文件与 Isla runtime 未因测试适配而修改。构建副本和原源码各自的 SHA-256、适配标记及命令在 `isla/target/float-solve-evidence/helper-p2-full-mixedbits-r2/reports/summary.json`；报告 SHA-256 为 `c6ccdd4c00cbfc8fa8a4369baab441e78b1d49f6abfa97bd673c4c3a15634b29`。最终三 runner SHA-256 为 D `b3b74aae207f9cf67c839eef30f34ce6f3a2e10e8ec0474b85b153ff60ae804d`、未知 `aa1345ab4ae39eb8c32dd4b0559cf715f94cb73a3cf0cb14995a38d9c6e53e66`、legacy `f7469bae7d312e880fb3881e90d9d9afa4b23917cd516da19ce62fae27ed0a03`。十组再次全部 exit 0、逐项 PASS，数量与上表相同。

这三 runner 的值路径使用 `execute_ir_function` → `Model::get_val`、`smt_value`/求解器差异查询及 B64 具体位向量比较，不调用 `FmtVal`、`BitVal::from_bv` 或 `Model::get_fmtval`。若最后的执行器冻结仅改 `fmtval.rs` 的大于 64 位输出编码，则本批 helper 数值证明的调用链不受影响；仍需核最终源码树差异确实只在该文件。若还有其他生产变化，应按所改模块重新界定受影响测试。

## 统一最终 IR/runtime 复验（2026-09-27）

真实 Sail 严格生成的统一 IR SHA-256 为 `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`，源码快照 manifest 为 `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`。同一快照的 `isla-lib/src/{primop,ir,fmtval,smt}.rs` SHA-256 分别为 `6c6d5a42…`、`d26e7923…`、`43806138…`、`3ce7310d…`，与正式执行批次所用运行时冻结坐标一致。本批已包含标量 min/max、两处纯 mapping、宽位 FmtVal 和单 Model 具体值缓存。

用 [闭包检查器](tools/solve_fix_helpers/check_closure.py)重新核对旧 `6fc39efd…` IR：79 个历史声明和 79 个普通函数体均齐，含四个显式 preserve 的 `riscv_f16ToI16/Ui16` 与 `riscv_f32ToI16/Ui16`；当前 94 个 `riscv_*` 声明与函数体一一对应，模型 `riscv_*`/`ieee_*` 调用无缺体。报告为 `isla/target/float-solve-evidence/helper-final-1dcc8081/reports/static-closure.json`，SHA-256 `ec88337c…`。

按本目录 [runner](tools/solve_fix_helpers/run.py) 以 `--p2 <统一冻结stage> --candidate-ir <新IR> --isla-lib <stage中的isla-lib> --baseline <历史基线IR> --unknown-ir <历史未知入口IR> --unknown-inputs <归档未知输入目录> --normalize-model-mixed-bits` 在空证据目录重新构建 D、unknown、legacy 三个 runner。`--normalize-model-mixed-bits` 只修改外部构建副本：按顺序拼接全 Concrete 片段；遇 Symbolic 片段立即失败。每例仍需真实普通体 trace、SAT 和单完成路径；D/legacy 另对完整结果 bits 与五 flags 求差异 UNSAT，并核具体值。十组全部 exit 0、逐项计数达标：未知 90/96/91，原 helper 67，估算 350/1618/420，旧 12 体 39/24，legacy 35。三 runner 二进制 SHA-256 分别为 D `91b9f5c4…`、unknown `9d2b9dcc…`、legacy `e9ca69c5…`。准确命令、源/输入/二进制/日志逐项哈希和原始输出见 `isla/target/float-solve-evidence/helper-final-1dcc8081/reports/summary.json`，其 SHA-256 为 `8154da5f0d336ab66f99ea7aba7c301f0de85179274c90bc1cda99c23f78d0e4`。本结论限于这些 helper 输入和未知入口路径；正式 77 项整指令批次另计。
