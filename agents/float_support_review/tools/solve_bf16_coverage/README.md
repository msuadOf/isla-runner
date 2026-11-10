# BF16 六 clause 定向覆盖包

源码覆盖的阶段结果与精确版本见 [BF16 覆盖记录](../../solve-fix-bf16-coverage.md)。`proof_contracts.py` 提供源码语义键和新版本消费门禁；PC 只属于版本证据。`scoped_contract_ledger.py` 按 BF 自己的引用核全局前沿，并保留未建立 caller 义务的 source site；`rhs_contracts.py` 独立登记正常 RHS Bool 与异常候选，可消费已审返回数据流。两种账本命令的完整参数见 `--help`，输入文件路径和 SHA 保存在结果 `artifacts` 中，输出使用排他创建。`not_lowered` 需完整 runtime inventory 与变换审查；不等于源码 arm 已闭合。

工具测试按文件隔离 Python 模块路径，避免 BF 与 scalar 的同名消费器导入冲突：

```sh
for test in agents/float_support_review/tools/solve_bf16_coverage/test_*.py; do
  python3 "$test" || exit 1
done
```

合同字段校验不能替代证据文件 SHA、实际调用/CFG/域重验及新版 trace 严格审计。

`scoped_runtime_inventory.py` 对范围账中未建 caller 的引用，重新核实际源码、manifest/generation、完整 sidecar 和全部 root Call，再列源码声明宿主、token 共址 Jump 与 raw 调用闭包分类。输出是候选库存，缺共址不能单独证明 `not_lowered`。`rhs_dataflow.py` 流式消费已审完整 trace，按无环正常路径、局部赋值与布尔否定找 RHS 的实际消费 Jump；未知运算丢弃标签，局部引用逃逸、异常出口及重复调用实例拒绝。RHS 输出也须独审后才能消费，命令参数均见 `--help`。

`rhs_candidate_index.py` 核全部候选依赖文件 SHA、原义务、完整 root 与值身份，生成候选索引并保留原证明状态。`source_rebinding_inventory.py` 为新候选准备源文件身份表：同字节项等待 runtime 重绑定，源文件改变的项须另审语义及新跨度；generation 的声明不代替集成来源桥和严格运行 gate。两个工具也使用新输出文件，不覆盖旧证据。

本目录保存输入生成器、运行入口及证据校验工具。生成输入、SoftFloat 参考值和运行日志写到仓库外的新目录；最终审计 JSON 还可写入已授权的 `isla/target/float-support-review/final-coverage/bf16/`，避免占用临时文件系统。当前固定 IR 为 RV64、VLEN128、ELEN64、`Fcsr_RM_Illegal`。六项为 `FCVT_BF16_S`、`FCVT_S_BF16`、`VFNCVTBF16_F_F_W`、`VFWCVTBF16_F_F_V`、`VFWMACCBF16_VV`、`VFWMACCBF16_VF`。

## 构建参考 oracle 与译码负例 runner

从仓库根目录执行。SoftFloat oracle 源码及编译方式见 [oracle](../../oracle/README.md)。译码 runner 源码复用 [negative_runner.rs](../e_scalar_cases/negative_runner.rs)，Cargo 依赖模板见 [negative_runner_Cargo.toml](../e_scalar_cases/negative_runner_Cargo.toml)。译码 runner 须用与受测 IR 配套的 `isla-lib` 编译；目前 d012 固定件可用原 E scalar 产物。重新生成 IR 后，优先使用同批重建的三 runner。

```sh
ORACLE_BUILD=$(mktemp -d)
cmake -S agents/float_support_review/oracle -B "$ORACLE_BUILD" -DCMAKE_BUILD_TYPE=Release
cmake --build "$ORACLE_BUILD" -j 12

STAGE=/path/to/ir-stage
DECODE_RUNNER=/path/to/negative-runner
OUT=$(mktemp -d)
python3 agents/float_support_review/tools/solve_bf16_coverage/run.py \
  --stage "$STAGE" --decode-runner "$DECODE_RUNNER" \
  --oracle "$ORACLE_BUILD/oracle" --profile baseline --out "$OUT"
```

