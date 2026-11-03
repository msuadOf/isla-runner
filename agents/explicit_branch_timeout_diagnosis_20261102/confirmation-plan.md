# 7200秒超时原因确认实验

## 目标

用户要求分清路径规模、单次SMT长尾、tactic与其他成本；未完成对照前不判定“策略正确”或排除tactic。保留历史84次与300秒采样结果，不覆盖。

## 并行分工与写边界

- path-accounting/：GPT-6 Sol从冻结IR/配置推导整Clause与新增分支结构上界，核可达限制；独立程序副本记录fork、终态、活动及排队路径，完整7200秒观测。
- tactic-investigation/：GPT-6 Sol核已有7200秒每次check，可靠捕获原始断言与assumptions，固定query跨策略交叉比较；记录unknown及reason，区分独立query与增量Clause。
- active-lane-control/：GPT-6 Sol使用当前正确gate IR，仅替换overflow选择的A/B，同旧初态域配置完整7200秒，以验证不活动lane因素纠正后是否仍超时。
- collector-cost/：GPT-6 Sol对冻结源码的结果收集阶段插桩，核编码辅助求解是否携带昂贵执行约束，并对同一具体指令做原checkpoint/独立上下文对照。
- 主agent：核版本/输入/策略/种子/机器调度条件，汇总冲突与证据，更新状态。生产源码、子模块和历史输出均不修改。

## 计数口径

真实二分fork、任务入队/开始/终结、待执行任务、正在执行任务和生成JSON分别统计。理论结构上界与SMT约束下可达数分开；不把潜在组合乘积当作实际可达路径。外部Clause超时与SMT check返回unknown/timeout分开，外部终止时未返回的check单独列。

预算：完整Clause外限7200s，显式SMT7200s，T1，不缩短路径预算。实验CPU固定且核对物理核；主机共享，记录用户CPU/墙钟和资源干扰，不声称独占机器。独立query试验固定输入哈希、seed，交叉至少三次，无法完整重放的query不得用于结论。

已有诊断long run更新：flags B finished/10668次check全返回，最长135.175秒，无unknown；未记录wait返回码及精确wall。旧正式三轮仍是7200秒超时。sat B最长已完成check6.160秒，但外部终止时有一个pending，需核其实际持续时间。新旧轮插桩/日志/CPU/负载不同，不能据此直接归因或覆盖旧结果。

## 已确认、仍待合并的子实验

旧基底精确活动gate控制已完成：旧B seed17一次7200s外限；保留该B全部其余源码和overflow-if，只加VFUNARY0活动分支，严格生成IR后同seed17三次57.29–63.78秒全部finished。旧B其余seed29/43只作跨种子记录，不冒称相同seed重复。当前新基底ITE/if各五次也都finished。详见active-lane-control/report.md。

策略单query：原C API AST直接装入新solver，flags与sat两条各qffp/default/smt三次均SAT，default两条实际probe进入qffp；完整六臂仍待预算结束。文本导出有类型打印错误，未用作有效重放。

路径重要纠偏：原-D f位置日志同时包含主Clause和编码辅助执行，不能以其总数加1当主路径总数。新计数分别核主树与辅助树；主路径完成、collector完成、JSON数量分开。

## 路径上界独审修订

主Clause固定域结构上界flags332、sat1033已独立核：分别是160Retire各最多二分加12Illegal，以及4条Retire各最多8lane二分加其余9条。可编码用例类上界368/1038不同于主路径数。辅助树由于collector在模型具体化后调用汇编等函数，其调用形状可能随具体值改变；先前2444/8551全系统累计界缺乏严证，已撤回为条件性估算，不用于主结论。详见path-accounting/theory.md和independent-review/。
