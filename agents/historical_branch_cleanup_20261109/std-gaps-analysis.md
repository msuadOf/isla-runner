# feat/sail-std-gaps 与 isarch 的实际差异

2026-11-09，只读源码调查及独立副本合并树预检。没有合入生产分支，没有新增类型检查、IR 或功能验证 PASS。

## 核心结论

该分支不是被判定为不能合并。方案 B 明确要求从 `d5aec317` 只 cherry-pick `5667f347` 和 `7d7e76f3`，当时按指定范围实施，没有做整枝向量语义的验收裁决。本轮已证明没有 Git 文本冲突，而且整枝合并会保留 x0 修复；不能把未合并解释为 x0 冲突或整枝必然不兼容。

相对共同基线 `4f2ac293`，分支有六个增量提交；isarch 只有其中两个补丁，以及独立的 x0 修复。

| 原提交 | 内容与议题 | 当前去向 |
| --- | --- | --- |
| ba729ce9 | memory：segment load/store 的寄存器组界限，`reg + NFIELDS * ceil(EMUL) <= 32`；store 显式传入 vs3 | 未进入模型 isarch/master；为 runner/memory 固定模型 d79d8b32 的祖先 |
| 1fa93117 | memory、共享向量 vstart：get_start_element 从 result(nat,unit) 改为 nat；采用越界不陷阱策略，适配整数/浮点/访存共16个调用点 | 未进入模型 isarch/master；已在 runner/memory |
| c70482a7 | memory 的 Isla workaround 配置：24份文件迁移源码坐标、移除消失的 vstart 区域，并修改 VVTYPE 的7处预算1→0 | 未进入模型 isarch/master；已在 runner/memory |
| 37e244ff | ecfg2 基线固化，兼含真实模型修复：process_vlre/process_vsre 在 vstart>=evl 早退前清零 vstart；vmtype 区域改为658:2–679:3 | 未进入模型 isarch/master，也不是 runner/memory@3278a442 固定模型的祖先 |
| 5667f347 | Svnapot：64KiB NAPOT、level0及PPN低位检查、配置和定向汇编测试 | 等价 cherry-pick 为 isarch 的 e8b686cd |
| 7d7e76f3 | Svpbmt：PBMTE控制、PBMT合法性，非叶PTE的U/A/D保留位检查，配置和测试 | 等价 cherry-pick 为 isarch 的34903a1e |

`git cherry isarch feat/sail-std-gaps` 对前四项为 +、后两项为 -。后两对提交的 stable patch-id 也分别一致。六个原SHA都不属于模型 master 的祖先链；两项功能通过新SHA存在于isarch，不能把原SHA未出现理解为功能缺失。

## 剩余四项的具体影响

ba729ce9 来源于独立修复46f8273a，再按memory职责重组。原先只有EMUL×NFIELDS不超过8及组对齐检查，无法保证从高编号寄存器起始不越过v31。例如v31起始、NFIELDS=2、EMUL=1时，旧组大小检查可以通过，新检查因31+2>32而拒绝。普通及indexed load/store均涉及。

1fa93117采用与XiangShan/NEMU重放环境匹配的Vstart_Ignore方向，改变原先越界返回Err/Illegal的行为。它不是仅改访存：基线16个调用点为arith5、fp1、mem3、utils7。非陷阱是规范允许的实现选择，不应把它描述成任何模型都必须采用的唯一行为。新策略影响相关路径的陷阱、退休及写回结果，必须以精确候选复验。当前isarch的两个V源码文件仍逐字等于4f2ac293的对应文件，尚未包含这些变更。

c70482a7不只修行号。除坐标适配及删除vexttype/vxtype中消失的vstart区域外，vvtype的7个max_forks_per_region从1改为0，涉及gather循环、舍入helper、重叠判断、饱和arm等。它不直接改变Sail模型语义，但会改变使用配置时的符号探索和取样；合入必须同时审视覆盖影响，不能当作纯注释维护。

37e244ff虽然提交标题强调ecfg2复现，实际还改变向量全寄存器LOAD/STORE的后态：旧代码在vstart>=nf*elem_per_reg时直接退休，保留非零vstart；新代码先set_vstart(zeros())再退休。它依赖前面的get_start_element接口改造，不能把整个补丁当作可随意删除的实验配置。

## 为什么方案 B 没有整枝合入

事实依据是当时用户明确指定“d5aec317 + 两个cherry-pick”，不是已查明的冲突。d5aec317只改model/core/regs.sail，std-gaps剩余源码改动位于V文件；本轮在独立Git副本执行`git merge-tree --write-tree origin/isarch origin/feat/sail-std-gaps`，exit0，无冲突。合并结果的regs.sail blob与isarch完全相同，x0修复保留。相对当前isarch，结果额外修改4份V源码与24份workaround，共28个文件。

该结果只能证明Git可以合并，不证明模型类型、语义和性能均通过。历史ba729ce9/1fa93117有普通与SYMBOLIC严格类型检查，所属议题还有其他适用版本的验证；不是完全未测试的代码。此前方案B只重生当前v128 IR并通过path merge、Python及标量Sv39 STORE fuzz smoke，没有验收新增segment/vstart/whole-register行为。不能把旧结果移署整枝合并树。

## 建议与前提

不建议因为历史清理就丢弃这些修复。应把剩余部分作为单独的向量模型补齐候选：保留x0与已接纳分页改动；确认vstart的实现选择；审查正确性修复与探索预算的不同作用。可以在当前isarch上整枝合并，也可分组迁移四个剩余提交；目前没有证据说明只能选择后一种方法。不要直接检出旧分支作为新主线，否则旧分支本身不包含x0修复。

验收至少覆盖：普通/SYMBOLIC严格类型检查；segment组界的合法/非法、分数EMUL和indexed/store；vstart边界及整数/浮点/访存调用；全寄存器LOAD/STORE早退清零；受影响源码区域坐标及7项预算的探索影响。随后重生实际使用的IR，保留新来源记录，语义复验已有corpus entry，重跑path merge/fuzz和受影响向量回归，再固定Isla IR提交与runner gitlink。其他配置仍须分别记验证范围。

## 证据

- [原内存模型提交与历史验证](../sail_riscv_commit_review/topics-20261022.md)
- [原模型合流中预算与接口处理](../float_memory_merge_20261103/implementation/model/report.md)
- [本轮合并树检查](../../.worktree/sail-std-gaps-audit-20261109/merge-result.json)
- [本轮实际提交图](../../.worktree/sail-std-gaps-audit-20261109/commit-graph.txt)
- [本轮相对isarch的候选补丁](../../.worktree/sail-std-gaps-audit-20261109/merge-from-isarch.patch)
