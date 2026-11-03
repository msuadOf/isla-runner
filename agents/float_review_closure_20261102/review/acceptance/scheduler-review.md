# 完整 Clause 调度器独立签收

`validation/full_batch/scheduler.py` SHA-256 `b478384ce3be9873bfa669c327b5723ebcbb53516e03a4c451aa4310ae42d690` 的调度与结果汇总逻辑限定签收，无当前阻断。此签收允许在最终输入另经 freeze/runner 审查后启动批次，不表示任何新 Clause 已完成或通过。

## 范围与证据

读取 [调度器](../../validation/full_batch/scheduler.py)、[规程](../../validation/full_batch/README.md)、[结构 dry-run](../../validation/full_batch/dry-run.json)。77 个不同任务明确拆为64受影响与13兼容回归；未缩小任何 Clause 的符号输入域。每CPU只同时绑定一个任务，候选CPU不含SMT同胞；实际是否受外部任务竞争，仍由启动前分配和运行时观测核实。

初版会漏查批次中输入漂移、对坏结果JSON直接退出、未核harness退出及结果身份，也缺重复监督器锁。owner已修正；审查者只改本审查目录。

独立执行：

```sh
python3 agents/float_review_closure_20261102/review/acceptance/audit_scheduler.py
```

[结果](scheduler-independent.json)与[日志](scheduler-independent.log)是临时假任务模拟，**没有执行 Isla 或正式 Clause**：

- 四任务中，坏 JSON、非零 harness 退出和错误任务身份分别保留失败账，正常任务通过，4条任务守恒。
- 批次中改 harness 后，已启动2条完成，其余3条明确 blocked，5条任务守恒，`batch_complete=false`。
- 另一个监督器已持有锁时，重复监督被拒绝。

正式 `run_clause.py` 的 source/IR/config/binary/官方库/seed/schema/JSON来源门由 [enum reviewer](../enum/runner-review.md)另签；启动前须使用同版已签文件与最终输入。调度器保存其哈希，每轮和每次启动前重核；每条结果须匹配job、batch、inputs、模型与Isla版本、完整域和seed，且harness退出0、原结果`pass=true`。目录已存在时拒绝覆盖。

## 限制和非阻断意见

`supervision_finished`只表示监督循环结束；`batch_complete`只表示所有任务已结束，不能代替`passed=77`或`affected_passed=64`。外限、partial、缺失或坏JSON、blocked均不能当作预算通过。

主树/collector/单次SMT实时阶段计数目前不可观测，调度器明确保留null；发生超时后仍须按计划单独诊断，不能据CPU或JSON缺失断言单次SMT卡住。通用进程/磁盘故障不具有跨监督器重启的自动续跑保证；旧输出保留，不能直接复用批次名重跑。瞬时CPU负载不能保证整批无外部竞争，不能从本批得出受控性能加速比。
