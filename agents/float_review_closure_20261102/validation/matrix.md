# 浮点遗留项验证矩阵

本表规定验收义务，不表示逐项已经 PASS。实施基线为模型 `6202e23`、Isla `cf1aa14`、父仓 `a6b6ecd`、旧 IR `a877e245…`；本轮实际预算输入见[最终清单](inputs.model-21418d0-itrace.json)，固定模型 `21418d0`、Isla `42000be`、四份新生成 IR、官方 Z3、trace 版二进制与 seed17。受影响64 Clause与兼容13 Clause分别核账。旧 56 项定向语义/SoftFloat、三表示及 Make 结果只作可复用方法和历史对照，不能迁为最终版 PASS。

## 义务与实际入口

| 义务 | 源函数/格式 | 真实 Clause 与合法 SEW | 必须观察的分界、结果和状态 |
| --- | --- | --- | --- |
| F1 flags changed | `accrue_fflags`，H/S/D/BF16 及所有浮点调用者 | 标量算术、转换、BF16；下列向量/归约 Clause | `old=0,new=0`、旧位已覆盖新位、旧位不同而新增、首次新增；FFLAGS=`old|new`、FS/SD、其余 mstatus 位与 callback。整指令写 FPR 可独立置 Dirty，须用 helper 定向检验 changed 假臂。 |
| N0–N2 f16 窄有符号/无符号 | `f16ToI16/I8/Ui8/Ui16_pure`，H 源 | `VFUNARY0` SEW16：i16/ui16；`VFNUNARY0` SEW8：i8/ui8 | signed 正/负溢出与范围内、unsigned 上游负饱和0/NaN/Inf/上界、NV 覆盖 NX、旧 flags。N0 是已有恢复项，须在合成版重新验。 |
| N3–N4 f32 窄有符号/无符号 | `f32ToI16/Ui16_pure`，S 源 | `VFNUNARY0` SEW16 | 32767/32768 与 −32768/−32769，65535/65536、范围内 inexact、NaN/±Inf、NV 与 NX；正常五 RM 与固定 RTZ opcode。 |
| E1 加减无穷抵消 | `ieee_add/sub{16,32,64}_exceptions` | `F_BIN_RM_TYPE_H/S/D`；`FVVTYPE/FVFTYPE` SEW16/32/64；`FWVVTYPE/FWVTYPE/FWVFTYPE/FWFTYPE` 源SEW16/32→目标S/D；`RFVVTYPE/RFWVVTYPE` 仅加法 | add 异号 Inf、sub 同号 Inf 的 NV，与有效 Inf 及有限对照；左右源独立 sNaN/qNaN。 |
| E2 零乘无穷 | `ieee_mul{16,32,64}_exceptions` | 标量 FMUL、`FVVTYPE/FVFTYPE/FWVVTYPE/FWVFTYPE`；FMA 另见 E5 | +0/−0 与 ±Inf 的左右源互换、普通有限×Inf；NV、结果位。`FWVTYPE` 无乘法。 |
| E3 除法原因 | `ieee_div{16,32,64}_exceptions` | 标量 FDIV；`FVVTYPE/FVFTYPE` SEW16/32/64 | 0/0、Inf/Inf 各 NV；有限非零/±0 为 DZ；Inf/0、0/有限、正常有限分别对照。相同 NaN 出口不能合并两种 NV 原因。 |
| E4 负非零平方根 | `ieee_sqrt{16,32,64}_exceptions` | `F_UN_RM_FF_TYPE_H/S/D`、`VFUNARY1` SEW16/32/64 | 负有限、−Inf 为 NV；−0/＋0、正有限、sNaN/qNaN 分开；目标和原 flags。 |
| E5 FMA 两类无效 | `ieee_fma{16,32,64}_exceptions` | `F_MADD_TYPE_H/S/D`；`FVVMATYPE/FVFMATYPE/FWVVMATYPE/FWVFMATYPE`；BF16 `VFWMACCBF16_VV/VF` | 两源互换的零×Inf、有效 Inf 积与第三源反号 Inf、同号对照、第三源 sNaN/qNaN；只调用一次融合运算；活动 lane 的 flags OR。 |
| E6 整数转换饱和 | 三份 `softfloat_symbolic_f*.sail` 共12包装 | `F_UN_RM_FX_TYPE_H/S/D`；`VFUNARY0/VFNUNARY0/VFWUNARY0` 等实际调用 | 每个 H/S/D→I32/Ui32/I64/Ui64 各列 NaN（含负 NaN）、±Inf、可达有限越界、边界内舍入；合法结果与 NV/NX。以最终调用图增补其他 Clause。 |
| E7 finite gate 与最终异常类别 | `ieee_mask_exact_exceptions`、rounded/exact helper，H/S/D/BF16 | 算术、转换、估算、BF16 与归约的实际调用闭包 | 特殊输入不得先执行普通有限舍入控制再屏蔽；分别见证 NV、DZ、OF、UF、NX 的成立/不成立及同时发生。位拼接不用机械分叉，F1 changed 也不能代替各异常类别的语义分界。 |
| R1/R2 ROD | `f32ToF16`、`f64ToF32` 包装与 `ieee_rod32_to_16/64_to_32` | `VFNUNARY0` 源S→H时 SEW16，源D→S时 SEW32 | 普通 RM0–4 与专用 ROD6 分开；精确、非精确且RTZ低位原0/原1、负值、溢出、tiny、±0、Inf、NaN；同臂 flags/result，保留 OF/UF/NX。 |
| R3 估算与归约调用闭包 | Recip7/Rsqrte7，BF16，归约 | `VFUNARY1` SEW16/32/64；`RFVVTYPE/RFWVVTYPE`；BF16 Clause | 分类十臂已有显式控制，但 H/S/D 实际见证尚缺。归约至少两活动 lane、顺序/无序和宽化调用分别核账，累加 flags 与目的组。 |

