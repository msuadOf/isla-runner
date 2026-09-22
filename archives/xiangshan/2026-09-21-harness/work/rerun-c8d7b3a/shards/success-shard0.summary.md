# success-shard0 重跑监控报告

- 状态: **完成**（log 出现 `shard 0 完成`, 2026-09-19 14:16）
- 数据: `success-shard0.ndjson`, 2700 条, 按 id 去重后 2700(无重复行)
- 进程: 877707, 参数 `--shard 0 --shards 4 --jobs 4 --timeout 60`, 04:53 启动 → 14:16 结束(约 9.4h)

## 总体计数

| category | 数量 | 占比 |
|---|---|---|
| success (HIT GOOD TRAP) | 729 | 27.0% |
| failure | 1971 | 73.0% |

failure 细分:

| 类型 | 数量 | 说明 |
|---|---|---|
| timeout (returncode=None, 60s 超时) | 1882 | 绝对主体 |
| vr-sync-polluted | 16 | diffs 全为 `v\d+_(low\|high)` |
| 其余 abort (非 vr 字段) | 73 | 见下 |

## vr-sync-polluted (16 条, 已知 emu vr 同步缺陷)

top5 指令: vslide1up.vx(2), vaadd.vx(2), vwsubu.vx(2), vslidedown.vi(1), vrgather.vi(1)

## 其余 abort (73 条, 非 vr 字段)

top5 指令: vwsll.vx(13), vwsll.vi(7), vrol.vx(6), vwsll.vv(6), vror.vx(5)

结构: 55 条有 diff 行(53 条为 mode/mstatus/mtval/mcause 四件套 = trap 行为差异; 2 条 vtype), 18 条无 diff 行(emu 非零退出)。

### 非 vr 字段 ABORT 样例 3 条

| id | 指令 | diff 字段 |
|---|---|---|
| case-1392 | vwredsumu.vs v0, v24, v0, v0.t | mode, mstatus, mtval, mcause |
| case-1600 | vandn.vv v0, v0, v0 | mode, mstatus, mtval, mcause, v0_low |
| case-1636 | vandn.vx v0, v0, x0 | mode, mstatus, mtval, mcause |

## 监控过程事件

- 04:38 首轮启动(jobs=8, timeout=30); 04:41 外层重启一次; **04:52-04:53 外层全量重启并清空 ndjson, 参数改为 jobs=4/timeout=60**(监控起点前的 122 条旧结果被覆盖, 本报告基于重启后全量数据)。
- 全程速率 ~4.5 条/分钟, 无进程异常死亡。

## 结论

- 已知 vr 同步缺陷影响仅 16/2700 (0.6%), 非 vr 类 ABORT 73 条 (2.7%), 真实通过率 27%。
- 最大失分项是 timeout(1882 条, 69.7%), 其量级远超字段差异类失败, 与 emu 仿真速度/挂死相关, 建议优先排查。
