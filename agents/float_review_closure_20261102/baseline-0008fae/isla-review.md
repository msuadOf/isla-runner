# Isla 相对共同祖先的增量必要性审查

结论：本轮枚举缓存、已有编码约束隔离和 ExecuteAs 续执行均有明确失败或耗时实证，不能归为无依据包装。可以进一步缩减的是若干**历史策略和接口选择**；其中自动 FS/VS 见证偏好会改变输出分布，不能当作无行为影响的清理。没有修改生产源码、分支、冻结 inputs 或77条长跑进程。

## 版本与审查边界

- 仓库：只比较 `isla/`，基准 `0008fae76f4cff86dae1a036d889f0414c228e9d`，受审提交 `42000be47596ec088623881d03c0eadc5cf0ba27`；已确认前者是后者祖先。没有将 Isla SHA 用于 Sail-RISC-V 或父仓 diff。
- 这一区间包含9月至11月继承的浮点、通用支持、trace、V和工具改动。**本轮闭环相对 `cf1aa14` 的 Rust 修改只有 `isla-lib/src/smt.rs`。** 该提交整体+168/-21行；测试模块之前生产段+66/-21行，其余新增102行属于测试。
- 机器清单列45个生产路径，其中内联测试仍计入文件增删，不能将这些数字或大IR/归档数据的行数当作生产复杂度。逐文件哈希、提交关系及保留的工作区状态见[证据](isla-review.json)，只读重建脚本见[isla-review.py](isla-review.py)。本次重点深入核对下表调用链，不声称对全部历史模块逐行重新验收。
- 当前未提交的永久IR测试修改不属于42000be；本审查使用 Git 提交对象，不将这些改动写成已验生产实现。当前模型21418d0及外部生成IR由对应模型基准审查，本文不跨仓比较。

## 浮点功能本身所需

| 位置（42000be行号） | 必要性与最小边界 | 进一步缩减判断 |
| --- | --- | --- |
| `isla-lib/src/smt/smtlib.rs:97–98`、`smt.rs:1376`、`smt.rs:2339–2340` | FP结果必须能够转回IEEE位串，FromIEEE的结果类型也必须按正确指数/有效位宽构造，否则原生SMT浮点与寄存器位串不能形成正确闭环。 | 保留ToIEEE及字段顺序修正；无需ISA专用运行时分派。 |
| `isla-lib/src/primop/float.rs:59–103,192–230,311–327`；`smt.rs:2484` | 具体Bits、Symbolic和MixedBits要进入同一原语；FP/RM/BV sort与位宽错误须在进入Z3前发现。BF16转换实际由 `softfloat_symbolic_f32.sail` 调用 `fp32_to_bf16`，不是未使用的包装。 | `fp_arg/rm_arg/bv_arg`由多组原语复用，沿用现有 `smt_value`；它们的Rust类型检查不产生符号路径，不能按“多余语义分支”删除。FP128多数原语基准已存在，不能以RV64不含Q扩展为由删除公开接口。 |
| `isla-lib/src/primop/float.rs:394` | FMA构造单个 `FPfma`，保持单次舍入。 | 不能改成mul+add以省封装。 |
| `src/isarch/target.rs:632`及 `configs/riscv64_difftest_fd.toml`、`scripts/run.mk` | fcsr必须进入同一符号前态，F/D静态扩展与公共非访存入口需要正确接线。 | 配置、名单和Make入口属于用户可用功能；不等于每个名单策略都属于算术核心。 |

历史中曾新增 `softfloat_dispatch/softfloat_call`，但 `d5ce1b7` 已移除专用运行时分派。42000be的 `executor.rs` 不再按 `riscv_*` 名称截获浮点helper，而由普通Sail函数调用原生FP原语。不能把已移除的整套分派再次算成当前可删增量。此迁移的旧IR缺实现回归和修复见[仅浮点审查](../../float_only_review/report.md)。

## 已证实错误或耗时所需

