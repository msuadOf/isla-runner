# P1/P2：共用浮点数值 C++ adapter 合同

日期：2026-09-27。状态：P1首轮闭包基线已冻结；P1/P2统一库已完成190条声明的实际生成、链接、执行和值验证，186个native定义与四个Sail工具逐项闭合。七个冻结adapter文件已移交生产、候选v5和最终候选v6并核对哈希，最终测试manifest的59项已独立复核一致。这里的PASS限定数值原语和生成ABI；共享Sail异常公式、完整模型与ISA状态仍由后续集成门槛验证。本文属于[统一后端计划](unified-backend-plan.md)的 adapter 合同，技术前提见[C++ 可行性调查](unified-backend-cpp-feasibility.md)。当前正式 `1dcc` 批次及 P0 独占目录保持其原版本边界。

用户已授权统一方向。P1 采用一个数值接口：C++ 调用 SoftFloat，Isla 调用 Z3；两者执行同一份 Sail 数值辅助、异常公式和 ISA 包装。数值 adapter 只返回 FP、BV 或 Bool，不返回架构 flags。独立 SoftFloat 原生结果及 flags 参考继续保留，不能把执行同一份 Sail 公式的 C++ 当作 flags 的独立 oracle。

## 1. 交付与可写边界

本文件由架构评审者独占。P0 负责人独占 `agents/float_support_review/tools/unified_backend_p0/` 及其既有隔离证据/工具链副本。主agent已批准 P1 adapter 实现者（Sol high，任务名 `unified_p1_adapter`）独占根目录下的 `tools/unified_backend_p1_adapter/` 和 ignored `.tmp/unified-backend-p1-adapter/`；先交可复现 adapter、测试、构建脚本及生产补丁，不写 P0 目录、Sail 模型或其他 agent 的状态文档。

后续并行分工已明确：P2 的 `unified_p2_wide_impl` 独占 `agents/float_support_review/tools/unified_backend_p2_wide/sail_softfloat_wide.cpp/.h`，P1仍唯一编辑主 `sail_softfloat.cpp/.h`、构建清单及公有入口接线。生产三处CMake由模型集成人单点修改，P1/P2仅提供补丁。P2范围与算法见[宽转换合同](unified-backend-wide-conversion-contract.md)，不并入下表P1的97条静态分母。

内部wide头的首次完整冻结 SHA-256 为 `966116135755712e470f2374d0b9a38fd688fbf95eac77e8c076a69fa9ac358f`。现行名字位于 `namespace sail_softfloat::wide`：8个 `from_signed/unsigned{16,32,64,128}(rm,lbits)`，四种源FP各自的 `to_signed/unsigned{16,32,64}(rm,floatN_t)` 重载与 `to_signed/unsigned128(lbits*,rm,floatN_t)`，以及 `from_ieee128(lbits)`/`to_ieee128(lbits*,float128_t)`。BV128返回指针形式已由P0 patched Sail实际生成并对象编译确认；头哈希/ABI变化须重新交接，早期 `fpN_*_wide` 建议已被本合同取代。

生产集成时按下表移交明确写入权。2026-09-27主agent追加授权：最终值测试及源码冻结后，P1唯一负责移交 `sail_softfloat_types.h`、`sail_softfloat.h/.cpp`、`sail_softfloat_wide.h/.cpp`、`sail_softfloat_extra.h/.cpp` 七个新文件到生产 `sail-riscv/c_emulator/` 及模型候选。P1可直接复制，也可提供校验明确冻结哈希的复制脚本和清单让模型集成人执行；不得由其他owner手工取旧版本。三处生产CMake仍由模型集成人单点修改，完整候选manifest由其核对七文件哈希后更新。实际七文件交接见第13节，生产模型构建另行验收。

| 文件/区域 | adapter 包负责内容 | 边界 |
| --- | --- | --- |
| `sail-riscv/c_emulator/sail_softfloat_types.h`（拟新增） | 与生成模型无关的 SoftFloat 类型声明、ABI 宏校验、typed equality 声明 | 供生成模型头先 include；不得 include `sail_riscv_model.h` |
| `sail-riscv/c_emulator/sail_softfloat.h`、`.cpp`（拟新增） | typed 数值 extern、位串转换、分类、环境作用域 | 不包含 RISC-V flags 编码、canonical 规则、CSR 或寄存器处理 |
| `sail-riscv/dependencies/softfloat/CMakeLists.txt` | TLS 与 `SOFTFLOAT_FAST_INT64` 的库/调用端一致配置 | 保留既有 RISCV specialization 和 ROD 编译选项；不得链接旧非 TLS 库充当新构建 |
| `sail-riscv/c_emulator/CMakeLists.txt` | adapter 源及头进入 target、依赖传递 | 模型生成选项由集成人协调 |
| `sail-riscv/model/CMakeLists.txt` | `--c-header-include` 类型头和 `--c-include` extern 头接入 | 与模型共用实现者协调，不由两个 agent 同时编辑 |
| `tools/unified_backend_p1_adapter/` | 闭包清单、独立数值/环境/TLS测试、运行入口、补丁 | 无提交文档中的本机绝对路径；输出位置由参数传入 |

