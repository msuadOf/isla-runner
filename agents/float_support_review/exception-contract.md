# 浮点实施接口与异常契约

> 2026-09-26 接续接口修订：按用户要求复用既有 Sail 类型，最终共享异常编码复用 `fp_exception_flags`；性能对照后保留局部五Bool事实结构，仅在出口打包一次；共享位序 NV0/DZ1/OF2/UF3/NX4，仅在 ISA 包装转换成 RISC-V flags。直接使用 `float_rounding_mode`，分类复用 `float_bits`/`float_decompose`。本文原RM别名等接口描述保留原设计时点，record为经性能验证后保留的内部表示，现行接口与验证门槛见[类型复用审定](type-reuse-architecture.md)和[实施记录](implementation.md)。

日期：2026-09-26。本文由 Astra xhigh 审定，供 [实施计划](plan.md) A–D 阶段派发实现；职责边界沿用 [设计说明](refactoring-plan.md) 和 [逐项参考表](reference-list.md)。

**状态：接口及下述数学算法已明确，可按本文实现；完整 Sail 编译、Isla 求解、SoftFloat 差分和性能仍待验证。第 5 节的 f32→f16 下溢边界已用固定 SoftFloat 动态核对 80 项，通过仅限这些 oracle 样本，本文不是浮点实施整体 PASS。** 本文中的“证明”指基于 IEEE 正确舍入语义的推导及格式界限论证，不表示对 Z3、编译器或所生成程序完成了形式验证。实现若不满足这里的前提，不能沿用结论。

## 1. A 阶段：通用原语契约

保留现有 73 个名称的数值映射。FP 表示继续用 `Val::Symbolic`，底层 Z3 Float sort 承担值语义；不增加 host float 表示。基础映射见 `isla/isla-lib/src/primop/float.rs` 和 `isla/isla-lib/src/smt.rs`。

| 接口 | 输入、输出 | 必须检查与保证 |
| --- | --- | --- |
| `fp16/32/64/128_from_ieee` | 对应宽度 BV → FP | 接受具体 Bits、符号 BV、MixedBits；实际位宽必须分别为 16/32/64/128；按编码重解释，不作整数转换 |
| `fp16/32/64/128_from_signed/unsigned` | `(RM, BV(n)) → FP` | `n > 0`，同样接受三种 BV 表示；signed 按补码解释，unsigned 用独立无符号 Z3 转换 |
| 新 `fp16/32/64/128_to_ieee` | 同格式 FP → BV | 检查输入实际格式，输出宽度由该格式确定；NaN 不保证恢复原 payload、sign 或 signaling 信息 |
| 既有 `fp_to_signed16/32/64/128` | `(RM, 任意 FP) → BV(W)` | 后缀是目标整数宽度；仅有效转换域有数值契约，NaN/超范围域由模型屏蔽 |
| 新 `fp_to_unsigned16/32/64/128` | 同上，无符号转换 | 对称提供四个宽度，四项均须测试；不得加入 RISC-V 无效返回规则 |
| 新 `fp32_to_bf16` | `(RM, FP32) → BV(16)` | 输入实际格式必须 `(8,24)`；内部依次原生 Convert `(8,8)`、ToIEEE `(8,8)`；不返回 flags，不规定 canonical NaN |
| 通用 FP 一元/二元/FMA | 既有签名 | 每个 FP 参数必须确为 Float sort，二元和 FMA 全部 FP 参数同格式；分类结果为 Bool |
| 五个 RM 构造及用 RM 的操作 | `unit → RM` 及既有签名 | RM 参数实际 sort 必须是 RoundingMode，不能因是 Symbolic 就接受 Bool/BV/FP |

格式固定为 f16 `(5,11)`、f32 `(8,24)`、f64 `(11,53)`、f128 `(15,113)`；BF16 是 `(8,8)`，不能用 f16 替代。BF16 暂不增加 Sail/IR 的公开 FP 类型，最小位串出口足够供本模型使用。

BV 到 SMT 表达式复用 `primop_util::smt_value`。MixedBits 应在建立 Concat 之前检查：非空、每段为非零宽度 BV、符号段实际为 BV，累加宽度正确。不能将 FP/Bool 片段先送入 Z3 再期待它报错。已有 `Solver::length/is_bitvector` 能处理部分检查；若需新增 sort 查询，沿 `smt.rs` 的 Z3 sort 查询封装最小能力，不另建一套类型推导系统。

