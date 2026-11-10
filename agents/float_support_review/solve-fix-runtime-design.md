# solve 完整性修复：运行器设计与实施边界

2026-09-26。依据当前主工作树 `exec.rs`、`target.rs`、`mod.rs`、executor、itrace 和正式 IR 核对；本文件只规定运行器改动，不表示实现或验证完成。总计划由 [总架构](solve-fix-architecture.md) 与 `plan.md` 统一。独立内存工作树不在本轮范围。

## 1. 必须保持的语义

- 官方浮点求解保留 constructor 参数和现有运行态的完整符号域。`fcsr`、FS/VS、`vl/vstart/vtype`、mask/tail 与寄存器号不能固定为代表值。
- 模型完成仅在终端路径输出具体 witness 时使用；不能先取得一个编码或初始状态再将其执行结果当作符号全集。
- 自然结束、合法 Retire、没有丢失或失败终态、具体记录可重放分别验证。部分路径 JSON 不构成成功。
- 真实译码不接受的 constructor 域可以公开列为边界终态；不能默默过滤，也不能计为 Illegal、Retire 或已验证合法样例。
- 结果仍使用现有 `PreStateCtx`、`RegisterBindings`、`FmtVal`、`Model`、executor 和 `ItracePerPath`；不另建求解器或指令语义框架。

## 2. 当前实现事实

1. RV64 `reg_list()` 没有 `fcsr`；`mstatus` 虽被主动符号化，但 `solve_pre_state` 会省略 Arbitrary 值。只有四个向量上下文寄存器强制输出。
2. `AssemGenJsonItem` 没有 post-state、路径关联字段，扩展字段固定为 `IMACFD`。`frame.regs()` 才是执行后的寄存器；参数 `regs` 是入口寄存器。
3. `SolveCollectorState::record_error` 只接受 Timeout/Smt。Unknown、类型错误、MatchFailure、AssertionFailure 等可能不影响成功状态；Poison、Exit、Suspended 没有完整结果。最终非 SAT 或被 `catch_unwind` 捕获的 model 构造失败还可能落出空字段记录。
4. `mod.rs` 的 assembly/encdec helper 会新开执行会话；它们不能承担符号入口与当前路径之间的关系证明。当前调用还使用入口的原始 `regs`，没有体现输出 witness 的运行态。
5. 现有 `--fork-assertions` 已通过 `ir::assertions_to_jumps` 把 assert 变成显式 Jump/AssertionFailure；无须再写断言执行器。Optimistic 只检查 true 可满足，会隐藏同一前置条件下仍可满足的 false 域；Pessimistic 在 false 可满足时结束当前路径，也不能保留双方。
6. `TaskId` 在 fork 时继承；`path_signature` 是排序指纹，都不能单独充当运行内绝对唯一的 case ID。
7. 正式 IR 的 `zencdec_forwards` **也执行 mapping guard**。例如 BF16 包含 `currentlyEnabled` 与 `get_sew()==16`，并非与运行态无关的位拼接器。

## 3. R1：状态快照，独占 target.rs

可写文件：`isla/src/isarch/target.rs` 及该文件既有单元测试。不改 JSON collector、executor 或内存代码。

### 接口与输出

- RV64 `reg_list` 增加 `fcsr`，按其原始 IR 类型通过既有 `symbolic()` 和 `PreStateCtx` 建立与执行帧相同的值。
- 旧 `solve_pre_state` 可以保留稀疏兼容行为，但格式化错误必须传播；增加完整 pre-state 物化接口，输出本目标所有实际存在的 pre-state 寄存器。
- 增加 post-state 物化接口，参数为 `frame.regs()`、同一 `Model`、`SharedState`；用 `get_last_if_initialized` 获取实际末值。目标清单中应存在且初始化的寄存器缺失是内部不变量错误，不能略过或读入口值替代。
- collector 在任何 instruction/pre/post 物化之前创建一次 `Model` 并启用 complete model。所有字段使用这个 model；不能各自重求一个模型。原始模型配置与初始化环境以受测 manifest 固定。
- 完整快照至少包含 x1–x31、f0–f31、vr0–vr31、cur_privilege、mstatus、fcsr、vl、vstart、vtype、vcsr 中实际存在的项。IR 不存在的架构项不伪造值。
- 非访存运行若发现依赖清单外的非固定初始寄存器，必须扩展完整输入快照，或在可重放 manifest 中明确其固定初始化来源。不能仅凭清单名字认定完整。

不要从 post-state 的 `read_init_value_if_initialized()` 反推通用 pre-state：普通非 relaxed 寄存器写入不保留旧值；应继续使用执行前 `PreStateCtx`。

### TDD 门槛

