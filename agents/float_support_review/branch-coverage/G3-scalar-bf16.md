# G3 分支覆盖对照：FCVT_BF16_S、FCVT_S_BF16

- 数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/{distribution.md,cases.tsv}`（57 目标官方产物，IR 56cc69a4，run `official-56cc-long-20260927-064348`，逐 case 过滤 `$2=="zFCVT_BF16_S"` / `$2=="zFCVT_S_BF16"`），并逐 case 复核 replay 包 `official-56cc-long-20260927-064348/stage/output/rv64_z{FCVT_BF16_S,FCVT_S_BF16}.json` 的 `isa-state`（rs1 初值、fcsr、mstatus）与 `terminals`（phase/function）。
- 源码基线：`sail-riscv/model/extensions/bfloat16/zfbfmin_insts.sail`、`zfbfmin_utils.sail` 与 `extensions/FD/{fext_insts,fdext_regs,softfloat_symbolic_f32}.sail`、`core/ieee_fp_exceptions.sail`。与 IR 56cc69a4 构建源一致性见[版本注记](#版本注记)。
- rm 有效性链路（与 G2 相同）：`fext_insts.sail:31-38` `encdec_rounding_mode` 值域仅 000/001/010/011/100/**111(DYN)**，0b101/0b110 在指令 rm 字段**无映射**→译码层失败；`fext_insts.sail:49` `valid_rounding_mode`（FRM 排除 0b101/0b110）；`fext_insts.sail:51-63` `select_instr_or_fcsr_rm`（dyn 时读 `fcsr[FRM]`，非法→按 `fcsr_rm_reserved_behavior` 取 `Fcsr_RM_Illegal` 的 `None()`，`config.json.in:53`、`platform_config.sail:65-68,95`）。
- fcsr 列解析：frm = fcsr[7:5]，`32'h0000_00a0`→5、`0xc0`→6、`0xe0`→7。
- 通用口径：run 配置固定启用 Zfbfmin/F/Zicsr，`encdec` 的 `when currentlyEnabled(Ext_Zfbfmin)`（zfbfmin_insts.sail:11,18,43，经 fdext_control.sail:18 检查 misa.F/mstatus.FS/Zicsr）只测到 true 侧；guard=false 译码失败分支两 clause 均未测，统一在未达分支小节计一次。

---

## FCVT_BF16_S（1873 case = 1872 gen + 1 direct-negative；Illegal=433, Retire=1440）

### Illegal 归因表（433 例逐类）

| 类别 | 数量 | 源码分支 | 归因与特征 |
| --- | ---: | --- | --- |
| gen 执行期 Illegal：dyn+FRM=5 | 144 | zfbfmin_insts.sail:23（经 fext_insts.sail:57-61 `None()`） | 指令 rm=0b111(DYN)，fcsr=`32'h0000_00a0`；`select_instr_or_fcsr_rm` 读 FRM=0b101 保留→`Fcsr_RM_Illegal` 返回 `None()`→`Illegal_Instruction`。terminals 记录 phase=`execute`。代表 case 62/806/1154 |
| gen 执行期 Illegal：dyn+FRM=6 | 144 | 同上 | fcsr=`0xc0`（FRM=0b110）。代表 case 227/1575 |
| gen 执行期 Illegal：dyn+FRM=7 | 144 | 同上 | fcsr=`0xe0`（FRM=0b111）。代表 case 62/1554 |
| direct-negative 译码失败 | 1 | zfbfmin_insts.sail:16-18 encdec 模式 | case 1：terminals 记 phase=`encode`、function=`zencdec_forwards`、detail=`Pattern match failure`、mapping-source=`zfbfmin_insts.sail 16:24-16:48`，即 32 位编码不满足本子句位模式（含 rm=0b101/0b110 无映射情形）→非 encodable→非法。原始破坏位型未保留在证据中 |

