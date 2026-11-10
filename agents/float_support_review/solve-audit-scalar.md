# RV64 非访存 scalar 分支覆盖审计

审计日期：2026-09-26。范围为 77 个 RV64 非访存浮点目标中的 **49 个 scalar clause**：27 个类型化 H/S/D clause 与 22 个 Zfa clause。BF16 两个 scalar clause 由 BF16 审计负责；RV32 专属 `FMVH_X_D`、`FMVP_D_X` 不在 77 项内。本轮不修改模型、仓库测试代码或已有测试输入；新增 min/max 生成脚本、输入与结果均位于独立仓库外目录。

**结论：49 个 clause 的定向结果均有当前 IR 证据，不能证明每个 Sail 分支都已覆盖。** 当前 scalar 六组 471 条结果逐项通过；本审计另重跑非法 RM 30 条、新增 min/max 312 条，均在当前 IR 通过，共 813 条。FLI 常数表、FCVTMOD 显式控制分支，以及本轮补齐的普通 MIN/MAX 七路、MINM/MAXM 五路结果选择均可按输入逐臂映射。多个 clause 的非法 RM 退路、扩展禁用和部分寄存器/状态分支仍无足够证据。没有将 enum 90/90、具体状态差异 UNSAT 或旧官方批次退出 0 视为全分支覆盖。

## 版本与证据口径

