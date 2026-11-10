# G8 · F_UN_RM_FF_TYPE_D/H/S 分支覆盖对照（Sail 源码 vs 56cc 80416 case）

数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/cases.tsv`（列 run,clause,case,cat,mn,verdict,ret,rm,priv,vl,vill,sew,lmul,fcsr,ins）；clause 名实际带 `z` 前缀。Sail 行号取自当前工作树 `sail-riscv/model/extensions/FD/`，三文件与 IR 56cc69a4 构建源逐字节一致（cmp 验证，见文末版本注记）。

三 clause 同构：一元带 rm 的 float↔float 运算（fsqrt 与格式互转），编码 = funct7 @ rs2 域（00000=fsqrt / 00001/00010=互转源宽）@ rs1 @ rm @ rd @ 0b101_0011。每 mn 计数核对：D 组 fcvt.d.s 与 H 组 fsqrt.h/fcvt.s.h/fcvt.h.s/fcvt.d.h 及 S 组 fsqrt.s 各 79=60R+19I；D 组 fcvt.s.d/fsqrt.d 与 H 组 fcvt.h.d 各 40=30R+10I。

## 0. Illegal 聚类（三 clause 统一，各节引用）

| 类别 | 每 mn 数量（S/H 源 / D 源） | 机制 | 证据 |
| --- | ---: | --- | --- |
| gen，rm=dyn | 18 / 9 | `select_instr_or_fcsr_rm`（fext_insts.sail:51-63）：RM_DYN → 读 `fcsr[FRM]`，FRM∈{5,6}（`valid_rounding_mode` 假，fext:49）或 FRM=7（与 RM_DYN 编码相等，fext:55 第二合取）→ else 分支 → `Fcsr_RM_Illegal => None()`（fext:60）→ execute `None() => Illegal_Instruction()`。fcsr 证据 0xa0/0xc0/0xe0 三档齐全（各 6 / 3 例）。 | D 组 fcvt.d.s 23/25/27…；fcvt.s.d 121/123/124…；fsqrt.d 20/21/24…；H/S 组同类 |
| direct-negative，rm 列=rup | 1 / 1 | **归因已定论（本组用负例 JSON 的 isa-state 定论，区别于 G9 的 A/B 不可定）**：编码 rm 域实为合法 0b011（rup），fcsr=0，但 mstatus=`64'h0000_000a_0000_0000`（FS=00=Off，priv=User）→ `currentlyEnabled(Ext_F/Ext_D)` 假（fdext_control.sail:18-19 要求 `mstatus[FS] != 0b00`）→ 译码 guard `haveSingleFPU/haveDoubleFPU/haveHalfFPU/haveHalfMin` 假 → decode-rejected（负例 `decoded-instruction: ILLEGAL(#x…)`）。附注：D 组 case 3 的 `32'h4200_3053`（funct7=0100001 @ rs2=00000）还兼 rs2 模式洞——fcvt.d.s 要求 rs2=00001，该编码即使 FS 使用也不可译码；其余 8 个负例编码本身均合法。 | D=3/4/35；H=5/9/38/41/69；S=1（负例 JSON：`…/results/F_UN_RM_FF_TYPE_*/input-complete/direct-negative-cases.json`） |

18 vs 9（60R vs 30R）差异根因：**D 源读与 S/H 源读的生成器变体数差异**，非分支结构差异——S/H 源 mn 每 (rm,FRM) cell 6 例、D 源 3 例，Retire/Illegal 全体恰 2 倍（同 G9 第 3 条结论的现象）。

## 1. zF_UN_RM_FF_TYPE_D（fcvt.d.s / fcvt.s.d / fsqrt.d，159 case）

源码：`dext_insts.sail`（encdec 383-409，execute 431-444/506-519/521-534）。

### Illegal 归因

见 §0：18+9+9=36 例 gen dyn-Illegal 全归因 FRM 保留值（fcsr a0/c0/e0）；3 例 direct-negative 归因 FS=Off（case 3 另兼 rs2=00000 模式洞）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard 真：FSQRT_D（haveDoubleFPU & validDoubleRegs([rs1,rd])） | dext_insts.sail:383-385；haveDoubleFPU=dext:214 | 译码命中 | 是 | fsqrt.d 全部 gen case（30R+9I 先译码成功） |
| encdec guard 真：FCVT_S_D（validDoubleRegs([rs1])）/ FCVT_D_S（validDoubleRegs([rd])） | dext_insts.sail:403-405/407-409 | 译码命中 | 是 | fcvt.s.d / fcvt.d.s 全部 gen case |
| encdec guard 假（FS Off → currentlyEnabled(Ext_D) 假） | fdext_control.sail:18-19；dext:214 | 不译码 → Illegal | 是 | direct-negative 3/4/35（mstatus=0xa_0000_0000） |
| rs2 模式洞（0100001@00000 无任何子句匹配） | dext_insts.sail:383-409 模式位 | 不可译码 | 是（与 FS=Off 复合出现） | case 3（0x42003053） |
| 编码 rm=101/110 → encdec_rounding_mode 无反映射 → 译码失败 | fext_insts.sail:31-38 | rm 保留编码拒绝 | **否**（gen rm∈{0..4,7}，负例 rm=011，全 159 case 无一覆盖） | — |
| select：instr_rm≠DYN → Some(instr_rm) | fext_insts.sail:63 | 静态 rm 直用 | 是 | fcvt.d.s 46/57/140/65/143（rne/rtz/rdn/rup/rmm，各 6×3mn） |
| select：DYN+FRM∈0..4 → Some(FRM) | fext_insts.sail:52-56 | 动态取 FRM | 是 | fcvt.d.s 149/157/84/34/22（fcsr 00/20/40/60/80，各 6×3mn） |
| select：DYN+FRM∈{5,6,7} → else | fext_insts.sail:49,55 | FRM 保留值 | 是 | 36 例 fcsr=a0/c0/e0 |
| Fcsr_RM_Fatal → reserved_behavior 致命 | fext_insts.sail:57-58；platform_config.sail:95 | 平台配置另一臂 | 否（运行配置 Fcsr_RM_Illegal，由 verdict 全为 Illegal_Instruction 证实） | — |
| Fcsr_RM_Illegal → None() | fext_insts.sail:60 | 转非法指令 | 是 | 36 例 gen dyn-Illegal |
| execute match None → Illegal_Instruction | dext_insts.sail:434/509/524 | rm 无效异常 | 是 | 39 Illegal（含 3 负例） |
| helper Some 路径：riscv_f64Sqrt / f64ToF32 / f32ToF64 | softfloat_symbolic_f64.sail:65/162-172；softfloat_symbolic_f32.sail:166-172 | 舍入+转换+例外打包 | 是 | 120 Retire 全体 |
| accrue_fflags + F_or_X_D/S 写回 + RETIRE_SUCCESS | dext_insts.sail:439-441/514-516/529-531 | 写回 | 是 | 120 Retire |
| rs1 读 nan_unbox 双臂（仅适用 S 读的 fcvt.d.s） | fdext_regs.sail:49-51（rF_S:339-343） | 上位全 1→取低位；否则→canonical NaN_S | 是（两臂均有） | f0=0xffff_ffff_0000_0000（装箱 +0）→ 臂 1；f0=0（未装箱）→ 臂 2，post 证实 | 
| D 读恒等（fsqrt.d/fcvt.s.d） | fdext_regs.sail:351-355 | rF_D 无 unbox | 是 | 全部 case |
| rd 写 nan_box（fcvt.s.d 写 S）/ wF_D 直写 | fdext_regs.sail:41,345-349,357-361 | 装箱写回 | 是 | fcvt.s.d f0,f0,rtz：post f0=0xffff_ffff_0000_0000（装箱 +0） |
| F_or_X_D/S 的 Zfinx/RV32 偶对分支 | fdext_regs.sail:381/389-395,411/419-428 | Zfinx 语义 | 否（本配置 sys_enable_zfinx=false） | — |
| validDoubleRegs 的 RV32Zdinx 奇数臂 | dext_insts.sail:219-230 | RV32Zdinx 奇寄存器拒绝 | 否（RV64 + Zfinx off，配置域外） | — |
| helper 内部 canonical-NaN ite（fcvt.d.s 宽化，f32ToF64） | softfloat_symbolic_f32.sail:170 | NaN→canonical NaN64 | 是（输入类推得：f0=0 经 unbox 得 qNaN） | fcvt.d.s f0=0 全部 Retire |
| helper 内部 canonical-NaN ite（fcvt.s.d 窄化，f64ToF32） | softfloat_symbolic_f64.sail:171 | NaN→canonical NaN32 | **否**（fcvt.s.d 全部输入 f0=0 即 +0.0，无 NaN 输入 case） | — |
| helper 内部 NaN 臂（fsqrt.d） | softfloat_symbolic_f64.sail:65-69 | sqrt(NaN)→NaN | **否**（fsqrt.d 输入仅 +0.0） | — |
| helper 内部 RoD（rm=0b110）ite（f64ToF32） | softfloat_symbolic_f64.sail:163-170 | rm=110 舍入 | 否且本配置不可达（编码 rm=110 译码失败、FRM=110→None，0b110 无法到达 helper） | — |

### 未达分支小结

① 编码 rm=101/110 的译码失败分支**无任何 case**（本组最主要缺口，9 个 mn 全缺）；② Fcsr_RM_Fatal 配置臂；③ Zfinx/RV32Zdinx 寄存器分支（配置域外）；④ helper 内部 NaN 臂在 D 源读 mn（fsqrt.d、fcvt.s.d）无 NaN 输入 case，未达；⑤ helper 内部 rm=110（RoD）分支配置性不可达。

### rm 覆盖矩阵（每 mn）

| rm\结果 | Retire | Illegal |
| --- | ---: | --- |
| rne/rtz/rdn/rup/rmm | 各 6（fcvt.d.s）/ 3（fcvt.s.d、fsqrt.d） | 0（rup 的 1 例 Illegal 为 direct-negative FS=Off，非 rm 语义归因） |
| dyn,FRM=0..4（fcsr 00/20/40/60/80） | 各 6 / 3 | 0 |
| dyn,FRM=5/6/7（fcsr a0/c0/e0） | 0 | 各 6 / 3 |
| 编码 rm=5/6 | 0 | **0（无 case）** |

## 2. zF_UN_RM_FF_TYPE_H（fsqrt.h + fcvt.s.h/h.s/h.d/d.h，356 case）

源码：`zfh_insts.sail`（encdec 470-504，execute 529-542/604-617/619-632/634-647/649-662）。

### Illegal 归因

同 §0：4×18+9=81 例 gen dyn-Illegal 全归因 FRM 保留值；5 例 direct-negative 归因 FS=Off（case 5/9/38/41/69，mstatus=0xa_0000_0000）。

### 宽转窄额外 guard（任务关注点）

- fsqrt.h：`haveHalfFPU()`（zfh_insts.sail:470-472，=currentlyEnabled(Ext_Zfh)｜Ext_Zhinx，zfh:155）→ **要求完整 Zfh/Zhinx**。
- fcvt.h.s/h.d 与 s.h/d.h（h↔s/d 互转四条）：`haveHalfMin()`（zfh:490-504，=haveHalfFPU｜Ext_Zfhmin｜Ext_Zhinxmin，zfh:158）→ **仅需 Zfhmin 即可，弱于 Zfh**；`currentlyEnabled(Ext_Zfhmin)=(hartSupports(Zfhmin)&Ext_F)｜Ext_Zfh`（fext_insts.sail:29）。
- fcvt.h.d / fcvt.d.h 额外 `haveDoubleFPU() & validDoubleRegs([rs1]/[rd])`（zfh:496/504）→ 交叉端 D 扩展使能 + D 侧寄存器有效（RV32Zdinx 奇数臂 dext:219-230 本配置不可达）。
- FS=Off 经 `currentlyEnabled(Ext_Zfh)=hartSupports(Zfh)&currentlyEnabled(Ext_F)`（fext:28）与 Ext_Zfhmin 同路传导为假 → 5 个负例同时覆盖 Zfh/Zfhmin guard 假臂；但"F 使能而 Zfh 单独关闭"维度单配置 replay 不可测（配置域）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard 真：FSQRT_H（haveHalfFPU） | zfh_insts.sail:470-472 | 译码命中（需完整 Zfh） | 是 | fsqrt.h 全部 gen case（60R+18I） |
| encdec guard 真：FCVT_H_S/S_H（haveHalfMin） | zfh_insts.sail:490-492/498-500 | 译码命中（Zfhmin 即可） | 是 | fcvt.h.s / fcvt.s.h 全部 gen case |
| encdec guard 真：FCVT_H_D/D_H（haveHalfMin & haveDoubleFPU & validDoubleRegs） | zfh_insts.sail:494-496/502-504 | 译码命中 + D 端 guard | 是 | fcvt.h.d / fcvt.d.h 全部 gen case |
| guard 假（FS Off→Ext_F/Zfh/Zfhmin 全假） | fext_insts.sail:28-29；fdext_control.sail:18 | 不译码 → Illegal | 是 | direct-negative 5/9/38/41/69 |
| 编码 rm=101/110 译码失败 | fext_insts.sail:31-38 | rm 保留编码拒绝 | **否**（356 case 无一覆盖） | — |
| select 静态 rm / DYN+FRM∈0..4 / FRM∈{5,6,7}→None / Fatal 配置臂 | fext_insts.sail:51-63（同 §1） | 同 §1 | 是/是/是/否 | fcvt.d.h 267/103/274/114/294（固定 rm）；21/34/303/304/157（fcsr 00..80）；133/296/30（a0/c0/e0）；其余 mn 同构 |
| execute match None → Illegal_Instruction | zfh_insts.sail:532/607/622/637/652 | rm 无效异常 | 是 | 86 Illegal（含 5 负例） |
| helper Some 路径：riscv_f16Sqrt/f32ToF16/f64ToF16/f16ToF32/f16ToF64 | softfloat_symbolic_f16.sail:44-49/126-131/133-138；f32.sail:174-184；f64.sail:154-160 | 舍入+转换 | 是 | 270 Retire |
| accrue_fflags + F_or_X_H/S/D 写回 + RETIRE_SUCCESS | zfh_insts.sail:537-539/612-614/627-629/642-644/657-659 | 写回 | 是 | 270 Retire |
| rs1 读 nan_unbox 双臂（H 读：fsqrt.h/s.h/d.h；S 读：h.s） | fdext_regs.sail:49-51（rF_H:327-331，rF_S:339-343） | 装箱→低位；未装箱→canonical NaN_H/S | 是（两臂均有） | f0=0xffff_ffff_ffff_0000（装箱 +0）vs f0=0（→canonical NaN，post 证实） |
| D 读恒等（fcvt.h.d） | fdext_regs.sail:351-355 | rF_D 无 unbox | 是 | fcvt.h.d 全部 case |
| rd 写 nan_box（H/S 写）/ wF_D 直写 | fdext_regs.sail:41,333-349 | 装箱写回 | 是 | fsqrt.h f0,f0,rmm：post f0=0xffff_ffff_ffff_7e00 |
| F_or_X_* Zfinx/Zhinx 分支 | fdext_regs.sail:373/403 等 | Zfinx 语义 | 否（配置域外） | — |
| validDoubleRegs RV32Zdinx 奇数臂 | dext_insts.sail:219-230 | RV32Zdinx 拒绝 | 否（配置域外） | — |
| helper 内部 canonical-NaN ite NaN 臂（S/H 源 mn：fsqrt.h、fcvt.h.s、fcvt.s.h、fcvt.d.h） | f16.sail:48/130/137；f32.sail:180-182 | NaN→canonical NaN | 是（输入类含 qNaN，经 unbox 产生） | fsqrt.h f0=0 → post 0xffff_ffff_ffff_7e00；fcvt.h.s f0=0 → post 0xffff_ffff_ffff_7e00（**窄化 canonical NaN 有 post 直接证据**） |
| helper 内部 canonical-NaN ite NaN 臂（D 源 mn：fcvt.h.d） | f64.sail:158 | NaN→canonical NaN16 | **否**（fcvt.h.d 输入仅 +0.0） | — |
| helper 内部 RoD（rm=110）分支（f32ToF16/f64ToF16） | f32.sail:175,181-182；f64.sail:154-159 同构 | rm=110 舍入 | 否且配置不可达（同 §1⑤） | — |

### 未达分支小结

同 §1 五项，其中 helper NaN 臂缺口仅在 D 源 mn（fcvt.h.d）；另有"F 使能而 Zfh/Zfhmin 单独关闭"维度单配置不可测（配置域，非 case 缺口）。

### rm 覆盖矩阵（每 mn）

与 §1 矩阵完全同构：S/H 源 mn（fsqrt.h、fcvt.s.h、fcvt.h.s、fcvt.d.h）固定 rm 与 dyn+FRM=0..4 各 6 Retire、FRM∈{5,6,7} 各 6 Illegal；D 源 mn（fcvt.h.d）各 3；编码 rm=5/6 全组 0 case。

## 3. zF_UN_RM_FF_TYPE_S（fsqrt.s，79 case）

源码：`fext_insts.sail`（encdec 495-497，execute 535-548）。

### Illegal 归因

见 §0：18 例 gen dyn-Illegal 归因 FRM 保留值；1 例 direct-negative（case 1，0x58003053 = fsqrt.s f0,f0,rup 合法编码）归因 FS=Off（mstatus=0xa_0000_0000）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard 真：haveSingleFPU() | fext_insts.sail:495-497；haveSingleFPU=fext:253 | 译码命中 | 是 | 78 gen case |
| encdec guard 假（FS Off → Ext_F 假） | fdext_control.sail:18 | 不译码 → Illegal | 是 | direct-negative case 1 |
| 编码 rm=101/110 译码失败 | fext_insts.sail:31-38 | rm 保留编码拒绝 | **否**（79 case 无一覆盖） | — |
| select 静态 rm | fext_insts.sail:63 | 静态 rm 直用 | 是 | 47/23/25/28/64（rne/rtz/rdn/rup/rmm，各 6） |
| select DYN+FRM∈0..4 → Some | fext_insts.sail:52-56 | 动态取 FRM | 是 | 17/55/48/21/13（fcsr 00/20/40/60/80，各 6） |
| select DYN+FRM∈{5,6,7} → Fcsr_RM_Illegal→None | fext_insts.sail:49,55,60 | FRM 保留值转非法 | 是 | 73/67/53（a0/c0/e0，各 6） |
| Fcsr_RM_Fatal 臂 | fext_insts.sail:57-58 | 配置另一臂 | 否 | — |
| execute match None → Illegal_Instruction | fext_insts.sail:538 | rm 无效异常 | 是 | 19 Illegal |
| helper Some：riscv_f32Sqrt | softfloat_symbolic_f32.sail:77-82 | sqrt+例外打包 | 是 | 60 Retire |
| accrue_fflags + F_or_X_S 写回 + RETIRE_SUCCESS | fext_insts.sail:543-545 | 写回 | 是 | 60 Retire |
| rs1 读 nan_unbox 双臂 | fdext_regs.sail:49-51（rF_S:339-343） | 装箱/未装箱 | 是（两臂均有） | f0=0xffff_ffff_0000_0000（+0.0，post 不变）vs f0=0（→canonical NaN_S） |
| rd 写 nan_box | fdext_regs.sail:41,345-349 | 装箱写回 | 是 | f0=0 case：post f0=0xffff_ffff_7fc0_0000（case 47 等） |
| F_or_X_S Zfinx 分支 | fdext_regs.sail:381/411 | Zfinx 语义 | 否 | — |
| helper 内部 NaN 结果路径（riscv_f32_symbolic_bits） | softfloat_symbolic_f32.sail:9,81 | NaN→canonical | 是（f0=0 经 unbox 得 qNaN 输入，post 为 boxed canonical NaN_S） | case 47/23/25/28/64（f0=0 类） |
| helper 内部 RoD（rm=110）分支 | —（f32Sqrt 无 RoD ite） | 不存在该分支 | —（f32Sqrt 直用 rm，无 110 特判） | — |

qNaN 语义注记：sqrt(qNaN) 与 sqrt(+0) 均不置位 fflags（IEEE：qNaN 输入静默、√+0=+0），post fcsr 与 in 相同（如 case 47：fcsr=0 前后一致）——正确行为，非写回缺失。

### 未达分支小结

① 编码 rm=101/110 译码失败（无 case）；② Fcsr_RM_Fatal；③ Zfinx 分支。helper 内部 NaN 臂本 clause 已达（经 nan_unbox 制造 qNaN 输入）。

### rm 覆盖矩阵（每 mn=fsqrt.s）

| rm\结果 | Retire | Illegal |
| --- | ---: | --- |
| rne/rtz/rdn/rup/rmm | 各 6 | 0（rup 的 1 例 Illegal 为 FS=Off 负例） |
| dyn,FRM=0..4 | 各 6 | 0 |
| dyn,FRM=5/6/7 | 0 | 各 6 |
| 编码 rm=5/6 | 0 | **0（无 case）** |

## 4. 全组结论

1. **语义层控制流基本全覆盖**：9 个 mn 的译码 guard 真臂（含 TYPE_H 的 Zfhmin/Zfh 分层 guard 与 h↔d 交叉 validDoubleRegs）、select 静态 rm 5 值、DYN×FRM∈{0..4}、DYN×FRM∈{5,6,7}→None→Illegal_Instruction、helper Some 路径、accrue_fflags、装箱写回、RETIRE_SUCCESS 全部有 case 达到；rm 维度指令编码 8 值中 6 值、FRM 8 值全枚举。
2. **gen 内 Illegal 全部归因 FRM 保留值**（fcsr=0xa0/0xc0/0xe0 → Fcsr_RM_Illegal → None()），每 mn 9 或 18 例；**direct-negative 归因已定论为 FS=Off**——负例 JSON 的 isa-state 直接给出 mstatus=`0x0000_000a_0000_0000`（FS=00）、编码 rm=0b011 合法，属译码 guard（fdext_control.sail:18-19）拒绝而非 rm 保留编码。此结论同步解决 G9（FX 组）遗留的 A/B 归因问题：已抽验 F_UN_RM_FX_TYPE_D/S 负例（case 5/6）mstatus 同为 FS=Off，G9 §0 的候选 (B) 成立、(A) 不成立。
3. **唯一 case 级缺口：编码 rm=101/110 的译码失败分支**（fext_insts.sail:31-38 无反映射），三 clause 594 case 中无一覆盖；负例生成器选择了 FS=Off 反例而非 rm 保留编码反例。如需闭合，可补充 rm=101/110 编码的 direct-negative。
4. **NaN 规范化路径**：S/H 源读 mn 经 nan_unbox（fdext_regs.sail:49-51）两臂均有 case——f0=0 未装箱读出 canonical qNaN 是 NaN 输入的制造机制；fcvt 窄化 canonical NaN 路径属 helper 内部（f32.sail:170/180-182、f64.sail:158/171、f16.sail:48/130/137），其中 fcvt.h.s 有 post 直接证据（f0=0 → post 0xffff_ffff_ffff_7e00）；**D 源读 mn（fsqrt.d、fcvt.s.d、fcvt.h.d）无 NaN 输入 case，其 helper NaN 臂未达**（rF_D 恒等读，gen 输入只有 +0.0）。
5. **18/9 与 60/30 的数量差异是生成器变体数**（S/H 源每 cell 2 组寄存器变体、D 源 1 组），三 clause 分支结构同构。
6. **系统性未达分支**（配置域，非 case 可闭合）：Fcsr_RM_Fatal 臂、Zfinx/Zhinx/RV32Zdinx/RV32 偶对寄存器分支、"F 使能而 Zfh 单独关闭"维度、helper 内部 rm=110（RoD）分支（编码与 FRM 两条路都到不了 0b110）。

## 版本注记

- IR 56cc69a4（SHA-256 `56cc69a44ee1…35996ac`，2026-09-27 构建，run `official-56cc-long-20260927-064348`；本组 case 出自 `single-56cc-20260927-014615-05/06/07-*` replay 包，manifest 记录 `sail_riscv_head=f8ce8490981eac6396a31013180a2e718615757d`，Sail 0.20.1 feat/float-support）的构建源副本位于 `isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/sail-riscv/`；本报告以 `cmp` 验证 `fext_insts.sail`、`dext_insts.sail`、`zfh_insts.sail` 三文件与当前工作树**逐字节一致**，全部行号对两版本同时成立。
- 当前工作树相对子模块 HEAD f8ce849 在三文件上有未提交修改（negate_* 改 XOR、FMIN/FMAX 改 fp_min/fp_max_pure、旧辅助函数注释），经 diff 核对均不触及 F_UN_RM_FF_TYPE_* 的 encdec/execute/类型定义段（FMIN/FMAX 改动位于 dext:719-745、fext:787-817、zfh:376-406，与本组行号无交叠）。
- 配置证据：replay 配置 `stage/configs/riscv64_difftest_fd.toml`（sys_enable_fdext=true、sys_enable_zfinx=false、misa=0x34112f 含 F/D、mstatus 缺省 0x6600 FS=Dirty）；fcsr_rm_reserved_behavior 取 Fcsr_RM_Illegal 系行为证据反推（FRM 保留值时 verdict 一律 Illegal_Instruction 而非 fatal 停机），配置注入点 `platform_config.sail:95`。
- 负例与 gen 用例明细 JSON：`isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-incremental-56cc69-20260927/results/F_UN_RM_FF_TYPE_{D,H,S}/input-complete/`（direct-negative-cases.json / gen-cases.json）；cases.tsv 的 clause 名带 `z` 前缀（isarch 内部命名）。