错误调用返回现有 `ExecError::Type`，携带操作名及源位置；参数个数、sort、位宽错误不能 fallback 或强行转换。不可能出现的内部丢失 symbol 等不变量失败可以直接 panic。FP/整数转换的数值无效域属于 SMT 操作正常定义域中的未指定结果，必须由模型选择返回值，不能当成 Rust 类型错误。

Sail 声明文件在 SYMBOLIC 下使用 `$sail_internal` 和 `float_rounding_mode`，可命名本地别名 `ieee_rounding_mode`。不能直接引入定义同名 `rounding_mode` 的旧 `<float.sail>`，以免与 RISC-V 枚举冲突。按 FP 源格式区分的 Sail 函数名可共用 `fp_to_signedW/unsignedW` extern 名称。未知 FP 构造保持 impure。通用 `ite(condition, true_value, false_value)` 复用既有接口，实参同型且均为纯值。

## 2. B 阶段：双后端与最小编译门槛

`isla/isla-sail/sail_plugin_isla.ml` 的 `remove_extern_impls` 只收集 **Isla 所接收 Jib 中实际带 extern 的声明** 并删除同名函数体，不能从源文件有 cpp/lem 绑定推断它一定被删除。2026-09-26 的隔离实验已证实：当前插件和 Sail 0.20.1 对 cpp/lem-only 声明加 SYMBOLIC 同名函数体，在 Isla IR 中保留无 extern 的 val 和普通 fn；C++ 生成代码仍调用 cpp extern。

据此采用原计划的最小模型侧结构：

```sail
val helper = pure {cpp: "原绑定", lem: "原绑定"} : (参数类型) -> 返回类型

$ifdef SYMBOLIC
function helper(参数) = 实现
$endif
```

保留原签名及 cpp/lem 绑定，仅在 SYMBOLIC 分支添加函数体，不条件化 val、不改插件。B 阶段对真实比较 helper 再验证；D 对全部迁移 helper 逐名核对 IR，尚未完成异常的正式 helper 不提前切换。插件不加入 RISC-V 白名单，也不全局更改 extern 实现保留规则。

初始静态审查曾将 `remove_extern_impls` 扩大解释为所有后端 extern 都会删函数体，因此建议条件化 val；该判断现由上述实验修正。复核的 fixture 源 SHA256 为 `ec1d0bb6da9ad34b22b3d8600d9d5882e0d840732eaf53e62f7fcc9a77749cb2`，IR 为 `46eb2530ffc625b2981f89b20c64272eb23ba62b84040352138b4d3e24a72de0`，C++ 为 `41098d5a89b2265e84a77d16a18194e2437214183ff95dc883e413736742d7f2`。源码使用 `val demo_extern = pure {cpp: "demo_cpp", lem: "demo_lem"}`，SYMBOLIC 函数体原样返回 bits8；IR 有 `fn zdemo_extern`，C++ 调用 `demo_cpp`。本结果仅证明该声明/函数体组合可保留，不代表完整浮点数值或全部正式 helper 已通过。

B 门槛如下：

1. 完整 quiet Eq 或 signaling Lt/Le 示例生成普通 IR 函数体，内部使用原生 FP 比较和通用纯 ITE；测试结果和五 flags。
2. 不同名 `demo_f32_add_bits` 只返回 bits，验证原生加法调用及数值结果；不得给正式 `riscv_f32Add` 安装缺少精确 flags 的实现。
3. BF16 的 `RM,FP32 → BV16` 声明可编译，实际 IR 调用正确的通用原语。
4. 同一 fixture 的 C++ 分支仍调用原 SoftFloat extern；SYMBOLIC 的 native FP 类型不泄入该分支。
5. IR 静态检查、`trace_functions` 和运行记录同时证明进入普通函数体；纯值选择无新增数据分叉。不用全局 linearize 消去断言。

## 3. 共享异常库的输入和输出

