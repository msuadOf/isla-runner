# 状态

五组并行消融完成。正式比较均等量预热后 AB/BA/AB 三对，基线为 float1c7a354／Isla80231ce9／模型9c339044。各实验 B 完整严格生成 IR，并核对目标函数以外定义保持。

min/max、mask/归约等 ITE 有耗时收益且减少默认条件见证；flags、NaN规范化及饱和项出现固定预算完成性差异；分类和宽域合法性两臂均超时，无法判断。未把删失时间算速度比，也未把见证数当覆盖率。全部逐项建议见[汇总报告](report.md)。

生产 float/memory 及子模块 HEAD、干净状态核对保持；未回退源码、未提交或推送。未测全量格式、全部向量/BF16调用点和主动查询变更，不宣称逐行穷尽。

[协议](protocol.md)、[基线](versions.json)、[计划](plan.md)。

## 2小时预算续测

用户明确每Clause预算7200秒，现按新协议重新并行测试原超时项；撤去30秒路径/10秒SMT提前截断。上一轮60秒完成性结论仅保留为历史短预算证据，最终取舍待本轮结果。原已自然完成的数据仍有效，但不与新协议混算性能比。

## 2026-11-01核查更正

不传SMT参数仍有底层默认60秒限时，之前描述错误。分类和宽域guard完整结果可用；flags/NaN partial及饱和外限按显式SMT7200秒重测，输出独立保存。[核查与现行入口](budget-2h-audit-20261101.md)。

## 性能问题定位

已定位flags/NaN慢在符号Jump的分支可达性查询；导出相同query的策略重放确认qfaufbv不适合这些浮点条件，sqrt输入分类等价条件亦有快速结果。只验证单查询，不宣称Clause修复。[定位报告](solver-diagnosis/report.md)。

## 2026-11-01：两个上游替代PR已发布

A953e433先dt2bv再原分发，Bae64857受限识别FP/枚举后直接qffp，独立review完成；A初版lambda回退已修并复审。两PR11505/11506和issue11500评论已回读，生产未改。A90/90query通过，B两条flags长query待结果，完整Clause未验。[状态、代码结论与证据](z3-alternative-prs/status.md)。

Z3 B长query现已完成：两项分别395.04/436.12秒SAT，90项跨已声明预算均有预期答案；非完整Clause验收。[汇总](z3-alternative-prs/B/combined-summary.json)。

## 五重复交叉实验完成（2026-11-01）

最终A953e433与Bae64857，8个相同workload，各版本5次，AB/BA/AB/BA/AB，固定每组CPU，80/80均SAT且退出0，输入和二进制哈希核对一致。无预热，SMT7200秒/外限7210秒；机器共享，独立query而非完整Clause。

墙钟中位秒A/B：NaN0.1456/0.2356、flags6.4469/15.4842、最小例0.3525/0.2135、枚举6×256为0.1636/0.1198、512×256为0.5946/0.0676、1024×256为1.2632/0.0552、flags-7为6.3014/41.4227、flags-11为1.8329/119.0785。四个真实query均A更快；最小及三枚举规模query均B更快。不能外推全workload；短例进程启动/共享负载影响明显，B慢例波动较大（flags-7为41.29–234.50秒、flags-11为85.70–241.24秒）。原计时pilot因wait(timeout)轮询尾延迟废弃，正式80次全部从头重跑，未复用pilot数据。

[全部五次数据与原始证据](z3-alternative-prs/comparison-five/report.md)。

**六成员枚举变量规模复测完成（2026-11-01）**：A953e433/Bae64857，64/256/512/1024变量，AB/BA/AB/BA/AB各5次，共40/40均SAT、退出0。墙钟中位毫秒A/B：39.20/29.71、63.34/47.29、70.09/45.64、91.69/52.29，A额外9.49/16.05/24.45/39.40ms。256输入与旧测试字节一致；每变量仅约束不等于C0，另有独立fp.isNaN(x)，不含真实浮点运算耦合；短时进程墙钟含启动/解析，机器共享，不能从跨规格非单调耗时推导算法下降。未改生产/PR。[五次原始数据与来源](z3-alternative-prs/enum-six-five/report.md)。

## A作为fork主线及数据共享（2026-11-01，完成）

按用户选择创建msuadOf/z3的main分支并设为默认，精确指向已审查A953e43301f406bbf41cf1ae8e600641345a8823b（tree完全相同），原master8fbb275保留。仅推进独立Z3 fork，未将新Z3安装到生产Isla或修改组件gitlink。上游A/B PR继续作为替代提案，不代替上游合并决策。

[issue11500新增评论](https://github.com/Z3Prover/z3/issues/11500#issuecomment-6553829092)已发布并逐字回读：两套120次逐次墙钟/中位数、构建与运行命令、完整枚举生成内容、真实flags-11说明、硬件与限时、共享机器/短查询限制及选A理由。

[公开复现材料](https://github.com/msuadOf/z3/tree/2dec1be817c1c13c4dcc77545e349c913fd706cf/benchmarks/fp-enum-11500)在独立benchmarks/fp-enum-11500分支，提交2dec1be8；502文件包含12个精确输入、哈希、120次原始记录/输出/资源统计、报告、便携复现脚本与README，不把材料塞入main源码补丁。公开脚本完整40次六成员规模smoke已通过，smoke耗时不混入正式数据；query字节与原测核对一致。公开JSON中的本机路径已改为相对档案路径，保留逻辑和数值；正式复现入口为README和reproduce.py。GitHub main SHA、默认分支和材料tree均已回读。详细机器记录见fork-selection.json。
