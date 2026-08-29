# Agent 友好化与子模块版本收敛计划

状态：等待用户确认；本文件确认前不执行删除、移动、子模块登记、提交或推送。

## 目标

- 将依赖版本固定为根仓库可审阅的 Git submodule gitlink，而不是由 `Makefile` 隐式 clone。
- 让 Codex 与 Claude Code 共享简短、单一来源的项目说明和 `SKILL.md` 工作流。
- 仅保留持续有用的说明、源码和可复现输入；生成物、索引和历史临时记录均不进入版本控制。
- 保全当前所有未提交的子仓库与实验工作，绝不以清理为名丢弃修改。

## 目标目录

```text
.
├── .agents/
│   ├── findings.md
│   ├── overview.md
│   └── skills/
│       └── generate-riscv-ir/
│           └── SKILL.md
├── .claude/
│   └── skills/
│       └── generate-riscv-ir -> ../../.agents/skills/generate-riscv-ir
├── deps/
│   ├── isla/                 # submodule
│   ├── sail/                 # submodule
│   ├── sail-riscv/           # submodule
│   └── xiangshan/            # submodule；仅在保留 XiangShan 链路时创建
├── tools/
│   ├── assembly-gen/         # submodule
│   ├── difftest/             # submodule
│   └── difftest-xiangshan/   # 根仓库自有 harness；仅在保留时创建
├── .gitmodules
├── .gitignore
├── AGENTS.md
├── CLAUDE.md                  # 仅导入 AGENTS.md，避免副本漂移
├── Makefile
└── README.md
```

`artifacts/` 仅作为 ignored 的 IR 输出目录；不会重新加入当前已经删除的 `rv32d.ir` / `rv64d.ir`。

## 实施步骤

1. **先保全版本。** 为每个独立子仓库记录 remote、commit 和未提交差异。所有要固定的修改必须先进入相应子仓库的可引用 commit（本地提交或已推送分支，由用户决定）；仅 `sail` 当前可直接按现有 commit 固定。
2. **登记 submodule。** 以确认后的 URL 和 commit 创建 `deps/{isla,sail,sail-riscv}` 与 `tools/{assembly-gen,difftest}`，生成 `.gitmodules`，并将构建脚本改为只执行 `git submodule update --init --recursive`，不再 clone 或 checkout 隐藏版本。
3. **处理 XiangShan 链路。** 若保留，则将 harness 变为根仓库受控的 `tools/difftest-xiangshan`，把 `xiangshan` 作为 `deps/xiangshan` submodule，并更新路径引用；若不保留，则在确认后删除整个未跟踪目录。不能把现有外层未跟踪目录直接变成一个 submodule。
4. **重写构建入口。** 将 `Makefile` 拆成明确的 `init`、`build-sail`、`build-isla`、`ir`、`test` 和仅清理 ignored 输出的 `clean`。`ir` 将 IR 写入 ignored `artifacts/`；构建前验证 Sail patch 是否已被目标 revision 吸收，避免重复 apply。`distclean` 不删除 submodule 工作树。
5. **压缩 agent 配置。** 将根 `AGENTS.md` 缩为项目范围、目录职责、唯一构建命令、验证与删除边界；将 `CLAUDE.md` 改为对 `AGENTS.md` 的导入。新增共享的 `generate-riscv-ir` Skill，正文只记录可复现的 IR 工作流与前置条件；`.claude/skills` 使用符号链接，不复制 Skill 内容。
6. **清理冗余文件。** 重写根 `README.md`，只保留项目目的、初始化、IR 生成、子模块更新和最小目录图。删除已被 `findings.md` 吸收的历史 agent 计划、审计稿、子 agent 报告与日志；删除或忽略 `.serena/`、`out/`、`report/`、Python cache、空 `.codex` 文件与可再生构建目录。停止跟踪或删除失配的 Docker/CI 文件前，会先采用下方的明确决策。
7. **验证。** 执行 `git submodule status --recursive`、从空 clone 初始化 submodule、`make -n` 检查路径、Skill frontmatter 校验、`git diff --check`。仅在工具链已可用且不需要下载依赖时执行目标构建验证。

## 必须确认的决策

1. **子仓库未提交修改：** 选择“先提交到各子仓库，再固定 commit”，或明确授权我为哪个仓库生成本地提交；没有可引用 commit 的修改不会被纳入 submodule。
2. **XiangShan：** 保留为 `tools/difftest-xiangshan` + `deps/xiangshan`，还是删除现有未跟踪的 `difftest-xiangshan/`？
3. **历史与本地状态：** 是否确认删除所有旧 `agents/<旧议题>/` 文档、`.worktrees/`、`.serena/`、`out/`、`report/` 与子仓库构建输出？`.worktrees/` 内存在未提交修改，删除前必须先保全或明确放弃。
4. **Docker/CI：** 当前 `Dockerfile` 与 GitHub workflow 的镜像/仓库名不匹配且没有可用 IR 构建流程；是删除它们，还是把修复容器与 CI 纳入本次范围？

## 不做的事

- 不自动执行 `git clean`、`git reset`、强制 checkout、删除子模块或推送远端。
- 不恢复当前工作区中已存在的 IR 删除。
- 不把个人权限配置 `.claude/settings.local.json` 提交到仓库。
