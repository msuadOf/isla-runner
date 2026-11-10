# G2 分支覆盖对照：FLI_D/H/S、FROUND_D/H/S、FROUNDNX_D/H/S、FCVTMOD_W_D

- 数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/{distribution.md,cases.tsv}`（57 目标官方产物，IR 56cc69a4，run `official-56cc-long-20260927-064348`，逐 case 过滤 `$2=="z<clause>"`）。
- 源码基线：`sail-riscv/model/extensions/FD/zfa_insts.sail`（HEAD=IR 56cc69a4；工作树差异见[版本注记](#版本注记)，对本文 10 个 clause 的控制流分支无影响）。
- rm 有效性链路：`fext_insts.sail:49` `valid_rounding_mode`（排除 0b101/0b110）、`fext_insts.sail:51-63` `select_instr_or_fcsr_rm`、`fext_insts.sail:31-38` `encdec_rounding_mode`（值域仅 000/001/010/011/100/111，**0b101/0b110 无映射**→译码层失败）。保留值策略 `config.json.in:53` = `Fcsr_RM_Illegal`（`platform_config.sail:70-71,95`），即 fcsr.FRM 为保留值时返回 `None()`。
- fcsr 列解析：frm = fcsr[7:5]，如 `32'h0000_00a0`→frm=5。
- 通用口径：所有 run 的扩展使能固定开启，因此各 clause `encdec` 的 `when` guard 只测到 true 侧；guard=false（禁用 Zfa/D/Zfh）译码失败分支全组均未测，下文各表不再重复列出，仅在未达分支小节统一计一次。

---

## FLI_D（97 case = 96 gen Retire + 1 direct-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard `Ext_D & Ext_Zfa`（true 侧） | zfa_insts.sail:117 | 扩展启用才可译码 | 达到 | 96 个 gen 全 Retire |
| execute match 臂 0b00000（-1.0） | :124 | 写 -1.0 | 达到 | case 4/6/67 |
| execute match 臂 0b00001（min） | :125 | 最小正规范数 | 达到 | case 5/8/68 |
| execute match 臂 0b00010..0b11101（2^-16..65536.0 共 29 臂） | :126-153 | 常量表 | 达到（每臂 3 case） | 如 2^-16=case 7/10/69，65536.0=case 63/64/96 |
| execute match 臂 0b11110（+inf） | :154 | 写 +inf | 达到 | case 65/66/97 |
| execute match 臂 0b11111（canonical NaN） | :155 | 写 NaN | 达到 | case 2/3/13 |
| 写回 `F_D(rd)` + `RETIRE_SUCCESS` | :157-158 | 单出口 | 达到 | 96 Retire |

- execute 无 rm/fcsr 读取、无异常分支；tsv 中 rm/fcsr 列为空，与源码一致。
- **未达分支**：仅 guard=false（禁用 D 或 Zfa）译码失败分支（全组共性，未计 per-clause）。
- **维度小结**：立即数 32 个取值全枚举（32/32，每值 3 次 gen Retire，边界 -1.0/min/inf/nan/65536.0 均含）；负例 case 1（ins `fli.d f0, -1.0`，fcsr=0，vl=3）Illegal 来自译码层编码破坏（execute 无 Illegal 出口），具体破坏编码未保留在证据中。

## FLI_H（98 case = 96 gen Retire + 2 direct-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard `(Zfh \| Zvfh) & Zfa`（true 侧） | zfa_insts.sail:17 | 半精度扩展启用 | 达到 | 96 gen Retire |
| execute match 32 臂（0bc00..NaN） | :23-56 | 常量表（H 编码） | 全部达到（每臂 3 case） | -1.0=case 5/9/68，min=case 6/11/69，65536.0(0x7c00,11101)=case 62/66/97，inf(0x7c00,11110)=case 64/67/98，nan=case 2/3/13 |
| 写回 `F_H(rd)` + `RETIRE_SUCCESS` | :57-58 | 单出口 | 达到 | 96 Retire |

- H 特有：0b11101（65536.0）与 0b11110（+inf）结果位型同为 0x7c00 但编码不同，两个 mnemonic 均有独立 case 覆盖（case 62 组 vs 64 组）。
- **未达分支**：guard=false；另 Zvfh-only（无 Zfh）的 guard 组合未单独测（同一 true 侧出口，不构成独立分支）。
- **维度小结**：立即数 32/32 全覆盖；负例 case 1、case 4（ins 相同，均译码层 Illegal）。

