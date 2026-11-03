# e9完整Clause调度器独审

**准备条件签收通过，可按受签内容启动两核主批。** 受审`validation/full_batch/e9/scheduler.py` SHA-256 `3ecd0ebc27db2e365b5d74fb49f8daceebc7a9ca29a3a87dddffb69d8650cf5b`；旧214调度器仍为`b478384c…`，字节未变。本页不签77项完整预算的动态结果。

独立比较新旧源码，改动限于e9子目录路径、从冻结inputs读取闭包、16核上限、磁盘/轨迹余量启动guard，以及结果身份补affected清单哈希和scope。每轮及每次Popen前继续核inputs/harness/affected文件hash；漂移使尚未启动队列转blocked，已启动项继续监管。每Clause的完整域、T1/qffp/seed17和整Clause/单次SMT各7200秒仍由原受签harness执行，没有截短、抽样或缩Clause配置。

实际只读`read_jobs`核冻结inputs `eb830e77…`、模型`e9d69d2`、Isla`42000be`、affected清单 `7b3c98bc…`；77条仍是64受影响+13兼容。闭包额外要求committed component heads、clean及分母相符；正式inputs缺affected项或hash不符即拒绝，模板占位模式仅用于准备。CPU池继续校验affinity及SMT同胞互斥；初始2并行和5分钟/RSS扩容门保持，max_parallel=16接受、17拒绝。后续扩容应依据现场资源观测，不由该上限自动批准实际16核同时运行。

独立[审计脚本](audit_scheduler_e9.py)没有启动Isla；在本审查目录内临时构建假harness和队列，自动清理，见[结果](scheduler-e9-independent.json)：

| 场景 | 实际结果 |
| --- | --- |
| 重复supervisor | flock拒绝第二监督器 |
| 坏JSON、非零退出、错job、错affected哈希、错scope | 五项均记失败，唯一正常项通过，6项全部守恒 |
| 运行后harness漂移 | 已启2项继续完成，余3项blocked，未伪称batch_complete |
| 起始磁盘不足 | 3项仍排队，无进程启动；恢复余量后3项完整完成 |
| 轨迹增长率抬高预估 | 尚有active任务时暂停新任务，不杀active、不丢队列；恢复余量后3项完整完成 |

磁盘启动门以20GiB基础余量加每任务`max(1GiB,历史最大log+itrace字节,历史峰值增长率×7200秒)`作保守预估；summary明确显示free/projected/required/guard。它不是全部未来磁盘写入的上界，未计入该采样的JSON/SMT dump等仍可能增长，且不终止已有任务。磁盘暂停可长期保留排队任务，不能当失败或通过；恢复磁盘后同一监督器继续，跨监督器重启仍无自动续跑。路径/collector/SMT实时计数未知仍记null，不由CPU利用率猜测。

独立mock验证期间无生产源码、IR、inputs或旧实验修改。inventory方另报真实harness dry-run77条/负例及FLEQ_S smoke，动态证据应按新批次继续单列，不能由调度器mock外推完整预算PASS。
