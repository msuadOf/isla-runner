# 当前浮点向量非访存 clause 覆盖审计（2026-09-26）

本次只审计非 BF16 的 22 个浮点向量 clause；四个 BF16 向量 clause 由独立审计负责。依据是当前 Sail 源码、[77 项清单](tools/official_float/targets77.txt)、[静态矩阵](clause-matrix.md)、三个输入包及最终 IR 的原始结果。未修改模型、执行器、正式输入或配置；另在外部目录构造一条初始/预期 flags 为 0 的 ROD 样例及 18 条 FVVTYPE OF/UF 样例，未进入独立内存 worktree。

**结论：22/22 clause、97 个 enum 的 262 个合法 enum×SEW 格，以及四个固定编码 clause 的 12 个格式格，都有当前 IR 的具体状态证明；不能据此声明分支全覆盖或普通 `make solve` 验收通过。** 原最终矩阵中这部分为 981 条成功记录，本次补跑四条既有 FVVTYPE 状态例，新增一条零 flags 的 ROD 跳过 sNaN 变体及 18 条 OF/UF 活动/抑制样例，合计 1004 条记录，其中有重复输入。补跑的 24 条非 BF16 非法 FRM 例另计。没有新发现的动态失败；非法扩展/SEW、vill、LMUL/重叠、其它状态及 OF/UF 更多边界仍未完整覆盖。

## 1. 版本与本次复核

最终批次外部目录名为 `isla-float-ir-final-20260926.q1Auj4`，以 `IR_STAGE` 指代；本次补跑外部目录名为 `isla-float-vector-audit-20260926.v59gu3by`，以 `AUDIT_STAGE` 指代。两者都不是仓库内路径，实际位置由运行环境保存。当前版本由[最终 IR 记录](ir-refresh.md)给出，不能仅用子模块 HEAD 代替未提交模型修改。

| 输入/工具 | SHA-256 |
|---|---|
| 完整 V128 IR；与当前 `isla/rv64d.ir` 相同 | `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409` |
| E 成功路径 runner | `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425` |
| 非法路径 runner | `e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3` |
| E RV64 配置 | `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987` |

逐组核对了 `IR_STAGE/matrix/summary.json` 指向的输入文件和实际输出 SHA-256、行数及逐行名称、clause、全部 tuple 字段和预期状态。各行均为 SAT、`Retire_Success`、一条完成执行路径、`difference_unsat=true`、`structural_ok=true`。成功 runner 在真实编码译码/反编码后执行，并对列入 `expected` 的寄存器任意差异求 UNSAT，足以支持列定输入及观察状态的结论。

本次补跑使用同一完整 IR、配置与已有 runner。前三批输入未改，三个命令、退出码、耗时及哈希保存在 `AUDIT_STAGE/summary.json`，各组另有 `.log` 和 `.json`。第四批只从原 `vfncvt_rod_skip_snan` 派生一条输入，将 `initial.fcsr` 与 `expected.fcsr` 的 `0x10` 改为 `0x0`；逐字段核对其余内容完全相同，元数据独立保存在 `rod-skip-snan-zero-flags.summary.json`。第五批构造三个格式的独立 IEEE OF/UF 输入，生成规则与全部位串、命令、哈希另存 `fvvtype-of-uf.summary.json`。

