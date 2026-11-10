# Sail-RISC-V 浮点函数参考清单

## 1. 范围、依据与结论

本清单按“IEEE 数值计算由 Isla 调用 Z3；异常标志、ISA 返回规则和状态更新由 Sail 模型负责”检查。再用 RISC-V、ARM、x86 交叉判断：相同格式、舍入方式和输入下，一个 Isla 原语不能因 ISA 改变含义。通用 ITE 可以组合结果，选择条件和选什么值由模型写明。

- 检查日期：2026-09-26。
- Sail-RISC-V：`f8ce8490981eac6396a31013180a2e718615757d`。
- Isla：`f4f8e4584a70588c66c9e7a6286cc20211618f18`。
- 当前 `isla/rv64d.ir` SHA-256：`6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`。
- 逐名核对结果：`softfloat_interface.sail` 的 **67 个声明**，与 IR 中 **79 个声明减去 12 个已有函数体**后的名称集合完全相等，没有缺失或多余。
- 本文覆盖上述 79 个 helper 的名称、签名、现有实现与修改方向，并检查其外侧的标量、RVV、Zfa、BF16 支撑函数族。只做静态调查；“有实现”“保留”都不表示功能测试通过。

**结论：67 个 helper 需要增加 Sail 符号函数体，逐步替代 Isla 按 RISC-V 名称分发；12 个已有函数体留在模型。原生数值运算继续调用通用 primop。**保留现有 C++ SoftFloat 绑定作为运行后端和对照来源，不必改它的接口。

对照来源要按函数语义选择：第 3 节中有同语义 C++ SoftFloat 包装的 67 个 helper 可逐位比较结果和 flags，其中 ROD 窄化须启用 ROD；第 4 节的 Recip7/Rsqrte7 和第 6 节的 FCVTMOD、mask、状态更新没有可直接替代的同语义 SoftFloat API，应按 RISC-V 规范、模型控制流和独立样例验收。已有窄整数转换还要检查其饱和与 NV 优先级。

本次补充发现：**RVV 的 `vfncvt.rod.f.f.w` 需要 round-to-odd，当前两个窄化 helper 用 `rm=0b110` 传递；Isla 只接受 0..4，具体值 6 会 panic。**此前“支持五种舍入方式即可覆盖全部 helper”的范围描述不足，详见第 5 节。

## 2. 读表说明

源码位置缩写均为仓库根目录相对路径：

| 缩写 | 文件 |
| --- | --- |
| S | [sail-riscv/model/core/softfloat_interface.sail](../../sail-riscv/model/core/softfloat_interface.sail) |
| C | [sail-riscv/c_emulator/riscv_softfloat.cpp](../../sail-riscv/c_emulator/riscv_softfloat.cpp) |
| V | [sail-riscv/model/extensions/V/vext_fp_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_utils_insts.sail) |
| IR | [isla/rv64d.ir](../../isla/rv64d.ir) |
| Rust | [isla/isla-lib/src/primop/float.rs](../../isla/isla-lib/src/primop/float.rs) |

表中的 `R`=`bits(3)`（RISC-V/SoftFloat 舍入编码）；`F`=`bits(5)`（NV,DZ,OF,UF,NX）；`B16/B32/B64` 和 `bits(8/16)` 是原始位串。浮点或整数含义由函数名决定。`Bool` 是布尔值。`exact` 只控制 roundToInt 是否报告 NX，不改变舍入后的数值。

67 个外部 helper 当前都通过 `executor.rs:1196` 的名称分发进入 Rust `softfloat_call`。这是当前实现的位置，不应作为未来通用 primop 接口。下面每组的“需改”适用于组内每个名称；同组共享 Rust 分支已经逐段阅读，不能把名称覆盖视为数值或 flags 正确。

## 3. 67 个外部 helper：逐名清单

### 3.1 加减乘除：12 个

当前实现：Rust:1047 的 `SfOp::Bin`。通用计算分别使用 `fp.add/sub/mul/div`；原始位串分类、五个异常、canonical NaN 留在模型。

