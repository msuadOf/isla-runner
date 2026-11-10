# G5 · F_BIN_RM_TYPE_{D,S,H} 分支覆盖核对（fadd/fsub/fmul/fdiv）

数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/cases.tsv` + 三个 replay 包
`single-56cc-20260927-020959-05-f_bin_rm_type_d`（-03=H，-04=S）的
`stage/output/rv64_zF_BIN_RM_TYPE_*.json`（terminals/gen）与
`unified-backend-cpp-replay/sharedtrace-continuation-56cc69-20260927/results/F_BIN_RM_TYPE_*/input-complete/{gen-cases,direct-negative-cases,derived-negative-cases}.json`。
IR 版本 56cc69a4（workarounds-report: candidate_ir_sha256 前缀 56cc69a4）。本文行号同时适用于快照与当前工作树（除另注）。

三条 clause 的执行函数逐行同构（读寄存器 → `select_instr_or_fcsr_rm` → op 分派 → `accrue_fflags` → 写回），因此 Illegal 归因与覆盖结构完全一致，差异仅在位宽与 guard 函数。

## 1. Illegal 归因（三条 clause 相同）

每 mn 的 Illegal = 63(D)/252(S/H) 个 gen 执行期 Illegal + 1 个 decode 负例：

1. **执行期 Illegal（gen，phase=execute）**：指令 rm=DYN 且 `fcsr.FRM ∈ {5,6,7}`。
   `select_instr_or_fcsr_rm`（`fext_insts.sail:51-63`）：`valid_rounding_mode`（:49）排除 101/110，另用 `fcsr_rm != encdec_rounding_mode(RM_DYN)` 排除 111；frm∈{5,6,7} 落入 reserved 分支，按配置 `Fcsr_RM_Illegal`（`platform_config.sail:69-72,95`；默认值 `sail-riscv/config/config.json.in:53`）返回 `None()`，execute 的 `None() => Illegal_Instruction()` 收下。
   证据：D 非法 gen 252 例的 fcsr 恰为 `32'h0000_00a0/00c0/00e0`（frm=5/6/7 各 84 例）；S/H 各 1008 例同构（3 frm × 336）。
   每个保留 frm 值独立有 case，**三个执行期非法取值全部覆盖，无遗漏**。
2. **decode 负例（每 clause 4 例，phase=encode 时 official 求解器报 non-encodable，后由同版真实 encoder 补齐为 raw 编码）**：**与 rm 无关**。负例 pre-state 的 `mstatus = 64'h0000_000a_0000_0000`（mstatus.FS=0b00=Off），使 `currentlyEnabled(Ext_F)`（`fdext_control.sail:18`）= false → encdec 的 `when haveXxxFPU()` guard 不成立 → 译码落入 ILLEGAL → `Illegal_Instruction`。请求元组取 rm=RMM 只是偶然（FS=Off 下任何元组都编不出），cases.tsv/distribution.md 中这些行显示 "rmm"（D）或 `32'h0000_4053` 等裸编码（S/H）**易误导为 rm 相关负例，实际是 FP 关闭状态负例**。负例自带 `guard-source`/`mapping-source` 直接指向对应 encdec 行（见下表）。
   负例编码：D 0x0200/0a00/1200/1a00_4053；S 0x0000/0800/1000/1800_4053；H 0x0400/0c00/1400/1c00_4053（rm=100，寄存器全 f0）。

对账：D 每 mn 64 Illegal = 63 gen + 1 负例；210 Retire = 静态 5 rm × 21 + dyn×frm{0..4} 5×21。S/H 每 mn 252 = 3 frm×84 + 1；840 = 5×84 + 5×84。与 distribution.md 逐 mn 计数一致。

## 2. F_BIN_RM_TYPE_D（1096 例：gen 1092 + direct-negative 4）

分支枚举（✓=有 case 达到；结构性不可达单独标注）：

