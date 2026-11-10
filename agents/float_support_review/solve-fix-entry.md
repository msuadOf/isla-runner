# 官方非访存浮点 solve 入口

2026-09-26 在 `isla/scripts/run.mk` 增加 `solve-fd-nonmem` 聚合目标。集合 `FD_NONMEM_RV64` 从 `FD_FLOAT` 去除 `MEMORY`、`FMVH_X_D`、`FMVP_D_X`，共 77 项；经原 `FD_FLOAT_SOLVE_TARGETS` 规则继承 `configs/riscv64_difftest_fd.toml`。单项 `solve-%` 命令、超时默认值、execution limits 和 `solve-pre` 计数器逻辑未修改。

先写 [dry-run 检查](tools/solve_entry_tests/check_entry.py)并运行：修改前退出 1，断言失败在缺失 `FD_NONMEM_RV64`；当时 `make -np solve-fd-nonmem` 会把入口名交给通用 `solve-%` 规则，当作 `fd-nonmem` clause。增加显式聚合目标后，同一检查退出 0：`make -np` 展开的 77 个 clause 与[固定清单](tools/official_float/targets77.txt)逐项同序，77 个命令均使用 FD 配置，聚合目标本身没有执行命令；默认 `solve` 仍为 220 项，原 `solve-fd-float` 仍为 89 项，计数器只初始化一次。

复核命令：

```sh
python3 agents/float_support_review/tools/solve_entry_tests/check_entry.py
git -C isla diff --check -- scripts/run.mk
```

两项均退出 0。本次只做静态 `make -np` 和差异检查，没有重跑完整 77 项；当前 d012 IR 的实际逐项结果仍见[官方批次审计](solve-audit-batch.md)。
