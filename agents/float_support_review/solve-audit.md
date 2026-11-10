# 非访存浮点 solve、日志与源码分支审计

## 2026-09-27 接续结论

**最新勘误**：双后端重放的纯读检查漏计frame注入的三个异常let，旧decoder/encoder“完整闭包零写”证书不充分。历史数值及102状态字段配对事实保留，完整等价验收暂回到待修复/补证；下述旧独审PASS须按此范围理解。详见[独审报告](unified-backend-cpp-replay-independent-audit.md)。 随后normalEnd固定点及独审消费`4cbc8ca9…e521`已恢复指定初态/非Poison正常返回域的列定成功输入等价；完整闭包纯读仍FAIL，异常路径不签。新动态observer回归继续。

**统一双后端已经构建并通过列定数值验证；全77求解与全部源码分支仍未完成。**

- 同一份Sail数值/flags模型已生成C++与Isla IR `348147`。67 helper的83 smoke与17,586完整语料三方比较通过独审；见[完整数值报告](unified-backend-crosscheck.md)。完整模拟器已链接，工具链补丁及离线入口见[构建记录](unified-backend-build.md)。
- 新IR的9,583定向结果及其trace来源绑定审计、FD/VPR direct通过；这些结果不代表源码分支全部闭合。正式主IR仍为d012。
- 348147历史两个官方热点 `FVVMATYPE`、`F_MADD_TYPE_D` 在300/270/30秒同预算下仍外限124、无最终JSON。后续56cc全77长批出现资源中断，已按独立stage续跑；当前唯一自然完成57/77，20未完成。最新逐项情况见[执行表](solve-audit-batch.md)与[官方记录](solve-fix-official.md)。
- 历史1dcc全部18,584条可用输入已在新Isla/C++重新配对，完整AST、返回值和102状态字段全部匹配；这是跨版本回归，不能替代新77求解。完整回放独审已通过；当前继续处理纯合法性判断及前端格式匹配热点和源码分支证据。构建告警已通过 `--all-warnings` 展开核对，详见[告警审计](tools/unified_backend_model/warning-audit.md)。

历史性能候选 `56cc69` 已完成同源C++/IR构建，V纯判断与AMO真实guard接线的完整IR独审通过；helper全组已重新执行且最终绑定独审通过（`7421e482…73ca6d`，限定67 helper）。严格配置已精确退役一条无Jump的region，其余129条逐项验证及最终独审通过。该候选18,584条历史输入的新整指令全量回放及独审已通过；9,583定向用例及其严格trace审计通过；官方代表为D FMA自然完成、V FMA外限124，已按新trace审定完整77长批1800/1740/30秒、8目标×2线程，保持输入域与完整trace，该预算的首轮j8长批出现资源压力及137/15信号退出，已停止该批调度保留证据，后续j1续跑见下文；D代表全1096输入双后端回放及独审已通过，以上348147结果不迁记。

最新目标集合核账：同56cc IR的旧j8自然26、D代表1、后续家族23无重叠，当时**50/77唯一目标自然完成**；各自runtime/预算/stage独立保留，新23的9692输入完整回放及独审已过；续批6项目标自然完成后，最新VFMERGE长预算2359.20秒自然完成后为**57/77唯一自然完成、20未完成**；VFMV全回放独审通过，VFMERGE30603输入首轮完整回放prepare失败、尚未提交分片，输入审计确定为7615条vd=0汇编拒绝（原记录均Illegal），逐case Sail/IR guard独审已通过（`f900c97b…e8f9f`），新目录完整30603重放已退出0，120片全PASS、61206阶段/异常槽写0（summary `119a6cfb…016fa`），最终数值/phase双独审及联证通过（`74eff86c…e5b5a`）。不能把跨版本、跨阶段通过混成全77验收。

当前生产续版为nan＋归约组合a040：完整同源C++/IR构建、完整IR/C++与strict/source双独审均通过；67 helper的83＋17586三方输入和五配置89整指令已按新版本实际执行并完成独审。a040的RFWVVTYPE、RFVVTYPE分别于10:42、10:58 UTC以7200/7140/30秒、每目标两线程、完整输入域及完整trace实际启动，结果待最终退出。前版441c FVFTYPE/VFUNARY1及86f FVFTYPE两小时均外限124、无最终JSON；86f FVFMTYPE三十分钟亦外限124。旧运行证据保留，不计完成。

