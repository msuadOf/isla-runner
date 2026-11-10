# 统一浮点接口的 C++ 后端可行性

日期：2026-09-27。本文是只读调查和隔离编译探针，供[统一后端方案](unified-backend-plan.md)审阅；未修改 Sail、Sail-RISC-V 或 Isla 生产实现，未生成或替换正式 IR。现有 `1dcc` IR/helper 验证保留其原有适用范围。

结论：可以让 C++ 和 Isla 执行同一组 Sail 浮点数值辅助、异常公式和 ISA 包装。除新增通用 SoftFloat runtime 外，当前 Sail 0.20.1 还必须补齐 C/C++ 后端的原生浮点类型降低；仅取消 `SYMBOLIC` 条件和添加 C++ extern 实现会在生成 C++ 前失败。

## 受审版本和本轮证据

- Sail：`0.20.1`，工具报告源码 HEAD `446fb477c508853595ccc937ed60765aa685ae31`；已核同 HEAD 源码中的 C 后端。当前工作区根目录没有 `sail/` checkout，实际工具与源码位置由本机环境提供，未改变它们。
- Sail-RISC-V：HEAD `f8ce8490981eac6396a31013180a2e718615757d` 加现有未提交浮点实现。关键受审源码哈希记录在 `.tmp/unified-backend-cpp-feasibility/manifest.json`。
- 本轮可复现证据在 ignored 目录 `.tmp/unified-backend-cpp-feasibility/`。该目录包含探针源码、命令、退出码、生成代码、编译日志和 manifest；它是准备工作证据，不是新架构验收。
- 文中的原生类型布局、函数选路事实以实际源码和下述探针为依据。[既有双后端契约](exception-contract.md)只证明原 `cpp` extern 与 `SYMBOLIC` 函数体可以共存，不能证明 C++ 已执行共享函数体。

## 当前可直接复用的实现

| 位置 | 已有能力 | 在统一方案中的用途 |
| --- | --- | --- |
| `sail-riscv/model/core/softfloat_interface.sail` | 67 个 `riscv_*` helper 的 `cpp` / `lem` 外部绑定；现有 `bits_rm`、`bits_fflags`、H/S/D/BF16 和整数位串类型 | 保留 ISA 入口签名；统一默认 C++ 路径时需移除或切换对应 `cpp` 绑定，使 C++ 真正生成共享 Sail body |
| `sail-riscv/model/prelude/ieee_fp_primops.sail` | Sail 原生 `float16/32/64/128`、`float_rounding_mode` 和通用数值 extern | 为同一声明增加明确的 `cpp` runtime 绑定，保留 Isla 原有通用名称 |
| `sail-riscv/model/core/ieee_fp_exceptions.sail` | 纯 Sail 分类、五个 Bool 异常事实、精确 flags 公式、ROD 派生转换 | 解除仅 `SYMBOLIC` 可见的限制，使 C++ 与 Isla执行同一算法；继续复用现有 `float_bits` 和 `fp_exception_flags` |
| `sail-riscv/model/extensions/FD/softfloat_symbolic*.sail` | ISA canonical NaN、无效整数返回、共享 flags 到 RISC-V 位序转换 | 与两端共用的 helper body 一起生成；状态累计仍走 Sail ISA 逻辑 |
| `sail-riscv/c_emulator/riscv_softfloat.{h,cpp}` | f16/f32/f64 和 BF16 的 67 个直接 SoftFloat tuple wrapper | 可保留为独立具体 oracle；其 API 返回 `(fflags,result)`，不能直接作为只返回数值的通用 FP extern |
| `sail-riscv/dependencies/softfloat/CMakeLists.txt` | 编译 Berkeley SoftFloat generic + RISCV 源码，开启 `SOFTFLOAT_ROUND_ODD` 和 `SOFTFLOAT_FAST_INT64` | 复用现有依赖，不必引入 host float；f128 算术/转换源也已在库内 |
| `sail-riscv/model/CMakeLists.txt`、`c_emulator/CMakeLists.txt` | `--cpp` 生成 `hart::Model`、附加 runtime header、链接 `softfloat` 与 `sail_runtime` | 添加通用 FP 类型头和 runtime 源的最小构建入口 |

