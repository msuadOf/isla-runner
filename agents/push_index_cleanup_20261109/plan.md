# 全分支推送与暂存区清理

目标：先发布三仓12个本地分支的提交，再清除审计确认的暂存区。明确只改索引，不覆盖工作区，不删除未跟踪材料；原CoW备份不访问。

范围：三仓主Git存储及runner关联worktree中已初始化的同名子模块，去重后11个Git存储、47条worktree记录。只有3处暂存，计163+30+30=223条。外部data1_b记录属于另一个Git存储，只读保留；仅一个/tmp缺失worktree记录可prune。

步骤：核对12个本地分支；额外5个未被这些分支覆盖的worktree HEAD或必要gitlink提交，用archive标签保全而不恢复旧分支；生成原子快进推送脚本并设置upstream。审计223条暂存blob的后续提交归属，保存原索引、binary patch与完整暂存blob pack；推送全部验证成功后，仅restore --staged，逐工作树确认文件/未跟踪材料不变；最后清理已核准dead记录。

热点：`.worktree/push-index-cleanup-20261109/`内推送与清索引脚本、inventory.json、staged-coverage.json及恢复材料。先生成可审阅结果，当前原.git只读及网络限制下交由Claude执行。

验证：隔离bare远端实推全部分支/标签、设置upstream、验证非快进拒绝；独立worktree实测部分暂存的中间版本可恢复、文件不变和dead记录仅清元数据；真实离线参数/索引核对。禁止将未推送或未清理记为完成。
