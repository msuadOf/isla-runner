# G4 · F_BIN_F_TYPE_D / F_BIN_F_TYPE_H / F_BIN_TYPE_F_S 分支覆盖对照（Sail 源码 vs 56cc 80416 case）

- 数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/{distribution.md,cases.tsv}`。clause 实名带 `z` 前缀（zF_BIN_F_TYPE_D=110、zF_BIN_F_TYPE_H=425、zF_BIN_TYPE_F_S=425）。
- run 来源（cases.tsv `$1`）：D、H 同属 `official-56cc-long-20260927-064348`（同 config `riscv64_difftest_fd.toml`、同 IR `stage/rv64d.ir`）；S 属专门 run `single-f_bin_type_f_s-56cc-20260927-091855`（manifest：同 56cc IR 家族产物）。
- 计数核对（awk `$2×$5×$6`）：每 clause 5 助记符（fsgnj/fsgnjn/fsgnjx/fmin/fmax），D 各 21 Retire＋1 Illegal=110；H 各 84 Retire＋5 Illegal（derived-negative，mn 显示为编码 32'h2400_0053/2400_1053/2400_2053/2c00_0053/2c00_1053）=425；S 同 H 结构=425。
- 源码基线：当前工作树 `sail-riscv/model/extensions/FD/`（行号引用处；版本差异见[版本注记](#版本注记)）。

## 0. Illegal 归因（核心问题：execute 是否存在执行期 Illegal 分支）

三个 clause 的 execute 函数（dext_insts.sail:684–736、zfh_insts.sail:342–393、fext_insts.sail:753–804）**全部以 `RETIRE_SUCCESS` 无条件结尾，体内无 None()/throw/trap/Illegal 出口**：

- fsgnj 族只做 fsplit/fmake 位拼接（无分支、无异常）；
- fmin/fmax 调 `fp_min_pure`/`fp_max_pure`（fp_minmax.sail:2–44），NaN 走 canonical NaN 或旁路操作数臂，**不产生 Illegal**；
- frm/fcsr[FRM] 完全不被读取（`fp_min_pure` 无 rm 参数，encdec 亦无 rm 字段），fcsr 只经 `accrue_fflags` 写 FFLAGS——"frm 保留"对本组无影响；
- 15 个 Illegal（D 5 direct-negative + H 5 + S 5 derived-negative）全部是**encode/译码 guard 失败**：JSON 终端均 `phase=encode, function=zencdec_forwards, detail="Pattern match failure"`，mapping-source 分别指向 dext_insts.sail:650、zfh_insts.sail:308、fext_insts.sail:719（各 clause 的 FSGNJ encdec 子句），初始 mstatus=`64'h0000_000a_0000_0000`（**FS=Off**）→ `currentlyEnabled(Ext_F)`（fdext_control.sail:18）为假 → `haveXxxFPU()` guard 失败。gen 的 mstatus=`…2000`（FS=Clean）/`…4000`（FS=Initial）。

结论：**源码无执行期 Illegal 分支，Illegal 全部来自负例（FS=Off 译码失败），分布合理**。

## 1. zF_BIN_F_TYPE_D（fsgnj.d/fsgnjn.d/fsgnjx.d/fmin.d/fmax.d，110 case）