| 分支 | 文件:行号 | 语义 | 达到 | 证据 case-id |
| --- | --- | --- | --- | --- |
| encdec when guard 真 | dext_insts.sail:317/321/325/329 `when haveDoubleFPU() & validDoubleRegs(...)` | FS≠Off 时可译码 | ✓ | 全部 1092 gen（entry-domain=decoded，编码↔译码回环已验证） |
| encdec when guard 假 → ILLEGAL | 同上（guard 区 317:24-317:65） | mstatus.FS=Off → 译码失败 → Illegal_Instruction | ✓ | 负例 5(fadd.d)/6(fdiv.d)/47(fsub.d)/50(fmul.d)，guard-source=dext_insts.sail 317:24-317:65 |
| select_instr_or_fcsr_rm: instr_rm≠DYN → Some | fext_insts.sail:63 | 静态舍入模式直通 | ✓ | rne 857 / rtz 122 / rdn 324 / rup 336 / rmm 177（各 84 例） |
| DYN 且 frm∈0..4 → Some(frm) | fext_insts.sail:55-56 | 动态取 fcsr.FRM | ✓ | frm0:732, frm1:249, frm2:1067, frm3:751, frm4:491（各 84 例 Retire） |
| DYN 且 frm∈{5,6}（invalid）→ reserved 路径 | fext_insts.sail:55 假 + 57-61 | valid_rounding_mode 排除 101/110 | ✓ | frm5:1058, frm6:797（各 84 例 Illegal） |
| DYN 且 frm==7（==DYN 编码）→ reserved 路径 | fext_insts.sail:55 第二合取假 | frm=111 同样拒绝 | ✓ | frm7:634 等 84 例 Illegal |
| Fcsr_RM_Fatal → reserved_behavior(...) | fext_insts.sail:58 | assert 型保留行为 | ✗（配置门控：config.json.in:53 默认 Fcsr_RM_Illegal，本构建不可达） | — |
| execute None() => Illegal_Instruction | dext_insts.sail:340 | 执行期非法 | ✓ | 上述 frm5/6/7 共 252 例 |
| execute Some 分支：rm_3b + op 四臂 | dext_insts.sail:341-348（Add 344/Sub 345/Mul 346/Div 347） | 算术分派 | ✓ | 每 mn 274 例（210 R+64 I 之外的 I 不过此臂；四 mn 均匀） |
| accrue_fflags（SYMBOLIC 版）: `ite(changed,...)` 双极性 | fdext_regs.sail:542-554（changed 计算于 545，ite 于 548-551） | fflags 置位时把 mstatus.FS 置 Dirty | ✓ 数据级 | Retire 630 例 post-fflags==0（changed=false）、210 例 ≠0（changed=true；pre-fflags 恒 0） |
| accrue_fflags: `if hartSupports(Ext_F)` 假极性 | fdext_regs.sail:548 | Zfinx-only hart | ✗（结构性：hartSupports(Ext_F) 静态 true） | — |
| rF_or_X_D: `if hartSupports(Ext_F)` | fdext_regs.sail:384-396 | F 寄存器 vs Zfinx X 寄存器/奇偶对 | ✓ 仅真极性（假极性=Zfinx，结构性不可达；RV32 偶对分支 391-395 亦 xlen=64 不可达） | 全部 gen 读 rs1/rs2 |
| wF_or_X_D 写回真极性 | fdext_regs.sail:414-428 | 写 F 寄存器 | ✓ | 全部 840 Retire |
| nan_unbox `'n=='m` 直通极性 | fdext_regs.sail:49-50 | D 读宽==FLEN，恒走 then | ✓（类型级固定极性） | 全部 gen |
| validDoubleRegs 内 RV32Zdinx 奇数寄存器分支 | dext_insts.sail:219-228 | rv32zdinx 限制 | ✗（结构性：xlen=64 且 Ext_Zdinx 关） | — |

**未达分支汇总**：fcsr_rm 的 Fatal 臂（配置门控）；F_or_X/accrue_fflags 的 Zfinx 极性（hart 静态配置）；validDoubleRegs RV32Zdinx 分支（xlen）。均非本目标（rv64, F/D 开）可达，不构成求解遗漏。

rm 覆盖矩阵（gen 1092；行=指令 rm，列=fcsr.FRM 初值；"–"=该组合无用例；静态 rm 下 frm 架构上不被读取，见证 state 无 fcsr 记录）：

| 指令 rm \ frm | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 无 fcsr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rne | – | – | – | – | – | – | – | – | R×84 |
| rtz/rdn/rup/rmm | – | – | – | – | – | – | – | – | R×84 各 |
| dyn | R×84 | R×84 | R×84 | R×84 | R×84 | I×84 | I×84 | I×84 | – |
| （编码 101/110） | 不在 rounding_mode 枚举域，无 case（见 §5 缺口） | | | | | | | | |

另维度：priv M/S/U 全有；mstatus.FS：Initial(1)/Clean(2)（gen）+ Off(0)（4 负例）；FS=Dirty(3) 无 case（对 guard 语义等价于 Clean，低风险）。

## 3. F_BIN_RM_TYPE_S（4372 例：gen 4368 + derived-negative 4）