1. 未受约束的 mstatus/fcsr 也出现在完整 pre-state；预先声明的 FRM 与五 flags 保持独立符号，测试两组不同赋值均 SAT。
2. 真实小 IR 写目标寄存器、OR 新 flags、清 vstart；同一记录 pre/post 分别为写前/写后值，未写寄存器保持一致。
3. 旧稀疏字段仍可消费；完整状态在同一 model 下与 instruction 参数、post 表达式一致。
4. 错误格式化不能返回部分成功 map；目标缺失与未初始化不能用 0 填补。

现有 `rv64_target_trait` 测试已要求 x0/PC，而实现没有列出；此为本轮前已存在的不一致。实施时先记录基线，不因本任务盲目主动符号化 x0/PC。它们是否进入观测清单应按实际 IR 和已有目标契约处理。

## 4. R2：终态与真实入口，独占 collector 及 isarch 接线

可写文件：`isla/src/isarch/exec.rs`、`isla/src/isarch/mod.rs`、`isla/src/isarch_main.rs`；需要新增小 wrapper 构造模块时仍由本 lane 独占。若要为 `ExecError` 增加 Clone，由本 lane 提交一个明确的 `error.rs` 小改动，其他 lane 不同时写。

### 4.1 兼容 JSON

旧 `gen`、`isa-state`、`test-ins`、`test-ins-encdec`、`ret_val` 保留。新增字段的最小契约如下；精确字段拼写由实现前统一给 replay lane。

| 字段 | 内容 |
| --- | --- |
| `case-id` | clause 内由 collector Mutex 分配的递增 ID，与 clause/本次运行标识组成唯一键。 |
| `path-signature` | 既有指纹，继续用于稳定排序；不是唯一性承诺。 |
| `requested-instruction` | 调用者指定 constructor 及物化参数。 |
| `decoded-instruction` | 同一符号编码经真实 decoder 得到的 constructor 及参数。 |
| `entry-domain` | 成功译码、译码 ILLEGAL、明确不可编码 constructor；后者只进入终态账本。 |
| `isa-state-complete` | R1 提供的完整具体初态。 |
| `isa-state-post` | 同一 model 下的实际完整末态。 |
| 顶层 `summary` / `terminals` | 所有回调终态、阶段、source/function、成功/拒绝/UNSAT/错误/采样计数及最终 complete 判定。 |

`ext` 不再写未经核实的固定 `IMACFD`；使用实际模型配置的扩展信息与 manifest 引用。运行态使能与静态 hartSupports 分开，不能用配置支持代替 FS/VS 等动态 guard。

每个 collector 回调先分配 ID、记录一个终态，再尝试具体物化；物化失败属于该终态的失败阶段，不能丢掉原执行结果或增造第二条执行路径。输出配额只影响 `gen`，不影响终态计数、错误状态或覆盖证据。

### 4.2 错误分类

| 终态 | 完整性处理 |
| --- | --- |
| Finished Retire / Illegal 且最终 SAT | 成功架构结果，完整物化后可进入 gen。Illegal 本身不是运行器错误。 |
| Finished 但最终 UNSAT、Run::Dead | 明确不可满足终态；不生成空结果。记录 UNSAT 排除，不计覆盖成功。 |
| SMT Unknown/Error、Timeout、NoModel、Type、缺函数、越界等 | 明确错误，整个 clause 不通过；保留阶段与源位置。 |
| Poison、Exit、Suspended | 非正常完整结果；单指令 solve 不能认作通过。Poison 还保留 Sail exception 信息。 |
| execute 阶段 MatchFailure / AssertionFailure | 真实 decoded 域中的失败；不能静默。 |
| encode 阶段 MatchFailure | 仅当精确 function/source 与已审 mapping guard、constructor 域对应时标 expected non-encodable；嵌套/未知匹配失败仍是错误。 |
| 输出 assembly/encoding/state 格式化失败 | 物化错误；不能跳过后保持成功。 |
| 分支采样、truncate、keep_current_model | 单独 incomplete 计数；即使没有 ExecError，也不能宣称完整求解。 |

扩大 `first_error` 范围必须保留原错误内容。`ExecError` 当前未实现 Clone，可在确认所有字段后派生 Clone，或让 collector 持有首次错误所有权；不能将所有错误伪装成 Timeout。删除吞 model 构造 panic 的 `catch_unwind`。内部不变量破坏遵循仓库直接 panic 的规则。

### 4.3 同 solver 的 encoder → decoder → execute

优先在 isarch 初始化时用现有 IR `Def/Instr` 构造一个很小的 wrapper，并复用 `execute_ir_function_with_checkpoint_multi_thread` 执行整个 wrapper：

```text
requested := 全符号 constructor
encoded   := encdec_forwards(requested)
decoded   := ext_decode(encoded)
result    := execute(decoded)
```

wrapper 保留 requested/encoded/decoded locals，供 collector 读取；所有步骤共享初态、求解约束、执行限制和 timeout 生命周期。不是在 Rust collector 中对某个 model 的编码重新开一个“符号执行”调用。

