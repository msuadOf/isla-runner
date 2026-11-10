# 标量数值 helper 的实际调用库存

`inventory.py` 从当前 scalar 源目录的 49 个 constructor、94 个 execute 定义及各配置真实 `zexecute` 的 Call 重新发现调用点。它保留每个 root 的源表达式、实参、完整保守 Call 闭包、逐函数全部 Jump/Call、原始 body 哈希、源码文件绑定和未解析的 SourceLoc。旧 119 个 helper 名字及 162 个 root 只作差异对照。

```sh
python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/inventory.py \
  --catalog "$SCALAR/source-catalog.json" \
  --control-catalog "$SCALAR/shared-control-catalog.json" \
  --runtime-index "$INTEGRATION/runtime-catalogs/index.json" \
  --snapshot "$MODEL_STAGE" --generation "$GENERATION" \
  --runtime-manifest "$RUNTIME_MANIFEST" --source-bridge "$SOURCE_BRIDGE_V3" \
  --old-helper-index "$OLD_SCALAR/configuration-helper-equivalence.json" \
  --old-prefix "$OLD_SCALAR/numeric-prefix-equivalence-v3.json" \
  --output "$NEW_OUTPUT_DIR"

python3 -m unittest discover \
  -s agents/float_support_review/tools/solve_scalar_numeric_helpers -p 'test_*.py'
```

四配置各自读实际 sidecar，并重新执行 v3 来源验证。工具沿全部 Call 建闭包，不应用旧固定 CFG 或类型排除；`numeric_source_*` 只按明列数值源文件作分类，完整根集合始终保留。它不产生动态命中，也不证明调用点可达、正常返回、纯度或源码分支闭合。输出拒绝覆盖已有库存。

## 56cc 首版结果

[四配置索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/index.json)（SHA `c949156850760219b5418a61782e0dbab887b4fad3e9fbb6013ce6468d02b829`）与[验证摘要](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/validation.json)分别保存实施库存和测试边界。六项测试先红后绿，覆盖错来源／函数的同名 callee、非 SYMBOLIC 定义、重复源归属、循环和外部调用、源位置越界及 UTF-8 字节偏移。

每个实际配置均发现 629 个源 Call root，完整保守闭包为 255 个内部函数、11 个外部 callee、810 个 Jump 与 1285 个 Call。旧 119 个名字全部出现在当前完整闭包中，这一事实只用于对照。数值源分类得到 96 个 root，其完整子闭包为 166 个函数、37 个 Jump、706 个 Call、0 个外部 Call。

37 个 Jump 中，7 个来自 Sail 库 `float/inf.sail`、`nan.sail`、`normal.sail`、`zero.sail` 的 Bool 短路。原 scalar 源目录只收录 `classify.sail` 和 `common.sail`，因此这四个文件需要独立补充源因子及 caller 义务。另有 3459 个实际 SourceLoc 为无文件名的 `n:0 - 0:0` 形式，库存逐项保留未解析状态，不从缺源位置推得 `not_lowered`。

本库存尚待独立审查，`source_branch_closed=false`。上述函数与边数为各自的保守库存，不能与其它账本分母相加。

上述“尚待独立审查”为首版时点状态。后续[库存独审与因子证书索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/independent-library-factor7-review/README.md)已确认完整保守库存；库存证书 SHA `5ba90e33ffa682e94038297d99d79c2e3981779d01c85bf2d7905a0e291d61e5`。未知来源与可达性限制均保留。

## 七个库短路因子的补充目录

`library_factors.py` 从冻结库的四个实际文件提取七个 `&` token，复用既有向量短路工具重新检查源操作数、到达定义和完整 CFG。为兼容这些工具的源码寻址方式，输出目录中的 `source-root/sail-library/` 只复制已校验 SHA 的库字节。共享工具和原 scalar catalog 均保持原样。

```sh
python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/library_factors.py \
  --inventory-index "$INVENTORY/index.json" --snapshot "$MODEL_STAGE" \
  --output "$NEW_FACTOR_DIR"

python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/library_witnesses.py \
  --factor-index "$NEW_FACTOR_DIR/index.json" \
  --strict-summary "$SCALAR/strict-audit-summary.json" \
  --output "$NEW_WITNESS_CANDIDATE"
```

[补充目录](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/index.json)（SHA `272423061895863ea23b74897ae047c60a028846c80eac2b558240632b86715f`）在四个实际配置中各得到 7 个通过词法／SSA／CFG 检查的候选、21 个保守 root-factor 配对、42 个 LHS 方向。正常 RHS 返回值与异常义务另待证明。

