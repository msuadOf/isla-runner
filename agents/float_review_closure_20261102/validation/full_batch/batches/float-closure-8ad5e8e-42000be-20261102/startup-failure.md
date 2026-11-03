# 首批完整 Clause 启动门失败

批次 `float-closure-8ad5e8e-42000be-20261102` 使用冻结 inputs SHA-256 `25a1a624cb5dcac76a2261c470e198c64a75b20259322a1c7ee5d0572b83ec24`、受影响清单 SHA-256 `6f3fc71ea2c9c6ebea3e21a1bdbf76db144db8464e0313e9f00655c8c7ad603c`，签收调度器 `b478384c...` 与 harness `7b126047...`，按 T1/qffp/seed17/7200秒预算后台启动，首两条是 `F_BIN_RM_TYPE_S`、`VFUNARY0`。

首条 `run.log` 立即报告“当前构建未启用轨迹支持，请启用 itrace/ftrace/btrace feature”。已签 binary `fe4bdceb...` 未编译 `tracetool`，而已签 `run_clause.py` 固定传 `--itrace`。这是启动资产不匹配，无法得到正式 Clause 结果；harness 的 dry-run 核过文件/链接哈希但未执行该 CLI feature 检查。已启动的 14 条均 isarch exit 1、无结果 JSON、PASS 0；余 63 条未启动。supervisor PID 617801 已停止并确认退出，所有 14 个作业子进程已退出。最后一次周期 summary 只汇总前12条，完整14条账以 [halt.json](halt.json) 和各 `validation/runs/<batch>/<Clause>/result.json` 为准。

旧批次原样保留，不重用其名称，也不将这些退出写成 7200 秒超时、部分覆盖或语义失败。下一步由 validation owner 以正式 Isla 42000be 重建带 `tracetool` 的独立 binary，更新冻结 inputs，并由 enum reviewer 对新 binary/官方库/runner 合同重签；用新唯一批次名称先跑一条真实 CLI smoke，再启动77条后台批次。保留 `--itrace` 有利于长时路径诊断，避免修改已签 harness 及其审查边界。