隔离Z3诊断v2已获限定独审，首个固定前缀实际362.365秒：47258完成调用、2未完成；完成FFI占匹配worker观测窗口97.5723%。该比例不代表CPU或FP占比，未完成调用未补时间。查询位置聚合指向`valid_reg_group`末尾整数比较热点，已在保持公共整数域和pow/mod异常顺序的前提下完成隔离组件独审，931源桥通过并应用，普通/SYMBOLIC完整strict均通过；下一CPP/IR构建中，20region/4锚点迁移及新版本回归另验。源码合同导航已到[v12](../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v12.json)，262入口保留原179并新增83；[17类剩余义务](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/unified-remaining-obligations-v1/remaining.md)已形成统一入口，完整分母及`source_branch_closed=false`保持。诊断和新候选细节见[性能记录](solve-fix-performance.md)及[架构记录](solve-fix-architecture.md)。

57完成目标已按机器映射闭合全部可用输出：80416输入＝80283gen＋91direct＋42derived，目标及(run-id,clause,case-id)均无重复；共同IR56cc，32runID/3源binary分列。汇总 `2b858535…deefd`、target-map `52b0b27f…5f6d3`，详见[最终独审](unified-backend-cpp-replay-independent-audit.md)。排除历史18584跨版回归和额外42encoder；不代替20未完成目标或完整source分支验收。

## 历史审计适用范围

> 本文主体保留 d012 历史审计。2026-09-27：修复候选 IR `1dcc8081…8180`、源码 manifest `28fb65ee…a055e` 的全77批已结束：50自然退出0、27外限124，全组未通过；50完整目标的日志/JSON/trace守恒及全部18,477条gen重放通过，其余27项无JSON；批次入口 `isla/target/float-solve-evidence/official-1dcc-20260927-002314/`。同版9152条定向结果通过，但源码分支闭合仍未完成，不能与官方求解混计。此前c5批41退出0/36外限仅作宽位输出缺陷诊断。当前进展见[摘要](status.md)及[官方批记录](solve-fix-official.md)；统一C++/Isla模型改造见[方案](unified-backend-plan.md)，其后续版本须重新验证。

2026-09-26；本轮按用户要求检查实际调度、当前 IR 的官方执行、原始日志以及 Sail clause 分支。实现状态、定向语义测试、符号执行是否完成分别判断。

## 结论

**检查已完成；非访存浮点官方全组未通过，也未达到全部源码分支覆盖。** 现行 IR 的 77 个显式目标都已尝试，40 个退出 0、36 个外层超时、1 个 SMT 错误退出 1。新补 433 条定向验证全部通过，所列输入没有发现新的数值/flags 反例；官方输出另有确定的重放缺口及汇编文本错误。

## 调度集合

独立解析当前 `isla/scripts/run.mk`：`ALL` 347 项、`FD_FLOAT` 89 项、`MEMORY` 48 项；`ACTIVE_ALL` 是排除后两组的 220 项。因此普通 **`make solve` 不调度浮点**。`make solve-fd-float` 包含 10 项浮点访存，不等于本轮所需集合。

本轮明确运行的集合为 `FD_FLOAT - MEMORY - {FMVH_X_D, FMVP_D_X}`，共 77 项，与 [targets77.txt](tools/official_float/targets77.txt) 集合差为空。两个 Zfa 条目的合法性取决于 RV32 架构模式；其隔离 RV32 证据单列，不算现行 RV64 模式的官方复验。独立内存工作树不在本任务检查范围。