共享函数保留原始操作数位串，用于 NaN、sNaN、zero、infinity 和原 sign 判定；数值计算交给通用 Z3 FP 原语。共享异常结果为五个独立布尔值：invalid、divide_by_zero、overflow、underflow、inexact。RISC-V 包装再打包 `NV/DZ/OF/UF/NX` 为 bit4/3/2/1/0，并选择该 ISA 的结果位。

普通运算的输入舍入模式为 RNE、RTZ、RTN、RTP、RMM；这五者映射五个原生 RM。只有 `f32→f16` 和 `f64→f32` 的 RVV ROD 窄化在对应包装接收编码 6。普通指令的保留编码、dynamic frm 和合法性仍由已有架构路径处理，不能用 solver 断言静默删除非法状态。

共享库首版只承诺 RISC-V 使用的 after-rounding tininess。五 flags 按下文给出的条件计算，不公开尚未实现的 before-rounding 策略。

## 4. 定向邻点：精确 NX 和阈值比较

设有效有限输入的精确实数结果为 `z`，目标格式结果为 `r`。数值主体始终调用目标格式原生 Add/Sub/Mul/Div/Sqrt/FMA。另将原始输入无损拓宽到工作格式，在该格式以同一个原生操作计算：

```text
lo = operation(RTN, widened_original_operands)
hi = operation(RTP, widened_original_operands)
rw = exact_widen(r)
```

FMA 的辅助计算也必须是原生 FMA，不能拆乘加。工作格式的指数足以容纳所有非零精确结果，且目标结果和下节阈值可在工作格式精确表示。

IEEE 定向舍入使 `lo`、`hi` 分别为包围 `z` 的相邻可表示值，或者同时等于 `z`。因此：

```text
z == rw  当且仅当 fp.eq(lo,rw) AND fp.eq(hi,rw)
NX       = NOT (fp.eq(lo,rw) AND fp.eq(hi,rw))
```

`r` 为目标 infinity 时，工作格式的有限邻点不等于 `rw`，故 NX 自然为真。正负零使用 `fp.eq` 比较；精确零的不同符号不产生 NX。

任一能在工作格式精确表示的阈值 `T` 满足：

| 精确条件 | 可计算的等价条件 |
| --- | --- |
| `z < T` | `lo < T` |
| `z <= T` | `hi <= T` |
| `z > T` | `hi > T` |
| `z >= T` | `lo >= T` |

证明关键在于 `T` 自身可表示：定向舍入不会越过它。该方法不假设更宽浮点能精确表示任意加法、除法或平方根，因而不会漏掉极大指数差造成的微小余项。

对绝对值 `m=abs(z)`，令 `l=min(abs(lo),abs(hi))`、`h=max(abs(lo),abs(hi))`，即可用 `l/h` 替换上表中的 `lo/hi` 比较 `m`。这里只需要有限数值的 min/max，正负零的位编码差异不影响比较；也可用原生比较加纯 ITE 表达。

### 格式和界限证明

| 目标 | 精度 p | emin / emax | 工作格式 | 所有算术非零结果的保守界限 |
| --- | ---: | --- | --- | --- |
| f16 | 11 | -14 / 15 | f32，p=24，emin=-126，emax=127 | `2^-48 <= abs(z) < 2^40` |
| f32 | 24 | -126 / 127 | f64，p=53，emin=-1022，emax=1023 | `2^-298 <= abs(z) < 2^277` |
| f64 | 53 | -1022 / 1023 | f128，p=113，emin=-16382，emax=16383 | `2^-2148 <= abs(z) < 2^2098` |

理由：目标最小非零数分别为 `2^-24`、`2^-149`、`2^-1074`。有限 Add/Sub 的最小非零差仍为该最小数的整数倍；Mul 和 FMA 的最小非零结果是其平方的整数倍。Div 的最小幅值为最小数除以目标最大有限数，分别严格大于 `2^-40`、`2^-277`、`2^-2098`；最大幅值严格小于 `2^(emax+1) / 最小数`。Sqrt 的范围更窄。乘积与加数的最大合成幅值也在表中上界内。所有这些结果均落在工作格式的正规范围，辅助定向计算不会 underflow 到零或 overflow 到 infinity。

