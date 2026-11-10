# Isla 浮点分支详细复核（2026-09-25）

## 阅读范围与后续修订（2026-09-26）

本文保留 **2026-09-25 对固定分支 `1a1910e` 的调查**。下文原始命令、`85d7c70` checkout、两边尚未合并及“移植”的描述均属于那个时间点。现行 Isla 为 `f4f8e45`，已包含被调查的浮点实现；与中间合并提交 `8148bc1` 文件树相同。实施时应保留已合入的通用改进，完成模型替代后删除旧专用分发，不再按本文末尾的历史建议重新移植分支。

最新方案见 [实施计划](plan.md)，全部现有接口与修改意见见 [参考总表](reference-list.md)。后续又确认 ROD=6 的真实调用、BF16 非活动元素累计 NV，以及无穷加法/整数转 f16 的额外 flags 反例，见 [模型清单](inventory-sail.md)及[专用实现清单](inventory-runtime.md)。因此下文问题表和仅写五种舍入模式的建议都不是最终范围。旧反例仍适用于对应未修改代码；本轮未运行 Isla 动态复现。

## 结论与证据边界

`origin/feat/float-support` 已建立 Sail SoftFloat helper 到 SMT 浮点理论的执行通路，helper 名称覆盖较完整；语义尚处原型阶段。它适合继续完善浮点符号执行，当前不适合作为结果位和 fflags 均可信的差异测试参考模型。除旧记录的符号 rm、Eq/qNaN、FMA NV 外，本轮还确认减法 NX、NaN/invalid 时 NX、整数转换边界等问题；部分错误直接影响结果位。

本轮只读审查源码并更新文档，未检出、重新构建或运行该分支。下文反例是由表达式及 SoftFloat 参考代码推导的预期差异，不是分支动态执行日志。作者报告的测试通过和性能现象单独标明。

## 调查当时的版本

- `git -C isla ls-remote origin refs/heads/feat/float-support` 返回 `1a1910e17759d2f52344124dc0b0daa1ff5982bd`，与本地远端跟踪引用一致。
- 调查当时 Isla checkout 为干净的 `85d7c70f163aa23febb2e94c541725acd11f70b5`；共同基线为 `0008fae76f4cff86dae1a036d889f0414c228e9d`。
- `git -C isla rev-list --left-right --count HEAD...origin/feat/float-support` 为 `8 5`。浮点分支相对基线增加 5 个提交、修改 8 个文件；并未包含当前 HEAD 后续的全部修改。
- 浮点分支 `rv64d.ir` SHA-256：`7c626989a03056c43c67c81de8f40f611cef4c43ed1069a81526b37856d7e37b`；当前 IR：`6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`。
- Sail-RISC-V 当前提交为 `f8ce8490981eac6396a31013180a2e718615757d`。本轮用其现行调用链和工作区 SoftFloat 源码交叉核对。