Sail 编译器 native 类型降低及 equality 生成由 P0 交接；Sail 声明双绑定和共用函数体由模型集成人负责。adapter 包不自行重写两者。原 `riscv_softfloat.{h,cpp}` 的 67 个策略级包装作为隔离参考，生产绑定迁移与 oracle target 的建立由集成人明确安排。

## 2. 当前调用闭包：45 个 FP extern，97 个 typed 声明

依据为本轮 `native_calls.tsv` 的非空 `call_sites` 记录，已与 `model/prelude/ieee_fp_primops.sail`、`core/ieee_fp_exceptions.sail`、四个 `softfloat_symbolic*.sail` 及相关 FD/V helper 核对。构建脚本须保存 TSV 内容、源码哈希及重建命令；临时调查文件的位置不作为长期依赖。P1 准入需要生成代码的实际调用清单复核，不能只依据静态计数。

表中的 N 是 FP 位宽，不是整数位宽；每个 typed Sail 声明有独立 `cpp` 名称，Isla 继续复用原有通用 `c` extern 名。

| 类别 | 当前 typed 声明 | 个数 | SoftFloat/adapter 实现 |
| --- | --- | ---: | --- |
| RM 构造 | `round_nearest_ties_to_even/away`、`round_toward_positive/negative/zero` | 5 | 返回第 3 节约定值 |
| 常量 | `fp128_zero` | 1 | 正零的精确位编码 |
| 绝对值 | `fp32_abs`、`fp64_abs`、`fp128_abs` | 3 | 清 sign 位；不经过 host FP |
| NaN 分类 | `fp16/32/64_is_nan` | 3 | 指数全一、fraction 非零 |
| 符号分类 | `fp32/64/128_is_negative` | 3 | 非 NaN 且 sign=1；包含负零 |
| BV 重解释 | `fp16/32/64/128_from_ieee` | 4 | 第 4 节精确布局 |
| 开方 | `fp16/32/64/128_sqrt` | 4 | `fN_sqrt` |
| 取整到同格式 FP | `fp16/32/64_round_to_integral` | 3 | `fN_roundToInt`，结果仍是 FP |
| FP 格式转换 | `fp16_to_fp32/64/128`、`fp32_to_fp16/64/128`、`fp64_to_fp16/32/128` | 9 | 对应 `fA_to_fB`；窄化只舍入一次 |
| 整数到 FP | `fp16/32/64/128_from_signed/unsigned` | 8 | P1 实际实例为 32/64 位；对应 i/ui32/64 API |
| 数值比较 | `fp16/32/64/128_eq/lt/lteq`，`fp32/64/128_gt/gteq` | 18 | `fN_eq/lt_quiet/le_quiet`；gt/ge 交换操作数 |
| 算术 | `fp16/32/64/128_add/sub/mul/div/fma` | 20 | `fN_add/sub/mul/div/mulAdd` |
| FP 位串出口 | `fp16/32/64_to_ieee` | 3 | 非 NaN 精确编码，NaN 统一代表 |
| FP 到整数 | 源 FP16/32/64，各自 `to_signed32/unsigned32/signed64/unsigned64` | 12 | 对应 `fN_to_i/ui32/64`；第 6 节定义域/域外合同 |
| BF16 | `fp32_to_bf16` | 1 | `f32_to_bf16`，输出 BV16 |
| 合计 | 45 个不同 FP extern 名 | 97 | 不含下列四通用工具 |

另有 `ite`、`strict_and_bool`、`strict_or_bool`、`isla_bool_to_bit` 四条工具声明，合计 101 条 typed 声明、49 个 extern 名。优先按 P0 方案为 C++ 使用普通纯 Sail 函数体，为 `c` 保留现有 Isla extern；宽位串/record 的复制与释放交给生成器。adapter 不另造浅拷贝泛型 ITE。

当前闭包没有 native `fp128_to_ieee`、`fp128_round_to_integral`、f128→小 FP、FP→16/128 位整数、一般 `is_positive/is_normal/is_subnormal/is_zero/is_infinite`、NaN/inf/负零构造、neg/min/max/rem 等调用；公开声明仍保留。P0/P1 测试可用专用入口观察 f128 编码，但不能据此把全部公开 FP 接口列为已验收。完整 82 FP 原语/190声明与任意宽转换属于 P2。

## 3. 类型、名字和生成 ABI

P0 已交接的类型合同如下。P1 的 `tools/unified_backend_p1_adapter/abi_probe.sail` 已用隔离patched Sail实际生成CPP，生成源保存在 `.tmp/unified-backend-p1-adapter/abi_probe.cpp`；首探针核实固定/多态BV输入、FP128和unit调用ABI，后续P1基线已完成闭包链接与运行，证据见第12节。

