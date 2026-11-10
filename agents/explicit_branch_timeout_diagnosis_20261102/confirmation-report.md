# flags 与饱和转换超时：确认实验汇总

状态：**完整实验已结束，最终独立复核中**。六臂策略对照、主路径7200秒计数、活动lane单变量控制及干净collector诊断均已完成。源模型和生产Isla未修改；实验副本、输入、命令和哈希均保存在各子目录。

## 回答什么

分别核对主Clause路径总量、主/辅助执行与结果收集的耗时、单次Z3 check长尾、tactic选择、活动lane执行范围。主路径、编码辅助路径、SMT check数及JSON数分开。

## 固定域的控制流规模

详见[path-accounting/theory.md](path-accounting/theory.md)，主树结构界经[independent-review/report.md](independent-review/report.md)独核。

|负载|ITE基线已穷尽主路径|显式B主路径结构上界|推导|
|---|---:|---:|---|
|flags算术|172|332|160条退休路径各最多二分一次，12条非法早退不变|
|f16→i16饱和|13|1033|4条路径各8lane二分，其余9条不变：4×256+9|

这是当前冻结IR/配置的主指令控制流上界，不是全部可达组合的精确计数、辅助树总数或执行时间界。编码等辅助树另有计数。曾将A辅助实测数外推成严格总系统界，独审发现模型具体化会影响后续辅助执行，已撤回；不使用该估算作结论。

## 饱和超时的活动范围控制

旧B在vl1/SEW16/VLEN128时，仍先对8个物理lane计算转换，然后才屏蔽结果。对旧模型只加VFUNARY0活动gate，其余源码及overflow-if helper不变，严格生成IR：同seed17三次完整Clause自然finished，57.29、59.00、63.78秒，1318check/次、无unknown/错误/超时。旧B同seed17那次7200秒外限退出；其他旧B种子29/43单列历史，不冒称同seed三重复。此控制说明修正活动范围足以使这个配置完成，不使用跨CPU/插桩差异计算精确速度比。

当前模型的overflow ITE/if各五次也全部finished，A为21.74–35.36秒，B为45.15–64.14秒；见证集合不同，不称等覆盖加速比。完整证据见[活动lane对照](active-lane-control/report.md)。

## 慢查询与求解策略

从原C API assert入口保留AST，在相同context新建solver交叉三次，避免无效文本重放。flags #47、sat #235各三策略九次及原增量check均SAT；两条goal经simplify后is-qffp probe均1，default对它们实际进入qffp。中位秒数：flags qffp36.19、default34.88、smt121.98；sat qffp2.79、default2.65、smt26.13。这不能证明所有查询皆如此，也不能用两条query排除所有tactic性能因素；完整六臂结果见下文。flags首轮smt有短时同核竞争，其余两轮仍较慢。详见[策略调查](tactic-investigation/report.md)与[逐次数据](tactic-investigation/query-crosscheck.csv)。

新完整路径计数轮中，flags collector第8条主路径的一次check已实际SAT返回，耗时1038.658秒。早先300秒采样最长22秒只适用于那段窗口，不能用来否认后段单次长尾。完整截止账见下文。

## 结果收集成本的同输入诊断

干净复核使用同一已具体化FDIV_S字段、相同编码helper，两侧得到唯一机器字0x191f7053且编码集合相等：保留原浮点路径断言的checkpoint时，编码阶段36.50秒，7次check累计36.418秒；移除15条Assert、保留540声明/定义的上下文三次0.05/0.05/0.04秒，check累计0.007524/0.008160/0.007072秒。主路径结束后的首次collector SAT检查另耗7.85秒。

本轮实际wait返回87（诊断首case出口），整进程wall59.94秒、user57.95/sys1.86秒；前后本组probe残留PID均0。两侧约束集不同，结果仅证明该具体输入的原执行断言拖慢编码求解，不证明可直接删除生产断言。其它符号候选、可达性及完整编码集合必须另行证明。详见[collector调查](collector-cost/report.md)、[干净进程账](collector-cost/clean-result.json)。