现行 IR SHA-256：`d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。旧 `c9e1bfe2…` 官方批次的 39 个退出 0、37 个外限 124、1 个 SMT 错误退出 1 保留为历史；其中多个外限目标的日志也含 SMT 超时，“只有一个退出 1”不能理解为“只有一个目标发生 SMT 超时”。

## 审计文件

| 检查 | 证据与结论入口 |
| --- | --- |
| 退出码、日志、JSON、assert 与分支轨迹的解释 | [运行器审计](solve-audit-method.md) |
| 当前 IR 官方 77 目标逐项执行 | [新批次](solve-audit-batch.md) |
| 标量非 BF16 的 49 个 clause | [标量源码审计](solve-audit-scalar.md) |
| 向量非 BF16 的 22 个 clause | [向量源码审计](solve-audit-vector.md) |
| BF16 的 6 个 clause，另附 RV32 两条边界 | [BF16 源码审计](solve-audit-bf16.md) |
| 官方结果与源码守卫的独立对照 | [日志语义复核](solve-audit-log-semantics.md) |

## 覆盖与结果的验收边界

- 既有 24 组、1509 条定向状态测试触及全部 77 个 clause，并检查各自具体输入的结果和五 flags。它们没有建立全部源码 branch 的分母、轨迹与完成结果对应关系，不能称为分支全覆盖。
- 官方 JSON 只给输入状态、汇编/编码与返回类别，没有输出状态；RV64 状态清单还缺少参与动态舍入和异常累计的 `fcsr`。因此既不能独立重放所有浮点路径，也不能仅用 JSON 证明数值/flags 正确。
- `Illegal_Instruction` 是可预期的架构结果。需要按源码非法条件核对，不能直接当作执行报错。反之，exit 0 也不保证没有丢弃路径：collector 静默处理 MatchFailure/AssertionFailure，且仅将 Timeout/SMT 类错误记入最终错误状态。
- 两个现有 workaround（VFMERGE、VFMV）的顶层 branch 预算实际作用于整个调用树中的重复分支，与“只限制逐 lane 循环”的注释不符；采样不能作为穷尽证据。本轮保留配置原样并报告实际范围。
- 检查完成不等于全部验收通过。分支表中未观察、配置排除、无足够证据、限时截断分别保留，不能把未测分支推定正确或错误。

## 当前 IR 的官方批次结果

外部批次目录名 `isla-float-official-d012-20260926-150048`，调用者以 `RUN_DIR` 指代；四个隔离 stage 使用同一源码、IR、配置和固定二进制，独立保存 output。完整 manifest、实际命令、全部目标表及外部证据相对位置见[批次报告](solve-audit-batch.md)。未覆盖主工作树旧输出，未收窄向量符号上下文。

参数：`THREADS=2 OUTER_TIMEOUT=90s SOLVE_TIMEOUT=80s SMT_TIMEOUT=15s TASTIC=qfaufbv`，最多四项并行；路径预算与整项预算不同。相对旧批次改变预算，且主机存在其他任务，不以结果数量变化判定性能改善。

| 判定 | 目标数 | 证据解释 |
| --- | ---: | --- |
| make/isarch 均退出 0 | 40 | 日志未检出执行错误、panic、Poison、Unknown 或超时；都有有效 JSON。这不排除静默过滤或未输出的分支。 |
| isarch 外层退出 124 | 36 | 无最终 JSON；已打印的部分路径不能计为整项目标完成。 |
| isarch 退出 1 | 1 | `F_UN_RM_FF_TYPE_S`；SMT 超时，仍生成含 16 条路径的 JSON，说明文件存在不等于成功。 |

77 项日志共打印 8122 条完成返回（3935 Retire、4187 Illegal），其中大量来自未完成目标。最终 41 份 JSON 合计 3474 条（3350 Retire、124 Illegal）；字段非空、条数及类别与对应日志匹配。日志与 JSON 数字的分母不同，不能混算通过率。

逐行精确检查得到 62 条“执行错误”：11 个目标中 61 条 `CheckSatAssuming` SMT 超时，另 `VFNCVTBF16_F_F_W` 一条 CLI 路径超时。SMT 热点是 `fdext_regs.sail:523` 的 `accrue_fflags` 条件；不是 61 个独立数值反例。外部宽正则汇总的 execerror=63、other_error=64还含总结行，不能重复计数。未检出真实 panic、Poison、Z3Unknown；MatchFailure/AssertionFailure 默认静默，所以没有相应文本不能证明没有过滤路径。

限时内没有观察到任何 Retire 的 12 项：`FVFMATYPE`、`FVVMATYPE`、`FWVFMATYPE`、`FWVFTYPE`、`FWVTYPE`、`FWVVMATYPE`、`FWVVTYPE`、`F_BIN_RM_TYPE_D`、`F_MADD_TYPE_D`、`VFNCVTBF16_F_F_W`、`VFNUNARY0`、`VFWUNARY0`。它们当时只输出 Illegal；现有具体编码成功样例仍然有效，但不能替代官方符号目标的完成证据。

## 已确认的输出问题

1. **3474 条 JSON 全部缺 `fcsr`**，其中 443 条文本为动态舍入；向量指令还隐式使用 FRM。没有 post-state，也没有足够信息独立重放/验证 flags。`mstatus` 未输出，扩展元数据固定 `IMACFD`，真实译码使能需要外部启动状态约定。
2. **96 条 FLI 汇编文本均不能被标准汇编器接受**：Sail 输出表索引，如 `fli.s f0, 0x10`，标准语法要求对应浮点常量；此编码实际对应 `1.0`。另外 3378 条 JSON 的 1169 个唯一汇编文本用 LLVM 重汇编，编码一致。
3. **四个 BF16 向量 clause 的日志有汇编语法错误**：两个转换多拼逗号，两个 MACC 在寄存器之间缺逗号；修正文本后，抽取样例重汇编与原编码一致。这些 assembly 映射是原 Sail HEAD 的既有问题，不是本轮 C1 数值类型迁移引入的回归。

上述问题、源码位置、标准汇编器验证命令和正常 Illegal 的区别见[日志语义复核](solve-audit-log-semantics.md)。本轮保持被测生产源码和 IR 不变，修订了此前文档中的一处 BF16 runner 哈希笔误。

## 本轮补跑与针对性验证

原 1509 条矩阵记录保持原样。本轮另执行 433 条记录，均在现行 d012 IR 下通过相应 SAT、期望状态差异 UNSAT 和结构检查；它们不是 433 个独立 branch，也不能直接累计为不重复输入总数。

| 补证 | 条数 | 已解决的证据缺口及限制 |
| --- | ---: | --- |
| 既有标量非法 RM 输入 | 30 | 12 条真实译码拒绝、18 条 execute Illegal；限 FADD/FROUND 的 H/S/D。 |
| 既有向量负例 | 21 | 当前版本非法 FRM 复验；不代表所有合法性 guard。 |
| 既有混合非法 FRM | 9 | VFNUNARY0 三条、BF16 六条；状态保持通过。 |
| 既有 FVVTYPE 状态输入 | 4 | mask/vstart/sNaN 的列定状态复验。 |
| 标量 min/max 新输入 | 312 | 12 个操作×格式各 26 例；普通 MIN/MAX 每项七个、MINM/MAXM 每项五个结果选择叶子，共 72 个叶子有输入映射及正确结果。扩展/寄存器/状态 guard 和共享函数的其他分支仍未穷尽。 |
| ROD 跳过 sNaN，旧 flags 清零 | 1 | 仍不新增 NV，消除旧 NV 已置位掩盖错误的可能；仅该输入。 |
| 三格式向量 OF/UF 与非活动抑制 | 18 | RNE maxfinite×2→∞、minsub÷2→+0，以及 mask/prestart 抑制，通过完整目标、fcsr/vstart/mstatus 检查。其它操作、舍入/阈值/tail 未据此通过。 |
| BF16 清零初始 flags | 38 | 六个 clause 的 NaN/中点代表输入；预期新 flags 独立指定为 0/NV/NX，排除这些例子的旧 NV/NX 掩盖效应。未扩张到其余数值域。 |

各输入、输出、runner/配置/IR 哈希、原始命令和独立预期来源分别记在标量、向量和 BF16 审计中。Astra 另以独立位字段 oracle 复核新 min/max 与向量 OF/UF 预期，见[终审方法](solve-audit-method.md)。最初审计发现的 min/max 局部选择缺口、指令级 OF/UF 完全无样例及上述 flags 区分能力缺口，已按本表列定范围补证；此前输入的局限仍保留在细表中，不抹掉历史。
