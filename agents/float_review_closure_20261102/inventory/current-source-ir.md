# 浮点遗留控制流清单（实施前，只读核查）

## 版本、口径与证据界限

本清单核对 `.worktree/runner-float/sail-riscv` 的模型 `6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a` 和 `.worktree/runner-float/isla` 的源码 `cf1aa1431d5f2d05584c78c0e7c84862a9a9b1fa`。检查的是现成 `rv64d.ir`；其 SHA-256 为 `a877e245cda62b8430b13541faf05a3a2f47719dddad283dd336fa45e068f97e`。未重新生成 IR，未运行新求解，因此现成 IR 与模型的同源关系还须在实施后的严格生成中正式核对。以下“无 Jump”仅指所列函数体内的目标条件；调用方、被调函数可能有其他 Jump。旧证据必须按原版本解释。

`ieee_is_nan/is_snan/is_inf/is_zero` 是纯分类谓词，NaN 操作数行为由 `ieee_operand_invalid` 的显式分支决定，结果 NaN 规范化在当前包装函数已有 Jump。仍须区分异常**原因**、ROD/普通转换、窄整数饱和及 `fflags` 更新引起的状态行为。普通浮点运算、舍入边界公式、逐位 flags 打包及多 lane OR 属数据计算，不因含 ITE 就机械增加分支。一个 Jump 也不表示它支配了目标条件。

现有历史见证：`special_control_restore_20261102/review/report.md` 的 156 条 JSON／3518 断言只覆盖其固定域与 `vl≤2`；`encoding_constraint_isolation_20261102/status.md` 对 `6202e23` 的 `VFUNARY0` f16→i16 给出 46 条完整 Clause JSON 和永久 CFG 回归；`float_review_completion_20261102/data-conditions/report.md` 的 FLEQ/估算见证属于早于 `6202e23` 的模型，不能直接算当前版本 PASS。后续须按实际被读源、完整结果、flags、状态及机器码重新核账。

## 文件所有权建议

独立 Sol 的实施前审查见 [设计审查](../review/model/design-review.md)。本轮正式范围为四个互不重叠的模型文件 owner：FD regs、V 窄 helper、三个 FD wrapper 文件作为一个 owner、core exceptions。下表是文件写边界；本清单 owner 不改生产源码。普通 FP→32/64 整数的 12 个 wrapper、两种 ROD 模式与奇数化均纳入本轮，不留作后续可选项。

| 工作流 | 唯一拟写生产文件 | 并行界限 |
| --- | --- | --- |
| `fflags changed` | `.worktree/runner-float/sail-riscv/model/extensions/FD/fdext_regs.sail` | 独立 owner；与其他模型文件可并行。`isla/` 枚举修复由另一 owner 管理。 |
| 五个窄整数适配器 | `.worktree/runner-float/sail-riscv/model/extensions/V/vext_fp_utils_insts.sail` | 一个 owner 改五函数，保留已恢复 f16→i16 与共同调用关系。 |
| 算术异常原因、finite/valid gate、ROD 奇数化 | `.worktree/runner-float/sail-riscv/model/core/ieee_fp_exceptions.sail` | 单一 owner；与 FD wrapper owner 仅通过函数契约协调，不同时编辑此文件。 |
| ROD 模式与结果配对、12 个普通整数转换包装 | `.worktree/runner-float/sail-riscv/model/extensions/FD/softfloat_symbolic_f16.sail`、`softfloat_symbolic_f32.sail`、`softfloat_symbolic_f64.sail` | 这三个文件交同一个 owner，统一核 NaN/符号饱和与 ROD 同臂 `(flags,bits)`。 |

模型实施仅在 runner-float 模型工作树；根 `sail-riscv/` dirty，不在写边界。IR、配置、父 gitlink 由主 agent 集成。同一个 Clause 的控制流恢复可能跨上述文件，验收按最终合成版本，不把各 owner 的局部证据累加成完整 PASS。

## F1：`fflags` 更新改变架构状态