源码：`dext_insts.sail`（译码 650–668，执行 684–736）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard `haveDoubleFPU()` 真侧 | dext:650–668 + dext:214 + fdext_control.sail:19 | D 启用（misa.D 静态=1、mstatus.FS≠0、flen≥64）→ 可译码执行 | 是 | 105 Retire（fmax.d: 57,23…） |
| guard 假侧（FS=Off） | 同上 | 不可编码→Illegal | 是 | 5,6,24,25,41（encode pattern match failure） |
| `validDoubleRegs` RV32Zdinx 奇寄存器子分支 | dext:218–230 | RV32+xlen32+Zdinx 时奇 freg 禁用 | 配置不可达 | —（xlen=64 且 Zfinx off） |
| FSGNJ_D/N/X 执行（读→fsplit→fmake→写） | dext:684/696/707 | 符号位替换，无值分支 | 是 | fsgnj.d 各 21 Retire（case 56,52…） |
| `F_or_X_D` 读/写 `hartSupports(Ext_F)` 分支 | fdext_regs.sail:384–396/414–429 | F 寄存器 vs Zfinx X 寄存器 | 仅真侧（静态） | sys_enable_zfinx=false，X 侧配置不可达 |
| `rF_D`/`wF_D` | fdext_regs.sail:351–361 | 64 位直读直写，**无 nan_unbox ite** | 是（无分支） | — |
| FMIN_D→`fp_min_pure` both_nan 臂 | fp_minmax.sail:15 | 双 NaN→canonical NaN | **否** | D gen 操作数全为 +0 |
| FMIN_D op1_nan / op2_nan 臂 | fp_minmax.sail:16/17 | 单 NaN→取另一操作数 | **否** | 同上 |
| FMIN_D ±0 两臂（-0,+0)/(+0,-0) | fp_minmax.sail:18/19 | min 返回 -0 | **否** | 无 ±0 对 |
| FMIN_D cmp 臂 ite(op1<op2) | fp_minmax.sail:20 | 取小者 | 部分：仅 lt=**false** 侧 | 21 case 均 +0 vs +0（110,49…） |
| FMAX_D 对应五臂 | fp_minmax.sail:37–42 | 镜像 | 同 FMIN（仅 cmp/lt=false） | fmax.d 57,23… |
| `riscv_f64Lt_quiet` NV 置位（sNaN 输入） | softfloat_symbolic_f64.sail:22–25 + core/ieee_fp_exceptions.sail:270–274 | fflags.NV=1 | **否** | 无 sNaN（无任何 NaN） |
| `accrue_fflags`(SYMBOLIC) `changed=true` 侧 | fdext_regs.sail:542–554 | 写 FFLAGS 且 mstatus.FS→Dirty | **否** | flags 恒 0、fcsr 初值恒 0 |

### 未达分支（D 独有说明）

fp_minmax 六臂中 **5 个未达**（both_nan/op1_nan/op2_nan/±0 两臂）＋cmp 臂 lt=true 侧：D 无 unbox 旁路，rF_D 直读 64 位，而生成器采样的 f 寄存器值全部为 0（rs1=f0=+0、rs2=fN=+0）。这些臂在模型中可达（f 寄存器为符号值），属采样未覆盖，非死代码。

### 维度小结

- priv：M/S/U 各 7 Retire/mn；负例覆盖 U/M/S。rm 列 gen 全空（不读 rm），负例 rm=rne 仅记录字段。
- FS 状态：gen 仅 FS=Clean（mstatus 单一值 …2000）；FS=Initial 侧未采样（H/S 有）。
- 操作数组合：7 组（rs2∈{f0..f5,f17}）×3 priv=21/mn。
- fcsr 恒 0x0 → FFLAGS/NV 只走了不变侧。

## 2. zF_BIN_F_TYPE_H（fsgnj.h/fsgnjn.h/fsgnjx.h/fmin.h/fmax.h，425 case）

