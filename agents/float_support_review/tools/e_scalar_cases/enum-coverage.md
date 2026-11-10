# E 标量类型化 enum 覆盖

此表由 `inventory.py` 从当前 Sail 编码映射、原主实例和增补实例生成。
27 个 clause 的 90 个实际 enum 均已有本目录逐项真实编码与写回证明：
原有 28 项见 `v2-proofs.json`，增补 62 项见 `enum-proofs.json`。
带 RM 字段的 enum 至少一条具体 RNE 实例；无 RM 字段的 enum 至少一条合法实例。
其他 RM 路由见 `rm-v2-proofs.json`。

| Clause / enum | 格式 | 有效 RM | 映射 guard | 状态 |
|---|---|---|---|---|
| `F_BIN_F_TYPE_D` / `FMAX_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:666`） | 增补 PASS |
| `F_BIN_F_TYPE_D` / `FMIN_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:662`） | 增补 PASS |
| `F_BIN_F_TYPE_D` / `FSGNJN_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:654`） | 增补 PASS |
| `F_BIN_F_TYPE_D` / `FSGNJX_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:658`） | 增补 PASS |
| `F_BIN_F_TYPE_D` / `FSGNJ_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:650`） | 原有 PASS |
| `F_BIN_F_TYPE_H` / `FMAX_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:324`） | 增补 PASS |
| `F_BIN_F_TYPE_H` / `FMIN_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:320`） | 增补 PASS |
| `F_BIN_F_TYPE_H` / `FSGNJN_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:312`） | 增补 PASS |
| `F_BIN_F_TYPE_H` / `FSGNJX_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:316`） | 增补 PASS |
| `F_BIN_F_TYPE_H` / `FSGNJ_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:308`） | 原有 PASS |
| `F_BIN_RM_TYPE_D` / `FADD_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:317`） | 增补 PASS |
| `F_BIN_RM_TYPE_D` / `FDIV_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:329`） | 增补 PASS |
| `F_BIN_RM_TYPE_D` / `FMUL_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:325`） | 增补 PASS |
| `F_BIN_RM_TYPE_D` / `FSUB_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1, rd])`（`dext_insts.sail:321`） | 增补 PASS |
| `F_BIN_RM_TYPE_H` / `FADD_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:176`） | 原有 PASS |
| `F_BIN_RM_TYPE_H` / `FDIV_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:188`） | 增补 PASS |
| `F_BIN_RM_TYPE_H` / `FMUL_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:184`） | 增补 PASS |
| `F_BIN_RM_TYPE_H` / `FSUB_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:180`） | 增补 PASS |
| `F_BIN_RM_TYPE_S` / `FADD_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:429`） | 增补 PASS |
| `F_BIN_RM_TYPE_S` / `FDIV_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:441`） | 增补 PASS |
| `F_BIN_RM_TYPE_S` / `FMUL_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:437`） | 增补 PASS |
| `F_BIN_RM_TYPE_S` / `FSUB_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:433`） | 增补 PASS |
| `F_BIN_TYPE_F_S` / `FMAX_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:735`） | 增补 PASS |
| `F_BIN_TYPE_F_S` / `FMIN_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:731`） | 增补 PASS |
| `F_BIN_TYPE_F_S` / `FSGNJN_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:723`） | 增补 PASS |
| `F_BIN_TYPE_F_S` / `FSGNJX_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:727`） | 增补 PASS |
| `F_BIN_TYPE_F_S` / `FSGNJ_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:719`） | 原有 PASS |
| `F_BIN_TYPE_X_S` / `FEQ_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:739`） | 原有 PASS |
| `F_BIN_TYPE_X_S` / `FLE_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:747`） | 增补 PASS |
| `F_BIN_TYPE_X_S` / `FLT_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:743`） | 增补 PASS |
| `F_BIN_X_TYPE_D` / `FEQ_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])`（`dext_insts.sail:670`） | 原有 PASS |
| `F_BIN_X_TYPE_D` / `FLE_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])`（`dext_insts.sail:678`） | 增补 PASS |
| `F_BIN_X_TYPE_D` / `FLT_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs2, rs1])`（`dext_insts.sail:674`） | 增补 PASS |
| `F_BIN_X_TYPE_H` / `FEQ_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:328`） | 原有 PASS |
| `F_BIN_X_TYPE_H` / `FLE_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:336`） | 增补 PASS |
| `F_BIN_X_TYPE_H` / `FLT_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:332`） | 增补 PASS |
| `F_MADD_TYPE_D` / `FMADD_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])`（`dext_insts.sail:249`） | 原有 PASS |
| `F_MADD_TYPE_D` / `FMSUB_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])`（`dext_insts.sail:253`） | 增补 PASS |
| `F_MADD_TYPE_D` / `FNMADD_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])`（`dext_insts.sail:261`） | 增补 PASS |
| `F_MADD_TYPE_D` / `FNMSUB_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs3, rs2, rs1, rd])`（`dext_insts.sail:257`） | 增补 PASS |
| `F_MADD_TYPE_H` / `FMADD_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:240`） | 原有 PASS |
| `F_MADD_TYPE_H` / `FMSUB_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:244`） | 增补 PASS |
| `F_MADD_TYPE_H` / `FNMADD_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:252`） | 增补 PASS |
| `F_MADD_TYPE_H` / `FNMSUB_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:248`） | 增补 PASS |
| `F_MADD_TYPE_S` / `FMADD_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:362`） | 原有 PASS |
| `F_MADD_TYPE_S` / `FMSUB_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:366`） | 增补 PASS |
| `F_MADD_TYPE_S` / `FNMADD_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:374`） | 增补 PASS |
| `F_MADD_TYPE_S` / `FNMSUB_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:370`） | 增补 PASS |
| `F_UN_F_TYPE_D` / `FMV_D_X` | X | 无 | `currentlyEnabled(Ext_D) & xlen >= 64`（`dext_insts.sail:840`） | 原有 PASS |
| `F_UN_F_TYPE_H` / `FMV_H_X` | X | 无 | `currentlyEnabled(Ext_Zfhmin) | currentlyEnabled(Ext_Zfbfmin)`（`zfh_insts.sail:806`） | 原有 PASS |
| `F_UN_RM_FF_TYPE_D` / `FCVT_D_S` | S→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rd])`（`dext_insts.sail:407`） | 增补 PASS |
| `F_UN_RM_FF_TYPE_D` / `FCVT_S_D` | D→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs1])`（`dext_insts.sail:403`） | 增补 PASS |
| `F_UN_RM_FF_TYPE_D` / `FSQRT_D` | D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs1, rd])`（`dext_insts.sail:383`） | 原有 PASS |
| `F_UN_RM_FF_TYPE_H` / `FCVT_D_H` | H→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfMin() & (haveDoubleFPU() & validDoubleRegs([rd]))`（`zfh_insts.sail:522`） | 增补 PASS |
| `F_UN_RM_FF_TYPE_H` / `FCVT_H_D` | D→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfMin() & (haveDoubleFPU() & validDoubleRegs([rs1]))`（`zfh_insts.sail:514`） | 增补 PASS |
| `F_UN_RM_FF_TYPE_H` / `FCVT_H_S` | S→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfMin()`（`zfh_insts.sail:510`） | 增补 PASS |
| `F_UN_RM_FF_TYPE_H` / `FCVT_S_H` | H→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfMin()`（`zfh_insts.sail:518`） | 增补 PASS |
| `F_UN_RM_FF_TYPE_H` / `FSQRT_H` | H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:490`） | 原有 PASS |
| `F_UN_RM_FF_TYPE_S` / `FSQRT_S` | S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:495`） | 原有 PASS |
| `F_UN_RM_FX_TYPE_D` / `FCVT_LU_D` | D→LU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & xlen >= 64`（`dext_insts.sail:417`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_D` / `FCVT_L_D` | D→L | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & xlen >= 64`（`dext_insts.sail:413`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_D` / `FCVT_WU_D` | D→WU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs1])`（`dext_insts.sail:391`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_D` / `FCVT_W_D` | D→W | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rs1])`（`dext_insts.sail:387`） | 原有 PASS |
| `F_UN_RM_FX_TYPE_H` / `FCVT_LU_H` | H→LU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU() & xlen >= 64`（`zfh_insts.sail:535`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_H` / `FCVT_L_H` | H→L | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU() & xlen >= 64`（`zfh_insts.sail:531`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_H` / `FCVT_WU_H` | H→WU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:498`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_H` / `FCVT_W_H` | H→W | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:494`） | 原有 PASS |
| `F_UN_RM_FX_TYPE_S` / `FCVT_LU_S` | S→LU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU() & xlen >= 64`（`fext_insts.sail:521`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_S` / `FCVT_L_S` | S→L | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU() & xlen >= 64`（`fext_insts.sail:517`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_S` / `FCVT_WU_S` | S→WU | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:503`） | 增补 PASS |
| `F_UN_RM_FX_TYPE_S` / `FCVT_W_S` | S→W | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:499`） | 原有 PASS |
| `F_UN_RM_XF_TYPE_D` / `FCVT_D_L` | L→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & xlen >= 64`（`dext_insts.sail:421`） | 增补 PASS |
| `F_UN_RM_XF_TYPE_D` / `FCVT_D_LU` | LU→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & xlen >= 64`（`dext_insts.sail:425`） | 增补 PASS |
| `F_UN_RM_XF_TYPE_D` / `FCVT_D_W` | W→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rd])`（`dext_insts.sail:395`） | 原有 PASS |
| `F_UN_RM_XF_TYPE_D` / `FCVT_D_WU` | WU→D | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveDoubleFPU() & validDoubleRegs([rd])`（`dext_insts.sail:399`） | 增补 PASS |
| `F_UN_RM_XF_TYPE_H` / `FCVT_H_L` | L→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU() & xlen >= 64`（`zfh_insts.sail:539`） | 增补 PASS |
| `F_UN_RM_XF_TYPE_H` / `FCVT_H_LU` | LU→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU() & xlen >= 64`（`zfh_insts.sail:543`） | 增补 PASS |
| `F_UN_RM_XF_TYPE_H` / `FCVT_H_W` | W→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:502`） | 原有 PASS |
| `F_UN_RM_XF_TYPE_H` / `FCVT_H_WU` | WU→H | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveHalfFPU()`（`zfh_insts.sail:506`） | 增补 PASS |
| `F_UN_RM_XF_TYPE_S` / `FCVT_S_L` | L→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU() & xlen >= 64`（`fext_insts.sail:525`） | 增补 PASS |
| `F_UN_RM_XF_TYPE_S` / `FCVT_S_LU` | LU→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU() & xlen >= 64`（`fext_insts.sail:529`） | 增补 PASS |
| `F_UN_RM_XF_TYPE_S` / `FCVT_S_W` | W→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:507`） | 原有 PASS |
| `F_UN_RM_XF_TYPE_S` / `FCVT_S_WU` | WU→S | RNE/RTZ/RDN/RUP/RMM；DYN 仅在 fcsr.FRM=0–4 时合法 | `haveSingleFPU()`（`fext_insts.sail:511`） | 增补 PASS |
| `F_UN_TYPE_F_S` / `FMV_W_X` | X | 无 | `currentlyEnabled(Ext_F)`（`fext_insts.sail:906`） | 原有 PASS |
| `F_UN_TYPE_X_S` / `FCLASS_S` | S | 无 | `haveSingleFPU()`（`fext_insts.sail:898`） | 原有 PASS |
| `F_UN_TYPE_X_S` / `FMV_X_W` | W | 无 | `currentlyEnabled(Ext_F)`（`fext_insts.sail:902`） | 原有 PASS |
| `F_UN_X_TYPE_D` / `FCLASS_D` | D | 无 | `haveDoubleFPU() & validDoubleRegs([rs1])`（`dext_insts.sail:830`） | 原有 PASS |
| `F_UN_X_TYPE_D` / `FMV_X_D` | D | 无 | `currentlyEnabled(Ext_D) & xlen >= 64`（`dext_insts.sail:836`） | 原有 PASS |
| `F_UN_X_TYPE_H` / `FCLASS_H` | H | 无 | `haveHalfFPU()`（`zfh_insts.sail:798`） | 原有 PASS |
| `F_UN_X_TYPE_H` / `FMV_X_H` | H | 无 | `currentlyEnabled(Ext_Zfhmin) | currentlyEnabled(Ext_Zfbfmin)`（`zfh_insts.sail:802`） | 原有 PASS |

RM 编码合法域：RNE/RTZ/RDN/RUP/RMM/DYN；DYN 需 `fcsr.FRM=0–4`。
静态 RM 5/6 与动态 FRM 5/6/7 的拒绝路径见 `negative-proof.json`。
单实例不覆盖该 enum 的所有数值边界或全部舍入模式。