| 原函数与当前实现 | 实际 IR | 调用者、Clause、格式 | 现有见证与缺口 | 最小改法 |
| --- | --- | --- | --- | --- |
| `FD/fdext_regs.sail:556` 普通 `accrue_fflags` 用 `if old != old|flags` 才写 `fcsr` 并调用 `dirty_fd_context_if_present`；`SYMBOLIC` 版 `:542` 无条件写 `FFLAGS`，`mstatus.bits = ite(changed, dirty.bits, mstatus.bits)`，再调用两个 CSR callback。 | `rv64d.ir:35216` 中 `changed` 为 `znot_bool(zeq_anything(old,f))`，`hartSupports(Ext_F)` 有 Jump；`changed` 仅供 `zitezIB64zK`，无相应 Jump。 | 凡调用 `accrue_fflags` 的标量 FD/Zfh/Zfa、BF16 和 RVV 浮点算术/转换/归约均受影响，H/S/D/BF16；向量还涉及不同 SEW、活动 lane 与合并 flags。 | 旧 ITE/显式对照 `explicit_branch_timeout_diagnosis_20261102/confirmation-report.md` 中 flags Clause 显式版 7200s 外限无完整 JSON；不能写成当前 `6202e23` 预算失败或成功。缺 `old|flags==old` 与新置一两种实际见证、FS/SD/回调后态及完整 Clause 预算。 | 在 `hartSupports(Ext_F)` 臂内以 `if changed` 控制 Dirty 更新；先确认非 F/Zfinx 契约、原断言与 callback 次序。保持 flags OR 值及两 callback，审 IR 中 changed Jump 真臂支配架构状态写。 |

flags 为 5 位，`old` 已含某异常位时，新增运算虽产生相同位，`changed=false`；故 `post & ~old` 只能判新可见位，不能反推本次是否出现异常。状态检验须分别固定旧 flags 全零、已有同位、已有其他位。

## N1–N5：五个窄整数溢出适配器

普通 Sail 函数在 `model/extensions/V/vext_fp_utils_insts.sail:505–545` 以有符号上/下界或无符号上界 `if` 饱和；现用的 `_pure` 函数在同文件 `:547–589`。已恢复的 `f16→i16_pure:547` 用 `if overflow`，其 `rv64d.ir:71407` 有该 Jump。其余五个在当前 `rv64d.ir` 中的 flags 与结果均是 `zitez`；无目标 overflow Jump。所有六个先调用对应 `riscv_f16/f32ToI32/Ui32`，上游 32 位转换还对 NaN／符号／invalid 选择结果；不要把仅恢复窄适配器等同于所有转换特殊值分界已闭合。

| 项 | 原函数；当前 `_pure` 与 IR | 直接调用者及影响 Clause | 格式/SEW、当前证据与缺口 | 最小改法／拟写文件 |
| --- | --- | --- | --- | --- |
| N1 | `riscv_f16ToI8:512` 上/下界 if；`riscv_f16ToI8_pure:554` 用 `overflow = sig32 != sign_extend(low8)`、符号选 `0x80/0x7f`、flags/result ITE；IR `rv64d.ir:71470` 无 overflow Jump。 | `VFNUNARY0` `FNV_CVT_X_F` 与 `FNV_CVT_RTZ_X_F`，`vext_fp_insts.sail:1430,1478`；普通非 SYMBOLIC 臂 `:1351,1405`。 | 源 f16、目标 SEW8；普通 RM0–4/固定 RTZ。当前无该适配器版本绑定的完整溢出两侧见证；须有正溢出、负溢出、范围内、屏蔽/活动 lane，检查 NV 覆盖 NX、目标位和旧 flags。 | 在 `_pure` 内用显式正/负/范围三出口或先 overflow if 后在真臂按符号分支；优先三出口便于两饱和方向各见证。只写 `V/vext_fp_utils_insts.sail`。 |
| N2 | `riscv_f16ToUi8:533` 上界 if；`_pure:575` 用高24位非零与 `0xff` 饱和 ITE；IR `:71653` 无目标 Jump。 | `VFNUNARY0` `FNV_CVT_XU_F`/`RTZ_XU_F`，`vext_fp_insts.sail:1422,1470`；普通 `:1342,1396`。 | 源 f16、目标 SEW8；须区分正越界、NaN/负数由 Ui32 上游饱和、范围内，以及两种 RM 和 lane gate。 | 显式 `if overflow` 返回 `(NV,0xff)`，否则原 `(flag,low8)`；上游 invalid 单列。相同文件。 |
| N3 | `riscv_f16ToUi16:526` 上界 if；`_pure:568` 高16位非零，flags/result ITE；IR `:71596` 无目标 Jump。 | `VFUNARY0` `FV_CVT_XU_F`/`RTZ_XU_F`，`vext_fp_insts.sail:750,782`；普通 `:840,876`。 | 源/目标 SEW16；当前 f16→i16 的 46 条不能替代 Ui16。f16 最大有限值 65504，无法编码 65535/65536；用最大有限对照、+Inf/NaN 导致 Ui32 上游全1再触发窄 overflow、负值转0走 overflow 假臂，另查活动/屏蔽 lane。 | 显式 overflow 真/假臂，保留 `0xffff` 与 flag；同文件。 |
| N4 | `riscv_f32ToI16:519` 上/下界 if；`_pure:561` 与 N1 同型，界 `0x8000/0x7fff`；IR `:71533` 无目标 Jump。 | `VFNUNARY0` `FNV_CVT_X_F`/`RTZ_X_F`，`vext_fp_insts.sail:1431,1479`；普通 `:1352,1406`。 | 源 f32、目标 SEW16；需正/负溢出、范围内、NaN、五 RM、屏蔽与多 lane。 | 三出口显式分界；同文件。 |
| N5 | `riscv_f32ToUi16:540` 上界 if；`_pure:582` 高16位非零，flags/result ITE；IR `:71710` 无目标 Jump。 | `VFNUNARY0` `FNV_CVT_XU_F`/`RTZ_XU_F`，`vext_fp_insts.sail:1423,1471`；普通 `:1343,1397`。 | 源 f32、目标 SEW16；需正越界、NaN/负数、范围内、RM 与 mask；无当前版全义务见证。 | 显式 overflow 真/假臂；同文件。 |

