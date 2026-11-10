# G6 · F_MADD_TYPE_D/H/S 分支覆盖对照（Sail 源码 vs 56cc 80416 case）

数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/cases.tsv`（列 run,clause,case,cat,mn,verdict,ret,rm,priv,vl,vill,sew,lmul,fcsr,ins）。clause 名实际带 `z` 前缀（zF_MADD_TYPE_D/H/S）。Sail 行号取自当前工作树 `sail-riscv/model/extensions/FD/`（HEAD f8ce849，MADD 区域无未提交改动，见文末版本注记）。

- F_MADD_TYPE_D：1096 = run `representatives-56cc-20260927-061428`（official-d-1096 代表批）。
- F_MADD_TYPE_H：8740 = run `single-56cc-20260927-020959-01-f_madd_type_h`（H/S FMA 续批）。
- F_MADD_TYPE_S：8740 = run `single-56cc-20260927-020959-02-f_madd_type_s`。

每 mn 计数核对：D 每 mn 274 = 64 Illegal（63 dyn + 1 负例）+ 210 Retire（105 dyn + 105 静态 rm）；H/S 每 mn 2185 = 504 Illegal（全 dyn）+ 1680 Retire（840 dyn + 840 静态），另每 clause 4 条负例（mn 为原始编码）。

## 1. zF_MADD_TYPE_D（fmadd/fmsub/fnmadd/fnmsub.d，1096 case）

源码：`dext_insts.sail:245-306`。

### Illegal 归因（256 例）

| 来源 | 数量/mn | 机制 |
| --- | ---: | --- |
| gen, rm=dyn | 63 | `select_instr_or_fcsr_rm`（fext_insts.sail:51-63）：instr_rm=RM_DYN 时读 `fcsr[FRM]`，FRM∈{5,6}（`valid_rounding_mode` 为假，fext:49）或 FRM=7（等于 RM_DYN 编码）→ else 分支 → `Fcsr_RM_Illegal => None()`（fext:60）→ execute `None() => Illegal_Instruction()`（dext:274）。证据 fcsr：0xa0/0xc0/0xe0（FRM=5/6/7）各 21 例（fmadd.d 等 4 mn 共 3×84=252）。样本 case：650/270/32/647（fmadd.d）。 |
| direct-negative | 1 | case 5/6/46/48：`fmadd.d f0,f0,f0,f0,rtz` 等，**rm 编码与 FRM（fcsr=0x3→FRM=0）均合法仍 Illegal_Instruction** → 只能走译码 guard 失败：`encdec when haveDoubleFPU()`（dext:251/255/259/263）为假（currentlyEnabled(Ext_D)=misa.D & mstatus.FS≠Off & Zicsr，fdext_control.sail:19）。tsv 无 misa/FS 列，该归因是从排除法得出的推断。 |
| gen rm=rtz（非负例） | 0 | rtz Illegal 仅上述 1 例 direct-negative；其余 21 例 rtz 全 Retire。**“gen 内 64 Illegal 归因 rm 保留值”的推测不成立**：63 例 dyn-Illegal 全部由 FRM 保留值触发，指令 rm 编码本身合法。 |

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard 真（haveDoubleFPU & validDoubleRegs） | dext_insts.sail:249-263 | 译码命中 F_MADD_TYPE_D 四 clause | 是（全部 Retire/正常 Illegal 路径） | 524(rne) 等 840 Retire |
| encdec guard 假 | dext_insts.sail:251 等 | 扩展/FS 未启用 → 不译码 → Illegal | 是（推断，见归因） | 5/6/46/48 |
| select：instr_rm≠DYN → Some(instr_rm) | fext_insts.sail:63 | 静态 rm 直用 | 是 | 524(rne)/556(rtz)/572(rdn)/594(rup)/154(rmm)，fmadd.d |
| select：DYN+FRM∈0..4 → Some(FRM) | fext_insts.sail:54-56 | 动态取 FRM | 是 | 735(FRM=0)/169(FRM=4) 等 5×21 |
| select：DYN+FRM∈{5,6} → else→None | fext_insts.sail:49,55,57-61 | FRM 保留值 | 是 | 650 等（fcsr=0xa0/0xc0） |
| select：DYN+FRM=7 → else→None | fext_insts.sail:55,57-61 | FRM=DYN 编码亦视为保留 | 是 | dyn-Illegal 中 fcsr=0xe0 各 21 |
| Fcsr_RM_Fatal → reserved_behavior | fext_insts.sail:58 | 平台配置另一分支 | 否（运行配置为 Fcsr_RM_Illegal，由 verdict 全为 Illegal_Instruction 证实；platform_config.sail:95） | — |
| execute None → Illegal_Instruction | dext_insts.sail:273-274 | rm 无效异常 | 是 | 256 例 Illegal |
| op match：FMADD_D | dext_insts.sail:279 | f64MulAdd 直传 | 是 | fmadd.d 210 Retire（524 等） |
| op match：FMSUB_D（negate_D rs3） | dext_insts.sail:280；negate_D=dext:124 | rs3 取负 | 是 | fmsub.d Retire（case 46 同名组） |
| op match：FNMSUB_D（negate_D rs1） | dext_insts.sail:281 | rs1 取负 | 是 | fnmsub.d Retire |
| op match：FNMADD_D（双 negate） | dext_insts.sail:282 | rs1、rs3 取负 | 是 | fnmadd.d Retire（case 6 同名组） |
| riscv_f64MulAdd 符号化 FMA+例外打包 | softfloat_symbolic_f64.sail:72-76 | fp64_fma+ieee_fma64_exceptions，数值子分支在求解域 | 不可判（tsv 无输出 fflags/操作数位型，限据） | — |
| accrue_fflags | fdext_regs.sail:542/556 | FFLAGS 累加 | 是（所有 Retire 走到） | 840 Retire |
| F_or_X_D 读×3/写×1（F 分支） | fdext_regs.sail:384-396/414-429 | hartSupports(Ext_F)=真 → F 寄存器堆 | 是 | 全部 Retire |
| F_or_X_D X/Zfinx 分支、RV32 偶对分支 | fdext_regs.sail:389-395/419-428 | Zfinx/RV32Zdinx 语义 | 否（配置未启用 Zfinx；xlen=64） | — |
| RETIRE_SUCCESS | dext_insts.sail:286 | 正常返回 | 是 | 840 Retire |
| 指令编码 rm=5/6（encdec_rounding_mode 无该映射，译码失败→Illegal） | fext_insts.sail:31-38 | rm 域保留编码 | 否（输入域缺口，见 rm 矩阵） | — |
| validDoubleRegs 奇寄存器 reserved | dext_insts.sail:218-230 | 仅 RV32Zdinx 生效 | 否（非本配置域，RV64 恒真） | — |

### 未达分支小结
① 指令 rm 编码 5/6 无采样；② Fcsr_RM_Fatal 配置分支未行使；③ F_or_X_D 的 Zfinx/RV32 分支；④ validDoubleRegs 奇寄存器分支；⑤ softfloat 数值内部子分支覆盖不可判（数据未记录输出 fflags）。

### rm 覆盖矩阵（每 mn 计数）

| rm\结果 | Retire | Illegal |
| --- | ---: | ---: |
| rne/rtz/rdn/rup/rmm | 各 21 | 0（rtz 的 1 例 Illegal 为 direct-negative，非 rm 归因） |
| dyn,FRM=0..4（fcsr 00/20/40/60/80） | 各 21 | 0 |
| dyn,FRM=5/6/7（fcsr a0/c0/e0） | 0 | 各 21 |
| 编码 rm=5/6 | 0 | 0（**缺**） |

## 2. zF_MADD_TYPE_H（fmadd/fmsub/fnmadd/fnmsub.h，8740 case）

源码：`zfh_insts.sail:236-296`（译码 guard `haveHalfFPU()`=currentlyEnabled(Ext_Zfh)|Ext_Zhinx，zfh:155；fmt=0b10）。

### Illegal 归因（2020 例）
- gen 2016 例 = 4 mn × 504，全部 rm=dyn + FRM∈{5,6,7}（fcsr 0xa0/0xc0/0xe0 各 672），走 fext:57-61→None→zfh:264 Illegal_Instruction。
- derived-negative 4 例（case 4/6/53/63，mn=`32'h0400_104f/1043/1047/104b`）：这些是**各 opcode 的合法 fmadd.h 型编码**（fmt=2、rm=rtz、全 f0；tsv rm 列 rne 为占位，与编码位不一致，以 ins 原始码为准），编码合法仍 Illegal → 译码 guard `haveHalfFPU()`（zfh:242/246/250/254）失败（Zfh/FS 未启用，推断，tsv 无该维度）。与 D 版 direct-negative 同机制。

