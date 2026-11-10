# E 标量 enum/特殊域缺口清单

状态：**增补前快照**。扩展后的逐项覆盖见 `enum-coverage.md`；保留此表以说明选例依据。

此清单由 `inventory.py` 从当前 `clause-matrix.md`、Sail 三个 FD 映射文件和本目录主实例自动生成。
27 个类型化标量 clause 共 90 个实际 enum：本目录已有 28 项逐编码 PASS，
外部 E runner smoke 已有 FADD.S/D 两项，各余 **60 个 enum** 未逐项验收。
外部两项没有并入本目录证明；表中“已测”仅表示一个具体输入。

带 `rm` tuple 字段的映射可编码 RNE/RTZ/RDN/RUP/RMM/DYN；
DYN 仅当 `fcsr.FRM` 为 0–4 时合法。编码 5、6 没有映射，动态 FRM 5–7
由 `select_instr_or_fcsr_rm` 的保留行为处理。其余映射无舍入字段。
下表只列合法域，不将所有 RM 组合视作已测。

| Clause / enum | 格式 | 有效 RM | 映射 guard | 状态 |
|---|---|---|---|---|
| `F_BIN_F_TYPE_D` / `FMAX_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:666`） | 缺口 |
| `F_BIN_F_TYPE_D` / `FMIN_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:662`） | 缺口 |
| `F_BIN_F_TYPE_D` / `FSGNJN_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:654`） | 缺口 |
| `F_BIN_F_TYPE_D` / `FSGNJX_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:658`） | 缺口 |
| `F_BIN_F_TYPE_D` / `FSGNJ_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:650`） | 本目录 PASS |
| `F_BIN_F_TYPE_H` / `FMAX_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:324`） | 缺口 |
| `F_BIN_F_TYPE_H` / `FMIN_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:320`） | 缺口 |
| `F_BIN_F_TYPE_H` / `FSGNJN_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:312`） | 缺口 |
| `F_BIN_F_TYPE_H` / `FSGNJX_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:316`） | 缺口 |
| `F_BIN_F_TYPE_H` / `FSGNJ_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:308`） | 本目录 PASS |
| `F_BIN_RM_TYPE_D` / `FADD_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:317`） | 外部 FADD smoke |
| `F_BIN_RM_TYPE_D` / `FDIV_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:329`） | 缺口 |
| `F_BIN_RM_TYPE_D` / `FMUL_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:325`） | 缺口 |
| `F_BIN_RM_TYPE_D` / `FSUB_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:321`） | 缺口 |
| `F_BIN_RM_TYPE_H` / `FADD_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:176`） | 本目录 PASS |
| `F_BIN_RM_TYPE_H` / `FDIV_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:188`） | 缺口 |
| `F_BIN_RM_TYPE_H` / `FMUL_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:184`） | 缺口 |
| `F_BIN_RM_TYPE_H` / `FSUB_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:180`） | 缺口 |
| `F_BIN_RM_TYPE_S` / `FADD_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:429`） | 外部 FADD smoke |
| `F_BIN_RM_TYPE_S` / `FDIV_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:441`） | 缺口 |
| `F_BIN_RM_TYPE_S` / `FMUL_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:437`） | 缺口 |
| `F_BIN_RM_TYPE_S` / `FSUB_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:433`） | 缺口 |
| `F_BIN_TYPE_F_S` / `FMAX_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:735`） | 缺口 |
| `F_BIN_TYPE_F_S` / `FMIN_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:731`） | 缺口 |
| `F_BIN_TYPE_F_S` / `FSGNJN_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:723`） | 缺口 |
| `F_BIN_TYPE_F_S` / `FSGNJX_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:727`） | 缺口 |
| `F_BIN_TYPE_F_S` / `FSGNJ_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:719`） | 本目录 PASS |
| `F_BIN_TYPE_X_S` / `FEQ_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:739`） | 本目录 PASS |
| `F_BIN_TYPE_X_S` / `FLE_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:747`） | 缺口 |
| `F_BIN_TYPE_X_S` / `FLT_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:743`） | 缺口 |
| `F_BIN_X_TYPE_D` / `FEQ_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])`（`dext_insts.sail:670`） | 本目录 PASS |
| `F_BIN_X_TYPE_D` / `FLE_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])`（`dext_insts.sail:678`） | 缺口 |
| `F_BIN_X_TYPE_D` / `FLT_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])`（`dext_insts.sail:674`） | 缺口 |
| `F_BIN_X_TYPE_H` / `FEQ_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:328`） | 本目录 PASS |
| `F_BIN_X_TYPE_H` / `FLE_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:336`） | 缺口 |
| `F_BIN_X_TYPE_H` / `FLT_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:332`） | 缺口 |
| `F_MADD_TYPE_D` / `FMADD_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])`（`dext_insts.sail:249`） | 本目录 PASS |
| `F_MADD_TYPE_D` / `FMSUB_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])`（`dext_insts.sail:253`） | 缺口 |
| `F_MADD_TYPE_D` / `FNMADD_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])`（`dext_insts.sail:261`） | 缺口 |
| `F_MADD_TYPE_D` / `FNMSUB_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])`（`dext_insts.sail:257`） | 缺口 |
| `F_MADD_TYPE_H` / `FMADD_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:240`） | 本目录 PASS |
| `F_MADD_TYPE_H` / `FMSUB_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:244`） | 缺口 |
| `F_MADD_TYPE_H` / `FNMADD_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:252`） | 缺口 |
| `F_MADD_TYPE_H` / `FNMSUB_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:248`） | 缺口 |
| `F_MADD_TYPE_S` / `FMADD_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:362`） | 本目录 PASS |
| `F_MADD_TYPE_S` / `FMSUB_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:366`） | 缺口 |
| `F_MADD_TYPE_S` / `FNMADD_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:374`） | 缺口 |
| `F_MADD_TYPE_S` / `FNMSUB_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:370`） | 缺口 |
| `F_UN_F_TYPE_D` / `FMV_D_X` | X | 无 | `currentlyEnabled(Ext_D) & xlen >= 64`（`dext_insts.sail:840`） | 本目录 PASS |
| `F_UN_F_TYPE_H` / `FMV_H_X` | X | 无 | `currentlyEnabled(Ext_Zfhmin) | currentlyEnabled(Ext_Zfbfmin)`（`zfh_insts.sail:806`） | 本目录 PASS |
| `F_UN_RM_FF_TYPE_D` / `FCVT_D_S` | S→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rd])`（`dext_insts.sail:407`） | 缺口 |
| `F_UN_RM_FF_TYPE_D` / `FCVT_S_D` | D→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs1])`（`dext_insts.sail:403`） | 缺口 |
| `F_UN_RM_FF_TYPE_D` / `FSQRT_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs1, rd])`（`dext_insts.sail:383`） | 本目录 PASS |
| `F_UN_RM_FF_TYPE_H` / `FCVT_D_H` | H→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfMin() & (haveDoubleFPU() & validDoubleRegs([rd]))`（`zfh_insts.sail:522`） | 缺口 |
| `F_UN_RM_FF_TYPE_H` / `FCVT_H_D` | D→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfMin() & (haveDoubleFPU() & validDoubleRegs([rs1]))`（`zfh_insts.sail:514`） | 缺口 |
| `F_UN_RM_FF_TYPE_H` / `FCVT_H_S` | S→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfMin()`（`zfh_insts.sail:510`） | 缺口 |
| `F_UN_RM_FF_TYPE_H` / `FCVT_S_H` | H→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfMin()`（`zfh_insts.sail:518`） | 缺口 |
| `F_UN_RM_FF_TYPE_H` / `FSQRT_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:490`） | 本目录 PASS |
| `F_UN_RM_FF_TYPE_S` / `FSQRT_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:495`） | 本目录 PASS |
| `F_UN_RM_FX_TYPE_D` / `FCVT_LU_D` | D→LU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & xlen >= 64`（`dext_insts.sail:417`） | 缺口 |
| `F_UN_RM_FX_TYPE_D` / `FCVT_L_D` | D→L | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & xlen >= 64`（`dext_insts.sail:413`） | 缺口 |
| `F_UN_RM_FX_TYPE_D` / `FCVT_WU_D` | D→WU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs1])`（`dext_insts.sail:391`） | 缺口 |
| `F_UN_RM_FX_TYPE_D` / `FCVT_W_D` | D→W | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs1])`（`dext_insts.sail:387`） | 本目录 PASS |
| `F_UN_RM_FX_TYPE_H` / `FCVT_LU_H` | H→LU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU() & xlen >= 64`（`zfh_insts.sail:535`） | 缺口 |
| `F_UN_RM_FX_TYPE_H` / `FCVT_L_H` | H→L | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU() & xlen >= 64`（`zfh_insts.sail:531`） | 缺口 |
| `F_UN_RM_FX_TYPE_H` / `FCVT_WU_H` | H→WU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:498`） | 缺口 |
| `F_UN_RM_FX_TYPE_H` / `FCVT_W_H` | H→W | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:494`） | 本目录 PASS |
| `F_UN_RM_FX_TYPE_S` / `FCVT_LU_S` | S→LU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU() & xlen >= 64`（`fext_insts.sail:521`） | 缺口 |
| `F_UN_RM_FX_TYPE_S` / `FCVT_L_S` | S→L | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU() & xlen >= 64`（`fext_insts.sail:517`） | 缺口 |
| `F_UN_RM_FX_TYPE_S` / `FCVT_WU_S` | S→WU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:503`） | 缺口 |
| `F_UN_RM_FX_TYPE_S` / `FCVT_W_S` | S→W | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:499`） | 本目录 PASS |
| `F_UN_RM_XF_TYPE_D` / `FCVT_D_L` | L→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & xlen >= 64`（`dext_insts.sail:421`） | 缺口 |
| `F_UN_RM_XF_TYPE_D` / `FCVT_D_LU` | LU→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & xlen >= 64`（`dext_insts.sail:425`） | 缺口 |
| `F_UN_RM_XF_TYPE_D` / `FCVT_D_W` | W→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rd])`（`dext_insts.sail:395`） | 本目录 PASS |
| `F_UN_RM_XF_TYPE_D` / `FCVT_D_WU` | WU→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rd])`（`dext_insts.sail:399`） | 缺口 |
| `F_UN_RM_XF_TYPE_H` / `FCVT_H_L` | L→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU() & xlen >= 64`（`zfh_insts.sail:539`） | 缺口 |
| `F_UN_RM_XF_TYPE_H` / `FCVT_H_LU` | LU→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU() & xlen >= 64`（`zfh_insts.sail:543`） | 缺口 |
| `F_UN_RM_XF_TYPE_H` / `FCVT_H_W` | W→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:502`） | 本目录 PASS |
| `F_UN_RM_XF_TYPE_H` / `FCVT_H_WU` | WU→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:506`） | 缺口 |
| `F_UN_RM_XF_TYPE_S` / `FCVT_S_L` | L→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU() & xlen >= 64`（`fext_insts.sail:525`） | 缺口 |
| `F_UN_RM_XF_TYPE_S` / `FCVT_S_LU` | LU→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU() & xlen >= 64`（`fext_insts.sail:529`） | 缺口 |
| `F_UN_RM_XF_TYPE_S` / `FCVT_S_W` | W→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:507`） | 本目录 PASS |
| `F_UN_RM_XF_TYPE_S` / `FCVT_S_WU` | WU→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:511`） | 缺口 |
| `F_UN_TYPE_F_S` / `FMV_W_X` | X | 无 | `currentlyEnabled(Ext_F)`（`fext_insts.sail:906`） | 本目录 PASS |
| `F_UN_TYPE_X_S` / `FCLASS_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:898`） | 本目录 PASS |
| `F_UN_TYPE_X_S` / `FMV_X_W` | W | 无 | `currentlyEnabled(Ext_F)`（`fext_insts.sail:902`） | 本目录 PASS |
| `F_UN_X_TYPE_D` / `FCLASS_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs1])`（`dext_insts.sail:830`） | 本目录 PASS |
| `F_UN_X_TYPE_D` / `FMV_X_D` | D | 无 | `currentlyEnabled(Ext_D) & xlen >= 64`（`dext_insts.sail:836`） | 本目录 PASS |
| `F_UN_X_TYPE_H` / `FCLASS_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:798`） | 本目录 PASS |
| `F_UN_X_TYPE_H` / `FMV_X_H` | H | 无 | `currentlyEnabled(Ext_Zfhmin) | currentlyEnabled(Ext_Zfbfmin)`（`zfh_insts.sail:802`） | 本目录 PASS |

