# BF16 六项 clause 与 RV32 两项排除边界审计

日期：2026-09-26。结论：当前证据支持 BF16 六项 clause 的列定样例，**不足以认定全部源码分支或全部输入域通过**。本审计只新增本文；未修改模型、runner、配置或 IR，未进入独立内存 worktree。实施与验证总状态由 [status.md](status.md) 汇总。

## 1. 版本与证据核对

本次逐项核对当前源码、输入 JSON、runner 检查逻辑和原始输出。`IR_STAGE` 指仓库外目录 `isla-float-ir-final-20260926.q1Auj4`，`NEG_STAGE` 指本轮补跑目录 `isla-float-vector-audit-20260926.v59gu3by`；不把路径名相似的旧结果当作本轮结果。

- 当前 `isla/rv64d.ir` 与 `IR_STAGE/ir/rv64d_final.ir` SHA-256 均为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，XLEN64/VLEN128/ELEN64。
- 四个 BF16 源文件及共享 `fdext_regs.sail`、`fext_insts.sail`、`zfa_insts.sail`、`vext_utils_insts.sail`、`vext_fp_utils_insts.sail` 的当前文件哈希均与 `IR_STAGE/source-manifest.json` 相符。VF/VV 文件 SHA-256 为 `814008056c5a43d1bf3c38af1aa3da1d31bc4518619fdf55051879961ea14b60`。
- 成功 runner SHA-256 为 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`；非法路径 runner 实际 SHA-256 为 `e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3`。后者以二进制实算和 [BF16 LMUL 记录](tools/bf16_lmul/README.md) 为准；审计发现此前 `ir-refresh.md` 中该哈希有拼接笔误，主记录负责人已修正。
- E 配置 SHA-256 为 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`；启用 F/D、Machine 模式、MXL64，`__isla_use_extra_ops=true`。当前 IR 的 `fcsr_rm_reserved_behavior` 固定为 `Fcsr_RM_Illegal`。

下表只统计 BF16 行，不包括同一输入文件中的 FADD、ROD 等其他 clause。输入与输出哈希逐组比对 `IR_STAGE/matrix/summary.json`；逐例核对名称、constructor、写回预期、SAT、差异 UNSAT、结构检查和唯一完成执行路径。

| 当前 IR 输入/证据 | BF16 行数 | 内容 |
| --- | ---: | --- |
| [priority.json](tools/e_nonmem/inputs/priority.json) | 7 | 两项标量转换：有限数、qNaN、sNaN，另有窄化中点 |
| [bf16-vector.json](tools/e_nonmem/inputs/bf16-vector.json) | 15 | 四项向量转换/乘加：有限数、sNaN、活动状态 |
| [bf16-rm.json](tools/e_nonmem/inputs/bf16-rm.json) | 20 | 标量和向量窄化，各正负中点 × 五种动态 FRM |
| [bf16-macc-rm.json](tools/e_nonmem/inputs/bf16-macc-rm.json) | 10 | VV/VF 各一个正 f32 中点 × 五种 FRM |
| [bf16-vf-extra.json](tools/e_nonmem/inputs/bf16-vf-extra.json) | 3 | VF 未 boxing 标量；旧 flags=0 的全屏蔽及 `vstart=vl` |
| [BF16 LMUL cases.json](tools/bf16_lmul/cases.json) | 10 | VF：8 个 e16,m8 非法状态，2 个 e16,m4 合法状态；输出 `IR_STAGE/reports/bf16-lmul-results.json` |
| [illegal-frm.json](tools/e_nonmem/inputs/illegal-frm.json) | 6 | 本轮由向量审计负责人补跑；标量窄化和 VF 各 FRM=5/6/7，输出 `NEG_STAGE/nonmem-illegal-frm.json` |

