# 现有 RISC-V 浮点专用实现：逐项处理参考

## 范围

核对版本：Isla `f4f8e4584a70588c66c9e7a6286cc20211618f18`。本文检查 `isla/isla-lib/src/primop/float.rs` 第 430 行之后的专用实现和执行器入口。它们不是前半部分注册的通用浮点 primop，不应混在一起计数。

这是静态源码检查。下面的错误样例来自表达式及 SoftFloat 源码推导，未运行当前 Isla 复现。处理意见按 [计划中的主要判断依据](plan.md#1-要完成什么)：IEEE 数值计算调用通用 Z3/Isla 操作，异常判断和 ISA 规则由模型负责。

表中的“原生操作保留”只指 Z3 数值运算的含义；当前专用异常公式和 RISC-V 结果规则仍需替换。下文两个 i32→f16 边界的预期依据对应 SoftFloat 转换源码；Recip7/Rsqrte7、FCVTMOD、mask 和状态更新不在这套同语义转换对照范围内。

## 1. 名称分发、格式和基础工具

| 函数或类型 | 当前作用与位置 | 处理意见 |
| --- | --- | --- |
| `softfloat_dispatch`、`parse_fp_op`、`parse_int_to_fp` | 按 `riscv_*` 名字选择操作，[float.rs:539](../../isla/isla-lib/src/primop/float.rs#L539) | **模型替代后删除这套分发**。不能改名后当成跨 ISA 通用 primop。`parse_fp_op` 的 Eq 还选错了异常规则，见后表 |
| `SfOp` | 把算术、比较和 ISA helper 参数形状合在一起，[float.rs:526](../../isla/isla-lib/src/primop/float.rs#L526) | 随专用分发退出；通用算术继续使用已有 FP 操作类型 |
| `SfFmt::{from_name,ebits,sbits,width,wide}` | 名称解析、f16/f32/f64 格式及异常计算用宽格式，[float.rs:475](../../isla/isla-lib/src/primop/float.rs#L475) | 通用格式复用 `FPTy`；`wide` 的选择属于具体异常算法，须在模型算法中说明适用范围，不因“更宽”就假定精确 |
| `softfloat_result_struct`、`softfloat_result_width` | 拼接 IR 中 `(flags,result)` 的结构体名，[float.rs:587](../../isla/isla-lib/src/primop/float.rs#L587) | 模型普通函数直接返回原结构，不保留 Rust 对这些生成名称的依赖 |
| 执行器中的 `softfloat_dispatch/softfloat_call` 入口 | 查 IR 结构字段并调用专用计算，[executor.rs:1196](../../isla/isla-lib/src/executor.rs#L1196) | 67 个模型函数接通并验证之后移除，再跑全量函数测试 |
| `bv`、`bv_wide`、`bool`、`and`、`or`、`not`、`eq`、`ite` | SMT 表达式构造小工具，[float.rs:609](../../isla/isla-lib/src/primop/float.rs#L609) | 没有各自新增 Sail primop 的必要；模型复用现有位串、布尔和 ITE 接口。`eq` 是 SMT 相等，不等同浮点数值比较 |
| `fp_ieee_eq`、`fp_pred`、`fp_from_bits`、`fp_to_bits`、`fp_convert` | 构造原生 FP 操作，[float.rs:649](../../isla/isla-lib/src/primop/float.rs#L649) | **保留其原生运算思路**；模型改用公开通用 primop。其中 ToIEEE 的公开出口还需补齐 |
| `bits_exp` | 接受 Symbolic、Bits、Bool；具体位串按至多 64 位处理，[float.rs:725](../../isla/isla-lib/src/primop/float.rs#L725) | 不作为通用 128 位或 MixedBits 转换工具推广；原语复用现有值转换并检查类型。Bool 这里只服务 `roundToInt` 的 exact 参数 |

## 2. 模型应承担的规则与异常函数

| 函数或类型 | 当前作用与位置 | 处理意见 |
| --- | --- | --- |
| `FpPat::{new,exp_field,man_field,sign_bit,exp_ones,is_nan,is_snan,is_inf,is_zero}` | 按原始位串分类，[float.rs:670](../../isla/isla-lib/src/primop/float.rs#L670) | 共享 Sail 模型复用位串分类；原始 NaN 编码必须保留，不能改用会丢失编码的 FP 值恢复 |
| `FpPat::canonical_nan` | 返回 RISC-V 使用的规范 NaN 位串，[float.rs:717](../../isla/isla-lib/src/primop/float.rs#L717) | 移到 RISC-V 模型。其他 ISA 的 NaN 处理不能被这个返回值固定 |
| `RM_MODES`、`rm_smt`、`rm_is` | RISC-V/SoftFloat rm 编码解释，[float.rs:467](../../isla/isla-lib/src/primop/float.rs#L467)、[737](../../isla/isla-lib/src/primop/float.rs#L737) | **修改并移到模型**：符号 rm 恒为 RNE；且 RVV 窄化实际会传入 ROD=6，不能笼统断言全部 helper 的 rm 都在 0–4 |
| `flags_word` 及内层 `bit` | 五个 Bool 编成 RISC-V fflags 位次，[float.rs:770](../../isla/isla-lib/src/primop/float.rs#L770) | 移到 RISC-V 模型，复用 Bool 转 bit 和拼接操作 |
| `add_nx`、`exp_diff` | 宽格式和指数差辅助判断加减是否不精确，[float.rs:786](../../isla/isla-lib/src/primop/float.rs#L786) | **修正算法后放共享模型**：Sub 错用 Add，NaN 和第二操作数无穷的处理错误；不能原样搬迁 |
| `mul_nx` | 宽格式精确乘积与目标结果比较，[float.rs:823](../../isla/isla-lib/src/primop/float.rs#L823) | 放共享模型；保留精确乘积分析方向，但补齐 NaN/无效域屏蔽和对应测试 |
| `sqrt_nx` | 结果平方与输入比较，[float.rs:836](../../isla/isla-lib/src/primop/float.rs#L836) | 放共享模型；负有限输入无效时不能再误置 NX |
| `wide_pow`、`wide_bound`、`Bound::to_exp`、`Cmp::apply` | 构造浮点转整数的范围常数和比较，[float.rs:853](../../isla/isla-lib/src/primop/float.rs#L853) | 随转换异常算法重新设计。`wide_bound` 有内部有效位数不足的问题；简单照搬不安全 |
| `conv_range_nv` | 每种 rm 手写一组越界条件，[float.rs:916](../../isla/isla-lib/src/primop/float.rs#L916) | **重做并放共享模型**。建议先按指定方式舍入成整数值，再检查目标范围；上下界必须能精确表示 |
| `itofp_of` | 整数转 f16 的溢出条件，[float.rs:979](../../isla/isla-lib/src/primop/float.rs#L979) | **重做并放共享模型**。符号比较和向正/负方向舍入的边界都有问题，不只是移动文件 |

## 3. `softfloat_call` 各操作分支

| 分支及所用原生操作 | 当前问题 | 修改参考 |
| --- | --- | --- |
| `Bin::Add/Sub`：原生 add/sub，[1050](../../isla/isla-lib/src/primop/float.rs#L1050) | NX 算法错误；OF/UF 近似；RISC-V NaN/flags 混在 Rust | 保留原生算术，重做共享异常判断，模型选择返回位和打包 flags |
| `Bin::Mul`：原生 mul | NaN/invalid 多置 NX；OF/UF 近似 | 同上；精确乘积比较仅用于允许的输入范围 |
| `Bin::Div`：原生 div | NX 只取 OF 或 UF，普通 `1/3` 漏 NX；OF/UF 近似 | 精确异常判定仍需实现，不能因原生数值正确就标完整支持 |
| `MulAdd`：原生 fma，[1105](../../isla/isla-lib/src/primop/float.rs#L1105) | 漏掉无穷乘积与反号无穷相加的 NV/NaN 处理；NX/OF/UF 近似 | 保持一次舍入的原生 FMA；完整异常与 ISA 结果规则由模型补齐 |
| `Sqrt`：原生 sqrt，[1136](../../isla/isla-lib/src/primop/float.rs#L1136) | 负 qNaN 错置 NV；负有限数错误附加 NX | 分类使用原始位；共享库修正 NV/NX，RISC-V 包装输出规定 NaN |
| `Cmp`：原生 eq/lt/le，[1153](../../isla/isla-lib/src/primop/float.rs#L1153) | Eq 被选成 signaling 规则，qNaN 错置 NV | 数值比较保留；模型明确 quiet/signaling 异常规则 |
| `RoundToInt`：原生 roundToIntegral，[1166](../../isla/isla-lib/src/primop/float.rs#L1166) | 仍依赖错误 rm 解码；ISA NaN/flags 在 Rust | 移到模型组合；保留 exact 参数是否产生 NX 的区别。静态未另发现本分支数值公式错误，不代表已动态通过 |
| `FpToI`：原生 to_sbv/to_ubv，[1180](../../isla/isla-lib/src/primop/float.rs#L1180) | 越界表错误、64 位目标界构造问题、结果规则耦合 | 共享库检查舍入后范围；ISA 选择无效输入的规定返回值。无效域的原生转换结果不能直接写回 |
| `IFp`：原生 signed/unsigned→FP，[1223](../../isla/isla-lib/src/primop/float.rs#L1223) | RTZ 与 RUP 比较漏掉负整数 NX；f16 OF 条件错误 | 数值操作保留，重新实现共享异常算法 |
| `FpToFp` / `softfloat_fp_to_fp`：原生 convert，[1284](../../isla/isla-lib/src/primop/float.rs#L1284) | 窄化 qNaN 多置 NX；OF/UF 近似；ROD=6 不支持 | 区分原生五种模式和模型的 ROD 派生计算，完整检查异常 |
| `ToBF16`：原生 Convert(8,8)，[1267](../../isla/isla-lib/src/primop/float.rs#L1267) | 目前只在专用实现中可用；共用上述窄化异常错误 | 补通用 BF16 数值出口或明确类型方案；ISA NaN/flags 留模型 |

## 4. 本轮新增核实的错误样例

下面均为**源码推导**，后续须建立可运行测试。

| 输入 | 当前实现可推导的行为 | 应有行为及依据 |
| --- | --- | --- |
| `riscv_f32Add(RNE, 1, +inf)` | `add_nx` 的指数差为 128，大于阈值 28；只检查第一个输入有限，因此 NX=1。交换两个输入则 NX=0 | 两种顺序均返回 +inf、flags=0；见 [add_nx:795](../../isla/isla-lib/src/primop/float.rs#L795) |
| `riscv_i32ToF16(RUP, 65505)` | 返回 +inf，但 OF 判断仍用 65520，flags 只有 NX（1） | 应为 OF 和 NX（5）；[i32_to_f16.c](../../sail-riscv/dependencies/softfloat/berkeley-softfloat-3/source/i32_to_f16.c) 转到 exp=0x1d、sig=0x7ff1，[roundPackToF16](../../sail-riscv/dependencies/softfloat/berkeley-softfloat-3/source/s_roundPackToF16.c) 加 15 后触发溢出 |
| `riscv_i32ToF16(RUP, -65520)` | 返回 -65504，错误置 OF，并漏 NX，flags=4 | 应只置 NX（1）。负数向正方向舍入，SoftFloat roundIncrement=0，不触发此处 OF |
| `vfncvt.rod.f.f.w` 的窄化调用，rm=6 | 具体 rm 在 `rm_smt` 中 panic；符号 rm=6 被断言排除 | ROD 是模型实际使用的转换规则，必须支持；见 [Sail 函数清单](inventory-sail.md)。它不是 Z3 的第六种原生舍入方式 |

以往符号 rm、Eq/qNaN、FMA、Sub NX、NaN NX、FP→整数界和 f16 OF 等反例仍适用，见 [原审查报告](report.md)。

## 5. 测试代码也需要调整

- 当前 21 个测试中，20 个经 `solve_call` 求解，1 个只检查分发。它们测试的是旧 RISC-V 专用实现，不能直接作为 73 个通用 primop 或新 Sail 模型的通过证据。
- `solve_call` 直接新建 Solver，未配置当前必须的 SMT 初始化；独立运行这组测试需先修正测试初始化。完整说明见 [支撑层清单](inventory-support.md)。
- `solve_call` 目前只取一个模型里的结果。迁移后应同时确认输入条件可满足，并排除存在错误结果的可能；求解器不确定或超时单列。
- 五个 flags 应整体比较，不能只检查一个掩码；`f32_add_inexact_nx` 实际调用 Mul，名称也需改正。
- 增加五种原生舍入方式、ROD 窄化、符号输入、符号舍入方式、f64 算术、无符号转换、64 位整数目标、负整数、NaN/无穷/正规与次正规边界测试。
- 清理时修正 `float.rs:438` 起“数值/NV/转换精确”的现有注释，避免与已确认错误矛盾。除法/FMA 的 NX 未完成不能以注释或已分发冒充支持完成。