- `zext_decode` 和 `zencdec_forwards` 已存在；`execute ILLEGAL` 返回正常 `Illegal_Instruction`。使用它们的真实语义，不另抄一份扩展/SEW/RM 合法条件。
- 必须核验成功 decoded constructor 及参数与 requested 的关系。意外解码到其他指令不是悄悄换目标成功；合法 alias 若存在须明确证明/记录。
- encoder guard 失败单列不可编码 constructor 终态；这不证明同一物理 word 已走 decoder Illegal。需要 word 级负例直接调用 decoder，补证 FS/VS Off、SEW 不匹配等真实位编码域。
- 不可编码域的识别须基于已审 source mapping，不允许“所有 encoder MatchFailure 都正常”。无法识别时保留失败，并由架构复核原因。
- `mod.rs` 的纯 assembly printer 可继续对物化 instruction 运行，但要使用与该记录一致的完整初态；不得让独立 helper 的默认运行态改变编码合法性。正式编码直接来自 wrapper 的 encoded 符号值。
- 不直接全局替换其他工具的 constructor 入口；完整 solve 的入口模式与 schema 显式记载。原 constructor 诊断模式如保留，必须标注不同的可达域。

这增加真实 encoder/decoder guard 的分支与 SMT 开销。应先小 fixture 和 BF16/FLI/FADD 实测；不能因为预算变化再退回具体编码入口。若采用分阶段 checkpoint API，需要证明约束、初态、deadline、limits、错误和路径 ID 连续，成本高于一个小 wrapper。

本轮 77 项均为 32 位编码；当前 IR 的 `zencdec_forwards : instruction -> bits(32)`、`zext_decode : bits(32) -> instruction` 可直接连接。成功 decode 的 alias 允许集为空：constructor 与所有字段关系须一致，不能只比较一个具体模型。

严格 mapping 缺省失败的可操作识别：从实际运行时 `zencdec_forwards` 函数验证唯一末尾 `Exit(MatchFailure)`，核对 requested 为已审 77 项且对应 Kind arm 与 mapping SourceLoc 存在；回调的当前 function/PC 必须精确命中该退出点。将位置、源位置、constructor 对应关系、原 IR SHA 和变换配置写入本次 catalog。d012 原 IR 的退出点是 PC 31450、SourceLoc 标记 22483，这只是该版本事实，不能跨 IR 硬编码。嵌套 helper MatchFailure 的当前 function 不同，仍为错误；结构不再满足唯一缺省失败时停止自动分类并重审。

上述规则经总架构确认。它只证明“模型编码关系在此初态无像”，不证明 guard 本身正确；相应真实 word 的合法/负例缺失时，branch 验收仍未闭合。成功 requested/decoded 关系应检查当前路径下不相等条件 UNSAT；SAT 是关系错误，Unknown/Error 是求解失败。

### 4.4 assert

完整模式复用 `assertions_to_jumps`，在 primop 替换前对函数处理；成功/失败两臂都交给既有 executor。避免重复转换。原始 IR SHA 与运行时变换均记入 manifest。

在 decoder 已接受的路径上，assert false 为模型/执行问题；mapping 本就拒绝的域在 encode/decode 阶段公开分类。这使 BF16 的 SEW assert 与真实合法域关系可检验，既不把所有 assert 当作正常过滤，也不把正常译码拒绝一概判 bug。

### TDD 门槛

1. 小 IR 分别触发所有上述错误类、Poison、Exit、Suspended、UNSAT；每条终态可见且成功状态正确，没有空 gen 或无声消失。
2. Bool 符号 assert 的 true/false 均 SAT：两臂均出现；guard 已保证 assertion：false 不出现；encoder 精确拒绝域与执行失败不混淆。
3. encoder 读取符号运行态，decoder 检查同一状态；两个合法 rm、多个寄存器参数仍可达，不能只剩一个 model。
4. encoder guard 拒绝、decoder ILLEGAL、意外其他 constructor、嵌套 MatchFailure 分别测试。
5. 同一结果具体重放达到原 ret 与完整 post；动态 FRM/初始 fflags 的区分输入不得被省略。
6. 多线程回调 case ID 唯一、summary 总数守恒、输出配额不隐藏失败。

## 5. R3：关联轨迹与运行时坐标

独占 `isla/isla-lib/src/tracetool/itrace.rs`、executor 的轨迹提交接口及 Jump 记录点；确需只读 getter 时改 `executor/frame.rs`。不要并行修改 R2 文件。性能 lane 若也修改 executor.rs，由 root 分函数/补丁顺序安排。

### 接口

