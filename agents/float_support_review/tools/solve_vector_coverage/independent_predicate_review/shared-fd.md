# 共享 FD 控制与 BF 精确入口排除

2026-09-27，限定冻结 `1dcc8081…` IR、`aa069e7f…` actual SharedState 和默认配置 `20851fdb…`。本补件保留原 31-site 与 overlap 证书，不修改其文件或 SHA。

## 已核结果

| 证书 | 结果 | 边界 |
| --- | --- | --- |
| `shared-fd-control.json` | 5 个短路因子、4 个语义谓词、1 个 RM mapping 静态 PASS；6 个负控拒绝 | 只给静态源表达式与实际 CFG 的对应，动态 caller/phase/config 由 owner 补齐 |
| `shared-fd-exclusions.json` | 30 条 BF 精确 caller/config 排除 PASS；4 个负控拒绝 | 12 条 hartSupports F、12 条默认 misa.F、6 条成功译码后的 encode FS；不增加动态命中 |
| `cfi-review.json` | 当前 CFI 6-site / 15 局部义务证书审定 PASS；2 个额外负控拒绝 | 同一个 FVFMATYPE 实际 decoder caller，Machine/User/Supervisor 与固定默认 CSR 域 |
| `shared-rm-domains.json` | 17 条 RM 精确实参域排除 PASS，48 个 selector 有限输入与 2 个 decoder infallible 前提；3 个负控拒绝 | 只排两条 scalar BF execute 根下的内部 RM 调用与直接 `execute:51088`，不增加动态命中 |
| `vector-fixed-capabilities.json` | V P1 的 9 个固定能力谓词、554 条精确 caller 排除 PASS；2 个负控拒绝 | actual IR 的 Full 向量支持与正常 typed 返回；FS/VS 保持变量 |
| `vector-state-domains.json` | V P1 的 251 条条件排除 PASS；1 个负控拒绝 | 231 encode 成功译码状态前提、20 decode 关联前提；另 1 条 537 false 待实际见证 |
| `scalar-fd-predicates.json` | 共享 FD 原 catalog 的 23 个语义谓词与 21 个短路因子静态 PASS；3 个负控拒绝 | 13 个正常布尔 CFG、10 个能力常量；具体 caller/config 另核 |

完整结果位于 `isla/target/float-support-review/final-coverage/vector/independent-predicate-review/`；冻结 SHA 与工具 SHA 见 [shared-fd-evidence.json](shared-fd-evidence.json)。全部报告保持 `source_branch_closed=false`。

## FD 静态证明

[shared_fd_control.py](shared_fd_control.py) 对 `valid_rounding_mode`、`select_instr_or_fcsr_rm` 的内部条件及 `currentlyEnabled(Ext_F)` 逐实际指令穷举布尔真值表，核 LHS、短路常量、RHS callee/实参、join 与返回值。异常分支单列为 `Arbitrary`，不当作普通布尔返回。

冻结 IR 中 `hartSupports(F)`、`hartSupports(Zicsr)` 与委托的 `currentlyEnabled(Zicsr)` 正常返回 true；F 整体仍保留 `misa.F` 和 `mstatus.FS` 两项动态输入。RM 六个枚举的五个生成函数共审查 34 个合法域输入；`backwards_infallible` 的前提为 `backwards_matches=true`，不声称它对 5/6 两个域外输入做拒绝。

[scalar_fd_predicates.py](scalar_fd_predicates.py) 扩展到共享 FD 原 catalog 的全部 23 个语义谓词，保留原 global key。D 的四个因子、haveSingle/Double/Half 的 OR、Zfh/Zfhmin/Zhinx/Zhinxmin/Zfa/Zfinx/Zdinx 链均逐正常 CFG 全真值表核对。OR 真臂写 true 并跳过 RHS，假臂才计算 RHS；D capability 中 `constraint(ext_d_supported)` 实际为 `zhartSupports:12` 的 literal true 条件，也单列该固定短路因子。`flen` 的整数窄化由实际初始化64支撑。misa 和 FS 保持运行期原子，不把基线输入当作全域常量。

## 30 条 BF 排除

