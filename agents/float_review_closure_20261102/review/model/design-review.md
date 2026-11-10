# 模型与控制流独立实施前审查

审查基线为已发布 `6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a`，检出位于 runner-float 的模型子模块；检查时干净。源码哈希见 [baseline.json](baseline.json)。本文件只签实施前语义与验收契约，不签尚未提交的源码、生成 IR 或动态结果。审查者未参与实现，未改生产源码，未启动构建或重型求解。

当前五个窄适配器确实只把 overflow 放进 ITE；`accrue_fflags` 的 changed 仍只控制 mstatus 的 ITE。剩余整数转换、异常原因和 ROD 也存在控制边界，不能仅改这六处后声明全部特殊行为闭合。

## 逐项分类

下面行号均以基线源码为准，路径相对模型仓库。

| 候选 | 判定 | 代码依据与最小语义 |
| --- | --- | --- |
| `FD/fdext_regs.sail:542` 的 changed | 应显式 | `old != old|flags` 决定是否把 FS 置 Dirty、SD 置1，并决定 F/Zfinx 互斥断言是否需要成立。新 flags 非零不等于 changed；旧 flags 已包含新 flags 时必须走不变臂。 |
| `V/vext_fp_utils_insts.sail:554-586` 五个 `_pure` overflow | 应显式 | 有符号 overflow 分别饱和最小/最大值，并将 flags 替换为仅 NV；无 overflow 保留上游 flags 和低位。无符号只有上界饱和臂。不要把上游 flags 与 NV 做 OR。 |
| 同文件 `:550`，既有 f16→i16 的 limit 符号 ITE，以及另两个 signed narrow 的 limit | 应显式 | 正 overflow 与负 overflow 选择不同端点，原普通 helper 有三种出口。仅增加 overflow 一个二叉分支仍将正、负端点合在同一路径；应在 overflow 真臂分别选择符号，或恢复原上下界三臂。 |
| `softfloat_symbolic_f16:51-88`、f32 `:98-135`、f64 `:86-123` 的12个 FP→32/64位整数 wrapper | 应显式 | invalid 决定候选整数还是架构饱和值；invalid 中 NaN（包括负 NaN）一律选正端点，非 NaN 才按符号选端点。f64 的 `NaN OR positive` 合并同样不能独立见证 NaN 与正溢出。与窄转换同时审查，禁止只检查下一级 overflow。 |
| `core/ieee_fp_exceptions.sail:53` 的 NaN/sNaN/qNaN 分类 | 已显式，保持 | 每个源操作数独立调用该 helper，先分 NaN，再分 sNaN；多源 strict OR 不短路。纯 `ieee_is_*` 分类谓词仍应返回 Bool，不在谓词内部制造重复分支。 |
| 各 wrapper 的 canonical NaN 出口 | 已显式，保持 | f16/f64 结果出口和 f32 helper，以及跨格式/BF16 出口均已有 if；它只区分 NaN 结果，不能替代导致同一 NaN 结果的各异常原因。 |
| `ieee_add/sub{16,32,64}_exceptions` 的 Inf 抵消 | 应显式原因边界 | add 的异号 Inf、sub 的同号 Inf 产生 NV；同号 add/异号 sub 的有效 Inf 无 NV。现有源 NaN 分类后，这些都在非 NaN 源路径，只有结果 NaN 出口能区分 invalid/valid，不能据此宣称 Inf 与有限算术已分别见证。 |
| `ieee_mul*` 与 `ieee_fma*` 的零×Inf | 应显式原因边界 | 0×Inf 或 Inf×0 产生 NV，FMA 即使 c 为 qNaN 也不能丢这项 NV。两个源位置须有见证，不能用短路导致后源未分类。 |
| `ieee_fma*` 的 Inf product 与反号 Inf c 抵消 | 应显式原因边界 | 仅有效非零非 NaN 的 Inf product 可进入抵消；product 符号由 a、b 异或，须分别测试两种 product 符号及非抵消对照。不要把 FMA 拆成乘加。 |
| `ieee_div*:393/492/591` 的 0÷0、Inf÷Inf、有限非零÷0 | 应显式且分别可见证 | 前两种 NV、无 DZ；第三种 DZ、无 NV。0÷0 与 Inf÷Inf 共享现有 NaN 出口，DZ 与有效 Inf 共享非 NaN 出口；现有 Jump 不足以证明这些原因各有路径。 |
| `ieee_sqrt*` 的 negative-nonzero | 应显式原因边界 | 负有限非零和 -Inf 产生 NV；-0 必须保留 -0 且不 NV；不能只按符号位判 invalid。 |
| 算术 finite/valid gate、转换 `ieee_mask_exact_exceptions:737` | 应显式语义 gate | 特殊输入禁止带入普通有限舍入 OF/UF/NX；应把有限舍入异常的选择放在 gate 内，避免非活动/特殊路径先执行新控制后再事后屏蔽。纯有限性谓词仍是 Bool。 |
| 最终 NV/DZ/OF/UF/NX 的成立/不成立 | 应显式异常边界，检查已有控制后补缺 | 异常是用户确认的语义分界；仅把 Bool 拼成 flags 或在最后 changed 分叉，会合并例如新增 NV 与新增 DZ。应在语义判定处暴露最终异常类别；无需把每个阈值子项、每个 strict AND/OR 都改为 if。已由原因分支确定的异常无需再次机械分叉。 |
| f32/f64 narrowing 的 `rm==6` | 应显式模式选择 | `softfloat_symbolic_f32:174-183`、f64 `:162-172` 仍用 ITE 同时算普通/ROD，再选 flags 和 bits。ROD 与普通应分臂，flags 与 bits 必须同一臂返回；只在普通臂解码原五种 RM，禁止把6传给 native RM。 |
| `ieee_rod32_to_16:950`、`ieee_rod64_to_32:961` 的 exact/inexact 选择 | 应显式结果策略边界 | 精确时保留 RTZ 结果；非精确时最低位置1，flags 仍为原 RTZ 异常（不新造第六种 Z3 RM）。`base_bits | 1` 本身保留数据流。历史审查把 ROD 整体视为数值公式并未恢复；本轮按明确要求检查 ROD 控制边界，是范围修订，不能继承旧签收。 |
| `riscv_valid_rm_to_ieee` 的五种 RM 解码 | 数据流/已有调用者控制 | 架构合法性和指令 RM 选择已在调用者。常量映射链本身不必再制造五叉；五种 RM 各有实际见证的义务保留。 |
| directed bounds、lower/upper 幅值排序、nearest/outward/inward 阈值公式 | 数据流 | 它们是计算正确舍入异常的数学方法。保留数值公式与各比较谓词，在最终异常边界分叉；不能因为含 ITE 就重写。 |
| `width64/is_unsigned` 常量参数选择、flag 位重排/OR、截位/扩展、位或 jam | 数据流 | 这些调用配置或位运算不单独选择新的指令行为；上级类型、opcode 和异常策略已决定语义。 |
| ±0/Inf 的符号处理是否需新增独立源码分支 | 逐操作核实 | 若符号选择饱和端点、min/max 的 ±0 策略、sqrt 负非零合法性，则属于控制。若只是 native 加减乘除的数值符号传播，不把全部符号运算机械分叉；但有关特殊符号输入/输出仍须独立实际见证，不能由一个符号的样例外推。 |