- 在现有 tracer 中增加通用 terminal metadata，含 `case_id`、`status`、`phase`、`path_signature`；不把 isarch 专有 JSON 类型塞入 library。
- 新提交接口形状为 `submit_itrace_for_local_frame_with_metadata(frame, shared_state, diagnostics, metadata)`；旧 API 作为兼容入口保留。R2 将同一个 ID 写入 JSON、日志与 tracer。
- `ItraceCompletedPath` 保存 metadata，所有正常、失败、UNSAT、不可编码终态都能提交。AssertionFailure 不再特殊禁止提交。
- 从 **实际 `SharedState.functions`** 输出运行时函数/PC/指令/SourceLoc catalog，或用其构建现有 `IrFileCache`。assert 转换新增 handler 后，不能还按原 `.ir` 文件行号解释 PC。
- 分支证据需要实际执行的 edge：具体 Bool、只一臂 SAT、两臂 fork 的各自已执行方向都记录；仅调度未完成的分支另列。调用上下文用既有 backtrace，重复循环命中不与其他调用混接。
- 复用既有 ItracePerPath 记录机制；若为了大批运行减少体积，可在同一 tracer 中只保存 branch/source/终态所需记录，不能以丢失分支或调用上下文换小日志。
- 采样摘要纳入 complete 判定。纯 SMT ITE 不伪装为 executor branch，继续由数值/状态证明覆盖；源码层分母与 IR branch 分母各自说明。

已发给 R2/R3 的具体共享类型为 `ItraceTerminalMetadata { scope: String, case_id: u64, status: String, phase: String, path_signature: u64 }`。scope 为 clause，`(scope, case_id)` 在本次 run 唯一；JSON 的 `summary.clause` 与 `case-id` 对应。status 使用 retire/illegal/decode-rejected/non-encodable/unsat/error/materialization-error，phase 使用 encode/decode/execute/materialize。采样是额外不完整属性，不覆盖原本的 Retire/Illegal 分类。

metadata 类型和提交 API 应在无 tracetool feature 的构建中同样可用，例如定义于常驻的 `tracetool.rs` 或 executor 并由 itrace 引用。无 feature 时仍保留 R2 的 JSON 终态账本；不能因类型落在 gated 模块导致普通 release 无法构建。

### TDD 门槛

1. 固定 Bool Jump、仅一臂 SAT、两臂 fork：每个已走方向都带实际 PC/SourceLoc 与最终 case ID。
2. 递归/重复调用与循环：上下文不同的同 PC 不串接。
3. assert 转换后 handler 的 catalog 与实际 PC 相同，失败路径终态可关联；原 IR 文件不能误指另一条源码。
4. 多线程 case/terminal/itrace 一一关联；采样/外限/错误不会被写成完成的分支结果。

## 6. 独立 replay/coverage lane 的边界

该 lane 只消费 R1/R2/R3 的协议，写 fixture、审计与重放脚本，不修改它们的生产文件。

- 用完整 pre-state、同版本 IR/模型初始化与编码走真实 decode→execute，比较 ret 和每个导出 post 寄存器。生成的 expected post 来自求解输出，只证明重放一致；数值正确性仍须独立 oracle。
- 保留独立 oracle 的现有样例并补 guard/flags 情况；每条测试使用 case ID 绑定 branch 证据。
- 对不可编码 constructor 保存它的 guard/源码边界证明，并补真实 word 的 decoder 负例；不能把它加入合法 Retire 覆盖计数。
- 官方 77 项须自然完成、有合法 Retire、无未分类失败或采样截断；退出 0 和有效 JSON 只是其中两项。全部源码 branch 结论仍需明确分母与不可达依据。

所有实施者按 isla 的 TDD 先保存红测试，再实现并记录绿测试，修改 Rust 后运行 cargo fmt。本设计不预报 77 项性能结果；调通由新的实际批次证据判断。

## 7. 独立实施复核记录

- R1 第一阶段 `target.rs` SHA-256 `de2658391cf874860b7f7ed522112ddd0c18e949f8af9f5d688657d5080cd4d8`：独立核对生产代码使用同一调用者 Model、pre 使用执行前快照、post 使用末帧真实寄存器。RV32/RV64 的真实 Sail/IR 都为 `Fcsr{bits:bits(32)}`，附带增加 RV32 fcsr 有类型依据。
- 首版测试将 fcsr 当裸 bv64，不能证明 Sail bitfield 结构路径；复核后补入真实单字段 Fcsr/Mstatus、`Ty::Struct` setup 和依赖原 fcsr 的符号 OR 写回，精确检查 `0x20→0x21`。独立重跑所记测试二进制的 target 测试为 29/29；构建日志文件名 `isla-r1-target-tests-20260926.log`，SHA-256 `0cc1b2b7a79a3396ec38ca07cc0f7e12c08322bd97a81399ffa2ed73fe10d465`。这只验收 R1 第一阶段组件；真实 executor、collector 与重放待集成验证。
- R3 复核发现仅以 branch `sample_ordinals` 判断采样会遗漏 Monomorphize 的 `KeepCurrentModel`：该分支丢弃 SAT remainder 却不更新 ordinal。已交实施者加通用路径采样标记与具体红测试；该问题修复和验证前不得写完整运行器通过。
- scalar/vector/BF16 的新定向包统一由 IR 集成负责人接入 R3 的 runtime catalog 和 terminal metadata；每个输入名映射各阶段实际 terminal ID。静态 branch/obligation 标签只是测试计划，尚未绑定动态 edge 的记录不能标为动态覆盖。