| 输入 | 当前结果 | 输出名 / SHA-256 |
|---|---|---|
| [vector negative](tools/e_vector_cases/negative-cases.json) | 21/21，exit 0，5.874 s | `vector-negative.json`；`98318fdfe25f95a7370500765352f67da9ec97857fc4336bbd6266a8faae6471` |
| [illegal-frm](tools/e_nonmem/inputs/illegal-frm.json) | 9/9，exit 0，5.322 s；其中 VFNUNARY0 三条、BF16 六条 | `nonmem-illegal-frm.json`；`f4d58614f3aaf7d63305dce0c37a0599b681164af5e72d9d412ab5e412ab0b1d` |
| [FVVTYPE 状态](tools/e_nonmem/inputs/vector-cases.json) | 4/4，exit 0，5.121 s | `fvvtype-state.json`；`455a612b69555b6c0c65f09f7357a1a537fdc96035839cde22b547449b7bbdeb` |
| 外部 `rod-skip-snan-zero-flags.inputs.json` | 1/1，exit 0，4.871 s；SAT、单执行路径、成功退休、状态差异 UNSAT | `rod-skip-snan-zero-flags.results.json`；`386b22dc903afe41d53ca959de3d4abf35bea52d9e7371b04756bcd756f26705` |
| 外部 `fvvtype-of-uf.inputs.json` | 18/18，exit 0，5.774 s；SAT、单执行路径、成功退休、状态差异 UNSAT | `fvvtype-of-uf.results.json`；`ee154e15e8329461ef1a7f7db478c651234207702ce30d6d0fbce13f62a208ab` |

ROD 变体输入 SHA-256 为 `ccbe2ccd2f843a489b13e4540c3c8d2566bbafc2fb1258454ad6d23cb0bbe2a9`，原 `priority.json` SHA-256 为 `b0c2f935c9662c8536e5f5fcbd633969cdfc47f94cf4ec198ff4ed8f93a5c56b`。实际观察 `fcsr=0`、`vr4=0x3c00beef`、`vstart=0`、`mstatus=0x8000000000006600`；完整观察状态与预期的任意差异 UNSAT，支持这条 SEW16、VL2、vstart1 输入跳过 sNaN 时不新增 NV。此结论不外推其它格式、mask 或转换 enum。

前两批逐行核对 `Illegal_Instruction`、单完成执行路径、SAT、完整观察状态保持的差异 UNSAT。其中 BF16 六条结果已共享给 BF16 审计，不重复计入本文件的 24 条非 BF16 非法例。重跑命令如下，调用者先设置两个外部目录变量：

```sh
"$IR_STAGE/isla-float-e-illegal-runner" "$IR_STAGE/ir/rv64d_final.ir" \
  "$IR_STAGE/rv64-e.toml" agents/float_support_review/tools/e_vector_cases/negative-cases.json \
  "$AUDIT_STAGE/vector-negative.json"
"$IR_STAGE/isla-float-e-illegal-runner" "$IR_STAGE/ir/rv64d_final.ir" \
  "$IR_STAGE/rv64-e.toml" agents/float_support_review/tools/e_nonmem/inputs/illegal-frm.json \
  "$AUDIT_STAGE/nonmem-illegal-frm.json"
"$IR_STAGE/isla-float-e-nonmem-runner" "$IR_STAGE/ir/rv64d_final.ir" \
  "$IR_STAGE/rv64-e.toml" agents/float_support_review/tools/e_nonmem/inputs/vector-cases.json \
  "$AUDIT_STAGE/fvvtype-state.json"
"$IR_STAGE/isla-float-e-nonmem-runner" "$IR_STAGE/ir/rv64d_final.ir" \
  "$IR_STAGE/rv64-e.toml" "$AUDIT_STAGE/rod-skip-snan-zero-flags.inputs.json" \
  "$AUDIT_STAGE/rod-skip-snan-zero-flags.results.json"
"$IR_STAGE/isla-float-e-nonmem-runner" "$IR_STAGE/ir/rv64d_final.ir" \
  "$IR_STAGE/rv64-e.toml" "$AUDIT_STAGE/fvvtype-of-uf.inputs.json" \
  "$AUDIT_STAGE/fvvtype-of-uf.results.json"
```

### 本轮新域：FVVTYPE OF/UF 与非活动 lane

这是原 981 条之外的 18 条独立输入：MUL 溢出、DIV 下溢 × SEW16/32/64 × 活动/掩码关闭/prestart。指令字与操作数字段基于已有 GNU 汇编的 `fvvtype-finite.json`；数值预期直接从 IEEE 指数/尾数字段及 RNE 规则构造，没有调用 Sail、待测 helper 或 host 浮点计算预期。输入 SHA-256 为 `260ca581e1526aa316c97a98476a4cbdb00d541cc0f3df973c8536a92cc45c53`。

