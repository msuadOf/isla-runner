# 合法性 guard 两小时宽域完整 Clause 复测

状态：**已完成**。本轮于 2026-10-31 UTC 启动，复用 `../A` 与 `../B_normal` 的严格 IR、`../context.toml` 和同一运行器。先前 60 秒试验仍见 [原报告](../report.md)；两轮不合并。

三对并行：CPU56 A→B、CPU57 B→A、CPU58 A→B，每对固定 CPU、`-T 1`。本轮没有额外预热。每次只用进程外 `timeout 7200s`，不传路径或 SMT 超时；`/usr/bin/time` 在外层保留终止时的 wall/user/sys/RSS。真实 fork 无可靠口径。

启动 PID 与原始命令见 [launch.json](launch.json) 和各 `pair-*/run-*/command.json`；运行状态见各 `pair-*/status.json`，逐次日志、资源和最终 JSON 在相应 `run-*` 目录。输入哈希逐次写入命令和结果记录。

| 对次 | CPU | 顺序 | 状态 | worker PID | 当前运行 |
| --- | ---: | --- | --- | ---: | --- |
| 1 | 56 | A→B_normal | complete | 3218095 | agents/branch_ablation_20261031/guards/budget-2h/pair-0/run-1-B_normal |
| 2 | 57 | B_normal→A | complete | 3218096 | agents/branch_ablation_20261031/guards/budget-2h/pair-1/run-1-A |
| 3 | 58 | A→B_normal | complete | 3218097 | agents/branch_ablation_20261031/guards/budget-2h/pair-2/run-1-B_normal |

当前已完成运行数：6/6。

## 三次正式运行统计

数值为中位数 [最小, 最大]，只按本轮三次结果统计。
- A：墙钟 {'median': 132.69, 'min': 129.88, 'max': 134.49} 秒；用户 CPU {'median': 122.59, 'min': 120.84, 'max': 124.98} 秒；系统 CPU {'median': 8.96, 'min': 8.49, 'max': 9.61} 秒；RSS {'median': 527232, 'min': 518728, 'max': 555988} KiB；gen/退休/非法/其它异常 {'median': 81, 'min': 81, 'max': 81}/{'median': 54, 'min': 54, 'max': 54}/{'median': 27, 'min': 27, 'max': 27}/{'median': 0, 'min': 0, 'max': 0}；外限次数 0。
- B_normal：墙钟 {'median': 133.68, 'min': 132.29, 'max': 136.59} 秒；用户 CPU {'median': 122.95, 'min': 122.09, 'max': 125.36} 秒；系统 CPU {'median': 10.16, 'min': 9.6, 'max': 10.69} 秒；RSS {'median': 513612, 'min': 506516, 'max': 530164} KiB；gen/退休/非法/其它异常 {'median': 108, 'min': 108, 'max': 108}/{'median': 54, 'min': 54, 'max': 54}/{'median': 54, 'min': 54, 'max': 54}/{'median': 0, 'min': 0, 'max': 0}；外限次数 0。

B/A 墙钟中位数比为 1.0075；仅对应本轮宽域完整 Clause。
