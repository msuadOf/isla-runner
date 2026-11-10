# 浮点 solve 审计口径与运行器证据边界

2026-09-26，只读核对主工作树源码、当前 `isla/output/` 和旧官方批次日志；没有修改执行器、配置、IR 或独立内存分支。本文件规定本轮审计怎样解释证据，实际逐 clause 结果由本轮汇总记录提供。现行 IR 为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`；旧官方批次 `c9e1bfe2…` 不能计为现行 IR 的复验。

## 1. 要核对的集合

`isla/scripts/run.mk` 的 `ACTIVE_ALL=$(filter-out $(FD_FLOAT) $(MEMORY),$(ALL))` 明确排除了整个浮点组。普通 `make solve` 不调度浮点；`make solve-fd-float` 调度 89 个 clause，但包含本任务不验收的 10 个访存项。当前官方批次沿用 77 个显式 `solve-X` 清单；其余 `FMVH_X_D`、`FMVP_D_X` 的合法编码要求 `in32BitMode()`，应另列模式可达性和既有 RV32 具体样例，不能仅因所用 IR 名称含 rv64 就判不可达。

`sys_regs.sail::architecture` 在 XLEN64 时按当前特权查询 MXL/SXL/UXL；正常 reset/CSR 合法化将这些字段固定为本机 XLEN，当前模型不支持动态切换 SXL/UXL。官方入口重新符号化 `cur_privilege/mstatus`，并非固定 Machine；其任意注入域不能直接等同正常 CSR 可达域。77 项是明确选取的批次，不是全部 79 个非访存 constructor 的官方执行证明。两项模式边界见 [BF16 附带模式审计](solve-audit-bf16.md)。

对每个 clause 分开给出：是否启动、是否自然结束、是否记录错误、是否产出有效 JSON、至少一条合法成功路径、源码分支覆盖、结果与完整状态的对照。39 项退出 0、77 项都被启动、77 项各有一个成功定向样例是不同结论。

## 2. 真实入口与输出的含义

- `isla/src/isarch/exec.rs` 的 `run_symbolic_execute_with_target` 先按 constructor 类型创建符号参数，随后直接调用 `zexecute`。该过程没有先经过机器编码的 `encdec` 正向译码守卫。collector 的 `try_get_assembly_encdec` 是执行结束后的编码物化。因此 execute 内可达状态与真实机器译码可达状态需要分别审查。
- `AssemGenJsonItem` 仅保存 `arch`、`test-ins`、`test-ins-encdec`、输入 `isa-state` 和 `ret_val`。没有输出寄存器、post-state、fflags 结果或分支 ID；路径签名仅用于内部排序后丢弃。JSON 本身不能验证数值或副作用正确性，这不表示实际结果错误。
- `Target::setup_pre_state` 会重新符号化 `reg_list`，包括 `mstatus`、`cur_privilege`、向量上下文及各类寄存器。不能仅凭配置中的 `mstatus=Dirty` 判断 FS/VS 相关路径被排除。RV64 额外约束了合法 `vtype/vl` 配对和 `vill => vl=0`，这部分不属于任意 CSR 位模式的穷尽。
- RV64 的 `reg_list` **没有 `fcsr`**。`solve_pre_state` 只输出由该清单建立的 `PreStateCtx`，collector 没有另外输出 `fcsr` 的通路。当前 `FCVT_S_BF16` JSON 有 39 项、33 项使用 `dyn`（30 项 Success、3 项 Illegal），39 项全部不含 `fcsr`；日志同时有 `fcsr` taint。例：`fcvt.s.bf16 f30, f8, dyn`、编码 `32'h4064_7f53` 的 Illegal 输入没有记录所需的非法 `frm`。因此 JSON 无法独立重放该浮点路径，也无法证明旧 fflags 的累计行为。该缺口同时存在于核对过的旧官方同名 JSON。
- 任意输入寄存器若没有参与约束，输出可以按既有设计省略；但参与判定 `dyn/fflags` 的 `fcsr` 不属于可据此忽略的无关状态。`fcsr` 出现在 taint 名字中并不提供其具体值。