| 格式 | maxfinite | 2.0 | 预期 +∞ | minsub |
|---|---|---|---|---|
| f16 | `0x7bff` | `0x4000` | `0x7c00` | `0x0001` |
| f32 | `0x7f7fffff` | `0x40000000` | `0x7f800000` | `0x00000001` |
| f64 | `0x7fefffffffffffff` | `0x4000000000000000` | `0x7ff0000000000000` | `0x0000000000000001` |

- MUL 的 lane0 为 `maxfinite × 2`，RNE 返回 +∞ 并产生 OF|NX=`0x5`；lane1 是精确 `1×2=2`。
- DIV 的 lane0 为 `minsub / 2`，精确值处于 +0 和 minsub 正中间，RNE 选偶数 +0；结果在舍入后仍 tiny 且不精确，产生 UF|NX=`0x3`。lane1 是精确 `1/2=0.5`。
- 三种状态均为 LMUL1、VL2、FRM0、旧 flags 仅 DZ=`0x8`，目标初值为非零哨兵 `0xa5a55a5af0f00f0f1122334455667788`。活动例预期完整 fcsr 分别 `0xd`、`0xb`。mask例设vm0/v0=`0b10`，prestart例设vm1/vstart1，两者只抑制异常lane0、保留活动lane1，完整fcsr必须仍为`0x8`。
- 全部18条均验证完整128位目标（包括旧lane0及其它tail）、fcsr、vstart清零和mstatus=`0x8000000000006600`，逐行任意差异UNSAT。该结果证明三个格式中上述RNE输入的OF/UF产生与mask/prestart抑制；未覆盖定向舍入、符号反转、normal/subnormal边界、精确tiny值、异常lane位于tail或其它clause的OF/UF。

## 2. 证明粒度及共同缺口

原始包分工：`e_vector_cases` 的 22+227+49+564=862 条覆盖 20 clause；`e_fvvtype_cases` 的 27+24 条和 `e_nonmem/smoke.json` 中一条覆盖 FVVTYPE；`e_nonmem` 七个相关批次共 67 条覆盖 VFNUNARY0。以上合计 981。五 RM 包的 564 条含 SQRT 三个同输入 shape，原文已说明只有 534 个不同完整输入；全包总数也不应视作不同状态数或分支数。

预期来源合理：普通有限样例用可精确表示的 Python 算术、位串/符号公式；五 RM 中点用显式 tie/方向规则，SQRT 用有理数平方夹逼；FVVTYPE 边界使用独立 IEEE 位串。扩展包从 Sail 抽取 enum/编码，再与 GNU assembler 对照，属于编码一致性核对；数值预期并非执行待测 Sail 后抄回。但这些样例没有代码分支计数器、覆盖率 trace 或每个 guard 的正反条件证据。

所有表中“已证”均受下列边界限制：

