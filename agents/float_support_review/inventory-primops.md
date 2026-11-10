# 通用浮点 primop 参考清单

## 1. 检查范围和判断方法

- 检查日期：2026-09-26；Isla：`f4f8e4584a70588c66c9e7a6286cc20211618f18`。
- 主清单是 `isla/isla-lib/src/primop/float.rs:59–425` 中实际注册的 **73 个名称**：42 个 unary、26 个 binary、5 个 variadic。按注册名称计数，不把 Sail 为不同格式起的别名重复计算。
- `float.rs:428` 之后的 `riscv_*` 专用 helper 分发不属于这 73 个通用原语；它们应与模型函数清单一起审查。不要把“73 个通用原语”与“67 个需要实现的 RISC-V 外部 helper”相加，当作同一种统计。
- 主要依据：IEEE 数值计算调用 Z3 原生操作；异常标志及 ISA 规则由模型负责。再检查：同样的格式、RM 和输入，换成 ARM/x86，原语是否仍有相同含义。
- 本文的“保留”表示职责和直接映射合理，**不表示功能已经通过测试**。本轮没有构建 Isla 或运行其浮点测试；只另外执行了第 7 节列出的独立 Z3 语义探针。

全部注册入口已核对：`primop.rs:4360`、`:4445`、`:4504` 分别合入三个注册表。公共 Z3 映射在 [smt.rs](../../isla/isla-lib/src/smt.rs) 的 `2222–2301` 行，SMT 文本输出在 [simplify.rs](../../isla/isla-lib/src/simplify.rs) 的 `1483–1584` 行。

下表中的 `F` 表示同一种 FP 格式，`RM` 是 SMT RoundingMode 类型，`BV(n)` 是 n 位位串。RM **不是** RISC-V 的 `bits(3)` 编码。

