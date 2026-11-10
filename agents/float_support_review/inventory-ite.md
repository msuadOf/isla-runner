# 浮点相关 ITE 与条件选择接口核对表

调查日期：2026-09-26。源码基线：`isla@f4f8e4584a70588c66c9e7a6286cc20211618f18`，调查时 Isla 子模块无未提交源码修改。本文只做静态核对，未构建、运行测试或修改源码、IR；表中的“可复用”不代表新增动态测试已经通过。

判断依据：IEEE 数值操作由 Z3/Isla 提供；异常、ISA 规定的返回值和状态操作由模型组合。再检查同一操作换到 RISC-V、ARM、x86 后是否含义不变。通用 `ite(condition, true_value, false_value)` 可以由所有 ISA 复用；选择条件和候选值若包含 ISA 规定，就写在模型中。

本文补充 [原 15 处 ITE 分析](ite-boundary.md)，并核对现行 [实施计划](plan.md) 所需的可复用接口。主要源码：[primop.rs](../../isla/isla-lib/src/primop.rs)、[primop_util.rs](../../isla/isla-lib/src/primop_util.rs)、[float.rs](../../isla/isla-lib/src/primop/float.rs)、[executor.rs](../../isla/isla-lib/src/executor.rs)、[smt.rs](../../isla/isla-lib/src/smt.rs)、[smtlib.rs](../../isla/isla-lib/src/smt/smtlib.rs)、[linearize.rs](../../isla/isla-lib/src/ir/linearize.rs)。以下行号均对应上述基线。

## 1. 先给结论

- 浮点方案需要的 Bool、非零位宽 BV、FP、RoundingMode 选择已有通用 `ite`，无需新造 `fp_select`、`rm_select`。
- FP/RM 的常量也保存成 `Val::Symbolic`，所以能够走通用 `ite` 的标量路径；“只支持 Symbolic”在这里不等于“常量不能选择”。
- 普通记录（record/struct）可以逐字段选择，但字段最终必须是受支持的值。不能把这一点扩大为“任意 Sail 类型都支持”。
- `isla_mux2` 接受的是一位 BV 条件，参数顺序为 **条件、false 值、true 值**；它不接受 FP 或 RM 作为两臂。直接使用 Bool 条件时优先用 `ite`。
- 本轮发现通用接口的额外问题：union 的条件关系有缺失，同 constructor 的复杂 payload 也未递归处理。它们应列入修改参考，但不应误报为 FP/RM 标量 `ite` 本身算错。
- “union 需改”仅在方案实际使用符号条件选择 union/Option 时成为本轮前置项；当前 FP/RM 标量和 Bool 字段记录可先使用现有通用路径并补测试。

## 2. 相关接口完整表