### 分支枚举表（与 D 同构，仅列差异与证据）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec guard 真/假 | zfh_insts.sail:240-254 | haveHalfFPU | 是（Retire 全量；4 负例走假侧，推断） | 6065 等；4/6/53/63 |
| select 四子分支（fext_insts.sail:49-63 共用） | fext_insts.sail:51-63 | 同 D | 是（结构同，8× 计数） | rne:6065(fmadd.h)/8454(fmsub.h)/810(fnmadd.h)/576(fnmsub.h)；dyn FRM0:7014/7592/1396/2803 |
| None → Illegal_Instruction | zfh_insts.sail:263-264 | rm 无效 | 是 | 2020 例 |
| op match FMADD/FMSUB/FNMSUB/FNMADD_H（negate_H=zfh:37） | zfh_insts.sail:268-273 | f16MulAdd±negate | 是 | 四 mn 各 1680 Retire |
| riscv_f16MulAdd | softfloat_symbolic_f16.sail:37 | 符号化半精度 FMA | 不可判（同 D） | — |
| F_or_X_H（仅 F 分支；无 RV32 配对问题） | fdext_regs.sail:368-374/398-404 | H 读/写 | 是（F 侧）；X/Zfinx 侧否 | — |
| RETIRE_SUCCESS | zfh_insts.sail:276 | 正常返回 | 是 | 6720 Retire |
| 编码 rm=5/6、Fcsr_RM_Fatal | fext_insts.sail:31-38/58 | 同 D | 否 | — |

