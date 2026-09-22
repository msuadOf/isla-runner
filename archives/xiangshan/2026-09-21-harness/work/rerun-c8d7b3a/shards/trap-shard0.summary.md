# trap-shard0 重跑统计

- 数据源: `work/rerun-c8d7b3a/shards/trap-shard0.ndjson`
- 运行参数: `--shard 0 --shards 4 --jobs 4 --timeout 60`
- 状态: **完成**(log 出现 "shard 0 完成",2278/2278)
- 备注: 过程中进程重启过两次(jobs 8→4,timeout 30→60),ndjson 以最终重跑为准

## 总览

| 指标 | 数量 |
|---|---|
| 总条目 | 2278 |
| success | 1036 |
| failure | 1242 |

failure 细分(1242 = 1046 + 68 + 128):

| 类别 | 判定条件 | 数量 |
|---|---|---|
| timeout | `returncode == null` | 1046 |
| vr-sync-polluted | failure 且 diffs 非空且全部为 `v\d+_(low\|high)` 形式 | 68 |
| 其余 abort | failure 且非上两类 | 128 |

## abort Top5 指令(按 mnemonic)

| mnemonic | 条数 |
|---|---|
| vwsll.vx | 23 |
| vwsll.vi | 14 |
| vwsll.vv | 13 |
| vror.vx | 12 |
| vrol.vx | 10 |

abort 样例(前 10):

- case-1336 `vnclipu.wi v8, v24, 0x9, v0.t`(6 处 diff)
- case-1692 `vnclip.wv v0, v0, v27`(3)
- case-1720 `vnclipu.wv v0, v0, v20`(4)
- case-1768 `vnclipu.wv v28, v0, v0`(4)
- case-1792 `vnclipu.wv v4, v28, v0, v0.t`(5)
- case-1800 `vnclipu.wv v31, v6, v22, v0.t`(4)
- case-2504 `vandn.vv v13, v0, v4, v0.t`(5)
- case-2516 `vandn.vv v0, v0, v0`(6)
- case-2536 `vandn.vv v11, v17, v0, v0.t`(4)
- case-2572 `vandn.vv v0, v0, v0`(6)

## vr-sync-polluted 样例

case-616、case-1196、case-1216、case-1244、case-1260 等(diff 形如 `v2_low different at pc = ...`)。