| Sail 类型 | Jib/C++ 类型 | adapter 规则 |
| --- | --- | --- |
| `float16/32/64/128` | `CT_float(N)` → `floatN_t` | 复用 SoftFloat struct，按值传递/返回 |
| `float_rounding_mode` | `CT_rounding_mode` → `uint_fast8_t` | RM 构造和比较是确定的纯函数 |
| 固定 BV16/32/64 | `fbits`，底层 `uint64_t`；首探针核实32/64 | 输出高位必须清零；完整闭包编译继续覆盖16位 |
| BV128/多态 BV | Sail `lbits`/`sail_bits` | 已核 `fp128_from_ieee(lbits)`；32/64 FromSigned 调用前创建带相应 `len` 的 `lbits` |
| `unit` | Sail runtime `unit` | 常量/RM构造参数按生成代码保留，不凭接口外观省略 |

明确 typed 绑定示例：

```sail
val fp32_add = pure {c: "fp_add", cpp: "sail_fp32_add"} :
  (float_rounding_mode, float32, float32) -> float32
```

对应候选 C++ 签名为 `float32_t sail_fp32_add(uint_fast8_t, float32_t, float32_t)`。其他函数采用 `sail_` 加完整 typed Sail 名称，包括 `sail_fp64_to_fp128`、`sail_fp32_to_unsigned64`。P0 若已采用另一等价命名，则在生成 bindings 清单中统一继承，不同时维护两套手写命名表。

首个实际生成探针确认 `sail_round_nearest_ties_to_even(UNIT)`、`sail_fp128_from_ieee(lbits)` 和 `sail_fp32_from_signed(uint_fast8_t,lbits)`。固定32/64位外层函数的 `uint64_t` 输入不能直接转交多态extern：生成器先经 `CONVERT_OF(lbits,fbits)` 构造对应32/64位 `len`，extern按该字段选择准确转换。输入 `lbits` 由调用者管理，adapter不得释放或篡改它。BV128返回另经实际生成和对象编译确认：公有函数使用 `void ...(lbits *result, ...)`，由调用者提供已初始化结果对象。

RM 值固定为 RNE=0、RTZ=1、RTN=2、RTP=3、RNA/RMM=4，使用 `softfloat_round_*` 常量，不依赖另一个 enum 的声明顺序。ROD=6、动态 RM=7 均不属于 native RM。Sail 的两个 ROD 窄化 helper 已先转为 RTZ 再置奇；oracle 才直接用 SoftFloat 6。从无效内存或错误手写调用制造的 RM=5/6/7 是 ABI 合同错误，可以明确拒绝；它不同于第 6 节合法 FP 输入产生的无效整数转换。

`eq_rounding_mode(a,b)` 使用 RM 值相等。`eq_float16/32/64/128` 必须满足 SMT sort equality：两个 NaN 相等、正负零不同，其他非 NaN 位编码相同才相等。不得复用数值 `fp_eq`，因为后者 NaN 不等、正负零相等。编译器直接生成的 FP `Eq/Neq` 也须走同一语义；如果仍输出 struct `==/!=`，这是 P0 编译器交接缺口，应回交修正。

## 4. 位串、NaN、f128 与构建宏

`softfloat_types.h` 使用 `float16_t { uint16_t v; }`、`float32_t { uint32_t v; }`、`float64_t { uint64_t v; }`、`float128_t { uint64_t v[2]; }`。当前 Linux x86_64 平台头声明 LITTLEENDIAN，f128 的 `v[0]` 为低64位、`v[1]` 为高64位。因此 Sail BV128 的 bits[63:0] 和 bits[127:64] 必须分别进入这两字；sign 位为高字 bit63，15位 exponent 为高字 bits62:48。通过项目既有宽位串设施导入/导出，两字均须检查；禁止依赖 host `long double` 布局或只调低64位 getter。

构造 FP 时只作按位重解释，不作数值整数转换。接口的数值域把全部 NaN 视为同一 FP 值：原始 payload、sign、sNaN 仍由 Sail 保存的 BV 负责。为保持函数一致性，`to_ieee(NaN)` 必须给该格式统一代表，不得根据载体残留 payload/sign 返回不同位串。建议代表为 H=`0x7e00`、S=`0x7fc00000`、D=`0x7ff8000000000000`，f128测试出口为高字 `0x7fff800000000000`、低字0；这只是 generic NaN 的允许实现选择，RISC-V 规范结果仍由 Sail 包装显式选择。

`is_negative(NaN)` 为 false。`abs` 清 sign 后即使保留内部 NaN payload，也不得经任何数值可观察操作区分两个 NaN。`fp32_to_bf16` 同样将所有 NaN 数值输入映射到单一允许 BV16 代表，建议 `0x7fc0`；Sail 根据原始源判断 sNaN 和 canonical 结果。所有非 NaN BV 往返必须逐位相同，包含两种零、无穷和次正规。

SoftFloat f128 按值函数声明受 `SOFTFLOAT_FAST_INT64` 控制。当前库把该宏设为 PRIVATE，新 adapter 和生成模型头不能自动看到它。P1 采用按值 ABI，必须把 `SOFTFLOAT_FAST_INT64` 作为 `softfloat` target 的 PUBLIC 使用要求传给所有调用端，并沿用库的相同定义；不能混用未声明的按值函数与 f128M 指针函数。构建清单和独立 header 编译测试必须检查这一点。

## 5. 数值计算与异常环境