五种原生 RM 不包含 RVV `vfncvt.rod.f.f.w` 实际需要的 round-to-odd（模型内部编码 `6`）。这种派生窄化转换先在模型中用通用转换、位操作和 ITE 表达，不能把编码 `6` 当成第六种 Z3 RoundingMode；具体调用路径和修改要求见 [Sail 清单第 5 节](inventory-sail.md#5-必须补进计划的-round-to-odd)。

“必须”指分层方案接通模型前要修的入口或出口；“保留映射，补检查”指 Z3 操作选择可沿用，但参数类型检查仍要实现。测试也按接口分开：通用 FP 原语检查 Z3 操作及类型；RISC-V helper 只有在 SoftFloat 有同语义 API 时才对照完整结果和 flags；mask、CSR、Recip7/Rsqrte7、FCVTMOD 另按规范/模型测试。

## 2. 73 个已注册名称：逐组列全

实现与注册行号均指 [float.rs](../../isla/isla-lib/src/primop/float.rs)。

| 编号 | 完整注册名称 | 数量 | 输入 → 输出；当前映射 | 处理建议及证据 |
| --- | --- | ---: | --- | --- |
| P01 | `round_nearest_ties_to_even`、`round_nearest_ties_to_away`、`round_toward_positive`、`round_toward_negative`、`round_toward_zero` | 5 | `unit → RM`；分别是 RNE、RNA/RMM、RTP、RTN、RTZ | **保留**通用常量；不在这里读取 rm/frm。实现 `59–71`，注册 `327–331`。每次调用产生一个绑定 SMT 常量的 `Val::Symbolic`。 |
| P02 | `fp16_nan`、`fp32_nan`、`fp64_nan`、`fp128_nan` | 4 | `unit → F`；SMT NaN | **保留**；不能把它当成某 ISA 的 canonical NaN 位串，也不能从它恢复 payload/sNaN。实现 `89–121`，注册 `333–336`。 |
| P03 | `fp16_inf`、`fp32_inf`、`fp64_inf`、`fp128_inf` | 4 | `unit → F`；正无穷 | **保留**。实现 `89–122`，注册 `338–341`。 |
| P04 | `fp16_negative_inf`、`fp32_negative_inf`、`fp64_negative_inf`、`fp128_negative_inf` | 4 | `unit → F`；负无穷 | **保留**。实现 `89–123`，注册 `343–346`。 |
| P05 | `fp16_zero`、`fp32_zero`、`fp64_zero`、`fp128_zero` | 4 | `unit → F`；正零 | **保留**；与负零分别表示。实现 `89–124`，注册 `348–351`。 |
| P06 | `fp16_negative_zero`、`fp32_negative_zero`、`fp64_negative_zero`、`fp128_negative_zero` | 4 | `unit → F`；负零 | **保留**。实现 `89–125`，注册 `353–356`。 |
| P07 | `fp16_undefined`、`fp32_undefined`、`fp64_undefined`、`fp128_undefined` | 4 | `unit → F`；声明一个新的、未约束的 FP 变量 | **保留**；这是产生未知输入，不能替代“尚未实现的计算”。实现 `73–87`，注册 `358–361`。Sail 中应保持 impure 声明，避免多次调用被合并。 |
| P08 | `fp_abs`、`fp_neg` | 2 | `F → F`；`fp.abs`、`fp.neg` | **保留映射，补参数类型检查**。实现 `127–139`，注册 `363–364`。涉及原始 NaN 位保留的搬运/符号注入操作仍用模型位运算。 |
| P09 | `fp_is_normal`、`fp_is_subnormal`、`fp_is_zero`、`fp_is_infinite`、`fp_is_nan`、`fp_is_negative`、`fp_is_positive` | 7 | `F → Bool`；对应 SMT 分类谓词 | **保留映射，补参数类型检查和语义说明**。实现 `140–146`，注册 `365–371`。不能用 `is_negative/is_positive` 读取 NaN 原始 sign 位；不能用 `is_nan` 区分 qNaN/sNaN。 |
| P10 | `fp16_from_ieee`、`fp32_from_ieee`、`fp64_from_ieee`、`fp128_from_ieee` | 4 | `BV(16/32/64/128) → 对应 F`；`(_ to_fp e s)` 对位编码作解释，不是整数转浮点 | **必须修入口**：当前具体 `Val::Bits` 和 `Val::MixedBits` 被拒绝；还需校验位宽。实现 `127–162`，注册 `373–376`。已合入的 `(ebits,sbits)` 顺序修复要保留。 |
| P11 | `fp_sqrt`、`fp_round_to_integral` | 2 | `(RM,F) → F`；`fp.sqrt`、`fp.roundToIntegral` | **保留映射，补参数类型检查**。实现 `165–180`，注册 `383–384`。`round_to_integral` 输出仍是 FP；不带 flags，也不接受“是否抑制 NX”的 ISA/模型参数。 |
| P12 | `fp16_convert`、`fp32_convert`、`fp64_convert`、`fp128_convert` | 4 | `(RM,任一 F) → 指定目标 F`；`(_ to_fp e s)` 的 FP 格式转换重载 | **保留映射，补类型检查**。实现 `182–197`，注册 `386–389`。四个名字按目标格式命名，覆盖各来源格式，不用为每个来源再注册名字。 |
| P13 | `fp16_from_signed`、`fp32_from_signed`、`fp64_from_signed`、`fp128_from_signed` | 4 | `(RM,BV(n)) → 指定目标 F`；把 n 位二进制补码解释成整数后转换 | **必须修具体/混合 BV 入口，补类型检查**。实现 `199–214`，注册 `391–394`。目标 FP 格式修复已合入，应保留；n 是输入整数宽度，不是目标 FP 宽度。 |
| P14 | `fp16_from_unsigned`、`fp32_from_unsigned`、`fp64_from_unsigned`、`fp128_from_unsigned` | 4 | `(RM,BV(n)) → 指定目标 F`；无符号整数转换，`to_fp_unsigned` | **必须修具体/混合 BV 入口，补类型检查**。实现 `216–231`，注册 `396–399`。与 signed 使用不同 Z3 API，不应只改名字共用 signed 语义。 |
| P15 | `fp_to_signed16`、`fp_to_signed32`、`fp_to_signed64`、`fp_to_signed128` | 4 | `(RM,任一 F) → BV(16/32/64/128)`；`fp.to_sbv` | **保留通用转换，补 Sail 声明和类型检查**。实现 `233–236`，注册 `401–404`。数字后缀是目标整数宽度；不能在原语内加 RISC-V 的 NaN/超范围返回值。 |
| P16 | `fp_rem` | 1 | `(F,F) → F`；IEEE remainder，`fp.rem` | **保留映射，补同格式检查**。实现 `255`，注册 `406`。它不接受当前 RM，也不是 C 的 `fmod`。 |
| P17 | `fp_min`、`fp_max` | 2 | `(F,F) → F`；SMT `fp.min`/`fp.max` | **保留通用 SMT 含义，补同格式检查和边界说明**。实现 `256–257`，注册 `407–408`。不能直接作为任意 ISA 的 FMIN/FMAX 完整实现，见第 4 节。 |
| P18 | `fp_lteq`、`fp_lt`、`fp_gteq`、`fp_gt`、`fp_eq` | 5 | `(F,F) → Bool`；`fp.leq`、`fp.lt`、`fp.geq`、`fp.gt`、`fp.eq` | **保留映射，补同格式检查和比较测试**。实现 `258–262`，注册 `410–414`。只返回比较结果；Quiet/Signaling 对 NV 的区别由模型处理。 |
| P19 | `fp_add`、`fp_sub`、`fp_mul`、`fp_div` | 4 | `(RM,F,F) → F`；对应 Z3 原生算术 | **保留映射，补 RM/同格式检查**。实现 `264–299`，注册 `420–423`。已有参数个数检查；没有写错 Add/Sub/乘除映射。不能因为专用 helper 的 flags 有错而改动这些算术含义。 |
| P20 | `fp_fma` | 1 | `(RM,F,F,F) → F`；`fp.fma`，乘加整体只舍入一次 | **保留映射，补 RM/同格式检查**。实现 `301–323`，注册 `424`。不能拆成 `fp_mul` 后再 `fp_add`。 |
| 合计 | 以上每个名称仅计一次 | **73** | unary 42，binary 26，variadic 5 | 已与源码注册表逐个比对，无注册遗漏或同名覆盖。 |

## 3. 应修改或补充的通用接口

### 必须先补：模型改用 primop 时会直接遇到

| 编号 | 要改什么 | 当前证据 | 需要检查什么 |
| --- | --- | --- | --- |
| G01 | **让 FromIEEE、FromSigned、FromUnsigned 接受具体和混合位串** | `float.rs:129–132`、`:168–175` 只匹配 `Val::Symbolic`；原始寄存器/常数可能是 `Val::Bits` 或 `Val::MixedBits` | 同一组 bits 分别用具体、符号、混合形式输入，结果一致。复用 `primop_util.rs:194–222` 的 `smt_value` 等现有转换，不另写一套位串转换。 |
| G02 | **公开 FP→IEEE bits 操作** | `smtlib.rs:90,98` 已有 `ToIEEE(e,s)`，`smt.rs:2253` 已调用 `Z3_mk_fpa_to_ieee_bv`；73 名称中没有出口 | 可按四种格式提供声明，或用一个类型可推导的通用注册名；按项目接口风格定名。返回宽度须由真实 FP 类型确定/核对，不能仅相信随意填入的 `(e,s)`。普通数字、无穷大、正负零可作 bits 往返测试；NaN 不承诺保留输入 payload。 |
| G03 | **公开 FP→unsigned BV 操作** | `smtlib.rs:113`、`smt.rs:2271` 已有 `ToUnsigned`/`Z3_mk_fpa_to_ubv`，`float.rs` 没有相应函数或注册 | 为当前模型至少补 32/64 位无符号出口；若按 signed 家族对称提供 16/32/64/128，四种宽度均需登记验证。NaN/超范围返回值仍在模型选择。 |
| G04 | **补足模型使用的 Sail 原语声明** | 本机已安装 Sail 0.20.1 的 `<float.sail>` 绑定 69 个不同 primop 名称，未声明已有的四个 `fp_to_signed*`；也没有 G02/G03 | 新声明要覆盖 signed、unsigned、FP→bits、typed RM、ITE，并做最小 Sail→IR 编译检查。`<float.sail>` 自己定义 `rounding_mode` 别名，不能不检查命名冲突就整份 include。 |
| G05 | **把 BF16 的格式接口补上** | `FPTy`、IR parser、Sail 插件公开 f16/f32/f64/f128；没有 BF16 `(8,8)` 类型出口 | 评估一个只做“f32 按 RM 转 BF16 bits”的通用原语，或正式扩展类型。不能用 f16 `(5,11)` 代替；不能夹带 RISC-V canonical NaN 和 flags。先用最小编译验证确定方案。 |

### 应一起补：类型错误不能等到 Z3 才发现

| 编号 | 要改什么 | 当前证据 | 建议 |
| --- | --- | --- | --- |
| G06 | **核对 RM 和操作数的真实类型** | 五类宏及 `fp_fma` 只检查是否为 `Val::Symbolic`。一个 symbolic Bool、BV 或另一格式 FP 都会先通过这个 Rust match；`smtlib.rs:1107–1129` 的类型推导也没有检查 RM、右操作数或 FMA 全部输入 | 在通用入口检查：RM 确为 RoundingMode；FP 操作数同格式；FromIEEE 位宽精确相符；整数源为非空 BV。已有 typed Sail 声明能防住正常调用，但 Rust 直接调用或错误 extern 声明仍需明确报错。保持 FP 本体用 symbolic 表示即可，不需新增 host float 表示。 |
| G07 | **验证当前 solver 配置确实处理这些公式** | `float.rs:42–44` 仍写需要 ALL theory；当前实际由 `smt.rs:2119` 的 `configure_tastic` 与 `smt/tactic.rs` 决定，默认 Qfaufbv | 用当前入口验证 FP+BV+Bool+RM 混合公式和符号 RM；再更新说明。不能仅看到源码调用了 Z3 FP API，就声明当前执行配置已验证。 |
| G08 | **增加直接针对通用原语的测试** | 现有三个 Sail property：`fp_add_non_assoc.sat.sail`（非结合性）、`fp_nan_is_nan.unsat.sail`（NaN 分类）、`fp_lteq_max.unsat.sail`（比较/max）；`float.rs` 内新增单测主要走专用 `softfloat_dispatch` | G01–G06 的成功路径和错误输入都要有用例；至少检查零/NaN 比较、五种 RM、f128 参数宽度、FMA 一次舍入及转换范围边界。已有专用 helper 测试不能代替新接口测试。 |

### 可以保留，使用边界要写清

- **FP/RM 求解结果取值**：`get_finite_domain_var` 在 `smt.rs:1743` 对 FP/RM 返回 `None`，仅表示输出多样化不直接选择它们；直接 `get_var/get_val` 走 `get_ast`，会在 `:2012` 报 unsupported sort。两者不可混写成“所有 FP/RM 取值都返回 None”。当前架构结果转成 BV 再输出即可；若将来要直接输出 FP/RM，再单独扩展取值接口。
- **f128 是已有通用能力**：类型是 `(15,113)`，不能随 RISC-V helper 迁移删除。Isla 的 FP 公式可内部使用 f128；完整 f128 输入/输出尚未在本轮运行。128 位 BV 的物化还取决于具体 `BV` 后端的 `MAX_WIDTH`（`smt.rs:1625–1631`），应把公式支持与宿主取值能力分别验证。
- **ToIEEE 的文本打印**：`simplify.rs:1519` 当前写 `(_ fp.to_ieee_bv)`；本机 Z3 4.16.0 能解析。若整理接口，可以统一为通常的 `fp.to_ieee_bv` 拼写，不能把此项写成“当前 Z3 已证实无法解析”的 bug。
- **unit 参数**：RM/常量/undefined 构造函数忽略传入 `Val`，由 Sail 声明保证 unit。若补入口类型检查，可一并检查；优先级低于 G01–G06。

## 4. 容易用错、但不应改成 RISC-V 语义的原语

### `fp_eq` 与普通 `eq_anything`

`fp_eq` 调用 `Z3_mk_fpa_eq`，是数值比较；`eq_anything` 在 `primop.rs:2144–2151` 构造 SMT `=`，是值相等。

| 输入 | `fp_eq` | 普通 SMT `=` |
| --- | --- | --- |
| `+0` 与 `-0` | true | false |
| NaN 与 NaN | false | true（SMT FP 中只有一个 NaN 值） |

因此模型里的浮点数值比较必须显式使用 `fp_eq`，不能因为 Sail 的 `==` 写起来方便就替换它。比较是否要设置 NV，仍要看模型规定及输入原始 NaN 位。

### `fp_min` / `fp_max`

它们应继续表示 SMT 浮点理论的 min/max。该语义在混合正负零时不足以替代 RISC-V 的规定结果；本机 Z3 探针显示 `fp.min(+0,-0)` 取 `+0` 和取 `-0` 都能满足约束。不同 ISA 的 NaN 选择、操作数优先顺序及异常规则也需要分别建模。

因此修改点是 **模型组合与边界测试**，不是把 Isla 的 `fp_min` 硬改成 RISC-V FMIN。RISC-V 模型可以保留已有 bits/比较/ITE 组合；ARM/x86 则组合自己的规则。

### `fp_is_negative` / `fp_is_positive`、`fp_abs` / `fp_neg`

FP 值已经丢失原始 NaN payload/sign/sNaN 区别；例如 SMT `fp.isNegative(NaN)` 为 false。需要实现 `FSGNJ*`、原样搬运、NaN 分类的指令时，必须对原始位串做相应位操作。不能用数值谓词替代“读 sign 位”。

### `fp_to_signed*` 与新增 unsigned 出口

通用转换只在有效范围内有所需的整数结果保证；NaN、无穷大和超范围输入不能拿 solver 的未指定结果直接当 ISA 返回值。模型判断有效性后，用 ITE 选 ISA 规定的结果；这不要求改写 `fp.to_sbv/ubv` 本身。

### `fp_rem`

IEEE remainder 以最接近的整数商决定余数；C `fmod` 使用向零截断的整数商。它们是不同操作。当前 `fp_rem` 直接映射 Z3 remainder 合理，不应为适配某 ISA 同名指令而改变含义。

## 5. 格式、方向、符号性核对

| 项目 | 当前状态 |
| --- | --- |
| f16 / f32 / f64 / f128 | `ir.rs:151–164` 分别为 `(5,11)`、`(8,24)`、`(11,53)`、`(15,113)`；四种类型均有常量、未知值、from_ieee、目标格式转换、signed/unsigned 来源转换 |
| BV bits → FP | 四种 FromIEEE 已注册；具体/混合 bits 入口有 G01 问题 |
| FP → BV bits | SMT 层已有；G02 补公开接口 |
| FP → FP | 四个按目标格式命名的 convert 已注册；不是仅支持某两种格式相互转换 |
| signed BV → FP | 四种目标格式已注册；输入整数宽度可独立指定；G01 修入口 |
| unsigned BV → FP | 四种目标格式已注册；使用独立的 unsigned API；G01 修入口 |
| FP → signed BV | 16/32/64/128 位已注册；G04 补 Sail 声明 |
| FP → unsigned BV | 底层已有、尚未注册；G03 |
| BF16 | `(8,8)`，当前无公开类型；G05 |
| x86 ext80 等格式 | 当前不在 Sail/IR 公开四格式中；不能因支持 f128 就宣称支持 ext80 的存储编码和 x87 规则。本次不扩展为全 x86 支持。 |

## 6. 最小参考修改列表

按优先顺序，后续实施可直接对照：

1. G01：修好位串进入 FP 的三组接口，具体输入与未知输入都能用。
2. G02/G03/G04：让模型可以调用 FP→bits、FP→signed、FP→unsigned，完成输入和输出闭环。
3. G06：核对参数类型、宽度、RM；错误调用应在接口处说明原因。
4. G05：定下 BF16 表达方式，不能拿 f16 代替。
5. G07/G08：在当前 solver 配置下逐项测试；更新过时说明。
6. 在模型一侧处理 `fp_eq`、min/max、NaN 编码、转换失败返回值和 flags；不改通用操作的跨 ISA 含义。

## 7. 本轮做过的检查及限制

静态核对覆盖：73 名称登记、三处注册表接入、FP 类型定义、Sail 插件格式映射、Z3 C API 映射、SMT 文本打印、参数匹配、类型推导、模型取值以及安装的 Sail 原语声明。安装工具版本由 `sail --version` 确认：`Sail 0.20.1 (HEAD @ 446fb477c508853595ccc937ed60765aa685ae31)`；该已安装库不等同于本仓库固定的 Sail 源码版本，实施时仍应核对实际生成工具。

注册数量采用 `primops.insert("名称", ...)` 提取并与安装的 `<float.sail>` extern 名称集合对照：73 个注册，69 个 Sail 绑定，唯一的四个差集是 `fp_to_signed16/32/64/128`。

另外用本机 `Z3 version 4.16.0 - 64 bit` 执行以下独立语义检查：

```smt2
(set-logic ALL)
(define-fun pz () (_ FloatingPoint 8 24) (_ +zero 8 24))
(define-fun nz () (_ FloatingPoint 8 24) (_ -zero 8 24))
(simplify (= pz nz))
(simplify (fp.eq pz nz))
(simplify (= (_ NaN 8 24) (_ NaN 8 24)))
(simplify (fp.eq (_ NaN 8 24) (_ NaN 8 24)))
(simplify (fp.isNegative (_ NaN 8 24)))
(push)
(assert (= (fp.min pz nz) pz))
(check-sat)
(pop)
(push)
(assert (= (fp.min pz nz) nz))
(check-sat)
(pop)
```

通过 `z3 -in` 输入，输出依次为 `false / true / true / false / false / sat / sat`。这确认第 4 节展示的操作差别，**没有验证 Isla 的调用路径、所链接 Z3、求解 tactic 或整条 RISC-V 指令**。额外的 NaN→bits 探针在该版本不允许结果为全零；不能因此推导所有版本的完整 NaN 编码契约，更不能把返回位当成原始 NaN payload。

本轮未修改源码、IR 或配置；没有给通用原语、67 个 RISC-V helper 或完整浮点指令写功能 PASS。