R3 随后补入 `sampled_execution_domain`，普通 branch commit 与 KeepCurrentModel 均置位，随 frame fork 继承。独立运行 `cargo test -p isla-lib --features tracetool --lib itrace_ --quiet` 为 41/41，`runtime_catalog_` 为 3/3；无 feature 的 `monomorphize_path_limit_can_keep_current_model_without_forking` 为 1/1。测试前后五个相关源码 SHA 均未变化，日志及 `source-before.json`、`source-after.json` 保存在外部目录 `isla-runtime-independent-review-20260926`。该轮 executor SHA 为 `dbca79cbb665159dc4a839849fde7cbef97002fdb5f3cc2bd1648bc274807145`，limits SHA 为 `3e7b1abe575234a58d1e078b60b36d47364f76a99bdae935e06e873de3da03d0`。这证明组件记录覆盖所列具体分支形态；R2 接入及真正指令的动态源码覆盖仍须验证。

R2 独立审查另提出并交修：小 wrapper 必须在 encoder/decoder/execute Call 后传播 Sail `HAVE_EXCEPTION`，不能将异常返回的 Poison 传到下一阶段才报 Type；nested 错误阶段按 wrapper 调用栈识别。不可编码 witness 失败必须使 summary 不完整；assembly/legacy encoder helper 应读取同一 model 的具体初态，而非原默认寄存器。requested/decoded 符号关系证明须先于任何输出层具体候选约束。

### 经总架构确认的静态能力域补充

真实模型 `hartSupports(Ext_H)=false`，且 RV64 的 SXL/UXL 在初始化后由 `legalize_mstatus` 保持不变。把所有 Privilege 成员与这些只读字段任意符号化会制造源码不支持的内部错误；不能将这些错误吞掉，也不能以 TOML 中覆盖后的 `mstatus=0x6600` 推断静态能力。

R1 后续将以同一 IR/lets、空寄存器状态执行现有 `zhartSupports(Ext_S/U/H)`，要求唯一 concrete Bool、无寄存器/内存依赖、错误或采样。按所得能力保留全部支持的特权模式：Machine；S 支持时 Supervisor；U 支持时 User；H 与 S/U 同时支持时相应虚拟模式。RV64 的只读 SXL/UXL 按源初始化规则分别为支持该模式时 2、否则 0，并校验 xlen=64。FS/VS 和其余运行态仍保持符号。

这些静态能力、来源和约束以 `Target::domain_manifest()` 交 collector 输出；`constrain_pre_state` 改为可变 receiver 保存普通 domain 字段，无需 Mutex。合成 fixture 若两种相关寄存器均不存在可标不适用；真实模型缺失部分输入或无法探测能力必须停止，不能猜测。此追加改动实施后，R1 第一阶段 29/29 不能直接作为新版通过依据，须另行复验。

### MPP 域与实际 smoke 的追加复核

`zMRET` 诊断路径曾返回 `Invalid privilege level or virtual mode` Poison。实际源码 `core/types.sail::privLevel_bits` 缺少 MPP=`10`，`core/sys_regs.sail::have_nominal_privLevel` 对该编码恒为 false；reset、trap 和 CSR legalize 都不会产生这一保留编码。因此最小修正仅排除 `mstatus.MPP[12:11]=10`，保留 `00/01/11`。不按静态 S/U 能力进一步筛 MPP，也不约束 raw MPV：当前 `sys/sys_control.sail` 的 MRET 明确传入虚拟位 `0b0`，MPV 不是此次异常根因。

R1 最终 `target.rs` SHA-256 `3b7ebaf2180237e5dc6a89a7a12ace9129388f308b759fb29923674a11c4115d`。专项测试日志 `isla-r1-target-tests-mpp-20260926.log` SHA-256 `88a106c5d323bbb477457cdb07faa17ef24a5ef57499bbd8eb2813974c656d3a` 记录 34/34 PASS；独立重跑该构建测试二进制的 `isarch::target::tests:: --test-threads=1` 亦为 34/34。实际 [MRET JSON](tools/solve_runtime_tests/output/rv64_zMRET.json) 核得 `complete=true`、4 终态（3 Retire、1 Illegal）、0 Poison，manifest 含 `mstatus-mpp=0,1,3`、`reserved-mpp=2-excluded`。此为 constructor diagnostic smoke，不是 77 项正式译码入口验收。

旧 d012 的 [FLI_S JSON](tools/solve_runtime_tests/output/rv64_zFLI_S.json) 首条 witness 编码 `0xf0108053`，将 `f0` 写为 `0xffffffff00800000`，但 pre/post `mstatus` 都是 `0x0000000a00002000`（FS=Initial）。已与 FD 状态 owner 核实，这是旧 `set_F_bits` 快速写路径漏掉 Dirty/callback 的同一缺陷。当前源码已有修正；这份旧 IR 的 96 Retire 只能证明运行器终态/状态导出，不能作为 FD 状态正确性通过。新 IR 必须重验 FS→Dirty、SD→1 与未产生 flags 时 fcsr 保持。

