# 仅浮点分支审查报告（2026-10-08）

**后续修复已交付（2026-10-08）**：当前分支`be1296b`已修复R1及R2；本文仍作为修前`d04883b`的审查证据保留。[提交与最终验证](fix.md)。


受审：`feat/float-only-20261008@d04883b`，基线 `7b7337b`。主审与独立 `gpt-6-astra high` 分别阅读源码；独审全程只读，未派生 agent。生产源码、分支和原工作区未修改。

**结论：浮点 helper 迁移与 BF16 无活动元素修复有效，但存在新增 P1 兼容性回归，不能验收为“原有行为全部保持正确”。默认 IR 另保留基线已有的 FS/SD 状态缺陷。语义确实发生变化，其中数值修正、BF16 修正和符号输入域扩展是有意变化。**

## 发现

### R1 — P1：删除全局分派后，仓库内其余 IR 的浮点调用全部缺少实现

位置：[executor.rs](../../.worktree/isla-float-only-20261008/isla-lib/src/executor.rs) 第1212–1214行；`scripts/run.mk` 第90、228行仍提供 `IR_FILE` 入口。

分支删除 `softfloat_dispatch/softfloat_call` 及执行器接线，但只更新默认 `rv64d.ir`。仍由 Git 跟踪的 `rv32d.ir` 有63个已声明而无普通函数体的 `riscv_*` helper；`ir/rv64d_v128_e64.ir`、`ir/rv64d_v256_e64.ir`、`ir/rv64d_v512_e64.ir` 各有67个。`zriscv_f32Add` 就在其中。基线可由专用分派实现，分支进入 `NoFunction`。

本轮在两版执行器中，给同一旧 IR 的外部测试副本附上相同普通包装器，调用 `riscv_f32Add(RNE,1.0,2.0)`，预期完整结果 `0x40400000`、flags=0：

| IR | 基线7b7337b | 分支d04883b |
| --- | --- | --- |
| `ir/rv64d_v128_e64.ir` | PASS，退出0 | `NoFunction("riscv_f32Add")`，退出1 |
| `ir/rv64d_v256_e64.ir` | PASS，退出0 | 同上 |
| `ir/rv64d_v512_e64.ir` | PASS，退出0 | 同上 |
| `rv32d.ir` | PASS，退出0 | 同上 |
| 分支新默认 `rv64d.ir` | 本轮未做该helper基线对照 | PASS，退出0 |

原始命令及退出码见 [probes.json](evidence/probes.json)，日志见 `evidence/{base,head}-add-*.log`，静态缺体清单见 [ir-audit.json](evidence/ir-audit.json)。这是新增回归，影响仓库自带且公共入口仍可选择的产物，不只是外部旧文件。

公共命令也已动态复现：`make solve-fd-nonmem FD_NONMEM_RV64=FLEQ_S IR_FILE=./ir/rv64d_v256_e64.ir`（其余预算同下文smoke）退出仍为0，却生成0条；日志明确报`riscv_f32Le_quiet`的`NoFunction`。错误不计最终失败是基线已有collector策略，但本分支新触发了它。不能以退出0验收。证据：[old-ir-smoke.json](evidence/old-ir-smoke.json)、[old-ir-FLEQ_S.log](evidence/old-ir-FLEQ_S.log)。

建议：在移除全局分派的交付边界内一并迁移仍受支持的 IR，并加入实际执行回归。如果这些 IR 有意退役，应显式调整入口、文档和兼容性检查；当前分支没有做到。单独测试默认新 IR 不能证明全局删除安全。

### R2 — 基线遗留：快速 FPR 写回仍漏掉 FS/SD Dirty 更新

位置：[rv64d.ir](../../.worktree/isla-float-only-20261008/rv64d.ir) 第32638–32653行。快速 `set_F_bits` 直接 `zwF_from_vector`，没有普通 `wF` 的扩展断言、原值 callback 与 `dirty_fd_context`。FD 配置默认启用 `__isla_vector_fpr=true`。

本轮对实际默认 IR 执行 FADD.S `1.5+2.0`，设置 fcsr=0、FS=Initial、VS=Dirty，即 mstatus=`0x2600`：

