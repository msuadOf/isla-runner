# `accrue_fflags` 条件状态更新消融

本报告的算术 Clause 结论仅适用于每臂外限 60 秒、路径预算 30 秒、SMT operation 预算 10 秒。用户已要求按每臂两小时总预算重测原超时项；独立实验及后续结论见 [两小时实验](budget-2h/report-2h.md)。两轮预算不同，不能直接比较墙钟或复用本轮超时判断两小时结果。

## 结论

在完整 `FLEQ_S` Clause 上，恢复条件状态更新的显式 `if` 使输出从 10 条增至 16 条；新增的 6 条均见证浮点异常标志由 0 变为 `NV=0x10`。当前 ITE 臂在本轮三次中都只生成标志不变的见证。真实标量算术 `F_BIN_RM_TYPE_S` 中，ITE 三次均在约 52 秒完成，显式 `if` 三次均触及 60 秒外限、没有最终 JSON。**合并确有固定预算下的可完成性收益，同时损失默认生成集合中的新 flags 见证**。两臂输出不同且算术显式臂被删失，不能换算等覆盖加速倍数。建议将此项标为“有预算收益、有覆盖代价”，不作无条件自动回退；若默认输出必须直接见证新 flags，应恢复显式分支并接受算术 Clause 当前的超时，或者为 ITE 的 `changed` 条件增加两侧定向见证后重新验证。生产模型未改。

## 控制变量与来源

- 基线为根 float `1c7a354`、Isla `80231ce9`、模型 `9c339044`，`nan_unbox` 维持已恢复的显式 `if`。A 的 166 个模型源文件、插件、配置与现行完整 IR 的生成清单逐项哈希相同，复用交付 IR `10bea88c…bbf`；B 从冻结的完整模型严格新生成，耗时 **372.63 秒**，IR `c450a442…f09`。编译选项、文件哈希和命令见 [A 来源清单](A/source-manifest.json)、[B 来源清单](B/source-manifest.json)、[B 生成报告](B/ir/generation-rv64d_flags_if.json)及[变体清单](variant-manifest.json)。
- [最小源差异](variant.diff)仅把 `mstatus.bits = ite(changed, dirty.bits, mstatus.bits)` 改为 `if changed then mstatus.bits = dirty.bits`。`fcsr` 赋值、`strict_or_bool` 断言、`Ext_F` 分支、`csr_write_callback` 的位置与次数，以及 `FS/SD` 的 Dirty 值均保持。两臂使用相同的 `not_bool(eq_anything(old, f))`，**本实验不衡量** `eq_anything` 相对 `neq_bits` 避免主动查询的收益。非 SYMBOLIC 体未变。
- 两份完整 IR 仅 `zaccrue_fflags` 函数内两处文本差异；两臂均有一次 `zeq_anything(B5)`，无 `zneq_bits`，B 比 A 多一个条件 Jump。[IR 结构计数](ir-structure.json)、[完整逐行差异摘要](ir-diff-summary.json)。固定二进制 SHA-256 `e9fd5a0b…204`，固定 FD 配置 SHA-256 `20851fdb…0d0`，相同 `-T 1 --timeout 30s --smt-timeout 10s --tastic qfaufbv`。`taskset -c 40-43`，外限 60 秒；A/B 各预热一次后按 AB/BA/AB 顺序运行。命令和输出由 [探针脚本](probe.py)保留。

## 完整 Clause：`FLEQ_S`

三次正式运行均自然退出 0，`summary.status=finished`；两臂 `errors`、`execution-timeouts`、`smt-timeouts`、`unfinished-paths`、`sampled-paths`、`omitted-cases` 均为 0。下表为三次中位数与范围；资源由 `/usr/bin/time` 逐次记录。原始结果见 [记录](runs/FLEQ_S/records.json)，每轮目录内含命令、日志与 JSON。