**需改：**必须补 Sail 函数体。必须修正 Sub 的 NX 误用 Add 公式；Add/Mul 等 NaN 或 invalid 结果不能额外报 NX；OF 不能只看结果为无穷大；UF 不能只看次正规；Div 的 NX 不能用 OF|UF 代替。全部带 R 的入口还受当前符号 RM 恒 RNE 错误影响。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_f16Add` | `(R, B16, B16) -> (F, B16)` | S:38 / IR:23726 | `softfloat_f16add`，C:16 |
| `riscv_f16Sub` | `(R, B16, B16) -> (F, B16)` | S:39 / IR:23728 | `softfloat_f16sub`，C:27 |
| `riscv_f16Mul` | `(R, B16, B16) -> (F, B16)` | S:40 / IR:23730 | `softfloat_f16mul`，C:38 |
| `riscv_f16Div` | `(R, B16, B16) -> (F, B16)` | S:41 / IR:23732 | `softfloat_f16div`，C:49 |
| `riscv_f32Add` | `(R, B32, B32) -> (F, B32)` | S:42 / IR:23741 | `softfloat_f32add`，C:60 |
| `riscv_f32Sub` | `(R, B32, B32) -> (F, B32)` | S:43 / IR:23743 | `softfloat_f32sub`，C:71 |
| `riscv_f32Mul` | `(R, B32, B32) -> (F, B32)` | S:44 / IR:23745 | `softfloat_f32mul`，C:82 |
| `riscv_f32Div` | `(R, B32, B32) -> (F, B32)` | S:45 / IR:23747 | `softfloat_f32div`，C:93 |
| `riscv_f64Add` | `(R, B64, B64) -> (F, B64)` | S:46 / IR:23756 | `softfloat_f64add`，C:104 |
| `riscv_f64Sub` | `(R, B64, B64) -> (F, B64)` | S:47 / IR:23758 | `softfloat_f64sub`，C:115 |
| `riscv_f64Mul` | `(R, B64, B64) -> (F, B64)` | S:48 / IR:23760 | `softfloat_f64mul`，C:126 |
| `riscv_f64Div` | `(R, B64, B64) -> (F, B64)` | S:49 / IR:23762 | `softfloat_f64div`，C:137 |

### 3.2 融合乘加：3 个

当前实现：Rust:1105 的 `SfOp::MulAdd`。数值用一次 `fp.fma`，不能拆成普通乘法再加法。

**需改：**必须补 Sail 函数体。补齐无穷乘积加反号无穷大的 NV 和 canonical NaN；精确计算 OF/UF/NX，移除当前 NX=OF|UF 近似。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_f16MulAdd` | `(R, B16, B16, B16) -> (F, B16)` | S:54 / IR:23764 | `softfloat_f16muladd`，C:148 |
| `riscv_f32MulAdd` | `(R, B32, B32, B32) -> (F, B32)` | S:55 / IR:23766 | `softfloat_f32muladd`，C:160 |
| `riscv_f64MulAdd` | `(R, B64, B64, B64) -> (F, B64)` | S:56 / IR:23768 | `softfloat_f64muladd`，C:172 |

### 3.3 开方：3 个

当前实现：Rust:1136 的 `SfOp::Sqrt`。数值用 `fp.sqrt`；sNaN、负数 invalid 和 canonical NaN 由模型处理。

**需改：**必须补 Sail 函数体。负 qNaN 不应仅因符号位为 1 就报 NV；NaN/负有限数导致的 invalid 不能额外报 NX；检查 -0 保留负号。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_f16Sqrt` | `(R, B16) -> (F, B16)` | S:61 / IR:23770 | `softfloat_f16sqrt`，C:184 |
| `riscv_f32Sqrt` | `(R, B32) -> (F, B32)` | S:62 / IR:23772 | `softfloat_f32sqrt`，C:194 |
| `riscv_f64Sqrt` | `(R, B64) -> (F, B64)` | S:63 / IR:23774 | `softfloat_f64sqrt`，C:204 |

### 3.4 浮点转 32/64 位整数：12 个

当前实现：Rust:1180 的 `SfOp::FpToI`。通用原语需要 `fp.roundToIntegral`、`fp.to_sbv/ubv`、比较和位操作。无效域返回值、NV 与 NX 优先级属于模型。

**需改：**必须补 Sail 函数体并重做范围判定。采用先按 RM 舍入到整数值、再检查目标范围的方案；比较边界要能精确表示，不能用 f16 构造 2^64。修正当前无符号 RDN 下 +0 被判越界、范围边界错误及 f16/f32→64 位界构造问题；NV 时 NX 不应同时置位。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_f16ToI32` | `(R, B16) -> (F, B32)` | S:68 / IR:23776 | `softfloat_f16toi32`，C:217 |
| `riscv_f16ToUi32` | `(R, B16) -> (F, B32)` | S:69 / IR:23778 | `softfloat_f16toui32`，C:229 |
| `riscv_f16ToI64` | `(R, B16) -> (F, B64)` | S:72 / IR:23784 | `softfloat_f16toi64`，C:241 |
| `riscv_f16ToUi64` | `(R, B16) -> (F, B64)` | S:73 / IR:23786 | `softfloat_f16toui64`，C:253 |
| `riscv_f32ToI32` | `(R, B32) -> (F, B32)` | S:77 / IR:23792 | `softfloat_f32toi32`，C:265 |
| `riscv_f32ToUi32` | `(R, B32) -> (F, B32)` | S:78 / IR:23794 | `softfloat_f32toui32`，C:276 |
| `riscv_f32ToI64` | `(R, B32) -> (F, B64)` | S:81 / IR:23800 | `softfloat_f32toi64`，C:287 |
| `riscv_f32ToUi64` | `(R, B32) -> (F, B64)` | S:82 / IR:23802 | `softfloat_f32toui64`，C:299 |
| `riscv_f64ToI32` | `(R, B64) -> (F, B32)` | S:85 / IR:23808 | `softfloat_f64toi32`，C:311 |
| `riscv_f64ToUi32` | `(R, B64) -> (F, B32)` | S:86 / IR:23810 | `softfloat_f64toui32`，C:323 |
| `riscv_f64ToI64` | `(R, B64) -> (F, B64)` | S:89 / IR:23816 | `softfloat_f64toi64`，C:335 |
| `riscv_f64ToUi64` | `(R, B64) -> (F, B64)` | S:90 / IR:23818 | `softfloat_f64toui64`，C:346 |

