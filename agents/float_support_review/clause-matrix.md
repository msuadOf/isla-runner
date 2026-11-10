# FD_FLOAT clause 逐项初筛表

状态：本表保留实施前的静态源码初筛和当时逐行“未测”标记。现行动态结果见[89项验收索引](e-coverage.md)；本表逐行状态不能作为当前功能结果。清单来自 `isla/scripts/run.mk` 与 `sail-riscv/` 工作树；`FD_FLOAT` 的 89 项是 clause 名称，不等同于 89 条编码或 89 个浮点 helper。

清单核对命令：`rg -n '^(FD_FLOAT|MEMORY)=' isla/scripts/run.mk`；用 make 变量或脚本展开两集合并集/交集。本轮静态提取结果：FD_FLOAT 89 项，MEMORY 交集 10 项。

初筛时先展开类型化标量组与 VFNUNARY0 的 enum/源码位置；本文件后续附表又补了其他向量类型的 funct/op enum 与配置 guard，不能由类别名推断子操作。主表的 XLEN/扩展列仍是初筛候选，逐行“未测”是当时记录；`MEMORY=是` 表示也在 MEMORY 列表，动态验收须核真实读写。

| # | Clause | 类别 / 源码入口 | XLEN / 扩展限制候选 | 子操作 / 合法编码注意 | MEMORY 交集 | 状态 |
|---:|---|---|---|---|:---:|---|
| 1 | `C_FLD` | 压缩 D 访存；`sail-riscv/model/extensions/FD/zcd_insts.sail` | Zcd+D；RV32/RV64 均需核对 | FLD，宽度 8；SP 或压缩寄存器寻址；**真实读/写及状态变化** | 是 | 未测 |
| 2 | `C_FLDSP` | 压缩 D 访存；`sail-riscv/model/extensions/FD/zcd_insts.sail` | Zcd+D；RV32/RV64 均需核对 | FLD，宽度 8；SP 或压缩寄存器寻址；**真实读/写及状态变化** | 是 | 未测 |
| 3 | `C_FLW` | 压缩 F 访存；`sail-riscv/model/extensions/FD/zcf_insts.sail` | Zcf+F+Zca；RV32 only（映射 `when xlen == 32`） | FLW，宽度 4；SP 或压缩寄存器寻址；**RV32 合法译码 + 真实访存** | 是 | 未测 |
| 4 | `C_FLWSP` | 压缩 F 访存；`sail-riscv/model/extensions/FD/zcf_insts.sail` | Zcf+F+Zca；RV32 only（映射 `when xlen == 32`） | FLW，宽度 4；SP 或压缩寄存器寻址；**RV32 合法译码 + 真实访存** | 是 | 未测 |
| 5 | `C_FSD` | 压缩 D 访存；`sail-riscv/model/extensions/FD/zcd_insts.sail` | Zcd+D；RV32/RV64 均需核对 | FSD，宽度 8；SP 或压缩寄存器寻址；**真实读/写及状态变化** | 是 | 未测 |
| 6 | `C_FSDSP` | 压缩 D 访存；`sail-riscv/model/extensions/FD/zcd_insts.sail` | Zcd+D；RV32/RV64 均需核对 | FSD，宽度 8；SP 或压缩寄存器寻址；**真实读/写及状态变化** | 是 | 未测 |
| 7 | `C_FSW` | 压缩 F 访存；`sail-riscv/model/extensions/FD/zcf_insts.sail` | Zcf+F+Zca；RV32 only（映射 `when xlen == 32`） | FSW，宽度 4；SP 或压缩寄存器寻址；**RV32 合法译码 + 真实访存** | 是 | 未测 |
| 8 | `C_FSWSP` | 压缩 F 访存；`sail-riscv/model/extensions/FD/zcf_insts.sail` | Zcf+F+Zca；RV32 only（映射 `when xlen == 32`） | FSW，宽度 4；SP 或压缩寄存器寻址；**RV32 合法译码 + 真实访存** | 是 | 未测 |
| 9 | `FCVTMOD_W_D` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | FCVTmod.W.D 环绕整数转换；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 10 | `FCVT_BF16_S` | BF16 标量转换；`sail-riscv/model/extensions/bfloat16/zfbfmin_insts.sail` | `Ext_Zfbfmin` 与 F；RV32/RV64 | f32→BF16；普通 RM、boxing、结果位与flags | 否 | 未测 |
| 11 | `FCVT_S_BF16` | BF16 标量转换；`sail-riscv/model/extensions/bfloat16/zfbfmin_insts.sail` | `Ext_Zfbfmin` 与 F；RV32/RV64 | BF16→f32；合法 RM 编码、boxing、结果位与flags | 否 | 未测 |
| 12 | `FLEQ_D` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 安静 <= 比较；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 13 | `FLEQ_H` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 安静 <= 比较；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 14 | `FLEQ_S` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 安静 <= 比较；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 15 | `FLI_D` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 立即数表/保留编码；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 16 | `FLI_H` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 立即数表/保留编码；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 17 | `FLI_S` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 立即数表/保留编码；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 18 | `FLTQ_D` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 安静 < 比较；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 19 | `FLTQ_H` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 安静 < 比较；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 20 | `FLTQ_S` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 安静 < 比较；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 21 | `FMAXM_D` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 任一输入为NaN则返回规范NaN；另测±0与flags | 否 | 未测 |
| 22 | `FMAXM_H` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 任一输入为NaN则返回规范NaN；另测±0与flags | 否 | 未测 |
| 23 | `FMAXM_S` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 任一输入为NaN则返回规范NaN；另测±0与flags | 否 | 未测 |
| 24 | `FMINM_D` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 任一输入为NaN则返回规范NaN；另测±0与flags | 否 | 未测 |
| 25 | `FMINM_H` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 任一输入为NaN则返回规范NaN；另测±0与flags | 否 | 未测 |
| 26 | `FMINM_S` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 任一输入为NaN则返回规范NaN；另测±0与flags | 否 | 未测 |
| 27 | `FMVH_X_D` | Zfa 位搬运；`sail-riscv/model/extensions/FD/zfa_insts.sail:523–559` | D+Zfa；RV32 only（`in32BitMode()`） | FMVH.X.D 取 D 高32位并符号扩展；FMVP.D.X 拼接两个 X[31:0]；**RV32 合法编码/译码** | 否 | 未测 |
| 28 | `FMVP_D_X` | Zfa 位搬运；`sail-riscv/model/extensions/FD/zfa_insts.sail:523–559` | D+Zfa；RV32 only（`in32BitMode()`） | FMVH.X.D 取 D 高32位并符号扩展；FMVP.D.X 拼接两个 X[31:0]；**RV32 合法编码/译码** | 否 | 未测 |
| 29 | `FROUNDNX_D` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 舍入并报告 NX；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 30 | `FROUNDNX_H` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 舍入并报告 NX；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 31 | `FROUNDNX_S` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 舍入并报告 NX；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 32 | `FROUND_D` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 舍入到整数；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 33 | `FROUND_H` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 舍入到整数；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 34 | `FROUND_S` | Zfa 标量扩展；`sail-riscv/model/extensions/FD/zfa_insts.sail` | Zfa；D 项需 D，H 项需 Zfh；核对映射 guard | 舍入到整数；格式由后缀；**扩展使能、立即数/op 编码、flags** | 否 | 未测 |
| 35 | `FVFMATYPE` | RVV scalar-vector 融合乘加；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 操作 enum/func6 见“RVV clause”附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 36 | `FVFMTYPE` | RVV scalar-vector 比较写 mask；`sail-riscv/model/extensions/V/vext_fp_vm_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 6 个比较 enum 见附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 37 | `FVFTYPE` | RVV scalar-vector 算术；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 13 个 funct6 enum 见附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 38 | `FVVMATYPE` | RVV vector-vector 融合乘加；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 8 个融合 funct6 enum 见附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 39 | `FVVMTYPE` | RVV vector-vector 比较写 mask；`sail-riscv/model/extensions/V/vext_fp_vm_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 4 个比较 enum 见附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 40 | `FVVTYPE` | RVV vector-vector 算术；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 9 个 funct6 enum 见附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 41 | `FWFTYPE` | RVV vector-wide scalar FP widening 算术；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve64d@SEW32 | 2 个 enum；SEW 16→32 或 32→64；mask/vstart/vtype 另核 | 否 | 未测 |
| 42 | `FWVFMATYPE` | RVV vector-scalar widening 融合乘加；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve64d@SEW32 | 4 个融合 enum；宽化目标；mask/vstart/vtype 另核 | 否 | 未测 |
| 43 | `FWVFTYPE` | RVV vector-scalar widening 算术；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve64d@SEW32 | 3 个 enum；SEW 16→32 或 32→64；mask/vstart/vtype 另核 | 否 | 未测 |
| 44 | `FWVTYPE` | RVV 窄向量源/宽向量源 widening 算术；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve64d@SEW32 | 2 个 enum；宽窄寄存器组约束；mask/vstart/vtype 另核 | 否 | 未测 |
| 45 | `FWVVMATYPE` | RVV vector-vector widening 融合乘加；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve64d@SEW32 | 4 个融合 enum；宽化目标；mask/vstart/vtype 另核 | 否 | 未测 |
| 46 | `FWVVTYPE` | RVV vector-vector widening 算术；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve64d@SEW32 | 3 个 enum；SEW 16→32 或 32→64；mask/vstart/vtype 另核 | 否 | 未测 |
| 47 | `F_BIN_F_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | D / haveDoubleFPU；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 48 | `F_BIN_F_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | half-FPU 路径；编码 guard 待逐项复核 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 49 | `F_BIN_RM_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | D / haveDoubleFPU；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 50 | `F_BIN_RM_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | haveHalfFPU；Zfh/Zhinx 配置另核 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 51 | `F_BIN_RM_TYPE_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F / haveSingleFPU；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 52 | `F_BIN_TYPE_F_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 53 | `F_BIN_TYPE_X_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 54 | `F_BIN_X_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | D / haveDoubleFPU；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 55 | `F_BIN_X_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | half-FPU 路径；编码 guard 待逐项复核 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 56 | `F_MADD_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | D / haveDoubleFPU；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 57 | `F_MADD_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | haveHalfFPU；Zfh/Zhinx 配置另核 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 58 | `F_MADD_TYPE_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F / haveSingleFPU；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 59 | `F_UN_F_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | D；仅 RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 60 | `F_UN_F_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | Zfhmin 或 Zfbfmin，映射见 zfh:804–808 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 61 | `F_UN_RM_FF_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | D / haveDoubleFPU；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 62 | `F_UN_RM_FF_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | half-FPU/HalfMin；D 转换另需 D | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 63 | `F_UN_RM_FF_TYPE_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F / haveSingleFPU；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 64 | `F_UN_RM_FX_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | D；FCVT_L/LU 仅 RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 65 | `F_UN_RM_FX_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | half-FPU；FCVT_L/LU 仅 RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 66 | `F_UN_RM_FX_TYPE_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F；FCVT_L/LU 仅 RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 67 | `F_UN_RM_XF_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | D；FCVT_*_L/LU 仅 RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 68 | `F_UN_RM_XF_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | half-FPU；FCVT_*_L/LU 仅 RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 69 | `F_UN_RM_XF_TYPE_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F；FCVT_*_L/LU 仅 RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 70 | `F_UN_TYPE_F_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 71 | `F_UN_TYPE_X_S` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/fext_insts.sail` | Ext_F；RV32/RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 72 | `F_UN_X_TYPE_D` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/dext_insts.sail` | FCLASS: double FPU；FMV_X_D 仅 RV64 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 73 | `F_UN_X_TYPE_H` | 标量浮点类型化指令；`sail-riscv/model/extensions/FD/zfh_insts.sail` | Zfhmin 或 Zfbfmin，映射见 zfh:804–808 | 具体 op enum、encdec 映射及 guard 见下方逐 clause 附表 | 否 | 未测 |
| 74 | `LOAD_FP` | 标量浮点访存；`sail-riscv/model/extensions/FD/fext_insts.sail:255–298` | 宽度2需Zfhmin或Zfbfmin、4需F、8需D；XLEN按配置核对 | 同一clause覆盖FLH/FLW/FLD，分别核2/4/8字节地址、读事件、NaN boxing与FPR写回；仅clause名称不足以证明各宽度 | 是 | 未测 |
| 75 | `RFVVTYPE` | RVV 单宽浮点归约；`sail-riscv/model/extensions/V/vext_fp_red_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 4 个 reduction enum，见附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 76 | `RFWVVTYPE` | RVV 宽化浮点归约；`sail-riscv/model/extensions/V/vext_fp_red_insts.sail` | Zvfh@SEW16 / Zve64d@SEW32 | ordered/unordered enum 两种；实现当前采用同一顺序算法；mask/vstart/vtype 另核 | 否 | 未测 |
| 77 | `STORE_FP` | 标量浮点访存；`sail-riscv/model/extensions/FD/fext_insts.sail:255–349` | 宽度2需Zfhmin或Zfbfmin、4需F、8需D；XLEN按配置核对 | 同一clause覆盖FSH/FSW/FSD，分别核2/4/8字节地址、写事件、写入低位与前后内存；仅clause名称不足以证明各宽度 | 是 | 未测 |
| 78 | `VFMERGE` | RVV 浮点标量与向量 merge；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 固定 funct encoding；vm=0；mask/vstart/vtype 另核 | 否 | 未测 |
| 79 | `VFMV` | RVV 浮点 scalar broadcast；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 固定 encoding；vm=1、vs2=0；mask/vstart/vtype 另核 | 否 | 未测 |
| 80 | `VFMVFS` | RVV 向量元素提取至 FP scalar；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 固定 encoding；vs1=0、vm=1；mask/vstart/vtype 另核 | 否 | 未测 |
| 81 | `VFMVSF` | RVV FP scalar 插入向量元素；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 固定 encoding；vs2=0、vm=1；mask/vstart/vtype 另核 | 否 | 未测 |
| 82 | `VFNCVTBF16_F_F_W` | BF16 标量/向量；`sail-riscv/model/extensions/bfloat16/` | Zvfbfmin 或 Zvfbfwma guard，详见 BF16 专表 | BF16 固定 funct 编码与 SEW=16 guard 见 BF16 专表；**格式、flags、活动元素** | 否 | 未测 |
| 83 | `VFNUNARY0` | RVV 浮点窄转换/一元；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | V + 格式所需 F/D/Zfh；固定 VLEN/SEW/LMUL | 见 VFNUNARY0 子表：8 个 enum 含普通/ROD/RTZ；**ROD 两种窄化、mask/vstart/flags** | 否 | 未测 |
| 84 | `VFUNARY0` | RVV 向量浮点窄转换；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 6 个转换 enum，见附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 85 | `VFUNARY1` | RVV 向量浮点一元操作；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | Zvfh@SEW16 / Zve32f@SEW32 / Zve64d@SEW64 | 4 个一元 enum，见附表；mask/vstart/vtype 另核 | 否 | 未测 |
| 86 | `VFWCVTBF16_F_F_V` | BF16 标量/向量；`sail-riscv/model/extensions/bfloat16/` | Zvfbfmin 或 Zvfbfwma guard，详见 BF16 专表 | BF16 固定 funct 编码与 SEW=16 guard 见 BF16 专表；**格式、flags、活动元素** | 否 | 未测 |
| 87 | `VFWMACCBF16_VF` | BF16 标量/向量；`sail-riscv/model/extensions/bfloat16/` | Zvfbfmin 或 Zvfbfwma guard，详见 BF16 专表 | BF16 固定 funct 编码与 SEW=16 guard 见 BF16 专表；**格式、flags、活动元素** | 否 | 未测 |
| 88 | `VFWMACCBF16_VV` | BF16 标量/向量；`sail-riscv/model/extensions/bfloat16/` | Zvfbfmin 或 Zvfbfwma guard，详见 BF16 专表 | BF16 固定 funct 编码与 SEW=16 guard 见 BF16 专表；**格式、flags、活动元素** | 否 | 未测 |
| 89 | `VFWUNARY0` | RVV 向量浮点宽化转换；`sail-riscv/model/extensions/V/vext_fp_insts.sail` | valid_widening_fp_conversion；具体扩展/SEW per enum | 7 个转换 enum，谓词见 vext_utils_insts.sail:126–139；mask/vstart/vtype 另核 | 否 | 未测 |


## 待复核项与核验入口

- **89 项集合及 10 项交集**：从 `isla/scripts/run.mk` 的 `FD_FLOAT`、`MEMORY` 赋值重新提取比较；不以运行日志 Finished 数量替代集合核对。
- **RV32 限制候选**：查看 `FD/zcf_insts.sail` 四个压缩 F clause 的 `when xlen == 32`，以及 `FD/zfa_insts.sail` 的 `FMVH_X_D`、`FMVP_D_X` `in32BitMode()` guard；合法译码仍需 RV32 IR/config 执行验证。
- **RV32 工具入口**：当前 `isla/src/isarch_main.rs` 的 RV32 `solve-state` 分支无条件 panic；`make solve-*` 不能作为六项 RV32 验收。需用完整 RV32 IR 的编码→反向译码→执行隔离 harness 或 Sail 模拟器取指路径核对，直接构造 clause 和仅正向取得编码都不等于合法译码。公共 CLI 如需通过，另修 RV32 入口并验证 target/内存初始化。
- **压缩访存路径**：查看 `FD/zcf_insts.sail`、`FD/zcd_insts.sail` execute 函数如何调用 `LOAD_FP`/`STORE_FP`；需观察真实 memory event、寄存器变化与内存初值/终值。
- **VFNUNARY0 子操作**：`V/vext_fp_insts.sail` 的 `encdec_vfnunary0_vs1` 和 `execute VFNUNARY0` 列出 XU/X/F 转换、普通窄化、ROD、RTZ。ROD helper 传入 `0b110`，需独立实例。
- **类型化标量指令**：在 `FD/fext_insts.sail`、`FD/dext_insts.sail` 按 union clause 名定位；由 `f_bin_*_op_*`、`f_un_*_op_*`、`f_madd_*_op_*` 映射确定合法 op enum。D/H 文件位置与 ISA guard 不应仅凭命名推断。
- **其他 RVV、BF16 与 Zfa 开关**：除 VFNUNARY0 外，逐项读取表列文件中的 `currentlyEnabled`、`valid_*`、funct/op enum 编码映射和格式 match；目前没有完成所有 RVV 子操作枚举，需待查。分别固定配置，并留存合法汇编/编码、反汇编/译码及执行记录。
- **真实访存验收**：10 项交集待内存接口具备后检查地址、宽度、读写事件、寄存器写回与内存前后值。直接注入 clause 或仅得到 Finished 不足以证明读写。

建议只读定位：`rg -n 'union clause instruction =|mapping clause encdec|currentlyEnabled|in32BitMode|when xlen == 32|valid_.*conversion|encdec_vfnunary0' sail-riscv/model/extensions/FD sail-riscv/model/extensions/V sail-riscv/model/extensions/bfloat16`


## 类型化标量 clause：实际 enum 与映射位置

下表按当前 Sail `mapping clause encdec` 中实际构造的 enum 整理；位置均为可复查的源码行。各映射的 `when` 是编码/译码适用条件，需按目标配置验证。普通动态/静态舍入编码还受 `select_instr_or_fcsr_rm` 和 `valid_rounding_mode` 约束（`fext_insts.sail:31–51`）；此处不把非法 RM 当合法操作覆盖。类型化 clause 的 execute 语义须再对照相同行附近的 `function clause execute`，当前模型 helper 调用情况以这些执行分支为准。

| Clause | 实际 op enum（映射中的成员） | enum 类型 / 编码映射位置 | guard 候选 / XLEN | 复核注意 |
|---|---|---|---|---|
| `F_BIN_RM_TYPE_S` | `FADD_S`, `FSUB_S`, `FMUL_S`, `FDIV_S` | `f_bin_rm_op_S`；`FD/fext_insts.sail:425–441` | `haveSingleFPU()`（`fext_insts.sail:253`）；RV32/RV64 | 四则运算，执行分支调用 f32 helper |
| `F_MADD_TYPE_S` | `FMADD_S`, `FMSUB_S`, `FNMSUB_S`, `FNMADD_S` | `f_madd_op_S`；`fext_insts.sail:358–374` | `haveSingleFPU()`；RV32/RV64 | 三输入融合运算；逐个 op 覆盖 |
| `F_BIN_TYPE_F_S` | `FSGNJ_S`, `FSGNJN_S`, `FSGNJX_S`, `FMIN_S`, `FMAX_S` | `f_bin_op_f_S`；`fext_insts.sail:714–735` | `haveSingleFPU()`；RV32/RV64 | 符号注入/最小最大，执行中部分用 fp helper |
| `F_BIN_TYPE_X_S` | `FEQ_S`, `FLT_S`, `FLE_S` | `f_bin_op_x_S`；`fext_insts.sail:714–747` | `haveSingleFPU()`；RV32/RV64 | 写整数寄存器的比较；核对 NaN/flags |
| `F_UN_RM_FF_TYPE_S` | `FSQRT_S` | `f_un_rm_ff_op_S`；`fext_insts.sail:489–495` | `haveSingleFPU()`；RV32/RV64 | 平方根，动态 RM 路径 |
| `F_UN_RM_FX_TYPE_S` | `FCVT_W_S`, `FCVT_WU_S`, `FCVT_L_S`, `FCVT_LU_S` | `f_un_rm_fx_op_S`；`fext_insts.sail:490–521` | `haveSingleFPU()`；L/LU 仅 `xlen>=64`（`:515–521`） | FP→有/无符号整数；分别验证 32/64 位目标 |
| `F_UN_RM_XF_TYPE_S` | `FCVT_S_W`, `FCVT_S_WU`, `FCVT_S_L`, `FCVT_S_LU` | `f_un_rm_xf_op_S`；`fext_insts.sail:491–529` | `haveSingleFPU()`；L/LU 仅 `xlen>=64`（`:523–529`） | 有/无符号整数→FP；分别验证 32/64 位源 |
| `F_UN_TYPE_X_S` | `FCLASS_S`, `FMV_X_W` | `f_un_op_x_S`；`fext_insts.sail:893–902` | `Ext_F`；RV32/RV64 | 分类和位搬运，非舍入算术 |
| `F_UN_TYPE_F_S` | `FMV_W_X` | `f_un_op_f_S`；`fext_insts.sail:893–906` | `Ext_F`；RV32/RV64 | 整数位搬运至 FP，核对 NaN boxing |
| `F_BIN_RM_TYPE_D` | `FADD_D`, `FSUB_D`, `FMUL_D`, `FDIV_D` | `f_bin_rm_op_D`；`FD/dext_insts.sail:313–329` | `haveDoubleFPU()`；RV32/RV64 | D 格式算术；合法寄存器条件见每条映射 |
| `F_MADD_TYPE_D` | `FMADD_D`, `FMSUB_D`, `FNMSUB_D`, `FNMADD_D` | `f_madd_op_D`；`dext_insts.sail:245–261` | `haveDoubleFPU()`；RV32/RV64 | 融合三输入；逐项核对 rounding 与 flags |
| `F_BIN_F_TYPE_D` | `FSGNJ_D`, `FSGNJN_D`, `FSGNJX_D`, `FMIN_D`, `FMAX_D` | `f_bin_f_op_D`；`dext_insts.sail:645–666` | `haveDoubleFPU()`；RV32/RV64 | 符号注入/最小最大 |
| `F_BIN_X_TYPE_D` | `FEQ_D`, `FLT_D`, `FLE_D` | `f_bin_x_op_D`；`dext_insts.sail:645–678` | `haveDoubleFPU()`；RV32/RV64 | 比较写整数寄存器 |
| `F_UN_RM_FF_TYPE_D` | `FSQRT_D`, `FCVT_S_D`, `FCVT_D_S` | `f_un_rm_ff_op_D`；`dext_insts.sail:377–407` | `haveDoubleFPU()`；RV32/RV64 | sqrt 与 S/D 转换；检查 source/destination FPU regs |
| `F_UN_RM_FX_TYPE_D` | `FCVT_W_D`, `FCVT_WU_D`, `FCVT_L_D`, `FCVT_LU_D` | `f_un_rm_fx_op_D`；`dext_insts.sail:379–417` | `haveDoubleFPU()`；L/LU 仅 `xlen>=64`（`:411–417`） | FP→整数；拆分 32 位和 64 位目标 |
| `F_UN_RM_XF_TYPE_D` | `FCVT_D_W`, `FCVT_D_WU`, `FCVT_D_L`, `FCVT_D_LU` | `f_un_rm_xf_op_D`；`dext_insts.sail:378–425` | `haveDoubleFPU()`；L/LU 仅 `xlen>=64`（`:419–425`） | 整数→FP；拆分 32 位和 64 位源 |
| `F_UN_X_TYPE_D` | `FCLASS_D`, `FMV_X_D` | `f_un_x_op_D`；`dext_insts.sail:825–836` | FCLASS 用 double FPU；FMV_X_D 要 `Ext_D & xlen>=64`（`:830–836`） | FMV_X_D RV32 不合法；不要与 Zfa 的 FMVH_X_D 混淆 |
| `F_UN_F_TYPE_D` | `FMV_D_X` | `f_un_f_op_D`；`dext_insts.sail:826–840` | `Ext_D & xlen>=64`（`:838–840`） | RV64 64 位搬运 |
| `F_BIN_RM_TYPE_H` | `FADD_H`, `FSUB_H`, `FMUL_H`, `FDIV_H` | `f_bin_rm_op_H`；`FD/zfh_insts.sail:172–188` | `haveHalfFPU()`；结合 `Ext_Zfh`/`Ext_Zhinx` 配置，见 `zfh_insts.sail:9–10,155` | half 格式算术；文件中的 encdec 支持 Zfinx 变体，需确认 fd 条目所用配置 |
| `F_MADD_TYPE_H` | `FMADD_H`, `FMSUB_H`, `FNMSUB_H`, `FNMADD_H` | `f_madd_op_H`；`zfh_insts.sail:236–252` | `haveHalfFPU()`；配置需区分 Zfh/Zhinx | fused half 运算 |
| `F_BIN_F_TYPE_H` | `FSGNJ_H`, `FSGNJN_H`, `FSGNJX_H`, `FMIN_H`, `FMAX_H` | `f_bin_f_op_H`；`zfh_insts.sail:303–324` | half-FPU 相关；执行/映射逐条核对 | 符号注入/最小最大 |
| `F_BIN_X_TYPE_H` | `FEQ_H`, `FLT_H`, `FLE_H` | `f_bin_x_op_H`；`zfh_insts.sail:303–336` | half-FPU 相关；执行/映射逐条核对 | half 比较及 NV 规则 |
| `F_UN_RM_FF_TYPE_H` | `FSQRT_H`, `FCVT_H_S`, `FCVT_H_D`, `FCVT_S_H`, `FCVT_D_H` | `f_un_rm_ff_op_H`；`zfh_insts.sail:484–522` | `haveHalfFPU()`；S/H 转换用 `haveHalfMin()`，D 转换另要求 double FPU；见 `:155–158,510–522` | 格式转换方向分别覆盖；不是每项都只依赖 Zfh |
| `F_UN_RM_FX_TYPE_H` | `FCVT_W_H`, `FCVT_WU_H`, `FCVT_L_H`, `FCVT_LU_H` | `f_un_rm_fx_op_H`；`zfh_insts.sail:485,494–535` | W/WU 用 half FPU；L/LU 仅 `xlen>=64`（`:531–535`） | FP→整数；位宽/符号分开 |
| `F_UN_RM_XF_TYPE_H` | `FCVT_H_W`, `FCVT_H_WU`, `FCVT_H_L`, `FCVT_H_LU` | `f_un_rm_xf_op_H`；`zfh_insts.sail:486,502–543` | W/WU 用 half FPU；L/LU 仅 `xlen>=64`（`:539–543`） | 整数→FP；位宽/符号分开 |
| `F_UN_X_TYPE_H` | `FCLASS_H`, `FMV_X_H` | `f_un_x_op_H`；`zfh_insts.sail:793–802` | 映射允许 `Zfhmin` 或 `Zfbfmin`；详见 `:804–808` | 分类/搬运；FMV 扩展要求可能与 FCLASS 不同 |
| `F_UN_F_TYPE_H` | `FMV_H_X` | `f_un_f_op_H`；`zfh_insts.sail:793–806` | 映射允许 `Zfhmin` 或 `Zfbfmin`；详见 `:804–808` | H 位搬运；当前配置需确认启用扩展 |

## `VFNUNARY0` 子操作与编码

实际枚举来自 `sail-riscv/model/extensions/V/vext_fp_insts.sail`：`vfnunary0` union/映射于 `652–667`，执行分支于 `669–778`，mnemonic 对照于 `782–790`。编码字段为 `vs1` 的 5 位值；`valid_narrowing_fp_conversion(vfnunary0)` 决定合法组合，encdec guard 在 `vext_fp_insts.sail:665–667`，谓词定义在 `sail-riscv/model/extensions/V/vext_utils_insts.sail:140`。

| Enum | vs1 编码 | mnemonic | 执行分支与 helper/限制 |
|---|---:|---|---|
| `FNV_CVT_XU_F` | `10000` | `vfncvt.xu.f.w` | `701–709`；按 SEW 选择 f16→ui8、f32→ui16、f64→ui32 |
| `FNV_CVT_X_F` | `10001` | `vfncvt.x.f.w` | `710–718`；按 SEW 选择 f16→i8、f32→i16、f64→i32 |
| `FNV_CVT_F_XU` | `10010` | `vfncvt.f.xu.w` | `719–727`；SEW=8 时非法，其余 ui32→f16、ui64→f32 |
| `FNV_CVT_F_X` | `10011` | `vfncvt.f.x.w` | `728–736`；SEW=8 时非法，其余 i32→f16、i64→f32 |
| `FNV_CVT_F_F` | `10100` | `vfncvt.f.f.w` | `737–745`；f32→f16 或 f64→f32，使用动态 rm |
| `FNV_CVT_ROD_F_F` | `10101` | `vfncvt.rod.f.f.w` | `746–754`；helper 显式传 `0b110`（ROD），不能并入普通 rm=0..4 覆盖 |
| `FNV_CVT_RTZ_XU_F` | `10110` | `vfncvt.rtz.xu.f.w` | `755–763`；整数转换 helper 显式传 RTZ=`0b001` |
| `FNV_CVT_RTZ_X_F` | `10111` | `vfncvt.rtz.x.f.w` | `764–772`；有符号转换 helper 显式传 RTZ=`0b001` |

RVV 子项适用 V 与窄化格式所需浮点扩展；clause 编码还受 `valid_narrowing_fp_conversion`、`illegal_fp_variable_width`、寄存器重叠和 SEW 断言约束。需要分别测试 enum 合法译码、非法子项拒绝、mask/vstart 和 flags；以上源码检查不构成功能通过。

## 其余 RVV clause 的 enum、共用 mapping 与 guard 初筛

下表按 Sail 实际 union 类型与 encdec mapping 列出子操作。除固定 move/merge clause 外，mapping 用 funct6 或 vs1 子字段；同一 funct enum 可能由普通/宽化变体复用，但每类有单独编码 helper 与 encdec clause。源码 guard 只是编码/译码准入条件，执行时还会检查 vtype、SEW、LMUL、寄存器分组/重叠、mask 与 vstart。所有项仍待执行覆盖核实。

| Clause | Enum / 子操作及 funct 编码 | 共用映射与源码位置 | encdec guard（源码位置） | 可以据源码规划的覆盖 |
|---|---|---|---|---|
| `FVVTYPE` | `FVV_VADD 000000`, `FVV_VSUB 000010`, `FVV_VMIN 000100`, `FVV_VMAX 000110`, `FVV_VSGNJ 001000`, `FVV_VSGNJN 001001`, `FVV_VSGNJX 001010`, `FVV_VDIV 100000`, `FVV_VMUL 100100` | `fvvfunct6` + execute match：`V/vext_fp_insts.sail:16–36,55–82` | Zvfh & SEW16 / Zve32f & SEW32 / Zve64d & SEW64 (`:30–32`) | 每个算术、min/max、sign-inject enum；VV、mask/vstart、动态 rm、flags |
| `FVVMATYPE` | `FVV_VMADD 101000`, `FVV_VNMADD 101001`, `FVV_VMSUB 101010`, `FVV_VNMSUB 101011`, `FVV_VMACC 101100`, `FVV_VNMACC 101101`, `FVV_VMSAC 101110`, `FVV_VNMSAC 101111` | `fvvmafunct6` + execute match：`vext_fp_insts.sail:102–120,141–165` | 同 FVVTYPE (`:115–117`) | 8 种符号/累加形态各自验证 fused helper、旧 vd 的角色、mask/vstart、flags |
| `FVFTYPE` | `VF_VADD 000000`, `VF_VSUB 000010`, `VF_VMIN 000100`, `VF_VMAX 000110`, `VF_VSGNJ 001000`, `VF_VSGNJN 001001`, `VF_VSGNJX 001010`, `VF_VSLIDE1UP 001110`, `VF_VSLIDE1DOWN 001111`, `VF_VDIV 100000`, `VF_VRDIV 100001`, `VF_VMUL 100100`, `VF_VRSUB 100111` | `fvffunct6` + execute match：`vext_fp_insts.sail:925–950` 与 `:968–1014` | 同 FVVTYPE (`:943–945`) | VF scalar source；除算术/比较类外还覆盖 slide、reverse divide/subtract 和 scalar boxing |
| `FVFMATYPE` | `VF_VMADD 101000`, `VF_VNMADD 101001`, `VF_VMSUB 101010`, `VF_VNMSUB 101011`, `VF_VMACC 101100`, `VF_VNMACC 101101`, `VF_VMSAC 101110`, `VF_VNMSAC 101111` | `fvfmafunct6` + execute match：`vext_fp_insts.sail:1034–1053,1071–1100` | 同 FVVTYPE (`:1047–1049`) | 8 种 VF 融合形态、累加数排列、mask/vstart、flags |
| `FVVMTYPE` | `FVVM_VMFEQ 011000`, `FVVM_VMFLE 011001`, `FVVM_VMFLT 011011`, `FVVM_VMFNE 011100` | `fvvmfunct6` + execute 比较：`V/vext_fp_vm_insts.sail:16–29,32–58` | 同 FVVTYPE (`:25–27`) | VV 比较各 enum、mask destination、NaN、vm 与结果位 |
| `FVFMTYPE` | `VFM_VMFEQ 011000`, `VFM_VMFLE 011001`, `VFM_VMFLT 011011`, `VFM_VMFNE 011100`, `VFM_VMFGT 011101`, `VFM_VMFGE 011111` | `fvfmfunct6` + execute 比较：`vext_fp_vm_insts.sail:87–102,105–135` | 同 FVVTYPE (`:98–100`) | VF 比较各 enum、NaN、mask destination、scalar boxing |
| `FWVVTYPE` | `FWVV_VADD 110000`, `FWVV_VSUB 110010`, `FWVV_VMUL 111000` | `fwvvfunct6` + execute match：`vext_fp_insts.sail:184–202,222–247` | Zvfh & SEW16 / Zve64d & SEW32 (`:192–194`) | widening VV 的 add/sub/mul；窄输入 widening、宽 vd、宽重叠合法性 |
| `FWVVMATYPE` | `FWVV_VMACC 111100`, `FWVV_VNMACC 111101`, `FWVV_VMSAC 111110`, `FWVV_VNMSAC 111111` | `fwvvmafunct6` + execute match：`vext_fp_insts.sail:255–273,293–319` | 同 FWVVTYPE (`:264–266`) | widening fused VV 四变体、单次舍入、宽累加器与重叠 |
| `FWVTYPE` | `FWV_VADD 110100`, `FWV_VSUB 110110` | `fwvfunct6` + execute match：`vext_fp_insts.sail:328–343,361–383` | 同 FWVVTYPE (`:335–337`) | 宽化向量源 vs 窄向量源的 add/sub；宽/窄组重叠规则 |
| `FWVFTYPE` | `FWVF_VADD 110000`, `FWVF_VSUB 110010`, `FWVF_VMUL 111000` | `fwvffunct6` + execute match：`vext_fp_insts.sail:1115–1131,1150–1178` | 同 FWVVTYPE (`:1123–1125`) | widening VF add/sub/mul；scalar widen、宽目标和 mask |
| `FWVFMATYPE` | `FWVF_VMACC 111100`, `FWVF_VNMACC 111101`, `FWVF_VMSAC 111110`, `FWVF_VNMSAC 111111` | `fwvfmafunct6` + execute match：`vext_fp_insts.sail:1185–1202,1210–1235` | 同 FWVVTYPE (`:1194–1196`) | widening VF fused 四变体、scalar widen、vd 与 flags |
| `FWFTYPE` | `FWF_VADD 110100`, `FWF_VSUB 110110` | `fwffunct6` + execute match：`vext_fp_insts.sail:1257–1272,1288–1310` | 同 FWVVTYPE (`:1264–1266`) | 宽目标与宽向量源的 `.wf` add/sub；scalar widen、组约束 |
| `RFVVTYPE` | `FVV_VFREDOSUM 000011`, `FVV_VFREDUSUM 000001`, `FVV_VFREDMAX 000111`, `FVV_VFREDMIN 000101` | `rfvvfunct6` + execute match：`V/vext_fp_red_insts.sail:15–28,31–69` | Zvfh & SEW16 / Zve32f & SEW32 / Zve64d & SEW64 (`:24–26`) | ordered/unordered sum、min/max；vl=0、mask、初始 vs1、顺序及 flags |
| `RFWVVTYPE` | `FVV_VFWREDOSUM 110011`, `FVV_VFWREDUSUM 110001` | `rfwvvfunct6`；execute 当前对两者同用顺序累加：`vext_fp_red_insts.sail:90–101,104–138` | Zvfh & SEW16 / Zve64d & SEW32 (`:97–99`) | widen ordered/unordered sum、宽结果、vl=0/mask；Sail 注释明确此实现选择合法顺序实现，不应要求两者实现不同树 |
| `VFUNARY0` | `FV_CVT_XU_F 00000`, `FV_CVT_X_F 00001`, `FV_CVT_F_XU 00010`, `FV_CVT_F_X 00011`, `FV_CVT_RTZ_XU_F 00110`, `FV_CVT_RTZ_X_F 00111` | `vfunary0` + execute match：`vext_fp_insts.sail:395–415,417–494` | 同 FVVTYPE (`:406–408`) | 6 种转换；源/目标 SEW 映射、RTZ 固定 rm、mask/vstart/flags |
| `VFUNARY1` | `FVV_VSQRT 00000`, `FVV_VRSQRT7 00100`, `FVV_VREC7 00101`, `FVV_VCLASS 10000` | `vfunary1` + execute match：`vext_fp_insts.sail:797–814,816–879` | 同 FVVTYPE (`:806–808`) | sqrt/rec7/rsqrt7/class 分开覆盖；只有前者和后者依赖其各自语义/flags |
| `VFWUNARY0` | `FWV_CVT_XU_F 01000`, `FWV_CVT_X_F 01001`, `FWV_CVT_F_XU 01010`, `FWV_CVT_F_X 01011`, `FWV_CVT_F_F 01100`, `FWV_CVT_RTZ_XU_F 01110`, `FWV_CVT_RTZ_X_F 01111` | `vfwunary0` + execute match：`vext_fp_insts.sail:517–536,538–624` | `valid_widening_fp_conversion` guard (`:529–531`)，谓词 `V/vext_utils_insts.sail:126–139` | 7 种 widening convert；SEW/源输出格式映射、整数符号、RTZ、mask/vstart/flags |
| `VFMERGE` | 无 funct enum；固定 `funct6=010111, vm=0, funct3=101` | 单一 encdec 和 execute：`vext_fp_insts.sail:1325–1344` | 同 FVVTYPE (`:1328–1330`) | `.vf` merge，mask operand 固定 v0；execute 注释指出所有 body 元素均处理，核对 v0 真/假和值选择 |
| `VFMV` | 无 enum；固定 funct6 `010111`, `vm=1`, `vs2=00000`, `funct3=101` | 单一 encdec 和 execute：`vext_fp_insts.sail:1386–1400` | 同 FVVTYPE (`:1389–1391`) | scalar FP 广播到 vector；mask-independent 初始化、tail/vstart |
| `VFMVFS` | 无 enum；固定 `funct6=010000, vm=1, vs1=00000, funct3=001` | 单一 encdec 和 execute：`vext_fp_insts.sail:889–902` | 同 FVVTYPE (`:891–893`) | 首个活动 vector 元素搬到 scalar FP；vl=0/vstart/boxing |
| `VFMVSF` | 无 enum；固定 `funct6=010000, vm=1, vs2=00000, funct3=101` | 单一 encdec 和 execute：`vext_fp_insts.sail:1431–1445` | 同 FVVTYPE (`:1433–1435`) | scalar FP 写入 vector 首元素；其余元素语义、vl/vstart/boxing |

### 逐族来源与覆盖清单（仍未执行）

- `FVVTYPE` / `FVVMATYPE` / `FWVVTYPE` / `FWVVMATYPE` / `FWVTYPE`：`vext_fp_insts.sail:16–387`。按各 funct enum 成员逐项检查 VV 算术、融合、widening 和 overlap；普通组 guard 是 SEW=16/32/64 三档，widening 组只列 SEW=16/32。
- `VFUNARY0` / `VFWUNARY0`：`vext_fp_insts.sail:395–624` 与 `vext_utils_insts.sail:126–139`。逐 enum 检查转换方向、signedness、格式宽度及 RTZ；widening conversion 的合法子项由专门 predicate 限制。
- `VFUNARY1`：`vext_fp_insts.sail:797–879`。SQRT、rec7、rsqrt7、class 四子项分别覆盖；不能因同属 unary 就推断共用同一 float helper。
- `FVFTYPE` / `FVFMATYPE` / `FWVFTYPE` / `FWVFMATYPE` / `FWFTYPE`：`vext_fp_insts.sail:925–1310`。scalar-FP 操作各 enum 独立，widening 三族使用 SEW16→32 或 SEW32→64，检查 scalar NaN boxing 与 destination LMUL。
- `FVVMTYPE` / `FVFMTYPE`：`vext_fp_vm_insts.sail:16–155`。VV/VF compare mask 操作按比较关系逐项覆盖，另检查 vd-mask、vm 和 NaN。
- `RFVVTYPE` / `RFWVVTYPE`：`vext_fp_red_insts.sail:15–138`。分别检查有序/无序及宽化归约、vl=0、初值和活动 mask；当前 RFWVVTYPE 的 Sail body 将 ordered 算法作为 unordered 的允许实现。
- `VFMERGE` / `VFMV` / `VFMVFS` / `VFMVSF`：`vext_fp_insts.sail:889–944,1325–1480`。这些没有共用 enum 映射，各有固定编码；分别覆盖 merge 选择、scalar 广播/提取与 vstart/tail。

编码与 guard 的上述静态提取只确定了候选必测子项，尚未验证当前 FD 配置确实启用相应扩展、生成器可合法编码/译码，或 Isla 对 clause 有实际覆盖。

## BF16 专用 RVV clause 的编码与 guard

这四个向量 BF16 clause 也各自有固定编码，并不进入上面的通用 funct6 enum。源码入口均为当前 `sail-riscv/model/extensions/bfloat16/`。

| Clause | 固定编码字段 / 子操作 | guard 与源码位置 | 可据源码规划的覆盖 |
|---|---|---|---|
| `VFNCVTBF16_F_F_W` | OP-V `funct6=010010`、`vs1=11101`、`funct3=001`；BF16 narrowing f32→BF16 | `zvfbfmin_insts.sail:11–14`；`currentlyEnabled(Ext_Zvfbfmin) & SEW==16`；扩展要求 `Zvfbfmin` 且 `Zve32f` (`:11`) | SEW=16、widened source、寄存器重叠、mask/vstart、动态 rm、flags |
| `VFWCVTBF16_F_F_V` | OP-V `funct6=010010`、`vs1=01101`、`funct3=001`；BF16 widening BF16→f32 | `zvfbfmin_insts.sail:62–65`；同为 `Ext_Zvfbfmin & SEW==16` | SEW=16、widened destination、mask/vstart；转换调用 `bf16_to_f32_set_flags` |
| `VFWMACCBF16_VV` | OP-V `funct6=111011`、`funct3=001`；向量 BF16×BF16 累加至宽 f32 vd | `zvfbfwma_insts.sail:11–15`；`Ext_Zvfbfwma & SEW==16`；扩展要求 `Zvfbfwma`、`Zvfbfmin` 和 `Zfbfmin` (`:11`) | 活动元素、两个 BF16 转换 flags、fused single-round FMA、mask/vstart、宽 vd overlap |
| `VFWMACCBF16_VF` | OP-V `funct6=111011`、`funct3=101`；标量 BF16×向量 BF16 累加至宽 f32 vd | `zvfbfwma_insts.sail:64–68`；同为 `Ext_Zvfbfwma & SEW==16` | 与 VV 相同，另有标量 `F_BF16(rs1)`；特别覆盖 `vl=0`、mask 全关、vstart≥vl、跳过前缀含标量 sNaN，检查是否错误累计 NV |
