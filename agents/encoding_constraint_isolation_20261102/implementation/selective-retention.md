# 编码辅助域选择性保留指令断言

状态：在 Isla `8e5a3f7` 上只修改 `isla-lib/src/smt.rs` 与 `src/isarch/encoding.rs`，现由主 agent 提交为 `cf1aa14`；未改 `exec.rs` 或正式 Release 二进制。源码 SHA256：`smt.rs` 为 `a8385213125f716342af65a1e197d39b91f6da1d563081bfe12189e0a372cb14`，`encoding.rs` 为 `d978e2122ec7a70795f125cd7323ea4726de7e022cc27c3c04bcdec90e17cd9a`。独立源码签收见[复核报告](../review/selective-source.md)。新源码尚无正式 Release 完整 Clause 结果；`de00adb` 初版旧 flags 2884.43 秒、328 条 JSON 的 PASS 仅适用于初版，不直接继承给本修订。

## 修改与依据

辅助 checkpoint 现在使用 `instruction.symbolic_variables()` 取得指令的全部符号叶。沿原 trace 事件顺序：仅把指令叶的 `DeclareConst` 标为纯；`DefineConst` 仅当其实际引用都已标纯且不含 `App` 才传递纯标记；仅保留全部引用已标纯且不含 `App` 的原 `Assert`。访问表达式复用 `Exp::modify`，只读取节点类型，不改写原表达式。未知函数、FPR 状态及混合指令/状态依赖断言暂时移去；其声明、定义、编号和非 SMT 事件仍完整保留。旧的全去断言接口已删除，测试使用 `Val::Unit` 表示没有指令符号输入，避免重复 checkpoint 构造 API。

保留集合 `R` 始终是原执行断言集合 `A` 的子集。完整原路径 `D∧A` 蕴含辅助前缀 `D∧R`，所以保留断言不会排除原可达候选。候选新增后缀仍只接到**完整原 checkpoint**，最终求 `D∧A∧C` 并过滤 UNSAT；normal 优先、压缩仅普通拒绝域、异常分类和同一最终求解模型规则均未改。分类保守只影响辅助候选数量，不影响完整域判定。

## TDD 与验证

先加入两个新测试，运行时均 RED：编译器 `E0599` 报缺少 `with_instruction_assertions`，证据为[SMT 红例](selective-red.log)和[编码红例](selective-encoding-red.log)。实现后，新 SMT 测试 1/1 通过，证明两级 `DefineConst` 的指令 guard 保留，单独 FPR 状态、指令与状态混合及未知 `App` 断言移去，完整 checkpoint 合并后恢复原断言导致互斥候选 UNSAT。编码测试在同一 IR fixture 中确认旧全去断言辅助域有 3 个候选，新辅助域为 2 个，且两个状态变体在完整域都返回；不是取单个模型。两项绿例原始记录分别见[SMT](selective-smt-final.log)和[编码](selective-encoding-final.log)。

旧 checkpoint 合并定向测试 1/1 通过，见[日志](selective-original-checkpoint-final.log)；现有 `collector_` 11/11 通过，见[日志](selective-collector-final.log)。所有 Cargo 测试使用 `taskset -c 74`、`CARGO_BUILD_JOBS=1` 和 Debug target，未覆盖正式 Release；`cargo fmt --all`、`cargo fmt --all -- --check` 与 `git -C isla diff --check` 通过。独立 Sol 直接重跑相同测试并审查源码，无阻断。

上述 Debug 程序实际链接系统 `libz3.so.4`。为覆盖与正式程序相同的库边界，另在 `cf1aa14` 干净隔离工作树使用正式 `RUSTFLAGS` 构建 Release 测试程序；两份程序实际链接官方 `libz3.so.5.3`、库 SHA 与正式程序一致，指定 checkpoint 2/2、encoding 2/2、collector 11/11，共 **15/15 通过**。命令、程序 SHA 和逐项日志见[官方库定向验证](diagnostic/official-targeted-tests.md)。

额外尝试的宽过滤命令 `cargo test -p isla-lib --lib checkpoint --no-default-features` 未通过：未修改的 `get_multi_member_enum_const_after_checkpoint_replay` 报 `enumeration sort name is already declared`，见[原始日志](selective-checkpoint-final.log)。干净 `8e5a3f7` 基线与当前程序在同一系统库下的同名单测均动态复现相同退出 1，测试正文逐字一致，见[基线复现](diagnostic/baseline-enum.md)；当前程序在官方库下单测也报同一错误，见[官方库日志](diagnostic/official-tests/enum_context.log)。该宽过滤和额外 enum 单测不计入上述 PASS；本轮涉及的两个 checkpoint 定向测试分别通过。该无关失败没有在本修订中修改或隐去。

旧 flags 的[300 秒诊断](diagnostic/report.md)在初版分离源码下完成：候选完整域检查 1280 次已返回，其中 1069 次 UNSAT，说明指令 guard 候选膨胀有实际成本。这个观察支持优先缩小辅助域，但不能证明本修订的完整 Clause 性能；正式 7200 秒预算、JSON/编码和最终模型一致性需用新 Release 再验。