当前 IR SHA-256：`d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。本审计核对主 `isla/rv64d.ir` 与生成目录产物同哈希，并逐字节核对下面六个当前 Sail 源文件与生成时冻结副本相同。Isla HEAD 为 `f4f8e4584a70588c66c9e7a6286cc20211618f18`，Sail-RISC-V HEAD 为 `f8ce8490981eac6396a31013180a2e718615757d`，均以包含已有未提交修改的冻结内容为实际受测版本。

| 文件，均位于 `sail-riscv/model/extensions/FD/` | 当前与冻结源码共同 SHA-256 |
| --- | --- |
| `fext_insts.sail` | `d32c4741bc63f7e850f469412d05a0288e48a415bfb4b5c19870988f8fc6bfd6` |
| `dext_insts.sail` | `3419798f019c2dc2646cca3193360f2124799140bfdc380f6221ed7b0d1295d0` |
| `zfh_insts.sail` | `1f589078f69f127ec9af63fd0bd32c52eac09a4b8e37e59a6bd334b0950841fc` |
| `zfa_insts.sail` | `7759b83d7c3597949b7672a33a495a956a5ab0c80dd84d79e9187a60c5f297a9` |
| `fdext_regs.sail` | `b71d9da2208ab0591ea676b52fd9280ab455faace1250980d157ef2e5562f948` |
| `fdext_control.sail` | `ba32768c933b97b3416fcfda895ab7cc3dec52dee213c151e26443cf57b6a8e6` |

完整生成绑定见 [IR 记录](ir-refresh.md)。当前定向矩阵位于仓库外目录 `isla-float-ir-final-20260926.q1Auj4/matrix/`；下文用 `IR_STAGE` 指代该生成目录。读取 `matrix/summary.json` 后，本审计独立检查了六组输入哈希、六组输出哈希和全部 471 行的 `sat`、`difference_unsat`、`structural_ok`、构造器、重编码、退休结果及观察寄存器等于预期。471 行均为一条 execute 完成路径。

| 简称 | 仓库内输入，均位于 `agents/float_support_review/tools/e_scalar_cases/` | 当前输出，均位于 `IR_STAGE/matrix/` | 条数 |
| --- | --- | --- | ---: |
| B | [scalar-cases.json](tools/e_scalar_cases/scalar-cases.json) | `scalar-scalar-cases.json` | 50 |
| N | [scalar-special-cases.json](tools/e_scalar_cases/scalar-special-cases.json) | `scalar-scalar-special-cases.json` | 18 |
| E | [enum-ops.json](tools/e_scalar_cases/enum-ops.json) | `scalar-enum-ops.json` | 62 |
| I | [fli-table.json](tools/e_scalar_cases/fli-table.json) | `scalar-fli-table.json` | 96 |
| R | [rm-routes.json](tools/e_scalar_cases/rm-routes.json) | `scalar-rm-routes.json` | 169 |
| S | [state-edges.json](tools/e_scalar_cases/state-edges.json) | `scalar-state-edges.json` | 76 |

下文 G 为本轮复跑的 30 条非法 RM；M 为本轮独立生成的 312 条 min/max。两组外部冻结件与命令分别在文末记录，不计入原 `matrix/summary.json` 的 471 条。

正向 runner SHA-256 为 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`，配置为 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`。版本、输入、输出的完整绑定沿用 `matrix/summary.json`，本文件不复制其全部 24 组清单。

这些 runner 直接调用 `zext_decode`、`zencdec_forwards`、`zexecute`；正向样例只观察目的 `f3` 或 `x3`、完整 `fcsr` 和 `mstatus`。源码 [runner/main.rs](tools/e_nonmem/runner/main.rs) 对这些字段逐路径先查 SAT，再查“任一字段不同”为 UNSAT。它没有输出完整 Sail 分支 ID/边命中表，没有检查所有未写目的寄存器，也没有证明任意输入的数值等价。因此下文的“分支映射”是把已验证具体输入代回源码判定，不能冒称插桩获得了覆盖率。

[旧 scalar README](tools/e_scalar_cases/README.md) 与 [enum 表](tools/e_scalar_cases/enum-coverage.md) 中归档的证明原属 `c9e1bfe2…`；这里只在同一输入已进入当前矩阵时使用其现版结果。旧 [官方 77 项批次](official-continuation.md) 为历史证据，不计现版覆盖。

## 共同分支与配置边界

| 源码分支 | 当前证据 | 仍不能证明的范围 |
| --- | --- | --- |
| [fext_insts.sail:51](../../sail-riscv/model/extensions/FD/fext_insts.sail#L51) `RM_DYN`/静态 RM；动态 FRM 合法/非法 | R 对 ADD、FMADD、SQRT、FP→W、X→FP、FROUND、FROUNDNX 七族各 H/S/D 测 FRM 0–4；S 各族五种静态 RM 与不同 FRM，H/D 各族一个静态优先例；三种窄化另有 15 动态例。本轮 G 对 FADD、FROUND 六个 clause 补齐非法 FRM 5/6/7 | R 不是每 enum×每 RM。其他 clause/enum 的 `None() => Illegal_Instruction()` 没有逐项现版证据；`Fcsr_RM_Fatal` 配置分支不在当前 `Fcsr_RM_Illegal` 配置内 |
| [fdext_control.sail:18](../../sail-riscv/model/extensions/FD/fdext_control.sail#L18) 与各 encdec guard：扩展支持、`misa`、FS、Zicsr、格式要求 | 全部 471 输入固定 `misa=0x800000000034112f`、`mstatus=0x6600`，合法译码方向已测 | FS=Off、F/D 位关闭、Zfa/Zfh 关闭、仅 Zfhmin 及禁用 guard 后 `ILLEGAL`；不能从合法译码推导拒绝路径已测 |
| [fdext_regs.sail:49](../../sail-riscv/model/extensions/FD/fdext_regs.sail#L49) `nan_unbox`：同宽、合法 box、非法 box | H/S 合法 box 广泛覆盖；S 有 FADD/FCLASS/FMINM 非法 box；FMV 验证其绕过 unbox；D 为 FLEN64 同宽 | H/S 每个操作数位置、每个调用族的非法 box 组合；FLEN128 不是本配置 |
| [fdext_regs.sail:348](../../sail-riscv/model/extensions/FD/fdext_regs.sail#L348) `F_or_X`：F 寄存器/整数寄存器；D 的 RV32 寄存器对 | 当前 F 路由已测 | Zfinx/Zhinx/Zdinx 与 RV32 偶数寄存器对属于其他配置；不把不可达的另一配置分支标 PASS |
| [dext_insts.sail:219](../../sail-riscv/model/extensions/FD/dext_insts.sail#L219) `validDoubleRegs` | RV64/F 配置返回 true | RV32Zdinx 奇数寄存器 Illegal/Fatal；当前配置不可达 |
| [fdext_regs.sail:521](../../sail-riscv/model/extensions/FD/fdext_regs.sail#L521) `accrue_fflags`：OR 后是否有变化 | B/E 的无异常、R 的新 NX、S 的新 NV 与旧 DZ 保留，已映射变化/不变两路；M 再验 60 条新 NV 与 252 条无新 flags | 初始 FS=Initial/Clean、已有同一 flag 再置、所有 dirty/SD 上下文组合未覆盖；B/E/R/S 的 FS 已为 Dirty，M 使用 FS=Dirty、SD=1 的一致初态 |
| GPR/FPR 索引和写回 | 所测固定目的寄存器为 3，源主要为 1/2/4 | x0 读写、源/目的别名、高编号寄存器及向量化寄存器访问实现分支没有遍历证明 |

## 27 个类型化 clause：逐族源码分支与用例映射

下表 H/S/D 仅在三份源码具有相同控制结构时合并；并没有把某格式的动态结果代替其他格式。格式特有转换在同一行明确列出。`S`、`D`、`H` 源码分别指 [fext_insts.sail](../../sail-riscv/model/extensions/FD/fext_insts.sail)、[dext_insts.sail](../../sail-riscv/model/extensions/FD/dext_insts.sail)、[zfh_insts.sail](../../sail-riscv/model/extensions/FD/zfh_insts.sail)。

| Clause，三项均明确纳入 | execute 分支与源码位置 | 已验证输入映射 | 未覆盖/不能证明项 |
| --- | --- | --- | --- |
| `F_BIN_RM_TYPE_H`、`F_BIN_RM_TYPE_S`、`F_BIN_RM_TYPE_D` | H:195、S:448、D:336：RM None/Some；Some 内 ADD/SUB/MUL/DIV 四臂 | B+E 各格式四 enum；R 只对 ADD 增补动态/静态路由；S 的 H/S unboxed ADD；G 各格式 ADD 非法 RM | SUB/MUL/DIV 的 RM 路由与非法 RM未逐项；所有算术特殊值、OF/UF/DZ/NV/NX 组合不是 clause 层穷尽；每 enum 的合法实例不等于每数值域 |
| `F_MADD_TYPE_H`、`F_MADD_TYPE_S`、`F_MADD_TYPE_D` | H:259、S:381、D:268：RM None/Some；FMADD/FMSUB/FNMSUB/FNMADD 四臂；部分臂另调用 `negate_*` 的 sign if | B+E 各格式四 enum 使用 1.5×2 与 0.5；R 对 FMADD 增补路由 | None 未测；FMSUB/FNMSUB/FNMADD 只用正输入，所调用 negate 的负输入→正输出分支未映射；无穷冲突、0×∞、NaN 等需单独 E 级输入，D helper 样例不能证明包装全部输入 |
| `F_BIN_F_TYPE_H`、`F_BIN_TYPE_F_S`、`F_BIN_F_TYPE_D` | H:342–414、S:753–824、D:684–756：SGNJ/SGNJN/SGNJX 三个独立执行体；MIN/MAX 各七路选择，且调用 `fle_*` | B+E 各格式五 enum；SGNJ 三操作具体位串合理；B/E 的 MIN/MAX 原仅 `(1.5,2.0)`。本轮 M 各操作/格式新增 26 条，七路选择全部有输入映射；正/负同号的指数相等/不等、异号、NV true/false 也有见证 | 原结果选择缺口已由 M 补齐；仍无插桩分支 trace，不覆盖所有 NaN payload、寄存器索引、扩展 guard 或 FS 状态；SGNJ 数值域未因 MIN/MAX 增补而扩展 |
| `F_BIN_X_TYPE_H`、`F_BIN_TYPE_X_S`、`F_BIN_X_TYPE_D` | H:415/427/439、S:826/838/850、D:758/770/782：EQ/LT/LE 三执行体；各调用 FP helper，最终写 bool 到 X | B+E 三 enum；S 对 EQ 有 rs1 qNaN/sNaN，LT 有 rs1 qNaN | LE 无 NaN实例；LT 无 sNaN实例；NaN 位于 rs2、双 NaN、有序假、±0 等未逐项覆盖。helper 的 SMT Bool/ITE 情形与 Sail 显式 branch 需分别理解 |
| `F_UN_RM_FF_TYPE_H`、`F_UN_RM_FF_TYPE_S`、`F_UN_RM_FF_TYPE_D` | H:549/624/639/654/669：SQRT、H←S、H←D、S←H、D←H；S:535：SQRT；D:431/506/521：SQRT、S←D、D←S。各体 RM None/Some | B+E 覆盖实际九个 enum；R 覆盖三 SQRT 与 H←S、H←D、S←D 的动态五 RM | 各 None 未测；宽化方向的动态/非法 RM 未逐项；NaN、溢出、下溢、负 SQRT 的 clause 层域没有穷尽 |
| `F_UN_RM_FX_TYPE_H`、`F_UN_RM_FX_TYPE_S`、`F_UN_RM_FX_TYPE_D` | H:564/579/684/700、S:550/565/610/626、D:446/461/536/552：W/WU/L/LU 各执行体，每个 RM None/Some；L/LU 有 XLEN 断言 | B+E 各格式四 enum；R 只加强到 W 的五动态 RM/静态优先 | None 未测；WU/L/LU 舍入路由、负数转无符号、上下界、NV/NX 优先等未逐 enum/指令穷尽；RV32 非法不是当前可执行模式 |
| `F_UN_RM_XF_TYPE_H`、`F_UN_RM_XF_TYPE_S`、`F_UN_RM_XF_TYPE_D` | H:594/609/716/732、S:580/595/642/658、D:476/491/568/584：从 W/WU/L/LU 各执行体，每个 RM None/Some；32 位截取与符号/无符号 helper 选择不同 | B+E 各格式四 enum；R 加强 H/S←W、D←L | None 未测；其他整数源 enum 的非 RNE、最高符号位/高位截断/饱和结果未在每个包装上逐项检查 |
| `F_UN_X_TYPE_H`、`F_UN_TYPE_X_S`、`F_UN_X_TYPE_D` | H:812/818、S:912/918、D:846/852：FCLASS / FMV 到 X 两执行体；FCLASS 走分类函数，FMV 直接位串搬运 | B 两 enum；S 各格式 FCLASS 十类别；H/S unboxed 分类为 qNaN；FMV 正、负号输入，H/S unboxed 原位读 | 十类别是已测分类结果全集，但无分支轨迹证明；共享写 X 的 x0/别名分支未测；D FMV 仅 RV64 guard 满足方向 |
| `F_UN_F_TYPE_H`、`F_UN_TYPE_F_S`、`F_UN_F_TYPE_D` | H:825、S:923、D:858：X→F，低位截取/nan_box 或 D 同宽写回，执行体无额外数值 if | B 正输入；S 负号及 H/S 的 X 高位非零截断；每格式两例 | 没有额外数据分支可因位数增加而计数；共享寄存器索引、扩展 guard、状态分支仍适用 |

### 原 471 条证据的 min/max 缺口快照

下面保留增补前核对结果，说明 M 的选例依据；这些结果选择叶子现已由 M 补齐，见“本轮补证 M”。这里只统计 execute 结果选择链的叶子，不含其提前执行的 `fle_*` 内部条件。原 471 条在每格式均有同样缺口，不能将不同格式的数据情形相互替代。

| 结果选择叶子 | `FMIN/FMAX` 现版 B/E | `FMINM/FMAXM` 现版 B/N/S | 最小补充输入建议，rs1/rs2 |
| --- | --- | --- | --- |
| 双 NaN→规范 NaN（普通 MIN/MAX 独立叶子） | 未测 | Zfa 的任一 NaN 合并叶子已测，但双 NaN 组合未测 | `(qNaN,qNaN)`，再用 `(sNaN,qNaN)` 检查 NV |
| 仅 rs1 NaN→rs2（普通）/规范 NaN（Zfa） | 未测 | qNaN 已测；H/S unboxed 也到此 | `(qNaN,2.0)`；`(sNaN,2.0)` |
| 仅 rs2 NaN→rs1（普通）/规范 NaN（Zfa） | 未测 | qNaN/sNaN 已测 | `(1.5,qNaN)`、`(1.5,sNaN)` 用于普通 MIN/MAX |
| rs1=-0、rs2=+0 | 未测 | 已测 | `(-0,+0)` 用于普通 MIN/MAX |
| rs1=+0、rs2=-0 | 未测 | 未测 | `(+0,-0)` 用于两族 |
| 普通有序条件 true/false | MIN 仅 true；MAX 仅 false | 两种结果都未测 | `(1.5,2.0)`、`(2.0,1.5)`；比较内层补 `(1.5,1.75)`、`(-1.5,-2.0)`、`(-1.5,-1.75)`、`(+1,-1)`、`(-1,+1)` |

普通 MIN/MAX 的 `fle_*` 仍是位域比较控制流，见 S:217、D:176、H:119；这里没有把旁边标注“当前无调用”的旧 `feq_quiet_*`/`flt_*` 错算为现行 clause 路径。`fle_*` 的 `is_quiet=false` 不由本表这些 min/max 调用触发，不能将该不可达实参情形登记为当前 clause 的必测叶子。M 已加入上述正/负号与指数/尾数比较见证；其输入映射不代替执行轨迹计数。

## 22 个 Zfa clause：逐族分支与输入映射

以下源码均在 [zfa_insts.sail](../../sail-riscv/model/extensions/FD/zfa_insts.sail)。

| Clause | 分支与源码位置 | 已验证映射 | 未覆盖/不能证明项 |
| --- | --- | --- | --- |
| `FLI_H`、`FLI_S`、`FLI_D` | :22/:72/:122 的 `match constantidx` 各 32 臂 | I 各 32 索引；B 重复索引 16。可把所有显式常数臂映射到现版 PASS 输入；H 特殊索引 29/30 为 +∞，31 为 qNaN | 三个 clause 的扩展 guard false、其他编码字段保留值、目的寄存器/FS 行为未覆盖；不能称整条指令所有分支完备 |
| `FMINM_H`、`FMAXM_H`、`FMINM_S`、`FMAXM_S`、`FMINM_D`、`FMAXM_D` | :174/:205/:236/:267/:298/:329：任一 NaN、两序 ±0、一般比较 true/false，共五个结果叶子；提前调用 `fle_*` | B rs1 qNaN；N rs2 qNaN、rs2 sNaN、(-0,+0)；S H/S MINM 非法 boxing。M 各操作/格式新增 26 条，五叶子均有映射，含 q/sNaN 左右位置与双 NaN | 原五路选择缺口已由 M 补齐；共享 guard/寄存器/FS 分支仍适用，且没有全模型分支轨迹证据 |
| `FROUND_H`、`FROUNDNX_H`、`FROUND_S`、`FROUNDNX_S`、`FROUND_D`、`FROUNDNX_D` | :360/:389/:418/:447/:476/:505：RM None/Some；向 roundToInt 传 exact=false/true | B RNE 的 1.5；R 七族中的两族，各格式五动态 RM，S 五静态优先，H/D 各一静态优先；G 对三个 FROUND 的 None | FROUNDNX 的 None 没有现版负例；零/整数/NaN/∞等未在这些 clause 逐项测试。R 可证明 NX 抑制/报告的有限具体例，不能证明所有特殊值 |
| `FLEQ_H`、`FLTQ_H`、`FLEQ_S`、`FLTQ_S`、`FLEQ_D`、`FLTQ_D` | :581/:606/:631/:656/:682/:707：执行体无本地数值 if；使用 Le_quiet/Lt_quiet，再累积 flags、写 X | B 普通真值；S 每 clause rs1 qNaN→false 无 NV、rs1 sNaN→false 有 NV，各三例 | 普通假值、相等、±0、NaN 位于 rs2或双 NaN未逐 clause 验证；共享函数/状态域不完备 |
| `FCVTMOD_W_D` | :788 执行体；:724 helper 有六路分类、两个 sign if、四路 flags 优先选择 | B `2^32+3`；S 11 边界。下表可将每个显式 helper 选择臂映射到现版输入 | 没有分支 trace；负边界邻值、sNaN/负∞、x0 等不是已证明域。固定 RTZ 编码以外的拒绝行为未测 |

`FCVTMOD_W_D` 的局部覆盖比“一个 clause 有样例”更强，但仍是具体输入支持的控制臂映射：

| `fcvtmod_helper` 源码选择 | 对应输入名与事实 |
| --- | --- |
| `is_zero` | S `fcvtmod_zero`：+0→0、无新 flags |
| `is_subnorm` | S `fcvtmod_subnormal`：最小正次正规→0、NX |
| `is_nan_or_inf` | S `fcvtmod_infinity`、`fcvtmod_qnan`：0、NV |
| `true_exp >= 84` | S `fcvtmod_huge`：2^84→0、NV |
| `true_exp < 0` | S `fcvtmod_fraction_half`：0.5→0、NX |
| 普通数计算及 `sign` 两臂 | S `fcvtmod_negative_fraction`：-1.5→-1；`fcvtmod_positive_limit`：2^31-1；另有正/负 wrap |
| flags `true_exp > 31` | B `fcvtmod_w_d_wrap`、S `fcvtmod_negative_wrap`：模 2^32 写回且 NV |
| flags `integer > max_integer` | S `fcvtmod_positive_overflow`；`fcvtmod_nv_over_nx` 验证 2^31+0.5 仅 NV |
| flags 非零 fractional | S `fcvtmod_negative_fraction`：NX |
| flags 零 | S `fcvtmod_positive_limit`：无新 flags，旧 DZ 保留 |

## 本轮补证 G：当前 IR 非法 RM 30 条

本轮复用 [negative-cases.json](tools/e_scalar_cases/negative-cases.json) 和 [negative_runner.rs](tools/e_scalar_cases/negative_runner.rs) 对应的现成二进制，不改测试代码。冻结到新的仓库外目录 `isla-float-scalar-audit-20260926.21ifq99w`，下文以 `SCALAR_AUDIT_STAGE` 表示。目录内保留 `runner`、`ir.ir`、`config.toml`、`cases.json`、`negative_runner.rs`、`stdout.log`、`stderr.log`、`results.json`、`summary.json`。

```sh
"$SCALAR_AUDIT_STAGE/runner" \
  "$SCALAR_AUDIT_STAGE/ir.ir" \
  "$SCALAR_AUDIT_STAGE/config.toml" \
  "$SCALAR_AUDIT_STAGE/cases.json" \
  "$SCALAR_AUDIT_STAGE/results.json"
