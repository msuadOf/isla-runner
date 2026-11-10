# make solve 浮点产物分支覆盖核账汇总（2026-09-28）

## 数据与版本

- 产物：57 个自然完成目标的官方 make solve 输出，80416 case（80283 gen + 91 direct-negative + 42 derived-negative），返回值全集 = 44559 Retire + 35857 Illegal，162 个 mnemonic。IR `56cc69a4…9956ac`，构建源冻结树 `isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/sail-riscv/`（sail-riscv HEAD `f8ce849` + 当时补丁）。
- 分布图与逐 case 数据：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/`（distribution.md/json、cases.tsv、unfinished.json；生成脚本 `agents/float_support_review/tools/solve_distribution/`）。
- 逐 clause 对照报告：本目录 G1–G12（12 组 × 57 clause，每 clause 含源码分支枚举表、达到证据 case-id、未达清单）。20 个未完成目标（全向量族）无产物，不在本次核账内。
- 主 agent 抽查复核：FROUNDNX_D 10 Illegal = 9×(dyn+fcsr a0/c0/e0) + 1×(rup, FS=Off 负例) ✓；BF16 向量两 clause Retire 全 vl=0 ✓；fdiv 操作数全零初值 ✓；VFMERGE vd=0 拒绝数与历史 7615 独审吻合 ✓。

## 总回答：控制流分支是否全都达到？

**分两层回答。**

### A. 指令层控制流（译码 guard 真假臂、execute 显式分支、RM 非法→Illegal、写回）：57 clause 基本全部达到

1. **35857 个 Illegal 全部归因、零残留**：
   - FRM 保留值执行期 Illegal：`rm=dyn + fcsr.FRM∈{5,6,7}`（fcsr=0xa0/c0/e0）→ `select_instr_or_fcsr_rm` None → `Illegal_Instruction`。标量各 rm 族每 mnemonic 9–63 例；向量族共 8919（G11）+ 504（G12）。
   - 译码负例（133 条）：`mstatus.FS=Off` 触发 encdec guard 假臂（G8 经负例 JSON mstatus=0xa00000000 + 合法 rm 编码定论；G9 遗留 A/B 之争裁定 B 成立）。
   - 向量 guard：vd=v0 红线 7560（任一命中 7615，与历史 vd=0 独审精确吻合）、寄存器组对齐/重叠 5832+507、vstart 越界 3744+451、LMUL=8 126、SEW≠16 译码 6、SEW=8 8（G11/G12，按 Sail 短路求值序逐 case 重放，预测与 verdict 零不一致）。
2. **execute 显式分支全达**：FLI 32 个立即数 match 臂全枚举（含边界）；fclass 三宽度 10/10 类全达；FROUND/FROUNDNX None→Illegal 与 Some 两臂；`select_instr_or_fcsr_rm` 四子路径；op match 四臂；negate；S/H `nan_unbox` 两臂；VFMVSF `mask[0]`/`tail_ag` 两臂；quiet 比较/minmax 族 execute 无 Illegal 分支（gen 全 Retire 是源码结构使然，非缺失）。
3. **唯一普遍性控制流缺口：指令编码 rm=0b101/0b110 的译码失败分支零覆盖**（`encdec_rounding_mode` 无反映射，gen 无法表达、负例生成器选了 FS=Off 而非 raw 保留编码）。G2/G5/G6/G8/G9/G10 一致报告。属输入域缺口，闭合需补 raw 负例（如 0x02804053/0x03004053 族）。

   **版本后继核对**：这句话的分母仅为56cc官方57目标产物。fc4版本89条定向双后端回放已有`F_BIN_RM_TYPE_S` raw `rm=101`见证：`fadd_s_static_rm5_decode_reject`，word `0x0020d1d3`、case-id `16394225216284458301`，初态`mstatus=0x0000000a00006600`（FS使能）、`fcsr=0`，真实解码为`ILLEGAL(raw_word)`；[89条case账本](../../../isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-valid-reg-group-replay-20260927/final-directed89/case-ledger.json)与[配对封包](../../../isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-valid-reg-group-replay-20260927/final-directed89/summary.json) `40296a3d…e499`。本轮从该完整初态派生`rm=110` word `0x0020e1d3`、新run-id，fc4 Isla实际两阶段与C++ AST/ret/102字段配对通过，[新见证](../../../isla/target/float-solve-evidence/fc4ce-rm6-directed-20260928/final-summary.json) `36aa0dad…2509`。两条列定输入不改56cc官方零覆盖结论，不覆盖其它clause，也不自动闭合17个源码义务门。组合73df隔离IR另对同rm=110物理word实际重跑Isla/新CPP通过（[新版本证](../../../isla/target/float-solve-evidence/num-elem-order-rm-eq-rm6-directed-20260928/summary.json) `ce61b42a…388d`），仍按定向而非官方分母记账。
4. **结构性/配置性不可达（不计缺口）**：Fcsr_RM_Fatal 臂、Zfinx/Zhinx/RV32Zdinx、RV32 拒译、vill、SEW>flen（flen=64）、扩展禁用 guard=false（运行配置固定启用）、`$else` C++ foreach 路径（IR 走 SYMBOLIC）、assert 防御臂。

### B. 数据通路层（元素循环、数值分支）：系统性未达——这是"分支全覆盖"不成立的真正原因

1. **vl=0 空转退休**：VFNCVTBF16_F_F_W（261/261）与 VFWCVTBF16_F_F_V（312/312）**全部 Retire case vl=0**，NaN 规范化、非精确舍入、flags 累计、掩码抑制等元素级分支 **0 达到**（G12 实证）；VFMV 1560/1872 vl=0；VFMVFS 40/63；VFMVSF 565/1440；VFMERGE 2551/8784（6233 条 vl>0 已进元素路径）。
2. **操作数值域退化（标量同样存在）**：f 寄存器初值全 0，有效输入实际只有 +0.0 与 canonical qNaN 两值。由此：fp_minmax ±0 两臂、比较 lt=true 侧、D 版 NaN 三臂、feq 的 sNaN→NV 路径（sNaN 样本只落 fle/flt）、±inf 操作数、非精确/溢出/次正规真臂、fdiv 非零除数（全部见证 0/0）——**均未达**（G3/G4/G5/G7/G8）。
3. **helper 内部分支 verdict 层不可区分**：softfloat extern、fcvtmod_helper 14 分支、roundToInt、fclass 10 类位图值、fflags 输出维度 cases.tsv 未记录。回放包含 102 字段 post 状态，可从此补 fflags/rd 维度对账。
4. **生成器维度单调**：实际枚举维度 = (特权, FRM, 寄存器编号, rm 编码, 部分向量 guard)；操作数值、vl、vstart、vill、vta 维度缺失或恒 0。

### C. 口径修正（相对既有表述）

- "gen 内 Illegal = rm 保留值"应更正为 **fcsr.FRM 保留值**（指令 rm 编码在 gen 中全部合法）。
- direct-negative 归因定论 **FS=Off**（非 rm 保留编码）；cases.tsv 将负例 rm 标为 "rmm/rup" 是展示层误导。
- BF16 向量两指令译码要求 **SEW=16**（非 32；32/16 是 widen 侧 EEW 检查，本配置恒过）。
- `fdext_regs.sail:50` nan_unbox 在当前树已改 ite（不再构成控制流分支），unbox 两臂结论仅适用 IR 56cc69a4 及更早。

## 各组报告索引

| 组 | clause | 报告 | 未达控制流分支 |
| --- | --- | --- | --- |
| G1 | FLEQ/FLTQ/FMINM/FMAXM ×D/H/S (12) | G1-scalar-quiet-cmp-minmax.md | 0 |
| G2 | FLI/FROUND/FROUNDNX/FCVTMOD (10) | G2-fli-fround-fcvtmod.md | 16（10 guard=false 配置性 + 6 rm=101/110） |
| G3 | FCVT_BF16_S/FCVT_S_BF16 (2) | G3-scalar-bf16.md | 0（配置性除外）；数据域缺口大 |
| G4 | F_BIN_F_TYPE_D/H、F_BIN_TYPE_F_S (3) | G4-bin-f-signj-minmax.md | 0；±0/lt=true/D-NaN 臂未达 |
| G5 | F_BIN_RM_TYPE_D/H/S (3) | G5-bin-rm.md | rm=101/110 译码失败；fdiv 见证全 0/0 |
| G6 | F_MADD_TYPE_D/H/S (3) | G6-madd.md | rm=5/6 编码；数值子分支不可判 |
| G7 | 比较/fclass/fmv (10) | G7-cmp-fclass-fmv.md | 0 控制流；D 无 NaN 输入、feq 无 sNaN |
| G8 | F_UN_RM_FF_TYPE_D/H/S (3) | G8-un-rm-ff.md | rm=101/110（594 case 零覆盖）；D 源无 NaN 输入 |
| G9 | F_UN_RM_FX_TYPE_D/H/S (3) | G9-un-rm-fx.md | rm 编码缺口；helper 越界路径不可判 |
| G10 | F_UN_RM_XF_TYPE_D/H/S (3) | G10-un-rm-xf.md | rm=5/6 编码；RV32/Zfinx 配置域外 |
| G11 | VFMV/VFMERGE/VFMVFS/VFMVSF (4) | G11-vfmv-vfmerge.md | vill、vta=1、结构性路径；Illegal 100% 归因 |
| G12 | VFNCVTBF16/VFWCVTBF16 (2) | G12-vector-bf16.md | vill、译码使能链；Retire 全 vl=0 数据通路 0 达 |

## 定向补例清单（下一轮）

1. raw 负例：fc4已补`F_BIN_RM_TYPE_S`的rm=101/110两值；其它rm指令家族仍须补保留编码并分别绑定IR/配置/源码和双后端，官方56cc分母保持零覆盖。
2. 数值域：f 寄存器预置 ±0 对、有限数对（lt 两侧）、boxed sNaN/qNaN 位模式、±Inf、次正规、溢出界值（如 0x477f_xxxx/0x4780_0000）、负数、非零除数/被除数。
3. 向量：vl>0 与 vl<vlmax（重点 BF16 两 clause）、vstart∈(0,vl)、vill=1、vta=1、FS=Off 正向 case。
4. 对账维度：从回放包 post 状态补 fflags/rd 输出维度，使 helper 内部分支可判。
5. 上述补例走定向测试通道记账，不与官方求解完整符号输入域混淆。

## 与源码义务门的关系

本核账把"数据通路分支未达"（尤其 BF16 向量 vl=0 空转、标量值域两值退化）确认为 `source_branch_closed=false` 17 类义务之外的一类独立缺口事实：即使 20 个未完目标全部完成求解，在当前生成器维度下元素级数值分支仍不会被官方产物覆盖。补例须走定向通道。
