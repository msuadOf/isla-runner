# 当前状态

2026-09-28 用户修订方案后的实施见 [plan.md](plan.md)。Sail-RISC-V `configs/isla/workarounds/` 中的 79 份文件现在是 Isla 直接使用的配置，均为 `strict=false`，保留 d012 IR 基准哈希。Isla 删除 79 份副本，`scripts/run.mk` 的 77 个目标直接引用 Sail-RISC-V 路径；VFMV/VFMERGE 两份历史配置仍在 Sail-RISC-V，但沿用先前暂存改动中已解除的 Makefile 绑定。先前的生成器及其测试已移除。

Isla `src/isarch_main.rs` 对 `strict=false` 的哈希不匹配输出 warning 并继续；`strict=true` 仍按原有规则拒绝。哈希相同或未配置哈希时不告警。只有相关 Sail 模型代码变化时，才需要复核并调整对应源码区域；基准哈希偏移本身不要求改配置。

## 验证

| 检查 | 结论 |
| --- | --- |
| `python3 -B -m unittest discover -s isla/scripts -p test_workaround_integration.py -v` | 3/3 PASS：Make 直接读取 Sail 配置、普通目标不加载 workaround、79 份配置为非严格且有基准哈希。 |
| `cargo test -p isla --bin isarch execution_limits_ --no-default-features --quiet` | 2/2 PASS：严格模式仍拒绝失配，非严格模式返回继续执行的 warning。 |
| `cargo fmt --all -- --check`、`git diff --check` | PASS；Rust 格式与修改补丁无空白错误。 |
| `python3 -B agents/v_symbolic_ir_workarounds/verify.py --model <f8ce849 导出模型>` | PASS：79 份、132 region、22 锚点。 |
| `python3 -B agents/v_symbolic_ir_workarounds/verify.py` | FAIL：当前暂存 Sail 模型已有源码位置变化，`mvvtype.toml` 等旧区域失效；此问题在文件迁移前已存在。 |

当前默认 IR SHA-256 为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。本轮没有重新生成 IR、运行完整 `make solve` 或把旧源码坐标视为当前模型的 PASS。当前 Sail 模型修改稳定后需逐区域核对，并用同源 IR 复验求解。

本议题已单独提交 Sail-RISC-V `1fb6988`（`feat/isla-workarounds`）与 Isla `b18d6b7`（`feat/float-support`）。父仓库本地 gitlink 指向这两个提交；两仓原有浮点模型、IR 和其他暂存内容仍留在索引/工作区。提交尚未推送，远端可获取性未验证。
