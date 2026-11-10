# R3 运行时轨迹与路径关联实施记录

2026-09-26。按 [运行器设计](solve-fix-runtime-design.md) 第 5 节实施。当前记录只证明通用 Isla library 的接口与定向测试；官方 77 项和 R2/R3 联合输出仍待运行。

## 实施

- `isla/isla-lib/src/tracetool.rs` 定义常驻的 `ItraceTerminalMetadata { scope, case_id, status, phase, path_signature }`。`tracetool` feature 关闭时，collector 仍可构造同一类型；开启时 `submit_itrace_for_local_frame_with_metadata(frame, shared_state, diagnostics, metadata)` 把它写到完成路径。旧提交接口保留。
- `ItraceHandler::set_runtime_catalog(shared_state)` 遍历实际 `SharedState.functions` 函数体，按执行时 PC 建立 IR 行、SourceLoc 与 Jump target。文件开头输出 `---- runtime branch catalog ----` 到 `---- end runtime branch catalog ----`，每个 Jump 一条 JSON，含 `function,pc,instruction,source_loc,target,fallthrough`。启用 catalog 后，查不到运行时 PC 不再回退到原始 `.ir` 文本，避免 `--fork-assertions` 附加 handler 被误标。
- `run_loop` 在 Jump 决策成功后记录实际方向和后继：具体 Bool、单 SAT 符号方向、fork 父子方向、限制采样方向均覆盖；Jump 求值报错或截断前不写 edge。每条 edge 保留完整 `backtrace`，输出为 `branch_edge function=... pc=... successor=... taken=... source=... context=[...]`。渲染时用运行时 catalog 校验 target/fallthrough。
- `LocalFrame` 增加 `function_name()`、`pc()` 和 `has_sampled_branch()` 只读接口。最后一个名字兼容 R2 已约定调用，语义是路径是否丢弃了可满足的执行域：既包括 Jump 的 `ConcretizeBranch`，也包括 Monomorphize 的 `KeepCurrentModel`。标记保存在路径状态，fork 克隆时继承，不改变既有限制策略。

路径块在原指令行后有 `---- terminal metadata ----` 和 `---- branch edges ----`，末尾仍为 `====`。`(scope, case_id)` 是 JSON、终态账本与轨迹的关联键；`path_signature` 只作排序/复现指纹，不能作为唯一 ID。每个 clause 配置 ITRACE 后调用一次 `set_runtime_catalog`，再执行并提交所有终态；R2 接线记录另见其实施文件。纯 SMT ITE 不会被写成 executor Jump。

`make solve-X ITRACE=1` 的运行器路径为 `isla/output/trace/itrace_X.txt`；隔离批次则在对应 stage 的 `output/trace/` 下。每份文件有一段 catalog 和多个以 `====` 结束的终态块。多线程块顺序不保证按 `case_id` 排列。

## TDD 与验证

先加入未实现 API 的失败测试，`cargo test -p isla-lib --features tracetool --lib runtime_catalog_uses_executed_function_bodies` 因缺类型和方法编译失败；实现后转绿。另给原 `monomorphize_path_limit_can_keep_current_model_without_forking` 加断言，原状态在 `remainder` 仍 SAT 时错误报告 `has_sampled_branch=false`，测试先红；路径级标记补齐后转绿。

在 `isla/` 执行：

```sh
cargo test -p isla-lib --features tracetool --lib itrace_ --quiet
cargo test -p isla-lib --features tracetool --lib runtime_catalog_ --quiet
cargo test -p isla-lib --lib monomorphize_path_limit_can_keep_current_model_without_forking
cargo test -p isla-lib --lib sampling_is_path_local_pair_balanced_and_two_phase
cargo check -p isla-lib --no-default-features
cargo check -p isla --features itrace
cargo fmt --package isla-lib
git diff --check
```

结果：ITRACE 41/41、catalog 3/3、两个无 feature 采样/Monomorphize 测试各 1/1，两个 `cargo check`、格式化和 diff 静态检查退出 0。顶层 Isla 的 feature 名是 `itrace`，它映射到 library 的 `tracetool`。定向语义测试包含具体 Jump target 与 fallthrough 相同时的真/假方向、双 SAT fork、单 SAT、失败 Jump 只到达不算走过、运行时 catalog 与同终态 ID 落盘、assert 转换新增 handler PC，以及重复调用上下文分离。

## 后续联合核对

R2 当前已在每个 clause 的 `itrace.configure(...)` 后调用 `set_runtime_catalog(shared_state)`，并在 collector 回调用同一 `case_id` 写终态账本与 ITRACE。两 lane 的 `cargo check -p isla --features itrace` 已通过，`FLI_S` 运行时绑定结果见下节。外部中止时尚未提交的活跃路径没有完成块；不得把部分文件解释为整个 clause 完成。77 项是否自然结束、终态守恒和实际 branch 覆盖以新批次验证为准。

## P1 `FLI_S` 联合运行及紧凑模式

使用仓库外证据目录 `isla-r3-itrace-20260926.06EO4T`，在三个独立工作目录运行同一 P1 IR（SHA-256 `f5141217f2695fb53a0584c1bc7dfa059eac15df51c07ae3f02307099e4b4a61`）和严格配置（`8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`）。调用参数为 `-T 1 --timeout 30s --smt-timeout 5s --tastic qfaufbv solve-state --clause=FLI_S`，外层 `timeout 45s`；无轨迹组省略 `--itrace`，另两组添加 `--itrace=itrace.txt`。原完整文本 trace 二进制 SHA-256 `2182b3baf7d9449b00f443f541cf4d0778e32203bbc3eaa904376b75472863d4`，紧凑版 `774aa84f2049692782cd2679ebb9d0c7c1f7d01e38a53a447c94a46a95140bbe`。三组均退出 0，JSON 都是 97 终态、96 Retire、1 non-encodable、96 gen、`complete=true`、零采样；汇编/编码、返回和 entry-domain 多重集相同。JSON 字节和任意初态 model 值不要求逐项相同。

