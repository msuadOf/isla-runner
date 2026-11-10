# 编码约束分离：实施与定向验证

本文记录初版 `de00adb` 的实施。后续保留指令字段断言的修订与复验见[选择性保留实施](selective-retention.md)；初版完整 Clause 结果见[动态验证](../validation/report.md)。

状态：`isla` 原基点 `99a83bb` 上的两份源码已实现并由主 agent 接收；完整 Clause 与性能结果另记，不在此处判 PASS。源码内容 SHA256：`isla-lib/src/smt.rs` 为 `5a12dc78e584da3524ab0a4029aeccedf42e43916f4b65886ef3f819b52568`，`src/isarch/encoding.rs` 为 `a66aa01584729ae630213971b31dbee0c7aebdebc9c3a8582fa126039cbed2db`。本实施 agent 未改 `exec.rs`，未自行提交，提交由主 agent 统一管理。

## 实施合同

`Checkpoint::without_assertions` 按原事件顺序只移去原执行 `Def::Assert`，保留声明、定义、枚举、非 SMT 事件及 `next_var`。辅助 normal 映射从此点开始；其正常拒绝 checkpoint 在同一辅助树上接续 compressed 映射。`with_suffix_from` 校验辅助基点是候选的 Arc 祖先，把候选新增事件接到完整原执行 checkpoint，并用候选 `next_var`。祖先或编号不变量失败直接报错。

每个有终态的候选先在合并后的完整约束下检查。UNSAT 被过滤；SAT 才按编码成功、普通拒绝或原有异常规则分类；UNKNOWN/SMT 错误传播。采样分支先报完整性错误；辅助域已 UNSAT 的 `Run::Dead` 直接忽略。普通成功仍优先，压缩只在普通拒绝域运行。返回给 collector 的是完整 checkpoint，后续使用同一个最终求解模型具体化编码、前态、后态和返回值。

约束关系：设原 trace 中非断言事件为 `D`、原断言为 `A`，辅助终态新增事件为 `C`。辅助探索求 `D∧C`；原可行候选一定也满足这个更宽的集合。合并严格恢复原事件顺序并接上 `C`，最终求 `D∧A∧C`，故返回集合与原约束下可行的辅助候选相同。定义可能包含路径相关符号，但 `D` 全部保留，合并前后引用同一符号 ID；新增 ID 从原 `next_var` 继续。`length_bits`、`segments_length` 和 `segment_length` 只读取宽度，不新增 SMT 事件，因此先取候选 checkpoint 不会漏掉其变化。

## TDD 与回归

先加入 checkpoint 测试，再运行 `cargo test -p isla-lib --lib isolated_checkpoint_preserves_definitions_and_rebases_only_new_constraints --no-default-features`，RED：编译器报告缺少 `without_assertions` 与 `with_suffix_from`。实现接口后同命令 GREEN：1/1。该测试在原断言与候选断言互斥时得到 UNSAT，另一候选得到 SAT；同时验证旧/新增枚举、符号编号、多段后缀、非 SMT 事件和原断言恢复。

先加入编码测试，再完成映射终态合并。`cargo test -p isla --lib isolated_candidates_keep_only_full_execution_feasible_encodings --no-default-features` GREEN：1/1，内部三种场景：辅助域保留两个互斥普通编码候选而完整域只留一个；普通拒绝后压缩成功；辅助域可达、原执行域不可达的 `AssertionFailure` 不污染结果。该测试初始 RED 与 checkpoint 测试共享缺失的新 API，未另称旧实现曾出现运行期断言失败。

`cargo test -p isla --lib collector_ --no-default-features` GREEN：11/11，覆盖原有多编码、压缩域、可达异常、前后态与 ExecuteAs。`cargo fmt --all`、`cargo fmt --all -- --check` 与 `git -C isla diff --check` 通过。独立审查直接执行构建好的测试程序，结果与实施自测一致，详见 [源码签收](../review/encoding-source.md)、[SMT 日志](../review/smt-tests.log)、[编码日志](../review/encoding-tests.log)、[collector 日志](../review/collector-tests.log)。

该实施对每个辅助终态仍做一次完整约束检查；这保留可行性判定，但完整约束查询可能仍慢。不能把干净诊断中去约束的 `0.04–0.05s` 直接当作生产耗时。完整 Clause 的运行时间、见证数、JSON 与机器编码需按新源码和新 IR 继续验证。
