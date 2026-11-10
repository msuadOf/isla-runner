# 浮点非访存 clause 官方入口批次

本目录固定 `scripts/run.mk` 的 77 个 RV64 非访存浮点 clause，顺序见 [targets77.txt](targets77.txt)。名单由 89 个 `FD_FLOAT` 去掉 10 个 `MEMORY` 交集和两个仅 RV32 合法的 `FMVH_X_D`、`FMVP_D_X` 得到。10 个访存项不在本批次范围。

这批使用当前主 Isla 浮点源码和 V128 IR；`make solve-*` 的退出码及 `Retire_Success` 只提供官方入口的运行层证据，不能单独证明数值、五种异常标志或完整输入域的语义正确性。语义定向证据仍见 [动态覆盖索引](../../e-coverage.md)。

## 复跑

调用者指定仓库外的全新运行目录；脚本只从主 Isla 目录复制 Cargo 工作区、IR、严格配置和运行入口，显式排除 `.worktrees`、`target`、`output`。准备阶段逐字节核对 `float.rs`、`executor.rs`、`smt.rs`、IR、FD 配置、`run.mk`、`Makefile` 和 79 份 workaround 配置，并将 SHA-256 写入外部 `evidence/manifest.json`。

```sh
./prepare.sh <主 Isla 目录> <仓库外运行目录>
cd <仓库外运行目录>/stage
env CARGO_BUILD_JOBS=4 make build-isarch
cd -
./run_range.sh <仓库外运行目录> 1 8
./run_range.sh <仓库外运行目录> 9 77
python3 ./summarize.py <仓库外运行目录>
```

每项固定 `THREADS=2`、`OUTER_TIMEOUT=60s`、`SOLVE_TIMEOUT=50s`、`SMT_TIMEOUT=5s`、`TASTIC=qfaufbv`，串行执行。单项 `evidence/<目标>.command/.make.log/.make.rc/.time`、`stage/output/log/<目标>.log` 和 `stage/output/status.*.log` 均留在外部运行目录。`summary.csv` 记录 make 与底层 isarch 退出码、已报告 Finished 路径、Retire、Illegal、其他返回、编码汇编条数、Unknown/timeout 字样、墙上时间和峰值 RSS。外层超时通常表现为底层 124、make 2；已完成的路径数不代表目标全量完成。

## 本轮配置

- 主 Isla HEAD：`f4f8e4584a70588c66c9e7a6286cc20211618f18`，浮点实现另有未提交修改，故以副本文件哈希为准。
- Sail-RISC-V HEAD：`f8ce8490981eac6396a31013180a2e718615757d`；本批不重新生成 IR。
- IR SHA-256：`c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`。
- 配置：`configs/riscv64_difftest_fd.toml`；命中目标专用 workaround 时由原 `run.mk` 自动带入。
- 运行时：Z3 4.16.0；Rust/Cargo 1.93.1；独立构建的 `isarch` 哈希及各文件哈希见外部清单。

本轮摘要见 [summary.md](summary.md)。完整原始日志与构建产物仅保存在调用者指定的仓库外目录。
