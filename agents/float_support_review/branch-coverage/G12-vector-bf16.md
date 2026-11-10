# G12 分支覆盖对照：VFNCVTBF16_F_F_W、VFWCVTBF16_F_F_V

- 数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/{distribution.md,cases.tsv}`（57 目标官方产物，IR 56cc69a4），逐 case 过滤 `$2=="zVFNCVTBF16_F_F_W"` / `$2=="zVFWCVTBF16_F_F_V"`，并逐 case join 两个单 clause run 的 replay 包 `single-56cc-20260927-014615-{20-vfncvtbf16_f_f_w,21-vfwcvtbf16_f_f_v}/stage/output/rv64_z*.json` 的 `isa-state`（mstatus/vl/vstart/vtype/fcsr）、`isa-state-post` 与 `terminals`（phase/function）。
- 源码基线：`sail-riscv/model/extensions/bfloat16/{zvfbfmin_insts,zfbfmin_utils}.sail` 与 `extensions/V/{vext_fp_utils_insts,vext_utils_insts,vext_control,vext_regs}.sail`、`extensions/FD/{fdext_control,softfloat_symbolic_f32}.sail`。行号以当前工作树（SYMBOLIC 变体，即 IR 编译路径）为准；与产物 IR 的关系见[版本注记](#版本注记)。
- 两条指令译码均无 rm 字段（VFUNARY0 编码，funct5=11101/01101），舍入模式恒取 `fcsr[FRM]`（zvfbfmin_insts.sail:20,119）；**FRM∈{5,6,7}（含 DYN）由 `valid_fp_op` 拒绝**（vext_fp_utils_insts.sail:19-21），这是 Zvfbfmin 对这两条指令"不允许 DYN"约束的模型落点。
- 归因口径：按源码 guard 求值顺序（译码 `when` → `illegal_fp_variable_width` OR `valid_reg_overlap` → `init_masked_result` Err）**首个命中归类，多因素不重复计数**；多因素重叠的完整维度另在维度小结标注。terminals 佐证：两 clause 各 3 条 direct-negative 停在 `phase=encode/zencdec_forwards`，其余全部进入 `phase=execute/zisarch_solve_wrapper`。
- fcsr 列解析：frm=fcsr[7:5]，`32'h0000_00a0`→5、`0xc0`→6、`0xe0`→7；**rm/fcsr 两列同时为空**表示该 case 的 legacy isa-state 不含 fcsr（见归因表"FRM 符号自由"行）。
- run 配置 VLEN=128（IR `zvlen_exp=7`）、ELEN=64；`get_start_element` 越界阈值 = 2^(3+7-4)-1 = **63**。

---

## VFNCVTBF16_F_F_W（1119 = 1116 gen + 3 direct-negative；Illegal=858, Retire=261）

### Illegal 归因表（858 例逐类，合计核验 858）