[自身见证候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/witness-candidates.json)（SHA `8e89294e807512f6e984e1c316b7d1d3bb03d8174db922127083a311cb1c908c`）重核原严格审计及实际运行产物关系，按 Machine、配置、clause、execute phase、root 和连续 Call 链提取已有见证：

| 配置 | 有自身观察的候选方向 | 待证方向 |
| --- | ---: | ---: |
| default | 39 | 3 |
| scalar-registers | 12 | 30 |
| Doff | 12 | 30 |
| Foff | 0 | 42 |

这些仍待独立完整调用栈与源码关系审查，不计作已接受命中；不同配置的见证不互借。default 三项未观察均为 S/D/H FCLASS 各自调用 `float_is_inf` 的 LHS false。未从有限输入缺失推得其不可达。工具累计十项测试通过，无新增模型运行。

新[全局词法身份 v2](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/global-site-identity-v2.json)（SHA `d614206ebd572fb2d0439e7ce5f9fde59bec8935c91309eb2e28ff36801ea8ef`）保留原四目录，追加七个因子后为 1259 个唯一候选、10 个共享候选。这是 token 身份计数，仍不是可达分母。

## 后续独审与严格消费

七因子独审证书 SHA `d884a73ebfdac52647610da33fea4d7637ad10936a1b56ecef5272e7d9f3e878` 已签上述 63 个精确 LHS 方向。独审重建 17 个输入的 51 个完整 phase，核对 121 个依赖，13 项变异负控全部拒绝。105 个 LHS 方向继续待证，RHS 未签，default 三项 `float_is_inf` 的 LHS false 未排除。

scalar owner 的[严格消费合同](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/library-factor7-contract.json)（SHA `8043a0786ccb8c107343f4e884b6fb96ca4516bf09d841d0c117e2c8289de917`）已逐项接入这 63 个方向；168 = 63 已观察 + 105 待证，无新增 RHS 或可达性升级。上述“自身见证候选”段保留为提交独审时的历史状态。

## default 三个分类方向的域候选

`classify_inf_domain.py` 从当前实际 `float_classify` 重算同参数的 zero、subnormal、normal 检查。令 `A` 为指数全 1、`Z` 为指数全 0、`M` 为尾数全 0，三个正常返回分别为 `Z & M`、`Z & !M`、`!A & !Z`；只有三项全部为 false 才可到达 `float_is_inf`。八个 Bool 赋值组成保守上界，均满足“可到达 inf 蕴含 A 为 true”。无需假定位型之间互斥，也不枚举浮点位空间。

```sh
python3 -m unittest discover \
  -s agents/float_support_review/tools/solve_scalar_numeric_helpers \
  -p 'test_classify_inf_domain.py'
python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/classify_inf_domain.py \
  --output "$NEW_OUTPUT_DIR/candidate.json"
```

[候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/classify-inf-domain/candidate.json) SHA `78555a4332c5259e11ca1c325bafa84e299513b7a138e89075d879c1a124a5c7`。四项测试先红后绿，覆盖参数更换、指数／尾数互换和前置 true 出口绕过。候选绑定 S/D/H 三个精确实际 root、同一 `float_decompose` 字段、完整 helper 返回与前置 false 的支配关系；待独审核对共同原子的 runtime 确定性和全部依赖后消费。其它配置、caller、RHS 正常值及异常、分类总性均未升级。

后续[独审证书](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/independent-classify-inf-domain-review/certificate.json) SHA `a5824ee1e68707699af16ea20f89b0e9f0cb1408ed88c1b761f14791e79f5c1e` 已签三个精确 `default/Machine` caller 排除。独审重算四函数、159 指令的同输入确定性、完整 helper 正常返回和全部八个抽象赋值；八项测试通过，49 个依赖无漂移，v3 来源桥接重新执行通过。真实分类断言和失败出口保留，动态新增为 0；证明不依赖 FS 状态或 decode/encode 的执行顺序。

scalar owner 已将三项接入[严格消费合同](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/classify-inf-three-contract.json)，SHA `e286c26994a1ae19986c2e584efeb79e3a1a8dfb88ad3ca81f2d43f0d9ed9f9d`。库因子总体变为 63 个实际 LHS 观察、3 个精确 caller 域排除、102 个待证方向；default 的 42 个 LHS 方向由 39 个观察和这 3 个排除分类完成。RHS 和异常仍未闭合，原七因子消费合同保持字节，五项新消费器测试通过。

### 三个备用配置的同类条件候选