### rm 覆盖矩阵：与 D 完全同构，计数 ×8：静态 5 值各 168 Retire；dyn×FRM0-4 各 168 Retire；dyn×FRM5/6/7 各 168 Illegal；编码 rm=5/6 为 0（缺）。

## 3. zF_MADD_TYPE_S（fmadd/fmsub/fnmadd/fnmsub.s，8740 case）

源码：`fext_insts.sail:358-419`（guard `haveSingleFPU()`=Ext_F|Ext_Zfinx，fext:253；fmt=0b00）。结构与 H 逐行同构。

- Illegal 2016 gen = dyn×FRM{5,6,7}；derived-negative 4 例（case 4/5/53/64，`32'h0000_1043/1047/104b/104f`）= 合法 fmadd.s 型编码（fmt=0、rm=rtz、全 f0）走 guard 假侧（推断）。
- 分支表同 H：select 四子分支（fext:51-63）、None→Illegal（fext:386）、op match 四分支+f32MulAdd（fext:390-395；softfloat_symbolic_f32.sail:84）、accrue_fflags、F_or_X_S（fdext_regs.sail:376-382/406-412，F 侧达、Zfinx 侧否）、RETIRE_SUCCESS（fext:398）全部达到；Fcsr_RM_Fatal、编码 rm=5/6 未达；数值子分支不可判。
- 证据：rtz Retire 3044(fmadd.s)/8474(fmsub.s)/942(fnmadd.s)/2416(fnmsub.s)；dyn FRM2 1369/7601/391/2631。
- rm 矩阵与 H 完全一致（×8 同构）。

## 4. 三格式对比

