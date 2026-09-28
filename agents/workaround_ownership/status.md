# 当前状态

2026-09-28 用户修订方案后的实施见 [plan.md](plan.md)。Sail-RISC-V `configs/isla/workarounds/` 中的 79 份文件现在是 Isla 直接使用的配置，均为 `strict=false`，保留已提交 V128 IR `6fc39efd…` 的基准哈希。Isla 删除 79 份副本，`scripts/run.mk` 的 77 个目标直接引用 Sail-RISC-V 路径；VFMV/VFMERGE 两份历史配置仍在 Sail-RISC-V，但沿用先前暂存改动中已解除的 Makefile 绑定。先前的生成器及其测试已移除。

Isla `src/isarch_main.rs` 对 `strict=false` 的哈希不匹配输出 warning 并继续；`strict=true` 仍按原有规则拒绝。哈希相同或未配置哈希时不告警。只有相关 Sail 模型代码变化时，才需要复核并调整对应源码区域；基准哈希偏移本身不要求改配置。

## 验证

| 检查 | 结论 |
| --- | --- |
| `python3 -B -m unittest discover -s isla/scripts -p test_workaround_integration.py -v` | 3/3 PASS：Make 直接读取 Sail 配置、普通目标不加载 workaround、79 份配置为非严格且有基准哈希。 |
| `cargo test -p isla --bin isarch execution_limits_ --no-default-features --quiet` | 2/2 PASS：严格模式仍拒绝失配，非严格模式返回继续执行的 warning。 |
| `cargo fmt --all -- --check`、`git diff --check` | PASS；Rust 格式与修改补丁无空白错误。 |
| 从 Sail-RISC-V HEAD 导出模型、从 Isla `b18d6b7` 导出 IR 后执行 `python3 -B agents/v_symbolic_ir_workarounds/verify.py --model <模型目录> --ir <导出 IR>` | PASS：79 份、132 region、22 锚点，基准 IR 哈希为 6fc。 |
| `python3 -B agents/v_symbolic_ir_workarounds/verify.py` | warning：79 份配置的 6fc 基准与当前暂存 d012 IR 不同；源码检查 FAIL：当前暂存 Sail 模型已有位置变化，`mvvtype.toml` 等旧区域失效。此源码问题在文件迁移前已存在。 |

Isla 提交 `b18d6b7` 的 IR SHA-256 为 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`；当前工作区暂存 IR 为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，因此当前运行会按设计提示基准哈希偏移。本轮没有重新生成 IR、运行完整 `make solve` 或把旧源码坐标视为当前模型的 PASS。当前 Sail 模型修改稳定后需逐区域核对，并用同源 IR 复验求解。

本议题已单独提交 Sail-RISC-V `1fb6988` 与基准哈希修正 `4f2ac29`（`feat/isla-workarounds`），以及 Isla `b18d6b7`（`feat/float-support`）。父仓库本地 gitlink 指向 Sail-RISC-V `4f2ac29` 和 Isla `b18d6b7`；两仓原有浮点模型、IR 和其他暂存内容仍留在索引/工作区。提交尚未推送，远端可获取性未验证。
