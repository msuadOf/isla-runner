#ifndef SOFTFLOAT_FAST_INT64
#error "The native oracle requires the same SoftFloat ABI"
#endif
#ifndef THREAD_LOCAL
#error "The native oracle requires the same SoftFloat TLS ABI"
#endif
extern "C" {
#include "softfloat.h"
}
#include <cinttypes>
#include <cstdio>

static void row(const char *name, uint64_t bits) {
  std::printf("%s %016" PRIx64 " %02x\n", name, bits, static_cast<unsigned>(softfloat_exceptionFlags));
}
static void begin(unsigned rm) {
  softfloat_roundingMode = rm;
  softfloat_detectTininess = softfloat_tininess_afterRounding;
  softfloat_exceptionFlags = 0;
}
int main() {
  for (unsigned rm = 0; rm < 5; ++rm) {
    char name[32];
    std::snprintf(name, sizeof(name), "f32_add_rm%u", rm);
    begin(rm);
    row(name, f32_add(float32_t{0x3f800000}, float32_t{0x33800000}).v);
  }
  begin(0); row("f16_add", f16_add(float16_t{0x3c00}, float16_t{0x1000}).v);
  begin(0); row("f64_div", f64_div(float64_t{UINT64_C(0x3ff0000000000000)}, float64_t{UINT64_C(0x4008000000000000)}).v);
  begin(0); auto q = f128_add(float128_t{{1, UINT64_C(0x3fff000000000000)}}, float128_t{{0, UINT64_C(0x3ffe000000000000)}});
  std::printf("f128_add %016" PRIx64 ":%016" PRIx64 " %02x\n", q.v[1], q.v[0], static_cast<unsigned>(softfloat_exceptionFlags));
  begin(0); row("f32_fma", f32_mulAdd(float32_t{0x3f800001}, float32_t{0x3f7fffff}, float32_t{0xbf800000}).v);
  begin(0); row("f32_sqrt", f32_sqrt(float32_t{0x40000000}).v);
  begin(0); row("f32_to_f16", f32_to_f16(float32_t{0x387fe000}).v);
  begin(0); row("f32_to_bf16", f32_to_bf16(float32_t{0x7f7fffff}).v);
  begin(2); row("f64_to_f32", f64_to_f32(float64_t{UINT64_C(0x3ff0000000000001)}).v);
  begin(0); row("i64_to_f32", i64_to_f32(INT64_MIN).v);
  begin(0); row("ui64_to_f64", ui64_to_f64(UINT64_MAX).v);
  begin(1); row("f32_to_ui32", f32_to_ui32(float32_t{0xbe800000}, 1, true));
  begin(0); row("f16_eq_zero", f16_eq(float16_t{0}, float16_t{0x8000}));
  begin(2); row("f32_round_int", f32_roundToInt(float32_t{0x3fc00000}, 2, true).v);
}