## 最小实施契约

`accrue_fflags` 保持 old|flags、FFLAGS 写入和现有两个 CSR callback；changed 真臂才要求扩展互斥，并在 Ext_F 时更新 FS/SD，假臂保持 mstatus 所有位。直接调用 `dirty_fd_context_if_present` 会新增 `long_csr_write_callback(mstatus)`，当前 SYMBOLIC 没有该事件，因此不是纯 ITE→if，应单列说明并验收，不能悄然加入。

窄 signed 可用原三臂比较，也可用已核实的无损符号扩展谓词加 overflow 内符号分支。unsigned 可用无损零扩展谓词。不改变上游转换、先舍入再判范围、NV 抑制 NX、负无符号饱和0和 NaN 饱和最大值。所有新增控制必须受既有 active lane gate 支配；全屏蔽和 vl=0 不得执行它们。

异常实现可以组织共享小 helper，但需保留每源 NaN 分类、独立原因与优先语义。数学上已不可能成立的后续分支不要求虚构见证；如果采用有优先级的 if/else，须写出前置条件，例如无 NaN 后的 0÷0，再 Inf÷Inf，再 DZ。纯条件算式可继续构造 Bool，但最终影响行为的选择不能仅留 ITE。原上下界公式不在本轮重算。

ROD 建议把 wrapper 分为 ordinary/ROD 两臂，各臂只运行自己的实现，NaN canonical 出口保持。ROD helper 的 finite/NaN 优先语义、sNaN 的 NV、exact/inexact jam、OF/UF/NX 都需配对验证。