| 类别 | 数量 | 源码分支 | 归因与特征 | 证据 case-id |
| --- | ---: | --- | --- | --- |
| E3：FRM=5/6/7 固定值 | 244 | zvfbfmin_insts.sail:28-30 → vext_fp_utils_insts.sail:19-21,43 | 指令无 rm 字段，`fcsr[FRM]`∈{5,6,7} → `valid_fp_op` false → `Illegal_Instruction`。frm5=61（fcsr=0xa0）、frm6=122（0xc0）、frm7=69（0xe0） | 328(frm5,mfrac4,v14,v3)、353(frm5,m4)、193(frm5,m8)、67(frm6)、200(frm7,m4,v0,v0) |
| E5：源/目标组对齐或重叠违规 | 219 | vext_utils_insts.sail:73-88（经 zvfbfmin_insts.sail:29） | 窄化指令 vs2 按 widen EMUL=2×LMUL 分组：未按组对齐（如 m1 时 vs2 奇数）120 例；vd 与 vs2 组重叠位置违规（vd 落在 vs2 组非最低段）54 例（首命中口径；两维度叠加已并入） | 315(m1, v1,v0：vd=v1 落 vs2 组 v0-v1 最高段)、41(m1, v0,v1：vs2=v1 未按 m2 对齐)、939(m1, v29,v28)、558(m2, v1,v16) |
| E6：vstart>63 | 201 | zvfbfmin_insts.sail:43-46 → vext_utils_insts.sail:276-287,303-306 | guard 全过后 `init_masked_result` 内 `get_start_element` 返回 Err → Illegal。vstart=0x8000_0000_0000_0000 为主（约 196），另有 0x4000.../0x100... 等零星高位值 | 925(mfrac2, v6,v5)、318(mfrac4, v1,v31)、857(m1, v16,v2) |
| E2：vd=v0 且 vm=1 | 68 | vext_utils_insts.sail:45-48（`valid_rd_mask`） | 未掩码目标组与 v0 冲突；注：这批中另有 vstart>63/frm 保留等叠加因素，按首命中归此 | 674(m2, v0,v0)、662(mfrac4, v0,v4)、681(mfrac4, v0,v4) |
| E4：LMUL=8 | 63 | vext_utils_insts.sail:23-25（`valid_eew_emul(32, LMUL_pow+1)` EMUL_pow≤3） | LMUL=8 时 widen 侧 EMUL=16 寄存器>8 → 非法；该组 vl 读回非 0（≤64）但仍在 execute guard 被拒 | 469、370(m8, v31,v1)、443(m8, v20,v4) |
| FRM 符号自由（isa-state 无 fcsr） | 60 | 同 E3 分支（符号输入侧） | legacy isa-state 缺 fcsr 键 → pre-state 中 fcsr 保持符号（target.rs `reg_list` 主动符号化 + 测试 `complete_pre_state_keeps_arbitrary_fcsr_and_mstatus`），存在 FRM∈{5,6,7} 的 illegal 路径，replay 取到 Illegal；tsv 中表现为 rm/fcsr 列为空 | 237(m2, v0,v4)、96(mfrac4, v0,v17)、52(mfrac2, v0,v0) |
| D2：SEW≠16 译码失败 | 3 | zvfbfmin_insts.sail:16 encdec `when get_sew()==16` | direct-negative：sew=8×2、sew=32×1；`when` 不满足 → 位模式失配，terminals 记 phase=encode、Pattern match failure | case 1(s8,m1)、2(s8,m1)、3(s32,m1)，均为 `v0, v0, v0.t` |

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id | case 数 |
| --- | --- | --- | --- | --- | --- |
| 译码 guard true 侧（Zvfbfmin&Zve32f&F 使能 + SEW=16） | zvfbfmin_insts.sail:16（使能链 zvfbfmin:9→vext_control.sail:18→fdext_control.sail:18） | 可译码为 VFNCVTBF16 | 达到 | 全部 1116 gen（phase=execute） | 1116 |
| 译码 guard SEW≠16 失配侧 | zvfbfmin_insts.sail:16 | SEW=8/32 时编码保留 → 非法 | 达到 | direct-negative 1/2/3 | 3 |
| 译码 guard 使能链 false（mstatus.FS=Off 等） | zvfbfmin_insts.sail:9-16 | Zvfbfmin 关闭 → 不可译码 | **未达** | 全部 case mstatus.FS∈{01,10} | 0 |
| execute guard `illegal_fp_variable_width` ∥ `valid_reg_overlap` 为真 → Illegal | zvfbfmin_insts.sail:28-30 | 五个 OR 子条件（vill/vd-v0/FRM/EEW-EMUL）+ 组重叠 | 达到 | 见归因表 E2/E3/E4/E5 及 FRM 符号自由行 | 654 |
| ├ valid_vtype（vill=1） | vext_utils_insts.sail:31-33 | vtype[vill]=1 → 非法 | **未达** | json vtype∈{0x8,0x9,0xa,0xe,0xf…} bit63=0 | 0 |
| ├ valid_rd_mask false（vm=1,vd=v0） | vext_utils_insts.sail:45-48 | 目标组与掩码寄存器 v0 冲突 | 达到 | 674/662/681 | 68 |
| ├ valid_fp_op FRM 保留（5/6/7） | vext_fp_utils_insts.sail:16-22 | 无 rm 字段指令读 FRM，DYN/保留非法 | 达到 | 328/67/200 等（frm5/6/7 全达） | 244+60(符号) |
| ├ valid_eew_emul false（LMUL=8） | vext_utils_insts.sail:23-25 | widen EMUL=16>8 非法 | 达到 | 469/370/443 | 63 |
| └ valid_reg_overlap false（对齐/重叠） | vext_utils_insts.sail:79-87（窄化走 rs_pow>rd_pow 臂 :85-87） | vs2 组对齐 + vd 落 vs2 组最低段 | 达到 | 315/41/939/558 | 219 |
| `assert(SEW==16)`/`assert(LMUL_pow_widen<=3)` | zvfbfmin_insts.sail:32-33 | 不变式（guard 后恒真） | 达到（恒真） | 全部 Retire | 261 |
| `init_masked_result` Err → Illegal（vstart 越界） | zvfbfmin_insts.sail:43-46 → vext_utils_insts.sail:276-287,303-306 | vstart>63 → get_start_element Err | 达到 | 925/318/857 | 201 |
| `init_masked_result` Ok → mask 计算：tail（i>vl-1，vl=0 全尾） | vext_utils_insts.sail:323-336 | vl=0 → 全元素 tail，mask 全 0 | 达到 | 全部 Retire（vl 读回全 0） | 261 |
| ├ prestart（vstart>0 且 vl>0） | vext_utils_insts.sail:319-322 | vstart 以下元素保留 | **未达** | vl 恒 0；vstart 仅 0 或 >63 | 0 |
| ├ inactive body（vm=0 掩掉、vl>0） | vext_utils_insts.sail:337-343 | 掩码非活动元素 | **未达** | vl=0 无 body 段 | 0 |
| ├ active body（mask[i]=1） | vext_utils_insts.sail:344-347 | 活动元素 | **未达** | 同上 | 0 |
| `assert_vector_num_elem`（num_elem≤vlen 分档） | vext_utils_insts.sail:301 → vext_control.sail:248-259 | SEW16 下 num_elem∈{8..64}≤128 恒真 | 达到（恒真） | 全部 | 1119 |
| foreach 元素循环 `riscv_f32ToBF16`：NaN 臂（→canonical_NaN_bf16） | zvfbfmin_insts.sail:50-51 → softfloat_symbolic_f32.sail:190 | F32 NaN → 规范化 BF16 qNaN | **语义未达** | SYMBOLIC 版对每个槽位无条件求值，但 mask 全 0 时无活动元素承载语义（post fflags=0、vd 保持） | 0(有效) |
| foreach 非 NaN 臂（`fp32_to_bf16` 舍入 + inexact/NV flags） | softfloat_symbolic_f32.sail:188-190 + ieee_bf16_from_f32_exceptions | 正常舍入与 flags 累计 | **语义未达** | 同上 | 0(有效) |
| `ite(mask[i]==1, lane_flags, 0)` 抑制臂 | zvfbfmin_insts.sail:53 | 掩掉元素不累计 flags | 达到（false 侧） | 全部 Retire（fflags 恒 0） | 261 |
| `vector_select_masked`（isla_vector_select） | zvfbfmin_insts.sail:55；vext_utils_insts.sail:383-387 | 按 mask 选择写回值 | 达到 | 全部 Retire（选回 initial_result=vd 原值） | 261 |
| `accrue_fflags`+`write_vreg`+`set_vstart(0)`+RETIRE | zvfbfmin_insts.sail:56-60 | 正常完成路径 | 达到 | 1003（post vstart=0,fcsr 保持 0x60, vl=0） | 261 |

