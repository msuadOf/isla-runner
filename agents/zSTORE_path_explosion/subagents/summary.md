# 20-agent PMA/MMIO 汇总

日期：2026-04-27

本轮按用户要求分派 20 个 subagent，main agent 只做调度、汇总和交互。所有 subagent 均已返回。各 agent 的详细报告位于本目录下的 `agentNN-*.md`。

## 总体结论

- PMA/MMIO 下一步的首要实现点应是 `pmaCheck` exact summary，而不是 `matching_pma_bits_range` 或 `phys_access_check`。
- `pmaCheck` 的返回域是 `option(ExceptionType)`，能把 PMA region first-match、`range_subset` wrap 语义、misaligned policy 和 access permission 收敛到小返回域；直接 summary `matching_pma_bits_range` 会暴露 `option(PMA_Region)` payload，solver 成本和后续字段选择更难控。
- `phys_access_check` 可作为 `pmaCheck` 验证后的一层 wrapper；第一步不应直接把 PMP exact formula 和 PMA formula 合进一个更大的 summary。
- `within_mmio_readable/writable` 是可行的 predicate summary 候选，但它直接决定 RAM/MMIO 分派边界，第一版必须显式 gate、默认关闭。
- `clint_load` 可做 concrete exact-hit 小 summary；symbolic addr/width 应回退 IR。
- `clint_store` / `clint_dispatch` 有 `mip`、`mtime`、`mtimecmp` 写入和 callback/interrupt side effect，不应作为默认宽 summary 目标。
- HTIF load/store 当前应延后；HTIF predicate 只在 `htif_tohost_base=None()` 或 concrete `Some(base)` 且能精确保留 wrapping 语义时可考虑。

## 原型状态

- agent05 在 `isla/.worktrees/zstore-pma-mmio/isla-lib/src/executor.rs` 中加入了默认关闭的 `ISLA_RISCV_BUILTIN_PMA_CHECK` 原型。
  - 支持读取 `zpma_regions`，按 `range_subset` 语义合成 PMA 命中、misaligned access/alignment fault 和 permission fault。
  - 不支持条件回退 IR。
  - `cargo check -p isla-lib` exit `0`，仍有既有 warning。
  - 尚未做 builtin on/off 行为对照或 zSTORE/zLOAD profile。
- agent19 在同一文件中加入了默认关闭的 `ISLA_RISCV_BUILTIN_WITHIN_MMIO` 最小原型。
  - 当前只支持 `get_config_rvfi=false`、`htif_tohost_base=None()`、concrete width、concrete CLINT base/size。
  - `cargo check -p isla-lib` exit `0`，`diff --check` 通过。
  - 尚未做 wrapper/runtime profile 对照。

## 验证状态

- agent16 在 `isla/.worktrees/zstore-pma-mmio` 新鲜运行 `cargo check -p isla-lib`：exit `0`，`isla-lib` 有既有 `65 warnings`，无 Rust error。
- agent16 45 秒 profile smoke 目录为 `/tmp/isla-agent16-current-smoke-20260427-rerun`：
  - exit `124` timeout。
  - 完成 22 条 `fork_profile`。
  - `total_fork_events=118`，`max_fork_events=8`。
  - 热点为 `get_X=44`、`matching_pma_bits_range=40`、`phys_access_check=22`、`within_mmio_writable/clint_store/clint_dispatch=4`。
  - 未生成最终 JSON；该 smoke 只能作为健康检查和热点趋势证据，不能替代语义回归。

## 需要保留的边界

- `pmaCheck None` 只表示 PMA permit，不表示 plain RAM；RAM/MMIO 分派仍必须由 `within_mmio_*` 和后续 `mmio_read/write` / `read_ram/write_ram` 决定。
- `pmaCheck` summary 不应产生 memory event，也不应隐式关闭 MMIO。
- `pmaCheck` 必须补 `ReadReg zpma_regions`；CLINT 方向若后续内置，必须补对应 `ReadReg` / `WriteReg` 和 callback/trace 边界说明。
- 当前 output normalizer 只能做粗筛；PMA/MMIO 语义对照还需要比较 `address`、exception ctor/address、callback/MMIO event 或 sidecar trace、path constraints。
- builtin 命中仍会绕过函数级 trace/probe/stop/function-assumption；可称为 ISA 状态语义目标，不应称为函数级 trace 等价。

## 建议下一步

1. 审查 agent05 的 `pmaCheck` prototype，确认代码质量和 semantic boundary。
2. 用 agent06 的矩阵跑 `ISLA_RISCV_BUILTIN_PMA_CHECK=0/1` 的 short profile。
3. 如果 short profile 无 panic/fallback 风暴，再跑 long case，生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`。
4. 增强 normalizer 或补 sidecar trace，再比较 ret_val、memory event、exception address/type、RAM/MMIO/callback 分界。
5. 只有在 PMA on/off 语义对照和性能指标稳定后，再考虑 `phys_access_check` wrapper 或 `within_mmio_*` predicate gate。