## 3. 退出码与异常分类

`SolveCollectorState::record_error` 只保存 `ExecError::Timeout` 和 `ExecError::Smt`；结束时仅 `first_error` 决定该 clause 是否向上返回错误。以下行为应逐项解释，不能只扫描 make 退出码。

| 现象 | 现行实现行为 | 审计结论与严重性 |
| --- | --- | --- |
| 外层 timeout 124/137、进程异常退出 | 可能尚未写最终 JSON；内部部分路径仍已打印 | 本 clause 未完成；阻断完整覆盖。还要查日志中是否同时存在 SMT 错误，不能把 124 简化成纯外层超时。 |
| SMT timeout、SMT error、CLI path timeout | 写入 `first_error`；正常收尾时返回错误，也可能在此之前被外层限时杀死 | 已探测到未完成路径；阻断本次完整验收。 |
| Z3 `Unknown` | `SmtResult::is_sat/is_unsat` 转成独立 `ExecError::Z3Unknown`，不属于上行的 `ExecError::Smt`，因而不进入 `first_error` | 必须额外扫描 unknown；不能假设它随 SMT error 自动导致非零退出。当前已扫日志未发现此现象，机制由源码确认。 |
| `Type`、`NoFunction`、`SymbolicLength`、越界、branch/loop/depth limit 等其他 `ExecError` | 通常打印“执行错误”和调用栈，但不进入 `first_error` | 即使最后退出 0 也必须按错误路径审查；若涉及合法输入即为阻断问题。当前审计源码确认此机制，不声称新浮点批已实际触发每种错误。 |
| `Run::Finished(Poison)` | 警告后不生成该路径用例，不进入 `first_error` | 该路径没有可接受的架构结果，需追溯来源；不能把其他线程的 Retire 当作该路径恢复。当前 `MRET.log:29` 有真实例，`status.intime.log` 同时含 MRET；这里只证明运行器行为，不归为浮点算术错误。 |
| `MatchFailure` | collector 静默丢弃；不进入 `first_error`；启用 itrace 时会提交该执行帧 | 可能是 constructor 状态不满足解码守卫，也可能是有效输入中的模型缺口；必须先核对来源。日志没有该字样不证明未发生。 |
| `AssertionFailure` | collector 静默丢弃；不进入 `first_error`；也不提交 itrace | 对合法域的前置条件过滤和模型内部不变量失败必须分开。无法凭日志零次断言失败证明 assert 全部成立。 |
| 汇编名称/编码或 pre-state 物化失败 | 部分情况警告并丢弃用例；SMT 类会上报，其他种类未必导致非零退出 | `Finished` 数可能大于有效用例数；需逐项对照日志/JSON 数量和缺失字段。 |
| collector 最终 SAT 检查非 Sat，或 `Model::new` panic 被捕获 | 仅 `SmtResult::Error` 显式报错返回；Unknown/Unsat 或被捕获 panic 会跳过填充，仍走后续用例构造 | 源码可产生空 `test-ins`、空编码、空 `isa-state` 的记录；逐 JSON 校验字段，不能只验证 JSON 可解析。本轮不声称已实际触发。 |
| `Run::Exit`、`Run::Suspended` | 只打印路径状态，不生成正常用例，不记 `first_error` | 不是指令正常退休；若该 clause 预期退休，列未完成并追溯。 |
| `Run::Dead` | 不生成用例、不提交 itrace | 对不可满足路径是正常排除；不能直接计入已覆盖源码分支。 |
| `Illegal_Instruction` | 正常 Sail 架构返回，可以记录在 JSON | 本身不是执行器报错；需检查非法条件是否与源码和真实译码可达域一致。 |
| `No primop` 初始化警告 | `ir.rs::insert_instr_primops` 保留普通 Call，直到真正执行时才暴露缺实现 | 不直接等于该次失败，也不能无条件忽略；确认相关函数未被已测非访存调用链执行。 |

