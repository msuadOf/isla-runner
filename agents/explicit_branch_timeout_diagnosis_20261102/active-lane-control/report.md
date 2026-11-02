# 饱和 overflow × 活动 lane 对照

## 当前结论

在已有正确活动 gate 的 `a9fd947` v128 IR 上，只把 f16→i16 helper 的 overflow ITE 改成显式 if，五次运行都自然完成。ITE 臂各 42 条 JSON，显式臂各 46 条；全部退出 0、`summary.status=finished`，错误、SMT/执行超时、未完路径均为 0。显式臂新增了活动 lane 溢出时 NV（invalid operation）见证。这证明**当前活动 gate 下此显式 overflow 在这个 Clause 和状态域内不触发旧 7200 秒超时**，并未证明其他宽度、VL/LMUL或全部转换调用点可完成。

旧冻结 `9c339044` 的显式 B 仍是 7200 秒外限超时；它在 `vl=1` 时提前计算 8 个物理 lane，后面才选择掩码。当前 A/B 与旧 B 之间还含 NaN 分类、其他活动 gate 和相邻源码变化，不能把新旧时间差直接称为活动 gate 单变量效应。**旧 B 模型仅加 `VFUNARY0` 活动 gate 后，三次完整 Clause 均自然完成，墙钟 57.29–63.78 秒、28条JSON。**这直接排除其他新源码变化作为本次可完成性恢复的必要条件。旧 B 与 gate 版不是等覆盖集合，不能把 7200 秒与约60秒当作等覆盖加速比。

## 当前同基底单变量实验

- 输入：`A.ir` SHA `23e37501…`，`B.ir` SHA `a7640fce…`；[manifest](manifest.json) 固定完整哈希。两份 IR 除 `zriscv_f16ToI16_pure` 外逐字相同，helper 前缀也逐字相同；只有该函数 overflow 出口由 ITE 变成 if。[IR 审计](ir-audit.json) 检查了 gate PC25878 的真出口25881、假出口25879；两处 f16→i16 调用 PC25982/26277 都受活动 gate 支配，假出口绕过调用。
- 配置：原 sat `config.toml` SHA `da35c576…`，`vtype=0x8`、`vl=1`、`vstart=0`，VLEN128/SEW16；冻结 `isarch` SHA `c9c5bb8…`，RUNPATH 指向官方 Z3 `1fd1d3613` 的 `libz3.so.5.3`（库 SHA `899cbc70…`）。`--tastic qffp -T 1 --smt-timeout 7200s`，外层 `timeout 7200s`，seed17 已由每次 `seed.log` 证实。C API 插桩 `probe.so` SHA `8ffa94f…` 对 A/B 一致。
- 首对不同物理核同时启动：A CPU98/B CPU99。其后 pair2–5 在相同 CPU 上依次运行，次序 BA/AB/AB/BA；CPU98、99 属不同物理核。完整命令、墙钟/user/sys/RSS、逐次状态和查询统计见[结果](results.json)。

| 臂 | 5次墙钟范围 | 每次JSON | 每次Z3 check | unknown | Z3 check累计范围 |
| --- | ---: | ---: | ---: | ---: | ---: |
| A：活动 gate + overflow ITE | 21.74–35.36秒 | 42 | 1369 | 0 | 8.66–16.47秒 |
| B：活动 gate + overflow if | 45.15–64.14秒 | 46 | 1617 | 0 | 28.67–46.65秒 |

同核四对 B/A 墙钟比为 1.36、2.53、1.80、2.95，中位 2.17；主机仍有其他负载，且 B 生成的见证集合不同，所以该比值仅描述本轮完成时间，不是等覆盖速度比。check 次数不是 fork 数。

启用 `-D f` 的 B 独立复跑退出 0，实际 helper overflow fork 四次，分散于现有指令/掩码路径；旧 eager IR 日志曾在单次循环连续出现八次。此运行增加 taint 日志成本，未纳入上表配对。`B-forks/` 保存命令和原始日志。

显式 B 中 `vfcvt.x.f.v` 和 `vfcvt.rtz.x.f.v` 出现活动 lane 新增 NV 的完成见证，例如 `vfcvt.rtz.x.f.v v4, v8, v0.t` 的 `fcsr` 由 `0x00000000` 到 `0x00000010`；A 的本轮集合无新增 NV 样例。它证明本轮见证覆盖不同，不能据此声称 A 计算错误。

## 旧基底精确 gate 控制

旧 `sat_f16_i16_if/model` 是模型 `9c339044` 加唯一 overflow-if 源差异的冻结副本。已复制到 `old-gate/model`，仅替换 SYMBOLIC `VFUNARY0` 循环的活动 gate 块；[源记录](old-gate/source-manifest.json) 及 `diff` 显示函数前后文不变、其余文件逐字复制。Sail `0.20.1`、同 `rv64d.json`、原插件和 preserve 集合的严格 IR 生成退出0，源码全程不变。先前无旧 memo 的一次编译到1131秒仍在外部类型约束查询而被终止，记录保留在 `old-gate/generation/result.json`；复用原旧 B 的 Sail SMT memo 副本后246.80秒完成，见 `old-gate/generation-cached/result.json`。memo 是编译加速缓存；运行的 IR SHA `39860ed4…` 独立冻结。

[旧 IR 审计](old-gate/ir-audit.json)确认：原旧 B IR SHA `d29e971b…` 与 gate IR 的 f16→i16 显式 helper 逐字相同，`zexecute` 前所有IR逐字相同；2053个函数中其余22个文本差异仅为编译器参数编号重排，按局部参数映射等价。`zexecute` 新活动 gate PC25898 真出口25901、假出口25899；两处 helper 调用 PC26002/26297 由该 gate 支配，假出口均绕过。旧 B 的 eager 循环在 helper 前没有此 gate，源码在所有8个lane先调用 helper，再用mask选择。

旧 gate IR 三次均在 CPU98、seed17、QFFP、T1、官方Z3、完整 Clause/SMT 7200秒预算下退出0；`summary=finished`，28条JSON，errors、timeouts、unfinished全0。三次墙钟分别63.78、57.29、59.00秒；每次1318次Z3 check、unknown0，累计check约45.59、39.75、39.43秒。逐次完整命令、哈希、time、query及JSON在 `old-gate/run{,2,3}/`。严格同 seed17 的历史旧 B 对照只有 `agents/branch_ablation_official_z3_20261102/runs/sat-pair1/B/result.json`：外限7200秒、exit124；该历史运行没有 probe、CPU40，因此不能计算等硬件或等插桩性能比。旧 B 另两次 seed29/43 也各到7200秒外限，只是跨种子补充证据，不能冒充 seed17 重复。旧gate三次同seed17完成说明：在旧模型相同输入域、策略与预算内，overflow显式if不必然超时；移除不活动lane提前计算已足以让这个seed的完整Clause完成。不能据此断定全部种子或宽域都完成。

旧 gate IR 另带 `-D f` 复跑也退出0；真实 overflow fork 共4次，没有旧 eager 循环的连续8次。`old-gate/run-forks/` 保存此定性复跑的命令、查询与原生日志，不混入三次计时。