阈值最多需目标 `p+1` 位有效数，上表工作精度均足够。阈值最低二进制位可能为 `2^(emin-p-1)`，分别是 `2^-26`、`2^-151`、`2^-1076`，其指数也在工作格式内。目标数值无损拓宽以及阈值精确表示都成立。

本证明只覆盖目标 f16/f32/f64 的本次算术需求；不声称用 f128 对 f128 本身继续成立。f128 仍作为通用原语受支持，其 ISA flags 若将来需要应另审定。

## 5. OF 与 after-rounding UF 的精确阈值

对目标 `(p,emin,emax)` 定义：

```text
N = 2^emin                     // 最小正规数
H = 2^(emax+1)                 // 最大指数外的相邻幂
g = 2^(emax-p+1)
M = H - g                     // 最大有限数
O = M + g/2                   // 最近舍入溢出中点
U = N - 2^(emin-p-1)          // 最近舍入不再 tiny 的中点
P = N - 2^(emin-p)            // 无指数下限时 N 的前一个 p 位数
```

`nearest` 指 RNE/RMM；`outward` 指正结果 RTP 或负结果 RTN；其余方向为 `inward`，含 RTZ。结果符号可从正确舍入的目标结果或非零邻点读取；精确零用任一符号都不影响下面正阈值的判定。

| 模式 | OF | tiny |
| --- | --- | --- |
| nearest | `l >= O` | `l < U` |
| outward | `h > M` | `h <= P` |
| inward | `l >= H` | `l < N` |

最终 `UF = NX AND tiny`。这些公式只在第 6 节的有效有限域启用。

OF 判据对应“目标精度舍入、假设指数范围无界后，指数是否超出 emax”。因此向零舍入的结果虽为最大有限数，输入达到 `H` 时仍 OF；输入仅稍大于 `M` 而未到 `H` 时则只有 NX。最近舍入的 `O` 恰为上方 `H` 和下方 `M` 的中点，RNE 和 RMM 在此均进位到 `H`。

tiny 判据同样先按目标精度、无指数下限舍入。`P` 与 `N` 在较低 binade 的间距是次正规间距的一半，不能把最终结果是否次正规当成 tiny。最近舍入在 `U` 恰好进位到 `N`，故使用严格 `<`；朝远离零舍入时精确 `P` 仍 tiny，故使用 `<=`。

结果恰为最小正规数也可能同时 UF 和 NX。例如 f32 输入 `2^-14 - 2^-25` 转 f16、RNE：最终为 `0x0400`，精确值仍小于 `U=2^-14-2^-26`，所以 flags 是 UF|NX。精确次正规数则 NX=false、UF=false。下面的固定 SoftFloat 实验已确认这个例子及阈值邻点；迁移后的 Sail/Isla 实现仍须回归同一组预期，不能只测试一般的 subnormal。

### 2026-09-26：after-rounding UF 的独立动态复核

受测参考库取自 Sail-RISC-V `f8ce8490981eac6396a31013180a2e718615757d` 的 `dependencies/softfloat`，使用该仓库 CMake 目标 `softfloat`，RISCV specialization、`SOFTFLOAT_ROUND_ODD`、`SOFTFLOAT_FAST_INT64`、`INLINE_LEVEL=5`、`SOFTFLOAT_FAST_DIV32TO16`、`SOFTFLOAT_FAST_DIV64TO32` 均启用；编译器是 Ubuntu GCC 15.2.0。探针逐次显式设置 `softfloat_detectTininess=softfloat_tininess_afterRounding`、RM 和 flags=0，直接调用 `f32_to_f16`，不经过待测 Sail 公式或旧 Isla helper。

受测库 SHA256：`129f91c3723e056167f86d13ebc00a62506009e4d160d2317fb1e3de55be69bf`。两个直接参与边界判断的源文件 SHA256：`f32_to_f16.c` 为 `6a413eb2ca2de4e345b7e8aaf416a2987c3ec8cb13b6135953d470df67fc4f1d`，`s_roundPackToF16.c` 为 `91f093c7d2d32f24350fcfb350c1f0a82eec6b2202c7c45ddd38f57f0b62a8f9`。

RNE 正输入的完整八点结果如下。`δ=2^-38` 是这一区间相邻 f32 数的间距，flags 为 NV/DZ/OF/UF/NX 的五位整数。