与 §2 同构，仅列差异。S 侧数字：gen 4368=3360 R+1008 I；每 mn 840 R / 252 I（21→84 上下文放大）。

| 分支 | 文件:行号 | 达到 | 证据 case-id |
| --- | --- | --- | --- |
| encdec when `haveSingleFPU()` 真/假 | fext_insts.sail:429/433/437/441（guard@431 等）；假极性→ILLEGAL | ✓/✓ | 真：4368 gen；假：负例 5/6/51/56（mapping-source=fext_insts.sail 429:24-429:65；1 Machine+3 User，FS=Off） |
| 静态 rm→Some（:63） | fext_insts.sail:63 | ✓ | rne 736 / rtz 3063 / rdn 862 / rup 3349 / rmm 1605（各 336） |
| dyn+frm0..4→Retire | fext_insts.sail:55-56 | ✓ | frm0:2835, 1:1173, 2:4027, 3:343, 4:2107（各 336） |
| dyn+frm5/6/7→Illegal（None→ fext_insts.sail:60 → execute None 臂 fext_insts.sail:452） | :49,55,60; 452 | ✓ | frm5:2121, 6:4290, 7:676（各 336） |
| op 四臂 f32Add/Sub/Mul/Div | fext_insts.sail:456-459 | ✓ | 四 mn 均匀（每 mn 1092） |
| accrue_fflags ite 双极性 | fdext_regs.sail:542-554 | ✓ 数据级 | post-fflags==0 3150 例 / ≠0 210 例 |
| rF_or_X_S / wF_or_X_S 真极性 | fdext_regs.sail:376-382 / 406-412 | ✓ | 全部 gen |
| **rF_S 内 nan_unbox 双极性** | fdext_regs.sail:41-51（调用点 342；`if 'n=='m` 对 S 恒走 else 50） | ✓ 数据级 | case 级：rs 为合法 NaN-box 3276 例、非 box 3276 例（读出 canonical NaN），同 case 双极性 2184 例 |
| Zfinx 假极性 / Fatal 臂 | fdext_regs.sail:381,411；fext_insts.sail:58 | ✗（结构性/配置门控，同 §2） | — |

rm 覆盖矩阵：同 §2 形状，每格 84→336；frm 0..4 全 Retire、5/6/7 全 Illegal；priv M/S/U 全覆盖；FS=Off 由 4 负例覆盖。

## 4. F_BIN_RM_TYPE_H（4372 例：gen 4368 + derived-negative 4）

与 §2/§3 同构。guard 换为 `haveHalfFPU()`（zfh_insts.sail:155 = currentlyEnabled(Ext_Zfh)|Zhinx；currentlyEnabled(Ext_Zfh) 还要求 currentlyEnabled(Ext_F)，fext_insts.sail:28——故 FS=Off 同样令 H 译码失败）。

| 分支 | 文件:行号 | 达到 | 证据 case-id |
| --- | --- | --- | --- |
| encdec when `haveHalfFPU()` 真/假 | zfh_insts.sail:176/180/184/188（guard@178 等） | ✓/✓ | 真：4368 gen；假：负例 4/6/51/52（mapping-source=zfh_insts.sail 176:24-176:65；1 Machine+3 User，FS=Off；编码 0x0400/1c00/1400/0c00_4053） |
| 静态 rm→Some | fext_insts.sail:63 | ✓ | rne 771 / rtz 3119 / rdn 899 / rup 3235 / rmm 1718（各 336） |
| dyn+frm0..4→Retire | fext_insts.sail:55-56 | ✓ | frm0:2853, 1:1173, 2:4027, 3:346, 4:2010（各 336） |
| dyn+frm5/6/7→Illegal（None 臂 zfh_insts.sail:199 `return Illegal_Instruction()`） | :49,55,60; 199 | ✓ | frm5:2045, 6:4332, 7:679（各 336） |
| op 四臂 f16Add/Sub/Mul/Div | zfh_insts.sail:203-206 | ✓ | 四 mn 均匀 |
| accrue_fflags ite 双极性 | fdext_regs.sail:542-554 | ✓ 数据级 | post-fflags==0 3150 / ≠0 210 |
| rF_or_X_H / wF_or_X_H 真极性 | fdext_regs.sail:368-374 / 398-404 | ✓ | 全部 gen |
| rF_H 内 nan_unbox 双极性（H 读高 48 位须全 1） | fdext_regs.sail:41-51 | ✓ 数据级 | box 3276 / 非 box 3276（canonical NaN），同 case 双极性 2184 |
| Zfinx 假极性 / Fatal 臂 | 同 §2 | ✗（结构性/配置门控） | — |