[shared_fd_exclusions.py](shared_fd_exclusions.py) 消费 owner 的 80 条精确义务表。另 50 条动态见证留给 owner 合并。默认 916 个输入的 input/result/init 分别与 4 份严格审计 SHA 绑定，核实际 R1 状态、配置和真实初始化 `misa=0x800000000034112f`；实际 `_get_Misa_F` 取 `bits[5]`。

6 个 encode FS 排除都要求：同 word 的真实 decoder 成功返回该 BF constructor，encoder 使用同一个 decoded 值和同一前态，两阶段均静态纯读。每个 BF constructor 的唯一构造点受其本 clause 的 extension guard Call 支配；禁用该扩展时实际 CFG 返回 `None`，且之后不能再到该构造点。另对 Zfbfmin、Zvfbfmin、Zvfbfwma、Zve32f 的实际布尔 CFG 穷举，证明启用 BF 必须启用 F，而 F 为 true 要求 FS 非零。

**decode 中 FS=false 仍可达。** 直接构造 constructor、另行修改 CSR 或换配置不满足这六项 encode 排除的前提。

## BF RM 实参域

[shared_rm_domains.py](shared_rm_domains.py) 逐实际指令运行六个 instruction RM 枚举与全部八个 FRM 的 48 种组合。内部 `select:15` forwards 始终接受常量 DYN；`select:40` backwards 只接受 0..4；选择器成功返回的 Some 值只有 RNE/RTZ/RDN/RUP/RMM。直接 `execute:51088` 的参数来自 `execute:51077` 的 Some 解包，并受相应分支支配，因此不含 DYN。

两条 decoder infallible Call 分别与 `matches` Call 使用同一个 bits3 实参。编译器将短路结果写入临时变量，单纯删除一个 CFG 真边不能证明前提；工具保守分叉未知条件，并传播 RM matches=false，所有路径都到 None，无法进入 infallible。保留前提 `matches=true`，不将 5/6 输入视为 infallible 自行拒绝。

证书还核实际 `Fcsr_FRM` getter 为 bits[7:5]，两条 scalar BF clause 到 select 前的 FCSR 不写闭包，以及只读寄存器 builtin 和冻结 primop 源码。owner 可把此证明与实际 FRM=6/7 的入口和完整布尔真值表结合登记 RHS 语义值；不能添加不存在的末项 Jump。

## CFI 审定

[cfi_review.py](cfi_review.py) 消费向量 owner 冻结的三特权完整 trace 证书，独立复核所选 typed 返回链、实际 CSR 零值和排除前提。实际 MLPE getter 取 bit10，两项 LPE getter 取 bit2，`bool_bit_backwards(0)=false`；与三条实际 decoder 的 false 消费一致。

虚拟态排除有公共 R1 的静态依据：冻结 `Target::constrain_pre_state` 仅在 `supports_h && supports_s/u` 时加入 VirtualSupervisor/VirtualUser，并约束允许枚举的析取。实际 `hartSupports(H)` 为 literal false。因此六个虚拟态拒绝运行作为负控；静态域约束支撑通用排除。绑定初始化和 canonical 入口保持三项非 Target CSR 为零，LPE=true 不属于该域。三种特权的完整 decoder 序列不同，不能据此宣称全 decoder 等价。

## 复跑

将 `IR_STAGE` 指向冻结 `isla-float-solve-fix-final-20260926.GThshy`，`SIDECAR_STAGE` 指向冻结 runtime catalog，`CATALOG_STAGE` 指向共享 source catalog。

```sh
REVIEW_TOOLS=agents/float_support_review/tools/solve_vector_coverage/independent_predicate_review
COVERAGE_STAGE=isla/target/float-support-review/final-coverage
REVIEW_STAGE="$COVERAGE_STAGE/vector/independent-predicate-review"
python3 "$REVIEW_TOOLS/shared_fd_control.py" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --manifest "$IR_STAGE/source-manifest.json" \
  --model-root "$IR_STAGE/model" --references "$CATALOG_STAGE/scalar/shared-bf16-references.json" \
  --factors "$COVERAGE_STAGE/bf16/shared-fd-five-factors.json" --output "$REVIEW_STAGE/shared-fd-control.json"
python3 "$REVIEW_TOOLS/shared_fd_exclusions.py" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --manifest "$IR_STAGE/source-manifest.json" \
  --model-root "$IR_STAGE/model" --coverage-root "$COVERAGE_STAGE" --output "$REVIEW_STAGE/shared-fd-exclusions.json"
python3 "$REVIEW_TOOLS/cfi_review.py" \
  --report "$COVERAGE_STAGE/vector/cfi-three-privilege-source-witnesses.json" --freeze "$IR_STAGE" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --output "$REVIEW_STAGE/cfi-review.json"
```

