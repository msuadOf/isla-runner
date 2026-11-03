# 2026-11-03新双门准则：e9架构接纳裁决

**e9数值/源码/IR正确性签字不等于新准则下的架构接纳。** 当前明确建议REVERT本轮33个仅返回NV/DZ事实的原因分支、八个窄适配器新增分支及12整数包装的纯结果分支；changed写回、finite/valid gate与ROD模式新增控制为OPEN，缺适用的证据门，不能宣称必要性已签。KEEP已有NaN实际传播、原生陷阱/合法性控制和e9已恢复的数据流。全部是审查裁决，不修改冻结e9/214或其运行输入；REVERT须另有候选与验证，不能静默回滚当前长跑。

依据是`specs/GOAL.md`的2026-11-03最新架构准则：新增/恢复显式分支必须同时通过证据门和语义门。严重超时必须指出同位置的可比实验；正确结果、多了见证、结构2^N上界、函数名含invalid/overflow均不够。特殊值分类也不自动通过证据门。此前本审查把“饱和/异常边界”直接当作新增fork必要性，这个架构判断按最新口径修订；旧等价/实际IR/动态结果仍适用于原受测版本。

模型坐标：本轮`6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a`→`e9d69d2f28586c089244c8e37ee4c904c5114458`；原模型参照`4f2ac293654a02db26dac5055be7f93fd6e3141e`。`0008fae76f4cff86dae1a036d889f0414c228e9d`只属于Isla，未用作模型diff。下文路径与行号基于e9的`sail-riscv/model/`；现场只读对象为独立named树。

## 首批正式逐项裁决

| 对象与源码位置 | 原生/恢复/新增，实际两臂 | 裁决与双门依据 |
| --- | --- | --- |
| `extensions/FD/fdext_regs.sail:547` changed；Ext_F`:549` | 4f2普通模型本有changed if；6202 SYMBOLIC将其折叠到状态ITE及断言前提，本轮恢复外层if。真臂才核F/Zfinx互斥并更新FS/SD，假臂无该状态写回。Ext_F本身在6202已有。 | **changed OPEN；原Ext_F KEEP。** changed有真实副作用控制，语义门有依据；但原ITE也正确按changed选择状态，没有证据证明6202该ITE是严重瓶颈或新if解决瓶颈。不能以flags已非零代替changed，也不能因OPEN撤销FS/SD语义。缺的是新增fork架构许可，不是状态正确性。 |
| `extensions/V/vext_fp_utils_insts.sail:549/550/558/559/567/568/576/582/588` | 6202已有f16→I16外overflow if；本轮新加其sign分支、另五个overflow及另两个signed sign，共8个新增if。各臂仅返回NV/clamped bits或原flags/低位，无trap、状态更新、模式切换。4f2普通六适配器已有native if，但这些SYMBOLIC `_pure`函数和无损BV表达式是后来版本。 | **本轮8新分支REVERT；6202既有f16→I16外if OPEN；4f2普通六函数未改的native if KEEP。** 当前活动gate下ITE和if五次都完成，不能以旧eager-lane显式版超时证明当前ITE需要新fork。正负饱和值/NV抑制NX仍完整保留数据流，不因结果最终写寄存器将其提升为控制。 |
| `core/ieee_fp_exceptions.sail`18算术异常helper的33个原因if，首例`:142`；H/S/D add/sub各1、mul各2、div各3、sqrt各1、FMA各3 | 这些是6202后新加。调用者已先运行native FP生成result，再调用该异常helper。原因真臂只返回`ieee_empty_exceptions(true)`或DZ facts，未触发FP trap、未选择结果NaN传播、无寄存器写。Inf/0/sqrt名称不改变这一事实。每源NaN分类/最终canonical结果在既有独立调用处。 | **33处REVERT到Bool事实合并。** 恢复原invalid_nan OR各原因、DZ布尔值；finite臂取rounded facts，非finite臂只清OF/UF/NX。保留NaN/Inf/零谓词、FMA融合及每源NaN独立流程，保留所有五位flags。无本轮33处A/B严重瓶颈证据；“各NV原因必须各有路径”是旧额外见证目标，不满足新门槛。 |
| 同18算术helper finite/valid gate，首例`:144` | 6202后新增，将原先已算好后按Bool屏蔽的纯宽精度lo/hi/rounded计算移入有限真臂。没有trap/状态写，但确实控制是否构造这些FP约束；源NaN流程仍先运行。 | **18处OPEN，当前保持冻结。** 不能只用“finite是特殊值”自动批准；也不能只用“FP纯函数”断言所有性能效应不存在。e9的rounded已无纯输出fork，原来“必须gate以免特殊输入穿过rounded新分叉”的理由不再充分。缺单变量瓶颈证据及为何选择控制而非原native约束的论证。可准备去gate数据候选，但本页不授权实施。 |
| `core/ieee_fp_exceptions.sail:814/827`整数核心finite/valid；`:839/886/933`三个round finite；`:980/992/1004/1025`四转换/BF16 finite；`:1040/1055`两ROD finite | 共11个本轮新增gate：FPint2、round3、转换4、ROD2。只改变是否运行纯FP/BV计算或返回NV/NX字段，未自行触发trap或架构写回。它们还决定下游wrapper得到的literal invalid，而新wrapper若回数据流则该literal便利不是必要性证据。 | **11处OPEN。** finite/valid分别审因果，不能作为成组KEEP的标签。与18算术gate合计29处。没有逐项6202→e9 A/B瓶颈或足以推出7200秒不能完成的可达工作量下界。保留返回语义，另候选才能判断是否需要原mask Bool结构；mask空壳helper不因OPEN恢复。 |
| `extensions/FD/softfloat_symbolic_f16.sail:56/69/82/95`、f32`:103/116/129/142`、f64`:91/104/117/130`及各NaN/sign内层 | 12函数6202本来已有；本轮将纯整数结果选择ITE改3层if。candidate与异常均在外层if之前已算好，各臂无trap/状态写/模式变更；负NaN必须选正端点是位结果规则。上游NV在当前finite/valid各路径是literal，不等于新增源码if有架构必要性。 | **本轮12×3纯选择if REVERT到6202原ITE/Bool表达式。** 保留完整NaN/符号饱和规则、candidate、flags和之前已存在的源NaN/canonical流程；不删12函数。没有该36处新增fork的适用性能证据，定向819/315通过不构成证据门。 |
| `extensions/FD/softfloat_symbolic_f32.sail:187`、f64`:175` ROD模式 | 6202已用`rm==6`的ITE先规范普通候选RM为RTZ，再选择派生ROD/普通flags与bits。本轮新增模式if，使两算法只运行所选臂。两者都是纯计算，但derived ROD与native普通规则的模式差异真实。 | **2处OPEN。** 语义门可由模式切换解释；证据门未闭。不能声称6202把6直接传native导致错误，原规范化helper/ordinary_rm已避免该问题。未有该guard消除严重瓶颈的同版本A/B。保留ROD规则、flags/bits配对、NaN canonical，待独立证据后决定控制实现。 |
| rounded/exact末端、round/FPint NX、ROD jam；当前局部underflow/facts | e9已删18纯输出if，flags/JAM保持原facts/ITE；四underflow及六facts是局部值名，无函数调用层/分支/新数学操作。 | **KEEP e9数据流及十个局部名，不构成阻断。** underflow是纯Bool的一次命名，facts调用本来必须发生，别名只返回它；可内联但没有必须删除的新增辅助逻辑。不能仅为少行数重开已冻结模型。 |
| NaN operand分类/NaN-boxing/canonical结果、原生非法指令/真实trap及普通六窄adapter | 本轮6202→e9未改的既有控制。NaN返回实际canonical结果及每源quiet/signaling规则在原位置保留；不混同本轮仅回NV的33分支。 | **KEEP原版本控制和数学语义。** 本页不追溯撤销全部4f2→6202历史工作，也不将历史功能称成本轮优化。若另审历史恢复分支需独立条目与证据，不能借本轮REVERT批量删除。 |
| 五个RM_RNE assembly具体映射，dext`:608/638/642`、zfh`:738/742` | 真实GNU拒绝原显式RM文本；五条专映射保RM000机器字，非零仍generic；不增加数值求解fork框架。 | **KEEP最小兼容修复。** 有已复现文本/机器字错误与实际双汇编器探针；不把这类必须功能修复误算成纯求解显式化。 |

