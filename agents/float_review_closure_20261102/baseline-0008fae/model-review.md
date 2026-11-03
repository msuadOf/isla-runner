# 模型最小性复审：共同Isla基准0008fae

当前模型数值/特殊值语义已通过先前审查，但按用户最新的“尽量回到原结构”原则，本轮还不是最小结构。下一独立candidate应把18处纯数值输出选择恢复为数据流，并删除已被外层finite判断完全覆盖的mask包装；特殊值、饱和和状态副作用边界保留。这里的“可收敛”是源码/语义结论，不是已验证的运行时间收益，也不否定冻结版本已经完成的正确性验证。

本报告只读审查，没有修改模型、Isla、IR、inputs或当前正式运行。此前独审的PASS证明受测版本正确，不证明该版本在所有等价实现中最小。我此前把“异常显式”扩大为“每个最终异常类别都必须成为路径”，这导致了多加的输出fork。当前未启用FP trap，OF/UF/NX及ROD jam只构造返回flags/bits，不选择陷阱或外部副作用，应保留为数据流。NaN/Inf/零、invalid原因、finite/valid、饱和及changed写回仍是必须保留的控制。本报告直接按这个区分裁决，无需用户再次决定。

## 版本与范围

- **Isla共同基准**：`0008fae76f4cff86dae1a036d889f0414c228e9d`，该SHA属于Isla，不能用于模型仓diff。
- **本轮模型diff**：`6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a` → `21418d0b0d4942fae20061ed580ee04aff4a8a61`。
- **原模型对照基准**：`4f2ac293654a02db26dac5055be7f93fd6e3141e`。只核与本轮有关的flags、窄转换和IEEE后端边界；不扩大审查无关历史功能。

本轮改8个模型文件，648行增加、435行删除；没有新增或删除生产函数。54个既有函数发生语义结构变化，另有两文件中的5条固定RM_RNE汇编映射。逐函数名称、当前源码行号、分类与if词项数见 [核账](model-review.json)，[复核脚本](model-review.py)只读取Git对象并做有限布尔等价检查。if词项数不是路径数。

以下源码路径以根仓`sail-riscv/model/`为基准，行号属于冻结版本21418d0；实际只读核查对象是`.worktree/runner-float/sail-riscv`，未读取根目录dirty模型来推断候选。

## 推荐收敛的部分

| 位置 | 现行结构与判定 | 最小替代及边界 |
| --- | --- | --- |
| `sail-riscv/model/core/ieee_fp_exceptions.sail:132`、`:236`、`:341` 的H/S/D rounded末端，以及`:801`的exact_threshold末端 | 4处各有OF→UF→NX三层if，共12处。此前lo/hi、tiny、overflow及inexact公式已经算好，分支只是构造同一组5位异常事实。属于数值结果编码；这些分支本身不选择新的NaN、Inf、舍入模式或状态副作用。 | 保留所有公式，直接`ieee_exception_facts(false, false, overflow, underflow, inexact)`。对任意8种OF/UF/NX布尔元组都等价，既不假定OF⇒NX，也不假定OF/UF互斥。**删除这12处fork**。OF/UF/NX的分类见证用定向约束/fixture核输出值，不将分类需求扩大成生产返回点的控制层级。 |
| `sail-riscv/model/core/ieee_fp_exceptions.sail:885`、`:935`、`:985`，三个round helper的末层NX if | `raise_inexact && !eq`已经给出NX；两个出口只相差NX位。外层finite与源NaN分类才是特殊值边界。 | 保留源分类和finite gate，将finite臂末端恢复`ieee_exception_facts(invalid_nan, false, false, false, inexact)`，减少3处if。**删除这3处fork**，NX/无NX用输出断言与定向输入验证。 |
| `sail-riscv/model/core/ieee_fp_exceptions.sail:869`，fp_to_int_core的最内层NX if | finite→valid已经决定正常转换还是NV；最内层只编码精确/非精确位。 | 保留finite和valid两层，在valid臂直接返回`ieee_exception_facts(false, false, false, false, inexact)`，减少1处if。invalid的两种上层路径和NaN/Inf饱和不变。 |
| `sail-riscv/model/core/ieee_fp_exceptions.sail:1098`、`:1116`，两个ROD jam if | flags已由RTZ异常计算完成，两个出口使用同一flags，仅选`base_bits`或`base_bits | 1`。这是ROD数值舍入规则，不能仅因结果位改变就认定必须fork。 | 直接恢复原`(flags, ite(ieee_has_inexact(flags), base_bits | 1, base_bits))`，减少2处if；保留ROD/普通模式和NaN canonical控制。**删除这2处fork**，exact/inexact仍通过定向输入核RTZ base、结果位及flags。不能把jam误改为恒1或修改原flags。 |
| `sail-riscv/model/core/ieee_fp_exceptions.sail:841` 的mask helper，以及`:1036/1048/1060/1081/1096/1114`六个调用 | 全部生产调用的第二实参都是字面`true`，调用外层已有finite分支。`operand_invalid(false,a)`在finite臂必为false；传入的exact facts本身NV=DZ=false。因此mask既不改变facts，也不需要再次选择finite。 | 六处直接返回`facts`，保留之前每源`ieee_operand_invalid`调用和外层finite gate；随后删除`ieee_mask_exact_exceptions`定义；全仓test/preserve依赖核账见下文。该helper在6202已有，本轮把它改成if后才与移出的finite gate形成此冗余。**其true实参不会新增独立符号fork**，收益是结构简化，不是已证明提速。不要另加“finite-only”helper替代它。 |

