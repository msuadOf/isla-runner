# GOAL — 目标与验收口径

本文记录 isla-runner 的长期目标与验收边界。当前任务进度见 [TODOs.md](TODOs.md)，目录和版本关系见 [project-structure.md](project-structure.md)，逐次验证见 [RESULTS.md](../docs/RESULTS.md)。

IR 生成与严格配置的可复用检查约定见 [ir-workflow.md](ir-workflow.md)。

## 目标

将兼容版本的 Sail 工具链、RISC-V Sail 模型与 Isla 放在同一工作区，生成并分析 RISC-V 模型 IR，并让汇编生成与差异测试链路使用可追溯的模型和输入。根仓库负责组织这些组件及其辅助工具；具体代码语义以对应源码和专题分析为准。

## 主要工作流

1. 使用父仓库 gitlink 初始化或验证 `isla/` 与 `sail-riscv/`，同时按需准备独立管理的 Sail 和测试工具。
2. 构建 Sail、Sail-RISC-V 和 Isla，生成所需的 RISC-V IR；记录使用的源版本、配置和 IR 哈希。
3. 以明确的 IR、Isla 配置和指令集合做符号执行；检查完整退出状态、生成结果与超时，不以单条路径成功代表整组验收。
4. 需要硬件差异测试时，记录 DUT、参考模型、VLEN/ELEN、ELF、输入状态和对比结果；历史 PoC 不能脱离其版本与配置复用。

## 验收原则

- 初始化不得覆盖已有未提交修改；子模块 HEAD 与父仓库 gitlink 不同时显式停止。
- 验证结论必须指向实际命令、配置、版本和输出。实现完成与验证通过分别记录；实现或受测配置变化后，旧 PASS 只作历史证据。
- 跨 Isla、Sail-RISC-V、硬件模拟器的结果需先核对模型、向量长度和测试输入是否一致，再解释语义差异。

当前各议题的进展与剩余验证统一见 [TODOs.md](TODOs.md)；历史实验和限制见 [RESULTS.md](../docs/RESULTS.md)及对应专题文件。
