# FLI 常量编号文本的 GNU / LLVM 差异

2026-10-17。针对 `1a135b24` 的用户追问，核对官方文档及实际工具行为。结论：不能称 GNU 和 LLVM 都拒绝 `fli.s f0, 0x10`。本次 GNU 接受它，但按数值 16.0 编码，而非按表索引16编码；LLVM 拒绝整数形式。该提交仍有必要：标准常量文本既避免 LLVM 报错，也避免 GNU 静默改变指令。

## 范围与结果

独立单行汇编探针，不依赖当前 dirty Sail 模型或 IR。工具为 GCC 14.2.0、GNU as 2.45.50.20251209 和 2.46、LLVM/Clang 22.1.8。每种文本运行两版 GNU as、GCC、llvm-mc 和 Clang，共15次；返回值、诊断及成功编码全部符合下表。完整命令和输出见 [机器记录](fli-syntax-20261017.json)。这是汇编/编码检查的限定 PASS，没有运行浮点数值模型或硬件。

| 文本 | 两版 GNU as / GCC | LLVM MC / Clang | 编码索引 / 数值 |
| --- | --- | --- | --- |
| `fli.s f0, 0x10` | 成功，机器字 `f01c8053` | 退出1，`invalid floating point immediate` | GNU索引25 / 16.0 |
| `fli.s f0, 1.0` | 成功，机器字 `f0180053` | 成功，同一机器字 | 索引16 / 1.0 |
| `fli.s f0, 16.0` | 成功，机器字 `f01c8053` | 成功，同一机器字 | 索引25 / 16.0 |

复现命令（输出放入新建的外部目录）：

```sh
: "${FLI_PROBE_OUT:?set a fresh external output directory}"
printf 'fli.s f0, 0x10\n' > "$FLI_PROBE_OUT/probe.s"
riscv64-unknown-elf-as -march=rv64gc_zfa -o "$FLI_PROBE_OUT/probe.o" "$FLI_PROBE_OUT/probe.s"
riscv64-unknown-elf-objdump -d -M numeric,no-aliases "$FLI_PROBE_OUT/probe.o"
riscv64-unknown-elf-gcc -march=rv64gc_zfa -c "$FLI_PROBE_OUT/probe.s" -o "$FLI_PROBE_OUT/gcc.o"
llvm-mc -triple=riscv64 -mattr=+f,+zfa -show-encoding "$FLI_PROBE_OUT/probe.s"
clang --target=riscv64 -march=rv64gc_zfa -c "$FLI_PROBE_OUT/probe.s" -o "$FLI_PROBE_OUT/clang.o"
```

将输入改为 `1.0` 和 `16.0` 即得两组对照。GNU objdump 将16.0打印为 `0x1p+4`，1.0打印为 `0x1p+0`。另做的探索性测试中，GNU接受整数 `16`、LLVM拒绝；两者均接受十六进制浮点写法 `0x1p+0`，该项未纳入15次机器记录。

## 官方依据

- [RISC-V Zfa 标准](https://docs.riscv.org/reference/isa/v20260120/unpriv/zfa.html)：表中 `rs1=16` 对应1.0，`rs1=25` 对应16；汇编参数描述浮点常量，不能将机器字段索引直接替代参数。
- [GNU as 手册 RISC-V Floating Point](https://sourceware.org/binutils/docs/as/RISC_002dV_002dFloating_002dPoint.html)：列出十进制/十六进制浮点表示，明确说明用 `strtof()` 解析参数，再与内置常量比较。手册没有逐字列出 `0x10` 示例，是否接受由本次实测确认。
- [LLVM RISC-V 文档](https://llvm.org/docs/RISCVUsage.html)：列出Zfa支持，但未逐项规定这里的词法规则。精确规则由官方 [release/22.x RISCVAsmParser.cpp](https://github.com/llvm/llvm-project/blob/release/22.x/llvm/lib/Target/RISCV/AsmParser/RISCVAsmParser.cpp#L2036) 的 `parseFPImm()` 确认：特殊标识符之外须为 `AsmToken::Real`，否则报 `invalid floating point immediate`。本次22.1.8实际诊断一致。

历史104项测试仅采用 LLVM，仍按当时范围有效，不能从该结果外推GNU同样报错。现行结论补充在原有发现之后，不改写历史结果。未修改 Sail-RISC-V 源码、索引、HEAD 或父 gitlink。

## 2026-10-18 四个小常量的可读写法

用户询问索引2至5的长小数是否正确及是否有更易读的形式。用Python `Fraction` 精确检查十进制普通/科学计数文本与对应二次幂相等，再对每个索引的三种形式运行GNU as2.45.50.20251209与LLVM MC22.1.8。24次独立 `fli.s f0, TOKEN` 汇编均成功，机器码均保留原索引；GNU产物经objdump检查，LLVM读取show-encoding结果。完整命令、诊断及编码见 [24次记录](fli-literals-20261018.json)。未修改生产映射或预期文本，未验FLI.H/D或运行硬件。

| 索引 | 原文本（精确值） | 科学计数法 | 推荐的十六进制浮点文本 |
| --- | --- | --- | --- |
| 2 | `0.0000152587890625` = 1/65536 | `1.52587890625e-5` | `0x1p-16` |
| 3 | `0.000030517578125` = 1/32768 | `3.0517578125e-5` | `0x1p-15` |
| 4 | `0.00390625` = 1/256 | `3.90625e-3` | `0x1p-8` |
| 5 | `0.0078125` = 1/128 | `7.8125e-3` | `0x1p-7` |

`0x1p-16` 表示1×2^-16；`p` 后是以2为底的指数。它与纯整数十六进制 `0x10` 的词法形式和含义不同。GNU官方手册已有 `0x1p-4` 示例。本轮仅确认推荐写法，未获要求改生产源码；未来采用时应同步汇编文本预期表并复跑104项回归和32项mapping往返。