旧官方 77 项实际日志中，已有外层 124 的 FMA clause 同时打印多次 `SMT timeout during CheckSatAssuming`，热点为 `fdext_regs.sail` 的 flags 累计。旧记录中的“1 项 SMT 超时退出 1”只描述最终退出类别，不表示只有一个 clause 的日志出现 SMT 超时。完整逐日志计数由日志审计记录提供。

### 乐观 assert 的特别边界

`isla/src/isarch_main.rs:463` 选用 `AssertionMode::Optimistic`；`primop.rs::optimistic_assert` 对符号条件只检查 true 可满足。可满足时加入 true 约束，不继续枚举 false 臂；只有 true 不可满足或条件具体为 false 时才返回 `AssertionFailure`。这是工具采用的预条件过滤策略。

例如 BF16 的 execute 含 `assert(SEW == 16)`，而真正的 encdec 守卫已要求 SEW16。直接 constructor 执行可能进入 encdec 不允许的 SEW 状态；不能把这一类 assert 过滤直接判成合法指令错误。相反，若某 assert 声称已由此前合法性检查保证，则必须以其合法前置条件检查 `pre && !assertion` 是否 UNSAT。正常退出和没有断言日志均不能替代该检查。

`--fork-assertions` 会将 Call 改成 Goto，并在函数末尾追加 handler Jump/Exit；原 IR 文本与运行 PC 在这些点不再一一匹配。若使用此选项调查，须保存转换后的坐标映射；原 collector 仍不提交失败 assertion 的 itrace，单开该选项不足以产生完整断言失败账本。

## 4. 源码 branch 的粒度与证据

使用当前 Sail 源文件的 clause/辅助函数、源码区间和 arm 名建立分母；IR 哈希、函数名和 PC 用于连接动态证据。至少分别核对下列粒度：

| 粒度 | 应列的 branch | 覆盖所需证据 |
| --- | --- | --- |
| 指令选择 | clause 内每个 `match` 的 opcode/enum arm、SEW/格式 arm | 每个可达 arm 的合法编码及完成状态；enum 在模型中保持符号且只输出一个具体代表值时，不可只按 JSON 助记符计数。 |
| 控制与合法性 | `if` 两臂、option/Result 两臂、rm/dyn/非法 frm、寄存器对齐与重叠、vill/vstart 等检查 | 固定 IR 的逐路径轨迹，或明确约束下的可达性及完整结果检查；非法路径也核对不应有副作用。 |
| 向量循环 | 不进入、首次进入、继续/退出；活动/屏蔽/前缀/尾部各类 lane，首活动与后续活动 | 逐 lane 策略的证据。两个静态分支方向均执行不等于所有 lane 组合穷尽。 |
| 浮点数据策略 | NaN boxing、sNaN/qNaN、±0/∞、普通/次正规、异常累计、round/ROD、BF16转换等 | 位级结果及全部五 flags 与适用参考对照；成为 SMT ITE 的选择不表现为 executor fork，不能按“无 fork”判缺失或正确。 |
| 配置与死分支 | XLEN、VLEN/ELEN、扩展开关、预条件恒真/恒假 | 明确本次配置下不可达的推导/UNSAT证据；不能用“日志没出现”代替不可达证明。 |

每一项采用“已观察且结果验证”“仅观察到进入/分叉”“样例仅验证结果、无轨迹绑定”“未观察”“被限时/采样截断”“本配置不可达且有理由”“证据不足”等状态。不得将未观察自动记为未实现，也不得将部分静态覆盖率写成全输入证明。

### 日志和 itrace 可证明什么