## V P1 状态域

[vector_fixed_capabilities.py](vector_fixed_capabilities.py) 读取冻结 IR 的 `vector_support_level=Full` let，并核该 let 不被运行期改写。实际整数比较、能力枚举转换和 `hartSupports`/`currentlyEnabled` 正常调用路径给出 9 个固定 LHS，排除 554 条精确 caller 的 false 方向。

[vector_state_domains.py](vector_state_domains.py) 枚举 FS 0..3 与 VS 0..3 的 16 个位域投影，逐实际 getter、Call 和比较证明五项浮点向量扩展启用恰要求 FS/VS 均非零。其它 mstatus 位不进入此闭包。对未知 enum/数值条件保守分叉后，22 个唯一 constructor 的首 guard 在 FS 或 VS 为零时都走 None。成功真实译码同 constructor、同 word，加上同前态 encoder 与两阶段纯读，支撑 231 条 encode 排除。20 条 decode 排除来自 Zve64d 内较早的 Zve64x 成功蕴涵后续 Zve32x 为真，未将 decode FS/VS 固定为基线值。工具绑定默认实际 TOML、所有 2,509 个初态 R1/init/result 和 runner 源码。

`VFNUNARY0` 的 decode `currentlyEnabled:537 false` 不作排除：`FNV_CVT_F_F`、SEW16、FS0、VS1 可达。此证书以旧前沿保留该项；owner 后续实际 narrow1 见证须按完整键消费与去重。以上静态推理不增加动态 case 或 hit。

```sh
python3 "$REVIEW_TOOLS/vector_fixed_capabilities.py" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --freeze "$IR_STAGE" \
  --input "$COVERAGE_STAGE/vector/actionable-default-frontier.json" \
  --output "$REVIEW_STAGE/vector-fixed-capabilities.json"
python3 "$REVIEW_TOOLS/vector_state_domains.py" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --freeze "$IR_STAGE" \
  --input "$COVERAGE_STAGE/vector/actionable-default-frontier.json" \
  --fixed "$REVIEW_STAGE/vector-fixed-capabilities.json" \
  --phase-purity "$COVERAGE_STAGE/integration/phase-purity-binding.json" \
  --entry "$COVERAGE_STAGE/scalar/entry-invariants-v2.json" \
  --output "$REVIEW_STAGE/vector-state-domains.json"
```

## BF 新共享短路与 FDVoff 补件

[bf_vector_control_domains.py](bf_vector_control_domains.py) 按 BF 新 73 条 pending 表独核 32 条 currentlyEnabled caller：24 条 fixed（PC340/349/376），8 条成功同 BF constructor 译码后的 encode 状态条件（PC361/385）。两项 BF 向量扩展在实际 16 种 FS/VS 投影下启用均恰要求二者非零。旧 371 项证书的 root key 不充当这批新义务的动态见证。decode FS1/VS0 能到 361 false，作为禁止跨 phase 排除的负控。

[bf_fdvoff_review.py](bf_fdvoff_review.py) 审定 owner 的 v2 候选，并逐字节重放相同候选：完整 actual 当前启用函数、Misa_F getter 和 decoder body 比较，实际初始化与六例 R1，完整严格 Jump 审计、父纯读绑定、每 root 三项零写字段均通过。另核 summary PASS、退出 0 和六例完整数量。F 必须为零与配置域替换两个负控均拒绝。结论仅为指定 FDVoff 域中六个 BF constructor 不可成功译码；不声称所有 word 都为 None，不迁移到 default/Voff。

