# 分支与合并选择核查状态

2026-10-21接续：用户明确选择根仓两条分支分别记录整套版本。已建立 `float@3bb9e8d`（首版本754ca8e，Isla be1296b＋Sail-RISC-V候选3ea3cbaf，随后保存独审）与 `memory@8b24dc8`（Isla47ac90c＋模型4f2ac293），工作树 `.worktree/runner-float`、`.worktree/runner-memory` 均干净、子模块独立检出。manifest／gitlink／checkout／origin／IR哈希一致，两套 `init.sh --submodules-only` 通过。原master及两子仓HEAD／索引／暂存补丁和子仓未暂存补丁保留；远端TLS查询失败，未push。只做版本核查，不记联合功能PASS。Sail-RISC-V独审已完成：确认工具链交付与三个测试入口问题，无新增确证数值／最终状态回归，受测18算术包装704880次调用一致（含重复）。见 [本轮计划](root-sync-plan.md)、[版本说明](../../specs/topic-versions.md)、[核查证据](root-sync-validation.json)、[独立报告](../sail_riscv_commit_review/independent-review-20261021.md)。

2026-10-21：调查完成。当前Isla原分支7b7337b仍有24个dirty路径；内存47ac90c、仅浮点be1296b、通用09fe582与随机化2fefa72已定位。三条Sail-RISC-V拆分链末端tree相同，等于原暂存树排除12pyc。

修订旧worktree描述：`.worktree/isla-float-support` 已在10-09成为detached合并cf128bb，tree等于仅浮点分支；通用＋浮点候选仍在 `.worktree/isla-merge-check-20261008`，tree54fb4e8e，待提交。它们都没有使原feat/float-support分支移动。

7组merge-tree试算完成，内存联合冲突已列；推荐复用通用＋浮点候选，再独立迁入内存及可选随机化，模型拆分链只选一套。远端查询TLS失败，线上最新状态未核实。本轮无功能测试、无实际合并／提交／分支移动／push。后续取舍及联合验证待实施。

- [计划](plan.md)
- [分支、工作树、冲突和合并选择报告](report.md)
- [版本、工作区哈希和试算证据](evidence-20261021.json)

2026-10-30根版本更新完成：float@bb9d271固定Isla b0138b7／模型18389a89；memory@1731207固定Isla47ac90c／模型1fa93117。两套版本/初始化检查通过，未重生IR/联合功能测试/推远端。[精确记录](root-version-update-20261030.md)。