| 输入位置 | f32 bits | f16 结果 bits | flags |
| --- | --- | --- | --- |
| `P-δ` | `0x387fdfff` | `0x03ff` | `0x03`，UF\|NX |
| `P=N-2^-25` | `0x387fe000` | `0x0400` | `0x03`，UF\|NX |
| `P+δ` | `0x387fe001` | `0x0400` | `0x03`，UF\|NX |
| `U-δ` | `0x387fefff` | `0x0400` | `0x03`，UF\|NX |
| `U=N-2^-26` | `0x387ff000` | `0x0400` | `0x01`，NX |
| `U+δ` | `0x387ff001` | `0x0400` | `0x01`，NX |
| `N-δ` | `0x387fffff` | `0x0400` | `0x01`，NX |
| `N` | `0x38800000` | `0x0400` | `0x00` |

探针还运行同八点的负数和其余四个 RM，共 80 项；其全部 flags 与第 5 节公式独立求值一致。其中正 RTP、负 RTN 在 `abs(x)=P` 时仍 UF|NX，紧邻 `P` 上方变为仅 NX，确认 outward 的 `<=P`。RTZ 及 inward 在 `abs(x)<N` 的七点均 UF|NX，`N` 精确无 flags。RMM 与 RNE 在这些点相同。进程退出 0，输出 SHA256 为 `fdf4a753bd4104e595eb452dac2c5d4007bbb44bb0320a6f24f475126a25275b`。

`s_roundPackToF16` 的执行过程解释了 RNE 的 `P` 样本：转换传入 `exp=-1, sig=0x7ff0`；舍入增量 `0x8`，因此 `sig+increment=0x7ff8<0x8000`，after-rounding 的 `isTiny` 为真。随后右移一位并带 sticky 后得到 `sig=0x3ff8`，最终舍入进位到 `0x0400`，同时 roundBits 非零，所以 UF 与 NX 都置位。`U` 样本原 sig 为 `0x7ff8`，加增量已到 `0x8000`，isTiny 为假，只置 NX。最终存储格式的舍入进位与无指数下限的精度舍入并非同一步。

可复现实验的 C 源码如下（保存为构建目录的 `fp_uf_probe.c`；不会修改模型）：

```c
#include <stdint.h>
#include <stdio.h>
#include "softfloat.h"
int main(void) {
  const uint32_t inputs[]={0x387fdfffu,0x387fe000u,0x387fe001u,0x387fefffu,0x387ff000u,0x387ff001u,0x387fffffu,0x38800000u};
  for (unsigned sign=0; sign<2; ++sign) {
    for (unsigned rm=0; rm<=4; ++rm) {
      for (unsigned i=0; i<sizeof(inputs)/sizeof(*inputs); ++i) {
        float32_t x={inputs[i] | (sign ? 0x80000000u : 0)};
        softfloat_detectTininess=softfloat_tininess_afterRounding;
        softfloat_roundingMode=rm;
        softfloat_exceptionFlags=0;
        float16_t y=f32_to_f16(x);
        printf("rm=%u input=%08x result=%04x flags=%02x tininess=%u\n",rm,x.v,y.v,(unsigned)softfloat_exceptionFlags,(unsigned)softfloat_detectTininess);
      }
    }
  }
  return 0;
}
```

源码 SHA256：`ec0489b7806800015c844d1228c01bcb16bd07ab6b405f457b41fe03132fde26`。在仓库根目录执行以下命令；`FP_UF_BUILD` 指向已构建上述 CMake `softfloat` 目标的目录，探针源文件放在那里：

```sh
cc -std=c11 -DSOFTFLOAT_FAST_INT64 \
  -I sail-riscv/dependencies/softfloat/berkeley-softfloat-3/source/include \
  "$FP_UF_BUILD/fp_uf_probe.c" \
  "$FP_UF_BUILD/dependencies/softfloat/libsoftfloat.a" \
  -o "$FP_UF_BUILD/fp_uf_probe"
"$FP_UF_BUILD/fp_uf_probe"
```

结论：维持现有 `tiny` 边界及该 UF|NX 例，不按“最终结果等于最小正规数则无 UF”修改。此次验证仅涉及固定 SoftFloat 的 f32→f16 边界，尚不代表其他操作/格式或迁移后的 Isla 实现通过。