| 位置 | 实证与当前实现 | 最小缩减建议及对已验语义的影响 |
| --- | --- | --- |
| `smt.rs:678–809,2400,2448`：Context枚举缓存 | 原单成员、多成员、结构体三项同Context重放在官方库下均退出1、重复声明sort；修复后原断言保留，29项独立SMT测试通过。官方C API探针还证明：原Solver全销毁后，同Context仍不能重新声明同名sort。 | **保留缓存和Context强引用。** 继续复用原sort/构造器/识别器，不改类型名、不新建枚举后备类型。局部/跨Solver/直接DefineEnum三入口的size校验分别防止不同绕过路径，不能只留 `get_enum` 一处。`inc_refs/dec_refs`各有多处调用，属于去重。 |
| `smt.rs:216–290`、`src/isarch/encoding.rs:20–136`：编码辅助域与完整域 | 干净同一具体FDIV_S编码：完整路径编码36.50秒，移去原路径Assert的诊断副本三次0.05/0.05/0.04秒，同编码 `0x191f7053`。生产没有直接丢断言，而保留指令字段原Assert子集、全声明/定义/符号编号，候选新增后缀接回完整checkpoint后验可达性。旧7200秒超时还有主路径/collector核账。 | **保留完整域验证与所有可达候选。** 指令依赖分类使用现成 `Val::symbolic_variables` 和 `Exp::modify`，没有新建表达式框架；`with_suffix_from`是回接原约束所需的最小操作。原版本全去Assert已被更精确的保留原Assert子集替代。 |
| `src/isarch/encoding.rs:54–92`与 `exec.rs:858–970` | 普通成功、普通拒绝、异常都在完整域中校验，避免不可达错误阻断合法候选；普通拒绝才尝试压缩编码。已有定向测试证明单个model会漏掉替代编码/压缩域，严格错误传播也有红例。 | 不以 `get_val` 取一个编码代替探索，不使用任意fallback。成功候选在mapping层检查后，collector又重放/求解一次，**存在可去重复求解的具体位置**；但拒绝和异常仍须先验完整域，不能整段删检查。下方另列候选。 |
| `src/isarch/exec.rs:721–742,1299–1320`；`executor.rs:2203` | ExecuteAs首次返回就被标finished的旧实际C_ADDI4SPN：编码0x1fe0、x2=7，旧x8=7，应为1027。现沿用既有 `LocalFrame::new_call`、同TaskState和checkpoint队列续执行，最终返回才导出。 | **保留续执行**，不是多余包装。没有新执行器；`new_call`在基准已存在。`ScopedCollector`独立调用寿命有旧E0597编译红例，新别名保留旧API；仅把闭包塞入Arc不能解决借用期。 |
| `executor.rs:821`及 `executor/frame.rs:445` | 完成帧未保存最后一次fork后的SMT统计，ExecuteAs续执行漏计尾段；真实check_sat无fork测试先红后绿。 | 保留返回前刷新统计；不是重新实现计时。该修改不改变数值或约束。 |
| `primop.rs:1602`、`executor.rs:225,310,Monomorphize分支`、`memory.rs:460,576` | append保留常量分段以后，整数运算、寄存器索引、具化与地址消费者不能只接受Bits/Symbolic。独立基线/新增测试给出Type错误红例。 | 在保留MixedBits表示优化的前提下，**消费者规范化修复须成套保留**，继续复用已有 `replace_mixed_bits`。若另作表示回退，须覆盖原有宽位串与用户初态MixedBits，不能据此先删消费者。 |
| `fmtval.rs:45`、`ir.rs:315`、`smt.rs:1863` | 旧 `lower_u64 >> i` 格式化会损坏高64位；超宿主宽度模型具体化也不能构造单个宿主BV。已有65/128/129位及宽VPR红绿测试。 | 复用 `BV::to_vec` 和 `Val::from_bits_slice`是更小修法。不能回退到只取低64位或任意默认值。 |
| `src/isarch/mod.rs:49–225`、`exec.rs:905之后` | mapping默认拒绝须区别内部异常；assertions_to_jumps会附加处理块，旧固定尾部匹配会漏压缩接续；状态/编码/返回值必须使用最终同一个求解模型。均有先红后绿回归。 | 保留严格分类、错误传播与最终模型具体化。`run_mapping`被助记符和编码两处复用；兼容的旧Option接口委托try接口，不应为少几个函数破坏已有调用方。 |

对应原始证据：[枚举红绿](../review/enum/report.md)、[collector因果实验](../../explicit_branch_timeout_diagnosis_20261102/collector-cost/report.md)、[编码最终审查](../../encoding_constraint_isolation_20261102/review/final-report.md)、[ExecuteAs红绿及API边界](../../float_review_completion_20261102/executeas/status.md)、[MixedBits消费者红例](../../general_support_review/fix2-20261008.md)。