`classify_inf_alternates.py` 在 `scalar-registers`、`d-off`、`f-off` 各自的当前 sidecar 上重新运行上述完整 helper 关系、八个 Bool 赋值、同参数支配关系及确定性闭包。每配置先重新执行 source-v3，再按实际源声明重建 629 个 execute 调用根并与本配置库存逐项对齐；三个 `float_classify` 根由 clause 和实际 callee 定位，随后才核对 PC。`float_is_inf` 的实际 Jump 由 `is_all_ones` 的结果 SSA 定位，源码 token 另从冻结 `inf.sail` 重算。

```sh
python3 -m unittest discover \
  -s agents/float_support_review/tools/solve_scalar_numeric_helpers \
  -p 'test_classify_inf_alternates.py'
python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/classify_inf_alternates.py \
  --output "$EVIDENCE/classify-inf-alternates/candidate.json"
```

[九项候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/classify-inf-alternates/candidate.json) SHA `13c32444d96b11ddc4dd45e56f2dcbd88863da914036b9fb72b8a0a0701c6977`，当前待独审。七项测试通过，覆盖配置混用、重复或缺失 pending 方向、错误源 owner、改变实际根、不同参数等负控。模块尚未实现时的红例及首轮源 owner 拒绝抛错类型不符的日志均保留；后者改为明确的根唯一性断言后通过。

候选只涉及三个备用配置各三个精确 `Machine` caller 的 inf LHS false 条件排除，不依赖 FS 非零或先成功 decode；要求正常 typed、非 Poison、相同 bits 输入及前置分类正常返回。原 default 三项合同和工具保持字节。待独审及严格消费后才可从库因子 pending 中处理这九项；当前仍为 63 个观察、3 个已审排除、102 个 pending，RHS、异常、根可达性和总性均未升级。

上述九项随后获得[备用配置独审](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/independent-classify-inf-alternates-review/certificate.json)，SHA `0974ad4d417b8b261a46659c8c503416e3f2418dcad97b0b8704efc71396f322`。独审分别重枚举三个配置的实际 629 个源调用根、source-v3、源范围、实参位宽与 getter；每配置三项负控被拒绝。局部四函数、159 指令及八个 Bool 抽象态另行重核，仅按正常 typed、非 Poison 的实际 caller 条件签署。

scalar owner 已在[九项消费合同](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/classify-inf-alternates-nine-contract.json)中精确接入，SHA `a2e83a013a006c8ee694619c44ba7c84bb4f25dbc7b6b5fde898b269817ab2c6`；六项消费器测试通过。现行库因子 168 个 LHS 方向为 **63 个实际观察、12 个条件排除、93 个 pending**。其中仍待证的三个备用配置分别为 27、27、39 项；旧 default 三项及先前各版合同保持字节，RHS 和异常未升级，没有新增执行。

### e6a 模型的三个新候选

`classify_inf_e6a.py` 使用新 IR 的实际 debug 目录，重新执行 source-v4、提取 scalar 源声明和库 token，并从当前 `zexecute` 重找 629 个根、49 个 caller。三个分类根按 source clause／callee 定位，inf Jump 按 `is_all_ones` 的实际 SSA 定位；其源范围包含重新提取的 `&` token。随后在新实际结构上重跑原 helper 返回、八个 Bool 上界、支配关系和确定性闭包算法。

```sh
python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/classify_inf_e6a.py \
  --candidate "$NEW_MODEL_STAGE" \
  --preparation "$NEW_EVIDENCE/runtime-catalog-preparation-v1/report.json" \
  --output "$NEW_EVIDENCE/scalar/classify-inf-candidate-v1.json"
```

[新候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/scalar/classify-inf-candidate-v1.json) SHA `5c1ccca688063115082bbaea71730b9e3db2ff6d36e083c58bc33f9ff0882b53`，三个 `default/Machine` 条件排除尚待独审。1382 个依赖重新核验无漂移；6 项新增根身份测试先红后绿，连同既有分类测试共 17 项通过，见[限定验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/scalar/classify-inf-validation-v1/validation.json)。旧版合同与动态见证迁移数为 0，新执行为 0。新候选仍要求正常 typed、非 Poison、同 bits 参数；RHS、异常、根可达性和总性保持 OPEN。

随后[新模型独审](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/scalar/independent-classify-inf-review/certificate.json) SHA `099c9ebe99b5a85eb4b3bcaa1847af645b771f39f820be1c6d52d841150b45f4` 签署这三个精确条件方向，联立[新 actual 目录来源独审](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/independent-runtime-catalog-review/certificate.json) SHA `af75f09f743d6b59ed83ba768c772e42475079eee8a27318da2d38dbfb1d020a`。独审重定位 94 个当前定义、49 个 caller、629 个 root，核三 caller 的 32／64／16 位实际数据来源；9 项测试、4299 项绑定通过。此时待严格消费，旧版计数不变。

