# 统一浮点双后端独立合同复核

日期：2026-09-27。审阅对象为[统一方案](unified-backend-plan.md)、[C++可行性记录](unified-backend-cpp-feasibility.md)和隔离P0实际编译器补丁。本轮未修改生产实现、正式IR、共享状态文档或他人文件，未进入内存worktree。

## 结论与继续实施边界

同一Sail数值/flags/ISA语义分别调用C++ SoftFloat和Isla Z3的架构可以继续实施。此次没有发现需要推翻架构的新语义冲突。发现一个**实际编译器输出缺陷**和一个**已复现的新适配ABI合同**：

| ID | 严重度 | 证据与影响 | 最小修正及放行边界 |
| --- | --- | --- | --- |
| INDEP-01 | 中，C目标编译失败 | P0公共C/C++生成器为native FP/RM生成`T{}`任意返回；C++合法，`-c`输出经`gcc -std=c11`失败。 | 按`Config.cpp`选择C++初始化与C11合法初始化。C++ P0可继续；修复前不能声称同时支持native类型的C目标。 |
| INDEP-02 | 中，新adapter必须满足的ABI合同 | `bits(32)`外部返回实际为`uint64_t`，生成器不自动截断。真实SoftFloat `f32_to_i32(-1)`若直接转`uint64_t`返回，得到64个1，Sail与32个1相等比较为false。 | 所有不足64位的bits返回须规范化到声明宽度，例如`uint64_t(uint32_t(result))`。当前旧wrapper/oracle已正确，新adapter尚未受测；不阻止P0加法，进入P1整数转换前必须覆盖。 |

可继续隔离P0及真实三方数值/flags比较。此文的局部运行结果不构成全模型、82原语、并发隔离或新架构验收；正式版本切换仍须依统一方案重新生成IR、绑定严格配置并完成指令和状态验证。

## 版本、证据与执行结果

受审模型为`sail-riscv@f8ce8490981eac6396a31013180a2e718615757d`及当前未提交内容，Isla为`f4f8e4584a70588c66c9e7a6286cc20211618f18`及当前未提交内容。隔离Sail基于`446fb477c508853595ccc937ed60765aa685ae31`；工具来源为`isla/target/float-solve-evidence/unified-backend-p0/20260926T162859Z/sail-src/`，未覆盖安装工具。

独占ignored证据目录为[`.tmp/unified-backend-independent-review/`](../../.tmp/unified-backend-independent-review/)。[manifest](../../.tmp/unified-backend-independent-review/manifest.json)记录受测生成器、Sail可执行文件、实际C插件、runtime/SoftFloat静态库、源文件、生成文件和探针可执行文件哈希；[版本记录](../../.tmp/unified-backend-independent-review/versions.json)记录版本。受审初版`compiler.patch` SHA-256为`256a2a8db5289709a0ffec2aa5e7e69e0d23798d019cbebd0d6741edb66d1fd9`，受测C插件SHA-256为`cf2e7aa002aaf3fe16b1a0340e6724a6c2f0086a9afaba3a250aeb9a06d56d69`。后续P0修改不自动继承本次结论。

| 验证 | 实際结果 | 限定范围 |
| --- | --- | --- |
| `python3 .tmp/unified-backend-independent-review/run.py` | PASS：生成、编译、运行均exit 0，37项断言；ASan/UBSan无诊断 | native FP32/FP128/RM与bits128混合record的C++生成和运行，generic equality分发、ITE两臂、宽位串复制，以及signed32反例/修正。 |
| Sail `-c`生成native float32/RM identity，再以`gcc -std=c11 -c`编译 | FAIL：生成exit 0，编译exit 1 | 实际初版patch的C输出；详见INDEP-01。 |
| 新双后端完整共享数值/flags probe | 未测 | 本轮没有代替P0实施者执行完整数值链，也没有重跑正式77项。 |

