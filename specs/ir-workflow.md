# RISC-V IR 与 workaround 配置约定

本专题从原 [代码发现](../agents/findings.md) 和 [IR/workaround 记录](../agents/v_symbolic_ir_workarounds/status.md) 提炼可复用的流程约束。项目目标见 [GOAL.md](GOAL.md)，当前版本与验证状态见 [TODOs.md](TODOs.md)。

- RISC-V Sail 模型来自 `sail-riscv/`，Isla 工具来自 `isla/`。生成 IR 时先记录这两个目录的实际 commit、生成配置、IR 文件哈希及编译命令；历史文件名相同不代表内容相同。
- `sail-riscv/configs/isla/workarounds/` 是 Isla 直接使用的唯一 workaround 配置目录。79 份配置设 `strict=false` 并保留基准 IR 哈希；IR 哈希不匹配时 Isla 只告警并继续执行。只有相关 Sail 模型代码改动时，才核对并按需更新受影响的 region 行列与注释锚点；单纯 IR 哈希变化不要求改配置。
- `isla/scripts/run.mk` 的命令和默认 IR/配置取值以当前文件为准。正式验收需要记录运行时实际采用的 IR、配置、指令集合和求解退出情况；历史性能对照的限时完成路径数不能当作全量完成。
- [源码区域验证脚本](../agents/v_symbolic_ir_workarounds/verify.py) 在历史合流模型 `bf861b3e` 上检查了 79 份配置、130 个 region 和 22 处注释锚点；旧 float 版本的 132 个 region 是历史数量。两处旧 `get_start_element` 陷阱区域随 memory 语义退役，19 份冲突配置的映射见[模型实施记录](../agents/float_memory_merge_20261103/implementation/model/report.md)。基准 IR 哈希不符只提示 warning，不能替代本轮 IR 来源核对。

这些是检查流程；具体历史哈希、性能数字和逐次结果保留在 [RESULTS.md](../docs/RESULTS.md)及专题记录，不作为永久固定的版本选择。


2026-11-07 的 `d79d8b32` 模型仍为79配置/130区域/22锚点，源码位置复验通过。仅 `vmtype.toml` 一项涉及变动文件；其坐标已由模型 `70b4d10` 迁到 `[658:2,679:3)`，与 `bf861b3e` 原区间正文一致，本轮不改 workaround。新 IR 的79个基准哈希不匹配仍按 `strict=false` 只告警，来源哈希另行核对。

模型新增 `extensions.Svnapot.supported`、`extensions.Svpbmt.supported` 后，Isla 后端要求生成 JSON 显式提供它们；普通 `--just-check` 通过不能替代该检查。本轮遵循当前 `config/config.json.in` 的 `CONFIG_XLEN_IS_64`，四份生成配置仅补 RV64=true、RV32=false。失败、重跑和五入口结果见[本轮报告](../agents/memory_enum_ir_20261107/final-report.md)。