源码：`zfh_insts.sail`（译码 308–326，执行 342–393）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard `haveHalfFPU()` 真侧 | zfh:308–326 + zfh:155 + fext_insts.sail:28 | Zfh 启用 & currentlyEnabled(Ext_F)（含 FS≠0） | 是 | 420 Retire |
| guard 假侧（FS=Off） | 同上 | 不可编码→Illegal | 是 | 5,6,27,30,50（编码 0x24000053 等） |
| guard 右析取 `currentlyEnabled(Ext_Zhinx)` | zfh:155 + zfh:9 | Zhinx（Zfinx）路径 | 配置不可达 | sys_enable_zfinx=false |
| Zfh 支持位（hartSupports(Ext_Zfh)） | core/extensions.sail:174 + fext:28 | IR 配置静态真 | 是（静态） | 420 Retire 证明 H 指令可译码 |
| FSGNJ_H/N/X 执行 + `rF_H`/`wF_H` `nan_unbox` ite | zfh:342/353/364 + fdext_regs.sail:327–337,48–51 | 高位非全 1→canonical NaN，否则取低 16 位 | 是（4 组合全达） | fsgnj.h box00:367,382；box01:221,202；box10:225,207；box11:90,9（各 21 case） |
| FMIN_H→`fp_min_pure`(m=16) both_nan/op1_nan/op2_nan | fp_minmax.sail:15–17 | NaN 臂 | 是 | fmin.h bothNan:423,416；op1Nan:345,348；op2Nan:347,352（各 21，经 unbox canonical qNaN） |
| FMIN_H/FMAX_H ±0 两臂 | fp_minmax.sail:18/19（min），40/41（max） | -0/+0 择小/大 | **否** | 无 ±0 对 |
| cmp 臂 ite(op1<op2)（`riscv_f16Lt_quiet`） | fp_minmax.sail:20/42 + softfloat_symbolic_f16.sail:146–150 | 取小/大者 | 部分：仅 lt=false | fmin.h cmp:56,52（+0 vs +0） |
| `riscv_f16Lt_quiet` NV（sNaN）→`accrue_fflags` changed=true | softfloat_symbolic_f16.sail:146–150 + ieee_fp_exceptions.sail:270–274（16 位版） + fdext_regs.sail:542–554 | fflags.NV | **否** | NaN 全为 canonical qNaN |

### 未达分支

±0 两臂、cmp lt=true 侧、sNaN→NV→changed=true 链。NaN 臂只经 **unbox canonical qNaN** 路径达到（寄存器实际 NaN 位模式路径未单独采样，但与 unbox 臂同属 fp_minmax 同一分支，覆盖等价）。

### 维度小结

- priv M/S/U；FS=Clean（多数）+FS=Initial（…4000，少量）两态；vcsr/vl/vill/sew/lmul 维度扰动多样（含 vill=1、vl=0x7f 等），但 FP execute 不读 vcsr，对控制流无影响。
- 操作数寄存器 f0–f31 广泛（28 组合×3 priv=84/mn），与 4 个 boxed 组合各 21 case 精确吻合。

## 3. zF_BIN_TYPE_F_S（fsgnj.s/fsgnjn.s/fsgnjx.s/fmin.s/fmax.s，425 case）

源码：`fext_insts.sail`（译码 719–737，执行 753–804）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard `haveSingleFPU()` 真侧 | fext:719–737 + fext:253 + fdext_control.sail:18 | F 启用（misa.F=1、FS≠0、Zicsr） | 是 | 420 Retire |
| guard 假侧（FS=Off） | 同上 | 不可编码→Illegal | 是 | 5,6,28,29,50（编码 0x20000053/20001053/20002053/28000053/28001053） |
| guard 右析取 `currentlyEnabled(Ext_Zfinx)` | fext:253 + fdext_control.sail:20 | Zfinx 路径 | 配置不可达 | sys_enable_zfinx=false |
| FSGNJ_S/N/X 执行 + `rF_S`/`wF_S` `nan_unbox` ite | fext:753/764/775 + fdext_regs.sail:339–349,48–51 | 高 32 位非全 1→canonical NaN | 是（4 组合全达） | fsgnj.s box00:367,384；box01:221,205；box10:235,208；box11:100,10 |
| FMIN_S/FMAX_S NaN 三臂（m=32→`riscv_f32Lt_quiet`） | fp_minmax.sail:15–17/34–36 + softfloat_symbolic_f32.sail:31 | NaN 臂 | 是 | fmin.s bothNan:423,416；op1Nan:344,349；op2Nan:347,350 |
| ±0 两臂 / cmp lt=true 侧 | fp_minmax.sail:18–19/40–41/20/42 | 择 -0/取小大 | **否**/部分 | 同 H |
| NV→`accrue_fflags` changed=true | ieee_fp_exceptions.sail:270–274 + fdext_regs.sail:542–554 | sNaN 置 NV | **否** | NaN 全为 canonical qNaN |