R2 新 helper 已采用 sticky first-error，拒绝 Unknown/UNSAT、Poison 和异常返回，quota 内容排序不含回调分配的 case-id。独立审查仍要求补齐：顶层 mapping 拒绝必须是唯一末尾缺省退出，不能接受任意顶层 MatchFailure；嵌套 helper 采样必须报不完整；返回值不能带着独立 solver 的符号逃逸到外层 Model。真实 nested MatchFailure、wrapper 异常、同 model 写回和 16 位 diagnostic fixture 尚在补验，运行器整体暂不标 PASS。

### P1 的真实 JSON/trace 关联与紧凑输出边界

R3 在 P1 IR `f5141217f2695fb53a0584c1bc7dfa059eac15df51c07ae3f02307099e4b4a61`、配置 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987` 上取得 FLI_S 实际 trace。独立流式解析外部证据目录 `isla-r3-itrace-20260926.06EO4T` 的 `trace/itrace.txt`：25,924 个 catalog Jump、97 个 terminal block 与 JSON 的 scope/case-id/status/phase/signature 全部对应，297,721 条 edge 的 successor 与 SourceLoc 全部匹配实际 catalog，0 个异常。该批 96 个 gen 的 post 全为 FS=Dirty、SD=1。FD 独立 runner 另以首条编码 `0xf0108053` 重放，先 SAT，f0/fcsr/mstatus 与预期差异 UNSAT；这些结论只适用于 P1 与所列输入。

旧 d012 的 96 条 FLI_S gen 经独立解析是 32 个立即数与 U/S/M 的完整笛卡尔积；编码固定域、Sail 的 32 项常量表及 NaN-boxed f0 结果一致，102 个 pre/post 键一致、fcsr 均保持。96 条的 FS=Initial/SD=0 则全部暴露上述旧 Dirty 缺陷。旧 JSON SHA-256 为 `4f1139664d3e8612201c6b2a138058da42b6f8df4848a1ab9436af75cfc2c26b`，不能把常量表通过转写成完整状态通过。

R3 原文本 trace 约 298 MB，单次 P1 wall 从 13.66 s 增至 23.17 s。经总协调请求，批准 catalog 模式改为紧凑渲染：只省略普通逐指令文本，保留完整 catalog、按执行顺序的全部 edges/context/SourceLoc、terminal metadata、branch conditions、timing、limits/sample、所有 summary 与 timeout/异常诊断。应明确 `branch-compact` 模式，汇总 executed functions/instruction count 以保留无分支 helper 的调用证据；无 catalog 的旧输出不变。不得改变记录或求解过程。须先红后绿并以同 P1 做 A/B，严格比较 metadata/edges、JSON 内容与 catalog；紧凑 trace 不称完整逐指令轨迹。

### 正式批次与 replay 接口抽审

发现并交各 owner 修正两项集成阻断：正式 make 目标使用裸名 `FLI_S`，JSON/log/trace 实际 clause 为 `zFLI_S`，旧审计脚本误将二者直接比较；正式批 manifest 与 replay 消费者的 schema/相对路径基准不同，须输出明确适配的 replay manifest 并以真实 P1 fixture 验证。正式记录还须补 raw 与 canonical catalog 双哈希、损坏 edge/重复 catalog 拒绝、全部限制字段预检、实际 CLI/初始化来源/运行时变换绑定及批次结束与 make 退出核验。

Replay Rust runner 初版只输出实际 decoded 文本，未把完整 constructor/fields 与记录预期比较；已要求自动失败门槛，并补 Poison/sample 拒绝和 Cargo.lock/依赖源码绑定。不可臆造未导出的 x0/PC 为零；固定初始化与未初始化状态必须按实际 IR/config 声明。以上是审查事项，补验完成前不把正式脚本或全量 replay 标为 PASS。

完整导出的 102 项初态仍可能留下初始化中的符号辅助状态，因此独立 replay 不以 SAT 路径恰为一条作为唯一验收规则：若确有多条，须保留全部终态，对每条可满足 decoder 结果比较完整 constructor/fields，再对全部 execute 结果检查 ret 与所有导出 post。UNSAT/Dead 只计不可达终态；Unknown、Poison、采样和可达执行错误必须失败。不能只消费第一条，也不能添加约束强制单路径。若未导出的辅助状态影响观察结果，应补齐状态协议而非豁免差异。

上述“检查”不能仅对每条路径的一个 model 值比较。与总架构补充确认：每条路径须先 SAT，再以实际 symbolic decoded/ret/全量 post 对应的差异查询得到 UNSAT，证明该路径的所有辅助状态取值均产生相同观察结果。最小实现可在同一 Model 取得 concrete witness，复用 `eq_anything` 比较原始 Val 与该 witness，对其合取的否定求 UNSAT；消费者再自动规范化比较这一已证唯一的 witness 与 expected。Sat/Unknown/错误均失败。Replay 还须匹配官方入口的 `assertions_to_jumps` 与 `use_model_register_init=true`；原具体样例 runner 的 Optimistic 且无 rewrite、model init=false 不能直接用作正式 replay 配置。

R2 曾以 `C_ADD` 做 16 位兼容 smoke，具体输出模型选到 `rs2=x0`，触发 assembly 默认拒绝。源码 `extensions/C/zca_insts.sail` 的 encoder/assembly 都要求 `rs2!=x0`，但该符号执行终态仍包含非零 rs2；因此不能用所选 witness 的拒绝把整个终态改记 `non-encodable`。此外 C_ADD 返回 `ExecuteAs(RTYPE(...))`，本轮不新增该续接语义。保留其诊断失败，16 位正向 smoke 使用直接返回 Retire 的 `C_NOP`，精确验证 32 位 encoder 默认拒绝后 16 位 encoder 成功的兼容路径。

独立核对随后生成的 [C_NOP JSON](tools/solve_runtime_tests/output/rv64_zC_NOP.json)：`complete=true`、1 个 Retire、编码 `16'h0001`、文本 `c.nop`，102 项 pre/post 全无变化，入口明确标为 `constructor-diagnostic`，decoded 字段为空。这只验证所列 16 位兼容路径。日志中的 `No primop parse_hex_bits/emulator_write_tag/emulator_read_tag/valid_reservation` 来自 IR 初始化的 extern 绑定提示，应单列说明；若实际执行触达未实现原语，仍必须以执行错误失败。过期 `__isla_always_aligned` 的 FD 配置条目已交 IR 集成人清理，最终配置哈希需重新记录。

