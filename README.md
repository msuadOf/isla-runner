# isla-runner

本仓库把兼容版本的 Sail、RISC-V Sail 模型和 Isla 组织到一个工作区，用于生成与分析 RISC-V 模型 IR。目标和验收边界见 [specs/GOAL.md](specs/GOAL.md)；当前议题状态见 [specs/TODOs.md](specs/TODOs.md)。

## 初始化

新 clone 可使用：

```sh
git clone --recurse-submodules <isla-runner-url>
```

已有工作区运行：

```sh
./init.sh
```

仅初始化或验证父仓库固定的 Isla、Sail-RISC-V 子模块：

```sh
./init.sh --submodules-only
```

`./init.sh --ssh` 使用 SSH clone URL。脚本保留与 gitlink 匹配的脏子模块；HEAD 不匹配时停止，不自动 reset、checkout 或清理。Sail 与其他独立仓库由脚本按其分支和兼容版本处理，已有本地修改不会被覆盖。具体目录边界见 [specs/project-structure.md](specs/project-structure.md)。

## float／memory 根仓版本

根仓已建立 `float`、`memory` 两条分支，分别用gitlink固定整套Isla与Sail-RISC-V版本；本机工作树为 `.worktree/runner-float`、`.worktree/runner-memory`。各分支的 `specs/topic-version.json` 记录提交、IR哈希和候选边界，入口及远端同步顺序见 [双分支说明](specs/topic-versions.md)。原根工作区保持master及其未提交内容。

```sh
git -C .worktree/runner-float status
git -C .worktree/runner-memory status
git diff float memory -- isla sail-riscv specs/topic-version.json
```

当前两版本仅在本机准备，未推送；float采用审阅中的模型候选，未完成精确源码重生IR及联合验收。远端TLS连接失败，发布前需先保证子模块提交可从正式远端获取。

## 构建

```sh
make repos
```

该目标构建 Sail、Sail-RISC-V 和 Isla 所需组件；使用前请检查当前工作树、工具链与可用资源。`Makefile` 中的 `repo-sail-riscv` 目标会生成 RV32/RV64 Isla IR，并打印生成位置。`init.sh` 本身不构建、不生成 IR，也不自动应用历史 `sail-riscv.patch`。Docker 构建入口当前未作为已验证的使用路径。

### 统一浮点 C++ / Isla 模型

当前共享浮点模型需要带仓内补丁的 Sail 0.20.1。按[隔离构建入口](agents/float_support_review/tools/unified_backend_build/README.md)先从固定 Sail 提交构建工具链和匹配的 Isla 插件，再构建同源 C++ 模拟器与 V128/E64 IR；入口显式设置 CMake 的 `SAIL_BIN`。现有 opam Sail 未被修改，原安装版本缺少本次所需的 Sail 原生浮点类型 C++ 生成支持。

```sh
python3 agents/float_support_review/tools/unified_backend_build/build_toolchain.py --help
python3 agents/float_support_review/tools/unified_backend_build/build_model.py --help
```

完整模型已完成生成、编译和链接，命令、固定输入与证据见上述入口及[构建记录](agents/float_support_review/unified-backend-build.md)。可用 `--dependency-cache` 指定经哈希校验的离线依赖；`--configure-only` 只验证配置。数值、整指令状态和求解验收分别记录在[当前状态](agents/float_support_review/status.md)。

浮点非访存求解入口为 Isla 目录内的 `make solve-fd-nonmem`；普通 `make solve` 排除了浮点组。当前主 `isla/rv64d.ir` 仍是 d012，统一候选在隔离证据目录验证，尚未切换默认输入。运行前须确认 IR 与严格配置同版，完整77项进展见[执行表](agents/float_support_review/solve-audit-batch.md)。

workaround 配置直接位于 `sail-riscv/configs/isla/workarounds/`，`make solve-<clause>` 从该目录加载对应文件。配置设 `strict=false`：IR 哈希偏离基准时 Isla 报 warning 并继续执行。只有相关 Sail 模型代码变化时才需检查并调整源码区域；检查入口见 [IR 工作流](specs/ir-workflow.md)。

## 结果与分析

三种工具平级隶属 `tracetool`，共用路径状态和 writer。当前 Isla 轨迹按 `itrace`（逐指令）、`ftrace`（函数调用/返回）和 `btrace`（静态分支清单＋实际分支）组合。例如 `make solve ALL=MRET THREADS=1 FTRACE=1 BTRACE=1`，需要逐指令时追加 `ITRACE=1`；CLI 对应 `--ftrace --btrace --trace-output=FILE`，或 `--itrace=FILE --ftrace --btrace`。旧运行时查询表、紧凑模式及 `--no-itrace-catalog` 已由组合开关替代。JSON 的 `gen[].path-signature` 对应轨迹 `path_signature`，不保证唯一或完整覆盖；原未提交完整状态输出仍以顶层 `state-domain` 说明域。当前版本及逐层验证见[轨迹重组记录](agents/float_support_review/trace-composition-20261006.md)，历史结果按原生成版本解释。

逐次验证摘要见 [docs/RESULTS.md](docs/RESULTS.md)，专题调查与历史记录见 [agents/](agents/)。这些记录可能对应不同源码、IR、配置和模拟器版本；复用结论前先核对其 provenance。

在 `isla/` 中运行 solve 时，每个任务独立管理其 timeout 进程组，Ctrl-C 会清理该任务。手动停止使用 `make solve-kill SOLVE_PID=<监督进程PID>`；PID 可从运行中的 `solve_process.py run` 命令确认，不再按进程名全局清理。退出详情写入 `output/process/`。


仅浮点分支 `feat/float-only-20261008` 的多 IR 兼容性、FPR 状态修复及持久回归入口见[交付记录](agents/float_only_review/fix.md)；该记录对应独立工作树，不改变当前 `isla/` 的未提交状态。
