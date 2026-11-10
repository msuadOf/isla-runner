# G9 · F_UN_RM_FX_TYPE_D/H/S 分支覆盖对照（Sail 源码 vs 56cc 80416 case）

数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/cases.tsv`（列 run,clause,case,cat,mn,verdict,ret,rm,priv,vl,vill,sew,lmul,fcsr,ins）。clause 名实际带 `z` 前缀。Sail 行号取自当前工作树 `sail-riscv/model/extensions/FD/`，三文件与 IR 56cc69a4 构建源逐字一致（见文末版本注记），行号对两个版本同时有效。

三 clause 同构：每 clause 4 条指令（fcvt.{w,wu,l,lu}.{d,h,s}），编码 = funct5(1100000/1100010/1100001) @ rs2 域(00000/00001/00010/00011) @ rs1 @ rm @ rd @ 0b101_0011。每 mn 计数核对：D 每 mn 70 = 60 Retire + 10 Illegal（280=4×70）；H/S 每 mn 139 = 120 Retire + 19 Illegal（556=4×139）。

## 0. Illegal 聚类（三 clause 统一，先给出，各节引用）

| 类别 | 每 mn 数量（D / H,S） | 机制 | 证据 |
| --- | ---: | --- | --- |
| direct-negative，rm 列=rup | 1 / 1 | ins 打印 `fcvt.xx.x x0, f0, rup` 且 fcsr=0（FRM=0 合法）却 Illegal。候选归因二选一（tsv 无 misa/FS 列，无法定论）：**(A)** 编码 rm 域实为保留值 101/110，`encdec_rounding_mode`（fext_insts.sail:31-38）无该反映射 → 译码失败，rm 列/ins 的 "rup" 为工具解析回落（旁证：F_BIN_RM_TYPE_D 负例 rm 列打印 rmm 同样与 Illegal 矛盾）；**(B)** `haveFPU()` guard 为假（mstatus.FS=Off，同 G6 的排除法归因）。 | case：D=37/38/5/6（l/w/wu/lu.d），H=39/40/5/6，S=39/40/5/6 |
| gen，rm=dyn | 9 / 18 | `select_instr_or_fcsr_rm`（fext_insts.sail:51-63）：RM_DYN → 读 `fcsr[FRM]`，FRM∈{5,6}（`valid_rounding_mode` 假，fext:49）或 FRM=7（等于 RM_DYN 编码）→ else 分支 → `Fcsr_RM_Illegal => None()`（fext:60）→ execute `None() => Illegal_Instruction()`。fcsr 证据：0xa0/0xc0/0xe0（FRM=5/6/7）三档齐全，各 priv（M/S/U）齐全。 | D：fcsr a0=c0=e0 各 3×4mn；H/S：各 6×4mn |

19 vs 10 差异根因（任务原文"H 19 vs S/D 10"；实测 S=19、D=10，差异实为 **D vs H/S**）：1（direct-negative）+ 18 vs 1 + 9。gen dyn-Illegal = 3 个 FRM 保留值 × 3 priv × 每 (mn,priv,FRM) 变体数：H/S 产 2 组寄存器变体（如 fcvt.l.h fcsr=a0：M=x3/x17、S=x28/x3、U=x29/x29），D 只产 1 组（如 fcvt.l.d fcsr=a0：M=x28/U=x16/S=x13）。Retire 同比例（每 rm 12 vs 6）。纯生成器用例变体数差异，三 clause 分支结构完全相同。

## 1. zF_UN_RM_FX_TYPE_D（fcvt.l/lu/w/wu.d，280 case）

源码：`dext_insts.sail`（encdec 387-427，execute 446-566）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard 真：haveDoubleFPU & validDoubleRegs([rs1])（w/wu） | dext_insts.sail:387-393；haveDoubleFPU=dext:214,validDoubleRegs=dext:219 | 译码命中（本配置 Ext_D 启用、32 fregs 恒真） | 是 | 全部 276 gen case（Retire 与 dyn-Illegal 均先译码成功） |
| encdec guard 真：& xlen>=64（l/lu） | dext_insts.sail:413-419 | RV64 才有 l/lu | 是（xlen=64 恒真） | fcvt.l.d/lu.d 全部 case |
| encdec guard 假（FS Off 或 rm 域 5/6 反映射失败） | dext_insts.sail:387-427；fext_insts.sail:31-38 | 不译码 → Illegal | 不可定（见 §0 归因 A/B；若 A 或 B 任一成立即达到） | 候选：37/38/5/6 |
| select：instr_rm≠DYN → Some(instr_rm) | fext_insts.sail:63 | 静态 rm 直用 | 是 | fcvt.w.d 74(rne)/77(rtz)/220(rdn)/87(rup)/167(rmm)，各 6×4mn |
| select：DYN+FRM∈0..4 → Some(FRM) | fext_insts.sail:54-56 | 动态取 FRM | 是 | fcvt.w.d 105/…/1（fcsr 00/20/40/60/80 各 6×4mn） |
| select：DYN+FRM∈{5,6} → else | fext_insts.sail:49,55 | FRM 保留值 | 是 | 36 例 fcsr=a0/c0 |
| select：DYN+FRM=7 → else | fext_insts.sail:55 | FRM=DYN 编码亦保留 | 是 | 36 例 fcsr=e0 |
| fcsr_rm_reserved_behavior=Fcsr_RM_Fatal → reserved_behavior | fext_insts.sail:57-58；platform_config.sail:95 | 平台配置另一分支 | 否（运行配置为 Fcsr_RM_Illegal，由 verdict 全为 Illegal_Instruction 证实） | — |
| fcsr_rm_reserved_behavior=Fcsr_RM_Illegal → None() | fext_insts.sail:60 | 转非法指令 | 是 | 108 例 gen dyn-Illegal |
| execute match None → Illegal_Instruction | dext_insts.sail:449/464/540/556 | rm 无效异常 | 是 | 40 Illegal（含 4 负例） |
| execute assert(xlen>=64) 失败 | dext_insts.sail:537/553 | RV32 防御 | 否（encdec when 已挡 RV32，不可达） | — |
| helper Some 路径：riscv_f64ToI32/Ui32/I64/Ui64 | softfloat_symbolic_f64.sail:86/96/106/116 | 舍入+转换+例外打包 | 是（每 mn 60 Retire） | fcvt.w.d Retire 全体 |
| helper 内部 ite(ieee_has_invalid, invalid, candidate)（NaN/越界→0x7fff…/0x8000…，正负各一臂） | softfloat_symbolic_f64.sail:90-93 等；ieee_fp64_to_int_exceptions=core/ieee_fp_exceptions.sail:863-867, ieee_has_invalid=62 | 越界/NaN 写特定值 | 不可判（**返回值层面不可区分**：tsv 只记 verdict=Retire_Success，无 rd 值与 fflags，两臂在 verdict 层同象） | — |
| accrue_fflags | fdext_regs.sail:542/556 | FFLAGS 累加 | 是（所有 Retire 走到） | 240 Retire |
| X(rd)=sign_extend + RETIRE_SUCCESS | dext_insts.sail:455-456/470-471/546-547/562-563 | 写回 | 是 | 240 Retire |
| rF/wF F_or_X_D 的 F 寄存器堆分支 | fdext_regs.sail:384/414 | Ext_F 启用 | 是 | 全部 case |
| F_or_X_D 的 Zfinx/RV32 偶对分支 | fdext_regs.sail:389-395/419-428 | Zfinx 语义 | 否（本配置未启用 Zfinx） | — |
| riscv_valid_rm_to_ieee ite 链 5 臂 | softfloat_symbolic.sail:23-28 | rm 0..4→IEEE mode | 是（rm 全枚举间接覆盖） | 全部 Retire |

### 未达分支小结
① Fcsr_RM_Fatal 配置分支未行使（有意排除）；② helper 内部 invalid/candidate 两臂与 positive 臂不可判（数据无 rd/fflags）；③ F_or_X_D 的 Zfinx/RV32 分支；④ encdec guard 假分支：达到与否取决于负例归因 A（rm 域 5/6，则达到）或 B（FS Off，则达到），两者必居其一但 tsv 无法区分。

### rm 覆盖矩阵（每 mn）

| rm\结果 | Retire | Illegal |
| --- | ---: | --- |
| rne/rtz/rdn/rup/rmm | 各 6 | 0（rup 的 1 例 Illegal 为 direct-negative，非 rm 语义归因） |
| dyn,FRM=0..4（fcsr 00/20/40/60/80） | 各 6 | 0 |
| dyn,FRM=5/6/7（fcsr a0/c0/e0） | 0 | 各 3 |
| 编码 rm=5/6 | 0 | 0 或 1（取决于负例归因 A/B，不可定） |

## 2. zF_UN_RM_FX_TYPE_H（fcvt.l/lu/w/wu.h，556 case）

源码：`zfh_insts.sail`（encdec 474-480、511-517，execute 544-557、559-572、664-678、680-694）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard 真：haveHalfFPU()（w/wu） | zfh_insts.sail:474-480；haveHalfFPU=zfh:155 | 译码命中（Ext_Zfh 启用） | 是 | 全部 552 gen case |
| encdec guard 真：& xlen>=64（l/lu） | zfh_insts.sail:511-517 | RV64 | 是 | fcvt.l.h/lu.h 全部 |
| encdec guard 假 | zfh_insts.sail:474-517；fext_insts.sail:31-38 | 不译码 → Illegal | 不可定（同 §0 归因 A/B） | 候选：39/40/5/6 |
| select：instr_rm≠DYN → Some(instr_rm) | fext_insts.sail:63 | 静态 rm | 是 | fcvt.w.h 486(rne)/9(rtz)/534(rdn)/306(rup)/108(rmm)，各 12×4mn |
| select：DYN+FRM∈0..4 → Some(FRM) | fext_insts.sail:54-56 | 动态取 FRM | 是 | fcvt.w.h 357/…/164（fcsr 五档各 12×4mn） |
| select：DYN+FRM∈{5,6,7} → else→Fcsr_RM_Illegal→None | fext_insts.sail:49,55,57-61 | FRM 保留值 | 是 | 72 例 gen dyn-Illegal（fcsr a0/c0/e0 各 24） |
| Fcsr_RM_Fatal → reserved_behavior | fext_insts.sail:58 | 配置分支 | 否（同上，Fcsr_RM_Illegal 生效） | — |
| execute match None → Illegal_Instruction | zfh_insts.sail:547/562/668/682 | rm 无效异常 | 是 | 76 Illegal（含 4 负例） |
| execute assert(xlen>=64) 失败 | zfh_insts.sail:665/681 | RV32 防御 | 否（encdec 已挡） | — |
| helper：riscv_f16ToI32/Ui32/I64/Ui64 | softfloat_symbolic_f16.sail:51/61/71/81 | 舍入+转换 | 是（每 mn 120 Retire） | fcvt.w.h Retire 全体 |
| helper 内部 NaN/越界→特定值（ite(invalid,candidate) 等） | softfloat_symbolic_f16.sail:51-90；ieee_fp16_to_int_exceptions=core/ieee_fp_exceptions.sail:767 | 越界/NaN 写 MAX/MIN | 不可判（返回值层面不可区分，同 §1） | — |
| accrue_fflags + X(rd)=sign_extend + RETIRE_SUCCESS | zfh_insts.sail:552-554 等；fdext_regs.sail:542/556 | 写回 | 是 | 480 Retire |
| rF/wF F_or_X_H F 堆分支 | fdext_regs.sail:368/398 | Ext_F 启用 | 是 | 全部 case |
| F_or_X_H Zhinx 分支（rF:373 / wF:403） | fdext_regs.sail:368-404 | Zhinx 语义 | 否（未启用 Zhinx） | — |

### 未达分支小结
同 §1：① Fcsr_RM_Fatal；② helper 内部数值臂不可判；③ Zhinx/RV32 寄存器分支；④ encdec guard 假分支归因不可定。

### rm 覆盖矩阵（每 mn）

| rm\结果 | Retire | Illegal |
| --- | ---: | --- |
| rne/rtz/rdn/rup/rmm | 各 12 | 0 |
| dyn,FRM=0..4 | 各 12 | 0 |
| dyn,FRM=5/6/7 | 0 | 各 6 |
| 编码 rm=5/6 | 0 | 0 或 1（同 §1 归因不可定） |

## 3. zF_UN_RM_FX_TYPE_S（fcvt.l/lu/w/wu.s，556 case）

源码：`fext_insts.sail`（encdec 499-505、517-523，execute 550-563、565-578、610-624、626-640）。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard 真：haveSingleFPU()（w/wu） | fext_insts.sail:499-505；haveSingleFPU=fext:253 | 译码命中（Ext_F 启用，无 validSingleRegs 附加条件——与 D 版 guard 差异：S 不查寄存器宽度） | 是 | 全部 552 gen case |
| encdec guard 真：& xlen>=64（l/lu） | fext_insts.sail:517-523 | RV64 | 是 | fcvt.l.s/lu.s 全部 |
| encdec guard 假 | fext_insts.sail:499-523；fext_insts.sail:31-38 | 不译码 → Illegal | 不可定（同 §0 归因 A/B） | 候选：39/40/5/6 |
| select：instr_rm≠DYN → Some(instr_rm) | fext_insts.sail:63 | 静态 rm | 是 | fcvt.w.s 488(rne)/10(rtz)/534(rdn)/303(rup)/106(rmm)，各 12×4mn |
| select：DYN+FRM∈0..4 → Some(FRM) | fext_insts.sail:54-56 | 动态取 FRM | 是 | fcsr 五档各 12×4mn |
| select：DYN+FRM∈{5,6,7} → else→Fcsr_RM_Illegal→None | fext_insts.sail:49,55,57-61 | FRM 保留值 | 是 | 72 例（fcsr a0/c0/e0 各 24；样本 fcvt.l.s 209/240/56/424/441/222） |
| Fcsr_RM_Fatal → reserved_behavior | fext_insts.sail:58 | 配置分支 | 否 | — |
| execute match None → Illegal_Instruction | fext_insts.sail:553/568/614/630 | rm 无效异常 | 是 | 76 Illegal（含 4 负例） |
| execute assert(xlen>=64) 失败 | fext_insts.sail:611/627 | RV32 防御 | 否（encdec 已挡） | — |
| helper：riscv_f32ToI32/Ui32/I64/Ui64 | softfloat_symbolic_f32.sail:98/108/118/128 | 舍入+转换 | 是（每 mn 120 Retire） | fcvt.w.s Retire 全体 |
| helper 内部 NaN/越界→特定值 | softfloat_symbolic_f32.sail:98-137；ieee_fp32_to_int_exceptions=core/ieee_fp_exceptions.sail:815 | 越界/NaN 写 MAX/MIN | 不可判（返回值层面不可区分，同 §1） | — |
| accrue_fflags + X(rd)=sign_extend + RETIRE_SUCCESS | fext_insts.sail:558-560 等；fdext_regs.sail:542/556 | 写回 | 是 | 480 Retire |
| rF/wF F_or_X_S F 堆分支 | fdext_regs.sail:376/406 | Ext_F 启用 | 是 | 全部 case |
| F_or_X_S Zfinx 分支（rF:381 / wF:411） | fdext_regs.sail:376-412 | Zfinx 语义 | 否 | — |

### 未达分支小结
同 §1 四项。

### rm 覆盖矩阵（每 mn）

与 §2 完全相同（各 12 / 12 / 6，编码 rm=5/6 同归因不可定）。

## 4. 全组结论

1. **三 clause 语义层控制流全覆盖**：译码 guard 真臂、select 的静态 rm、DYN+FRM∈0..4、DYN+FRM∈{5,6,7}→None→Illegal_Instruction、helper Some 路径、accrue_fflags、sign_extend 写回、RETIRE_SUCCESS 全部有 case 达到；rm 维度 5 静态 × DYN×FRM{0..7} = 11 种组合全枚举，无一遗漏。
2. **gen 内 Illegal 全部归因 FRM 保留值**（fcsr=0xa0/0xc0/0xe0 → `fcsr_rm_reserved_behavior=Fcsr_RM_Illegal` → `None()`），共 9/18 per mn；direct-negative 每 mn 1 例的归因（rm 域保留值编码 vs FS=Off guard）在 tsv 无 misa/FS 列下不可定，两候选机制均已列明。
3. **19 vs 10 差异是生成器变体数，非分支结构差异**：任务原文"S/D 10"应为"D 10"（S 实测 19）；H/S 每 (mn,priv,FRM) 产 2 组寄存器变体、D 产 1 组，Retire/Illegal 全体恰 2 倍。
4. **helper 内部路径返回值层面不可区分**：float→int 的越界/NaN→MAX/MIN 特定值路径（`ite(ieee_has_invalid(flags), invalid, candidate)` 及 positive 臂）在 softfloat_symbolic_*.sail 内部，cases.tsv 只记 verdict=Retire_Success，无 rd 值/fflags 输出，覆盖不可判；如需闭合须引入结果寄存器/FCSR 终态比对。
5. **系统性未达分支**（三 clause 相同）：Fcsr_RM_Fatal 配置臂（有意排除）、Zfinx/Zhinx/RV32 寄存器分支（配置域外）、execute assert 防御臂（被 encdec when 前置挡住）。

## 版本注记

- IR 56cc69a4（SHA-256 `56cc69a44ee1…35996ac`，2026-09-27 构建，run `official-56cc-long-20260927-064348`，80416 case 即出自该 IR）的构建源副本位于 `isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/sail-riscv/`；`fext_insts.sail`、`dext_insts.sail`、`zfh_insts.sail` 三文件与当前生产工作树**逐字节一致**（diff 验证），本文全部行号对 IR 版本与当前工作树同时成立。
- 当前工作树相对子模块 HEAD f8ce849 在这三个文件上有未提交修改（negate_* 改 XOR、FMIN/FMAX 改 fp_min/fp_max_pure、注释），但均不触及 F_UN_RM_FX_TYPE_* 的 encdec/execute/类型定义段；FCVT 段在 HEAD 与工作树间行号与内容亦一致（zfh 的 FMIN/FMAX 改动位于 36-395 区段，影响其自身后续行号但不影响 474+ 的 FCVT 段——两版本对照确认 474/544 等锚点行号相同）。
- 配置证据：fcsr_rm_reserved_behavior 取 Fcsr_RM_Illegal 系**行为证据**反推（FRM 保留值时 verdict 一律 Illegal_Instruction 而非 fatal 停机）；`platform_config.sail:95` 为配置注入点，运行包内未发现显式配置文件。