- 普通 `make solve-X` 的 `--debug=fmlgcsra` 会打印 `FORK` 来源和 taint。`executor.rs` 仅在某符号 Jump 的 true/false 均 SAT 并准许 fork 后打印这些信息，故可证明两侧当时均可达且已调度；不能证明二者最终完成。具体 Bool、单侧 SAT、采样和纯 SMT ITE 均不会得到这种完整二臂记录。
- `--trace-all` 将 Call/Return 记入内存中的 solver trace。collector 中打印 `Event::Fork` 的整段代码被注释；其参数名不代表已有逐路径 source branch 报告。`--probe-all` 也不自动打开 PROBE 日志类别（默认 debug 字符串没有 `p`）。
- `ITRACE=1` 对每条被提交的路径保存 `[function pc]: IR line` 序列。对普通 Jump，可按下一条同一调用上下文内的 PC 是 target 还是 pc+1 判断所走 arm。需用**同一份原 IR**恢复 SourceLoc；itrace 展示文本主动去掉 SourceLoc。采样摘要为 `execution limit: … action=sample_branch_condition/keep_current_model`，必须纳入覆盖限制。
- itrace 记录在执行指令前；路径最后出现一个 Jump 但没有后继时，只能证明到达该 Jump。其路径标题记录部分 fork 条件，不包含所有具体/单侧条件，也不替代完整 SMT 环境。AssertionFailure、Dead 和被外层杀死时尚未提交的活跃路径不可从现有 itrace 恢复。相同 function/pc 的递归或重入要维护调用上下文，不能跨调用错误拼接。
- 完成的 itrace 与最终 JSON 目前没有显式共享 path ID，错误/Poison 轨迹也没有统一的 terminal status 字段。因此逐 branch 的结果验证仍需补充可关联的具体输入或独立语义验证证据。

## 5. 现有采样配置的准确范围

`configs/workarounds/vfmerge.toml` 和 `vfmv.toml` 都设置顶层 `max_forks_per_branch=1`、`on_limit_reached="concretize"`，并另设局部 `region_fork_limits`；二者没有 `execution_limits.regions` 过滤。

`ExecutionLimits::applies_to` 在 `regions=None` 时对所有位置返回 true，`max_forks_per_branch_for_scope` 会将顶层预算应用于整个调用树。因而注释所称“只限制 execute 的逐 lane 循环”并不准确：调用树中重复命中的同一静态 branch 也受该顶层预算影响。默认 `call_context_depth=None`，预算 key 不区分调用上下文。每条路径首次命中该 branch 仍可两臂 fork，重复命中后采样；这不足以推导所有动态上下文组合穷尽。本轮只记录此范围，不修改配置。

## 6. 最小必要复验

1. 在不覆盖既有输出的新目录，用现行源码/IR/配置/二进制 manifest 固定 77 项官方入口，保留 `vl/vstart/vtype/mask/tail/寄存器` 的符号上下文。本轮使用 `OUTER_TIMEOUT=90s SOLVE_TIMEOUT=80s SMT_TIMEOUT=15s TASTIC=qfaufbv`，具体线程数和并行数以批次命令记录为准。旧 5 秒单查询预算叠加共享主机负载，难以区分复杂查询正常耗时与持续不收敛；本轮给查询更多时间以取得错误诊断和完成证据，不能据两轮耗时作性能比较。全部记录底层退出码、每类错误、Finished/JSON条数和有无合法成功。
2. 对源分支表中没有证据的热点只做所需诊断复跑，启用 itrace 和 timeout SMT 输出。先分清外层总时限、单路径限时和单查询超时，再决定复验参数；不能靠固定运行态消除缺口。不要仅为得出 exit0 任意调高时间。
3. 将官方输出与本次已有的定向数值/状态证明对应。既有 1509 样例可验证其具体输入；若没有 branch 轨迹，不能反推全部源码 arm 均覆盖。对 fcsr 缺失、post-state 缺失的官方 JSON，结果合理性结论限于独立参考已经验证的范围。
4. 最终明确报告哪些 clause 未自然完成、哪些源码 arm 未观察、哪些因编译配置或前置条件不可达、哪些有明确结果位/flags证据。全部 branch 尚未闭合时直接报告缺口，不能将“检查已完成”写成“实现全量验收 PASS”。