| 维度 | D（1096） | H（8740） | S（8740） |
| --- | --- | --- | --- |
| run | representatives-56cc-20260927-061428（official-d-1096 批） | single-…-01-f_madd_type_h（H/S FMA 续批） | single-…-02-f_madd_type_s |
| mn 集合 | 4 值相同 | 4 值相同 | 4 值相同 |
| rm 输入域 | 静态 5 值+dyn×FRM0-4 Retire；dyn×FRM5-7 Illegal；编码 5/6 缺 | 与 D 等价（计数×8） | 与 D 等价（×8） |
| Illegal:Retire 比 | 64:210（0.305） | 504:1680（0.305） | 同 H |
| 环境网格（priv×vl×sew×lmul） | 3 priv×7 格=21/rm | 3 priv×56 格=168/rm | 3 priv×56 格=168/rm |
| sew 采样 | {8,32} | {8,16,32,64} | {8,16,32,64} |
| lmul 采样 | frac2 为主 | {1,2,4,8,frac2,frac4,frac8} | 同 H |
| vl 采样 | {0,7} | {0,3,7,b,f,1f,2f,3e,7f} | 同 H |
| vill=1 例数 | 1 | 44 | 82 |
| 负例类型 | direct-negative×4（汇编文本） | derived-negative×4（原始编码） | derived-negative×4 |
| 译码 guard 差异 | haveDoubleFPU **& validDoubleRegs**（dext:251） | haveHalfFPU（zfh:242） | haveSingleFPU（fext:364） |

结论：三格式**控制流覆盖等价**——8 倍 case 数差异完全来自 (vl,sew,lmul,vill) 环境维度采样密度（21→168/rm），而这些维度不进入标量 FMA 的任何分支（execute 只依赖 rm/FRM/操作数/扩展使能）；mn、rm、FRM、verdict、priv 的输入域结构与比例三者一致。差异点：① D 版环境维度窄（sew 仅 8/32、vl 仅 0/7、vill 仅 1 例），若后续要按环境状态对拍需注意 D 版代表性弱；② 负例类别不同（direct vs derived）但机制同归译码 guard；③ f 操作数位型与输出 fflags 未记录，数值输入域等价性无法从本数据判定。

## 全组结论

1. **F_MADD_TYPE_D/H/S 三 clause 的 Sail 控制流分支在指令层全部达到**（译码 guard 真/假、select_instr_or_fcsr_rm 四子路径、None→Illegal、op match 四分支、negate 组合、accrue_fflags、F_or_X F 侧写回、RETIRE_SUCCESS），Illegal:Retire 结构三者成 8 倍等比。
2. **“gen 内 Illegal=rm 保留值”的归因需修正**：63/504 例每 mn 的 gen-Illegal 全部是 `rm=dyn 且 fcsr.FRM∈{5,6,7}`（fcsr=0xa0/0xc0/0xe0），即 **FRM 保留值**；指令自身 rm 编码均合法。每 mn 另 1 例 Illegal（D 的 rtz direct-negative、H/S 的 derived-negative）是合法编码（全 f0+静态 rm）走译码 guard 失败（扩展/FS 未启用，tsv 未记录该维度，属排除法推断）。
3. **共同未覆盖/不可判**：① 指令编码 rm=5/6（encdec_rounding_mode 无映射，译码层直接 Illegal）三格式均无采样——分支覆盖意义上的缺口很小（同为 Illegal 出口）但属输入域缺口；② Fcsr_RM_Fatal 平台分支；③ Zfinx/RV32Zdinx 侧的 F_or_X/validDoubleRegs 分支；④ softfloat 符号化 FMA 的数值内部子分支（数据未含输出 fflags，无法评估）。

## 版本注记

- case 产物绑定 IR `56cc69a44ee1acdb…3d9956ac`（outputs.ir.sha256，见 `isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/model-build.json`），生成时 sail-riscv HEAD = `f8ce849`（model_head_verified_from_git_checkout=true），与当前工作树 HEAD 相同。
- 当前工作树在 HEAD 之上有未提交修改：`FD/dext_insts.sail、fext_insts.sail、zfh_insts.sail、fdext_regs.sail、zfa_insts.sail、core/softfloat_interface.sail`（M）及 `softfloat_symbolic*.sail`（未跟踪）。经 diff hunk 核对（fext@@164/183/787/807、dext@@123/142/719/739、zfh@@36/376/396），**均不在 F_MADD 家族译码/执行区域**，本文引用行号与 IR 生成时语义一致。
- `fdext_regs.sail` 的未提交 diff 涉及 `accrue_fflags`（新增 `csr_write_callback` 观测回调，fdext_regs.sail:542/556 现两处定义），属 fflags 写回观测增强，不影响 MADD 控制流结论；后续若以本报告行号复核，请以该文件当前树为准。