历史诊断240/455秒一度当作单核测量，独审发现四个残留probe同核竞争，已保存现场并停止，报告撤回该性能表述；另修正首轮check分界。历史数据保留作受干扰诊断，最终主要证据改用上述干净复核。

## 完整两小时结果

主路径诊断两臂均在7200秒外限退出124，详情见[path-accounting/result.json](path-accounting/result.json)。以下计数直接来自执行器任务事件，不由JSON条数反推。

### 六臂正式策略结果

冻结B的flags/sat各qffp/default/smt一臂，全部7200秒进程外限退出124，无完整JSON；独立退出观测7200.17–7200.43秒，CPU采样约7166–7175秒/臂，即99.5%–99.7%。seed17与实际官方库一致，独立物理核。结果证明本次只更换default或smt不能使旧B两Clause在预算内完成；不能外推所有策略、种子与负载。详见[六臂CSV](tactic-investigation/full-verified.csv)。

补充同AST捕获的q685三策略fresh均SAT，qffp8.669/default8.406/smt18.549秒；同进程另测fresh qffp7.475秒、原增量7.243秒。它们未复现另一路径计数轮1038.658秒长尾，且该长尾没有原始AST哈希，不能仅凭查询编号认定为同一公式，也不能据此确认增量会话历史是原因。长尾真实计时与阶段归属成立；跨轮差异的微观原因未证实。

### 两小时主路径最终账

|负载|理论主路径上界|已创建任务(1+fork)|执行器已返回|collector已返回|排队|当时阶段|
|---|---:|---:|---:|---:|---:|---|
|flags|332|256|150|149|106|另1条在collector|
|饱和|1033|435|199|198|236|另1条在collector|

collector返回表示收集回调已返回，不等于完整JSON已经写出。两项均尚未完成整Clause，无完整JSON；不能把执行器Run::Finished或部分收集当作Clause完成。守恒：flags 256=149+106+1；sat 435=198+236+1。辅助树完整2h未启用逐任务仪表，result中的aux零值为未测字段，不是实际没有辅助路径。完整A增强插桩已证明其存在，辅助实测另见theory.md。

flags已返回6387次check，执行阶段602次/396.786秒、collector5785次/6777.716秒；约94.47%的已完成check时间在collector。最长一次1038.658秒返回SAT，不是单次7200秒超时。sat已返回16951次，执行阶段8338次/2900.641秒、collector8613次/4195.809秒；最长4.819秒。flags已返回SAT4801/UNSAT1586、sat SAT11287/UNSAT5664，UNKNOWN均0。两臂最后各一个正在check的查询被外层终止，按启动时刻与time墙钟估算，开始距终止约1秒以内；pending只描述尚未返回，不称SMT自身返回timeout。

flags实际wall7200.37秒、user7081.96/sys91.94秒；sat wall7200.16秒、user7098.98/sys77.25秒。CPU时间/墙钟99.63%/99.67%，不能主要归因没有得到CPU。查询包裹器统计的是check墙钟，非Z3精确CPU；/proc/stat及进程CPU用于另外核调度。

## 有证据支持的结论与未决边界

1. 本轮qffp/default/smt全Clause均不能在2h完成，换default或通用smt没有解决旧B超时。两条同AST交叉对照的default实际进入qffp，smt更慢；不外推所有策略/参数。
2. 旧饱和循环在vl1仍执行8lane溢出判断，导致2^8局部组合和对应反复求解；只修活动范围即可使同旧源域/seed17完整Clause三次约一分钟完成。这是本次已有修复方向的因果控制。
3. flags主树为百级，额外changed判断至多每退休路径二分一次；实际预算主要被collector重复求解昂贵浮点路径约束及长尾消耗。干净同具体输入对照确认编码辅助带原断言时36.5秒，隔离后0.04–0.05秒，同编码。不能未经完整等价证明就删除生产断言。
4. 原17分钟长尾查询没有原始AST哈希，另一轮同编号捕获并未复现；为什么这一次异常慢仍没有微观求解器级归因证据。不把它改写成已确认会话历史bug或排除所有tactic改进。

本轮只调查/实验，不修改生产模型、Isla或其默认策略。