## 6. 各操作的五 flags

`snan(x)`、`nan(x)`、`inf(x)`、`zero(x)`、`sign(x)` 都从原始位串判断，`finite(x)=!nan(x)&!inf(x)`。`sign` 对 NaN 只用于位模式判定，不通过 FP 的 isNegative 取原 NaN sign。

| 操作 | NV | DZ | NX/OF/UF 使用第 4–5 节的域 |
| --- | --- | --- | --- |
| Add(a,b) | 任一 sNaN，或两 inf 异号 | false | a、b 均有限 |
| Sub(a,b) | 任一 sNaN，或两 inf 同号 | false | a、b 均有限；辅助运算必须是 Sub |
| Mul(a,b) | 任一 sNaN，或 zero×inf 任一顺序 | false | a、b 均有限 |
| Div(a,b) | 任一 sNaN，或 zero/zero，或 inf/inf | a 有限非零且 b 为 zero | a、b 均有限且 b 非零 |
| Sqrt(a) | sNaN，或非 NaN 的负非零输入，含 -inf | false | a 有限且非负，或 a 为任一符号零 |
| FMA(a,b,c) | 见下段 | false | a、b、c 均有限 |

域外三个 flags 均为 false，数值结果仍来自原生操作并经 ISA NaN 包装。`inf/0` 不置 DZ；`-0` 开方合法，保持数值操作给出的 -0；`1+inf` 与 `inf+1` 均不置 NX。

FMA 的 NV 为以下条件严格 OR：

1. 任一操作数是 sNaN。
2. a、b 为 zero×inf 任一顺序，**即使 c 是 qNaN 也置 NV**。
3. 有效 infinity 乘积与 infinity 加数异号。有效 infinity 乘积是“一乘数 inf、另一乘数非 NaN 且非 zero”，允许两乘数都为 inf。乘积符号是两原始 sign 的异或。

不能只从最终 NaN 反推 NV，不能把 qNaN 传播当成 NV，不能漏掉 `inf*1 + -inf`。

比较、取整和转换的其他 flags 如下：

| 操作 | NV | DZ / OF / UF | NX |
| --- | --- | --- | --- |
| Eq、quiet Lt/Le | 任一 sNaN | 均 false | false |
| signaling Lt/Le | 任一 NaN | 均 false | false |
| roundToIntegral(rm,x,raise_inexact) | sNaN(x) | 均 false | `raise_inexact & finite(x) & !fp.eq(x,r)` |
| FP→整数 | 第 7 节的 `!valid` | 均 false | `valid & !fp.eq(x,y)` |
| 整数→FP | false | DZ/UF=false，OF 用第 5 节 | 第 7 节的精确源比较 |
| FP→FP | sNaN(x) | DZ=false；OF/UF 在有限源域用第 5 节 | 有限源域的精确源比较 |
| ROD 窄化 | sNaN(x) | DZ=false；OF/UF 按 RTZ | 按 RTZ 窄化前后精确比较 |

比较真假必须使用原生 `fp.eq/lt/le`；所有 NaN 比较为 false，正负零数值相等。sNaN 规则独立检查原始位串。

## 7. 转换和 ROD

### FP 转 32/64 位整数

```text
x = from_ieee(raw_bits)
y = roundToIntegral(rm,x)
yw = exact_convert_to_fp128(y)
valid = finite(x) AND integer_range(yw)
NV = NOT valid
NX = valid AND NOT fp.eq(x,y)
candidate = to_signed_or_unsigned_W(RTZ,y)
```

signed 的范围为 `[-2^(W-1), 2^(W-1))`；unsigned 为 `[0,2^W)`。上下界在 fp128 精确可表示，f16/f32/f64 的 y 也可无损拓宽。使用 y 作转换参数避免无符号负小数已舍入为 -0 后误判；`fp.eq(-0,+0)` 和范围比较保证其结果为零且可置 NX。

无效转换的 candidate 在 SMT 中未指定，包装必须用 ITE 屏蔽。RISC-V signed 无效结果：NaN、正溢出选最大正数，负溢出选最小负数；unsigned：NaN、正溢出选全一，负溢出选零。NV 为真时 NX 为假。不得仅比较原始未舍入 x 的整数上下界。

