# G1 分支覆盖对照：FLEQ_D/H/S、FLTQ_D/H/S、FMINM_D/H/S、FMAXM_D/H/S

- 数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/{distribution.md,cases.tsv}`（run `official-56cc-long-20260927-064348`，IR sha256 前缀 56cc69a4，逐 case 过滤 `$2=="z<clause>"`）。
- 源码基线：`sail-riscv/model/extensions/FD/zfa_insts.sail`（当前工作树与冻结 manifest 哈希一致，见[版本注记](#版本注记)），共享分支在 `fdext_regs.sail`、`fdext_control.sail`、`fext_insts.sail`、`fp_minmax.sail`、`softfloat_symbolic_f{16,32,64}.sail`、`ieee_fp_exceptions.sail`。
- 本组 12 clause 结构完全同构：**execute 函数体内没有任何返回 `Illegal_Instruction` 的分支，单出口 `RETIRE_SUCCESS`**（对照 FROUND 家族在 `select_instr_or_fcsr_rm` 的 `None() => Illegal_Instruction` 臂，zfa_insts.sail:316 等）。因此 Illegal 只能产生于译码层（encdec guard 失败 fallback）。

## 共享分支详表（各 clause 表按编号引用）

| # | 分支 | 文件:行号 | 语义 | verdict 可见性 |
| --- | --- | --- | --- | --- |
| S1 | encdec 位域匹配（funct7/funct3/opcode 固定值，rs1/rs2/rd 全 5 位自由） | zfa_insts.sail 各 clause encdec 行 | 编码合法即匹配，无变量 guard 位 | 可见（匹配→execute，不匹配→fallback Illegal） |
| S2 | `when currentlyEnabled(Ext_Zfa)` = `hartSupports(Ext_Zfa) & currentlyEnabled(Ext_F)` | zfa_insts.sail:9 | Zfa+F 使能合取 | 可见（false→fallback） |
| S3 | `currentlyEnabled(Ext_F)` = `hartSupports(F) & misa[F]==1 & mstatus[FS]!=0 & currentlyEnabled(Ext_Zicsr)` | fdext_control.sail:18 | 4 项合取的 F 使能 | 可见（同上；4 子项在 verdict 层合并，不可区分） |
| S4 | `currentlyEnabled(Ext_D)`（D 格式追加：`misa[D] & FS!=0 & flen>=64 & Zicsr`） | fdext_control.sail:19 | D 使能 | 可见（同上） |
| S5 | `currentlyEnabled(Ext_Zfh)` = `hartSupports(Ext_Zfh) & currentlyEnabled(Ext_F)`（H 格式追加） | fext_insts.sail:28 | 半精度支持检查 | 可见（同上） |
| S6 | 读 `F_H/F_S`：`assert` ×2 + `nan_unbox` 两方向（高位全1→取低位 / 否则→canonical NaN） | fdext_regs.sail:327-331/339-343（调用），nan_unbox :48-51 | NaN-box 解包 ite | 不可见（数据流，两方向均 Retire） |
| S7 | 读 `F_D`：`assert` ×2，直接读（flen=64 无 unbox） | fdext_regs.sail:351-354 | 无数据流分支 | — |
| S8 | quiet 比较 `riscv_f*Le/Lt_quiet`：`fp*_lteq/lt`（external 未解释，IR 无 fn）+ `ieee_lt*_exceptions(false,a,b)` | softfloat_symbolic_f16.sail:146/158、f32:31/43、f64:22/32；exceptions ieee_fp_exceptions.sail:85-90/178-183/270-275；external 声明 ieee_fp_primops.sail:121-126 | 比较结果 bool（true/false 两方向）+ NV 标志（quiet 版仅 `is_snan(a)|is_snan(b)` 置 NV，两方向） | 不可见（rd 写回 0/1、fflags 均不进 verdict） |
| S9 | `fp_minm_pure/fp_maxm_pure`：外层 `strict_or(is_nan op1, is_nan op2)`→canonical NaN 的 ite + `fp_min/max_pure` 内层 6 臂 ite 链（双NaN/单NaN×2/-0+0 两种/LT 选臂） | fp_minmax.sail:46-50/52-56（外层），:2-22/24-44（内层），Lt_quiet 调用 :5-8/27-30 | min/max 结果选择 | 不可见（数据流） |
| S10 | `accrue_fflags`（SYMBOLIC 版）：`changed` ite（FFLAGS 变化→`mstatus.FS=Dirty,SD=1` / 不变）+ `hartSupports(Ext_F)` 方向 + assert | fdext_regs.sail:542-554 | fflags 累积与 mstatus 副作用 | 不可见（状态副作用） |
| S11 | 写回 `X(rd)=zero_extend(bool_to_bit(...))`（FLEQ/FLTQ）或 `F_*(rd)=rd_val`（MINM/MAXM，wF_S/H 含 nan_box 无分支） | zfa_insts.sail 各 execute 末行；fdext_regs.sail:333-337/345-349/357-361 | 无控制流分支 | — |

IR 佐证（stage/rv64d.ir，sha256=56cc69a4…）：`zriscv_f*Le/Lt_quiet`、`zfp_min/max/m_pure`、`zieee_lt*_exceptions`、`znan_unbox` 均为展开 `fn`（真实数据流分支）；`zfp*_lteq/zfp*_lt` 为 external 未解释 `val`（"fp_lteq"，IR 内无分支）。IR 行号引用（如 fp_minm_pure@`88 178`、f32Le_quiet@`88 588`）与工作树源码逐行吻合。

## FLEQ_S（211 case = 210 gen Retire + 1 direct-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域 `0b101_0000 @ rs2 @ rs1 @ 0b100 @ rd @ 0b101_0011`（true 侧） | zfa_insts.sail:574-576 | 合法编码译码 | 达到 | 210 gen 全 Retire（U=179/S=78/M=196） |
| S2+S3 guard（true 侧） | :576、:9、fdext_control.sail:18 | Zfa+F 使能 | 达到 | 同上 |
| S1/S2/S3 guard=false→fallback Illegal | 同上 | 译码拒绝 | 达到 | case 1（direct-negative，ins `fleq.s x0, f0, f0`，priv=Machine） |
| S6 读 `F_S`×2（nan_unbox 两方向） | :584-585 | 操作数读 | 达到（进入 execute） | 任一 gen case；两方向无法区分 |
| S8 `riscv_f32Le_quiet` | :587-588、softfloat_symbolic_f32.sail:43-47 | LE 结果+NK/不置、lteq true/false | 达到（调用发生） | 任一 gen case；方向不可区分 |
| S10 `accrue_fflags` | :590 | fflags 累积 | 达到 | 任一 gen case |
| S11 写回 `X(rd)` + RETIRE | :591-592 | 单出口 | 达到 | 210 Retire |

- **未达分支**：无（控制流层面）。
- **维度小结**：rm 字段不存在（funct3=100 是功能码），不读 fcsr.frm——tsv gen 行 rm/fcsr 列空与源码一致，该两维度结构性不适用；priv U/S/M 各 70 条 gen；f 操作数取值维度（NaN/sNaN/±0/普通）不在 tsv，全部归"需 trace"。execute 无 Illegal 出口，gen 全 Retire 是源码结构使然。

## FLEQ_H（211 case = 210 gen Retire + 1 direct-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域 `0b101_0010 @ … @ 0b100 @ …`（true 侧） | zfa_insts.sail:524-526 | 合法编码译码 | 达到 | 210 gen（U=179/S=78/M=193） |
| S2+S3+S5 guard `Ext_Zfh & Ext_Zfa`（true 侧） | :526、:9、fext_insts.sail:28、fdext_control.sail:18 | Zfh 支持检查+F 使能 | 达到 | 同上 |
| guard=false→fallback Illegal | 同上 | 译码拒绝 | 达到 | case 1（direct-negative，ins `fleq.h x0, f0, f0`，priv=Supervisor） |
| S6 读 `F_H`×2 | :534-535 | H 操作数 nan_unbox | 达到 | 任一 gen case |
| S8 `riscv_f16Le_quiet` | :537-538、softfloat_symbolic_f16.sail:158-162 | LE+N | 达到 | 任一 gen case |
| S10 `accrue_fflags` / S11 写回 `X(rd)` + RETIRE | :540-542 | 单出口 | 达到 | 210 Retire |

- **未达分支**：无（控制流层面）。
- **维度小结**：同 FLEQ_S；H 特有的 mstatus.FS 使能（S3 内）与 Zfh 检查（S5）各只有"合取真/假"两档结果被测到，单独翻转哪一项无法区分。gen=210 全 Retire、Illegal=1 为 direct-negative——execute 本身无非法分支，属正常。

## FLEQ_D（85 case = 84 gen Retire + 1 derived-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域 `0b101_0001 @ … @ 0b100 @ …`（true 侧） | zfa_insts.sail:625-627 | 合法编码译码 | 达到 | 84 gen（U=5/S=77/M=32） |
| S2+S3+S4 guard `Ext_D & Ext_Zfa`（true 侧） | :627、fdext_control.sail:18-19 | D+F 使能 | 达到 | 同上 |
| guard=false→fallback Illegal | 同上 | 译码拒绝 | 达到 | case 1（derived-negative，编码 `32'ha200_4053`＝`fleq.d x0,f0,f0` **完整合法编码**，priv=User；Illegal 只能由状态禁用产生） |
| S7 读 `F_D`×2（无 unbox） | :635-636 | 操作数读 | 达到 | 任一 gen case |
| S8 `riscv_f64Le_quiet` | :638-639、softfloat_symbolic_f64.sail:32-36 | LE+N | 达到 | 任一 gen case |
| S10 `accrue_fflags` / S11 写回 `X(rd)` + RETIRE | :641-643 | 单出口 | 达到 | 84 Retire |