`VFNUNARY0` 的 `SEW8` 浮点目标子操作为非法；但 `X/XU←f16` 在 SEW8 可执行。`SYMBOLIC` 路径 `vext_fp_insts.sail:1306–1489` 的实际活动 lane gate 包住 `_pure` 调用，必须保留。`VFUNARY0` 同样在 `:718–801` 的活动 lane 内调用。现有 f16→i16 的 overflow 真臂仍用符号 ITE 选正/负饱和端点，应与 N1/N4 同时检查三种出口。以 `vl=1` 的完成结果推断多 lane/LMUL/尾部保持会越过证据范围。

## E1–E6：异常原因与结果分类

`model/core/ieee_fp_exceptions.sail` 的下列函数对 H/S/D 三种格式各有一份；当前 `rv64d.ir` 对这些函数体的目标异常条件均为 **0 个 Jump**。被调包装函数对 NaN 结果可能已有 Jump，但 `0÷0` 与 `Inf÷Inf` 可同走 NaN 出口，`finite_nonzero÷0` 与 `Inf÷nonzero` 可同走非 NaN 出口，故不能由结果 NaN Jump 代签异常原因见证。各项均须在原始操作数位模式、实际新 flags、结果与目的状态上验。

| 项 | 原 Sail / `_pure` 当前行为；实际 IR | 调用者、Clause、格式/SEW | 当前见证与缺口；最小改法／拟写文件 |
| --- | --- | --- | --- |
| E1 异号无穷加／同号无穷减 | `ieee_add{16,32,64}_exceptions:234,140,329` 的 `invalid_inf=Inf(a)&Inf(b)&sign不同`；`sub:256,162,351` 为 sign相同。`strict_*` 合成 NV，IR 分别 `rv64d.ir:24846/24523/25199`、`:24937/24614/25290`，六函数无目标 Jump。 | 标量 `F_BIN_RM_TYPE_H/S/D` 的 FADD/FSUB；向量 `FVVTYPE/FVFTYPE/FWVVTYPE/FWVTYPE/FWVFTYPE/FWFTYPE` 相关加减，归约 `RFVVTYPE/RFWVVTYPE` 仅加法。非宽化目标 SEW16/32/64；宽化目标为源 SEW×2，即 32/64。见 `vext_fp_utils_insts.sail:203–213`。 | 现无按此模型和 Clause 的异号/同号无穷单独见证。分别加/减两种符号组合、同格式 finite 对照、sNaN 独立源。只在原因选择处建显式分界，维持 `invalid_nan OR invalid_inf` 及结果包装；写 `core/ieee_fp_exceptions.sail`。 |
| E2 零乘无穷 | `ieee_mul{16,32,64}_exceptions:372,471,570`，`invalid_zero_inf` 为 a零/b无穷 或 a无穷/b零；IR `:25379/25843/26307` 无原因 Jump。 | 标量 FMUL H/S/D；向量 `FVVTYPE/FVFTYPE/FWVVTYPE/FWVFTYPE` 乘法和所有 FMA 经独立 E5 条件；非宽化目标 SEW16/32/64，宽化目标 SEW32/64。`FWVTYPE` 只有加/减，不含乘法。 | 需正负零与 ±Inf 交换位置、非零有限×Inf、sNaN/quiet 对照；显式区分两操作数位置且保留同一 NV 公式。写异常核心。 |
| E3 除法多因 | `ieee_div{16,32,64}_exceptions:393,492,591` 分别算 `0/0`、`Inf/Inf` 为 NV；有限非零/零为 DZ；IR `:25464/25928/26392` 无四种原因 Jump。 | 标量 FDIV H/S/D；`FVVTYPE/FVFTYPE` 中 div/rdiv，SEW16/32/64。 | 需要 `0/0`、`Inf/Inf`、`1/+0`、`1/-0`、`Inf/0`、`0/1`、正常有限除法；各有 NV/DZ/结果位，不以 NaN/非 NaN 二分替代。每个原因显式分界，仍使用原 flags 合成和数值算式；写异常核心。 |
| E4 sqrt 负非零 | `ieee_sqrt{16,32,64}_exceptions:417,516,615`：`negative_nonzero` 与非 NaN 结合置 NV，`-0` 被排除；IR `:25575/26039/26503` 无目标 Jump。 | 标量 `F_UN_RM_FF_TYPE_H/S/D` 的 FSQRT 子项；向量 `VFUNARY1` 的 sqrt 路径，SEW16/32/64。 | 需负有限、`-Inf`、`-0`、`+0`、sNaN/qNaN及正有限。现行 `VFUNARY1` 估算 1.0 与次正规定向证据仅旧模型/SEW32，不能代签 sqrt。显式异常分界；写异常核心。 |
| E5 FMA 两类无效 | `ieee_fma{16,32,64}_exceptions:435,534,633`：零×无穷两位置与 `valid_inf_product` 反号抵消无限加数；IR `:25654/26118/26582` 无目标 Jump。 | 标量 `F_MADD_TYPE_H/S/D` 四种正负变体；向量 `FVVMATYPE/FVFMATYPE/FWVVMATYPE/FWVFMATYPE` 和 BF16 融合 FMA，目标 H/S/D 或 BF16 扩成 S。 | 需乘源互换、积符号与第三源无穷同/反号、第三源 sNaN/qNaN、普通融合边界、活动/屏蔽 lane；原 `fp*_fma` 必须仍只调用一次。显式原因分界，保持 `invalid_nan OR invalid_zero_inf OR invalid_inf_cancel`；写异常核心。 |
| E6 FP→整数上游 invalid 饱和 | `softfloat_symbolic_f16.sail:51–83`、f32 `:98–130`、f64 `:86–122` 的 12 个 32/64 位有符号/无符号包装：`invalid`、NaN、符号决定饱和结果，当前用嵌套 ITE。示例 `riscv_f32ToI32` 的 IR 在包装中没有这些选择的目标 Jump；需对 12 个函数逐项做 IR CFG 回归。 | 标量 `F_UN_RM_FX_TYPE_H/S/D` 的 FCVT_W/WU/L/LU 子项；向量 `VFUNARY0/VFNUNARY0/VFWUNARY0` 等的有符号/无符号/固定 RTZ 实际调用，H/S/D、整数目标 32/64。`FROUND*` 转回浮点，不在这 12 个包装调用集。 | 当前窄适配器恢复不关闭上游 NaN/±Inf/越界/合法舍入。先按每个包装函数确认实际调用范围和 SoftFloat 饱和常量，显式区分 NaN 与正负无效及合法值；不能只按名字批量改。拟写三个 `softfloat_symbolic_f*.sail`，实施前由独立审查确认每项数学等价。 |