`--profile baseline` 重现 d012 旧 FPR dirty 语义。`--profile final` 对新样例采用合法 Clean FS/VS 初态，并要求成功标量 FPR 写回置 FS Dirty/SD；新增向量例分别观察 VS Dirty 与新浮点 flags 对 FS 的影响。38 条旧清 flags 输入从五个既有 JSON 按固定选择和独立 flags 规则重建，不依赖历史 `/tmp` 文件，也不改原输入。final 对其中 14 条成功标量旧例只迁移 `mstatus` 预期，具体逐例前后值保存在 `migration.json`。旧 LMUL 十例保留原初态和预期。

三个输入包是 `success.json`、`illegal.json` 和 `decode.json`；相应 runner 逐例检查真实机器字译码、字段、回编码（decode Illegal 除外）、唯一执行路径及先 SAT 后全观察集差异 UNSAT。`run.py` 再核返回记录与输入预期、寄存器值、字段、路径数和结构标志一致。失败保留 stderr，并使整包状态为 FAIL。`--only-case <name>` 可单例复现；输出目录必须为仓库外的新目录或空目录，避免覆盖旧证据。

`coverage.json` 为机器可读映射，`case_id` 是 case 名 UTF-8 SHA-256 前八字节大端无符号整数，在 baseline/final 两 profile 相同；同时保存 batch/index、clause、源码文件、条件与预期结果。源码分支状态仍为 `pending-trace`，因为现 runner 的 SAT/差异 UNSAT 和构造器调用记录不足以证明实际 PC 已走过具体分支。固定 d012 IR 中 `hartSupports` 关闭三扩展和 `Fcsr_RM_Fatal` 分支不可达，列在 `fixed_ir_unreachable`。当前 `Zve32x` gating 不读取 `misa.V`，因此该位清零仍有成功样例；FS/VS 关闭和 `misa.F` 关闭另有真实译码负例。

数值输入用独立 Berkeley SoftFloat oracle 生成，覆盖 BF16 窄化正负边界、UF/OF、NaN/∞/零、扩宽与 VV/VF 乘加。`overflow_cancel` 与 `tiny_add` 的 FMA 样例验证融合结果及 flags；FMA 的两个 BF16 源先由 oracle 扩成 f32，再由 oracle 执行一次 f32 FMA，五 flags 做 OR。数值例、mask/vstart、agnostic policy、LMUL 活动 VLMAX 与合法 overlap 均观察完整目的寄存器组。固定 `m4` 扩宽到 EMUL8 为合法上界；`m8` 到 EMUL16 为 execute Illegal。`vill` 样例使用 canonical `vtype=1<<63`，当前 IR 因 SEW 守卫先在译码阶段拒绝。

另有 24 条定向副作用回归：VF boxed scalar sNaN，以及 VF/VV 的 f32 累加器 sNaN，分别置于 `vl=0`、全屏蔽、`vstart=vl` 和合法的 `vstart>vl` 四种无活动状态，并交叉旧 flags 0/1。每条都要求 flags 不变、完整目的组保持、`vstart` 清零及 VS 写回状态；这组样例单独运行后再并入成功输入包。

基线 d012 的完整运行结果只应以相应 `summary.json` 的三个包状态、输入/结果 SHA-256 及实际 IR/config/runner/oracle SHA-256 判定；final 必须在包含 FPR dirty 修复的新 IR 上重新运行。旧 d012 对 final 的未置 dirty 路径是预期红例，不能把 baseline PASS 继承给新 IR。

## 源码分母与真实轨迹校验

`source_catalog.py --out "$CATALOG_OUT"` 生成绑定实际源码哈希的 BF16 专属清单，包括六项 encoding guard、执行控制流、BF16 helper 和 `rF_BF16` 的 boxing 分支。SYMBOLIC 与非 SYMBOLIC 定义分别保存，ITE 数据选择另表列出；共享 FD/V helper 的分母由相应共享清单补足。该命令只建立待核清单，不生成动态覆盖结论。

