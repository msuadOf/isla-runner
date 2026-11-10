# 浮点分层细化方案（2026-09-26）

> 2026-09-26 接续接口修订：按用户要求复用既有 Sail 类型，最终共享异常编码复用 `fp_exception_flags`；性能对照后保留局部五Bool事实结构，仅在出口打包一次；共享位序 NV0/DZ1/OF2/UF3/NX4，仅在 ISA 包装转换成 RISC-V flags。直接使用 `float_rounding_mode`，分类复用 `float_bits`/`float_decompose`。本文原RM别名等接口描述保留原设计时点，record为经性能验证后保留的内部表示，现行接口与验证门槛见[类型复用审定](type-reuse-architecture.md)和[实施记录](implementation.md)。

实施顺序、当前版本和用户认可的五条验收标准以 [实施计划](plan.md) 为准。本文件保留具体接口、算法候选和编译注意事项。

现有接口逐项检查见 [修改参考总表](reference-list.md)。本轮补充 ROD=6 的真实 RVV 窄化需求、BF16 无活动元素时的 flags 问题，以及 FP/RM 读取接口的准确限制；此前仅列五种 RM 的设计范围据此修订。

## 状态与目标

用户认可“Isla通用FP原语、共享IEEE异常模型、RISC-V策略”方向，并要求进一步细化。本文件是接口、迁移与验收方案，未实施代码或IR变更。既有调查见 [语义报告](report.md)、[15处ITE清单](ite-boundary.md)。

本轮调查起点为 `isla@85d7c70`、`sail-riscv@f8ce849`。收尾核对发现Isla已更新为合并浮点分支的 `8148bc1`；此HEAD变更不是本轮文档操作产生的。合并后的 `float.rs` 与 `1a1910e` 相同，IR/严格配置未随该次合并变化。上一轮据此以 `8148bc1` 编写设计。正式计划核对时HEAD又更新为 `f4f8e45`，`git diff 8148bc1..HEAD` 无差异；实施基线改记为 `f4f8e45`，继续保留已合入通用改进，模型替代完成后移除已有RISC-V专用分发。Sail库核对的是本机安装的0.20.1（`446fb477`），不是一个已签出的 `sail/` 源码树。既有未提交调查文档保留。示例函数名和伪代码描述契约，不表示现有实现已经提供这些接口或已编译通过。

目标是：完整RISC-V helper语义由模型组合，Isla的FP原语表达与ISA无关的通用运算，已有IEEE数值操作直接调用Z3。确有必要的通用纯组合可以使用已有运算和ITE；ISA的flags、结果规则和状态行为留在模型中。必要的纯条件选择使用现有ITE，避免为模型分层引入额外数据路径fork。异常算法必须精确，不将缺失flags填零或使用已知近似充当已完成支持。

