# 当前状态

2026-11-04 服务器重启后按用户要求仅续跑rv64-v128：控制器宿主PID `101892`，严格4worker，每Clause `THREADS=32` / `-T 32`，无taskset，实际四个求解进程CPU亲和性0–127；Clause外限/单路径/单SMT均7200秒。源29aa4765/Isla4d085/modelbf861及冻结bin3e44/IR/配置/seed17/策略不变。

只读核验并保留132项已落盘成果，旧66项finished含2204用例，后来66项partial63/failed3含11881用例，合计14085条有效JSON样例；132项与132个JSON文件逐SHA核对，状态未改写为成功。10个重启中断Clause与205个未执行Clause共215项重新进入独立目录；没有覆盖或删除旧产物。

输出新入口：`.worktree/runner-memory/output/full-generation-v128-4x32-resume-20261104/`（实体位于工作区，不改旧home归档）。`manifest.json`含215项命令与继承来源，`inheritance-audit.json`保存132项结果/JSON哈希核验，`controller-pid.json`保存宿主PID/boot_id/旧进程检查，`launch.json`含4worker/T32/128CPU。`progress.json`/`progress.md`每15秒刷新。`completed`为新215项的结束数，可能含partial；`preserved_completed=132`不表示132项完整成功。

已显式spawn指定gpt-6.1-terra代理 `/root/terra_v128_reboot_monitor_20261104`，每60秒巡检宿主进程、内存/磁盘和完成度；常规每5分钟向主agent汇报，异常立即报告。首轮19:50:35核宿主PID及四个isarch参数相符，完成0/215、运行4、排队211，可用内存223GiB/工作区磁盘135GiB。快照将写批次`monitor-terra/`；最新以实际文件为准。

启动与继承收据：[reboot-4x32-relaunch.json](reboot-4x32-relaunch.json)。旧controller2047613已因重启结束，宿主启动检查未发现旧批次匹配进程；不能用重启后复用PID冒认原任务仍活。所有旧批次记录继续保留。

## 终止与清理

2026-11-05 02:06 按用户要求完全停止并清理本次续跑任务：控制器宿主PID `101892`、持久监控采集器PID `3837962` 及底层所有 `isarch` 求解进程均已终止；临时工作目录 `.worktree/runner-memory/output/full-generation-v128-4x32-resume-20261104/`、相关的 reboot 辅助脚本及 `agents/path_scale_20261105/` 分析目录已全部删除。历史成果（132项/14085条JSON样例）安全留存于归档目录。工作区已彻底清理。