## 可用证据及其不能证明的内容

- `agents/explicit_branch_timeout_diagnosis_20261102/active-lane-control/report.md`：在a9fd947、有正确active gate的单变量f16→I16对照，ITE五次21.74–35.36秒、if五次45.15–64.14秒，均完整。旧显式B超7200秒；只加active gate三次57.29–63.78秒完成。支持active gate修复eager非活动lane的问题，不支持再引入八个饱和fork，也不证明所有宽度全域完成。
- `agents/branch_ablation_official_z3_20261102/live-report.md`及最终summary：原flags算术显式B有实际超时，但方向是新增if变贵，不是原ITE严重瓶颈由if解决。`agents/encoding_constraint_isolation_20261102/validation/selective-report.md`中固定旧显式flags B在新编码隔离后2626.07秒完成；瓶颈位于辅助编码路径约束，不能转记为模型changed新分支的性能收益。
- `agents/explicit_branch_timeout_diagnosis_20261102/path-accounting/theory.md`的332与1033是旧固定配置结构上界；2^8来自8个eager物理lane，现active gate后的控制不同。上界不含每路径求解时间下界，不足以理论推出7200秒不能完成；无权扩推当前29个finite gate、33原因或12wrapper。
- 214/e9完整77运行按版本保留，启用trace/主机竞争/排队状态不等于单变量源码超时；未完成或整体完成都不能替代各新增分支的因果证据。源码/IR等价、定向oracle及SAT正确仍是正确性证据，不是性能证据或双门架构批准。

## owner自检核查与core diff

owner的八文件`+590/-435`、core`+452/-360=812`、`-w`后core`+300/-208=508`数值属实。纯缩进忽略后差异行从812降到508，减少304，约37.4%；因此**不能把“812行主要是缩进”作严格多数事实**。18个helper确实将既有纯数值let及返回块移入finite臂，812行也包含移动位置、原因return和外层重组；此前已核所有数值表达式不变，不是812行新数值算法。新准则下，gate是否必要必须另过双门，不能因“只是缩进”获得许可。

四underflow（core`:131/228/326/779`）和六facts（`:983/995/1007/1028/1043/1058`）在新版IR没有新增条件Jump，facts只保留原exact调用的命名结果。它们是非阻断文本选择；owner“因此没有任何可删分支”的最终架构结论则已被最新双门裁决取代。再改十个局部名不是当前优先事项，也不能弥补33原因fork和纯饱和结果fork缺乏必要性证据。

本页优先冻结首批架构裁决。后续候选只在议题目录准备，主agent明确授权后才进入新模型树；OPEN不是KEEP，REVERT不是已执行回滚，数值正确性与当前运行证据均不静默改写。

准备候选后续补记：[33原因、12整数包装及六窄回数据流候选](architecture-candidates-review-20261103.md)已完成独立源公式/精确Git体核查，限定源码等价通过；仍未应用生产，未签OPEN、strict、新IR或动态。该源签不改变本页KEEP/REVERT/OPEN裁决。