异常核心的 flag 事实保留 `NV,DZ,OF,UF,NX` 五 bool 与当前共享/RISC-V 位序。`ieee_*_rounded_exceptions` 的上/下界、tiny、舍入方向为数值判定，五位 flags 打包与 lane OR 是数据组合；若要专门见证五种异常类别，应对实际原始输入和新增位单独测，不能仅为每个位制造条件 Jump。上述 E 类显式分界只约束“不同特殊行为”的原因选择，不改变普通数值计算。

E6 的现成 `rv64d.ir` 逐函数核对：f16 的 `ToI32/Ui32/I64/Ui64` 分别始于 `35595/35634/35673/35712`；f32 为 `36195/36234/36273/36312`；f64 为 `36742/36781/36820/36859`。这 12 个包装函数体各有 **0 个 Jump**，f16/f32 各有 3 个目标 `zitez`，f64 各有 2 个。数字只描述函数体，不代表对应 Clause 已有或缺少何种真实输入见证。

十二个包装的测试不能照抄相同越界数值。例：f16→i64 的有限输入不可能超过 64 位整数范围，仍可用 NaN/±Inf 命中 invalid 饱和；对每种格式/目标宽度先核可达边界，再选择定向输入。

E7 异常 gate 与最终类别：`ieee_f{16,32,64}_rounded_exceptions:195,101,290`、`ieee_exact_threshold_exceptions:671` 的上下界、tiny、舍入方向公式保持数据计算；`ieee_mask_exact_exceptions` 的 finite、`ieee_fp_to_int_core` 的 valid，以及算术各函数的 finite/valid gate 决定特殊输入是否进入普通 OF/UF/NX，应按独立 [设计审查](../review/model/design-review.md) 恢复最终语义分界。NV/DZ/OF/UF/NX 的最终成立/不成立应逐项可见证，但已经由原因分支确定的异常不重复机械分叉；不把每个比较子项和 flags 位拼接都改成 if。拟写文件仍仅 `core/ieee_fp_exceptions.sail`。`ieee_round{16,32,64}_exceptions` 的 sNaN 与可选 NX 同样进入最终类别核账。

