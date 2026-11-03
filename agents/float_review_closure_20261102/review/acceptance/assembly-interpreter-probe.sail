union fregidx = { Fregidx : bits(5) }

union regidx = { Regidx : bits(5) }

enum rounding_mode = {RM_RNE, RM_RTZ, RM_RDN, RM_RUP, RM_RMM, RM_DYN}

enum f_un_rm_ff_op_D = {FSQRT_D, FCVT_S_D, FCVT_D_S}

enum f_un_rm_ff_op_H = {FSQRT_H, FCVT_H_S, FCVT_H_D, FCVT_S_H, FCVT_D_H}

enum f_un_rm_xf_op_D = {FCVT_D_W, FCVT_D_WU,    // RV32 and RV64
                        FCVT_D_L, FCVT_D_LU}

enum f_un_rm_xf_op_S = { FCVT_S_W, FCVT_S_WU, // RV32 and RV64
                         FCVT_S_L, FCVT_S_LU }

mapping frm_mnemonic : rounding_mode <-> string = {
  RM_RNE <-> "rne",
  RM_RTZ <-> "rtz",
  RM_RDN <-> "rdn",
  RM_RUP <-> "rup",
  RM_RMM <-> "rmm",
  RM_DYN <-> "dyn"
}

mapping freg_or_reg_name : fregidx <-> string = {

  Fregidx(0b00000) <-> "f0",

  Fregidx(0b00001) <-> "f1",

  Fregidx(0b00010) <-> "f2",

  Fregidx(0b00011) <-> "f3",

  Fregidx(0b00100) <-> "f4",

  Fregidx(0b00101) <-> "f5",

  Fregidx(0b00110) <-> "f6",

  Fregidx(0b00111) <-> "f7",

  Fregidx(0b01000) <-> "f8",

  Fregidx(0b01001) <-> "f9",

  Fregidx(0b01010) <-> "f10",

  Fregidx(0b01011) <-> "f11",

  Fregidx(0b01100) <-> "f12",

  Fregidx(0b01101) <-> "f13",

  Fregidx(0b01110) <-> "f14",

  Fregidx(0b01111) <-> "f15",

  Fregidx(0b10000) <-> "f16",

  Fregidx(0b10001) <-> "f17",

  Fregidx(0b10010) <-> "f18",

  Fregidx(0b10011) <-> "f19",

  Fregidx(0b10100) <-> "f20",

  Fregidx(0b10101) <-> "f21",

  Fregidx(0b10110) <-> "f22",

  Fregidx(0b10111) <-> "f23",

  Fregidx(0b11000) <-> "f24",

  Fregidx(0b11001) <-> "f25",

  Fregidx(0b11010) <-> "f26",

  Fregidx(0b11011) <-> "f27",

  Fregidx(0b11100) <-> "f28",

  Fregidx(0b11101) <-> "f29",

  Fregidx(0b11110) <-> "f30",

  Fregidx(0b11111) <-> "f31"

}

mapping reg_name : regidx <-> string = {

  Regidx(0b00000) <-> "x0",

  Regidx(0b00001) <-> "x1",

  Regidx(0b00010) <-> "x2",

  Regidx(0b00011) <-> "x3",

  Regidx(0b00100) <-> "x4",

  Regidx(0b00101) <-> "x5",

  Regidx(0b00110) <-> "x6",

  Regidx(0b00111) <-> "x7",

  Regidx(0b01000) <-> "x8",

  Regidx(0b01001) <-> "x9",

  Regidx(0b01010) <-> "x10",

  Regidx(0b01011) <-> "x11",

  Regidx(0b01100) <-> "x12",

  Regidx(0b01101) <-> "x13",

  Regidx(0b01110) <-> "x14",

  Regidx(0b01111) <-> "x15",

  Regidx(0b10000) <-> "x16",

  Regidx(0b10001) <-> "x17",

  Regidx(0b10010) <-> "x18",

  Regidx(0b10011) <-> "x19",

  Regidx(0b10100) <-> "x20",

  Regidx(0b10101) <-> "x21",

  Regidx(0b10110) <-> "x22",

  Regidx(0b10111) <-> "x23",

  Regidx(0b11000) <-> "x24",

  Regidx(0b11001) <-> "x25",

  Regidx(0b11010) <-> "x26",

  Regidx(0b11011) <-> "x27",

  Regidx(0b11100) <-> "x28",

  Regidx(0b11101) <-> "x29",

  Regidx(0b11110) <-> "x30",

  Regidx(0b11111) <-> "x31"

}

