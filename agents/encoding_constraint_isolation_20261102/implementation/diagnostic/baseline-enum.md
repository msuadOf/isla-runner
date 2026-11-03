# enum checkpoint 测试失败：基线复现

结论：`get_multi_member_enum_const_after_checkpoint_replay` 的 `enumeration sort name is already declared` 在本轮保留指令断言修订之前的干净 Isla `8e5a3f7` 上也可单独复现；当前 `cf1aa14` 同名测试单独运行得到相同错误、相同退出码 1。这是本次新增 checkpoint 筛选代码之外的现存失败，本文不修复或把它计为 PASS。

## 运行边界

基线使用独立 `isla-baseline/` worktree，HEAD `8e5a3f7c542ba5cbbd95a0ffb46441dfb01ce217`，工作树干净。`baseline-target/debug/` 由生产 Debug 缓存以 btrfs reflink 复制后独立构建，不覆盖生产 target。命令在该 worktree 执行：

```sh
taskset -c 114 env CARGO_BUILD_JOBS=1 CARGO_TARGET_DIR=../baseline-target cargo test -p isla-lib --lib get_multi_member_enum_const_after_checkpoint_replay --no-default-features
```

实际调用中 `CARGO_TARGET_DIR` 为上述相对目录对应的绝对路径，日志见[基线原始输出](baseline-enum-test.log)。构建 32.32 秒，测试仅运行 1 项，报 `Error: enumeration sort name is already declared`，进程退出 1。基线测试程序 SHA256 为 `63cf30b6bb2daeff3408e82a0548dc3ba5249a1272befb67f35ac2273decd248`。

当前测试使用已构建 Debug 程序的独立 reflink 副本 `current-test-bin`，只读执行，不修改生产 target：

```sh
taskset -c 114 ./current-test-bin --exact smt::tests::get_multi_member_enum_const_after_checkpoint_replay
```

[当前原始输出](current-enum-test.log)同样仅运行 1 项并报同一 Z3 错误，退出 1。当前测试程序 SHA256 为 `675ee0e901d0838d67395a7b6337d33bb86bbdad70980199a239b6f7c842311c`。两侧均固定 CPU114；执行前抽样其与同胞 CPU50 使用率约 0%/0%，因为原 CPU74 的同胞 CPU10 当时接近满载。未改正式运行进程。

`git show 8e5a3f7:isla-lib/src/smt.rs` 与当前 `cf1aa14` 源码中的该测试函数正文逐字一致，SHA256 均为 `ae2a61dc23e8a5a73393753d605daa7631e2ae312255ec99fab30740d526bb86`。测试在同一 Z3 `Context` 上创建 enum，然后把含 enum 定义的 checkpoint 重放到该 `Context`；报错文字指向重复 sort 声明。这里仅说明可复现路径，不把原因扩大为新筛选逻辑的动态证明。与本轮改动直接相关的两项 checkpoint 定向测试分别通过，见[选择性保留实施](../selective-retention.md)。

## Z3 动态库边界

两份 Debug 测试程序的 `NEEDED` 均为 `libz3.so.4`。在测试环境下，[基线 ldd](baseline-ldd.txt)与[当前 ldd](current-ldd.txt)都解析到 `/usr/lib/x86_64-linux-gnu/libz3.so.4`，真实文件 SHA256 均为 `eff8f0f91482d0809aae7aa0ed54cb52ff5ee9b5fe1ed1d2bfa9153c4a2fcfaf`。审计时 `RUSTFLAGS`、`LD_LIBRARY_PATH`、`LD_PRELOAD` 均未设置；基线 Cargo 命令只另外设置 `CARGO_BUILD_JOBS` 和独立 `CARGO_TARGET_DIR`。

为直接核对运行时装载，再分别以 `env -u LD_PRELOAD -u LD_LIBRARY_PATH LD_DEBUG=libs taskset -c 114` 单独执行两份程序。同样退出 1，动态链接器日志均显示装入上述系统 `libz3.so.4`，错误原文仍相同：[基线装载日志](baseline-enum-runtime-z3.log)、[当前装载日志](current-enum-runtime-z3.log)。因此“基线与当前在同一 Z3 库下同样失败”的动态证据成立。

**这不是正式 Clause 使用的官方 Z3 库。** 正式 Release 链接 `/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3`，SHA256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。本报告不能断言此 Debug 测试在官方 `libz3.so.5.3` 下也失败；两份 Debug 程序需要 `libz3.so.4`，未把不同 SONAME 的库强行替换。