前四行合计18处if可恢复为数据流；第五行另消除一个恒真包装分支和一个无效包装层。它们的实施顺序是在下一独立named模型树改源，再同批调整回归合同、生成新IR和重新验证；当前冻结资产保持原状。尤其不应为使新源码满足旧的“必须三层Jump”检查而保留纯输出分支。

## 下一candidate的精确最小范围与证明义务

模型侧只需改`sail-riscv/model/core/ieee_fp_exceptions.sail`：14个既有函数改返回构造，删除1个mask函数；不动12整数包装、六窄转换、accrue_fflags、ROD模式包装或汇编映射。具体为三个rounded、exact_threshold、三个round、fp_to_int_core、两个ROD helper、三个普通跨格式转换及一个BF16转换。

1. 三个rounded及exact_threshold的末端改为`ieee_exception_facts(false, false, overflow, underflow, inexact)`；原lo/hi、eq、阈值、tiny和舍入方向表达式必须逐字/规范化相同。对任意OF/UF/NX的8个元组，旧三层选择与直接构造逐位相等，已独立穷举，绝不依赖OF⇒NX。
2. 三个round finite臂保留原`inexact`表达式，直接`ieee_exception_facts(invalid_nan, false, false, false, inexact)`；fp_to_int_core valid臂直接`ieee_exception_facts(false, false, false, false, inexact)`。invalid/NX的4个布尔元组逐位相等；finite/valid守卫和原NV出口不动。
3. 两个ROD helper只将末端改回`(flags, ite(ieee_has_inexact(flags), base_bits | 0x0001, base_bits))`与32位的`0x00000001`版本。任意宽度的NX为真选原base|1、为假选原base，flags逐字相同；脚本另核512个8位base/NX组合。这个位选择恒等式不需要对FP舍入作新假设。
4. 六处mask直接返回`facts`：源码有限谓词为`exp != all_ones`，NaN要求`exp == all_ones`，故finite⇒非NaN⇒`operand_invalid(false,a)=false`；四种exact helper均经exact_threshold返回NV=DZ=false，因此`mask(false,true,facts)=facts`。保留调用前源分类及外层finite gate，删除函数和旧checker对其存在性的要求。

这些是静态等价义务；还需在新named树严格检查/生成，核IR仅上述14个函数变化、mask函数消失，所有特殊值与状态控制保持，并做对应定向数值/flags验证。214的77项正式运行继续按214保存，不与新候选混账。不新增生产函数、模式包装或“兼容空壳”。

## 应保留的控制边界