### 3.5 32/64 位整数转浮点：12 个

当前实现：Rust:1223 的 `SfOp::IFp`。数值用 signed/unsigned BV→FP 通用转换；OF/NX 在模型计算。

**需改：**必须补 Sail 函数体。修正负整数用 RTZ 与 RUP 比较会漏 NX；修正整数→f16 的溢出边界。i32/ui32→f64 应精确，i64/ui64→f64 不保证精确，不能整组统一置 NX=0。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_i32ToF16` | `(R, B32) -> (F, B16)` | S:70 / IR:23780 | `softfloat_i32tof16`，C:357 |
| `riscv_ui32ToF16` | `(R, B32) -> (F, B16)` | S:71 / IR:23782 | `softfloat_ui32tof16`，C:366 |
| `riscv_i64ToF16` | `(R, B64) -> (F, B16)` | S:74 / IR:23788 | `softfloat_i64tof16`，C:375 |
| `riscv_ui64ToF16` | `(R, B64) -> (F, B16)` | S:75 / IR:23790 | `softfloat_ui64tof16`，C:384 |
| `riscv_i32ToF32` | `(R, B32) -> (F, B32)` | S:79 / IR:23796 | `softfloat_i32tof32`，C:393 |
| `riscv_ui32ToF32` | `(R, B32) -> (F, B32)` | S:80 / IR:23798 | `softfloat_ui32tof32`，C:402 |
| `riscv_i64ToF32` | `(R, B64) -> (F, B32)` | S:83 / IR:23804 | `softfloat_i64tof32`，C:411 |
| `riscv_ui64ToF32` | `(R, B64) -> (F, B32)` | S:84 / IR:23806 | `softfloat_ui64tof32`，C:420 |
| `riscv_i32ToF64` | `(R, B32) -> (F, B64)` | S:87 / IR:23812 | `softfloat_i32tof64`，C:429 |
| `riscv_ui32ToF64` | `(R, B32) -> (F, B64)` | S:88 / IR:23814 | `softfloat_ui32tof64`，C:438 |
| `riscv_i64ToF64` | `(R, B64) -> (F, B64)` | S:91 / IR:23820 | `softfloat_i64tof64`，C:447 |
| `riscv_ui64ToF64` | `(R, B64) -> (F, B64)` | S:92 / IR:23822 | `softfloat_ui64tof64`，C:456 |

### 3.6 浮点格式转换：6 个

当前实现：Rust:1263/1284 的 `softfloat_fp_to_fp`。通用原语负责指定格式的转换；模型处理 sNaN、canonical NaN、OF/UF/NX。

**需改：**必须补 Sail 函数体。三种拓宽的有限数数值精确，仍需处理 sNaN；三种窄化需要修正 NaN 多报 NX、精确次正规多报 UF、定向溢出漏 OF、舍入到零漏 UF。`riscv_f32ToF16` 和 `riscv_f64ToF32` 还必须处理 RVV 的 ROD，不能把 rm=6 送进五种 RM 解码。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_f16ToF32` | `(R, B16) -> (F, B32)` | S:93 / IR:23824 | `softfloat_f16tof32`，C:465 |
| `riscv_f16ToF64` | `(R, B16) -> (F, B64)` | S:94 / IR:23826 | `softfloat_f16tof64`，C:476 |
| `riscv_f32ToF64` | `(R, B32) -> (F, B64)` | S:95 / IR:23828 | `softfloat_f32tof64`，C:487 |
| `riscv_f32ToF16` | `(R, B32) -> (F, B16)` | S:96 / IR:23830 | `softfloat_f32tof16`，C:498 |
| `riscv_f64ToF16` | `(R, B64) -> (F, B16)` | S:97 / IR:23832 | `softfloat_f64tof16`，C:509 |
| `riscv_f64ToF32` | `(R, B64) -> (F, B32)` | S:98 / IR:23834 | `softfloat_f64tof32`，C:520 |

### 3.7 f32 转 BF16：1 个

当前实现：Rust:1267 调用 `softfloat_fp_to_fp(F32,8,8,...)`。BF16 是指数 8 位、精度 8 位，不能作为 f16。