除明确说明“当前 HEAD”或 Sail 路径外，下文 Isla 源码行号均对应 **浮点分支 `1a1910e`**，不可直接套用当前 checkout 的行号。固定版本源码入口：[float.rs](https://github.com/ariscv/isla/blob/1a1910e17759d2f52344124dc0b0daa1ff5982bd/isla-lib/src/primop/float.rs)、[executor.rs](https://github.com/ariscv/isla/blob/1a1910e17759d2f52344124dc0b0daa1ff5982bd/isla-lib/src/executor.rs)、[作者设计说明](https://github.com/ariscv/isla/blob/1a1910e17759d2f52344124dc0b0daa1ff5982bd/agents/float_support.md)。

## 实现思路

原来的阻塞点是 IR 中有声明、无函数体的 `riscv_*` helper。例如 `riscv_f32Add` 接受 `(bv3 rm, bv32 a, bv32 b)`，返回 `(bv5 fflags, bv32 result)`。普通函数查询失败后原执行器会报 `NoFunction`。Isla 已有通用 SMT FP 操作，但这套 RISC-V 外部接口没有绑定。

分支在执行器 `run_special_primop` 末尾增加分发（`executor.rs:1196-1229`）：

1. 解码 Sail 名称，经 `softfloat_dispatch` 得到格式和操作枚举。
2. 求值实参，并从 IR 类型表找到返回 tuple-struct 的 flags/result 字段。
3. `softfloat_call` 把寄存器 IEEE 位向量 reinterpret 为 SMT FP 值，建立舍入模式和运算表达式。
4. 数值结果经 `fp.to_ieee_bv` 转回位向量；NaN/invalid 情形尝试强制规范 NaN。原始输入位仍用于区别 sNaN/qNaN。
5. 手工建立 NV/DZ/OF/UF/NX 的布尔表达式并拼成 bv5，与结果一起返回。Sail 后续代码继续负责寄存器写回和 fflags 累计。

这条通路保留符号输入间的约束关系。运行时没有调用主机 SoftFloat C 库，也没有将 helper 返回值简单处理成无约束符号。

SMT 层新增 `FPUnary::ToIEEE`，接到 `Z3_mk_fpa_to_ieee_bv`；修复 `FromIEEE` 结果类型的指数位/有效数位顺序；修复既有 fp32/fp64/fp128 整数到浮点 primop 错用 fp16 目标格式的问题。

fflags 中 `NV/DZ/OF/UF/NX` 分别为 bit4/3/2/1/0。SMT FP 运算直接给出舍入后的结果，并不直接返回 SoftFloat 的异常标志。分支采用位模式分类、宽格式重算、往返比较和转换边界比较补出 flags；这部分是当前主要问题来源。

## 覆盖范围

| 维度 | 源码支持 | 适用边界 |
| --- | --- | --- |
| helper 数量 | 分支及当前 IR 均为 79 个 `zriscv_*` val、12 个已有函数体、67 个无函数体；分发覆盖这 67 个名称 | 名称覆盖不代表全部数值组合正确 |
| 格式 | f16/f32/f64，另有 f32→BF16 | 无新的 f128 RISC-V helper 家族；fp128 用于部分内部精度分析 |
| 算术 | Add/Sub/Mul/Div、MulAdd、Sqrt | FMA 使用真正 `fp.fma`，一次舍入；flags 另算 |
| 比较 | Lt/Le、quiet 变体、Eq | Eq 的 NV 规则有错 |
| 转换 | 浮点↔有/无符号 32/64 位整数；f16/f32/f64 相互转换；roundToInt | 转换边界、负整数 NX 等仍有缺陷 |
| 其他 helper | Recip7/Rsqrte7 各三种格式、部分窄整数转换已在 IR 有函数体 | 这 12 个不要求增加同名原生分发 |
| 指令外围行为 | 沿用 Sail 的状态检查、NaN boxing、寄存器访问、fflags 累计及向量控制逻辑 | 不能由 helper 单测推断端到端已验证 |

RVV 会复用同一条通路：当前 `sail-riscv/model/extensions/V/vext_fp_insts.sail:37` 读取 `fcsr[FRM]`，`:64-75` 在逐元素循环中调用 `fp_add/fp_sub/...`；`vext_fp_utils_insts.sail:179-188` 按 SEW 选择 f16/f32/f64 helper 并累计 flags。因此此分支可以解除向量浮点的外部函数缺失阻塞，相关语义错误也会传播到 RVV。

分支没有新增向量批量语义或消除原来的 mask、vstart、VL/SEW/LMUL 路径展开。helper 可分发不能证明全部 RVV 浮点 clause 可在合理资源内完成。

## 静态确认的具体问题

以下的“分支行为”均为源码推导；后续应先建立对应失败测试再修复。

| 问题 | 证据（`float.rs` 行号） | 具体反例及影响 |
| --- | --- | --- |
| 符号 rm 恒为 RNE | `745-758` 的 fold 初值及两个分支恒为 RNE | 符号 rm 即使约束为 RUP，f32 `1 + 2^-24` 仍按 RNE 返回 1；应返回 `0x3f800001`。具体 `Val::Bits` rm 路径正常映射五种模式 |
| Eq 错当 signaling 比较 | `561`、`1162` | `Eq(qNaN,1)` 应 false、NV=0；实现 false、NV=1。SoftFloat `f32_eq.c` 仅对 sNaN 置 invalid |
| FMA 漏 invalid | `1116-1124` | `(+inf)*1+(-inf)` 应规范 NaN、NV=1；实现遗漏该条件，NV=0，且 NaN 不进入规范化分支，`to_ieee_bv(NaN)` 的结果位缺少保证 |
| Sub 的 NX 用了 Add | `791`、`1097-1098` | f32 RNE `1-2^-24` 可精确表示为 `0x3f7fffff`，实现却依据 `1+2^-24` 置 NX；`1-(-2^-24)` 则会漏 NX |
| NaN/invalid 未正确屏蔽 NX | `793-802`、`832`、`842-844`、`1306` | `qNaN+1` 会多置 NX；`0*inf`、`sqrt(-4)` 会给 NV\|NX，正确仅 NV；qNaN 窄化也会多置 NX。因为 `fp.eq(NaN,NaN)=false`，不能直接把往返不相等当 NX |
| 负 qNaN 开方误置 NV | `1143-1145` | `sqrt(0xffc00000)` 应传播规范 qNaN、不置 NV；实现把带符号 NaN 归入负非零数 |
| 无符号转换 RDN 下界错 | `950`、`1203-1208` | 判定条件写成 `x<+1`。具体 rm=RDN 时，`f32ToUi32(+0)` 错置 NV 并返回 `0xffffffff`；正确为 0、flags=0 |
| 浮点转整数边界依赖错对象 | `926-939` | f64→i32 RNE：`2147483647.75` 舍入后越界，但实现漏 NV，使不合法 SMT 整数转换结果缺少约束；`-2147483648.25` 可舍入至 i32 最小值，却误报 NV。需要按目标整数范围及实际舍入规则建界 |
| f16/f32→64 位整数界常数越过内部格式 | `868`、`934`、`953`、`963-970` | 部分界构造要求 j=64，而内部宽格式有效数位 ws=53；`ws-j` 或 `ws-1-j` 下溢。所有舍入模式的表项都会构造；静态可推导 debug 有 panic 风险，release 有错误移位/界常数风险，尚未运行分支确认 |
| 负整数转浮点漏 NX | `1239-1260` | i32 `-16777217`→f32 RNE 必须舍入，NX 应为1；RTZ 与 RUP 对负数相同，现有比较却给 NX=0 |
| i→f16 的 OF 符号判定错 | `1005`、`1014-1020` | signed `-1` 在 RDN 下先符号扩展再按无符号与65536比较，误置 OF；正确结果 -1、flags=0 |

符号 rm 的影响以“helper 收到符号 rm”为前提：标量路径可能通过 Sail 的舍入枚举提前具体化；RVV 直接读符号 `frm` 的路径尤其需要覆盖。不能将此问题描述成每一条标量指令都无条件使用 RNE。

整数转换及负数等新增问题意味着作者“数值结果精确”“NV 精确”“转换 NX/范围精确”的总括声明不能作为现版本保证。

## 已声明的近似仍需补足

即使修复上面的实现错误，作者设计说明已经承认以下近似：

- **Div/FMA 的 NX 仅为 OF|UF。** 例如 f32 `1/3` 的正常有限结果不精确，应该 NX=1，实现会漏报。FMA 的普通舍入也类似。
- **UF 用非零次正规结果代替下溢。** 精确产生次正规数会误报，例如 f32 最小正规数乘0.5；舍入到零的微小非零精确值会漏报。需要结合不精确和舍入后微小检测，不能只看结果分类。
- **OF 主要看有限输入是否得到 infinity。** 定向舍入溢出到最大有限数会漏报，例如正最大有限 f32 乘2、rm=RTZ；正确应 OF|NX。

缺少现成 SMT flags 返回值不代表这些条件无法精确建模。可建立足够宽的位向量精确中间结果以及 guard/round/sticky 位，或采用经差分核实的每操作判定；需要证明 NaN、溢出、下溢和舍入边界。简单提高一个浮点格式的精度并不能保证除法/FMA 所有中间量都精确。

## 测试与性能的实际证据

分支 `softfloat_tests` 有21个测试，35次 `solve_call`，实际求解15种 helper；其中20个测试调用真实 Z3，1个只测分发/返回类型。所有输入都是具体 `Val::Bits/Bool`，没有符号输入构造。rm 只覆盖 RNE 和少量 i64→f16 的 RTZ。

- f64 只作为 f64→f32 输入，没有 f64 算术测试。
- f16 主要为1+1和整数转换上界；BF16只有1.0精确转换。
- 无直接 Sub、Eq、unsigned 数值转换、fp→i64/ui64测试。
- FMA只有 `2*3+1=7`；除法没有正常不精确样本。
- 多个样本只检查某个 flag 掩码，漏掉了其他 flag 的错误置位。
- `f32_add_inexact_nx` 名称下实际测试的是 Mul。
- 测试直接调用 helper，使用自行构造的返回字段 Name，跳过 IR 加载、执行器接入和真实结构体解析。

作者报告 `cargo test -p isla-lib --lib softfloat` 通过，以及 `make solve-FLEQ_S THREADS=4` 完成。本轮未重新执行。FLEQ_S 是 quiet 比较，不接受 rm，不能验证符号舍入、算术、转换或 FMA。

作者还报告 `F_BIN_RM_TYPE_S` 约8分钟产生91条路径，高负载下可能 OOM。这是作者的性能观察，不能当作全组完成率或当前机器测试数据。宽格式重算将 f64 部分辅助求解提升到 fp128，RVV 再按元素重复表达式，是值得测量的成本来源。

分支 `scripts/run.mk:53-68` 的 `FD_FLOAT` 共89个 clause，包含标量、RVV浮点、BF16和浮点访存目标；默认 `make solve` 仍明确排除 FD_FLOAT。浮点入口为 `make solve-fd-float`，此目标没有完成的独立验收证据。外部正常退出/intime也需结合成功路径、内部超时及输出内容解释。

## 接到当时工作区的建议（历史记录）

以下四项保留当时两边未合并时的判断。“当前”指 `85d7c70`。其中接口和测试缺口已重新对照 `f4f8e45` 登记到现行计划，不把这段作为最新实施步骤。

1. 当前 HEAD 已有与浮点分支相同的 FD 配置文件，以及四个向量浮点搬运目标的配置接线；浮点分支把专用配置扩到整个 FD_FLOAT。移植时应结合两边已有实现。
2. 两边 IR 哈希不同，原浮点冒烟结果不能直接覆盖现行 IR；严格 workaround 的绑定仍按现行流程核对。
3. 当前 `Solver::new` 要求先 `configure_tastic`（当前 `smt.rs:2115`），浮点分支测试没有该初始化。直接移植测试需适配；当前默认 Qfaufbv tactic 对混合 FP/BV 公式的表现也需实测。
4. FD 配置启用 F/D 并将 FS、VS 设为 Dirty，只解决模型允许执行的前提；不证明状态导出、ELF装载、DUT回放、fflags对比完整。

建议顺序是：先为上述反例建立完整结果/flags回归并修复，再完成精确 flags；随后做五舍入模式及格式/操作矩阵的 SoftFloat 差分、符号/具体输入一致性和执行器集成；最后在固定版本配置上评估标量、RVV、访存各类 clause 的完成率、耗时、峰值内存及真实 DUT 差分。此处为调查建议，没有实施修复。

**后续修订：**五种原生舍入模式之外，还要单列 ROD 窄化；SoftFloat 对照仅用于同语义接口。Recip7/Rsqrte7、FCVTMOD、状态和无序归约分别采用对应规范。现在按 [计划第 5 节](plan.md#5-实施顺序)的 A–E 阶段推进，不能按上段只修旧分支几个错误就宣布完成分层。
