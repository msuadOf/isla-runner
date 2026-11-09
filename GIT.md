# Git 版本与工作树边界

本文记录 isla-runner 的版本管理规则。目录职责见 [specs/project-structure.md](specs/project-structure.md)，初始化命令见 [README.md](README.md)。

## 根仓的双议题版本

`float` 与 `memory` 是根仓分支，各自提交两个子模块gitlink和 `specs/topic-version.json`。本机分别检出于 `.worktree/runner-float`、`.worktree/runner-memory`，原master及dirty工作区保留。版本、发布前提及更新步骤见 [双分支说明](specs/topic-versions.md)。获取远端引用不等于已更新根仓版本；子模块提交应先可从正式远端获取，再推根仓议题分支。

## 父仓库固定的源码

`isla/` 与 `sail-riscv/` 是父仓库记录精确 commit 的 Git submodule。`.gitmodules` 记录获取地址，`160000` gitlink 记录实际版本；分支名不代替 gitlink。更新其中任一源码版本时，先确认目标 commit、remote 与工作树状态，再由父仓库显式移动对应 gitlink。不要用 `git submodule update --remote` 隐式推进版本，也不要为了匹配 gitlink 对已有修改运行 reset 或 clean。

`./init.sh --submodules-only` 只初始化缺失的子模块或核对已有 checkout。已有 HEAD 与 gitlink 一致时，即使有未提交修改也保留；HEAD 不一致时停止。`./init.sh` 的其他初始化动作处理独立仓库，执行前也须检查其本地修改。

## 独立仓库与运行证据

`sail/`、Ara、assembly-gen、difftest 及 XiangShan 上游 checkout 不由上述两个 gitlink 固定；它们的实际 commit、branch、dirty diff 与构建配置要分别记录。父仓库提交只固定它跟踪的源码与文档，不能声称同时固定这些独立仓库里未提交的实验状态。

每次 IR 生成或测试应记录受测的源码 commit、IR 哈希、配置、关键工具版本和输出位置。历史结果以生成当时的 provenance 为准；当前状态及是否需要复验见 [specs/TODOs.md](specs/TODOs.md)，逐次记录见 [docs/RESULTS.md](docs/RESULTS.md)。

提交或迁移前检查根仓库及相关子仓库的 staged、unstaged 和 untracked 内容。移动文件时先保留用户已有修改，再核对目标文件和引用。发布父仓库 gitlink 前，确认引用的子模块 commit 可从记录的 remote 获取。

workaround 配置归 `sail-riscv/configs/isla/workarounds/` 管理，Isla 直接读取，不再保留生成副本。后续提交这组改动时，先形成可获取的 Sail-RISC-V 提交，再形成消费它的 Isla 提交，最后由父仓库同时更新两个 gitlink；仅提交父仓库文档不能固定当前子模块未提交内容。


## 增量审查参照

Isla 统一以 `0008fae76f4cff86dae1a036d889f0414c228e9d` 为共同基准核对实际生产代码增量。当前任务的短期基线仍需明确，以区分继承改动与本次改动；大IR、归档数据行数不能代替生产复杂度统计。必要性与最小化原则见 [项目验收口径](specs/GOAL.md)，本次审查见 [共同基准审查](agents/float_review_closure_20261102/baseline-0008fae/isla-review.md)。