**需改：**必须补 Sail 函数体和可供模型调用的通用格式转换能力。typed IR 目前没有 BF16，需先验证纯 `fp32_to_bf16_bits` 等接口；canonical NaN 从原始输入判断后选择；异常计算修复同窄化组。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_f32ToBF16` | `(R, B32) -> (F, B16)` | S:99 / IR:23836 | `softfloat_f32tobf16`，C:531 |

### 3.8 比较：15 个

当前实现：Rust:1153 的 `SfOp::Cmp`；名称解析在 Rust:557-561。数值关系使用 `fp.lt/leq/eq`；原始输入用于 sNaN/qNaN 判断。

**需改：**必须补 Sail 函数体。Eq 和 Lt_quiet/Le_quiet 只对 sNaN 报 NV；Lt/Le 对任意 NaN 报 NV；其余四个异常为 0。当前 Eq 错按 signaling 比较处理 qNaN，必须修复；不要用 SMT 通用等号代替 IEEE `fp.eq`。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_f16Lt` | `(B16, B16) -> (F, Bool)` | S:104 / IR:23845 | `softfloat_f16lt`，C:542 |
| `riscv_f16Lt_quiet` | `(B16, B16) -> (F, Bool)` | S:105 / IR:23847 | `softfloat_f16lt_quiet`，C:553 |
| `riscv_f16Le` | `(B16, B16) -> (F, Bool)` | S:106 / IR:23849 | `softfloat_f16le`，C:564 |
| `riscv_f16Le_quiet` | `(B16, B16) -> (F, Bool)` | S:107 / IR:23851 | `softfloat_f16le_quiet`，C:575 |
| `riscv_f16Eq` | `(B16, B16) -> (F, Bool)` | S:108 / IR:23853 | `softfloat_f16eq`，C:586 |
| `riscv_f32Lt` | `(B32, B32) -> (F, Bool)` | S:109 / IR:23855 | `softfloat_f32lt`，C:597 |
| `riscv_f32Lt_quiet` | `(B32, B32) -> (F, Bool)` | S:110 / IR:23857 | `softfloat_f32lt_quiet`，C:608 |
| `riscv_f32Le` | `(B32, B32) -> (F, Bool)` | S:111 / IR:23859 | `softfloat_f32le`，C:619 |
| `riscv_f32Le_quiet` | `(B32, B32) -> (F, Bool)` | S:112 / IR:23861 | `softfloat_f32le_quiet`，C:630 |
| `riscv_f32Eq` | `(B32, B32) -> (F, Bool)` | S:113 / IR:23863 | `softfloat_f32eq`，C:641 |
| `riscv_f64Lt` | `(B64, B64) -> (F, Bool)` | S:114 / IR:23865 | `softfloat_f64lt`，C:652 |
| `riscv_f64Lt_quiet` | `(B64, B64) -> (F, Bool)` | S:115 / IR:23867 | `softfloat_f64lt_quiet`，C:663 |
| `riscv_f64Le` | `(B64, B64) -> (F, Bool)` | S:116 / IR:23869 | `softfloat_f64le`，C:674 |
| `riscv_f64Le_quiet` | `(B64, B64) -> (F, Bool)` | S:117 / IR:23871 | `softfloat_f64le_quiet`，C:685 |
| `riscv_f64Eq` | `(B64, B64) -> (F, Bool)` | S:118 / IR:23873 | `softfloat_f64eq`，C:696 |

### 3.9 舍入到整数值、结果仍为浮点：3 个

当前实现：Rust:1166 的 `SfOp::RoundToInt`。数值用 `fp.roundToIntegral`；C:707 等将第三个参数传给 SoftFloat 的 `exact`。

**需改：**必须补 Sail 函数体。保留 `exact=false` 抑制 NX、`exact=true` 按是否改变数值置 NX 的区别；sNaN 的 NV 不受 exact 抑制；canonical NaN、±0、±∞及符号 RM 都要验证。

| 函数 | 参数 → 返回 | 声明 / IR 声明 | C++ 实现 |
| --- | --- | --- | --- |
| `riscv_f16roundToInt` | `(R, B16, Bool) -> (F, B16)` | S:119 / IR:23875 | `softfloat_f16roundToInt`，C:707 |
| `riscv_f32roundToInt` | `(R, B32, Bool) -> (F, B32)` | S:120 / IR:23877 | `softfloat_f32roundToInt`，C:718 |
| `riscv_f64roundToInt` | `(R, B64, Bool) -> (F, B64)` | S:121 / IR:23879 | `softfloat_f64roundToInt`，C:729 |

## 4. 12 个已有 Sail/IR 函数体：逐名清单

这些函数已经在模型中，不应迁入 Isla 名称分发。六个窄整数转换依赖前面的 32 位整数 helper，其正确性会受底层修改影响；六个估算函数按 RISC-V 指定查表规则计算，不能用精确 `1/x` 或 `1/sqrt(x)` 替换。