新 runner 的每条结果须包含 `trace_terminals`（scope、input_case_id、terminal_case_id、phase、status、path_signature、terminal_ordinal、sampled）。输入ID保持不变；每次callback的 `terminal_case_id` 为 `SHA256(name + NUL + phase + NUL + decimal ordinal)` 前8字节大端u64，并作为R3 metadata的case_id，避免同一输入的多个decode终态共用ID。decode数量取实际正整数 `decode_paths`，逐phase检查callback数量和连续ordinal，并与trace、trace-map双向守恒；不固定为历史两条。以下命令核对集成运行摘要的输入/结果/trace、IR/config/runner 哈希和实际 argv，再将每个结果终态与 R3 metadata 双向匹配，并核对每条真实 edge 的 runtime function/PC、后继、方向及 SourceLoc：

```sh
python3 agents/float_support_review/tools/solve_bf16_coverage/trace_audit.py \
  --run-summary "$RUN_SUMMARY" --group "$GROUP_NAME" \
  --cases "$CASES" --results "$RESULTS" --trace "$TRACE" \
  --runtime-sidecar "$ACTUAL_RUNTIME_JSONL" \
  --out "$EDGE_REPORT"
```

输出是带输入名、case-id、阶段、path signature 和调用上下文的实际边索引。SourceLoc 共址时须结合 runtime 指令/控制流审查才能对应 Sail arm，不能自动把同一行全部分支标为覆盖。不同 clause 调用同一 helper 的义务也分别核对。R3 metadata 键碰撞会显式拒绝，不按文件顺序猜终态编号。

生产入口使用 `stream_trace_paths()` 逐终态读取完整 edge 序列，略过指令正文；全部真实见证保留在报告中，输出以 `json.dump` 流式写入。`trace_paths()` 仍供小型测试夹具使用。共享 FD 提取器 `shared_witnesses.py` 可逐 edge 读取大型报告，核对全文件 SHA 后复用共享极性证书；只压缩同 edge/scope/phase/context 的重复见证，原报告中的全部见证保持不变。压缩观察仍须与精确 root-call PC 义务匹配，不能以全局 site 命中消除其他 caller。

共享 FD 关联命令如下，输出可由共享 `caller_obligations.py --caller-definitions` 消费；BF 六 caller 声明和标量 49 caller 分别保存。

```sh
python3 agents/float_support_review/tools/solve_bf16_coverage/shared_witnesses.py \
  --full-summary "$BF_FULL_SUMMARY" --suite default \
  --lowering "$FD_LOWERING" --source-catalog "$FD_SOURCE_CATALOG" \
  --out "$BF_SHARED_FD_OBSERVATIONS"
```

`shared_vector_witnesses.py` 接受 `--edges`（已核大报告的完整方向压缩件）、`--references`（四 BF caller 源码作用域）、`--lowering`、`--short-candidates`、`--short-cfg` 与 `--out`。其输出分别保留已核结构映射、待独审的短路 LHS 见证和未观察引用候选；后者仍需 typed 调用域与排除证明。短路末项没有独立 Jump 时，应复用 V 的返回数据流工具另证 RHS，不能从 LHS 命中推断 RHS 两臂。

`shared_control_witnesses.py` 消费 FD 的独审短路、谓词和 RM 主件，以及逐精确 BF root 的动态表。`--exclusions` 可接 30 项 caller 前提排除；`--rm-domains` 连同其 `--rm-base` 原表与 `--full-summary` 绑定 RM 域和真实 FRM 输入的末项 RHS。所有文件创建使用排他模式，保留此前阶段结果。

```sh
python3 agents/float_support_review/tools/solve_bf16_coverage/shared_control_witnesses.py \
  --factor-witnesses "$BF_FACTOR_ROOTS" --review "$FD_CONTROL_REVIEW" \
  --edges "$BF_DEFAULT_EDGES" --references "$BF_FD_REFERENCES" \
  --sidecar "$DEFAULT_RUNTIME" --exclusions "$FD_CALLER_EXCLUSIONS" \
  --rm-domains "$RM_CALLER_DOMAINS" --rm-base "$RM_BASE_TABLE" \
  --full-summary "$BF_FULL_SUMMARY" --out "$BF_FD_REVIEWED_CONTROLS"
```

