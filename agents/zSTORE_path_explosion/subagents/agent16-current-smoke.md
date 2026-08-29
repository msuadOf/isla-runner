# agent16 current smoke

日期：2026-04-27

目标 worktree：`/home/baiyifan/workplace-local/isla-runner/isla/.worktrees/zstore-pma-mmio`

本次只写入本文件；未修改生产代码。运行前已读取：

- `agents/findings.md`
- `agents/zSTORE_path_explosion/status.md`

## 1. `cargo check`

实际执行命令：

```sh
cargo check -p isla-lib
```

执行目录：

```text
/home/baiyifan/workplace-local/isla-runner/isla/.worktrees/zstore-pma-mmio
```

结果：

- exit code：`0`
- 是否通过：通过
- 关键输出：
  - `Finished dev profile [unoptimized + debuginfo] target(s) in 1.05s`
  - `isla-lib` 生成 `65 warnings`
  - warning 主要是既有 `unused import` / `unused variable` / style warning / dead code / private interface / lifetime syntax warning
  - 未出现 Rust error

代表性 warning：

- `isla-lib/src/isarch.rs` 多处 unused import
- `isla-lib/src/isarch_args_yaml.rs:174` unnecessary parentheses
- `isla-lib/src/isarch_exec.rs` non-camel-case type、unused variable
- `isla-lib/src/primop.rs:2653` unreachable expression after `panic!("arrive carryless_mul!!")`
- `isla-lib/src/executor.rs` 若干 unused helper / variable
- `isla-lib/src/ir.rs:1233` mismatched lifetime syntaxes

## 2. zSTORE/zLOAD profile smoke

第一次 profile 命令用于预热/实际 smoke；45 秒 timeout 内包含 debug binary 编译，完成 profile 较少。

实际执行命令：

```sh
env RUST_BACKTRACE=1 ISLA_RISCV_PROFILE_FORKS=1 ISLA_RISCV_VMEM_BUILTIN_MODE=off ISLA_RISCV_VMEM_ASSUME_ALIGNED=1 ISLA_RISCV_BUILTIN_PMP_CHECK=1 ISLA_RISCV_TEST_ZSTORE_WIDTH=4 ISLA_RISCV_TEST_ZLOAD_WIDTH=4 timeout 45s cargo run --manifest-path /home/baiyifan/workplace-local/isla-runner/isla/.worktrees/zstore-pma-mmio/Cargo.toml --bin isarch -- -A /home/baiyifan/workplace-local/isla-runner/isla/.worktrees/zstore-pma-mmio/rv64d.ir -C /home/baiyifan/workplace-local/isla-runner/isla/.worktrees/zstore-pma-mmio/configs/riscv64_difftest.toml --verbose --probe-all --trace-all -I cur_privilege=Machine list-instructions > run.log 2>&1
```

执行目录：

```text
/tmp/isla-agent16-current-smoke-20260427
```

结果：

- exit code：`124`
- 是否通过：未完成；被 `timeout 45s` 截断
- build 输出：`Finished dev profile ... in 28.89s`
- profile 数：`3`
- `total_fork_events=15`
- `max_fork_events=6`
- 热点：
  - `matching_pma_bits_range=6`
  - `get_X=6`
  - `phys_access_check=3`
- 是否生成 JSON：否；没有 `output/`
- 关键 warning/error：
  - 编译 warning 仍为既有 warning
  - 未见运行时 panic / Rust error / builtin fallback

第二次 profile 命令复用已编译 binary，作为本次主要 smoke 样本。

实际执行命令：

```sh
env RUST_BACKTRACE=1 ISLA_RISCV_PROFILE_FORKS=1 ISLA_RISCV_VMEM_BUILTIN_MODE=off ISLA_RISCV_VMEM_ASSUME_ALIGNED=1 ISLA_RISCV_BUILTIN_PMP_CHECK=1 ISLA_RISCV_TEST_ZSTORE_WIDTH=4 ISLA_RISCV_TEST_ZLOAD_WIDTH=4 timeout 45s cargo run --manifest-path /home/baiyifan/workplace-local/isla-runner/isla/.worktrees/zstore-pma-mmio/Cargo.toml --bin isarch -- -A /home/baiyifan/workplace-local/isla-runner/isla/.worktrees/zstore-pma-mmio/rv64d.ir -C /home/baiyifan/workplace-local/isla-runner/isla/.worktrees/zstore-pma-mmio/configs/riscv64_difftest.toml --verbose --probe-all --trace-all -I cur_privilege=Machine list-instructions > run.log 2>&1
```

执行目录：

```text
/tmp/isla-agent16-current-smoke-20260427-rerun
```

结果：

- exit code：`124`
- 是否通过：未完整跑完；被 `timeout 45s` 截断
- build 输出：`Finished dev profile ... in 0.07s`
- profile 数：`22`
- `total_fork_events=118`
- `max_fork_events=8`
- profile return 分布：
  - `Retire_Success`: `6`
  - `Memory_Exception`: `16`
- 热点：
  - `get_X=44`
  - `matching_pma_bits_range=40`
  - `phys_access_check=22`
  - `within_mmio_writable=4`
  - `clint_store=4`
  - `clint_dispatch=4`
- 是否生成 JSON：否；没有 `output/`，也没有其它 `*.json`
- 关键 warning/error：
  - `isla-lib` 编译 warning：`65 warnings`，另有一条重复聚合为 `71 warnings (65 duplicates)`
  - `isla` bin `isarch` 编译 warning：`32 warnings`
  - 未见运行时 panic / `panicked at` / Rust `error:` / `test_exec_main` 运行错误 / builtin fallback
  - 日志中出现的 `SymbolicLength("zeros")` 只来自 compiler warning 展示源码行 `primop.rs:703`，不是本次运行时错误

## 3. 基线判断

当前 worktree 基线适合继续 PMA/MMIO：

- `cargo check -p isla-lib` 新鲜通过，说明当前基线可编译。
- 45 秒 profile smoke 在 `ISLA_RISCV_BUILTIN_PMP_CHECK=1`、`VMEM_BUILTIN_MODE=off`、显式 aligned 和固定 width 前提下能持续产出 `fork_profile`，没有运行时 panic/fallback。
- profile 热点已经落在 PMA/MMIO 相关链路：`matching_pma_bits_range`、`phys_access_check`、`within_mmio_writable`、`clint_store`、`clint_dispatch`；这与 status 中“PMP exact summary 后下一层转向 PMA/MMIO”的判断一致。

需要保留的 concern：

- 45 秒 smoke 没有生成最终 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`，不能替代 120 秒级完整 profile 或语义回归。
- 本次 profile 主要覆盖 `zSTORE` 早期路径；在 45 秒窗口内没有跑到 `zLOAD` 最终 JSON。
- warning 数量仍多，但与当前基线既有 warning 一致，未构成本次 PMA/MMIO 阻塞项。

结论：`DONE_WITH_CONCERNS`。