scattered union instruction

val assembly : instruction <-> string

scattered mapping assembly

union clause instruction = F_UN_RM_FF_TYPE_D : (fregidx, rounding_mode, fregidx, f_un_rm_ff_op_D)

union clause instruction = F_UN_RM_XF_TYPE_D : (regidx, rounding_mode, fregidx, f_un_rm_xf_op_D)

mapping f_un_rm_ff_type_mnemonic_D : f_un_rm_ff_op_D <-> string = {
    FSQRT_D   <-> "fsqrt.d",
    FCVT_S_D  <-> "fcvt.s.d",
    FCVT_D_S  <-> "fcvt.d.s"
}

mapping f_un_rm_xf_type_mnemonic_D : f_un_rm_xf_op_D <-> string = {
    FCVT_D_W  <-> "fcvt.d.w",
    FCVT_D_WU <-> "fcvt.d.wu",
    FCVT_D_L  <-> "fcvt.d.l",
    FCVT_D_LU <-> "fcvt.d.lu",
}

mapping clause assembly = F_UN_RM_FF_TYPE_D(rs1, RM_RNE, rd, FCVT_D_S)
                      <-> "fcvt.d.s" ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ freg_or_reg_name(rs1)

mapping clause assembly = F_UN_RM_FF_TYPE_D(rs1, rm, rd, op)
                      <-> f_un_rm_ff_type_mnemonic_D(op)
                          ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ freg_or_reg_name(rs1)
                          ^ sep() ^ frm_mnemonic(rm)

mapping clause assembly = F_UN_RM_XF_TYPE_D(rs1, RM_RNE, rd, FCVT_D_W)
                      <-> "fcvt.d.w" ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ reg_name(rs1)

mapping clause assembly = F_UN_RM_XF_TYPE_D(rs1, RM_RNE, rd, FCVT_D_WU)
                      <-> "fcvt.d.wu" ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ reg_name(rs1)

mapping clause assembly = F_UN_RM_XF_TYPE_D(rs1, rm, rd, op)
                      <-> f_un_rm_xf_type_mnemonic_D(op)
                          ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ reg_name(rs1)
                          ^ sep() ^ frm_mnemonic(rm)

union clause instruction = F_UN_RM_FF_TYPE_H : (fregidx, rounding_mode, fregidx, f_un_rm_ff_op_H)

mapping f_un_rm_ff_type_mnemonic_H : f_un_rm_ff_op_H <-> string = {
    FSQRT_H   <-> "fsqrt.h",
    FCVT_H_S  <-> "fcvt.h.s",
    FCVT_H_D  <-> "fcvt.h.d",
    FCVT_S_H  <-> "fcvt.s.h",
    FCVT_D_H  <-> "fcvt.d.h",
}

mapping clause assembly = F_UN_RM_FF_TYPE_H(rs1, RM_RNE, rd, FCVT_S_H)
                      <-> "fcvt.s.h" ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ freg_or_reg_name(rs1)

mapping clause assembly = F_UN_RM_FF_TYPE_H(rs1, RM_RNE, rd, FCVT_D_H)
                      <-> "fcvt.d.h" ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ freg_or_reg_name(rs1)

mapping clause assembly = F_UN_RM_FF_TYPE_H(rs1, rm, rd, op)
                      <-> f_un_rm_ff_type_mnemonic_H(op)
                          ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ freg_or_reg_name(rs1)
                          ^ sep() ^ frm_mnemonic(rm)

union clause instruction = F_UN_RM_XF_TYPE_S : (regidx, rounding_mode, fregidx, f_un_rm_xf_op_S)

mapping f_un_rm_xf_type_mnemonic_S : f_un_rm_xf_op_S <-> string = {
    FCVT_S_W  <-> "fcvt.s.w",
    FCVT_S_WU <-> "fcvt.s.wu",
    FCVT_S_L  <-> "fcvt.s.l",
    FCVT_S_LU <-> "fcvt.s.lu"
}

mapping clause assembly = F_UN_RM_XF_TYPE_S(rs1, rm, rd, op)
                      <-> f_un_rm_xf_type_mnemonic_S(op)
                          ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ reg_name(rs1)
                          ^ sep() ^ frm_mnemonic(rm)

end instruction

end assembly