1. **扩展和格式。** 正常合法格式已触达；未逐个关闭 Zvfh、Zvfhmin、Zve32f、Zve64f、Zve64d，也未对保留 SEW 或非法转换 enum×SEW 组合完成真实译码拒绝证明。`valid_widening_fp_conversion` 与 `valid_narrowing_fp_conversion` 的条件不同，不能只按 `SEW=16/32` 归并。源码见 `vext_utils_insts.sail:126–155`。
2. **合法性。** [浮点公共检查](../../sail-riscv/model/extensions/V/vext_fp_utils_insts.sail)的 `illegal_fp_normal`、`illegal_fp_variable_width` 等还检查 vill、vd/v0、SEW/FRM、EEW/EMUL；[通用检查](../../sail-riscv/model/extensions/V/vext_utils_insts.sail)另检查组对齐与重叠。当前新增非法证明只固定 FRM=5/6/7 的八个代表 clause，未覆盖其余条件的拒绝。返回一次 Illegal 不能证明同一 OR 条件里的其他子项。
3. **LMUL 与状态。** 除 `FWVVTYPE` 一条 LMUL2→目标 EMUL4 跨物理寄存器例，全部成功输入 LMUL1；没有 mf2/mf4/mf8、m4/m8、最大合法/首个非法 widening EMUL、非法组对齐、合法/非法重叠矩阵。全部当前成功输入 `vta=vma=0`；普通 mask/vstart 组合主要 SEW32、一种 enum。`get_start_element` 的 Err 路径、比较写 v0、归约允许与源/掩码重叠等均未独立验收。
4. **Sail 路径。** E 配置 `__isla_use_extra_ops=true`，`init_masked_result`/`init_masked_result_cmp` 走 `isla_init_mask`，不能把结果算作它们的 `*_default` 分支已测。源码目前对 agnostic 采用保留旧值，是允许的具体模型选择；后续验证应核对当前选择，不能强行期待全 1。VFMERGE、归约有独立循环，不能仅凭普通 ALU 的 mask 测试推断其分支。
5. **flags。** 对 981 条原始记录计算 `expected_fflags & ~initial_fflags`，分布为 0:342、NX:611、DZ:9、NV:19，原批次没有新产生 OF 或 UF 的指令状态样例。本次额外18条中，三条MUL活动例新增OF|NX、三条DIV活动例新增UF|NX，其余12条证明mask/prestart抑制，详见上节。原例预置OF=4后保持仍不能计为产生OF；新增证明也不覆盖其它舍入、边界或clause。不同活动lane分别触发多个新flags的OR累计尚未系统覆盖。
6. **观察范围。** 证明覆盖每例显式列入 `expected` 的目标、fcsr、vstart 及多数例的 mstatus；首轮 22 条没有 mstatus 观察。多数例预置 FS/VS 已 Dirty，只证明对应 SD/已 Dirty 状态，未测 Initial/Clean→Dirty 或 Off/扩展关闭的拒绝。未把全部源寄存器、非目标寄存器、vl/vtype 纳入“不应改变”观察，不能称完整机器状态等价。

## 3. 逐 clause 的分支与证据

以下源码简称 FP=`sail-riscv/model/extensions/V/vext_fp_insts.sail`，VM=`vext_fp_vm_insts.sail`，RED=`vext_fp_red_insts.sail`。行号按当前工作树，历史 clause-matrix 行号部分已变化。“格数”只计 enum×合法 SEW；固定编码计格式数。成功记录数为原最终矩阵，FVVTYPE 另列本次四条既有状态与18条OF/UF新域，VFNUNARY0 另列本次零 flags 变体一条。