- **归因结论**：433 个 Illegal 全部落在 **RM 有效性 guard**（dyn+FRM 保留值→执行期 None 臂；编码失配→译码期），与 NaN 规范化、BF16 扩展使能 guard 无关。NaN 规范化路径在 Retire case 内通过「未 box 寄存器→`nan_unbox`→canonical NaN」达到（见下表），不产生 Illegal。
- **非法路径枚举完备性**：FRM 8 个取值中 3 个保留值（5/6/7）全部有 case、4 个合法值（0-4）全部 Retire；特权 U/S/M 三档在 Illegal 桶均有分布；指令 rm 字段 8 个编码中 6 个可编码值全达，0b101/0b110 不可编码侧仅由 direct-negative 1 例代表（机制粒度所限，非分支缺口）。执行期非法分支**完备覆盖**。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard `currentlyEnabled(Ext_Zfbfmin)`（true 侧） | zfbfmin_insts.sail:11,16-18 | Zfbfmin&F 启用才可译码 | 达到 | 1872 gen 全部译码通过（IR 中 `jump @not(...) goto`，IR:133615 附近同构） |
| encdec 位模式失配（含 rm=0b101/0b110 无映射） | zfbfmin_insts.sail:16-18；fext_insts.sail:31-38 | 非 FCVT_BF16_S 编码→译码失败 | 达到（代表 1 例） | direct-negative case 1 |
| execute `None() => Illegal_Instruction()` | zfbfmin_insts.sail:22-23 | dyn+FRM∈{5,6,7}→非法 | 达到（432） | 62/227/806/1154/1554/1575 等 |
| execute `Some(rm')`→转换+accrue+写回+RETIRE | zfbfmin_insts.sail:24-31 | 正常路径 | 达到（1440） | 见下三行 |
| `select_instr_or_fcsr_rm` 静态 rm 臂（直接返回 instr_rm） | fext_insts.sail:52-53,63 | rm∈{rne,rtz,rdn,rup,rmm} | 达到（720=5 rm×144） | rne=48/1177、rtz=521/1377、rdn=110/1434、rup=683/1498、rmm=693/765 |
| `select_instr_or_fcsr_rm` dyn+FRM 合法臂 | fext_insts.sail:54-56 | FRM∈{0..4}→Some(FRM) | 达到（720=5 FRM×144） | frm0=936/1679、frm1=828/1103、frm2=486/1104、frm3=68/1859、frm4=3/211 |
| `select_instr_or_fcsr_rm` `Fcsr_RM_Fatal` 臂 | fext_insts.sail:57-59 | 保留值触发 reserved_behavior 异常 | **未达** | 配置=`Fcsr_RM_Illegal`（config.json.in:53），IR 存在跳转但配置不可达 |
| `rF_or_X_S` 取 `F_S` 臂 | fdext_regs.sail:376-381 | hartSupports(Ext_F)=true 读 F 寄存器 | 达到 | 全部 gen（isa-state 含 f 寄存器足迹） |
| `rF_or_X_S` 取 X 臂（Zfinx 无 F） | fdext_regs.sail:381-382 | 从整数寄存器读 | **未达** | 本 hart 配置 Ext_F=true，配置不可达 |
| `nan_unbox` box 命中臂（高位全 1→取低 32 位） | fdext_regs.sail:49-51 | rs1=`64'hffff_ffff_0000_0000`→f32=+0.0 | 达到（936） | 48/521/683/936 等 |
| `nan_unbox` 失配臂→`canonical_NaN_S` | fdext_regs.sail:49-51 | rs1=`64'h0000_0000_0000_0000`→f32=0x7fc00000 | 达到（936） | 110/1177/1679 等 |
| `riscv_f32ToBF16` NaN 臂（`ite(ieee_is_nan(a), 0x7fc0, raw)`） | softfloat_symbolic_f32.sail:190 | 输入 NaN→canonical BF16 NaN | 达到 | 即全部未 box case（输入恒为 canonical qNaN 0x7fc00000） |
| `riscv_f32ToBF16` 非 NaN 臂（raw=`fp32_to_bf16` 结果） | softfloat_symbolic_f32.sail:188-190 | 正常舍入转换 | 达到 | 即全部 box case（输入恒为 +0.0，5 种 rm 值全到达） |
| `fp32_to_bf16` 内部舍入分支（inexact/tie/overflow/subnorm） | ieee_fp_primops.sail:202（opaque 原语）+ieee_fp_exceptions.sail:718-730 阈值 ite | 按 rm 与输入分类 | **值域未达**（见未达分支） | 唯一非 NaN 输入为 +0.0（精确、无舍入差异） |
| `ieee_bf16_from_f32_exceptions` invalid(sNaN→NV) 真臂 | ieee_fp_exceptions.sail:929-934 | sNaN 输入置 NV | **未达** | 输入只有 qNaN/+0.0，无 sNaN |
| 写回 `F_BF16(rd)`=`wF_BF16`→`nan_box` | fdext_regs.sail:323-325,41 | 无内部分支 | 达到（1440） | 全部 Retire |

