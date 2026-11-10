# solve 进程管理独立提交（2026-10-06）

## 目标与范围

用户要求将现有暂存的 solve 进程管理、Ctrl-C 清理及测试独立提交。仅纳入 `isla/scripts/solve_process.py`、`test_solve_cleanup.py`、`run_ctrl_c.mk` 以及 `run.mk` 的监督命令与清理接入；`solve-fd-nonmem` 入口继续留在暂存区。保留其他暂存、未暂存和父仓库改动。

## 步骤与验证

先备份 HEAD、索引条目、两层补丁与文件哈希；从原暂存生成四文件候选，移除run.mk浮点入口增量。运行候选既有进程清理回归（覆盖退出/超时、重复信号、顽固孙进程、并行隔离、PID核验及真实make信号转发）；执行工作区MRET smoke。使用独立索引新建提交，主索引和所有工作区源码不变，核对剩余run.mk仅含浮点入口。没有新增实现，不另造测试或改Rust。证据目录：`isla/target/solve-process-commit-20261006/`。

## 状态

已提交 `1eddd687c4393855c49677d9fb1d130e1eed1916`，父 `a9884b2`，四文件 +507/-46。索引条目、工作区文件哈希及未暂存补丁逐字不变；run.mk剩余暂存差异只有浮点非访存求解入口及相应注释。未push、未提交父仓库gitlink。

## 验证结果（限定PASS）

- `/usr/bin/python3 isla/target/solve-process-commit-20261006/candidate/scripts/test_solve_cleanup.py`：12项全部通过，7.833秒；这是精确提交脚本候选的测试，包含真实make与模拟worker。
- 完整工作区 `make solve ALL=MRET THREADS=1 ITRACE=1`：退出0、4 gen，监督器JSON的return_code为0。
- 本轮未改实现，复验已有回归；未跑全量solve或硬件。无需Rust格式化。
- IR SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`；配置 `71fb63e105331a0f329261c636e55446af42ba0367c96e45c9b49cb60332ad2d`；工作区binary `825535965a36d3958a54c2e4486d936b8e08fa1ccf0bafaa0ac16d01c789857a`。

证据目录含候选、tests.log、make.log、smoke.json、监督器报告、commit.patch、after.json，以及操作前两层补丁和文件清单。

## 接续：通用 smtperf 测试修正独立提交

用户要求再单独提交 `isla-lib/src/smt/z3_timeout.rs` 的既有测试修正：补四参数宏所需SourceLoc并用真实Z3 Context替代空指针。仅此文件+3/-1，不改生产逻辑。计划从HEAD隔离候选，复验smtperf与smtperf,smt-thread-interrupt两种feature下的测试和fmt，再独立索引提交；其余索引条目、工作区文件与未暂存补丁保持。证据位于 `isla/target/smtperf-test-commit-20261006/`，当前验证中。

已完成为 `d9f0fe0fbd1f14b98fef5450d227dc06ee6618b1`，父 `1eddd68`。精确候选执行 `cargo test --offline -q -p isla-lib --lib --features smtperf smtperf_tests -- --test-threads=1` 及将feature改为 `smtperf,smt-thread-interrupt` 的同命令，均4/4通过；`cargo fmt --all -- --check`通过。仅测试修正，本轮未重跑make solve，前节smoke属于前节版本。原索引条目、工作区文件哈希与未暂存补丁核验不变，未push。命令日志/checks.json/after.json见上述证据目录。

## 接续：worker panic 记账独立提交

用户要求独立提交既有worker panic修复。仅提取executor.rs未暂存补丁（+25/-2），原暂存浮点dispatcher/采样改动不纳入；候选从HEAD应用该补丁，复验有界panic回归、executor测试和fmt。提交时将此修复同步到主索引以避免出现反向未暂存差异，原浮点暂存补丁保持不变，工作区源码不改。证据目录 `isla/target/worker-panic-commit-20261006/`，当前验证中。

完成提交 `7b7337b0dea0c4105644436a606dbec5ae9b3fea`，父 `d9f0fe0`，仅executor.rs +25/-2。候选 `cargo test --offline -q -p isla-lib --lib --features itrace,smt-thread-interrupt --no-run`编译通过；随后15秒外限筛选 `multi_runtime_propagates_collector_panic` 通过，30秒外限筛选 `executor::` 通过；`cargo fmt --all -- --check`通过，具体命令/输出见checks.json和日志。此前同工作区make solve MRET结果见本报告进程管理节，本轮工作区源码哈希未变，未重复运行solve，不将其记为精确提交的solve验证。原暂存增删行与全部工作区文件哈希保持不变，其他索引条目未改；executor.rs现仅有暂存的浮点支持改动。未push。
