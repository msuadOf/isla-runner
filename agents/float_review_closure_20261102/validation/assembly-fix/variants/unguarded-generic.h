#pragma once

#include "sail.h"
#include "sail_config.h"
#include "rts.h"
#include "elf.h"
#ifdef __cplusplus
extern "C" {
#endif
extern void (*sail_rts_set_coverage_file)(const char *);

// enum rounding_mode
enum zrounding_mode { zRM_RNE, zRM_RTZ, zRM_RDN, zRM_RUP, zRM_RMM, zRM_DYN };

// union regidx
enum kind_zregidx { Kind_zRegidx };

struct zregidx {
  enum kind_zregidx kind;
  union {struct { uint64_t zRegidx; };} variants;
};

// union fregidx
enum kind_zfregidx { Kind_zFregidx };

struct zfregidx {
  enum kind_zfregidx kind;
  union {struct { uint64_t zFregidx; };} variants;
};

// type abbreviation fp_rounding_modes
typedef uint64_t zfp_rounding_modes;

// type abbreviation fp_exception_flags
typedef uint64_t zfp_exception_flags;

// enum float_class
enum zfloat_class { zfloat_class_negative_inf, zfloat_class_negative_normal, zfloat_class_negative_subnormal, zfloat_class_negative_zzero, zfloat_class_positive_zzero, zfloat_class_positive_subnormal, zfloat_class_positive_normal, zfloat_class_positive_inf, zfloat_class_snan, zfloat_class_qnan };

// enum f_un_rm_xf_op_S
enum zf_un_rm_xf_op_S { zFCVT_S_W, zFCVT_S_WU, zFCVT_S_L, zFCVT_S_LU };

// enum f_un_rm_xf_op_D
enum zf_un_rm_xf_op_D { zFCVT_D_W, zFCVT_D_WU, zFCVT_D_L, zFCVT_D_LU };

// enum f_un_rm_ff_op_H
enum zf_un_rm_ff_op_H { zFSQRT_H, zFCVT_H_S, zFCVT_H_D, zFCVT_S_H, zFCVT_D_H };

// enum f_un_rm_ff_op_D
enum zf_un_rm_ff_op_D { zFSQRT_D, zFCVT_S_D, zFCVT_D_S };

// struct tuple_(%union zfregidx, %enum zrounding_mode, %union zfregidx, %enum zf_un_rm_ff_op_D)
struct ztuple_z8z5unionz0zzfregidxzCz0z5enumz0zzrounding_modezCz0z5unionz0zzfregidxzCz0z5enumz0zzf_un_rm_ff_op_Dz9 {
  struct zfregidx ztup0;
  enum zrounding_mode ztup1;
  struct zfregidx ztup2;
  enum zf_un_rm_ff_op_D ztup3;
};

// struct tuple_(%union zfregidx, %enum zrounding_mode, %union zfregidx, %enum zf_un_rm_ff_op_H)
struct ztuple_z8z5unionz0zzfregidxzCz0z5enumz0zzrounding_modezCz0z5unionz0zzfregidxzCz0z5enumz0zzf_un_rm_ff_op_Hz9 {
  struct zfregidx ztup0;
  enum zrounding_mode ztup1;
  struct zfregidx ztup2;
  enum zf_un_rm_ff_op_H ztup3;
};

// struct tuple_(%union zregidx, %enum zrounding_mode, %union zfregidx, %enum zf_un_rm_xf_op_D)
struct ztuple_z8z5unionz0zzregidxzCz0z5enumz0zzrounding_modezCz0z5unionz0zzfregidxzCz0z5enumz0zzf_un_rm_xf_op_Dz9 {
  struct zregidx ztup0;
  enum zrounding_mode ztup1;
  struct zfregidx ztup2;
  enum zf_un_rm_xf_op_D ztup3;
};

// struct tuple_(%union zregidx, %enum zrounding_mode, %union zfregidx, %enum zf_un_rm_xf_op_S)
struct ztuple_z8z5unionz0zzregidxzCz0z5enumz0zzrounding_modezCz0z5unionz0zzfregidxzCz0z5enumz0zzf_un_rm_xf_op_Sz9 {
  struct zregidx ztup0;
  enum zrounding_mode ztup1;
  struct zfregidx ztup2;
  enum zf_un_rm_xf_op_S ztup3;
};

// union instruction
enum kind_zinstruction { Kind_zF_UN_RM_FF_TYPE_D, Kind_zF_UN_RM_FF_TYPE_H, Kind_zF_UN_RM_XF_TYPE_D, Kind_zF_UN_RM_XF_TYPE_S };

struct zinstruction {
  enum kind_zinstruction kind;
  union {
    struct { struct ztuple_z8z5unionz0zzfregidxzCz0z5enumz0zzrounding_modezCz0z5unionz0zzfregidxzCz0z5enumz0zzf_un_rm_ff_op_Dz9 zF_UN_RM_FF_TYPE_D; };
    struct { struct ztuple_z8z5unionz0zzfregidxzCz0z5enumz0zzrounding_modezCz0z5unionz0zzfregidxzCz0z5enumz0zzf_un_rm_ff_op_Hz9 zF_UN_RM_FF_TYPE_H; };
    struct { struct ztuple_z8z5unionz0zzregidxzCz0z5enumz0zzrounding_modezCz0z5unionz0zzfregidxzCz0z5enumz0zzf_un_rm_xf_op_Dz9 zF_UN_RM_XF_TYPE_D; };
    struct { struct ztuple_z8z5unionz0zzregidxzCz0z5enumz0zzrounding_modezCz0z5unionz0zzfregidxzCz0z5enumz0zzf_un_rm_xf_op_Sz9 zF_UN_RM_XF_TYPE_S; };
  } variants;
};

// union exception
enum kind_zexception { Kind_z__dummy_exnz3 };

struct zexception {
  enum kind_zexception kind;
  union {struct { unit z__dummy_exnz3; };} variants;
};

// enum VectorHalf
enum zVectorHalf { zHigh, zLow };

// enum Signedness
enum zSignedness { zSigned, zUnsigned };

void zspc_forwards(sail_string *rop, unit);

void zopt_spc_forwards(sail_string *rop, unit);

void zdef_spc_forwards(sail_string *rop, unit);

void zsep_forwards(sail_string *rop, unit);

void zsep_forwards_infallible(sail_string *rop, unit);

void create_letbind_0(void);
void kill_letbind_0(void);


void create_letbind_1(void);
void kill_letbind_1(void);


void create_letbind_2(void);
void kill_letbind_2(void);


void create_letbind_3(void);
void kill_letbind_3(void);


void create_letbind_4(void);
void kill_letbind_4(void);


void create_letbind_5(void);
void kill_letbind_5(void);


void create_letbind_6(void);
void kill_letbind_6(void);


void create_letbind_7(void);
void kill_letbind_7(void);


void create_letbind_8(void);
void kill_letbind_8(void);


void create_letbind_9(void);
void kill_letbind_9(void);


void create_letbind_10(void);
void kill_letbind_10(void);


void create_letbind_11(void);
void kill_letbind_11(void);


void create_letbind_12(void);
void kill_letbind_12(void);


void zfrm_mnemonic_forwards(sail_string *rop, enum zrounding_mode);

void zfrm_mnemonic_forwards_infallible(sail_string *rop, enum zrounding_mode);

void zfreg_or_reg_name_forwards(sail_string *rop, struct zfregidx);

void zfreg_or_reg_name_forwards_infallible(sail_string *rop, struct zfregidx);

void zreg_name_forwards(sail_string *rop, struct zregidx);

void zreg_name_forwards_infallible(sail_string *rop, struct zregidx);

void zassembly_forwards(sail_string *rop, struct zinstruction);

void zf_un_rm_ff_type_mnemonic_D_forwards(sail_string *rop, enum zf_un_rm_ff_op_D);

void zf_un_rm_ff_type_mnemonic_D_forwards_infallible(sail_string *rop, enum zf_un_rm_ff_op_D);

void zf_un_rm_xf_type_mnemonic_D_forwards(sail_string *rop, enum zf_un_rm_xf_op_D);

void zf_un_rm_xf_type_mnemonic_D_forwards_infallible(sail_string *rop, enum zf_un_rm_xf_op_D);

void zf_un_rm_ff_type_mnemonic_H_forwards(sail_string *rop, enum zf_un_rm_ff_op_H);

void zf_un_rm_ff_type_mnemonic_H_forwards_infallible(sail_string *rop, enum zf_un_rm_ff_op_H);

void zf_un_rm_xf_type_mnemonic_S_forwards(sail_string *rop, enum zf_un_rm_xf_op_S);

void zf_un_rm_xf_type_mnemonic_S_forwards_infallible(sail_string *rop, enum zf_un_rm_xf_op_S);

void zassembly_forwards_infallible(sail_string *rop, struct zinstruction);

unit zcheck_case(struct zinstruction, const_sail_string, bool);

unit zmain(unit);

unit zinitializze_registers(unit);

extern struct zexception *current_exception;

extern bool have_exception;

extern sail_string *throw_location;



#ifdef __cplusplus
}
#endif