- 普通 FPR 路径：f0=`0xffffffff40600000`、fcsr=0、mstatus=`0x8000000000006600`，正确。
- 快速 FPR 路径：相同数值结果及flags，但 mstatus仍为`0x2600`，错误。
- FS=Clean（`0x4600`）同样漏更新；直接调用 `set_F_bits` 也复现，故不只是指令外围问题。
- 基线与分支的12个状态探针均为6通过、6失败。失败包括上述合法 Initial/Clean 状态的4例，以及构造 FS=Dirty但SD=0的2个raw状态探针；后两例不作为合法状态域的主要证据。

证据：[head-state.log](evidence/head-state.log)、[base-state.log](evidence/base-state.log)。两版该 helper 在去源码位置与自动形参编号后完全相同。现行 d012 哈希也与 [已有FD红例](../float_support_review/solve-fix-fd-state.md)一致；后续修复源码/候选 IR 没有进入本分支。

**这不是新增回归。** 它说明本分支达到“从指定基线整理浮点专用提交”的狭义目标，仍没有达到长期计划的“浮点指令状态正确”目标。FS/VS=Dirty 见证偏好通常选择已有Dirty输入，会使此缺陷在默认 smoke 中更难暴露。不能用 helper 数值测试或预先Dirty的指令样例代替状态检查。

## 有意语义变化及效果

| 变化 | 审查及动态证据 | 判断 |
| --- | --- | --- |
| 旧专用浮点分派 → 普通 Sail helper | 35旧向量通过；新增327例覆盖67个迁移helper，全部完整结果/五位flags差异UNSAT且恰好一条路径 | 对所测输入迁移有效；不证明任意输入全域等价 |
| FEQ 的 NaN 异常规则 | 旧分派Eq对qNaN也置NV；新增三格式qNaN/sNaN及正负零用例均符合独立SoftFloat | 有意修正语义，不是逐位保留旧错误 |
| `VFWMACCBF16_VF` 标量sNaN的flags累计时机 | `vl=0`、全mask、`vstart>=vl`、旧flags非零无活动、活动及旧flags非零活动共6例；基线4败2过，分支6过 | 修复有效：无活动元素不新增NV，活动元素仍累积NV，保留旧flags |
| BF16非法LMUL处理 | 静态确认 guard 前移到位宽断言前 | 有意由断言失败改为Illegal；本轮未动态测该非法LMUL边界 |
| fcsr符号化 | `RV32/RV64::reg_list`新增fcsr；既有测试验证frm/flags不固定及初态保留 | 扩大输入域，符合目标；真实指令副作用仍须另外验证 |
| 终态FS/VS=Dirty见证偏好 | SAT才assert，UNSAT/Unknown不增加该约束；既有collector测试验证16个固定组合及无约束偏好 | 改变代表见证及输出分布，未发现删掉执行可行路径；不保证全状态采样覆盖 |
| 新非访存FD入口 | 77项名单与Make筛选吻合；4项make smoke有最终JSON及可编码gen | 入口有效，不代表77项全部完成 |

BF16探针输入：V128/E64，SEW16/LMUL1，vs2=v4、rs1=f1、vd=v8，标量boxed sNaN=`0xffffffffffff7f81`，向量初值零，frm=RNE。检查真实`zexecute`返回Retire及最终fcsr，不只调用helper。未检查完整VPR/全机post或硬件差分。详见 [probe.rs](evidence/probe.rs)、[head-bf16.log](evidence/head-bf16.log)、[base-bf16.log](evidence/base-bf16.log)。

静态IR比较：基线1903函数→分支2049函数，新增146、删除0；去位置及自动形参编号后，1902个既有函数体一致，仅`zexecute`不同。独审进一步排除临时编号和跳转地址漂移后，定位到`VFWMACCBF16_VF`上述两处变化。此比较有助于缩小范围，**不是控制流同构或全IR语义等价证明**。FD配置移除的`__isla_always_aligned`在两版IR中都没有对应寄存器，未见该删除改变有效对齐语义。

## 现有测试是否切题