Add/Sub/Mul/Div/Sqrt 分别直接调用同格式 SoftFloat 对应函数；FMA 调用一次 `fN_mulAdd`，不得拆成两次舍入。显式 RM 在调用前进入 SoftFloat 环境。宽化仍接受同一 RM 参数，即使有限输入数学上精确；NaN 转换不会借助 native flags 改写模型异常。

数值比较返回 IEEE Bool：任何 NaN 与其他值的 eq/lt/le 为 false，±0 相等。推荐 lt/le 用 quiet 接口，gt/ge 通过反序 lt/le 实现；底层产生何种 native flags 都不进入模型。比较也应恢复调用前环境。纯位操作/分类/常量/equality 不调用 SoftFloat，不需要制造环境作用域。

`round_to_integral` 返回同格式已舍入 FP，建议 native `exact=false`；在共享 Sail 中由 `raise_inexact` 控制 NX。整数转换也可用 `exact=false`，因为生产 adapter 不返回 native flags；oracle 维持原本 `exact=true` 的 flags 语义。两种选择不得改变数值结果。

共享 `ieee_fp_exceptions.sail` 重建五异常，native flags 全部丢弃。尤其辅助 f128 RD/RU 运算产生的 flags 不能被 OR 到 ISA `fflags`。原 flags 的独立参考必须在 native 单次操作结束、环境恢复前捕获。

## 6. 32/64 位整数与域外总定义

FromSigned/Unsigned 当前被调用的输入宽度为32或64，必须在生成实例清单中逐项核实。32位 signed 以补码解释，用对应 `i32_to_fN`；64位 signed 用 `i64_to_fN`；无符号独立调用 ui32/ui64。不能以 C++ 越界有符号 cast 或 host 浮点中转实现数学解释。推荐用位复制或明确补码解码得到整数对象，再调用 SoftFloat；最小负数不得通过有符号取负制造溢出。

原始8/16位 V 输入的 sign/zero extend 已在 Sail；目标8/16位整数的饱和与 NV 优先也留在 Sail。P1 不添加自己的窄整数 ISA 策略。

FP→32/64 位整数返回固定宽度 BV：数值转换有效域是按请求 RM 舍入后的整数落入目标范围。SoftFloat 的 i/ui32/64 接口适用，返回的 `int_fast32_t` 等须规范成目标32/64位补码位串；高位清零，不依赖宿主 fast 类型刚好等于目标宽度。

NaN、无穷、越界也是数值 extern 可收到的合法 FP 输入。当前共用 Sail 会先求值 candidate，再用 ITE 屏蔽，因此 adapter 必须在域外终止并返回选定 BV，不能 assert、panic、trap 或触发 C++ undefined behavior。可直接保留固定 SoftFloat specialization 的确定结果，因为通用合同在这些输入不规定数值；架构结果仍由 Sail 选择。generic NaN 具有单一数值，所有 NaN 的域外返回应一致。

前述总定义不意味着 P1 已实现任意宽输入。公开 `FromSigned/Unsigned` 的任意 `n>0` 和128位整数出口属于 P2。P1 的实际实例清单必须拒绝新增未实现宽度；不能以截低64位作为悄然扩域，也不能普通舍入到 f128 再窄化替代任意宽整数的单次舍入。此处拒绝的是包外 ABI 实例，不能用于拒绝本包内无效数值转换。

## 7. TLS 与作用域：推荐实现

已核现版 `softfloat.h`/`softfloat_state.c` 在未定义 `THREAD_LOCAL` 时将其展开为空；项目 CMake/平台头未定义它。历史实际构建的三个状态符号也为 OBJECT GLOBAL。P0 只承诺单线程独立进程加保存/恢复，不宣称 TLS 已通过。

P1 推荐在专用、重新配置的 SoftFloat target 上让库和全部调用端一致启用 TLS：C 用 `_Thread_local`（C11），C++ 用 `thread_local`（C++11以上）。编译定义由 target PUBLIC 使用要求传递；不要只在 adapter 头临时定义宏。CMake 示意如下，实际修改与现有宏列表合并，不能遗留相互冲突的 PRIVATE 定义：

```cmake
target_compile_features(softfloat PRIVATE c_std_11)
target_compile_definitions(softfloat PUBLIC
  SOFTFLOAT_FAST_INT64
  "$<$<COMPILE_LANGUAGE:C>:THREAD_LOCAL=_Thread_local>"
  "$<$<COMPILE_LANGUAGE:CXX>:THREAD_LOCAL=thread_local>"
)
```

所有 include `softfloat.h` 的 TU 均须继承相同模式，涵盖 adapter、旧 oracle wrapper 和独立测试。头中的 `extern THREAD_LOCAL` 声明必须与库的 TLS 定义一致。`softfloat.h` 本身缺少 C++ linkage guard，adapter 类型头仍以 `extern "C"` 包住其 include。C 与 C++ 宏拼写不同，但必须生成同一 TLS storage ABI。测试必须检查编译命令、目标对象的 TLS 符号及实际链接；只发现源码宏不能记 PASS。

一次调用的环境作用域：

