# min/max 结果选择消融（2026-10-31）

**结论：当前 ITE 在完整 `F_BIN_TYPE_F_S` 中有可复测的时间收益，也减少了默认生成的条件见证。** 三对 AB/BA/AB 中，A（ITE）墙钟中位数 5.51 秒，B（显式 `if`）12.82 秒；两臂均自然完成。A 仅生成 20 条、B 生成 36 条退休见证，差异全部来自 FMIN.S/FMAX.S（各 4→12），因此时间差不能解释为“相同覆盖量下加速 2.33 倍”。B 见证了正常有限数的两种大小关系及 `-0/+0` 两种次序，A 在本配置的自然生成结果中未见证这些条件。建议在当前生成器没有条件见证补充机制前恢复这两处显式选择；若保留 ITE，需先给出等价条件见证和同等覆盖量下的性能验收。

## 边界与变体

- A：根 float `1c7a354`、Isla `80231ce9`、模型 `9c339044` 的现行完整 IR；`nan_unbox` 已是 `if`。A IR SHA-256 `10bea88ca9bc2938cc9f8d303fc3f851c0a256a31ef894bd84d5c7e2e8142bbf`，与 `isla/ir/provenance/manifest.json` 的 RV64D/V128/E64 条目及模型 `fp_minmax.sail` 哈希一致。
- B：从上述模型冻结 166 个文件，仅修改 `extensions/FD/fp_minmax.sail` 中 `fp_min_pure`、`fp_max_pure` 的六层结果选择：相同条件、相同顺序、相同结果臂，从 ITE 换为 `if` 链。`riscv_f{16,32,64}Lt_quiet`、`ieee_is_nan`、零检测、`strict_and_bool`、`accrue_fflags` 与底层数值后端均保持原样。A 源文件 SHA-256 `547156c7…e32a`，B `d24bea03…e986`；最小差异见 [source.diff](source.diff)，166 文件哈希核对见 [variant.json](variant.json)。
- B 使用相同冻结 Sail 0.20.1 工具链、插件、`isla/ir/provenance/rv64d.json` 与严格 SYMBOLIC 参数，从冻结模型完整生成；命令、退出 0、363.22 秒和 IR SHA-256 `33563af6c675db0040077b0e339345ce11c1e45fdb657c3340120a19f2a41c3b` 见 [generation.json](B/generation.json)。两份 IR 均 2053 函数，无增删；剥除源码位置后，仅 `zfp_min_pure`、`zfp_max_pure` 两函数体变化，见 [ir-comparison.json](ir-comparison.json)。`fp_minm_pure`、`fp_maxm_pure` 的附加 NaN ITE 函数体未变。

## 完整 Clause 结果

同一 `isarch` SHA-256 `e9fd5a0b…9204`、FD TOML SHA-256 `20851fdb…23d0`，CPU 44–47、线程 1、`qfaufbv`、`LD_LIBRARY_PATH=/home/linuxbrew/.linuxbrew/opt/z3/lib`。未固定操作数或寄存器，未启用采样/分叉配额。每臂先预热，正式三对 AB/BA/AB；单次外限 60 秒、路径 30 秒、SMT 10 秒。生成时间不计入下表。表中时间为三次中位数（范围），RSS 为最大驻留内存中位数；所有退出码均 0，JSON `status=finished`、`errors=0`、内部/SMT 超时 0、`sampled-paths=0`、`unfinished-paths=0`，`model-coverage=not-measured`。

| Clause | 臂 | 墙钟秒 | 用户 CPU 秒 | 系统 CPU 秒 | RSS KiB | 实际 fork | gen / retire / illegal |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `F_BIN_TYPE_F_S` | A | 5.510 (5.510–5.510) | 4.71 (4.65–4.73) | 0.81 | 232944 | 39 | 20 / 20 / 0 |
| `F_BIN_TYPE_F_S` | B | 12.816 (12.716–13.116) | 11.43 (11.36–11.56) | 1.46 | 241568 | 71 | 36 / 36 / 0 |
| `FMINM_S` | A | 1.807 | 1.41 | 0.33 | 229680 | 7 | 4 / 4 / 0 |
| `FMINM_S` | B | 4.609 (4.509–4.611) | 3.95 | 0.59 | 232760 | 23 | 12 / 12 / 0 |
| `FMAXM_S` | A | 1.807 | 1.46 | 0.32 | 229420 | 7 | 4 / 4 / 0 |
| `FMAXM_S` | B | 4.708 (4.609–4.709) | 4.02 | 0.60 | 232648 | 23 | 12 / 12 / 0 |

实际 fork 从 `-D f` 日志计数：每次 SAT 双臂可行后的一条源码位置 `[FORK]` 日志计一次，排除紧随的 taint 描述。首轮对应原始日志中 A/B 分别有 78/142 条 `[FORK]` 行，恰是 39/71 条事件和各自 39/71 条 taint 行；不把静态 Jump 数当 fork。`FMINM_S` 与 `FMAXM_S` 测到的是两者共享的 `fp_min_pure`/`fp_max_pure` 差异，**不能**将其 4→12 条归因于未变的附加 NaN ITE。

