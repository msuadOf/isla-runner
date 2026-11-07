# 枚举分支五入口 IR 更新计划

目标：在根仓 `29aa4765` / `feat/memory-enum`，从 Isla `d7c25993` 与模型 `d79d8b32` 重新生成五入口 IR。保持模型和 workaround 原字节，不执行 Git 写操作；发布状态为待发布。

范围与热点：`isla/rv32d.ir`、`isla/rv64d.ir`、`isla/ir/rv64d_v*_e64.ir`、`isla/ir/provenance/manifest.json`，以及根仓版本、状态和验证记录。四份 provenance JSON 是生成配置；补齐当前模型新增且 Isla 必须显式指定的 Svnapot/Svpbmt 支持项，RV64=true、RV32=false，其余配置保持原文件。本轮生成记录另存 sidecar。

步骤：复制历史浮点 Sail 0.20.1 快照和 Isla 插件到 `output/memory-enum-20261107/toolchain/`；普通严格检查；四配置独立缓存并行生成；核对源、工具、配置和五入口哈希；更新来源。重跑旧合流本机定向验证，分别记录通过、失败和未做。核对模型改动与 workaround 的交集，再运行 verify.py；不因 IR 哈希变化修改配置。

验证：沿用 `agents/float_memory_merge_20261103/validation/` 的严格生成、输入冻结及动态脚本。生成最多四路；符号执行单次 -T64，批量每例 -T32且最多四路。旧定向 T1 在新批次调整为 -T32，差异需明确。每步无进展超过40分钟停止。命令、原始输出和大产物放本工作树 `output/`，可提交报告不含本机绝对路径。

未决：新分支与旧验收器的兼容性、依赖是否齐全、受影响 workaround 区域是否有效；既有全域/硬件限制不转记为本轮通过。