| Clause / 当前入口 | 格数；成功记录 | 已有具体证明 | 该 clause 尚未证明的关键分支 |
|---|---:|---|---|
| `FVVTYPE` FP:36 | 9×3=27；52+本次22 | add/sub/min/max/mul/div/三种 sign；三格式 finite，min/max ±0、sNaN、min qNaN、div 1/0、mul ∞×0、sgnj sNaN payload；本次补 f32 ADD 跳过/屏蔽/活动 sNaN，以及三格式MUL OF/DIV UF的活动、mask/prestart抑制 | 所有 enum 仅 FRM0；ADD/SUB cancellation、一般 inexact mul/div、OF/UF其它边界、双 NaN/操作数互换；vl0/vstart≥vl、ADD其它SEW的mask、非法组/FRM/vill |
| `FVVMATYPE` FP:121 | 8×3=24；75 | 八种累加/乘数角色和符号；MACC 五 RM 三格式；f32 MACC mask/vstart/sticky 及融合低乘积例 | 另七 enum 的非 RNE/特殊值；∞×0、乘积∞与异号∞相加、NaN 优先级；vl0/全 mask；组对齐与别名 |
| `FVFMATYPE` FP:1053 | 8×3=24；75 | 同上 VF 路由；MACC 合法 boxed scalar；本次 MACC FRM5/6/7 拒绝 | 除 MACC 外 RM/特殊值；scalar malformed boxing、scalar sNaN 活动/非活动；组/别名。VF 与 VV 参数角色仍分别执行，不能合为一条证据 |
| `FVFTYPE` FP:949 | 13×3=39；95 | add/sub/reverse-sub/min/max/sign/mul/div/reverse-div/两 slide；ADD 五 RM、masked skipped sNaN、vl0/vstart≥vl、H/S malformed boxing；两个 slide 的首/末和中间来源、qNaN payload；本次 ADD 非法 FRM | slide1up `vs2==vd` 拒绝与 slide1down 同寄存器合法；mask/vstart 与 slide 相交；reverse/div/sub 的非 RNE及特殊数；min/max 的 VF NaN/±0 选择；scalar sNaN 活动边界 |
| `FVVMTYPE` VM:31 | 4×3=12；18 | 四关系真值；SEW32 Eq/Ne quiet qNaN、Le signaling qNaN、Eq sNaN；NE mask/vstart/tail | 各关系 false/equal/±0、Lt qNaN/sNaN、其它 SEW NaN、源互换；写 v0 及与源重叠；LMUL与非法 FRM |
| `FVFMTYPE` VM:104 | 6×3=18；25 | 六关系真值；SEW32 Eq false/qNaN/sNaN、Ne qNaN、Le qNaN；NE mask/vstart；本次 NE 非法 FRM | Lt/Gt/Ge 特殊值与反向关系、scalar boxing/NaN、全部关系 false/equal、目的 v0/源重叠及格式状态交叉 |
| `FWVVTYPE` FP:197 | 3×2=6；41 | add/sub/mul，16→32/32→64；ADD 五 RM、mask/vstart；唯一 LMUL2/EMUL4 跨寄存器例核完整四个目标寄存器 | 两个窄源分别与宽目标重叠的合法/非法分支，非法 EMUL/对齐；SUB/MUL 特殊数；其它 LMUL与lane布局 |
| `FWVVMATYPE` FP:269 | 4×2=8；42 | 四种 widening FMA 符号；MACC 五 RM及mask/vstart | 两窄源 overlap 条件、特殊值/NaN/无效 fused、vl0/全mask；非MACC的有符号舍入 |
| `FWVTYPE` FP:340 | 2×2=4；38 | 宽 vs2+窄 vs1 的 add/sub；ADD 五 RM及mask/vstart | 窄 vs1 与宽目标 overlap 和宽 vs2 组检查各自失败；宽源/目标合法相同组；SUB 特殊数和非RNE |
| `FWVFTYPE` FP:1128 | 3×2=6；40 | 两窄输入、宽目标 add/sub/mul；ADD 五 RM及mask/vstart | scalar malformed box/sNaN，非活动 scalar 不置flags；窄源 overlap、EMUL/对齐非法；SUB/MUL 特殊数 |
| `FWVFMATYPE` FP:1199 | 4×2=8；42 | 四种 widening VF FMA；MACC 五 RM及mask/vstart | scalar boxing/NaN、特殊 fused 和其它符号变体RM；overlap、EMUL边界、vl0/全mask |
| `FWFTYPE` FP:1269 | 2×2=4；38 | 宽 vs2 与窄 scalar add/sub；ADD 五 RM及mask/vstart | 宽源与目标两项组检查、合法别名、scalar boxing/NaN；SUB 特殊数和非RNE |
| `VFUNARY0` FP:412 | 6×3=18；81 | 整数正2/FP2 六路；signed FP→int 五 RM；两固定RTZ在FRM0/3；signed转int的mask/vstart；本次非法FRM | unsigned 和 int→FP 的舍入边界、signed负整数符号扩展、整数最大/最小、NaN/∞/越界饱和；RTZ在非法FRM下仍应拒绝的独立例 |
| `VFWUNARY0` FP:533 | 16；60 | 七enum正常宽化；仅 int8→FP16 两enum有SEW8；额外 `0xfe` signed/unsigned辨识；signed FP→wide-int 五RM、RTZ覆盖；F→F mask/vstart与非法FRM | SEW8其余五enum须先由译码拒绝，不能执行后遇不到循环而误算合法；整数/NaN边界、扩展最小组合；overlap/EMUL；F→F sNaN实际NV与其它enum状态 |
| `VFNUNARY0` FP:669 | 20；67+本次1 | 全八enum SEW16/32与四种FP16→int8；F→F两格式五RM、SEW16 signed FP→int五RM、ROD frm0/4、RTZ frm0；各宽度正向整数overflow→NV；ROD vl0/全mask/vstart；本次ROD frm5/6/7拒绝，新增零flags证明SEW16跳过sNaN不置NV | ROD subnormal/tiny/overflow/NaN及截断低位形状；其余enum的mask/vstart；unsigned/int→FP五RM、负溢出/NaN/∞；窄目标与宽源允许低段重叠/禁止高段重叠。原skip_snan例局限与补证见下节 |
| `VFUNARY1` FP:812 | 4×3=12；63 | SQRT4及SQRT2五RM、mask/vstart；rec7/rsqrt7只在+0输入验证+∞/DZ；class只测正normal；本次SQRT非法FRM | **指令层 rec7/rsqrt7 查表正常路径和归一化尚无例**；负有限、±0、∞、q/sNaN；class其余9类；负sqrt/NaN/∞；估算helper单测不能替代lane状态集成 |
| `RFVVTYPE` RED:30 | 4×3=12；67 | sum ordered/unordered/min/max；SEW32三lane；ordered五RM、vl0早退、全mask跳过sNaN并复制qNaN seed；本次vl0非法FRM仍拒绝 | `vstart!=0` 必须拒绝，vs2组非法；中间NaN/±0/溢出与flags OR；部分mask、多lane不可结合输入的顺序辨识；非零目标tail保持与源/目标/v0重叠 |
| `RFWVVTYPE` RED:106 | 2×2=4；41 | ordered/unordered均用Sail顺序算法；SEW32三lane、ordered五RM、vl0、全mask保留seed payload | 与上行同类；宽seed与窄lane格式差异、SEW16多lane、vstart/非法FRM/EEW边界。无序采用有序结果是该Sail合法实现选择，不是漏实现另一棵树 |
| `VFMERGE` FP:1333 | 3；5 | 三格式固定编码；SEW32两个lane同时覆盖v0真/假及tail保留 | 独立loop的prestart、vl0/vstart≥vl、fractional LMUL、tail agnostic；`vd==v0`拒绝、get_start_element Err、scalar malformed boxing/NaN payload |
| `VFMV` FP:1394 | 3；4 | 三格式scalar广播到一个活动lane并保持tail | vl0/vstart≥vl/prestart、多活动lane、fractional LMUL、malformed box/NaN payload；目标组/非法FRM。不能用 VFMVSF 的首元素例代替广播循环 |
| `VFMVFS` FP:897 | 3；6 | 三格式首元素提取及H/S结果boxing；SEW32 vl0、vstart1仍读取元素0并清vstart | LMUL≠1仍忽略LMUL、NaN payload/非数值移动；非法FRM/vill；FLEN<SEW需要另一合法配置，当前固定FLEN64无此动态证据 |
| `VFMVSF` FP:1439 | 3；6 | 三格式写首元素；SEW32 vl0/vstart1抑制首元素写回 | LMUL≠1仍只写单个物理寄存器首元素、非零tail、malformed box/NaN payload、tail agnostic；非法FRM/vill。与VFMVFS在vl0/vstart上的相反行为不能归并 |

