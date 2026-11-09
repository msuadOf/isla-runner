# 执行帧 CoW 合入状态

2026-11-09：候选实现、限定验证和本次增量自查完成。候选提交 `7885b24d8506d8f110842c3f4b7948836f624c42`，分支 `feat/cow-local-frame`，位于 `.worktree/isla-cow-local-frame/`，基线为当前 Isla `isarch` 的 `849900a6`。

默认未知回调深拷贝，SeqMemory／ImmutablePageTables 显式启用纯读取共享；冻结、恢复、直接 Clone、新调用均有隔离保护。第三方仍须正确实现 Clone 与纯读取契约，不能承诺违反契约时自动隔离。

验证：默认 frame 6 通过；tracetool 执行器 498 通过／0 失败／5 项既有忽略（含 frame 11 项）；数组内存 34 通过；axiomatic 编译检查、格式和差异检查通过。无新增端到端性能或 make solve 验收。旧候选独审不代签新版本，本轮为增量自查。

**实际主线尚未合入**：原 `.git/modules/isla` 只读，创建正式分支已被文件系统拒绝。已完成独立 feature 提交，真实仓库只读预检通过，隔离副本实际快进及重复执行通过。未推送、未移动父仓 gitlink，原 Isla 工作树和旧 CoW 修改保留。

在允许写 Git 元数据的环境，从根目录执行：

```sh
python3 agents/cow_local_frame_20261109/finalize.py --apply
```

脚本要求目标仍为干净的 `isarch@849900a6`，只从本地候选导入并快进；主线变化或同名分支冲突时停止，不覆盖用户改动。仅推进 Isla 本地主线，发布与父仓 gitlink 更新另按版本边界处理。

[实现、审查与局限](report.md)、[验证表](verification.json)、[交付版本](delivery.json)、[计划](plan.md)、[旧候选审查](history/REVIEW.md)。MMU 的最终结论与归档见 [关停报告](../mmu_symbolic_experiment/final-report.md)。
