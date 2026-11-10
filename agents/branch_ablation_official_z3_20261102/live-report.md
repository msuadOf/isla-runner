# 新官方 Z3 控制变量消融

当前：队列 0、运行中 0、成对完成 42、失败 0；已写出 84/84 条正式单臂记录。

14 个完整 Clause 工作负载各三对 AB/BA/AB，种子依次 17/29/43。最多 12 对同时运行，各对两臂固定同一物理 CPU、`-T 1`、qffp、显式 `--smt-timeout 7200s`，进程外限 7200 秒。没有更短路径预算或额外长预热。

官方运行器、Z3 库、seed 拦截器和输入哈希、IR 目标函数差异见 [launch.json](launch.json) 与 [input-verification.json](input-verification.json)。真实 seed 拦截 pilot 见 `pilot/seed-a/intercept.log`；每次正式运行的独立拦截日志、命令、时间、原始 JSON 在 `runs/<workload>-pairN/<arm>/`。

本轮与先前 qfaufbv/60 秒结果分开。两臂未完成或条件见证不同，不给等覆盖加速比；fork 无可靠全局口径，记未知。

## 已完成工作负载

下表仅对两臂各三次自然完成的工作负载给出中位墙钟和范围；类别差异按三次目标条件见证计数。

| 工作负载 | A 墙钟秒 中位 [范围] | B 墙钟秒 中位 [范围] | A/B gen 中位 | 目标条件类别差异 |
| --- | ---: | ---: | ---: | --- |
| flags-compare | 34.33 [24.16, 39.58] | 43.91 [43.60, 52.17] | 10/16 | fflags:changed:NVTrue: 3→18；fflags:same:NVFalse: 27→30 |
| minmax | 33.84 [22.40, 57.57] | 60.31 [57.48, 60.72] | 20/36 | NaN:finite/nan: 0→6；NaN:nan/finite: 0→6；NaN:nan/nan: 0→6；NaN:nan/zero: 0→6；NaN:zero/nan: 0→6；finite_eq: 0→1；finite_gt: 0→1；finite_lt: 0→6；zero_pair:0/0: 24→18；zero_pair:0/1: 0→6；zero_pair:1/0: 0→6；zero_pair:1/1: 0→4 |
| minm | 9.12 [8.52, 17.63] | 14.22 [9.63, 20.12] | 4/5 | NaN:nan/nan: 0→3 |
| maxm | 7.97 [7.03, 9.14] | 12.05 [9.64, 15.37] | 4/5 | NaN:nan/nan: 0→3 |
| mask | 32.12 [27.56, 53.92] | 48.91 [28.46, 54.85] | 27/54 | masked_active_only: 0→27；masked_mixed: 0→54 |
| reduction | 8.02 [7.42, 9.42] | 12.02 [9.63, 14.43] | 12/24 | masked_active_only: 0→12；masked_mixed: 0→24 |
| nan | 12.63 [10.93, 18.94] | 160.78 [92.05, 187.92] | 26/36 | result_finite: 0→26；result_infinity: 0→1；result_nan: 30→60；result_zero: 30→3 |
| class | 1445.16 [1202.15, 1517.79] | 1444.04 [1325.32, 1645.57] | 310/508 | class_bit_0: 0→33；class_bit_1: 0→30；class_bit_2: 0→47；class_bit_3: 0→30；class_bit_4: 3→32；class_bit_5: 0→47；class_bit_6: 0→30；class_bit_7: 0→30；class_bit_8: 0→49；class_bit_9: 0→32；class_other_0x0: 3→240 |
| guard-valid | 23.73 [17.45, 27.46] | 26.84 [22.64, 36.18] | 27/54 | FRM5|masked_vd0=False|vstart_nonzero=False|vill=False: 0→27；FRM6|masked_vd0=False|vstart_nonzero=False|vill=False: 0→27；FRM7|masked_vd0=False|vstart_nonzero=False|vill=False: 0→27；FRM7|masked_vd0=True|vstart_nonzero=F…（详见 summary.json） |
| guard-normal | 41.88 [26.15, 48.09] | 33.75 [26.84, 42.07] | 27/36 | FRM5|masked_vd0=False|vstart_nonzero=False|vill=False: 0→6；FRM6|masked_vd0=False|vstart_nonzero=False|vill=False: 0→3；FRM7|masked_vd0=False|vstart_nonzero=False|vill=False: 0→18；FRM7|masked_vd0=True|vstart_nonzero=Fal…（详见 summary.json） |
| guard-reduction | 10.04 [9.35, 19.43] | 12.02 [11.12, 15.85] | 12/16 | FRM6|masked_vd0=False|vstart_nonzero=False|vill=False: 0→6；FRM7|masked_vd0=False|vstart_nonzero=False|vill=False: 12→6；FRMok|masked_vd0=False|vstart_nonzero=True|vill=False: 0→12 |
| guard-normal-wide | 730.97 [367.84, 796.02] | 659.55 [525.34, 826.43] | 81/108 | FRM5|masked_vd0=False|vstart_nonzero=False|vill=False: 0→12；FRM5|masked_vd0=True|vstart_nonzero=False|vill=False: 14→0；FRM6|masked_vd0=False|vstart_nonzero=False|vill=False: 0→19；FRM6|masked_vd0=True|vstart_nonzero=Fa…（详见 summary.json） |