| 位置/数量 | 保留依据 | 最小性意见 |
| --- | --- | --- |
| `sail-riscv/model/extensions/FD/fdext_regs.sail:542`，accrue_fflags | changed决定是否更新FS/SD，以及是否需要F/Zfinx互斥断言。这是状态副作用控制；`flags != 0`不能代替`old != old|flags`。原4f2函数本来就在changed后更新状态。 | 保留changed外层与Ext_F条件。OR及位拼接仍为数据流，不另加按五个flag分别更新Dirty的分支。不要直接改调用`dirty_fd_context_if_present`，它会新增目前SYMBOLIC路径没有的mstatus callback。FFLAGS写回当前位于changed前是6202既有行为；本报告不顺带改该历史事件边界。 |
| `sail-riscv/model/extensions/V/vext_fp_utils_insts.sail:546/555/564/573/579/585`，六窄转换 | overflow决定正常结果/原flags或NV饱和；signed还要区分正端点和负端点。原4f2普通函数已有三出口/两出口，这些不是新造的数值算法分支。 | 保留饱和边界，不机械恢复所有ITE。当前无损符号扩展/高位为零谓词可保留；它们仍是Bool数据流。f16→Ui16的有限正数最大65504，不存在正有限65536饱和，不能据此虚增见证或分支。 |
| `sail-riscv/model/extensions/FD/softfloat_symbolic_f16.sail:51/64/77/90`、f32`:98/111/124/137`、f64`:86/99/112/125`，12整数包装 | invalid选择架构饱和值，NaN包括负NaN始终返回正端点，非NaN invalid再按符号选择端点；普通候选保留。这是特殊值与饱和规则。 | 这12个函数在6202已经存在，本轮未新增12个包装。外层invalid判断读取`ieee_fp_to_int_core`各出口的**字面invalid布尔值**，不应将它一律记为新的独立符号fork；它还防止在valid臂提前执行无关NaN/sign选择。保留当前守卫结构；少写一个if但急切计算invalid_result再用ITE选择，可能反而在普通路径执行不需要的分类。候选native转换仍在外层判断之前，本轮没有借此消除该计算，不得称之为性能修复。 |
| `sail-riscv/model/core/ieee_fp_exceptions.sail:142/168/246/272/351/377/402/428/460/483/525/551/583/606/648/674/706/729`，18算术异常helper | Inf抵消、0×Inf、0÷0、Inf÷Inf、有限非零÷0、负非零sqrt、FMA Inf抵消决定NV/DZ与有效特殊结果。源NaN分类保留；native结果canonical NaN不能代替这些原因。 | 保留特殊原因与普通有限运算的分离。原因谓词中的AND/OR/符号位仍为数据流，不再拆小分支。保留现有各invalid原因路径；mul两个0×Inf位置、div的0÷0与Inf÷Inf、FMA的三项原因是此前特殊值控制覆盖，不能因为同回NV就与纯flags拼装一同删除。 |
| 同18算术helper的finite/valid gate；`sail-riscv/model/core/ieee_fp_exceptions.sail:854`；round`:882/932/982`；转换/BF16`:1032/1044/1056/1077`；ROD`:1092/1110` | 非有限输入不应沿普通有限舍入异常路径继续执行；finite/valid gate将NaN/Inf与普通舍入/阈值比较隔开。源NaN helper只分NaN/sNaN，不能单独分Inf与finite。 | 保留一处实际起作用的gate。尤其若仍保留rounded内OF/UF/NX分支，删outer gate会让特殊输入先经过无用普通分支再被屏蔽。即使把末端flags恢复数据流，保留gate仍有特殊值控制依据；不能以“mask最终清零”代替用户要求的路径边界。也不能因此声称这些原始FP表达式理论不可判定或必然超时。 |
| `sail-riscv/model/extensions/FD/softfloat_symbolic_f32.sail:186`、f64`:174`，两个ROD模式包装 | `rm==6`选择派生ROD，普通臂才解码原生RM并执行普通转换；flags/bits来自同一模式。ROD不是第六个native FP RM。 | 保留模式判断和NaN canonical出口。普通五RM映射与位选择保持数据流，不再拆五个if。可把两臂相同的canonical处理提到模式选择之后，减少文本重复；它不会减少每条路径实际经过的一次NaN分类，不应作为性能成果。f32 ordinary当前按目标NaN分类，若改按源NaN需保留转换保持NaN的合同并重新验数值，当前没有实施。 |
| `sail-riscv/model/extensions/FD/dext_insts.sail:608/638/642`、`sail-riscv/model/extensions/FD/zfh_insts.sail:738/742`，五个固定RM_RNE映射 | 已有真实GNU/Clang文本/编码探针；五个精确转换GNU拒绝显式RM，省略表示RM000。固定RNE专映射解决已复现的表示兼容问题。 | 保留最小20行具体模式优先映射及原generic文本。非零RM不得省略，原显式`, rne`反向声明保留。不增加wrapper、guard框架或新的反向执行辅助；完整reverse mapping既有NonExec边界不靠伪运行掩盖。 |

