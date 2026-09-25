# 项目结构与源码管理

本文只记录长期稳定的目录职责与版本边界。项目目标见 [GOAL.md](GOAL.md)，动态状态见 [TODOs.md](TODOs.md)，逐次验证见 [RESULTS.md](../docs/RESULTS.md)，用户命令见 [README.md](../README.md)。

| 路径 | 职责与管理方式 |
| --- | --- |
| `isla/` | Isla 核心源码与 IR 生成、执行工具；父仓库以 gitlink 固定版本，目录内另有 `AGENTS.md`。 |
| `sail-riscv/` | RISC-V Sail 模型；父仓库以 gitlink 固定版本。 |
| `sail/` | Sail 工具链；由 `init.sh` 按兼容版本独立管理，不是父仓库 gitlink。 |
| `ara/`、`difftest-xiangshan/` | 处理器 PoC 和差异测试 harness；内部上游 checkout 按各自边界管理。 |
| `agents/` | 原有的议题计划、状态摘要、审查、报告、证据和辅助脚本；保持原位，由 `agents/overview.md` 索引。 |
| `docs/RESULTS.md` | 逐次验证摘要、受测版本和专题证据入口。 |
| `specs/` | 目标、长期结构、当前唯一状态表及仍有效的专题方案；不放运行产物。 |
| `archives/` | 已冻结的成套复现证据；不因文档迁移改写原始数据。 |
| `init.sh`、`Makefile` | 工作区初始化与构建入口。 |

`isla/` 与 `sail-riscv/` 的精确版本由父仓库 gitlink 和 `.gitmodules` 决定；分支名不代替 gitlink。已有 checkout 的修改必须保留。`sail/` 及其他独立仓库遵循各自的分支和工作树规则，不应被父仓库的子模块初始化命令重置。

具体 Git 操作边界见 [GIT.md](../GIT.md)。

`AGENTS.md` 是协作入口，`CLAUDE.md` 是指向它的符号链接。根规则与子目录规则按适用路径共同生效；进入 `isla/` 时还需遵守其局部规则。`agents/<topic>/status.md` 指向议题细节；全仓状态以 [TODOs.md](TODOs.md) 汇总，旧记录的路径和版本仍需按其原文理解。
