# Agent 协作规范与项目文档重构计划

状态：用户已授权执行；按反馈保留 `agents/` 原有文件和目录。

## 目标结构

参考 `nacc_boom@aa03a94` 建立根 `AGENTS.md`、`GIT.md`、`README.md`、`specs/GOAL.md`、`specs/project-structure.md`、`specs/TODOs.md` 和 `docs/RESULTS.md` 的职责分工。`CLAUDE.md -> AGENTS.md` 已存在，保留原状。

**根 `agents/` 是原有协作资料的归属目录，不迁入 `docs/`。** `agents/overview.md` 负责议题入口，`agents/findings.md` 记录可复用的代码发现，`agents/<topic>/plan.md` 是方案，`status.md` 是摘要和详细文件导航；报告、审查、实验与脚本仍留在对应议题下。

## 实施内容

1. 从现有 README、根规则、`.gitmodules`、`init.sh` 和议题记录中提炼目标、结构、版本边界与已验证用法，写入新的根文档和 `specs/`，不改变构建或子模块行为。
2. `specs/TODOs.md` 汇总各议题当前实施、验证、证据和下一步，指向原位 `agents/<topic>/status.md`。实施和验证分列；历史 PASS 不能自动代表当前版本。
3. `docs/RESULTS.md` 汇总逐次结果及其适用版本，链接原位议题详细文件或冻结档案。完整过程仍在 `agents/` 和 `archives/`。
4. 更新根 `AGENTS.md`、README 与 `agents/overview.md` 的入口关系；保留先写议题 plan、用户确认后实施的本仓库工作流程。
5. 核对原有未提交内容、Markdown 链接、脚本运行路径、局部 `isla/AGENTS.md` 和 Git 差异。任何先前错误移动的 `agents/` 文件、名字与脚本都恢复原位。

## 验收

- 根 `agents/` 是实体目录；原有文件仍以原路径和原文件名访问，辅助脚本从原路径解析正确。
- 新规范、状态总表和结果索引均指向 `agents/`，没有把议题历史误写成当前 PASS。
- 用户已有未提交修改保留；新文档链接、脚本静态检查及 `git diff --check` 通过。

具体修正和验证见 [migration.md](migration.md)，参考依据见 [research.md](research.md)。
