# isla-runner

当前根仓议题分支：`memory`（float 合流候选）。已测范围获限定验收，原域访存 partial 与全域无退化未证另列；父仓提交/发布待完成。版本见 [topic-version.json](specs/topic-version.json)，合流范围见 [最终报告](agents/float_memory_merge_20261103/final-report.md)。

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

## 构建

```sh
make repos
```

该目标构建 Sail、Sail-RISC-V 和 Isla 所需组件；使用前请检查当前工作树、工具链与可用资源。`Makefile` 中的 `repo-sail-riscv` 目标会生成 RV32/RV64 Isla IR，并打印生成位置。`init.sh` 本身不构建、不生成 IR，也不自动应用历史 `sail-riscv.patch`。Docker 构建入口当前未作为已验证的使用路径。

workaround 配置直接位于 `sail-riscv/configs/isla/workarounds/`。求解目标由 `isla/scripts/run.mk` 提供，从根目录执行 `make -C isla solve-<clause>`；根目录的 `Makefile` 提供 `repos` 等初始化和构建目标。配置设 `strict=false`：IR 哈希偏离基准时 Isla 报 warning 并继续执行。只有相关 Sail 模型代码变化时才需检查并调整源码区域；检查入口见 [IR 工作流](specs/ir-workflow.md)。合流版定向 Make 已在已测范围限定签收；LOAD_FP、C_LD、STORE 原域仍为 partial，详见[最终报告](agents/float_memory_merge_20261103/final-report.md)。

## 结果与分析

逐次验证摘要见 [docs/RESULTS.md](docs/RESULTS.md)，专题调查与历史记录见 [agents/](agents/)。这些记录可能对应不同源码、IR、配置和模拟器版本；复用结论前先核对其 provenance。

历史 float 候选的 Sail-RISC-V 独立代码审阅及构建／测试建议见 [审阅报告](agents/sail_riscv_commit_review/independent-review-20261021.md)。报告及小型证据随float版本保存；不表示已修复报告问题或完成联合验收。
