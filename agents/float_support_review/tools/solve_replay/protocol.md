# 官方 solve 记录的独立重放协议

本目录只增加消费端工具与 fixture，不修改 Isla 生产运行器。依据 [运行器设计](../../solve-fix-runtime-design.md)第 6 节；Astra 已审阅协议，R1/R2/R3 与官方批次编排者已确认字段契约。

## 输入与不可混淆的标识

- 一次调用接收同一批次根目录的 `replay-manifest.json`、IR、Isla 配置、官方 `rv64_z<clause>.json`、对应 itrace、输出目录。正式批次位于已批准且 Git 忽略的 `isla/target/float-solve-evidence/<run>/`；仓库外冻结目录也可用于组件测试。manifest 固定 IR/配置/官方二进制、Isla 与 Sail 源文件树、Cargo feature/锁文件、初始化来源及 `assertions_to_jumps`/model-init 变换；消费者逐文件核哈希。缺字段或哈希不符直接失败，不回退到主树当前文件。
- R2 JSON 顶层为 `gen`、`summary`、`terminals`。`summary` 包含 `clause,entry-mode,total,counts,complete,state-domain,emitted,suppressed`；终态含 `case-id,path-signature,status,phase,function,source,detail,sampled,emitted,witness-error`，不可编码终态另含 `mapping-source/requested-instruction/isa-state-complete`。每个 `gen` 保留旧字段，新增 `case-id,path-signature,requested-instruction,decoded-instruction,entry-domain,isa-state-complete,isa-state-post`；编码仍在 `test-ins-encdec`，为 Sail `32'h...` 格式。
- 主键是 `(manifest run-id, summary.clause, case-id)`。同一 clause 的 `case-id` 必须唯一且对应**一个**终态；`path-signature` 只作交叉校验，不当唯一键。每个 `gen` 必须指向同一签名、状态相容的终态；错误、未编码、UNSAT 等终态不能冒充正常 replay 用例。`summary.total == len(terminals) == sum(summary.counts.values())`，各状态计数须与终态逐项一致。`CaseQuota` 若把可物化终态从 `gen` 筛去，必须有独立抑制记录；否则 `replay_complete=false`，不能仅凭 `summary.complete=true` 声称所有终态可重放。
- R3 itrace 的 terminal metadata 用 `(scope,case_id)` 对应，另核 `status,phase,path_signature`。运行时 branch catalog 来自实际 `SharedState.functions`；每个 `branch_edge` 必须命中 catalog 的 function/PC/SourceLoc、合法 successor、taken 方向和调用上下文。trace 中终态 ID 与 JSON 终态应双向匹配；采样标记和 `sample_branch_condition` 使相应 clause **incomplete**。缺 trace 不得声称 branch 覆盖。

## 静态验收与产物

`audit.py` 只读核 manifest、77 项集合、每项目标退出码与 JSON/trace 绑定、case ID/终态守恒、sample/incomplete、branch 关联。输出机器可读 `audit.json` 和明细，分开写 `runner_complete`、`replay_complete`、`trace_binding_complete`；任一失败不转写成通过。`source_branch_closed` 须另取得 Astra 审核的源码 site/arm 分母与不可达依据，不能从 trace 绑定推得。正式 `gen` 全部进入 replay 队列，不能只抽样后称全量已验。若输出配额抑制成功终态，即使运行自然结束，也把全量 replay 结论标为 incomplete。真实不可编码 constructor 单列 guard/source 边界，并要求另有物理 word 的 decoder 负例；它不计 Retire 覆盖。

标准汇编文本的重汇编调用 `sail-riscv/test/assembly_text/check.py` 导出的 `assemble_texts` / `decode_encodings`，不复制 LLVM 命令。合法 Retire 必须逐条重编码与原 word 一致。LLVM 拒绝 Illegal 文本时，仅经 guard/操作数字段审核的非法重叠或寄存器组合可列 `confirmed-illegal-operand`，仍保留原 word 做 decode→execute；语法错误和 FLI 错误不能泛化豁免。汇编文本检查与编码→真实译码→执行重放分别给出结果。

## 批量 Rust runner

`prepare_runner.py` 将本目录 Rust runner 模板及锁文件复制到仓库外空目录或获批 `<run>/replay-runner/`，`isla-lib` 路径绑定本批冻结 stage；Cargo target 保持隔离。运行命令形状为 `runner <IR> <CONFIG> <cases.json> <out.json>`。一次进程只解析 IR、初始化架构**一次**，与官方入口相同地先做 `assertions_to_jumps`，使用 `Optimistic` 与 model register init，然后逐条 clone 初始化寄存器并应用 `isa-state-complete`，用同一初态把 word 交 `zext_decode`→`zexecute`。

寄存器输入值按 R1 `FmtVal::to_str` 解析：`N'h...` 位串（含下划线）、`cur_privilege` 枚举名；`fcsr/mstatus/vtype/vcsr` 按实际 IR 单字段 struct 装配。完整 pre/post 清单为 x1–31、f0–31、vr0–31、cur_privilege、mstatus、fcsr、vl/vstart/vtype/vcsr 中实际存在的项。物理 x0/PC 在当前配置与 IR 初始化中未赋值且未导出；架构 x0 通过 Sail `zero_reg` 得 0。manifest 如实声明，runner 若发现实际 `ReadReg(PC|x0)` 直接失败，不假填零。

