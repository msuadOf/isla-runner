# 性能测试 IR 快照

四份 `.gz` 文件保存 2026-09-23 测试实际使用的 RV64/VLEN=128/ELEN=64 IR。`base` 对应 Sail-RISC-V `5f1a0de0`，`new` 对应去重后的 `f8ce8490`，`history` 是当时正式的 `isla/rv64d.ir`，`direct` 是在 `new` IR 上仅把 MOVETYPEV 的 helper 调用换回原语的隔离对照。原始 IR 的 SHA-256 记录在 `../prepare.py`，准备输入时逐一校验。

从仓库根目录运行 `python agents/v_symbolic_dedup_perf/bench.py --prepare-only` 可展开 `base`、`new`、`history`，并生成对应的严格限制配置；`python agents/v_symbolic_dedup_perf/helper-bench.py --prepare-only` 另展开 `direct`。正常运行脚本时自动执行同一步骤。运行需要与原测试相同哈希的 `isla/target/release/isarch`，脚本会先校验它。生成的 IR、日志和结果保留在本目录的被忽略子目录中。
