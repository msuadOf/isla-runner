# FD_FLOAT 89 项动态验收索引

> 2026-09-26 最终C1复验：正式V128 IR已更新为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。原归档输入在新IR上按24组重跑，1509条定向样例全部通过，clause集合仍恰为77个RV64非访存项；另有BF16非法LMUL10例。最终命令/哈希/原始输出见[IR验证](ir-refresh.md)。下文旧c9e1bfe2证据保留原时点，未重跑范围不自动转记新版本。

更新日期：2026-09-26。本表按[静态 clause 矩阵](clause-matrix.md)的固定 89 项顺序记录动态证据。`具体样例 PASS`仅指所列真实编码和初态通过，不代表同名 clause 的所有 enum、RM、SEW、mask 或异常域。逐项执行命令、IR/配置/runner 哈希及失败史见各证据包；正式状态摘要见[议题状态](status.md)。

当前：77 个 RV64 非访存 clause 各至少一条真实编码样例 PASS；两项 RV32 Zfa 非访存指令有隔离具体样例 PASS。10 个浮点访存 clause 依赖独立内存分支，本浮点任务不验收其读写或状态，不计入已通过数。完整E仍有全量回归与部分输入域待验证。

| # | Clause | 当前动态证据 | 尚需闭合 |
| ---: | --- | --- | --- |
| 1 | `C_FLD` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 2 | `C_FLDSP` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 3 | `C_FLW` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 4 | `C_FLWSP` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 5 | `C_FSD` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 6 | `C_FSDSP` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 7 | `C_FSW` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 8 | `C_FSWSP` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 9 | `FCVTMOD_W_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作；模转换边界与flags按证据继续补 |
| 10 | `FCVT_BF16_S` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 标量转换的适用RM、NaN/boxing边界按证据说明；无向量活动lane |
| 11 | `FCVT_S_BF16` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 标量转换的适用RM、NaN/boxing边界按证据说明；无向量活动lane |
| 12 | `FLEQ_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 13 | `FLEQ_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 14 | `FLEQ_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 15 | `FLI_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 32个立即数索引已逐项测；扩展guard与非法编码边界待核 |
| 16 | `FLI_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 32个立即数索引已逐项测；扩展guard与非法编码边界待核 |
| 17 | `FLI_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 32个立即数索引已逐项测；扩展guard与非法编码边界待核 |
| 18 | `FLTQ_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 19 | `FLTQ_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 20 | `FLTQ_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 21 | `FMAXM_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | NaN位置、sNaN与±0已有加强样例；其他输入域待补 |
| 22 | `FMAXM_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | NaN位置、sNaN与±0已有加强样例；其他输入域待补 |
| 23 | `FMAXM_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | NaN位置、sNaN与±0已有加强样例；其他输入域待补 |
| 24 | `FMINM_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | NaN位置、sNaN与±0已有加强样例；其他输入域待补 |
| 25 | `FMINM_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | NaN位置、sNaN与±0已有加强样例；其他输入域待补 |
| 26 | `FMINM_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | NaN位置、sNaN与±0已有加强样例；其他输入域待补 |
| 27 | `FMVH_X_D` | RV32隔离具体样例PASS： [实施记录](implementation.md) | 公共RV32 solve-state入口仍panic |
| 28 | `FMVP_D_X` | RV32隔离具体样例PASS： [实施记录](implementation.md) | 公共RV32 solve-state入口仍panic |
| 29 | `FROUNDNX_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 30 | `FROUNDNX_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 31 | `FROUNDNX_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 32 | `FROUND_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 33 | `FROUND_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 34 | `FROUND_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 固定子操作的适用RM/NaN/flags与非法编码按证据继续补 |
| 35 | `FVFMATYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 36 | `FVFMTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 37 | `FVFTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 38 | `FVVMATYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 39 | `FVVMTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 40 | `FVVTYPE` | RV64具体样例PASS： [FVVTYPE专属证据](tools/e_fvvtype_cases/RESULTS.md) 与 [mask/vstart证据](tools/e_nonmem/RESULTS.md) | 9个enum×3种SEW及IEEE边界已有样例；其他RM、mask/vstart组合待补 |
| 41 | `FWFTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 42 | `FWVFMATYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 43 | `FWVFTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 44 | `FWVTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 45 | `FWVVMATYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 46 | `FWVVTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 47 | `F_BIN_F_TYPE_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 48 | `F_BIN_F_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 49 | `F_BIN_RM_TYPE_D` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 未列出的格式、RM与活动元素组合仍待核 |
| 50 | `F_BIN_RM_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 51 | `F_BIN_RM_TYPE_S` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 未列出的格式、RM与活动元素组合仍待核 |
| 52 | `F_BIN_TYPE_F_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 53 | `F_BIN_TYPE_X_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 54 | `F_BIN_X_TYPE_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 55 | `F_BIN_X_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 56 | `F_MADD_TYPE_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 57 | `F_MADD_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 58 | `F_MADD_TYPE_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 59 | `F_UN_F_TYPE_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 60 | `F_UN_F_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 61 | `F_UN_RM_FF_TYPE_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 62 | `F_UN_RM_FF_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 63 | `F_UN_RM_FF_TYPE_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 64 | `F_UN_RM_FX_TYPE_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 65 | `F_UN_RM_FX_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 66 | `F_UN_RM_FX_TYPE_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 67 | `F_UN_RM_XF_TYPE_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 68 | `F_UN_RM_XF_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 69 | `F_UN_RM_XF_TYPE_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 70 | `F_UN_TYPE_F_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 71 | `F_UN_TYPE_X_S` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 72 | `F_UN_X_TYPE_D` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 73 | `F_UN_X_TYPE_H` | RV64具体样例PASS： [标量证据](tools/e_scalar_cases/README.md) | 适用的其他enum/RM与特殊状态按证据扩展 |
| 74 | `LOAD_FP` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 75 | `RFVVTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 76 | `RFWVVTYPE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 77 | `STORE_FP` | 未验收：依赖独立内存分支 | 本浮点任务不修改或集成该分支；访存结果不得计入浮点PASS |
| 78 | `VFMERGE` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 79 | `VFMV` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 80 | `VFMVFS` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 81 | `VFMVSF` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 82 | `VFNCVTBF16_F_F_W` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 未列出的格式、RM与活动元素组合仍待核 |
| 83 | `VFNUNARY0` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 20/20合法enum×SEW及关键RM/ROD已测；其余输入域待补 |
| 84 | `VFUNARY0` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 85 | `VFUNARY1` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |
| 86 | `VFWCVTBF16_F_F_V` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 未列出的格式、RM与活动元素组合仍待核 |
| 87 | `VFWMACCBF16_VF` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 未列出的格式、RM与活动元素组合仍待核 |
| 88 | `VFWMACCBF16_VV` | RV64具体样例PASS： [BF16/ROD等证据](tools/e_nonmem/RESULTS.md) | 未列出的格式、RM与活动元素组合仍待核 |
| 89 | `VFWUNARY0` | RV64具体样例PASS： [向量证据](tools/e_vector_cases/README.md) | enum×合法SEW基线已扩展；RM、mask/vstart、LMUL与特殊值按证据继续补 |

## 后续子操作、舍入与状态扩展

- [标量扩展证据](tools/e_scalar_cases/README.md)：类型化90个enum、FLI三格式全96索引、RM路由169例、状态边界76例与非法舍入30例均按归档输入通过。此前“其他enum待补”的逐行文字保留初版时点；现行范围以该证据包和[实施记录](implementation.md)为准。
- [向量扩展证据](tools/e_vector_cases/README.md)：80个enum×合法SEW的215格、四固定编码跨SEW12格、状态49例、RM路由564条及非法舍入21+4条定向证明；[FVVTYPE专包](tools/e_fvvtype_cases/RESULTS.md)另覆盖9enum×SEW16/32/64和24条边界。
- [BF16/ROD扩展证据](tools/e_nonmem/RESULTS.md)：VFNUNARY0的20个合法enum×SEW格及关键五RM、ROD、BF16活动/NaN和9条非法FRM验证。各包仅证明固定具体初态与受测域。

## 计数与适用范围

- 静态矩阵总数 89；本表按真实 clause 名集合核对，77个非访存RV64样例的三包集合47+20+10两两无重叠，且恰为89项扣除10个MEMORY交集和两项RV32限定Zfa。
- 浮点非访存证据采用V128 IR SHA-256 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`。两项RV32 Zfa来自独立完整RV32 IR；其余涉及真实内存的条目留待独立议题处理。
- BF16、ROD、标量和向量的进一步 enum×SEW、特殊值与RM用例在各证据包持续追加。普通 `make solve` 220项60秒有界尝试退出137，全量仍待复验。
