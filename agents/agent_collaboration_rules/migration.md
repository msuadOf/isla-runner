# 文档重构与目录修正记录（2026-09-25）

## 最终边界

根据用户反馈，`agents/` 是原有 agent 协作资料的归属目录。先前将它移入 `docs/topics/` 的操作已撤回；根 `agents/` 现在是实体目录，原文件名、议题目录和八个 Python 辅助脚本均在原位。`docs/` 仅保存新建的项目级 `RESULTS.md`，`specs/` 保存目标、结构、状态总表和 IR 流程约定。

原有 101 个文件路径逐一检查，全部是原位置的普通文件，没有依赖兼容符号链接。用户在任务开始前已有的 `agents/findings.md`、`agents/overview.md`、`agents/float_support_review/status.md` 的 SHA-256 分别仍为 `5ffa97e5c4ea4f4298dcdc72087947ade433a7dc8cce24bfdb46d0b5209458db`、`0e277f64df37fc3675ec48bde8927029231ab3db77fece4bdf7208cd60cd65f0`、`b01c0bf3cf43688a9011474dec2b464cf3e27c1c73faea99af229a792635c55d`。

## 项目级文档

- 根 `AGENTS.md` 指定阅读入口、文档职责及原有计划确认流程；根 `CLAUDE.md -> AGENTS.md` 保持原样。
- `specs/GOAL.md`、`specs/project-structure.md`、`specs/TODOs.md`、`specs/ir-workflow.md` 提供目标、长期结构、全仓状态与 IR 检查约定。TODOs 指向原位的议题 `status.md`。
- `docs/RESULTS.md` 汇总已有的验证结果，链接原位的议题详细文件和 `archives/`。
- 根 `GIT.md` 与 README 根据当前 `.gitmodules`、`init.sh` 和 Makefile 描述版本边界与使用入口。源码、构建规则和子模块 gitlink 未改。

## 验证与限制

- 原 101 个文件路径和目录类型已核对；三份用户未提交文件哈希与开始时一致。
- 新建的项目级文档链接、辅助脚本路径、Python 语法和 `git diff --check` 已核对。`agents/v_symbolic_ir_workarounds/verify.py` 的严格配置校验通过：79 份配置、67 个 region、22 处注释锚点，IR SHA-256 为 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`。
- 原有历史文档中仍有指向当前工作区不存在的旧源码、worktree 或产物的链接；本轮没有改写这些历史证据。性能脚本需要历史实验指定 SHA-256 的 `isla/target/release/isarch`，当前缺少该二进制，故未重新运行性能实验。
