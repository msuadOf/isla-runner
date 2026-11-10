#include "closure.h"
#include "sail_softfloat.h"

#include <cassert>
#include <cstdint>
#include <cstdio>
#include <initializer_list>

static bool same(float16_t a, float16_t b) { return a.v == b.v; }
static bool same(float32_t a, float32_t b) { return a.v == b.v; }
static bool same(float64_t a, float64_t b) { return a.v == b.v; }
static bool same(float128_t a, float128_t b) {
  return a.v[0] == b.v[0] && a.v[1] == b.v[1];
}

static void set_bits(lbits *b, unsigned width, unsigned value) {
  b->len = width;
  mpz_set_ui(*b->bits, value);
}

int main() {
  model::Model m;
  m.model_init();
  softfloat_roundingMode = softfloat_round_min;
  softfloat_detectTininess = softfloat_tininess_beforeRounding;
  softfloat_exceptionFlags = 0x15;
  lbits raw, out;
  CREATE(lbits)(&raw);
  CREATE(lbits)(&out);

#define CHECK_FROM(N) \
  assert(same(m.zprobe_fp##N##_from_signed_1(0, 1), i32_to_f##N(-1))); \
  assert(same(m.zprobe_fp##N##_from_unsigned_1(0, 1), ui32_to_f##N(1))); \
  assert(same(m.zprobe_fp##N##_from_signed_33(0, 42), i32_to_f##N(42))); \
  assert(same(m.zprobe_fp##N##_from_unsigned_33(0, 42), ui32_to_f##N(42))); \
  for (unsigned width : {65u, 113u, 129u, 1024u}) { \
    set_bits(&raw, width, 42); \
    switch (width) { \
      case 65: \
        assert(same(m.zprobe_fp##N##_from_signed_65(0, raw), i32_to_f##N(42))); \
        assert(same(m.zprobe_fp##N##_from_unsigned_65(0, raw), ui32_to_f##N(42))); \
        break; \
      case 113: \
        assert(same(m.zprobe_fp##N##_from_signed_113(0, raw), i32_to_f##N(42))); \
        assert(same(m.zprobe_fp##N##_from_unsigned_113(0, raw), ui32_to_f##N(42))); \
        break; \
      case 129: \
        assert(same(m.zprobe_fp##N##_from_signed_129(0, raw), i32_to_f##N(42))); \
        assert(same(m.zprobe_fp##N##_from_unsigned_129(0, raw), ui32_to_f##N(42))); \
        break; \
      case 1024: \
        assert(same(m.zprobe_fp##N##_from_signed_1024(0, raw), i32_to_f##N(42))); \
        assert(same(m.zprobe_fp##N##_from_unsigned_1024(0, raw), ui32_to_f##N(42))); \
        break; \
    } \
  }
  CHECK_FROM(16)
  CHECK_FROM(32)
  CHECK_FROM(64)
  CHECK_FROM(128)
#undef CHECK_FROM

  // A 65-bit input with only bit 64 set detects accidental low-word truncation.
  raw.len = 65;
  mpz_set_ui(*raw.bits, 0);
  mpz_setbit(*raw.bits, 64);
  assert(m.zprobe_fp16_from_unsigned_65(0, raw).v == 0x7c00);
  assert(m.zprobe_fp16_from_signed_65(0, raw).v == 0xfc00);
  assert(m.zprobe_fp32_from_unsigned_65(0, raw).v == 0x5f800000);
  assert(m.zprobe_fp32_from_signed_65(0, raw).v == 0xdf800000);
  assert(m.zprobe_fp64_from_unsigned_65(0, raw).v == UINT64_C(0x43f0000000000000));
  assert(m.zprobe_fp64_from_signed_65(0, raw).v == UINT64_C(0xc3f0000000000000));
  assert(m.zprobe_fp128_from_unsigned_65(0, raw).v[1] == UINT64_C(0x403f000000000000));
  assert(m.zprobe_fp128_from_signed_65(0, raw).v[1] == UINT64_C(0xc03f000000000000));

#define CHECK_TO(N, ONE_HALF) \
  for (unsigned rm = 0; rm < 5; ++rm) { \
    const unsigned expected = (rm == 1 || rm == 2) ? 1 : 2; \
    assert(m.zprobe_fp##N##_to_signed16(rm, ONE_HALF) == expected); \
    assert(m.zprobe_fp##N##_to_unsigned16(rm, ONE_HALF) == expected); \
    m.zprobe_fp##N##_to_signed128(&out, rm, ONE_HALF); \
    assert(out.len == 128 && mpz_cmp_ui(*out.bits, expected) == 0); \
    m.zprobe_fp##N##_to_unsigned128(&out, rm, ONE_HALF); \
    assert(out.len == 128 && mpz_cmp_ui(*out.bits, expected) == 0); \
  }
  CHECK_TO(16, (float16_t{0x3e00}))
  CHECK_TO(32, (float32_t{0x3fc00000}))
  CHECK_TO(64, (float64_t{UINT64_C(0x3ff8000000000000)}))
  CHECK_TO(128, (float128_t{{0, UINT64_C(0x3fff800000000000)}}))
#undef CHECK_TO

  const float128_t q{{UINT64_C(0x123456789abcdef0), UINT64_C(0x3fff800000000000)}};
  m.zprobe_fp128_to_ieee(&out, q);
  assert(out.len == 128 && mpz_get_ui(*out.bits) == q.v[0]);
  mpz_t high;
  mpz_init(high);
  mpz_fdiv_q_2exp(high, *out.bits, 64);
  assert(mpz_get_ui(high) == q.v[1]);
  const float128_t nan{{0xbeef, UINT64_C(0xffff000000000000)}};
  m.zprobe_fp128_to_ieee(&out, nan);
  assert(mpz_get_ui(*out.bits) == 0);
  mpz_fdiv_q_2exp(high, *out.bits, 64);
  assert(mpz_get_ui(high) == UINT64_C(0x7fff800000000000));
  mpz_clear(high);

  assert(m.zprobe_fp128_is_nan(nan));
  assert(!m.zprobe_fp128_is_nan(q));
  for (unsigned rm = 0; rm < 5; ++rm) {
    const unsigned expected = (rm == 1 || rm == 2) ? 1 : 2;
    const float128_t rounded = m.zprobe_fp128_round_to_integral(rm, float128_t{{0, UINT64_C(0x3fff800000000000)}});
    assert(same(rounded, expected == 1 ? float128_t{{0, UINT64_C(0x3fff000000000000)}}
                                       : float128_t{{0, UINT64_C(0x4000000000000000)}}));
    assert(m.zprobe_fp128_to_signed32(rm, q) == expected);
    assert(m.zprobe_fp128_to_unsigned32(rm, q) == expected);
    assert(m.zprobe_fp128_to_signed64(rm, q) == expected);
    assert(m.zprobe_fp128_to_unsigned64(rm, q) == expected);
  }
  (void)m.zprobe_fp128_to_signed32(0, nan);
  (void)m.zprobe_fp128_to_unsigned64(0, nan);
  assert(m.zprobe_fp128_to_signed32(0, i32_to_f128(INT32_MIN)) == UINT32_C(0x80000000));
  assert(m.zprobe_fp128_to_signed64(0, i64_to_f128(INT64_MIN)) == UINT64_C(0x8000000000000000));
  assert(m.zprobe_fp128_to_unsigned32(0, ui32_to_f128(UINT32_MAX)) == UINT32_MAX);
  assert(m.zprobe_fp128_to_unsigned64(0, ui64_to_f128(UINT64_MAX)) == UINT64_MAX);
  assert(m.zprobe_fp16_abs(float16_t{0xbc00}).v == 0x3c00);
  assert(m.zprobe_fp16_gt(float16_t{0x3e00}, float16_t{0x3d00}));
  assert(m.zprobe_fp16_gteq(float16_t{0x3e00}, float16_t{0x3e00}));
  assert(!m.zprobe_fp16_gt(float16_t{0x7e00}, float16_t{0x3c00}));
  assert(m.zprobe_fp16_is_negative(float16_t{0x8000}));
  assert(!m.zprobe_fp16_is_negative(float16_t{0xfe00}));

  assert(softfloat_roundingMode == softfloat_round_min);
  assert(softfloat_detectTininess == softfloat_tininess_beforeRounding);
  assert(softfloat_exceptionFlags == 0x15);
  KILL(lbits)(&raw);
  KILL(lbits)(&out);
  m.model_fini();
  std::puts("public wide 17 + polymorphic widths + 10 symmetric native entries: PASS");
}
