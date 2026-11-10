# Isla 浮点改动的范围与封装审查（2026-09-28）

本轮按用户要求审查现有改动是否围绕“基于 Z3 增加浮点支持”，以及非必要改动和过度封装。仅审查和记录，未修改 Isla 源码、配置或 IR。两名 Sol high 和一名 Astra high 分别辅助检查运行器、原语/SMT、执行器/trace/脚本；下述正式问题由主审重新核对源码，Python 失败由主审再次复现。

> 上述“仅审查”及 R1–R4 行号对应首轮冻结 diff。用户随后明确清理范围，R1/R2 的实施接续见文末；R3/R4 未在本次清理中修改。

## 受审版本与范围

- 实际分支：`feat/float-support`；HEAD：`b18d6b7ef296147a7568c7c77add225a442ad006`。以实际 `git diff HEAD` 为边界，不沿用旧文档中的 fc9ba69。
- 31 个文件均为暂存改动；`git diff HEAD --binary` 的 SHA-256 为 `02bf5c1cabd97aeef5740b12cd0e2279d4e18af21fd104742b540fe021efa011`。
- `rv64d.ir` SHA-256：`d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。它不是历史隔离运行使用的 73df IR。
- 审查核心为手写 Rust、脚本、接口及调用关系；生成 IR 核对浮点声明/普通 helper 接线，未重做整个生成模型的语义等价证明。未改独立内存 worktree。

## 正式问题

### R1 / P1：浮点见证策略无条件污染所有 solve-state 的终态

位置：`isla/src/isarch/exec.rs:944–957,995–1015,1244–1248,1348–1351`。

`materialize_finished_case` 在 `ConstructorDiagnostic` 模式下对每个 clause 都执行 `constrain_enabled_fp_vector_witness`，向同一终态 solver 直接断言初态 `mstatus.FS=3`、`VS=3`。没有检查该路径是否允许这两个值，也没有浮点 clause 限定。它不是单纯的格式化操作：原先 SAT 的路径若要求 FS/VS=0、1 或 2，追加断言后为 UNSAT，随后变为 `ExecError::NoModel`、`materialization-error`，并使整个 clause 返回错误。原本未约束这些位的整数指令输出也被统一钉成 Dirty。

真实语义消费者包括 `sail-riscv/model/extensions/FD/fdext_control.sail:18–19` 的 FS 非零检查和 `model/extensions/V/vext_control.sail:17` 的 VS 非零检查；普通 CSR 指令访问 fcsr/frm/fflags 也经过前者。是否某个完整 IR 输入形成独立终态，本轮未做端到端复现；“已约束为非 3 的 SAT 终态会在此失败”由当前控制流和约束直接确定。

建议移除该无条件断言。若需要优先选可编码见证，应只在终态仍可满足时采用候选，保持原模型可以输出；编码失败按真实原因记录。当前单测 `direct_retire_witness_enables_fp_and_vector_context` 只测无约束 mstatus，未覆盖与已有路径约束冲突的情况。

### R2 / P2：保留了生产入口不可达的完整编码—译码框架

位置：`isla/src/isarch/exec.rs:27–85,818–943,960–993,1119–1123,1258–1283`。

`SOLVE_ENTRY_MODE` 被硬编码为 `ConstructorDiagnostic`，生产调用固定进入 `zexecute`。全仓检索 `install_solve_wrapper` 只有定义和两个单测调用，没有生产安装点。`FullEncoded32` 的 wrapper 生成、固定 PC 阶段识别、wrapper 变量读取、编码再译码一致性校验、encoder rejection 见证等仍留在通用路径里，使当前只运行一个入口的逻辑承担两个模式的维护成本。单改常量也不能恢复模式，因为还缺 wrapper 安装。

建议从本轮生产代码中移除不可达模式及只为它服务的辅助，必要实验保留在专题测试工具；确实重新启用时再一起提交完整接线。不要误删 `mod.rs` 的 `run_mapping` 和顶层拒绝识别：当前直接入口仍真实使用它们做汇编和编码。

另有明确残留：`exec.rs:376` 的 `should_collect_unfinished_path` 只被单测调用，生产 collector 已不用它。其单测不能覆盖当前 collector 的实际行为。

### R3 / P2：catalog 初始化隐式改变既有 ITRACE 输出契约

> 2026-09-29 回查补充：当时的 `solve-fix-runtime-design.md:199` 明确记录，经总协调请求批准紧凑输出，以缓解 FLI_S 完整 trace 约298MB的体积开销；对照降至约60MB、有序分支边相同。此格式变化有明确动机，不能称为偶然副作用。原问题具体指 API 将“运行时索引就绪”与“输出紧凑格式”绑定；catalog 本身解决的 assert 改写后定位问题仍需保留。详见[历史对照](solve-fix-trace.md#p1-fli_s-联合运行及紧凑模式)。

位置：`isla/isla-lib/src/tracetool/itrace.rs:833–880,944–966`；调用方 `isla/src/isarch/exec.rs:753`。

每个开启 ITRACE 的 solve clause 都安装 runtime catalog；`render_lines` 又把 `runtime_catalog_ready` 同时当作紧凑输出开关，跳过全部普通指令行。用户继续使用同一 `--itrace`，得到的却是函数集合、总指令数和 branch edges，不能再读取逐指令执行顺序。这一变化影响所有指令，且没有显式输出模式选择。

运行时 catalog 修复 assertions_to_jumps 后的 PC 映射是合理需求；让它顺便决定输出格式没有必要。建议分开这两个职责，保留完整输出能力，紧凑格式单独选择。现行紧凑模式还构建所有普通指令的 Debug 字符串而不输出它们，可随模式边界一并收缩。

### R4 / P2：新增进程测试把当前机器的 Python 布局当成前置不变量

位置：`isla/scripts/test_solve_cleanup.py:222–229`。

测试强制 PATH Python 与 `/usr/bin/python3` 不同，并要求前者恰好具有 `pidfd_open=False`、`pidfd_send_signal=True`。在正常的系统 Python 环境中，两个入口指向同一解释器，测试立即失败，尚未验证任何进程清理功能。主审已复现下方命令的退出 1，失败位置为第 223 行。

建议用受控的兼容性测试环境，或按实际可用解释器测试并跳过不存在的额外组合。`solve_process.py`、清理测试和 `run_ctrl_c.mk` 替换本身属于独立进程管理修复；旧全局 pkill 的确有误杀问题，但该修复不依赖 Z3 浮点数值支持，应独立提交、独立验收。

## 封装和必要性判断

| 改动 | 判断与建议 |
| --- | --- |
| `primop/float.rs` 补 ToIEEE、ToUnsigned、BF16；接收具体/混合 BV；验证真实 sort | 浮点核心，保留。复用已有 Z3 FP 表达式和原语注册方式；BF16 没有另建全套类型系统。 |
| 删除旧 `softfloat_dispatch` 及 Rust 专用 helper | 必要简化。架构语义由 Sail 普通函数体承担，通用数值运算由 Z3 原语承担。 |
| `fp_arg`、`rm_arg`、`bv_arg`、`scalar_sort` | 真实多处调用，不属于过度封装；`bv_arg` 继续复用既有 `smt_value`。 |
| fcsr、完整 pre/post 状态、错误传播、terminal 账本、采样标记 | 支撑浮点结果/flags/状态重放与验收，可以保留；不要因处于通用文件就全部判为无关。 |
| `fmtval.rs` 使用 `BV::to_vec()` | 真实宽位输出修复，代码改动很小；向量浮点状态输出需要它。 |
| `SharedSequence<T>` | records、branch_conditions、branch_edges 三处生产复用；共享 fork 前缀和迭代析构有具体用途，属于合理重构。可独立成性能提交。 |
| `Model::concrete_cache` | 单 Model 缓存具体值，completion 切换时清空；直接服务重复状态物化，边界小，未见过度封装。 |
| `primop.rs` MixedBits 拼接优化 | 复用已有表示，属于通用性能支撑；建议独立提交，避免与 FP 数值接口混合审查。 |
| `solve-fd-nonmem`、77 清单、旧 SoftFloat 回归迁移 | 直接支撑浮点验收，保留。 |
| 全局进程监督器与 pidfd 手动停止 | 有独立修复价值，拆分提交；不应视为浮点功能必需的抽象层。 |

另两项应明确行为边界：`isarch_main.rs:463–467` 默认将全部 solve-state 的断言转换为分支；`target.rs:435–595` 新增 S/U/H 能力探测和特权态、SXL/UXL、MPP 合法域约束。它们有覆盖与状态合法化的理由，但影响全部 RV64 clause，应单独说明、提交和验证，不能仅凭浮点原语测试通过签收。

可顺手减少的薄包装：`isla/src/isarch/mod.rs:186–194` 的私有 `get_assembly_encdec_forwards` 现在只原样转调 `run_mapping`，两个调用点可直接调用后者；它没有独立契约。`exec.rs` 的 `AssemGenJsonItem::new` 是单生产调用、12 个参数的字段搬运，可直接构造结构体。两项优先级低于 R1–R4，不建议为了消掉几行再建立新 builder/trait。

未升级为正式故障：MixedBits 新越界断言与具体位串线性化后越界切片处理不一致（`primop.rs:1097,1180–1206`）；本轮未证明真实输入从旧成功变为新失败，因此仅列后续定向验证风险。

## 本轮验证

以下命令除 Python 的显式 PATH 设置外均在 `isla/` 执行，使用当前默认 Cargo features；不是完整 solve 或 SoftFloat 全量差分验收。

| 命令 | 结果 |
| --- | --- |
| `cargo test -q -p isla-lib --lib primop::float` | PASS，10/10，退出 0 |
| `cargo test -q -p isla --bin isarch` | PASS，24/24，退出 0 |
| `cargo test -q -p isla --lib` | PASS，84/84，退出 0 |
| `env PATH=/usr/bin:/bin /usr/bin/python3 scripts/test_solve_cleanup.py ProcessTests.test_default_and_system_python_run_kill_combinations` | FAIL，1 项失败，退出 1；两解释器均为 `/usr/bin/python3.14`，触发第 223 行不等断言 |

未重跑 `make solve`、77 项长批、完整 IR 等价或开启 itrace feature 的动态输出测试。R1–R3 为源码/调用关系审查结论，R4 有动态失败复现；上述小测试通过不消除正式问题，也不迁移历史全量 PASS。

## 建议收口顺序

1. 修复 R1，去掉不可满足的全局见证钉值；用已受 FS/VS 约束的终态验证。
2. 删除 R2 的不可达生产路径和废弃辅助，保留真实使用的 mapping 公共实现。
3. 拆开 runtime catalog 与 trace 输出模式，明确完整与紧凑输出的契约。
4. 将进程管理修复、通用 MixedBits 优化、模型缓存和 trace 性能重构分别成可审查提交；保留已证明必要的依赖顺序。修复机器相关测试。
5. 浮点核心提交保留原语、专用分发退役、匹配 IR 和迁移回归；状态/验收支持单列。此次不执行拆分、重置、提交或源码修复。

## 用户明确边界后的实施接续

用户明确：Make solve 应直接以 Execute 为入口，编码模式是排查期间误加的逻辑；只删除暂存区相对 HEAD 的相关改动，最初已有的求解后 `test-ins-encdec` 字段不在删除范围。封装只计算生产代码复用；测试专用复用应放在 `mod tests`，不能反向作为生产抽象的依据。

实施仅修改 `isla/src/isarch/exec.rs`，相对此轮开始的暂存文件为 +105/−479 行：

清理后源码 SHA-256：`a25a85b01cff7ed48e78776ae683f6927170fadf37f137827753c3c9ba7f38ca`；基线仍为 `b18d6b7` 加原暂存改动。

- 删除 SolveEntryMode、wrapper IR 安装、编码/译码变量与固定 PC、译码一致性证明、encoder rejection 检查及专属见证逻辑；生产直接调用 `zexecute`。
- 删除为编码强加初态 FS=VS=3 的约束。原有求解后汇编文本和 `test-ins-encdec` 输出流程保留，未引入新的编码回退逻辑。
- 删除编码模式专属 JSON 字段 `decoded-instruction`、`entry-domain`、summary 的 `entry-mode`，以及 terminal 中仅服务 non-encodable 分支的 requested/state/witness-error/mapping-source 字段。执行结果本身、case-id、path-signature、gen requested-instruction、pre/post 状态及 execute/materialize 阶段仍保留。
- 删除与退役模式对应的四个单测，在 `mod tests` 新增真实物化回归：固定 FS/VS 全部 16 种组合，检查 pre/post 保持指定状态，同时检查原有编码字符串仍为 `32'h0000_0053`。没有为该测试增加生产 API 或辅助函数。
- catalog 与进程脚本本轮未改动。核对 HEAD 后，`AssemGenJsonItem::new`、`SolveCollectorState::new`、`should_collect_unfinished_path`、ErrorRecorder 的既有封装不列为本次删除对象；上文薄包装建议不能被理解为授权清理这些基线代码。

