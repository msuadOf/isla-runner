# 浮点 ITE 全量清单与语义边界（2026-09-25）

## 2026-09-26 判断标准补充

用户明确：IEEE数值计算由Z3/Isla通用操作提供，ISA的flags、分支和状态由模型负责；再以“换成RISC-V、ARM或x86，操作含义是否不变”交叉检查。通用ITE属于Isla，带ISA含义的选择条件和候选值属于模型；是否使用ITE不决定归属。共有异常公式仍可由Sail共享库复用。正式标准、例子和实施检查见 [实施计划第1节](plan.md#1-要完成什么)。下文固定提交的15处清单保留，尚未实施迁移。

当前接口的完整复核见 [参考总表](reference-list.md)与[ITE接口清单](inventory-ite.md)。新增确认：ROD窄化实际传rm=6，不能把所有helper限制在0–4；通用ITE的union路径有条件关联和内容选择问题，标量FP/RM路径不经过它。

本文后续行号和 15 处计数固定于 `1a1910e`；当前合并版本 `f4f8e45` 中相关 `float.rs` 内容相同。**15 处是私有浮点实现中调用 ITE 的源码位置；16 项是后来检查的通用选择相关接口，两者不是同一个计数。**计划中的“不新增执行分叉”针对迁移的 67 个纯 helper 及新纯辅助，不要求本次把原有 12 个函数中的所有循环改成表达式。

## 调查范围及结论

用户要求逐项解释浮点分支的所有 ITE，并区分通用 IEEE 浮点计算与 ISA 建模职责。本轮只读核对 `origin/feat/float-support@1a1910e17759d2f52344124dc0b0daa1ff5982bd` 相对 `0008fae` 的8个变更文件，未改实现、运行分支或迁移模型。此前分析见 [报告](report.md)。

新增 ITE 全部在分支 `isla-lib/src/primop/float.rs`：**15处 `ite(...)` 源码调用，分布在13行**；1204、1206各包含两次嵌套调用。645–646的包装定义不重复计数。其余7个变更文件没有新增ITE构造。

加减乘除、FMA、开方、格式转换本身已经直接映射Z3原生FP操作。额外ITE用于舍入编码适配、异常辅助计算以及模型规定的结果/flags编码；没有用这些ITE重新实现浮点加法器或除法器。

“某个条件选择在完整语义中必要”与“它应该硬编码在Isla通用核心里”是两个问题。建议核心保持通用FP原语，IEEE异常条件由共享建模库提供，RISC-V编码与策略由ISA模型组合。该建议供讨论，未实施。

## 三种条件机制

- Rust `if/match`：根据helper名称、格式、signed、quiet等已知元数据选择如何建公式，不是针对符号操作数分裂执行路径。
- SMT `ite(c,t,f)`：一个条件值表达式。分支 `float.rs:646` 构造 `Exp::Ite`，`smt.rs:2193` 翻译，`:1035-1039` 调用 `Z3_mk_ite`。本身不产生Isla执行任务。
- Sail/IR控制流：分支 `executor.rs:1520` 的 `Instr::Jump` 处理符号分支；可行的两侧可能产生fork。不能把9个SMT选择表达式算成512条Isla路径。

表达式ITE仍可增加求解成本；Z3内部可能把FP理论降成含大量布尔选择的电路。迁移到Sail时应核对IR，避免纯值选择被无意展开成多条执行路径，也不能声称消除源码ITE就消除了条件语义。

## 全部15处ITE

以下行号均属于固定提交的 [float.rs](https://github.com/ariscv/isla/blob/1a1910e17759d2f52344124dc0b0daa1ff5982bd/isla-lib/src/primop/float.rs)。伪代码省略类型和Box，`raw`表示原生FP结果的IEEE位向量。

| 序号 | 行号 | 选择内容 | 作用与建议归属 |
| --- | --- | --- | --- |
| 1 | 758 | 按rm=4/3/2/1选择SMT舍入模式 | RISC-V 3位编码→通用RoundingMode。符号rm时构造4层选择，具体rm不构造。映射应归模型；通用primop接受typed rounding mode。现实现所有叶子都是RNE，需修正 |
| 2 | 772 | `ite(flag, 1<<index, 0)` | 每次helper执行5次，将异常Bool打包为bv5。编码应归模型；这个ITE是Bool转位向量的正常表达，不计算异常条件本身 |
| 3 | 810 | `ite(exp_field==0, 1, exp_field)` | Add/Sub的NX算法中，将次正规数/零的指数域统一到最小指数尺度，a/b各一次。应归共享异常建模算法；原生FP数值加减不需要该辅助操作 |
| 4 | 814 | `ite(ea>=eb, ea-eb, eb-ea)` | 取上述指数尺度差的绝对值，服务NX检测。属于共享异常建模算法；当前周围算法仍有Sub/NaN缺陷 |
| 5 | 989 | `ite(signed_i<0, -signed_i, signed_i)` | 有符号整数→f16时取幅值，以检测OF。选择本身合理，归共享异常建模算法；不是整数→FP结果计算所需步骤 |
| 6 | 1081 | `ite(any_nan || invalid, canonical_nan, raw)` | Add/Sub/Mul/Div的RISC-V规范NaN编码。归ISA模型结果策略；Z3原生运算已经负责算出NaN数值 |
| 7 | 1124 | `ite(any_nan || invalid, canonical_nan, raw)` | FMA规范NaN编码。归ISA模型；当前invalid漏无穷乘积加反号无穷，条件不完整 |
| 8 | 1148 | `ite(input_nan || negative_nonzero, canonical_nan, raw)` | Sqrt规范NaN编码。归ISA模型；负qNaN误NV源于共用的invalid谓词，不是这个值选择本身 |
| 9 | 1176 | `ite(input_nan, canonical_nan, raw)` | RoundToInt规范NaN编码。归ISA模型；真正舍入由原生 `fp.roundToIntegral` 执行 |
| 10 | 1204外层 | `ite(isnan, signed_max, sign_default)` | 浮点→有符号整数时NaN规定返回最大值。归RISC-V模型；正负NaN同样处理 |
| 11 | 1204内层 | `ite(isnegative, signed_min, signed_max)` | 无效的有符号转换按符号选饱和值。归RISC-V模型 |
| 12 | 1206外层 | `ite(isnan, unsigned_max, sign_default)` | 无符号转换的NaN返回最大值。归RISC-V模型 |
| 13 | 1206内层 | `ite(isnegative, 0, unsigned_max)` | 无效无符号转换按符号选0或最大值。归RISC-V模型 |
| 14 | 1208 | `ite(nv, invalid_default, fp.to_sbv/ubv(rm,x))` | 有效时用原生转换，无效时选ISA规定结果。语义补全必要，归RISC-V模型；现有范围判定错误会导致选错结果 |
| 15 | 1300 | `ite(input_nan, target_canonical_nan, raw)` | f16/f32/f64格式互转及BF16的目标规范NaN编码。归ISA模型 |

汇总为六类：舍入模式1处、flags打包1处、指数辅助2处、整数幅值1处、规范NaN5处、整数无效返回5处。

## 每类选择是否合理

### 舍入模式

Z3接受RoundingMode类型，不知道RISC-V把RNE/RTZ/RDN/RUP/RMM编码成0/1/2/3/4，也不知道DYN和frm。因此有3位编码输入时，必须有等价的解码关系。

合理形式是一个 `fp.add(decoded_rm,a,b)`，decoded_rm可以是4层ITE；无需计算五份加法再选择结果。若模型直接传入通用RoundingMode，Isla通用FP函数中无需这一段。五种模式的常量primop在分支前已存在（59–71、327–331）；IR也已有 `%rounding_mode` 类型。

本分支 `rm_smt:747-749` 还断言rm在0..4。原先依赖“模型已完成合法性检查”的说明不适用于全部helper：本轮查到ROD窄化会明确传入6，这条断言会排除模型要求的行为。应由模型分别处理普通rm、ROD、动态frm、保留编码和非法指令行为，不能把ISA策略藏在通用原语断言中。

### flags打包

`ite(flag,1<<index,0)`仅把五个异常布尔值编码成 `bv5`，与计算这些异常值的复杂度应分开看。可写成五个1位结果拼接，条件语义仍存在。常量false的flag可被简化；为了删除ITE改写位技巧，没有已经证实的收益。

IEEE定义了异常事实；RISC-V规定fflags的bit布局、与CSR的OR累计、脏状态和回调。前者可以放共享IEEE建模库，后者应在ISA模型。现行 `fdext_regs.sail:521-529` 已在Sail中负责累计。

### 指数差和整数幅值

这三处源码选择都只服务异常检测。Z3数值运算已经处理次正规数和负整数转换。若使用者只需要SMT数值结果，通用primop不应因为内部硬编码RISC-V helper而强制承担这些额外公式。

条件选择本身合理不等于整体异常算法正确：当前Sub误用Add NX公式、NaN屏蔽不足、OF符号比较等问题见 [报告](report.md)。建议将算法作为可单独验证、显式调用的模型库。

### 五处NaN规范化

SMT FP只有一个抽象NaN，不能保留输入的NaN payload、符号或sNaN/qNaN区别。Z3有FP→IEEE BV扩展，但它不等于RISC-V规范NaN策略。f32返回 `0x7fc00000` 等位模式应由模型明确选择。

在RISC-V算术/格式转换结果编码处，可考虑统一组合：

```text
fp_result = native_fp_operation(...)
result_bits = ite(fp.isNaN(fp_result), riscv_canonical_nan, to_ieee(fp_result))
```

这样由Z3判定运算结果是否NaN，减少在结果路径重复枚举无效输入组合。每个结果仍有一次条件选择。NV不能由“结果NaN”直接推导，例如qNaN传播通常不触发NV；原始位模式及操作类别仍用于独立的异常建模。

此建议只针对产生浮点数值的操作；位搬运等需要保持payload的指令应沿用位向量语义，不应经过会丢失NaN信息的FP往返转换。

### 五处整数转换返回选择

SMT `fp.to_sbv/fp.to_ubv` 对NaN、无穷和舍入后越界结果未指定。RISC-V规定这些输入的返回位模式，所以不能直接调用后忽略无效情形。

完整语义需要按有效性选择结果，但返回什么应由ISA模型决定。嵌套默认值可等价合并，例如signed/unsigned分别选择负非NaN边界或最大值；是否改变表达式形状应以可读性、正确性和实测为据。当前主要缺陷在NV条件的边界判定，不能仅删除ITE。

## 构造数量与路径数量

下表数的是每次helper直接执行 `ite()` 包装的次数，排除 `.clone()` 展开的节点、既有输入表达式和Z3内部改写；常量条件也暂计入。不是最终DAG节点数量、求解复杂度或执行路径数。

| helper | 具体rm | 符号rm |
| --- | --- | --- |
| Add/Sub | 9 | 13 |
| Mul/Div/FMA/Sqrt/RoundToInt | 6 | 10 |
| 比较 | 5 | 无rm参数 |
| FP→signed/unsigned整数 | 8 | 12 |
| signed整数→f16 | 6 | 10 |
| unsigned整数→f16、整数→f32/f64 | 5 | 9 |
| FP格式转换/BF16 | 6 | 10 |

复杂条件也能完全由AND/OR表达。例如逐舍入模式转换边界表（916–970）、Eq/Lt/Le的NV条件（1162）、RoundToInt的exact抑制（1177）没有另加ITE，却仍承担建模职责。边界和成本审查不能只搜索ITE。

## 建议的职责与接口

| 层 | 负责内容 | 不应隐含的策略 |
| --- | --- | --- |
| Z3 FP理论 | 原生算术、舍入结果、比较/分类、格式/整数转换的已定义语义 | 不直接返回IEEE异常flags，不指定RISC-V非法转换结果或fflags |
| Isla通用FP原语 | 类型/位宽、舍入模式类型、FP/BV转换、原生操作映射、通用符号选择 | 不绑定RISC-V rm位编码、canonicalNaN、整数饱和值和CSR布局 |
| 共享IEEE建模库 | 每操作的异常条件、sNaN位模式检查、精确性/上溢/下溢检测及必要的明确参数 | 不隐式读写某ISA寄存器；相关策略需要接口声明 |
| Sail RISC-V模型 | rm/frm解析与合法性、quiet/signaling指令选择、规范NaN、无效整数结果、fflags编码/累计、FS和向量状态 | 不手写替代Z3原生数值算术 |

共享IEEE库属于建模层，本计划使用Sail纯函数实现并复用通用FP原语。早期曾讨论将异常库改为native实现的性能选项；**该选项不在本次计划内**，不能据此继续把异常算法放进Isla。以后若确有性能证据要求改变位置，需另写接口、职责变化和等价验证方案。

当前接口 `[softfloat_interface.sail:42]` 为 `(rm,bits,bits)->(flags,bits)`；C包装 `riscv_softfloat.cpp:12-14,60-68` 每次清空SoftFloat flags，返回本次异常及结果；Sail指令随后累计。因此将flags移回建模层必须建立模型包装函数，不能在保留此契约时只删除Rust中的flags并填零。

通用底座已有主要FP操作和舍入模式类型，但本分支仍缺两项模型可调用的出口：新增ToIEEE仅接入SMT层，尚未注册对应Sail primop；ToUnsigned底层已有，却只有ToSigned系列公开primop。明确边界后的实现方案应先核对并补齐这些通用接口，再由模型组合现行helper语义。

本轮未实施任何接口或模型调整。

## 标准与源码证据

- [SMT-LIB FloatingPoint理论](https://smt-lib.org/theories-FloatingPoint.shtml)：单一NaN，不区分quiet/signaling；浮点转整数无效域未指定。标准理论与Z3扩展需区分。
- [SMT浮点理论论文](https://smt-lib.org/papers/BTRW15.pdf)，第3节：明确专注算术，抽象掉exception handling等操作行为。
- 分支 `float.rs:59-71,138-322`：既有通用舍入常量、分类和原生FP运算；`:373-376`是FromIEEE公开绑定；没有ToIEEE公开绑定。
- 分支 `smt/smtlib.rs:105-124`：底层已有ToSigned/ToUnsigned；`float.rs:401-404`公开绑定仅ToSigned系列。
- 当前 `sail-riscv/model/core/softfloat_interface.sail:23,42`、`c_emulator/riscv_softfloat.cpp:60-68`：现行返回flags+result的契约。
- 当前 `sail-riscv/model/extensions/FD/fext_insts.sail:31-72,448-462`、`fdext_regs.sail:521-529`：ISA舍入/flags编码、动态rm合法性及CSR累计。
