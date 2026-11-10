# 新官方 Z3 控制变量消融实施方案

目标：在官方 Z3 `1fd1d3613`、固定 qffp 策略与同一冻结运行器下，重测 14 个完整 Clause 工作负载的 A/B 消融。每项三对 AB/BA/AB，种子 17/29/43；各对固定独立物理 CPU，最多 12 对并行。

范围：只读复用 `agents/branch_ablation_20261031/` 的已生成 IR/配置；所有新输入、pilot、调度、原始日志、JSON、报告只写本目录。A 是当前 ITE/严格布尔，B 只恢复该项 `if`/短路。`nan_unbox` 仍为已恢复的显式 `if`。不改生产源码、生产 IR、分支和其它组目录。

实施步骤：

1. 冻结二进制、Z3 库、seed 拦截器和 14 项输入，核 SHA、源版本和两臂配置一致。
2. IR 逐函数去源码位置，再仅将每个函数的**形式参数**按位置 alpha 归一化；核对只剩目标函数差异。mask 的 23 个位置剥离后变动函数中，22 个仅形式参数改号，另一个是目标 `zexecute`。
3. 用真实小 Clause 证明 seed 拦截日志含 `random_seed` 原值与固定值，核进程自然完成；pilot 与正式数据分开。
4. 启动持久后台队列。12 个不同物理核上的 worker 每次只跑一对，两臂同核、同种子、同输入；`-T 1`、qffp、显式 `--smt-timeout 7200s`、整个 Clause 外限 7200 秒且 TERM 后 10 秒 KILL，不传更短路径预算。
5. 每次保存命令、退出、wall/user/sys/RSS、seed 拦截、输出 JSON 与哈希。增量汇总终态、partial/timeout 和目标条件见证；两臂未全部完成或见证类别不同，不写等覆盖加速比。

验证：`input-verification.json`、`alpha-audit.json`、pilot 原始日志、`launch.json`、`queue.json` 与 `runs/` 逐次记录。运行中看 [实时机器汇总](live-summary.json) 和 [实时报告](live-report.md)，最终结论见 [status.md](status.md)、`summary.json` 和 `report.md`。

未决：长尾 Clause 是否在两小时内完成；不同种子下条件见证集合能否一致。完成前不推断被外限截断一臂的耗时或覆盖。