### 未达分支

1. `Fcsr_RM_Fatal` 臂（fext_insts.sail:58）：配置关闭，本 run 不可达（IR 内跳转存在）。
2. encdec guard=false 侧（mstatus.FS=Off/misa.F=0/Zicsr off→currentlyEnabled(Ext_Zfbfmin)=false）：全部 case 的 mstatus 仅 `0x...2000`(FS=01)/`0x...4000`(FS=10)，无 FS=00。
3. `rF_or_X_S` 的 X 臂（fdext_regs.sail:381，Zfinx-only hart）：配置不可达。
4. 值域性未达：非 NaN 输入恒 +0.0 → `fp32_to_bf16` 的非精确舍入/进位/tie/溢出路径无输入差异；`ieee_bf16_from_f32_exceptions` 的 overflow/underflow/inexact 真臂（ieee_fp_exceptions.sail:718-721 阈值比较）恒假；sNaN→NV 真臂未达。5 种 rm 虽全部作为参数到达，但仅区分了 NaN/+0 两类输入，未验证 rm 语义差。

### 维度小结

- 1872 gen = 13 个 rm 组合 × 144：静态 rm 5 种（×144）+ dyn×FRM{0..4}（×144）+ dyn×FRM{5,6,7}（×144）。144 ≈ 3 特权 × 2 box 维 ×（rd,rs1）identity 组合（全部 gen 去重后 346 个 (rd,rs1) 对、1151 个 (priv,rd,rs1,rm,box,fcsr) 完整组合）。
- **rs1 载荷低 32 位恒为 0x00000000**，唯一变化是高 32 位（box/未 box）→ 有效 f32 输入仅 2 个值：+0.0 与 canonical qNaN（经 nan_unbox 产生）。tsv 的 vl/sew/lmul 列为共享状态采样维度，与本指令控制流无关。
- Illegal 桶保留 box 维（144=2×72×特权）：源码 zfbfmin_insts.sail:21 先读 `F_or_X_S(rs1)`、:22 才查 rm，故 f 寄存器在非法 case 中仍被读取并记录——与 FCVT_S_BF16 形成对照（见下）。

## FCVT_S_BF16（1657 case = 1656 gen + 1 direct-negative；Illegal=217, Retire=1440）

### Illegal 归因表（217 例逐类）

| 类别 | 数量 | 源码分支 | 归因与特征 |
| --- | ---: | --- | --- |
| gen 执行期 Illegal：dyn+FRM=5 | 72 | zfbfmin_insts.sail:46-47（经 fext_insts.sail:57-61） | fcsr=`32'h0000_00a0`。代表 case 362 |
| gen 执行期 Illegal：dyn+FRM=6 | 72 | 同上 | fcsr=`0xc0`。代表 case 797 |
| gen 执行期 Illegal：dyn+FRM=7 | 72 | 同上 | fcsr=`0xe0`。代表 case 223 |
| direct-negative 译码失败 | 1 | zfbfmin_insts.sail:41-43 encdec 模式 | case 1，phase=`encode`、`zencdec_forwards` Pattern match failure（funct7/rs2=`0b01000_00_00110` 或 rm 字段任一位型失配） |