| 编号 | 接口与源码位置 | 当前做什么 | 本次处理意见 |
| --- | --- | --- | --- |
| SEL-01 | 公开 `ite`；`primop.rs:4295,4470` | 三参数调用 `primop_util::ite`，顺序为 Bool、true 值、false 值 | **复用**。补上 FP/RM 和符号条件的定向测试；不要新增同义浮点接口 |
| SEL-02 | `primop_util::ite`；`:316` | 条件是具体 Bool 时直接返回一臂；是 Symbolic 时调用 `build_ite` | **复用**。具体条件与符号条件的支持范围不同，见第 3 节 |
| SEL-03 | `build_ite`；`primop_util.rs:224` | 标量建 SMT ITE；struct 逐字段递归；union 有单独处理 | **标量/普通记录复用；union 需改**，问题见第 4 节 |
| SEL-04 | `smt_value`；`primop_util.rs:194` | 将 Bool、Bits、MixedBits、I64、I128、Enum、Symbolic 转为 SMT 表达式 | **复用**。不是任意 Sail 值序列化函数；不能直接接收 Vector、List、Unit、Struct 等 |
| SEL-05 | `float.rs` 私有 `ite`；`:645` | 将三个 `Exp<Sym>` 包为 `Exp::Ite` | **随模型代码迁移收尾**。这是内部表达式包装，不是 Sail primop；其参数类型与 SEL-01/02 不同，不应机械互换 |
| SEL-06 | 公开 `isla_bool_to_bit`；`primop.rs:408,4310` | Bool→bits(1)；符号值用 `ite(b,1,0)` | **复用**。RISC-V 模型可将五个异常 Bool 转一位后拼接，不需要在 Isla 新增 `fflags` 打包 primop |
| SEL-07 | 公开 `bit_to_bool`；`primop.rs:398,4309` | bits(1)→Bool，符号值与 `#b1` 比较 | **按需复用**。直接符号 BV/具体 BV 可用；没有直接 MixedBits 分支。Sail 声明需保证输入是一位 |
| SEL-08 | 公开 `strict_and_bool`、`strict_or_bool`；`primop.rs:460,473,4369,4371` | 两个 Bool 的 AND/OR；具体值简化，符号值建 SMT 布尔表达式 | **复用**。两边都已经求值，只适合纯条件公式，不能靠它保护一侧的断言或副作用 |
| SEL-09 | 公开 `not`、`eq_bool`；`primop.rs:452,454,4312,4373` | Bool 否定、Bool 相等；可组合异常条件 | **复用**，不需浮点特化 |
| SEL-10 | `isla_mux2` / `isla_mux2_internal`；`primop.rs:3250,3274,4479` | `(bits(1), bits(N), bits(N)) -> bits(N)`，顺序为 selector、false、true；检查条件位宽及两臂等宽；Bits、Symbolic、MixedBits 可进入既有转换路径 | **复用**。不能代替 FP/RM 的 ITE；补充符号输出值测试，而不只检查位宽 |
| SEL-11 | `mask_bit_condition` / `select_value`；`primop.rs:3006,3026` | 前者把 BV 中一位变条件；后者用该条件选值，符号分支经 `smt_value` 建 ITE | **保留既有内部用途**。它们不是 Sail 公开接口；不必为浮点再复制一组 |
| SEL-12 | `ite_choice` / 公开 `choice`；`primop_util.rs:331`、`primop.rs:3540` | 给候选值引入新的自由 Bool，表示任意选一个 | **不用来解码 rm 或实现确定的浮点规则**。它是任意选择，不能代替给定条件的 ITE |
| SEL-13 | `ite_phi` / executor 的 `ITE_PHI`；`primop_util.rs:346`、`executor.rs:1076` | 合并控制流已有条件和值；最后候选作为默认值 | **保留内部合并用途**。依赖调用方提供的路径条件，不作为新的浮点 helper 接口 |
| SEL-14 | `Exp::Ite` / `Ast::ite` / SMT 翻译；`smtlib.rs:203`、`smt.rs:1037,2206` | 原生表达式和 Z3 `Z3_mk_ite` 调用 | **保留通用实现**。不负责 RISC-V 规则，不新建执行任务；要求 Bool 条件和两臂相同 SMT 类型 |
| SEL-15 | `Solver::choice`；`smt.rs:2446` | 与 SEL-12 类似，为两个 SMT 表达式创建自由 Bool 后建 ITE | **不用来代替确定规则**；保持现有通用用途 |
| SEL-16 | `linearize::ite_chain` / `linearize`；`ir/linearize.rs:250,376` | 将控制流合并为公开 `ite`；入口先 `drop_assertions` | **不用于整体改写浮点指令**。需保留架构合法性、trap、状态操作；只考虑经过证明和自测的纯函数 |

这些接口自身的条件选择都不创建 executor 分叉任务。若输入表达式此前已经通过 Sail `if` 执行、或求值过程中包含其他分叉，外层套一个 `ite` 不会将已产生的路径合回去。

## 3. 通用 `ite` 到底支持哪些输入