`riscv_softfloat.h` 依赖生成的 `sail_riscv_model.h` 和 `hart::ztuple_*` 名称。新通用 runtime 的类型头应独立于生成模型：模型头先 include SoftFloat 类型/通用 ABI，模型实现再 include extern 实现声明，避免头文件循环依赖。CMake 已有 `--c-header-include` 与 `--c-include` 两种入口。

## 当前 Sail C/C++ 后端缺口已复现

同 HEAD 的 `src/sail_c_backend/c_backend.ml` 有以下现成能力：

- `is_stack_ctyp` 已把 `CT_float _` 与 `CT_rounding_mode` 作为按值传递类型。
- 类型打印已把它们映射到 `floatN_t` 和 `uint_fast8_t`，可与 SoftFloat 的 `float16_t/float32_t/float64_t/float128_t` 对接。
- 但 `C_config.convert_typ` 没有把 Sail 的五个原生类型降低到这些 Jib 类型，最终落入 `No C type for type ...`。

本轮分别生成五个独立 identity 函数，每个只用一种原生类型。命令形式为：

```sh
sail --cpp --c-no-main --c-preserve probe --no-memo-z3 --no-color \
  -o .tmp/unified-backend-cpp-feasibility/float32 \
  .tmp/unified-backend-cpp-feasibility/float32.sail
```

`float16`、`float32`、`float64`、`float128`、`float_rounding_mode` 五项均退出 1，分别报告缺少对应 C 类型。另有一个 `from_ieee → add → to_ieee`、带显式 `cpp` extern 的 f32 探针同样在 RM 类型处失败。具体命令与源哈希见 `native_types_results.json`；这确认失败在类型降低，尚未进入 C++ 编译或 SoftFloat 链接。

建议最小工具链修改：在 `C_config.convert_typ` 添加五项映射，复用已有 `CT_float` / `CT_rounding_mode` 类型，不增加模型侧同义类型。还需补 `I_undefined` 的 `codegen_exn_return`：当前同文件1553起的分支没有 FP/RM，最终报 `Cannot create undefined value for type ...`；`jib_compile.ml` 的异常改写会为按值返回函数追加此任意返回。因此这也是明确的生成器缺口，不能只加五项映射。仍须用实际生成文件检查 record/tuple 中 FP 字段、泛型相等和 ITE，而不能把“已有 printer”当作整个 C++ ABI 已完成。

共享公式含多处 `rm == round_*()`。C 后端的 `eq_anything` 会生成 `eq_<type>`，RM 类型名为 `rounding_mode`，因此要提供 `eq_rounding_mode(uint_fast8_t,uint_fast8_t)`。四种 native FP 同样生成 `eq_float16/32/64/128`；record 字段相等也经 `codegen_equal` 调用这些函数，目前 runtime 没有相应定义。它们应匹配 Isla 的 SMT sort equality：所有 NaN 相等，正负零不相等；这与 `fp_eq` 的 NaN 不等、正负零相等不同。另 `sgen_call` 对原始 `Eq/Neq` 指令默认直接打印 `==/!=`，应在补丁测试中核 native FP 到达该分支的可能性，必要时补 typed lowering；SoftFloat struct 没有默认数值相等运算符。

## extern 选路和纯工具函数

现有 `cpp: "softfloat_f32add"` 的声明即使旁边新增普通函数体，C++ 后端也会跳过该 Sail body（`CDEF_fundef` 分支先判断 `ctx_is_extern`）。统一后端切换必须同时处理这一层绑定，否则只是新增了一套未被 C++ 使用的共享代码。

Isla 插件当前构建 Jib context 使用 `for_target:"c"`。统一原语声明可以用 `{cpp:"通用runtime函数", c:"现有Isla原语"}` 明确双绑定；不应使用 `{isla:"..."}` 假定插件按此名字选路。Lem 仍可保持原外部绑定；native FP 的声明/body 可仅在 C++ 与符号后端可见，避免无意扩大正式 Lem 后端承诺。