## 4. 样例区分能力需收紧的地方

- `e_nonmem/inputs/priority.json` 的原 `vfncvt_rod_skip_snan` 初始 `fcsr=0x10` 已含 NV，期望也是 `0x10`。原样例能证明目标前缀保留及没有新增其它 flags，**单凭原样例不能证明跳过 sNaN 不贡献 NV**。本次保持其余输入与结果完全不变、将初始/预期fcsr设为0，真实执行并以差异UNSAT补证该输入的NV抑制，证据见第1节。仍可进一步用旧NX=1及相同源vstart0建立非零旧flag/活动NV对照。现有 `vfncvt_rod_masked` 用不精确有限值，能辨识NX抑制，却不是sNaN/NV抑制例。
- 比较扩展包主动选使每个关系为true的输入。额外状态包只为部分关系补false/NaN，故“六enum×三SEW”不能证明每个比较正反结果及unordered分支。
- 归约三lane使用 1.5+2.25+1+0.5 这种精确可结合数；能够检测漏lane/选择，但不能区分累加顺序或中间舍入。ordered五RM例仅一lane，无法补足该缺口。
- FMA八enum的普通输入运算都精确；融合低乘积辨识只覆盖SEW32的两个普通MACC clause。已有结果支持参数/符号路由，并不单独证实每种符号变体在NaN/无穷输入下的优先级。
- `vtype` policy 位从未置1，且活跃样例均以FS/VS Dirty开始，不能从“状态已检查”推出policy或CSR全部状态转换已覆盖。

