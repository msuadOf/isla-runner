# 77 条完整 Clause 批次调度

当前状态：调度器已完成结构性 dry-run，**未启动正式批次**。等待 validation owner 交付最终冻结 inputs/五 IR/正式 binary，并由独立 Sol 的 acceptance_review、enum_review 分别签收。旧现成 binary 或将被共享 target 覆盖的路径不得填入正式 inputs。

本目录的 `scheduler.py` 直接调用 `../run_clause.py`，不改 harness、不复制其求解和 PASS 判定逻辑。harness 输出保存在其默认 `../runs/<batch>/<Clause>/`；本目录只存批次 plan、控制、PID、增量 summary 和 supervisor 日志。本轮唯一批次名由主 agent 最终确定；目录已存在时拒绝覆盖。

结构性 dry-run 可在冻结前执行：

~~~sh
python3 agents/float_review_closure_20261102/validation/full_batch/scheduler.py \
  --dry-run --batch float-closure-preview \
  --inputs agents/float_review_closure_20261102/validation/inputs.template.json
~~~

它核 77 条 jobs 与 `inventory/affected-clauses.json` 的 64 受影响条、13 兼容回归条，查看 CPU 兄弟关系和初始忙碌率，不检占位资产、也不启动求解。当前输出见 [dry-run.json](dry-run.json)，CPU 是当时快照，正式启动会重新选。

正式输入和双审查签收后，由主 agent 明确启动：

~~~sh
python3 agents/float_review_closure_20261102/validation/full_batch/scheduler.py \
  --launch --batch <唯一批次名> --inputs <冻结inputs.json> \
  --acceptance-review <独立Sol的acceptance_review报告> \
  --enum-review <独立Sol的enum_review报告> \
  --cpus <2到8个互非同胞的逻辑CPU，逗号分隔>
~~~

`--cpus` 可省略，调度器在当前 affinity 内按1秒 CPU 忙碌率选择最多8个物理核；若找不到两个忙碌率不超过50%的独立核则停止。显式 CPU 仍须通过 affinity 和 SMT 同胞检查。启动器先对首项执行原 harness 的 `--dry-run`，让它核两个源码清单、五 IR 中首项所用 IR、完整域配置、binary 与官方库哈希及动态链接；随后后台独立进程监督所有 77 条，终端立即返回 supervisor PID。其余各项由原 harness 在运行前逐项重核各自 IR/config。输入或 harness 哈希在批次中漂移会导致监督器拒绝继续。

第一阶段最多同时跑 2 条，每条 T1/qffp/seed17、整 Clause 和单 SMT 各7200秒。运行 5/15/30 分钟在 `batches/<batch>/observations.jsonl` 留 RSS、可用内存、外部 emu 线程数和所选 CPU 同胞竞争快照；`summary.json` 每30秒刷新，每完成一条追加其 exit/summary/JSON数/峰值 RSS/PASS，`pids.json` 记录监督器和活动子进程。外部负载只观测，不调整其他人的进程。需要扩大并发时，先检查前两条 RSS 和主机空闲情况，再将 `batches/<batch>/control.json` 的 `max_parallel` 改为4到8；监督器在不足5分钟、RSS未知或内存余量不足时仍限制为2。CPU 始终一核一任务，不同时使用 SMT 同胞。

状态以原 harness 的 `../runs/<batch>/<Clause>/result.json` 为准；本目录聚合区分 64 条受影响与 13 条兼容回归。部分任务完成、外限124、partial、没有结果 JSON、seed 拦截失败均不作为整组 PASS。调度器只作执行和聚合，不把有限样例或某 Clause 的完成称为全格式/全子操作覆盖。

本批原 harness 启用 itrace、verbose 和 debug，墙钟时间包含轨迹写盘与外部 CPU 竞争，不能直接同历史无轨迹程序作纯源码性能比较。若本批在 7200 秒内完成，可签该更强运行条件下的预算；若超时，先按真实路径和 SMT 账分析，再另建同模型/binary/config/seed 的受控诊断批比较日志开关，不据本批单独归因控制流性能。诊断批不替代正式完整域结果。
