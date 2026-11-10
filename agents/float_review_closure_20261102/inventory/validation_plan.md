# 浮点遗留项最终模型验证计划（待执行）

## 范围来源与机读入口

实施前清单基线是模型 `6202e23`、Isla `cf1aa14`；当前机读列表按模型已提交候选 `8ad5e8e` 与 Isla `cf1aa14` 的 HEAD 源码生成，精确 SHA 由 JSON 内 `model_commit/isla_commit` 固定。`build_clause_closure.py` 对全部 `model/**/*.sail` 的普通与 `SYMBOLIC` 函数定义取并集，反向递归查找四个 owner 所改函数的 Clause 调用者，再与当前 `isla/scripts/run.mk` 的 `FD_FLOAT` 表相交。结果是 **89 个 FD_FLOAT 入口中的 64 个静态受影响 Clause**；另 25 个没有调用本轮所改函数。完整有序集合、类别、每条 `solve-<Clause>` 目标、source 位置和预设预算在 [affected-clauses.json](affected-clauses.json) 的 `full_clause_run_list`，可直接供主机调度器读取；若最终源码再变化，执行前须重新生成该 JSON 并对差异复审。该静态闭包取并集以防漏项，可能含某个 Clause 中不触发本轮条件的 enum；它不证明某种输入或格式实际可达。

按改动种类，64 个中：`fflags_changed` 64，五窄 2，普通整数 wrapper 6，异常原因 24，ROD 3；类别重叠，不能相加。若最终 diff 扩及其他函数或文件，须扩大 seed 和重算闭包。没有进入本轮调用闭包的 25 个目标仍属 `FD_FLOAT`，不是“全浮点已覆盖”的证明。

## 正式四 owner 与审查门

| Owner | 唯一生产写边界 | 必须核的语义 |
| --- | --- | --- |
| FD regs | `sail-riscv/model/extensions/FD/fdext_regs.sail` | changed 真/假、FS/SD、FFLAGS、原断言与两个 callback；不能无说明引入不同 callback。 |
| V 窄 helper | `sail-riscv/model/extensions/V/vext_fp_utils_insts.sail` | 五 `_pure` overflow，另审已恢复 f16→i16 的正/负端点；所有新增 Jump 留在活动 lane gate 内。 |
| FD wrappers | `sail-riscv/model/extensions/FD/softfloat_symbolic_f16.sail`、`softfloat_symbolic_f32.sail`、`softfloat_symbolic_f64.sail` | 12 个普通 FP→32/64 整数 wrapper 的 invalid/NaN/符号饱和；两种 ROD 模式下 flags 与 bits 同臂，普通五 RM 解码不吃 RM6。 |
| core exceptions | `sail-riscv/model/core/ieee_fp_exceptions.sail` | E1–E5 异常原因、finite/valid gate、最终 NV/DZ/OF/UF/NX 类别、ROD exact/inexact；数值阈值公式和位 OR 保持数据流。 |

以上边界已由独立 Sol 在 [设计审查](../review/model/design-review.md) 确认。模型仅写 `.worktree/runner-float/sail-riscv`；原根 dirty `sail-riscv` 只读。inventory owner 不写生产。各 owner 提交以后，主 agent 核合成 diff、四配置严格生成和旧版不能通过的永久 CFG 回归；Sol 独立复审最终源码、IR 和动态结果。

## 64 条完整 Clause 预算清单

主机应读取 JSON 的全部 `full_clause_run_list`，逐条执行并写回结果。以下为人工分组核账，避免只跑代表样例：