```sh
python3 "$REVIEW_TOOLS/bf_vector_control_domains.py" \
  --input "$COVERAGE_STAGE/bf16/shortcircuit-proofs/run-20260926T193221Z/shortcircuit-review.json" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --freeze "$IR_STAGE" \
  --fixed "$REVIEW_STAGE/vector-fixed-capabilities.json" \
  --bf "$REVIEW_STAGE/shared-fd-exclusions.json" --state "$REVIEW_STAGE/vector-state-domains.json" \
  --output "$REVIEW_STAGE/bf-vector-control-domains.json"
python3 "$REVIEW_TOOLS/bf_fdvoff_review.py" \
  --candidate "$COVERAGE_STAGE/bf16/fdvoff-constructor-rejection-candidate-v2.json" \
  --output "$REVIEW_STAGE/bf-fdvoff-review.json"
```

新工具拒绝覆盖既存结果；复跑应选择另一个输出目录，旧冻结证书保持原样。

## BF 新分母的 38 项 typed 排除

[bf_short_typed_domains.py](bf_short_typed_domains.py) 对新表重新绑定 14 个 overlap、12 个 valid_eew_emul、8 个 valid_fp_op 与 4 个 illegal_fp_variable_width 精确 caller。overlap 的 14 项由实际相邻 LMUL 实参固定外层分支，因而内部短路不可达。另 3 项 `51403/119 true`、`51620/109 true`、`51620/52 true` 保留真实见证义务。

24 项 typed 排除重新为四个 BF constructor 跑完整 decoder Bool 固定点，未知指令位和扩展结果保守分叉，成功构造的 SEW 上界均只有 16。公共 R1 的普通 vtype 低 8 位与 canonical vill 域分开：后者的实际 SEW getter 为 8，无法成功译码这些 BF constructor；前者的实际 valid_vtype 为 true。工具核同 decoded/regs 的 execute、vtype 全阶段不写闭包，以及新四个 illegalwidth root 的唯一支配实参定义，得到 EEW32 与 LMUL+1。前置 LMUL 故意使用更宽 signed3 域 -4..3；不借 execute 后置 LMUL<=2。保留 LMUL3→扩宽非法、域外 SEW128 和允许 vill 的负控。

该工具复用 V typed 工具的完整 decoder 固定点与不写分析，并绑定依赖文件 SHA；旧 BF371 root key 不作为新命中。全证书仍限定 `1dcc`，不自动迁移到新的 IR。

```sh
python3 "$REVIEW_TOOLS/bf_short_typed_domains.py" \
  --input "$COVERAGE_STAGE/bf16/shortcircuit-proofs/run-20260926T193221Z/shortcircuit-review.json" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --freeze "$IR_STAGE" \
  --fixed "$COVERAGE_STAGE/vector/default-fixed-cfg.json" \
  --overlap "$REVIEW_STAGE/overlap-arguments.json" --bf-entry "$REVIEW_STAGE/shared-fd-exclusions.json" \
  --output "$REVIEW_STAGE/bf-short-typed-domains.json"
```

## scalar 五因子与 V conversion encode21

[scalar_five_factors.py](scalar_five_factors.py) 对原 scalar 五个待审源码因子完成全表达式真值表：`validDoubleRegs:7`、`execute:7556/7605` 的 D move 断言、`fcvtmod_helper:23/52`。每个 AND 的源 LHS、false 常量、RHS 与 join 均核对实际全部指令。`exp`/`mant` 绑定 fsplit_D 实际 tuple 字段和 11/52 位声明，`zeros` 绑定同宽 builtin。三个负控在同步修改候选副本后仍被语义审查拒绝。只交静态对应关系，完整 caller 动态消费另核。

[vector_conversion_encode.py](vector_conversion_encode.py) 将状态证书条件明确应用到 VFWUNARY0/VFNUNARY0 的两个实际 encode root（18778/18851），排除 21 个 currentlyEnabled LHS false 因子。逐个重新核实际 Call 支配 Jump、字面 extension、源码词法操作数和完整 AND 表达式正常 CFG，再消费成功同 constructor decoder⇒FS/VS 均非零及九个正状态投影。15 个 decode 方向完全保留；极性互换与撤销成功 decode 条件的负控均检出。

