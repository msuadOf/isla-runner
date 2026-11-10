# FmtVal 全宽具体值输出修复

## 实施边界

`isla/isla-lib/src/fmtval.rs::BitVal::from_bv` 原先对 `lower_u64()` 的结果逐位右移。超过 64 位时，debug 构建在移位 64 处 panic，release 构建把低 64 位重复到高半。按已审定方案，改为调用现有 `BV::to_vec()`，再经 `Self::concrete` 生成完整 LSB-first 位串和全 `true` mask。没有改动零宽值的其它接口契约。

本次格式化后的 `fmtval.rs` SHA256：`43806138bf1f3981b198bdd1f35a611d650dac49cbef9537912a9ed6df7a679e`。旧官方批次的只读源码快照 SHA256：`ae02f6e0b8969fb5361bf8f0edb4d6bce3d1a329c2407e94bafc9c5aada9e778`。探针源码 SHA256：`cfadaaccc120db77671d00bed6ef3d0d3c438118c771710a0ebddbfcd377d9a1`。

## 验证

证据保存在 `isla/target/float-solve-evidence/fmtval-wide-20260926/`，其中 `manifest.json` 记录源码、探针、所链接库的精确哈希及命令；`test-debug.log`、`test-release.log`、`results-red-rebuilt.json`、`results-green.json` 保留逐项结果。红绿探针均用同一 `probe.rs` 重编；红 debug 链接留存旧库 SHA256 `9e62b4b54b7e3b6221ff8d7f760617213ae0427854377fd73b35d15d47a6389f`，红 release 链接旧只读 stage 库 SHA256 `ee6b0c45fd529a610435c0cdf304ea0809d64e2fe97df7f324e256e6dacf3159`。`results-red.json` 另保存初次发现时的旧探针重跑结果，其二进制原构建命令和库哈希未留存，只作辅证。前述旧 stage `fmtval.rs` 哈希只证明旧实现文本，不能单独证明旧二进制的构建来源。

| 输入 | 旧 debug | 旧 release | 新 debug/release |
| --- | --- | --- | --- |
| `Bits(128'h123456789abcdef0fedcba9876543210)` | panic，退出 101 | 错误输出 `fedcba9876543210fedcba9876543210` | 正确输出 `123456789abcdef0fedcba9876543210` |
| 单个 128 位 Concrete 的 `MixedBits` | panic，退出 101 | 同样重复低 64 位 | 正确输出完整 128 位 |
| 两个 64 位 Concrete 段 | 正确输出完整 128 位 | 正确输出完整 128 位 | 正确输出完整 128 位 |

对最终源码分别执行 `cargo test -p isla-lib --lib fmtval::tests -- --nocapture` 与 `cargo test --release -p isla-lib --lib fmtval::tests -- --nocapture`，均为 **2 通过、0 失败**。测试覆盖 0、1、63、64、65、128、129 位；B129 第 128 位 tag；高低半不同的 128 位值；整体 Bits、单宽段、拆分宽段、倒序段、单字段 Struct；以及 80 位具体段与 8 位 arbitrary 段、48 位具体段组合后的位序和 mask。`cargo fmt -p isla-lib -- --check` 退出 0，`git diff --check` 退出 0。

架构独立复核重跑了上述红绿六例、debug/release 两组单测，并额外用每宽零值与单热位探针覆盖 B64 2145 例、B129 8515 例（包括 tag），全部通过；外部临时证据标识为 `fmtval-independent-review-0lda26v_`。这只放行 `FmtVal` 全宽输出局部修复。先前使用旧 `fmtval.rs` 的 77 项官方批次仍为诊断证据，最终运行时须重新冻结后复验。