## 实际见证义务

1. flags：old=0/new=0、old 已含 new 的非零不变情况、新增单 flag、已有其他 flag 后新增 flag；Ext_F 下 FS 初始 Clean/Initial 等状态、changed 两臂、SD 和其他 mstatus 位；Zfinx 配置若在声明范围内亦核实不误改 FS。指令写目标寄存器可能独立置 Dirty，应另有 helper 定向状态检查，不能仅从整指令 Dirty 后态反推 changed 分支生效。
2. signed narrow：正 overflow/负 overflow/精确边界/范围内 inexact，各五种 RM 与显式 RTZ opcode；f16→i8 可用128、-129，f32→i16可用32768、-32769。既有 f16→i16 也补两端独立见证。NV 真臂只返回 NV，正常臂精确保留原 flag。
3. unsigned narrow：正上界、负输入饱和0、NaN（含负 NaN）/+Inf/-Inf、范围内 inexact。f16→ui16 的最大有限数65504小于65535，不存在正有限数 overflow；其 overflow 真臂由 +Inf/NaN 的上游 ui32 饱和等触发。不得用不可达数值阻塞验收或虚写有限 overflow PASS。
4. H/S/D 每类算术分别检查 sNaN/qNaN、valid Inf、上述各 NV 原因、±0、有限精确/非精确及 OF/UF。division 还分别见证 NV=0÷0、NV=Inf÷Inf、DZ=有限非零÷±0 与 valid Inf/有限非零，不以相同输出归并原因。
5. ROD 两种实际宽度，exact（含尾位0/1）、inexact RTZ 低位0→1 与原已1、负值、溢出最大有限、tiny/underflow、±0、±Inf、sNaN/qNaN。普通五 RM 与 ROD 的 oracle 分开核实；不能只检查输出奇数位而忽略 flags。
6. 向量覆盖对应 SEW、活动/屏蔽、多 lane flags 合并、vl0；scalar/vector/BF16 和归约调用闭包由最终 inventory 固定。定向见证只证明对应条件，不等于完整 Clause 域预算验收。

## 分阶段签收

设计契约可据此实施，但无源码/IR/动态 PASS。源码阶段检查固定 commit 的完整 diff、数学等价、控制优先序、同臂 flags/result、active gate 和调用闭包。IR 阶段分别核四配置 SYMBOLIC 与 ordinary 严格检查，五 IR 的实际 CFG 条件及支配关系，不能只数 Jump；永久回归应对旧实现失败，并拒绝运算移回 mask 之前的负例。

动态阶段使用固定模型、Isla、IR、配置、binary、官方 Z3、seed17，T1/qffp；每个受影响完整 Clause 与单次 SMT 均7200秒，记录命令和退出账。定向 oracle 与完整域 Clause 预算分别签。若改动使范围增加，新增 Clause 也入账；若超时则保留未通过，并核已完成/排队/单次求解耗时，不可缩域替代验收。源码、IR、动态结果分开签收，不跨版本继承 PASS。

## 清单交叉检查与估算补查

与 [实施前清单](../../inventory/current-source-ir.md) 交叉检查：N3 的 f16 输入不能取65535/65536（不在该格式有限值集合），已要求改为最大有限65504与 +Inf/NaN 对照。E2 的乘法不经 `FWVTYPE`（该 Clause 只做 add/sub），对应额外入口应是 `FWVFTYPE`；源码 `vext_fp_insts.sail:2258`。E1 的归约仅 add，宽化的目标格式是 `2*SEW`，不能把源 SEW16 误作目标 H。

`vext_fp_utils_insts.sail:636/652/667` 的三个 Rsqrte7 已通过十分类 match 处理特殊值；`:740/756/772` 的三个 Recip7 已有 ±Inf/±0/sNaN/qNaN/subnormal 与 abnormal 分支，不存在待恢复的对应 ITE 出口。需要保留 H/S/D 实际见证，历史 S/vl1 不替代其他格式。

Recip7 另有既存计算顺序：在分类 match 前无条件计算 `recip7(v,rm,true)` 和 `recip7(v,rm,false)`，内部包含 sub、指数和 overflow 控制；因此特殊输入也先运行不用的数值分支。这是额外成本核查项，尚未以实验判作超时根因。若改成分类后仅计算所需候选，须另审数学/断言与路径变化并重新预算，不把它混入“恢复原 ITE 特殊出口”的说明。