`shared_v_control_candidates.py` 将 BF 共享 V 引用、172 个真实声明内 root、默认完整方向压缩件与 V 的短路/CFG/独审 if 目录联立。输出仍区分待独审规则的 LHS、未观察 caller、固定 CFG 与已独审的 if；不会把 V22 的动态见证转移到 BF。完整参数由 `--help` 列出。

`shared_v_control_review.py` 消费上述原候选、机械证明和独立主审，使用可重复的 `--domain-review` 逐份关联精确 caller/site/arm/config 域排除；`--fixed-cut-review` 另接四个 write root 的八项精确闭包排除。工具拒绝排除已命中项、重复排除或身份变化。只登记 LHS 与已审 if，RHS 值和整体源码闭合另行核验。

`configuration_semantics.py` 复用标量的 normalized 指令与逆 CFG 前缀算法，登记默认/Voff 十个数值 root 的同体、输入读集合、能力/寄存器读取切口。`alternate_guard_semantics.py` 将已审 BF→F 必要条件和唯一 constructor 守卫绑定到 FDVoff 的实际函数体、初始化和 decode 纯读。两者输出均为 `FOR_INDEPENDENT_REVIEW`；必须消费独审结论后才可据其作跨配置语义声明，不能将候选当作新增动态覆盖。

`configuration_review_index.py` 消费默认/Voff 和 FDVoff 的最终独审，将有条件的数值 helper/typed gate 关系或 BF execute 空域附到 18 格代表索引。它验证候选与依赖 SHA，完整携带独审的必要前提和禁止推论，保持动态计数不变；不证明写回或整指令等价。

`--runtime-sidecar` 为必需参数，必须是同IR/config/runtime及初始化模式的实际SharedState全指令目录。校验复用 [runtime_binding.py](../solve_scalar_coverage/runtime_binding.py)，双向比较itrace与sidecar的全部Jump，包括未被本组命中的Jump；逐项比function、PC、target、fallthrough、SourceLoc及完整指令，只允许根据符号表规范化Name ID。输出 `runtime_catalog_sha256` 和 `runtime_catalog_binding`；`arm_closure.py` 要求base/control/Wma静态证书绑定同一sidecar SHA并与动态报告相等。仅有runtime标签的旧报告不能进入源码闭合。

当前校验另要求实际 `<results>.init.json` 及摘要的 `initialization_sha256`。侧车的 IR/config/binary 和 `runtime_snapshot_manifest_sha256` 须与摘要一致，每行结果须有 `actual_concrete_prestate_R1_SAT`、相同R1合同、具体寄存器绑定及与实际初始化一致的misa域。只接受定向 `directed-decode-first` 与默认/合法替代misa域。`arm_closure.py` 再将同一runtime manifest SHA与静态证书绑定；同IR/config下的旧runtime不能混入。旧runner产物保留为历史证据，不补写缺失字段冒充新验证。

初始化合同统一调用 [entry_contract.py](../solve_fix_integration/entry_contract.py) 的 `validate_initialization`，成功返回 `None`，拒绝抛 `ValueError`。它固定审定Target源码SHA与 `cur_privilege/mstatus/vtype/vl` 四字段，并重算 `initialized_lets_sha256`。实际runner构建启用了 `serde_json/preserve_order`，摘要采用侧车原键序的紧凑UTF-8 JSON；Python读取时保留键序，不能排序后沿用旧摘要。文件哈希与真实argv绑定仍由调用方负责。

轨迹解析/绑定负控制可执行 `PYTHONDONTWRITEBYTECODE=1 python3 agents/float_support_review/tools/solve_bf16_coverage/test_trace_audit.py`；它们只验证证据校验工具，不属于 BF16 数值或分支通过结果。

