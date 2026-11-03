# 纯输出选择与特殊值控制的独立意见

2026-11-03后续修订：本页保留e9阶段的历史审查。最新用户“双门”准则和明确结项授权已由[架构裁决](architecture-decision-20261103.md)及[终验范围](../review/acceptance/final-exit-scope.md)取代本页对33个NV/DZ纯返回原因、36个整数结果选择和8个窄转换新增if的保留建议；这77处已批准恢复数据流，NaN结果/饱和值/flags语义仍保留。changed、29 finite/valid及2ROD模式为冻结延期OPEN，不因本页旧解释变成KEEP，也不再阻断本轮限定结项。原18处flags/jam等价结论仍成立，动态证据继续绑定原版本。

结论：同意将4个rounded/exact_threshold末端的OF→UF→NX、3个round末层NX、fp_to_int_core有效臂的NX，以及2个ROD jam恢复为原数据流，共18处if。它们只构造flags或结果位，既无架构状态写入，也不决定是否执行后续特殊值处理。应保留源NaN/sNaN、Inf/零/invalid原因、finite/valid gate、整数饱和、ROD模式和flags changed写回控制；不能把这一结论扩大成“全部if都可改ITE”。

本意见只读，模型、IR和冻结inputs未修改。当前受审模型为`21418d0b0d4942fae20061ed580ee04aff4a8a61`，`core/ieee_fp_exceptions.sail` SHA-256 `23fda9824c2280609062bbe2b9766597681c29af13a1e9cf1be045d9106757a8`。`0008fae76f4cff86dae1a036d889f0414c228e9d`属于Isla；模型用`6202e23f`作本轮前对照，并实际读取该版本Git对象，确认rounded末端和ROD jam原来就是对应facts/ite表达式。模型路径在下文均相对Sail-RISC-V的`model/`。完整逐项边界另见[模型审查](model-review.md)。

## 18处可以恢复数据流

| 位置（21418d0行号） | 精确替代 | 依据与不能省略的内容 |
| --- | --- | --- |
| `core/ieee_fp_exceptions.sail:132/236/341/801`，三个rounded及exact_threshold末端，共12个if | `ieee_exception_facts(false, false, overflow, underflow, inexact)` | 三个布尔量已在分支前算好；每个出口只是把当前条件改写为相同字段中的字面true/false。对OF/UF/NX全部8种布尔组合逐一相等，不依赖OF⇒NX、OF/UF互斥等FP附加定理。保留原精度、阈值、directed bounds、tiny及inexact公式。有限输入溢出后结果为Inf，也不使这个末层flags构造成为源Inf分类。 |
| 同文件`:885/935/985`，三个round的finite臂NX | `ieee_exception_facts(invalid_nan, false, false, false, inexact)` | 两个出口只差NX位；`ieee_empty_exceptions(invalid_nan)`本来就等于其余四位false。保留前面的源NaN处理、finite gate和`raise_inexact && !eq`，不得无条件置NX。 |
| 同文件`:869`，fp_to_int_core的finite且valid臂NX | `ieee_exception_facts(false, false, false, false, inexact)` | 有效转换已由上层finite/valid决定；末层只构造NX。不得删finite/valid或把无效转换也执行这个返回，以免丢NV/饱和边界。 |
| 同文件`:1098/1116`，两个ROD jam | `(flags, ite(ieee_has_inexact(flags), base_bits \| 1, base_bits))`，常量位宽仍分别16/32 | 两臂flags完全相同；base与flags均已算好，无新增急切执行的状态操作。保留RTZ计算、非有限出口、外层ROD/普通模式、NaN canonical和原flags。不能从“jam后结果有无改变”反推NX。 |

本审查实际以独立Python枚举核8组OF/UF/NX、4组invalid/NX，以及全部65,536个16位base×两种NX的131,072组jam，均相等；32位jam由相同的逐位恒等式成立。这里只证明列出的局部替代，不构成尚未实现candidate的Sail类型检查、IR或动态PASS，也没有运行时间结论。

