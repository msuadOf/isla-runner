# 浮点向量合法性 guard 严格布尔聚合消融

## 结论

在完成的窄域完整 Clause 中，A（当前严格布尔聚合）比只恢复对应短路判断的 B 快约 0.20–1.20 秒中位数，但 B 生成更多**非法原因分区的见证**；退休例数不变。宽域 `FVVTYPE` 的 A/B_normal 各三次均撞 60 秒外限，无最终 JSON，不能计算该域加速比，也不能据窄域推断全向量初态域。建议暂不据本次数据自动回退或宣称严格布尔的全域收益；若验收目标要求每个拒绝原因分别出现在生成集合，应改进条件见证或再讨论恢复对应短路。

## 固定边界与装配

- 基线为根 float `1c7a354`、Isla `80231ce9`、冻结模型 `9c339044`。`A`、`B_valid`、`B_normal`、`B_reduction` 各自保存完整模型副本、源哈希清单和 [最小源 diff](B_valid/source.diff)；另两份 diff 在 `B_normal/source.diff`、`B_reduction/source.diff`。[源边界核对](source-boundary-check.json)证实原 166 个模型文件来自干净的 `9c339044`，A 未变、每个 B 只改 `vext_fp_utils_insts.sail` 中一个函数；`eq_anything`、异常、状态更新、`nan_unbox` 的显式 `if` 均未改。`valid_fp_standard_op` 保持原样。
- 四臂均由同一 Sail 0.20.1（`f4f8e458`）、同一插件与带注释的 RV64/V128/E64 JSON 严格生成完整 IR；命令、日志、退出、源/工具/IR 哈希见各臂的 `ir/generation-*.json` 和 [summary.json](summary.json)。生成不计入求解时间。插件 SHA-256 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`；运行器 SHA-256 `e9fd5a0bba97c736e88f2bb06f3d46c542de0f10744b9d644b38731ffa279204`。
- [IR 定义核对](ir-definition-check.json)：四臂均有 2053 个函数定义；去掉 IR 调试源码位置和未改断言的位置字符串后，三个 B 与 A 分别只改变 `zvalid_fp_op`、`zillegal_fp_normal`、`zillegal_fp_reduction`。这只忽略位置元数据，不忽略控制流或运算定义。
- 每项先同条件预热 A/B，正式顺序 `A/B/B/A/A/B`（即 AB/BA/AB），各三次。CPU 限于 56–59，`-T 1`，外限 60 秒、路径 30 秒、SMT 单次 10 秒；Z3 库路径见每次原始命令。无采样、路径配额或操作数具体化。真实 fork 总数没有可靠口径，记为**未知**。RSS 是 `/usr/bin/time` 的单次最大驻留集。

## 完整 Clause 结果

表中时间为秒、RSS 为 MiB；每格写正式三次的**中位数 [最小, 最大]**。`gen/退休/非法` 三次均相同。所有完成的 JSON 都报告 `status=finished`、错误/SMT 超时/未完路径为 0，但自身的 `model-coverage=not-measured`，故不把生成集合当成全部模型行为。

| 函数与 Clause、初态域 | 臂 | 墙钟 | 用户 CPU | 系统 CPU | RSS | gen/退休/非法 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `valid_fp_op`；`FVVTYPE`；SEW32、LMUL1、vl1、vstart0 | A | 7.825 [7.825, 8.227] | 6.677 [6.675, 7.071] | 1.010 [0.975, 1.054] | 251.4 [249.9, 251.5] | 27/18/9 |
| 同上 | B_valid | 9.028 [8.827, 9.428] | 7.415 [7.227, 7.720] | 1.442 [1.440, 1.487] | 251.5 [249.9, 251.6] | 54/18/36 |
| `illegal_fp_normal`；`FVVTYPE`；SEW32、LMUL1、vl1、vstart0 | A | 8.126 [8.025, 8.326] | 7.017 [6.978, 7.240] | 0.979 [0.955, 1.004] | 250.5 [250.0, 252.1] | 27/18/9 |
| 同上 | B_normal | 8.827 [8.426, 8.927] | 7.484 [7.090, 7.549] | 1.206 [1.205, 1.210] | 250.9 [250.7, 251.9] | 36/18/18 |
| `illegal_fp_reduction`；`RFVVTYPE`；SEW32、LMUL1、vl1、vstart0/1 | A | 4.321 [4.321, 4.521] | 3.728 [3.700, 3.887] | 0.529 [0.525, 0.562] | 248.2 [248.1, 249.4] | 12/8/4 |
| 同上 | B_reduction | 4.521 [4.521, 4.621] | 3.865 [3.847, 3.890] | 0.590 [0.579, 0.616] | 249.0 [248.9, 249.5] | 16/8/8 |

各臂使用同一对照域的 [配置](context_vl1.toml) 或 [归约配置](context_reduction.toml)，向量元素与寄存器输入仍符号化，FRM 未固定。`valid` 的 SEW32 主测不能衡量 SEW8 的短路收益；`normal` 主测的 vill 恒为 0；归约测量中 vstart0/1 两侧可达。非法返回都为 `Illegal_Instruction(())`，其它异常为 0。单次命令、退出码、逐次 wall/user/sys/RSS、配置/IR/日志哈希和完整输出 JSON 在 `runs/`；机器表见 [summary.json](summary.json)。

### 拒绝原因见证

以下是每臂首个正式运行的互斥分组，重复运行计数一致。普通 Clause 的两个布尔原因是 `FRM∈{5,6,7}` 与 `vm=0 且 vd=0`；归约用 `vstart≠0` 替代目的寄存器原因。两原因理论上可同时成立，因此单独列出交集；这不是把两个计数简单相加。

| Clause 与对照 | 臂 | 只因 FRM 保留 | 只因第二原因 | 两因同时 | 退休 |
| --- | --- | ---: | ---: | ---: | ---: |
| `FVVTYPE` / valid | A | 8 | 1 | 0 | 18 |
| `FVVTYPE` / valid | B_valid | 27（FRM 5/6/7 各 9） | 9 | 0 | 18 |
| `FVVTYPE` / normal | A | 8 | 1 | 0 | 18 |
| `FVVTYPE` / normal | B_normal | 9 | 9 | 0 | 18 |
| `RFVVTYPE` / reduction | A | 0 | 1 | 3 | 8 |
| `RFVVTYPE` / reduction | B_reduction | 4 | 4 | 0 | 8 |

例如 B_normal 的 `vm=0, vd=0, FRM=0` 和 `FRM=5, vm=1` 各有 9 条非法见证；A 也各有见证，但分别只有 1 与 8 条。B_valid 把 FRM 5/6/7 分开，各有 9 条。归约 A 的四条非法中三条同时含 vstart=1 与保留 FRM；B 分开生成两组各四条。具体指令编码、fcsr、vtype、vstart 和互斥分组见 [summary.json](summary.json) 中 `first_run_reason_witness`。生成数增加表示路径分区及选解改变，不能单凭此断言 A 的语义有误或 B 覆盖了全部取值。

## 宽域、补充域和限制

- 首先冻结的 [宽域](context.toml) 固定 LMUL1、vl2，保留 SEW8/16/32/64 与 vstart0/1，元素仍符号化。完整 `FVVTYPE` 的 A/B_normal 预热及正式各三次全部触及外限，均无最终 JSON。墙钟中位数都约 60.10 秒，仅是外限观测；实际完成时间未知，60 秒为下界。gen、退休、非法与真实 fork 均未知。此域结论为**超时无法判断**。
- 超时后追加的窄域完整 Clause 把 SEW 固定 32、vl 固定 1，以保留活动元素而缩小向量上下文。另一个 `vl=0` 普通 guard 对照三次 A 27/18/9、B_normal 36/18/18，墙钟中位数 8.527 与 8.928 秒，作为辅助证据，不替代 vl1 主表。
- `valid_fp_op` 的 SEW8/32 扩域 [配置](context_sew8_32.toml) 固定 vl0，也按完整 AB/BA/AB 跑完：A 墙钟 42.976 [42.277, 43.574] 秒、B_valid 45.579 [44.977, 45.580] 秒，三次均 finished，仍为 27/18/9 与 54/18/36。**输出见证的 vtype 全是 SEW32**；`FVVTYPE` 的编码条件过滤 SEW8，故该补测不能判断 SEW8 拒绝原因。虽输入配置允许 SEW8，也不能把未出现当成该 guard 未接受或求解错误。
- 这些窄域完成值说明当前严格聚合在已测条件下有小幅性能收益，同时压缩了非法原因分区。不能将此小幅差异外推到广域、其它 Clause 或 `eq_anything` 主动求解；后者本轮完全未改、未独立测量。

复现入口为 `setup.py`（仅用于重建空目录）、`verify_ir.py`、`measure.py` 与 `summarize.py`。已生成的源副本、IR、命令日志、逐次 JSON 和哈希保留在本目录。没有改生产模型、生产 IR、源码分支或其它组文件。