### R2 组件冻结复核结果

此前提出的 R2 helper 边界与真实 fixture 已补齐。实际 executor 小 IR 测试确认 encoder/decoder 抛异常分别短路到 wrapper PC 9/10，后续函数未执行；正常路径 Retire 且实际末帧寄存器从 1 写成 2，异常路径保留 1。嵌套 MatchFailure 不能被成功分支覆盖，顶层非末尾缺省失败不被豁免，helper 采样报错，返回值在自身 solver 内物化；Poison 的 throw_location 写入 terminal.source。decode-rejected 的 phase 为 decode，Dead/Exit/Suspended 按实际 wrapper 阶段记录。C_ADD 的 ExecuteAs 在物化前明确报错。

最终冻结 `exec.rs`/`mod.rs`/`isarch_main.rs`/`error.rs` SHA-256 为 `a1a400783d19aca3f599647fffb75f093a110985a9ff6d4752adc04ab21ab534`、`00f8259b4a4017b9e34757b29299f4ec08b4e3386d63e12bb68c6dc7724e8c30`、`dfc97b702674b452a0db443cd3f0323e53361465d643ba7751b5e32de5d74978`、`bec463f1e1d724f328d9dd3aaf99a911e39f5dc6618785d6ebea8e31306c31e6`。独立核对最终 debug binary `616efeb60ce72fed902f43fccd3ca05a28b11e886a9c1e03946c3271ca4bae00`、82/82 原始测试日志 `9612b1706c2c618ae962ffef0448bbb69e258abb19332406b323a903383cb5f8`、d012 IR 与配置 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0` 下四项新 smoke 产物，均符合[collector 记录](solve-fix-collector.md)。最后仅闭包命名及 throw_location 字段追加前的测试二进制已由本 lane 独立复跑 82/82，外部日志 `r2-all82.log` SHA-256 `3efa99b3ec2f950fb778390b500d23d9aad9d455e10abff23fa44423846419b4`。据此判 R2 所列组件门槛 PASS；新 IR、含 itrace 的正式 77 项及全量 replay 仍是独立验收门槛。

正式批脚本版本 `ca1f8d12096537797f44ff2855ed8f7475e1301fe5e45e145f5d3fe6ee13f9aa` 已独立重跑 6/6 测试，包括实际 make dry-run 的 77 条完整 CLI、真实 P1 字段的 z 前缀与 replay manifest 适配；额外损坏 edge/重复 catalog 均被拒绝，真实运行器 FLI_S JSON schema 核账无错误。此为该固定脚本版本的组件通过；其后的初始化 manifest 补充和完整新批消费仍需按新版本记录。

后续脚本 `fb3e188fe68ec875e17fd45759a9ba74d398f3600387771b63f2a3581fd93c05` 的隔离目录与记录增量亦经独立审查，7/7 测试通过，前后哈希不变。总协调批准使用已被 Git 忽略的 `isla/target/float-solve-evidence/<新批次>/stage`；快照选取排除 target，避免递归复制。Replay 准备工具须按同一精确目录边界允许该冻结 isla-lib，仍拒绝活跃源码；不能沿用“一律拒绝根仓内路径”而使正式产物无法消费。

### 续接独审：FmtVal 宽位输出与 replay 证明边界

`FmtVal::BitVal::from_bv` 旧实现把 `lower_u64()` 右移 `i`，在 B129 超过 64 位时丢掉高位；debug 会移位溢出，release 可重复低 64 位。修复复用 `BV::to_vec()`：该接口先在整个 BV 上右移再读低位，给出已有格式器所需的 LSB-first 全宽位序，与 `concat` 和十六进制输出一致。修后 `fmtval.rs` SHA-256 `43806138bf1f3981b198bdd1f35a611d650dac49cbef9537912a9ed6df7a679e` 已独立复核；64/65/128/129 位、Concrete/MixedBits 宽片段及 arbitrary mask 的定向测试在 debug、release 各 **2/2**。独立执行二进制 SHA-256 分别为 `0fdfdc73857c6995c702f3ac9891f72d40ec596d86e725513519e27ade4b05c8`、`e591b3a83ff4e86e25a1b49ecf53801d4846e90d3c98983b463d3fffbdb1107e`；此为该格式器组件通过。

Replay 消费端独立格式化路径现可接收 `Model::get_val` 返回的全部 Concrete MixedBits，按原高低片段顺序合并。真实完整 102 寄存器 vadd 的高低半部正例及旧重复低 64 位负控制已由 Rust/Python 同时验收，见[重放记录](solve-fix-replay.md)。初态 `misa` 使用配置默认来源；物理 PC/x0 若被读取仍失败。不得因消费者已能拒绝错误输出，把采用旧 FmtVal 的 c5 正式批改记为通过。

实现仍将 decoder 与 execute 分两段调用。架构独审认可其保守过近似条件：同配置及完整 pre、每条 decoder 路径的完整 AST 唯一、decoder 无状态或外部副作用，随后 execute 枚举扩大的辅助状态域并逐路径证明 ret/全 post 观察唯一。纯读前提已成为自动门槛：实际 IR 闭包前检禁止 register/let/间接写及 global `Monomorphize` 写回，未分类 callee 和函数假设失败；证书绑定 IR/config/runner/源码。动态 decoder 仅允许 Smt/Fork/Function/ReadReg。Dead 须再次 UNSAT，采样标记始终失败。没有把具体 model completion 变成额外路径约束；Model 丢弃后才向同 solver 添加差异查询。

新 Model 缓存仍在运行时 lane 验证中；本次 c5 replay 组件未包含该变更。最终 77 项验收须以包含全部运行时修复的新冻结源码、IR、配置和 runner 再跑，不复用上述旧版结果作为正式通过。

2026-09-27 追加：运行时 lane 放行后，以冻结 manifest `28fb65ee…` 的库和新 IR `1dcc8081…` 重建独立 runner，包含 Model 缓存 `smt.rs=3ce7310d…`。复核该缓存仅保存本 Model 的成功具体 Bits/Bool/Enum 值，切换 completion 模式清空，不缓存 Arbitrary/错误；replay 仍在 Model 释放后执行原符号值差异查询。Rust 9/9、新 IR 完整状态高位正/负控制及重生成 decoder 纯读证书均通过。新增 `strict_or_bool` 已按真实映射 `or_bool` 的纯语义逐项审定，白名单仅增加该名称；证书现在为248函数/568调用。完整版本/哈希见[新候选重放组件](solve-fix-replay.md#2026-09-271dcc-候选与最终运行时同版组件)。官方同批 77 项重放门槛仍待完成。

### 1dcc 正式输出回放和序列化边界

正式批次自然完成 50 项、超时 27 项且超时未形成最终 JSON；全部 50 项的 18,477 gen 已逐条证明 decoder 完整 AST、ret 与 102 项 post 观察唯一并与记录一致。107 个不可编码终态均有原 witness 初态下的物理 word decoder 负例，其中 24 个缺少同 payload 现成 word，使用明确记录的合法辅助 context 调用真实 encoder 生成唯一 word；辅助 decoder 再验与原 payload 同值，随后回到原初态做负例。不能用不同 payload 或辅助初态替代原 witness，也不能把派生负例称原 encode-first 路径重演。

首轮 Python 比较拒绝暴露名称打印协议差异：collector 对 tuple 字段名称只 zdecode 一次，普通 dprint 递归解码。消费端新增精确协议序列化后红绿通过；完整实际 Val 的差异 UNSAT 主合同与 Python 全字段比较保持。401 条 LLVM Illegal 拒绝逐条绑定冻结的 mask/寄存器组重叠 guard，全部参与动态回放；Retire 与语法错误无豁免。详细命令、原红/新绿及汇总哈希见[正式输出重放记录](solve-fix-replay.md#2026-09-27正式-1dcc-批次全部现有完整输出)。汇总只声明全部现有完整输出子集通过，27 项超时使 `whole-run-complete=false`。
