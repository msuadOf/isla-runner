# Scalar RM 与译码 guard 定向输入（静态生成记录）

范围：RV64 非 BF16 的 27 个类型化 scalar clause 中 **90 个 enum**，以及 22 个 Zfa scalar clause，共 112 个编码 op。源码依据为当前 `sail-riscv/model/extensions/FD/{fext_insts,dext_insts,zfh_insts,zfa_insts,fdext_control}.sail`；正向/负向 runner 分别使用现有 `tools/e_nonmem/runner/main.rs` 和 `tools/e_scalar_cases/negative_runner.rs` 的 JSON 协议。此文件只记录**生成与静态核查**；动态结果由主 agent 统一运行后另记。输出不写入仓库。

## 生成与预期

入口：`python3 agents/float_support_review/tools/solve_scalar_coverage/rm_guards.py /tmp/isla-scalar-rm-guards-20260926-v2`。也可导入 `generate(repo_root: Path)`，返回 `positive` / `negative` 两个列表。每条带 `branch_ids`，runner 忽略该附加字段。编码与译码字段取已汇编的 `tools/e_scalar_cases/{scalar-cases,enum-ops}.json` 作为模板，RM 仅替换 bit 14:12；计算结果由脚本独立的精确二进制操作数恒等式给出，没有读取 Sail 或 Isla 输出当 oracle。

- RM op：类型化 57 个，加 Zfa `FROUND`/`FROUNDNX` 6 个，共 **63**。每项静态 RM 0–4 各一例且 FRM 取不同的合法值；DYN 加 FRM 0–4 各一例。正向 **630** 条，预期退休、目的值精确、flags 为零，FRM、mstatus、misa 及所有源寄存器不变。正向初态与预期均为 `mstatus=0x8000000000006600`（FS=Dirty、SD=1），不使用不一致的 SD=0 初态。`FROUND`/`FROUNDNX` 用整数 2.0，避免任何舍入或 NX 分歧。算术、FMA、平方根与转换使用 1.5、2、3、4 等精确数，结果按 IEEE H/S/D 位串并做 H/S NaN boxing。
- 每项 RM 的静态 5/6 各一例，预期 `zext_decode -> ILLEGAL`，共 **126**；DYN 加 FRM 5/6/7 各一例，预期译码为原 clause、重编码相同、`zexecute -> Illegal_Instruction`，共 **189**。这里 `Fcsr_RM_Illegal` 是当前配置；`Fcsr_RM_Fatal` 需另一配置，不能以本批覆盖。
- 每个 op 的 FS=Off 一例，共 **112**；可达的 misa.F=0 有 **82**，misa.D=0 有 **40**，均预期译码 `ILLEGAL`，未执行。所有拒绝例观察目的、源、fcsr、mstatus、misa 未变；原字节词保留，正向只改合法 RM 位。
- 合计 **630 正向 + 549 负向 = 1179** 条。脚本静态断言 90 typed、27 typed clause、22 Zfa、63 RM、唯一名字和全部映射存在；生成后另读 JSON 核对 32 位 word、RM 位、分支标签和计数。动态状态尚未标 PASS。

## 分支标识与预期动作

每条 `branch_ids[0]` 指向下表的具体 op 映射。`encdec` 表示译码成功，`encdec_candidate` 只表示该编码对应的候选映射，不声称此映射译码成功。静态 RM 0–4 分别指向 `fext_insts.sail:32–36` 的相应映射臂、`:52` 静态选择、`:63` 的 `Some`；DYN+FRM 0–4 指向 `:37`、`:52`、`:55` 的有效 FRM 与 `:56` 的 `Some`，各个 FRM 有独立臂标识。静态 RM 5/6 仅标 `encdec_rounding_mode`（:31–38）没有匹配臂，**不**标记未到达的 `select_instr_or_fcsr_rm`。DYN+FRM 5/6 指向 `:49` 非法判断，FRM 7 指向 `:55` 与 `RM_DYN` 相等判断；三者再到 `:57` 保留行为及 `:60` 的 `None`。guard 拒绝标候选映射、该行 `when_false` 及 `fdext_control.sail:18` 或 `:19` 对应状态原因；H/Zfa 的依赖链还见 `fext_insts.sail:28–29`、`zfa_insts.sail:9`、`zfh_insts.sail:155–158`、`dext_insts.sail:214`。这些是源码条件与输入的映射，不是插桩 trace。源码位置在当前未提交工作树核对，后续改动需重查。