## 5. 可执行的补测顺序

1. **继续补旧flags和活动对照，沿已有 runner 另建输入包。** 零flags的ROD跳过sNaN例已补证；进一步把初始/期望flags设为NX=1，补同源vstart0预期NV|NX=17、全mask=0预期NX保持。为FVVTYPE add/sub/mul/div分别构造两格式以上的inexact中点并跑FRM0–4；已有helper oracle可生成完整bits/flags，但须记录独立来源。
2. **每种实际guard逐项只改变一个条件。** 保持真编码，分别测试 `vill=1`；普通masked算术`vd=v0`非法与比较/归约`vd=v0`合法；m2源或目标奇数寄存器；widening m4合法/m8非法；widening源位于目标高段合法/低段非法；narrowing目标在源低段合法/高段非法；slide1up源=目标非法/slide1down同寄存器合法；两归约vstart1非法。非法例同时观察目标、源哨兵、fcsr、mstatus、vstart、vl、vtype，要求未更新，而不是只看返回标签。
3. **以真实译码区分格式和扩展准入。** 额外用译码拒绝runner验证SEW8普通FP、SEW64 widening/narrowing及SEW8不适用转换，逐个禁用所需扩展。配置要分别保留Zvfhmin、Zvfh、Zve32f、Zve64f、Zve64d的合法依赖，不能用关闭全部FP作唯一反例。guard拒绝时预期`ILLEGAL(raw_word)`，不伪造合法constructor执行。
4. **继续补数值与lane副作用。** 本次三格式MUL OF、DIV UF及mask/prestart抑制已通过；尚需F→F窄化的OF/UF、异常lane位于tail、定向舍入和normal/subnormal边界，并为每个helper路由补qNaN/sNaN、±0、∞、最小normal/subnormal、maxfinite。用两个活动lane分别触发NV与DZ，加旧NX，预期完整fflags=25；同时核目标每lane，防止只验累计值。
5. **补专用分支。** class逐十类；rec7/rsqrt7至少各一个normal查表、subnormal归一化、特殊值并保留独立规范oracle；归约用精确有理数计算逐步舍入预期，例如binary32 seed=`2^24`、lanes=`1,-2^24` 的有序RNE结果为0，换顺序会得到1，并补masked lane/非零tail。无序例接受当前Sail选择的有序算法。move/merge各测vl0、vstart、malformed boxing、NaN payload、LMUL≠1。
6. **补配置状态及官方入口。** 合法mf2/mf4/mf8和m2/m4/m8选择能覆盖物理寄存器边界的VL；vta/vma四组合按模型允许结果验证；Initial/Clean→Dirty和Off拒绝分开。现有定向runner按每clause预期输入执行，官方 `make solve-<clause>` 仍需在当前d012下记录真实配置、退出码、最终JSON与成功/拒绝/受限路径；将两类证据分别报告。

普通 `make solve` 当前通过 `ACTIVE_ALL=$(filter-out $(FD_FLOAT) $(MEMORY),$(ALL))` 排除了这些浮点clause。显式 `make solve-<clause>` 或相应浮点目标组才会进入它们。旧c9e官方77项的外部超时不能写为当前d012超时，本审计也没有用定向1004条成功记录替代当前官方入口的完成性验收。
