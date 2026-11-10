# Sv39 全符号页表实验状态

2026-11-09：议题结束，停止旧 MMU 预算调优。按用户决策，后续采用路径合并，并为 fuzz 保留更大探索空间。归档只保留 Markdown 与处理后的数据／表格；旧运行产物已筛选，清理结果见最终报告。

[最终结论与关停理由](final-report.md)、[处理后数据](archive/summary.json)、[归档清单](archive/archive-inventory.json)、[原计划](plan.md)。历史超时计数为下界，模板后处理不是语义接纳证明。本轮没有重新运行 MMU 实验。

## 2026-11-03 历史状态

2026-11-03：三组对照与见证核验完成；全符号探索触及预算，未取得全量路径总数。

指定现成二进制与 IR 未修改、未重建。单线程正式轮：Bare 与具象 Identity 各 1 条成功，1.166/1.668 秒；全符号 60 秒返回 415 条（成功76／Page Fault291／Access Fault48），外限退出124。已完成检查8564次，累计26.629秒、最长0.01302秒。16线程补充返回3181条仍触限；不能填报完整总数或过滤数。

两条成功路径的原始 SMT 字节数组与所有读事件吻合，独立 Sv39 检查2/2 PASS；分别为1GiB根叶和2MiB叶，PTE bit59遵循受测模型启用的Svrsw60t59b。无硬件或独立 Sail 重放验收。

报告与原始数据：`.worktree/mmu-symbolic-experiment/REPORT.md`、`summary.json`、`selected-witnesses.json`。准备步骤见[计划](plan.md)。后续若需完整计数，应另定总预算或收集中途摘要；当前不把预算内下界当作全量PASS。