- 同 FCVT_BF16_S：全部 Illegal 归因于 RM 有效性 guard，执行期 3 个 FRM 保留值 + 3 特权完备覆盖，非 NaN 规范化/BF16 使能问题。
- **读写顺序交叉验证**：源码 zfbfmin_insts.sail:46-47 先做 rm 检查、:49 才读 `F_BF16(rs1)`。证据吻合——216 个 gen Illegal case 的 isa-state **只含 fcsr、完全不含 f 寄存器足迹**（rm 检查失败即返回，寄存器从未被读），而 FCVT_BF16_S 的 Illegal case 两者皆有。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard（true 侧） | zfbfmin_insts.sail:41-43 | Zfbfmin 启用 | 达到 | 1656 gen |
| encdec 位模式失配 | zfbfmin_insts.sail:41-43 | 非 FCVT_S_BF16 编码→译码失败 | 达到（代表 1 例） | direct-negative case 1 |
| execute `rm==None → return Illegal_Instruction()` | zfbfmin_insts.sail:46-47 | dyn+FRM∈{5,6,7} | 达到（216） | 223/362/797 等 |
| execute 正常路径 | zfbfmin_insts.sail:49-53 | 转换+accrue+写回+RETIRE | 达到（1440） | 见下 |
| `select_instr_or_fcsr_rm` 静态 rm 臂 | fext_insts.sail:52-53,63 | 5 种静态 rm | 达到（720） | rne=47/1172、rtz=511/1292、rdn=108/1347、rup=681/1415、rmm=685/755 |
| `select_instr_or_fcsr_rm` dyn+FRM 合法臂 | fext_insts.sail:54-56 | FRM∈{0..4} | 达到（720） | frm0=912/1474、frm1=911/1510、frm2=305/1632、frm3=989/1213、frm4=3/68 |
| `Fcsr_RM_Fatal` 臂 | fext_insts.sail:57-59 | 保留值→reserved_behavior | **未达** | 配置=Fcsr_RM_Illegal |
| `rF_BF16` box 命中臂（`v[flen-1..16]==ones()`→取低 16 位） | fdext_regs.sail:314-321 | rs1=`64'hffff_ffff_ffff_0000`→bf16=0x0000(+0.0) | 达到（720） | 47/511/912 等 |
| `rF_BF16` 失配臂→`canonical_NaN_BF16`(0x7fc0) | fdext_regs.sail:318-320 | rs1=`64'h0000_0000_0000_0000`→bf16=0x7fc0（qNaN） | 达到（720） | 108/1172/1474 等 |
| `bf16_to_f32` 非 NaN 臂（`v @ zeros(16)` 直通） | zfbfmin_utils.sail:16-18（SYMBOLIC 版） | +0.0→0x00000000，flags=0 | 达到 | 全部 box case |
| `bf16_to_f32` is_nan 臂（is_snan=false→canonical_NaN_S，无 NV） | zfbfmin_utils.sail:16,18 | qNaN 0x7fc0→0x7fc00000，flags=0 | 达到 | 全部未 box case |
| `bf16_to_f32` is_snan 臂（`nvFlag()` 置位） | zfbfmin_utils.sail:17-18 | sNaN（mant[6]=0）→NV | **未达** | 输入无 sNaN：box 臂恒送 0x0000、失配臂恒送 canonical qNaN |
| `bf16_to_f32` 非 SYMBOLIC 版的 is_inf 独立分支 | zfbfmin_utils.sail:24,29（`$else` 版） | Inf→`fmake_S(sign,ones(),zeros())` | **IR 外未达** | IR 为 SYMBOLIC 编译（$ifdef），此分支不进 IR；值域上也无 Inf 输入 case |
| 写回 `F_S(rd)`→`wF_S`→`nan_box` | fdext_regs.sail:345-349,41 | 无内部分支 | 达到（1440） | 全部 Retire |

### 未达分支

1. `Fcsr_RM_Fatal` 臂（配置关闭）；encdec guard=false 侧（同上，FS 恒∈{01,10}）。
2. `bf16_to_f32` is_snan 臂（zfbfmin_utils.sail:17-18）：需 boxed 寄存器携带 sNaN 载荷（低 16 位 exp=0xff 且 mant[6]=0），全部 case 载荷恒 0x0000 → NV 置位分支从未执行。
3. 值域性未达：bf16 有效输入仅 {+0.0, canonical qNaN} 两值，Inf/非零有限值/异号值无 case（SYMBOLIC 版无独立 Inf 分支，仅值域缺口；$else 版的 is_inf 分支则 IR 外未达）。
4. `bf16_to_f32_set_flags`（zfbfmin_utils.sail:36-39）为向量路径共用 helper，本标量 clause 不经其调用，不计入。

### 维度小结