## FLI_S（97 case = 96 gen Retire + 1 direct-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard `Ext_Zfa`（true 侧） | zfa_insts.sail:67 | 仅要求 Zfa（含 Ext_F，:9） | 达到 | 96 gen Retire |
| execute match 32 臂（0xbf800000..NaN） | :73-106 | 常量表（S 编码） | 全部达到（每臂 3 case） | min=case 5/9/68，inf=case 66/97，nan=case 2/3/12 |
| 写回 `F_S(rd)` + `RETIRE_SUCCESS` | :107-108 | 单出口 | 达到 | 96 Retire |

- **未达分支**：仅 guard=false。
- **维度小结**：立即数 32/32 全覆盖；负例 case 1 为译码层 Illegal。

## FROUND_D（40 case = 39 gen + 1 direct-negative；Illegal=10、Retire=30）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard `Ext_D & Ext_Zfa`（true 侧） | zfa_insts.sail:421 | 扩展启用 | 达到 | 39 gen |
| execute `None() => Illegal_Instruction()` | :431-432 | rm=dyn 且 fcsr.FRM∈{101,110,111}（`select_instr_or_fcsr_rm` 经 Fcsr_RM_Illegal 返回 None） | 达到 | case 11/26/33（frm=5，fcsr=a0）、case 13/28/35（frm=6，c0）、case 14/29/36（frm=7，e0），共 9 个 gen Illegal |
| execute `Some(rm')` → roundToInt(false) + accrue + 写回 + RETIRE | :433-441 | 静态 rm 或 dyn+有效 FRM | 达到 | 静态：rne=2/10/12、rtz=4/18/20、rdn=5/21/22、rup=6/23/24、rmm=7/25/27；dyn+frm0..4：case 15/30/37（0x00）、16/31/38（0x20）、32/39（0x40）、40/34（0x60）、3/8/9（0x80），共 30 Retire |
| 指令 rm 字段=0b101/0b110 → 译码失败 | fext_insts.sail:31-38（共享） | encdec_rounding_mode 无此二值映射 | **未达** | gen 的 rm 仅 {rne,rtz,rdn,rup,rmm,dyn} |
| guard=false | :421 | 禁用扩展 | **未达** | 运行配置固定启用 |

- **Illegal 归因**：10 个 Illegal = 9 个 gen（全为 dyn+FRM∈{5,6,7}→None 臂）+ 1 个 direct-negative（case 1，ins `fround.d f0, f0, rup`、fcsr=0，若编码合法必走 Some 臂 Retire，故为译码层编码破坏；破坏字段未保留在证据中）。
- **维度小结**：指令 rm 字段 5/8 个可译码值覆盖（缺 101/110 两个不可译码值）；fcsr.frm 初始值 0..7 全枚举（0..4→Retire，5/6/7→Illegal）。

## FROUNDNX_D（40 case = 39 gen + 1 direct-negative；Illegal=10、Retire=30）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard `Ext_D & Ext_Zfa`（true 侧） | zfa_insts.sail:450 | 扩展启用 | 达到 | 39 gen |
| `None() => Illegal_Instruction()` | :460-461 | 同 FROUND_D | 达到 | case 11/27/33（frm=5）、13/28/35（frm=6）、14/29/36（frm=7） |
| `Some(rm')` → roundToInt(true) + 写回 + RETIRE | :462-469 | 与 FROUND_D 仅第三参差异 | 达到 | 静态 5 rm（case 2/9/12 等 15 个）+ dyn+frm0..4（case 3/8/10、15/16/17、31/32、20/34/40、30/37/38）共 30 Retire |
| 指令 rm=0b101/0b110 译码失败 | fext_insts.sail:31-38 | 同上 | **未达** | 同 FROUND_D |
| guard=false | :450 | | **未达** | |

- **Illegal 归因**：与 FROUND_D 完全同构（9 gen None 臂 + 1 负例 case 1 译码层）。
- **维度小结**：与 FROUND_D 相同；roundToInt 的 raise_inexact=true 数据效应无独立记录（见"无法判定"）。

