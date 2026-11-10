# solve 运行时入口与终态账本实施记录

2026-09-26。对应[运行时设计](solve-fix-runtime-design.md)的 R2；实施/验证分开记录。源码在 `isla/src/isarch/exec.rs`、`mod.rs`、`isarch_main.rs`，错误类型仅在 `isla/isla-lib/src/error.rs` 增加 Clone。固定 77 清单复制到 `isla/src/isarch/official_float77.txt`，SHA-256 `d5df3754b214c6316e45b45143331f7d1c8c2f976ccce460ceaba4a37c508113`，与[审计清单](tools/official_float/targets77.txt)相同；独立 Isla checkout 编译不依赖父仓目录。

## 已实施

- 官方 77 项使用 `FullEncoded32`：初始化前插入小 IR wrapper，让完整符号 constructor、当前符号初态在同一 solver/路径依次走 `zencdec_forwards`、`zext_decode`、`zexecute`。每个 Call 后检查 `HAVE_EXCEPTION` 并短路，避免把 Sail 的 Poison 继续传给下一阶段。assert 在初始化前复用 `assertions_to_jumps`，没有改变全局 Optimistic 模式。
- 其余 clause 使用原 `zexecute` constructor 诊断入口及 32/16 位既有 encoding helper；共享新的终态账本，不把其输出标为真实译码通过。输出的 `summary.entry-mode` 明示 `full-encoded-32` 或 `constructor-diagnostic`，诊断模式的 `decoded-instruction` 为空字符串。
- 每个 executor 回调先分配 clause 内唯一 `case-id`，再分类、物化并关联 itrace。所有正常、UNSAT、Poison、Exit、Suspended、assert/match/SMT/模型与格式化错误均有终态；非超时错误不再只打印后被覆盖。真实错误保持原 `ExecError`，导致 clause 退出非零。sampled/KeepCurrentModel 使 `summary.complete=false`。
- 编码器 MatchFailure 仅在当前实际 IR 的 `zencdec_forwards` 唯一末尾默认 `Exit(MatchFailure)`、准确 PC/SourceLoc 且所请求 constructor 有带源码位置的 mapping arm 时列为 `non-encodable`。终态保存 requested、完整初态 witness 与 arm `mapping-source`；未知或嵌套失败仍报错。
- 成功译码路径先用当前 solver 对 requested 与 decoded 全值关系做“不等式 UNSAT”检验，再选择输出 witness；与真实 decoder 不一致时报错。encoded word 从同一 wrapper 的局部变量直接物化，不再从具体值另开编码执行。完整初态和末态调用 R1 接口并使用同一 Model；旧稀疏 `isa-state` 保留。汇编 printer 与非77编码 helper 得到与记录一致的具体入口寄存器。
- `gen` 保留旧字段，新增 `case-id`、`path-signature`、`requested-instruction`、`decoded-instruction`、`entry-domain`、`isa-state-complete`、`isa-state-post`。顶层 `summary` 记录 clause、entry-mode、state-domain、分类计数、emitted/suppressed 和 complete；`terminals` 按 case-id 保存 status/phase/function/source/detail/sampled/emitted及可用 witness。case-id 只用于关联，排序与配额键排除 case-id，具体指令文本对 Struct 字段排序。
- `mod.rs` 的 assembly/encoding helper 改为粘性错误收集。仅函数本身唯一末尾默认 MatchFailure 可作为无映射返回 None；嵌套、内联、AssertionFailure、Poison、Exit/Suspended、SMT Unknown/错误或采样不能由另一个成功分支覆盖。辅助函数返回前在自身 solver 内物化值。

## 已验证

先写 `collector_keeps_non_timeout_execution_errors`，基线运行失败（旧 `record_error` 对 AssertionFailure 返回 false）；修改后通过。真实小 IR `assembly_mapping_success_cannot_hide_an_error_branch` 在 Bool 两臂分别成功/AssertionFailure 时返回错误；`nested_mapping_match_failure_is_not_a_top_level_rejection` 验证嵌套失败不当作无映射；另有末尾失败结构与 wrapper 异常跳转结构测试。

当前源码已执行 `cargo fmt --package isla --package isla-lib`、`cargo test --lib -q`，82/82 PASS，日志见 `tools/solve_runtime_tests/output/cargo-test-lib.log`。`cargo build --bin isarch -q` 退出 0，日志见同目录 `cargo-build.log`；R3 的 `cargo check -p isla --features itrace` 由 R3 lane 运行通过。真实小 IR wrapper fixture 现在执行 encode/decode/execute 三种情况：encode/decode Sail 异常分别在 wrapper PC 9/10 短路为 Poison，后续函数若执行会触发断言但未触发；正常路径 Retire 且末帧寄存器由 1 写为 2，两异常路径仍为 1。

最新默认 debug 二进制 SHA-256 `616efeb60ce72fed902f43fccd3ca05a28b11e886a9c1e03946c3271ca4bae00`，IR `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，配置 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`。R2 源文件 `exec.rs`/`mod.rs`/`isarch_main.rs`/`error.rs` 分别为 `a1a400783d19aca3f599647fffb75f093a110985a9ff6d4752adc04ab21ab534`、`00f8259b4a4017b9e34757b29299f4ec08b4e3386d63e12bb68c6dc7724e8c30`、`dfc97b702674b452a0db443cd3f0323e53361465d643ba7751b5e32de5d74978`、`bec463f1e1d724f328d9dd3aaf99a911e39f5dc6618785d6ebea8e31306c31e6`。从 `tools/solve_runtime_tests` 隔离工作目录运行：
`timeout 30s <isla>/target/debug/isarch -A <isla>/rv64d.ir -C <isla>/configs/riscv64_difftest_fd.toml -T 1 --timeout 20s --smt-timeout 5s --tastic qfaufbv solve-state --clause=FLI_S`，退出 0，97 终态=96 Retire+1 non-encodable，96 gen、0 sampled、complete=true。完整初态与末态包含 fcsr/mstatus；non-encodable 保存具体 requested/初态。相同参数下 `MRET` 使用 constructor-diagnostic，退出 0，4 终态=3 Retire+1 Illegal，4 gen、complete=true。MRET 先前出现的 `Invalid privilege level or virtual mode` Poison 在 R1 经审的保留 MPP 值排除后消失；它没有被 collector 静默过滤。原始 JSON/日志在本专题 `tools/solve_runtime_tests/output/`。

相同命令参数换 clause 为 `C_NOP`，退出 0，1 Retire/1 gen，原宽度编码 `16'h0001`，证明非77诊断模式的压缩编码 fallback 可用。换为 `C_ADD` 退出 1，1 条 `error/execute`，内容为未支持的 `ExecuteAs(RTYPE(...))`；没有把该符号域的一个不可汇编 witness 伪装成整条路径不可编码。四项的原始 stderr 与 JSON 均在 `tools/solve_runtime_tests/output/`，所有本轮摘要从真实文件重新读取。初始化 stderr 另有 `No primop parse_hex_bits`、`emulator_write_tag`、`emulator_read_tag`、`valid_reservation` 提示；这四项 smoke 未执行到它们，当前结论不扩展到这些 extern 的运行语义。

以上仅证明列定入口和受测快照。官方 77 项全组自然结束、重放、分支覆盖和外层限时仍须以新批次证据判断。外部批次 manifest 负责绑定 IR、配置、binary、feature、runtime catalog、命令、退出码及 JSON 哈希；关联键是 manifest + clause + case-id。
