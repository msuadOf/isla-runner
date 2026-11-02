# 选择性保留修订：官方 Z3 的 Release 定向测试

结论：Isla `cf1aa1431d5f2d05584c78c0e7c84862a9a9b1fa` 源码在与正式程序相同的官方 Z3 库下，指定的 **15/15 项 Release 定向测试通过**。两份测试程序均从干净隔离 worktree 构建，使用独立 `official-target/`，未覆盖生产 `target/release/isarch` 或修改生产源码。完整构建输出见[build.log](official-build.log)，逐项命令、退出码、程序与库 SHA256、`ldd` 见[机器记录](official-tests/result.json)。

构建基点与正式程序的 [binary-selective-ready.json](../../binary-selective-ready.json) 一致：默认 feature（本仓默认为空）、`RUSTFLAGS='-L native=/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib -C link-arg=-Wl,-rpath,/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib'`。在 `isla-official-tests/` 执行：

```sh
taskset -c 122 env CARGO_BUILD_JOBS=1 CARGO_TARGET_DIR=../official-target RUSTFLAGS='-L native=/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib -C link-arg=-Wl,-rpath,/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib' cargo test --release --no-run -p isla-lib -p isla --lib
```

实际 `CARGO_TARGET_DIR` 为上述相对路径对应的绝对路径；构建用时 3 分 40 秒。原拟使用 CPU114，但预检发现其上有近满载 EMU，故改为物理同胞 CPU58/122 均约 0–1% 的 CPU122，避免竞争正式任务。所有测试进程也固定 CPU122，`--test-threads=1`；运行脚本见[run_official_targeted.py](run_official_targeted.py)。

|测试程序|SHA256|实际 Z3|
|---|---|---|
|`isla-lib` Release 测试程序|`bc052086db88317876989c1fa008813c2e8d9b029991fba9f6cbd69bedd2e570`|`libz3.so.5.3`|
|`isla` Release 测试程序|`3092eace9c098b489d5d90e487aa141474e9d9fa01095bd6097e3f98562d83fd`|`libz3.so.5.3`|

两程序的 `ldd` 均解析到 `/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3.4.0`，真实库 SHA256 均为 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`，与正式程序记录一致；`readelf` 均显示 `NEEDED libz3.so.5.3` 和上述目录的 RUNPATH。

|过滤器|结果|原始日志|
|---|---:|---|
|原 checkpoint 合并测试|1/1|[日志](official-tests/checkpoint_old.log)|
|新指令断言筛选测试|1/1|[日志](official-tests/checkpoint_new.log)|
|编码候选测试|2/2|[日志](official-tests/encoding.log)|
|原 collector 回归|11/11|[日志](official-tests/collector.log)|

额外将 `get_multi_member_enum_const_after_checkpoint_replay` 单独在此官方库下运行，仍报 `enumeration sort name is already declared`，退出 1，见[原始日志](official-tests/enum_context.log)。它不属于上述 15 项通过数；此前的[系统库基线复现](baseline-enum.md)现在又有官方库下的当前源码结果，但未在官方库下重建旧基线测试程序，因此不把两版官方库动态对照说成已完成。该测试源码未因本修订改变，本轮不修复它。

本测试证明源码定向行为与正式 Z3 库组合可运行；完整旧 flags、新模型 flags/sat 的 7200 秒 Clause 性能、全部 JSON 与编码仍以对应 Release 完整验证为准。初版 `de00adb` 的完整结果不自动成为 `cf1aa14` 的 PASS。
