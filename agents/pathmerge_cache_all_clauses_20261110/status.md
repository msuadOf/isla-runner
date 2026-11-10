# 路径合并与缓存实测状态

## 最新追加：第二轮等待（2026-11-10）

主轮宿主机 PID 2128518 保持运行。新增独立等待脚本，不改主轮正在使用的文件。等待主轮锁释放并完成子进程收尾后，自动补跑环境错误，以及指定 Poison 错误；后者使用 default tactic，其他参数保持。其他错误、partial 和超时不补跑。此授权取代下文历史状态里对两项环境错误“不重试”的处理。

当前名单：FWVFTYPE、FWVTYPE（qffp），ORCB、RORI（default）；随主轮记录更新，结束后冻结。第二轮最多两个 isarch，结果独立保存，最终汇总合并两轮。五项名单筛选、default 优先、结果合并和主轮收尾门槛测试通过，尚未运行第二轮 isarch。

- [等待进度](../../.worktree/pathmerge-cache-all-20261110/progress-second.json)
- [动态名单](../../.worktree/pathmerge-cache-all-20261110/second-queue.json)
- [等待脚本启动信息](../../.worktree/pathmerge-cache-all-20261110/second-launch.json)
- [第二轮结果](../../.worktree/pathmerge-cache-all-20261110/results-second.jsonl)
- [规则与文件说明](../../.worktree/pathmerge-cache-all-20261110/README.md)

## 前一轮交付时状态（保留历史）

当前：221 项全量 driver 已后台运行，PID `4`（工具隔离进程空间），持续工具会话 `55673`。已验证独立调用之间进度继续更新、driver 持锁，始终最多两个 isarch。当前运行项和完成数以 progress.json 为准。

## 验证结果与实际异常

- ORCB、RORI 冒烟缓存检查通过：双格式文件存在，manifest、批次号、JSON 实际条目数一致，sampled-paths=0；两项求解均因译码回环 Poison 报错，outcome 均记 error，不能称完整探索通过。
- 四项限制核查通过：命令无 execution limit 参数或 workaround；driver 清理限制环境；三份 ISA 配置无 execution_limits 和 include；源码不加载默认限制文件。只开启路径合并，预算为空。
- 首次后台启动的隔离会话随启动命令结束而退出，FWVFTYPE、FWVTYPE 仅运行到约 4 秒末次心跳。已核实锁释放，登记为运行环境 error，不重试。后续用持续会话承载 setsid nohup 后台 driver，继续剩余 217 项。
- 全量最终可完成性、超时数仍待真实运行结束；未新增全量 PASS。停止条件、逐项数据和最终汇总均由 driver 维护。

## 入口

- [计划](plan.md)
- [运行说明与实际命令](../../.worktree/pathmerge-cache-all-20261110/README.md)
- [后台启动与存活证据](../../.worktree/pathmerge-cache-all-20261110/launch.json)
- [实时进度](../../.worktree/pathmerge-cache-all-20261110/progress.json)
- [逐项结果](../../.worktree/pathmerge-cache-all-20261110/results.jsonl)
- [限制核查](../../.worktree/pathmerge-cache-all-20261110/limits-audit.json)
- [冒烟报告](../../.worktree/pathmerge-cache-all-20261110/smoke.json)

没有 Git 写操作；没有修改旧实测目录、IR 或缓存工作树源码。范围变更前的冒烟保留在本实验 superseded-smoke-347/，不计入 221 项。