包含运行时闭合负控制的完整工具检查须逐文件使用独立进程。历史单进程 discovery 曾因 BF/scalar 同名 `shared_control_witnesses` 导入冲突失败；现行命令为：

```sh
for test in agents/float_support_review/tools/solve_bf16_coverage/test_*.py; do
  PYTHONDONTWRITEBYTECODE=1 python3 "$test" || exit 1
done
```

`shared-overlap-illegal.json` 是冻结922条主包之外的4条共享guard补例：三项扩宽在LMUL=mf2时令源/目的同一物理寄存器，VV两源分别测试。组末端相等而源EMUL小于1，因此必须由 `valid_reg_overlap` 的最后一项条件拒绝。它们采用Clean FS/VS且观察状态保持，直接交execute Illegal runner；不经SoftFloat计算，预期来自寄存器重叠规则。主包输入不因这项补验改写。

## 官方R1域输入副本

`canonicalize.py` 保留冻结final的922条及独立4条overlap输入，另建新名称、新case ID与逐例迁移表。它要求实际同IR/config的state-domain manifest，顶层字段为 `ir_sha256`、`config_sha256`、`state-domain`（R1 map）、`vlen` 和 `elen`。仅恢复mstatus只读SXL/UXL；原4条vill实际vl1，规范化副本改vl0，decode拒绝意图保持。FS/VS/SD、FRM、vstart及数值预期不据模型输出修改。

```sh
python3 agents/float_support_review/tools/solve_bf16_coverage/canonicalize.py \
  --source "$FROZEN_FINAL_INPUTS" --source-config "$HISTORICAL_CONFIG" \
  --target-config "$ACTUAL_FD_CONFIG" --ir "$IR" \
  --domain "$ACTUAL_DOMAIN_MANIFEST" --out "$CANONICAL_OUT"
```

原273条标量例未在case或历史config指定vtype/vl；历史runner禁用model register init时二者为Uninit，不存在可抄写的具体配置值。两条标量BF16指令及其FD/RM依赖不读取二者。规范化副本显式选取SEW16/LMUL1、vl0作为固定合法见证，逐字段登记新增值；这不约束official solve的完整符号域。生成器会检查旧config没有这些默认值，否则要求重新审查迁移。真正的source-arm证据还须由采用official assert/init的runner验证每例R1域，生成输入本身不是通过结果。

`base_lowering.py` 从实际SharedState全指令侧车核对基础BF16 source arm的局部控制流和极性；要求同IR/catalog/source manifest及冻结executor源码，输出仓外新文件。它同时核对Kind的“不匹配”语义、union成员、if后继、完整when的Not guard、Bool alias的实际CFG与boxing两臂。不能只凭同一SourceLoc把全部Jump归为同一arm。完整命令形式：

```sh
python3 agents/float_support_review/tools/solve_bf16_coverage/base_lowering.py \
  --catalog "$BF16_CATALOG" --runtime "$ACTUAL_RUNTIME_JSONL" \
  --ir "$IR" --executor-source "$FROZEN_EXECUTOR_RS" \
  --source-manifest "$SOURCE_MANIFEST" --out "$BASE_LOWERING_REPORT"
```

canonical v2还显式设置Machine并使用后缀 `__official_r1_v2`。原因是最终FD配置中没有特权态默认值，实际model初始化后仍可能未具体化；静态能力允许Machine不能代替这个输入字段。v1构建产物未运行且不作为实际见证。

当前canonical v3使用后缀 `__official_r1_v3`，再显式恢复旧E配置中未被case覆盖的32个VPR零初值，每例全部32个VPR均有具体值。已有mask、lane及非零VPR保持，逐字段保存旧config的SHA、键和值。这是固定定向见证的初态重放。生成器系统核对E→FD恰35项defaults差异及全部const_primops相同：32个VPR默认零与Machine被删除；mstatus默认改变，但每例原已显式给值；旧 `__isla_always_aligned` 在实际IR无符号，仅记为无效历史配置项，不添加假初态字段。目标IR/config必须匹配域manifest。v1/v2及原包保留；输入构建核对不代替运行验证。

