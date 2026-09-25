# Git 版本与工作树边界

本文记录 isla-runner 的版本管理规则。目录职责见 [specs/project-structure.md](specs/project-structure.md)，初始化命令见 [README.md](README.md)。

## 父仓库固定的源码

`isla/` 与 `sail-riscv/` 是父仓库记录精确 commit 的 Git submodule。`.gitmodules` 记录获取地址，`160000` gitlink 记录实际版本；分支名不代替 gitlink。更新其中任一源码版本时，先确认目标 commit、remote 与工作树状态，再由父仓库显式移动对应 gitlink。不要用 `git submodule update --remote` 隐式推进版本，也不要为了匹配 gitlink 对已有修改运行 reset 或 clean。

`./init.sh --submodules-only` 只初始化缺失的子模块或核对已有 checkout。已有 HEAD 与 gitlink 一致时，即使有未提交修改也保留；HEAD 不一致时停止。`./init.sh` 的其他初始化动作处理独立仓库，执行前也须检查其本地修改。

## 独立仓库与运行证据

`sail/`、Ara、assembly-gen、difftest 及 XiangShan 上游 checkout 不由上述两个 gitlink 固定；它们的实际 commit、branch、dirty diff 与构建配置要分别记录。父仓库提交只固定它跟踪的源码与文档，不能声称同时固定这些独立仓库里未提交的实验状态。

每次 IR 生成或测试应记录受测的源码 commit、IR 哈希、配置、关键工具版本和输出位置。历史结果以生成当时的 provenance 为准；当前状态及是否需要复验见 [specs/TODOs.md](specs/TODOs.md)，逐次记录见 [docs/RESULTS.md](docs/RESULTS.md)。

提交或迁移前检查根仓库及相关子仓库的 staged、unstaged 和 untracked 内容。移动文件时先保留用户已有修改，再核对目标文件和引用。发布父仓库 gitlink 前，确认引用的子模块 commit 可从记录的 remote 获取。
