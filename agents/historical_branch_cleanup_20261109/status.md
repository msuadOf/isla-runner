# 历史分支清理状态

2026-11-09：25 个本地分支逐一审计完成，清理脚本与预检完成；本环境实际 `--apply` 在任何 detach/删除前被原 `.git` 只读权限阻止，删除数量为 0。

计划删除 12 个分支：runner 1、Isla 9、Sail-RISC-V 2，全部由保留主线或其组件 gitlink 覆盖。关联 11 个 worktree，其中 5 个有未提交内容。脚本先转为同提交 detached，再验证 HEAD、索引条目、暂存/未暂存 diff 和未跟踪状态均未变；保留所有 worktree 文件。

执行后预期保留：runner 的 master/isarch/float/memory；Isla 的 master/isarch 加三策略线性化与见证随机化两个未合并分支；Sail-RISC-V 的 master/isarch 加 std-gaps、ZVKSHA2 断言、vd/nf 修复三个未合并分支。没有依据把这五条线认定为废弃，未加入删除清单。

隔离验证 2/2，通过实际清理五个分支及五个 dirty worktree 验证内容保留，同时验证过期清单在修改前拒绝。真实三仓预检通过，当前 Git 引用未变；未运行或新增功能验证结论。

- [方案](plan.md)
- [完整逐分支清单](../../.worktree/historical-branch-cleanup-20261109/audit.md)
- [可执行脚本](../../.worktree/historical-branch-cleanup-20261109/cleanup_historical_branches.py)
- [真实执行记录](../../.worktree/historical-branch-cleanup-20261109/result.json)
- [脚本验证](../../.worktree/historical-branch-cleanup-20261109/script-validation.json)
- [交付与执行说明](../../.worktree/historical-branch-cleanup-20261109/README.md)

原 CoW 备份目录不在脚本操作范围内，未触碰。后续真实结果以 result.json 和 *-branches-after.txt 为准。


## 2026-11-09 后续实际状态与 std-gaps 说明

Claude已在沙箱外执行清理；本轮重新核对result.json与三仓真实引用，12个计划分支已删除，核心分支和5个未合并分支保留。上文“本环境删除0”描述生成脚本时的历史状态，不是当前剩余操作。

新增[std-gaps详细核对](std-gaps-analysis.md)：该分支六个增量提交中，Svnapot/Svpbmt已等价cherry-pick入isarch；前三项已由runner/memory固定，37e244ff仍包含独立的全寄存器访存早退清零。独立副本合并树exit0，x0修复保留，无Git文本冲突；未新增合并候选的类型检查、IR或功能PASS。