### 未达分支

与 H 完全一致：±0 两臂、cmp lt=true、sNV 链。

### 维度小结

- 专门 run（single-f_bin_type_f_s-56cc-20260927-091855），84/mn=83×FS=Clean+1×FS=Initial；vcsr 维度扰动与 H 相同量级；priv M/S/U。

## 4. D(110) vs H/S(425) 差异来源

1. 同 run、同 config（`riscv64_difftest_fd.toml`：RV64、misa=0x…34112f 含 F/D、FS 默认 Dirty 但 mstatus 为符号寄存器）、同 IR（rv64d.ir），故差异**不在源码/config，而在生成覆盖饱和点**（产物按 identity-coverage 去重）。
2. 执行体分支差：D 的 `rF_D` 64 位直读**无 nan_unbox ite**；H/S 读经 nan_unbox（flen=64 下判高位全 1），每条指令 2 个操作数读→(rs1,rs2)boxed 4 组合身份。实测 H/S 每 mn 恰好 4 组合×21=84，D 每 mn 21（7 操作数组合×3 priv）——4 倍差与 unbox 组合数精确对应。
3. 采样维度差：D gen 只采 FS=Clean、寄存器仅 f0..f5/f17；H/S 采 FS=Clean+Initial、寄存器 f0–f31、vcsr 多样。
4. S 为专门 run 仍得 84/mn，与 H 相同，佐证该数量由分支结构（而非 run 预算）决定。

## 5. 全组结论

- **执行期 Illegal 分支不存在**：五个助记符 execute 均无条件 RETIRE_SUCCESS；NaN 不引发 Illegal；frm 不参与。15 个 Illegal 全为 FS=Off 译码负例（encode 阶段 pattern match failure 实证），分布合理。
- 译码 guard 真/假两侧、nan_unbox 4 组合（H/S）、fp_minmax NaN 三臂（H/S）均达到。
- 组级未达（模型可达、采样未覆盖）：① fp_minmax ±0 两臂（min 18–19/max 40–41）全组未达；② cmp 臂 lt=true 侧全组未达（所有非 NaN case 均为 +0 vs +0）；③ D 独有 NaN 三臂未达；④ sNaN→NV→accrue_fflags changed=true 链全组未达。
- 配置不可达（不计缺口）：validDoubleRegs RV32Zdinx 奇寄存器臂、F_or_X 的 Zfinx/X 侧、haveHalfFPU 的 Zhinx 侧、`__isla_vector_fpr`=false 侧。
- 建议补例方向：f 寄存器预置 {±0 对、有限数对（lt 两侧）、boxed sNaN/qNaN 位模式}，即可闭合上述未达臂。

## 版本注记

- `56cc69a4` 是 IR 产物哈希：manifest 记 `stage/rv64d.ir` sha256=`56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`，配套 model-tree-sha256=`fc6857e3…`、config sha=`20851fdb…`；它**不是** sail-riscv 提交号（`git 56cc69a4` 无此修订）。
- 当前 submodule HEAD=f8ce849，工作树带未提交改动：`fext/dext/zfh/fdext_regs/zfa_insts.sail` 修改，`fp_minmax.sail`、`softfloat_symbolic*.sail`、`core/ieee_fp_exceptions.sail` 未跟踪。本文行号取自当前工作树。
- 目标五指令的 encdec/execute 子句在工作树 vs HEAD **无差异**（grep 目标函数行无 +/-）；`fdext_regs.sail` 的本地改动（nan_unbox 由 if-else 改写为单行 ITE、accrue_fflags 新增 SYMBOLIC `ite(changed,…)` 变体、vector-fpr 写路径补 dirty_fd_context）恰与 IR 中这些分支的形态对应（nan_unbox 单行 ITE 已生产应用），故行号与 IR 生成源一致性高；因 56cc 无对应提交可 diff，此为推断而非逐字节核对。