## RHS独审与新版重绑定

`rhs_review_consumer.py` 逐完整 source key、root、clause、phase、arm、config 消费正常 RHS 与异常独审，验证所有依赖 SHA，并保留异常证书的全部条件。随后 `rhs_static_review_consumer.py` 精确消费旧29条静态独审；旧 1dcc 正常 RHS 为175 actual、22入口排除、29静态条件排除，40条异常独立列账。它不把异常转成 Bool，也不迁移版本。

`rhs_static_candidates.py` 使用实际旧 IR 的完整状态路径重放值，为24个currentlyEnabled、四个SEW16上界和一个先前overlap成功前提建立旧版候选；这些候选随后完成旧29独审。参数由 `--help` 给出，工具不覆盖输出。

新版工作流依次使用：

1. `prepare_strict_p1.py` 从新集成计划、真实结果和完整 runtime 目录生成九组计划；独立 driver 实际重跑 v3 来源桥，然后调用原 `trace_audit.py`。`caller_config_summary.py` 根据这些新结果构造 18 格，并逐条核实际 privilege。
2. 共享 `short_circuit_candidates.py` 与 `short_circuit_cfg.py` 在新源码及 sidecar 上重新执行。`rhs_rebinding.py` 按同函数的左右操作数 token 匹配源码关系候选，按源码调用锚重新发现 root；PC 和旧证明状态不参与选择。
3. 冻结 `rhs_dataflow.py` 从新版严格 trace 提取数据流候选，`rhs_candidate_index_p1.py` 索引新合同；`rhs_frame_check_p1.py` 重执行冻结完整 phase 栈算法，逐终态核 Call/End、全部 Jump 和 instruction_count。产物须经新版独立签收后才用于源码闭合。
4. `overlap3_rebinding.py` 另审三条增量，按源码算式选择三方向，逐完整 phase 栈核精确 root 和 helper 正常 End；三输入／九终态与 942 基线分开。
5. `rhs_review_consumer_p1.py` 只消费56cc69新版139 RHS／327见证独审，47条保持pending；增量36见证没有新增唯一RHS合同。`overlap3_review_consumer.py` 另消费三个LHS=true/RHS跳过方向，不增加正常RHS值。
6. `rhs_static47_candidates.py` 从新root/SSA/CFG和实际入口重算24条currentlyEnabled、15条overlap、8条write-default静态候选。它明确拒绝phase-purity v2的完整无写结论，保留24条phase合同待补。`rhs_retirement_candidates.py` 另绑定五site／40历史RHS到新V4变换候选，值域/消费义务继续pending。
7. `rhs_retirement_review_consumer.py` 精确消费BF40正式变换独审，其v1保留40条旧控制 `not_lowered` 及40条历史候选值标签。后续架构修订由 `rhs_retirement_ledger_revision.py` 另写v2：40旧键多对一映射到4root×2helper的8个待审集成合同，原v1字节冻结，40标签不计当前分母。正式8合同由主coverage生产，本包只绑定和消费。
8. `rhs_static47_review_consumer.py` 联立正式phase-state合同及返回依赖附证消费新47独审：23条caller域排除、24条正常phase条件排除。逐条保留 `scope`、`required_premises`、`unclosed_outside_scope` 和局部证明，原139动态合同不变。完整闭包纯读FAIL与域外未决保留，不升级为无条件全源码结论。
9. `v4_integration_review_consumer.py` 消费正式8项V4独审的 `accepted_contracts`。逐canonical ID、完整新root/helper Call、公式、旧键及前提核对，只将40条历史链接更新为 `legacy_transformation_discharged`；保留8个accepted合同及完整范围，分母为8，新增branch、动态见证及无条件全源码排除均为0。旧迁移账、139＋47账和producer原字节冻结。
10. `v4_dependency_relocation_consumer.py` 消费正式依赖定位附证，只将15条列定活动模型locator固定到同SHA/同manifest键的快照，先确定路径后核字节；未列locator仍原位强验。原candidate126条引用合并为124条，accepted-v1的134条依赖合并为132条。新accepted-v2只更新依赖绑定及重定位元数据，原8合同、全部前提/范围、40迁移链接及计数逐项不变；旧账和producer保持冻结。

