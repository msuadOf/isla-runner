# 修后新 IR 的真实 Make smoke

使用冻结清单 `validation/inputs.model-21418d0-itrace.json`（SHA-256 `44641223d4541b042a337c9adab6ac902f34d3af82f3835213f28b39cc247b19`），在 CPU36 执行 `PYTHONDONTWRITEBYTECODE=1 python3 agents/float_review_closure_20261102/validation/make/run.py --inputs agents/float_review_closure_20261102/validation/inputs.model-21418d0-itrace.json --batch model-21418d0-exact --cpu 36`。私有工作目录中的 `target/release/isarch` 指向冻结新程序；实际调用当前 Isla `scripts/run.mk` 的 `solve-FLEQ_S` recipe、修后 IR 和固定 qNaN 初态配置。Make 命令行显式传 `THREADS=1`、`TASTIC=qffp`、`SOLVE_TIMEOUT=7200s`、`SMT_TIMEOUT=7200s`、`OUTER_TIMEOUT=7200s`，`LD_PRELOAD` 固定 seed17。完整 argv、来源/配置/程序/IR/Z3/工具链哈希见 [命令记录](model-21418d0-exact/smoke/command.json)。

实际 recipe 启动，退出0，墙钟 **4.04秒**，生成 **8条新 JSON**。`summary.status=finished`，八项 partial 计数逐项存在且为0，seed日志明确 `fixed=17`。FLEQ.S 的 qNaN 左右角色语义检查通过；GCC/Clang 助记符、精确字节、`.insn` **48/48项严格通过**，没有精确转换回退。结果 JSON SHA-256 `d17e33758a16ad45b30f6eeb384343593020e8a2f37521ae8c00fa8e61b16d89`；原始证据见 [结果记录](model-21418d0-exact/smoke/result.json)、同目录 `make.log`、`output/log/FLEQ_S.log` 和 `toolchains/{results,selection}.json`。

此项固定初态真实 Make smoke **PASS** 仅适用于该模型/IR/程序和FLEQ_S输入，不计入正式完整域 Clause 完成数。独立审查已复核实际 recipe、seed 日志、8条 JSON 和48项工具链结果，见 [修后结果审查](../../review/acceptance/model214-results-review.md)。