```

实际通过 Python `subprocess.run(..., timeout=90)` 调用上述 argv，完整 argv 在外部 `summary.json`。2026-09-26 运行退出 0，耗时 6.0246 秒。随后独立读取输出检查 30 行的 SAT、差异 UNSAT、结构检查及观察寄存器等于预期；12 行静态 RM 5/6 在译码处为 `ILLEGAL`，原编码 payload 正确、没有执行；18 行动态 FRM 5/6/7 为 `Illegal_Instruction`、每项一条执行路径。全部 30 行译码各有两条完成路径。

| 固定件 | SHA-256 |
| --- | --- |
| IR | `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409` |
| 配置 | `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987` |
| runner | `7b3a086e208527ea2a0e4fe7c3cfa527be553f795177bd52377573aaaa259f89` |
| runner 源码快照 | `0b08a08400e5f9b470826a91c6fcca9b9fccb285ed91b1426f8467c44c307381` |
| 30 条输入 | `29028e5e240295bc4b4fac2f0150bafc9ca3f848ca3219c32fd722b5ee648252` |
| 30 条输出 | `5a0f9c47062336f237fa5395bf57f71cc730c9eee8252ae41e888b37036e5a2c` |

覆盖仅为 `F_BIN_RM_TYPE_{H,S,D}` 中 FADD 和 `FROUND_{H,S,D}`。原 471 条现版证据加 G 的 30 条为 501 条，再加下述 M 的 312 条合计 813 条，仍覆盖同一 49 个 clause；不是新增 clause，也不是全体 RM 指令的非法路径验收。

准备时先按归档哈希检查旧目录顶层 `illegal-runner-fixed`，其实际哈希为执行阶段专用 runner 的 `e265b798…`，与支持译码拒绝的目标 runner 不同；检查在调用前停止。随后定位到 `negative-target/debug/isla-float-e-illegal-runner`，核对为上表 `7b3a086e…` 后才执行正式补证。这是固定件选择纠正，不是模型测试失败；旧证据和原文件均保留。

## 本轮补证 M：min/max 312 条与 72 个结果选择叶子

本轮在仓库外新建 `isla-float-minmax-audit-20260926.8234wb5b`，下文以 `MINMAX_AUDIT_STAGE` 指代。目录固定保存同一 d012 IR、同一配置及正向 runner；另外复制 B/E 作为**机器码、构造器与字段模板**，不复用其结果预期。`generate_and_run.py` 在调用 runner 之前独立生成全部预期及源码叶子映射，随后执行；未读取被测输出来构造 oracle。

输入为 **4 种操作 × H/S/D × 26 种操作数对 = 312 条**；涉及 9 个 clause（普通 MIN/MAX 共享三个类型化 clause，Zfa 为六个 clause），不是 12 个 clause。26 种操作数对包括 qNaN/qNaN、sNaN/qNaN、qNaN/sNaN、sNaN/sNaN，左右单 NaN 各 q/s 两种，两序 ±0 与同号零，正/负数各自的不同指数顺逆序、相同指数顺逆序与相等，正负异号两序，以及 ±∞ 两序。每个格式、每个操作都有完整同一组 26 条，不以跨格式例子替代。

预期遵循独立规则：普通 MIN/MAX 单 NaN 返回数值、双 NaN 返回规范 NaN；MINM/MAXM 任一 NaN 返回规范 NaN；任一 sNaN 才新增 NV；零号按 MIN 选负零/MAX 选正零，同号零保留符号。过滤 NaN 后，精确可表示的有限数与无穷使用数值比较，不按位串大小比较。H/S 输出补齐 NaN boxing。输入 qNaN 带非零 payload `0x13`，输出要求规范 NaN。每例旧 `fcsr=0x68`，验证旧 DZ 与 FRM=3 保留；预期仅在 sNaN 时变为 `0x78`。初始 `mstatus=0x8000000000006600`（FS=Dirty、SD=1），预期完整保持，未把该批次当作 FS→Dirty 转换验证。

每条同时观察 `f1`、`f2`、`f3`、`fcsr`、`mstatus`、`misa`，因此还检查源值与 misa 未变化。2026-09-26 实际运行退出 0，耗时 14.5405 秒；312 行全部 SAT、差异 UNSAT、结构检查、译码字段、重编码与 `Retire_Success` 正确。每行译码/重编码/执行完成路径数为 2/1/1。新增 NV 共 60 条，其余 252 条无新 flags；没有发现结果反例。

| 每个操作与格式的结果选择叶子 | 普通 MIN / MAX 各条数 | MINM / MAXM 各条数 | 示例输入后缀 |
| --- | ---: | ---: | --- |
| 双 NaN | 4 | 合入 any_nan | `qnan_qnan`、`snan_qnan`、`qnan_snan`、`snan_snan` |
| 仅 rs1 NaN | 2 | 合入 any_nan | `qnan_number`、`snan_number` |
| 仅 rs2 NaN | 2 | 合入 any_nan | `number_qnan`、`number_snan` |
| 任一 NaN | 不适用 | 8 | 上述八条 |
| rs1=-0、rs2=+0 | 1 | 1 | `zero_neg_pos` |
| rs1=+0、rs2=-0 | 1 | 1 | `zero_pos_neg` |
| 其余比较条件 true | 10 | 10 | MIN 的 `positive_diff_exp_less`、MAX 的 `positive_diff_exp_greater`；还包括同值 |
| 其余比较条件 false | 6 | 6 | MIN 的 `positive_diff_exp_greater`、MAX 的 `positive_diff_exp_less` |
| 合计 | 26；每操作/格式七叶子 | 26；每操作/格式五叶子 | 完整名称为 `audit_{fmin/fmax/fminm/fmaxm}_{h/s/d}_{后缀}` |

普通族 2×3×7=42 个叶子、Zfa 族 2×3×5=30 个叶子，共 **72 个 op/format/结果选择叶子**已有具体输入映射。`branch-mapping.json` 保存 312 条名称→clause/op/format/leaf/输入位串/预期位串/新 flags 的明细，`branch-coverage.json` 保存每个操作与格式的上述计数。M 另外通过正负号四组合、同号指数相等与不同、同号相等值、sNaN 存在与不存在，给 `fle_*` 的相应条件两臂提供输入见证。这里统计的是审定选择链叶子，**不是执行器插桩得到的全模型 branch coverage**，不外推任意浮点值、所有 guard/寄存器索引或不同 FS 状态。

实际生成与运行入口：

```sh
python3 "$MINMAX_AUDIT_STAGE/generate_and_run.py"
```

脚本调用如下 argv，采用 `subprocess.run(..., timeout=180)`，stdout/stderr 和完整命令另存外部目录：

```sh
"$MINMAX_AUDIT_STAGE/runner" \
  "$MINMAX_AUDIT_STAGE/ir.ir" \
  "$MINMAX_AUDIT_STAGE/config.toml" \
  "$MINMAX_AUDIT_STAGE/cases.json" \
  "$MINMAX_AUDIT_STAGE/results.json"