- **未达分支**：无（控制流层面）。
- **维度小结**：priv U/S/M 各 28 条；rm/fcsr 不适用（同 FLEQ_S）。derived-negative 的编码经位域复核（funct7=1010001、funct3=100、opcode=1010011）为本 clause 完全合法编码，证明其 Illegal 走的是 guard=false 路径而非编码破坏。

## FLTQ_S（211 case = 210 gen Retire + 1 derived-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域（funct3=`0b101`）true 侧 | zfa_insts.sail:599-601 | 合法编码译码 | 达到 | 210 gen（U=178/S=80/M=193） |
| S2+S3 guard（true 侧） | :601 | Zfa+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（derived-negative，`32'ha000_5053`＝`fltq.s x0,f0,f0` 合法编码，priv=Machine） |
| S6 读 `F_S`×2 | :609-610 | nan_unbox | 达到 | 任一 gen case |
| S8 `riscv_f32Lt_quiet` | :612-613、softfloat_symbolic_f32.sail:31-35 | LT+N | 达到 | 任一 gen case |
| S10/S11 写回 + RETIRE | :615-617 | 单出口 | 达到 | 210 Retire |

- **未达分支**：无（控制流层面）。**维度小结**：同 FLEQ_S。

## FLTQ_H（211 case = 210 gen Retire + 1 derived-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域（funct7=`0b101_0010`、funct3=`0b101`） | zfa_insts.sail:549-551 | 合法编码译码 | 达到 | 210 gen（U=187/S=76/M=190） |
| S2+S3+S5 guard `Ext_Zfh & Ext_Zfa` | :551 | Zfh+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（derived-negative，`32'ha400_5053`＝`fltq.h x0,f0,f0` 合法编码，priv=Machine） |
| S6 读 `F_H`×2 / S8 `riscv_f16Lt_quiet` | :559-563、softfloat_symbolic_f16.sail:146-150 | LT+N | 达到 | 任一 gen case |
| S10/S11 写回 + RETIRE | :565-567 | 单出口 | 达到 | 210 Retire |

