# G10 · F_UN_RM_XF_TYPE_D/H/S 分支覆盖对照（Sail 源码 vs 56cc 80416 case）

数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/cases.tsv`（列 run,clause,case,cat,mn,verdict,ret,rm,priv,vl,vill,sew,lmul,fcsr,ins）。clause 实际带 `z` 前缀（zF_UN_RM_XF_TYPE_D/H/S）。Sail 行号取当前工作树 `sail-riscv/model/extensions/FD/`（HEAD f8ce849；本 clause 区域无未提交改动，见文末版本注记）。

三 clause 各 316 case = run `single-56cc-20260927-014615-11/12/13-f_un_rm_xf_type_{d,h,s}`（batch sharedtrace-23），每 clause 4 mn × 79 = 4×(60 Retire + 19 Illegal)，direct-negative=4 + gen=312。全部 312 gen 的 arch=rv64（xlen=64）、entry-domain=decoded。

计数核对（awk mn×rm×priv×verdict×fcsr）：每 mn 静态 rm（rne/rtz/rdn/rup/rmm）各 2×3 priv=6 Retire（共 30）；rm=dyn 按 fcsr.FRM 网格 8 值（0x00/20/40/60/80/a0/c0/e0）各 2×3 priv=6（FRM0–4 共 30 Retire，FRM5/6/7 共 18 Illegal）；另 1 direct-negative Illegal。60+19=79 ✓。

## 1. zF_UN_RM_XF_TYPE_D（fcvt.d.w/wu/l/lu，316 case）

源码：`dext_insts.sail`（译码 395–427，执行 476–596）。共用 rm 解析 `select_instr_or_fcsr_rm`（fext_insts.sail:51–63）。

### Illegal 归因（76 例 = 4 mn × 19）

| 来源 | 数量/mn | 机制 |
| --- | ---: | --- |
| gen, rm=dyn, FRM∈{5,6,7} | 18 | `select_instr_or_fcsr_rm`（fext_insts.sail:51–63）：FRM=5/6 使 `valid_rounding_mode`（fext:49）为假、FRM=7 命中 `fcsr_rm != RM_DYN 编码` 排除（fext:55）→ else → `Fcsr_RM_Illegal => None()`（fext:60）→ execute `None() => Illegal_Instruction()`（dext:478/493/570/586）。证据 fcsr 0xa0/0xc0/0xe0 各 6（fcvt.d.l: 207/209/306）。 |
| direct-negative | 1 | case 5/6/37/38，`decode-rejected`，初始 mstatus=`64'h…0000`（FS=Off）vs gen mstatus=`64'h…2000`（FS=Initial）→ `currentlyEnabled(Ext_D)`（fdext_control.sail:19：misa.D & mstatus.FS≠0 & flen≥64 & Zicsr）为假 → 译码 guard `haveDoubleFPU()`（dext:214）失败。编码：#5=0xd2303053、#37=0xd2203053 为 funct5=69h+rs2∈{2,3}（D 译码表保留组合，双重非法）；#6=0xd2003053、#38=0xd2103053 为合法 FCVT_D_W/WU 编码（rm 编码=011/rmm，tsv rm 列 rup 为请求文本，与编码不一致，以原始码为准），只能归因 FS=Off。 |

int→float 无越界非法路径确认：execute 体内无任何操作数相关异常出口（W/WU 取 `X(rs1)[31..0]`，L/LU 取 `X(rs1)`，转换恒成功），唯一 Illegal 出口即 select None。故 gen 内 18/19 Illegal 全部归因 **FRM 保留值**（指令 rm 编码本身合法：dyn=111 或静态 0–4），非指令 rm 保留值。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec FCVT_D_W 命中（69h,rs2=0；guard haveDoubleFPU & validDoubleRegs([rd])） | dext_insts.sail:395–397 | 32 位有符号→D | 是 | fcvt.d.w 60 Retire（rne:74） |
| encdec FCVT_D_WU 命中（69h,rs2=1） | dext_insts.sail:399–401 | 32 位无符号→D | 是 | fcvt.d.wu（rne:40） |
| encdec FCVT_D_L 命中（69h,rs2=2；+xlen≥64，无 validDoubleRegs） | dext_insts.sail:421–423 | 64 位有符号→D | 是 | fcvt.d.l（rne:270） |
| encdec FCVT_D_LU 命中（69h,rs2=3） | dext_insts.sail:425–427 | 64 位无符号→D | 是 | fcvt.d.lu（rne:73） |
| guard 假侧（FS=Off/扩展未启用→不译码） | dext:397 等 + fdext_control.sail:19 | Illegal 译码 | 是 | 负例 6/38（合法编码，唯一解释）；5/37 复合 |
| rs2 保留组合（69h+rs2∈{2,3}）无 encdec 映射 | dext:395–427（表未命中） | 译码表 miss | 部分（仅与 FS=Off 复合，无独立采样） | 5/37 |
| select：rm≠DYN→Some(instr_rm) | fext_insts.sail:63 | 静态 rm 直用 | 是 | 5×6 静态 Retire/mn |
| select：DYN+FRM∈0..4→Some(FRM) | fext_insts.sail:52–56 | 动态取 FRM | 是 | dyn fcsr 00/20/40/60/80 各 6（fcvt.d.w: 1/112/33/130/29） |
| select：DYN+FRM∈{5,6}→None | fext_insts.sail:49,55,57–60 | FRM 保留值 | 是 | 207/209（0xa0/0xc0） |
| select：DYN+FRM=7→None | fext_insts.sail:55,57–60 | FRM=DYN 编码亦保留 | 是 | 306（0xe0） |
| Fcsr_RM_Fatal→reserved_behavior | fext_insts.sail:58–59 | 平台配置分支 | 否（运行配置 Fcsr_RM_Illegal，core/platform_config.sail:71,95；verdict 全为 Illegal_Instruction 佐证） | — |
| execute None→Illegal_Instruction | dext_insts.sail:478/493/570/586 | rm 无效异常 | 是 | 72 gen Illegal |
| op match 4 分支（i32/ui32/i64/ui64ToF64） | dext_insts.sail:476–596 | 4 个 execute clause | 是 | 4 mn 各 60 Retire |
| softfloat 数值内部子分支 | softfloat 接口 | i32/i64→f64 恒不精确舍入等 | 不可判（tsv 未记录输出 fflags） | — |
| accrue_fflags | fdext_regs.sail:542/556 | FFLAGS 累加 | 是（全部 Retire） | 240 Retire |
| F_or_X_D 写回 F 分支 | fdext_regs.sail:414–417 | F 寄存器堆 | 是 | 全部 Retire |
| F_or_X_D X/Zfinx 分支、RV32 偶对分支 | fdext_regs.sail:418–429 | Zfinx/RV32Zdinx | 否（配置无 Zfinx，xlen=64） | — |
| RETIRE_SUCCESS | dext_insts.sail:484 等 | 正常返回 | 是 | 240 Retire |
| validDoubleRegs 奇寄存器拒绝 | dext_insts.sail:218–230 | 仅 RV32Zdinx 生效 | 否（RV64 恒真） | — |
| xlen≥64 假侧（RV32 拒 L/LU） | dext_insts.sail:423/427 | RV32 下不译码 | 否（312 gen 全 rv64） | — |
| 指令编码 rm=5/6（encdec_rounding_mode 无映射→译码失败） | fext_insts.sail:31–38 | rm 域保留编码 | 否（输入域缺口） | — |

### 未达分支小结
① 指令编码 rm=5/6 零采样；② RV32（xlen<64）L/LU 译码拒绝；③ Fcsr_RM_Fatal；④ Zfinx/RV32Zdinx 侧（F_or_X_D、validDoubleRegs）；⑤ rs2 保留组合无独立采样（负例与 FS=Off 复合）；⑥ softfloat 内部子分支不可判。

### rm 覆盖矩阵（每 mn，4 mn 同构）

| 指令 rm \ FRM | Retire | Illegal |
| --- | ---: | ---: |
| rne/rtz/rdn/rup/rmm（静态） | 各 6 | 0 |
| dyn, FRM=0/1/2/3/4（fcsr 00/20/40/60/80） | 各 6 | 0 |
| dyn, FRM=5/6/7（fcsr a0/c0/e0） | 0 | 各 6 |
| 编码 rm=5/6 | 0 | 0（**缺**） |
| （负例：编码 rm=011 合法，FS=Off） | — | 1 |

## 2. zF_UN_RM_XF_TYPE_H（fcvt.h.w/wu/l/lu，316 case）

源码：`zfh_insts.sail`（译码 482–525，执行 574–728）；guard `haveHalfFPU()`（zfh:155，=currentlyEnabled(Ext_Zfh)|Ext_Zhinx）。

### Illegal 归因（76 例）
与 D 同构：每 mn 18 = dyn×FRM∈{5,6,7}（fcvt.h.l: 203/205/305）；1 direct-negative（case 5/6/37/38，mstatus FS=Off，guard 失败）。编码：#5=0xd4303053、#37=0xd4203053 为 funct5=6Ah+rs2∈{2,3}，RV64 下属**合法的 FCVT.S.LU/FCVT.S.L**（S clause 指令，非 H 译码表保留）；#6=0xd4003053、#38=0xd4103053 为合法 FCVT_H_W/WU。即 H 的 4 个负例中全部为合法编码，Illegal 只能归因 FS=Off→haveHalfFPU 假（排除法，tsv 无 misa/FS 列）。

### 分支枚举表（与 D 同构，列差异）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec FCVT_H_W 命中（6Ah,rs2=0；haveHalfFPU） | zfh_insts.sail:482–484 | i32→H | 是 | fcvt.h.w（rne:74） |
| encdec FCVT_H_WU 命中（6Ah,rs2=1） | zfh_insts.sail:486–488 | ui32→H | 是 | fcvt.h.wu（rne:40） |
| encdec FCVT_H_L 命中（6Ah,rs2=2；+xlen≥64） | zfh_insts.sail:519–521 | i64→H | 是 | fcvt.h.l（rne:269） |
| encdec FCVT_H_LU 命中（6Ah,rs2=3） | zfh_insts.sail:523–525 | ui64→H | 是 | fcvt.h.lu（rne:72） |
| guard 假侧（FS=Off） | zfh:484 等 + fdext_control.sail | Illegal 译码 | 是（推断，排除法） | 5/6/37/38 |
| select 四子路径 + None→Illegal | fext_insts.sail:51–63；zfh:576/591/698/714 | 同 D | 是 | 静态各 6；dyn FRM0–4 各 6（fcvt.h.w: 1/104/33/122/29）；FRM5/6/7 各 6 Illegal（255/117/243） |
| op match 4 分支（i32/ui32/i64/ui64ToF16） | zfh:574–728 | 4 execute clause | 是 | 4 mn 各 60 Retire |
| Fcsr_RM_Fatal | fext:58–59 | 平台分支 | 否 | — |
| F_or_X_H 写回 F 分支 / X(Zfinx) 分支 | fdext_regs.sail:398–404 | H 写回 | 是 / 否 | 全部 Retire / — |
| RETIRE_SUCCESS | zfh:583 等 | 正常返回 | 是 | 240 Retire |
| 编码 rm=5/6；xlen≥64 假侧 | fext:31–38；zfh:521/525 | 同 D | 否 | — |

注：H 译码表对 6Ah+rs2∈{2,3} 并非"保留"，而是被 S clause 的 FCVT_S_L/LU 占用（fext:525–531）——本数据集内该跨界组合仅出现在 FS=Off 负例中。

### 未达分支小结
同 D 之 ①②③④⑥；另：H 无 validDoubleRegs 维度（无 RV32 偶对问题），rs2 保留组合维度不适用。

### rm 覆盖矩阵
与 D 完全同构（每 mn：静态 5 值各 6 R；dyn×FRM0–4 各 6 R；dyn×FRM5/6/7 各 6 I；编码 rm=5/6 缺；负例 1 I）。

## 3. zF_UN_RM_XF_TYPE_S（fcvt.s.w/wu/l/lu，316 case）

源码：`fext_insts.sail`（译码 507–531，执行 580–672）；guard `haveSingleFPU()`（fext:253，=currentlyEnabled(Ext_F)|Ext_Zfinx）。

### Illegal 归因（76 例）
每 mn 18 = dyn×FRM∈{5,6,7}（fcvt.s.w: 248/107/243）；1 direct-negative（case 5/6/37/42，FS=Off）。编码：#6=0xd0303053（68h,rs2=3）、#42=0xd0203053（68h,rs2=2）为 **68h+rs2∈{2,3} 真保留组合**（68h 仅映射 rs2∈{0,1}）；#5=0xd0003053、#37=0xd0103053 为合法 FCVT_S_W/WU 编码，只能归因 FS=Off。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec FCVT_S_W 命中（68h,rs2=0；haveSingleFPU） | fext_insts.sail:507–509 | i32→S | 是 | fcvt.s.w（rne:72） |
| encdec FCVT_S_WU 命中（68h,rs2=1） | fext_insts.sail:511–513 | ui32→S | 是 | fcvt.s.wu（rne:38） |
| encdec FCVT_S_L 命中（6Ah,rs2=2；+xlen≥64） | fext_insts.sail:525–527 | i64→S | 是 | fcvt.s.l（rne:279） |
| encdec FCVT_S_LU 命中（6Ah,rs2=3） | fext_insts.sail:529–531 | ui64→S | 是 | fcvt.s.lu（rne:79） |
| guard 假侧（FS=Off） | fext:509 等 + fdext_control.sail:18 | Illegal 译码 | 是 | 5/37（合法编码唯一解释）；6/42 复合 |
| rs2 保留组合（68h+rs2∈{2,3}）无 encdec 映射 | fext:507–514 表未命中 | 译码表 miss | 部分（仅与 FS=Off 复合） | 6/42 |
| select 四子路径 | fext_insts.sail:49–63 | 同 D | 是 | 静态各 6；dyn FRM0–4 各 6（fcvt.s.w: 29/106/33/114/1）；FRM5/6/7 各 6 I |
| execute None→Illegal_Instruction | fext_insts.sail:582/597/644/660 | rm 无效异常 | 是 | 72 gen Illegal |
| op match 4 分支（i32/ui32/i64/ui64ToF32） | fext:580–672 | 4 execute clause | 是 | 4 mn 各 60 Retire |
| Fcsr_RM_Fatal | fext:58–59 | 平台分支 | 否 | — |
| F_or_X_S 写回 F 分支 / X(Zfinx) 分支 | fdext_regs.sail:406–412 | S 写回 | 是 / 否 | 全部 Retire / — |
| RETIRE_SUCCESS | fext:589 等 | 正常返回 | 是 | 240 Retire |
| 编码 rm=5/6；xlen≥64 假侧 | fext:31–38；fext:527/531 | 同 D | 否 | — |

### 未达分支小结
同 D 之 ①②③④⑥（S 无 validDoubleRegs 维度）。

### rm 覆盖矩阵
与 D 完全同构。

## 4. 三格式横向对照

| 维度 | D | H | S |
| --- | --- | --- | --- |
| case/run | 316，single-56cc-…-11 | 316，…-12 | 316，…-13 |
| mn 集合 | 4 值对应 | 4 值对应 | 4 值对应 |
| 每 mn R:I | 60:19（30 静态+30 dyn-R；18 dyn-FRM 保留+1 负例） | 同 | 同 |
| fcsr 网格 | 8 值×24 | 同 | 同 |
| 译码 guard | haveDoubleFPU **& validDoubleRegs([rd])**（仅 W/WU） | haveHalfFPU | haveSingleFPU |
| L/LU 附加 guard | xlen≥64 | xlen≥64 | xlen≥64 |
| 负例编码性质 | 2 保留 rs2 + 2 合法 | 0 保留（2 属 S clause 编码）+4 合法 | 2 保留 rs2 + 2 合法 |
| 环境 sew 采样 | {8,16,32,64}=107/14/180/15 | 105/22/177/12 | 108/21/180/7 |
| 环境 lmul 采样 | {1,2,4,8,frac2,frac4} | {1,2,4,8,frac2} | 同 H |
| vill | 全 0 | 全 0 | 全 0 |

环境维度（vl/sew/lmul/vill）不进入标量 FCVT 任何分支（execute 仅依赖 rm/FRM/扩展使能/操作数），三格式覆盖等价。

## 全组结论

1. **三 clause 的指令层控制流分支全部达到**：encdec 四命中、guard 真侧、select_instr_or_fcsr_rm 四子路径（静态 Some / DYN+FRM0–4 Some / DYN+FRM5、6 None / DYN+FRM7 None）、None→Illegal、op match 四分支、accrue_fflags、F_or_X F 侧写回、RETIRE_SUCCESS；guard 假侧由 4 条 direct-negative 达到（FS=Off，排除法归因）。Illegal:Retire=19:60 三者严格同构。
2. **"19I 每指令归因 rm 保留值"的精确口径**：18/19 是 **fcsr.FRM 保留值**（5/6/7，fcsr=0xa0/0xc0/0xe0）+ 指令 rm=dyn 的组合（fext:49/55→60→None）；指令自身 rm 编码在全部 gen 中均合法；第 19/19 是 direct-negative（FS=Off 译码拒绝，与 rm 无关）。int→float 转换在 Sail 中确无越界非法路径（execute 无操作数相关异常出口），不存在被遗漏的数值 Illegal 分支。
3. **共同未覆盖/不可判**：① 指令编码 rm=5/6（encdec_rounding_mode 无映射，译码层 Illegal 出口）三格式零采样——输入域缺口；② RV32（xlen<64）下 L/LU 译码拒绝分支（312 gen 全 rv64）；③ Fcsr_RM_Fatal→reserved_behavior；④ Zfinx/Zhinx/Zdinx 侧（F_or_X X 分支、validDoubleRegs 奇寄存器）；⑤ rs2 保留组合（D:69h、S:68h 的 rs2∈{2,3}）仅以 FS=Off 复合形式出现，无独立正交采样；⑥ softfloat 数值内部子分支不可判（tsv 未记录输出 fflags）。
4. 数据口径注意：direct-negative 的 tsv rm 列（rup）取自请求文本，实际编码 rm=011(rmm)，分析以原始编码为准；tsv 未记录 misa/mstatus，FS=Off 归因经负例与 gen 的 mstatus 差异（input-complete JSON）证实。

## 版本注记

- case 产物绑定 IR `56cc69a44ee1acdb…3d9956ac`（target-map.json `ir-sha256`，batch sharedtrace-23，run `single-56cc-20260927-014615-11/12/13`），生成时 sail-riscv HEAD=`f8ce849`，与当前工作树 HEAD 相同。
- 当前工作树在 HEAD 之上有未提交修改：`FD/{dext_insts,fext_insts,zfh_insts,zfa_insts,fdext_regs}.sail`（M）及 `fp_minmax.sail`、`softfloat_symbolic*.sail`（未跟踪）。经 diff hunk 核对（fext@@164/183/787/807、dext@@123/142/719/739、zfh@@36/376/396），**均不在 F_UN_RM_XF_TYPE 家族译码/执行区域**（fext 507–531/580–672、dext 395–427/476–596、zfh 482–525/574–728），本文行号与 IR 56cc69a4 语义一致。
- `fdext_regs.sail` 的未提交 diff 涉及 `accrue_fflags`（新增 `csr_write_callback` 观测回调，fdext_regs.sail:542/556 现两处定义），属 fflags 写回观测增强，不影响本 clause 控制流结论；以本报告行号复核时请以该文件当前树为准。