## Zfa 固定 clause 的剩余域

- `FCVTMOD_W_D`：编码固定 RTZ（`zfa_insts.sail:781–784`）。已测 `2^32+3` → 3、NV；
  未逐项测零、次正规、小于 1、负数、分数 NX、NaN/∞、指数 ≥84。
- `FLI_H/S/D`：每格式有 32 个常数索引（0–31），本目录仅索引 16 的 `1.0`。
  GNU as 输入应写浮点数值，不能把 `0x10` 当索引传给助记符。
- `FROUND_H/S/D` 与 `FROUNDNX_H/S/D`：本目录仅 RNE、1.5；其余四个静态 RM、
  有效 DYN、整数/零/负数、NaN/∞及 flags 边界未测。
- `FLEQ_H/S/D` 与 `FLTQ_H/S/D`：本目录仅普通数真值；qNaN、sNaN、
  正负零、假值和 NV 边界未测。
- `FMINM_H/S/D` 与 `FMAXM_H/S/D`：rs1=qNaN、rs2=qNaN、rs2=sNaN/NV、
  `-0/+0` 已测；反向零顺序、rs1=sNaN、双 NaN 和一般数值序关系未测。
- H 映射 guard 明确需要 `Ext_Zfh` 而非仅 `Ext_Zfhmin`；D 项需要 `Ext_D`，
  所有 Zfa 项还需 `Ext_Zfa`。当前固定 RV64 配置满足这些 guard，
  不能把这批结果外推到不同扩展组合。

## 计数

- 类型化：90 enum，28 本目录已测，2 外部 smoke，60 缺口。
- Zfa：22 个归属固定 clause 已各有编码，但上列特殊输入域仍有缺口。