- **未达分支**：无（控制流层面）。**维度小结**：同 FLEQ_H。

## FLTQ_D（85 case = 84 gen Retire + 1 derived-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域（funct3=`0b101`） | zfa_insts.sail:650-652 | 合法编码译码 | 达到 | 84 gen（U=5/S=77/M=29） |
| S2+S3+S4 guard `Ext_D & Ext_Zfa` | :652 | D+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（derived-negative，`32'ha200_5053`＝`fltq.d x0,f0,f0` 合法编码，priv=User） |
| S7 读 `F_D`×2 / S8 `riscv_f64Lt_quiet` | :660-664、softfloat_symbolic_f64.sail:22-26 | LT+N | 达到 | 任一 gen case |
| S10/S11 写回 + RETIRE | :666-668 | 单出口 | 达到 | 84 Retire |

- **未达分支**：无（控制流层面）。**维度小结**：同 FLEQ_D。

## FMINM_S（85 case = 84 gen Retire + 1 derived-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域 `0b001_0100 @ … @ 0b010 @ …` | zfa_insts.sail:211-213 | 合法编码译码 | 达到 | 84 gen（U=5/S=77/M=28） |
| S2+S3 guard（true 侧） | :213 | Zfa+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（derived-negative，`32'h2800_2053`＝`fminm.s f0,f0,f0` 合法编码，priv=Machine） |
| S6 读 `F_S`×2 | :221-222 | nan_unbox | 达到 | 任一 gen case |
| S9 `fp_minm_pure`（内层 6 臂 ite + 外层 NaN 重写 + `riscv_f32Lt_quiet`） | :224、fp_minmax.sail:46-50/2-22 | min 结果选择+N | 达到（调用发生） | 任一 gen case；各臂方向不可区分 |
| S10 `accrue_fflags` / S11 写回 `F_S(rd)` + RETIRE | :225-227 | 单出口 | 达到 | 84 Retire |

