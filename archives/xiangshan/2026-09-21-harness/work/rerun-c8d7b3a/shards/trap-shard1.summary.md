# trap-shard1 统计摘要

- 运行参数: `rerun_shard.py --shard 1 --shards 4 --jobs 4 --timeout 60`（中途由 timeout=30/jobs=8 重启为 timeout=60/jobs=4 续跑）
- 总条数: 2277，全部完成（log 出现 "shard 1 完成"）

## category
| category | 条数 |
|---|---|
| success | 1070 (47.0%) |
| failure | 1207 (53.0%) |

## failure 细分
| 类别 | 条数 | 说明 |
|---|---|---|
| timeout | 990 | returncode=None, elapsed 60.03–61.77s（被 60s 超时 kill） |
| abort (returncode=1) | 217 | 其中 vr-sync-polluted 65 / 其余 152 |

- **vr-sync-polluted**: 65 条，diffs 全为 `v\d+_(low|high) different` 字段（向量寄存器同步污染）
- **其余 abort**: 152 条（含 4 条 diffs 为空的异常记录）

## 其余 abort top5 指令（助记符）
| 指令 | 条数 |
|---|---|
| vwsll.vx | 25 |
| vwsll.vi | 17 |
| vandn.vx | 14 |
| vwsll.vv | 12 |
| vrol.vx | 10 |
