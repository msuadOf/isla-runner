#include "closure.h"
#include "sail_softfloat.h"

#include <cassert>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <thread>
#include <vector>

static void sentinel() {
  assert(softfloat_roundingMode == softfloat_round_max);
  assert(softfloat_detectTininess == softfloat_tininess_beforeRounding);
  assert(softfloat_exceptionFlags == 0x15);
}

int main() {
  model::Model model;
  model.model_init();
  softfloat_roundingMode = softfloat_round_max;
  softfloat_detectTininess = softfloat_tininess_beforeRounding;
  softfloat_exceptionFlags = 0x15;

  assert(model.zprobe_round_nearest_ties_to_even(UNIT) == 0);
  assert(model.zprobe_round_toward_zzero(UNIT) == 1);
  assert(model.zprobe_round_toward_negative(UNIT) == 2);
  assert(model.zprobe_round_toward_positive(UNIT) == 3);
  assert(model.zprobe_round_nearest_ties_to_away(UNIT) == 4);
  assert(model.zprobe_fp32_add(0, float32_t{0x3f800000}, float32_t{0x40000000}).v == 0x40400000);
  sentinel();

  float32_t qnan{0x7fc00001}, snan{0xff800001}, pzero{0}, nzero{0x80000000};
  assert(eq_float32(qnan, snan));
  assert(!eq_float32(pzero, nzero));
  assert(model.zprobe_generic_eq32(qnan, snan));
  assert(!model.zprobe_generic_neq32(qnan, snan));
  assert(!model.zprobe_generic_eq32(pzero, nzero));
  assert(model.zprobe_generic_neq32(pzero, nzero));
  assert(!model.zprobe_fp32_eq(qnan, qnan));
  assert(model.zprobe_fp32_eq(pzero, nzero));
  assert(model.zprobe_ite_float32(true, pzero, nzero).v == 0);
  assert(model.zprobe_ite_float32(false, pzero, nzero).v == 0x80000000);
  for (int a = 0; a < 2; ++a) for (int b = 0; b < 2; ++b) {
    assert(model.zprobe_strict_and_bool(a, b) == (a && b));
    assert(model.zprobe_strict_or_bool(a, b) == (a || b));
  }
  assert(model.zprobe_isla_bool_to_bit(false) == 0);
  assert(model.zprobe_isla_bool_to_bit(true) == 1);
  assert(model.zprobe_fp32_to_ieee(qnan) == 0x7fc00000);
  assert(model.zprobe_fp32_to_ieee(snan) == 0x7fc00000);
  assert(!model.zprobe_fp32_is_negative(snan));
  assert(model.zprobe_fp16_from_ieee(UINT64_C(0xffff000000000001)).v == 1);
  assert(model.zprobe_fp32_from_ieee(UINT64_C(0xffff00003f800000)).v == 0x3f800000);
  assert(model.zprobe_fp16_to_ieee(float16_t{0x8000}) == 0x8000);
  assert(model.zprobe_fp32_to_bf16(0, float32_t{0x3f800000}) == 0x3f80);
  assert(model.zprobe_fp32_to_fp16(0, float32_t{0x387fe000}).v == 0x0400);
  sentinel();

  assert(model.zprobe_fp32_from_signed_32(0, UINT32_C(0xffffffff)).v == 0xbf800000);
  assert(model.zprobe_fp32_from_signed_64(0, UINT64_C(0x8000000000000000)).v == 0xdf000000);
  assert(model.zprobe_fp32_from_unsigned_64(0, UINT64_C(0xffffffffffffffff)).v == 0x5f800000);
  assert(model.zprobe_fp32_to_unsigned32(1, float32_t{0xbe800000}) == 0);
  assert(model.zprobe_fp32_to_signed32(0, float32_t{0xbf800000}) == UINT32_C(0xffffffff));
  (void)model.zprobe_fp32_to_signed32(0, qnan);
  (void)model.zprobe_fp32_to_signed64(0, float32_t{0x7f800000});
  const float16_t invalid16[] = {{0x7e01}, {0xfe01}, {0x7c00}, {0xfc00}, {0x7bff}, {0xfbff}};
  const float32_t invalid32[] = {{0x7fc00001}, {0xff800001}, {0x7f800000},
                                 {0xff800000}, {0x7f7fffff}, {0xff7fffff}};
  const float64_t invalid64[] = {{UINT64_C(0x7ff8000000000001)},
                                 {UINT64_C(0xfff0000000000001)},
                                 {UINT64_C(0x7ff0000000000000)},
                                 {UINT64_C(0xfff0000000000000)},
                                 {UINT64_C(0x7fefffffffffffff)},
                                 {UINT64_C(0xffefffffffffffff)}};
  for (int i = 0; i < 6; ++i) {
    (void)model.zprobe_fp16_to_signed32(0, invalid16[i]);
    (void)model.zprobe_fp16_to_unsigned32(0, invalid16[i]);
    (void)model.zprobe_fp16_to_signed64(0, invalid16[i]);
    (void)model.zprobe_fp16_to_unsigned64(0, invalid16[i]);
    (void)model.zprobe_fp32_to_signed32(0, invalid32[i]);
    (void)model.zprobe_fp32_to_unsigned32(0, invalid32[i]);
    (void)model.zprobe_fp32_to_signed64(0, invalid32[i]);
    (void)model.zprobe_fp32_to_unsigned64(0, invalid32[i]);
    (void)model.zprobe_fp64_to_signed32(0, invalid64[i]);
    (void)model.zprobe_fp64_to_unsigned32(0, invalid64[i]);
    (void)model.zprobe_fp64_to_signed64(0, invalid64[i]);
    (void)model.zprobe_fp64_to_unsigned64(0, invalid64[i]);
  }
  assert(model.zprobe_fp32_to_unsigned32(0, invalid32[0]) ==
         model.zprobe_fp32_to_unsigned32(0, invalid32[1]));
  sentinel();

  lbits wide;
  CREATE(lbits)(&wide);
  wide.len = 128;
  assert(mpz_set_str(*wide.bits, "4000123456789abcdef0123456789abc", 16) == 0);
  float128_t f128 = model.zprobe_fp128_from_ieee(wide);
  assert(f128.v[0] == UINT64_C(0xdef0123456789abc));
  assert(f128.v[1] == UINT64_C(0x4000123456789abc));
  assert(model.zprobe_fp128_add(0, f128, float128_t{{0, 0}}).v[1] == f128.v[1]);
  KILL(lbits)(&wide);
  sentinel();

  lbits wide_a, wide_b, wide_out;
  CREATE(lbits)(&wide_a);
  CREATE(lbits)(&wide_b);
  CREATE(lbits)(&wide_out);
  wide_a.len = wide_b.len = 128;
  assert(mpz_set_str(*wide_a.bits, "abcdef01234567890000000000000001", 16) == 0);
  assert(mpz_set_str(*wide_b.bits, "0123456789abcdef0000000000000002", 16) == 0);
  model.zprobe_ite(&wide_out, false, wide_a, wide_b);
  assert(wide_out.len == 128 && mpz_cmp(*wide_out.bits, *wide_b.bits) == 0);
  KILL(lbits)(&wide_a);
  KILL(lbits)(&wide_b);
  KILL(lbits)(&wide_out);

  model::zprobe_record rec_a, rec_b, rec_out;
  CREATE(lbits)(&rec_a.zraw);
  CREATE(lbits)(&rec_b.zraw);
  CREATE(lbits)(&rec_out.zraw);
  rec_a.zraw.len = rec_b.zraw.len = 128;
  assert(mpz_set_str(*rec_a.zraw.bits, "abcdef01234567890000000000000001", 16) == 0);
  mpz_set(*rec_b.zraw.bits, *rec_a.zraw.bits);
  rec_a.zvalue = float32_t{0x7fc00001};
  rec_b.zvalue = float32_t{0xff800001};
  assert(model.zprobe_eq_record(rec_a, rec_b));
  model.zprobe_ite_record(&rec_out, false, rec_a, rec_b);
  assert(rec_out.zvalue.v == rec_b.zvalue.v);
  assert(rec_out.zraw.len == 128 && mpz_cmp(*rec_out.zraw.bits, *rec_b.zraw.bits) == 0);
  mpz_set_ui(*rec_b.zraw.bits, 42);
  assert(mpz_cmp(*rec_out.zraw.bits, *rec_b.zraw.bits) != 0);
  KILL(lbits)(&rec_a.zraw);
  KILL(lbits)(&rec_b.zraw);
  KILL(lbits)(&rec_out.zraw);

  {
    sail_softfloat::Scope outer(softfloat_round_min);
    assert(softfloat_roundingMode == softfloat_round_min);
    softfloat_exceptionFlags = 0x04;
    (void)model.zprobe_fp32_sqrt(softfloat_round_near_even, float32_t{0x40000000});
    assert(softfloat_roundingMode == softfloat_round_min);
    assert(softfloat_exceptionFlags == 0x04);
  }
  sentinel();

  std::atomic<int> entered{0}, checked{0};
  std::vector<std::thread> threads;
  for (int id = 0; id < 4; ++id) {
    threads.emplace_back([id, &entered, &checked]() {
      softfloat_roundingMode = softfloat_round_max;
      softfloat_detectTininess = softfloat_tininess_beforeRounding;
      softfloat_exceptionFlags = static_cast<uint_fast8_t>(0x10 + id);
      {
        sail_softfloat::Scope scope(static_cast<uint_fast8_t>(id));
        softfloat_exceptionFlags = static_cast<uint_fast8_t>(id + 1);
        ++entered;
        while (entered.load() < 4) std::this_thread::yield();
        assert(softfloat_roundingMode == static_cast<uint_fast8_t>(id));
        assert(softfloat_detectTininess == softfloat_tininess_afterRounding);
        assert(softfloat_exceptionFlags == static_cast<uint_fast8_t>(id + 1));
        ++checked;
        while (checked.load() < 4) std::this_thread::yield();
      }
      assert(softfloat_roundingMode == softfloat_round_max);
      assert(softfloat_detectTininess == softfloat_tininess_beforeRounding);
      assert(softfloat_exceptionFlags == 0x10 + id);
    });
  }
  for (auto &t : threads) t.join();
  threads.clear();
  for (int id = 0; id < 4; ++id) {
    threads.emplace_back([id]() {
      model::Model local;
      softfloat_roundingMode = (id & 1) ? softfloat_round_min : softfloat_round_max;
      softfloat_detectTininess = softfloat_tininess_beforeRounding;
      softfloat_exceptionFlags = static_cast<uint_fast8_t>(0x10 + id);
      for (int n = 0; n < 2000; ++n) {
        const auto rm = (n & 1) ? softfloat_round_min : softfloat_round_max;
        const auto expected = (rm == softfloat_round_min) ? 0x3f800000u : 0x3f800001u;
        const auto got = local.zprobe_fp32_add(rm, float32_t{0x3f800000}, float32_t{1});
        assert(got.v == expected);
        assert(softfloat_roundingMode == ((id & 1) ? softfloat_round_min : softfloat_round_max));
        assert(softfloat_detectTininess == softfloat_tininess_beforeRounding);
        assert(softfloat_exceptionFlags == 0x10 + id);
        if ((n & 31) == 0) std::this_thread::yield();
      }
    });
  }
  for (auto &t : threads) t.join();
  sentinel();
#include "all_calls.inc"
  model.model_fini();
  std::puts("closure generated-call, numeric, nested scope, TLS: PASS");
}