共享库还依赖 `ite`、`strict_and_bool`、`strict_or_bool`、`isla_bool_to_bit`。C++ 端可以用普通纯 Sail body，Isla 端保留通用 primop。下面的结构已针对 bits32、bits128 和一个 Bool+bits32 record 做 C++ 探针：

```sail
val choose = pure {c: "ite"} : forall ('a : Type). (bool, 'a, 'a) -> 'a
function choose(c, a, b) = if c then a else b
```

`sail --cpp` 生成退出 0，`g++ -std=c++17 ... -c cpp_body.cpp` 退出 0。生成的 bits128 实例正确使用 `COPY(lbits)`，record/小位串按值返回。源和精确命令见 `cpp_body.sail`、`cpp_body_results.json`。这支持复用 Sail 生成器管理复制，比为所有生成 record 和宽位串手写 C++ ITE ABI 更小。

这个 PASS 仅限生成和对象编译；没有运行该对象，也没有在本轮生成 Isla IR。最终还要用同一 fixture 验证 Isla 选中 `c:"ite"`、进入通用 primop、未知条件不产生新增路径，并补测原生 FP/RM 类型。

## 通用 SoftFloat runtime 的最小合同

通用 extern 返回数值或 Bool，flags 仍由同一份 Sail 公式计算。runtime 需要覆盖共享代码实际闭包：四种 FP 格式、五种 RM、分类/常量/符号、IEEE 编码转换、算术/FMA/sqrt、比较、round-to-integral、格式转换、整数转换和 BF16 位串出口。`float128` 是 f64 flags 和整数边界算法的必需辅助精度，不能因为 ISA 暂无 Q 指令而省略。

| 边界 | 必须明确的实现要求 |
| --- | --- |
| RM | Sail 的 `float_rounding_mode` 在 C++ 落为 `uint_fast8_t`；五个构造返回 SoftFloat 0/1/2/3/4，对应 RNE/RTZ/RTN/RTP/RMM。RISC-V 的含 DYN 枚举和 `bits_rm` 继续保留；ROD 不成为第六个原生 RM |
| IEEE 编码 | f16/f32/f64 与 `.v` 之间按位重解释；f128 需要 Sail `lbits` 与 SoftFloat 两个 64 位 word 的准确转换，明确 word 序和 128 位宽，不能经过 host `long double` |
| NaN | Z3 FP 不保留 raw sNaN/payload；原始位串必须继续用于共享分类和 NV。SoftFloat 类型即使能保存 raw encoding，数值 API 也不得借此影响两端可观察合同。通用 `to_ieee(NaN)` 需要固定同一编码，不能由载体残留 payload/sign 改变结果，否则不符合 SMT 单一 NaN 值的函数一致性；具体位模式属于允许选定的实现。最终 ISA canonical NaN 仍在 Sail 包装选择；通用 `is_negative/is_positive` 对 NaN 必须匹配 Z3，不能直接返回 raw sign |
| 比较 | 通用 `fp_eq/lt/le` 返回数值 Bool，NV 由共享 Sail 逻辑决定；SoftFloat signaling/quiet 的内部 flags 不能意外进入架构状态 |
| flags | Sail 共享编码为 NV0/DZ1/OF2/UF3/NX4，RISC-V/SoftFloat 为 NV4/DZ3/OF2/UF1/NX0；runtime 内部 SoftFloat flags 不应代替共享 Sail flags。保留直连 oracle 时单独比较完整位串及五 flags |
| tininess | 现 RISCV specialization 默认 after-rounding；通用适配宜在作用域内显式设置并恢复，避免前一次库调用改变状态 |
| ROD | 原 SoftFloat 构建支持模式 6；统一执行应共用现有 Sail 的 RTZ+不精确置奇推导，另以 direct SoftFloat mode 6 为 oracle |
| 整数宽度 | SoftFloat 只原生提供 i/ui32 和 i/ui64 转换。当前生产闭包用 32/64；公开 FromSigned/Unsigned 声明为任意 `n>0`，ToSigned/Unsigned 又有 16/128 出口。不能把前者截断到64或把后者当已支持。先给实际闭包建立明确覆盖表；完整公开合同需宽整数准确适配/额外验证或显式能力边界 |