`F_BIN_TYPE_F_S` 的 FSGNJ 三种操作在两臂各 4 条；FMIN.S/FMAX.S 在 A 各 4 条、B 各 12 条。按输入分类的每次见证，A 的 min/max 共：单侧 NaN 4、双侧 NaN 2、双零 2；B：单侧 NaN 8、双侧 NaN 8、双零 4、正常有限数 `op1<op2` 2、`op1>op2` 2。B 的双零包含 `-0/+0` 与 `+0/-0` 各 2 条；A 只见 `+0/+0`。B 另见源 sNaN 和正常有限数与 NaN 混合。上述是**生成见证覆盖**，不是代码语义差异或完整输入域覆盖证明。默认生成器每条合并的符号路径只取有限见证，A 的缺项可由 ITE 合并与取解策略解释。

## 独立修改意见与未测项

当前 ITE 的完整 Clause 运行时间收益有证据，但伴随可直接观察的正常数、零符号条件见证缺口。按仓库 `specs/GOAL.md` 的控制流取舍口径，我建议恢复 `fp_min_pure`/`fp_max_pure` 的显式选择，或先让生成器对每个合并条件取到两侧见证，再重新比较相同见证口径下的时间。此报告只提供隔离变体和建议，没有改生产模型。

`fp_minm_pure`/`fp_maxm_pure` 最后一层“任一 NaN → canonical NaN”的 ITE 已另用独立 C 变体消融，见下节。F16/F64、向量调用点、更多初态域与硬件回放未测；本结论只适用上述 RV64D/V128/E64 Clause 及配置。原旧标量 fixture 的 1566→12 历史数字未用于本轮时间结论。

可复核入口：[生成脚本](generate.py)、[运行脚本](run.py)、[汇总脚本](summarize.py)、[机器汇总](summary.json)、[逐次命令、日志、时间与 JSON](runs/)。额外一次 A 预热在 B 生成期间进行，未入正式结果；正式配对前另有 A/B 各一次预热。

## 独立子项：minm/maxm 末层 NaN 选择

C 从 A 原始模型冻结，**仅**把 `fp_minm_pure` 与 `fp_maxm_pure` 最后一层 `ite(strict_or_bool(ieee_is_nan(op1), ieee_is_nan(op2)), canonical_NaN('m), result_val)` 改为相同条件与结果的 `if`；`fp_min_pure`、`fp_max_pure` 的六层选择仍为 A 的 ITE。166 个文件中只变 `fp_minmax.sail` 两行，源 SHA-256 `45cb8e98…82f6`，见 [C 源差异](source-C.diff)和 [C 变体](variant-C.json)。相同严格工具链/配置完整生成 IR 退出 0，耗时 361.56 秒、IR SHA-256 `4dbec681f26b59470b510012e731e979089a5b88810b381383366cd0f0a313ad`，见 [C 生成记录](C/generation.json)。两份 IR 均 2053 函数，无增删；去源码位置后仅 `zfp_minm_pure`、`zfp_maxm_pure` 函数体不同，见 [C IR 比较](ir-comparison-C.json)。

与上节相同 binary、FD 配置、输入域、CPU 44–47、线程 1、外限 60 秒/路径 30 秒/SMT 10 秒；A/C 各预热后按 AC/CA/AC 各跑三对。每次退出 0、`finished`、无内部超时或采样、无错误/illegal。下表为三次墙钟中位数（范围），其他资源与逐次 JSON 见 [C 机器汇总](summary-C.json)和 [C 原始运行](runs_C/)。

| Clause | A：末层 ITE | C：末层 if | fork A→C | 退休见证 A→C |
| --- | ---: | ---: | ---: | ---: |
| `FMINM_S` | 1.808 秒 (1.807–1.808) | 2.107 秒 (2.107–2.108) | 7→9 | 4→5 |
| `FMAXM_S` | 1.907 秒 (1.807–1.908) | 2.209 秒 (2.208–2.209) | 7→9 | 4→5 |

C 在两个 Clause 各多一条双侧有效 boxing 的 qNaN/qNaN 见证；A 的默认生成集合仅有双侧无效 boxing 的 NaN 见证，单侧 NaN 两条及 `+0/+0` 一条两臂共有。**这只说明末层 NaN 选择的一个独立覆盖代价**：正常有限数大小两侧及零符号次序仍由下层六层 ITE 合并，C 没有补出，不能把 B 变体的较大覆盖增量算给此小项。

独立意见：末层 ITE 在这两个完整 Clause 各节省约 0.30 秒及 2 次 fork，但少一条可观察的有效 qNaN 双侧见证；由于生成集合不同，不能按相同覆盖量给精确加速倍数。若目前以自然生成的条件见证为验收，建议恢复这两处显式 NaN 判断；若保留 ITE，需先补这个条件见证后再测时间。C 仅为隔离实验，没有修改生产模型。