## FROUND_H（79 case = 78 gen + 1 direct-negative；Illegal=19、Retire=60）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard `Zfh & Zfa`（true 侧） | zfa_insts.sail:305 | 半精度扩展启用 | 达到 | 78 gen |
| `None() => Illegal_Instruction()` | :315-316 | dyn+FRM∈{5,6,7} | 达到 | 每 frm 保留值 6 case，如 case 73/53（a0/e0）等共 18 个 gen Illegal |
| `Some(rm')` → f16roundToInt(false) + 写回 + RETIRE | :317-324 | | 达到 | 静态 5 rm×6（rne=case 49 等）+ dyn+frm0..4×6，共 60 Retire |
| 指令 rm=0b101/0b110 译码失败 | fext_insts.sail:31-38 | | **未达** | |
| guard=false | :305 | | **未达** | |

- **Illegal 归因**：19 = 18 gen（None 臂）+ 1 负例（case 1，rup+fcsr=0，译码层）。
- **维度小结**：78 gen = 13 个 rm 组合×6（环境 sew∈{32,8} 各 3 个，非控制流维度）；rm/fcsr.frm 两维度覆盖同 FROUND_D 全枚举。

## FROUNDNX_H（79 case = 78 gen + 1 direct-negative；Illegal=19、Retire=60）

结构同 FROUND_H（guard :334；None 臂 :344-345，证据 case 73/53 等 18 个 gen Illegal；Some 臂 :346-353，60 Retire）。未达分支同为 rm=101/110 译码路径与 guard=false。维度小结同 FROUND_H。

## FROUND_S（79 case = 78 gen + 1 direct-negative；Illegal=19、Retire=60）

结构同 FROUND_H，guard 为 `Ext_Zfa`（zfa_insts.sail:363），roundToInt 用 f32 版（:377）。None 臂 :373-374 达到（18 gen Illegal，证据 case 73/53 等）；Some 臂 :375-382 达到（60 Retire）。未达分支与维度小结同 FROUND_H。

## FROUNDNX_S（79 case = 78 gen + 1 direct-negative；Illegal=19、Retire=60）

结构同 FROUND_S（guard :392；None 臂 :402-403，18 gen Illegal 证据 case 73/53 等；Some 臂 :404-411，60 Retire）。未达分支与维度小结同上。

## FCVTMOD_W_D（79 case = 78 gen Retire + 1 direct-negative Illegal）

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case |
| --- | --- | --- | --- | --- |
| encdec guard `Ext_D & Ext_Zfa`（true 侧） | zfa_insts.sail:735 | 扩展启用 | 达到 | 78 gen |
| encdec rm 字段固定 0b001（rtz） | :734 | rm 不构成分支（其它 rm 编码译码为 fcvt.w.d 等） | 达到（78 case 全 rtz） | 全部 |
| execute 读 F_D(rs1)→helper→accrue_fflags→sign_extend 写回 X(rd)→RETIRE | :740-746 | execute 单出口，无 Illegal/异常分支 | 达到 | 78 Retire（User=case 65、Supervisor=case 16、Machine=case 60） |
| helper `is_zero` 臂 | :681,:697 | ±0 → (0, 0) | **无法判定** | tsv 无 rs1 输入值记录 |
| helper `is_subnorm` 臂 | :680,:698 | 次正规 → nx | **无法判定** | 同上 |
| helper `is_nan_or_inf` 臂 | :682,:699 | NaN/Inf → nv | **无法判定** | 同上 |
| helper `is_too_large`（true_exp≥84） | :694,:700 | → nv | **无法判定** | 同上 |
| helper `is_too_small`（true_exp<0） | :695,:701 | → nx | **无法判定** | 同上 |
| helper normal 路径（移位/取整） | :702-712 | 定点化取整 | **无法判定** | 同上 |
| helper result 符号臂（sign=1 取负 / sign=0） | :715-716 | 2 臂 | **无法判定** | 同上 |
| helper max_integer 符号臂（0x80000000/0x7fffffff） | :719-720 | 2 臂 | **无法判定** | 同上 |
| helper flags 4 臂（true_exp>31 nv / 整数溢出 nv / fractional≠0 nx / 无标志） | :721-724 | 4 臂 | **无法判定** | 同上 |

