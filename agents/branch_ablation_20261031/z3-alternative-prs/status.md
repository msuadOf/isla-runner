# 两种Z3最小修复：已发布两个替代PR

共同base为8fbb275aba0472e862e289c7af1331b3bd5d512c，构建自报Z3 5.3.4。未改生产Z3/Isla/float/memory和gitlink。

- A：fix/default-finite-enum-preamble，953e433；[PR11505](https://github.com/Z3Prover/z3/pull/11505)。生产新增3行（include及两行调用）；现有dt2bv处理无量词goal，保留proof/core路径。独审发现初版lambda类型回退，已增加has_quantifier守卫及回归，修订[独审](A/review/revised/report.md)通过。修订[A-revised/test-summary.json](A-revised/test-summary.json)为90/90query、18API、64原断言模型求值true，test-z3 fpa通过。另独审42次新CLI/14次模型回读通过。
- B：fix/default-fp-enum-direct，ae64857；[PR11506](https://github.com/Z3Prover/z3/pull/11506)。受限FP＋简单枚举probe直接复用qffp，无dt2bv。独审27query/base/显式SMT三组、三种API状态序列和fpa通过，[报告](B/review/report.md)。作者90query中88个在60秒SMT探针内符合预期，两条flags超时UNKNOWN/canceled；18API及64原断言模型求值true。两个慢例已在显式7200000ms SMT、7210s外限复测返回SAT，分别395.04/436.12秒；结合88项短预算结果，90项均取得预期答案，不能记为90项均在60秒内通过。详见B/combined-summary.json及B/long-query-validation。计时含初期CPU共享和后续绑核调整，不作严格性能对比；不是完整Clause验收。
- 已在[issue11500评论](https://github.com/Z3Prover/z3/issues/11500#issuecomment-6553223896)提供两种方案、语义依据、验证边界和对照。发布回读JSON与commit见publication.json、pr-*-published.json、issue-published.json。

[代码等价性说明](equivalence.md)：对B支持片段，两种路线均保留可满足性与原公式模型语义；全局适用范围、模型选择、预算结果和性能不同。A初版不含lambda守卫的结果不能直接外推全输入，历史保留A/；最终版本单独冻结A-revised/。既有comparison/是初版A对B的三对对照，不冒充修订版重跑。

保留的成本取舍：A影响无FP纯枚举并急建模型恢复表达式，B保留混合SMT残留，两者都不保证全输入更快。没有恢复4096成本阈值，没有改原FP语义或Sail分支。全Clause7200秒、生产接入、debug/ASan/RSS未验。PR审查/合并等待社区；不自动合并。

## A/B交叉五重复（进行中）

按用户新要求对最终发布二进制同八项workload做五对AB/BA交叉，加入两条真实慢flags；独立目录comparison-five/，显式7200秒SMT预算，单项两臂同CPU且不变更。[计划](comparison-five/plan.md)、[实时报告](comparison-five/report.md)。

## 五重复交叉实验完成（2026-11-01）

最终A953e433与Bae64857，8个相同workload，各版本5次，AB/BA/AB/BA/AB，固定每组CPU，80/80均SAT且退出0，输入和二进制哈希核对一致。无预热，SMT7200秒/外限7210秒；机器共享，独立query而非完整Clause。

墙钟中位秒A/B：NaN0.1456/0.2356、flags6.4469/15.4842、最小例0.3525/0.2135、枚举6×256为0.1636/0.1198、512×256为0.5946/0.0676、1024×256为1.2632/0.0552、flags-7为6.3014/41.4227、flags-11为1.8329/119.0785。四个真实query均A更快；最小及三枚举规模query均B更快。不能外推全workload；短例进程启动/共享负载影响明显，B慢例波动较大（flags-7为41.29–234.50秒、flags-11为85.70–241.24秒）。原计时pilot因wait(timeout)轮询尾延迟废弃，正式80次全部从头重跑，未复用pilot数据。

[全部五次数据与原始证据](comparison-five/report.md)。

## 六成员枚举变量规模复测

按用户要求，固定6成员，64/256/512/1024变量，A/B各5次交叉，共40次。[计划](enum-six-five/plan.md)、[结果](enum-six-five/report.md)。

**六成员枚举变量规模复测完成（2026-11-01）**：A953e433/Bae64857，64/256/512/1024变量，AB/BA/AB/BA/AB各5次，共40/40均SAT、退出0。墙钟中位毫秒A/B：39.20/29.71、63.34/47.29、70.09/45.64、91.69/52.29，A额外9.49/16.05/24.45/39.40ms。256输入与旧测试字节一致；每变量仅约束不等于C0，另有独立fp.isNaN(x)，不含真实浮点运算耦合；短时进程墙钟含启动/解析，机器共享，不能从跨规格非单调耗时推导算法下降。未改生产/PR。[五次原始数据与来源](enum-six-five/report.md)。

## A作为fork主线及数据共享（2026-11-01，完成）

按用户选择创建msuadOf/z3的main分支并设为默认，精确指向已审查A953e43301f406bbf41cf1ae8e600641345a8823b（tree完全相同），原master8fbb275保留。仅推进独立Z3 fork，未将新Z3安装到生产Isla或修改组件gitlink。上游A/B PR继续作为替代提案，不代替上游合并决策。

[issue11500新增评论](https://github.com/Z3Prover/z3/issues/11500#issuecomment-6553829092)已发布并逐字回读：两套120次逐次墙钟/中位数、构建与运行命令、完整枚举生成内容、真实flags-11说明、硬件与限时、共享机器/短查询限制及选A理由。

[公开复现材料](https://github.com/msuadOf/z3/tree/2dec1be817c1c13c4dcc77545e349c913fd706cf/benchmarks/fp-enum-11500)在独立benchmarks/fp-enum-11500分支，提交2dec1be8；502文件包含12个精确输入、哈希、120次原始记录/输出/资源统计、报告、便携复现脚本与README，不把材料塞入main源码补丁。公开脚本完整40次六成员规模smoke已通过，smoke耗时不混入正式数据；query字节与原测核对一致。公开JSON中的本机路径已改为相对档案路径，保留逻辑和数值；正式复现入口为README和reproduce.py。GitHub main SHA、默认分支和材料tree均已回读。详细机器记录见fork-selection.json。

**Z3 fork二进制Actions（2026-11-01，已启用／首次云端构建待完成）**：main32f4df28，五平台native构建/fpa/解压smoke及GitHub Release/SHA256，无外部secret；本机Linux打包与actionlint通过。首轮[Actions41279354596](https://github.com/msuadOf/z3/actions/runs/41279354596)由push触发，尚未宣称发布成功，未替换生产Z3。[状态与验证]( fork-actions/status.md )。

**Isla使用fork Z3 A（2026-11-01，隔离加载与限定验证通过）**：实际Release5292580e5校验和通过；float isarch副本显式换新libz3，ldd -r/版本验证通过，default种子能力校验未阻塞，FLEQ_S 4.08秒/10条/finished/无错误超时。MRET新旧均partial/unfinished=1，未作完整验收。使用A须新库＋--tastic default；尚未正式重链接/修改生产或分支。[证据]( isla-integration/status.md )。

## 2026-11-02现行方案修订

用户要求改用维护者方案；main现为d5aa015a24e266578164157d7b0268c2babf3008，采用已合并PR11506最新qffp内dt2bv方案，原全局A前处理已移除。旧A提交/包/性能保持历史范围。新版CI正在重建，详见[当前方案与证据](../../z3_maintainer_route_20261102/status.md)。
