# AGENTS.md

## 目录介绍

本仓库用于把 `sail`、`sail-riscv` 和 `isla` 的特定版本收敛到同一工作区，围绕 RISC-V 模型生成与分析 IR。顶层目录可按用途理解为：

- `isla/`：Isla 主仓库，包含 `isla-sail`、`isla-lib` 等组件，也是生成 `rv32d.ir` / `rv64d.ir` 的核心目录。
- `sail/`：Sail 语言与工具链源码。
- `sail-riscv/`：RISC-V 的 Sail 模型源码。
- `assembly-gen/`：汇编/指令生成与测试相关工具目录，包含 `main.py`、`src/`、`input/`、`resource/` 等内容。
- `agents/`：辅助分析记录目录，用于沉淀代码逻辑与排查结论。
- `rv32d.ir`、`rv64d.ir`：已生成的 RISC-V IR 产物。
- `Makefile`：顶层构建入口，用于拉取、编译和组织相关产物。
- `extract_clause.sh`：本地辅助脚本。
- `sail-riscv.patch`：针对 `sail-riscv` 的本地补丁。

## 索引
- `agents/`: 记录目录下仓库中与agent写作的相关文档
- `agents/findings.md`: 记录目录下仓库中代码相关的逻辑

## Rules(规则)
- 子目录的`AGENTS.md`中对于子目录的规则，需要尊重，如果有明显冲突应当询问用户
- 要秉持着遵循原来的代码风格和变量使用习惯
- `agents/overview.md`中查看仓库代码的概览，和代码有关的活动看这个目录
- `agents/<本次规划的主题和目标>/`: 记录目录下当前主题的仓库中代码相关的工作文件，如plan.md、status.md
  - `agents/<本次规划的主题和目标>/plan.md`: 存放规划的plan文件，在plan后写入文件，等待用户修改plan并确认
  - `agents/<本次规划的主题和目标>/status.md`: 当前工作的状态，包含不限于：当前修改的热点文件、关注的部分、进展情况等
- `agents/findings.md`: 记录目录下仓库中代码相关的逻辑，所有的对代码的发现、对代码逻辑的理解都必须写到本文件中，在涉及代码工作的时候必须先加载本文件再做代码分析