精确命令和退出码保存在[commands.json](../../.tmp/unified-backend-independent-review/commands.json)及[native_c_commands.json](../../.tmp/unified-backend-independent-review/native_c_commands.json)。C++用`g++ 15.2.0 -std=c++17 -O2 -fsanitize=address,undefined`。测试链接当前机器已有的历史Sail runtime和SoftFloat库；其确切路径和哈希在ignored manifest中，不能据此声称当前依赖源码已重新构建。

## INDEP-01：公共生成器的任意返回只适用于C++

初版patch在`c_backend.ml:1573`为`CT_float _ | CT_rounding_mode`输出`sprintf "%s{}" (sgen_ctyp ctyp)`。同一`Codegen`模块服务C和C++，已有`Config.cpp`开关，类型lowering也没有只对C++启用。初版源码副本保存在[reviewed_c_backend.ml](../../.tmp/unified-backend-independent-review/reviewed_c_backend.ml)，补丁保存在[reviewed_compiler.patch](../../.tmp/unified-backend-independent-review/reviewed_compiler.patch)。

实际[native_c.sail](../../.tmp/unified-backend-independent-review/native_c.sail)只定义float32和native RM identity。`sail -c`成功生成；[native_c.c](../../.tmp/unified-backend-independent-review/native_c.c)第87、98行分别产生：

```c
return float32_t{};
return uint_fast8_t{};
```

[gcc错误日志](../../.tmp/unified-backend-independent-review/native_c_compile.stderr)分别报告`expected expression before 'float32_t'`与`'uint_fast8_t'`。这些是编译器为异常返回追加的语句，即使正常路径只返回入参也会使整个C文件无法编译。

最小修复为按`Config.cpp`分支，C++继续`T{}`，C目标FP采用例如`(float32_t){0}`、RM采用`(uint_fast8_t)0`；或用已有局部声明/赋值代码生成辅助构造合法值。应对四FP和RM各跑C/C++ identity生成及对象编译。这里没有证据表明既有非FP的C输出出现回退；问题范围是补丁新启用的native类型。已交P0实施者修正。

## INDEP-02：小位宽整数返回须规范化其64位载体

真实模型[ieee_fp_primops.sail](../../sail-riscv/model/prelude/ieee_fp_primops.sail)第169–199行给FP转整数声明固定`bits(16/32/64/128)`输出。C后端将固定不超过64位的bits降为`uint64_t`，`codegen_conversion`在同型stack值之间直接赋值；Sail runtime的`eq_fbits`按完整载体做`op1 == op2`，不根据Sail静态宽度掩码。

独立fixture声明`candidate : unit -> bits(32)`，再执行`eq_anything(candidate(), 0xffffffff)`。生成的[probe.cpp](../../.tmp/unified-backend-independent-review/probe.cpp)第143–145行直接调用外部函数后比较，没有`& 0xffffffff`：

```cpp
uint64_t candidate;
candidate = review_signed32_candidate(UNIT);
result = eq_fbits(candidate, UINT64_C(0xFFFFFFFF));
```

适配实验使用真正的`f32_to_i32(float32_t{0xbf800000}, RNE, true)`。直接把有符号返回转为`uint64_t`得到`0xffffffffffffffff`，Sail相等式为false；先转`uint32_t`再扩成`uint64_t`，得到`0xffffffff`，相等式为true。[执行日志](../../.tmp/unified-backend-independent-review/execute.stdout)记录两者。输入是合法、精确的-1，因此这不是原语无效域或未指定转换结果。

现有[riscv_softfloat.cpp](../../sail-riscv/c_emulator/riscv_softfloat.cpp)第217–226行等把i32结果放入`float32_t.v`，已自然截成32位；现有[oracle.cpp](oracle/oracle.cpp)第104–108行也显式转`uint32_t`。因此本项是新通用adapter必须继承的ABI合同，并非旧包装已发现错误。P1的所有i32路径应加入-1和最小有符号值；P2的i16出口同理。要求在Sail侧比较完整结果位串，单独打印后截位会掩盖问题。

## 已核验而未发现新增问题的范围

### Native值、record、相等与宽位串