上述三个方向已由 scalar owner 在[新模型正式合同](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/scalar/classify-inf-three-contract-v1.json)中严格消费，SHA `0b08b31460463976c2592e7066fa794eb8f2e649f4cca123e400b410734eae7d`。4301 个依赖重核、10 项消费测试通过；这是 e6a 模型自身条件合同，不并入旧 56cc 的 168 方向，也未迁移旧动态观察。

### 56cc 备用配置的 26 条分类增量

剩余库方向另补 26 条实际输入：`scalar-registers` 对 H/S/D 各运行 inf、subnormal、zero、snan、qnan，并补此前缺失的 S normal，共 16 条；`d-off` 对 H/S 各运行前五类，共 10 条。`classify_alternate_inputs.py` 复用冻结 default 分类的独立预期，保留数据和其它初态，仅变更新 case ID、明确的 alternate 配置与 MISA。两配置实际运行及完整 strict 审计均通过，共 **26 输入、78 终态**，见[strict 汇总](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/alternate-classify-strict-v1/summary.json)，SHA `b26f03a9686c33f067c4e855393bd577608cb91e5937ec18539666f69abc14ba`。

```sh
python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/classify_alternate_inputs.py \
  --baseline "$FROZEN_INPUTS/scalar/default/baseline.json" \
  --config-root "$FROZEN_ALTERNATE_INPUTS" --output "$LIBRARY_EVIDENCE/alternate-classify-inputs-v1"
```

运行使用冻结 `run_suites.py`、原 `56cc69`／`28fb65ee…` runtime 及对应 runner；完整参数保存在[执行命令](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/alternate-classify-results-v2/commands.json)。首次准备因两个 runner 文件名推测错误，在模型执行前即失败，记录于 `alternate-classify-results-v1/preflight-failure.json`；核对实际文件名及二进制 SHA 后在独立 v2 目录执行成功。

复用 `library_witnesses.py` 提取自身方向，再由 `classify_alternate_delta.py` 与原 63 个观察做精确差集，形成[41 个新增 LHS 候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/alternate-classify41-candidate-v1.json)，SHA `2e2f3fea57cc767c353f9f189825eee18cd67a794d681f9cad3a9c01c2ea98a1`。其中 scalar-registers 为 27 个、d-off 为 14 个；11 项新增测试通过，尚待独立完整调用栈和 Bool 来源审查。原计数仍为 63 个观察、12 个条件排除、93 个待证方向。

后续[41 项独审](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/independent-alternate-classify41-review/certificate.json)已通过，SHA `d6a21107d11fa5f76543aed77a4457fd67840c46e68579d7535f1c164df6e0d3`。独立重建 78 个 phase、436602 条指令、19074 对 Call/End、69309 条边，核 223 个依赖；3 项测试与 8 项负控通过。仅签这 41 个自身 LHS；由 scalar owner 严格消费后，旧库账才可变为 104 个观察、12 个条件排除、52 个待证方向。

[41 项正式消费合同](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/alternate-classify41-observed-contract-v5.json)已生成，SHA `97a6ead3d4bcc6eeea94b40e113017861fb1f425aeaa1e37ab88f16a3ee615f1`。352 个依赖重新核验、10 项消费负控通过；四配置各 42 项守恒，合计为 104 个观察、12 个条件排除、52 个待证方向。新批的 26 输入／78 终态与消费者本身不执行模型分别记账。

## 失能 MISA 下的直接构造子执行

FCLASS 的 `execute` 源体没有扩展启用 guard，不能以 decode mapping 的失能拒绝排除其源码调用义务。新增 `direct-constructor-execute` 入口，显式保留真实 Foff／Doff 配置与 MISA，直接构造当前 IR 类型的 FCLASS ADT 并调用一次 `zexecute`。三个构造子均由实际 `type_info` 核对字段顺序、Bits5 索引和枚举身份；完整执行、R1 等式绑定及差异 UNSAT 逻辑复用冻结 runner。7 项 Rust 类型测试通过。

冻结[输入清单](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/direct-classify-inputs-v1/index.json)含 24 个唯一输入：Foff 的 H/S/D 各 6 类、Doff 的 D 共 6 类。复用原独立数值预期，删除执行用 `word` 字段；历史机器字仅作来源记录。MISA 被显式加入初态及 post 观察。