| 模式 | trace 字节 | 墙钟 | 峰值 RSS | 说明 |
| --- | ---: | ---: | ---: | --- |
| 不启用 ITRACE | — | 13.66s | 504488 KiB | 同一 feature 二进制，只不传 `--itrace`。 |
| 完整文本 trace | 297845196 | 23.17s | 668924 KiB | 含 1846606 条普通指令行。 |
| runtime catalog 紧凑 trace | 60000062 | 22.10s | 665940 KiB | 保留全部 edge、终态及诊断；普通指令行改为数量与执行函数集合。 |

两份 trace 的 runtime catalog 均为 25924 个 Jump，逐字一致；各有 97 个完成块，`(scope,case_id)` 对 JSON 97 个终态一一对应且状态、阶段、签名相同。两份均有 297721 条真实 branch edge，逐条按执行顺序的 SHA-256 同为 `4eaa8cd52394f54771fe373c9107ef99545a2bed67a06661823abd58b404e454`；每条 successor 与 catalog target/fallthrough、SourceLoc 一致，逐 case edge 数相同。紧凑版 `instruction_count` 合计 1846606，97 块均有非空 `executed_functions`。独立消费端 `solve_replay/audit.py::validate_trace` 对紧凑文件返回 `trace_binding_complete=true`、25924 catalog、97 块、297721 edge。

原始 IR 的 `$zsail_assert` 调用共 297 个。原始函数体长度与运行时 catalog PC 对照：297 个 Jump 位于 84 个原函数体末尾以外，恰与 `assertions_to_jumps` 附加 handler 的数量相符；另 3 个 Jump 属于运行器 wrapper。例：原 `zaccrue_fflags` 有 90 条 IR 指令，原 PC47 是 `$zsail_assert`，运行时 PC90 的新增 Jump 保留同一 Sail 547 行 SourceLoc；不能用原文件第 91 行解释它。此次 FLI_S 的已执行 edge 中，原 IR EOF 以外的 handler/wrapper 坐标共出现 672 次，其中含 wrapper 分支；这只是所列输入的动态观察，不推断所有新增 handler 均已走到。

紧凑模式只在 `set_runtime_catalog` 后生效，输出 `trace-mode: branch-compact`、`instruction_count` 和 `executed_functions`，仍记录每条普通指令的运行时内部状态以保留既有求解/记录行为。没有 catalog 的旧文本模式保持原样。测试先红后绿：相同 path 在有/无紧凑渲染时保持 terminal metadata、branch condition、edge、限制摘要、SMT 摘要、计时和 timeout diagnostic；`cargo test -p isla-lib --features tracetool --lib itrace_ --quiet` 为 41/41，`runtime_catalog_ --quiet` 为 4/4，`cargo fmt --package isla-lib --check` 与 `git diff --check` 退出 0。

本例紧凑文件较完整 trace 小约 79.9%，但相对不启用 ITRACE 的运行仍多约 61.8% 墙钟和 161 MiB RSS。全 77 项启用轨迹可取得绑定证据；该单项的开销不能直接外推为 77 项总耗时或总磁盘量，批次须实际计量，外层限时与 trace 开销共同记录。

### 定向 runner 首条真实路径

IR 集成 lane 的仓库外目录 `isla-solve-fix-runner-smoke-20260926.NjDlGy` 使用同一 P1 IR 建立首个成功样例 `baseline_migrated_fadd_s`。runner 二进制 SHA-256 `3b7b2c26981570b192e32b653f84f42afa53e65a8966e7a1478b412bcbf6fc43`；结果 JSON `ce32281a6bd87d068377c90e836cacb2ebe906c106744899253ecea52112c576`，trace-map `186533ccc6728bb73e1ba92e43d0a7f2375364dc90b656e7c842ebb5098df348`，ITRACE `4e79c5a11be511bc538bd171f17a3214fa477686dab1fbcec47b2faf7f518efe`。这条输入有四次回调：decode 两条、encode 一条、execute Retire 一条；runner 使用每回调唯一 `terminal_case_id=SHA256(name\0phase\0ordinal)` 的前八字节大端值，另保留输入级 case ID。

只读调用既有 `solve_replay/audit.py::parse_trace` 检查：四个完成块与 trace-map 四行的 `(scope,terminal_case_id)` 双向对应、唯一，status/phase/path_signature 全相同；catalog 25624 个 Jump、3931 条实际 edge，所有后继和 SourceLoc 均与 catalog 相符。与同 P1 的 official-fork catalog 比较，共有 25624 个 `(function,pc)`，它们的 SourceLoc/target/fallthrough 全同；official-fork 另外 300 个坐标对应 297 个断言 handler 与 3 个 wrapper Jump。两种入口的 `instruction` Debug 文本使用不同 Name 显示（符号名与数字 ID），文本未直接相等，源码审计需按同一 symtab 规范化后核；不能据文本差异推断语义或 PC 不同。该样例用 Optimistic/no assert rewrite 的 custom 入口，只证明列定 P1 成功样例的 trace 关联，不代替官方 solve 或其他定向输入。