## 原4f2模型增量的相关边界

`4f2ac293`没有`sail-riscv/model/core/ieee_fp_exceptions.sail`和三份`sail-riscv/model/extensions/FD/softfloat_symbolic_f*.sail`；这些来自此前共享FP后端工作，不是6202→214本轮增加。当前模型使用native FP原语，必须同时有架构flags、NaN canonical、整数异常饱和和派生ROD实现，不能通过删掉这些源文件把新后端伪装成原外部SoftFloat接口。恢复原外部后端是另一个架构选择，不属于本轮最小回改。

与原4f2相关的直接收敛点有两个：changed和普通窄转换原本就有架构控制分支，当前恢复这些控制与原结构一致；`_pure`六适配器与普通六适配器存在历史重复，但本轮没有新建它们。后续若统一，可把已证明等价的位向量饱和体用于原六函数，删除六个`_pure`体并改SYMBOLIC调用点；需要同时验ordinary/SYMBOLIC、active lane、flags与调用边界。没有实测证据支持仅凭`pure`名字、signed转整数或函数数量宣称必须保留/必须删除某个版本，本轮也不为此扩改既有调用图。

`sail-riscv/model/extensions/FD/softfloat_symbolic_f32.sail:14`的`riscv_f32_to_f16_normal_rm_bits`在主项目已无调用，现仅由`sail-riscv/test/symbolic_fp/f32_c.sail:50`的candidate探针使用。它不是本轮新函数；可在后续把相同定义移到该测试文件并维持现有探针，而不是在生产文件保留测试专用接口。主IR已DCE掉它，没有当前运行fork或已证明性能负担；不应为当前最小性复审重做冻结输入。

## mask helper的全仓引用核账

对冻结模型整棵Git受控树执行`git grep -n ieee_mask_exact_exceptions`，只有定义1处和上述6个调用，包含test和脚本在内没有其他引用。另查模型隐藏文本文件、test目录、Isla配置/脚本及`isla/ir/provenance`，没有该符号的preserve条目或直接测试调用。模型端可以在六处改为`facts`后删除定义，不需要保留兼容wrapper。

根仓当前正式`isla/test/float_ir/check_float_closure_branches.py`有三处旧结构依赖：`:541`要求ROD finite臂调用mask、`:696`要求转换helper返回mask、`:737`单独查找mask函数。这三处应在下一candidate对应检查器中改为核finite臂的exact facts赋值/返回及相同NV/DZ/OF/UF/NX数据来源，并去掉对已删mask符号的查找；不应为旧checker绿而保留空壳helper。历史IR、生成清单、review脚本/快照及旧结果里的符号引用是受测版本证据，全部保留；新增候选另有清单，不能静默改旧账。机器可核的引用列表见[核账](model-review.json)的`mask_reference_audit`。

## 永久检查器与证据边界

永久checker已签，不在本轮重写。布尔树解释、12类带符号代表值、FMA组合和定向负控都在测试目录，生产不调用；它们实测抓到了FMA符号、sqrt负零、NV出口等错误，不能仅因测试较长就删除。`defs/reachable/jump`等工具也被迁移后的special检查复用，未发现本轮新建且无人调用的生产级“测试框架”。本轮真正应调整的是将纯数值输出规定为固定Jump层数的合同：一旦采用上述18处收敛，最小替代是核同一OF/UF/NX/RTZ jam表达式和特殊gate/出口，并以等价/负控验数值，而不是再次添加包装层来维持旧分支数。原20个active-lane gate与源NaN分类/特殊原因检查继续保留。

所有建议都没有以未证实的性能推断作依据。固定宽度FP/BV不是因为宽到f128就理论不可判定；本报告也没有逐项A/B超时证据。需要后续实际改动时，原源码/IR/动态PASS只能用于旧冻结版本，新版本应重新冻结并验受影响部分。本次仅完成只读逐项最小性复审及代数替代核账，不新增实现或性能PASS。
