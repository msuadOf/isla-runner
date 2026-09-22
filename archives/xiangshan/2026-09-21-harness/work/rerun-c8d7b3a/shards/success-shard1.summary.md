# success-shard1 运行摘要

- 数据源: `work/rerun-c8d7b3a/shards/success-shard1.ndjson`(2700 条,Retire_Success 输入)
- 状态: **完成**(log 末行 `shard 1 完成`,进程已退出,ndjson 2700/2700)
- 运行时段: 04:53 重启后至 14:10 完成(jobs=4, timeout=60s;首轮 04:29 启动的 jobs=8/timeout=30 进程组于 04:52 被外部终止,其约 130 条记录被覆盖作废)

## 总体计数

| 指标 | 数量 | 占比 |
|---|---|---|
| 总条目 | 2700 | 100% |
| category=success | 741 | 27.4% |
| category=failure | 1959 | 72.6% |

failure 细分(无独立 timeout/abort category,按 diffs/elapsed/returncode 判定):

| 细分 | 数量 | 判据 |
|---|---|---|
| timeout | 1816 | diffs 为空且 elapsed≈60s |
| vr-sync-polluted | 38 | diffs 全为 `v\d+_(low|high)`(新 emu vr 同步缺陷) |
| 其余失败 | 105 | 见下 |

其余失败 105 = 含非 vr 字段 diff 83 + emu 非零退出(diffs 空,rc=1,非 60s)22。

## vr-sync-polluted top5 指令

1. vsaddu.vv v31, v0, v0, v0.t (3)
2. vwsubu.vx v16, v12, x0, v0.t (2)
3. vmulh.vx v0, v0, x0 (1)
4. vslide1up.vx v2, v0, x0, v0.t (1)
5. vnclip.wv v31, v31, v31, v0.t (1)

## timeout top5 指令

1. vmerge.vxm v31, v0, x0, v0 (10)
2. vandn.vx v0, v0, x31 (9)
3. vclmulh.vx v0, v0, x0, v0.t (9)
4. vclmul.vx v0, v0, x0, v0.t (9)
5. vfmv.v.f v0, f0 (7)

## 非 vr 失败 top5 指令

1. vrol.vx v0, v0, x31 (7)
2. vror.vx v0, v0, x31 (5)
3. vandn.vv v0, v0, v0 (4)
4. vror.vv v0, v0, v0 (4)
5. vrol.vx v0, v0, x0 (3)

## 非 vr ABORT 样例 3 条

1. **case-1089** `vnclip.wv v11, v8, v31, v0.t` — diff 字段含 `vcsr`、`vxsat`(饱和标志 CSR 未同步,另含 v11_low/high)
2. **case-1385** `vwredsum.vs v0, v24, v0` — diff 字段含 `mcause`、`mode`、`mstatus`、`mtval`(陷入异常类差异)
3. **case-261** `vmv.v.x v0, x0` — diffs 空、rc=1、elapsed 30.9s,emu 非零退出(崩溃类,非 diff)

## 结论

failure 主要成分为 timeout(占 failure 92.6%),真 diff 失败仅 121 条,其中 38 条为已知 vr 同步缺陷污染;非 vr 真异常集中在 vnclip/vnclipu 饱和(vcsr/vxsat)、vwredsum 异常寄存器、以及 vrol/vror/vandn 位运算指令,值得后续单独排查。
