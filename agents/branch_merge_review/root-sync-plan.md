# 根目录双议题同步计划

2026-10-21。用户希望在工作区根目录同步float和memory两个议题的fork，同时要求独立审阅Sail-RISC-V。

已核实当前 `isla/` 的origin为 `ariscv/isla`，float和memory成果目前表现为同一fork内不同本地分支；根仓只以单个isla gitlink固定版本。用户已澄清选择根仓两条分支分别记录整套版本。

实施选择：从根仓已提交基线 `a85d6df` 创建 `float`、`memory` 两条分支，放在 `.worktree/runner-float`、`.worktree/runner-memory`。每条分支用gitlink固定Isla与Sail-RISC-V，并以 `specs/topic-version.json` 记录候选范围、IR哈希和限制。float记录已提交仅浮点be1296b及Sail-RISC-V源码候选3ea3cbaf；memory记录47ac90c及现有模型基线4f2ac293。这表示可追溯源码快照，不表示新模型／旧IR已完成联合验收，Sail-RISC-V代码建议待独审完成。通用09fe582与随机化2fefa72仍独立，不擅自完成尚未提交的合并。

根仓现有未提交文档／脚本／实验材料继续原位保留，不作为任一议题的隐式公共提交。两新分支仅提交本轮版本记录、同步说明和gitlink；根仓主工作区保持master。新工作树使用本机已有Git对象初始化其独立子模块，配置文件仍保存正式远端URL。发布时必须先使精确子模块提交可从正式远端获取，再推根仓分支；当前TLS错误下先交付本地可用分支。

范围与约束：保留原 `isla/` 24个dirty路径、`sail-riscv/` 163个暂存路径及全部既有worktree；复用明确提交的候选，区别提交和残余工作区。同步分开处理获取远端引用与更新本地检出；分叉、dirty或gitlink不一致不得以reset/clean掩盖。若需要新增版本管理入口，同步README、GIT和项目结构说明，实际命令验证后再记结论。

独立审阅已委派一个subagent，审阅 `4f2ac293..3ea3cbaf` 精确Sail-RISC-V候选；仅可写 `agents/sail_riscv_commit_review/independent-review-20261021.md` 及同名证据目录。主agent维护共享状态与根目录同步入口，不与审阅agent编辑同一文件。审阅不自动授权代码修复、实际合并或推送。

步骤：确认同步语义；实现最小可用入口；核验各目录与提交／远端关系及原工作区保全；主agent复核独立审阅发现并汇总取舍建议。联合功能验证及实际合并不因本轮目录同步自动获得PASS。