| 函数 | 参数 → 返回 | Sail 函数体 / IR 函数体 | 处理意见 |
| --- | --- | --- | --- |
| `riscv_f16ToI16` | `(R, B16) -> (F, bits(16))` | V:379 / IR:65341 | 保留；32 位结果再检查窄范围并饱和。建议把纯选值改用通用 ITE；验证 NV 覆盖 NX、NaN、负无符号数及窄边界。 |
| `riscv_f16ToI8` | `(R, B16) -> (F, bits(8))` | V:386 / IR:65475 | 保留；32 位结果再检查窄范围并饱和。建议把纯选值改用通用 ITE；验证 NV 覆盖 NX、NaN、负无符号数及窄边界。 |
| `riscv_f32ToI16` | `(R, B32) -> (F, bits(16))` | V:393 / IR:65602 | 保留；32 位结果再检查窄范围并饱和。建议把纯选值改用通用 ITE；验证 NV 覆盖 NX、NaN、负无符号数及窄边界。 |
| `riscv_f16ToUi16` | `(R, B16) -> (F, bits(16))` | V:400 / IR:65729 | 保留；32 位结果再检查窄范围并饱和。建议把纯选值改用通用 ITE；验证 NV 覆盖 NX、NaN、负无符号数及窄边界。 |
| `riscv_f16ToUi8` | `(R, B16) -> (F, bits(8))` | V:406 / IR:65789 | 保留；32 位结果再检查窄范围并饱和。建议把纯选值改用通用 ITE；验证 NV 覆盖 NX、NaN、负无符号数及窄边界。 |
| `riscv_f32ToUi16` | `(R, B32) -> (F, bits(16))` | V:412 / IR:65849 | 保留；32 位结果再检查窄范围并饱和。建议把纯选值改用通用 ITE；验证 NV 覆盖 NX、NaN、负无符号数及窄边界。 |
| `riscv_f16Rsqrte7` | `(R, B16) -> (F, B16)` | V:463 / IR:66851 | 保留 RISC-V 查表与特殊值规则；验证全部类别、查表索引和次正规归一化，不新增专用浮点 primop。 |
| `riscv_f32Rsqrte7` | `(R, B32) -> (F, B32)` | V:479 / IR:66955 | 保留 RISC-V 查表与特殊值规则；验证全部类别、查表索引和次正规归一化，不新增专用浮点 primop。 |
| `riscv_f64Rsqrte7` | `(R, B64) -> (F, B64)` | V:494 / IR:67059 | 保留 RISC-V 查表与特殊值规则；验证全部类别、查表索引和次正规归一化，不新增专用浮点 primop。 |
| `riscv_f16Recip7` | `(R, B16) -> (F, B16)` | V:567 / IR:68225 | 保留 RISC-V 查表与特殊值规则；验证全部类别、查表索引和次正规归一化，不新增专用浮点 primop。 |
| `riscv_f32Recip7` | `(R, B32) -> (F, B32)` | V:583 / IR:68429 | 保留 RISC-V 查表与特殊值规则；验证全部类别、查表索引和次正规归一化，不新增专用浮点 primop。 |
| `riscv_f64Recip7` | `(R, B64) -> (F, B64)` | V:599 / IR:68633 | 保留 RISC-V 查表与特殊值规则；验证全部类别、查表索引和次正规归一化，不新增专用浮点 primop。 |

具体依赖：`riscv_f16ToI16`、`riscv_f16ToI8` 使用 `riscv_f16ToI32`；`riscv_f32ToI16` 使用 `riscv_f32ToI32`；三个无符号对应函数使用相同格式的 `ToUi32`。`riscv_f*Rsqrte7` 使用 V:419 的 `rsqrt7`；`riscv_f*Recip7` 使用 V:510 的 `recip7`。

## 5. 必须补进计划的 round-to-odd

来源：[vext_fp_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_insts.sail):746-750：

```text
FNV_CVT_ROD_F_F:
  16 => riscv_f32ToF16(0b110, input)
  32 => riscv_f64ToF32(0b110, input)
```

这不是非法 `frm` 值漏过检查。`frm` 合法性检查在指令层；这里是该指令明确向 SoftFloat 接口传入它的 round-to-odd 编码。SoftFloat 构建文件 [CMakeLists.txt](../../sail-riscv/dependencies/softfloat/CMakeLists.txt):53 明确启用 `SOFTFLOAT_ROUND_ODD`。

当前 Rust:737 `rm_smt` 只接受 0..4。传入具体 6 时 `RM_MODES.get(6)` 失败并 panic；若内部编码以符号 BV 表示，额外断言也会排除 6。**这是静态确认的接口缺口，尚未运行指令复现。**

建议处理：模型区分“普通五种舍入”与“ROD 窄化”。ROD 数值规则可从朝零窄化出发：对非精确有限结果，将结果有效数的最低位置 1；必须单独核对下溢到零、溢出、NaN 和 flags。底层仍使用通用转换、位操作和 ITE，不把编码 6 硬塞进 Z3 的五种 `RoundingMode`。若以后多种 ISA 确实需要相同语义，可再讨论通用派生转换原语；首次实现放共享 Sail 函数即可。

验收增加：`vfncvt.rod.f.f.w` 的 f32→f16 和 f64→f32 必须单列，检查精确值保持不变、非精确值最低位为 1，以及结果与全部 flags 对照 SoftFloat。不能只做五种普通 RM 测试。

## 6. 标量、RVV、Zfa、BF16 的外侧支撑函数

本节补充 79 个 helper 之外的模型代码。其职责归属和主要检查点如下；这些条目也不能算已通过动态测试。

以下路径前缀均为 `sail-riscv/model/extensions/`。名称中的 `{H,S,D}` 表示三个明确格式的同族函数，`{16,32,64}` 同理；不表示额外未实现格式。

### 6.1 舍入、寄存器和位串辅助