下表每行的 op 后数字就是 `sail-riscv/model/extensions/FD/<file>:<line>`。`RM` 列的“是”表示该 op 生成 10 正向、5 非法 RM；所有行均生成 FS Off，`F关` / `D关` 列表示另生成对应 misa 拒绝。编码 guard 的原始表达式列用于复核分支条件。

| Clause | op:源码行 | RM | F关 | D关 | 映射 guard |
| --- | --- | :---: | :---: | :---: | --- |
| `FCVTMOD_W_D` | `FCVTMOD_W_D` → `zfa_insts.sail:781` | — | 是 | 是 | `currentlyEnabled(Ext_D) & currentlyEnabled(Ext_Zfa)` |
| `FLEQ_D` | `FLEQ_D` → `zfa_insts.sail:673` | — | 是 | 是 | `currentlyEnabled(Ext_D) & currentlyEnabled(Ext_Zfa)` |
| `FLEQ_H` | `FLEQ_H` → `zfa_insts.sail:572` | — | 是 | — | `currentlyEnabled(Ext_Zfh) & currentlyEnabled(Ext_Zfa)` |
| `FLEQ_S` | `FLEQ_S` → `zfa_insts.sail:622` | — | 是 | — | `currentlyEnabled(Ext_Zfa)` |
| `FLI_D` | `FLI_D` → `zfa_insts.sail:115` | — | 是 | 是 | `currentlyEnabled(Ext_D) & currentlyEnabled(Ext_Zfa)` |
| `FLI_H` | `FLI_H` → `zfa_insts.sail:15` | — | 是 | — | `(currentlyEnabled(Ext_Zfh) | currentlyEnabled(Ext_Zvfh)) & currentlyEnabled(Ext_Zfa)` |
| `FLI_S` | `FLI_S` → `zfa_insts.sail:65` | — | 是 | — | `currentlyEnabled(Ext_Zfa)` |
| `FLTQ_D` | `FLTQ_D` → `zfa_insts.sail:698` | — | 是 | 是 | `currentlyEnabled(Ext_D) & currentlyEnabled(Ext_Zfa)` |
| `FLTQ_H` | `FLTQ_H` → `zfa_insts.sail:597` | — | 是 | — | `currentlyEnabled(Ext_Zfh) & currentlyEnabled(Ext_Zfa)` |
| `FLTQ_S` | `FLTQ_S` → `zfa_insts.sail:647` | — | 是 | — | `currentlyEnabled(Ext_Zfa)` |
| `FMAXM_D` | `FMAXM_D` → `zfa_insts.sail:320` | — | 是 | 是 | `currentlyEnabled(Ext_D) & currentlyEnabled(Ext_Zfa)` |
| `FMAXM_H` | `FMAXM_H` → `zfa_insts.sail:196` | — | 是 | — | `currentlyEnabled(Ext_Zfh) & currentlyEnabled(Ext_Zfa)` |
| `FMAXM_S` | `FMAXM_S` → `zfa_insts.sail:258` | — | 是 | — | `currentlyEnabled(Ext_Zfa)` |
| `FMINM_D` | `FMINM_D` → `zfa_insts.sail:289` | — | 是 | 是 | `currentlyEnabled(Ext_D) & currentlyEnabled(Ext_Zfa)` |
| `FMINM_H` | `FMINM_H` → `zfa_insts.sail:165` | — | 是 | — | `currentlyEnabled(Ext_Zfh) & currentlyEnabled(Ext_Zfa)` |
| `FMINM_S` | `FMINM_S` → `zfa_insts.sail:227` | — | 是 | — | `currentlyEnabled(Ext_Zfa)` |
| `FROUNDNX_D` | `FROUNDNX_D` → `zfa_insts.sail:496` | 是 | 是 | 是 | `currentlyEnabled(Ext_D) & currentlyEnabled(Ext_Zfa)` |
| `FROUNDNX_H` | `FROUNDNX_H` → `zfa_insts.sail:380` | 是 | 是 | — | `currentlyEnabled(Ext_Zfh) & currentlyEnabled(Ext_Zfa)` |
| `FROUNDNX_S` | `FROUNDNX_S` → `zfa_insts.sail:438` | 是 | 是 | — | `currentlyEnabled(Ext_Zfa)` |
| `FROUND_D` | `FROUND_D` → `zfa_insts.sail:467` | 是 | 是 | 是 | `currentlyEnabled(Ext_D) & currentlyEnabled(Ext_Zfa)` |
| `FROUND_H` | `FROUND_H` → `zfa_insts.sail:351` | 是 | 是 | — | `currentlyEnabled(Ext_Zfh) & currentlyEnabled(Ext_Zfa)` |
| `FROUND_S` | `FROUND_S` → `zfa_insts.sail:409` | 是 | 是 | — | `currentlyEnabled(Ext_Zfa)` |
| `F_BIN_F_TYPE_D` | `FMAX_D` → `dext_insts.sail:666` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_F_TYPE_D` | `FMIN_D` → `dext_insts.sail:662` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_F_TYPE_D` | `FSGNJN_D` → `dext_insts.sail:654` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_F_TYPE_D` | `FSGNJX_D` → `dext_insts.sail:658` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_F_TYPE_D` | `FSGNJ_D` → `dext_insts.sail:650` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_F_TYPE_H` | `FMAX_H` → `zfh_insts.sail:324` | — | 是 | — | `haveHalfFPU()` |
| `F_BIN_F_TYPE_H` | `FMIN_H` → `zfh_insts.sail:320` | — | 是 | — | `haveHalfFPU()` |
| `F_BIN_F_TYPE_H` | `FSGNJN_H` → `zfh_insts.sail:312` | — | 是 | — | `haveHalfFPU()` |
| `F_BIN_F_TYPE_H` | `FSGNJX_H` → `zfh_insts.sail:316` | — | 是 | — | `haveHalfFPU()` |
| `F_BIN_F_TYPE_H` | `FSGNJ_H` → `zfh_insts.sail:308` | — | 是 | — | `haveHalfFPU()` |
| `F_BIN_RM_TYPE_D` | `FADD_D` → `dext_insts.sail:317` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_RM_TYPE_D` | `FDIV_D` → `dext_insts.sail:329` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_RM_TYPE_D` | `FMUL_D` → `dext_insts.sail:325` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_RM_TYPE_D` | `FSUB_D` → `dext_insts.sail:321` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])` |
| `F_BIN_RM_TYPE_H` | `FADD_H` → `zfh_insts.sail:176` | 是 | 是 | — | `haveHalfFPU()` |
| `F_BIN_RM_TYPE_H` | `FDIV_H` → `zfh_insts.sail:188` | 是 | 是 | — | `haveHalfFPU()` |
| `F_BIN_RM_TYPE_H` | `FMUL_H` → `zfh_insts.sail:184` | 是 | 是 | — | `haveHalfFPU()` |
| `F_BIN_RM_TYPE_H` | `FSUB_H` → `zfh_insts.sail:180` | 是 | 是 | — | `haveHalfFPU()` |
| `F_BIN_RM_TYPE_S` | `FADD_S` → `fext_insts.sail:429` | 是 | 是 | — | `haveSingleFPU()` |
| `F_BIN_RM_TYPE_S` | `FDIV_S` → `fext_insts.sail:441` | 是 | 是 | — | `haveSingleFPU()` |
| `F_BIN_RM_TYPE_S` | `FMUL_S` → `fext_insts.sail:437` | 是 | 是 | — | `haveSingleFPU()` |
| `F_BIN_RM_TYPE_S` | `FSUB_S` → `fext_insts.sail:433` | 是 | 是 | — | `haveSingleFPU()` |
| `F_BIN_TYPE_F_S` | `FMAX_S` → `fext_insts.sail:735` | — | 是 | — | `haveSingleFPU()` |
| `F_BIN_TYPE_F_S` | `FMIN_S` → `fext_insts.sail:731` | — | 是 | — | `haveSingleFPU()` |
| `F_BIN_TYPE_F_S` | `FSGNJN_S` → `fext_insts.sail:723` | — | 是 | — | `haveSingleFPU()` |
| `F_BIN_TYPE_F_S` | `FSGNJX_S` → `fext_insts.sail:727` | — | 是 | — | `haveSingleFPU()` |
| `F_BIN_TYPE_F_S` | `FSGNJ_S` → `fext_insts.sail:719` | — | 是 | — | `haveSingleFPU()` |
| `F_BIN_TYPE_X_S` | `FEQ_S` → `fext_insts.sail:739` | — | 是 | — | `haveSingleFPU()` |
| `F_BIN_TYPE_X_S` | `FLE_S` → `fext_insts.sail:747` | — | 是 | — | `haveSingleFPU()` |
| `F_BIN_TYPE_X_S` | `FLT_S` → `fext_insts.sail:743` | — | 是 | — | `haveSingleFPU()` |
| `F_BIN_X_TYPE_D` | `FEQ_D` → `dext_insts.sail:670` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])` |
| `F_BIN_X_TYPE_D` | `FLE_D` → `dext_insts.sail:678` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])` |
| `F_BIN_X_TYPE_D` | `FLT_D` → `dext_insts.sail:674` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])` |
| `F_BIN_X_TYPE_H` | `FEQ_H` → `zfh_insts.sail:328` | — | 是 | — | `haveHalfFPU()` |
| `F_BIN_X_TYPE_H` | `FLE_H` → `zfh_insts.sail:336` | — | 是 | — | `haveHalfFPU()` |
| `F_BIN_X_TYPE_H` | `FLT_H` → `zfh_insts.sail:332` | — | 是 | — | `haveHalfFPU()` |
| `F_MADD_TYPE_D` | `FMADD_D` → `dext_insts.sail:249` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])` |
| `F_MADD_TYPE_D` | `FMSUB_D` → `dext_insts.sail:253` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])` |
| `F_MADD_TYPE_D` | `FNMADD_D` → `dext_insts.sail:261` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])` |
| `F_MADD_TYPE_D` | `FNMSUB_D` → `dext_insts.sail:257` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])` |
| `F_MADD_TYPE_H` | `FMADD_H` → `zfh_insts.sail:240` | 是 | 是 | — | `haveHalfFPU()` |
| `F_MADD_TYPE_H` | `FMSUB_H` → `zfh_insts.sail:244` | 是 | 是 | — | `haveHalfFPU()` |
| `F_MADD_TYPE_H` | `FNMADD_H` → `zfh_insts.sail:252` | 是 | 是 | — | `haveHalfFPU()` |
| `F_MADD_TYPE_H` | `FNMSUB_H` → `zfh_insts.sail:248` | 是 | 是 | — | `haveHalfFPU()` |
| `F_MADD_TYPE_S` | `FMADD_S` → `fext_insts.sail:362` | 是 | 是 | — | `haveSingleFPU()` |
| `F_MADD_TYPE_S` | `FMSUB_S` → `fext_insts.sail:366` | 是 | 是 | — | `haveSingleFPU()` |
| `F_MADD_TYPE_S` | `FNMADD_S` → `fext_insts.sail:374` | 是 | 是 | — | `haveSingleFPU()` |
| `F_MADD_TYPE_S` | `FNMSUB_S` → `fext_insts.sail:370` | 是 | 是 | — | `haveSingleFPU()` |
| `F_UN_F_TYPE_D` | `FMV_D_X` → `dext_insts.sail:840` | — | — | 是 | `currentlyEnabled(Ext_D) & xlen >= 64` |
| `F_UN_F_TYPE_H` | `FMV_H_X` → `zfh_insts.sail:806` | — | 是 | — | `currentlyEnabled(Ext_Zfhmin) | currentlyEnabled(Ext_Zfbfmin)` |
| `F_UN_RM_FF_TYPE_D` | `FCVT_D_S` → `dext_insts.sail:407` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rd])` |
| `F_UN_RM_FF_TYPE_D` | `FCVT_S_D` → `dext_insts.sail:403` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs1])` |
| `F_UN_RM_FF_TYPE_D` | `FSQRT_D` → `dext_insts.sail:383` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs1, rd])` |
| `F_UN_RM_FF_TYPE_H` | `FCVT_D_H` → `zfh_insts.sail:522` | 是 | 是 | 是 | `haveHalfMin() & (haveDoubleFPU() & validDoubleRegs([rd]))` |
| `F_UN_RM_FF_TYPE_H` | `FCVT_H_D` → `zfh_insts.sail:514` | 是 | 是 | 是 | `haveHalfMin() & (haveDoubleFPU() & validDoubleRegs([rs1]))` |
| `F_UN_RM_FF_TYPE_H` | `FCVT_H_S` → `zfh_insts.sail:510` | 是 | 是 | — | `haveHalfMin()` |
| `F_UN_RM_FF_TYPE_H` | `FCVT_S_H` → `zfh_insts.sail:518` | 是 | 是 | — | `haveHalfMin()` |
| `F_UN_RM_FF_TYPE_H` | `FSQRT_H` → `zfh_insts.sail:490` | 是 | 是 | — | `haveHalfFPU()` |
| `F_UN_RM_FF_TYPE_S` | `FSQRT_S` → `fext_insts.sail:495` | 是 | 是 | — | `haveSingleFPU()` |
| `F_UN_RM_FX_TYPE_D` | `FCVT_LU_D` → `dext_insts.sail:417` | 是 | — | 是 | `haveDoubleFPU() & xlen >= 64` |
| `F_UN_RM_FX_TYPE_D` | `FCVT_L_D` → `dext_insts.sail:413` | 是 | — | 是 | `haveDoubleFPU() & xlen >= 64` |
| `F_UN_RM_FX_TYPE_D` | `FCVT_WU_D` → `dext_insts.sail:391` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs1])` |
| `F_UN_RM_FX_TYPE_D` | `FCVT_W_D` → `dext_insts.sail:387` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs1])` |
| `F_UN_RM_FX_TYPE_H` | `FCVT_LU_H` → `zfh_insts.sail:535` | 是 | 是 | — | `haveHalfFPU() & xlen >= 64` |
| `F_UN_RM_FX_TYPE_H` | `FCVT_L_H` → `zfh_insts.sail:531` | 是 | 是 | — | `haveHalfFPU() & xlen >= 64` |
| `F_UN_RM_FX_TYPE_H` | `FCVT_WU_H` → `zfh_insts.sail:498` | 是 | 是 | — | `haveHalfFPU()` |
| `F_UN_RM_FX_TYPE_H` | `FCVT_W_H` → `zfh_insts.sail:494` | 是 | 是 | — | `haveHalfFPU()` |
| `F_UN_RM_FX_TYPE_S` | `FCVT_LU_S` → `fext_insts.sail:521` | 是 | 是 | — | `haveSingleFPU() & xlen >= 64` |
| `F_UN_RM_FX_TYPE_S` | `FCVT_L_S` → `fext_insts.sail:517` | 是 | 是 | — | `haveSingleFPU() & xlen >= 64` |
| `F_UN_RM_FX_TYPE_S` | `FCVT_WU_S` → `fext_insts.sail:503` | 是 | 是 | — | `haveSingleFPU()` |
| `F_UN_RM_FX_TYPE_S` | `FCVT_W_S` → `fext_insts.sail:499` | 是 | 是 | — | `haveSingleFPU()` |
| `F_UN_RM_XF_TYPE_D` | `FCVT_D_L` → `dext_insts.sail:421` | 是 | — | 是 | `haveDoubleFPU() & xlen >= 64` |
| `F_UN_RM_XF_TYPE_D` | `FCVT_D_LU` → `dext_insts.sail:425` | 是 | — | 是 | `haveDoubleFPU() & xlen >= 64` |
| `F_UN_RM_XF_TYPE_D` | `FCVT_D_W` → `dext_insts.sail:395` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rd])` |
| `F_UN_RM_XF_TYPE_D` | `FCVT_D_WU` → `dext_insts.sail:399` | 是 | — | 是 | `haveDoubleFPU() & validDoubleRegs([rd])` |
| `F_UN_RM_XF_TYPE_H` | `FCVT_H_L` → `zfh_insts.sail:539` | 是 | 是 | — | `haveHalfFPU() & xlen >= 64` |
| `F_UN_RM_XF_TYPE_H` | `FCVT_H_LU` → `zfh_insts.sail:543` | 是 | 是 | — | `haveHalfFPU() & xlen >= 64` |
| `F_UN_RM_XF_TYPE_H` | `FCVT_H_W` → `zfh_insts.sail:502` | 是 | 是 | — | `haveHalfFPU()` |
| `F_UN_RM_XF_TYPE_H` | `FCVT_H_WU` → `zfh_insts.sail:506` | 是 | 是 | — | `haveHalfFPU()` |
| `F_UN_RM_XF_TYPE_S` | `FCVT_S_L` → `fext_insts.sail:525` | 是 | 是 | — | `haveSingleFPU() & xlen >= 64` |
| `F_UN_RM_XF_TYPE_S` | `FCVT_S_LU` → `fext_insts.sail:529` | 是 | 是 | — | `haveSingleFPU() & xlen >= 64` |
| `F_UN_RM_XF_TYPE_S` | `FCVT_S_W` → `fext_insts.sail:507` | 是 | 是 | — | `haveSingleFPU()` |
| `F_UN_RM_XF_TYPE_S` | `FCVT_S_WU` → `fext_insts.sail:511` | 是 | 是 | — | `haveSingleFPU()` |
| `F_UN_TYPE_F_S` | `FMV_W_X` → `fext_insts.sail:906` | — | 是 | — | `currentlyEnabled(Ext_F)` |
| `F_UN_TYPE_X_S` | `FCLASS_S` → `fext_insts.sail:898` | — | 是 | — | `haveSingleFPU()` |
| `F_UN_TYPE_X_S` | `FMV_X_W` → `fext_insts.sail:902` | — | 是 | — | `currentlyEnabled(Ext_F)` |
| `F_UN_X_TYPE_D` | `FCLASS_D` → `dext_insts.sail:830` | — | — | 是 | `haveDoubleFPU() & validDoubleRegs([rs1])` |
| `F_UN_X_TYPE_D` | `FMV_X_D` → `dext_insts.sail:836` | — | — | 是 | `currentlyEnabled(Ext_D) & xlen >= 64` |
| `F_UN_X_TYPE_H` | `FCLASS_H` → `zfh_insts.sail:798` | — | 是 | — | `haveHalfFPU()` |
| `F_UN_X_TYPE_H` | `FMV_X_H` → `zfh_insts.sail:802` | — | 是 | — | `currentlyEnabled(Ext_Zfhmin) | currentlyEnabled(Ext_Zfbfmin)` |