**预算证据修订：** 上轮abce451a只启default，虽然命令含 `--smt-timeout 7200s`，实际上没有单次watchdog；其整Clause外限及实际结果仍有效。本文不复述旧报告的“双7200实际执行”结论。当前acda0dce构建已启interrupt+itrace/tracetool，同构建rlib实际watchdog通过，见[旧程序审计](../review/enum/old-binary-timeout-audit.json)和[新程序探针](../review/enum/watchdog-itrace-result.json)。也没有把有限BV/FP问题描述成理论不可判定来证明这些优化必要。

## 可以更小、但不能混作无影响删除的具体候选

| 候选 | 最小方向 | 现有依据与限制 | 是否影响已验语义 |
| --- | --- | --- | --- |
| S1 自动FS/VS见证偏好：`exec.rs:861–904`与 `official_float77.txt` | 若产品只保留原模型可满足性，可去掉自动名单偏好；显式定向要求使用已有initial_state配置。不要再为此增加一套包装或新的启发式分支。 | 该策略有“优先取可执行见证”的功能理由和组合测试，但不是FP数值必需、也没有预算超时必要性证明。它是10月继承功能，非本轮新增。 | **会改变代表见证、FS/VS分布和生成集合；不能称等价清理。** 已验数字/flags关系仍由完整约束保证，但须重新核覆盖与用户期望。 |
| S2 typed Tactic及强制初始化：`smt/tactic.rs:1–39`、`smt.rs:2140–2215`、`src/opts.rs:184` | 若重新设计最小补丁，可保留基准 `Option<&str>`/默认default入口，仅增加按实际参数类型验证及一次缓存；不必新增四值枚举和要求所有库调用者先初始化。 | 官方qffp、种子参数与错误提前报告有必要；四值类型和独立模块是接口选择，并非纠正FP公式所需。当前相对基准还收窄了原本可传任意Z3 tactic字符串的API。 | 保持当前四策略、默认与错误行为时，数学语义可不变；但公开API和初始化时序需要重新兼容测试。不能简单删能力检查或恢复不存在参数的fallback。 |
| S3 Model具体值缓存：`smt.rs:1693,1751,1813–1825` | 追求最少实现时，可删除每Model缓存、恢复直接 `get_ast`，保留宽值修复和同一最终Model规则。 | 有真实局部A/B：VFMVFS 17.934→13.771秒、ModelEval 157648→73100；不是“无证据”。但没有单独证明本缓存是当前7200秒预算必需。 | 正常完成时应保持已读取的具体结果关系；调用次数/耗时/超时行为会改变，不能继承旧预算PASS。 |
| S4 枚举cache key：`smt.rs:708–713,759–765` | 当前公共Solver只用整数Name，SMT-LIB2 dump私有入口每次自建Context；若显式固定这一调用不变量，缓存可直接按Name，省去整数/字符串key包装与转换。 | 仅是十余行的简化空间；当前实现同时照顾两种已存在命名器，有合理依据。 | 现有调用可保持；若未来同Context混用两种命名器会串类型。收益很小，不建议为少量行数破坏更稳的局部边界；绝不采用任意新类型名。 |
| S5 成功编码的重复完整域求解：`encoding.rs:54–66`、`exec.rs:858–860,945之后` | 将成功候选的最后一次完整域检查与collector最终求解/模型回读合并；拒绝和异常分支仍提前验完整域。 | 当前两次校验的正确性依据明确；没有单独A/B证明去重复后有显著收益。`encoding_paths`现返回“已验可达候选”，改后须调整其契约，collector遇UNSAT应过滤而非NoModel失败。 | 可设计为保留结果，但需要新红绿测试覆盖不可达成功/异常/normal→compressed；不能据重复就直接删check。 |
| S6 MixedBits扩大使用：`primop.rs:1602–1609` | 若限定更小生产表示改动，可评估恢复这两臂为原SMT Concat，其余已有MixedBits输入与宽值支持保留。 | 有真实热点和200次→0次SMT微对照、58组decoder等价；当前没有据此独立证明最新完整Clause预算必须。不能把几条消费者修复当成凭空膨胀。 | 合法位串数学语义可保持；片段具体性、查询/路径成本、诊断和实际见证选择会变，需重新预算。**不建议当前直接回退。** |

