# origin远程分支清理状态

2026-11-09：10条目标与本地清理记录/缓存核对完成，无缓存内遗漏或多余。9条已由保留主线或组件gitlink覆盖，p0-replay按明确退役授权处理（24个独有提交，不称整枝合并）；4个核心脚本与当前isarch逐字节一致，原replay-p0工作树保留。

真实三仓删除dry-run均因代理不可达退出128；脚本实时读取origin同样失败。未实际删除GitHub分支，也未执行origin fetch-prune。当前branch -r只是缓存。原Git元数据仍只读。

脚本参数校验通过；3项隔离bare远端测试通过（exit0，5.183秒）：真实删除10条目标并仅prune origin，保留本地/核心远端分支、标签与upstream；实时提交推进时拒绝整批操作；预检后并发推进时atomic租约拒绝删除。

外部执行入口：`python3 .worktree/origin-branch-cleanup-20261109/cleanup_origin_branches.py --apply`。白名单、实时提交租约及所有三仓dry-run为写入前条件。删除后仅fetch --prune --no-tags origin，核对最终branch -r；不触碰备份。

- [方案](plan.md)
- [完整分支及依据](../../.worktree/origin-branch-cleanup-20261109/audit.md)
- [脚本](../../.worktree/origin-branch-cleanup-20261109/cleanup_origin_branches.py)
- [交付说明](../../.worktree/origin-branch-cleanup-20261109/README.md)
- [参数校验](../../.worktree/origin-branch-cleanup-20261109/parameter-check.json)
- [真实dry-run失败记录](../../.worktree/origin-branch-cleanup-20261109/network-dry-run-attempts.json)
- [真实执行状态](../../.worktree/origin-branch-cleanup-20261109/result.json)
- [隔离验证](../../.worktree/origin-branch-cleanup-20261109/isolation-validation.json)