| 分组 | 完整 Clause 列表 |
| --- | --- |
| 异常原因调用闭包，24 条 | `FVFMATYPE FVFTYPE FVVMATYPE FVVTYPE FWFTYPE FWVFMATYPE FWVFTYPE FWVTYPE FWVVMATYPE FWVVTYPE F_BIN_RM_TYPE_D F_BIN_RM_TYPE_H F_BIN_RM_TYPE_S F_MADD_TYPE_D F_MADD_TYPE_H F_MADD_TYPE_S F_UN_RM_FF_TYPE_D F_UN_RM_FF_TYPE_H F_UN_RM_FF_TYPE_S RFVVTYPE RFWVVTYPE VFUNARY1 VFWMACCBF16_VF VFWMACCBF16_VV`。 |
| 非上组而涉及五窄、整数 wrapper 或 ROD，6 条 | `F_UN_RM_FX_TYPE_D F_UN_RM_FX_TYPE_H F_UN_RM_FX_TYPE_S VFNUNARY0 VFUNARY0 VFWUNARY0`。 |
| 仅由 `accrue_fflags changed` 进入闭包，34 条 | `FCVTMOD_W_D FCVT_BF16_S FCVT_S_BF16 FLEQ_D FLEQ_H FLEQ_S FLTQ_D FLTQ_H FLTQ_S FMAXM_D FMAXM_H FMAXM_S FMINM_D FMINM_H FMINM_S FROUNDNX_D FROUNDNX_H FROUNDNX_S FROUND_D FROUND_H FROUND_S FVFMTYPE FVVMTYPE F_BIN_F_TYPE_D F_BIN_F_TYPE_H F_BIN_TYPE_F_S F_BIN_TYPE_X_S F_BIN_X_TYPE_D F_BIN_X_TYPE_H F_UN_RM_XF_TYPE_D F_UN_RM_XF_TYPE_H F_UN_RM_XF_TYPE_S VFNCVTBF16_F_F_W VFWCVTBF16_F_F_V`。 |

正式运行采用最终五 IR 与四配置源同版、`configs/riscv64_difftest_fd.toml`、官方 Z3 `1fd1d3613`、T1/qffp、整 Clause 外限 7200 秒及单次 SMT 7200 秒。`run.mk` 默认 `OUTER_TIMEOUT=60m`、`SMT_TIMEOUT` 可能为 1m，故不能直接用默认值冒充本计划；传入精确 120m/7200s，并留原 argv、环境、库路径、IR/config/binary SHA、工作核、退出码、summary 和 JSON 总数。`seed17` 在现行 `smt.rs` 不是标准 Make 选项，而由实验拦截器控制随机种子；正式启动器须显式保存拦截器版本/哈希及日志，证明每次实际使用 17。若不用拦截器，则记录真实随机种子并将“同 seed17 对照”标未达，不伪称固定。现有 `run.mk` 的 `solve-%` 每条依赖 build，共享 target 软链；主机并行时应先冻结一次 binary，再用独立输出目录/CPU运行，避免构建互相覆盖。

验收以每个 Clause 的 `finished`、退出 0、无 error/SMT timeout/未完成为完整预算结果。若外限、partial 或 JSON 缺失，按主树/编码辅助树、完成/排队、累计与最长单次 SMT 记真实状态；不能缩短输入域、换配置或拿固定样例当 PASS。64 条全完成仍只证明此配置、seed、时间预算下的 Clause 执行完成，不证明各 enum/格式/异常原因都见证。

## 实际特殊条件见证矩阵

完整 Clause 与下列定向条件是两份证据。定向输入须从**实际被读操作数**的位模式分类，而非只看初态全部 FPR/VR；比较输入、结果、五位 flags、FS/SD、目的全寄存器组、vstart、机器字。每个条件至少有对应正常对照，`old fflags=0` 与已含同位/其他位分开。