## 固定 IR 下不可达与适用边界

- `hartSupports(Ext_F/D/Zfh/Zfa/Zfbfmin/Zicsr)` 与 `xlen`、`flen` 是生成 IR/配置的结构性常量，不能通过本 runner 的 `misa` 或 `mstatus` 注入把它们关掉；需重生 IR 或换配置，故本批**不**标这些 guard 反向覆盖。`Zfa`、`Zfh` 是编译期扩展能力，不对应运行时 misa 位。特别是 H 搬运可能由 Zfhmin 或 Zfbfmin 任一支持，不能用假造的 misa.Zfh 位做拒绝。
- `currentlyEnabled(Ext_D)` 在 `fdext_control.sail:19` 只检查 misa.D、FS、FLEN、Zicsr，并不检查 misa.F。因此类型化 D op 在仅关闭 misa.F 且 D 保持开启时不应被本批伪造为译码拒绝；Zfa D op 另依赖 `currentlyEnabled(Ext_Zfa)`，关闭 F 则可拒绝。H 的 `FCVT_H_D` / `FCVT_D_H` 同时要求 D，因而有 D 位负例。
- `Zfinx/Zhinx/Zdinx` 替代路由、RV32 `validDoubleRegs` 奇数寄存器、RV32 专属 `FMVH_X_D`/`FMVP_D_X` 均不属于当前固定 RV64/FPR IR；本批不声称这些分支覆盖。`Fcsr_RM_Fatal`、Zicsr 关位以及扩展支持位关闭也需另一配置。
- 当前 JSON runner 检查具体输入的 SAT、观察字段差异 UNSAT、译码构造器/字段、重编码和执行结果；即使动态全部通过，也只是这些输入对上述源码条件的见证，不是插桩的全模型 branch coverage。