| 函数或函数族、位置 | 当前作用 | 是否要改、理由 |
| --- | --- | --- |
| `encdec_rounding_mode`、`valid_rounding_mode`、`select_instr_or_fcsr_rm` — `FD/fext_insts.sail:31,49,51` | 3 位编码与 ISA 枚举互转；选择指令 rm 或 CSR frm；处理保留编码 | **保留模型。**新增 typed RM 转换在合法性处理之后调用；不能用 solver 约束直接删去非法指令状态。ROD 的内部编码另按第 5 节处理。 |
| `nxFlag/ufFlag/ofFlag/dzFlag/nvFlag` — `FD/fext_insts.sail:68` | RISC-V 的五位布局 | **保留模型。**共享异常 Bool 明确按 NV,DZ,OF,UF,NX 打包。 |
| `write_fcsr`、`accrue_fflags` — `FD/fdext_regs.sail:514,521`；CSR 处理 — `FD/fdext_control.sail:18` | flags 累计、FS、CSR callback、权限和扩展开关 | **保留模型并验证。**含状态更新；不是可放在提前求值 ITE 两臂中的纯函数。测旧 flags OR 本次 flags、FS 和回调行为。 |
| `canonical_NaN`、`canonical_NaN_H/S/D/Q`、`canonical_NaN_BF16` — `FD/fdext_regs.sail:20,30,33` | RISC-V 规定的 NaN 位串 | **保留模型。**不放入通用 FP→bits 原语。存在 Q 的常量不表示本次已提供 Q 算术。 |
| `nan_box/nan_unbox` — `FD/fdext_regs.sail:40,48`；`rF_BF16/wF_BF16` — `:294,303` | 窄值写入补 1；不合法 boxing 按指定格式读为 canonical NaN | **保留模型。**纯选值适合用 ITE；BF16 NaN 是 `0x7fc0`，不能混用 f16 的 `0x7e00`。 |
| `rF/wF/get_F_bits/set_F_bits`、`rF_H/S/D`、`wF_H/S/D`、`rF_or_X_H/S/D`、`wF_or_X_H/S/D` — `FD/fdext_regs.sail:122,163,251,261,307,348,378` | 寄存器布局、F/Zfinx 路径、RV32 寄存器对 | **保留模型并验证。**不能改为纯浮点转换，不能破坏原始 NaN 位串。 |
| `fsplit_H/S/D`、`fmake_H/S/D` — `FD/zfh_insts.sail:31`、`fext_insts.sail:78`、`dext_insts.sail:36` | 原始位串拆分、组合 | **保留或共享 Sail 纯函数。**现有 BV 截取和拼接已够用，无须新增 ISA primop。 |
| `f_is_{neg_inf,neg_norm,neg_subnorm,neg_zero,pos_zero,pos_subnorm,pos_norm,pos_inf,SNaN,QNaN,NaN}_{H,S,D}` — H `:43`、S `:86`、D `:44`；V 同名无格式后缀族 — `V/vext_fp_utils_insts.sail:57` | 从 bits 分类，含 sNaN/qNaN | **保留或共享 Sail 纯函数。**普通分类可调用通用 FP 原语，但 sNaN/qNaN 必须看原始 bits，没有必要强制重写所有分类。 |
| `negate_H/S/D`、`negate_fp` — H `:37`、S `:165`、D `:124`、V utils `:171` | 翻转符号位，为 FMA 变体准备输入 | **保留位操作；S/D 可改进。**现有符号位 `if` 可换成 XOR/ITE。不要经 FP→bits 往返而丢失 NaN 编码。 |

### 6.2 标量比较、取最值、分类和 Zfa