- 1656 gen = 静态 5×144 + dyn×FRM{0..4} 5×144 + dyn×FRM{5,6,7} 3×**72**。Illegal 桶仅 72/组（约 Retire 桶一半）：box 维消失，因 rm 检查先于 `F_BF16(rs1)` 读、寄存器从未被读（isa-state 无足迹佐证）。全部 gen 去重 214 个 (rd,rs1) 对、942 个完整组合。
- rs1 两态：`0x0000_0000_0000_0000`（未 box→canonical qNaN）与 `0xffff_ffff_ffff_0000`（box→+0.0），各 720。
- rm 语义维度：同 FCVT_BF16_S，5 种 rm 全达但无数据维差异可区分。

---

## 版本注记（IR 56cc69a4 vs 当前工作树）

- IR=`target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/ir/rv64d_p1_unified.ir`（SHA256 前缀 56cc69a4）。与其构建源逐文件比对：`zfbfmin_insts.sail`、`zfbfmin_utils.sail`、`fext_insts.sail`、`ieee_fp_exceptions.sail`、`softfloat_symbolic_f32.sail`、`fdext_control.sail` 与当前工作树**完全一致**；`fdext_regs.sail` 有一处实质差异——IR 内 `nan_unbox` 为 `if .. then .. else`（fdext_regs.sail:50，IR:31244 起编译为 jump 分支），当前工作树改为 `ite(eq_anything(..), .., ..)`（符号 ite，消除控制流分叉）。两 case 桶已分别覆盖 box 命中/失配两臂，该改写不改变本文覆盖结论。
- `zfbfmin_utils.sail` 的 `$ifdef SYMBOLIC` 版 `bf16_to_f32` 属**未提交的工作树改动**，但 IR 已按 SYMBOLIC 编译生效（IR:101510 的 zbf16_to_f32 引用源位置 16:31/17:40/18:3 与工作树行号一一对应），因此本文按 SYMBOLIC 版枚举分支；`$else` 版仅作 IR 外对照。
- 上游提交 `4d7812e`（Add configuration option to handle reserved dynamic rounding modes, #1491）明确了 FRM 保留值=0b101/0b110/0b111 与静态保留 rm=0b101/0b110 的区分，与本文 Illegal 归因一致。另注：本模型 `encdec_rounding_mode` 将 DYN 映射为 **0b111**（fext_insts.sail:37，上游既有行为），0b110 在指令字段不可编码——与官方手册「rm=110=dynamic、111=reserved」的分配相反，值得单独核对（证据：case 828 的 `test-ins-encdec=32'h4486_f053`，bits[14:12]=111 且反汇编为 dyn）。

## 全组结论

1. **两 clause 的执行期控制流分支（跳转级）已全数达到**，除配置性不可达项（Fcsr_RM_Fatal 臂、guard=false 侧、Zfinx X 臂）外无缺口；FCVT_BF16_S 与 FCVT_S_BF16 各 433/217 个 Illegal **全部归因于 RM 有效性 guard**（dyn+FRM∈{5,6,7}→`None()`→`Illegal_Instruction`，zfbfmin_insts.sail:23 / :46-47），不是 NaN 规范化或 BF16 使能 guard；执行期非法枚举**完备**（3 个 FRM 保留值 × 3 特权全有 case），译码期非法由各 1 个 direct-negative 代表（粒度所限）。两 clause Illegal 数差异（432 vs 216）源于 identity 维度中 box 维是否保留（读序不同），并非覆盖能力差异。
2. **共同的主要覆盖缺口是输入值域退化**：rs1 载荷低位恒 0，有效输入仅 +0.0 与 canonical qNaN 两值（box 维经 nan_unbox/rF_BF16 两臂均达）。由此 sNaN→NV 分支（FCVT_S_BF16 的 `bf16_to_f32` is_snan 臂；FCVT_BF16_S 的 `ieee_bf16_from_f32_exceptions` invalid 臂）及一切非精确舍入/overflow/underflow 相关真臂**均未达**；5 种 rm 到达但无可区分数据。若目标是分支级全覆盖，需补 rs1 载荷维（sNaN、Inf、次正规、可入可舍尾数、溢出界值如 0x477f_xxxx/0x4780_0000、负数）。
3. 读写顺序的源码行序（BF16_S 先读 rs1 再查 rm；S_BF16 反之）被 isa-state 寄存器足迹独立印证，回放数据与源码控制流一致。
