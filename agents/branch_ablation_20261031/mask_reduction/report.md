# 向量掩码与顺序归约的独立消融

两个限定完整 Clause 都显示相同取舍：当前 ITE 版本 A 较快，但默认生成集合没有已屏蔽指令的活动 lane 见证；只恢复活动 lane 显式 `if` 的 B 较慢，却生成了活动、不活动和混合 lane 见证。建议在已测的 `FVVTYPE` 与 `RFVVTYPE` 范围恢复 B；其余向量 Clause 和 SEW/vl/vstart 上下文仍需分别核对，不能从本组推断全域收益或语义等价。

## 源码边界与 IR

基线为根 float `1c7a354`、Isla `80231ce9`、干净模型 `9c339044`，冻结于本目录四份完整模型。A 是当前 ITE；mask B 只改 `model/extensions/V/vext_fp_insts.sail` 的 SYMBOLIC `FVVTYPE`，reduction B 只改 `model/extensions/V/vext_fp_red_insts.sail` 的 SYMBOLIC `RFVVTYPE`。每组 A/B 的 166 个模型文件仅目标文件哈希不同，插件和生成配置一致。精确补丁见 [mask/source.diff](mask/source.diff) 与 [reduction/source.diff](reduction/source.diff)。

mask B 在 `if mask[i] == 1` 内调用原有纯数值函数、写结果 lane、OR 该 lane 的 flags；不活动 lane 保留 `initial_result`，flags 不加入。reduction B 也只在该判断内调用原有纯数值函数、OR flags、按原递增 lane 顺序更新 `sum`。因此纯数值后端、NaN-boxing 已恢复的 if、合法性判断、`vl=0` 早退、`vstart` 检查和最后的 `accrue_fflags` 均没有被回退；此处没有单独动态证明这些语义边界的全域等价。普通模式源码也未变。

A 的 166 个源码文件、插件、生成配置及 Sail launcher 哈希与已完成严格生成的 `agents/nan_unbox_branch_restore_20261031/generation/rv64d/generation.json` 完全相同，因此复用其完整 IR `10bea88c…142bbf`；逐项核对见两份 `A/ir/baseline-reuse.json`。本组重复启动的 mask A 生成在核实该证明后主动终止，`generation-rv64d_mask_A.json` 中的 `-15` 不作为验收结果。两个 B 均从各自冻结源以严格 `SYMBOLIC` 命令完整生成，退出 0，保留函数无缺失；IR 哈希分别为 mask `f7f4c073…2f425fa`、reduction `c6dbeef1…1a45de6`。生成命令、原日志和完整哈希见各自 `B/ir/generation-*.json`、`generate-*.log`，以及 [summary.json](summary.json)。没有使用实验 IR 装配。

## 共同输入与预算

两组均用 V128/ELEN64 IR、同一 `isarch` 二进制 `e9fd5a0b…279204`、同一 F/D 配置附加 `[initial_state]`：`vtype=0x10`（SEW32、LMUL1）、`vl=2`、`vstart=0`。向量寄存器、mask 数据和浮点操作数仍符号化。所有已生成终态中的这三项实值分别为 16、2、0；这只限定上下文，不代表测试了 `vl=0` 或非零 `vstart`。mask 组测完整 `FVVTYPE`，reduction 组测完整 `RFVVTYPE`；未指定单个 opcode。

`taskset -c 52-55`、`-T 1`、外限 60 秒、路径 30 秒、SMT 10 秒、Z3 `qfaufbv`，两臂各一次等量预热后按 AB/BA/AB 跑三对。IR 生成耗时不计入下表。原始命令、工作目录、退出码、逐次墙钟/用户/系统 CPU、最大 RSS、输出与日志 SHA-256 均在 [summary.json](summary.json) 和各组 `runs/*/result.json`；原日志与原 JSON 保留在对应 `runs/*/`。运行环境 `LD_LIBRARY_PATH=/home/linuxbrew/.linuxbrew/opt/z3/lib`。当前工具没有可靠的全局真实 fork 计数，记为未知；不把每条叶路径的累计值相加。

## 完整 Clause 结果

下表每个三元组对应三次正式运行；时间为 `/usr/bin/time` 墙钟秒，RSS 为三次最大值范围（KiB）。四种版本的正式运行均退出 0，`summary.status=finished`，errors、execution/SMT/model-query timeouts、unfinished、omitted、pending、encoding-filtered 均为 0，未出现 partial。`gen` 是生成见证数，不是覆盖率。

| Clause | 版本 | 墙钟三次／中位数 | user CPU 三次 | sys CPU 三次 | RSS 范围 | 每次 gen／Retire／Illegal | 已屏蔽成功见证：有活动／有不活动／混合 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FVVTYPE | A ITE | 7.88, 7.59, 7.65／7.65 | 7.06, 6.75, 6.80 | 0.91, 0.92, 0.94 | 255764–257172 | 27／18／9 | 0／9／0 |
| FVVTYPE | B if | 11.23, 11.16, 11.17／11.17 | 9.77, 9.63, 9.65 | 1.64, 1.71, 1.71 | 255904–260728 | 54／45／9 | 27／27／18 |
| RFVVTYPE | A ITE | 4.17, 4.14, 4.17／4.17 | 3.71, 3.68, 3.76 | 0.49, 0.49, 0.45 | 246292–246352 | 12／8／4 | 0／4／0 |
| RFVVTYPE | B if | 5.20, 5.25, 5.21／5.21 | 4.58, 4.57, 4.57 | 0.69, 0.76, 0.71 | 246224–247224 | 24／20／4 | 12／12／8 |

见证分类用最终 JSON 中 `test-ins` 的 `v0.t`、初态 `vr0` 低两位、`vl` 和 `vstart` 计算。每条见证可同时计入“有活动”和“有不活动”；“混合”指两者同在。A 的未屏蔽指令仍有活动 lane，表中只统计已屏蔽指令，避免用这类见证冒充 mask 正侧。B 的例子 `vfsgnjx.vv v31, v0, v0, v0.t` 带 `vr0[1:0]=01`，因此 lane0 活动、lane1 不活动。A/B 的 Illegal 数相同；没有发现运行错误，但生成集合差别不能单独证明全域语义等价或不等价。

分类为“完整 Clause 耗时收益在 A，同时有覆盖见证损失”。在本次限定域内 A 比 B 少用 3.52 秒和 1.04 秒中位墙钟；B 多探索了活动 lane 分支，所以这些时间不是等覆盖工作量的纯速度比较。局部 helper 的历史收益未作为本次完整 Clause 结论。独立建议是恢复这两个已测 Clause 的显式判断，再对其他向量 Clause、宽化归约、BF16 和不同 SEW/vl/vstart 输入域做各自消融；本组未改生产源码、分支或 IR。
