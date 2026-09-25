# RISC-V IR 与严格配置约定

本专题从原 [代码发现](../agents/findings.md) 和 [IR/workaround 记录](../agents/v_symbolic_ir_workarounds/status.md) 提炼可复用的流程约束。项目目标见 [GOAL.md](GOAL.md)，当前版本与验证状态见 [TODOs.md](TODOs.md)。

- RISC-V Sail 模型来自 `sail-riscv/`，Isla 工具来自 `isla/`。生成 IR 时先记录这两个目录的实际 commit、生成配置、IR 文件哈希及编译命令；历史文件名相同不代表内容相同。
- `isla/configs/workarounds/` 的严格配置按 IR SHA-256 和 Sail 源码区域约束执行。重新生成 IR 后，应核对全部配置绑定的哈希，并逐项检查受源文件移动影响的 region 行列与注释锚点；不能仅替换哈希就视为完成迁移。
- `isla/scripts/run.mk` 的命令和默认 IR/配置取值以当前文件为准。正式验收需要记录运行时实际采用的 IR、配置、指令集合和求解退出情况；历史性能对照的限时完成路径数不能当作全量完成。
- 现有 [验证脚本](../agents/v_symbolic_ir_workarounds/verify.py) 可检查当前 79 份严格配置、67 个相关源码区域和 22 处注释锚点；任何数量变化都要先核对脚本假设与仓库实际状态。

这些是检查流程；具体历史哈希、性能数字和逐次结果保留在 [RESULTS.md](../docs/RESULTS.md)及专题记录，不作为永久固定的版本选择。