### 未达分支

1. `valid_vtype` false（vill=1，vext_utils_insts.sail:31-33）：无任何 case 设置 vill。
2. 译码使能链 false（mstatus.FS=Off/misa.F=0，fdext_control.sail:18）：全部 case FS∈{01,10}。
3. **元素级语义全未达**：全部 Retire case vl=0 → body 段为空 → mask 全 0 → `riscv_f32ToBF16` 的 NaN 规范化臂、非精确舍入臂、NV/IX flags、vm 掩码对活动元素的抑制、prestart/inactive 分类、`write_vreg` 实际数据通路均无活动元素承载；Retire 只证明了"guard 通过 + 空体完成 + vstart 清零"。
4. vstart∈[1,63]（合法非零 prestart）未达：vstart 取值只有 0 与 >63 两类。
5. `__isla_use_extra_ops` 两条实现路径（vext_utils_insts.sail:365-376）：IR 编译常量二选一，另一路不可达（结构性）。
6. `valid_eew_emul` 其余子条件（EEW<8 / EEW>elen / EMUL_pow<-3）：SEW_widen=32、elen=64、LMUL≥frac2 时结构不可达。

### 维度小结

- 261 Retire：FRM 0-4 全达（184/15/21/27/14）；vm=0/1（123/138）；LMUL m1/m2/m4/mf2/mf4 全达（45/33/21/81/81），**无 m8**（m8 必非法）；vl、vstart 恒 0；M/S/U 均匀。
- 858 Illegal 中 FRM 类（244 固定+60 符号自由）占 35%；E5 组对齐/重叠 25%；E6 vstart 越界 23%；LMUL8 与 vd=v0 合计 15%；SEW≠16 仅靠 3 条 direct-negative。vill、FS=Off 两类 0 覆盖。
- tsv `vl` 列：replay 后读回值，除 m8 组（≤64）外恒 0；`vill` 列恒 0，与 json vtype 一致。