**S1的重要纠正：FD TOML的 `mstatus=0x6600` 不等于 solve-state 初态被固定。** `Target::setup_pre_state` 在 `target.rs:124–156` 为reg_list建立fresh符号并覆盖原寄存器，mstatus在清单中；无initial_state配置时，不会把该默认值重新加成约束。因此自动偏好在本批也会起作用，不能以“正式FD已经Dirty，所以偏好完全多余”直接删除。偏好是在每个完整编码可行域中SAT才assert，路径要求FS/VS关闭时保留其原域。此前runner准备说明把配置默认值误写成固定运行态限制，应据此追加修订；不改变长跑输入或原始结果。

优先可独立讨论的是S1策略归属和S2接口增量；S3/S6都有实测性能收益，不能标成无依据，只能在严格最小实现目标下另作成本取舍。S4收益很小；S5需要改契约，当前没有证据证明更值得做。**本审查没有找到可以直接删除、同时保证全部既有独立功能和当前验收边界都不变的大块生产wrapper。**

## 历史继承功能，不能记作本轮新增

| 范围 | 来源与边界 |
| --- | --- |
| itrace/ftrace/btrace组合、共享序列、writer等待、CLI与frame接线 | `69cf43a`、`a9884b2`等；基准已有itrace，区间内是轨迹体系整理及历史已授权观测功能。与当前枚举缓存无因果关系，不应为了浮点最小补丁删除。writer空队列等待和worker panic记账还有真实挂起红例。 |
| V区域预算、采样标记、workaround迁移与advisory hash | `97390b0`、`85d7c70`、`b18d6b7`、`b96022e`等。基准已有execution limits与vtype/vl约束，不是本轮添加新向量取值限制；采样标记是如实报告已有丢域。 |
| `[initial_state]`、部分符号位模式、UTF-8解析修复 | `8948cc4`、`ef882f0`；用户独立要求的通用配置能力。不是浮点计算所需，但定向边界实验真实使用，不能当“helper包装冗余”删掉。 |
| 可选RV64特权域、hart能力探测 | 通用支持继承；当前 `initial_state_rv64_domain` 默认false，开启才施加能力相关限制。其探测wrapper不属于当前浮点路径必需逻辑，但承担已有独立功能；删除会影响启用此选项的输入域合同。 |
| 顶层let的const_primops覆盖：`init.rs:66–124` | 复用现成配置映射适配模型由extern迁到let的形式，测试证明同名配置生效；不是另设静态配置层。普通FD/PMP/platform配置不能因模型声明形式迁移静默失效。 |
| 三表示、summary/provenance、进程组清理 | `09678a7`、`8fae36a`、`1eddd68`及相关继承；有独立用户输出/可重放/可停止需求。`representation.rs:6–42`只格式化已具体化16/32位编码，不新增语义分支或新的求解模型。 |
| 临时日志、归档JSON/PPT、五份大IR及生成provenance | 不属于生产源码必要性行数。IR正确性与源版本另验，不能因占diff行数最多而当作多余运行时实现。 |

本次没有新增动态PASS、没有承诺缩减后的预算或覆盖。若主agent决定实施任一S项，应在当前冻结长跑之外开新受测版本，并分别记录API/输出策略变化、真实语义回归和预算结果。

## 2026-11-03：验证说明修订落实

经主agent授权，仅修订本议题 `validation/procedure.md` 与 `validation/matrix.md` 的解释文字：前者改正当前FS/VS范围描述，并追加保留旧“配置固定Dirty”说法及修订依据；后者追加F1的初态/代表见证覆盖边界，保留changed假臂定向检查义务。源码依据仍为42000be，不是新增动态实验。

修订前后逐项核对冻结inputs、构建manifest及 `run_clause.py`、`freeze_source.py`、`full_batch/scheduler.py` 的SHA256，全部未变化；前后文档哈希与保护资产清单追加于[机器证据](isla-review.json)的 `documentation_correction_20261103` 字段。没有修改status/plan、源码、结果或任何已签实验脚本，也没有因说明纠正增加PASS或完整域Clause完成数。