```sh
python3 "$REVIEW_TOOLS/scalar_five_factors.py" \
  --input "$COVERAGE_STAGE/scalar/default/five-factor-review-input.json" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --freeze "$IR_STAGE" \
  --output "$REVIEW_STAGE/scalar-five-factors.json"
python3 "$REVIEW_TOOLS/vector_conversion_encode.py" \
  --input "$COVERAGE_STAGE/vector/conversion-encode21-state-candidates.json" --freeze "$IR_STAGE" \
  --output "$REVIEW_STAGE/vector-conversion-encode21.json"
```

## scalar 新增 11 谓词 / 12 因子

[scalar_control_addendum.py](scalar_control_addendum.py) 单独审定 v2 库存新增项：haveHalfMin、currentlyEnabled 的 Zvl32b/Zve32x/Zve32f/Zvfh/Zfbfmin 六个完整 Bool CFG，另五个实际 hartSupports 固定返回。新增 12 个短路因子包括 haveHalfMin 的两个 OR 与两个 hart 的 ELEN 整数比较；后者保留源码 `sizeof(elen_exp)>=5` 与冻结 IR 特化 6>=5 的关系。源码正文、原 global key、分派/return 链和完整表达式真值表均绑定。Full 不写域复用已审证书，VS/F 等状态子表达式保持原子。OR false 常量变异与 ELEN 阈值变异两个负控被拒绝。

旧 FD23 证书适用范围未变；此件不声称完成 112 encdec guard 的正常接受/拒绝 CFG 或动态 caller 消费。

```sh
python3 "$REVIEW_TOOLS/scalar_control_addendum.py" \
  --input "$COVERAGE_STAGE/scalar/shared-control-catalog-v2.json" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --freeze "$IR_STAGE" \
  --fixed "$REVIEW_STAGE/vector-fixed-capabilities.json" \
  --output "$REVIEW_STAGE/scalar-control-addendum.json"
```

## scalar 112 encdec guard

[scalar_encdec_guards.py](scalar_encdec_guards.py) 对 112 个源码 `when` 的 decode/encode 两阶段分别核完整正常布尔真值表，共 224 个阶段实例；60 个源码短路因子共形成 120 个阶段实例，LHS 两方向、AND/OR 极性与 skip 常量均逐项核对。异常后继单列到 `Arbitrary`。v2 库存补全的表达式正文与冻结源码一致，原 global key 保持不变。

每个 guard 按紧邻的三行 mapping 声明重新绑定：decode 接受路径的 constructor 绑定到本声明的完整 SourceLoc，并写同一局部结果为 Some；拒绝路径写 None。encode 的 constructor Kind、编码表达式 SourceLoc 和当前声明相同，接受后的块无未核分支，其唯一编码结果赋值直接沿 Goto 到公共 return；拒绝路径跳过本 mapping 并继续分派。因此 decode 的 None 仅指本 mapping，encode 的 guard false 不能解释为整个 encoder 拒绝。完整位编码语义与 decoder/execute 分派链联立仍是独立义务。

`validDoubleRegs` 的向量列表保留源码原文和实际 Call 参数，不把底层 vector update 的物理次序改称源码列表次序。冻结 helper 的 21 条指令完全不读写两个形参，唯一正常 End 必经 literal true 返回，实际 xlen=64；据此允许抽象列表内容与次序。vector init 大小、更新索引的范围、唯一性和完整性仍逐项检查。

五个负控分别改动 guard 极性、同名 constructor 的 mapping 源行、encoder 结果后的 return 路径、向量更新索引及 helper 参数读取，均在指定检查处拒绝。正式证书 `scalar-encdec-guards.json` SHA 为 `ea01a58b6e9cfd9917a6b930ab6da992aa0c81ddc08fee85bf878371ed18fc09`；初版候选保留为 `scalar-encdec-guards-candidate-before-disposition-strengthening.json`，不用于消费。全部限定旧 `1dcc` IR，`source_branch_closed=false`；不迁移到后续 IR。

```sh
python3 "$REVIEW_TOOLS/scalar_encdec_guards.py" \
  --input "$COVERAGE_STAGE/scalar/default/encdec-guard-review-input.json" \
  --catalog "$COVERAGE_STAGE/scalar/shared-control-catalog-v2.json" \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" --freeze "$IR_STAGE" \
  --output "$REVIEW_STAGE/scalar-encdec-guards.json"
```

该命令已以冻结输入执行，退出 0。复跑须选择新的输出路径；正式证书拒绝覆盖。
