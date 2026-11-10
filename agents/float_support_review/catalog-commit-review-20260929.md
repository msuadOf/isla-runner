# d740e02 提交与文件职责审查

**2026-10-03 后继修订**：已再次 amend 为 `8545e7c`，撤销终态账本，恢复原 exec.rs 流程；下文“现行”均是 09-29 当时状态。当前实施与验证见 [局部修补记录](catalog-local-patch-20261003.md)。

**现行版本**：用户批准按“catalog只追加观测信息”收缩职责，已 amend 为 `323021b`；见文末[观测范围收缩](#catalog限于观测信息2026-09-29)。`31523ab` 及更早版本仍混入执行行为修改，均保留为历史阶段。

**后续实施**：用户要求最小修正并 amend，已形成 `f5aa97d`；见文末[最小修正](#最小修正与-amend2026-09-29)。以下原审查保持 `d740e02` 的历史适用范围，模块拆分建议未实施。

审查对象：`isla@d740e021b62005e6788058aad3871e9c136e4e3e`，父提交 `b18d6b7`。以下源码行号均指提交快照，不指有额外暂存修改的当前文件。采用 `git show` / `git diff` 检查七文件及调用上下文、同提交 `rv64d.ir`、已有测试；未修改 Isla 源码或 index，未重新运行 Rust 测试或 solve。既有隔离测试只按[原记录](status.md#catalog-单提交收拢2026-09-29)理解，不作为本轮动态复现。

## 结论

运行时 catalog、实际 Jump 边、终态关联和不可变前缀共享具有共同目标，放在一个提交内合理。跨层依赖方向基本正确，但通用 collector 新增了过窄的结果白名单，存在应先修复的行为回归；文件内部职责仍可收拢。

## 应修复：正常架构结果被判为执行器错误（P1）

- `src/isarch/exec.rs:822–832` 只接受 `Retire_Success` / `Illegal_Instruction`，其余 `ExecutionResult` 在物化前变成 `ExecError::Unreachable`。
- 同提交 `rv64d.ir:3573–3585` 的 `ExecutionResult` 还包含 `Memory_Exception`、`Trap`、`Enter_Wait`、`Virtual_Instruction`、扩展检查失败以及 `ExecuteAs`。其中 `rv64d.ir:285270–285278` 的 EBREAK 分支明确返回 `Memory_Exception(...E_Breakpoint...)`；紧接的 WFI Machine 分支返回 `Enter_Wait`。这不是浮点或当前暂存 IR 才有的行为。
- 父提交对 `Run::Finished(ret_val)` 没有该白名单。新提交即使尚未物化也会拒绝上述结果：终态为 error、无对应 gen，`first_error` 导致 clause 返回失败。通用 `solve-state` 和默认 solve 目标中的 EBREAK/WFI 等受影响。
- `SolveSummary::from_terminals`（122–136）和物化后的二次字符串分类（862–877）也只认可这两个结果，修复应同步三处。应区分正常架构异常、执行器失败与需要续执行的 `ExecuteAs`，不能将模型正常返回值统一作为内部错误。浮点批次只接受两类结果的验收条件应留在对应批次策略中。
- 验证缺口：新增账本测试只手工填入 retire/error；物化测试覆盖 Retire_Success。应补实际 collector 对 EBREAK、WFI 和正常退休结果的回归，断言状态、输出与退出结果。上述回归本轮尚未执行。

## 文件职责

| 文件 | 当前职责与评价 |
| --- | --- |
| `isla-lib/src/executor.rs` | 在所有实际 Jump 路径记录方向与后继，向 trace 提交终态元数据；没有引入 RISC-V 结果分类，职责正确。 |
| `isla-lib/src/executor/execution_limits.rs` | 记录路径是否实际采样，包括 monomorphize 保留当前模型；属于执行限制状态，位置正确。 |
| `isla-lib/src/executor/frame.rs` | 暴露函数名/采样状态，并验证真实 freeze/fork 的前缀共享；位置正确。 |
| `isla-lib/src/error.rs` | 为 collector 保留首个错误支持 Clone；是必要配套。 |
| `isla-lib/src/tracetool.rs` | 无 trace feature 时仍可使用的终态元数据；避免业务调用层散布条件编译，边界合理。 |
| `isla-lib/src/tracetool/itrace.rs` | 前缀容器、路径数据、旧文件缓存、runtime catalog、渲染和 writer 都在同一文件；仍属于 trace 层，但内部职责较多。 |
| `src/isarch/exec.rs` | 执行编排、物化、配额、JSON schema、终态分类/汇总集中；最值得分离的是报告模型及终态管理，RISC-V 分类应留在 isarch。 |

优先改善两处，不需要逐 struct 拆文件，也不需要把这次提交拆成多个提交：

1. **将 catalog 绑定与输出模式分开。** `set_runtime_catalog`（832–881）既建表又输出 catalog，并设置 `runtime_catalog_ready`；`render_lines:944–966` 用同一标志禁止普通指令输出。当前公共 API 无法表达“使用运行时 PC 定位，同时输出完整指令”。紧凑模式有历史批准及体积收益，本审查不否定它；应由独立格式选项控制，保留当前 solve 的紧凑默认值即可。可将建表/查询放入私有 `tracetool/itrace/catalog.rs`，handler 负责生命周期，renderer 负责展示。
2. **将报告模型及终态管理从编排中移出。** 可新增私有 `isarch/solve_report.rs`，集中 JSON 数据、终态状态/阶段及汇总不变量；`exec.rs` 保留执行与物化流程，已有 `timeout_report.rs` 继续负责超时产物。用枚举集中状态语义可避免采集、物化和 complete 判定重复维护字符串白名单。

`SharedSequence<T>` 已在 records / conditions / edges 三处复用，属于有实际收益的私有抽象；不建议上升成全仓通用容器。其测试涵盖 payload 不复制、迭代顺序、深链释放、并行读取/释放及完整/紧凑输出字节对照；大量新增行是这些测试，不能仅凭 diff 行数判断封装过度。

## 其他清理与验证缺口

- `should_collect_unfinished_path`（234）已无生产调用，但 `unfinished_path_collection_skips_dead_paths`（1475）仍测试旧的“不收 Dead”；新 collector 在 896 将 Dead 记作 unsat 并统一提交 trace。应移除失效 helper，并改为真实 collector 的 Dead 记账测试，避免测试名称误导。
- `exec.rs:834` 和 `materialize_finished_case:698` 对 Retire_Success 会连续执行两次没有新增约束的 `check_sat`。父提交只有一次最终查询。可让物化入口统一负责最终可满足性检查，保留 unsat/error 区分；性能影响本轮未测，不将此项升级为已证性能回归。
- 本轮为静态审查：不新增 PASS、不覆盖原隔离测试结果，也不声称全量 solve 已验收。下一步先补正常架构异常 collector 回归，再修白名单；结构调整可随后在同一主题内完成。

## 最小修正与 amend（2026-09-29）

用户明确“添加信息没有问题，但是应该最小改动”，并确认通过 `git commit --amend` 合入现有提交。最终提交为 `f5aa97d563349116f6cf543b9cbb1a1c5480c6db`，替代 `d740e02`，父提交仍 `b18d6b7`；精确 tree 为 `e6019bdb19cdfbbf3ace29b65705362149b77164`。

- 实施仅改 `src/isarch/exec.rs`：删除物化前和物化后的两处返回值白名单；既有 retire/illegal 标签保留，其他正常返回记为 finished，原始 ret_val 保留在用例里。完整性与配额抑制统计同步识别 finished。finished 表示函数正常返回且物化完成，不表示正常退休，也不新增 ExecuteAs 续执行。
- 物化流程、错误传播、case-id、路径签名、终态/trace 关联、catalog 格式、文件结构均保持。本次不实施报告前面的模块拆分建议，不处理重复 SMT 检查等其他事项。
- 使用精确 `d740e02` 隔离副本先添加真实 collector 回归，前两种返回通过后，在 Memory_Exception 上复现 `unsupported ExecutionResult before materialization`。修复后八场景全部通过：Retire_Success、Illegal_Instruction、Memory_Exception、Enter_Wait、Trap、Virtual_Instruction，另有物化失败与配额抑制。测试核对原始 ret_val、编码、退出结果、JSON summary/terminals/gen 关联及 trace 元数据；fixture 为最小 IR，并非完整 Sail 指令或硬件重放。
- 最初测试准备修正过临时字符串生命周期、TimeoutReporter 配置；首轮完整回归的编码失败 fixture 未提供压缩编码入口，测试挂起后受控终止，改为汇编失败 fixture 并完整重跑。上述日志保留，不计为通过。

命令在隔离候选 `isla/target/catalog-minimal-20260929/candidate` 或主 `isla/` 执行；临时目录使用证据目录的 tmp，构建缓存使用 `isla/target`：

| 受测版本 / 命令 | 结果 |
| --- | --- |
| 修复前候选：`cargo test --offline -q -p isla --lib --features itrace,smt-thread-interrupt collector_preserves_finished_results_and_materialization_failures` | FAIL（预期红例，Memory_Exception 被拒绝），`red-collector.log` |
| 最终精确候选：`cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --skip isarch::target::tests::rv64_target_trait` | PASS，66库＋24bin，`green-final.log` |
| 主工作区（精确候选＋原暂存内容）：同上一命令 | PASS，84库＋24bin，`worktree-green.log` |
| 最终精确候选：`cargo test --offline -q -p isla --lib collector_preserves_finished_results_and_materialization_failures` | PASS，默认 feature 单项含八场景，`default-test.log` |
| 最终精确候选：`cargo check --offline -q -p isla --bin isarch`；`cargo fmt --all -- --check` | PASS，`checks.json` 与对应日志 |

库回归排除的是原记录已复现的 x0 列表测试失败；没有声称未过滤的全库通过。未跑全量 make solve、完整 Sail EBREAK/WFI 或硬件重放，未重跑未改动 trace/executor 模块的历史测试。

[证据目录](../../isla/target/catalog-minimal-20260929/)保存原 index、原暂存补丁、原工作区文件、隔离候选、日志及提交前后账本。amend 使用独立 index；主 index 仅同步本次 exec.rs 修正，另外所有 index 条目和26个原改动文件字节均核对保持，原27文件仍暂存且无 unstaged 差异。未 push，未提交父仓库 gitlink。沙箱最初阻止写 Git 对象，随后授权提升执行提交脚本成功。

## 撤销单调用封装（2026-09-29）

用户进一步限定：不保留只有一个生产调用点、主要为测试提取的函数。已将 `f5aa97d` amend 为 `6fefb6bf3917b69790559f6e52e4c2c125fe1750`，父提交仍 `b18d6b7`，tree 为 `c3885a434c78854ed24ac7010e88b983d8c57c29`。

- 实施只改 exec.rs，移除六个函数：`materialize_finished_case`、`SolveSummary::from_terminals`、`begin_terminal`、`finish_terminal`、`set_terminal_source`、`should_collect_unfinished_path`。前五处逻辑回到各自调用位置，最后一处已无生产调用，随旧测试删除。
- 物化中的各步骤和错误类别保持，以局部带标签块将失败汇合到既有 Err 分支；没有新增替代生产函数或闭包。终态锁的作用范围保持局部，所有正常返回继续物化并保留原 ret_val。
- 保留 `case_sort_key`（全量排序和配额排序实际复用）、共享轨迹序列、跨模块状态访问接口及旧有错误处理接口。没有拆文件、改输出格式或扩展执行语义。
- 原 FS/VS 测试不再直接调用物化函数，改为仅在测试模块实现固定约束目标，通过真实 setup_pre_state/execute/collector/JSON 验证16组合；主工作区额外核对既有完整初态/后态字段。终态关联测试改为真实布尔分叉产生两条终态，验证不同 case-id、原始返回值、配额/汇总和 JSON/trace 关联，替代旧的手工账本封装测试。生产代码不为测试保留入口。

验证目录为 [catalog-inline-20260929](../../isla/target/catalog-inline-20260929/)，命令的 TMPDIR 使用其中 tmp、CARGO_TARGET_DIR 使用 `isla/target`：

| 版本 / 命令 | 结果 |
| --- | --- |
| `f5aa97d` 隔离副本先迁移测试：`cargo test --offline -q -p isla --lib --features itrace,smt-thread-interrupt collector_preserves_constrained_fs_vs_and_encoding_output` | PASS，16组合，`baseline-test-ready.log`；准备时修正过新旧Target trait接收者差异及寄存器绑定初始化，前次失败日志保留 |
| 最终精确候选：`cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --skip isarch::target::tests::rv64_target_trait` | PASS，64库＋24bin，`green-final-checked.log`；首轮内联汇总遗漏借用的编译错误已修正后完整重跑 |
| 主工作区（候选＋原暂存内容）：同上一命令 | PASS，82库＋24bin，`worktree-green.log` |
| 最终精确候选：`cargo test --offline -q -p isla --lib collector_preserves` | PASS，默认feature两项collector测试，`default-test.log` |
| 最终精确候选：`cargo check --offline -q -p isla --bin isarch`；`cargo fmt --all -- --check` | PASS，`checks.json`及对应日志 |

两项旧的直接封装测试被真实collector验证替代，因此库测试计数比上一阶段少2；并非过滤新增失败。库回归仍显式跳过已知x0旧失败，不宣称未过滤全库通过。未跑全量solve、完整Sail指令或硬件重放。

独立index只收入精确候选的exec.rs；主工作区相同逻辑同步后，其他index条目及26个原改动文件字节保持，原27文件仍暂存、无unstaged。原始快照、隔离源码和 `after.json` 均保存在证据目录；未push、未提交父gitlink。

## 恢复回调原结构和注释（2026-09-29）

用户指出上一轮仅取消函数、内联为标签块仍不符合最小结构改动要求，且原注释被删除。本轮将 `6fefb6b` amend 为 `31523abb30db7acb74179601081306c576d22300`，父仍为 `b18d6b7`。本轮提交差异仅为 `src/isarch/exec.rs`：以父提交原 callback 为底稿，恢复 `match exec_result → match run`、物化中的嵌套 match、日志和原早退位置；撤销物化标签块及其结果二次 match。在原有多次调用的 `submit_itrace` 闭包上追加账本、case-id 和 trace 元数据，每个正常或早退出口提交一次。

原 callback 的21个注释块（含 assembly、lets、events 实验代码和注释掉的执行入口）逐块核对无缺失，exec.rs 生产区的原注释也无缺失。排序注释中原“JSON逐字节一致”句保留并追加版本限定：加入调度相关 case-id 后只保证用例内容集合和排序稳定。正常返回仍支持 retire/illegal/finished；UNSAT、Unknown 和模型获取失败在原 SMT/model 分支旁追加早退，防止失败后生成空用例。原 Assertion/MatchFailure 的丢弃用例注释保留，并追加失败终态仍记账的说明。

验证目录为 [catalog-structure-20260929](../../isla/target/catalog-structure-20260929/)。以下 cargo 命令使用该目录的 tmp 作为 TMPDIR，`isla/target` 作为 CARGO_TARGET_DIR，均设180秒上限：

| 受测版本 / 命令 | 结果与日志 |
| --- | --- |
| `6fefb6b` 隔离基线：`cargo test --offline -q -p isla --lib --features itrace,smt-thread-interrupt collector_preserves` | PASS，2项真实collector测试，`baseline-test.log` |
| 最终精确候选：`cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --skip isarch::target::tests::rv64_target_trait` | PASS，64库＋24bin，`green-final-checked.log` |
| 候选＋原暂存内容的工作区：同上一命令 | PASS，82库＋24bin，`worktree-green.log` |
| 精确候选：`cargo test --offline -q -p isla --lib collector_preserves`；`cargo check --offline -q -p isla --bin isarch` | PASS，默认2项collector与编译，`default-test.log`、`default-check.log`、`checks.json` |
| 两份源码 `cargo fmt --all` 后检查；原注释与修改范围核对 | PASS，`fmt-check.log`、`structure-check.json`、`callback-parent.diff`；测试代码未改 |

首次编译发现新闭包的显式生命周期约束过强，撤销类型标注并在外层获取 path_signature 后修复；中间编译失败日志保留为 `green-first-compile.log`、`green-inference-compile.log`。表中PASS只指最终修复后的源码。库仍显式跳过已知x0旧失败，未跑完整Sail指令、全量solve或硬件重放。

独立index仅提交精确候选；完整初态/后态和具体寄存器传入辅助映射等原暂存功能仍保留在工作区。提交脚本逐一验证其他index条目、26个其他暂存文件字节不变，原27文件仍暂存、无unstaged。快照及最终提交树见目录中的 `before.json`、`original.index`、`after.json`；没有移动父gitlink或push。

## catalog限于观测信息（2026-09-29）

用户批准收缩职责，并再次明确“amend只添加catalog改动”。已将 `31523ab` amend 为 `323021b943c413a4a17ce879040eb260f9138a50`，父仍 `b18d6b7`。本轮只调整 `src/isarch/exec.rs` 并撤销仅为扩大错误传播添加的 `ExecError: Clone`，因此最终catalog提交由7文件缩为6文件；浮点、IR、完整状态及脚本改动不在提交内。

- 恢复父提交原有的 Timeout/SMT 错误退出策略，普通执行错误、物化无结果和抽样不完整只在账本中反映；`summary.complete` 不再决定命令返回值。恢复 Assertion/Dead 原有的路径trace提交策略，账本仍记录这些终态。退出0不代表 `summary.complete=true`，也不代表源码覆盖完成。
- 撤掉为了记账新增的 UNSAT/Unknown/模型获取失败早退和 Poison/Exit/Suspended 错误升级。原回调8个早退、1次最终SMT查询均保持，原嵌套物化流程与全部生产区注释保留。原流程在非SAT或模型获取失败后可能生成空用例的问题未夹带修复；这类终态记为物化未完成。
- 原 `submit_itrace` 闭包接收终态记录，在原提交位置追加详情；正常返回的 retire/illegal/finished 标签仅用于描述结果，不筛选生成物。callback相对父提交净增96行，上一轮净增179行；没有新增生产函数或测试专用入口。

证据目录：[catalog-observation-20260929](../../isla/target/catalog-observation-20260929/)。cargo命令使用该目录 `tmp` 为TMPDIR、`isla/target` 为CARGO_TARGET_DIR，并设180秒上限。

| 受测版本 / 命令 | 结果与证据 |
| --- | --- |
| `31523ab`＋新行为断言：`cargo test --offline -q -p isla --lib --features itrace,smt-thread-interrupt collector_preserves` | 预期FAIL：普通错误进入first_error、assembly无结果导致命令错误；`red-policy.log` |
| 精确候选：`cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --skip isarch::target::tests::rv64_target_trait` | PASS，64库＋24bin，`candidate-green.log` |
| 候选＋原暂存完整状态内容：同上 | PASS，82库＋24bin，`staged-green.log` |
| 再加原未暂存浮点见证/non-encodable内容的工作区：同上 | PASS，83库＋24bin，`worktree-green.log` |
| 精确候选默认features：`cargo test --offline -q -p isla --lib collector_preserves`；`cargo check --offline -q -p isla --bin isarch`；`cargo fmt --all -- --check` | PASS，3项定向测试、编译及fmt，`checks.json`与对应日志；主工作区fmt另通过 |

真实collector回归由8场景扩为11场景，补 Assertion、Exit、抽样终态；验证原退出行为、账本完整性与trace策略相互独立。仍显式过滤已知x0旧失败，未跑全量solve、完整Sail指令或硬件重放，历史执行结果不迁记为此版本PASS。

本轮开始时已有27文件暂存，exec.rs另有未暂存浮点见证和non-encodable逻辑。独立index只收入精确候选；主index用“候选＋原暂存”版本，工作树使用包含未暂存逻辑的组合版本。其他index条目及26个其他原改动文件字节核对保持，最终仍27文件暂存、仅exec.rs含unstaged。浮点helper及其测试原文保持，回调中的新增调用仅适配终态参数；原non-encodable汇总条件仍保留为观测条件，不再继承旧complete退出门槛。快照、`new-unstaged.diff`、注释/结构核对和提交树在证据目录中；未提交父gitlink、未push。