允许残余辅助状态产生多条可满足译码/执行路径，但必须列举所有终态；Poison、采样、Unknown 与可达错误失败，Dead 单列为不可满足。每条 SAT 路径先用同一 model 物化 decoded/ret/全 post，再用 Isla `eq_anything` 对这些原始值与物化值的任一差异求 SAT，必须为 UNSAT。Python 再对已证唯一的值与官方完整结构/返回/每个 post 寄存器比较；struct 字段顺序归一化，值差异仍拒绝。预期 post 来自求解记录，所以这里只证明**同版本执行可重放一致**；数值正确性仍由独立 SoftFloat/规范 oracle 与现有定向样例承担。

实际 runner 分两次执行 decoder 和 execute。decoder 的每条 SAT 路径先证明完整 AST 唯一；execute 使用同配置初始化及同一完整 pre，从该 AST 重新枚举全部辅助状态。丢弃 decoder 的辅助状态路径条件扩大了 execute 验证域，因此通过结论依赖 decoder 纯读。启动时对已解析、尚未替换原语的实际 `zext_decode` 调用闭包进行前检：寄存器、全局 let 与间接地址写入均禁止，包含 `Monomorphize` 写回；函数、constructor、已审纯原语、配置常量与两个仅生成局部向量值的内部原语必须逐个分类。未分类 callee 或函数假设配置失败。`results.decoder-purity.json` 保存完整闭包、调用分类与 IR/config/runner/源码 SHA-256；`run_batch.py` 核哈希并将其作为完成条件。动态 decoder 仅允许 Smt/Fork/Function/ReadReg 事件；内存、写寄存器和外部抽象活动拒绝。Dead 还须再次证明 UNSAT，并拒绝采样标记。

全量 trace 核验使用逐行事件解析：catalog 常驻，每条 edge 即时核对，每个 terminal 与 JSON 双向关联，不保留整文件或整条路径的 edge 列表。文件哈希按 1 MiB 分块。`parse_trace` 保留小 fixture/既有覆盖工具的兼容接口，正式 `audit_run` 使用 `validate_trace_stream`；重复 metadata/catalog、孤儿 edge 和 trace 中的采样动作均失败。

完整 AST 的输出使用 collector 的单次名称 zdecode 协议；普通 `Val::to_str`/`to_str_fmt` 会递归解码 tuple 类型中的 enum 名称，不能用作该协议。该序列化发生在实际完整 AST 与同 Model witness 差异 UNSAT 之后，Python 仍逐字段比较，不丢弃 enum 类型或 payload。

## 增量完整输出与补充证据

`prepare_wave.py` 只在 `status.intime` 确认 isarch 已退出后冻结新目标，避免读到 `fs::write` 尚未完成的 JSON。每波保存原 evidence manifest、全部输入哈希和完整官方目标分母；`run_batch.py --incremental` 强制 `whole_run_complete=false`。版本修复使用 `replay-runner-rNN` 与 `replay-audit-wave-NNN-rNN` 新目录，保留原红证据。

找不到精确同 requested 字段的现成 gen word 时，`negative_words.py` 和辅助 typed encoder 保留原 payload/102 pre/hash，并选择同 clause 已 Retire/decoded gen 的完整辅助 pre。真实 encoder 的全部 SAT word 必须唯一且跨路径相同，辅助 decoder 再证 AST 完全一致，最后回原 witness pre 用正式 runner 证明 ILLEGAL/ret/全 post。辅助 context 和原 context 显式分开记录；无法编码的原 payload 不改值、不隐去缺口。

`review_illegal_operands.py` 仅处理已审 BF16 转换的 `vm=0 && vd=0` 或宽转换同 base 重叠，逐项绑定冻结 guard、真实 word 字段、完整标准文本及 LLVM 原始拒绝原因。原始静态失败保留。`aggregate_waves.py` 核对最终官方产物、全部自然完成目标和每条 gen、纯读证书、逐字段 replay、精确负例缺口及非法操作数补证；超时目标仍在完整 77 项分母，全部现有输出通过不等于整批完成。

## TDD 与正式接入

1. 先写纯 JSON/trace fixtures：重复 case ID、计数不守恒、孤儿 gen/terminal、签名不符、sampled 却 complete、无 catalog 的 edge 必须红；正确小 fixture 绿。
2. Rust 单测验证未约束辅助值可改变观察值时差异 SAT、固定观察值的差异 UNSAT；真实 P1 FLI 的完整 102 寄存器输入正例通过，故意翻转预期 `fcsr` 的负例失败。P1 的 96 个 `gen` 已用单次 IR 初始化做组件批重放；这些是组件证据，正式同版本全量结果另记。
3. 不可编码终态用相同 requested constructor 的已编码 word 配合该终态完整初态生成物理 word 负例，走真实 decoder；无匹配 word 列为缺口。P1 FLI 的 FS Off witness 已观察物理 word 被译为 ILLEGAL、ret Illegal 且全 post 不变。
4. 接入正式新官方 `gen` 后全量 replay；77 项完整官方验收另要求自然结束、至少一条合法 Retire、无未分类失败与采样截断。`run_batch.py` 一次进程提交全部 gen 与可构造的 decoder 负例，不逐 case 重载 IR。源码 branch 关闭仍需 Astra 审核分母，不能仅凭 trace 绑定宣布。
5. `smoke_high_half.py` 使用完整 102 寄存器 `vfadd.vv` fixture：未写 `vr0` 与写回 `vr3` 的高低 64 位不同，真实正例通过；分别把预期高 64 位替换为低 64 位的两个负例必须由 Rust 与 Python 同时拒绝。配置默认 `misa` 保持来源明确。独立 `Model::get_val` 单测覆盖 Symbolic+Concrete 输入返回全 Concrete MixedBits 的格式化与唯一性证明。
