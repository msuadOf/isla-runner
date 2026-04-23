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
- `agents/findings.md`: 记录目录下仓库中代码相关的逻辑