56cc69 新版有17个保留短路site／186 RHS合同，当前分类为139实际见证、23caller域排除及24正常phase条件排除，不能据此宣称全源码闭合。另五旧site／40旧控制义务已独审 `not_lowered`，现40条历史迁移链接已消退，多对一关联8个已审限定域callee-instance集成合同。只限默认配置、RV64/vtype64、typed且非Poison、SEW来自正常get_sew及其他predicate正常Bool返回；不证明所有callee总性。严格Bool中间值不算新branch，不存在旧证书自动换版。最新SHA与范围见[专题报告](../../solve-fix-bf16-coverage.md)。原96项、消退消费3项、迁移修订3项、限定域消费4项及V4消费10项工具测试分别通过。

下列为V4账本v1的历史消费命令。它严格校验原locator，活动模型后续变化后会拒绝；当前依赖复核使用下方重定位入口，原producer不做哈希失败后回退：

```sh
BF16_EVIDENCE=isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16
PYTHONDONTWRITEBYTECODE=1 python3 agents/float_support_review/tools/solve_bf16_coverage/v4_integration_review_consumer.py \
  --candidate "$BF16_EVIDENCE/v4-value-integration/candidate.json" \
  --migration "$BF16_EVIDENCE/rhs40-retirement-migration-v2.json" \
  --review "$BF16_EVIDENCE/independent-v4-call-integration-review/review.json" \
  --index "$BF16_EVIDENCE/independent-v4-call-integration-review/index.json" \
  --out "$BF16_EVIDENCE/v4-value-integration-reviewed-v1.json"
```

现行依赖重定位入口如下，独审仅授权列定15条映射，不新增语义许可。已封存的输出不能覆盖；复核时须给 `--out` 一个不存在的新文件：

```sh
BF16_EVIDENCE=isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16
PYTHONDONTWRITEBYTECODE=1 python3 agents/float_support_review/tools/solve_bf16_coverage/v4_dependency_relocation_consumer.py \
  --relocation "$BF16_EVIDENCE/v4-value-integration/dependency-relocation-candidate.json" \
  --permission "$BF16_EVIDENCE/independent-v4-call-integration-review/dependency-relocation-review.json" \
  --index "$BF16_EVIDENCE/independent-v4-call-integration-review/dependency-relocation-index.json" \
  --out "$BF16_EVIDENCE/v4-value-integration-reviewed-v2.json"
```

重定位consumer的10项测试以 `PYTHONDONTWRITEBYTECODE=1 python3 agents/float_support_review/tools/solve_bf16_coverage/test_v4_dependency_relocation_consumer.py` 单独运行。它们验证定位门禁，不能计为新的模型动态输入或分支命中。

## 默认与替代misa域

`split_domains.py` 将canonical v3按实际misa分组，保留全部原926条，并独立新增6条合法F/D/V全部关闭的译码拒绝例：

```sh
python3 agents/float_support_review/tools/solve_bf16_coverage/split_domains.py \
  --canonical-manifest "$CANONICAL_OUT/manifest.json" \
  --parent-config "$ACTUAL_FD_CONFIG" --out "$CLASSIFIED_OUT"
```

默认misa `0x800000000034112f` 的916条才可作为官方默认域定向见证。4条V关闭成功例属于合法替代域；6条原F关闭例仍置D/V，违反D⇒F和V⇒F&D，列 `raw-misa-override` 诊断。新增6条同时清F/D/V，使用独立名称与ID，保留word、Decode_Illegal与无写回预期。替代/原始域各有只改misa默认值的派生TOML及parent SHA、diff；运行必须实际使用各组config并核初始化，不能在默认config之上暗改misa冒称官方域。输出含总manifest及每份config的独立子manifest。仍需实际域探测及runner结果，不能由输入构建推断模型通过。
