# SoftFloat 独立参考 oracle

此命令行工具直接调用仓库随附的 Berkeley SoftFloat API，不调用 Isla 或 Sail 的符号实现，也不用待测模型的公式计算预期标志。构建复用 Sail-RISC-V C++ 模拟器所用的 SoftFloat 源码、RISC-V 专用配置和编译选项。每次调用前清除异常标志、设置舍入方式，并显式指定**舍入后检测下溢**。

## 构建与定向检查

从仓库根目录执行；构建和运行产物都放在仓库外的临时目录：

```sh
ORACLE_BUILD_DIR=$(mktemp -d)
cmake -S agents/float_support_review/oracle -B "$ORACLE_BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$ORACLE_BUILD_DIR" -j 12
ORACLE_BIN="$ORACLE_BUILD_DIR/oracle" python3 agents/float_support_review/oracle/smoke.py
```

本目录的 CMake 文件引入 `sail-riscv/dependencies/softfloat/CMakeLists.txt`，因此参考库使用其 `RISCV` 专用源码和头文件目录，以及 `SOFTFLOAT_ROUND_ODD`、`SOFTFLOAT_FAST_INT64`、`SOFTFLOAT_FAST_DIV32TO16`、`SOFTFLOAT_FAST_DIV64TO32`、`INLINE_LEVEL=5`。每次差分验证都应记录 Sail-RISC-V commit、编译器版本和构建选项。

## 命令接口

一次调用执行一次 SoftFloat 运算，输出一行 JSON。输入是带 `0x` 前缀、位宽不超过格式宽度的**原始位串**；有符号整数输入使用二进制补码。无效参数导致非零退出状态，不输出 JSON。JSON 包含操作 `op`、源格式 `fmt`、实际结果格式 `dst`、固定位宽十六进制 `result_bits`、五位 `flags`（`0x00`–`0x1f`）和布尔值 `NV`、`DZ`、`OF`、`UF`、`NX`。标志位从 bit 4 到 bit 0 按 RISC-V 顺序排列。

| `--op` | `--fmt` | 其他必需参数 | `--dst` |
| --- | --- | --- | --- |
| `add`、`sub`、`mul`、`div` | `f16`、`f32`、`f64` | `--rm`、`--a`、`--b` | 不允许 |
| `sqrt` | `f16`、`f32`、`f64` | `--rm`、`--a` | 不允许 |
| `fma` | `f16`、`f32`、`f64` | `--rm`、`--a`、`--b`、`--c` | 不允许 |
| `eq`、`lt`、`le`、`eq_signaling`、`lt_quiet`、`le_quiet` | `f16`、`f32`、`f64` | `--a`、`--b` | 不允许；结果为一位 `bool` |
| `round` | `f16`、`f32`、`f64` | `--rm`、`--a`、`--exact 0\|1` | 不允许 |
| `fp_to_int` | `f16`、`f32`、`f64` | `--rm`、`--a`、`--dst` | `i32`、`u32`、`i64`、`u64` |
| `int_to_fp` | `i32`、`u32`、`i64`、`u64` | `--rm`、`--a`、`--dst` | `f16`、`f32`、`f64` |
| `fp_to_fp` | `f16`、`f32`、`f64`、`bf16` | `--rm`、`--a`、`--dst` | 仅支持 `f16→f32/f64`、`f32→f16/f64/bf16`、`f64→f16/f32`、`bf16→f32` |

`--rm` 的取值：`0` RNE、`1` RTZ、`2` RDN、`3` RUP、`4` RMM。`6` ROD 仅用于 `fp_to_fp` 的 `f32→f16` 或 `f64→f32`，对应模型中的两种实际调用。此 oracle 直接使用 SoftFloat 的 ROD 模式；符号模型则由向零转换和最低位置位派生该结果。`--exact` 指定 `round` 是否报告 NX；FP 转整数固定报告不精确异常。

例如：

```sh
"$ORACLE_BUILD_DIR/oracle" --op add --fmt f32 --rm 0 --a 0x3f800000 --b 0x3f800000
"$ORACLE_BUILD_DIR/oracle" --op fp_to_fp --fmt f32 --dst f16 --rm 6 --a 0x3f800800
```

第二条命令返回 `0x3c01`，并置 NX。定向样例还包含两种 ROD 转换、BF16 转换、整数转换溢出、sNaN、FMA 无效操作，以及最终舍入到 f16 最小正规数却仍同时置 UF 和 NX 的边界。

## 适用范围

结果只代表所给原始位串的 SoftFloat API 运算，适合核对迁移中的 67 个 helper 的相应数值操作和五个标志，包括 RISC-V 默认 NaN 位模式。单独运行 oracle 无法证明指令译码、NaN boxing、寄存器写回、mask/vstart 或 CSR 累计。FCVTMOD、Recip7/Rsqrte7、六个窄整数包装和无序归约必须按各自指令规则建立参考，不能直接把此工具的普通 SoftFloat 运算结果当成预期。SoftFloat 源码或构建选项变化后，应重建并重新差分。