| 条件/两臂 | 静态核对结果 | 需要注意 |
| --- | --- | --- |
| 具体 `Val::Bool(true/false)` | 直接 clone 被选中的值 | 不调用 `smt_value`，因此两臂即使是列表/向量等也可能在具体条件下成功；不能据此声称符号条件也支持这些类型 |
| 符号 Bool + Bool | 支持 | 两臂可分别是具体 Bool 或符号 Bool |
| 符号 Bool + BV | 支持具体 Bits、Symbolic 和非空 MixedBits 的组合 | 两臂最终必须等宽；`smt_value` 按原段顺序拼接 MixedBits |
| 符号 Bool + FP | 支持同格式 FP | 当前 `Val` 没有具体 FP 变体，FP 常量和运算结果都是 Symbolic；不能把 IEEE 原始 BV 直接当作另一条 FP 分支 |
| 符号 Bool + RoundingMode | 支持 | 五个舍入常量 primop 返回 Symbolic 的 RM，见 `float.rs:59-71` |
| 符号 Bool + I64 / I128 | 同类可转 SMT 位向量 | I64 是 64 位、I128 是 128 位，不能直接混选 |
| 符号 Bool + Enum | 可转同一枚举类型的 SMT 值 | 不同枚举类型不能混选；IR 的 typed RM 本身不是 RISC-V 的枚举编码 |
| 符号 Bool + Struct | 按 lhs 字段逐个找 rhs 同名字段，再递归 | 同一声明、字段为 Bool/BV/FP/RM 等的异常记录可用。lhs 有字段而 rhs 无则 Type；rhs 多出字段当前会被忽略，类型一致性依赖前端 |
| 符号 Bool + 同 constructor 的 Union | 只对能被 `smt_value` 接受的 payload 有直接路径 | `Some(bits)` 可以走该路径；结构体 payload 或 `None()` 的 Unit payload 无法经此路径编码 |
| 符号 Bool + 不同/符号 constructor 的 Union | 有实现，但条件关系不完整 | 不能将其作为已正确支持的任意类型选择；详见第 4 节 |
| 符号 Bool + Vector/List/String/Ref/Unit/Poison | 普通标量路径报 Type | 不直接支持按容器逐元素选择；零位 BV 也不是合法 SMT BV 类型 |

当前接口还依赖“输入已正确类型化”：`primop_ite` 没有显式检查参数数量；`ite` 看见 Symbolic 条件后不确认其 SMT 类型为 Bool；`Exp::infer` 在 `smtlib.rs:1098` 只从 true 臂推断返回类型，并不验证 false 臂类型。**“同类型可选”是使用前提，不是接口会自动转换类型。**正常 Sail 声明可以保证很多前提；若补充原语错误输入检查，应按仓库既有错误/不变量处理方式统一，不填默认值继续计算。

已有声明范例见 [unknown_struct_ite.unsat.sail](../../isla/test/property/unknown_struct_ite.unsat.sail):10：

```sail
val "ite" : forall ('a: Type). (bool, 'a, 'a) -> 'a
```

该声明是多态接口，不是运行时支持所有 `'a` 的证明。

### 两臂提前求值

`executor.rs:1748-1753` 会先对全部实参求值，再调用 variadic primop。因此可以这样组合纯值：

```text
raw = fp_to_ieee(native_result)
result = ite(fp_is_nan(native_result), riscv_nan_bits, raw)
```

不能把会 trap、失败断言或写寄存器的操作放进一臂，指望条件为 false 时它不会执行。`strict_and_bool/strict_or_bool` 同理。完整指令中的合法性检查和状态更新继续由正常 Sail 控制流负责。

