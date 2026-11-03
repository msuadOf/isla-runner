#include "sail_riscv_model.h"
#include "sail_softfloat.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <random>
int main(int argc,char**argv) {
 std::ifstream f(argv[1]); std::string config((std::istreambuf_iterator<char>(f)),{});
 sail_config_set_string(config.c_str()); hart::Model model; model.model_init();
 std::mt19937_64 rng(20261021); unsigned cases=0,failed=0;
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint16_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f16Add(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f16_add(float16_t{a}, float16_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7c00)==0x7c00 && (bits & 0x3ff)) bits=0x7e00;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f16Add rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint16_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f16Sub(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f16_sub(float16_t{a}, float16_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7c00)==0x7c00 && (bits & 0x3ff)) bits=0x7e00;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f16Sub rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint16_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f16Mul(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f16_mul(float16_t{a}, float16_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7c00)==0x7c00 && (bits & 0x3ff)) bits=0x7e00;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f16Mul rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint16_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f16Div(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f16_div(float16_t{a}, float16_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7c00)==0x7c00 && (bits & 0x3ff)) bits=0x7e00;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f16Div rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint16_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f16Sqrt(rm,a);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f16_sqrt(float16_t{a}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7c00)==0x7c00 && (bits & 0x3ff)) bits=0x7e00;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f16Sqrt rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint16_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f16MulAdd(rm,a, b, c);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f16_mulAdd(float16_t{a}, float16_t{b}, float16_t{c}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7c00)==0x7c00 && (bits & 0x3ff)) bits=0x7e00;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f16MulAdd rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint32_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f32Add(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f32_add(float32_t{a}, float32_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7f800000)==0x7f800000 && (bits & 0x7fffff)) bits=0x7fc00000;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f32Add rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint32_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f32Sub(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f32_sub(float32_t{a}, float32_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7f800000)==0x7f800000 && (bits & 0x7fffff)) bits=0x7fc00000;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f32Sub rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint32_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f32Mul(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f32_mul(float32_t{a}, float32_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7f800000)==0x7f800000 && (bits & 0x7fffff)) bits=0x7fc00000;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f32Mul rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint32_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f32Div(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f32_div(float32_t{a}, float32_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7f800000)==0x7f800000 && (bits & 0x7fffff)) bits=0x7fc00000;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f32Div rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint32_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f32Sqrt(rm,a);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f32_sqrt(float32_t{a}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7f800000)==0x7f800000 && (bits & 0x7fffff)) bits=0x7fc00000;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f32Sqrt rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint32_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f32MulAdd(rm,a, b, c);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f32_mulAdd(float32_t{a}, float32_t{b}, float32_t{c}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & 0x7f800000)==0x7f800000 && (bits & 0x7fffff)) bits=0x7fc00000;
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f32MulAdd rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint64_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f64Add(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f64_add(float64_t{a}, float64_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & UINT64_C(0x7ff0000000000000))==UINT64_C(0x7ff0000000000000) && (bits & UINT64_C(0x000fffffffffffff))) bits=UINT64_C(0x7ff8000000000000);
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f64Add rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint64_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f64Sub(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f64_sub(float64_t{a}, float64_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & UINT64_C(0x7ff0000000000000))==UINT64_C(0x7ff0000000000000) && (bits & UINT64_C(0x000fffffffffffff))) bits=UINT64_C(0x7ff8000000000000);
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f64Sub rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint64_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f64Mul(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f64_mul(float64_t{a}, float64_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & UINT64_C(0x7ff0000000000000))==UINT64_C(0x7ff0000000000000) && (bits & UINT64_C(0x000fffffffffffff))) bits=UINT64_C(0x7ff8000000000000);
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f64Mul rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint64_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f64Div(rm,a, b);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f64_div(float64_t{a}, float64_t{b}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & UINT64_C(0x7ff0000000000000))==UINT64_C(0x7ff0000000000000) && (bits & UINT64_C(0x000fffffffffffff))) bits=UINT64_C(0x7ff8000000000000);
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f64Div rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint64_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f64Sqrt(rm,a);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f64_sqrt(float64_t{a}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & UINT64_C(0x7ff0000000000000))==UINT64_C(0x7ff0000000000000) && (bits & UINT64_C(0x000fffffffffffff))) bits=UINT64_C(0x7ff8000000000000);
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f64Sqrt rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
for(unsigned rm=0;rm<5;rm++) for(unsigned i=0;i<2000;i++) {
 uint64_t a=rng(), b=rng(), c=rng();
 auto actual=model.zriscv_f64MulAdd(rm,a, b, c);
 softfloat_roundingMode=rm;softfloat_detectTininess=softfloat_tininess_afterRounding;softfloat_exceptionFlags=0;
 auto expected=f64_mulAdd(float64_t{a}, float64_t{b}, float64_t{c}); unsigned flags=softfloat_exceptionFlags;
 auto bits=expected.v; if((bits & UINT64_C(0x7ff0000000000000))==UINT64_C(0x7ff0000000000000) && (bits & UINT64_C(0x000fffffffffffff))) bits=UINT64_C(0x7ff8000000000000);
 cases++; if(actual.ztup0!=flags || actual.ztup1!=bits){
 if(failed++<30) std::cout<<"FAIL f64MulAdd rm="<<rm<<" a="<<std::hex<<uint64_t(a)<<" b="<<uint64_t(b)<<" c="<<uint64_t(c)<<" got="<<actual.ztup0<<","<<actual.ztup1<<" expected="<<flags<<","<<uint64_t(bits)<<std::dec<<"\n";
 }
}
std::cout<<"cases="<<cases<<" failed="<<failed<<"\n";model.model_fini();return failed?1:0;}