### 接续验证与证据

命令在 `isla/` 执行；临时目录改用 `target/execute-entry-cleanup-20260928/tmp`，避免系统 `/tmp` 配额耗尽。

| 命令 / 版本 | 结果 |
| --- | --- |
| 旧代码加新回归，`cargo test -q -p isla --lib materialization_preserves_constrained_fs_vs_and_encoding_output` | RED，退出101；FS=0/VS=0 在真实物化阶段报 `No SMT model found` |
| 清理后同一回归 | GREEN，1/1，16 组合均通过，退出0 |
| `cargo test -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt`，TMPDIR 指向上述项目内目录 | PASS，84 库测试＋24 bin 测试，退出0 |
| `cargo fmt --all`、`cargo fmt --all -- --check`、`git diff --check` | PASS |

原始日志：[red](../../isla/target/execute-entry-cleanup-20260928/red.log)、[green](../../isla/target/execute-entry-cleanup-20260928/green.log)、[regression](../../isla/target/execute-entry-cleanup-20260928/regression.log)。原受审源码仍由首轮 diff 哈希定位。删除前含新增回归的源码副本保存在同证据目录的 `exec-before-cleanup.rs`。

未重跑完整 Make solve、77 项批次或完整模型重放；旧 FS=VS=3 见证批次不能转记为此次清理后的验收。更新了 JSON 模式字段，历史冻结脚本继续按原产物版本解释。源码清理留在工作区，未改原暂存快照、未提交。