- **未达分支**：无（控制流层面）。
- **维度小结**：无 rm 字段（funct3=010 功能码）、不读 fcsr.frm——与 FLEQ 族相同，rm/fcsr 维度不适用；priv U/S/M 各 28。操作数分类维度（双 NaN/单 NaN/-0 对 +0/LT 大小关系）共 7 个结果方向（fp_minmax.sail:15-20 六臂 + :49 外层），verdict 层全不可区分。

## FMINM_H（85 case = 84 gen Retire + 1 derived-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域 `0b001_0110 @ … @ 0b010 @ …` | zfa_insts.sail:165-167 | 合法编码译码 | 达到 | 84 gen（U=5/S=77/M=31） |
| S2+S3+S5 guard `Ext_Zfh & Ext_Zfa` | :167 | Zfh+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（derived-negative，`32'h2c00_2053`＝`fminm.h f0,f0,f0` 合法编码，priv=Machine） |
| S6 读 `F_H`×2 | :175-176 | H nan_unbox | 达到 | 任一 gen case |
| S9 `fp_minm_pure`（`riscv_f16Lt_quiet`，fp_minmax.sail:5） | :178、fp_minmax.sail:46-50/2-22 | min+N | 达到 | 任一 gen case |
| S10/S11 写回 `F_H(rd)` + RETIRE | :179-181 | 单出口 | 达到 | 84 Retire |

- **未达分支**：无（控制流层面）。**维度小结**：同 FMINM_S，另 Zfh/FS 使能细分不可区分（同 FLEQ_H）。gen=210/84 全 Retire 而 Illegal 仅 1 条 direct/derived-negative，与"execute 无非法分支"一致。

## FMINM_D（22 case = 21 gen Retire + 1 direct-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域 `0b001_0101 @ … @ 0b010 @ …` | zfa_insts.sail:257-259 | 合法编码译码 | 达到 | 21 gen（U=5/S=16/M=22） |
| S2+S3+S4 guard `Ext_D & Ext_Zfa` | :259 | D+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（direct-negative，ins `fminm.d f0, f0, f0` 合法编码，priv=Machine） |
| S7 读 `F_D`×2 | :267-268 | 直接读 | 达到 | 任一 gen case |
| S9 `fp_minm_pure`（`riscv_f64Lt_quiet`，fp_minmax.sail:7） | :270、fp_minmax.sail:46-50/2-22 | min+N | 达到 | 任一 gen case |
| S10/S11 写回 `F_D(rd)` + RETIRE | :271-273 | 单出口 | 达到 | 21 Retire |

