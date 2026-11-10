#include "closure.h"

#include <cinttypes>
#include <cstdio>

static void row(const char *name, uint64_t bits) {
  std::printf("%s %016" PRIx64 "\n", name, bits);
}

int main() {
  model::Model m;
  m.model_init();
  for (unsigned rm = 0; rm < 5; ++rm) {
    char name[32];
    std::snprintf(name, sizeof(name), "f32_add_rm%u", rm);
    row(name, m.zprobe_fp32_add(rm, float32_t{0x3f800000}, float32_t{0x33800000}).v);
  }
  row("f16_add", m.zprobe_fp16_add(0, float16_t{0x3c00}, float16_t{0x1000}).v);
  row("f64_div", m.zprobe_fp64_div(0, float64_t{UINT64_C(0x3ff0000000000000)}, float64_t{UINT64_C(0x4008000000000000)}).v);
  auto q = m.zprobe_fp128_add(0, float128_t{{1, UINT64_C(0x3fff000000000000)}}, float128_t{{0, UINT64_C(0x3ffe000000000000)}});
  std::printf("f128_add %016" PRIx64 ":%016" PRIx64 "\n", q.v[1], q.v[0]);
  row("f32_fma", m.zprobe_fp32_fma(0, float32_t{0x3f800001}, float32_t{0x3f7fffff}, float32_t{0xbf800000}).v);
  row("f32_sqrt", m.zprobe_fp32_sqrt(0, float32_t{0x40000000}).v);
  row("f32_to_f16", m.zprobe_fp32_to_fp16(0, float32_t{0x387fe000}).v);
  row("f32_to_bf16", m.zprobe_fp32_to_bf16(0, float32_t{0x7f7fffff}));
  row("f64_to_f32", m.zprobe_fp64_to_fp32(2, float64_t{UINT64_C(0x3ff0000000000001)}).v);
  row("i64_to_f32", m.zprobe_fp32_from_signed_64(0, UINT64_C(0x8000000000000000)).v);
  row("ui64_to_f64", m.zprobe_fp64_from_unsigned_64(0, UINT64_C(0xffffffffffffffff)).v);
  row("f32_to_ui32", m.zprobe_fp32_to_unsigned32(1, float32_t{0xbe800000}));
  row("f16_eq_zero", m.zprobe_fp16_eq(float16_t{0}, float16_t{0x8000}));
  row("f32_round_int", m.zprobe_fp32_round_to_integral(2, float32_t{0x3fc00000}).v);
  m.model_fini();
}