任意宽整数不能简单先转 f128 再转目标精度：大整数可能因两次舍入失真。对当前32/64输入，精确转换至 f128 的算法前提成立；不能由此推及任意 `n`。FP→整数的无效域属于通用原语未指定结果，由 ISA 包装屏蔽并选择规定返回；C++ 适配需保证此域也不会触发 C/C++ undefined behavior。

还有一个现成 ABI 宏的可见性问题：SoftFloat CMake 当前把 `SOFTFLOAT_FAST_INT64` 设为 `PRIVATE`，而 `softfloat.h` 的 f128 按值 API 声明受该宏保护。新 runtime 若使用上述按值 ABI，必须对 adapter 编译也一致定义宏，或改用 f128M 指针 ABI；不能仅链接已有库后假定头文件会声明 f128 函数。

## SoftFloat 状态与并发

现 `SOFTFLOAT_PRELUDE` 每次清 exceptionFlags、设置 roundingMode；不保存旧值、不恢复、不设置 detectTininess。`softfloat.h` 与 `softfloat_state.c` 的 `THREAD_LOCAL` 默认为空，当前依赖 CMake 未定义它，平台头也未补定义，因此源码默认是进程全局状态。

额外核对本机历史 CMake 构建：其 `flags.make` 确无 `THREAD_LOCAL`，`readelf --wide -s softfloat_state.c.o` 中 roundingMode、exceptionFlags、detectTininess 均为 `OBJECT GLOBAL`，不是 `TLS`。输出、对象哈希和实际路径记录于本轮证据目录。此证据只确认该历史构建的 ABI，不是当前工作树完整构建 PASS。

新的 `pure` 通用 runtime 不能让调用者可观察到 SoftFloat 全局状态污染。需要一个统一作用域，设置本次 RM/after-rounding/干净异常状态后执行，并恢复原状态。并发另行解决：保存恢复本身不消除线程竞争。可选择把整个 SoftFloat 库及所有使用者一致编译为 TLS，或对所有新旧 wrapper 统一加锁。只在新 C++ header 加 `thread_local` 会与现有 C 库的非 TLS 符号产生 ABI 冲突；只锁新 wrapper 也不能保护并发旧 oracle 调用。初期若采用单线程/独立进程快验，须在构建和测试合同中明确，后续并发测试使用不同 RM 与 sticky flags 的同时调用。

## 最小可编译、可运行的下一步探针

1. 在隔离 Sail checkout 补五项 type lowering，固定源码与工具哈希。先重跑五个 identity 探针，再生成含 FP/RM record、RM 相等和宽位串的最小 fixture，验证生成、对象编译和链接。
2. 新建不依赖完整 `hart::Model` 的通用 SoftFloat 类型/extern adapter，先接 f32 加法、f64→f128、f128加法、f128→IEEE 和一个整数转换。用同一 Sail 函数分别生成 C++ 与 Isla IR，输入和输出都以位串穿过边界；选择五种 RM、signed zero、sNaN/qNaN、精确/不精确和大于64位有效位的 f128 例子。
3. 把当前一个真实 `riscv_f32Add` 共享 body 与异常公式作为入口，确保 C++ 生成文件中调用通用数值 adapter，未调用旧 `softfloat_f32add`；与独立 direct SoftFloat oracle 对照结果和 flags。隔离 probe 应同时覆盖 state save/restore，避免数值正确但污染 caller flags。
4. 扩展到生产闭包所有实际 native 调用，再验证67个 RISC-V helper；完成后再走全模型 C++、正式 IR、严格配置和整条指令状态验收。具体/符号差分只能证明两后端一致，flags 公式独立正确性仍要用 direct SoftFloat oracle 校验。

以上是建议的实施顺序，尚待统一方案审阅。当前已确认“原工具缺类型降低”和“纯Sail fallback能正确生成CPP宽位串复制”；没有宣称新 native runtime、共享 C++ 数值算法、线程安全或统一全模型已经通过。
