# 新版本真实 Make smoke

使用与三表示批次相同的封存输入清单（SHA-256 `25a1a624cb5dcac76a2261c470e198c64a75b20259322a1c7ee5d0572b83ec24`），在 CPU36 独立工作目录执行 `python3 agents/float_review_closure_20261102/validation/make/run.py --inputs agents/float_review_closure_20261102/validation/inputs.model-8ad5e8e.json --batch model-8ad5e8e --cpu 36`。运行器把冻结的新 `isarch` 链到私有 `target/release/isarch`，实际运行当前 Isla `scripts/run.mk` 的 `make solve-FLEQ_S` recipe；使用冻结新 rv64 VLEN128 IR 和固定 qNaN 初态配置。Make 命令行显式传 `THREADS=1`、`TASTIC=qffp`、`SOLVE_TIMEOUT=7200s`、`SMT_TIMEOUT=7200s`、`OUTER_TIMEOUT=7200s`，并使用 `LD_PRELOAD` 固定 seed17。完整 argv、环境、源码/IR/程序/Z3/seed 库及工具链哈希见 [command.json](model-8ad5e8e/smoke/command.json)。

实际 recipe 启动，退出 0；墙钟 4.02 秒，生成 8 条新 JSON。summary 为 `finished`，八项 partial 计数均存在且为零；seed 日志明确 `fixed=17`。qNaN 左右角色语义检查通过，GCC/Clang 助记符、精确字节和 `.insn` **48/48 通过**。逐项结果和日志见 [result.json](model-8ad5e8e/smoke/result.json) 与同目录 `make.log`、`output/log/FLEQ_S.log`、`toolchains/results.json`。结果 JSON SHA-256 为 `de742d75190d3e264b5889fde36f697d4fe03eac8d0bf8a9e27eaaef68f04ee4`。

此项是固定初态的真实 Make 入口 smoke，**PASS** 只适用于该新版本、该 FLEQ_S 定向输入；不计入正式完整域 77 Clause 的完成数。独立审查仍须签实际产物。