- **未达分支**：guard=false（共性）；负例 case 1（ins `fcvtmod.w.d x0, f31, rtz`，译码层 Illegal，破坏编码未保留）。
- **维度小结**：78 gen 的差异维度为环境 priv（U/S/M）×sew×lmul 随机组合，均为非控制流维度；fcsr 列为空（execute 不读 fcsr，与源码一致）；**helper 的 14 个数据依赖叶分支因产物未记录 rs1 输入值而无法判定**。

---

## 版本注记

- 产物基线 IR 56cc69a4 = 当前 `sail-riscv` HEAD（f8ce849 之前的提交边界由 gitlink 固定）；`git -C sail-riscv diff --stat -- model/extensions/FD/` 显示工作树有 5 文件改动 + 5 个未跟踪新文件。
- 对本组 10 clause 的实质核对（`git -C sail-riscv diff -- model/extensions/FD/zfa_insts.sail` 逐 hunk）：
  - FLI_H/S/D：仅 `assembly` 行由 `hex_bits_5(constantidx)` 改为 `fli_constant_mnemonic(constantidx)`（新增文件尾 :748-782 的 mnemonic 表）。**encdec guard 与 execute 的 32 臂 match 完全未变**。
  - FROUND/FROUNDNX 六条指令与 FCVTMOD_W_D（含 fcvtmod_helper）：**无任何 hunk，逐字一致**。
  - `select_instr_or_fcsr_rm`/`valid_rounding_mode`/`encdec_rounding_mode`（fext_insts.sail:31-63）：无 hunk，与 IR 版本一致（HEAD 版 encdec_rounding_mode 同样无 0b101/0b110 映射）。
  - 工作树其余 diff（FMINM/FMAXM 改调 fp_minm_pure/fp_maxm_pure、新增 softfloat_symbolic_f{16,32,64}.sail 重定位 roundToInt）不属于本组 clause，但注意 `riscv_f*roundToInt` 实现文件在工作树已更换，本组对 roundToInt 仅做调用层对照。
- 佐证细节：cases.tsv 的 ins 立即数显示为新 mnemonic 文本（`min`/`0.00390625` 等）而非 IR 版 assembly 的 hex 格式，说明 ins 列由 runner 侧反汇编生成而非 IR Sail assembly 直出；mnemonic↔constantidx 一一对应，不影响覆盖判定。

## 全组结论

1. **指令级 execute 分支 10/10 clause 全部达到**：FLI 三条 32 个常量 match 臂每臂 ≥3 case（立即数全枚举含 -1.0/min/inf/nan/65536.0 边界）；FROUND/FROUNDNX 六条 `None→Illegal_Instruction` 与 `Some→roundToInt+写回` 两臂均有 case；FCVTMOD execute 单出口有 78 个 Retire。
2. **gen 内全部 Illegal 均可归因**：FROUND/FROUNDNX 的 9+18×5=99 个 gen Illegal 全部为 rm=dyn 且 fcsr.FRM∈{101,110,111} → `select_instr_or_fcsr_rm` 返回 None（config=Fcsr_RM_Illegal）→ execute None 臂，三个保留 frm 值均覆盖；不存在未解释的 Illegal。
3. **确认未达分支共 16 个**（均属译码/配置层，非 zfa_insts.sail 内 execute 分支）：①10 条指令的扩展禁用 guard=false 分支各 1（运行配置固定启用）；②FROUND/FROUNDNX 六条的指令 rm 字段 0b101/0b110 编码路径各 1（encdec_rounding_mode 无映射、gen 未生成该编码）。
4. **无法判定**（产物 tsv 未记录输入操作数值）：fcvtmod_helper 的 6 个顶层分类 + 8 个子分支（sign×2、max_integer×2、flags×4）；FROUND/FROUNDNX 所调 `riscv_f*roundToInt` 的内部分支（含 raise_inexact true/false 的数据效应）。如需闭环需在 replay 包中保留 rs1 初值维度。
5. 10 个 direct/derived 负例 Illegal 均为译码层（合法 rm/fcsr 下 execute 无 Illegal 出口），实际破坏编码未保留在证据包中，对应的具体 guard/字段分支无法进一步定位。