### 整数转 FP

本次源为 32/64 位 signed/unsigned。将整数用原生 fp128_from_signed/unsigned 转成精确 `xw`：p=113 大于等于 64，指数覆盖所有输入，所以任何 RM 均精确。正式结果由目标格式 FromSigned/Unsigned 计算；令 `lo=hi=xw`，与精确拓宽的目标结果比较 NX，并使用第 5 节的 OF。NV、DZ、UF 均 false。

必须回归 RUP 的 `65505→f16`（OF|NX）及 `-65520→f16`（仅 NX），以及所有负整数不精确转换。

### FP 格式转换和 BF16

源值本身是精确二进制值，选择能无损表示源、目标和阈值的工作格式，令 `lo=hi=exact_widen(x)` 即可使用前述 NX/OF/UF。最简单的统一实现用 fp128；其精度和指数范围同时覆盖本次 f16/f32/f64/BF16 的数值及全部阈值，包含目标 f64 的 `H=2^1024`。只检查目标有效数位数并不足够，还必须检查阈值的指数范围。纯 widening 可直接证明仅 sNaN 置 NV，其余 flags 为零。

f32→BF16 的原生数值由 `fp32_to_bf16` 给 BV16。对于非 NaN 源，将该结果拼接 16 个零再解释为 f32，可无损重建 BF16 数值；随后将源值与该重建值无损拓宽到 **f64 或 f128**，在该工作格式中完成 flags 比较。BF16 的阈值 p=8，emin=-126，emax=127：M、O、N、P、U 可在 f32 精确表示，但 **`H=2^128` 超过 f32 的最大有限数**，完整阈值算法不能用 f32 作为比较格式。f64 与 f128 均精确容纳源、目标数值及全部 BF16 阈值。源为 NaN/inf 时屏蔽 NX/OF/UF，NV 只来自 sNaN。由于数值原语只返回 bits，包装以**原始源是否 NaN**选择 BF16 canonical NaN，不能依赖未保证 payload 的 ToIEEE 返回位推断源 NaN；转换只有源 NaN 才产生 NaN。

2026-09-26 修订：本节初稿曾误称 BF16 的所有阈值均可在 f32 精确表示，遗漏了 H 的指数越界。经独立复核改为上述 f64/f128 比较契约；f32 只用于源表示和 BF16 位串的数值重建。第 4 节的 f16→f32、f32→f64、f64→f128 算术工作格式，以及本节 FP↔整数的 fp128 范围比较，均已覆盖各自 H 或整数上下界，不受此次修订影响。

### ROD：仅两种窄化

适用 `f32→f16`、`f64→f32`，由模型解释内部编码 6：

```text
base = native_convert(RTZ,x)
NX = finite(x) AND NOT fp.eq(exact_widen(base), exact_widen(x))
result_bits = ite(finite(x) AND NX, raw_bits(base) OR 1, raw_bits(base))
```

NaN 在包装中 canonicalize。NV=sNaN，DZ=false，OF/UF 使用 RTZ 的阈值与 NX。精确结果不改最低位；负极小数得到的 RTZ -0 在置最低位后成为负最小次正规数；溢出时 RTZ 最大有限数本已最低位为一。

ROD 的上溢阈值为 `H`；稍超过最大有限数但小于 `H` 可以仅 NX。ROD 的 tiny 按 RTZ 为 `abs(x)<N`。该方案与 SoftFloat `SOFTFLOAT_ROUND_ODD` 下“截断后不精确则置位”的源码对应，仍必须完成两种转换的动态差分，不能把编码 6 加进原生 RM 枚举。

## 8. BF16 向量状态修正

`zfbfmin_utils.sail` 已有纯 `bf16_to_f32 : bits16 → (flags,bits32)`；`bf16_to_f32_set_flags` 才会调用 `accrue_fflags`。VF 乘加应在循环前调用纯版本得到标量值和标量 flags，在 `init_masked_result` 产生的 mask 中首次遇到实际活动 lane 时才累计标量 flags，一次足够。后续活动 lane 继续正常计算向量源转换和 FMA flags。