- **未达分支**：无（控制流层面）。**维度小结**：priv U/S/M 各 7（组内最少，因 identity-coverage 去重）；其余同 FMINM_S。

## FMAXM_S（85 case = 84 gen Retire + 1 derived-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域（funct3=`0b011`） | zfa_insts.sail:234-236 | 合法编码译码 | 达到 | 84 gen（U=5/S=77/M=31） |
| S2+S3 guard（true 侧） | :236 | Zfa+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（derived-negative，`32'h2800_3053`＝`fmaxm.s f0,f0,f0` 合法编码，priv=Supervisor） |
| S6 读 `F_S`×2 / S9 `fp_maxm_pure`（`riscv_f32Lt_quiet`） | :244-247、fp_minmax.sail:52-56/24-44 | max+N | 达到 | 任一 gen case |
| S10/S11 写回 + RETIRE | :248-250 | 单出口 | 达到 | 84 Retire |

- **未达分支**：无（控制流层面）。**维度小结**：同 FMINM_S（fp_max_pure 内层 6 臂 + 外层 NaN 重写共 7 方向不可区分）。

## FMAXM_H（85 case = 84 gen Retire + 1 derived-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域 `0b001_0110 @ … @ 0b011 @ …` | zfa_insts.sail:188-190 | 合法编码译码 | 达到 | 84 gen（U=5/S=77/M=31） |
| S2+S3+S5 guard `Ext_Zfh & Ext_Zfa` | :190 | Zfh+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（derived-negative，`32'h2c00_3053`＝`fmaxm.h f0,f0,f0` 合法编码，priv=User） |
| S6 读 `F_H`×2 / S9 `fp_maxm_pure`（`riscv_f16Lt_quiet`） | :198-201、fp_minmax.sail:52-56/24-44 | max+N | 达到 | 任一 gen case |
| S10/S11 写回 + RETIRE | :202-204 | 单出口 | 达到 | 84 Retire |

- **未达分支**：无（控制流层面）。**维度小结**：同 FMINM_H。

## FMAXM_D（22 case = 21 gen Retire + 1 direct-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| S1 位域 `0b001_0101 @ … @ 0b011 @ …` | zfa_insts.sail:280-282 | 合法编码译码 | 达到 | 21 gen（U=5/S=16/M=21） |
| S2+S3+S4 guard `Ext_D & Ext_Zfa` | :282 | D+F | 达到 | 同上 |
| guard=false→fallback | 同上 | 译码拒绝 | 达到 | case 1（direct-negative，ins `fmaxm.d f0, f0, f0` 合法编码，priv=Machine） |
| S7 读 `F_D`×2 / S9 `fp_maxm_pure`（`riscv_f64Lt_quiet`） | :290-293、fp_minmax.sail:52-56/24-44 | max+N | 达到 | 任一 gen case |
| S10/S11 写回 + RETIRE | :294-296 | 单出口 | 达到 | 21 Retire |

- **未达分支**：无（控制流层面）。**维度小结**：同 FMINM_D。

## 负例（译码拒绝）归因复核

12 条 negative case 的指令编码逐条位域复核结果：8 条 derived-negative 的十六进制编码（a2004053/a0005053/a4005053/a2005053/28002053/2c002053/28003053/2c003053）与 4 条 direct-negative 的汇编（`fleq.s`/`fleq.h`/`fminm.d`/`fmaxm.d`，均 `*0, f0, f0` 形式）**全部是本 clause 的完整合法编码**（funct7/funct3/opcode 全部匹配）。合法编码得到 `Illegal_Instruction` 的唯一途径是 encdec `when` guard（S2/S3/S4/S5 合取）在初始状态下为假（如 misa.F=0、mstatus.FS=00、Zicsr 禁用或 hartSupports 关闭），fallback 出译码。因此本组 **guard=false 译码拒绝分支均已达到**（每 clause 恰 1 条）。tsv 未保留具体禁用了哪个状态位，成因细分不可区分（需 trace）。

