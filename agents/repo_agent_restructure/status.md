# 当前状态

## 已完成

- 已读取根目录规则、`agents/overview.md` 与 `agents/findings.md`。
- 已确认 Codex 使用 `.agents/skills`、Claude Code 使用 `.claude/skills`；两者均可通过符号链接共享同一 `SKILL.md`。
- 已盘点根仓库、嵌套 Git 工作树、生成目录和未提交状态。
- 已创建待确认计划，尚未执行目录重构或删除。

## 关键风险

- `isla`、`sail-riscv`、`assembly-gen`、`difftest`、XiangShan 及 `.worktrees` 中都有未提交修改。
- 根仓库已有用户未提交的文档修改和 IR 删除；必须原样保留。
- 清理能释放大量空间，但需要先明确哪些实验应保全为 commit、patch 或被舍弃。

## 下一步

- 等待用户确认 `plan.md` 的目录方案和四项决策。