用户补充的主要判断依据和RISC-V/ARM/x86交叉检查见 [实施计划第1节](plan.md#1-要完成什么)：换ISA后含义应保持不变，还要能独立说明操作怎么算，才考虑作为通用primop。共用代码也可以留在Sail共享库；使用ITE本身不构成下沉到Isla的理由。此检查不扩大本次RISC-V实施范围。

## 1. 三部分的输入、输出和职责

本文沿用源码名称：FP 是用于数值计算的浮点值，BV 是原始位串，Bool 是真/假值；“typed RM”表示已经转换成求解器舍入类型的值，不再是 RISC-V 的三位编码。“sort”指求解器中的实际类型。更完整的说明和例子见 [计划第 1 节](plan.md#1-要完成什么)。

| 层 | 输入与输出 | 职责 |
| --- | --- | --- |
| Isla原生FP接口 | typed RoundingMode、FP/BV/Bool → FP/BV/Bool | 原生算术、比较/分类、转换、IEEE编码转换、通用选择；接口与SMT定义一致 |
| 共享IEEE模型库 | 原始IEEE位串、typed RM和必要显式选项 → 数值结果及本次五个异常Bool | sNaN识别，NV/DZ/OF/UF/NX精确条件，不读写架构状态 |
| Sail RISC-V包装 | 原有 `(rm_bits, operand_bits...)` → `(fflags_bits, result_bits)` | rm编码、规范NaN、无效整数转换返回值、比较模式选择和flags编码；指令层继续负责合法性与状态更新 |

FP原语不解释RISC-V的3位rm，也不读取frm、设置FS、决定trap或返回饱和值。IEEE库同样不包含RISC-V CSR位编号和sticky累计。

共享库只实现当前需要的格式/操作。首版使用显式的f16/f32/f64入口，复用内部公共计算；BF16作为单独格式处理，不把它当f16。共享的含义是相同输入下IEEE异常事实可供不同ISA模型使用，并不要求把这段Sail代码放进Isla。判断一个新primop能否进入Isla时，用RISC-V、ARM、x86模型分别代入相同输入：若操作含义会随rm编码、NaN返回位、flags布局或寄存器规则改变，这部分留在各自模型。通用ITE可以在任何一层被调用；是否使用ITE不决定归属。

## 2. 值与类型

原始位串是架构输入，FP值是内部计算值：

```text
input_bits: bits32
input_fp = fp32_from_ieee(input_bits)
```

- 原始位串用于sNaN/qNaN、符号和payload检查；搬运类指令直接处理位串。
- FP值用于原生算术和比较。转换成FP后不能恢复NaN payload/sNaN身份。
- 公共IEEE入口接受原始位串，在函数内创建相应FP值，避免调用方同时提交一对可能不一致的bits/FP参数。
- 共享库可用局部辅助函数复用已经创建的FP值和结果，但这些辅助函数的关系由调用点保证。
- FP/RoundingMode作为内部中间值；最终物化、寄存器值和差分结果仍经BV接口。修订旧稿“直接读取返回None”的表述：`get_finite_domain_var` 的FP/RM抽样返回None；直接 `get_var/get_val` 会报不支持的sort。两者都不能作为直接输出FP/RM的已实现能力，详见 [支撑层S11](inventory-support.md)。

建议异常结果使用命名Bool结构：

```text
IEEEExceptions = {
  invalid: Bool,
  divide_by_zero: Bool,
  overflow: Bool,
  underflow: Bool,
  inexact: Bool
}
```

这是本次操作的事实。Sail自带 `float/common.sail` 的异常bit布局为invalid在最低位、inexact在最高位，与RISC-V不同；不能将其 `bits(5)` 直接转交给架构fflags。可复用既有位分类函数，并在包装处显式打包上述Bool。

## 3. Isla接口工作范围

### 可直接复用

- 既有 `fp_add/sub/mul/div/fma/sqrt`、比较/分类、roundToIntegral、格式转换和整数转换框架。
- 五种typed RM常量及 `%rounding_mode` IR类型。
- 已公开的通用 `ite`，参数为Bool和两个同sort值，适用于BV、FP、RM；复用 `primop_util::ite/build_ite`。
- 既有 `isla_bool_to_bit`、`strict_and_bool/strict_or_bool`，供纯表达式建模。
- `smt_value` 等已有具体/符号值转换工具。

### 需要补齐或修正

1. 保留已随 `8148bc1` 合入的 `ToIEEE` SMT接线及 `FromIEEE` 结果类型修复，补测试并核对SMT打印。
2. 保留已合入的fp32/fp64/fp128 from_signed/from_unsigned目标格式修复并验证。
3. 暴露模型可调用的 `fp*_to_ieee` 和 `fp_to_unsigned*` 原语；沿用现有命名和注册方式。当前注册表有73个通用浮点名称，但这两个出口未公开；不能拿67个 `riscv_*` 名称分发代替通用接口。
4. 使具体BV、符号BV及需要的MixedBits输入使用同一套语义。当前FromIEEE宏只接受Symbolic，不能据此宣称具体输入入口已经可用。正确检查位宽/sort。
5. 用现行SMT初始化和tactic验证FP/BV/RM混合公式，不搬旧测试初始化假设。
6. Sail声明还要包含已有的4个 `fp_to_signed*`，以及新增的ToUnsigned/ToIEEE；本机安装的Sail原生浮点库仅绑定现有73个名称中的69个，缺少这4个signed声明。修正 `softfloat_tests::solve_call` 缺少初始化的问题。声明补齐只使Sail能够调用这些通用接口，不等于67个RISC-V helper已经迁移。

基于合并后的当前HEAD实施。最终移除已有 `executor.rs` 中的 `riscv_*` 名称识别及相应Rust兼容层，前提是等价模型helper和新IR已经完成验证。通用原语通过现有extern注册机制接入，模型helper通过普通IR函数执行。分阶段过程中，旧兼容层的存在不能作为未迁移helper已经符合新方案的证据。

### BF16独立检查点

现有typed IR只区分f16/f32/f64/f128；BF16的(8,8)与f16的(5,11)不同。不能把16位宽度当作完整格式说明。

首选评估一个明确命名、仅进行原生格式窄化和位编码的 `fp32_to_bf16_bits` 通用接口：输入f32和typed RM，输出16位BF16编码；内部使用Z3(8,8)，不附加NaN规范化或flags策略。模型另算异常和结果策略。它可避免为唯一窄化入口扩展所有IR类型。B阶段先用最小编译、输入sort和返回位宽测试冻结此接口形状；若不适合当前Sail类型体系，先由Astra xhigh重新划定接口边界，再进入C/D。D阶段仍负责完整BF16数值、异常和指令验证。此项完成前不声明全部67个helper完成迁移。

该接口的NaN结果位沿用Z3转换的未指定语义。包装应根据原始f32输入的NaN分类选择规范BF16 NaN，不检查返回位串来反推NaN；格式窄化产生NaN当且仅当源值为NaN。sNaN触发NV仍由共享库检查原始输入位。

## 4. 共享IEEE库最小参数

- **舍入模式**：typed RoundingMode，包含五种标准模式；不接收RISC-V保留编码。
- **ROD窄化**：`vfncvt.rod.f.f.w` 明确向f32→f16和f64→f32 helper传入编码6。RISC-V包装识别这个编码，再调用单独的派生窄化函数；普通五种typed RM才传给Z3原生转换。候选算法是RTZ窄化、判定是否精确、对不精确有限结果设置有效数最低位；零、溢出、NaN、无穷及五个flags要分别核对。当前没有证明这套组合在所有边界等价，不能直接当作已完成实现；ROD也不是“中点取奇数”或第六种Z3原生RM。经验证可复用的纯派生计算可放共享Sail库，编码6的解释仍在RISC-V包装中。
- **Quiet/Signaling**：只用于比较异常规则。Quiet对sNaN置NV；Signaling对任意NaN置NV。具体指令使用哪种由ISA包装决定。
- **raise_inexact**：仅用于具有抑制NX语义的roundToIntegral等接口；不改变结果或NV，不作为“允许近似”的开关。
- **tininess**：当前只承诺RISC-V所需的AfterRounding，在函数契约写清。若将来确有其他模型需要BeforeRounding，再增加已经实现并验证的选项；首版不暴露未实现策略。

异常库的位模式分类优先复用当前prelude已经引入的 `<float/interface.sail>`，核对函数是否是纯表达式及是否产生额外控制流，不整段复制分支Rust分类器。

## 5. 三个操作的具体调用过程

### 加法

共享库接口示意：

```text
ieee_add32_after_rounding(rm, a_bits, b_bits)
  -> (result_fp32, IEEEExceptions)

a = fp32_from_ieee(a_bits)
b = fp32_from_ieee(b_bits)
r = fp.add(rm, a, b)
e = 本次Add的精确异常判定(a_bits, b_bits, rm, r)
return (r, e)
```

`e = ...` 是尚未实现的算法位置，不是可直接运行的Sail语句。B阶段加法只在隔离小程序中使用暂名 `demo_f32_add_bits(rm_bits, a_bits, b_bits) -> bits32`：调用通用加法，再返回结果位串，不返回或写入flags，也不使用正式 `riscv_f32Add` 名称。它只检验Sail声明、生成的IR函数体及Isla原生加法调用。C阶段须先补精确异常判定并验证五个异常，才能给正式helper增加完整的 `(flags, bits)` 函数体。

将来完成异常算法后的ISA包装保持现行签名；以下不是B阶段要提交的函数体：

```text
riscv_f32Add(rm_bits, a_bits, b_bits):
  rm = decode_validated_riscv_rm(rm_bits)
  (r, e) = ieee_add32_after_rounding(rm, a_bits, b_bits)
  result = ite(fp.isNaN(r), RISCV_CANONICAL_NAN32, fp32_to_ieee(r))
  flags = pack_riscv_fflags(e)
  return (flags, result)
```

此加法示例的 `decode_validated_riscv_rm` 前置条件由原指令合法性路径保证；不能推广为全部helper只接收0–4，因为ROD窄化接口还会收到6。包装不能通过solver断言静默裁剪非法状态。标量dynamic rm和RVV frm的检查保留在原模型入口。最终flags仍由原Sail指令调用 `accrue_fflags` 累计。

### 浮点转整数

推荐先原生舍入，再检查已舍入值的范围，以替代分支逐舍入模式手写边界表：

```text
x = fp_from_ieee(input_bits)
y = fp.roundToIntegral(rm, x)

valid = isFinite(x) AND exact_integer_range(y, signed, W)
e.invalid = NOT valid
e.inexact = valid AND NOT fp.eq(x, y)
e.divide_by_zero = e.overflow = e.underflow = false

candidate = fp.to_sbv/ubv(RTZ, y)
```

范围为signed的 `[-2^(W-1), 2^(W-1))` 或unsigned的 `[0, 2^W)`。上下界都是二的幂，但必须在足够指数范围的内部格式精确表示；不能在f16中构造2^64。先无损拓宽再比较是首选候选，需证明当前格式/宽度组合全部无损。

`candidate`仅在 `!e.invalid` 时有数值契约。无效域中SMT结果未指定，ISA包装必须屏蔽：

```text
result = ite(e.invalid,
             riscv_invalid_integer_result(input_bits, signed, W),
             candidate)
```

本方案不额外返回option/valid字段；invalid已表达有效性，避免引入重复状态及不必要分叉。未指定的SMT值不是允许写回寄存器的任意结果。

这一路径意在表达f64→i32的两个边界：RNE下2147483647.75先舍为2147483648，应invalid；-2147483648.25先舍为-2147483648，应valid且NX。无符号负小数若舍入为-0，则转换舍入后的y而非负原值。以上是拟议算法的语义推导，尚未编译或动态验证；实施时先用独立参考和边界样本核对，再决定是否采用。

### 比较

```text
ieee_eq32_quiet(a_bits,b_bits):
  result = fp.eq(fp_from_ieee(a_bits), fp_from_ieee(b_bits))
  invalid = is_snan(a_bits) OR is_snan(b_bits)
  其他异常 = false

ieee_lt32_signaling(a_bits,b_bits):
  result = fp.lt(fp_from_ieee(a_bits), fp_from_ieee(b_bits))
  invalid = is_nan(a_bits) OR is_nan(b_bits)
  其他异常 = false
```

先提供确有调用的quiet/signaling入口，避免为了一个布尔参数枚举操作模式。RISC-V的FEQ/FLT/FLE及quiet变体分别调用正确入口。比较真假必须沿用FP语义，包括 `+0==-0`。

## 6. NX/OF/UF的精确性要求

共享库仍有需要完成的算法工作，迁移位置不会自动修复它们。

| 操作 | 可以考虑的实现 | 必须证明或验证的边界 |
| --- | --- | --- |
| Add/Sub | 带指数差证明的精确比较，或有效数/指数位向量辅助计算 | 极大指数差、抵消、Sub独立语义、NaN及无效输入屏蔽 |
| Mul | 足够宽格式中精确乘积与目标结果比较 | 有效数位数及指数上下界都足以容纳精确乘积 |
| Div | 研究精确乘积关系 `rounded_result * divisor == dividend` | 辅助乘积必须精确，限定有效有限域；不能假定宽格式商精确 |
| Sqrt | 研究精确平方关系 `rounded_result^2 == input` | 平方精度/指数范围、负数和NaN/无穷处理 |
| FMA | 精确乘积加加数的一次舍入分析 | 不拆成Mul和Add的两次舍入，不用OF|UF代替NX |
| 转换 | 舍入后范围比较或经证明无损的往返比较 | 正负方向、NaN/无穷、无效域屏蔽、目标精度和指数范围 |

OF需按目标精度和实际舍入模式的规则判断，最终结果为最大有限数也可能上溢。UF需按明确的tininess检测点及精度丢失规则计算；不能从“最终结果次正规/零”直接推出完整判据。最小正规数附近必须有参考差分样本。精确次正规数不应置UF，极小非零值舍入到零必须覆盖。

每个算法要附适用格式及位宽/指数论证。随机差分只证明所测样本；不作为数学精确性的充分证明。

C/D每类异常算法在派发实现前，由Astra xhigh把候选收敛为可审查的契约：输入域和适用格式、五个flags的精确判据、辅助FP/BV宽度及指数范围、纯选择不新增执行分叉的要求、独立参考与失败条件。上表只是研究候选；契约未确定或证据不足的操作维持未完成，不用近似公式填补。

## 7. 模型文件组织与编译边界

拟定热点及职责如下，实际名称沿实施时仓库风格确定：

| 路径 | 变更意图 |
| --- | --- |
| `isla/isla-lib/src/primop/float.rs` | 补通用原语、具体输入处理，保留并验证已合入的格式修复 |
| `isla/isla-lib/src/smt.rs`、`smt/smtlib.rs`、`simplify.rs` | 通用ToIEEE及类型/打印 |
| 新 `sail-riscv/model/prelude/ieee_fp_primops.sail` | SYMBOLIC下声明通用FP原语及typed RM/ITE |
| 新 `sail-riscv/model/core/ieee_fp_exceptions.sail` | 共享纯异常建模库 |
| `sail-riscv/model/core/softfloat_interface.sail` | 保留现行helper名称、签名及C++/Lem绑定 |
| 新 `sail-riscv/model/extensions/FD/softfloat_symbolic.sail` | SYMBOLIC helper函数体及RISC-V结果包装 |
| `sail-riscv/model/extensions/FD/fext_insts.sail`、`dext_insts.sail` | 隔离当前未调用且有错误的 `feq_quiet_S/D`、`flt_S/D`；在定义附近注明不可作为IEEE比较，新路径调用原生浮点比较。将来若要复用，先修正并测试 |
| `sail-riscv/model/extensions/bfloat16/zfbfmin_utils.sail`、`zvfbfwma_insts.sail` | 区分纯BF16转换与会累计flags的转换；修正 `VFWMACCBF16_VF` 在活动元素判断前累计NV的位置 |
| `sail-riscv/model/riscv.sail_project` | 组织依赖；包装在FD_core中放在规范NaN等定义之后 |
| `isla/scripts/run.mk`及FD配置 | 在语义通过后明确浮点目标、IR、tactic和资源参数 |

`isla-sail` 自动设置SYMBOLIC，当前Sail已有条件编译惯例。首选保留现有 `{cpp:...,lem:...}` 声明，在SYMBOLIC下增加函数体；普通C++构建继续走SoftFloat参考后端。

必须先做最小编译验证：B阶段在隔离小程序里确认 `demo_f32_add_bits` 的函数体和比较样本的完整函数体进入IR，内部通用FP/ITE成为正确外部原语；同时确认BF16纯数值接口的类型与IR形状，此时不验收BF16完整语义，也不能为正式 `riscv_f32Add` 安装缺少精确flags的函数体。D阶段再生成测试IR，逐名核对67个原外部helper都有普通IR函数体。当前执行器优先执行IR中的普通函数；只有缺少函数体时，旧RISC-V名称分发才兜底，并非旧分发抢先拦截。需用 `trace_functions` 等调用记录证明测试实际进入模型函数；可在隔离测试构建中把任何进入旧分发的调用改为立即失败，以发现漏迁移。后端可能按外部绑定移除函数体，不能仅凭Sail源码推断IR已经保留。旧正式IR仍有67个无函数体helper，因此D只在隔离候选删除分发；E将正式删除、新IR和匹配严格配置作为同一可运行交付边界。

不能直接include旧 `<float.sail>`：它定义 `rounding_mode = float_rounding_mode`，与RISC-V已有ISA枚举同名。声明应使用独立别名或直接使用 `float_rounding_mode`，类型别名/内部类型可见性由最小编译确认。已有 `<float/interface.sail>` 是另一套位串分类接口，需区分。

## 8. 保持纯计算不fork

现有公开 `ite` 已经支持所需标量类型，不新增 `fp_select/rm_select`。Sail测试中已有其extern声明范例。

1. 纯值选择显式绑定通用ITE；确认IR成为primop，而非只写一个内部包含if的普通同名函数。
2. flags条件使用已支持的严格Bool运算；检查短路表达式是否生成Jump。
3. rm解码选择RoundingMode值，再调用一次原生算术，不生成五份运算结果后选择。
4. 原trap、CSR/寄存器写入、内存访问、合法性检查和循环保持正常控制流。
5. ITE实参是提前求值的；两臂仅允许可安全求值的纯表达式。不能将trap、失败assert或未初始化访问藏进未选中分支。
6. 不将全局linearize当作解决方案。当前linearize会移除assert并要求纯/无环假设；不得据此消除架构检查或待证明前置条件。
7. 通用ITE并非任意Sail类型都可直接使用。Bool/BV及本方案所需FP/RM标量可复用；普通record按字段选择时要核对各字段类型。只有确实传入union/Option等带构造器值时，`build_ite` 中tag未绑定条件、交换两臂未反转条件、同构造器复杂内容未递归等问题才成为该用法的前置修复，见 [ITE接口清单](inventory-ite.md)。当前方案不为结果引入Option，也不把这些问题说成FP/RM标量选择已经失效。

验收同时观察IR、执行器分叉记录和生成的求解表达式。“纯计算零新增数据分叉”检查范围是本次迁移的67个helper及新增纯辅助；原有12个Sail函数体仍需正确性回归，但这条目标不要求消除其查表、循环或已有控制流。零新增数据分叉也不表示求解成本为零。

## 9. 分阶段实施与验收

根规则要求方案确认后再实施代码；用户已认可职责和验收标准，并要求先写计划。正式步骤见 [实施计划](plan.md)，以下保留对应技术要点，各阶段尚未执行。

| 阶段 | 交付 | 完成条件 |
| --- | --- | --- |
| A 通用接口 | 补浮点值转IEEE位串、转无符号整数和具体输入；准备B阶段的BF16最小接口候选和Sail声明清单；验证已合入的格式修复，复用按条件选值的ITE | 对照现有73个名称逐项记录新增和修正；先写失败测试再实现；具体值与约束为同一值的符号输入一致；五种舍入方式及同类型浮点值、位串、舍入方式选择正确。BF16此时只做类型/位宽候选，不验收完整数值或RISC-V函数的flags |
| B 最小调用链 | 在隔离小程序中接通一个完整比较样本、只返回位串的 `demo_f32_add_bits`，并冻结BF16数值接口形状 | Sail→IR保留两个普通函数体，内部通用原语可调用；比较样本验证完整结果与五个flags，加法样本只验证结果及调用结构；BF16最小类型编译通过；纯选择没有新增数据分叉；C++后端仍调用SoftFloat。正式 `riscv_f32Add` 暂不增加残缺函数体 |
| C 逐项完成语义 | 比较、加减乘开方、整数和浮点格式转换、取整，以及两种ROD窄化 | Astra先审定各类异常契约；对**逐项完成**的操作比对完整结果和五个异常；未知舍入方式、NaN、上下界、ROD编码6分别记录。ROD不计入五种普通舍入方式；缺精确异常算法的操作继续标未完成 |
| D 全函数测试 | 完成除法、融合乘加的精确异常、BF16数值/flags及剩余函数；修正BF16无活动元素累计；生成独立测试IR | Astra先审定剩余异常契约；67个原外部函数全部有完整模型函数体，12个已有函数体保留并回归。逐名核对测试IR、用 `trace_functions` 记录实际调用；隔离候选中令进入旧分发立即失败并删除旧分发。正式源码、IR和严格配置此阶段尚不切换 |
| E 正式IR与指令 | 同批集成删除旧分发的源码、新IR及匹配的79份严格配置；运行标量、向量、访存分组和性能测试 | 版本和IR哈希可追溯；五种普通舍入方式另加ROD指令、动态frm、NaN boxing、flags累计、向量mask/vstart及BF16无活动元素测试；89项按XLEN/扩展适用性逐项记录，访存项需真实读写证据，RV32专用项需独立合法编码测试；记录完成率、资源及失败原因 |

阶段B的加法小程序使用不同名称、只返回位串，不存在可被正式指令误用的 `(flags, bits)` 返回值；正式 `riscv_f32Add` 在精确flags完成前仍走旧路径。比较样本可以同时验证调用链和完整五个flags。若比较的flags尚未得到独立参考确认，只记录调用链通过，**此时阶段B仍未完成**。未完成的helper须明确标未实现，不能用旧近似算法补出“通过”的全组结果。

测试分层：

- 原语：正确sort、位宽、具体/符号输入、符号RM与五种具体RM等价、非NaN编码往返。
- IEEE库：本轮及旧报告全部已确认的反例、±0/次正规/最小正规/最大有限/±inf/正负qNaN和sNaN、五种舍入模式、完整五个异常布尔值。旧 `feq_quiet_S/D`、`flt_S/D` 当前没有调用，本次保持隔离并在定义附近注明不可作为IEEE比较；新路径用原生浮点比较。若决定复用，先修正并测试，不把旧函数自身缺陷写成现行指令失败。
- 派生转换：另测 `vfncvt.rod.f.f.w` 的f32→f16和f64→f32，完整结果及flags；包含精确值、不精确有限值、下溢到零、溢出和NaN，不将编码6混入五种原生RM统计。
- ISA包装：RISC-V规范NaN、invalid整数结果、flags位次、quiet/signaling、FROUND/FROUNDNX差别。
- 指令集成：合法/非法rm、动态frm、FPR/VPR、NaN boxing、CSR累计、mask/vstart和inactive元素flags不应累计。
- 已发现的BF16模型问题：`VFWMACCBF16_VF`在mask检查前调用带flags副作用的标量转换。将该累计移到确有活动元素执行的路径，测vl=0、全屏蔽、vstart>=vl且标量为sNaN时旧fflags保持原值；旧flags分别取0与非零值。再测至少一个活动元素时应累计NV。另一个用例只在被vstart跳过的向量前缀中放sNaN，标量和实际执行元素使用普通有限数，确认跳过元素不贡献NV。见 [Sail清单](inventory-sail.md)；这是待动态复现的源码推导。
- 参考源按操作分配：67个原外部helper的结果和flags对照固定版本、RISCV specialization、after-rounding tininess且启用ROD的SoftFloat C后端；BF16还核对其实际编译选项。原有12个Sail函数体（如Recip7/Rsqrte7、窄整数转换）及外层指令不能机械套用SoftFloat标量函数：估算查表对照RISC-V规范表/独立查表实现，窄转换核对规范边界和已有底层转换，mask、vstart、boxing、CSR累计对照指令规范和独立指令参考。逐项记录参考实现、版本、配置及预期位串/flags；若没有独立参考，标待验证。定向边界加随机差分，不以同一公式生成预期值。
- FCVTMOD按截断后模2^32和特殊异常规则检查；有序归约按规定顺序，无序归约按规范允许的结果检查，不能与任意一棵参考树强制逐位相等。上述SoftFloat配置中的RISCV specialization指RISC-V专用规则，after-rounding tininess指按舍入后的规则检测是否过小。89个FD_FLOAT clause还需逐项登记其格式、子操作、XLEN、合法编码及Zfa/BF16等扩展开关，保存实际执行的ROD等指令实例；这些详细登记仍在计划阶段A完成。`C_FLW`/`C_FSW`四项和`FMVH_X_D`/`FMVP_D_X`的合法编码受RV32限定，固定RV64不能证明其合法执行。10个浮点访存条目还需实际读写、写后读和状态证据；当前压缩浮点路径直接执行LOAD_FP/STORE_FP，不能照搬整数压缩指令的ExecuteAs续执行结论。
- 性能：先小型单helper和标量，再RVV；固定线程/超时、tactic、Z3版本、输入配置，分别统计fork、完成路径、超时/unknown、耗时和峰值内存。

现有 `make solve` 仍需作为通用回归，但它排除FD_FLOAT，浮点另需 `make solve-fd-float` 或明确的分阶段指令列表。执行时记录命令、Isla/Sail-RISC-V/Sail/Z3版本、IR哈希、配置、输入约束、退出状态和逐项结果。当前只有静态调查与独立Z3命令行小表达式检查，既不是Isla功能PASS，也不能复用作者旧PASS。

## 10. IR与提交边界

新模型函数体需要重新生成IR。当前正式RV64 IR是VLEN128/ELEN64；`model/CMakeLists.txt:225` 的默认formal配置却是VLEN256。不能仅按target名称推断实际向量长度，生成必须显式固定 `rv64d_v128_e64.json`。

D阶段把新IR放独立验证目录，记录Isla/Sail/Sail-RISC-V版本、配置、命令和哈希；逐名核对67个新函数体及12个已有函数体，并用调用记录排除旧名称分发兜底。D阶段可在隔离候选删除分发，但旧正式IR仍依赖它。E阶段将删除分发的正式Isla源码、新IR和严格配置作为同一可运行边界切换；按 [IR约定](../../specs/ir-workflow.md) 核对79份严格配置、源码区域行列和注释锚点，旧PASS标待复验；不能只改哈希。RV32限定指令另备RV32配置和测试IR，不改变正式RV64 IR的VLEN128约束。

建议提交边界依次为：Isla通用接口与测试；Sail声明/共享库/包装及其验证；全量语义与回归；经验证的新IR及严格配置；父仓库文档与gitlink更新。父仓库gitlink只引用已可获取的子模块提交，保留现有工作树修改。

## 11. 仍需实验确认

- SYMBOLIC函数体与现行extern声明的实际编译结果；native类型可见性及无命名冲突。
- BF16最小公开接口是否满足类型与NaN策略边界。
- 加减乘除、开方、FMA、转换的NX/OF/UF候选算法对各格式是否精确；第5、6节伪代码和算法表均未经过Isla验证。特别先核对加法的非有限输入、极大指数差及定向溢出，再决定能否从B进入C阶段的加法验收。
- ROD的RTZ加最低位置位组合在零、溢出、NaN和flags边界是否等价于参考；BF16转换接口的NaN位选择和带副作用标量转换的活动元素位置。
- 精确Div/FMA/OF/UF辅助算法的性能，当前tactic是否合适。
- shared函数展开和Bool短路是否引入额外fork，不能从Sail外观直接断言。

这些是实施阶段的具体验证点，不是本轮已通过的结果。