## 7. Astra 独立终审记录

本节独立读取原始输入、输出、摘要和当前源码，不执行其他审计人的预期生成脚本；核对哈希、逐行结果以及下述独立数值规则。检查脚本通过一次性 Python 命令运行，没有重新执行模型或改写证据文件。下列外部目录均以目录名识别，具体位置由运行环境保存。

| 检查项 | 独立复核结果 |
| --- | --- |
| 审计集合 | 从三份源码审计文档抽取显式 clause 名，与 `targets77.txt` 比较：scalar49、vector22、BF166；两两交集为空，并集恰为77。这里核对的是条目集合，不是77条指令的全部分支。 |
| 原最终矩阵 | `isla-float-ir-final-20260926.q1Auj4/matrix/summary.json` 的24组输入SHA和输出SHA均匹配；原始1509行的SAT、差异UNSAT、结构检查全部成立，clause并集77。原数1509保留不改。 |
| 本轮已有负例补跑 | scalar30：输入/输出和固定工具哈希匹配；12条静态RM5/6确为译码ILLEGAL、未执行，18条DYN+FRM5/6/7确为execute Illegal。vector21、混合非法FRM9、FVVTYPE状态4：逐行输入/输出哈希、SAT/差异UNSAT/结构与观察寄存器均匹配。混合包9中含BF16六条，不能再重复加六。 |
| min/max补证312 | `isla-float-minmax-audit-20260926.8234wb5b`：固定件、输入、输出、生成器和分支映射SHA均匹配。另用IEEE位域分类与符号位翻转/负数反码形成的单调整数键重新比较数值，独立检查NaN/sNaN、规范NaN、两序有符号零及旧DZ与新NV累计；所有312条目的完整预期位串和flags一致。另按机器字核对funct7/funct3/rs1/rs2/rd，均正确。12种操作×格式的72个结果选择叶子均有具体输入；共享guard/寄存器状态分支不在这72个分母内。 |
| vector补证19 | `isla-float-vector-audit-20260926.v59gu3by`：ROD跳过sNaN一条仅清除原NV遮蔽，结果`vr4=0x3c00beef`、flags=0，有区分能力。其余18条为H/S/D的RNE溢出/下溢×活动/屏蔽/前缀；独立从IEEE exponent/fraction算出maxfinite×2→+∞/OF\|NX、minsub÷2→+0/UF\|NX，并核对完整128位目标、保留哨兵及旧DZ累计，全部一致。输入、输出、IR、runner、配置SHA与逐行证明均匹配。 |
| BF16清flags补证38 | `isla-float-bf16-cleared-flags-20260926.gbmc6mc4`：逐条还原原输入，确认除名称和初始/预期fflags外无额外修改，全部初始fflags确为0，FRM保留。用独立有理数解码/精确乘加/五RM舍入计算全部有限输入，另按NaN quiet位和boxing规则处理qNaN/sNaN，38条的目的位串及新flags全部匹配。SHA、译码字段、重编码、单完成路径、SAT、差异UNSAT和观察寄存器逐项通过。该检查验证这批精确乘积中点，仍不构成任意FMA融合语义证明。 |

独立数值复核没有直接调用 SoftFloat、待测 Sail helper 或其他审计人的 oracle：min/max 使用位模式顺序，BF16 有限数表示为精确 `Fraction`；RNE在恰好中点选偶数、RMM中点远离零、RTZ截断、RDN/RUP按符号选择相邻值。新flags由是否精确、sNaN及列定溢出/微小边界直接推导。架构状态字段则逐项核对输入、既定预期和原始模型结果，不能将数值oracle独立性外推成整个机器状态的独立参考实现。