## VFWCVTBF16_F_F_V（1308 = 1305 gen + 3 direct-negative；Illegal=996, Retire=312）

### Illegal 归因表（996 例逐类，合计核验 996）

| 类别 | 数量 | 源码分支 | 归因与特征 | 证据 case-id |
| --- | ---: | --- | --- | --- |
| E5：组对齐/重叠违规 | 288 | vext_utils_insts.sail:73-88（经 zvfbfmin_insts.sail:128） | 宽化指令 vd 按 EMUL=2×LMUL 分组：对齐失败 138；vd 与 vs2 组非"最高段重叠"的违规 123 | 316(m1, v1,v0：vd=v1 组未按 m2 对齐)、385(m1, v1,v3)、1094(mfrac2, v2,v2：frac LMUL 下 vs2==vd 非 widen 合法形) |
| E6：vstart>63 | 250 | zvfbfmin_insts.sail:142-145 → vext_utils_insts.sail:276-287 | 同 E6 机制；vstart=0x8000... 约 234 例，含最小越界值 0x40(=64) 1 例 | 674、906(m4, v8,v4)、1207(m4, v16,v20) |
| E3：FRM=5/6/7 固定值 | 244 | zvfbfmin_insts.sail:127-129 → vext_fp_utils_insts.sail:19-21 | 指令自身转换不使用 rm（bf16→f32 精确），但 guard 仍查 `valid_fp_op` → FRM∈{5,6,7} 非法。frm5=55、frm6=130、frm7=67 | 330(frm5)、352(frm5)、179(frm7,m8)、200(frm7) |
| E2：vd=v0 且 vm=1 | 85 | vext_utils_insts.sail:45-48 | 同 E2 | 668(mfrac2, v0,v0)、1114(m4, v0,v4)、200(m4, v0,v0) |
| E4：LMUL=8 | 63 | vext_utils_insts.sail:23-25 | 同 E4 | 468、366(m8, v31,v1)、443(m8, v20,v4) |
| FRM 符号自由（isa-state 无 fcsr） | 63 | 同 E3 分支（符号输入侧） | 同前述机制 | 41(m1, v0,v1)、236(m2, v0,v4)、87(mfrac4, v0,v17) |
| D2：SEW≠16 译码失败 | 3 | zvfbfmin_insts.sail:115 encdec `when` | direct-negative：sew=32×1、sew=8×2（m4/m1） | case 1(s32)、2(s8,m4)、3(s8,m1) |

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id | case 数 |
| --- | --- | --- | --- | --- | --- |
| 译码 guard true / SEW≠16 失配 / 使能链 false | zvfbfmin_insts.sail:115 | 同 VFNCVT 对称 | 达到/达到/未达 | 1305 gen；direct-negative 1/2/3 | 1305+3 |
| execute guard 五子条件 + 组重叠 | zvfbfmin_insts.sail:127-129 | 同 VFNCVT，重叠走 `rs_pow<rd_pow` 臂（vext_utils_insts.sail:82-84，widen 合法形=vs2 组在 vd 组最高段） | 达到 | 见归因表 E2/E3/E4/E5 及 FRM 符号自由行 | 743 |
| ├ vill / FRM / vd-v0 / EMUL | 同前表 | — | 未达/达到(392)/达到(85)/达到(63) | — | 0/392/85/63 |
| `init_masked_result` Err（vstart>63）→ Illegal | zvfbfmin_insts.sail:142-145 | 同 VFNCVT | 达到 | 674/906/1207 | 250 |
| `init_masked_result` Ok：tail 臂（vl=0） | vext_utils_insts.sail:323-336 | 同 VFNCVT | 达到 | 全部 Retire | 312 |
| ├ prestart / inactive / active | vext_utils_insts.sail:319-322/337-343/344-347 | 同 VFNCVT | **均未达** | vl 恒 0 | 0 |
| foreach `bf16_to_f32` NaN 臂（→`canonical_NaN_S`+NV） | zvfbfmin_insts.sail:150 → zfbfmin_utils.sail:16-18 | BF16 NaN（含 sNaN 判定 `mant[6]==0`）→ 规范化 F32 qNaN + nvFlag | **语义未达** | mask 全 0 无活动元素 | 0(有效) |
| foreach `bf16_to_f32` 非 NaN 臂（`v @ zeros(16)` 精确扩展） | zfbfmin_utils.sail:18 | BF16→F32 恒精确（指数/尾数拓宽） | **语义未达** | 同上 | 0(有效) |
| `ite(mask[i]==1,…)` 抑制 / `vector_select_masked` / `accrue_fflags` / `write_vreg` / `set_vstart(0)` / RETIRE | zvfbfmin_insts.sail:152-159 | 空体完成路径 | 达到 | 1001（post vstart=0, fcsr 保持 0x60） | 312 |