- **10项原语测试切题**：具体/符号/MixedBits输入、错误sort、128位、符号RM、ITE、FMA单次舍入；检查注册表本身只能证明接线，其他数值断言才提供功能证据。
- **35例legacy测试切题但不足**：覆盖原20个有数值断言的测试、15个helper，完整结果及所有flags的检查比原局部flag断言更强。遗漏FEQ、其余迁移helper、真实写回与其他IR。本轮补充327例覆盖67个迁移helper和状态/兼容性探针。
- **fcsr测试切题但层次有限**：其中OR写回是测试自身构造，证明状态表示和初态保存，不能证明Sail实际指令正确累计或更新Dirty。
- **collector测试有价值**：经过真实collector，验证固定FS/VS约束不被覆盖。但测试encoder恒返`0x53`，不能证明真实Sail编码守卫与初态相容或编码后实际执行一致。
- **MRET/BF16 smoke不足以验收全分支**：MRET是非浮点回归；FCVT.S.BF16不覆盖BF16向量乘加、FADD Dirty、其他IR或完整77项。仅检查退出0尤其不充分。

## 本轮验证

执行脚本与日志均在 [evidence](evidence/)；[checks.json](evidence/checks.json)、[probes.json](evidence/probes.json)、[smoke.json](evidence/smoke.json)保存实际命令、配置、退出和耗时。

| 检查 | 结果 |
| --- | --- |
| `cargo fmt --all -- --check`、默认`cargo check -p isla --bin isarch` | PASS |
| 精确分支generic float测试 | 10/10 PASS |
| 精确分支isla库及isarch bin | 68＋25 PASS；明确跳过基线已有`rv64_target_trait`失败，不计全库PASS |
| 旧legacy回归 | 35/35 PASS |
| 新独立SoftFloat差分 | 327/327 PASS，67helper；三格式NaN/零、五RM、整数/格式转换、两种ROD、BF16 |
| 旧IR兼容性A/B | 基线4/4 PASS；分支4/4 FAIL（NoFunction） |
| FPR Dirty A/B | 两版均6/12 FAIL，证明遗留缺陷 |
| BF16 scalar sNaN活动性A/B | 基线4/6 FAIL；分支6/6 PASS，证明修复效果 |
| 最终`make solve`入口smoke | 退出0；MRET4、FCVT.S.BF1639、FLI.S32、FLEQ.S16 gen |

最终入口使用独立的`git archive d04883b`源码副本，运行：

```sh
make solve-MRET solve-fd-nonmem \
  'FD_NONMEM_RV64=FCVT_S_BF16 FLI_S FLEQ_S' \
  THREADS=1 ITRACE=1 OUTER_TIMEOUT=60s SOLVE_TIMEOUT=50s \
  SMT_TIMEOUT=20s TASTIC=qfaufbv
```

受测默认IR SHA-256=`d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`；FD配置SHA-256=`20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`。原工作树output未覆盖，最终四组JSON和日志封存在 [smoke-cases](evidence/smoke-cases/)；没有检查这些输出的硬件重放或所有汇编文本有效性。

Rust/Cargo 1.93.1。动态链接实核：debug测试/对照探针Z3=4.13.3，release make运行器Z3=4.16.0；不能用PATH中`z3 --version`代替二进制实际库版本。哈希和工作树清洁性见 [after.json](evidence/after.json)。额外数值预期来自既有独立SoftFloat oracle二进制，哈希见 [extra-oracle.json](evidence/extra-oracle.json)，生成输入与预期见 [generate_extra.py](evidence/generate_extra.py)、[extra-cases.tsv](evidence/extra-cases.tsv)。

保留早期无效测试记录：第一版旧IR探针直接用`execute_ir_function`调缺体helper，在harness自身unwrap处panic；已改为普通wrapper后重跑，该早期panic不作为R1证据，记录在`*-initial.log`及`probes-initial.json`。第一次make后的统计脚本误读`return`而非`ret_val`，没持久化make退出码；修正后重新执行，以最终`smoke.json`为准，旧日志保留。

本轮没有跑全77项、全isla-lib、RV32完整指令入口、完整源码branch覆盖或硬件差分；不能转记其他候选IR的历史PASS。受审分支仍干净、原isla工作区状态不变；没有修复、提交或push。下一步优先解决R1的多IR交付边界，再决定是否把已有FD状态修复纳入这条分支并复验。