前五组是 **55 条成功状态证明**：`FCVT_BF16_S` 14、`FCVT_S_BF16` 3、`VFNCVTBF16_F_F_W` 12、`VFWCVTBF16_F_F_V` 2、`VFWMACCBF16_VV` 8、`VFWMACCBF16_VF` 16。另有 LMUL 10 条及本轮非法 FRM 6 条，首次审计共 71 条列定 BF16 状态样例。随后新增清零初始flags的38条复验，见[第8节](#8-同轮追加清零初始flags的38条复验)，本文现记录109条状态样例；不把这个数解释为分支数。`e_scalar_cases/` 和 `e_vector_cases/` 的归档 JSON 没有 BF16 clause，不能把它们的 RM/状态扩展数加入 BF16 覆盖。

非法 FRM 整包 9/9、exit 0、5.322 秒，其中 BF16 6/6；输入 SHA-256 `fd5a5de400209b3028396283dc40c3b694f2351f4c1779c35c10f9147bc09a63`，整包输出 SHA-256 `f4d58614f3aaf7d63305dce0c37a0599b681164af5e72d9d412ab5e412ab0b1d`。本审计再次核对该输出哈希及全部 BF16 行。复跑命令形状如下，完整展开命令在 `NEG_STAGE/summary.json`：

```sh
"$IR_STAGE/isla-float-e-illegal-runner" \
  "$IR_STAGE/ir/rv64d_final.ir" "$IR_STAGE/rv64-e.toml" \
  agents/float_support_review/tools/e_nonmem/inputs/illegal-frm.json \
  "$NEG_STAGE/nonmem-illegal-frm.json"
```

## 2. 标量源码分支映射

入口：[zfbfmin_insts.sail](../../sail-riscv/model/extensions/bfloat16/zfbfmin_insts.sail)、[zfbfmin_utils.sail](../../sail-riscv/model/extensions/bfloat16/zfbfmin_utils.sail)、[寄存器 boxing](../../sail-riscv/model/extensions/FD/fdext_regs.sail)、[RM 选择](../../sail-riscv/model/extensions/FD/fext_insts.sail)。以下“缺口”指没有找到当前 IR 的相应独立状态证明；源码共享或其他 clause 通过不自动补齐该格。

| clause / 源码条件 | 现有证据 | 尚未覆盖或应限制的结论 |
| --- | --- | --- |
| 两项 decoder：`currentlyEnabled(Ext_Zfbfmin)`，进而要求 F；编码 RM 只允许 0–4、7 | 55 条中的标量样例从真实机器字反向译码并反编码 | 无 BF16 专用扩展关闭、FS 禁用、静态 RM=5/6 的译码拒绝样例；不能用执行返回 Illegal 代替 decoder 测试 |
| `FCVT_BF16_S`：`F_or_X_S` 读 f32；`nan_unbox` boxed/未 boxed 两支 | 有正确 boxing 的有限数/qNaN/sNaN | 未正确 boxing 的 f32 源无 BF16 专用当前状态证明。Zfbfmin 要求 F，本配置的 Zfinx 分支不可作为待跑合法 BF16 路由 |
| `FCVT_BF16_S`：`select_instr_or_fcsr_rm` 的静态/DYN、Some/None | 正负中点动态 FRM=0–4；FRM=5/6/7 本轮分别正确 `Illegal_Instruction`、目标/full fcsr/mstatus 保持 | 成功定向样例全用 RM_DYN，静态 RM=0–4 覆盖仍缺。`Fcsr_RM_Fatal` 属另一生成配置，本 d012 固定为 Illegal，不将其视作当前可达未覆盖分支 |
| `FCVT_BF16_S`：结果 canonical NaN 选择与 NV/NX；写 `F_BF16(rd)` | 精确 `1.5→0x3fc0`；正负 `1+2^-8` 中点；qNaN/sNaN；检查完整 64 位 BF16 boxing 与累计 flags | 指令层缺 ±0、±inf、次正规、UF/OF 阈值、奇数 LSB 中点、负 NaN、多 payload；纯 helper 结果不直接证明 CSR/boxing 链路 |
| `FCVT_S_BF16`：先验证 RM，非法则早退；合法路径不需要舍入 | `priority.json` 三条静态 RNE；新 IR 官方 smoke 39 完成路径含 36 退休、3 Illegal | 官方 smoke 证明可运行，不等于每条路径独立数值/不变状态证明；缺动态合法 RM 路由和 FRM5/6/7 三条独立状态样例 |
| `FCVT_S_BF16`：`F_BF16` boxed/未 boxed；`bf16_to_f32` 普通/inf/NaN，NaN 再分 quiet/signaling | boxed 有限数 `0x3fc0→0x3fc00000`、qNaN `0x7fc1`、sNaN `0x7f81`。qNaN 不置 NV，sNaN 累计 NV | 当前独立状态矩阵缺未 boxing、inf、±0、次正规和负号/payload 组合；既有 C++ NaN boxing 测试另有结果位回归，见第 5 节 |

`bf16_to_f32` 的 `signed(mant)>=0` 在 7 位尾数上检查 quiet 位为 0；配合 `is_nan`，仅 sNaN 产生 NV。NaN 输出固定 `0x7fc00000`，inf 保留符号，其余值尾数补 16 个零，转换完全精确，不应产生 NX/UF/OF/DZ。`rF_BF16` 的 boxing 失败回落为 BF16 qNaN `0x7fc0`，不能误用 FP16 canonical `0x7e00`。

窄化数值入口 [softfloat_symbolic_f32.sail](../../sail-riscv/model/extensions/FD/softfloat_symbolic_f32.sail) 使用 `fp32_to_bf16`，根据原始源的 NaN 分类选择规范 NaN；[异常库](../../sail-riscv/model/core/ieee_fp_exceptions.sail) 在 fp128 中比较原值与重建 BF16 值并屏蔽非有限源的算术 flags。最终 D 的 BF16 helper/legacy 具体数值分别只见 `1.5`、`1.0` 两个精确 RNE 样例；未知源五 RM 的单路径/SAT检查不包含与独立 oracle 的数值等价断言。此前隔离 C 的大量 BF16 差分属于对应旧候选范围，不能抵消当前指令状态的 UF/OF 缺口。

## 3. 四个向量 clause 的共享 guard 与控制分支

入口：[zvfbfmin_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfmin_insts.sail)、[zvfbfwma_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail)。四项编码都是固定操作，decoder 都要求 `get_sew()==16`；转换要求 Zvfbfmin/Zve32f，乘加另要求 Zvfbfwma/Zfbfmin。**它们没有通用 RVV funct enum 的全部 SEW 分支**，SEW8/32/64 应验证译码拒绝，而非直接构造 clause 后触发 `assert(SEW==16)`。

| 共享条件 / 分支 | 当前 BF16 定向证据 | 缺口或可达性界限 |
| --- | --- | --- |
| decoder 扩展开关及 SEW16 | 四项均有合法机器编码 | 四项非法 SEW、扩展关闭及依赖关闭无专用 decoder 证明 |
| `illegal_fp_variable_width`：`valid_vtype` | 正常 `vill=0` 的 e16,m1；VF 另 m4/m8 | 没有四项 BF16 的 vill 拒绝证明；应先区分可由 CSR 合法化产生的 vill 状态与手工注入异常 vtype |
| `valid_rd_mask`：vm=0 时 vd 不能为 v0 | VF/VV 有合法 vm=0；全部使用非 v0 目的 | vd=v0 且 vm=0 拒绝分支无专用样例 |
| `valid_fp_op`：FRM0–4 / FRM5–7 | 窄化、VV、VF 有五 FRM；VF 本轮非法 FRM5/6/7 | 两转换及 VV 的非法 FRM状态 proof 缺；扩宽转换虽数值精确，源码仍验证 FRM，不可宣称保留 FRM 对其无关 |
| `valid_eew_emul`：SEW×2/LMUL+1 在范围内 | VF m4→EMUL8 成功，m8→EMUL16 拒绝 | 其余三项 m8 拒绝、m4边界未独立测；四项合法分数 LMUL、m2、完整组末端均缺 |
| `valid_reg_overlap`：组对齐、无重叠/允许端部重叠/非法重叠 | 已有全部正向样例为对齐、不重叠组 | 未逐项覆盖失对齐、合法窄化低端重叠、合法扩宽高端重叠、禁止重叠、分数 EMUL 重叠；VV 有 vs1、vs2 两个独立检查 |
| `init_masked_result`：Ok / Err | 所有当前成功样例为 Ok | `get_start_element` 超界导致 Err→Illegal 无 BF16 专用证明；当前 V128、SEW16 源码界为 vstart>63，代码自身保留上界 TODO，不能以某个 `vstart>=vl` 正例代表该错误分支 |
| 每 lane `mask[i]` 活动/非活动 | VF 覆盖 vl0、全屏蔽、`vstart=vl=2`、跳过向量 sNaN 前缀；VV 有一个部分屏蔽 sNaN 例 | 两转换没有非活动 sNaN 例；VV 未分别测 vl0、全屏蔽、vstart跳过；所有成功 BF16 输入 vta/vma 均为 undisturbed，分数 LMUL 尾部也未测 |
| 写回、`set_vstart(0)`、Retire | 观察首个目的向量寄存器、full fcsr/vstart/mstatus 并求差异 UNSAT | 未观察目的组全部寄存器与所有非目标寄存器；扩宽 m1 有2个寄存器、m4有8个，现 proof 不能扩张为整个组和全机状态不变性 |

[vext_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_utils_insts.sail) 的 SYMBOLIC 路径在本配置用 `isla_init_mask`，普通 C++ 路径用 `init_masked_result_default`；二者均需按实际选用配置解释。普通路径当前对 tail/mask agnostic 也保留原目的值，这属于允许的选择之一；不同策略或全部 policy 组合没有被现 BF16 样例覆盖。

## 4. 四项向量数值与 flags 分支

| clause | 已证实的具体数值/活动分支 | 尚缺的具体反例域 |
| --- | --- | --- |
| `VFNCVTBF16_F_F_W` | 两 lane 精确有限数、活动 sNaN；正/负偶中点 × FRM0–4，NX 与旧 NV 累计 | qNaN、inf、±0、UF/OF阈值，屏蔽/尾部/前缀 sNaN不置NV，多 LMUL及完整目的组 |
| `VFWCVTBF16_F_F_V` | 两 lane 有限数精确扩宽、活动 sNaN→规范NaN并累计NV | qNaN/inf/±0/次正规，全部非活动组合，合法/非法FRM，其他LMUL |
| `VFWMACCBF16_VV` | 两 lane 有限乘加；一个源的活动sNaN；同一sNaN lane被mask；`1 + 1×2^-24` 正f32中点 × 五FRM | vs1与vs2分别单独sNaN、双sNaN、qNaN、累加器NaN、`0×inf`、无穷乘积加反号无穷、正负零抵消、UF/OF、负中点和能区分融合/分步舍入的样例 |
| `VFWMACCBF16_VF` | 有限两lane乘加；boxed scalar sNaN的活动/非活动；向量sNaN只在跳过前缀；未boxed scalar变qNaN不置NV；正f32中点 × 五FRM；m4合法边界 | scalar sNaN且首个活动lane位于非零索引、更多mask/vstart组合、标量与向量/累加器独立NaN/inf、融合舍入反例、UF/OF、负中点及完整宽目的组 |

VF 当前先纯计算 `(rs1_fflags, rs1_val)=bf16_to_f32(F_BF16(rs1))`；`rs1_flags_accrued=false`。只有进入首个活动 lane 才累计 scalar flags 并置 true，后续 lane 不重复；两个活动 lane 的已有样例触达 true/false 两侧。无活动 lane 时纯转换可执行，但不改 fflags。活动源向量转换和 `fp_muladd` 都在 mask 条件之内。

现有结果的数值预期合理：`1+2^-8` 是 BF16 的正偶中点，RNE/RTZ/RDN→`0x3f80`、RUP/RMM→`0x3f81`；负值在 RDN/RMM 时取 `0xbf81`，其余取 `0xbf80`。乘加的 `1+2^-24` 是 f32 偶中点，RNE/RTZ/RDN→`0x3f800000`、RUP/RMM→`0x3f800001`，均 NX。该乘积本身精确，因此它**不能区分 fused FMA 与先乘后加的实现**；源码确实调用 `fp_muladd`，完整融合语义仍需相应数值用例支持。

flags 累计使用 OR：旧 NX=1 再出现 sNaN 后应为 `0x11`；旧 flags=0 时活动sNaN为 `0x10`；非活动sNaN分别维持1或0。BF16 VF 的三种无活动原因均有旧 flags=0/1 的当前 IR证明。`vstart>=vl` 的已测具体值是**相等的2**，未覆盖所有严格大于状态。成功无活动向量指令仍写回原目的组并清 vstart，可令 VS/SD 变脏；“无活动不置 fflags”不能简写为“所有状态完全不变”。

首次审计发现累计 CSR 的观察存在掩盖效应：原BF16窄化/乘加RM包预置NV=1，所以完整fcsr相符仍不能检测本次运算错误新增NV；priority与多数vector NaN例预置NX=1，也不能检测该例错误新增NX。VF另有活动sNaN且旧flags=0，当时只有该组排除了其已测输入上的多余NX等位。随后按[第8节](#8-同轮追加清零初始flags的38条复验)对原NaN及全部五RM中点清初始flags复验，38/38通过，补上这些**相同数值输入**的flags可辨识性。原测试本身的掩盖属性没有改变，新证据也不替代其他未测NaN来源/inf/UF/OF域。

## 5. Illegal、断言与 C++ 证据的区别

旧 c9e1 IR 的 VF `assert(LMUL_pow_widen<=3)` 位于非法性检查前，真实 e16,m8 编码导致 `AssertionFailure`、runner退出101，证据是 [old_ir_red.stderr](tools/bf16_lmul/old_ir_red.stderr)。当前源码把 `illegal_fp_variable_width`/overlap 拒绝放到该断言前：同样 e16,m8 满足 `LMUL_pow_widen=4`，`valid_eew_emul` 为 false，返回 `Illegal_Instruction`。本次8条非法样例交叉 vm=0/1、vl=0/1、旧flags=0/1，并检查 vr16/full fcsr/vstart/mstatus保持；两条 e16,m4 正例检查精确结果和sNaN。

这8条得到的是 execute 层的架构拒绝结果，成功 runner/非法 runner 都把断言错误视为失败；断言没有被当作 Illegal 接受。证据不含顶层 trap entry 的 mepc/mcause/mtval 等状态转移，不能外推为完整陷阱流程验收。它也不意味着可以把所有内部断言都改为架构 Illegal：`get_sew_pow` 和 `get_lmul_pow` 的保留字段断言用于拒绝违反模型状态不变量的手工状态，正确入口应先经架构 CSR/vtype 合法化。

[test_bf16_wma_flags.S](../../sail-riscv/test/first_party/src/test_bf16_wma_flags.S) 与 [test_bf16_nan_boxing.S](../../sail-riscv/test/first_party/src/test_bf16_nan_boxing.S) 的当前模型 C++ V128/V256 回归见 [BF16 LMUL 记录](tools/bf16_lmul/README.md)。前者通过真实程序检查 VF 无活动旧flags0/1、部分活动规范NaN、前缀sNaN和VV mask；后者检查未正确 boxing 的 BF16→f32 结果位，但**没有检查 fflags**。两项均没有 e16,m8 编码，不能拿 C++ 两项通过代替 LMUL 十例。

普通官方入口的范围同样需保留：[旧 c9e1 官方77批次](official-continuation.md) 中 BF16 两标量退出0，四向量均触发60秒外限；本次审计开始前 d012 已归档的 BF16 官方证据为 `make solve-FCVT_S_BF16` 的39条路径 smoke。本轮主agent另起的当前IR官方批次以其最终报告为准，不能沿用旧批次时间/退出统计。55条定向成功或上面的71条状态样例均不证明四向量官方目标已完成，更不证明全部源码分支。

## 6. RV32 两条排除项的精确边界

`89 FD_FLOAT − 10 MEMORY交集 − 2个32位模式Zfa = 77` 是本议题选择 **RV64架构模式、非访存** 名单的口径。两个额外排除项是 `FMVH_X_D` 和 `FMVP_D_X`，不是 BF16 指令；四个 Zcf RV32访存项已经计入那10个访存项，不能再减一次。E定向状态证明固定Machine/MXL64；官方 `make solve-*` 会重新符号化特权/状态寄存器，日志确有VirtualUser初态，不能把E定向配置的Machine限定套用到官方整个符号域。77个名单项不等于官方入口对 `FD_FLOAT−MEMORY` 79项全部完成。

[zfa_insts.sail](../../sail-riscv/model/extensions/FD/zfa_insts.sail) 的两项 mapping guard 均为 `Ext_D & Ext_Zfa & in32BitMode()`。后者在 [sys_regs.sail](../../sail-riscv/model/core/sys_regs.sail) 定义为 `architecture(cur_privilege)==RV32`：编译XLEN32时恒为RV32；XLEN64模型则查询MXL/SXL/UXL。“排除2项”依据正常reset/CSR可达的64位架构模式范围，**不能改写为RV64 IR没有这两个函数或直接执行必然panic**。两个execute体没有再次检查该guard，直接构造clause会绕过译码的模式限制。

正常架构可达性还受CSR约束：`legalize_misa`使MXL只读固定本机XLEN；`legalize_mstatus`明确不支持动态改变SXL/UXL，reset时按本机XLEN初始化。因此当前模型的正常RV64 reset/CSR路径并不提供切入RV32的能力。手工注入SXL/UXL/MXL初态使`in32BitMode`成立，不能据此认定RV64硬件支持这些32位模式指令。VirtualUser/VirtualSupervisor分支报Hypervisor unsupported，不存在这里可用的HSTATUS切换路径。本审计未运行这两项RV64官方直接constructor目标，不给它们添加NoFunction、超时或panic的运行结论。

旧隔离证据目录为 `isla-float-rv32-20260926/test-run`，独立完整probe IR SHA-256 `7d8b5945a07872a3db02f168bb28dd1c9b09439a8a359f27a1e71ee14b5b506c`，不是d012。此次核对其manifest与probe IR、probe Sail、runner、配置、cases、results及最终日志的哈希，均一致；入口文件位于 [test/rv32_fp](../../sail-riscv/test/rv32_fp/)。

| 指令 | 实际编码→译码→执行样例 | 已证范围 |
| --- | --- | --- |
| `FMVH_X_D` | `0xe2108553`，f1=`0x89abcdef01234567`→x10=`0x89abcdef` | 真实反译constructor/字段；2条可行完成路径均退休，整数结果或任一fflags不同为UNSAT；旧flags1保持 |
| `FMVP_D_X` | `0xb2c58153`，x12=`0x89abcdef`、x11=`0x01234567`→f2=`0x89abcdef01234567` | 同样2条完成路径、64位写回与五flags差异UNSAT；拼接顺序是rs2高32位、rs1低32位 |

这些是对应独立 RV32 IR 的各一条具体语义样例。没有遍历所有寄存器、x0、源目的别名、关闭扩展或特权模式；没有在本轮 d012 上重跑，也没有公共 RV32 CLI 验收。当前 [isarch_main.rs](../../isla/src/isarch_main.rs) 的 RV32 `solve-state` 分支仍直接 `panic!("RV32 solve-state 暂不支持")`。四Zcf同包仅完成真实16位译码，真实访存未执行，继续留在独立内存议题边界。

## 7. 后续验收优先项

1. BF16负路径按六clause分清 decoder拒绝、execute Illegal及内部不变量断言；补静态非法RM、非法SEW/扩展开关、v0目的mask、组失对齐/重叠、vstart超界，其余三向量的m8边界。
2. BF16转换补 boxing失败的独立flags检查、±0/inf/subnormal、OF/UF阈值；VF/VV补NaN来源独立性、fused舍入反例、无穷无效运算，以及首个活动lane非零索引的scalar sNaN。
3. 每项向量覆盖合法fractional/m2/m4 LMUL及完整目的组观察；单独说明agnostic策略和架构可达的vtype边界。完成这些仍需按枚举表逐格确认，不能仅累计case总数。
4. 官方 `make solve-*` 的完整完成情况与独立数值/状态证明分别记录；RV32两Zfa继续注明独立IR和公共CLI限制。

## 8. 同轮追加：清零初始flags的38条复验

主agent要求补足前述flags可辨识性后，在仓库外新目录 `isla-float-bf16-cleared-flags-20260926.gbmc6mc4` 生成独立输入；下称 `CLEAR_STAGE`。没有改原始输入、生产代码、配置或IR。新输入只修改case名、初始fcsr低5位和预期fcsr低5位；FRM、高位、操作数、编码、观察寄存器与其余预期均保留原样。

预期新flags没有直接从受测输出取得：qNaN（含VF未正确boxing变成的qNaN）指定为0，sNaN指定为NV=`0x10`，有限非精确中点指定为NX=`0x01`。生成器检查原累计结果确为原sticky位与这一独立预期的OR；原始输入逐文件哈希记录于 `source-inputs.json`。同一d012 IR、同一成功runner和E配置运行后 **38/38 PASS、exit 0、7.125秒**；每例真实译码/反编码字段一致、唯一完成执行路径、`Retire_Success`，先SAT，再对原用例列定的全部目标及完整fcsr/mstatus/vstart预期求差异UNSAT。这里“全部”仅指各输入的观察集合，未扩大为全机寄存器观察。

| 原包与选择 | 新样例数 | 本次新增可辨识性 |
| --- | ---: | --- |
| `priority.json` 中两标量转换的qNaN/sNaN各一例 | 4 | qNaN结果为规范NaN且五flags全0；sNaN仅NV，排除旧NX位掩盖的多余NX |
| `bf16-vector.json` 的两转换sNaN与VV活动sNaN | 3 | 所选活动lane仅新增NV，排除多余NX/其他flags |
| `bf16-vf-extra.json` 的未boxed scalar qNaN | 1 | 规范f32 NaN，全部新flags为0，证明该值未被当sNaN或错误计NX |
| `bf16-rm.json` 全包，标量/向量窄化正负中点×五RM | 20 | 保留各模式结果位，仅新增NX，排除原NV sticky位掩盖的错误NV |
| `bf16-macc-rm.json` 全包，VV/VF正f32中点×五RM | 10 | 保留各模式结果位，仅新增NX，排除错误NV |

按clause计为 `FCVT_BF16_S` 12、`FCVT_S_BF16` 2、`VFNCVTBF16_F_F_W` 11、`VFWCVTBF16_F_F_V` 1、`VFWMACCBF16_VV` 6、`VFWMACCBF16_VF` 6。VF boxed scalar活动sNaN且初始flags0的证据已在原包，本轮没有重复生成这一例。

```sh
# 从仓库根目录执行；CLEAR_STAGE指新的仓库外输出目录。
python3 "$CLEAR_STAGE/make_cases.py"
"$IR_STAGE/isla-float-e-nonmem-runner" \
  "$IR_STAGE/ir/rv64d_final.ir" "$IR_STAGE/rv64-e.toml" \
  "$CLEAR_STAGE/cases.json" "$CLEAR_STAGE/results.json"
```

`CLEAR_STAGE/summary.json` 保存完整实际命令、退出码、秒数、六clause计数、所有受测产物哈希及原输入哈希，`run.log` 保存runner原始输出；源码和IR/runner/config哈希仍与第1节相同。

| 产物 | SHA-256 |
| --- | --- |
| `cases.json` | `e42f74d7c947a59e38d70d3e06290b0b4f3ffe47bdebcf0e3191727bea67d616` |
| `results.json` | `ed5d5e279c373ae6b0c47cf15473408f38fafd3b5d037338253de66b90dfb595` |
| `make_cases.py` | `c360c725d48c9495885f407a5dcb66f8a1a01a19f6f491c5f37ad369dfa545dd` |
| `run.log` | `5ca899ebab5bebcf71bfe198920eb239870119e2041fd1fdfa7035da042782fb` |

这次关闭的是指定输入上旧sticky位导致的观察盲点。没有新增NaN/inf/数值输入，没有补齐两向量转换qNaN、VV两个源各自NaN/累加器NaN、inf无效运算、OF/UF阈值或能区分融合/分步舍入的FMA样例；第2–4节其他分支缺口继续保留。