| 臂 | 墙钟秒，中位（范围） | 用户 CPU 秒，中位（范围） | 系统 CPU 秒，中位（范围） | 最大 RSS KiB，中位（范围） | gen / 退休 / 非法 | 新 flags / 不变 flags 退休见证 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A：ITE | 4.621（4.421–4.621） | 4.04（3.81–4.05） | 0.51（0.49–0.52） | 232,924（232,780–235,612） | 10 / 10 / 0 | 0 / 10 |
| B：显式 if | 6.324（6.324–6.424） | 5.54（5.53–5.68） | 0.74（0.72–0.77） | 231,880（231,016–234,652） | 16 / 16 / 0 | 6 / 10 |

两个源寄存器的 boxing 组合在两臂均有见证。B 多出的异常标志见证包含 `fleq.s x0, f31, f31`，输入 `f31=0xffffffff7fa00000`（信号 NaN），`fcsr: 0→0x10`，`mstatus: 0x6600→0x8000000000006600`；见 [B 第一次正式 JSON](runs/FLEQ_S/r1_B/output/rv64_zFLEQ_S.json)。本配置的初始 `FS=Dirty`、`SD=0`、旧 `FFLAGS=0`；新增 flags 时 `FS` 继续 Dirty、`SD` 置 1，不变 flags 时维持初态。A 本轮没有新增 flags 见证，不表示该条件在 ITE 模型中不可达；旧非同条件单次测试曾得到一条，此处只评价本轮受控生成集合。`summary.model-coverage=not-measured`，不能把生成条数当成完整模型覆盖率。

真实全局 fork 数未由固定 `isarch` 二进制或 JSON 可靠输出。日志中的每个叶路径累计 `frame.forks()` 会重复计算共同前缀，因此不相加；此项标记未知，以 IR Jump 数和完成路径数分别说明结构与结果。

## 真实标量算术补充：`F_BIN_RM_TYPE_S`

同一配置和预算下，A 三次均自然退出 0，`summary.status=finished`，其错误、路径超时、SMT 超时、未完成、采样和省略计数均为 0；每次生成 208 条，其中 160 条退休、48 条非法，退休中 10 条新 flags、150 条不变 flags。A 墙钟中位 **52.288 秒**（51.887–53.587），用户 CPU 中位 48.52 秒（48.22–49.81），系统 CPU 中位 4.24 秒（4.11–4.24），最大 RSS 中位 269,976 KiB（267,288–270,820）。旧 `FFLAGS=0` 且初始 `FS=Dirty`、`SD=0`；10 条新 flags 见证相应更新 `fcsr`。该算术 Clause 还写 FPR，因此即使 flags 不变，FPR 写回也会把 `SD` 置 1；不能用其最终 `SD` 区分 `accrue_fflags` 条件两侧。前述 `FLEQ_S` 不写 FPR，其 `SD` 变化才直接对应此条件。

B 三次均由 60 秒外限终止，返回 **124**，没有最终 JSON，因此 gen、退休、非法、最终 `summary` 和 flags 两侧见证数均**未知**。三次日志各记录 5 次 `CheckSatAssuming` 的 10 秒 SMT operation 超时诊断；外限并非模型执行完整结论。B 墙钟观测为 60.196 秒（60.195–60.198），均为**下界／删失值**，不用于计算速度比。外限终止了其内部 `/usr/bin/time` 包装，未写出用户/系统 CPU 与最大 RSS，这三项也标未知。原始 [记录](runs/F_BIN_RM_TYPE_S/records.json)、[A 第一次正式 JSON](runs/F_BIN_RM_TYPE_S/r1_A/output/rv64_zF_BIN_RM_TYPE_S.json)、[B 第一次正式日志](runs/F_BIN_RM_TYPE_S/r1_B/run.log)与逐轮 `result.json` 保留。此补充表明在固定 60 秒预算内 A 能完成而 B 不能；由于 B 无完整输出，不能推断其最终生成集合或等覆盖性能。

机器可读的全部运行结果与限制见 [summary.json](summary.json)。