## 具体反例说明改动边界

ROD的三条输入由现有独立SoftFloat程序实际重算（程序SHA-256 `0bb63bc72889502ef6a36cb739589745987a0788eb73d57e0570815a3c228bc6`），命令形式为`.tmp/unified-backend-crosscheck/oracle-build/oracle --op fp_to_fp --fmt f32 --dst f16 --rm 6 --a <输入>`：

| f32输入 | f16 ROD结果 | RISC-V flags | 说明 |
| --- | --- | --- | --- |
| `0x3f800000`（1） | `0x3c00` | 0 | 无条件jam会把精确1改错。 |
| `0x3f800001` | `0x3c01` | NX | 无条件返回RTZ base `0x3c00`会改错。 |
| `0x3f802001` | `0x3c01` | NX | RTZ base本来就为奇数`0x3c01`；jam没有改结果位，仍必须保留NX。 |

反例针对删除jam规则或错误重算flags，不反对用ITE保留该规则。类似地，`round(1.5)`的NX与`round(1)`的无NX仍须由原公式保留；将末层分支改为facts不会改变这两个结果。

控制路径集合会改变，需明确记账：例如f32加法的`1+1`与`1+2^-25`均是有限正常运算，分别精确和非精确；去掉末层NX分支后，不能仅靠这些返回位承诺两类各有一条自然路径。如果初始NX已为1，changed也同为false，架构状态写回守卫不能补回这项见证保证。这是生成集合可能减少，不是facts/ITE计算错误。如仍要求每种OF/UF/NX或ROD exact/inexact都有生成样例，应另列覆盖义务并验证，不能把这个额外目标称为NaN分类正确性所必需。

## mask、整数包装与实际写回

`ieee_mask_exact_exceptions`在整个`model/`和`test/`中只有定义及六个生产调用，均传`true`；六调用全部位于源finite臂。finite蕴含源非NaN，因此此前`ieee_operand_invalid(false,a)`返回false；而exact_threshold构造的facts本身NV=DZ=false。故每个调用均可直接返回facts，再删除无其他调用的mask定义。**只因实参true还不足以证明恒等**：若假设`invalid=true`或传入facts.NV=true，mask会改字段；本案恒等依赖已经核实的finite及facts字段约束。保留此前源NaN处理和finite gate，不新建替代包装；永久静态合同若引用旧helper，应随candidate修订。

12个整数包装的invalid守卫保留。`ieee_fp_to_int_core`非finite/非valid臂返回NV=true，有效臂返回NV=false；移除有效臂末层NX不会改变这个路径内的字面NV。因此源码可证明wrapper读取的invalid在各上游路径已固定，不能按12个if词项自动计成12个新的独立符号fork。invalid臂内部NaN和符号分类仍决定架构饱和值，尤其负NaN也必须返回正端点。具体IR是否已消掉分支由对应版本IR证据确认，本意见不以源码if数量代替IR统计。

`accrue_fflags`的changed必须保留：`old=NX, incoming=NX`时`incoming!=0`但`old|(incoming)==old`，不能再次把Clean/Initial的FS置Dirty；`old=0, incoming=NX`才改变状态。这个守卫控制FS/SD更新与Ext_F/Zfinx断言，属于真实副作用。恢复helper输出数据流不影响该后续条件，亦不授权移动/删除当前FFLAGS写入或callback，不能新增SYMBOLIC路径此前没有的mstatus callback。

本意见支持仅上述纯输出收敛。NaN/Inf/零/invalid原因及有限运算入口、饱和出口和架构写回均保留；不使用未证实的路径爆炸、可判定性或性能理由扩大修改。21418冻结长跑与已签动态结果继续按21418版本保存，后续candidate单独生成和验证，不改旧结果署名。
