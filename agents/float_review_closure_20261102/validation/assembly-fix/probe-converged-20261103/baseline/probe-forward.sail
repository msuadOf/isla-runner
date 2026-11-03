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

mapping clause assembly = F_UN_RM_FF_TYPE_D(rs1, rm, rd, op)
                      <-> f_un_rm_ff_type_mnemonic_D(op)
                          ^ spc() ^ freg_or_reg_name(rd)
                          ^ sep() ^ freg_or_reg_name(rs1)
                          ^ sep() ^ frm_mnemonic(rm)

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


function check_case(ins : instruction, expected : string, old_rne : bool) -> unit = {
  let actual : string = assembly(ins);
  assert(actual == expected, "forward assembly changed");


  print_endline("CASE\t" ^ actual)
}
val main : unit -> unit
function main() = {

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_D_S), "fcvt.d.s f3, f0", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00001), RM_RNE, Fregidx(0b01010), FCVT_D_S), "fcvt.d.s f10, f1", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00010), RM_RNE, Fregidx(0b10001), FCVT_D_S), "fcvt.d.s f17, f2", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_D_S), "fcvt.d.s f24, f3", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00100), RM_RNE, Fregidx(0b11111), FCVT_D_S), "fcvt.d.s f31, f4", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00101), RM_RNE, Fregidx(0b00110), FCVT_D_S), "fcvt.d.s f6, f5", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00110), RM_RNE, Fregidx(0b01101), FCVT_D_S), "fcvt.d.s f13, f6", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00111), RM_RNE, Fregidx(0b10100), FCVT_D_S), "fcvt.d.s f20, f7", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01000), RM_RNE, Fregidx(0b11011), FCVT_D_S), "fcvt.d.s f27, f8", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01001), RM_RNE, Fregidx(0b00010), FCVT_D_S), "fcvt.d.s f2, f9", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01010), RM_RNE, Fregidx(0b01001), FCVT_D_S), "fcvt.d.s f9, f10", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01011), RM_RNE, Fregidx(0b10000), FCVT_D_S), "fcvt.d.s f16, f11", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01100), RM_RNE, Fregidx(0b10111), FCVT_D_S), "fcvt.d.s f23, f12", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01101), RM_RNE, Fregidx(0b11110), FCVT_D_S), "fcvt.d.s f30, f13", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01110), RM_RNE, Fregidx(0b00101), FCVT_D_S), "fcvt.d.s f5, f14", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01111), RM_RNE, Fregidx(0b01100), FCVT_D_S), "fcvt.d.s f12, f15", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10000), RM_RNE, Fregidx(0b10011), FCVT_D_S), "fcvt.d.s f19, f16", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10001), RM_RNE, Fregidx(0b11010), FCVT_D_S), "fcvt.d.s f26, f17", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10010), RM_RNE, Fregidx(0b00001), FCVT_D_S), "fcvt.d.s f1, f18", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10011), RM_RNE, Fregidx(0b01000), FCVT_D_S), "fcvt.d.s f8, f19", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10100), RM_RNE, Fregidx(0b01111), FCVT_D_S), "fcvt.d.s f15, f20", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10101), RM_RNE, Fregidx(0b10110), FCVT_D_S), "fcvt.d.s f22, f21", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10110), RM_RNE, Fregidx(0b11101), FCVT_D_S), "fcvt.d.s f29, f22", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10111), RM_RNE, Fregidx(0b00100), FCVT_D_S), "fcvt.d.s f4, f23", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11000), RM_RNE, Fregidx(0b01011), FCVT_D_S), "fcvt.d.s f11, f24", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11001), RM_RNE, Fregidx(0b10010), FCVT_D_S), "fcvt.d.s f18, f25", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11010), RM_RNE, Fregidx(0b11001), FCVT_D_S), "fcvt.d.s f25, f26", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11011), RM_RNE, Fregidx(0b00000), FCVT_D_S), "fcvt.d.s f0, f27", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11100), RM_RNE, Fregidx(0b00111), FCVT_D_S), "fcvt.d.s f7, f28", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11101), RM_RNE, Fregidx(0b01110), FCVT_D_S), "fcvt.d.s f14, f29", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11110), RM_RNE, Fregidx(0b10101), FCVT_D_S), "fcvt.d.s f21, f30", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_D_S), "fcvt.d.s f28, f31", true);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_D_S), "fcvt.d.s f3, f0, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00001), RM_RTZ, Fregidx(0b01010), FCVT_D_S), "fcvt.d.s f10, f1, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00010), RM_RTZ, Fregidx(0b10001), FCVT_D_S), "fcvt.d.s f17, f2, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_D_S), "fcvt.d.s f24, f3, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00100), RM_RTZ, Fregidx(0b11111), FCVT_D_S), "fcvt.d.s f31, f4, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00101), RM_RTZ, Fregidx(0b00110), FCVT_D_S), "fcvt.d.s f6, f5, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00110), RM_RTZ, Fregidx(0b01101), FCVT_D_S), "fcvt.d.s f13, f6, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00111), RM_RTZ, Fregidx(0b10100), FCVT_D_S), "fcvt.d.s f20, f7, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01000), RM_RTZ, Fregidx(0b11011), FCVT_D_S), "fcvt.d.s f27, f8, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01001), RM_RTZ, Fregidx(0b00010), FCVT_D_S), "fcvt.d.s f2, f9, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01010), RM_RTZ, Fregidx(0b01001), FCVT_D_S), "fcvt.d.s f9, f10, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01011), RM_RTZ, Fregidx(0b10000), FCVT_D_S), "fcvt.d.s f16, f11, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01100), RM_RTZ, Fregidx(0b10111), FCVT_D_S), "fcvt.d.s f23, f12, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01101), RM_RTZ, Fregidx(0b11110), FCVT_D_S), "fcvt.d.s f30, f13, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01110), RM_RTZ, Fregidx(0b00101), FCVT_D_S), "fcvt.d.s f5, f14, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01111), RM_RTZ, Fregidx(0b01100), FCVT_D_S), "fcvt.d.s f12, f15, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10000), RM_RTZ, Fregidx(0b10011), FCVT_D_S), "fcvt.d.s f19, f16, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10001), RM_RTZ, Fregidx(0b11010), FCVT_D_S), "fcvt.d.s f26, f17, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10010), RM_RTZ, Fregidx(0b00001), FCVT_D_S), "fcvt.d.s f1, f18, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10011), RM_RTZ, Fregidx(0b01000), FCVT_D_S), "fcvt.d.s f8, f19, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10100), RM_RTZ, Fregidx(0b01111), FCVT_D_S), "fcvt.d.s f15, f20, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10101), RM_RTZ, Fregidx(0b10110), FCVT_D_S), "fcvt.d.s f22, f21, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10110), RM_RTZ, Fregidx(0b11101), FCVT_D_S), "fcvt.d.s f29, f22, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10111), RM_RTZ, Fregidx(0b00100), FCVT_D_S), "fcvt.d.s f4, f23, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11000), RM_RTZ, Fregidx(0b01011), FCVT_D_S), "fcvt.d.s f11, f24, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11001), RM_RTZ, Fregidx(0b10010), FCVT_D_S), "fcvt.d.s f18, f25, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11010), RM_RTZ, Fregidx(0b11001), FCVT_D_S), "fcvt.d.s f25, f26, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11011), RM_RTZ, Fregidx(0b00000), FCVT_D_S), "fcvt.d.s f0, f27, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11100), RM_RTZ, Fregidx(0b00111), FCVT_D_S), "fcvt.d.s f7, f28, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11101), RM_RTZ, Fregidx(0b01110), FCVT_D_S), "fcvt.d.s f14, f29, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11110), RM_RTZ, Fregidx(0b10101), FCVT_D_S), "fcvt.d.s f21, f30, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_D_S), "fcvt.d.s f28, f31, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_D_S), "fcvt.d.s f3, f0, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00001), RM_RDN, Fregidx(0b01010), FCVT_D_S), "fcvt.d.s f10, f1, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00010), RM_RDN, Fregidx(0b10001), FCVT_D_S), "fcvt.d.s f17, f2, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_D_S), "fcvt.d.s f24, f3, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00100), RM_RDN, Fregidx(0b11111), FCVT_D_S), "fcvt.d.s f31, f4, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00101), RM_RDN, Fregidx(0b00110), FCVT_D_S), "fcvt.d.s f6, f5, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00110), RM_RDN, Fregidx(0b01101), FCVT_D_S), "fcvt.d.s f13, f6, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00111), RM_RDN, Fregidx(0b10100), FCVT_D_S), "fcvt.d.s f20, f7, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01000), RM_RDN, Fregidx(0b11011), FCVT_D_S), "fcvt.d.s f27, f8, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01001), RM_RDN, Fregidx(0b00010), FCVT_D_S), "fcvt.d.s f2, f9, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01010), RM_RDN, Fregidx(0b01001), FCVT_D_S), "fcvt.d.s f9, f10, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01011), RM_RDN, Fregidx(0b10000), FCVT_D_S), "fcvt.d.s f16, f11, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01100), RM_RDN, Fregidx(0b10111), FCVT_D_S), "fcvt.d.s f23, f12, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01101), RM_RDN, Fregidx(0b11110), FCVT_D_S), "fcvt.d.s f30, f13, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01110), RM_RDN, Fregidx(0b00101), FCVT_D_S), "fcvt.d.s f5, f14, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01111), RM_RDN, Fregidx(0b01100), FCVT_D_S), "fcvt.d.s f12, f15, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10000), RM_RDN, Fregidx(0b10011), FCVT_D_S), "fcvt.d.s f19, f16, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10001), RM_RDN, Fregidx(0b11010), FCVT_D_S), "fcvt.d.s f26, f17, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10010), RM_RDN, Fregidx(0b00001), FCVT_D_S), "fcvt.d.s f1, f18, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10011), RM_RDN, Fregidx(0b01000), FCVT_D_S), "fcvt.d.s f8, f19, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10100), RM_RDN, Fregidx(0b01111), FCVT_D_S), "fcvt.d.s f15, f20, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10101), RM_RDN, Fregidx(0b10110), FCVT_D_S), "fcvt.d.s f22, f21, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10110), RM_RDN, Fregidx(0b11101), FCVT_D_S), "fcvt.d.s f29, f22, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10111), RM_RDN, Fregidx(0b00100), FCVT_D_S), "fcvt.d.s f4, f23, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11000), RM_RDN, Fregidx(0b01011), FCVT_D_S), "fcvt.d.s f11, f24, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11001), RM_RDN, Fregidx(0b10010), FCVT_D_S), "fcvt.d.s f18, f25, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11010), RM_RDN, Fregidx(0b11001), FCVT_D_S), "fcvt.d.s f25, f26, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11011), RM_RDN, Fregidx(0b00000), FCVT_D_S), "fcvt.d.s f0, f27, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11100), RM_RDN, Fregidx(0b00111), FCVT_D_S), "fcvt.d.s f7, f28, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11101), RM_RDN, Fregidx(0b01110), FCVT_D_S), "fcvt.d.s f14, f29, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11110), RM_RDN, Fregidx(0b10101), FCVT_D_S), "fcvt.d.s f21, f30, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_D_S), "fcvt.d.s f28, f31, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_D_S), "fcvt.d.s f3, f0, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00001), RM_RUP, Fregidx(0b01010), FCVT_D_S), "fcvt.d.s f10, f1, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00010), RM_RUP, Fregidx(0b10001), FCVT_D_S), "fcvt.d.s f17, f2, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_D_S), "fcvt.d.s f24, f3, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00100), RM_RUP, Fregidx(0b11111), FCVT_D_S), "fcvt.d.s f31, f4, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00101), RM_RUP, Fregidx(0b00110), FCVT_D_S), "fcvt.d.s f6, f5, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00110), RM_RUP, Fregidx(0b01101), FCVT_D_S), "fcvt.d.s f13, f6, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00111), RM_RUP, Fregidx(0b10100), FCVT_D_S), "fcvt.d.s f20, f7, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01000), RM_RUP, Fregidx(0b11011), FCVT_D_S), "fcvt.d.s f27, f8, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01001), RM_RUP, Fregidx(0b00010), FCVT_D_S), "fcvt.d.s f2, f9, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01010), RM_RUP, Fregidx(0b01001), FCVT_D_S), "fcvt.d.s f9, f10, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01011), RM_RUP, Fregidx(0b10000), FCVT_D_S), "fcvt.d.s f16, f11, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01100), RM_RUP, Fregidx(0b10111), FCVT_D_S), "fcvt.d.s f23, f12, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01101), RM_RUP, Fregidx(0b11110), FCVT_D_S), "fcvt.d.s f30, f13, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01110), RM_RUP, Fregidx(0b00101), FCVT_D_S), "fcvt.d.s f5, f14, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01111), RM_RUP, Fregidx(0b01100), FCVT_D_S), "fcvt.d.s f12, f15, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10000), RM_RUP, Fregidx(0b10011), FCVT_D_S), "fcvt.d.s f19, f16, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10001), RM_RUP, Fregidx(0b11010), FCVT_D_S), "fcvt.d.s f26, f17, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10010), RM_RUP, Fregidx(0b00001), FCVT_D_S), "fcvt.d.s f1, f18, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10011), RM_RUP, Fregidx(0b01000), FCVT_D_S), "fcvt.d.s f8, f19, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10100), RM_RUP, Fregidx(0b01111), FCVT_D_S), "fcvt.d.s f15, f20, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10101), RM_RUP, Fregidx(0b10110), FCVT_D_S), "fcvt.d.s f22, f21, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10110), RM_RUP, Fregidx(0b11101), FCVT_D_S), "fcvt.d.s f29, f22, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10111), RM_RUP, Fregidx(0b00100), FCVT_D_S), "fcvt.d.s f4, f23, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11000), RM_RUP, Fregidx(0b01011), FCVT_D_S), "fcvt.d.s f11, f24, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11001), RM_RUP, Fregidx(0b10010), FCVT_D_S), "fcvt.d.s f18, f25, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11010), RM_RUP, Fregidx(0b11001), FCVT_D_S), "fcvt.d.s f25, f26, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11011), RM_RUP, Fregidx(0b00000), FCVT_D_S), "fcvt.d.s f0, f27, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11100), RM_RUP, Fregidx(0b00111), FCVT_D_S), "fcvt.d.s f7, f28, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11101), RM_RUP, Fregidx(0b01110), FCVT_D_S), "fcvt.d.s f14, f29, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11110), RM_RUP, Fregidx(0b10101), FCVT_D_S), "fcvt.d.s f21, f30, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_D_S), "fcvt.d.s f28, f31, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_D_S), "fcvt.d.s f3, f0, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00001), RM_RMM, Fregidx(0b01010), FCVT_D_S), "fcvt.d.s f10, f1, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00010), RM_RMM, Fregidx(0b10001), FCVT_D_S), "fcvt.d.s f17, f2, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_D_S), "fcvt.d.s f24, f3, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00100), RM_RMM, Fregidx(0b11111), FCVT_D_S), "fcvt.d.s f31, f4, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00101), RM_RMM, Fregidx(0b00110), FCVT_D_S), "fcvt.d.s f6, f5, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00110), RM_RMM, Fregidx(0b01101), FCVT_D_S), "fcvt.d.s f13, f6, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00111), RM_RMM, Fregidx(0b10100), FCVT_D_S), "fcvt.d.s f20, f7, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01000), RM_RMM, Fregidx(0b11011), FCVT_D_S), "fcvt.d.s f27, f8, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01001), RM_RMM, Fregidx(0b00010), FCVT_D_S), "fcvt.d.s f2, f9, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01010), RM_RMM, Fregidx(0b01001), FCVT_D_S), "fcvt.d.s f9, f10, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01011), RM_RMM, Fregidx(0b10000), FCVT_D_S), "fcvt.d.s f16, f11, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01100), RM_RMM, Fregidx(0b10111), FCVT_D_S), "fcvt.d.s f23, f12, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01101), RM_RMM, Fregidx(0b11110), FCVT_D_S), "fcvt.d.s f30, f13, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01110), RM_RMM, Fregidx(0b00101), FCVT_D_S), "fcvt.d.s f5, f14, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01111), RM_RMM, Fregidx(0b01100), FCVT_D_S), "fcvt.d.s f12, f15, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10000), RM_RMM, Fregidx(0b10011), FCVT_D_S), "fcvt.d.s f19, f16, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10001), RM_RMM, Fregidx(0b11010), FCVT_D_S), "fcvt.d.s f26, f17, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10010), RM_RMM, Fregidx(0b00001), FCVT_D_S), "fcvt.d.s f1, f18, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10011), RM_RMM, Fregidx(0b01000), FCVT_D_S), "fcvt.d.s f8, f19, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10100), RM_RMM, Fregidx(0b01111), FCVT_D_S), "fcvt.d.s f15, f20, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10101), RM_RMM, Fregidx(0b10110), FCVT_D_S), "fcvt.d.s f22, f21, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10110), RM_RMM, Fregidx(0b11101), FCVT_D_S), "fcvt.d.s f29, f22, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10111), RM_RMM, Fregidx(0b00100), FCVT_D_S), "fcvt.d.s f4, f23, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11000), RM_RMM, Fregidx(0b01011), FCVT_D_S), "fcvt.d.s f11, f24, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11001), RM_RMM, Fregidx(0b10010), FCVT_D_S), "fcvt.d.s f18, f25, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11010), RM_RMM, Fregidx(0b11001), FCVT_D_S), "fcvt.d.s f25, f26, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11011), RM_RMM, Fregidx(0b00000), FCVT_D_S), "fcvt.d.s f0, f27, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11100), RM_RMM, Fregidx(0b00111), FCVT_D_S), "fcvt.d.s f7, f28, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11101), RM_RMM, Fregidx(0b01110), FCVT_D_S), "fcvt.d.s f14, f29, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11110), RM_RMM, Fregidx(0b10101), FCVT_D_S), "fcvt.d.s f21, f30, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_D_S), "fcvt.d.s f28, f31, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_D_S), "fcvt.d.s f3, f0, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00001), RM_DYN, Fregidx(0b01010), FCVT_D_S), "fcvt.d.s f10, f1, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00010), RM_DYN, Fregidx(0b10001), FCVT_D_S), "fcvt.d.s f17, f2, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_D_S), "fcvt.d.s f24, f3, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00100), RM_DYN, Fregidx(0b11111), FCVT_D_S), "fcvt.d.s f31, f4, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00101), RM_DYN, Fregidx(0b00110), FCVT_D_S), "fcvt.d.s f6, f5, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00110), RM_DYN, Fregidx(0b01101), FCVT_D_S), "fcvt.d.s f13, f6, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00111), RM_DYN, Fregidx(0b10100), FCVT_D_S), "fcvt.d.s f20, f7, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01000), RM_DYN, Fregidx(0b11011), FCVT_D_S), "fcvt.d.s f27, f8, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01001), RM_DYN, Fregidx(0b00010), FCVT_D_S), "fcvt.d.s f2, f9, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01010), RM_DYN, Fregidx(0b01001), FCVT_D_S), "fcvt.d.s f9, f10, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01011), RM_DYN, Fregidx(0b10000), FCVT_D_S), "fcvt.d.s f16, f11, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01100), RM_DYN, Fregidx(0b10111), FCVT_D_S), "fcvt.d.s f23, f12, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01101), RM_DYN, Fregidx(0b11110), FCVT_D_S), "fcvt.d.s f30, f13, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01110), RM_DYN, Fregidx(0b00101), FCVT_D_S), "fcvt.d.s f5, f14, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b01111), RM_DYN, Fregidx(0b01100), FCVT_D_S), "fcvt.d.s f12, f15, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10000), RM_DYN, Fregidx(0b10011), FCVT_D_S), "fcvt.d.s f19, f16, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10001), RM_DYN, Fregidx(0b11010), FCVT_D_S), "fcvt.d.s f26, f17, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10010), RM_DYN, Fregidx(0b00001), FCVT_D_S), "fcvt.d.s f1, f18, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10011), RM_DYN, Fregidx(0b01000), FCVT_D_S), "fcvt.d.s f8, f19, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10100), RM_DYN, Fregidx(0b01111), FCVT_D_S), "fcvt.d.s f15, f20, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10101), RM_DYN, Fregidx(0b10110), FCVT_D_S), "fcvt.d.s f22, f21, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10110), RM_DYN, Fregidx(0b11101), FCVT_D_S), "fcvt.d.s f29, f22, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b10111), RM_DYN, Fregidx(0b00100), FCVT_D_S), "fcvt.d.s f4, f23, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11000), RM_DYN, Fregidx(0b01011), FCVT_D_S), "fcvt.d.s f11, f24, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11001), RM_DYN, Fregidx(0b10010), FCVT_D_S), "fcvt.d.s f18, f25, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11010), RM_DYN, Fregidx(0b11001), FCVT_D_S), "fcvt.d.s f25, f26, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11011), RM_DYN, Fregidx(0b00000), FCVT_D_S), "fcvt.d.s f0, f27, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11100), RM_DYN, Fregidx(0b00111), FCVT_D_S), "fcvt.d.s f7, f28, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11101), RM_DYN, Fregidx(0b01110), FCVT_D_S), "fcvt.d.s f14, f29, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11110), RM_DYN, Fregidx(0b10101), FCVT_D_S), "fcvt.d.s f21, f30, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_D_S), "fcvt.d.s f28, f31, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_D_H), "fcvt.d.h f3, f0", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RNE, Fregidx(0b01010), FCVT_D_H), "fcvt.d.h f10, f1", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RNE, Fregidx(0b10001), FCVT_D_H), "fcvt.d.h f17, f2", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_D_H), "fcvt.d.h f24, f3", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RNE, Fregidx(0b11111), FCVT_D_H), "fcvt.d.h f31, f4", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RNE, Fregidx(0b00110), FCVT_D_H), "fcvt.d.h f6, f5", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RNE, Fregidx(0b01101), FCVT_D_H), "fcvt.d.h f13, f6", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RNE, Fregidx(0b10100), FCVT_D_H), "fcvt.d.h f20, f7", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RNE, Fregidx(0b11011), FCVT_D_H), "fcvt.d.h f27, f8", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RNE, Fregidx(0b00010), FCVT_D_H), "fcvt.d.h f2, f9", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RNE, Fregidx(0b01001), FCVT_D_H), "fcvt.d.h f9, f10", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RNE, Fregidx(0b10000), FCVT_D_H), "fcvt.d.h f16, f11", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RNE, Fregidx(0b10111), FCVT_D_H), "fcvt.d.h f23, f12", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RNE, Fregidx(0b11110), FCVT_D_H), "fcvt.d.h f30, f13", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RNE, Fregidx(0b00101), FCVT_D_H), "fcvt.d.h f5, f14", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RNE, Fregidx(0b01100), FCVT_D_H), "fcvt.d.h f12, f15", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RNE, Fregidx(0b10011), FCVT_D_H), "fcvt.d.h f19, f16", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RNE, Fregidx(0b11010), FCVT_D_H), "fcvt.d.h f26, f17", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RNE, Fregidx(0b00001), FCVT_D_H), "fcvt.d.h f1, f18", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RNE, Fregidx(0b01000), FCVT_D_H), "fcvt.d.h f8, f19", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RNE, Fregidx(0b01111), FCVT_D_H), "fcvt.d.h f15, f20", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RNE, Fregidx(0b10110), FCVT_D_H), "fcvt.d.h f22, f21", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RNE, Fregidx(0b11101), FCVT_D_H), "fcvt.d.h f29, f22", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RNE, Fregidx(0b00100), FCVT_D_H), "fcvt.d.h f4, f23", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RNE, Fregidx(0b01011), FCVT_D_H), "fcvt.d.h f11, f24", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RNE, Fregidx(0b10010), FCVT_D_H), "fcvt.d.h f18, f25", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RNE, Fregidx(0b11001), FCVT_D_H), "fcvt.d.h f25, f26", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RNE, Fregidx(0b00000), FCVT_D_H), "fcvt.d.h f0, f27", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RNE, Fregidx(0b00111), FCVT_D_H), "fcvt.d.h f7, f28", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RNE, Fregidx(0b01110), FCVT_D_H), "fcvt.d.h f14, f29", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RNE, Fregidx(0b10101), FCVT_D_H), "fcvt.d.h f21, f30", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_D_H), "fcvt.d.h f28, f31", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_D_H), "fcvt.d.h f3, f0, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RTZ, Fregidx(0b01010), FCVT_D_H), "fcvt.d.h f10, f1, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RTZ, Fregidx(0b10001), FCVT_D_H), "fcvt.d.h f17, f2, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_D_H), "fcvt.d.h f24, f3, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RTZ, Fregidx(0b11111), FCVT_D_H), "fcvt.d.h f31, f4, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RTZ, Fregidx(0b00110), FCVT_D_H), "fcvt.d.h f6, f5, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RTZ, Fregidx(0b01101), FCVT_D_H), "fcvt.d.h f13, f6, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RTZ, Fregidx(0b10100), FCVT_D_H), "fcvt.d.h f20, f7, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RTZ, Fregidx(0b11011), FCVT_D_H), "fcvt.d.h f27, f8, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RTZ, Fregidx(0b00010), FCVT_D_H), "fcvt.d.h f2, f9, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RTZ, Fregidx(0b01001), FCVT_D_H), "fcvt.d.h f9, f10, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RTZ, Fregidx(0b10000), FCVT_D_H), "fcvt.d.h f16, f11, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RTZ, Fregidx(0b10111), FCVT_D_H), "fcvt.d.h f23, f12, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RTZ, Fregidx(0b11110), FCVT_D_H), "fcvt.d.h f30, f13, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RTZ, Fregidx(0b00101), FCVT_D_H), "fcvt.d.h f5, f14, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RTZ, Fregidx(0b01100), FCVT_D_H), "fcvt.d.h f12, f15, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RTZ, Fregidx(0b10011), FCVT_D_H), "fcvt.d.h f19, f16, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RTZ, Fregidx(0b11010), FCVT_D_H), "fcvt.d.h f26, f17, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RTZ, Fregidx(0b00001), FCVT_D_H), "fcvt.d.h f1, f18, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RTZ, Fregidx(0b01000), FCVT_D_H), "fcvt.d.h f8, f19, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RTZ, Fregidx(0b01111), FCVT_D_H), "fcvt.d.h f15, f20, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RTZ, Fregidx(0b10110), FCVT_D_H), "fcvt.d.h f22, f21, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RTZ, Fregidx(0b11101), FCVT_D_H), "fcvt.d.h f29, f22, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RTZ, Fregidx(0b00100), FCVT_D_H), "fcvt.d.h f4, f23, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RTZ, Fregidx(0b01011), FCVT_D_H), "fcvt.d.h f11, f24, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RTZ, Fregidx(0b10010), FCVT_D_H), "fcvt.d.h f18, f25, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RTZ, Fregidx(0b11001), FCVT_D_H), "fcvt.d.h f25, f26, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RTZ, Fregidx(0b00000), FCVT_D_H), "fcvt.d.h f0, f27, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RTZ, Fregidx(0b00111), FCVT_D_H), "fcvt.d.h f7, f28, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RTZ, Fregidx(0b01110), FCVT_D_H), "fcvt.d.h f14, f29, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RTZ, Fregidx(0b10101), FCVT_D_H), "fcvt.d.h f21, f30, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_D_H), "fcvt.d.h f28, f31, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_D_H), "fcvt.d.h f3, f0, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RDN, Fregidx(0b01010), FCVT_D_H), "fcvt.d.h f10, f1, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RDN, Fregidx(0b10001), FCVT_D_H), "fcvt.d.h f17, f2, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_D_H), "fcvt.d.h f24, f3, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RDN, Fregidx(0b11111), FCVT_D_H), "fcvt.d.h f31, f4, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RDN, Fregidx(0b00110), FCVT_D_H), "fcvt.d.h f6, f5, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RDN, Fregidx(0b01101), FCVT_D_H), "fcvt.d.h f13, f6, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RDN, Fregidx(0b10100), FCVT_D_H), "fcvt.d.h f20, f7, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RDN, Fregidx(0b11011), FCVT_D_H), "fcvt.d.h f27, f8, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RDN, Fregidx(0b00010), FCVT_D_H), "fcvt.d.h f2, f9, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RDN, Fregidx(0b01001), FCVT_D_H), "fcvt.d.h f9, f10, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RDN, Fregidx(0b10000), FCVT_D_H), "fcvt.d.h f16, f11, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RDN, Fregidx(0b10111), FCVT_D_H), "fcvt.d.h f23, f12, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RDN, Fregidx(0b11110), FCVT_D_H), "fcvt.d.h f30, f13, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RDN, Fregidx(0b00101), FCVT_D_H), "fcvt.d.h f5, f14, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RDN, Fregidx(0b01100), FCVT_D_H), "fcvt.d.h f12, f15, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RDN, Fregidx(0b10011), FCVT_D_H), "fcvt.d.h f19, f16, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RDN, Fregidx(0b11010), FCVT_D_H), "fcvt.d.h f26, f17, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RDN, Fregidx(0b00001), FCVT_D_H), "fcvt.d.h f1, f18, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RDN, Fregidx(0b01000), FCVT_D_H), "fcvt.d.h f8, f19, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RDN, Fregidx(0b01111), FCVT_D_H), "fcvt.d.h f15, f20, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RDN, Fregidx(0b10110), FCVT_D_H), "fcvt.d.h f22, f21, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RDN, Fregidx(0b11101), FCVT_D_H), "fcvt.d.h f29, f22, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RDN, Fregidx(0b00100), FCVT_D_H), "fcvt.d.h f4, f23, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RDN, Fregidx(0b01011), FCVT_D_H), "fcvt.d.h f11, f24, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RDN, Fregidx(0b10010), FCVT_D_H), "fcvt.d.h f18, f25, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RDN, Fregidx(0b11001), FCVT_D_H), "fcvt.d.h f25, f26, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RDN, Fregidx(0b00000), FCVT_D_H), "fcvt.d.h f0, f27, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RDN, Fregidx(0b00111), FCVT_D_H), "fcvt.d.h f7, f28, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RDN, Fregidx(0b01110), FCVT_D_H), "fcvt.d.h f14, f29, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RDN, Fregidx(0b10101), FCVT_D_H), "fcvt.d.h f21, f30, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_D_H), "fcvt.d.h f28, f31, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_D_H), "fcvt.d.h f3, f0, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RUP, Fregidx(0b01010), FCVT_D_H), "fcvt.d.h f10, f1, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RUP, Fregidx(0b10001), FCVT_D_H), "fcvt.d.h f17, f2, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_D_H), "fcvt.d.h f24, f3, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RUP, Fregidx(0b11111), FCVT_D_H), "fcvt.d.h f31, f4, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RUP, Fregidx(0b00110), FCVT_D_H), "fcvt.d.h f6, f5, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RUP, Fregidx(0b01101), FCVT_D_H), "fcvt.d.h f13, f6, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RUP, Fregidx(0b10100), FCVT_D_H), "fcvt.d.h f20, f7, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RUP, Fregidx(0b11011), FCVT_D_H), "fcvt.d.h f27, f8, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RUP, Fregidx(0b00010), FCVT_D_H), "fcvt.d.h f2, f9, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RUP, Fregidx(0b01001), FCVT_D_H), "fcvt.d.h f9, f10, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RUP, Fregidx(0b10000), FCVT_D_H), "fcvt.d.h f16, f11, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RUP, Fregidx(0b10111), FCVT_D_H), "fcvt.d.h f23, f12, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RUP, Fregidx(0b11110), FCVT_D_H), "fcvt.d.h f30, f13, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RUP, Fregidx(0b00101), FCVT_D_H), "fcvt.d.h f5, f14, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RUP, Fregidx(0b01100), FCVT_D_H), "fcvt.d.h f12, f15, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RUP, Fregidx(0b10011), FCVT_D_H), "fcvt.d.h f19, f16, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RUP, Fregidx(0b11010), FCVT_D_H), "fcvt.d.h f26, f17, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RUP, Fregidx(0b00001), FCVT_D_H), "fcvt.d.h f1, f18, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RUP, Fregidx(0b01000), FCVT_D_H), "fcvt.d.h f8, f19, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RUP, Fregidx(0b01111), FCVT_D_H), "fcvt.d.h f15, f20, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RUP, Fregidx(0b10110), FCVT_D_H), "fcvt.d.h f22, f21, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RUP, Fregidx(0b11101), FCVT_D_H), "fcvt.d.h f29, f22, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RUP, Fregidx(0b00100), FCVT_D_H), "fcvt.d.h f4, f23, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RUP, Fregidx(0b01011), FCVT_D_H), "fcvt.d.h f11, f24, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RUP, Fregidx(0b10010), FCVT_D_H), "fcvt.d.h f18, f25, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RUP, Fregidx(0b11001), FCVT_D_H), "fcvt.d.h f25, f26, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RUP, Fregidx(0b00000), FCVT_D_H), "fcvt.d.h f0, f27, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RUP, Fregidx(0b00111), FCVT_D_H), "fcvt.d.h f7, f28, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RUP, Fregidx(0b01110), FCVT_D_H), "fcvt.d.h f14, f29, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RUP, Fregidx(0b10101), FCVT_D_H), "fcvt.d.h f21, f30, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_D_H), "fcvt.d.h f28, f31, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_D_H), "fcvt.d.h f3, f0, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RMM, Fregidx(0b01010), FCVT_D_H), "fcvt.d.h f10, f1, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RMM, Fregidx(0b10001), FCVT_D_H), "fcvt.d.h f17, f2, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_D_H), "fcvt.d.h f24, f3, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RMM, Fregidx(0b11111), FCVT_D_H), "fcvt.d.h f31, f4, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RMM, Fregidx(0b00110), FCVT_D_H), "fcvt.d.h f6, f5, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RMM, Fregidx(0b01101), FCVT_D_H), "fcvt.d.h f13, f6, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RMM, Fregidx(0b10100), FCVT_D_H), "fcvt.d.h f20, f7, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RMM, Fregidx(0b11011), FCVT_D_H), "fcvt.d.h f27, f8, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RMM, Fregidx(0b00010), FCVT_D_H), "fcvt.d.h f2, f9, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RMM, Fregidx(0b01001), FCVT_D_H), "fcvt.d.h f9, f10, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RMM, Fregidx(0b10000), FCVT_D_H), "fcvt.d.h f16, f11, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RMM, Fregidx(0b10111), FCVT_D_H), "fcvt.d.h f23, f12, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RMM, Fregidx(0b11110), FCVT_D_H), "fcvt.d.h f30, f13, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RMM, Fregidx(0b00101), FCVT_D_H), "fcvt.d.h f5, f14, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RMM, Fregidx(0b01100), FCVT_D_H), "fcvt.d.h f12, f15, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RMM, Fregidx(0b10011), FCVT_D_H), "fcvt.d.h f19, f16, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RMM, Fregidx(0b11010), FCVT_D_H), "fcvt.d.h f26, f17, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RMM, Fregidx(0b00001), FCVT_D_H), "fcvt.d.h f1, f18, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RMM, Fregidx(0b01000), FCVT_D_H), "fcvt.d.h f8, f19, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RMM, Fregidx(0b01111), FCVT_D_H), "fcvt.d.h f15, f20, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RMM, Fregidx(0b10110), FCVT_D_H), "fcvt.d.h f22, f21, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RMM, Fregidx(0b11101), FCVT_D_H), "fcvt.d.h f29, f22, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RMM, Fregidx(0b00100), FCVT_D_H), "fcvt.d.h f4, f23, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RMM, Fregidx(0b01011), FCVT_D_H), "fcvt.d.h f11, f24, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RMM, Fregidx(0b10010), FCVT_D_H), "fcvt.d.h f18, f25, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RMM, Fregidx(0b11001), FCVT_D_H), "fcvt.d.h f25, f26, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RMM, Fregidx(0b00000), FCVT_D_H), "fcvt.d.h f0, f27, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RMM, Fregidx(0b00111), FCVT_D_H), "fcvt.d.h f7, f28, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RMM, Fregidx(0b01110), FCVT_D_H), "fcvt.d.h f14, f29, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RMM, Fregidx(0b10101), FCVT_D_H), "fcvt.d.h f21, f30, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_D_H), "fcvt.d.h f28, f31, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_D_H), "fcvt.d.h f3, f0, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_DYN, Fregidx(0b01010), FCVT_D_H), "fcvt.d.h f10, f1, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_DYN, Fregidx(0b10001), FCVT_D_H), "fcvt.d.h f17, f2, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_D_H), "fcvt.d.h f24, f3, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_DYN, Fregidx(0b11111), FCVT_D_H), "fcvt.d.h f31, f4, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_DYN, Fregidx(0b00110), FCVT_D_H), "fcvt.d.h f6, f5, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_DYN, Fregidx(0b01101), FCVT_D_H), "fcvt.d.h f13, f6, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_DYN, Fregidx(0b10100), FCVT_D_H), "fcvt.d.h f20, f7, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_DYN, Fregidx(0b11011), FCVT_D_H), "fcvt.d.h f27, f8, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_DYN, Fregidx(0b00010), FCVT_D_H), "fcvt.d.h f2, f9, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_DYN, Fregidx(0b01001), FCVT_D_H), "fcvt.d.h f9, f10, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_DYN, Fregidx(0b10000), FCVT_D_H), "fcvt.d.h f16, f11, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_DYN, Fregidx(0b10111), FCVT_D_H), "fcvt.d.h f23, f12, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_DYN, Fregidx(0b11110), FCVT_D_H), "fcvt.d.h f30, f13, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_DYN, Fregidx(0b00101), FCVT_D_H), "fcvt.d.h f5, f14, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_DYN, Fregidx(0b01100), FCVT_D_H), "fcvt.d.h f12, f15, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_DYN, Fregidx(0b10011), FCVT_D_H), "fcvt.d.h f19, f16, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_DYN, Fregidx(0b11010), FCVT_D_H), "fcvt.d.h f26, f17, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_DYN, Fregidx(0b00001), FCVT_D_H), "fcvt.d.h f1, f18, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_DYN, Fregidx(0b01000), FCVT_D_H), "fcvt.d.h f8, f19, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_DYN, Fregidx(0b01111), FCVT_D_H), "fcvt.d.h f15, f20, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_DYN, Fregidx(0b10110), FCVT_D_H), "fcvt.d.h f22, f21, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_DYN, Fregidx(0b11101), FCVT_D_H), "fcvt.d.h f29, f22, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_DYN, Fregidx(0b00100), FCVT_D_H), "fcvt.d.h f4, f23, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_DYN, Fregidx(0b01011), FCVT_D_H), "fcvt.d.h f11, f24, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_DYN, Fregidx(0b10010), FCVT_D_H), "fcvt.d.h f18, f25, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_DYN, Fregidx(0b11001), FCVT_D_H), "fcvt.d.h f25, f26, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_DYN, Fregidx(0b00000), FCVT_D_H), "fcvt.d.h f0, f27, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_DYN, Fregidx(0b00111), FCVT_D_H), "fcvt.d.h f7, f28, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_DYN, Fregidx(0b01110), FCVT_D_H), "fcvt.d.h f14, f29, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_DYN, Fregidx(0b10101), FCVT_D_H), "fcvt.d.h f21, f30, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_D_H), "fcvt.d.h f28, f31, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_S_H), "fcvt.s.h f3, f0", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RNE, Fregidx(0b01010), FCVT_S_H), "fcvt.s.h f10, f1", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RNE, Fregidx(0b10001), FCVT_S_H), "fcvt.s.h f17, f2", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_S_H), "fcvt.s.h f24, f3", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RNE, Fregidx(0b11111), FCVT_S_H), "fcvt.s.h f31, f4", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RNE, Fregidx(0b00110), FCVT_S_H), "fcvt.s.h f6, f5", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RNE, Fregidx(0b01101), FCVT_S_H), "fcvt.s.h f13, f6", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RNE, Fregidx(0b10100), FCVT_S_H), "fcvt.s.h f20, f7", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RNE, Fregidx(0b11011), FCVT_S_H), "fcvt.s.h f27, f8", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RNE, Fregidx(0b00010), FCVT_S_H), "fcvt.s.h f2, f9", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RNE, Fregidx(0b01001), FCVT_S_H), "fcvt.s.h f9, f10", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RNE, Fregidx(0b10000), FCVT_S_H), "fcvt.s.h f16, f11", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RNE, Fregidx(0b10111), FCVT_S_H), "fcvt.s.h f23, f12", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RNE, Fregidx(0b11110), FCVT_S_H), "fcvt.s.h f30, f13", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RNE, Fregidx(0b00101), FCVT_S_H), "fcvt.s.h f5, f14", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RNE, Fregidx(0b01100), FCVT_S_H), "fcvt.s.h f12, f15", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RNE, Fregidx(0b10011), FCVT_S_H), "fcvt.s.h f19, f16", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RNE, Fregidx(0b11010), FCVT_S_H), "fcvt.s.h f26, f17", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RNE, Fregidx(0b00001), FCVT_S_H), "fcvt.s.h f1, f18", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RNE, Fregidx(0b01000), FCVT_S_H), "fcvt.s.h f8, f19", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RNE, Fregidx(0b01111), FCVT_S_H), "fcvt.s.h f15, f20", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RNE, Fregidx(0b10110), FCVT_S_H), "fcvt.s.h f22, f21", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RNE, Fregidx(0b11101), FCVT_S_H), "fcvt.s.h f29, f22", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RNE, Fregidx(0b00100), FCVT_S_H), "fcvt.s.h f4, f23", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RNE, Fregidx(0b01011), FCVT_S_H), "fcvt.s.h f11, f24", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RNE, Fregidx(0b10010), FCVT_S_H), "fcvt.s.h f18, f25", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RNE, Fregidx(0b11001), FCVT_S_H), "fcvt.s.h f25, f26", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RNE, Fregidx(0b00000), FCVT_S_H), "fcvt.s.h f0, f27", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RNE, Fregidx(0b00111), FCVT_S_H), "fcvt.s.h f7, f28", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RNE, Fregidx(0b01110), FCVT_S_H), "fcvt.s.h f14, f29", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RNE, Fregidx(0b10101), FCVT_S_H), "fcvt.s.h f21, f30", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_S_H), "fcvt.s.h f28, f31", true);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_S_H), "fcvt.s.h f3, f0, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RTZ, Fregidx(0b01010), FCVT_S_H), "fcvt.s.h f10, f1, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RTZ, Fregidx(0b10001), FCVT_S_H), "fcvt.s.h f17, f2, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_S_H), "fcvt.s.h f24, f3, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RTZ, Fregidx(0b11111), FCVT_S_H), "fcvt.s.h f31, f4, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RTZ, Fregidx(0b00110), FCVT_S_H), "fcvt.s.h f6, f5, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RTZ, Fregidx(0b01101), FCVT_S_H), "fcvt.s.h f13, f6, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RTZ, Fregidx(0b10100), FCVT_S_H), "fcvt.s.h f20, f7, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RTZ, Fregidx(0b11011), FCVT_S_H), "fcvt.s.h f27, f8, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RTZ, Fregidx(0b00010), FCVT_S_H), "fcvt.s.h f2, f9, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RTZ, Fregidx(0b01001), FCVT_S_H), "fcvt.s.h f9, f10, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RTZ, Fregidx(0b10000), FCVT_S_H), "fcvt.s.h f16, f11, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RTZ, Fregidx(0b10111), FCVT_S_H), "fcvt.s.h f23, f12, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RTZ, Fregidx(0b11110), FCVT_S_H), "fcvt.s.h f30, f13, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RTZ, Fregidx(0b00101), FCVT_S_H), "fcvt.s.h f5, f14, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RTZ, Fregidx(0b01100), FCVT_S_H), "fcvt.s.h f12, f15, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RTZ, Fregidx(0b10011), FCVT_S_H), "fcvt.s.h f19, f16, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RTZ, Fregidx(0b11010), FCVT_S_H), "fcvt.s.h f26, f17, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RTZ, Fregidx(0b00001), FCVT_S_H), "fcvt.s.h f1, f18, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RTZ, Fregidx(0b01000), FCVT_S_H), "fcvt.s.h f8, f19, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RTZ, Fregidx(0b01111), FCVT_S_H), "fcvt.s.h f15, f20, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RTZ, Fregidx(0b10110), FCVT_S_H), "fcvt.s.h f22, f21, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RTZ, Fregidx(0b11101), FCVT_S_H), "fcvt.s.h f29, f22, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RTZ, Fregidx(0b00100), FCVT_S_H), "fcvt.s.h f4, f23, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RTZ, Fregidx(0b01011), FCVT_S_H), "fcvt.s.h f11, f24, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RTZ, Fregidx(0b10010), FCVT_S_H), "fcvt.s.h f18, f25, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RTZ, Fregidx(0b11001), FCVT_S_H), "fcvt.s.h f25, f26, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RTZ, Fregidx(0b00000), FCVT_S_H), "fcvt.s.h f0, f27, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RTZ, Fregidx(0b00111), FCVT_S_H), "fcvt.s.h f7, f28, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RTZ, Fregidx(0b01110), FCVT_S_H), "fcvt.s.h f14, f29, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RTZ, Fregidx(0b10101), FCVT_S_H), "fcvt.s.h f21, f30, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_S_H), "fcvt.s.h f28, f31, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_S_H), "fcvt.s.h f3, f0, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RDN, Fregidx(0b01010), FCVT_S_H), "fcvt.s.h f10, f1, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RDN, Fregidx(0b10001), FCVT_S_H), "fcvt.s.h f17, f2, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_S_H), "fcvt.s.h f24, f3, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RDN, Fregidx(0b11111), FCVT_S_H), "fcvt.s.h f31, f4, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RDN, Fregidx(0b00110), FCVT_S_H), "fcvt.s.h f6, f5, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RDN, Fregidx(0b01101), FCVT_S_H), "fcvt.s.h f13, f6, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RDN, Fregidx(0b10100), FCVT_S_H), "fcvt.s.h f20, f7, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RDN, Fregidx(0b11011), FCVT_S_H), "fcvt.s.h f27, f8, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RDN, Fregidx(0b00010), FCVT_S_H), "fcvt.s.h f2, f9, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RDN, Fregidx(0b01001), FCVT_S_H), "fcvt.s.h f9, f10, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RDN, Fregidx(0b10000), FCVT_S_H), "fcvt.s.h f16, f11, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RDN, Fregidx(0b10111), FCVT_S_H), "fcvt.s.h f23, f12, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RDN, Fregidx(0b11110), FCVT_S_H), "fcvt.s.h f30, f13, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RDN, Fregidx(0b00101), FCVT_S_H), "fcvt.s.h f5, f14, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RDN, Fregidx(0b01100), FCVT_S_H), "fcvt.s.h f12, f15, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RDN, Fregidx(0b10011), FCVT_S_H), "fcvt.s.h f19, f16, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RDN, Fregidx(0b11010), FCVT_S_H), "fcvt.s.h f26, f17, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RDN, Fregidx(0b00001), FCVT_S_H), "fcvt.s.h f1, f18, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RDN, Fregidx(0b01000), FCVT_S_H), "fcvt.s.h f8, f19, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RDN, Fregidx(0b01111), FCVT_S_H), "fcvt.s.h f15, f20, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RDN, Fregidx(0b10110), FCVT_S_H), "fcvt.s.h f22, f21, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RDN, Fregidx(0b11101), FCVT_S_H), "fcvt.s.h f29, f22, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RDN, Fregidx(0b00100), FCVT_S_H), "fcvt.s.h f4, f23, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RDN, Fregidx(0b01011), FCVT_S_H), "fcvt.s.h f11, f24, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RDN, Fregidx(0b10010), FCVT_S_H), "fcvt.s.h f18, f25, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RDN, Fregidx(0b11001), FCVT_S_H), "fcvt.s.h f25, f26, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RDN, Fregidx(0b00000), FCVT_S_H), "fcvt.s.h f0, f27, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RDN, Fregidx(0b00111), FCVT_S_H), "fcvt.s.h f7, f28, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RDN, Fregidx(0b01110), FCVT_S_H), "fcvt.s.h f14, f29, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RDN, Fregidx(0b10101), FCVT_S_H), "fcvt.s.h f21, f30, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_S_H), "fcvt.s.h f28, f31, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_S_H), "fcvt.s.h f3, f0, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RUP, Fregidx(0b01010), FCVT_S_H), "fcvt.s.h f10, f1, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RUP, Fregidx(0b10001), FCVT_S_H), "fcvt.s.h f17, f2, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_S_H), "fcvt.s.h f24, f3, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RUP, Fregidx(0b11111), FCVT_S_H), "fcvt.s.h f31, f4, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RUP, Fregidx(0b00110), FCVT_S_H), "fcvt.s.h f6, f5, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RUP, Fregidx(0b01101), FCVT_S_H), "fcvt.s.h f13, f6, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RUP, Fregidx(0b10100), FCVT_S_H), "fcvt.s.h f20, f7, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RUP, Fregidx(0b11011), FCVT_S_H), "fcvt.s.h f27, f8, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RUP, Fregidx(0b00010), FCVT_S_H), "fcvt.s.h f2, f9, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RUP, Fregidx(0b01001), FCVT_S_H), "fcvt.s.h f9, f10, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RUP, Fregidx(0b10000), FCVT_S_H), "fcvt.s.h f16, f11, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RUP, Fregidx(0b10111), FCVT_S_H), "fcvt.s.h f23, f12, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RUP, Fregidx(0b11110), FCVT_S_H), "fcvt.s.h f30, f13, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RUP, Fregidx(0b00101), FCVT_S_H), "fcvt.s.h f5, f14, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RUP, Fregidx(0b01100), FCVT_S_H), "fcvt.s.h f12, f15, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RUP, Fregidx(0b10011), FCVT_S_H), "fcvt.s.h f19, f16, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RUP, Fregidx(0b11010), FCVT_S_H), "fcvt.s.h f26, f17, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RUP, Fregidx(0b00001), FCVT_S_H), "fcvt.s.h f1, f18, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RUP, Fregidx(0b01000), FCVT_S_H), "fcvt.s.h f8, f19, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RUP, Fregidx(0b01111), FCVT_S_H), "fcvt.s.h f15, f20, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RUP, Fregidx(0b10110), FCVT_S_H), "fcvt.s.h f22, f21, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RUP, Fregidx(0b11101), FCVT_S_H), "fcvt.s.h f29, f22, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RUP, Fregidx(0b00100), FCVT_S_H), "fcvt.s.h f4, f23, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RUP, Fregidx(0b01011), FCVT_S_H), "fcvt.s.h f11, f24, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RUP, Fregidx(0b10010), FCVT_S_H), "fcvt.s.h f18, f25, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RUP, Fregidx(0b11001), FCVT_S_H), "fcvt.s.h f25, f26, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RUP, Fregidx(0b00000), FCVT_S_H), "fcvt.s.h f0, f27, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RUP, Fregidx(0b00111), FCVT_S_H), "fcvt.s.h f7, f28, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RUP, Fregidx(0b01110), FCVT_S_H), "fcvt.s.h f14, f29, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RUP, Fregidx(0b10101), FCVT_S_H), "fcvt.s.h f21, f30, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_S_H), "fcvt.s.h f28, f31, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_S_H), "fcvt.s.h f3, f0, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_RMM, Fregidx(0b01010), FCVT_S_H), "fcvt.s.h f10, f1, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_RMM, Fregidx(0b10001), FCVT_S_H), "fcvt.s.h f17, f2, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_S_H), "fcvt.s.h f24, f3, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_RMM, Fregidx(0b11111), FCVT_S_H), "fcvt.s.h f31, f4, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_RMM, Fregidx(0b00110), FCVT_S_H), "fcvt.s.h f6, f5, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_RMM, Fregidx(0b01101), FCVT_S_H), "fcvt.s.h f13, f6, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_RMM, Fregidx(0b10100), FCVT_S_H), "fcvt.s.h f20, f7, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_RMM, Fregidx(0b11011), FCVT_S_H), "fcvt.s.h f27, f8, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_RMM, Fregidx(0b00010), FCVT_S_H), "fcvt.s.h f2, f9, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_RMM, Fregidx(0b01001), FCVT_S_H), "fcvt.s.h f9, f10, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_RMM, Fregidx(0b10000), FCVT_S_H), "fcvt.s.h f16, f11, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_RMM, Fregidx(0b10111), FCVT_S_H), "fcvt.s.h f23, f12, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_RMM, Fregidx(0b11110), FCVT_S_H), "fcvt.s.h f30, f13, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_RMM, Fregidx(0b00101), FCVT_S_H), "fcvt.s.h f5, f14, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_RMM, Fregidx(0b01100), FCVT_S_H), "fcvt.s.h f12, f15, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_RMM, Fregidx(0b10011), FCVT_S_H), "fcvt.s.h f19, f16, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_RMM, Fregidx(0b11010), FCVT_S_H), "fcvt.s.h f26, f17, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_RMM, Fregidx(0b00001), FCVT_S_H), "fcvt.s.h f1, f18, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_RMM, Fregidx(0b01000), FCVT_S_H), "fcvt.s.h f8, f19, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_RMM, Fregidx(0b01111), FCVT_S_H), "fcvt.s.h f15, f20, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_RMM, Fregidx(0b10110), FCVT_S_H), "fcvt.s.h f22, f21, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_RMM, Fregidx(0b11101), FCVT_S_H), "fcvt.s.h f29, f22, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_RMM, Fregidx(0b00100), FCVT_S_H), "fcvt.s.h f4, f23, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_RMM, Fregidx(0b01011), FCVT_S_H), "fcvt.s.h f11, f24, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_RMM, Fregidx(0b10010), FCVT_S_H), "fcvt.s.h f18, f25, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_RMM, Fregidx(0b11001), FCVT_S_H), "fcvt.s.h f25, f26, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_RMM, Fregidx(0b00000), FCVT_S_H), "fcvt.s.h f0, f27, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_RMM, Fregidx(0b00111), FCVT_S_H), "fcvt.s.h f7, f28, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_RMM, Fregidx(0b01110), FCVT_S_H), "fcvt.s.h f14, f29, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_RMM, Fregidx(0b10101), FCVT_S_H), "fcvt.s.h f21, f30, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_S_H), "fcvt.s.h f28, f31, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_S_H), "fcvt.s.h f3, f0, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00001), RM_DYN, Fregidx(0b01010), FCVT_S_H), "fcvt.s.h f10, f1, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00010), RM_DYN, Fregidx(0b10001), FCVT_S_H), "fcvt.s.h f17, f2, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_S_H), "fcvt.s.h f24, f3, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00100), RM_DYN, Fregidx(0b11111), FCVT_S_H), "fcvt.s.h f31, f4, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00101), RM_DYN, Fregidx(0b00110), FCVT_S_H), "fcvt.s.h f6, f5, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00110), RM_DYN, Fregidx(0b01101), FCVT_S_H), "fcvt.s.h f13, f6, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00111), RM_DYN, Fregidx(0b10100), FCVT_S_H), "fcvt.s.h f20, f7, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01000), RM_DYN, Fregidx(0b11011), FCVT_S_H), "fcvt.s.h f27, f8, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01001), RM_DYN, Fregidx(0b00010), FCVT_S_H), "fcvt.s.h f2, f9, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01010), RM_DYN, Fregidx(0b01001), FCVT_S_H), "fcvt.s.h f9, f10, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01011), RM_DYN, Fregidx(0b10000), FCVT_S_H), "fcvt.s.h f16, f11, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01100), RM_DYN, Fregidx(0b10111), FCVT_S_H), "fcvt.s.h f23, f12, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01101), RM_DYN, Fregidx(0b11110), FCVT_S_H), "fcvt.s.h f30, f13, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01110), RM_DYN, Fregidx(0b00101), FCVT_S_H), "fcvt.s.h f5, f14, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b01111), RM_DYN, Fregidx(0b01100), FCVT_S_H), "fcvt.s.h f12, f15, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10000), RM_DYN, Fregidx(0b10011), FCVT_S_H), "fcvt.s.h f19, f16, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10001), RM_DYN, Fregidx(0b11010), FCVT_S_H), "fcvt.s.h f26, f17, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10010), RM_DYN, Fregidx(0b00001), FCVT_S_H), "fcvt.s.h f1, f18, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10011), RM_DYN, Fregidx(0b01000), FCVT_S_H), "fcvt.s.h f8, f19, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10100), RM_DYN, Fregidx(0b01111), FCVT_S_H), "fcvt.s.h f15, f20, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10101), RM_DYN, Fregidx(0b10110), FCVT_S_H), "fcvt.s.h f22, f21, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10110), RM_DYN, Fregidx(0b11101), FCVT_S_H), "fcvt.s.h f29, f22, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b10111), RM_DYN, Fregidx(0b00100), FCVT_S_H), "fcvt.s.h f4, f23, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11000), RM_DYN, Fregidx(0b01011), FCVT_S_H), "fcvt.s.h f11, f24, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11001), RM_DYN, Fregidx(0b10010), FCVT_S_H), "fcvt.s.h f18, f25, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11010), RM_DYN, Fregidx(0b11001), FCVT_S_H), "fcvt.s.h f25, f26, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11011), RM_DYN, Fregidx(0b00000), FCVT_S_H), "fcvt.s.h f0, f27, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11100), RM_DYN, Fregidx(0b00111), FCVT_S_H), "fcvt.s.h f7, f28, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11101), RM_DYN, Fregidx(0b01110), FCVT_S_H), "fcvt.s.h f14, f29, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11110), RM_DYN, Fregidx(0b10101), FCVT_S_H), "fcvt.s.h f21, f30, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_S_H), "fcvt.s.h f28, f31, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_D_W), "fcvt.d.w f3, x0", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RNE, Fregidx(0b01010), FCVT_D_W), "fcvt.d.w f10, x1", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RNE, Fregidx(0b10001), FCVT_D_W), "fcvt.d.w f17, x2", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_D_W), "fcvt.d.w f24, x3", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RNE, Fregidx(0b11111), FCVT_D_W), "fcvt.d.w f31, x4", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RNE, Fregidx(0b00110), FCVT_D_W), "fcvt.d.w f6, x5", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RNE, Fregidx(0b01101), FCVT_D_W), "fcvt.d.w f13, x6", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RNE, Fregidx(0b10100), FCVT_D_W), "fcvt.d.w f20, x7", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RNE, Fregidx(0b11011), FCVT_D_W), "fcvt.d.w f27, x8", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RNE, Fregidx(0b00010), FCVT_D_W), "fcvt.d.w f2, x9", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RNE, Fregidx(0b01001), FCVT_D_W), "fcvt.d.w f9, x10", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RNE, Fregidx(0b10000), FCVT_D_W), "fcvt.d.w f16, x11", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RNE, Fregidx(0b10111), FCVT_D_W), "fcvt.d.w f23, x12", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RNE, Fregidx(0b11110), FCVT_D_W), "fcvt.d.w f30, x13", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RNE, Fregidx(0b00101), FCVT_D_W), "fcvt.d.w f5, x14", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RNE, Fregidx(0b01100), FCVT_D_W), "fcvt.d.w f12, x15", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RNE, Fregidx(0b10011), FCVT_D_W), "fcvt.d.w f19, x16", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RNE, Fregidx(0b11010), FCVT_D_W), "fcvt.d.w f26, x17", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RNE, Fregidx(0b00001), FCVT_D_W), "fcvt.d.w f1, x18", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RNE, Fregidx(0b01000), FCVT_D_W), "fcvt.d.w f8, x19", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RNE, Fregidx(0b01111), FCVT_D_W), "fcvt.d.w f15, x20", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RNE, Fregidx(0b10110), FCVT_D_W), "fcvt.d.w f22, x21", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RNE, Fregidx(0b11101), FCVT_D_W), "fcvt.d.w f29, x22", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RNE, Fregidx(0b00100), FCVT_D_W), "fcvt.d.w f4, x23", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RNE, Fregidx(0b01011), FCVT_D_W), "fcvt.d.w f11, x24", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RNE, Fregidx(0b10010), FCVT_D_W), "fcvt.d.w f18, x25", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RNE, Fregidx(0b11001), FCVT_D_W), "fcvt.d.w f25, x26", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RNE, Fregidx(0b00000), FCVT_D_W), "fcvt.d.w f0, x27", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RNE, Fregidx(0b00111), FCVT_D_W), "fcvt.d.w f7, x28", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RNE, Fregidx(0b01110), FCVT_D_W), "fcvt.d.w f14, x29", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RNE, Fregidx(0b10101), FCVT_D_W), "fcvt.d.w f21, x30", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_D_W), "fcvt.d.w f28, x31", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_D_W), "fcvt.d.w f3, x0, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RTZ, Fregidx(0b01010), FCVT_D_W), "fcvt.d.w f10, x1, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RTZ, Fregidx(0b10001), FCVT_D_W), "fcvt.d.w f17, x2, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_D_W), "fcvt.d.w f24, x3, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RTZ, Fregidx(0b11111), FCVT_D_W), "fcvt.d.w f31, x4, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RTZ, Fregidx(0b00110), FCVT_D_W), "fcvt.d.w f6, x5, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RTZ, Fregidx(0b01101), FCVT_D_W), "fcvt.d.w f13, x6, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RTZ, Fregidx(0b10100), FCVT_D_W), "fcvt.d.w f20, x7, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RTZ, Fregidx(0b11011), FCVT_D_W), "fcvt.d.w f27, x8, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RTZ, Fregidx(0b00010), FCVT_D_W), "fcvt.d.w f2, x9, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RTZ, Fregidx(0b01001), FCVT_D_W), "fcvt.d.w f9, x10, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RTZ, Fregidx(0b10000), FCVT_D_W), "fcvt.d.w f16, x11, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RTZ, Fregidx(0b10111), FCVT_D_W), "fcvt.d.w f23, x12, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RTZ, Fregidx(0b11110), FCVT_D_W), "fcvt.d.w f30, x13, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RTZ, Fregidx(0b00101), FCVT_D_W), "fcvt.d.w f5, x14, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RTZ, Fregidx(0b01100), FCVT_D_W), "fcvt.d.w f12, x15, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RTZ, Fregidx(0b10011), FCVT_D_W), "fcvt.d.w f19, x16, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RTZ, Fregidx(0b11010), FCVT_D_W), "fcvt.d.w f26, x17, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RTZ, Fregidx(0b00001), FCVT_D_W), "fcvt.d.w f1, x18, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RTZ, Fregidx(0b01000), FCVT_D_W), "fcvt.d.w f8, x19, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RTZ, Fregidx(0b01111), FCVT_D_W), "fcvt.d.w f15, x20, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RTZ, Fregidx(0b10110), FCVT_D_W), "fcvt.d.w f22, x21, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RTZ, Fregidx(0b11101), FCVT_D_W), "fcvt.d.w f29, x22, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RTZ, Fregidx(0b00100), FCVT_D_W), "fcvt.d.w f4, x23, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RTZ, Fregidx(0b01011), FCVT_D_W), "fcvt.d.w f11, x24, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RTZ, Fregidx(0b10010), FCVT_D_W), "fcvt.d.w f18, x25, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RTZ, Fregidx(0b11001), FCVT_D_W), "fcvt.d.w f25, x26, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RTZ, Fregidx(0b00000), FCVT_D_W), "fcvt.d.w f0, x27, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RTZ, Fregidx(0b00111), FCVT_D_W), "fcvt.d.w f7, x28, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RTZ, Fregidx(0b01110), FCVT_D_W), "fcvt.d.w f14, x29, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RTZ, Fregidx(0b10101), FCVT_D_W), "fcvt.d.w f21, x30, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_D_W), "fcvt.d.w f28, x31, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_D_W), "fcvt.d.w f3, x0, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RDN, Fregidx(0b01010), FCVT_D_W), "fcvt.d.w f10, x1, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RDN, Fregidx(0b10001), FCVT_D_W), "fcvt.d.w f17, x2, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_D_W), "fcvt.d.w f24, x3, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RDN, Fregidx(0b11111), FCVT_D_W), "fcvt.d.w f31, x4, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RDN, Fregidx(0b00110), FCVT_D_W), "fcvt.d.w f6, x5, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RDN, Fregidx(0b01101), FCVT_D_W), "fcvt.d.w f13, x6, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RDN, Fregidx(0b10100), FCVT_D_W), "fcvt.d.w f20, x7, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RDN, Fregidx(0b11011), FCVT_D_W), "fcvt.d.w f27, x8, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RDN, Fregidx(0b00010), FCVT_D_W), "fcvt.d.w f2, x9, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RDN, Fregidx(0b01001), FCVT_D_W), "fcvt.d.w f9, x10, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RDN, Fregidx(0b10000), FCVT_D_W), "fcvt.d.w f16, x11, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RDN, Fregidx(0b10111), FCVT_D_W), "fcvt.d.w f23, x12, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RDN, Fregidx(0b11110), FCVT_D_W), "fcvt.d.w f30, x13, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RDN, Fregidx(0b00101), FCVT_D_W), "fcvt.d.w f5, x14, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RDN, Fregidx(0b01100), FCVT_D_W), "fcvt.d.w f12, x15, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RDN, Fregidx(0b10011), FCVT_D_W), "fcvt.d.w f19, x16, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RDN, Fregidx(0b11010), FCVT_D_W), "fcvt.d.w f26, x17, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RDN, Fregidx(0b00001), FCVT_D_W), "fcvt.d.w f1, x18, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RDN, Fregidx(0b01000), FCVT_D_W), "fcvt.d.w f8, x19, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RDN, Fregidx(0b01111), FCVT_D_W), "fcvt.d.w f15, x20, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RDN, Fregidx(0b10110), FCVT_D_W), "fcvt.d.w f22, x21, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RDN, Fregidx(0b11101), FCVT_D_W), "fcvt.d.w f29, x22, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RDN, Fregidx(0b00100), FCVT_D_W), "fcvt.d.w f4, x23, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RDN, Fregidx(0b01011), FCVT_D_W), "fcvt.d.w f11, x24, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RDN, Fregidx(0b10010), FCVT_D_W), "fcvt.d.w f18, x25, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RDN, Fregidx(0b11001), FCVT_D_W), "fcvt.d.w f25, x26, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RDN, Fregidx(0b00000), FCVT_D_W), "fcvt.d.w f0, x27, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RDN, Fregidx(0b00111), FCVT_D_W), "fcvt.d.w f7, x28, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RDN, Fregidx(0b01110), FCVT_D_W), "fcvt.d.w f14, x29, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RDN, Fregidx(0b10101), FCVT_D_W), "fcvt.d.w f21, x30, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_D_W), "fcvt.d.w f28, x31, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_D_W), "fcvt.d.w f3, x0, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RUP, Fregidx(0b01010), FCVT_D_W), "fcvt.d.w f10, x1, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RUP, Fregidx(0b10001), FCVT_D_W), "fcvt.d.w f17, x2, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_D_W), "fcvt.d.w f24, x3, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RUP, Fregidx(0b11111), FCVT_D_W), "fcvt.d.w f31, x4, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RUP, Fregidx(0b00110), FCVT_D_W), "fcvt.d.w f6, x5, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RUP, Fregidx(0b01101), FCVT_D_W), "fcvt.d.w f13, x6, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RUP, Fregidx(0b10100), FCVT_D_W), "fcvt.d.w f20, x7, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RUP, Fregidx(0b11011), FCVT_D_W), "fcvt.d.w f27, x8, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RUP, Fregidx(0b00010), FCVT_D_W), "fcvt.d.w f2, x9, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RUP, Fregidx(0b01001), FCVT_D_W), "fcvt.d.w f9, x10, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RUP, Fregidx(0b10000), FCVT_D_W), "fcvt.d.w f16, x11, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RUP, Fregidx(0b10111), FCVT_D_W), "fcvt.d.w f23, x12, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RUP, Fregidx(0b11110), FCVT_D_W), "fcvt.d.w f30, x13, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RUP, Fregidx(0b00101), FCVT_D_W), "fcvt.d.w f5, x14, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RUP, Fregidx(0b01100), FCVT_D_W), "fcvt.d.w f12, x15, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RUP, Fregidx(0b10011), FCVT_D_W), "fcvt.d.w f19, x16, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RUP, Fregidx(0b11010), FCVT_D_W), "fcvt.d.w f26, x17, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RUP, Fregidx(0b00001), FCVT_D_W), "fcvt.d.w f1, x18, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RUP, Fregidx(0b01000), FCVT_D_W), "fcvt.d.w f8, x19, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RUP, Fregidx(0b01111), FCVT_D_W), "fcvt.d.w f15, x20, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RUP, Fregidx(0b10110), FCVT_D_W), "fcvt.d.w f22, x21, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RUP, Fregidx(0b11101), FCVT_D_W), "fcvt.d.w f29, x22, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RUP, Fregidx(0b00100), FCVT_D_W), "fcvt.d.w f4, x23, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RUP, Fregidx(0b01011), FCVT_D_W), "fcvt.d.w f11, x24, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RUP, Fregidx(0b10010), FCVT_D_W), "fcvt.d.w f18, x25, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RUP, Fregidx(0b11001), FCVT_D_W), "fcvt.d.w f25, x26, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RUP, Fregidx(0b00000), FCVT_D_W), "fcvt.d.w f0, x27, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RUP, Fregidx(0b00111), FCVT_D_W), "fcvt.d.w f7, x28, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RUP, Fregidx(0b01110), FCVT_D_W), "fcvt.d.w f14, x29, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RUP, Fregidx(0b10101), FCVT_D_W), "fcvt.d.w f21, x30, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_D_W), "fcvt.d.w f28, x31, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_D_W), "fcvt.d.w f3, x0, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RMM, Fregidx(0b01010), FCVT_D_W), "fcvt.d.w f10, x1, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RMM, Fregidx(0b10001), FCVT_D_W), "fcvt.d.w f17, x2, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_D_W), "fcvt.d.w f24, x3, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RMM, Fregidx(0b11111), FCVT_D_W), "fcvt.d.w f31, x4, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RMM, Fregidx(0b00110), FCVT_D_W), "fcvt.d.w f6, x5, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RMM, Fregidx(0b01101), FCVT_D_W), "fcvt.d.w f13, x6, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RMM, Fregidx(0b10100), FCVT_D_W), "fcvt.d.w f20, x7, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RMM, Fregidx(0b11011), FCVT_D_W), "fcvt.d.w f27, x8, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RMM, Fregidx(0b00010), FCVT_D_W), "fcvt.d.w f2, x9, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RMM, Fregidx(0b01001), FCVT_D_W), "fcvt.d.w f9, x10, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RMM, Fregidx(0b10000), FCVT_D_W), "fcvt.d.w f16, x11, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RMM, Fregidx(0b10111), FCVT_D_W), "fcvt.d.w f23, x12, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RMM, Fregidx(0b11110), FCVT_D_W), "fcvt.d.w f30, x13, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RMM, Fregidx(0b00101), FCVT_D_W), "fcvt.d.w f5, x14, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RMM, Fregidx(0b01100), FCVT_D_W), "fcvt.d.w f12, x15, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RMM, Fregidx(0b10011), FCVT_D_W), "fcvt.d.w f19, x16, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RMM, Fregidx(0b11010), FCVT_D_W), "fcvt.d.w f26, x17, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RMM, Fregidx(0b00001), FCVT_D_W), "fcvt.d.w f1, x18, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RMM, Fregidx(0b01000), FCVT_D_W), "fcvt.d.w f8, x19, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RMM, Fregidx(0b01111), FCVT_D_W), "fcvt.d.w f15, x20, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RMM, Fregidx(0b10110), FCVT_D_W), "fcvt.d.w f22, x21, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RMM, Fregidx(0b11101), FCVT_D_W), "fcvt.d.w f29, x22, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RMM, Fregidx(0b00100), FCVT_D_W), "fcvt.d.w f4, x23, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RMM, Fregidx(0b01011), FCVT_D_W), "fcvt.d.w f11, x24, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RMM, Fregidx(0b10010), FCVT_D_W), "fcvt.d.w f18, x25, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RMM, Fregidx(0b11001), FCVT_D_W), "fcvt.d.w f25, x26, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RMM, Fregidx(0b00000), FCVT_D_W), "fcvt.d.w f0, x27, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RMM, Fregidx(0b00111), FCVT_D_W), "fcvt.d.w f7, x28, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RMM, Fregidx(0b01110), FCVT_D_W), "fcvt.d.w f14, x29, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RMM, Fregidx(0b10101), FCVT_D_W), "fcvt.d.w f21, x30, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_D_W), "fcvt.d.w f28, x31, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_D_W), "fcvt.d.w f3, x0, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_DYN, Fregidx(0b01010), FCVT_D_W), "fcvt.d.w f10, x1, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_DYN, Fregidx(0b10001), FCVT_D_W), "fcvt.d.w f17, x2, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_D_W), "fcvt.d.w f24, x3, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_DYN, Fregidx(0b11111), FCVT_D_W), "fcvt.d.w f31, x4, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_DYN, Fregidx(0b00110), FCVT_D_W), "fcvt.d.w f6, x5, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_DYN, Fregidx(0b01101), FCVT_D_W), "fcvt.d.w f13, x6, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_DYN, Fregidx(0b10100), FCVT_D_W), "fcvt.d.w f20, x7, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_DYN, Fregidx(0b11011), FCVT_D_W), "fcvt.d.w f27, x8, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_DYN, Fregidx(0b00010), FCVT_D_W), "fcvt.d.w f2, x9, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_DYN, Fregidx(0b01001), FCVT_D_W), "fcvt.d.w f9, x10, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_DYN, Fregidx(0b10000), FCVT_D_W), "fcvt.d.w f16, x11, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_DYN, Fregidx(0b10111), FCVT_D_W), "fcvt.d.w f23, x12, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_DYN, Fregidx(0b11110), FCVT_D_W), "fcvt.d.w f30, x13, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_DYN, Fregidx(0b00101), FCVT_D_W), "fcvt.d.w f5, x14, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_DYN, Fregidx(0b01100), FCVT_D_W), "fcvt.d.w f12, x15, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_DYN, Fregidx(0b10011), FCVT_D_W), "fcvt.d.w f19, x16, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_DYN, Fregidx(0b11010), FCVT_D_W), "fcvt.d.w f26, x17, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_DYN, Fregidx(0b00001), FCVT_D_W), "fcvt.d.w f1, x18, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_DYN, Fregidx(0b01000), FCVT_D_W), "fcvt.d.w f8, x19, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_DYN, Fregidx(0b01111), FCVT_D_W), "fcvt.d.w f15, x20, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_DYN, Fregidx(0b10110), FCVT_D_W), "fcvt.d.w f22, x21, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_DYN, Fregidx(0b11101), FCVT_D_W), "fcvt.d.w f29, x22, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_DYN, Fregidx(0b00100), FCVT_D_W), "fcvt.d.w f4, x23, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_DYN, Fregidx(0b01011), FCVT_D_W), "fcvt.d.w f11, x24, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_DYN, Fregidx(0b10010), FCVT_D_W), "fcvt.d.w f18, x25, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_DYN, Fregidx(0b11001), FCVT_D_W), "fcvt.d.w f25, x26, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_DYN, Fregidx(0b00000), FCVT_D_W), "fcvt.d.w f0, x27, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_DYN, Fregidx(0b00111), FCVT_D_W), "fcvt.d.w f7, x28, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_DYN, Fregidx(0b01110), FCVT_D_W), "fcvt.d.w f14, x29, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_DYN, Fregidx(0b10101), FCVT_D_W), "fcvt.d.w f21, x30, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_D_W), "fcvt.d.w f28, x31, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_D_WU), "fcvt.d.wu f3, x0", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RNE, Fregidx(0b01010), FCVT_D_WU), "fcvt.d.wu f10, x1", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RNE, Fregidx(0b10001), FCVT_D_WU), "fcvt.d.wu f17, x2", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_D_WU), "fcvt.d.wu f24, x3", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RNE, Fregidx(0b11111), FCVT_D_WU), "fcvt.d.wu f31, x4", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RNE, Fregidx(0b00110), FCVT_D_WU), "fcvt.d.wu f6, x5", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RNE, Fregidx(0b01101), FCVT_D_WU), "fcvt.d.wu f13, x6", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RNE, Fregidx(0b10100), FCVT_D_WU), "fcvt.d.wu f20, x7", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RNE, Fregidx(0b11011), FCVT_D_WU), "fcvt.d.wu f27, x8", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RNE, Fregidx(0b00010), FCVT_D_WU), "fcvt.d.wu f2, x9", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RNE, Fregidx(0b01001), FCVT_D_WU), "fcvt.d.wu f9, x10", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RNE, Fregidx(0b10000), FCVT_D_WU), "fcvt.d.wu f16, x11", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RNE, Fregidx(0b10111), FCVT_D_WU), "fcvt.d.wu f23, x12", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RNE, Fregidx(0b11110), FCVT_D_WU), "fcvt.d.wu f30, x13", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RNE, Fregidx(0b00101), FCVT_D_WU), "fcvt.d.wu f5, x14", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RNE, Fregidx(0b01100), FCVT_D_WU), "fcvt.d.wu f12, x15", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RNE, Fregidx(0b10011), FCVT_D_WU), "fcvt.d.wu f19, x16", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RNE, Fregidx(0b11010), FCVT_D_WU), "fcvt.d.wu f26, x17", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RNE, Fregidx(0b00001), FCVT_D_WU), "fcvt.d.wu f1, x18", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RNE, Fregidx(0b01000), FCVT_D_WU), "fcvt.d.wu f8, x19", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RNE, Fregidx(0b01111), FCVT_D_WU), "fcvt.d.wu f15, x20", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RNE, Fregidx(0b10110), FCVT_D_WU), "fcvt.d.wu f22, x21", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RNE, Fregidx(0b11101), FCVT_D_WU), "fcvt.d.wu f29, x22", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RNE, Fregidx(0b00100), FCVT_D_WU), "fcvt.d.wu f4, x23", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RNE, Fregidx(0b01011), FCVT_D_WU), "fcvt.d.wu f11, x24", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RNE, Fregidx(0b10010), FCVT_D_WU), "fcvt.d.wu f18, x25", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RNE, Fregidx(0b11001), FCVT_D_WU), "fcvt.d.wu f25, x26", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RNE, Fregidx(0b00000), FCVT_D_WU), "fcvt.d.wu f0, x27", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RNE, Fregidx(0b00111), FCVT_D_WU), "fcvt.d.wu f7, x28", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RNE, Fregidx(0b01110), FCVT_D_WU), "fcvt.d.wu f14, x29", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RNE, Fregidx(0b10101), FCVT_D_WU), "fcvt.d.wu f21, x30", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_D_WU), "fcvt.d.wu f28, x31", true);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_D_WU), "fcvt.d.wu f3, x0, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RTZ, Fregidx(0b01010), FCVT_D_WU), "fcvt.d.wu f10, x1, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RTZ, Fregidx(0b10001), FCVT_D_WU), "fcvt.d.wu f17, x2, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_D_WU), "fcvt.d.wu f24, x3, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RTZ, Fregidx(0b11111), FCVT_D_WU), "fcvt.d.wu f31, x4, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RTZ, Fregidx(0b00110), FCVT_D_WU), "fcvt.d.wu f6, x5, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RTZ, Fregidx(0b01101), FCVT_D_WU), "fcvt.d.wu f13, x6, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RTZ, Fregidx(0b10100), FCVT_D_WU), "fcvt.d.wu f20, x7, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RTZ, Fregidx(0b11011), FCVT_D_WU), "fcvt.d.wu f27, x8, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RTZ, Fregidx(0b00010), FCVT_D_WU), "fcvt.d.wu f2, x9, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RTZ, Fregidx(0b01001), FCVT_D_WU), "fcvt.d.wu f9, x10, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RTZ, Fregidx(0b10000), FCVT_D_WU), "fcvt.d.wu f16, x11, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RTZ, Fregidx(0b10111), FCVT_D_WU), "fcvt.d.wu f23, x12, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RTZ, Fregidx(0b11110), FCVT_D_WU), "fcvt.d.wu f30, x13, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RTZ, Fregidx(0b00101), FCVT_D_WU), "fcvt.d.wu f5, x14, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RTZ, Fregidx(0b01100), FCVT_D_WU), "fcvt.d.wu f12, x15, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RTZ, Fregidx(0b10011), FCVT_D_WU), "fcvt.d.wu f19, x16, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RTZ, Fregidx(0b11010), FCVT_D_WU), "fcvt.d.wu f26, x17, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RTZ, Fregidx(0b00001), FCVT_D_WU), "fcvt.d.wu f1, x18, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RTZ, Fregidx(0b01000), FCVT_D_WU), "fcvt.d.wu f8, x19, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RTZ, Fregidx(0b01111), FCVT_D_WU), "fcvt.d.wu f15, x20, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RTZ, Fregidx(0b10110), FCVT_D_WU), "fcvt.d.wu f22, x21, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RTZ, Fregidx(0b11101), FCVT_D_WU), "fcvt.d.wu f29, x22, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RTZ, Fregidx(0b00100), FCVT_D_WU), "fcvt.d.wu f4, x23, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RTZ, Fregidx(0b01011), FCVT_D_WU), "fcvt.d.wu f11, x24, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RTZ, Fregidx(0b10010), FCVT_D_WU), "fcvt.d.wu f18, x25, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RTZ, Fregidx(0b11001), FCVT_D_WU), "fcvt.d.wu f25, x26, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RTZ, Fregidx(0b00000), FCVT_D_WU), "fcvt.d.wu f0, x27, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RTZ, Fregidx(0b00111), FCVT_D_WU), "fcvt.d.wu f7, x28, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RTZ, Fregidx(0b01110), FCVT_D_WU), "fcvt.d.wu f14, x29, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RTZ, Fregidx(0b10101), FCVT_D_WU), "fcvt.d.wu f21, x30, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_D_WU), "fcvt.d.wu f28, x31, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_D_WU), "fcvt.d.wu f3, x0, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RDN, Fregidx(0b01010), FCVT_D_WU), "fcvt.d.wu f10, x1, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RDN, Fregidx(0b10001), FCVT_D_WU), "fcvt.d.wu f17, x2, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_D_WU), "fcvt.d.wu f24, x3, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RDN, Fregidx(0b11111), FCVT_D_WU), "fcvt.d.wu f31, x4, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RDN, Fregidx(0b00110), FCVT_D_WU), "fcvt.d.wu f6, x5, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RDN, Fregidx(0b01101), FCVT_D_WU), "fcvt.d.wu f13, x6, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RDN, Fregidx(0b10100), FCVT_D_WU), "fcvt.d.wu f20, x7, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RDN, Fregidx(0b11011), FCVT_D_WU), "fcvt.d.wu f27, x8, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RDN, Fregidx(0b00010), FCVT_D_WU), "fcvt.d.wu f2, x9, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RDN, Fregidx(0b01001), FCVT_D_WU), "fcvt.d.wu f9, x10, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RDN, Fregidx(0b10000), FCVT_D_WU), "fcvt.d.wu f16, x11, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RDN, Fregidx(0b10111), FCVT_D_WU), "fcvt.d.wu f23, x12, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RDN, Fregidx(0b11110), FCVT_D_WU), "fcvt.d.wu f30, x13, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RDN, Fregidx(0b00101), FCVT_D_WU), "fcvt.d.wu f5, x14, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RDN, Fregidx(0b01100), FCVT_D_WU), "fcvt.d.wu f12, x15, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RDN, Fregidx(0b10011), FCVT_D_WU), "fcvt.d.wu f19, x16, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RDN, Fregidx(0b11010), FCVT_D_WU), "fcvt.d.wu f26, x17, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RDN, Fregidx(0b00001), FCVT_D_WU), "fcvt.d.wu f1, x18, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RDN, Fregidx(0b01000), FCVT_D_WU), "fcvt.d.wu f8, x19, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RDN, Fregidx(0b01111), FCVT_D_WU), "fcvt.d.wu f15, x20, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RDN, Fregidx(0b10110), FCVT_D_WU), "fcvt.d.wu f22, x21, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RDN, Fregidx(0b11101), FCVT_D_WU), "fcvt.d.wu f29, x22, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RDN, Fregidx(0b00100), FCVT_D_WU), "fcvt.d.wu f4, x23, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RDN, Fregidx(0b01011), FCVT_D_WU), "fcvt.d.wu f11, x24, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RDN, Fregidx(0b10010), FCVT_D_WU), "fcvt.d.wu f18, x25, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RDN, Fregidx(0b11001), FCVT_D_WU), "fcvt.d.wu f25, x26, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RDN, Fregidx(0b00000), FCVT_D_WU), "fcvt.d.wu f0, x27, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RDN, Fregidx(0b00111), FCVT_D_WU), "fcvt.d.wu f7, x28, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RDN, Fregidx(0b01110), FCVT_D_WU), "fcvt.d.wu f14, x29, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RDN, Fregidx(0b10101), FCVT_D_WU), "fcvt.d.wu f21, x30, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_D_WU), "fcvt.d.wu f28, x31, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_D_WU), "fcvt.d.wu f3, x0, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RUP, Fregidx(0b01010), FCVT_D_WU), "fcvt.d.wu f10, x1, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RUP, Fregidx(0b10001), FCVT_D_WU), "fcvt.d.wu f17, x2, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_D_WU), "fcvt.d.wu f24, x3, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RUP, Fregidx(0b11111), FCVT_D_WU), "fcvt.d.wu f31, x4, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RUP, Fregidx(0b00110), FCVT_D_WU), "fcvt.d.wu f6, x5, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RUP, Fregidx(0b01101), FCVT_D_WU), "fcvt.d.wu f13, x6, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RUP, Fregidx(0b10100), FCVT_D_WU), "fcvt.d.wu f20, x7, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RUP, Fregidx(0b11011), FCVT_D_WU), "fcvt.d.wu f27, x8, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RUP, Fregidx(0b00010), FCVT_D_WU), "fcvt.d.wu f2, x9, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RUP, Fregidx(0b01001), FCVT_D_WU), "fcvt.d.wu f9, x10, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RUP, Fregidx(0b10000), FCVT_D_WU), "fcvt.d.wu f16, x11, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RUP, Fregidx(0b10111), FCVT_D_WU), "fcvt.d.wu f23, x12, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RUP, Fregidx(0b11110), FCVT_D_WU), "fcvt.d.wu f30, x13, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RUP, Fregidx(0b00101), FCVT_D_WU), "fcvt.d.wu f5, x14, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RUP, Fregidx(0b01100), FCVT_D_WU), "fcvt.d.wu f12, x15, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RUP, Fregidx(0b10011), FCVT_D_WU), "fcvt.d.wu f19, x16, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RUP, Fregidx(0b11010), FCVT_D_WU), "fcvt.d.wu f26, x17, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RUP, Fregidx(0b00001), FCVT_D_WU), "fcvt.d.wu f1, x18, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RUP, Fregidx(0b01000), FCVT_D_WU), "fcvt.d.wu f8, x19, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RUP, Fregidx(0b01111), FCVT_D_WU), "fcvt.d.wu f15, x20, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RUP, Fregidx(0b10110), FCVT_D_WU), "fcvt.d.wu f22, x21, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RUP, Fregidx(0b11101), FCVT_D_WU), "fcvt.d.wu f29, x22, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RUP, Fregidx(0b00100), FCVT_D_WU), "fcvt.d.wu f4, x23, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RUP, Fregidx(0b01011), FCVT_D_WU), "fcvt.d.wu f11, x24, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RUP, Fregidx(0b10010), FCVT_D_WU), "fcvt.d.wu f18, x25, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RUP, Fregidx(0b11001), FCVT_D_WU), "fcvt.d.wu f25, x26, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RUP, Fregidx(0b00000), FCVT_D_WU), "fcvt.d.wu f0, x27, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RUP, Fregidx(0b00111), FCVT_D_WU), "fcvt.d.wu f7, x28, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RUP, Fregidx(0b01110), FCVT_D_WU), "fcvt.d.wu f14, x29, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RUP, Fregidx(0b10101), FCVT_D_WU), "fcvt.d.wu f21, x30, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_D_WU), "fcvt.d.wu f28, x31, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_D_WU), "fcvt.d.wu f3, x0, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_RMM, Fregidx(0b01010), FCVT_D_WU), "fcvt.d.wu f10, x1, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_RMM, Fregidx(0b10001), FCVT_D_WU), "fcvt.d.wu f17, x2, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_D_WU), "fcvt.d.wu f24, x3, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_RMM, Fregidx(0b11111), FCVT_D_WU), "fcvt.d.wu f31, x4, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_RMM, Fregidx(0b00110), FCVT_D_WU), "fcvt.d.wu f6, x5, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_RMM, Fregidx(0b01101), FCVT_D_WU), "fcvt.d.wu f13, x6, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_RMM, Fregidx(0b10100), FCVT_D_WU), "fcvt.d.wu f20, x7, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_RMM, Fregidx(0b11011), FCVT_D_WU), "fcvt.d.wu f27, x8, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_RMM, Fregidx(0b00010), FCVT_D_WU), "fcvt.d.wu f2, x9, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_RMM, Fregidx(0b01001), FCVT_D_WU), "fcvt.d.wu f9, x10, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_RMM, Fregidx(0b10000), FCVT_D_WU), "fcvt.d.wu f16, x11, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_RMM, Fregidx(0b10111), FCVT_D_WU), "fcvt.d.wu f23, x12, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_RMM, Fregidx(0b11110), FCVT_D_WU), "fcvt.d.wu f30, x13, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_RMM, Fregidx(0b00101), FCVT_D_WU), "fcvt.d.wu f5, x14, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_RMM, Fregidx(0b01100), FCVT_D_WU), "fcvt.d.wu f12, x15, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_RMM, Fregidx(0b10011), FCVT_D_WU), "fcvt.d.wu f19, x16, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_RMM, Fregidx(0b11010), FCVT_D_WU), "fcvt.d.wu f26, x17, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_RMM, Fregidx(0b00001), FCVT_D_WU), "fcvt.d.wu f1, x18, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_RMM, Fregidx(0b01000), FCVT_D_WU), "fcvt.d.wu f8, x19, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_RMM, Fregidx(0b01111), FCVT_D_WU), "fcvt.d.wu f15, x20, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_RMM, Fregidx(0b10110), FCVT_D_WU), "fcvt.d.wu f22, x21, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_RMM, Fregidx(0b11101), FCVT_D_WU), "fcvt.d.wu f29, x22, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_RMM, Fregidx(0b00100), FCVT_D_WU), "fcvt.d.wu f4, x23, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_RMM, Fregidx(0b01011), FCVT_D_WU), "fcvt.d.wu f11, x24, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_RMM, Fregidx(0b10010), FCVT_D_WU), "fcvt.d.wu f18, x25, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_RMM, Fregidx(0b11001), FCVT_D_WU), "fcvt.d.wu f25, x26, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_RMM, Fregidx(0b00000), FCVT_D_WU), "fcvt.d.wu f0, x27, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_RMM, Fregidx(0b00111), FCVT_D_WU), "fcvt.d.wu f7, x28, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_RMM, Fregidx(0b01110), FCVT_D_WU), "fcvt.d.wu f14, x29, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_RMM, Fregidx(0b10101), FCVT_D_WU), "fcvt.d.wu f21, x30, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_D_WU), "fcvt.d.wu f28, x31, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_D_WU), "fcvt.d.wu f3, x0, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00001), RM_DYN, Fregidx(0b01010), FCVT_D_WU), "fcvt.d.wu f10, x1, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00010), RM_DYN, Fregidx(0b10001), FCVT_D_WU), "fcvt.d.wu f17, x2, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_D_WU), "fcvt.d.wu f24, x3, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00100), RM_DYN, Fregidx(0b11111), FCVT_D_WU), "fcvt.d.wu f31, x4, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00101), RM_DYN, Fregidx(0b00110), FCVT_D_WU), "fcvt.d.wu f6, x5, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00110), RM_DYN, Fregidx(0b01101), FCVT_D_WU), "fcvt.d.wu f13, x6, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00111), RM_DYN, Fregidx(0b10100), FCVT_D_WU), "fcvt.d.wu f20, x7, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01000), RM_DYN, Fregidx(0b11011), FCVT_D_WU), "fcvt.d.wu f27, x8, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01001), RM_DYN, Fregidx(0b00010), FCVT_D_WU), "fcvt.d.wu f2, x9, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01010), RM_DYN, Fregidx(0b01001), FCVT_D_WU), "fcvt.d.wu f9, x10, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01011), RM_DYN, Fregidx(0b10000), FCVT_D_WU), "fcvt.d.wu f16, x11, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01100), RM_DYN, Fregidx(0b10111), FCVT_D_WU), "fcvt.d.wu f23, x12, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01101), RM_DYN, Fregidx(0b11110), FCVT_D_WU), "fcvt.d.wu f30, x13, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01110), RM_DYN, Fregidx(0b00101), FCVT_D_WU), "fcvt.d.wu f5, x14, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b01111), RM_DYN, Fregidx(0b01100), FCVT_D_WU), "fcvt.d.wu f12, x15, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10000), RM_DYN, Fregidx(0b10011), FCVT_D_WU), "fcvt.d.wu f19, x16, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10001), RM_DYN, Fregidx(0b11010), FCVT_D_WU), "fcvt.d.wu f26, x17, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10010), RM_DYN, Fregidx(0b00001), FCVT_D_WU), "fcvt.d.wu f1, x18, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10011), RM_DYN, Fregidx(0b01000), FCVT_D_WU), "fcvt.d.wu f8, x19, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10100), RM_DYN, Fregidx(0b01111), FCVT_D_WU), "fcvt.d.wu f15, x20, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10101), RM_DYN, Fregidx(0b10110), FCVT_D_WU), "fcvt.d.wu f22, x21, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10110), RM_DYN, Fregidx(0b11101), FCVT_D_WU), "fcvt.d.wu f29, x22, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b10111), RM_DYN, Fregidx(0b00100), FCVT_D_WU), "fcvt.d.wu f4, x23, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11000), RM_DYN, Fregidx(0b01011), FCVT_D_WU), "fcvt.d.wu f11, x24, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11001), RM_DYN, Fregidx(0b10010), FCVT_D_WU), "fcvt.d.wu f18, x25, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11010), RM_DYN, Fregidx(0b11001), FCVT_D_WU), "fcvt.d.wu f25, x26, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11011), RM_DYN, Fregidx(0b00000), FCVT_D_WU), "fcvt.d.wu f0, x27, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11100), RM_DYN, Fregidx(0b00111), FCVT_D_WU), "fcvt.d.wu f7, x28, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11101), RM_DYN, Fregidx(0b01110), FCVT_D_WU), "fcvt.d.wu f14, x29, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11110), RM_DYN, Fregidx(0b10101), FCVT_D_WU), "fcvt.d.wu f21, x30, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_D_WU), "fcvt.d.wu f28, x31, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_D_L), "fcvt.d.l f3, x0, rne", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_D_L), "fcvt.d.l f24, x3, rne", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_D_L), "fcvt.d.l f28, x31, rne", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_D_L), "fcvt.d.l f3, x0, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_D_L), "fcvt.d.l f24, x3, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_D_L), "fcvt.d.l f28, x31, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_D_L), "fcvt.d.l f3, x0, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_D_L), "fcvt.d.l f24, x3, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_D_L), "fcvt.d.l f28, x31, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_D_L), "fcvt.d.l f3, x0, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_D_L), "fcvt.d.l f24, x3, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_D_L), "fcvt.d.l f28, x31, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_D_L), "fcvt.d.l f3, x0, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_D_L), "fcvt.d.l f24, x3, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_D_L), "fcvt.d.l f28, x31, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_D_L), "fcvt.d.l f3, x0, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_D_L), "fcvt.d.l f24, x3, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_D_L), "fcvt.d.l f28, x31, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_D_LU), "fcvt.d.lu f3, x0, rne", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_D_LU), "fcvt.d.lu f24, x3, rne", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_D_LU), "fcvt.d.lu f28, x31, rne", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_D_LU), "fcvt.d.lu f3, x0, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_D_LU), "fcvt.d.lu f24, x3, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_D_LU), "fcvt.d.lu f28, x31, rtz", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_D_LU), "fcvt.d.lu f3, x0, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_D_LU), "fcvt.d.lu f24, x3, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_D_LU), "fcvt.d.lu f28, x31, rdn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_D_LU), "fcvt.d.lu f3, x0, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_D_LU), "fcvt.d.lu f24, x3, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_D_LU), "fcvt.d.lu f28, x31, rup", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_D_LU), "fcvt.d.lu f3, x0, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_D_LU), "fcvt.d.lu f24, x3, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_D_LU), "fcvt.d.lu f28, x31, rmm", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_D_LU), "fcvt.d.lu f3, x0, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_D_LU), "fcvt.d.lu f24, x3, dyn", false);

  check_case(F_UN_RM_XF_TYPE_D(Regidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_D_LU), "fcvt.d.lu f28, x31, dyn", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_S_W), "fcvt.s.w f3, x0, rne", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_S_W), "fcvt.s.w f24, x3, rne", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_S_W), "fcvt.s.w f28, x31, rne", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_S_W), "fcvt.s.w f3, x0, rtz", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_S_W), "fcvt.s.w f24, x3, rtz", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_S_W), "fcvt.s.w f28, x31, rtz", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_S_W), "fcvt.s.w f3, x0, rdn", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_S_W), "fcvt.s.w f24, x3, rdn", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_S_W), "fcvt.s.w f28, x31, rdn", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_S_W), "fcvt.s.w f3, x0, rup", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_S_W), "fcvt.s.w f24, x3, rup", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_S_W), "fcvt.s.w f28, x31, rup", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_S_W), "fcvt.s.w f3, x0, rmm", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_S_W), "fcvt.s.w f24, x3, rmm", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_S_W), "fcvt.s.w f28, x31, rmm", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_S_W), "fcvt.s.w f3, x0, dyn", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_S_W), "fcvt.s.w f24, x3, dyn", false);

  check_case(F_UN_RM_XF_TYPE_S(Regidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_S_W), "fcvt.s.w f28, x31, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RNE, Fregidx(0b00011), FSQRT_D), "fsqrt.d f3, f0, rne", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RNE, Fregidx(0b11000), FSQRT_D), "fsqrt.d f24, f3, rne", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RNE, Fregidx(0b11100), FSQRT_D), "fsqrt.d f28, f31, rne", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RTZ, Fregidx(0b00011), FSQRT_D), "fsqrt.d f3, f0, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RTZ, Fregidx(0b11000), FSQRT_D), "fsqrt.d f24, f3, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RTZ, Fregidx(0b11100), FSQRT_D), "fsqrt.d f28, f31, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RDN, Fregidx(0b00011), FSQRT_D), "fsqrt.d f3, f0, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RDN, Fregidx(0b11000), FSQRT_D), "fsqrt.d f24, f3, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RDN, Fregidx(0b11100), FSQRT_D), "fsqrt.d f28, f31, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RUP, Fregidx(0b00011), FSQRT_D), "fsqrt.d f3, f0, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RUP, Fregidx(0b11000), FSQRT_D), "fsqrt.d f24, f3, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RUP, Fregidx(0b11100), FSQRT_D), "fsqrt.d f28, f31, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RMM, Fregidx(0b00011), FSQRT_D), "fsqrt.d f3, f0, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RMM, Fregidx(0b11000), FSQRT_D), "fsqrt.d f24, f3, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RMM, Fregidx(0b11100), FSQRT_D), "fsqrt.d f28, f31, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_DYN, Fregidx(0b00011), FSQRT_D), "fsqrt.d f3, f0, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_DYN, Fregidx(0b11000), FSQRT_D), "fsqrt.d f24, f3, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_DYN, Fregidx(0b11100), FSQRT_D), "fsqrt.d f28, f31, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_S_D), "fcvt.s.d f3, f0, rne", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_S_D), "fcvt.s.d f24, f3, rne", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_S_D), "fcvt.s.d f28, f31, rne", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_S_D), "fcvt.s.d f3, f0, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_S_D), "fcvt.s.d f24, f3, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_S_D), "fcvt.s.d f28, f31, rtz", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_S_D), "fcvt.s.d f3, f0, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_S_D), "fcvt.s.d f24, f3, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_S_D), "fcvt.s.d f28, f31, rdn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_S_D), "fcvt.s.d f3, f0, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_S_D), "fcvt.s.d f24, f3, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_S_D), "fcvt.s.d f28, f31, rup", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_S_D), "fcvt.s.d f3, f0, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_S_D), "fcvt.s.d f24, f3, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_S_D), "fcvt.s.d f28, f31, rmm", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_S_D), "fcvt.s.d f3, f0, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_S_D), "fcvt.s.d f24, f3, dyn", false);

  check_case(F_UN_RM_FF_TYPE_D(Fregidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_S_D), "fcvt.s.d f28, f31, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RNE, Fregidx(0b00011), FSQRT_H), "fsqrt.h f3, f0, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RNE, Fregidx(0b11000), FSQRT_H), "fsqrt.h f24, f3, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RNE, Fregidx(0b11100), FSQRT_H), "fsqrt.h f28, f31, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RTZ, Fregidx(0b00011), FSQRT_H), "fsqrt.h f3, f0, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RTZ, Fregidx(0b11000), FSQRT_H), "fsqrt.h f24, f3, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RTZ, Fregidx(0b11100), FSQRT_H), "fsqrt.h f28, f31, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RDN, Fregidx(0b00011), FSQRT_H), "fsqrt.h f3, f0, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RDN, Fregidx(0b11000), FSQRT_H), "fsqrt.h f24, f3, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RDN, Fregidx(0b11100), FSQRT_H), "fsqrt.h f28, f31, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RUP, Fregidx(0b00011), FSQRT_H), "fsqrt.h f3, f0, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RUP, Fregidx(0b11000), FSQRT_H), "fsqrt.h f24, f3, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RUP, Fregidx(0b11100), FSQRT_H), "fsqrt.h f28, f31, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RMM, Fregidx(0b00011), FSQRT_H), "fsqrt.h f3, f0, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RMM, Fregidx(0b11000), FSQRT_H), "fsqrt.h f24, f3, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RMM, Fregidx(0b11100), FSQRT_H), "fsqrt.h f28, f31, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_DYN, Fregidx(0b00011), FSQRT_H), "fsqrt.h f3, f0, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_DYN, Fregidx(0b11000), FSQRT_H), "fsqrt.h f24, f3, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_DYN, Fregidx(0b11100), FSQRT_H), "fsqrt.h f28, f31, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_H_S), "fcvt.h.s f3, f0, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_H_S), "fcvt.h.s f24, f3, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_H_S), "fcvt.h.s f28, f31, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_H_S), "fcvt.h.s f3, f0, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_H_S), "fcvt.h.s f24, f3, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_H_S), "fcvt.h.s f28, f31, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_H_S), "fcvt.h.s f3, f0, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_H_S), "fcvt.h.s f24, f3, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_H_S), "fcvt.h.s f28, f31, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_H_S), "fcvt.h.s f3, f0, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_H_S), "fcvt.h.s f24, f3, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_H_S), "fcvt.h.s f28, f31, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_H_S), "fcvt.h.s f3, f0, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_H_S), "fcvt.h.s f24, f3, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_H_S), "fcvt.h.s f28, f31, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_H_S), "fcvt.h.s f3, f0, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_H_S), "fcvt.h.s f24, f3, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_H_S), "fcvt.h.s f28, f31, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RNE, Fregidx(0b00011), FCVT_H_D), "fcvt.h.d f3, f0, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RNE, Fregidx(0b11000), FCVT_H_D), "fcvt.h.d f24, f3, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RNE, Fregidx(0b11100), FCVT_H_D), "fcvt.h.d f28, f31, rne", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RTZ, Fregidx(0b00011), FCVT_H_D), "fcvt.h.d f3, f0, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RTZ, Fregidx(0b11000), FCVT_H_D), "fcvt.h.d f24, f3, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RTZ, Fregidx(0b11100), FCVT_H_D), "fcvt.h.d f28, f31, rtz", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RDN, Fregidx(0b00011), FCVT_H_D), "fcvt.h.d f3, f0, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RDN, Fregidx(0b11000), FCVT_H_D), "fcvt.h.d f24, f3, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RDN, Fregidx(0b11100), FCVT_H_D), "fcvt.h.d f28, f31, rdn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RUP, Fregidx(0b00011), FCVT_H_D), "fcvt.h.d f3, f0, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RUP, Fregidx(0b11000), FCVT_H_D), "fcvt.h.d f24, f3, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RUP, Fregidx(0b11100), FCVT_H_D), "fcvt.h.d f28, f31, rup", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_RMM, Fregidx(0b00011), FCVT_H_D), "fcvt.h.d f3, f0, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_RMM, Fregidx(0b11000), FCVT_H_D), "fcvt.h.d f24, f3, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_RMM, Fregidx(0b11100), FCVT_H_D), "fcvt.h.d f28, f31, rmm", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00000), RM_DYN, Fregidx(0b00011), FCVT_H_D), "fcvt.h.d f3, f0, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b00011), RM_DYN, Fregidx(0b11000), FCVT_H_D), "fcvt.h.d f24, f3, dyn", false);

  check_case(F_UN_RM_FF_TYPE_H(Fregidx(0b11111), RM_DYN, Fregidx(0b11100), FCVT_H_D), "fcvt.h.d f28, f31, dyn", false);

  ()
}