### 未达分支

与 VFNCVTBF16 对称：vill、使能链 false、元素级活动路径（NaN/sNaN 规范化、NV flag、掩码抑制活动元素、prestart/inactive）、vstart∈[1,63]、`__isla_use_extra_ops` 另一路、`valid_eew_emul` 结构不可达子条件。另注：`bf16_to_f32` 的 is_inf/is_subnorm 显式分类仅存在于 $else 非 SYMBOLIC 版（zfbfmin_utils.sail:23-30），IR 编译路径（SYMBOLIC 版 :14-19）用 `eq_anything`/`ite` 无分支表达，不构成 IR 层分支缺口。

### 维度小结

- 312 Retire：FRM 0-4 全达（225/17/30/27/13）；vm=0/1（144/168）；LMUL m1/m2/m4/mf2/mf4（87/42/33/75/75）全达、无 m8；vl/vstart 恒 0。
- 996 Illegal：E5 占 29%（宽化比重叠主导，与窄化对称）；FRM 类 31%；E6 25%；SEW≠16 仅 3 例 direct-negative。vill、FS=Off 0 覆盖。
- 与 VFNCVT 的结构性差异：重叠合法方向相反（widen 要求 vs2 在 vd 组**最高**段，narrow 要求 vd 在 vs2 组**最低**段，vext_utils_insts.sail:82-87 两臂分别被两 clause 达到）；mfrac2 时 vfwcvt `vs2==vd` 非法而 vfncvt 合法（1094 vs 905，均有 case 佐证）。

## 全组结论