该状态性分支属于完整指令控制流，不纳入 67 个纯 helper 零分叉要求。可用局部布尔值记载是否已累计，不允许通过 eager ITE 隐藏 `accrue_fflags`。

必须分别测 `vl=0`、全屏蔽、`vstart>=vl` 的 boxed 标量 sNaN，旧 flags 为零和非零时均保持；有活动 lane 时累计 NV；另测 sNaN 只位于被 vstart 跳过的向量前缀，实际元素与标量有限，不应贡献 NV。

## 9. 证据、待验证项和派发门槛

已核实的当前源码事实：

- `primop/float.rs` 的原语宏只检查 Symbolic，不能确保实际 sort；FromIEEE/FromSigned/Unsigned 未接具体和 MixedBits；SMT 底层已有 ToIEEE/ToUnsigned 接线。
- `primop_util.rs` 的 `smt_value` 已有 Bits、Symbolic、MixedBits 的公共转换；Solver 已有 BV 长度和 sort 查询实现供扩展复用。
- `isla-sail/sail_plugin_isla.ml` 的 native Float/RM 类型映射及 `remove_extern_impls` 规则要求第 2 节的编译验证。
- SoftFloat `s_roundPackToF16/F32/F64/BF16.c` 的 `roundIncrement`、溢出分支及 `isTiny` 分支对应第 5 节的严格/非严格阈值；ROD 在 roundBits 非零时置有效数最低位。
- `source/RISCV/specialize.h` 的 `init_detectTininess` 是 afterRounding；`dependencies/softfloat/CMakeLists.txt` 启用 RISCV specialization 和 `SOFTFLOAT_ROUND_ODD`。
- `s_mulAddF32.c` 的 `infProdArg` 和 `propagateNaN_ZC` 路径支持 zero×inf 即使加数 qNaN 仍 NV，以及反号 infinity 相加 NV。
- `model/core/softfloat_interface.sail` 保持原 C++/Lem 签名；`bf16_to_f32` 是纯函数，审查基线 `sail-riscv@f8ce849` 的 VF 曾在活动元素判断前调用带 flags 副作用的包装。本轮工作树已按第 8 节改为首次活动 lane 累计，具体实施和受测版本由主 agent 记录。

实现前写失败测试，随后检查以下门槛：

1. 通用接口：具体、符号、MixedBits 等价；五 RM 及符号 RM；错误 sort/宽度/片段；f128 位宽；正负零/NaN 比较；FMA 一次舍入；ToIEEE 非 NaN 往返。先证明测试输入可满足，再证明输出或 flags 与预期不同不可满足。
2. 阈值：对 M、O、H、P、U、N 的前/等/后三点，正负两侧、五模式分别与 SoftFloat 比较；某目标格式不能表示阈值邻点时使用更宽源转换或能到达该结果的算术。覆盖最终 min-normal 且 UF|NX、精确次正规、极小值到零。
3. 各算术：第 6 节所有特殊域、极大指数差、抵消、普通不精确 Div/FMA、所有旧报告反例；对完整结果位和全部五 flags 作固定边界及随机差分。
4. 转换：整数舍入后越界/回到合法域、unsigned 负小数到 -0、ROD 特殊域和边界、BF16 原始 sNaN。
5. 编译/执行：所有新辅助使用 strict Bool 与纯 ITE，无新增数据分叉；实际调用普通模型函数；隔离测试禁用旧专用分发；非 SYMBOLIC 后端仍可用 SoftFloat。
6. 性能：先测各格式单 helper，记录资源和 tactic；尤其 f64 Div/Sqrt/FMA 要额外计算 fp128 定向邻点，可能明显增加求解成本。任何优化必须保持等价证明并新增针对风险的差分，不能换回已知近似公式。Timeout/unknown 不计通过。

当前批准的是有精确语义论证的实现基线。使用精确乘积关系替代宽 Div/Sqrt、采用更小工作精度等可以继续研究，但尚未作为本文批准的替代算法；不得未经逐项论证就替换。

全部 67 个新模型 helper 的完整验证、原有 12 个 helper 回归、89 个 clause 的指令状态验证以及 E 阶段源码/IR/79 份严格配置同批切换仍按 [计划](plan.md) 执行。本文不能解除这些门槛，也不把未测项算作完成。