1. 保存 `softfloat_roundingMode`、`softfloat_detectTininess`、`softfloat_exceptionFlags`。
2. 设置请求 RM、`softfloat_tininess_afterRounding`、flags=0。
3. 执行这一条 native 操作；生产仅保留数值返回，oracle 在此处额外捕获 flags。
4. 无条件恢复保存的三值。C++ 用不可复制的 RAII guard，析构 `noexcept`；嵌套调用恢复到直接调用者的状态。

本包不调用 extF80，故不改变 `extF80_roundingPrecision`。TLS 宏会同时使库内该变量按同样 ABI 定义，但没有必要在未触及它的每次调用中读写它。

guard 生命周期覆盖 native 调用本身；不能先设置 RM 后释放 guard 再运算，也不能在作用域外读取本次 flags。外层共享 Sail helper 不读 SoftFloat 环境。所有内部 native 操作各自设置请求 RM，避免较宽辅助的 RD/RU 覆盖下一条正式运算。纯数值内部 helper 如复用 guard，须保证每条 native 调用实际使用它请求的 RM。

TLS 与保存/恢复解决不同问题：前者隔离并发线程，后者隔离同线程调用者和嵌套调用。二者都要验证。若最终工具链无法使用 TLS，应提交有明确全调用覆盖范围的互斥替代供审查；不能只锁新 adapter 而允许旧 wrapper 并发操作同一非 TLS 状态，也不能静默退回全局变量。

## 8. Oracle 并发与独立性

首选将原生参考运行在独立可执行文件/进程，保留其 SoftFloat 版本、RISCV specialization、after-rounding、ROD 和完整 flags。共享 C++ 和原生参考必须有不同入口，日志分别记录；不可从共享 Sail 结果派生预期。

同进程引用 oracle 时，必须使用与生产相同 TLS ABI 的库并对 oracle 操作采用完整环境作用域。旧 `riscv_softfloat.cpp` 的宏只清 flags/设 RM，不能直接满足这个环境纯性合同。若在进程内同时存在旧非 TLS 与新 TLS 构建，需独立链接名字/符号隔离；本包优先使用独立进程，避免同名状态/函数符号冲突。仅将 oracle 放入另一个线程不能隔离非 TLS 全局状态。

## 9. 验证与放行边界

实施采用红绿顺序：先建立实际生成的调用 fixture 和会暴露漏接口、错误位宽、错误环境的测试，再补 adapter。每次结果记录源码、Sail 编译器、SoftFloat 配置/对象、adapter 和可执行文件哈希。

| 门槛 | 所需证据 | 不能据此声称 |
| --- | --- | --- |
| ABI与闭包 | 97 typed FP实例/45 extern及四工具全部生成、编译、链接；实际调用清单无遗漏；f128/多态整数签名已核 | P2未用接口全支持 |
| 位串/分类/equality | 各格式非 NaN 往返；f128高低字不同、顶位/低位；多payload正负qNaN/sNaN统一NaN出口；genericEq和数值Eq的相反零/NaN规则；RM五值及record/ITE复制 | NaN payload可经native FP恢复 |
| 数值 | 所有现调用类别、五RM；非NaN结果逐位比独立SoftFloat；FMA融合反例；f128比较/定向算术；BF16指数/次正规边界；32/64 signed/unsigned端点 | 同Sail公式互比足以证明flags正确 |
| 域外总定义 | NaN/±inf/两侧越界的FP→int；先求值candidate的实际Sail入口正常完成；无UB；最终Sail饱和值/flags另比oracle | 原语域外任意值必须与Z3某次物化值逐位相等 |
| 环境顺序/嵌套 | 预填非默认RM、before-tininess、非零flags，调用后原样恢复；交替RM；嵌套guard；数值和原生flags参考互不污染 | 单线程结果代表线程安全 |
| TLS | C/C++ compile definitions一致；`softfloat_state`对象三状态符号为TLS；链接通过；不同线程不同RM/flags/tininess交错多轮，结果及各自哨兵状态正确 | 保存恢复可替代TLS或完整互斥 |
| 共用helper | 67 helper通过共享CPP与Isla及独立native flags三方对照，含ROD、最终min-normal且UF\|NX、NaN、unsigned负小数到零、窄整数NV优先 | 整条ISA、77项、完整架构状态已PASS |
| 性能 | 实际生成共享CPP的f16/f32/f64，Div/Sqrt/FMA、转换和lane吞吐；单次旧SoftFloat另列 | 统一CPP必然快于旧单次SoftFloat |

环境/TLS测试应使用可控交错和不同预置状态，不只并行重复RNE。测试中的同步不得把被测native运算全部串行化而掩盖共享状态错误。UB检查使用适合本工具链的 sanitizer 或等效检查，并包含最小负整数与64位最高位。

数值 NaN、无效整数转换等未指定域采用允许关系验证；共享 ISA 包装屏蔽以后再要求完整结果位和五 flags 一致。Isla的未知输入仍需SAT、单完成路径且无采样；此项由模型/Isla集成人运行，adapter包提供对应fixture与独立预期。

## 10. 交接清单与当前未决

