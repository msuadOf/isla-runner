# 历史分支清理方案

目标：逐一审计 runner、Isla、Sail-RISC-V 的所有本地分支，清理已由保留主线覆盖的历史分支。保留 `master`、`isarch`、`float`、`memory`；用户最新授权取代上一轮 allai 之前分支一律保留的限制。

范围：仅本地分支引用与关联工作树的 HEAD 归属。不删除 worktree、文件、索引内容、标签、远端引用或备份，不执行 reset/clean/gc，不改源码、IR、gitlink。

热点：`.worktree/historical-branch-cleanup-20261109/cleanup_historical_branches.py`、清单 `plan.json`、逐分支 `audit.md`。复用前轮“同一提交 detach 再删除分支”的技术路径，补充未提交内容保护与隔离验证。

步骤：读取所有本地分支和 worktree；核对保留分支祖先关系，并检查根仓保留分支固定的组件 gitlink；记录未合并提交与议题证据；生成确定清单；预检引用和工作树；先检查三仓可写性，再逐工作树同提交 detach、核对索引/diff，最后删除清单分支并终核保留引用。

验证：隔离三仓实测删除、暂存/未暂存/未跟踪内容保护及过期清单拒绝；真实三仓只读预检；调用 --apply 记录真实结果；重新导出 git branch -a。没有源码或 IR 改动，不重复运行上一轮功能测试。

未决：五个未合并分支未确认废弃，保留；原 Git 元数据在本环境只读，实际删除由 Claude 在沙箱外执行。


补充调查：用户询问std-gaps为何未整枝合并。范围为六提交的实际改动、祖先与补丁等价、x0兼容性，以及候选影响；独立副本只做合并树检查，不向生产分支实施合并。结果见std-gaps-analysis.md。