1. **两条 clause 的全部 Illegal 均可归因到源码 guard，无未解释残留**：译码层 `when get_sew()==16`（SEW≠16，仅 direct-negative 覆盖）+ execute 层五子条件 OR 组重叠 + `init_masked_result` 的 vstart Err。Illegal 大头不是 SEW 检查（任务假设的"ncvt 要求 SEW=32"不成立：两条指令都要求 **SEW=16**，32/16 是 widen 侧的 SEW_widen，仅在 `valid_eew_emul` 里作为 EEW≤elen 检查，本配置恒过），而是 **FRM∈{5,6,7}（含 DYN）、寄存器组对齐/重叠、vstart 越界** 三者。
2. **77%/76% 的 Illegal 占比主要成因**：生成器在 rm/寄存器编号/vstart 维度采样出大量非法组合（FRM 类 ~31-35%、E5 ~25-29%、E6 ~23-25%），加上 harness 对 126/126 条不约束 fcsr（符号 FRM）判为 Illegal。
3. **guard 覆盖完整度**：`illegal_fp_variable_width` 4 子条件中 vill 未达、其余 3 个达到；`valid_reg_overlap` 对齐与两臂重叠方向均达到；`get_start_element` Err 达到；译码使能链 false 未达。
4. **语义层（Retire 侧）覆盖接近空壳**：全部 Retire case vl=0 → 元素循环无活动元素 → NaN 规范化（`riscv_canonical_nan_bf16`/`canonical_NaN_S`）、非精确舍入、flags 累计、掩码抑制等值域分支全部未达。**"分支全覆盖"不成立**：控制流分支约 8/10 达到，数据通路分支 0 达到。这与 G3 标量 BF16（输入恒 +0.0/qNaN 两值）同为"状态生成维度单一"问题，建议后续 vl>0、vl<vlmax、vstart∈(0,vl)、vill=1、FS=Off 定向补例。
5. tsv 证据列局限：无 vstart 列（本报告由 replay json 补齐）；rm/fcsr 列空值需区分"FRM=7"（fcsr=0xe0）与"fcsr 未约束"（两列皆空）两种含义。

## 版本注记

- **产物 IR**：`rv64d.ir` sha256 `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`，完整副本存档于两 run 的 `stage/rv64d.ir`；`zvlen_exp=7`（VLEN=128）、`zelen_exp=6`（ELEN=64）。
- **当前工作树**：`isla/rv64d.ir` sha256 `d0123541…`（9-26 14:37 重建）≠ 产物 hash。两 IR 均由 SYMBOLIC 变体编译（都含 `isla_init_mask`/`isla_vector_select`、`riscv_f32ToBF16` 4 处、`illegal_fp_variable_width` 调用 14 处），本报告全部行号在两版本下同构成立。
- **sail-riscv 子模块**：HEAD=`f8ce849`，工作树 23 文件未提交修改，其中 `model/extensions/bfloat16/zvfbfmin_insts.sail` 的 +96 行即新增两条指令的 `$ifdef SYMBOLIC execute`（guard/循环结构与 `$else` 原版一致）及 assembly 分隔符微调——产物 IR 56cc69a4 即由该工作树形态编译；本报告引用的 SYMBOLIC 分支行号（19-61/118-160）与产物 IR 对应源一致，非符号版（63-104/162-201）guard 语义相同。
- tsv `vl` 列为 replay 后读回（多数 0，m8 组 ≤64=vlmax）；`vill` 列恒 0 与 json `vtype` 一致；`rm` 列对 frm=6 显示 `dyn` 系展示层近似，归因一律以 fcsr 数值为准。

### 复现命令

```sh
T=isla/target/float-solve-evidence/branch-coverage-distribution-20260928/cases.tsv
# 特征组合汇总（列序：verdict|rm|vl|vill|sew|lmul|fcsr）
awk -F'\t' '$2=="zVFNCVTBF16_F_F_W"{print $6"|rm="$8"|vl="$10"|vill="$11"|sew="$12"|lmul="$13"|fcsr="$14}' $T | sort | uniq -c | sort -rn
# 归因：join replay json isa-state（mstatus/vl/vstart/vtype/fcsr）+ ins 解析 vd/vs2/vm，
# 按译码 when→illegal_fp_variable_width(4 子条件)→valid_reg_overlap→get_start_element 顺序首命中归类；
# terminals phase 佐证 encode(3)/execute(1116|1305)。
```