```

| 固定件或新证据 | SHA-256 |
| --- | --- |
| IR | `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409` |
| 配置 | `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987` |
| runner | `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425` |
| `generate_and_run.py` | `b0af2761d459d37a9c61f7c1bda89299c4fce5991018fb5ad34b52b16fcacde2` |
| `cases.json`（312 条） | `74172a314894786ccf80c667afe7819c4a4ecfe868afa7c5584a7a2e61cee94f` |
| `branch-mapping.json` | `9292d98f571dd521065ba40887fb6122bac398a92d018ca1d2bd91ebcabeb367` |
| `branch-coverage.json` | `ddc7e0344c9e3561e82f727f66b434ea8988dad093152c4aec87e1d65b014d7e` |
| `results.json`（312 条） | `84b7677fc53de650eb9d71489cbe546b637695ee65530c1928eca71e20467aaa` |

## 结果合理性与下一步

现有数值结果有实质检查依据：enum/搬运/分类使用独立 IEEE 位串预期；FLI 使用独立常数表；RM 生成脚本用有理数与相邻浮点数、SQRT 中点平方比较给出预期。S 验证 qNaN/sNaN 的 NV 区分、NaN boxing、FCLASS 不修改 flags、旧 flags OR 保留与 FCVTMOD 的 NV 优先。各输出同时检查目的位串、fcsr 与 mstatus，不只是运行退出。审计未从这些样例发现新的结果冲突。

这些证据支持“所列状态合理”，不支持“所有 Sail branch 已覆盖且结果都正确”。原审计发现的普通 MIN/MAX 七叶子与 MINM/MAXM 五叶子缺口已通过 M 补齐，并保存逐输入→源码条件映射。仍需给每个剩余 RM 执行体一个非法 DYN 见证，再补扩展/FS 禁用译码见证。全路径生成还需单独审查当前 d012 官方 `make solve-*` 的结果与限制；旧 c9e 77 项状态不转记本版。若要求严谨的源码分支覆盖率，还需要明确统计范围、分支标识、不可达理由和 trace，当前 runner 的 `execute_paths=1` 不能替代这一证据。