例如 `ite(mask_bit, accrue_fflags(NV), old_flags)` 即使 `mask_bit=false`，也可能先执行 `accrue_fflags`；正确做法是先用纯表达式选出本元素的 flags，再只在元素实际执行的控制流里累计。BF16 VF 的现有问题正是活动元素检查之前已有带副作用的转换调用，见 [Sail 清单第 6.4 节](inventory-sail.md#64-本次新确认无活动元素时-bf16-vf-仍会置-nv)。

## 4. 本轮新确认的通用接口问题

以下是源码直接能推导的行为，不是本轮运行测试所得结果。它们独立于浮点分支中的 15 处私有 `ite`；FP/RM 标量路径没有经过 union 分支。

### ITE-U1：不同 constructor 的输出没有与条件绑定

`primop_util.rs:250-261` 对不同 constructor 只断言：

```text
result_tag == left_tag OR result_tag == right_tag
```

这里没有使用条件 `b`。因此符号 `b` 被约束为 true 时，`ite(b, A(1), B(2))` 仍允许结果 tag 为 B。它应建立 `result_tag = ite(b, A, B)` 或等价的条件约束。

`:265-281`（Ctor/SymbolicCtor）和 `:286-304`（SymbolicCtor/SymbolicCtor）同样只约束结果 tag 属于候选 tag，没有将选择与 `b` 对应起来。即使公共 constructor 的 payload 用 ITE 合并，tag 仍可能选错。

**意见：通用 union ITE 必须修；浮点接口暂不依赖 union，不把这个问题作为 FP/RM 标量迁移的前置条件。**现有 union 属性测试大量只检查“结果属于某个候选”，并不足以验证结果与选择条件的一一对应。

### ITE-U2：交换两臂时没有反转条件

`primop_util.rs:284` 将 `(SymbolicCtor, Ctor)` 转成 `build_ite(b, rhs, lhs, ...)`。两臂交换后仍用 `b`，会反转公共 constructor payload 的选择。

直接可推导的小例子：左值是 SymbolicCtor，其 tag 被约束为 A、A payload 为 1，右值是 `A(2)`；符号 `b` 被约束为 true。原来应返回 `A(1)`，交换后公共 payload 变为 `ite(b, 2, 1)`，会取 2。修复需维持原两臂方向，或交换时反转条件，同时修好 U1 的 tag 约束。

### ITE-U3：同 constructor 的复杂 payload 不能递归选择

`primop_util.rs:243-249` 对同 constructor 直接对两个 payload 调用 `smt_value`，没有递归 `build_ite`。例如：

```text
ite(b, A({value=1, flag=false}), A({value=2, flag=true}))
```

符号条件下会因 `smt_value(Struct)` 报 Type；`ite(b, None(), None())` 则因 Unit payload 报 Type。若以后浮点接口使用 `Option(result)`，必须先处理这一限制；当前命名 Bool 字段的异常记录不需要 Option。

## 5. `float.rs` 全部 15 处私有 ITE 调用

当前仍有 15 个源码调用点，分布在 13 行；1204、1206 各含外层/内层两次。645-646 的定义不重复计数。下表区分“选择是否需要”和“规则应放哪里”。

| 编号 | 当前行号与所在函数 | 选择内容 | 处理意见 |
| --- | --- | --- | --- |
| FP-ITE-01 | `758`，`rm_smt` | helper 的 3 位 rm 编码选 typed RM | **迁移到模型并修正**：普通五种模式当前在符号 rm 下全变成 RNE，应正确选择五个原生 RM 常量。RVV `vfncvt.rod.f.f.w` 另向窄化 helper 传 `rm=6`（ROD），不能断言所有 helper 的 rm 都在 0..4；ROD 用模型中的派生转换处理，不新增第六个 Z3 RM。见 [Sail 清单第 5 节](inventory-sail.md#5-必须补进计划的-round-to-odd) |
| FP-ITE-02 | `772`，`flags_word::bit` | Bool flag 转为相应的 5 位掩码 | **迁移到 RISC-V 模型**：fflags 位布局是 ISA 约定。复用 `isla_bool_to_bit` 后按 NV/DZ/OF/UF/NX 拼接，或用通用 ITE |
| FP-ITE-03 | `810`，指数辅助函数 | 指数域为 0 时按 1 参与尺度计算 | **迁移到共享异常模型并重审算法**：用于加减 NX 检测；原生数值加减不需要额外操作 |
| FP-ITE-04 | `814`，同上 | 两指数差取绝对值 | **同上**。当前这一段 Add/Sub NX 算法有已知错误，不能原样复制后算完成 |
| FP-ITE-05 | `989`，`itofp_of` | signed 整数负时取相反数得到幅值 | **迁移到共享异常模型并重审算法**：用于 i→f16 OF 判定，不是数值转换；范围与符号比较需一起修 |
| FP-ITE-06 | `1081`，`SfOp::Bin` | Add/Sub/Mul/Div 的 NaN 返回规范位模式 | **迁移到 RISC-V 模型**：用原生结果的 `fp_is_nan` 选择规定 NaN；异常条件单独计算 |
| FP-ITE-07 | `1124`，`SfOp::MulAdd` | FMA 的 NaN 返回规范位模式 | **迁移并修正**：当前输入组合判定漏无穷乘积与反号无穷相加；数值结果 NaN 选择可统一，NV 仍要独立完整建模 |
| FP-ITE-08 | `1148`，`SfOp::Sqrt` | Sqrt 的 NaN 返回规范位模式 | **迁移并修正异常条件**：当前负 qNaN 会被共用负数条件误置 NV；不应把“返回 NaN”当作“必须 NV” |
| FP-ITE-09 | `1176`，`SfOp::RoundToInt` | 输入 NaN 时返回规范 NaN | **迁移到 RISC-V 模型**；实际舍入继续使用 `fp.roundToIntegral` |
| FP-ITE-10 | `1204` 外层，`SfOp::FpToI` | signed 转换遇 NaN 返回整数最大值 | **迁移到 RISC-V 模型**。该返回值不能成为通用 `fp.to_sbv` 的隐藏规则 |
| FP-ITE-11 | `1204` 内层，同上 | 无效 signed 转换按符号选最小/最大值 | **迁移到 RISC-V 模型** |
| FP-ITE-12 | `1206` 外层，同上 | unsigned 转换遇 NaN 返回全 1 | **迁移到 RISC-V 模型** |
| FP-ITE-13 | `1206` 内层，同上 | 无效 unsigned 转换负值选 0，否则全 1 | **迁移到 RISC-V 模型** |
| FP-ITE-14 | `1208`，同上 | 有效转换用原生整数结果，无效时用规定值 | **迁移并修正有效范围判断**。ITE 合理；当前 NV 边界错误导致选择错误。原生转换在无效域未指定，不能直接写回 |
| FP-ITE-15 | `1300`，`softfloat_fp_to_fp` | f16/f32/f64/BF16 转换的目标规范 NaN | **迁移到 RISC-V 模型**。BF16 先依据原始输入判断 NaN，不能从未指定的 NaN 编码输出反推 |

六类计数：rm 解码 1、flags 打包 1、指数辅助 2、整数幅值 1、规范 NaN 5、无效整数返回 5。

15 是源码调用点数，不是每次执行的 ITE 数，也不是执行路径数。例如 rm 那一处在符号输入时建四层 ITE，flags 打包那一处每次执行五次。它们最终都只是值表达式。

## 6. 需要修改和需要验证的参考清单

| 项目 | 是否是本次浮点分层的必做项 | 如何检查 |
| --- | --- | --- |
| 将 FP-ITE-01/02/06-15 的 ISA 规则迁入 Sail-RISC-V | 是；模型替代验证后移除旧 Rust 路径 | 比较生成 IR 中 helper 函数体与通用 primop 调用；没有 RISC-V helper 名称特判时仍能运行 |
| 修正符号 rm 恒 RNE、ROD 缺失，以及相关 NV/NX/OF/UF 判断 | 是 | 普通五种 rm 的具体输入与“符号输入再约束为同值”得到一致结果；另测 `vfncvt.rod.f.f.w` 的 f32→f16、f64→f32（helper 编码 6），仅对应的窄化数值 helper 与启用 ROD 的 SoftFloat 同语义转换对照；指令 mask、写回、累计 flags 另测，不能把 6 排除后算通过 |
| FP-ITE-03/04/05 所在异常算法移入共享 Sail 库 | 是 | 精确异常测试通过后再替代；不要按 ITE 数目判断算法是否正确 |
| Bool/BV/FP/RM 标量 ITE 的定向测试 | 是，复用前验证 | 分别约束条件 true/false，输出必须与被选值一致；FP 包含 NaN、正负零，RM 选择影响实际舍入结果 |
| struct 的 Bool/FP/RM 字段选择测试 | 若模型需要整体选择记录 | 同一条件选中所有字段，不能出现两臂字段混搭；逐字段使用也应覆盖 |
| ITE-U1/U2/U3 union 缺陷 | 通用缺陷需记录；仅在方案使用 union/Option 选择时成为前置项 | 约束条件及 tag 后检查不能选另一臂；覆盖左右 SymbolicCtor 顺序、结构 payload、Unit payload |
| MixedBits 输入与符号 mux2 测试 | 模型使用这类输入时需验证，未发现需要改变当前顺序的依据 | 约束 selector 和分段中的符号后比较完整结果；覆盖符号/具体交错、不等段宽 |
| 原语数量、类型前提检查 | 可与通用原语整理一起做，不作为数值正确性的替代 | 不接受错误数量、非 Bool 条件或异类型两臂后继续计算；保持既有内部错误处理规则 |
| 避免迁移的 67 个 helper 及新纯辅助的数据选择生成 Jump/fork | 是 | 检查生成 IR 和实际路径记录；原架构分支不应因此消失。原有 12 个函数体仍须正确性回归，不要求本次消除其全部查表和循环 |
| `linearize` 整体套用 | 不建议 | 此入口会移除断言，不能用它替代对模型纯函数和控制流的逐处检查 |

现有测试文件包括 `unknown_struct_ite.*`、`union_ite_*`，以及 `primop.rs:5497` 的 Bool→bit、`:5939` 的 mux2 测试。后两者的符号案例目前只查结果位宽，没有验证 true/false 条件下的输出值。目录中的三个 `fp_*` 属性测试也没有覆盖 FP/RM 的条件选择。上述均为测试源码覆盖范围检查；本轮未执行它们。