| 函数或指令族、位置 | 当前作用 | 是否要改、理由 |
| --- | --- | --- |
| `feq_quiet_S/D`、`flt_S/D` — `FD/fext_insts.sail:171,187`、`dext_insts.sail:130,146` | 旧位串比较辅助 | **有问题，但当前无调用。**`feq_quiet` 对同编码 NaN 返回 true；`flt(-0,+0)` 返回 true。全模型搜索仅有定义，不能说现行 FEQ/FLT 指令因此错误；后续不得直接复用这些函数，应修正或明确弃用。 |
| `fle_H/S/D` — H `:119`、S `:217`、D `:176` | 位串 ≤ 比较与 quiet/signaling NV；供 MIN/MAX 使用 | **建议调整。**数值部分改用通用 `fp.leq`，flags 留模型。当前返回 Bool 对 NaN 不是完整 IEEE 比较；MIN/MAX 外层先选择 NaN 结果，因而不能据此直接认定当前 MIN/MAX 错误。 |
| `FMIN/FMAX_{H,S,D}` — H `:375,395`、S `:786,806`、D `:718,738`；`fp_min/fp_max` — V utils `:203,222` | 一个 NaN 取另一数；两个 NaN 取 canonical；±0 定向选择；sNaN 置 NV | **保留规则，纯选值可改 ITE。**不能只用原生 min/max 而遗漏 RISC-V 对 NaN 和 ±0 的要求。 |
| `FMINM/FMAXM_{H,S,D}` — `FD/zfa_insts.sail:174,205,236,267,298,329` | 任一 NaN 都返回 canonical | **保留独立规则。**与普通 MIN/MAX 不同；共用基础比较即可，不应错误合并行为。 |
| `FSGNJ/FSGNJN/FSGNJX_{H,S,D}` — H `:342`、S `:753`、D `:684`；V 的 `FVVTYPE/FVFTYPE` — `V/vext_fp_insts.sail:36,949` | 复制、取反、XOR 符号位 | **保留 bits 操作。**不产生 flags，NaN payload 必须保留，无须新 FP primop。 |
| `FCLASS_{H,S,D}` — H `:812`、S `:912`、D `:846`；`VFUNARY1` — `V/vext_fp_insts.sail:812` | 使用 `float_classify/float_class_onehot_bits` 输出 RISC-V 十位分类 | **保留输出编码。**分类可共享，sNaN/qNaN 仍看原始 bits。入口还包括 `model/core/float_classify.sail:10`。 |
| `LOAD_FP/STORE_FP` — `FD/fext_insts.sail:280,316`；`FMV_X_H/H_X/X_W/W_X/X_D/D_X`；`FMVH_X_D/FMVP_D_X` — `FD/zfa_insts.sail:533,553` | 访存、搬运、boxing、符号扩展 | **保留模型并验证。**不能走数值转换；区分“原始搬运”和“作为运算输入”的不合法 boxing 行为。 |
| `FLI_H/S/D` — `FD/zfa_insts.sail:22,72,122` | 指令规定的常量表 | **保留模型。**表选择使用通用 BV/ITE 即可，无须新 IEEE 数值原语。 |
| `FROUND/FROUNDNX_{H,S,D}` — `FD/zfa_insts.sail:360,389,418,447,476,505` | 调用 roundToInt；false/true 控制 NX 报告 | **接第 3.9 节的新函数体。**同输入两类指令结果相同，NX 可能不同；数值用 `roundToIntegral`，NX 开关、NV 和 NaN 选择留模型。 |
| `FLEQ/FLTQ_{H,S,D}` — `FD/zfa_insts.sail:581,606,631,656,682,707`；标量 `FEQ/FLT/FLE` | quiet/signaling 比较指令 | **继续模型包装。**基础比较 Bool 共用 Z3 操作，NV 规则分别处理；测试 qNaN/sNaN。 |
| `fcvtmod_helper`、`FCVTMOD_W_D` — `FD/zfa_insts.sail:724,788` | 朝零截断，整数结果模 2^32；越界 NV，NaN/inf 返回零，NV 优先于 NX | **保留模型算法，纯选值可改 ITE。**不能直接用 `fp.to_sbv 32` 替换，它不保证越界时的模结果。测 ±2^31、2^32、2^84 附近及分数。 |

### 6.3 RVV、估算及 BF16

| 函数或指令族、位置 | 当前作用 | 是否要改、理由 |
| --- | --- | --- |
| `valid_fp_op`、`illegal_fp_normal/vd_masked/vd_unmasked/variable_width/reduction/widening_reduction` — V utils `:16,24,29,34,39,45,50` | SEW、FRM、寄存器与 vstart 等合法性 | **保留模型。**这些是真正的非法指令控制流。`get_fp_rounding_mode:167` 当前仅有定义，不是唯一舍入模式入口。 |
| `get_scalar_fp` — V utils `:157` | 按 SEW 读标量及 unbox | **保留模型。**unbox 产生的输入与执行元素是否产生 flags 分开处理。 |
| `fp_add/sub/mul/div/muladd/nmuladd/mulsub/nmulsub/widen` — V utils `:181,192,298,309,320,331,343,355,368` | 按位宽调用 helper，随即累计 flags | **保留外层状态处理，内部接新纯 helper。**这些 Sail `fp_*` 含 CSR 副作用，不是纯 Isla operator；不能直接放进提前求值的 ITE 两臂。 |
| `fp_eq/gt/ge/lt/le` — V utils `:241,252,264,276,287` | 比较并累计 flags；gt/ge 借 NV 避免将 NaN unordered 取反为 true | **保留包装，建议调整 gt/ge 数值表达式。**可用原生 >、≥，NV 单独计算，无需靠 `fflags == 0b10000` 推导 Bool。 |
| 六个窄整数转换和六个估算函数 — 第 4 节 | 窄范围返回规则，或 RISC-V 查表估算 | **留在模型。**底层位操作和纯选值复用通用 primop/ITE；不添加 RISC-V 专用算子。 |
| `rsqrt7/recip7` — V utils `:419,510` | 指定表、索引及次正规归一化 | **保留算法并验证。**表查找、前导零、选值可改进，不能换成精确除法/开方。 |
| `FVVTYPE/FVVMATYPE/FWVVTYPE/FWVVMATYPE/FWVTYPE/FVFTYPE/FVFMATYPE/FWVFTYPE/FWVFMATYPE/FWFTYPE` — `V/vext_fp_insts.sail:36,121,197,269,340,949,1053,1128,1199,1269` | 逐元素算术、宽化和 FMA | **保留调度、mask、写回和 flags 累计。**当前计算在活动元素分支内，重构不能提前执行带副作用包装。 |
| `VFUNARY0/VFWUNARY0/VFNUNARY0/VFUNARY1` — `V/vext_fp_insts.sail:412,533,669,812` | 整数/浮点普通、宽化、窄化转换；开方、估算、分类 | **逐子操作验证。**ROD 需要第 5 节所述新处理，不能只检查 67 个名称都能分发。 |
| `FVVMTYPE/FVFMTYPE` — `V/vext_fp_vm_insts.sail:31,104` | 比较写入 mask，VMFNE 由 EQ 取反 | **保留模型。**qNaN 的 NE=true/NV=false，sNaN 置 NV；被屏蔽元素不能累计 NV。 |
| `RFVVTYPE/RFWVVTYPE` — `V/vext_fp_red_insts.sail:30,106` | 归约；当前有序、无序均顺序累加，宽化归约先拓宽 | **保留当前求和顺序并验证。**有序归约检查规定顺序；无序归约允许不同合法求和树，DUT 用不同归约树时，不能只因末位不同就判错误。测 vl=0、没有活动源元素、NaN 和 flags。 |
| `VFMVFS/VFMERGE/VFMV/VFMVSF` — `V/vext_fp_insts.sail:897,1333,1394,1439` | 向量/标量搬运和 mask 选择 | **保留 bits，复用通用选择。**不引入数值转换或计算 flags。 |
| `fsplit_BF16/fmake_BF16/bf16_to_f32/bf16_to_f32_set_flags` — `bfloat16/zfbfmin_utils.sail:9,11,13,27` | BF16 位串拓宽、canonical NaN、sNaN NV；`set_flags` 版本还会累计状态 | **保留纯位串转换，必须修 VF 调用位置。**有限 BF16→f32 拼接即可精确表达，无须为此添加 typed BF16；带 `set_flags` 的函数有副作用，不能放进 ITE 候选值。 |
| `FCVT_BF16_S/FCVT_S_BF16`、`VFNCVTBF16_F_F_W/VFWCVTBF16_F_F_V`、`VFWMACCBF16_VV/VF` — `bfloat16/zfbfmin_insts.sail:20,45`、`zvfbfmin_insts.sail:18,71`、`zvfbfwma_insts.sail:18,71` | BF16 标量/向量转换和 f32 融合累加 | **f32→BF16 补通用转换；VF 的 flags 累计位置必须修正。**详情如下。 |