上述本轮执行样例记录合计 **30+21+9+4+312+19+38=433**，其中19=ROD1+OF/UF18；含旧输入复验和新增定向输入，不是433个新分支。此前BF16 LMUL10是既有单列证据，不重复计入。新输入补齐了原报告中的若干数据选择与flags区分缺口，不能继续将这些列定情况写成完全未测；仍没有全源码分支覆盖结论。

### 当前官方77项的最终复核

外部批次目录 `isla-float-official-d012-20260926-150048`，本轮命令为 `make -o build-isarch solve-X THREADS=2 OUTER_TIMEOUT=90s SOLVE_TIMEOUT=80s SMT_TIMEOUT=15s TASTIC=qfaufbv`，四个隔离输出stage并行、各自顺序执行。独立按 `targets77.txt` 核对77个目标和顺序，逐项目录内底层状态日志、make/result元数据、CSV、原始路径日志及JSON交叉对照，**0项不一致**。

- 底层退出0共40项，124共36项，1共1项；唯一退出1为 `F_UN_RM_FF_TYPE_S`，其16条部分结果有最终JSON，但仍是失败。40项退出0仅证明本次运行器自然结束，不补足本节此前列出的证据缺口。
- 41份最终JSON、3474条记录；逐文件SHA、记录数和Retire/Illegal分类与日志完全一致，空汇编/编码/isa-state各0；3474条全部未输出 `fcsr`。原运行记录曾误用缺少 `z` 的JSON文件名，批次负责人保留初始元数据备份后纠正了元数据；本次直接读取实际 `rv64_z*.json` 验证。
- 全部日志共8122条已打印完成结果，其中3935条Retire、4187条Illegal，无其他Finished返回类别；36个外层中止目标的局部路径不计完整覆盖。12项目标在本次观察内没有Retire：FVFMATYPE、FVVMATYPE、FWVFMATYPE、FWVFTYPE、FWVTYPE、FWVVMATYPE、FWVVTYPE、F_BIN_RM_TYPE_D、F_MADD_TYPE_D、VFNCVTBF16_F_F_W、VFNUNARY0、VFWUNARY0。此事实只说明官方本轮没观察到成功路径，不抵消独立定向样例。
- 精确匹配“执行错误:”共62行：61条为SMT timeout（60条定位 `fdext_regs.sail:523:6`，1条定位该if的整体区间），另1条是 `VFNCVTBF16_F_F_W` 的CLI单路径 Timeout。11个目标日志出现SMT超时。CSV的 `execerror=63` 是宽正则的关键词计数，额外包括一条clause失败总结；不能把它当63个独立路径错误。
- `anomalies.jsonl` 共248条关键词匹配，逐条回查原日志目标/行号/文本均一致。没有观察到panic、Poison、Z3Unknown、类型/缺函数/符号长度/越界等另外的运行错误；MatchFailure/AssertionFailure本来可能静默，故不能从零文本匹配推导它们没发生。

四个stage在结束后分别再次对86项原manifest核对，全部0差异；另核对主树及四stage的 `src/isarch/{exec,target,mod}.rs`、`src/isarch_main.rs`、`isla-lib/src/primop.rs`、`isla-lib/src/executor/execution_limits.rs` 六个运行器文件，全部哈希一致，并由批次负责人保存 `evidence/runtime-supplement.json`。四份二进制SHA均为 `34feb0923bf13123cc11fded795308e1d4d52cf47d166a5496d6db29752b4eb8`。

终审读取时 `evidence/audit-summary.json` SHA-256为 `0f67e6b46fdc929daca02b9ad2afb49438975dfff91f7cceaa4f1358ce3fd658`，`evidence/audit.csv` 为 `16291fbe0d4ef741d34b80fa8d4fb13f8b822ea198145ddbad8b42eb4b520228`。本轮官方执行未达到77项全部自然完成，逐源码审计与433条补证也没有形成所有源码branch的穷尽证明；所列数值和状态例通过，不应外推。