## 5. 全组结论

1. **控制流分支（clause 自身+共享路径）在目标配置可达范围内全部达到**：rm 有效性三分支（静态直通 / dyn+合法 frm / dyn+保留 frm→Illegal）、op 四臂、fflags 累加与写回、encdec guard 真假两极性（真=gen 译码回环，假=FS=Off 负例，负例 guard-source 直接锚定 encdec 行）、S/H 的 nan_unbox 两数据极性均有 case。
2. **Illegal 恰好覆盖全部执行期非法分支且无遗漏**：执行期唯一非法出口是 `select_instr_or_fcsr_rm=None`（frm=5/6/7 三取值逐一有 case）；decode 负例恰好覆盖 encdec guard 假极性（4 op 各 1 例）。TSV 把负例行标成 rm=rmm/裸编码属展示层误导——真实归因是 mstatus.FS=Off 的译码 guard，与 rm 枚举无关。
3. **覆盖缺口（不影响上述"可达分支全覆盖"结论，但 rm 全枚举未闭合）**：
   - 指令 rm 字段保留编码 **101/110 的译码失败极性无用例**：`encdec_rounding_mode`（fext_insts.sail:31-38）只有 6 个枚举成员，101/110 不在 clause 值域，官方求解枚举无法表达；57 目标也没有针对它们的 raw 编码负例（4 个负例都是 rm=100）。若要闭合需补 raw 负例（如 0x02804053/0x03004053 族）。
   - fcsr_rm_reserved_behavior 的 `Fcsr_RM_Fatal`（fext_insts.sail:58）在默认配置 Fcsr_RM_Illegal 下不可达（配置门控，非用例缺失）。
   - Zfinx 读/写极性（fdext_regs.sail:373/381/390-395 等）、validDoubleRegs RV32Zdinx 分支（dext_insts.sail:219-228）为 hart/xlen 静态门控，本目标结构性不可达。
   - mstatus.FS=Dirty 无 pre-state case（guard 语义只判 !=0，低风险）。
4. **fdiv 数值分支（helper 内部，返回值层面不可区分）**：除零/0÷0/∞÷∞/sNaN/正常除位于 extern `fp64_div/f32_div/f16_div`（prelude/ieee_fp_primops.sail:155 等 `pure` extern，SoftFloat/Z3 侧）与 `ieee_div64_exceptions`（core/ieee_fp_exceptions.sail:577-599，纯值级 strict_or/and_bool 布尔式，无独立控制流分支），在 (fflags, rd) 返回元组层面不可区分。数据注记：**全部 fdiv 见证的 rs1=rs2=+0.0（0/0→NV+canonical NaN）**，DZ（x/0）与正常除数据路径未在见证值中出现——值级不影响分支覆盖，但若做数值对账（emu vs NEMU）需另行构造非零除数用例。
5. **rm 全枚举核对结论**：指令 rm 域 6 值（rne/rtz/rdn/rup/rmm/dyn）全覆盖；fcsr.frm 初始值 8 值全覆盖（0-4→Retire，5/6/7→Illegal，各 84/336 例）；静态 rm 不读 frm（无 fcsr 记录，维度不适用）；唯一缺口为指令 rm 保留编码 101/110（见上）。

## 6. 版本注记（IR 56cc69a4 vs 当前工作树）

- 对比基准：replay 包 `evidence/candidate/model/`（IR 56cc69a4 生成时冻结的源快照）vs `sail-riscv/` 当前工作树（HEAD=f8ce849 + 未提交修改）。
- `fext_insts.sail`、`dext_insts.sail`、`zfh_insts.sail`、`fdext_control.sail`：**逐字一致**，本文行号两版通用。
- `fdext_regs.sail` 仅 1 行差异：`nan_unbox`（:50）快照为 `if x[...]==ones() then ... else ...`（控制分支），当前工作树改为 `ite(eq_anything(...), ...)`（值级，消除分支）。语义等价；若以新树重生成 IR，本报告中 nan_unbox 一项将不再是控制流分支，其余结论不变。
- 工作树相对 HEAD 的未提交修改（git diff）涉及 FMIN/FMAX 改用 `fp_min/max_pure`、`get_F_bits/set_F_bits` 向量后端、`accrue_fflags` 的 `$ifdef SYMBOLIC` 双版本等；这些修改在快照中已存在（快照=当前工作树），**不影响本组三 clause 的 encdec/execute 路径**。
- 结论适用版本：IR 56cc69a4，runs single-56cc-20260927-020959-03/04/05；若 FD 源后续变动需重验。