- P0 已给候选 native 类型、typed `cpp` 命名、显式 `SOFTFLOAT_FAST_INT64` 和单次环境保存/恢复方向；五种native identity生成成功，可复用隔离 Sail wrapper 在 P1 独占目录生成完整 extern 签名。工具链源码由 Sail commit `446fb477c508853595ccc937ed60765aa685ae31` 的 git archive 加 P0补丁构建；wrapper的 `--version` 会误读父git版本，不能单独作为受测源码证据，须保存archive commit、补丁/关键源码和binary哈希。
- 多态32/64位FromSigned/Unsigned的 `lbits`/长度传递、FP128 from-BV及unit参数已由实际生成闭包链接并执行；BV128返回指针也已另行生成核实。P2公有wrapper随后已通过第13节完整公开测试，内部hook测试与此分开记录。
- P1 TLS编译、链接、顺序/嵌套/并发测试已在冻结基线上通过。C与C++定义分别为 `_Thread_local`/`thread_local`，Release测试显式保留断言；第12节限定受测范围。
- 主agent已明确P1/P2独占目录和生产补丁边界。架构评审已复核P1的NaN/equality、域外总定义、位宽和环境恢复，以及extra的NaN、分类、rem/min/max和窄化实现；P2 wide独立数学评审和最终合库值验证均已通过，证据见第12、13节。
- 任意宽整数、128位整数出口和其余公开FP原语由P2完成。它们是最终交付门槛，不能遗留为最终TODO，也不能把分包通过拼成未经统一运行的190声明PASS。

主agent负责在[议题摘要](status.md)和[全仓状态](../../specs/TODOs.md)登记实施与验证进度；本文不替代它们的状态权威。

## 11. P2 剩余 native 接口与最终公开闭合

主agent已要求最终交付覆盖全部190条公开声明，未使用接口不能作为最终TODO遗留。P1闭包门槛和P2公开门槛分别记录；P2宽转换由既有wide包完成，剩余native接口另交复用的Sol任务 `performance_resume`，独占 `agents/float_support_review/tools/unified_backend_p2_native_extra/` 及 ignored `.tmp/unified-backend-p2-native-extra/`。该包只写 `sail_softfloat_extra.h/.cpp`、专属生成测试与脚本；P1唯一编辑主header的include、公有wide wrapper和构建清单，不重复定义extra包的公有函数。

已用190条声明与P1首绿library的demangled定义核对：**107个已导出的native函数 + 17个需wide新增的公有函数 + 62个extra函数 + 4个纯Sail工具 = 190**。107包括P1宏顺带实现的格式对称函数，不能只按97个实际调用声明减剩余工作，也不能把这些额外实现未经验证就标为P2 PASS。17个wide公有缺口为四源格式各自的signed/unsigned16/128共16项，加`fp128_to_ieee`；已有8个FromSigned/Unsigned公有wrapper还须接任意合法宽度。

186个native C++名字统一为 `sail_` 加完整Sail名字；四工具使用普通Sail函数体。名字权威是bindings包的 `candidate-final/bindings.json`，首次冻结SHA-256为 `a98a8fdf466326f9bcb8a3843045c3f17b5c5bf3efc350bba66b713e7e6f9255`，不是本表的简称。`undefined_floatN` 对应 `sail_undefined_floatN`，Isla的`c`绑定仍为`fpN_undefined`，保留`impure`声明。

| extra类别 | typed范围 | 个数 | 确定合同 |
| --- | --- | ---: | --- |
| 任意FP值 | `undefined_float16/32/64/128` | 4 | CPP选择同格式正零作为一个允许的具体代表；仍保留impure声明，不宣称穷尽Isla未知FP取值 |
| NaN/无穷常量 | 四格式各自`nan/inf/negative_inf` | 12 | 精确NaN统一代表与正负无穷编码 |
| 零常量 | H/S/D的`zero`，四格式`negative_zero` | 7 | 精确符号零；`fp128_zero`已在P1，不能重定义 |
| 取负 | 四格式`neg` | 4 | 非NaN翻sign且保留其余位；NaN归一 |
| 分类 | 四格式各自`is_normal/is_subnormal/is_zero/is_infinite/is_positive` | 20 | 下述原始字段谓词，不读取native flags |
| f128窄化 | `fp128_to_fp16/32/64` | 3 | 五RM调用对应原生`f128_to_fN`，一次舍入、环境恢复 |
| IEEE余数 | 四格式`rem` | 4 | 调`fN_rem`；无RM参数，采用最近偶数整数商的IEEE remainder |
| 最小/最大 | 四格式`min/max` | 8 | 单NaN返回另一数值，双NaN归一；异号零按允许关系选择明确CPP代表 |
| 合计 | 均添加公有前缀`sail_` | 62 | 以实际生成调用/链接及值验证闭合 |

分类规则对四格式一致：normal的指数既非0也非全1；subnormal是指数0且fraction非0；zero是指数和fraction均0；infinite是指数全1且fraction0；positive是非NaN且sign=0，因此正零和正无穷为true，任何NaN为false。NaN常量和可观察输出使用第4节统一代表。FP128字段及字序沿用第4节。

