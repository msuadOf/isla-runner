# 暂存区外清理状态

2026-11-09：三仓及关联52个实际Git工作目录完成内容审计和已确认项清理。恢复79份未暂存文件，删除4538个文件（含805份Python字节码），无沙箱阻挡。6个有源码残留的历史Isla目录已干净；Sail-RISC-V主区旧浮点副本清除，仅保留有用的.gitignore改进。

并非所有残留无用：COW的快速冻结、MMU采样预算、semantic-mutation独有实现及仍有证据价值的文档和运行结果保留。merge-float-memory的189份条目属于历史证据；replay-p0重复源码和编译缓存已清，其文档和结果保留。43个目录Git状态为空；其余9个中2个仅有已暂存IR，均保持起点状态。

没有运行测试、编译、IR生成或isarch，没有执行哈希计算或核对命令，没有修改Git元数据和用户的CoW快照。远端依据为本地origin缓存和已有推送背景，本次未联网复核。

[完整审计](../../.worktree/unstaged-cleanup-20261109/audit.md)、[逐文件清理结果](../../.worktree/unstaged-cleanup-20261109/cleanup-result.json)、[方案](plan.md)。
