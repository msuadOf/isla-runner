# origin远程历史分支清理

用户已明确授权清理近期删除本地分支对应的origin分支。目标为runner2、Isla5、Sail-RISC-V3，共10条；只操作origin。硬保留master/float/memory/isarch、所有仍有本地分支的议题与全部upstream引用。备份目录不访问。

范围：对照22个已删本地分支与当前origin跟踪引用，记录提交覆盖；p0-replay作为明确授权的旧入口例外，不记为整枝合并。联网读取实时heads后逐提交核对；所有三仓dry-run通过后才进行实际删除，使用原SHA的force-with-lease及单仓atomic。最后仅fetch --prune origin并核对branch -r、upstream和本地分支。

热点：`.worktree/origin-branch-cleanup-20261109/cleanup_origin_branches.py`、plan.json、执行记录。原Git仍只读且网络不可达，交付参数校验和隔离远端验证通过的脚本，供Claude在外部执行。不得将网络失败记成dry-run通过。