编译器`is_stack_ctyp`已将四FP和RM作为按值类型。真实fixture的record包含FP32、FP128、RM与bits128；生成器对前三者直接赋值，对bits128调用`COPY(lbits)`，销毁仅处理bits128。实际执行两臂选择，重复覆盖五种RM，修改源record的GMP位串后目标仍保存旧值，未发现浅复制、双重释放或native字段布局问题。

直接`eq_anything(FP/RM)`和record字段相等分别生成`eq_float32`、`eq_rounding_mode`、`EQUAL(float128)`等调用。运行用独立测试header提供符合既有sort合同的相等实现，验证了两种NaN相等、正负零不同、FP128低64位和高64位完整保存。这证明生成和调用ABI能够使用该合同；不代表P0未来adapter的相等实现已被验收。

补丁中的原始Jib `Eq/Neq`分支静态都转到同一`eq_<type>`函数；本轮fixture没有证明Jib原始`Eq/Neq`在真实全模型中的触达。也未覆盖native FP列表/向量/union；不把普通record结论推广到这些容器。模型既有RISC-V `rounding_mode`枚举经过zencode生成`zrounding_mode`，其辅助函数名与native `rounding_mode`不冲突。

### FP128端序与高层严格求值

SoftFloat当前平台头`build/Linux-x86_64-GCC/platform.h:39`定义`LITTLEENDIAN`，`source/include/primitiveTypes.h:44–51`在此配置下把`uint128`布局为低word `v0`、高word `v64`；`float128_t`是两个`uint64_t`的array。此构建的`float128_t.v[0]`是低64位，`v[1]`是高64位。record运行验证了两个非零word按值复制。新adapter的`lbits ↔ float128_t`转换尚未提供，本轮没有为其数值重解释写PASS；需使用明确的GMP word导入/导出或移位，不按对象地址强制转换。

对`ieee_fp_exceptions.sail`和四个`softfloat_symbolic*.sail`进行了输入计算和位操作扫描。当前共享helper主要使用固定宽度分类、常量阈值、FP原语和ITE，没有发现额外由输入控制的宿主整数除零或移位越界表达式。未选ITE的无效FP→整数candidate仍需total，这已属于原计划；本轮没有新增反例，也没有以源码扫描代替adapter的UB运行验证。

### `rem`、`roundToIntegral`与oracle可检测范围

Isla `float.rs:348`将`fp_rem`直接绑定`FPBinary::Rem`，`fp_round_to_integral`绑定对应SMT舍入操作。SoftFloat的`f32_rem.c:142–154`按最近整数商、ties-to-even选择余数，可用于IEEE remainder；不能用宿主`fmod`替换。`f32_roundToInt.c:61,113`的`exact`只控制NX累积，五种RM的结果位计算与该Bool无关。因此数值adapter可固定`exact=false`并丢弃内部flags，架构的`raise_inexact`继续交共享Sail计算。此处是API/源码核验，37个尚未使用原语仍须按P2逐项验证。

[oracle.cpp](oracle/oracle.cpp)的实际运算直接调用SoftFloat算术、比较、舍入和转换；`main`在运行前独立设置after-rounding、清flags、设置RM，并从原生`softfloat_exceptionFlags`取五个flag。未发现它调用共享Sail异常公式，因而仍可独立检测共享flags公式错误。

但是C++数值adapter与该oracle最终使用同一个SoftFloat算术实现，两者数值一致不能独立排除SoftFloat本身的数值错误。三方验收应同时保留两个判断：C++共享体与Isla/Z3的数值及flags一致；共享Sail flags与原生SoftFloat flags一致。若C++/oracle一致而Isla不同，需要保留并分析差异，不能用“多数一致”自动判Isla错。原生SoftFloat也不验证boxing、fflags累计、FS/VS或mask/tail状态；这些仍须独立状态验证及可用的DUT/冻结参考证据。

## 交接

INDEP-01与INDEP-02已发送架构负责人及P0实施者。既有NaN抽象、正负零min/max未指定、sort equality、TLS、total转换及f128依赖门槛继续以统一方案为准。此次没有调整这些门槛，也没有把已有1dcc PASS迁移到新方案。共享findings/status/TODOs的同步由主agent负责，避免越过本轮独占文件边界。