## R1–R3：ROD 与其他特殊状态

| 项 | 原 Sail、实际 IR、调用者 | 见证缺口与最小改法／拟写文件 |
| --- | --- | --- |
| R1 ROD/普通模式 | `softfloat_symbolic_f32.sail:174–183` 的 `riscv_f32ToF16`、f64 `:162–172` 的 `riscv_f64ToF32` 以 `rm_bits==0b110` 选择不同 `(flags,bits)`；普通候选用 RTZ 代替非法 RM。IR `rv64d.ir:36441`、`:36988` 对模式用 `zitez`，虽对 NaN 有 Jump，模式本身无 Jump。`VFNUNARY0` `FNV_CVT_F_F` 与 `FNV_CVT_ROD_F_F`（SEW16: f32→f16，SEW32: f64→f32），`vext_fp_insts.sail:1450–1470`；普通 `:1375–1391`。 | 需普通五 RM 与专用 ROD 6、精确/非精确、NaN/Inf/±0、溢出/次正规、活动/屏蔽 lane，核 flags/result 同一模式来源。用单个 `if rm_bits==0b110` 同时选 `(flags,bits)`，保留 NaN canonical 及 RTZ 候选；分别写 f32/f64 包装文件。 |
| R2 ROD 奇数化 | `core/ieee_fp_exceptions.sail:950,961` 的 `ieee_rod32_to_16/ieee_rod64_to_32` 按 inexact 选 `base_bits | 1` 或原 base；IR `rv64d.ir:27550/27604` 无 inexact Jump。 | 同 `VFNUNARY0` 的 ROD 两格式。需精确与非精确输入、结果最低位原0/原1、最大有限/Inf/零/NaN及 OF/UF/NX。只把 `inexact` 导致的两种行为恢复显式 if；`|1` 保持数据运算，flags 公式不变。与 E 类同一核心文件 owner。 |
| R3 估算与 BF16 余项 | `VFUNARY1` 的 `vfrec7/vfrsqrt7` 现有 SEW32/vl1 1.0 和次正规旧版本定向见证；BF16 融合与 scalar/vector/累加器异常源另有历史 oracle。当前 `vext_fp_utils_insts.sail:638–683` 的 Rsqrte7 三格式已有十类显式 `match`；Recip7 `:742–789` 的 ±Inf、±0、s/qNaN、次正规和异常出口也已显式。 | 最终模型须重验 H/S/D、活动/屏蔽、多 lane、flags 和全目的组；无新增估算特殊值 ITE 恢复项。Recip7 三个 wrapper 在分类前无条件算 `recip7(...,true/false)` 两个候选，特殊输入也执行不用的内部控制；列为既存计算成本/预算核查点，尚无实验证明它导致超时，不顺手修改。BF16 另核融合与异常源。 |

## 验证义务与待决

每项先验证普通与 SYMBOLIC 严格编译、四配置 IR 生成、五 IR 同源哈希及目标 CFG 真实支配关系；再按 Clause、格式、SEW、RM/ROD、活动/屏蔽、多 lane、旧 flags 值布置完整预算与定向 oracle。正式完整 Clause 使用固定模型/Isla/配置/官方 Z3、同 seed 与两层 7200 秒上限，记录 finished/partial、JSON 数、SMT timeout、路径账及编码。定向固定输入可证明一个分支的数值/flags/后态，不能替代完整 Clause 或全输入域覆盖。

待独立审查确认：E1–E5 的异常原因是否应逐个设 Jump、同一 NV 的原因如何在保持公式与性能预算下拆分；E6 12 个上游整数包装的调用图/IR 一一核账；R1 普通 RM 与 ROD 仅在各自合法 Clause 可达，不能靠随机 rm_bits 代替指令真实入口。若新 Jump 导致超预算，按计划分辨主树与编码辅助树、已完成/排队路径、单次 SMT 和累计耗时，不缩域后宣称 PASS。
