# G7 分支覆盖核对：比较族 / fclass·fmv.x 族 / fmv.*.x 族（10 clause）

- 数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/{distribution.md,cases.tsv}`（57 目标、IR 56cc69a4、80416 case）。
- 用例明细：`isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-incremental-56cc69-20260927/results/<CLAUSE>/input{,-complete}/*.json`（含 `isa-state-complete` 完整前置状态）。
- 源码核对基准：`sail-riscv/model/`（当前工作树；与 IR 56cc69a4 快照逐字节一致，唯一例外见[版本注记](#版本注记)）。
- 结论口径：`decode`（encdec pattern + when guard）、`execute`、以及 execute 直调 helper 中的**控制流分支**（if/else、ite）；pure 外原语与 strict_bool 布尔项不构成控制流分叉，仅在数据维度记录。
- 案例数（去重后）：比较族 S/H 各 633（gen 630=每 mnemonic 210 + 负例 3）、D 255（gen 252=每 84 + 负例 3）；fclass 族 fclass.s/h 各 66 + fmv.x 6（+负例 2）、fclass.d 60 + fmv.x.d 6（+负例 2）；fmv.d.x/fmv.h.x/fmv.w.x 各 6 gen + 1 负例。

**关键前置事实（全组共用）**

1. **负例全部是 guard 失配，不是编码失配**。本组 18 个 Illegal 负例的编码本身全部是所测 clause 的合法编码（如 F_BIN_TYPE_X_S 的 `32'ha000_0053`=fle.s、`32'ha000_1053`=flt.s、`32'ha000_2053`=feq.s），其前置 `mstatus=64'h0000_000a_0000_0000` 使 `mstatus[FS]=00`，`currentlyEnabled(Ext_F)`（fdext_control.sail:18：`hartSupports & misa[F] & mstatus[FS]!=0 & currentlyEnabled(Ext_Zicsr)`）为假 → when guard 失败 → Illegal。gen 用例 `mstatus=...2000/...4000`（FS=01/10）guard 为真。
2. **rm 对本组全部指令只是译码 pattern 的固定位**，execute 一律不读 rm/frm，不存在执行期 rm 非法分支。rm 保留值（011/110/111）编码不匹配任何子句 → 译码期结构性 Illegal；本组无"FP 开启 + rm 保留值"的专属用例（该 fall-through 路径在本组 replay 内未单独出现）。
3. **S/H 读寄存器有 nan_unbox 真分支，D 读直通**。`rF_S/rF_H`（fdext_regs.sail:339/327）调 `nan_unbox`（fdext_regs.sail:48-51），IR 版为 if-else：高位非全 1 → 替换 canonical NaN；`rF_D`（:351）因 `'n=='m` 直通无分支。fmv.x.w/x.h 例外：直接 `F(rs1)[31..0]/[15..0]`，无 unbox。
4. **NV flag 在 helper 内且不分叉**：`ieee_eq/lt{16,32,64}_exceptions`（ieee_fp_exceptions.sail:175/79/267 等）全用 `strict_and/or_bool` 布尔项；比较主体 `fp32_eq/lt/lteq` 等为 pure 外原语（sail lib float.sail:201-221），无 Sail 控制流。NV 取值只通过 `accrue_fflags` 的 `ite(changed,...)`（fdext_regs.sail:542-555，SYMBOLIC 版）间接产生分支。
5. fclass 的 10 类结果位图是 rd 的**数据值**：控制流分支在 `float_classify`（sail lib classify.sail:27-38，6 级 if-else 链）与 `float_class_onehot_bits`（core/float_classify.sail:10-21，10 项映射）；verdict 层面（Retire_Success）不可区分类别，须按输入类核对（已核对，见各节）。

---

## 1. F_BIN_TYPE_X_S（feq.s/flt.s/fle.s，633）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FEQ_S rm=010 | fext_insts.sail:739-741（guard haveSingleFPU:253） | bit pattern+guard | 是 | gen feq.s×210（如 #31 同族 flt；feq 各 id 均在 gen 集） |
| 译码 FLT_S rm=001 | fext_insts.sail:743-745 | 同上 | 是 | gen flt.s×210 |
| 译码 FLE_S rm=000 | fext_insts.sail:747-749 | 同上 | 是 | gen fle.s×210 |
| guard=假（FS=Off）→Illegal | fdext_control.sail:18（mstatus[FS]!=0） | guard 失配 | 是 | 负例 #4(0xa0000053)/#3(0xa0002053)/#28(0xa0001053) |
| guard=真 | 同上 | | 是 | 全部 630 gen |
| encode 失配 fall-through（rm 保留值等） | 译码汇合 | 无子句匹配 | **否（本组无专属用例）** | — |
| execute FEQ/FLT/FLE_S | fext_insts.sail:806-816/818-828/830-840 | 读 2×F_or_X_S→riscv_f32Eq/Lt/Le→accrue→X(rd) | 是 | 同上 |
| rF_or_X_S 的 hartSupports(Ext_F) 分支 | fdext_regs.sail:376-383 | FPU vs Zfinx 读路径 | 真（配置常量）/假=配置死分支 | — |
| nan_unbox 真（高位全1）/假 | fdext_regs.sail:48-51（IR 版 if-else） | 假→canonical NaN | 两支均是 | 真：多数；假：#21,#23,#24,#25 等 504 操作数 |
| accrue_fflags ite(changed) 真/假 | fdext_regs.sail:542-555 | NV 置位→mstatus 置 Dirty | 两支均是 | 真：fle.s/flt.s（sNaN #19/#121/#379 及 unbox-fail→canonqNaN）；假：非 NaN 输入 |
| X(rd) 写 rd=x0/≠x0 | — | 零寄存器丢弃 | 两支均是 | 各 315 例（#1-…/#27-…） |

未达分支：仅"FP 开启 + rm 保留值(011/110/111)"的结构性 fall-through（rm=100/101 属 FLEQ/FLTQ 其他 clause 空间）。

维度小结：操作数有效类覆盖 snan(3，仅出现在 fle.s/flt.s)/pnorm/nnorm/pzero/nzero/psub；无原始 qNaN（unbox-fail 产生的 canonical qNaN 补齐 qNaN 语义）；无 ±inf 输入。**feq.s 用例内 NV 恒 0**（eq 仅 sNaN 置 NV，而 3 个 sNaN 都落在 fle/flt），NV=1 路径仅靠同 clause 的 fle.s/flt.s 达到（clause 级覆盖完整，mnemonic 级 feq.s 缺 NV=1 数据路径）。

## 2. F_BIN_X_TYPE_D（feq.d/flt.d/fle.d，255）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FEQ_D/FLT_D/FLE_D | dext_insts.sail:670-672/674-676/678-680（guard haveDoubleFPU:214 & validDoubleRegs:219） | bit+guard | 是 | gen 各 84 |
| guard=假 → Illegal | fdext_control.sail:19 + dext:672 | FS=Off/misa.D=0 | 是 | 负例 #3/#4/#24（0xa200_2053/0053/1053，编码均为合法 fle.d/flt.d/feq.d） |
| guard=真 | 同上 | | 是 | 252 gen |
| encode 失配 fall-through | — | rm 保留值等 | 否 | — |
| validDoubleRegs 的 Zdinx-RV32 奇寄存器分支 | dext_insts.sail:219-233 | RV32Zdinx 专用 | 配置性不可达（RV64/无 Zdinx 恒走 true 出口） | — |
| execute FEQ/FLT/FLE_D | dext_insts.sail:738-748/750-760/762-772 | riscv_f64Eq/Lt/Le | 是 | 同上 |
| nan_unbox | — | D 读直通无此分支 | N/A | — |
| accrue_fflags ite(changed) 假 | fdext_regs.sail:542-555 | NV=0 | 是 | 全部用例 |
| accrue_fflags ite(changed) 真（NV=1） | 同上 | NaN 比较置 NV | **否** | — |
| X(rd) rd=x0/≠x0 | — | | 两支均是 | 各 126 |

未达分支：**整个 clause 无任何 NaN 输入**（操作数类仅 pnorm/nnorm/pzero/nzero/psub/nsub；D 读无 unbox，无 canonical-NaN 旁路）→ NV=1→`ite(changed)` 真分支在本 clause 未达（该 helper 为全局共享，真分支由其他 clause 达到，但 F_BIN_X_TYPE_D 自身 replay 未达）。

维度小结：210+42 个操作数无非数类；FLT.D/FLE.D 的 NV 语义路径（IEEE lt64 signaling）从未以 NV=1 取值执行。rm 结构性失配同前未覆盖。

## 3. F_BIN_X_TYPE_H（feq.h/flt.h/fle.h，633）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FEQ_H/FLT_H/FLE_H | zfh_insts.sail:328-330/332-334/336-338（guard haveHalfFPU:155=Zfh|Zhinx） | bit+guard | 是 | gen 各 210 |
| guard=假 → Illegal | fext_insts.sail:28（Zfh→Ext_F→fdext_control:18） | FS=Off | 是 | 负例 #4(fle.h)/#3(0xa4002053)/#28(0xa4001053)，编码均合法 |
| guard=真 | 同上 | | 是 | 630 gen |
| encode 失配 fall-through | — | rm 保留值 | 否 | — |
| execute FEQ/FLT/FLE_H | zfh_insts.sail:395-405/407-417/419-429 | riscv_f16Eq/Lt/Le（softfloat_symbolic_f16.sail:164/140/152） | 是 | 同上 |
| nan_unbox 真/假（flen64→16） | fdext_regs.sail:48-51,327-331 | 高位非全1→canonNaN | 两支均是 | 假：#21,#23,#24,#25 等 504 操作数 |
| accrue_fflags ite(changed) 真/假 | fdext_regs.sail:542-555 | | 两支均是 | 真：flt.h/fle.h（unbox-fail→canonqNaN 置 NV）；假：非 NaN |
| X(rd) rd=x0/≠x0 | — | | 两支均是 | 各 315 |

未达分支：仅结构性 fall-through。

维度小结：无原始 sNaN/qNaN 操作数（unbox-fail 替换出的 canonical qNaN 提供 qNaN 语义）；**feq.h 的 NV=1 数据路径未达**（eq16 仅 sNaN 置 NV，而 qNaN 不置）；无 ±inf 输入。flt.h/fle.h NV=1 达到。

## 4. F_UN_TYPE_X_S（fclass.s 66 + fmv.x.w 6，74）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FCLASS_S rm=001 | fext_insts.sail:878-880（guard haveSingleFPU） | | 是 | gen fclass.s×66 |
| 译码 FMV_X_W rm=000 | fext_insts.sail:882-884（guard currentlyEnabled(Ext_F)，严于 FCLASS 的 haveSingleFPU） | | 是 | gen fmv.x.w×6（#1,5,6,8,15,16） |
| guard=假 → Illegal（两 clause 各 1 负例） | fdext_control.sail:18 | FS=Off | 是 | 负例 #2(fmv.x.w)/#3(fclass.s)，编码合法 |
| encode 失配 fall-through（如 funct7=1110000+rm=011） | — | | 否（无专属用例） | — |
| execute FCLASS_S | fext_insts.sail:892-896 | F_or_X_S→float_classify→onehot→X(rd) | 是 | 66 gen |
| float_classify 10 个类分支 | sail lib classify.sail:27-38（6 级 if-else + sign 二分；:36 unreachable assert 不可达） | 每类一分支 | **10/10 全达** | 每类 6 例：ninf #30 / nnorm #73 / nsub #66 / nzero #38 / pzero #18 / psub #54 / pnorm #58 / pinf #32 / qnan #43 / snan #13 |
| float_class_onehot_bits 10 项映射 | core/float_classify.sail:10-21 | 枚举→位图 | 10/10 全达 | 同上（rd 数据值随类变化） |
| nan_unbox 真/假 | fdext_regs.sail:48-51 | | 两支均是 | 假：#10,17,20,27,35,42（→canonqNaN，走 classify 的 qnan 分支） |
| execute FMV_X_W | fext_insts.sail:898-901 | `X(rd)=sign_extend(F(rs1)[31..0])`，**无 unbox、无数据分支** | 是 | 6 gen |
| X(rd) rd=x0/≠x0 | — | | 两支均是 | fclass x0/x31 均有；fmv.x.w #1,5,6(x0) 与 #8,15,16(x31) |

未达分支：仅结构性 fall-through。execute 层无缺口。

维度小结：66 = 10 类×6 + 6 unbox-fail（数据维度上 10 类位图全取值；verdict 层不可区分，已在输入层核实）。fclass 与 fmv.x.w 共用 clause，两子句译码分支各自达到；fmv.x.w 的 6 例覆盖 rs1=x0/x31 与 rd 两态，对无分支 execute 已充分。差异原因：fclass 的 classify 链有 10 分支需按类喂入，identity 去重后保留 66；fmv 无分支只需 2 编码×3 状态副本=6。

## 5. F_UN_X_TYPE_D（fclass.d 60 + fmv.x.d 6，68）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FCLASS_D rm=001 | dext_insts.sail:810-812（guard haveDoubleFPU & validDoubleRegs([rs1])） | | 是 | gen fclass.d×60 |
| 译码 FMV_X_D rm=000（RV64 only） | dext_insts.sail:816-818（guard Ext_D & xlen>=64） | | 是 | gen fmv.x.d×6（#1,5,6,9,14,15） |
| guard=假 → Illegal | fdext_control.sail:19 | FS=Off | 是 | 负例 #2(fmv.x.d)/#3(0xe2001053=fclass.d 合法编码) |
| validDoubleRegs Zdinx 分支 | dext_insts.sail:219-233 | RV32Zdinx | 配置性不可达 | — |
| encode 失配 fall-through | — | | 否 | — |
| execute FCLASS_D | dext_insts.sail:826-830 | F_or_X_D→classify→X(rd)；D 读直通无 unbox | 是 | 60 gen |
| float_classify 10 分支 + onehot 10 项 | classify.sail:27-38；core/float_classify.sail:10-21 | | 10/10 全达 | 每类 6：ninf #61 / nnorm #46 / nsub #66 / nzero #60 / pzero #16 / psub #32 / pnorm #45 / pinf #39 / qnan #43 / snan #8 |
| execute FMV_X_D | dext_insts.sail:832-836 | assert(xlen>=64&flen>=64)（配置恒真）+sign_extend | 是 | 6 gen |
| X(rd) rd=x0/≠x0 | — | | 两支均是 | fclass x0/x31；fmv.x.d 两态 |

未达分支：仅结构性 fall-through。

维度小结：60=10 类×6（无 unbox 维度）。fclass 66(S/H) vs 60(D) 差 = S/H 多 6 个 unbox-fail 例。fmv.x.d 6 例充分（无数据分支）。

## 6. F_UN_X_TYPE_H（fclass.h 66 + fmv.x.h 6，74）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FCLASS_H rm=001 | zfh_insts.sail:778-780（guard haveHalfFPU） | | 是 | gen fclass.h×66 |
| 译码 FMV_X_H rm=000 | zfh_insts.sail:782-784（guard Zfhmin|Zfbfmin） | | 是 | gen fmv.x.h×6（#1,3,6,8,13,16） |
| guard=假 → Illegal | fext_insts.sail:28-29→fdext_control:18 | FS=Off | 是 | 负例 #2(fmv.x.h)/#5(fclass.h)，编码合法 |
| encode 失配 fall-through | — | | 否 | — |
| execute FCLASS_H | zfh_insts.sail:792-796 | F_or_X_H→classify→X(rd) | 是 | 66 gen |
| float_classify 10 分支 + onehot | classify.sail:27-38；core/float_classify.sail:10-21 | | 10/10 全达 | ninf #31 / nnorm #73 / nsub #64 / nzero #39 / pzero #19 / psub #54 / pnorm #59 / pinf #32 / qnan #43 / snan #15 |
| nan_unbox 真/假（64→16） | fdext_regs.sail:48-51,327 | | 两支均是 | 假：#10,17,20,27,35,42 |
| execute FMV_X_H | zfh_insts.sail:798-803 | `sign_extend(F(rs1)[15..0])`，无 unbox 无分支 | 是 | 6 gen |
| X(rd) rd=x0/≠x0 | — | | 两支均是 | 两态均有 |

未达分支：仅结构性 fall-through。

维度小结：与 F_UN_TYPE_X_S 完全同构（66=10×6+6 unbox-fail）。

## 7. F_UN_F_TYPE_D（fmv.d.x，7）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FMV_D_X | dext_insts.sail:820-822（guard Ext_D & xlen>=64，rm=000 固定） | | 是 | gen×6（#2,3,4,5,6,7；rs1=x0:#4,6,7 / x31:#2,3,5） |
| guard=假 → Illegal | fdext_control.sail:19 | FS=Off | 是 | 负例 #1（0xf2000053=合法 fmv.d.x 编码） |
| encode 失配 fall-through | — | | 否（仅 1 个 guard 负例） | — |
| execute FMV_D_X | dext_insts.sail:838-842 | assert 恒真；`F(rd)=nan_box(X(rs1)[63..0])`，nan_box 在 'n=='m 时为直通，**无任何数据分支** | 是 | 任 1 例即全覆盖，实际 6 例 |

未达分支：仅结构性 fall-through（本 clause 无 bits 失配负例）。

维度小结：case 少完全合理——execute 控制流为直线（读 X→截位→nan_box→写 F），rm 无关、无异常、无 fflags 写（不调 accrue_fflags）；6 例=rs1 两编码×3 状态副本，已含全部可变维度（rs1 值是数据非分支）。guard 真假两支均有。

## 8. F_UN_F_TYPE_H（fmv.h.x，7）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FMV_H_X | zfh_insts.sail:786-788（guard Zfhmin|Zfbfmin，rm=000） | | 是 | gen×6（#2,3,4,5,6,7） |
| guard=假 → Illegal | fext_insts.sail:29→fdext_control:18 | FS=Off | 是 | 负例 #1（0xf4000053 合法编码） |
| encode 失配 fall-through | — | | 否 | — |
| execute FMV_H_X | zfh_insts.sail:805-810 | `F(rd)=nan_box(X(rs1)[15..0])`，nan_box 拼接无分支 | 是 | 6 gen |

未达分支：仅结构性 fall-through。

维度小结：同 fmv.d.x，直线 execute；**写侧 nan_box 无分支**（读侧 unbox 不涉及——fmv.h.x 读的是 X 寄存器），6 例充分。

## 9. F_UN_TYPE_F_S（fmv.w.x，7）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| 译码 FMV_W_X | fext_insts.sail:886-888（guard currentlyEnabled(Ext_F)，rm=000） | | 是 | gen×6（#2,3,4,5,6,7） |
| guard=假 → Illegal | fdext_control.sail:18 | FS=Off | 是 | 负例 #1（0xf0000053 合法编码） |
| encode 失配 fall-through | — | | 否 | — |
| execute FMV_W_X | fext_insts.sail:903-906 | `F(rd)=nan_box(X(rs1)[31..0])`，无分支 | 是 | 6 gen |

未达分支：仅结构性 fall-through。

维度小结：同上。注意 nan_box(32→64) 写入是纯拼接：与 fmv.x.w 读侧不查 unbox 相互对称，均无分支；rm 无关、无异常，6 gen+1 负例已覆盖 clause 全部控制流。

---

## 全组结论

1. **译码层**：10 个 clause 的全部子句分支（比较族 3 rm 变体×3 宽度、fclass/fmv.x 的 rm=001/000 双子句、fmv.*.x 单子句）均有 gen 达到；guard 假分支（mstatus[FS]=Off→currentlyEnabled(Ext_F/D/Zfh)=假→Illegal）均有负例达到。**共性缺口**：本组 18 个负例全部是"合法编码+FS=Off"的 guard 失配，没有任何"FP 开启 + rm 保留值/子句外编码"的结构性 fall-through 用例；rm=100/101 由 FLEQ/FLTQ（Zfa，其他组）覆盖，011/110/111 则全 57 目标内也未见本组专属用例。validDoubleRegs 的 RV32Zdinx 奇寄存器分支为配置性死分支（RV64、无 Zdinx）。
2. **execute 层**：所有指令 execute 体内无 rm/frm 读取、无执行期 Illegal 分支。真数据分支仅三类：`nan_unbox`（S/H 读，两支均达；D 读与 fmv.x.w/h 读不经过它）、`float_classify` 10 类链（fclass 三宽度 10/10 全达，unbox-fail 例另走 qnan 分支）、`accrue_fflags` 的 `ite(changed)`（比较族）。X(rd)/F(rd) 写的零寄存器维度两态均达。fmv.d.x/h.x/w.x 三 clause execute 为纯直线，各 6 gen+1 负例即完整覆盖，case 少是合理的。
3. **主要覆盖缺口（数据维度）**：**F_BIN_X_TYPE_D 全 clause 无 NaN 输入**（且 D 读无 unbox 旁路）→ FLT.D/FLE.D/FEQ.D 的 NV=1 从未取值，accrue_fflags `ite(changed)` 真分支在本 clause replay 未达。feq.s/feq.h 的 NV=1（仅 sNaN 触发）亦无用例（S 的 3 个 sNaN 均落在 fle.s/flt.s；H 无 sNaN）。NV 逻辑本身在 ieee_*_exceptions 内为 strict_bool 布尔项，不构成控制流分叉，故这是路径取值/数据缺口而非未达分支（D 的 changed-ite 真分支除外）。比较族亦无 ±inf 操作数。
4. **fclass 66 vs fmv 6 的差异**是分支结构使然：fclass 需按 10 类输入分别走 classify 链（10×6，S/H 另有 6 个 unbox-fail 例；D 无 unbox 恰为 60），fmv.x 无分支仅需 2 编码×3 副本。10 类位图结果在 verdict 层不可区分，本文按 gen-cases 的 `isa-state-complete` 输入值核实。

## 版本注记

- IR 56cc69a4 是 `rv64d_p1_unified.ir` 的 SHA256（见 `direct-state-p1-56cc69/reports/summary.json`），2026-09-27 由 `unified-backend-build/model-v4-amo-20260927` 以工作树状态（非 HEAD f8ce849，FD 文件相对 HEAD 有本地修改）构建，源快照 931 文件。
- 与当前工作树对比（`unified-backend-model/20260927-fvftype-caller-prebuild/source-manifest.json` 哈希核对）：本组涉及的 `fext/dext/zfh/zfa_insts.sail`、`fdext_control.sail`、`freg_type.sail`、`softfloat_symbolic_f{16,32,64}.sail`、`core/ieee_fp_exceptions.sail`、`core/float_classify.sail`、`core/softfloat_interface.sail` **逐字节一致**；IR 构建后的后续快照仅改 `V/vext_fp_insts.sail`（V 组，与本组无关）。
- **唯一差异**：`FD/fdext_regs.sail:50` 的 `nan_unbox`——IR 版为 `if ... then ... else canonical_NaN()`（真控制流分支，本文按此口径判定 S/H 的 unbox 两分支均被达到），当前工作树已改为 `ite(eq_anything(...), ..., ...)`（不分叉的符号 ite）。后续重新生成的 IR 中该处将不再构成控制流分支，本报告的 unbox 分支结论仅适用于 IR 56cc69a4 及更早。sail 标准库源（float.sail 的 pure 外原语、classify.sail 的 10 类链）取自 IR 快照 `p1-56cc69/source-ast-full/.../sail-src/lib/`。
