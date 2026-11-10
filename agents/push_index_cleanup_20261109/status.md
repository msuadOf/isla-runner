# 全分支推送与暂存区清理状态

2026-11-09：普查与逐项审计、脚本和隔离验证完成。12个本地分支加5个archive标签列入发布清单，覆盖detached历史和runner各gitlink；参数校验通过。真实联网因代理不可达，未能从服务器回读本计划全部引用。当前12分支均已设置origin上游，这是外部操作后的本地观察，不当作5标签已发布的证明。

原普查11个Git存储、47条worktree记录，仅3处暂存：模型主区163、Isla两个历史树各30，共223。207条能在保留提交历史中找到相同blob；16条未匹配条目含12个.pyc及4条旧源码（3份去重）。不是“全部已合并”。已保存原索引、binary patch、旧暂存版本及完整blob pack，并在独立Git存储验证可恢复。

本轮期间观察到会话外已清空三处索引、移除唯一dead记录。脚本在索引变化时停止，本会话未执行原索引清理或prune。最终普查cached全空，223文件在，220条原工作区与索引一致的内容复核一致。其余3条原部分暂存的工作区全文未在起点另存，不声称完成对其外部操作前后的逐字节校验；原暂存版已完整保全。外部data1_b记录实际属于另一Git存储，保持不动。

两项隔离测试通过，验证全部测试分支及archive真实发布、upstream、非快进拒绝、推送完成门槛、部分暂存中间版恢复、仅清索引保留文件及幂等prune。

Claude应先运行push_all_branches.py --apply，完整回执及实时回读通过后，再运行cleanup_staged_indexes.py --apply；已清部分会跳过，不覆盖文件。备份目录完全未访问。

[方案](plan.md)、[详细交付与命令](../../.worktree/push-index-cleanup-20261109/README.md)、[全部引用](../../.worktree/push-index-cleanup-20261109/publication-audit.md)、[223条审计](../../.worktree/push-index-cleanup-20261109/index-audit.md)、[隔离日志](../../.worktree/push-index-cleanup-20261109/isolated-tests.log)。


进一步回读本地reflog：三仓新增isarch/实验分支和runner/master等有外部`update by push`记录，12个origin缓存均与本地目标一致。[推送日志证据](../../.worktree/push-index-cleanup-20261109/external-push-reflogs.json)。这说明外部已执行相应分支推送，但不替代本计划17个引用的实时核验。