| 义务 | 实际入口与格式 | 最小输入和可达性界限 |
| --- | --- | --- |
| changed | 64 条中的代表不等于64条全见证；先 helper 定向证 old=0/new=0、old已含new、首次新增、已有异位再新增，再核标量/向量/BF16/归约的实际指令后态。 | Ext_F 的 FS 初值 Clean/Initial/Dirty、SD 与其他 mstatus 位；目标寄存器写也会 Dirty，须隔离判断 changed 的作用。Zfinx 若在正式范围内按其配置单核。 |
| signed narrow | `VFNUNARY0` 的 f16→i8（目标 SEW8）、f32→i16（目标 SEW16）及既有 `VFUNARY0` f16→i16。 | 正/负 overflow、两端精确界、范围内 inexact、NaN/±Inf；普通 RM0–4 与固定 RTZ 子操作、活动/屏蔽/multi-lane。f16→i8 例如128/-129；f32→i16 例如32768/-32769。NV 真臂只返回 NV。 |
| unsigned narrow | `VFNUNARY0` f16→ui8、f32→ui16；`VFUNARY0` f16→ui16。 | 有限正越界、负输入→0、NaN（含负 NaN）/±Inf、范围内；但 **f16→ui16 的最大有限数65504小于65535，有限正 overflow 不可达**。其 overflow 真臂可由 +Inf/NaN 的 Ui32 饱和触发；不得构造65535/65536的 f16输入。SEW8 的 `VFNUNARY0 X/XU←f16` 合法；SEW8 的浮点目标子项不合法。 |
| 12 个 FP→整数 wrapper | `F_UN_RM_FX_TYPE_H/S/D`、`VFUNARY0/VFNUNARY0/VFWUNARY0` 中实际子操作；源 H/S/D、目标 signed/unsigned 32/64。 | 各 wrapper 的 NaN/±Inf、正/负有限越界（若可达）、范围内精确/inexact、五 RM/固定 RTZ；f16 的有限值均能放进 signed32/64 与 unsigned32/64 的正范围，**f16→i64 等有限越界不可达**，但 NaN/±Inf invalid 可达。按最终源码和每个目标整数边界选定向数值。 |
| 加减/乘法 | H/S/D 标量 `F_BIN_RM_TYPE_*` 与对应向量加减乘 Clause。 | add 异号 Inf vs 同号 Inf、sub 同号 Inf vs 异号 Inf；mul 两操作数位置 0×Inf/Inf×0、有效 Inf×非零有限；±0、s/qNaN、有限 OF/UF/NX。宽化目标格式为源 SEW×2，归约仅加法。 |
| 除法 | 同上标量 FDIV、向量 `FVVTYPE/FVFTYPE` 的 div/rdiv，H/S/D。 | `0/0`、`Inf/Inf` 各 NV；`有限非零/+0`、`有限非零/-0` 各 DZ；`Inf/0`、`0/1`、有效 Inf/有限和普通有限对照。相同 NaN 结果不能合并两种 NV 原因。 |
| sqrt/FMA | `F_UN_RM_FF_TYPE_*` 的 FSQRT、`VFUNARY1` vfsqrt；`F_MADD_TYPE_*` 四变体与向量 `FVVMATYPE/FVFMATYPE/FWVVMATYPE/FWVFMATYPE`、BF16 FMA。 | sqrt 负有限/-Inf vs -0/+0/正有限；FMA 两乘源互换零×Inf、有效 Inf 积与反号/同号 Inf c、第三源 s/qNaN；BF16 scalar/向量/累加器异常源分别放 sNaN；保持单次融合。 |
| 最终异常类别 | 上述真实算术、转换、ROD。 | NV/DZ/OF/UF/NX 各成立/不成立；有限与特殊输入的 gate 真/假；五 RM 边界，NV 抑制 NX，旧 flags 预置避免仅从 `post & ~old` 误读本次异常。阈值内部比较不单独要求 Jump。 |
| ROD | `VFNUNARY0 FNV_CVT_ROD_F_F` 的 SEW16 f32→f16、SEW32 f64→f32；同 Clause 普通 `FNV_CVT_F_F` 作五 RM 对照。 | RM6 与普通模式同臂 flags/bits；exact 低位原0/1、inexact RTZ低位0→1和原1、负值、最大有限/溢出、tiny/underflow、±0/±Inf/sNaN/qNaN；oracle 核 result 与 flags。 |
| 估算补查 | `VFUNARY1` 的 Recip7/Rsqrte7，H/S/D。 | 特殊值现有显式分类；旧 SEW32/vl1 1.0和次正规只作历史证据。最终版核十类、活动/屏蔽、多lane及查表代表边界。Recip7 分类前两个候选 eager 计算只列预算成本，不未经数据改源码或认定超时根因。 |

向量项还要按 `vl=0/1/>1`、每 lane 单独/同时异常、屏蔽/非屏蔽、prestart/tail、LMUL 与目标组保持独立核；定向 oracle、编译器助记符、精确位串和 `.insn` 三种编码证据分开记。所有固定域样例只证明所选输入，不能把它们称为全域覆盖。

## 构建与提交检查

四配置 ordinary/SYMBOLIC 严格生成、166 模型源/工具/配置哈希、五 IR SHA、79 workaround 配置/132 region/22 锚点与永久 CFG 回归按最终版本重做。IR 检查每个新增 Jump 的条件、真/假臂可达、对 flags/result 或状态写的支配，以及不活动 lane 绕开转换/异常；仅数 Jump 不签。完整 Clause、定向 oracle、GCC/Clang 三表示和真实 `make solve` 分开记结果，Sol 对最终源码/IR/动态证据独立复核后由主 agent 集成发布。
