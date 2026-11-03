# 保留指令字段断言：修订源码独立签收

结论：两份 Rust 源码审查通过，无阻断，可提交并正式构建、进行新一轮完整 Clause 验证。受审文件与测试程序精确哈希见 [selective-source-manifest.json](selective-source-manifest.json)。本签收不沿用初版 de00adb 的性能或 JSON PASS 作为新源码结果。

实际修改仅把辅助基点的原断言筛选从“全部移去”改为“只保留指令字段及常量的断言”。`encoding_paths` 仍使用原 instruction，normal/compressed 执行、完整原约束合并验证、异常和 UNKNOWN/error 处理均未改变。

依赖分析按原事件顺序执行，`DeclareConst` 只有实际指令叶可标纯；`DefineConst` 必须自身表达式的全部依赖已纯，先去掉旧标记，不能凭定义 ID 出现在输入里绕过分析。原有 `Val::symbolic_variables` 覆盖嵌套、MixedBits 和 SymbolicCtor tag。复用 `Exp::modify` 遍历全部子式，仅观察 Var/App，完全不修改表达式；任何未知函数 App 不标纯。保留的都是原 Assert 事件，所有声明、定义和非 SMT 事件原序保存，故 `完整原约束 ⇒ 辅助约束` 保证原可达候选没有被筛掉。最终仍恢复完整原 checkpoint，而非仅依赖这些字段断言。

独立直接重跑已构建测试程序：新依赖筛选1/1、原 checkpoint 合并1/1、encoding2/2、collector11/11全部通过，日志为同目录 `selective-*-tests.log`。新回归实际确认旧辅助域3候选收敛到2候选，同时保留两个状态取值的真正可达编码；原配置、不可达异常过滤、可达异常、compressed 拒绝域、前后态与返回值同模型回归保持。`git -C isla diff --check` 退出0。

剩余边界：依赖分类只决定性能；跨多个 Assert 才能推出的指令限制可能仍未保留，常量 FP 式也不因无自由变量而保证便宜。完整旧 flags、新模型 flags/sat、定向与 Make 需使用新 Release 复验，不能直接复用初版的完成时间或见证。

补充独立 [selective_checkpoint_probe.rs](selective_checkpoint_probe.rs) 已编译并退出0：嵌套 Struct/Vector、MixedBits 指令字段、SymbolicCtor tag、枚举和两级定义均正确保留约束；输入中的派生状态别名与零参数 App 不误判为纯；非断言事件与表达式逐项不变；重新合并后原状态约束完整恢复。见 [结果](selective_checkpoint_probe.json) 和 [日志](selective_checkpoint_probe.log)。

官方 Z3 补验：隔离 worktree 的 cf1aa14 Release 测试程序分别为 `bc052086…e570` 和 `3092eace…83fd`。独立核对文件/库哈希、干净源码及 `ldd` 后，直接重跑原 checkpoint 1项、新筛选1项、编码2项和collector11项，共15/15通过；对两类程序同时用动态链接器日志确认实际装载官方 `libz3.so.5.3`、哈希 `899cbc70…9970`，与正式程序相同。此前 Debug 系统库测试保留为不同环境证据，未用它代替官方库补验。结果与日志见 [official-targeted-rerun/result.json](official-targeted-rerun/result.json)。

额外 enum 同Context重放测试在当前官方库下独立再现退出1，不计入上述15项。相同测试在系统库的旧基线与当前源码均有失败日志，且测试函数正文与8e5a3f7逐字一致；官方库未跑旧基线，因此不声称已经完成两版官方库的动态对照。边界见 [enum-boundary.json](official-targeted-rerun/enum-boundary.json)。本轮未修该单列失败，也未宣称全部 isla-lib 测试通过。

最终状态补充：上述待复验的正式项目均已在 cf1aa14 的冻结 Release 上完成并独审通过，见 [最终报告](final-report.md)。原“剩余”段保留为源码签收时的历史状态；额外 enum 单列失败的边界不变。