`rem`不接受RM，但内部仍使用`Scope(RNE)`隔离SoftFloat隐藏状态。它不是`fmod`或向零整数商余数：例如`remainder(7,2)=-1`，最近商4为偶数；`remainder(5,2)=1`，最近商2为偶数。返回零时保留被除数符号。NaN、零除数、无穷被除数等域按SoftFloat/SMT的FP数值结果处理，native flags仍丢弃；有限数对无穷除数返回原有限值。

`min/max`仅返回数值。任一输入为NaN而另一为非NaN时返回后者；双NaN返回统一代表。对`+0/-0`两输入，CPP固定选择min为`-0`、max为`+0`，两种参数顺序都相同；这是SMT允许结果集合内的实现选择，不能在跨后端测试中冒称Z3必定物化相同符号零。其余有限/无穷值通过native quiet比较或等价精确规则选值，并恢复环境；相等非零值有同一编码。通用min/max不承担RISC-V的sNaN/NV或ISA min/max扩展规则。

extra包的红绿验证必须使用真实Sail声明和P0编译器生成的调用代码。62条接口全部实际调用并断言结果；常量/分类覆盖四格式的±zero、±inf、normal、subnormal、正负qNaN/sNaN；neg核非NaN逐位翻sign；rem核商ties-to-even、负余数和特殊域；min/max核NaN两顺序、双NaN、异号零、普通顺序和相等；f128窄化核五RM及上下溢/舍入边界。每次native调用同时检查环境哨兵，实际链接P1的Scope与TLS库，不能以临时stub验证代替。

最终P1集成负责人读取冻结bindings清单，生成对全部190条公开声明的真实引用；检查每个native只有一个定义、四工具从Sail生成、完整链接、运行值与允许关系。P2独立wide hook的数学/ABI测试和extra包的62项测试是分包证据；只有接入公有`cpp` wrapper后通过此门槛，才可报告公开接口完整。路径、冻结header/source/binary哈希及阶段边界在最终README与manifest中按实际包目录分别记录。

## 12. 阶段证据与独立复核

P1首轮基线冻结于 `.tmp/unified-backend-p1-adapter/p1-baseline/`，包含 `source/`、生成Sail/C++、构建产物和原始日志。已逐项核对原 `manifest.json` 的27个SHA-256条目；其中原 `tools/unified_backend_p1_adapter/` 键对应基线 `source/` 快照。基线主adapter源码哈希为 `acaab7023df8dd384e72e1fa2d0bef620c845a29dd95d4e5e8c5e145e5d896b1`，闭包测试可执行文件为 `7d29d386482c41fb6f8cc64dc60ead9841dc9e662117e25dbe672577227995e7`。补充 `freeze-manifest.json` 已纳入矩阵生成源、两个矩阵二进制、TLS CMake和结果日志，其34项哈希也全部核对一致；该清单SHA-256为 `76b2b8b117cc209e35cdf0618faa93c46d0fd05ca5cb06c86288a4e07e5cb03b`。

`test.stdout` 记录114个实际生成wrapper调用通过，包含97条typed FP声明、四工具、多态整数32/64实例、generic Eq/Neq、FP ITE和带BV128的record复制。数值专用矩阵使用另一个进程直接调用SoftFloat；`matrix_compare.stdout` 记录365项数值逐位一致，并保留原生flags列。每条97声明至少有代表输入，带RM项覆盖五模式；该结果仅覆盖所列365例，不是任意输入证明，也不是共享Sail异常公式的独立flags验收。

环境测试包含顺序、嵌套、四线程确定性交错和每线程2000轮调用；线程分别持有不同Scope状态，并在全部线程进入后检查、全部检查后释放。实际编译参数确认C/C++两侧TLS宏一致，`SOFTFLOAT_FAST_INT64`传播到调用端，Release测试使用 `-UNDEBUG`。P1源中的LP64前提已有编译期检查，32位整数输出和固定宽输入mask另有断言。当前后续接线源码不沿用这份基线的PASS，必须运行统一包验证。

P2 extra分包已完成真实Sail生成红绿验证：去掉extra实现时恰好62个公有符号未定义，加入后62入口全部执行，15,623次值/环境检查和6,224次原生SoftFloat对Python整数/有理数比较通过。评审已读取实现、fixture、期望值生成器和结果日志，并逐项核对 `.tmp/unified-backend-p2-native-extra/manifest.json` 的47项产物及476项源码输入哈希。extra源码SHA-256为 `11c18c5fbf904af9e6e581660e1cd0ba25164a6184931f8c6c1464d20bfd77be`，header为 `5a0d4a0eb08aeaff5fee79ad4750ee2b6289e2173d1a7aa48c53eb7627405372`。首轮manifest为 `8b37a4a4722e1688e8c9109fb54de7fe6fee839858bf7847a40bfbdc39490ab8`；补记新输出目录复现结果后更新为 `1bea2831e889388049a77a5844bab73b499708c83fd4892a4577ec290a34a094`，最终清单也已逐项复核。复现的测试二进制和stdout与首轮逐字一致。分包范围、命令和输入矩阵见[extra说明](tools/unified_backend_p2_native_extra/README.md)；随后在P1统一库上的重链与运行结果见第13节。

