> 2026-11-03 旧候选历史记录。仅归档 Markdown，文中的日志路径属于原工作树；不能代签 2026-11-09 候选测试。当前结果见 [议题状态](../status.md)。

# Executor 快照写时复制实施记录

受测起点：Isla `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`，本工作树的未提交 Rust 修改。`LocalFrame` 的 `execution_limit_state`、`local_state`、`memory`、`stack_vars`、`backtrace`、`function_assumptions`、`pc_counts`、`taken_interrupts` 和启用 `tracetool` 时的 `itrace_path` 改为 `Arc`。冻结和恢复只克隆 `Arc`；各写入口调用 `Arc::make_mut`，独占状态原地写入，兄弟路径或父快照共享时才分离。原有公开方法签名保持。

先新增 `frozen_and_resumed_frames_share_heavy_state_until_written`，运行定向测试得到编译红例，记录于 `red-test.log`。实现后补充 `unique_local_frame_writes_in_place`，并扩充共享、内存实际 region 写入、调用栈压栈和 `tracetool` 路径分离断言。新增测试共 2 项；原有 `tracetool` 路径测试也增加指针共享与分离断言。已执行 `cargo fmt --all` 和 `git diff --check`。

测试统一使用以下环境变量：

```sh
export CARGO_TARGET_DIR=../../isla/.worktrees/memory-consistency/target
export RUSTFLAGS="-L native=$HOME/.local/opt/z3-official-1fd1d3613/lib -C link-arg=-Wl,-rpath,$HOME/.local/opt/z3-official-1fd1d3613/lib"
```

| 命令 | 结果 | 日志 |
| --- | --- | --- |
| `cargo test -p isla --lib` | 149/149 通过。`HEAD` 基线同一命令的 `-- --list` 也是 149 项，不能沿用其他版本的 163 项计数。 | `isla-root-lib.log`、`baseline-isla-list.log` |
| `cargo test -p isla-lib --lib -- --test-threads=1` | 在 `get_multi_member_enum_const_after_checkpoint_replay` 遇到 Z3 `enumeration sort name is already declared`，测试进程异常退出。 | `isla-lib-default.log` |
| `cargo test -p isla-lib --lib -- --test-threads=1 --skip _after_checkpoint_replay` | 275/275 通过，3 项过滤。 | `isla-lib-default-skip-replay.log` |
| `cargo test -p isla-lib --lib --features tracetool` | 在 Z3 枚举 sort 测试中异常退出。 | `tracetool-test.log` |
| `cargo test -p isla-lib --lib --features tracetool -- --test-threads=1 --skip _after_checkpoint_replay` | 332/332 通过，3 项过滤。 | `isla-lib-tracetool-skip-replay.log` |

被过滤的 3 项是 `get_single_member_enum_const_after_checkpoint_replay`、`get_multi_member_enum_const_after_checkpoint_replay`、`get_struct_with_enum_field_after_checkpoint_replay`。同一源码中，这些测试只操作 SMT checkpoint 与 solver，没有访问 `LocalFrame`。`git archive HEAD` 导出到独立临时目录；用相同 target 和 Z3 链接参数、`cargo test -p isla-lib --lib smt::tests::get_multi_member_enum_const_after_checkpoint_replay -- --exact --test-threads=1` 定向复现相同的 Z3 `enumeration sort name is already declared` 进程退出。证据见 `baseline-enum-replay.log`。根包基线列出 149 项，见 `baseline-isla-list.log`。

`LocalState` 的执行期表达式读取仍调用需要 `&mut LocalState` 的接口；若冻结快照后首次此类调用只读取数据，`Arc::make_mut` 仍会分离并复制整个 `LocalState`。这是现有可变接口下的性能边界。本轮没有修改表达式求值接口或 `Memory` 回调结构。