首轮 v1 的 24 个结果全部通过，但 `set_runtime_catalog` 启用了 `branch-compact`，缺逐指令 Call/End，不能供方向独审。v1 原结果保留；[v2 构建](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/direct-execute-runner-v2/build-record.json) SHA `a03bd0661d76f15a712759af298d545297bb0598899bbd6d4f16b8a6d770fd06` 使用原 runtime 公共完整渲染接口，510 个冻结源文件保持原字节。`direct_full_trace.rs` 从同次 SharedState 生成实际逐 PC 显示 cache；独立 handler 只导出同状态的静态 branch 目录，不执行模型。显示 cache 不进入执行解析器。完整 trace 中原始 `source=unknown` 保留，在审计时显式联立同次实际目录。

v2 对同 24 个输入重新执行，24 个单一 Retire 终态全部通过。两次运行分开记录，唯一输入仍为 24 个。[严格审计](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/direct-classify-strict-v2/summary.json) SHA `0979da7df19d76485bf308439136c9004006f9c46d88b0725deec1a0f8668eab` 核对每配置 377980 个实际 PC、全部 22384 条动态指令及 6612 条边，并独立比较真实 R1 值、AST 字段、ret 和全部观察寄存器。逐组完整命令与 hash 见[运行记录](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/direct-classify-results-v2/commands.json)。

```sh
python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_numeric_helpers -p 'test_direct_*.py'
python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/direct_classify_audit.py --help
python3 agents/float_support_review/tools/solve_scalar_numeric_helpers/direct_classify_candidates.py --help
```

21 项 Python 测试通过；[验证记录](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/direct-classify-validation-v1/validation.json)保留首轮缺完整 trace、v2 首次编译失败、strict 首次未处理 PrimopReset 显示指针的失败历史。后者只影响跨进程函数地址的显示规范化；原始 trace 未改写。

[52 项候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/direct-classify52-candidate-v1.json) SHA `74856c18c19d91e342bcd0f858dd1e5d93a00c2075007ae48fd35c23eefb2883`为 Foff 39 项和 Doff D 13 项，与原 63 项及新增 41 项精确不交。当前仍待独立完整 Call/End、同父 frame 和正常 Bool 来源审查；不得升级为 decode-first 或 official 入口覆盖。原 12 项条件排除、RHS 和异常义务保持各自范围，`source_branch_closed=false`。

候选中的 `all_matching_witness_count` 沿用提取器字段名，实际统计 strict 已保存的 `edge/scope/phase/context` 代表见证数量，不是该方向的全部动态出现次数。完整实例数由独审另外重建，见[计数口径附记](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/numeric-helper-inventory/library-factors/direct-classify52-count-clarification-v1.json)。原 52 项候选及依赖保持字节。

后续[52 项独审](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/independent-direct-classify52-review/certificate.json)已通过，SHA `2dbb4aac2f489387d2659dc8bb018c7b91b5a4d452f6f89ee08a9f69995eef35`；必须联立同目录 `source-and-delivery-check.json` 与 `lhs-local-declarations-check.json`。独立核对 24 个完整执行终态、52 个方向／128 次实际出现、996 次正常函数调用、48 次寄存器向量特殊操作，并区分 60 个 context 代表、52 条候选引用与全部实际出现。45 项测试／37 组负控、638 个依赖通过。严格消费由 scalar owner 生成新的入口分列合同；旧 decoder／official 覆盖、RHS 和总源码闭合均不升级。

[入口分列正式合同 v6](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/direct-classify52-entry-separated-contract-v6.json)已严格消费，SHA `63409fabbb445a0a1adf083495146378fc6a668a4e1e548db41ae863094d9ac3`。974 个依赖重新核验，12 项消费测试通过；选定库表的 **168 个 LHS = 104 个 decode-first 自身观察 + 52 个 direct 自身观察 + 12 个条件排除**，该有限表的 LHS 待证为 0。旧 decode-first 入口仍有 52 项未观察，两个入口没有互相升级；RHS、异常、完整 caller 以及整个源码分母仍 OPEN。后续以各族完整原生构造子根到源码义务表核对这些有限合同的适用范围。

FCLASS 执行体本身没有扩展启用 guard，限制位于 encdec mapping；访问器也不能仅按 MISA 禁用判为失败。因此 F-off 三个 caller、D-off 的 D caller 保留直接 execute 义务，不能把编解码入口拒绝改写为无条件根不可达。新增见证只适用自身 decode-first 入口，不增加官方 encode-first 自然 solve 的完成数。