P2 wide独立数学审查已完成：评审者逐函数核对sticky、溢出指数夹取、65,537位补码、f128字序、NaN/无效整数总定义、所有权与Scope，并用原合同的数学参考重新计算保存的61,820个输出，全部一致；本轮没有重跑数值二进制。源码SHA-256保持 `3e934be4379d627158b4dd2b2cecb54563a51dbd9cda7a579b798a7d5be318e5`，头保持第1节冻结值。详细边界与证据见[宽转换合同第9节](unified-backend-wide-conversion-contract.md)。本adapter评审也独立核对 `p+guard=15/31/63/177`、`L-1+bias-1` 指数、三字f128与原生roundPack参数及FP→整数先舍入后精确拆解的范围判断，未发现阻断。

## 13. 统一公开接口与七文件移交

统一测试证据位于 `.tmp/unified-backend-p1-adapter/full/`。已读取生成Sail、实际调用、原生数值、public值与extra重新链接日志；190条声明生成251个真实C++ wrapper，全部执行并检查环境。另以 `nm -C --defined-only` 独立核对统一 `libsail_softfloat.a`：186个公有native名字与冻结bindings集合完全一致，每个恰好一个定义，无缺失或多余项；四个undefined保留impure，四工具保留Sail函数体。

| 公开分母 | 在统一库上的值证据 |
| --- | --- |
| 原97条typed FP | 365个独立进程SoftFloat数值比较重新通过；原生flags单独记录 |
| extra 62条 | 实际extra生成源重新链接本轮统一库，15,623个值/环境检查与6,224个native/数学参考检查通过 |
| wide新增17条 | 四源到signed/unsigned16/128的五RM结果断言；FP128 IEEE出口高低字与NaN归一断言 |
| 原有8条整数输入的宽扩展 | 1/32/33/64/65/113/129/1024位生成实例均调用；附加值检查含signed1=-1、宽输入42和65位最高位为1的±2^64，直接暴露低64位截断 |
| P1宏额外10条 | FP128 is_nan、round_to_integral、四种32/64整数出口，FP16 abs/gt/gteq/is_negative均有结果断言；整数出口含有效端点与NaN总定义检查 |
| 四Sail工具 | ITE的FP/BV128/record值和复制检查；AND/OR四输入组合、bool-to-bit两个输入值检查 |

上述8条整数输入已计入97分母，不重复相加。最终分母为97+62+17+10+4=190。通过的依据是所列代表值和明确边界，不能扩写为对任意数值的穷尽验证；wide的独立数学矩阵和静态审查补充算法证据。

P1提供 [copy_frozen.py](../../tools/unified_backend_p1_adapter/copy_frozen.py)，内嵌七个明确源哈希，复制前检查全部源和既有目标，遇到不同内容保留目标并失败。已核 `.tmp/unified-backend-p1-adapter/adapter-copy-manifest.json`（SHA-256 `7de4d4c6d70690ea84c7fe25d01a8f8690769909253ae5208691d0daa66a3818`）指定的生产 `sail-riscv/c_emulator/` 和 `isla/target/float-solve-evidence/unified-backend-model/20260927-candidate-v5/sail-riscv/c_emulator/` 两处共14个文件，全部匹配冻结源。三处生产CMake和完整候选manifest仍由模型集成人负责；本次七文件交接不证明生产模型已经编译或运行通过。

最终交接另纳入 `isla/target/float-solve-evidence/unified-backend-model/20260927-final-v6/sail-riscv/c_emulator/`，copy manifest更新为 `27575d1794f53f0cc69271a2006723ca80f794d73771e6dfc85889a42f453666`；三处共21个文件均已独立核对相同哈希。已核生产及v6的emulator CMake哈希同为 `17d5656a19c88ec617a3cad8f90ba01514beb721a84f3ce1779524b31bfdb470`，`SAIL_SOFTFLOAT_ENABLE_WIDE=1` 和 `SAIL_SOFTFLOAT_ENABLE_EXTRA=1` 均为PUBLIC定义。v6完整源码清单哈希为 `749c3c5bba2995ecc048e22fd9baf375e6daec9b677c562b96d3c6d07ec7c911`，完整模型构建由其owner继续。

README命令重新生成extra fixture并重建full后，各项结果再次通过。最终 `.tmp/unified-backend-p1-adapter/full/manifest.json` SHA-256为 `73ac7a5ba0f74505c8eb2ff7fe32ad37dfbfa22c7366b46029df357d81af4a91`；59项源码、生成输入、测试、库、可执行文件、编译flags和TLS符号哈希均已独立重算一致。其中实际C/C++插件为 `cf2e7aa002aaf3fe16b1a0340e6724a6c2f0086a9afaba3a250aeb9a06d56d69`，统一adapter静态库为 `ea8870159d5a7e73046af2d53e744b385cb5cb9e07e65bc8e82d30ec7434126d`，public值测试二进制为 `cb62bd2aab35f224b295616c5103394cb37909d5ec02a27f22418dcee4a2b411`。末次仅补充插件身份并重算manifest，七个数值实现文件和已通过的测试二进制未变化。现行复现与维护边界见[P1包说明](../../tools/unified_backend_p1_adapter/README.md)。