对每个向量项按 `vl=0`、活动 lane、mask=0、mask混合、`vstart>0`、尾部、至少两活动 lane 与 LMUL 合法组分别记录前后完整状态；SEW8/16/32/64 只在对应 Clause 合法分区运行，非法编码由 Illegal 路径另列。`VFNUNARY0` 的 SEW8 浮点目标子操作非法，但 f16→i8/ui8 合法。固定寄存器和输入值的定向配置须逐字段列出，不能把 `vl=1`、单一 `vtype` 或一种寄存器组写成全域预算。

f16 最大有限正数为 65504，所以 **f16→ui16 正有限溢出不可达**；用 65504 与 +Inf/NaN 的上游饱和对照，并核负值到0。所有 f16→I32/Ui32/I64/Ui64 包装均无正有限上溢，signed 也无负有限下溢；unsigned 的负有限输入仍可触发 NV→0。f16→i64 不应安排虚假的有限越界样例。f32→i16/ui16、f64→i64 等有可达有限越界，按格式单独选择位模式，不能照抄同一十进制数。

五 RM 要通过实际指令入口分别见证 RNE、RTZ、RDN、RUP、RMM；固定 RTZ opcode 单列。ROD 是窄化专用模式，不计入普通五 RM。边界 oracle 按源/目的位串与五 flags 比较，包含 max finite、最小正规、次正规、半 ULP、±0、Inf、sNaN/qNaN。flags old/new 位重叠单列，因为 `old|new==old` 不表示本次没有异常。三表示检查助记符、精确位串/小端字节和 `.insn`，Illegal 样例保留预期汇编器拒绝；真实 Make 入口单列。

## 2026-11-03：F1初态与见证覆盖的说明纠正

本矩阵沿用的运行说明曾将FD配置的 `mstatus=0x6600` 推断为“完整域初态固定FS/VS=Dirty”，该说法不成立。Isla `42000be` 的 `Target::setup_pre_state` 会为清单内mstatus重新建立符号值；collector随后在完整编码可行域内尝试FS/VS=Dirty的代表见证偏好。初始化默认值、符号输入域和最终代表值是三个不同层次，详见[运行说明的纠正记录](procedure.md#2026-11-03mstatus初态范围说明纠正)。

F1验收须从实际用例分别记录初态FS/SD、最终FS/SD、旧FFLAGS、本次flags和 `changed=(old|flags)!=old`，不能只凭TOML默认值判定某种初态不可达，或凭finished判定Clean/Initial均已覆盖。helper定向检查changed假臂的义务仍保留：整指令FPR写回本身可能置Dirty，仅看最终Dirty不足以区分accrue_fflags是否在假臂错误写回。定向证据不增加完整域Clause完成数，也不因本说明纠正改写旧结果或增记PASS。