## 版本注记

- run manifest（`official-56cc-long-20260927-064348/evidence/manifest.json`）记录 IR `stage/rv64d.ir` sha256=`56cc69a4…`（09-27 05:25 构建）及冻结模型文件哈希。逐文件比对当前工作树：`zfa_insts.sail`、`fp_minmax.sail`、`fext_insts.sail`、`fdext_control.sail`、`softfloat_symbolic_f16/f32/f64.sail`、`ieee_fp_exceptions.sail` **完全一致**——本文引用行号即求解所用源码。
- 唯一差异文件 `fdext_regs.sail`：冻结版（manifest `5cc76926…`，快照 `nan-unbox-ite-probe-20260927/baseline`）与当前（`dc8bdf1c…`）仅有一处改动——`nan_unbox` 的 `if … then … else` 重写为 `ite(...)`（09-27 15:23 nan-unbox-ite-probe 性能改动），两路选择语义相同，分支结构不变，不影响本文结论。
- IR 内部佐证：56cc IR 中 `zfp_minm_pure@88:178`、`zriscv_f32Le_quiet@88:588` 等行号引用与工作树逐行吻合；比较 primop `fp*_lteq/fp*_lt`（ieee_fp_primops.sail:121-126）在 IR 中为 external 未解释（`val … = "fp_lteq"`），即比较真值在 IR 层无内部展开分支。
- 任务背景中提到的 `valid_reg_group` 等改动位于 V 扩展文件（sail-riscv git log：f8ce849/5f1a0de/f62dba8 等，均未触及 `model/extensions/FD/`），与本组无关。

## 全组结论

1. **确定未达的控制流分支：0 个**。三条控制流路径全部有 case 达到：
   - 译码接受 + execute 唯一出口 `RETIRE_SUCCESS`：每 clause 21~210 条 gen Retire；
   - 译码拒绝（encdec guard=false fallback Illegal）：每 clause 恰 1 条 direct/derived-negative（编码经复核为合法，Illegal 必由状态禁用产生）；
   - execute 内**不存在** Illegal/异常/保留值检查分支（与 FROUND 家族不同，本组无 `select_instr_or_fcsr_rm` 类分叉），故"gen 内从未出现 Illegal"是源码结构使然，不是覆盖缺失。
2. **无法从返回值层面区分、需 trace（rd 写回值 / fflags / mstatus）才能确认的方向**（每 clause 同构，共 6 类）：
   - guard=false 的具体成因（misa.F / mstatus.FS / Zicsr / hartSupports(Zfa) / D 或 Zfh 各自禁用，5~7 个合取子项）——每 clause 仅 1 条 neg，无法区分翻转项；
   - `nan_unbox` 读路径两方向（H/S 格式：NaN-box 合法 vs 返回 canonical NaN，fdext_regs.sail:48-51）；
   - quiet 比较的 NV 置位/不置位（`ieee_lt*_exceptions` 的 `is_snan` 分支，quiet 版 NV 仅由 sNaN 触发）；
   - `fp*_lteq/lt`（IR 未解释）结果 true/false → `rd`=1/0 两方向；
   - FMINM/FMAXM 的 `fp_min/max_pure` 6 臂 ite + 外层 NaN 重写共 7 个结果方向（fp_minmax.sail:15-20/37-42/49/55）；
   - `accrue_fflags` 的 `changed`→`mstatus.FS=Dirty` / 不变 两方向（fdext_regs.sail:546-553）。
3. **维度覆盖**：priv U/S/M 三档全有（S/H 比较 70、S minmax 与 D 比较 28、D minmax 7 条/档）；rm 维度结构性不适用（funct3 为功能码非舍入码，不读 fcsr.frm），fcsr 初值 gen 行未具体化且对控制流无影响；f 操作数取值维度不在 cases.tsv 中。