### 6.4 本次新确认：无活动元素时 BF16 VF 仍会置 NV

[zvfbfwma_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail):102 在 `VFWMACCBF16_VF` 的循环和 `if mask[i] == 0b1` 之前，执行：

```sail
let rs1_val = bf16_to_f32_set_flags(F_BF16(rs1));
```

`bf16_to_f32_set_flags` 在 [zfbfmin_utils.sail](../../sail-riscv/model/extensions/bfloat16/zfbfmin_utils.sail):27 调用 `accrue_fflags`；合法 boxed BF16 sNaN（例如低 16 位 `0x7f81`）会立即置 NV。

`init_masked_result_default` 及 SYMBOLIC 版本（[vext_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_utils_insts.sail):298,361）在合法 `vl=0` 或 mask 全零时仍返回 `Ok`，活动 mask 为零；不会阻止上述累计。因此，在 SEW/LMUL/FRM 合法、`vstart=0`、初始 `fflags=0` 的条件下，**没有任何活动元素，标量 sNaN 仍会使 NV 变成 1**。

这属于 Sail 模型的调用位置错误，与 Isla 是否使用原生 FP 无关。建议先加上述定向回归，再把标量转换改为纯 `(flags,value)`，仅在活动元素执行时累计 flags；或先将转换移入活动元素分支。VV 版本 `:52` 的相同转换已经位于 mask 内。

这是静态控制流确认，尚未运行动态复现。后续 ITE 优化必须保留这类“没有执行就不产生 flags”的行为。

## 7. 实施参考顺序与验证边界

1. 补齐公开通用 primop 及具体值/符号值入口；不新增 `riscv_*` primop。
2. 在 Sail 中保留这 67 个 helper 的签名和 C++ 绑定，逐步增加 SYMBOLIC 函数体。B 阶段按计划先用一个完整比较样本，以及不同名、只返回 bits 的隔离加法演示验证 Sail→IR→Isla；正式加法在 C 阶段具备完整 flags 后才迁移，不安装残缺的正式 helper。
3. 按第 3 节补数值、异常和结果选择；ROD 窄化必须与普通五种 RM 分开。
4. 12 个已有函数体和第 6 节支撑函数留在模型，补定向测试；有纯条件选择导致多路径时，再改成通用 ITE。寄存器写入、flags 累计、异常处理不能作为提前求值的 ITE 两臂。
5. 新 IR 中确认 79 个 helper 都有预期实现，并确认不再依赖 `executor.rs` 的 RISC-V 名称分发后，才删除旧 Rust 特判。
6. 对有同语义 SoftFloat API 的第 3 节 helper 逐操作对照结果 bits 与五个异常；固定 RISC-V specialization、after-rounding tininess，ROD 两项另启用 ROD。Recip7/Rsqrte7、FCVTMOD、mask/状态及无序归约分别按上文规范和模型测试；比较和精确位操作无需套用浮点误差容限。
7. 完整指令另测标量、RVV、Zfa、BF16；`make solve` 默认不含 FD_FLOAT，不能拿默认任务完成当浮点完成。覆盖到源码但在所用配置禁用的扩展，要明确记为未运行。

本次没有修改 Sail、Rust、IR 或配置，也没有构建或运行浮点功能测试。参考清单服务于后续逐项实施；源码修复、模型迁移和功能通过分别记录。
