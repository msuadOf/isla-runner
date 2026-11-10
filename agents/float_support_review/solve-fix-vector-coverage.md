# 向量浮点分支闭合实施与证据

2026-09-26，依据用户授权继续完成[向量审计](solve-audit-vector.md)缺口。范围为 22 个非 BF16、非内存浮点向量 clause。此包只修改 `tools/solve_vector_coverage/` 和本文，生产优化、IR 与 trace runner 由对应协作者维护。

## 当前结论与版本

**源分支尚未全部闭合。** 2026-09-27 的统一后端 V4/AMO IR `56cc69` 已完成主批 **3228 case、9396 唯一终态**及三组增量 **16 case、36 终态**的独立严格审计，合计 **3244 case、9432 终态**。旧 `1dcc` 默认前沿当前为 **5129 已观察、87 待核**；这些旧版数值没有迁入新 IR。

### 最新接续：主 v14 与完整 native 库存

[主账本 v14](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v14/index.json) SHA `61a64896cce11c583f4cf6b3874a939ee61bd0c85ecd9d0f081b3a07b3906185`，default SHA `1874829badeb9e27affa21a4f8ba64bb51637b0065cd7744aeacfb5ff7e89392`。默认原 13825 行现有 **3293 源观察（87 原观察＋3206 既有 trace 源语义）、1671 已审结构/执行待源语义、74 待源谓词、1877 待见证/域证明**；其余各类静态排除不变，六配置静态总数仍 26504。此处 13825 是已映射主库存，未声明完整分母。

[flag173 独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-direct-flag173-review/review.json) SHA `995d5dd5e0af6aaaf991ca6d54afede6e2551be4fb2089f14ba312caed5b4a7a`核六处直接 Bool 读取、173 条精确原行与两份旧 trace 的 40 完整 phase、435089 条指令；7 项测试、15 个单测变体及 6 个真实 claim 负控通过。[消费器](tools/solve_vector_coverage/consume_direct_flag_review.py) SHA `9542367b3770c1ebdce4dfe9487bd99f3b83283eddd06941a11b6fce53d76583`重算 producer 与独审两套局部合同及完整 row/root/source/动态身份，9 项消费负控通过，[控制记录](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v14/consumption-controls.json) SHA `ef31ada39ee28c6995580769c0bdf220399e307e043788f86217068b3c4f5890`。只升级既有 true 臂；两值真值表不产生 false 观察，不借初始化、配置固定、跨读取稳定或 assert 可达前提。首次消费因将独审语义摘要误对 producer 完整合同而拒绝，未产生输出；修正为核独审规范合同摘要后通过，独审原文件未改。

[独立补充账本 v2](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-caller-complement-v2/index.json) SHA `f7112ca04245cfeebe0d63bf676278318fe03f993c8ea0966c6f83ffd3b75111`，default SHA `8b7e78b8677adb8e35c4322de397f0de35c631c33ca1544a41e10d809d46f966`，保留原 **4325 补充项，其中 291 observed、4034 pending**。它联立 [mapping18 最终 v2](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-mapping18-current-review/certificate.json) SHA `533a067aaa45c0ceb248b316189e74b1aa44fa6f1d3c32b656d1eea44b67d130`、必需 type 附证 `d4c95fea6ced7d0e891b658702f71970724d16a71a50893e0926bca3867183bb`、native caller 保存帧附证及 [mapping291 动态独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-mapping291-source-semantics-review/certificate.json) SHA `b7b376464130dbcd42538707df4be3805f9e68a0fac314eb5339246fa124bfab`。表审覆盖 18 表／97 成员／90 函数／2339 输入／36 guard；动态独审核原组 274 输入、822 全终态，其中 97 输入的 194 完整 phase，共 2766908 指令、492983 Jump、97302 Call、97496 End。97 个反向 value 均有同次精确父 frame 的 matcher 正常 true 和同位串前件。

[补充消费器](tools/solve_vector_coverage/consume_mapping291_review.py)核全部冻结依赖、完整原行与精确 key、完整许可域中路径唯一性、194 phase 终态，以及 97 个 matcher 前件；[10 项消费负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-caller-complement-v2/consumption-controls.json) SHA `fa2dba7b025db60cdb047ccb6ec939bd5a0bfeb7b2b964b730f32361bee86692`通过。实现期分别因 phase 字段名及源码成员与 IR `z` 前缀的身份差异而拒绝，均在创建输出前终止；修正读取真实协议后通过。**主 13825、RHS 5640／1880 contexts、其他五配置均不因本补充消费改变**；291 不直接加到主观察3293或声称真实分母完整。表审 12 测试＋11 核心/4 类型负控，动态审 6 测试＋13 负控，新增 case/终态均为零。

[完整 native 准备库存 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-full-source-caller-preparation-v1/index.json) SHA `9501565b8ec0ca9613b77293de67bb53a38a6aab9caadd704bc10632241f0527`由[提取器](tools/solve_vector_coverage/vector_native_source_inventory.py)重新选择 22 个实际 outer constructor，形成双域 132 个 phase 根。普通域／SYMBOLIC 域分别得到 1202／1222 个单元、1393／1444 个 native 控制/映射/effect 节点，以及 35169／36090 条 root/site/arm 待证记录；每条保留完整闭包中的立即 caller 边，extern occurrence 为 1870／2084，名称未解析为零。5 项边界测试通过，634 个依赖绑定；exporter v2 正式有限独审只许可结构发现，全部源码分母和覆盖均为 false。原 879 site 与 121 待映射项均完整保留，位置/种类匹配只作候选，不作为 raw 来源证明或删除依据。

**上述 native v1 已知待复验**：BF 独审随后确认共用 `free_references` 漏 `E_ref`；即便目标已经出现在全局集合中，每个 root 的依赖闭包仍需重算。因此 v1 的零名称未解析不表示完整图或分母。下述 v2 已复用统一修订重算，仍待完整 raw 来源和调用域证明；冻结 v1 工具及产物保持。首次核验两次在导出输入清单的活动工具文档 SHA 处拒绝；随后按 exporter v2 独审明列的 `input-recheck` 精确快照映射完成 457 输入双射，未豁免哈希检查。

[native v2 的 attempt3](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-full-source-caller-preparation-v2-attempt3/index.json) SHA `d239ec0c840553242d17a07958164acaf07b633f47c60fe01c822bfa282766d3`由[修订提取器](tools/solve_vector_coverage/vector_native_source_inventory_v2.py) SHA `2cdaf240d3c0f0947daa39a164b69d901f8bd0eddc792ef4d2cff5f1977cadd1`复用共享 `native_semantic_dependencies_v8.py`（SHA `dde355e6fa7e1ba445043f4312273885aa5338345b38817a2823ae28e5e36ba1`）重算，绑定 694 依赖。普通／SYMBOLIC 两域各 66 根、1202／1222 单元、1393／1444 native 节点及 35169／36090 条 root/site/arm 候选保持；新增逐节点语义义务 2425／2845、逐 root 语义义务 33111／31226，包含真实 return、write、ref、sizeof、constraint 与类型条件，不把 annotation 中的 `Nexp_if/NC_and/NC_or` 次数当运行分支数。`E_ref` 依赖边为 0／64；本例每个 root 的 reached 集合恰未变，不豁免新增边。extern occurrence 修订为 1878／2548，对应 141／151 个唯一 extern 声明；ordinary 按 cpp、SYMBOLIC 按 c 的精确目标优先于 `_`，同名 Sail body 与有效执行目标分列，module/visibility 仍 OPEN。全 schema 为 278 构造器／149 实际出现；两域各有 6 项非 unit 声明义务未闭合。

v2 逐根保留 official/audit 入口、配置、constructor、phase 与显式 D 对象的 key；普通域 132、SYMBOLIC 域 792 个 scoped root。D 目前只是待绑定的协议对象，**不是已证输入公式**。official 从完整 typed constructor 参数和初态起，decode 只允许真实正常 encode image 及同 phase 状态，非 encodable 终态保留；audit 从原 word 和初态起。完整 dispatcher 前缀、matcher 求值、guard 失败、成功 value、目标失败后的 suffix、最终 ILLEGAL，以及 encode/execute 的选择、拒绝和 default 桥全部 OPEN。排除需另联立源/IR/D/实际顺序与独立域证，不能按最终 constructor 预选 body。初次 v2 因重复 `ast_path` 参数报错、attempt2 因共享路径缺口主动终止，均无 index；两个失败目录保留，attempt3 使用 v8 成功。共享 21 项测试只支持对应算法门槛，族实例和源码分母仍未签。

[完整 raw scope 候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-raw-scope-preparation-v1/index.json) SHA `5108cc69f8147da81bd1475971fa34fff28e8e9cce015ead8feb147d73277e8c`由[raw 关联工具](tools/solve_vector_coverage/vector_native_raw_scope.py) SHA `54e5c0f70973011235fcae70cc57924a19b29bf8483e42f0e379494e54f96617`复用共享 raw v3，从完整 **5083 scope** 重新建立索引并逐内容核共享 check，绑定 703 依赖。普通／SYMBOLIC 1202／1222 单元中，1134／1152 有同名和真实 pattern/decl 来源范围候选，68／70 有 bitfield/enum 生成来源候选，未解析 scope 为零。选中 scope 的 raw event 共 1688／1897；729／863 有同 kind 和精确物理范围的 typed 候选，**959／1034 未投影事件保留 OPEN**。这些候选不证明源码等价、失活或不可达。

原 879 身份联立父消费器 `global-native-token-identity-reviewed-v1.json`（SHA `7425182026397577d23f5b363a1cd63c925a4298fe8802362c09a4c37112f381`），仅以真实 raw AST 路径前缀关联 scope。两域 302／263 项未落入本次 scope 候选，保留待解释，不能删除。父消费器的 historical live gate FAIL 与 frozen recheck `PASS_HASH_BINDINGS_ONLY` 均保持，不迁移为 producer 链完整性 PASS。raw 类型声明中的 `ATyp_if`、派生 `Nexp/NC`、scattered/mapping/guard 投影、生成函数及每个 caller 来源仍需共用算法和独审。native 发现标签尚不是完整 branch 合同，循环四种时序臂、assert 真/假及异常、mapping 方向/guard 义务均保留。上述新库存没有新增模型运行、case、终态、观察或静态排除，`denominator_complete=false`、`source_branch_closed=false`。

raw 未投影事件按真实 kind 分解：普通域 959 项为 `raw_infix_operator` 375、`E_sizeof` 94、`E_config` 92、`MCL_bidir` 365、`E_assign` 11、`MCL_when` 22；SYMBOLIC 域 1034 项依次为 417、119、92、365、19、22。它们交由共享 raw 投影和 type/config 来源层继续处理；365 个 mapping 单元不收窄为旧 18 张表。

[完整 dispatcher 顺序候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-ordered-dispatcher-domains-v1/index.json) SHA `3ceab43df484a280d10c7058894249020adb33c2de64a6d59147bfe18092e5cb`绑定 702 依赖，复用共享 `native_dispatcher_order_v1.py` 从双域 AST 各重算 encdec forwards 392、backwards 392、execute 395、ext_decode 1 个 clause。两域各 66 个实际 root，关联原 132／792 个 entry/config/constructor/phase/D key，共 924 项；完整前缀和失败后缀逐根保存，最终 ILLEGAL、无匹配/default 桥及每个 matcher/guard/value 义务均保留。official 完整 typed constructor 参数 pattern 已绑定，但实际 harness 输入公式、正常 encode image 与同 phase 状态关系仍 OPEN；audit 不借 official image。源码组件顺序不等于运行时指令顺序，matcher 内的 infallible 子映射投影可能发生在 extension guard 前。

[dispatcher 关联工具](tools/solve_vector_coverage/vector_native_dispatcher_domains.py) SHA `81672f7265c2bc81e98980c54ce475135ab6039d00b97a06368371eb13a6ac81`按 TDD 先记录缺模块失败，再通过 [6 项边界测试](tools/solve_vector_coverage/test_native_dispatcher_domains.py)：方向、constructor 身份、重复 definition/target 和完整顺序删改均会拒绝。该测试与真实双域重算只支持有限关联门槛，不新增输入域排除或覆盖许可。尚未将完整 CPU body 无条件加入已达闭包，也未按最终 constructor 预选 decoder。

**dispatcher v1 的域占位勘误**：上述 `candidate_j_domain` 的“D 且此前正常失败”不能直接作为无状态 Bool 公式；`D_obligations.execute_input_relation` 的“prior phase resulting state”也不适用于实际审计 runner。[入口/状态补充 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-entry-domain-state-supplement-v1/index.json) SHA `e023839c6fdd09d23a1f555dca817e13c01084ac083805cf505bfff7aa6069cd`保留原 924 个协议 key 作为来源导航，逐项撤回这两处占位并补 `R_(j+1)(w,σ′)=∃σ. R_j(w,σ)∧RejectNormally_j(w,σ,σ′)`。异常是独立终态；仅有另证纯读及定义域时才允许 Bool 简化。它联立[共享入口边界独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/independent-dispatcher-boundary-review/review.json) SHA `5e3d1c1fb68a523c7a923085e83b9d4602a6b084d7f0e22d1ef56a24667099cb`的有限 source/IR 事实，未宣布实际全域关系已证明。

该补充从冻结 `privilege-runners-v2` 的 build report 和源码核实：成功/执行非法审计的 decode、encode、execute 各次 `run` 均传同一个原始 `regs` 和初始化 `lets`，`execute_ir_function` 新建 frame 并克隆二者，**只传递 decoded 值，不传递前 phase 输出状态**。decode-illegal runner 按原 `expected_result` 决定仅执行 decode 或继续三 phase。官方 wrapper 则在同一条路径连续调用 encode→decode→execute，三个异常出口保留，requested/decoded 相等是完成后的检查。decoder 正常返回 ILLEGAL、encoder 末尾 MatchFailure/non-encodable、execute 的 Illegal_Instruction 与剩余 C_ILLEGAL 解包分别登记，不能用共享通用 no-match 文字覆盖实际出口。

[入口来源工具](tools/solve_vector_coverage/vector_entry_domain_sources.py) SHA `2f74e9200c23d16c31677a19ae7b38905944b87108079ee4acebf0e10c5e904f`绑定 **923 依赖、56cc/default 的 42 组及 2622 个既有固定输入**：原 word 与 result.word、name/case ID/clause 双射、完整初态覆盖字段及初始化侧车，并复用公共 R1 校验读取既有结果。没有将 expected_fields 或最终 decoded constructor 作为原始 D 的条件，没有补零或将固定输入扩为 mask 全域。5 项 TDD 边界测试通过；未重读 trace、未重跑模型或 solver。其它五配置及普通 C++ 的 harness 应用保留 OPEN，2622 不是新增 case，也不改变累计 3244/9432。

[vector native/root 与 raw 实例独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-native-raw-root-instance-review/review.json) SHA `8f257d3c5f6cf255b271142723baeaa02da928000b83222ee51aefb38949c593`正式有限 PASS，仅签精确绑定的 native v2-attempt3 与 raw v1：每域 66 根、1202／1222 单元、68280／67316 项 caller/附加义务，多重集与原树路径全核；raw 1688／1897 事件及全部待投影项守恒。独审核 755 依赖、4 项红绿测试与 6 项真实负控，历史 live gate FAIL 保持。共用 v8 的[独立核心证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/independent-shared-closure-checker-review/certificate.json) SHA `ea9e5d80441cc4db5a6a88d90d12904313439f02ac91fe2578e286ff38e654cf`另签表达式引用/schema/目标 extern 库存机制，21 测试、32 负控。两证均不签完整分母、入口 D/dispatcher、type/generated、extern/module 唯一语义或新 raw 投影等价。

[完整 raw 来源投影候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-raw-source-projection-v1/index.json) SHA `50e517c77b528fc3dfbdb9e538e39b250abf59466c7c2260877b985e00879e88`由[应用工具](tools/solve_vector_coverage/vector_native_raw_projection.py) SHA `f36959b606307d5aa815183c482a2de62874b3d4a0fd18e9324825f48b2cb9b9`复用共享 raw projection v3 生成，绑定 810 依赖。工具重核上面实例独审全部 integrity 绑定，联立共享 v8 正式有限消费器，只消费原机制及实例范围；4 项 TDD 边界控制拒绝换图/换 raw、扩大许可和将历史 FAIL 改写。新投影仍待独审。

双域 1688／1897 个 raw event 的完整多重集不变，原精确 kind/extent 729／863 保持；新增 bool infix 357／367、bits 数据运算 18／50、raw when 到两侧 typed guard 各 22、scattered mapping 各 365 的精确来源候选。共享算法使用原生 operator 三元组、实际 operand gap 或单一原生直接 operator，bits 另核 overloaded 原名及结果/双 operand 类型；克隆 guard 的两个 typed link 共同保留。**pending 变为 197／230，分别为 sizeof 94／119、config 92／92、assign 11／19**。来源身份数为 1491／1667，保守组件 root/source/caller 上下文行 28894／30619；这些计数不等于完整源码 branch 分母。generated 68／70、旧 879 在所选 scope 之外的 302／263 以及全部入口域义务保持 OPEN，没有修改主账本或动态/静态覆盖数。

[旧 879 完整 raw scope 对账](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/original879-raw-scope-reconciliation-v1/index.json) SHA `596fc63b2b867ce32ead0c95172e6d4d49c3bc12de9697b5d39aa7f40897ea23`由[对账工具](tools/solve_vector_coverage/vector_original_raw_reconciliation.py) SHA `651f4b2b7f356a2751e4b434b02b4b64549fe0282ff716869cf66ea8a32f82ee`重新使用全 5083 raw scope 和共享 v8 的全部 6372／6410 native 单元，绑定 812 依赖。原“在所选 scope 之外”进一步解释为：两域各 **18 个 DEF_mapdef 声明是 97 个已选 clause scope 的祖先**，原单向 prefix 判断没有登记这层关系；原已有 selected scope 的 577／616 项保持。剩余 ordinary 269／SYMBOLIC 211 项没有同 backend 的精确 native scope，另 15／34 项有 native 单元但不在原组件图中。所有 879 项及完整 raw 归属保留；“未联立同 backend scope”不等于已证明预处理失活或不可达，“图外”也不构成删除许可。

[类型声明依赖应用 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-type-dependency-attachment-v1/index.json) SHA `e1515f0d04a8f2072fb128b77dc50ae9695ab629d89e5f7f648d3da3e42ee612`由[类型附件工具](tools/solve_vector_coverage/vector_native_type_attachment.py) SHA `3adcd4a5e7944780d6e963df7f29b58317f9519b732c588a716b9c34499a671b`联立共享 type v2 manifest `3e7e2b5e7723d02f2fb1e5daeb252b8d05906942328fa486a4caeba8ed47be7e`及全 unit 附件，绑定 831 依赖。按 unit ID、backend、definition、unit_index、kind/name 全身份接入 1202／1222 单元，无需重新提取；4 项 TDD 边界测试拒绝同 ID 换身份、缺失/重复及将编译前件升为运行调用。

两域各保留 227 个保守传递声明依赖。直接参考出现数 77464／86256，联声明后 79114／87906；直接义务 2106／2357，联声明后 2123／2369，其中声明层各增加 8 个 `Nexp_if`、4 个 `NC_and`，ordinary 另有 5 个 `TDC_key`。所选单元各有 5 个 `L_undef`；其 runtime rewrite 单元候选当前为零仍不证明依赖闭合。显式 sizeof 31／34 与 constraint 各 4 单列为 runtime reification 输入，ordinary 92 个 config 引用单列待选择。类型层本身及 raw `ATyp_if`/sizeof/config 来源、实际 module/outcome/undefined 目标仍待独审与桥接；不从 raw 197／230 中扣项，不把参考/annotation 出现数当运行分支分母。

上述 raw 投影与入口附证随后取得[有限独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-native-source-projection-review/review.json) SHA `d5e8c907e9273a5dcab08b0597d35814e17251f7b8b43328836cdfb11c2e0fd3`，manifest `580b57225863455a497075dd55a731a2290998166ef72aafccfa01389fbc947e`。独审核 1039 文件、1599／1775 实际 typed links、完整 raw 与 root/caller 多重集、42 组 2622 固定输入及 924 项状态修订；15 测试和 4 守恒负控通过。[严格消费结果](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-source-projection-reviewed-v1.json) SHA `f280d99b363dcd0e41f7a6d7677df57b0641d5ed3e4a866d14394c67212350ab`由[消费器](tools/solve_vector_coverage/vector_native_projection_review_consumer.py)重核 1051 依赖，4 项 TDD 边界测试通过。首次执行因把 integrity 的 `{sha256,bytes}` 当成 SHA 字符串而拒绝、未写产物；按真实协议修正后通过。许可限来源身份/分类、守恒及固定输入/状态边界，完整 D、raw 语义等价、通用 API 权限、完整分母与历史 producer 链权限仍为 false，原 879 live FAIL 保留。

[类型附件有限证输入消费](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-type-dependency-reviewed-inputs-v1.json) SHA `ec46293306045a90c2579b2d8b9d540b5f0cb1b84667fc82e65566d1839862d9`由[联证工具](tools/solve_vector_coverage/vector_native_type_review_attachment.py)调用公共 `native_type_review_consumer.consume`，与冻结共享结果 `2bc5e03c20fec2d42b347d455af03588dedbef6e039bca17072f18ef9dc4c4a6`逐内容相等，绑定 879 依赖。原 1202／1222 个选中附件重新按完整身份 join 并与 v1 逐项相等，两域各 66 root 保持；各 227 个声明候选中有 **10 个**精确匹配共享独审的 measure 声明构建前件。共享每域全量 13 个 measure 的权限只作用于列定声明表达式，不删除同名 helper 的运行调用。复用原 4 项附件测试通过；vector 新联立本身仍待独审，config/undefined/outcome 运行桥及完整依赖闭包仍 OPEN，raw pending 和覆盖数未减。

[全 native 反向来源库存](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-reverse-source-inventory-v1/index.json) SHA `a5a71c373da73e7e2f9c3f14406134dbd111b3edeaa415ede70bb4bec6da0065`由[反向工具](tools/solve_vector_coverage/vector_native_reverse_source_inventory.py)绑定 1059 依赖、46 个实际 raw 子树路径/哈希，4 项 TDD 测试通过。普通域 1393 节点中 1387 已有关联、**6 未关联**；SYMBOLIC 1444 中 1429 已关联、**15 未关联**。共同六项为 `flen/wF_S/wF_H` 的类型重化 `E_if`、`rF/float_classify` 的 `E_exit` 和 `num_of_vector_support` 的生成 `E_match`；SYMBOLIC 另有 `fp_class_onehot_pure` 的九个嵌套宽度 `E_if`，来自 `float_bits` 的 exp/mantissa 类型条件经 zeros/ones 隐式参数重化。源码 `ATyp_if`、typed condition/public type 与真实 ancestor instantiation 已保存；类型变量替换及隐式参数运行合同仍 OPEN，不能套用简单配置 Bool 常量化模板。

该反向库存逐域保存全部 66 root 的完整 node 集、raw pending、生成单元及实际 immediate caller，反向 root/node 关系为 132／141。所有 68／70 个 generated 单元均回读真实 typed 单元和 raw type 来源：constructor 各 17、getter 各 33、updater 17／19、enum 各 1；仅 enum 单元含控制节点，但其余调用/效果合同不因零控制豁免。两域各四个控制与 BF 既有候选精确重合，仅借来源身份，不借族语义权限。6／15 个反向节点按完整 raw origin 查旧 vector 879 身份，交集为零；没有可直接继承的旧 observed/static。全包仍是待审来源候选，不构成完整源码分母。

[setter 增量来源附件](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-setter-source-attachment-v1/index.json) SHA `9ef1180eb3e821488564ded0906c0d83eb379282ec8152762970f2f17df1396e`由[应用工具](tools/solve_vector_coverage/vector_native_setter_attachment.py)复用已冻结 scalar `join_setters`，接共享 `04261995864504daf71c1c385a0ac2176163be86125efc0beb29a62e59d0c75f`候选；1073 依赖、原 join 的 5 项测试通过。普通／SYMBOLIC 的 **11／19** 个 `E_assign` 各唯一对应 typed setter app；完整 raw 1688／1897 和 root/caller 28894／30619 多重集保持。候选未配变为 **186／211（sizeof 94／119，config 各 92）**；setter 尚待独审，因此原已审 pending 197／230 不正式扣减，运行效果、反向控制和入口域仍 OPEN。

[完整 raw 与旧 source/root 的剩余义务桥](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-legacy-source-root-remaining-v1/index.json) SHA `ed68a64cf7bd48e43dd1751fa97dc3a49ff123731a43d0b562c31605c3f46cd9`由[联立工具](tools/solve_vector_coverage/vector_native_legacy_source_bridge.py)绑定 1064 依赖、回读 2265 个跨后端去重 raw event，4 项 TDD 测试通过。旧 `E_infix` 身份的路径指 `E_aux` 外壳，事件路径指内层 `E_infix`，两者经真实树的 `args[0]` 和原生 operator 三元组连接；scattered mapping 的 `raw_clause_ast_path` 在完整 scope 内共享。由此原 selected **577／616 个旧 source ID 恰好全部对应事件**，其完整源码 hash、路径、token、raw identity 均保留；另有 **1111／1281** 个事件无旧 vector 身份，旧 879 中 **302／263** 项未成为精确 selected event 的说明仍保留。

该桥逐域保留所有 66 root 及 28894／30619 条 source/caller 关系，额外联入反向控制、generated call/effect、附加 native 义务和原完整 root/arm 文件。SYMBOLIC 中主 v14 **全部 13825 原行恰一次**得到完整 source/root 导航，旧 3293 observed 和各 static/pending 状态均可定位；补充账本仅 3164 个 pending 原行有精确事件，未联立的 **1161＝291 observed＋870 pending** 完整保留，主要涉及 mapping 容器/成员及 `get_V`、`assert_vector_num_elem_*` 等来源。ordinary 主账本对应 11531 行，仅为跨后端来源导航，不授予动态观察。原行哈希、完整 source ID、root/phase、arm 和 caller 由[逐行验证器](tools/solve_vector_coverage/validate_native_legacy_source_bridge.py)核对；新 native arm 与运行 caller 的等价合同、D 和完整分母仍 OPEN，未迁移任何 observed/static 权限。

[mapping 容器到实际成员桥](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-mapping-container-member-bridge-v1/index.json) SHA `ce2341378f05c5c2578d605837e4e75725617666f9502a9da2a3b35922d7d528`由[工具](tools/solve_vector_coverage/vector_native_mapping_container_bridge.py)绑定 1515 依赖、4 项测试，分别回读两域 18 个 `DEF_mapdef` 容器和 97 个 raw/typed `MCL_bidir` 成员；容器明确不是 branch。完整 enum 名称、位串值、宽度和 AST/hash 对齐后，保存既有 291 条原行及对应独审 claim：97 个 decode matcher、97 个同次父 frame 正常 matcher=true 的 infallible value、97 个 encode forwards。实际旧输入关联状态附证的 `baseline/default-FD` 与 `enum-sew`，保持审计入口逐 phase 重置原初态。ordinary 只有来源导航；SYMBOLIC 也只保留旧 291，不加主观察 3293。实施期先后因 typed `L_bin` 使用 `Non_empty<Bin_0/Bin_1>` 列表、旧输入 digest 使用排序 JSON 而拒绝，均在创建输出前停止；随后按实际 schema 和各自既定 hash 协议修正，未放宽验证。该新来源桥待独审，剩余补充未联行 ordinary 1011、SYMBOLIC 870。

[配置候选附件](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-configuration-source-attachment-v1/index.json) SHA `b513020e91e63d14b0a8aa811a132f7dbd124c461aa9e3be39c25959b700c165`由[工具](tools/solve_vector_coverage/vector_native_config_attachment.py)复用冻结 scalar `join_configs`，1099 依赖、5 项原 join 测试通过。两域各 92 个完整点分配置键与共享候选精确相等；ordinary 仍为运行期 `E_config` 读取，SYMBOLIC 为 90 个 `E_lit`、2 个 `E_id`，关联真实 Yojson 配置导出值。它尚未取得正式来源许可，actual IR 和配置运行语义仍 OPEN。

[正式 setter 与 sizeof 候选组合附件](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-source-layer-attachment-v1/index.json) SHA `4bddf2acc13fd7cb153376f53652db41cfad031e78b7e3767c908ef105facbc7`由[工具](tools/solve_vector_coverage/vector_native_source_layer_attachment.py)绑定 1143 依赖，调用公共 setter 独审消费器并逐内容核正式产物 `4342fe34a7bf65feaaaa4fb29e395ffa3f4f204b55c8e306ef9a7914e66f8966`，将列定 **11／19** 个 setter 升为正式来源身份。上文 setter 附件的“尚待独审”仅适用于当时冻结候选；现正式 raw source identity pending 为 **186／211**，只扣除 setter，callee/effect/IR/branch 权限仍未升级。再复用冻结 scalar `join_sizeofs`，5 项测试通过，将 **93／118** 项与共享 sizeof 候选 `334b22360180adf5c00cc553ff3a1abbcc0fe76ea43e9a9e626a97c64be365d2` 相联，其中 `bitvector_length` 为 39／41、`__id` 为 54／77；原 raw/root/caller 多重集保持。所有候选联合后各剩 **1 个 flen alias 事件**未配，该数字只描述候选事件配对，不证明完整分母、local binder、类型替换或运行桥闭合；config 和 sizeof 此时均待正式独审。

[全 raw 事件语义角色库存](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-source-semantic-roles-v1/index.json) SHA `de604efdb8c9dbb5fa4d068b7cc7144498548a8268e7db5b102379d4b61701cb`由[角色工具](tools/solve_vector_coverage/vector_native_source_roles.py)绑定 1569 依赖、4 项测试，保留完整 1688／1897 事件和 66 根。其使用的是配置候选阶段输入，早于上述正式 setter 组合，冻结版本不回写。无旧 vector source ID 的 1111／1281 事件按实际语法分为：双向 mapping 成员/选择/值 488／488、反向 mapping 各 1、显式 if 40／41、match 各 10、assert 18／20、Bool 短路各 143、bits 值运算 18／50、sizeof 类型重化 110／135、config 各 92、constraint 各 1、assign 130／173、ref 0／64、return 58／61、throw 各 2。97 个 enum 成员同时关联容器桥和旧观察 ordinal。**角色数量不是 branch 分母**；内部控制、异常、实际 caller、生成函数效果和类型来源义务继续保留。

[剩余旧 caller 的逐 root 对账](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-pending-root-reconciliation-v1/index.json) SHA `e13aba6df5bf0ecc999f84c2f5e216e66201d962f6f9e2b33a979decc9d3c670`由[对账工具](tools/solve_vector_coverage/vector_native_pending_root_reconciliation.py)绑定 1521 依赖、5 项 TDD，按冻结完整依赖边重新计算双域各 66 根闭包，逐旧原行核 source key、完整行 hash 和状态。**SYMBOLIC 剩余 870 全有真实 raw scope/native 单元，不能统称为全族图外**。其精确分解如下：

| 旧候选关系 | 原行 | 现行解释 |
| --- | ---: | --- |
| `assert_vector_num_elem_upto_256/512/1024` 的 5 个 source ID | 660 | native 只在 22 个 execute 根到达；此处旧候选均为 decode／encode，保留待证 |
| `get_V` 的 1 个 source ID | 132 | 存在 backend 来源单元，但没有本次选中组件根 |
| 其余 24 个 source ID | 78 | 旧行原本未指定 clause／phase，来源单元未进入所选组件闭包 |

旧 [caller 候选工具](tools/solve_vector_coverage/p1_pending_source_index.py) 在源码引用有记录但无精确 root Call 锚点时主动保存全部三 phase；这解释 660 项的由来，不是 runtime 不可达证明。新包保存 110 条 source/root 关系、28 条完整真实依赖 edge 及各根一条保守路径和全部立即入边。ordinary 的 1011 原行另为 693 项出现在其他组件根（其中 33 项原未指定 root）、273 项没有该 backend 单元、45 项原未指定且无所选根；它也没有动态许可。旧 870／1011 行均未删除或静态排除，source module/extern 选择、完整入口 dispatcher 与运行 caller 合同仍 OPEN。

[dispatcher 状态域 v2](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-ordered-dispatcher-domains-v2/index.json) SHA `9c4f0fa4b5233724425f49dd39ffba1e7c3ebca4e5386258720a0e4e2eaa0988`由[新应用工具](tools/solve_vector_coverage/vector_native_dispatcher_domains_v2.py)复用共享 `native_dispatcher_order_v2.py`，1056 依赖、4 项 TDD 通过。实际重新读取双域完整 typed AST，四个 dispatcher 共各 1180 个组件（392 forwards、392 backwards、395 execute、1 ext_decode），组件、完整顺序、每域 66 个真实 root 及 prefix/suffix 与旧 v1 全等。924 个旧域联立入口状态附证，**重新计算 D hash 和 scoped root 身份**并完整保留旧域；每个 dispatcher 的全候选模板显式绑定修订后的 D。正常拒绝关系保留前后状态，异常不当正常失败，禁止纯 Bool 前缀捷径。audit 每 phase 重置原 regs/lets、只传 decoded；official 连续传递实际输出状态。42 组 2622 固定输入仍只作来源导航，不定义全 D。decoder 正常 `ILLEGAL`、encoder 列定非 encodable `MatchFailure` 和 execute 的 `ILLEGAL` 消费仍按既有真实出口分别保存。新 v2 应用待独审，入口公式、matcher/binder 实际 IR 顺序、phase gate 和全域关系仍 OPEN。

[config／sizeof 正式来源应用 v2](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-source-layers-reviewed-v2/index.json) SHA `ef7a420bacb6359b898cb61e6882812029d126db129f76f5d6ae55091cee6577`由[严格消费工具](tools/solve_vector_coverage/vector_native_source_layers_reviewed.py)绑定 1213 依赖、5 项 TDD。重调公共 `native_source_projection_consumers.consume`，分别与正式 sizeof 产物 `85f1fce63c3e9ad5d8399ed6fa1acbba6a17276e7db6d7ed439bb45d3dce387a`、config 产物 `99c5cce2564700897a95f15e66864b2f0d26fd82ca84f393b525aa4a454d7105` 全文相等后，再逐 vector 候选原行重核 digest 和所有内容。正式来源现为 setter **11／19**、config **92／92**、sizeof **93／118**，完整 raw 1688／1897、root/caller 28894／30619 多重集保持，**正式 source identity pending 各 1 个 flen alias**。本段更新前述候选时期的等待状态，不回写冻结附件；来源身份许可不证明 local binder、callee、actual IR 或配置运行效果，6／15 反向控制、68／70 generated 单元、九个复杂宽度控制、完整 D 和 branch 分母均未升权。公共历史 live FAIL 保留。

架构 fmtval 协作者对反向包作了只读能力核对，确认 6／15 节点和各域 4 个 BF 候选交集、九个 `eq_int(bitvector_length(raw),16/32/64)` 条件及六个 raw `ATyp_if` 来源；未签新 vector 证。`'n` 到 `'m` 替换、implicit 重化和实际 pass 仍 OPEN，公共 333 项／5 alias 的有限辅助证不覆盖这九个局部宽度控制，不可据此固定 `'m`。

[新增来源的真实 typed 组件](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-new-source-components-v1/index.json) SHA `c4f465a97a68cd2d7bf928d65cdc5122adb12380d52b7c2daf197aa7d0909a54`由[组件工具](tools/solve_vector_coverage/vector_native_new_source_components.py)绑定 1695 依赖、5 项 TDD，实际回读双完整 typed 树，将原 1111／1281 新 raw 事件中的 **702／705** 个控制或 mapping 节点拆成 **2646／2653** 个精确子组件。分别为双向 mapping 488、反向 mapping 1、Bool 短路 143、if 40／41、match 10、assert 18／20、throw 2；余 **409／576** 个无直接 native 控制的值/效果/类型事件原样保留，不豁免内部或 callee 控制。每个条件、Bool 左右操作数、match 有序 pattern/guard/value 和 mapping 方向保存真实 AST 路径/hash、所需实际子树、调用点和全部依赖 edge；mapping 方向拆解复用公共接口。

该组件包逐域保留全部 66 根，新增 raw/root 关系为 25388／26619，控制/root 关系为 16733／16715，立即 caller 和修订后的 924 个入口 D 导航全部保留。源码正常条件的极性仅作待审合同；match 完备/default、各组件异常、assert 消息实际求值顺序、mapping 全部 caller/方向域及 actual IR 均 OPEN。702／705 或子组件数均不是 branch 分母，本包没有涉及暂停的 29 个循环，也没有迁移任何旧 observed/static。

[九个泛型宽度条件的逐实例来源候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-fp-class-width-reification-source-v1.json) SHA `a1f5f29a85c755b1c850fd24ec50d787da1f0c0798bb12e08c7ed22f871c6386`由[来源工具](tools/solve_vector_coverage/vector_native_fp_width_reification.py)绑定 1065 依赖、7 项 TDD，实际回读 `fp_class_onehot_pure` 的完整 typed owner、所需七个声明、raw `float_bits` 和原函数 scope。三个真实 `zeros()/ones()` 的 unit 实参调用分别对应 exp zeros、exp ones 和 mantissa zeros 的三个 typed implicit 参数；每条记录完整 owner/path/module、record 字段、raw `'n` 到局部 `'m` 的替换、accessor 类型、`eq_anything` 和 zeros/ones 的实际实例化、`__size` overload 元数据及 `bitvector_length(raw)` 参数类型。九个实际 `E_if` 和六个真实 raw `ATyp_if` 逐子树相等，保存所在唯一组件 root 的全部立即 caller。

原生 record 字段保留 `bits(...)`，函数声明和实际表达式类型已展开为 `bitvector(...)`，本工具显式绑定真实 `bits('n)=bitvector('n)` 声明。另一个关键事实是：内层六个 if 的注解仍保存**完整外层宽度类型**，不是从 32 或 64 比较起的尾部类型；候选保存实际 else 链的 false 前件和完整期望类型，不声明脱离路径前件的类型片段等式。实施期三次检查分别在 record 字段类型名、val 返回类型名、内层期望类型处拒绝，均未创建输出；随后按实际 schema 修订并复核。冻结编译器 `type_check.ml` 的 implicit 求解、sizeof/constraint 重化与 `type_env.ml` 的 record accessor 规则均以实际源码片段/hash 关联。

该九条件候选待专属独审；它将先前仅位置/类型相关的来源细化为逐实例候选，未直接升为正式来源或分支许可。完整 `'m` 符号域、所有 if 两臂和 else 的 15／112 均保留，没有借函数签名约束排除；module 可见性、有效执行目标、callee 语义、actual IR 和 caller 输入 D 仍 OPEN。它不构成通用 generated API，也不借公共 333 项常量证升权。

[named alias 正式来源应用 v3](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-source-layers-reviewed-v3/index.json) SHA `6c629e85bd430930a1fe3f7a72d60022002ee6b9229931bfeff1e29df5bcb4ce`由[可复用 join 与应用工具](tools/solve_vector_coverage/vector_native_named_sizeof_attachment.py)绑定 1253 依赖、6 项 TDD。公共 named4 正式消费 `cdf9e3e3e97d80b6b3c4e54a6eac27e8aafcf0b910df2d5e9edfe2f6e04044b6`重新运行并全文相等，随后逐完整事件/key/scope、candidate 行 hash、实际 typed 表达式 hash/kind、physical source ID 和嵌套控制核对；内部复用冻结 scalar `join_reviewed_projections`，没有另产出未审 candidate 账本。工具 SHA `16c91e78421b23f76a6a38971e1527ffd073c824182cb6c10994d551e0a15ba1`，`join_named_sizeofs(events, approved_backend_rows, family_event_keys)` 已交 scalar/BF 复用，投影 row ID 可选且原样保留。

两域各新增 **1 个 flen 的正式来源身份**，原选中 **1688／1897** raw 事件的 source identity pending 现为 **0／0**；原 **28894／30619** root/caller 多重集保持。这个零只说明该有限原事件集合的来源投影已经配齐；nested `E_if`、全部反向 6／15、generated 68／70、九个 fp_class 来源候选、module/runtime/IR、caller 与入口 D 的义务均未减少，完整依赖和 branch 分母仍未闭合。主 13825、补充 4325、3293 与 291 既有观察保持。

当前优先完整分母，29 个循环的局部推进仅保留只读结果：当前真实 Gt header、初值、步长、setup/回边和 handler 回入通过两套结构算法；23 个 execute 循环长度均有唯一当前 `get_num_elem` 结果定义。尚未联立完整长度域和当前动态臂，没有新增循环候选或闭合。上述全部工作新增模型运行、case、终态、源观察和静态排除均为零，正式证据仍限 `56cc/default`。

[九个泛型宽度来源的正式消费附件](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-fp-class-width-reification-source-reviewed-v1.json) SHA `853243c3fe90f7c9763a2f1e47df780cfcd3dfb8fe5a486da1ed647c284d64fa`更新上文九条件候选的等待状态；原候选和反向库存保持冻结。[独审证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-fp-class-width-reification-source-review/review.json) SHA `2405199173c3125e0abd64ee719ba77ebdab2b6ab3a13487d0081ad8fb0da238`实际回读完整 SYMBOLIC 8016 definitions、九个声明、三个 implicit 调用、九条件／六 raw 来源，另核 raw 参数无同名 shadow、`fp=float_decompose(raw)` 的实际 binder 与唯一 caller 的 raw/typed foreach 来源；8 项独审测试、7 项 producer 测试、56 项实际负控及六个 inner/outer 类型边界核对通过。

[严格消费器](tools/solve_vector_coverage/vector_native_fp_width_review_consumer.py)的 7 项 TDD 通过，完整重哈希 1120 个依赖；将每个 claim 与候选完整 condition/application、反向原行 digest、owner、native/raw 路径与 AST hash、implicit/raw call、完整外层类型和结构假前件逐项精确关联。正式许可只增加 **9 个来源关系**；原 SYMBOLIC **15 个反向控制义务全部保留**，普通六项及 generated 68／70 不动。完整 `'m`、所有两臂、else 15／112、caller/loop 输入域继续保留，module 有效 callee、IR、运行分支、D 和分母仍 OPEN。旧 3／457 live FAIL 原样保留；本轮模型运行、动态 case、观察和静态排除新增均为 0。

[生成 bitfield 的有限来源候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-generated-bitfield-source-v1.json) SHA `84dbe946bf25a59fa1893a074921cc5faec336a73812d5d78ef81dfeeab8f5df`由[逐单元来源工具](tools/solve_vector_coverage/vector_native_bitfield_source.py)绑定 1065 依赖、7 项 TDD，实际回读双完整 typed AST、raw AST、各域 19 个原 `TD_bitfield` 来源以及相关 alias、record、函数和 primitive 声明。普通／SYMBOLIC 的 **67／69** 个 bitfield 单元为 constructor **17／17**、get **33／33**、update **17／19**；所有真实 body 逐项匹配原字段的有序端点、`v/x` 参数和 `bits` 结构字段，核实际调用的类型实例及输入输出类型，保留完整 `xlen` 名称，不把它替换为运行时常量。

本候选同时保存真实编译器 `bitfield.ml` 的 constructor/get/update 宏规则和 `type_check.ml` 的 record 展开入口。**54／58** 个真实调用及同数 outgoing dependency edge、**4／6** 个额外 `sizeof`、两域全部 **66** 个组件 root 与所有原 caller 原样保留；各域一个 enum 生成单元也仍在原 **68／70** 总集合内。该有限集合只有单 bit／单范围字段，没有外推 concat 或 register setter，也没有证明完整 macro 默认 order 环境。零控制节点不授予豁免；primitive 运行语义、调用效果、有效 callee、IR 和 caller/D 仍 OPEN，候选等待独立审查，不新增观察或静态排除。

[新增源码组件的正式消费](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-new-source-components-reviewed-v1.json) SHA `b89f494d36768a614f9b7b2c2e512531debb969b8b2dc34a68169c50ef16de37`由[消费器](tools/solve_vector_coverage/vector_native_new_source_review_consumer.py)核 1716 依赖、5 项 TDD，消费[独证 47208](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-native-new-source-components-review-v1/certificate.json)。原 **1111／1281** raw、**702／705** 控制、**2646／2653** 组件及全部立即 caller／9c4 D 身份保留；非控制 **409／576** 也未删除。许可只为实际组件身份与结构，匹配拒绝、异常、assert 消息顺序、全部 caller/D 可行域和分母仍 OPEN。独审为 5 项测试、5 项 producer 测试与 6 项实际突变拒绝。

[initial type 正式附件](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-initial-pass-type-attachments-reviewed-v1.json) SHA `ead7b41b446a5cdd592295cea6e7ebb9d5a4e25be39f8fafc841abba718ffdbb`由[接线工具](tools/solve_vector_coverage/vector_native_initial_pass_attachment.py)复调公共 initial331 消费器并要求全文相等，复用冻结 scalar `join_initial_literals`，核 1919 依赖、4 项本地 TDD。精确交集 **38** 项：xlen 17、ext_d_supported 4、vlen_exp 11、elen_exp 6；同 unit 的原 obligation/ref、定义路径、源位置、节点 hash 和 alias 声明全部联立，保留 **38** unit 关联、**1476** root 关联及全部 **66** root。两项 Zbkb pending／另层 exit source 与本族交集为 0，没有复制其义务或改写共享旧 pending；本附件不证明普通域 literal、后端控制删除或 actual IR。

[反向来源正式附件](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-reverse-source-origins-reviewed-v1.json) SHA `ad4f6e0c08ba0839e7c5d1581a96a3ea77d28616572e9dd0c46597c86969b029`由[精确子集消费器](tools/solve_vector_coverage/vector_native_reverse_review_attachment.py)核 1587 依赖、5 项 TDD。先重新联立 scalar `5ac7fdc8` 的完整 16 签名和 BF `c3c96767` 正式原行，再按 backend/unit/node、完整 AST、definition/unit_index/path 取本族交集：普通 **6** 项全部来自共享来源；SYMBOLIC **15** 项为共享 **6** 加本族九宽度证。两域反向 source identity pending 现为 **0／0**，全部 **21** 控制义务仍保留。每域只继承 enum/rF **2** 个原域局部后端关系；`float_classify`、`wF_H/wF_S/flen` 及九宽度不借此升权。此段更新旧反向来源待审状态，不修改旧报告。

[bitfield 正式来源消费](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-generated-bitfield-source-reviewed-v1.json) SHA `9ab2cb25dc92f74d717d5a102099f899be1e928c893517c62d55b92effd25d22`由[消费器](tools/solve_vector_coverage/vector_native_bitfield_review_consumer.py)核 1127 依赖，逐 **136** 完整 claim、原 generated 行、unit/raw/declaration/call/sizeof 哈希、所有 outgoing edge 和各 root context 精确相等。[独证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-native-generated-bitfield-source-review/review.json) SHA `5889b3f75d1ae67050fcda808b40e0e92ec6f875caeb31be6a5499a585af34c1`独立完整双 AST 重建、producer 逐字节复演、8 项独审测试、7 项 producer 测试及 77 项实际负控通过。原 **67／69** bitfield 单元的来源全部正式；**54／58** 调用、**4／6** sizeof、enum **1／1** 和全部 root 保持。primitive 效果、module 有效 callee、macro 默认 order 环境、IR、caller/D 和全分母仍 OPEN。

bitfield 消费首轮测试有一项夹具错误：移除的第一个 root 不属于被测 `Mk_Misa`，因此该 unit claim 应保持相等。冻结原测试、工具和产物未改；[新测试夹具](tools/solve_vector_coverage/test_native_bitfield_review_consumer_v2.py)改为移除该 unit 实际所属 root，5 项通过。[消费验证记录](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-generated-bitfield-source-consumption-validation-v1.json) SHA `a89c315bbc5f54f419366962851e57dd2a75606ea0972e64b1fccb5a1d4ff825`保存实际命令、输出、所有文件哈希及首轮失败原因；完整 backend 的全部 66 root 另由整表 digest 保全。

[统一剩余义务包](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/semantic-remaining-obligations-v1/index.json) SHA `d236378bccc7d5981dbb6838a92b6b9584eda7dc0eebd2fbba7ff1a06eb50514`及[八类语义表](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/semantic-remaining-obligations-v1/remaining.md)由[生成工具](tools/solve_vector_coverage/vector_semantic_remaining_inventory.py)核 3238 依赖、3 项 TDD。[manifest](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/semantic-remaining-obligations-v1/manifest.json) SHA `69a92e9f97de50a5f65e8c20225deaa0ff2a35e092db8a59946523d85a448bd4`固定机器表与人读表。八个 gate 为 source arm/loop、正常异常拒绝、generated primitive 效果、module/有效声明、type initial→backend、stateful entry D、精确 caller 域及旧 arm 证据迁移；每项并列 source/typed/IR/caller/D、已有许可、未过门、下一行动和 owner，均为 OPEN。

该包以冻结路径、SHA、JSON pointer 与整表 digest 保留 **50** 份原表，完整保存所有原 occurrence/root/ref；控节点按 backend/unit/node，附加义务按原 semantic ID，旧 arm 按完整 source key/arm 归组并保留每个原行 ordinal。普通／SYMBOLIC 的 **1393／1444** 控制、**1688／1897** raw、**28894／30619** root/raw 记录、**2123／2369** type 义务、**79114／87906** 引用、**1202／1222** unit、**141／151** extern 和 **132／792** scoped D 均可回读；这些数是原集合规模，不能跨 gate 或 backend 相加为 branch 分母。首轮生成仅因相对输出路径格式在写出前拒绝，修正为根目录相对展示后成功；没有覆盖既有产物。本轮全部新增模型运行、case、终态、观察与静态排除仍为 0，loop29 持续暂停。

### 实际 Env 到原节点、root 与剩余义务的附接候选

[实际 Env 附接候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-environment-selection-attachment-v1-attempt2/index.json) SHA `6c380c78cee084c9d3f0f80dc6c0b099a85a14c9ce73c185c1419d49c67e4f9b`由[附接工具](tools/solve_vector_coverage/vector_native_environment_attachment.py)绑定 **3609** 项依赖。工具调用公共 `native_env_review_consumer.consume`，与已冻结[共享消费产物](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-environment-resolution-reviewed-v1.json) SHA `01e156b053b54f7babb485bef51c6c33df75e34f0e70858067ec62dddbf29af8`逐内容相等后，回读两域完整原 AST、selection、declaration join 和 query 表。本族附接仍为**待独审候选**，不新增语义闭合权限。

| 完整保留或精确附接的对象 | ordinary | SYMBOLIC |
| --- | ---: | ---: |
| 全模型实际 selection 原出现 | 55584 | 57975 |
| 完整 signature query 变体 | 6807 | 7060 |
| 仅供诊断的 selected Id／original binding／extern 聚类 | 2340 | 2384 |
| 本族原 unit／其中实际 selection | 1202／10327 | 1222／11438 |
| 原边全部精确对应实际查询节点 | 5156 | 5651 |
| 原 extern 调用：完整 DEF_val 与 extern 对应／声明身份仍待证 | 943／935 | 1044／1504 |
| 原类型引用／类型义务 | 79114／2123 | 87906／2369 |
| 原 raw 事件／raw-root 出现 | 1688／28894 | 1897／30619 |
| 原未解释 caller 行 | 1011 | 870 |

unit 完整路径来自原类型附件的 `source_clause_path`，先与 `definition_key`、`unit_index` 实际取出的完整 unit 树相等，再拼接原节点路径。每个 selection 核完整 owner/node SHA、identifier、operation 和 current Env；完整 query 保留内部类型位置、freshened binding 和 `union_binding`，不以诊断聚类替换变体身份。所有原 66 root、立即 caller 边、raw-root 关系和原 50 张完整表的冻结引用保留；原候选 body targets 仍单列，实际签名选择不自动授予执行体身份。

[原边验证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-environment-selection-attachment-v1-attempt2/edge-validation.json) SHA `930e150df5e018a7ba04cbe8e0419290b139cfe3ecd94349038be59d814d7db8`由[校验器](tools/solve_vector_coverage/validate_native_environment_edges.py)回读全部 **4851／5267 个 call＋305／384 个 global reference**，核名字、module、完整位置，及调用的完整 typed annotation/application。两域合计 10 个真实边变异均拒绝；[本地测试日志](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-environment-selection-attachment-v1-attempt2/local-tests.log)记录 **9＋2 项测试通过**。两种既有 hash 协议分别使用；未用 Env 的排序 JSON hash 替代原节点的非排序 UTF-8 hash。

每域原 6 个非 unit scope 项和 22 个未定 scope 声明全部保留：**21 项无表达式查询，7 项含子节点查询但实际声明写入来源仍待证**。四个无 typed Env 的 loop-measure `E_id` 与共享[构建前件附层](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-untyped-environment-measure-attachment-v1.json)按完整声明及表达式/父路径精确相交，恰为每域两个原未定 scope 声明；本族类型引用表与它们交集为 0，不造 Env 查询、不排除同名运行调用。类型引用处于表达式 annotation 内只记录结构上下文，不能变为该类型引用的实际 Env 选择。

旧 caller 行中 ordinary **693**、SYMBOLIC **660** 可经原 source 事件导航到此次附接，但其请求的 root/phase 和精确 caller 域仍 OPEN；其余 **318／210** 无选中 source occurrence，原行及未解释原因仍在。`LOCAL_OR_GLOBAL_LET` 不证明 binder 身份，`LE_id` 的 `UNBOUND` 仅表示赋值前 Env；signature 的声明差异、callee body、实际声明 write、完整 module、IR、stateful D 与完整分母均继续 OPEN。

[剩余维度明细](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/native-environment-selection-attachment-v1-attempt2/remaining-dimensions.json) SHA `db694e0d728723326bf908c858c53d81faf044a4c2b52e42c8e9292ce466a03a`由[汇总工具](tools/solve_vector_coverage/summarize_native_environment_attachment.py)重核 **3614** 项依赖并复用公共 noEnv `attach`，完整重建上述四项交集。4851／5267 个原调用中，完整 DEF_val 候选为 **2802／2977**；其余按公共原诊断分列为位置元数据差异 **1105／1243**、binding 结构或内容差异 **754／846**、union 无 DEF_val **179／191**、generated/other 无 DEF_val **11／10**。每项仍指完整 query key，诊断不授位置删除或 alpha 等价。汇总首轮因外部 OCaml 依赖路径不能相对仓库表示而在输出前拒绝，修正为如实保留外部依赖绝对路径后通过；原日志未覆盖。

依赖计数勘误：本节早先及交接消息曾引用运行末尾 stdout 的 **3610／3615**。两个工具均先写入 JSON，再在打印摘要时调用 `reference(index)`／`ref(output)`；后者把刚写出的文件加入内存依赖表，因此打印值比已冻结表多 1。冻结 `index.json`、`remaining-dimensions.json` 和 `manifest.json` 一致记录 **3609／3614**，以前者为准。三个文件及其 SHA 均未变，原 stdout、历史消息和源码保留。

实施记录保留首轮受控中断日志：预检发现 global reference 使用 `status`、call 使用 `resolution_status`，按原类别修正后第二轮完整结束；首轮未生成候选。原 `semantic-remaining-obligations-v1` 未修改。正式动态仍仅 **56cc/default**，本轮模型运行、case、终态、观察和静态排除新增均 **0**，loop29 继续暂停。

可复验命令（输出须选不存在的新路径；这些命令不执行模型）：

```sh
python3 -m unittest discover -s agents/float_support_review/tools/solve_vector_coverage -p 'test_native_environment*.py' -v
python3 agents/float_support_review/tools/solve_vector_coverage/vector_native_environment_attachment.py \
  --shared-review isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-environment-resolution-reviewed-v1.json \
  --output "$VECTOR_ENV_NEW_OUTPUT"
python3 agents/float_support_review/tools/solve_vector_coverage/validate_native_environment_edges.py \
  --candidate "$VECTOR_ENV_NEW_OUTPUT/index.json" --output "$VECTOR_ENV_NEW_OUTPUT/edge-validation.json"
python3 agents/float_support_review/tools/solve_vector_coverage/summarize_native_environment_attachment.py \
  --candidate "$VECTOR_ENV_NEW_OUTPUT/index.json" --output "$VECTOR_ENV_NEW_OUTPUT/remaining-dimensions.json"
```

### 56cc69 来源、V4 源义务与严格审计

冻结 basename 为 `isla-unified-p1-v4amo-candidate-20260927.nb1d9n1s`，IR SHA `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`，candidate manifest SHA `fdf105d19a9ac62f9c5036fbc80759adb7e9b500a51a34fcc4f886016329129e`，最终 generation SHA `9f01067ea8f2da31b37f5089e4c5870e47e8299f7622b9a456585a0648176a77`。v3 generation 绑定该 candidate manifest 及原始 model build SHA；runtime 仍绑定旧共同 manifest `28fb65ee…55e`。[来源正测](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-binding-positive.json) SHA `4faba1ccf1e7ee85f1075e403d83ab3e0865d4b83d38db7af1f4ccc1c956f762`重跑真实 v3 verifier，`source_binding_complete/reexecuted=true`；bridge SHA `388f295c34f02f426a70899cb1960ff77ca176a3c5c60cb63adce2a85d8cc9c0`。

[新源码目录](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/catalog/source-branch-catalog.json) SHA `3a30e17c6b1994da3941f94a018c5da59e63d397afd75d8159319fc5f99a6972`：22 clause、九文件、879 词法 site/2335 arm，其中活动 668/1784、out-of-build 211/551，73 数据策略。旧目录迁移登记 843 个保留候选、36 个 non-SYMBOLIC 待等价及 27 个手工迁移义务。[lowering 候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/lowering-candidates.json) SHA `6c37875b6b03992099cb7b1c928226014832ecde0121acf1210ea77cb8262689`在 668 个活动 site 中给出 323 个候选组，`actual_trace_catalog_verified=false`，仍需实际 root/CFG 消费。

[V4 源分支保留合同](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/v4-source-retirement.json) SHA `d5211e03e00b1f647a6e5c5f6347ed1e1f29ce5824fdb2ad3a96324a17cd8f75`逐完整函数正文核对旧 `1dcc/348147` 源码相同，消费组件等价与完整 IR 独审，并检查新实际六函数闭包没有 Jump/Goto/Exit/Arbitrary。`valid_fp_op` 四 site、`illegal_fp_normal` 两 site、`valid_rd_mask` 一 site 的 **7 site/14 arm 保留为 `not_lowered`、`observed=false`**；`valid_vtype` 虽旧目录没有控制 site，仍有完整函数合同。旧 root 与见证保留历史身份，新 caller 实参域及返回消费仍待核。

[主批严格索引](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/strict-audit-index.json) SHA `9d06e1abb30c5a03a4cb8a9d5a0ccbd483ce3dfbc55f0972ed8b3b0035321a94`为 **PASS：15 task、3228 case、9396 终态**。[增量严格索引](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/increment-strict-audit-index.json) SHA `1f92fdfb603831e34fdbd600d771b9878843202e511d819bc383b06cfd27c1c4`分别记录 slide2 **2/6**、conversion FS6 **6/6**、num32-8 **8/24**。每项使用对应新 sidecar，验证全部 **25676 runtime Jump**、实际 R1、输入/结果/初始化/trace/trace-map/唯一终态，且每项重新执行 v3 来源 verifier。精确 source/root 新见证另行审定；case PASS 不代替源码闭合。

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/p1_strict_audits.py \
  --stage "$P1_STAGE" --snapshot "$P1_SNAPSHOT" \
  --source-bridge "$P1_SNAPSHOT/source-repackage-proof-v3.json" \
  --source-binding-version 3 \
  --expected-ir-sha256 56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac \
  --expected-runtime-jumps 25676 --jobs 3
```

此处 `P1_STAGE` 为 `isla/target/float-support-review/final-coverage/integration/p1-56cc69`，`P1_SNAPSHOT` 指向本节冻结。脚本拒绝覆盖输出；重现须另备输出树。首轮调度在任何输出写入前因沿用 `348147` 的 runtime index 状态名而中止；v3 现明确验证 `p1-runtime-catalogs-v1/PASS`、IR SHA 和各条 sidecar，旧 v2 判定不变。

#### 新 num32 的 70 个实际 caller 见证

[独审证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-num32-70-review/certificate.json) SHA `d1f687d0e0898fff2846115541bba2232b2789c36719dfb182e21fdd730edaec`核验新 IR **35 root、两 source site、70 个实际方向**：完整 24 终态、791629 指令、59267 动态 Jump 的嵌套 Call/正常返回续体，实际 num_elem=32、vtype 无写、源码 v3 与严格审计重跑；独审六项负控通过。适用域仅 default FD、Machine、vtype=`0xa`、SEW16、LMUL4、VL0。每个 root 观察 `<=16 false` 和 `<=64 true`，不要求实际 num64。

[消费器](tools/solve_vector_coverage/consume_num32_review.py)重新核全部证据文件 SHA、当前 catalog 的完整 source identity、实际 sidecar Call/Jump、完整 runtime 25676 Jump 等值，以及每条见证的原始 trace 块/边索引、终态身份、完整 context、callee 正常 End 和逐层调用续体。[新版本独立账本](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/new-ir-observed-num32-70-ledger.json) SHA `750af71054550ebdf66b0f411fe88108a4d46063ef18570106de6961c78f573e`正式记录 **70 observed**；[九项消费负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/num32-70-consumption-controls.json) SHA `f7b67898f50947aaaf9dbb1c633593a14a292134aac33eb8df5548fe0960991e`全部拒绝跨 IR、错 source token/edge/root/num_elem/终态/context、缺续体或缺完整 phase。旧 89 前沿未修改；八 case/24 终态已属于上述 16 个增量，不重复计数。新 IR 全部源码分支仍未闭合。

#### 新主批 source/root 账本及 slide/FS17 消费

[新主账本 v1 索引](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v1/index.json) SHA `6c26382e87e97c94b57da5da67875b69132c7fb959479b8828502ab20d601fd4`绑定全部 18 份严格审计、3244 case/9432 终态及六个实际配置，由 [p1_root_ledger.py](tools/solve_vector_coverage/p1_root_ledger.py)重读当前源码/scopes/typed Call 闭包和实际 context。每个配置登记 **13825 条保守 source×clause×phase×root×arm 义务**，这些来自 668 个活动 site 中已有映射的 **547 site**；余 **121 site** 在账本另列，不能声称 13825 是全部源码可达分母。普通 323 组映射中 292 组结构已核、31 组谓词源语义待审；[新短路候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/full-short-candidates.json) SHA `0a808f659a21db99bfed8c8aeeb01905c3ce7c25b87f4d8609812e9dac6115a8`和[CFG 检查](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/full-short-cfg.json) SHA `2cadea84d0e0dd822053b61ff6f6ff6c6f4652007baf7f8edbee5baea00fa09f`覆盖 224 site/482 组结构，仅登记 LHS。每配置另有 **228 条 V4 历史源 arm×当前实际 root 的 `not_lowered` 义务**。旧 observed/fixed/domain 排除均未导入。v1 已交独审并冻结。

[slide/FS17 独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-bf-slide-fs20-review/slide-fs17-certificate.json) SHA `8c9550a46937a85c8116c05af1546b40b42b3cfe56bcdf1c655113d54de2d675`签两条 slide 普通 if 与 15 条 FS AND 的 **LHS=false、RHS 未执行**；含 BF 组的联合审查共重建 21 个 phase，vector 子范围为八 case/12 终态。完整 Call/End、instruction_count、R1 和九项语义负控已核。[消费器](tools/solve_vector_coverage/consume_slide_fs_review.py)按当前 global key、`direction_key_sha256`、phase/root/edge、LHS 消费和终态/context 精确消费 17 项，生成[主账本 v2 索引](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v2/index.json)，SHA `fbb75b60fc68510927d7a86a295fa64d1bc45b5387d37db273e901e49149b85d`，保留原 v1。

v2 默认账本 SHA `8510cb5e7804b5b3a1ff131cc1f56a0e6ffa7c407dbd49f3892f68f02e4e370c`在 13825 中登记：**87 项独审观察（num70+slide2+FS15）**、4877 项结构映射及实际 context 待账本独审、74 项已执行 edge 但谓词源语义待审、8787 项待见证/域证明。七项[消费负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v2/consumption-controls.json)全部拒绝，SHA `a6f5f8ae971f42cd289a00c612ec97633b85c0998dadcf2c9c52f333c60f9d15`。FS15 不计 RHS 值或 RHS 异常闭合；八 case/12 终态已在 16 增量中，不重复计数。旧版 87 项待核与新版 87 项观察是不同版本、不同账本。

[主账本独审证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-source-root-ledger-review/attempt3/certificate.json) SHA `0c1c7920ec60ef8940103cae1ad4be9804851a8c14166d0a1fbaaac3d3184bc7`已完成六配置：逐条签署 **17427 个实际 edge 与完整 phase/Call/End 许可**，其中 **11233 普通结构重算、5970 短路 LHS 结构与执行、70 原 num32 域观察继承**；这些类别重叠，不能相加作为分支数。其余 224 个 predicate 条目只获动态许可，默认配置为 74。独审重建 **1368 个选定完整 phase**，核对 3244 case/9432 终态守恒，40 项负控拒绝；未签全部源码分母、RHS/异常或额外 source-arm 语义。

[逐条消费器](tools/solve_vector_coverage/consume_source_root_review.py)核对证书及所有依赖 SHA、完整 config/clause/phase/site/arm/root/edge 键、源码身份、原始见证、实际 sidecar Jump/Call/End/续体，以及完整 phase 哈希和调用嵌套；同时重算 v2 的 slide/FS17 并逐 row 比对相等。[新主账本 v3 索引](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v3/index.json) SHA `86e3bdae030f0f61003c2f19e38db192dee9198950151e720a99041cededbc07`保留 v1/v2，默认状态为 **87 语义观察、4877 已独审结构/执行但源语义待核、74 已独审 edge 但源谓词待核、8787 待见证/域证明**。九项[消费负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v3/consumption-controls.json)均拒绝，SHA `1ad4fab8ebe0258cce1d378bc6828558ceaf5a6ef9c6608c02c5eebf148ce658`。本次没有增加 observed、case 或终态；13825 仍只覆盖已有映射的 547 site。

[主分母外补充索引](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/pending-source-caller-index-v1/index.json) SHA `cb1c40a5abf6e711c15446e8fe4543b4128c3c6dd46aed38feac45374a7f77f7`由 [p1_pending_source_index.py](tools/solve_vector_coverage/p1_pending_source_index.py)生成：六配置各保留 **121 个未映射 site 的 4325 个 source arm/caller 保守候选**，以及 **1880 个短路 site/root/phase context 的 5640 个 RHS 待证项**。RHS 分列正常 true、正常 false、正常结果前异常三类；此处只是待证合同分类，不是异常穷尽证明。源码锚点和原始 Call 闭包只用于搜集候选，未据此认定真实 caller；无法定位的 root/phase 仍显式保留。索引链接 27 项旧源迁移库存，V4 的 228 项仍由主账本保存。所有补充项均 pending，新增观察及排除均为零。

[新归约 Err2 绑定候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/reduction-Err2-current-binding-candidate.json) SHA `8d7e51fa1c9526430728bf039753c9d6b4b3390703583f17a74a49c8120e4a07`按新 execute 源码区域定位实际 Call，再核新 Kind/destination、完整 callee/get_start 正文和正常返回 CFG。当前 get_start=Ok 前提下 End 全为 Ok；撤此前提时保守返回集合含 Err。新 root 的 vstart/SEW/无写条件仍待独审，两项继续 pending，未借旧版排除。

[全函数 typed 重绑独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-function-rebinding/certificate.json) SHA `53030a4e5dd63882b07077dc94c130fefba1e0769a738fde6f132988a3235f3d`首批 16 函数为 **9 PASS、5 FAIL、2 UNCOVERED**。`get_start_element` 等九函数结构通过；`init_masked_source` 因原始诊断字符串中的源码行号 413→414 整体 FAIL，四个 V4 函数也 FAIL，整个 `execute` 未覆盖。只有函数总体 PASS 才可消费其 `pc_map/name_map`；局部结构 PASS 不能绕过整体失败。这份证书不迁移 caller、状态前提、动态见证或源分支排除，Err2 继续按当前函数正文与当前 root 前提重建。

[当前 root 前提候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/reduction-Err2-current-root-premises-candidate.json) SHA `22c068bb2b7fa04c2c58b36e20496b8ea61dce13995711c5db2e117c6d0d17f7`由 [p1_reduction_root_premises.py](tools/solve_vector_coverage/p1_reduction_root_premises.py)重新读取当前 `ir/rv64d_p1_unified.ir` 与实际 sidecar 并重跑 v3 来源绑定。两 root 的 `assert_vstart(0)` 检查支配后续调用，非法结果不能到达 root；前缀和 callee 的全部分支扫描没有 vstart/vlen_exp 显式或间接目标写入，全目录保护全局 Ref 逃逸检查通过，外部 helper 仅有实际绑定的 `read_register_from_vector`。未使用旧 fixed CFG 或函数重绑 map。

SEW getter 的实际输入只取 vtype `[5:3]`，八种值全部枚举：0–3 正常返回并使 `get_start_element` 返回 `Ok(0)`，4–7 进入真实 `AssertionFailure` Exit，未当作正常 Ok。完整 `init_masked_source` 正常返回 CFG 因而仅保留 Ok 候选；六项静态负控分别拒绝错误 vstart 检查实参，并在撤销 vstart=0 前提后重现 Err。这里只验证候选计算，当前 root 前提与列定原语效果仍待独审联立；两项继续 pending，新增观察和排除均为零，不声称无异常或保证终止。

上述候选随后通过[当前 Err2 独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-reduction-err2-current-review/certificate.json)，SHA `23ade870f800029f89b8103aa1a94dc3ffbe685e26e64b8fd0d21112b02b4fb8`：全新 guard、vstart/vlen_effect、八值 getter、131 指令 callee 正常 End 的反向到达定义及外部/variadic 作用重算，六项测试、七项语义负控通过。只授权当前 RFVVTYPE/RFWVVTYPE 两个外层 `Err(())`，未使用旧固定证书或全局 phase 纯度前提。[消费器](tools/solve_vector_coverage/consume_current_reduction_review.py)逐文件和精确源/root/Kind 消费并重算正常返回 CFG，生成[主账本 v4](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v4/index.json)，SHA `ad773d48d11c831113b852e68a1ff9028ccb9fbd63ca88a9f503eb78c31967f2`。默认账本现在为 **87 observed、2 当前静态排除、4877 已审结构/执行但源语义待核、74 已审 edge 但源谓词待核、8785 待见证/域证明**。七项[消费负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v4/consumption-controls.json)拒绝，SHA `99106d383abc0bb636e86da4eb5acdac7eb2ec904936eea3cfe937527fbcef9c`；动态数量仍为 3244/9432。

#### 共享合同优先级

[工作包聚合索引](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/shared-contract-work-buckets-v1.json)，SHA `4d33b25b5ecd672db1ae691031f78e1d5078ab89b9db7a510ced5c4ada518e7f`，基于 v3 库存生成 1231 个 default 源表达式/实际 callee/待证原因组，六配置分别计数；每项引用原 row ordinal，保留 clause/phase/root PC 和实参 AST。该索引没有新增 pending 或合并 caller 参数域，Err2 的后续 v4 变化以上节为准。

| 顺序 | 最小共享合同 | default 既有库存（类别不相加为分母） |
| --- | --- | --- |
| 1 | 四配置 Bool 的实际初始化优先级、入口不覆盖、完整 phase 无写/Ref/特殊原语写，再据当前 flag Jump 裁剪每个实际 root 闭包 | 主表 4050、未映射候选 520、RHS 合同 51；当前只准备主表中已映射的精确排除，后两类仍待证。 |
| 2 | SEW/LMUL 全有限正常返回域、vlen=128 与每个实际 root 的 SSA 维度/数值转发，补 assert/helper 合同 | 主表 3434、未映射候选 3215；无 lowering 部分先补完整源码到保留 IR 的关系。 |
| 3 | `hartSupports/currentlyEnabled` 的实际枚举、配置 misa 与完整 FS/VS 有限域，分别核 LHS、RHS 正常值及异常 | 主表 2876、RHS 合同 4314；各配置和实际 extension caller 分别绑定。 |

#### 当前配置 flags 候选与独审勘误

[配置候选 v2](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/config-flags-current-candidate-v2/index.json)，SHA `eb70c860393a7a2b9e20c8c79692be42d28082f547e6ceb8e70397524502375b`，按六配置分别列出 **4465/1489/4465/4465/4465/4710** 条精确主账本候选，共 24059。候选生成时未修改 v4 或增加排除；后续独审与 v5 消费见下段。默认 4465 包含 rV 的 2304 条与 wV 的 672 条，分别保留 72/21 个实际 root 的全部 bv5 索引；其余被配置关闭的下游函数还包含原本归入 typed/assert 桶的义务，不能与原 4050 桶相加。未映射 520 与 RHS51 未消费。

[生成器 v2](tools/solve_vector_coverage/p1_config_flag_contracts_v2.py)核对实际 TOML 默认 Bool、运行时 `initialize_register` 的配置优先级、3244 条既有输入无内部 flag 覆盖、实际 runner/R1 符号集合不改四 flag，再记录 22 execute 入口及 decode/encode 的原始完整调用闭包。四 flag 共 21 个实际引用均为直接 Jump；native、Reset 及特殊外部函数的效果由独审继续联立，不能仅凭直接写或 Ref 为零断言整个 phase 不改配置。[共享前提](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/config-flags-current-candidate-v2/shared-premises.json) SHA `3da6ea68f1a6245b6e0a14151e69569a48691d5d05f48ed3c7a1bc9927d7529a`。

冻结 [v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/config-flags-current-candidate-v1/index.json) SHA `d9ac8f3e33e323b42e85f8a7da75307a5d796372fe1491896a18bae788931148`有一处独审确认的生成器错误：`root_call=null` 时漏掉 phase 的下游函数，且以入口函数的 PC 集合检查 callee 的 PC，误列 455 条非默认 decode 义务为配置排除。实际 `zext_decode` 调用 `zencdec_backwards`，该 decode 闭包没有四 flag gate。v2 同时修复闭包与 PC 所属函数；[逐项修订核对](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/config-flags-v1-v2-revision-check.json) SHA `891a620179a744e0502ef1e1862f5b616656b72ac394b8d38d4b115283140c34`确认只撤回 455 条、无新增，保留的 24059 条完整 claim 相同。v1 及其生成器保留，不覆盖失败记录。

[实际反向配置负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/config-flags-actual-reverse-negative-control-v1.json) SHA `0e470335baba071c1abcd1b94e510a1b3eeaaa4e68e3c1958c0b0be6abcff43c`由[独立补充脚本](tools/solve_vector_coverage/p1_config_flag_negative_controls.py)解析既有目录：实际 `210396…` TOML 与默认配置仅有 `__isla_vector_vpr=true→false` 差异；各自 sidecar 重算 21 gate 后，默认排除的 93 root×32 arm 全部恢复保守可达。此为静态负控，无新执行、无动态反例，也未缩小索引域。

[配置 flags 正式独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-config-flags-review/certificate.json)，SHA `10b9c99db26d5567a144ab0cd43209765d6bde48883b24abdbc506d8b47b4cc3`，对六配置的 24059 条全部签署 `PASS_SCOPED`。独审从整个 `zexecute/zext_decode/zencdec_forwards` 重建原始完整闭包，核初始化/R1/3244 条输入、直接 flag 读与全部原语/Reset/特殊调用效果，并重算源码结构及每个实际 root 的裁剪闭包；六项单测、八项负控通过。其[独立反向配置证明](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-config-flags-review/actual-reverse-config-review.json) SHA `4374694192416f485b6d9d6cbbc10ead050f260c6ffd3e3a83de3d08861b3cd2`重新确认 2976 条恢复保守可达，[撤回证明](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-config-flags-review/v1-withdrawal-review.json) SHA `b58e38a35f6aebd475c3b2d23109ad521687e46f6991e77bb1c92261706a45f6`拒绝 v1 的 455 条。

[精确消费器](tools/solve_vector_coverage/consume_config_flags_review.py)核全部独审依赖 SHA、原 v4 row 摘要、完整 source/config/phase/root/arm 身份及每个 possible edge，重算实际四 flag/21 gate 的 CFG，并将每个 root 的完整函数/PC 集合与独审报告比为相等。生成[主账本 v5](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v5/index.json)，SHA `a4e6f7844ca0b70edc61338003c4b32ebd19768893cc7772735b8804bfd26eea`；保留 v1–v4。默认 13825 项现为 **87 observed、4465 配置排除、2 归约排除、4877 已审结构/执行但源语义待核、74 已审 edge 但源谓词待核、4320 待见证/域证明**。九项[消费负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v5/consumption-controls.json)全部拒绝，SHA `21c2044281883538517c6d2e352a54be5f809a74c4f259b0ba6b47805ef022ce`。新增 case/终态为零，仍为 3244/9432；未映射、RHS、V4 `not_lowered` 未变。

```sh
python3 -B agents/float_support_review/tools/solve_vector_coverage/consume_config_flags_review.py \
  --stage "$P1_STAGE" \
  --review "$P1_STAGE/vector/independent-config-flags-review/certificate.json" \
  --review-sha256 10b9c99db26d5567a144ab0cd43209765d6bde48883b24abdbc506d8b47b4cc3 \
  --output "$NEW_VECTOR_LEDGER"
```

`P1_STAGE` 指本节 56cc 集成目录；`NEW_VECTOR_LEDGER` 必须为不存在的输出目录。此命令只消费已有目录，不运行模型或提取 sidecar。

#### flags 后续未闭组与输入边界

下表是下一步合同安排，以正式消费后的 v5 默认义务统计。剩余无见证/域证明候选为 4320，另有 4877 条已审结构/执行及 74 条已审 edge 等待源语义。各组职责重叠，数字不相加为源码分母。

| 顺序 | 共享原因与当前主要库存 | 下一步最小合同 |
| --- | --- | --- |
| 1 | typed 宽度/元素数：`assert_vector_num_elem_upto_128` 1011、`assert_sew` 375、`assert_lmul_pow` 212、`get_sew_pow` 153、`assert_vector_num_elem` 87 | 当前 getter 的全部有限正常返回及异常出口；每 root 的 SSA 实参、VLEN128、SEW/LMUL/num_elem 关系，不能把一个 caller 的维度用于其它 caller。 |
| 2 | `currentlyEnabled` 1808 条无见证，1068 条已有结构/执行但源语义待核 | 当前扩展枚举与实际 caller，逐配置 misa/FS/VS 域；短路 RHS 正常值、异常和 LHS 分别审定。 |
| 3 | 寄存器组和循环：`read_vreg_extra` 158、`write_vreg_extra` 11、`valid_reg_overlap` 48 条无见证 | 全 bv5 索引与实际 EMUL 关系、对齐/末寄存器界限、活动和尾部循环；先排除 caller 参数下不可能的分支，再核真实可达方向。 |
| 4 | 源谓词与无 lowering：4877 条结构/执行和 74 条 predicate 仍不等于源语义观察；121 未映射 site、228 V4 历史 arm 另列 | 复用现有完整 phase/Call/End 许可，补源表达式和实际 Bool/返回值的精确关系；对编译为纯表达式的 site 保留等价合同。 |
| 5 | 数值 helper 与 SEW8 转换的残余边界 | `recip7/rsqrt7` 合计 42 条无见证均涉及每个专化 caller 不匹配的格式或 idx/leading-zero 断言，先做 typed/bounds；VFW/VFN 的 mask/enum 残项先核 SEW8/enum 相关性及实际主体入口。 |

本轮尚未确认必须新增执行的输入。只有完成上表合同后，仍被证明可达、且在 3244 条已有输入的完整 phase 中确实缺方向或返回值见证的精确 root/site/arm，才进入补输入清单。已有结果中的有限数值样本、raw pending 数量或未映射源码位置均不能直接作为新运行任务。

#### 第一份当前 typed/num 合同候选

[typed/num 候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/typed-numeric-current-candidate-v1.json)，SHA `f047edba68c90bf814479da26163a6eec39f26271d3b3c61d75fed483dacb873`，由 [p1_typed_numeric_contracts.py](tools/solve_vector_coverage/p1_typed_numeric_contracts.py)（SHA `aeeb8885739c46095b9ea5981b23d18880116ba5f071d0342bb4573b27790f13`）重跑 source-v3 并读取当前 default 实际目录，绑定正式 v5。366 个 root×helper 合同提出 **1318 条排除候选**：`assert_vector_num_elem_upto_128` 804、`assert_vector_num_elem` 87、`assert_sew` 239、`assert_lmul_pow` 188。另 367 条保留：num helper 207、SEW 136、LMUL 24；未修改 v5，未增加 observed、静态排除或执行。

叶断言复用冻结 `independent_loop_review/review.py::assertion_domain` 算法，重新解释当前完整函数，正常返回输入分别为 num 的 `{1,2,4,8,16,32,64,128}`、SEW 的 `{8,16,32,64}`、LMUL_pow 的 `[-3,3]`；正常整数域之外的断言失败保留。getter 各枚举全部八个字段编码，保留四个非法 SEW 编码及保留 LMUL 编码的实际 Exit；`get_num_elem` 另有 54 组有限输入，包含 LMUL=-4/4、SEW=0/128 的失败。新增数值解释层复用既有 typed 值与原语求值，只在本十函数闭包内增加完整 Call/Exit 传播，断言失败后不会继续 caller。

当前 SSA 转发中，87 个 num root 分为 82 个 `num(LMUL,SEW)`、4 个 `num(0,SEW)`、1 个 `num(0,2×SEW)`；SEW/LMUL 断言分别保留 `SEW/2×SEW` 和 `LMUL/LMUL+1/0`。每个 root 独立列出 getter 正常返回的 28 个笛卡尔组合，不借多个 getter 之间的 vtype 同值关系或后置 guard；寄存器索引、VL、mask、rm 和数值 lane 未收窄。`num=0`、`LMUL+1=4`、`SEW×2=128` 的失败与失败传播、将 Exit 错改 End 等七项控制已核。

最后一项负控在 producer 中的捕获区还包含返回值检查。为排除把测试自身断言误记为引擎拒绝，另存[直接引擎负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/typed-numeric-current-direct-negative-control-v1.json)，SHA `86d7500fa7bf0ef2e8b606d0ea6a85489348df8e305ffc0d495be7be91acfe28`：仅捕获 `assertion_domain` 调用，将当前 num128 的 Exit pc115/119/123 改 End 后，由引擎直接报 `断言返回域非有限单点`。原正常域重新核为八个正整数；冻结 v1 和 producer 未修改。

候选提交时仍待独审联立：当前 sidecar 的初始化 VLEN=128、完整目录无 vlen 直接写或 Ref、native/特殊调用对新增保护 let 的保持、每个当前 root 的参数定义与转发，以及原语和 Exit 效果。以下正式独审和 v6 消费更新此状态。配置 flags 证书仅供定位相同运行时效果源码，未直接外推成 vlen 证明；未使用旧 `init_masked_source` 绑定 map 或 BF16 caller 前提。文件保留完整数值路径供复算，未扩充 pending 分母。

#### typed/num 正式独审与 v6 精确消费

[最终主证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-typed-numeric-current-review/certificate.json)，SHA `286b2ec085ebcdadfafa0c1850dc4febc70ceef88971074eff116c565eb46fdf`，与其必需的[形参/算术附证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-typed-numeric-current-review/supplement.json)，SHA `ada918844ed97846d2d48a078fe9033e88c96ff72990c7a50cfe9fb077f2a86d`，联立签署 default 的 **1318 项排除、367 项保留及 366 个 root×helper**。主审独立重跑完整 366×28 路径及源绑定，重新核 VLEN 初始化、R1/runner、全目录无 shadow/写/Ref/Addr 和 native/Reset/特殊效果；VLEN256 反向配置恢复对应失败。附证核 21 个完整 helper 的形参无写/Ref/Addr，以及 17 种原语全部有限输入输出的实际运行时语义与 i64 无溢出。独审共 **10 项单测、15 项负控**；`certificate.initial.json` 仅留历史，不准单独消费。

[typed/num 消费器](tools/solve_vector_coverage/consume_typed_numeric_review.py)绑定最终主证书、必需附证、冻结 producer/引擎和 v5 的 SHA，复算 21 个完整函数正文、三个叶断言的全整数正常域及 366×28 数值路径，逐行核 source/config/clause/phase/root/site/arm、原 row 摘要和全部 possible edge。生成[主账本 v6](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v6/index.json)，SHA `52f4d2cbf718fb0d1a4fb387f5bddb78c40bcc26a02652f385c50f658b02b4dc`；[default 账本](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v6/20851fdbd512.json) SHA `46fc5e52cb5b141bd0eed92d9d8419c365c60f98f1b623e6e431042732344cb8`。默认 13825 项现为 **87 observed、4465 配置排除、2 归约排除、1318 typed/num 排除、4877 已审结构/执行但源语义待核、74 已审 edge 但源谓词待核、3002 待见证/域证明**。

[消费负控](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v6/consumption-controls.json)，SHA `5402b2350377a6e547d8fbadc89e032d7a76c770fc6a4e314581b59821522c4b`，拒绝八种精确身份/边篡改及撤去两种必需附证前提。367 条保留项、所有未选中行和其余五配置保持原样；v1–v5 均保留。v6 明列六配置静态排除合计 **25379 = 24059 flags + 2 归约 + 1318 typed/num**；该总数字段修正 v5 沿用的归约专属 `current_static_exclusions=2` 口径，各配置逐行 counts 没有此歧义。新增动态 case/终态均为零，总数仍为 **3244/9432**；`source_branch_closed=false`，未映射、RHS、V4 `not_lowered` 不变。不跨配置或新 IR 继承。

```sh
python3 -B agents/float_support_review/tools/solve_vector_coverage/consume_typed_numeric_review.py \
  --stage "$P1_STAGE" \
  --review "$P1_STAGE/vector/independent-typed-numeric-current-review/certificate.json" \
  --output "$NEW_VECTOR_LEDGER"
```

`NEW_VECTOR_LEDGER` 必须不存在。上述命令只静态解释已有 typed sidecar。[逐行守恒检查](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v6/conservation-check.json)，SHA `643660eeebcb527f1a50d0875a59ac3ea1d97511c7561f2d661868aef5fc2a23`，确认仅 1318 项状态及审查引用变化，其它行和五配置记录完整相等。`num=0`、`SEW×2=128`、`LMUL+1=4` 等失败仍保留，尚未据此提出新增动态输入。

#### get_num_elem 的局部 VLEN 比较候选

[局部合同候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/get-num-local-bounds-candidate-v1.json)，SHA `a111f164e6d44e15ec28f48761274d5ba83e12f611e8eabad820be99dd4a1f39`，由 [p1_get_num_bounds.py](tools/solve_vector_coverage/p1_get_num_bounds.py)绑定 v6 与上述正式 typed 主证书/附证，并重新执行 source-v3。当前 `get_num_elem` 完整 50 指令中，同一 LMUL/SEW 形参分别经 pc3/7 的断言正常返回，支配 pc13 的 `gteq(vlen,SEW)` 和 pc46；同一 SEW 的 I64→整数转换无改写。已审全整数正常域把到达此处的 SEW 限于 `{8,16,32,64}`，与保持为 128 的 VLEN 联立，提出 **24 个精确 source/root 的 `fails` 排除候选**。该局部结论不收窄调用者的其它参数，也不声称 root 必到达或整个函数总终止。

七个 LMUL 正常值×四个 SEW 正常值的完整路径全部复算；SEW=0/128 和 LMUL=-4/4 仍在前置 callee 内 AssertionFailure，尚不到 pc46。另将静态解释环境改为 VLEN32，SEW64 恢复 pc46=false→47 的真实局部失败，说明结论依赖 VLEN 前提。八项结构/域/身份/边篡改负控均拒绝。24 条 `holds` 仍为结构/执行已审、源语义待核；候选已交独审，**未改 v6 的 3002 pending、未新增排除或动态输入**。

后续[局部 24 项独审](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-get-num-elem24-review/certificate.json)，SHA `24cb812e4b12199fe46357e0823cc5d4fd8ecf80e8c16cfae58e8da8a4ecb90f`，重新核完整函数、源桥、13825 项结构、28 正常路径和四个前置失败，并通过 **7 项单测、8 项篡改及 1 项实际 VLEN32 反向控制**。许可只列定 24 条 `fails`，必需联立 typed 主证书及算术附证；不使用 root 实参收窄，不签全域终止。

[消费器](tools/solve_vector_coverage/consume_get_num_bounds_review.py)逐完整 source/config/root/arm 和全部 edge 消费该许可，再次核全整数正常域、当前支配关系、28 路径、前置失败和反向路径。生成[主账本 v7](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v7/index.json)，SHA `80f6a78ea52270d763ef502595642d8e16d32afb512fca3662b6f1b29c14069b`；default SHA `679c3402fa8fd5e3d0e9ae4c5f751d84f0198b992a9ebc2b9e4233912b5f6b68`。**pending 3002→2978，observed 87、结构/执行待源语义 4877、谓词待核 74 均不变**；其余五配置记录原样沿用，六配置静态排除合计 25403。十项[消费负控与守恒检查](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v7/consumption-controls.json)，SHA `d2afe3f2c6796830c4535ce448e21c954a102be412cbf85a34d76e4f11e36d94`，确认仅 24 指定行变化、24 holds 原样保留。新增 case/终态为零，`source_branch_closed=false`，不跨 IR 或配置继承。

#### 估计函数的格式/范围候选

[估计函数候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/estimate-width-bounds-candidate-v1.json)，SHA `05012ce50b7741c87e526c5fa77a727aeeb8a4f719e90b417ffb6df084a2c27f`，由 [p1_estimate_bounds.py](tools/solve_vector_coverage/p1_estimate_bounds.py)读取当前 v6、typed 目录和完整 IR，重跑 source-v3，重建六个实际 wrapper root 的固定输入位宽及全部两个 sub 调用。候选包含 **24 项固定格式、18 项 CLZ/无符号索引界限、3 项 `sub=false` 正常返回 Bool=false**，合计 45 个精确 source/root arm。实际分类值、lane 内容和 sub=true/false 两上下文均未裁剪。

该候选仅复用旧审查的区间传播算法（`review_contracts.py` SHA `4f232e12ad947115a11c5fa2632361f46fe1e21f81360b16a7ba589837133c9c`），重新解释当前完整函数；未读旧证书或移植旧 PC map。当前 31 函数未剪枝调用闭包逐正文保存，并核形参无写与无 Ref/Addr。六项反向控制分别恢复负 CLZ、7-bit 上界 128、两个格式宽度变化和错误 Bool 返回的相应方向。首次运行在负控定位阶段因返回结构先写局部量、随后复制到返回值而停止，未生成产物；按实际 Struct 字段定位后完整候选和六项控制通过。**候选仍待独审**当前原语语义、未知 Call 的效果、完整 typed 值宽、源分支/LHS 极性和 wrapper 返回字段合同；正常路径采用保守区间解释，不把未知 Call 当成已验证执行。未改 v6，新增 case/终态仍为零。

后续[45 项独审证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-estimate-width45-review/certificate.json)，SHA `e8dfa0ef976e420ff79d149096f0e65918823003ce17bbe56f6035afd75f92f3`，签署全部 45 项；**6 项基础测试、26 项真负控**通过。独审进一步补强候选中的 root 位宽依据：当前真实 `read_vreg` extra 链调用 `isla_read_vreg`，正常成员宽度为实际 SEW；同一保存的 SEW 局部经 identity/eq guard 在整个 CFG 上限制各 wrapper root 的实际值。该论证不借静态 Decl 补值，也不假定多次 getter 的 vtype 相等。CLZ 的 10/23/52 位来源、7-bit 索引、31 函数局部效果及两 sub 的全部 15 上下文另独立重算。

[width 消费器](tools/solve_vector_coverage/consume_estimate_width_review.py)先核 v6→v7 仅为已审 get_num24 差异且本 45 行完整不变，再重跑独审的实际 root 来源、31 函数局部不变量和 15 个完整区间上下文。生成[主账本 v8](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v8/index.json)，SHA `c082721cb78e27425ce3063fd7e258047cdadc1feb679a172920ae2036595aa7`；default SHA `d8f2d4f7c5b9d4d84db20ff9f132a1f7f4b7cc505b1334d145f3f2940f88f0d6`。**pending 2978→2933、observed 87、结构/执行待源语义 4877、谓词待核 74**；五配置和全部非选中行不变，六配置静态排除合计 25448。[九项消费负控及桥接守恒](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v8/consumption-controls.json) SHA `96da3656c561e84cb2b67ff7a1c97b6bceb6b64b6ae1ec3673b877c3e23fa7b7`全部通过。新增动态为零，`source_branch_closed=false`。

#### typed 断言的 799 条源语义联立候选

[源语义候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/typed-source-semantics-candidate-v1.json)，SHA `87f2c1390a107a2c9529eec7149ec42d08fe4d29bd1ce10e00be13d9c5ac939a`，由 [p1_typed_source_semantics.py](tools/solve_vector_coverage/p1_typed_source_semantics.py)（SHA `01f2df2e4dd5d4d05a0bd8de00c68292f5e94b63129d9747ee4320c89ecc9d61`）绑定正式 v7，选择 **799 条已有结构/执行许可**：num128 485、SEW 227、num wrapper 87。它们归为五个源码 site、十二个 source-arm 合同；不扩到另外 24 个 get_num `holds` 或其它函数。

每个合同从实际形参/全局符号出发，核唯一且支配的定义、`eq_int/lteq` 操作数、精确转换、Bool `Not` 及 Jump 极性，归一结果与当前源码的数字模式或 `<=` 表达式相等。匹配臂另沿真实 Goto 链核到对应源码 Unit body；首次运行因未跳过这一 Goto 停止且未输出，修正后的合同保存完整入口链。窄化只允许全整数断言分区已证安全的区间，不能凭声明宽度略去。

动态部分逐条核 v3 原签署 claim 的行号/SHA、精确 source/config/clause/phase/root/arm 和选定 witness，重新校验 **89 个完整 phase 的 Call/End 正常返回链**；证书 500 个来源和所用完整 trace 重算 SHA，source-v3 重执行。八项负控拒绝错误比较原语/操作数、源 token、taken、root、phase 路径摘要、缺正常返回链及终态 ordinal。候选已交独审，**正式账本仍为 observed 87、结构/执行待源语义 4877、pending 2978**；没有新增动态 case/终态，也未把前置异常或全域终止纳入许可。

后续[799 项独审证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-typed-source-semantics799-review/certificate.json)，SHA `01486cdff259d57740ba3be1eaf71a64c211ad7fa6648eef904acb813ca5d3cf`，签署上述精确源语义升级。独审对真实操作数、完整唯一 SSA、比较/Not/Jump 和字面量 body 独立核验，并重新流式校验三个原始 trace 的 **398 个既有输入、1194 终态**；89 个完整选中 phase 含 **1684051 指令、114575 Jump、56455 Call/56544 End**，新重建的动态证明与原 claim 全等。**7 项单测、11 项负控**通过；这些重读统计不新增 case 或终态。

[源语义消费器](tools/solve_vector_coverage/consume_typed_source_semantics_review.py)核 v7→v8 仅 45 条已审静态排除且本 799 行完整不变，重算十二个源谓词合同、叶断言全整数域、原 claim/见证和完整正常 Call/End 身份后，生成[主账本 v9](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v9/index.json)，SHA `5eafd4f9262a029765a8b6bed92b3db141406446210b4412e6f11bd15342b07a`；default SHA `bfdccc4388523e3a7b4c97da91c9625694c96ac9d3a0db6089766d9ba13e34ce`。原 87 个 observed 行逐字典不变，新增独立状态 `observed_by_independently_reviewed_existing_trace_source_semantics` 记录 799 条旧 trace 语义许可，**source observed 总数 886；结构/执行待源语义 4877→4078，pending 2933、谓词待核 74 不变**。

九项[消费负控与守恒](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v9/consumption-controls.json)，SHA `0a3b98796439e607e5cbaf3dcb4b9a97f864ed8984ca8708dbf5190386e1f65d`，确认仅上述 799 行升级，五配置、原 87 行和全部其它行不变。六配置静态排除仍为 25448，新增动态 case/终态仍为零，累计严格审计仍为 3244/9432；`source_branch_closed=false`。旧行内 v3 的 `source_semantics_not_upgraded` 是原证书权限记录，现行许可位于新增的 `independent_source_semantic_review`，未改写历史独审结论。

#### currentlyEnabled 的枚举入口域候选

[枚举域候选 v2](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/currently-enabled-enum-domain-candidate-v2.json)，SHA `9448c488fc71ad277e69d5ad2a030edacdcdd49b74486e089365bf187bfa1c53`，由 [p1_enabled_enum_domains_v2.py](tools/solve_vector_coverage/p1_enabled_enum_domains_v2.py)（SHA `6ec9e685cc886e6abdbadc5c3db2e01c189eea95434cff94c2662eb851eb562d`）绑定正式 v9、当前 typed sidecar 和源码桥接。真实 `extension` 有 109 个构造子；110 个实际 root 分为 5 个入口域，递归检查全部可达 Call 得到 28 个上下文、15 个完整函数。仅固定同一不可写形参与实际枚举构造子的 `Eq/Neq` 分派，其余 Bool、状态和 Call 返回均保留未知后继；不依赖 misa、FS/VS 或 `hartSupports` 返回值。

当前 2876 条 `currentlyEnabled` 义务中，**1056 条 pending 的整个 LHS site 均在对应完整枚举调用域之外**，涉及八个短路 site；1820 条保留，其中 1068 条已有结构/执行见证、752 条 pending。全 runtime 核构造子无写/无遮蔽，域内完整函数核形参无写、无 Ref/Addr 及局部写入。八项控制通过：撤去枚举分派恢复全部 1056 个 site，改变实际入口构造子恢复各源 site，形参写/引用逃逸及错 root/token/边/后继均拒绝。候选仍须独审精确枚举语义、完整调用上下文保守性和源义务绑定，**不改变 v9 的 pending 2933 或任何正式排除**。

历史 [v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/currently-enabled-enum-domain-candidate-v1.json)（SHA `5ccbcaa8a816fca6608e7117f5ecb11dc03b83b15154b013bb860ad611629f88`）误把 worklist 最后弹出的函数名写入五个诊断 `entry` 字段，未交独审。v2 保存真实入口，并逐项验证其它域字段、全部 claims 和保留行不变；v1 禁止单独消费。v2 首次验证因 JSON list 与内存 tuple 直接比较而提前拒绝、未生成输出，改为同一规范化摘要后通过。所有历史产物保留，新增动态 case/终态为零，`source_branch_closed=false`；证据仅限 `56cc/default`。

后续[枚举域独审证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-currently-enabled-enum1056-review/certificate.json)，SHA `8576608125921c6e45e81326c7f6cf1550626a3fcecb38ca0695dca346f74039`，签署全部 1056 项：decode/encode 各 528、lhs_true/lhs_false 各 528，覆盖八个 site。独审独立按函数/枚举/PC 队列同时饱和 CFG 和递归 Call，重核 109 构造子在完整 IR、2058 函数及运行时的身份、初始化绑定与无写/遮蔽/引用逃逸；9 项 TDD、16 项负控通过。另有[运行时身份附记](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-currently-enabled-enum1056-review/runtime-identity-note.json)，SHA `d9ac881009918e88387ae5faa1c0612d7d081c5a7ff15881e6c5d4c91aafdb68`，核实际 EnumId/EnumMember 相等语义和仅 register/let 的初始化作用域。

[消费器](tools/solve_vector_coverage/consume_enabled_enum_review.py)重算五域/28 frame/15 完整函数，逐源/root/phase/arm/全部映射 edge 消费独审许可及附记，生成[主账本 v10](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v10/index.json)，SHA `9038a2326c920ccaf4b5707367e1e33b312d744dca1a3a5c41291038027813dd`；default SHA `27e4d19daf7c822e64119a87e20307f4298631dc3c5f4ec02a628fa3e1423886`。**pending 2933→1877；source observed 886、结构/执行待源语义 4078、谓词待核 74 不变**。仅 1056 个已审行改变，1820 个其余 currentlyEnabled 行、其它全部行和五配置记录完整保持；六配置静态排除合计 26504。十项[消费负控与守恒](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v10/consumption-controls.json) SHA `d4bdd5515dd01cbbd324f9bd4e45ef96074c04904201a393606b4f66d9eaa3af`通过。新增动态 case/终态为零，累计仍为 3244/9432，`source_branch_closed=false`。

#### extra 读写的 969 条源谓词候选

[读写源语义候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/vreg-source-semantics-candidate-v1.json)，SHA `3789ec63a7109cdc33872875649a25dbcc8bab1ce90d1f890325e5c86711efc9`，由 [p1_vreg_source_semantics.py](tools/solve_vector_coverage/p1_vreg_source_semantics.py)绑定正式 v9 和既有动态独审。目标为 `read_vreg_extra` 的 742 条、`write_vreg_extra` 的 227 条已有结构/执行行，合计 **969 条、17 个源码 site、32 个源臂**。本候选没有选择 pending 行或新增静态排除。

源码端核精确 `LMUL_pow`、`max`、幂、寄存器端点/对齐及七个大小阈值表达式；typed 端核三份完整函数、五位实际寄存器参数、身份 accessor、同参数 `assert_lmul_pow` 的完整正常域和所有 Jump。reader 的 7×32 个输入及 writer 的七个 LMUL 值逐完整局部路径解释，每个经过的 Jump 均与独立源公式相等；全部相关整数运算和窄化检查 I64 安全，取余另核非负分子与正除数。

未知 Call 一律保留 caller 续体、返回值未知，可能的 callee 异常没有被排除；证明只约束已经执行到的本地 Jump，不宣称 root 必达或总终止。纯 LMUL leaf 的正常返回前提逐条保留，其它参数未知；源参数和局部值无写穿透/Ref/Addr，故不借 VPR、vtype 或整 phase 纯读。动态端重新核 **102 个既有完整 phase** 的许可、Call/End 链、终态和原始 trace SHA，尚待独审重读原 trace；12 项结构/源极性/未知值/动态身份负控通过。正式 v9 的 source observed 886、结构待源语义 4078、pending 2933 不变，新增动态 case/终态为零，`source_branch_closed=false`。

后续[969 项独审 v2 主证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-vreg-source-semantics969-review/certificate.json)，SHA `5d9b5bfbe77f4434627f30e325b5f6884c11d5123e328d88967beebb8d1158c5`，签署全部 969 条；22 项测试、34 项独立负控通过。独审实际重读四份原始 trace、102 个完整 phase，涉及 162 个既有输入与 486 个全部终态；逐行额外核同一次目标 invocation 的 LMUL 完整 Call/End 先于目标 Jump。reader 224、writer 七个局部参数组合、LMUL 全整数七值和寄存器 32 值 identity 均独立解释。

该许可必须联立 [native frame 附证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-vreg-source-semantics969-review/native-frame-supplement.json)，SHA `5141fcd043d19b1c3d3679c0814d22ae759c03bd06288a44f39013bff1211667`，以及 typed 主证与算术附证。初版主证只核 push/pop 片段，原文保留为 `certificate.pre-native-supplement.json`，禁止单独消费。补证扫描 45 份冻结 Rust 源码：Variadic 可取得可变 frame，但 read/pack wrapper 弃用该参数；`stack_vars` 的全部引用仅保存、恢复、克隆或只读，callee 的 `vars_mut` 只访问当前 frame。证明只提供已保存 caller 局部值隔离，不推导全 phase 纯读、VPR/vtype 不变或未知 callee 正常终止。

[969 消费器](tools/solve_vector_coverage/consume_vreg_source_semantics_review.py)，SHA `daf36ec5d82b4f8b0bdaef0af9c8aed205e698850f2343269a1e19f11ad2a718`，重核全部 45 份 Rust、两套完整局部合同、精确原行和实际 LMUL 前提；核 v9→v11 仅已审 enum1056 与 getter197 变化，均与本批不相交，生成[主账本 v12](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v12/index.json)，SHA `4d3e8559147b08fde413ef19969764b4d6d393bcb5bc9d5b2e9309a1339ba5f1`；default SHA `935dec5040246f79bc66aee7521d2489570eef01d61d024979ac80b92b515f77`。**source observed 1083→2052（87 原观察 + 1965 既有见证源语义许可）；结构/执行待语义 3881→2912；pending1877、谓词待核74 保持**。16 项[消费负控与守恒](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v12/consumption-controls.json)，SHA `ecb8263bd61703aa7e43d62ef2afa493e3dca8cbec35467778b1ea2b5fc51d7f`，覆盖撤去/篡改 native 附证、额外 saved-frame 写入、错误调用实例及晚于 Jump 返回。原 1083 观察、其余全部行与五配置记录保持，六配置静态合计 26504；新增模型执行、case、终态和静态排除均为零，动态累计仍 3244/9432，`source_branch_closed=false`。

#### getter 与 get_num 的 197 条断言见证候选

[局部断言源语义候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/getter-source-semantics-candidate-v1.json)，SHA `1b4d04dc0a20c7bfb20c4af7b134be828aeed5f180aa07796db65ec03d7008a6`，由 [p1_getter_source_semantics.py](tools/solve_vector_coverage/p1_getter_source_semantics.py)绑定 v9，选择 `get_sew_pow` 153、`get_lmul_pow` 20 和 `get_num_elem` 24 条既有 `holds` 见证。三个源码 site/源臂联立 **92 个既有完整 phase** 的原动态许可，未新增执行或排除。

两 getter 从当前源码位域、完整 accessor 实际切片、一次 `vtype` 值读取及 signed/unsigned 解释重建谓词；每个字段的全部八种值均解释，SEW 域外 4–7 及 LMUL 编码 4 的 AssertionFailure 仍明确保留。其余 `vtype` 位不进入切片，不假定两次 getter 读取同值。`get_num_elem` 则重算已审局部前缀和 28 个正常参数组合，将同一 SEW、VLEN128 与实际 `gteq`/Jump/失败后继对应；VLEN 保持证明仍严格依赖现有 typed 主证书和附证。12 项源极性、字段切片、signed/unsigned、源 key 与动态身份负控通过。候选尚待独审实际重读 trace 和源语义，**正式 v9 各计数不变**，`source_branch_closed=false`。

后续[197 项独审主证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-getter-source-semantics197-review/certificate.json)，SHA `0484887bbc24b0883306442081ff02539bf97ce42eb28eeb1f76567cbea5d377`，签署三个 `holds` 源臂；7 项 TDD、15 项独立负控通过。独审实际重读三个组的 316 个既有输入、908 个全部终态 ID，92 个选中完整 phase 共 1527550 指令、315869 Jump、51026 Call/51118 End；完整字段八编码、28 个 getnum 正常组合及四种前置失败均重算。getter 的 173 个 pending fails 和 24 个已审 getnum fails 排除原样保留。

[消费器](tools/solve_vector_coverage/consume_getter_source_semantics_review.py)逐完整原行、源谓词、实际见证和已审 Call/End 联立，重跑独审局部合同并核 v9→v10 仅已审枚举域 1056 行变化、与本 197 行不相交，生成[主账本 v11](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v11/index.json)，SHA `feca2f10e6c9b7a782d6e799b3cdb4b072f6d99c3fdeb4ec0fb75401ddb05bd1`；default SHA `b5022147e0e2a5db44ade74275b012ac8c2376f1a9ca7fa5c9668de9cefb7f20`。**source observed 886→1083（87 原观察 + 996 既有见证源语义许可）；结构/执行待语义 4078→3881；pending 1877、谓词待核 74 不变**。九项[消费负控与守恒](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v11/consumption-controls.json)，SHA `4d39329cd887bdc56a074ad95a8485c528cd940885063c1db1cc71ef6e05aea9`，确认其余行、197 fails 和五配置记录保持。随后独审另交[v9→v10 桥](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-getter-source-semantics197-review/v9-v10-bridge.json)，SHA `f197748bb4565c8230928c569b184a7493d0f1a4bee6935f5d7a49a57a0d2b9b`，独立核相同差异和 header/index 统计守恒；四项桥接 TDD 通过。新增 case/终态/静态排除均为零，六配置静态总数仍 26504，`source_branch_closed=false`。

#### currentlyEnabled 直接 Call 的 897 条 LHS 见证候选

[直接 Call 源语义候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/enabled-call-source-semantics-candidate-v1.json)，SHA `afcf7abb82bb7ccf7f2e9d8e6606220354b9a85f8ae1487770d481a9db144c23`，由 [p1_enabled_call_source_semantics.py](tools/solve_vector_coverage/p1_enabled_call_source_semantics.py)绑定正式 v10 和当前已审枚举身份。选择 897 条现有 `currentlyEnabled` 结构/执行行、13 个短路 site；其余 171 条状态读取或复合 LHS 保留待核，不推断返回值域。

源码端按 Sail 短路结合规则拆分冻结字节，要求 LHS 恰为 `hartSupports(Ext_...)` 或 `currentlyEnabled(Ext_...)`；typed 端核实际 callee、枚举实参、唯一且支配的返回值定义、Bool Jump 极性及短路 false 赋值。SourceLoc 只辅助核字节范围，源码 token 与实际操作数另行逐项比对；RHS 值与异常不在许可候选中。

本候选进一步从原始 trace **重建 118 个完整 phase**，逐项比对原已审路径/Call/End 摘要，并为每条见证保存 LHS callee 的实际正常 End、返回续体、所在父 frame 区间与后续 Jump 步号。callee 的结果值不受限制；只有所选正常动态路径建立局部源码 Call 语义，不把可能异常的其它路径删除。九项源 callee/实参/arm/key 和动态身份负控通过。候选仍待独审，**v10 的 source observed 886、结构待语义 4078、pending 1877 不变**；新增模型执行、case 和终态均为零，`source_branch_closed=false`。

后续[状态/复合 LHS 候选 v1](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/enabled-state-source-semantics-candidate-v1.json)，SHA `5b5d545d4508a33271aa6e8905e88c708d3d8673f3cb940435827a8d9fd9333d`，由 [p1_enabled_state_source_semantics.py](tools/solve_vector_coverage/p1_enabled_state_source_semantics.py)补充上述保留的 171 条、两个 site。165 条 VS 比较核冻结 `Mstatus.VS[10:9]` 定义、完整 accessor、一次真实 `mstatus` 读取、两位零常量及 `neq_bits` 操作数；四种 VS 值全覆盖，其它状态位未知。另六条 OR 的复合 LHS 核两个真实 callee/枚举实参、双定义汇合及后继，枚举两种返回 Bool 和异常标志的全部八种组合；异常真且需要第二个 Call 的路径保留为 `Arbitrary`，未转成正常 Bool。

动态端重新核 **96 个既有完整 phase**，每条 LHS callee 记录正常 End 和续体；复合表达式的第二次 Call 是否执行，由同一父 frame 中实际前置短路 Jump 决定，未执行时明确保存跳过证明。九项负控通过。897 与 171 候选在行号上不相交，共覆盖当前 1068 条 `currentlyEnabled` 结构/执行见证；两者均待独审，未改变正式 v10、未增加动态 case/终态或排除。

后续[897 直接 Call 主证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-enabled-source-semantics1068-review/direct-certificate.json)，SHA `7174354d39b4091bec98c70c0b0a629a975376e904173ac2633dd0d7a18f5a01`，以及[171 状态/复合 LHS 主证](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-enabled-source-semantics1068-review/state-certificate.json)，SHA `edb51ede505b9b921ea0e2b115b424451c6ec39befcc0c72dbe45cb1ca552c38`，分别签署 13 site/17 arm 和 2 site/4 arm。7 项 TDD、两 scope 各 12/19 项独立负控通过；不导入 producer 语义函数，重新核词法优先级、SSA/实际参数、四个 VS 值和八个复合 Bool/异常组合。

独审[共享原始 phase 报告](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-enabled-source-semantics1068-review/shared-raw-phase-report.json)，SHA `9007c31a3ae7430f8c35491d37c2a170ecab9f120ba679ece3ea4a010476c27a`，重读并集 **119 个完整 phase、六份 trace**，370 个既有输入/962 个全部终态 ID 双射，3223753 条指令、110572 Call/110691 End。118 与 96 的 scope phase 数有重叠，不能相加。每条 LHS 额外保留独立重建的精确 immediate parent Call 索引；复合第二 Call 的前置 guard 与后续 `have_exception=false` 实际 Jump 同样必须属于这个父 frame，跳过第二 Call 则保留实际短路证明。

[1068 消费器](tools/solve_vector_coverage/consume_enabled_source_semantics_review.py)重新执行 15 site 的独立局部合同，逐行检查原字典、行 SHA、ordinal、精确 key、已审正常返回及父 frame/guard 附证，核 v10→v12 只有 getter197 与 vreg969 的已审变更且与本批不相交，生成[主账本 v13](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v13/index.json)，SHA `2a4f85e34911a5444fc1f2bb3c232a8ca82e3dfcc792b345320e381d9a860068`；default SHA `0d173b89c6d309b84d2f70b391e542ca075829675cbffb42d6704b8c862c4226`。**source observed 2052→3120（87 原观察 + 3033 既有见证源语义许可）；结构/执行待语义 2912→1844；pending1877、谓词待核74 保持**。23 项[消费负控与守恒](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v13/consumption-controls.json)，SHA `cfac9f897627d817167cb044506cd5bb02af54da62875cc528f43df39ebbac9b`，含错父 frame、撤去前 guard、异常 guard 改 true 与跨 frame guard。其余全部行、先前 2052 观察和五配置记录保持；六配置静态总数 26504，动态累计 3244/9432，本轮新增执行、case、终态、RHS 或排除均为零，`source_branch_closed=false`。

#### 当前 mapping18 完整表与调用前提候选

[当前候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/mapping18-current-candidate-v1-attempt2/candidate.json)，SHA `d368fda740057b3a77120e6a8c3498ecd02bdddf67f581dc5ffbc1c3c80a5f6d`，由 [p1_enum_mapping_contracts.py](tools/solve_vector_coverage/p1_enum_mapping_contracts.py)（SHA `3a8e33d9eb7f28340eccfeee6a4db6422e04596a172733852d65dcd86eb798a5`）绑定 v13/default，实际重跑 source-v3；复用表解释算法，重新生成全部当前 source/typed 证据。18 个 mapping、97 个枚举成员、90 个完整函数和 2339 个有限域输入均核源表结果；完整 runtime 的 377980 指令、所有 IR 形参及新增求解 wrapper 形参均检查构造子无写、遮蔽或引用逃逸。

反向 infallible 的 36 个真实 caller 分别核同一实参定义支配、期间无重写/引用逃逸、完整 caller 无后向边，并以其余 Bool/Call 返回全部未知重算：对应 matcher 为 false 或被跳过均不可达 value Call；撤去 matcher 约束则恢复可达。所有未知 Call 保留 caller 续体，不根据可能异常删路径。另联立已审 native 保存帧隔离，并核区间直接 `eq_bits/eq_bit` 原语实际为无 frame 参数的 Binary。五项篡改控制通过；非法 bits 仍为 matcher=false 或普通 backwards 的 MatchFailure，infallible 不扩展到未匹配域。

该候选绑定主账本外 **291 个原始补充项**（97 个源成员各含 decode matcher/value 与 encode root），没有提供新的真实 source-arm 动态见证；所有 291 项保持 pending，未加入主 13825 分母、未增加观察或静态排除。首轮因 runtime 额外 `zisarch_solve_wrapper` 不在文本 IR 函数参数表中而 `KeyError` 停止，未生成正式 candidate；首目录中间产物保留。第二轮按冻结 `src/isarch/exec.rs` 精确核唯一 `zisarch_requested` 参数后通过。当前候选已交独审，正式 v13 各计数不变，`source_branch_closed=false`。

后续[291 条既有 trace 候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/mapping291-existing-trace-candidate-v1.json)，SHA `5f6866b9f7dd28f7c82c22d7183c5e0cde1c6e8fe64b4c8142c8712177d74888`，由 [p1_mapping_trace_witnesses.py](tools/solve_vector_coverage/p1_mapping_trace_witnesses.py)（SHA `c1ac3f541c0a3219b3d6333e2666fa21ce97d2e700eb16e187f8989e44670569`）独立补充动态部分，未改上面的表/guard 候选。原 enum-sew 274 输入/822 全部终态 ID 双射重核；选中 97 个已有输入的 **194 个完整 decode/encode phase**，从原始 trace 重新解释 2766908 指令、492983 Jump、97302 Call/97496 End。

逐 291 行核实际 root 的同一次正常 Call/End 和完整 callee 局部路径；该路径在完整许可输入域中恰对应一个输入，再由当前源表推出源成员。输入名只用于选择已保存的 case，不构成成员证明。97 个反向 infallible value 见证另核同一精确父 frame 内此前实际 matcher 正常 End、完整局部路径返回 true，以及相同 bits；仍必需联立静态同实参 guard 和 native caller 局部隔离。五项局部路径/方向/root/唯一性/返回时序负控通过。首启动因 `audit_suite` 同名模块导入顺序冲突而停止，未重读 trace 或输出；修正导入顺序后通过。表与动态两包分别待独审，291 条仍未消费到补充账本，主 v13 与动态累计保持原数。

#### 六个直接 Bool 开关 if 的 173 条源语义候选

[173 条候选](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/direct-flag-source-semantics-candidate-v1.json)，SHA `127430e3083066842054f4d3908202c5db0b3420406cd4e82fe5fe1dad33ce80`，由 [p1_direct_flag_source_semantics.py](tools/solve_vector_coverage/p1_direct_flag_source_semantics.py)（SHA `b761fefd44863c5f7b8b7848fee30b01bb0f312ca9833ccfdf995b3bc4854515`）绑定 v13 与 40 个已审完整 phase。范围为 get_V_bits72、read_vreg45、set_V_bits21、write_vreg17、init_masked_result16、init_masked_result_cmp2，共六个源码 if 的真实 true 臂。

每个源码 `if __isla_* then` 精确绑定 Bool 寄存器声明、同名 typed Id 与实际 Jump，两种 Bool 值均重算极性；不使用初值、配置固定值、跨读取稳定或整 phase 纯读。四个 wrapper 的 Jump 前缀为空；两个 init 前缀是完整 Decl＋`assert_lmul_pow` Call，并与源前置 assert 对应，但该 Call 不用于收窄 flag 值或证明入口可达。首内部尝试误要求前缀仅 Decl，在断言处拒绝且未输出；修正上述局部前提后通过八项源 token/flag Id/极性/实际 root/完整 phase 负控。候选已交独审，正式 v13 各计数不变，新增执行、case、终态、RHS 和排除均为零。

架构另请求的新 e6a FVFTYPE 物化使用[既有输入交接表](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/fvftype-existing-input-handoff-v1.json)，SHA `0dd6ac5dbf9d8a88fc98bffb61abf6538b9c802608abc0de834eecf045a201e7`。它从 14 个权威输入文件按原序号选出 26 条关键合法/非法记录，完整保留原 ID、word、initial 和 expected 及其它字段；只提供准备输入，新版本的物化、结果与证据由 replay 另行记录，不迁移旧 source-arm 观察。

### 348147 来源绑定与独立复验

新冻结 basename 为 `isla-unified-p1-candidate-20260927.fa8Sg2`，IR SHA `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061`，candidate manifest SHA `1890f0a13d9dc877185c46bcf398ea0b2f12fbe3b0ee6802adb5de0a845f1ed9`，generation SHA `69798fd276da2f5bcd5792261146c4c9dab899b68fb8725c6531927ddec7eae7`。generation 的真实来源 manifest 仍为 `749c3c5bba2995ecc048e22fd9baf375e6daec9b677c562b96d3c6d07ec7c911`，没有改写为 candidate 哈希；实际 runtime manifest 沿用下文旧冻结 `28fb65ee…`。

[新来源正测](../../isla/target/float-support-review/final-coverage/integration/p1-348147/vector/source-binding-positive.json) SHA `28d283be7e7dc0fffd71209423312d95b28afedbd36053306ba1c03677a7e521`使用共享 `verify_source_snapshot` 的显式 source bridge，重跑真实 verifier 并比对完整报告，确认 166 个 model、125 个 sail_lib、510 个 runtime 文件及九个选定源码文件。bridge SHA `1a043c3a42314781dcb93d645e7e2efb57c19b464b2b7ddcd680a8fb1ef25423`，verifier SHA `123c589eaea48ca6a3d2af0a0ed4bbf7053bc330bebc479db53d2cb98c38827f`，结果 `source_binding_complete=true`、`reexecuted=true`。

[p1_catalog.py](tools/solve_vector_coverage/p1_catalog.py)独立生成[新源码目录](../../isla/target/float-support-review/final-coverage/integration/p1-348147/vector/catalog/source-branch-catalog.json)，SHA `0f965ff3c7dc1f90112c2292d1091671a766a9708c865b3fc7cfb2550acba5dd`：22 clause、九文件、886 词法 site/2349 arm，其中活动 675/1798、out-of-build 211/551，73 个数据策略。旧 906 项迁移分为 850 个保留源码候选、36 个 non-SYMBOLIC 保留并待等价、20 个手工迁移义务；这不是闭合分母。四个 shared decoder matches 中只有 `encdec_nreg_forwards_matches` 与 `vext_vs1_backwards_matches` 仍有真实 Call，另外两个 constant-true 定义及 Call 已消失。目录内部的来源 pending 字段保留生成时事实，后续真实绑定由独立正测文件承载。

[p1_strict_audits.py](tools/solve_vector_coverage/p1_strict_audits.py)按[调度清单](../../isla/target/float-support-review/final-coverage/integration/p1-348147/vector/strict-audit-plan.json)消费新运行的 15 个 task，[完整审计索引](../../isla/target/float-support-review/final-coverage/integration/p1-348147/vector/strict-audit-index.json) SHA `8916d9c55aedcb514215049fd4773a227da362400fc2ab0837cc1d994fa516f2`为 **PASS：3228 case、9396 唯一终态**。各配置使用新提取的 sidecar，完整目录为 **25711 个 runtime Jump**；实际 argv、完整 R1、输入/结果/初始化/trace/trace-map、源码桥接及唯一终态均由 [audit_suite.py](tools/solve_vector_coverage/audit_suite.py)严格验证。每个 task 自己重跑来源 verifier，不只信任预先保存的正测标签。全部 summary 哈希和每组 `all_runtime_jumps_equal/actual_R1_gate_verified` 又与索引核对；九项入口接线与篡改负控复验通过。此处不继承旧 source-arm 极性、caller 域或 lowering 证书，整体仍为 `source_branch_closed=false`。

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/p1_strict_audits.py \
  --stage "$P1_STAGE" --snapshot "$P1_SNAPSHOT" \
  --source-bridge "$P1_SNAPSHOT/source-repackage-proof-v2.json" --jobs 3
```

`P1_STAGE` 为 `isla/target/float-support-review/final-coverage/integration/p1-348147`，`P1_SNAPSHOT` 指向上述新冻结。脚本拒绝覆盖既有严格审计目录；重现需先准备独立的新输出树，不能覆盖已记录证据。首次调度在写输出前因 runtime index 的实际状态名 `PASS_ACTUAL_RUNTIME_CATALOG` 与准备脚本的 `PASS` 预期不符而中止；修订为精确状态并逐条检查 completed task、sidecar Jump 数和结果 SHA 后，上述完整消费通过。该准备错误没有改写模型运行结果。

### 旧 1dcc 已验收版本

**旧冻结上的 3105 条向量结果及 9045 个唯一终态已完成实际 R1 与完整 trace 审计。** 新增 recip7 舍入前沿 **15/15、45 终态**、User/Supervisor 入口 **58/58、158 终态**、D-off 合法 caller **22/22、66 终态**及 overlap 高位源 **5+1/5+1、18 终态**分别完成实际 R1 与完整 trace 审计。再加 estimate 分类前沿 **21/21、63 终态**，以及 narrowing FS-off 译码拒绝 **1/1、1 终态**，旧版本严格合计 **3228 case、9396 唯一终态**；原 3105 计数及显式 Machine 标签保留。

最终冻结为 `isla-float-solve-fix-final-20260926.GThshy`：IR SHA `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`，共同 source/runtime manifest SHA `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`，generation SHA `fd8476de2c815cd3c72b76ad2b3f9b74272ae13b537ca07409772e595471b74b`。默认配置 SHA `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`；三个 runner 的 SHA 分别为成功 `303ddcc124d945a9b28110edf1b80bfa4f4ed32969c5a941d4a7a802458cfe92`、执行非法 `156638df374682eae3c92e7364995be06fe52a14492b868ef92c9a5e3635bd1f`、译码拒绝 `71be726500a3847248b8ccf919329197d335f1d9bff188839de0a25f0be4fffb`。

### 最终回放、来源与实际入口

| 配置包 | 结果数 | 唯一终态数 | 已观察 scoped Jump 方向 |
| --- | ---: | ---: | ---: |
| default-FD | 2509 | 7319 | 1832 |
| misa-F-off | 22 | 22 | 336 |
| misa-D-off | 9 | 9 | 197 |
| default-lanes | 299 | 897 | 1001 |
| default-vpr | 184 | 552 | 991 |
| default-fpr | 82 | 246 | 872 |

[全配置前沿](../../isla/target/float-support-review/final-coverage/vector/full-source-frontier.json)绑定 47 个已完成分组及最终 `summary.json`；default-FD 的前 17 组增量摘要与最终摘要逐组逐字段相同，后 14 组使用最终摘要，分组集合不重不漏。每组实际 argv、runner/IR/config/输入/结果/初始化/trace/trace-map 的哈希、完整 R1 `setup_pre_state`/Eq/SAT、唯一终态账本和 **25772 个 runtime Jump 全集**均已核。六配置 Jump 按完整符号化指令、目标、fallthrough 与 SourceLoc 一致后才合并展示；方向并集为 **1985**，不能跨配置相加充当源码分母。

[full_inputs.py](tools/solve_vector_coverage/full_inputs.py)封装现有 v4 默认 2501、fractional overlap 8、F-off 22、D-off 9 与分派对照 565，字节相同地保留输入和配置；非法 misa 31 仍排除。原始输入入口 basename 为 `isla-directed-final-full-inputs-20260926/vector`，index SHA `5bb5712044f12ddee6f9df9468f02f1e207dce9bd39b20db3792b6387c7528b2`。逐组证据在[最终审计目录](../../isla/target/float-support-review/final-coverage/vector/full-audits/)，生成/验收工具是 [audit_suite.py](tools/solve_vector_coverage/audit_suite.py) 与 [final_frontier.py](tools/solve_vector_coverage/final_frontier.py)。九项入口接线和篡改负控制已复验通过。

### 最终源码迁移与已补的具体缺口

[final_catalog.py](tools/solve_vector_coverage/final_catalog.py)已从共同冻结生成九文件目录，SHA `a8755acda37e27b62819e861fd730657442126bd657ef078e4c3d68cf5cb3f46`：22 clause、906 词法 site/2391 arm，其中 SYMBOLIC 活动候选 695/1840，out-of-build 211/551，另有 73 个数据选择策略。目录与迁移产物 basename 为 `isla-directed-final-coverage-20260926/vector`。`fp_min_pure/fp_max_pure` 搬至 `FD/fp_minmax.sail`，完整定义 token 相同，各保留一个 match 和六个 ITE 策略；新 global key 与 scalar 共用，不能按两族重复累计。四个共享 decoder matches 只列真实依赖，没有把整个 `vext_arith_insts.sail` 词法库存计入 22 clause 分母。

- 普通 lowering 338 项中，95 个 if 已核真实互斥 then/else 主体，7 个 if 已核隐式 false 跳到同 join；另有 127 个 match 和 78 个 assert 结构证据。31 个 predicate/early-return body 已全部通过[独立审定](../../isla/target/float-support-review/final-coverage/vector/independent-predicate-review/report.json)，报告 SHA `87cfd9abcb2158bfd5979b9ab81985c653fb79c643cc6df6de0eaccb69fbc353`，11 个错误极性、callee、参数、返回、常量、CFG 与 caller/config/context 负控全部拒绝。默认 FD 的 27 个直接 clause site 双向命中；两个 SEW8 mask 条件在实际 decode-first 域分别由五个、四个 enum 的 decoder 格式限制排除，含 160/128 次 Bool 赋值穷举和 vtype 无写闭包。共享 overlap、init_masked_source 的 caller/config 仍分别登记，不能因这 31 项静态通过而整体闭合。
- 237 个源码短路因子的 495 个编译实例全部通过冻结词法操作数、到达定义和正常 CFG 检查。原 3105 上 200 实例双向、114 单向、181 无方向；**162 个异常出口仍独立保留**。源码因子、多份编译 lowering 和 caller/config 义务不能互换计数。
- [overlap_returns.py](tools/solve_vector_coverage/overlap_returns.py)把最小 12 例中的 14 次 helper 调用按真实 edge 顺序与精确 `zexecute:CallPC` 重建到 `End`，再沿 caller 的 `znot`/Assign/Goto 到下一实际 Jump。八个 fractional caller 的 pc136 `EMUL_pow_rs >= 0` 均明确返回 false 并进入同终态 `Illegal`；窄化 pc95 RHS false 也有返回链。[V 证据](../../isla/target/float-support-review/final-coverage/vector/overlap-minimal12-return-bindings.json)与 [BF 四例证据](../../isla/target/float-support-review/final-coverage/vector/overlap-bf16-4-return-bindings.json)分别保留实际 caller，引用独审通过的 overlap 证书 `d0230dc0e1d45a9f2aab17c54fad71e246d881c2df69ee7109d9d7226f08c3ad`。这些 RHS 没有新增 Jump。
- [overlap 参数独审](../../isla/target/float-support-review/final-coverage/vector/independent-predicate-review/overlap-arguments.json)进一步核实 9 个 V、5 个 BF16 精确 Call PC 的实参到达定义：同一 `get_lmul_pow`、signed 三位保守范围 `[-4,3]`、精确 `+1` 转换、helper 形参无改写，以及 pc75/78 极性和控制依赖。SHA `a5ada1c373db052dd4f4f5b48721b3647f4ada6e8e6e86b07610d7abf7fa4b42`；6 个篡改负控拒绝。它支持 V 26 个、BF16 14 个指定 caller 方向的静态排除，实际调用到达另由对应 trace 证明。
- [rounding_frontier.py](tools/solve_vector_coverage/rounding_frontier.py)用固定 Spike SoftFloat oracle 派生 15 例：三种 SEW 各覆盖 RTZ、RDN 正负、RUP 正负的最小次正规溢出。新 runner 回放及[独立消费审计](../../isla/target/float-support-review/final-coverage/vector/recip7-frontier15-audit/summary.json)均通过；pc942/951/961/969 的四个 LHS 与 pc984 的 overflow 选择 if 在三个 width caller 各有双向见证，共 30 个明确局部义务。相对原集新增 11 scoped 方向，并集为 1996；[局部 source/caller 表](../../isla/target/float-support-review/final-coverage/vector/recip7-frontier15-source-witnesses.json)保留五个 source key、配置、阶段、context 与唯一终态 ID。

### 特权态增量边界

[privilege_frontier.py](tools/solve_vector_coverage/privilege_frontier.py)准备[58 条输入及源码前提](../../isla/target/float-support-review/final-coverage/vector/privilege-frontier58-inputs/index.json)：User/Supervisor 各 22 baseline、三 width `VFUNARY1`、FS-off/VS-off、F-off/D-off 代表。只改变显式特权枚举与身份，保留已验证独立预期。冻结 `FD/fdext_control.sail:18-19` 的 F/D 使能读取 capability、misa、FS、flen、Zicsr；`V/vext_control.sail:17-26` 另读 VS；`Zicsr` 只读 capability。这些使能链无 `cur_privilege`、虚拟化或 stateen 谓词。stateen 的特权分派属于 Zfinx 链，不能拿 FD 的命中清掉它的义务；现配置 `sys_enable_zfinx=false`、H=false。

新 privilege runner 已完成 58 条，三配置实际入口、初始化/结果/trace-map、全部 25772 runtime Jump 和唯一终态账本均验收通过：default-FD 54/154 终态，F-off 2/2，D-off 2/2。成功/执行非法/译码拒绝 runner SHA 分别为 `d17880a14f7cb6b04985386fa05f5dd869d6b104adb43106dfd5cb200cc9a745`、`fe7807cd6fce6853a49e2788d798df2b864275f1f53177af70d23ddba6b6ba5e`、`7bb8df3787aa8b63a1a5c7964c2f23c6c42e33186badd9c6eb684677a9f4b032`。每例实际 `bound_actual_registers.cur_privilege` 为对应 `|User|` 或 `|Supervisor|`；[特权 source/caller 表](../../isla/target/float-support-review/final-coverage/vector/privilege-source-witnesses.json)分列 29+29 条、79 对阶段终态及 1546 个 V 使能 LHS/context 见证。

逐对比较保留了真实差异：User/Supervisor 的完整 decoder 会经 `cfi/zicfilp_regs.sail:get_xLPE` 选择不同特权路径，不能宣称完整译码分支相同；本次 29 对具体输入的选定 V 使能因子序列一致，25 对 encode 与 25 对 execute 的完整序列一致。该有限观察不能推广成任意三特权状态域的全路径等价。

未主动固定 stateen，初始化摘要也未导出 stateen 的值，因此未声称已核其动态值。现 H=false 的官方 R1 域排除两个虚拟特权态；集成对三个 runner 各两个虚拟态做实际 R1 拒绝，另有未知枚举拒绝，共七个负控，不以放宽域制造通过。独立 decode/encode phase 纯读证书可作状态一致性前提，见集成 `phase-purity-binding.json`，不计新增动态 case。

[cfi_privilege.py](tools/solve_vector_coverage/cfi_privilege.py)消费既有同 word `FVFMATYPE` 的 Machine、Supervisor、User 三条实际 decode 终态，产出[CFI source/caller 绑定](../../isla/target/float-support-review/final-coverage/vector/cfi-three-privilege-source-witnesses.json)，SHA `6c2b1abe1f5044e4ee41e2ae473142ca99217aba1395c02af69e4027e79a4fec`。六个外部依赖 site、15 项局部义务独立登记，不改原 695 个活动词法库存：`get_xLPE` 的三个非虚拟 enum arm 实际命中，pc6 两向均观察；User 的 pc17 及下游 `currentlyEnabled(Ext_S)` 精确 context 命中。false 排除严格限定实际配置 `misa.S=1`、S/U/Zicsr 能力和 decode 无写前提；Zicfilp 能力由冻结 runtime 常量解释证明。三种 LPE getter 经 bool 转换、`currentlyEnabled` 返回及 decoder pc327 的实际 false 消费相连，没有虚构 RHS Jump。六个极性、实参、getter、位值及返回消费篡改负控拒绝。

该绑定已通过[独立 CFI 审定](../../isla/target/float-support-review/final-coverage/vector/independent-predicate-review/cfi-review.json)，SHA `4d626ed7194982e9ab166b9539ef3eecbd252e349ded8aab08e3f758aae8e7e8`，另有两个负控拒绝。实际[初始化提取 v2](../../isla/target/float-support-review/final-coverage/integration/cfi-initialization-extractor/extraction-report-v2.json)确认同 IR/runtime/config、`model_init=true` 后，`mseccfg/menvcfg/senvcfg` 原始 Val 均为具体零。三者不在 RV64 Target `reg_list` 中，canonical runner 的非 Target 覆盖仅允许 misa；本组三态输入也未覆盖它们。typed getter 分别读取 MLPE bit10、LPE bit2，`bool_bit(0)=false`；因此 LPE=true 不属于此固定入口域。两个虚拟枚举的通用排除依据是冻结 `constrain_pre_state` 只在 `supports_h && supports_s/u` 时加入枚举，以及实际 H=false；六个具体 R1 拒绝只作为负控。结论限定本 `FVFMATYPE`/默认配置/固定 CSR 入口；其它配置或自定义 CSR 入口须重新立义务。

### 六配置与合法 D-off caller

[fixed_cfg.py](tools/solve_vector_coverage/fixed_cfg.py)已为六配置生成各自的固定 CFG 证书。默认证书见 [default-fixed-cfg.json](../../isla/target/float-support-review/final-coverage/vector/default-fixed-cfg.json)，SHA `213b3b92b05f20d65998976bdeeba7e816e6f7ea0facd58ffccbdfa0354d89f7`。四内部配置的 21 个全 IR 引用仅为精确 Id Jump，未写入、未地址逃逸；结合固定 capability 与字面条件，共 93 个固定 Jump、67 个函数可作有限裁剪。各配置仍使用自己的 sidecar 和证书；caller 实参、SEW、LMUL 不是配置常量。BF16 同伴以该证书裁剪共享 V 的 1767 个 root×site/arm 候选，得到 441 已观察、941 条件排除、385 待核，未把它们称为全部可达分母。

原 D-off 九条拒绝只针对相应宽操作的 SEW32，不能据此排除其 SEW16 caller。[d_off_survivors.py](tools/solve_vector_coverage/d_off_survivors.py)准备 13 个普通 SEW32 和 9 个宽/窄 SEW16 成功代表，输入 manifest SHA `58446d9c66efe373ec32c68a5e80cd4f05ad71ff565a902ee9e313dec6e538ae`。[实际审计](../../isla/target/float-support-review/final-coverage/vector/d-off-survivors22-audit/summary.json)为 22 case、66 唯一终态、807 scoped 方向，完整 25772 Jump 绑定。其 D-off 配置 SHA `ca4d75bd0bb1610f5bb6f43c6e313c70544f8b58a03c73f0436353e0443f58a7` 同时清 misa.D/V，F 仍开启；sidecar SHA `749cd1928e40e63c1ffff2f5bd7af23c9e0f2846db962f75a05652fbb0350dc9`，使用上述 privilege-v2 runner，不借用默认 sidecar。

[caller_configuration_index.py](tools/solve_vector_coverage/caller_configuration_index.py)生成[22×6 实际 caller 表](../../isla/target/float-support-review/final-coverage/vector/caller-configuration-index.json)，SHA `481b6487968f507b919e38b80be6aad12a88a7e9fdab020856f2c3cdd6cbdcd5`。原 3105 与 D-off 22 合计 3127 case、9111 终态，132 格全部有实际 R1 代表：110 格有成功执行，F-off 22 格有译码拒绝。recip7 与 U/S 增量另列。每格保留配置、阶段终态、审计哈希和 context 计数；它不是 source arm×精确 root Call 的完整闭合证明，剩余 helper/guard/enum/宽度义务继续保留。

### 精确 root caller 前沿与下一批

[root_caller_frontier.py](tools/solve_vector_coverage/root_caller_frontier.py)逐配置从真实 typed Call 建立 284 个 decode、185 个 encode、728 个 execute 根调用候选，按 source/clause/phase/config/root Call 保留义务及完整见证 context。`currentlyEnabled` 的 literal Ext 实参只固定枚举分派，未知 FS/VS 和函数返回继续保留；每配置因此可再排除 1056 个过近似候选。[独审消费工具](tools/solve_vector_coverage/refine_reviewed_frontier.py)将两个 SEW8 mask source site 的四个 arm 关联六配置证书；默认配置的 overlap affine 参数证书沿 helper CFG 传播，排除 48 个 source/root arm，其中包含上述 26 个直接方向的控制后继。其它配置未借用默认 sidecar 的参数数据流证明。

[当前六配置前沿](../../isla/target/float-support-review/final-coverage/vector/root-caller-frontiers-reviewed/index.json)每配置保留 14095 个 source/root 候选；这不是已确认可达分母。

| 配置 | 已观察 caller 义务 | 配置及 Ext 裁剪 | mask 排除 | overlap CFG 排除 | 待参数域或实际见证 |
| --- | ---: | ---: | ---: | ---: | ---: |
| default-FD | 5100 | 5976 | 4 | 48 | 2967 |
| misa-F-off | 547 | 5976 | 4 | 0 | 7568 |
| misa-D-off | 2533 | 5976 | 4 | 0 | 5582 |
| default-lanes | 3235 | 6230 | 4 | 0 | 4626 |
| default-vpr | 3867 | 3000 | 4 | 0 | 7224 |
| default-fpr | 2691 | 5976 | 4 | 0 | 5424 |

默认 2967 项已压成[可执行审定清单](../../isla/target/float-support-review/final-coverage/vector/actionable-default-frontier.json)，SHA `8c1d1b3d8d73e76f4aa91dfa42c6103d2e4cf4b69ede2dd3541643c47dfd17e7`：overlap 5 项、capability/misa/FS/VS guard 806 项（68 个 typed 谓词）、逐 clause 整数域 1737 项（45 个）、数值 wrapper 宽度及分类 181 项（108 个）、clause enum/mask/VL/accessor 238 项（139 个）。每个谓词附源码位置、精确 PC/方向及全部 caller；整数域须沿各 clause 的 decode/guard 和 R1 证明，不能套用 BF16 的固定 SEW16。

[能力独审](../../isla/target/float-support-review/final-coverage/vector/independent-predicate-review/vector-fixed-capabilities.json) SHA `fa03cfcc002bf9a2fe95a7fcbbfab4f215fd8a4a215d597401859708584a2f63` 对实际 Ext 参数、七段 V Bool CFG、冻结 Full 能力常量和短路极性审定 554 个默认 source/root 排除。FS/VS 未全局固定，P1 其余 252 项继续单列。

estimate 分类增量的[严格审计](../../isla/target/float-support-review/final-coverage/vector/estimate-frontier21-audit/summary.json)为 **21/21、63 终态**：三个宽度各覆盖 Recip 负无穷、正负较大次正规、两个高指数普通值，以及 Rsqrt 负无穷和负次正规，预期来自固定 Spike 独立 oracle。逐 case 的 [21 个精确 source/root 见证](../../isla/target/float-support-review/final-coverage/vector/estimate-frontier21-source-witnesses.json) SHA `0fd4232070af8e484cc198326de12e5acdc4cb0b0195f984ad7c5452f13ac23d` 全部命中；新输入 manifest SHA `d622d73991f7b37a6eb9a3999417314c914297e71f34661cdccae9f1b5392dad`。消费 enum86、能力554 和 estimate21 后的[默认前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-plus-estimate21.json) SHA `0401ee3c91c2a359e78014abcf80df4fe08c08c18bc2159c76f91688bf8c9c27` 为 5126 已观察、2272 待核；各历史快照保留，整体尚未闭合。

P1 后续[状态域独审](../../isla/target/float-support-review/final-coverage/vector/independent-predicate-review/vector-state-domains.json) SHA `b7f245e5c782e46b63b44eae6f7b47ee7add117ee835da7e438c475d05aaa3d0` 接受 231 个 encode 与 20 个相关 decode 排除：成功同 constructor 真实 decode、16 种 FS/VS 投影、实际 R1 初始化和同前态纯读是明确前提。另用 `FNV_CVT_F_F/SEW16/FS0` 的[一条严格拒绝见证](../../isla/target/float-support-review/final-coverage/vector/narrow-fs-off1-audit/summary.json)命中 root `zencdec_backwards:28489` 下 `currentlyEnabled:537=false`，并补两个其它 guard 义务；原 P1 的 806 项在列定默认 source/root 域已完成，不推广到整个译码器或其它配置。

数值[宽度独审](../../isla/target/float-support-review/final-coverage/vector/independent-numeric-width-review/review.json)与[范围/返回合同独审](../../isla/target/float-support-review/final-coverage/vector/independent-numeric-width-review/contracts-review.json)再接受 24+21 项；两个 sub 上下文均保留，CLZ/7-bit unsigned 范围来自真实 typed 操作，未用观测次数代替证明。当前[正式默认前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-numeric45-reviewed.json) SHA `04c972079aed92f18339d4513674fba1eea7cf57c2c1e3a8ff257479da377da2` 为 **5129 已观察、1973 待核**。本节静态与动态证据严格限定旧 1dcc 冻结；新 IR 348147 的全族复验和证据迁移由集成单独记录，不能直接继承这些结论。

P2 [整数域独审](../../isla/target/float-support-review/final-coverage/vector/independent-domain-review/certificate.json) SHA `96703cb72cf9ec8ef88e6263262636f1afb99357bdc0c97ef6fa49fb0af23269` 通过 1737 项身份双射与八项负控，接受 1667 排除、保留 70 个真实可达候选。证明包含各 clause 的 decode 宽度、前置 guard、实际 SSA 实参、寄存器对齐/末界和整数集合；未跨越 guard 给前置调用追加后置条件。[消费前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-P2-reviewed.json) SHA `f3de519420fe6c3d626ed043fc727bc510faec53252360c6adbf73749436b4ae` 为 **5129 已观察、306 待核**：P2 70、P3 37、P4 199。70 项对应 35 个 root 下 `assert_vector_num_elem_upto_128` 的两个 count 方向，静态保守域含 32 或 64 个元素，仍须实际输入见证。

后续[转换 encode21 独审](../../isla/target/float-support-review/final-coverage/vector/independent-predicate-review/vector-conversion-encode21.json) SHA `e4cd7d397b70e623484e61cdd70648dad75ac8c2fbc381e52ea2e9f99fad8c4f`核对完整 AND 真值表、实际 Call 支配 Jump，以及同 constructor 成功 decode 后 FS/VS 非零和 encode 纯读同前态；两个负控拒绝。仅接受 `zencdec_forwards:18778/18851` 下 21 个 encode LHS=false 排除，15 个 decode 候选仍待真实拒绝见证。[严格消费器](tools/solve_vector_coverage/consume_conversion_encode_review.py)逐完整 edge/global key/root 检查后生成[encode21 阶段前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-conversion-encode21-reviewed.json)，SHA `a230817237ae272387b1e3845524e79ca075e367f5ac752ac415ccf760016c39`：**5129 已观察、285 待核**（P2 70、P3 37、P4 178），未新增动态 case，未应用于新 `348147`。

### width44 与 P3 37 的精确消费

[width44 独审](../../isla/target/float-support-review/final-coverage/vector/independent-valid-fp-width-review/certificate.json) SHA `ecabb90463fa5c9d237aa5d339340270501dffd6d9879deccdb9661fc6631af6`核对 22 个实际 root 的 SEW 首参、完整 SSA 支配、匹配前缀无写、未裁剪 helper 闭包唯一调用、完整 rm=0..7 typed 表及五项负控，接受两个源码 site 的 44 个 LHS=false 排除。[P3 数值余 37 独审](../../isla/target/float-support-review/final-coverage/vector/independent-numeric-width-review/widening-getscalar-review.json) SHA `d130e1cebfa66aacce678cf287cff31aca6ce2ede45351e227dcd572dd783877`核对 28 root 的实际值来源、SSA 与 SEW context，接受 m16 25 项、get_scalar 断言失败 9 项和 scalar64 arm 3 项；七项语义负控及一项正测通过。**P3 独审显式 `same_m_contract_used=false`**：转换正常返回的 32/64 位、negate 切片/拼接、read_vreg 的 2×SEW 与实际 dispatch 分别证明；未知参数保持未知，未采用旧候选的同 m 参数假设。

[消费器](tools/solve_vector_coverage/consume_width_reviews.py)逐完整原义务、source key、函数/clause/phase/root、边方向/successor、源码文件及配置/IR/artifact SHA 串行消费 44+37，保留两份中间前沿。最新[旧版本前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-numeric37-reviewed.json) SHA `4f171160518b47651aae220ecbab3b5ac6f1b03d59071d9df0fe616cbbf80e13`：总候选 14095，**5129 已观察、204 待核（P2 70、P3 0、P4 134）**，动态 case 未增加。另做[11 项消费负控](../../isla/target/float-support-review/final-coverage/vector/width44-numeric37-consumption-controls.json)，SHA `aaf0c771bfac5467ea71979f62c65ad15c1eb61f5a89f995016574c966f63c03`，跨 IR/配置、反向 edge、错 successor/global token、假 same_m 与独审帧仍含被排边均拒绝。这些结论只属于旧 `1dcc` 默认配置。

随后[clause40 独审证书](../../isla/target/float-support-review/final-coverage/vector/independent-clause-assert-review/certificate.json) SHA `f8607bbb2871f88be0443b64d43ed5f3a1eb19292e2f2435a3b981b6634b0104`接受 22 clause 的 30 个断言失败边与 10 个短路 LHS=false，独立核完整 SSA/AND join、guard 支配、129 个 get_end_element 返回以及末界路径和闭包无 VL/vtype 写；四项移除前提负控重现。[消费器](tools/solve_vector_coverage/consume_clause_assert_review.py)逐 `accepted_identities` 核对证书、正文、候选、源码及全部依赖，生成[clause40 阶段前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-clause-assert40-reviewed.json)，SHA `795100faf068493785e36dad3f0bbcc3901157f1311ba1c293366a91629d043b`：**5129 已观察、164 待核（P2 70、P3 0、P4 94）**。六项[消费篡改负控](../../isla/target/float-support-review/final-coverage/vector/clause-assert40-consumption-controls.json)全部拒绝，SHA `a301e4eb01495700fd90ce47fa0ecf786fb5a81c7aa10b31121780a0a9b56e49`。204 阶段前沿完整保留。

### accessor38、illegal21、conversion16 的旧版消费

[accessor38 独审](../../isla/target/float-support-review/final-coverage/vector/independent-accessor38-review/certificate.json) SHA `0cf332e7a8557a6d0749f20b6f33fec012011ff0f29df647b569e9f665460250`核 29 root、546 保守组合、七项语义负控；[消费器](tools/solve_vector_coverage/consume_accessor_review.py)核完整 source/root/edge 后形成[126 阶段前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-accessor38-reviewed.json)，SHA `fae94c55f9bcf4186d08ffaf3600b2e404cb668bd1b7f22b017e68fc38231537`。六项消费篡改负控通过，报告 SHA `88afd2073399940dc2913a9da80d19bef99c73503a10f5a7a5a59ca7967a7a88`。其内部 `get_start_element→Ok` 返回证明不能代替整个 `init_masked_source` 的正常返回证明，故归约外层两个 Err 义务仍保留。

[illegal21 独审](../../isla/target/float-support-review/final-coverage/vector/independent-illegal-guard21-review/review.json) SHA `aa056636c4fd8297c40f82ce2e06739d1b3ffbd7d7d303ea8e6d74a617ec28b4`独立解析原 IR：全部 47581 decoder PC、128 普通与唯一 vill getter、638 未剪枝闭包无 vtype 写/逃逸、20 root 入口分派纯声明/Jump，以及 RFW 的 EEW=2×SEW 支配链；21 项移除前提负控恢复目标边。[精确消费](tools/solve_vector_coverage/consume_final_static_reviews.py)形成[105 阶段前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-illegal21-reviewed.json)，SHA `9a75bc5d0168118e69b681edb0b9fca2b02be4b50b3f0bd1b67ddddd536f4ac8`；八项消费负控报告 SHA `fd5e87fdca3edb684e94b302ed2bceeb1ef747ffcd62ae8f6c794aee23893e4d`。

[conversion16 独审](../../isla/target/float-support-review/final-coverage/vector/independent-conversion16-review/certificate.json) SHA `459689cefb9cc9783890e650113adc76a40fdf3cd3d81dc67b184839f50b68a5`接受九个局部 m8 与七个 outer 因子排除，核 45 个完整 SEW/enum CFG context 和 160+128 decoder guard 组合。**九项候选原因已修订**：原 v1 的 enum-only CFG 遗漏 SEW/outer 相关性，其“撤 decode 即有真实反例/必须依赖 decode”标签不成立；完整 CFG 中九个 m8 位于 outer=false 路径，直接由 outer/SEW/enum 关联排除。九项负控改为明确修改 m 谓词、保持其它完整 CFG 关联；七个 outer 仍依赖成功 decode 的 SEW8/enum 限制。原 v1 候选 SHA `aa62e571…7baf8`完整保留，九条 `candidate_claim_correction` 已逐义务写入新账本。

同一消费器核对独审原文、依赖 SHA、实际 Jump/successor、完整源码身份及 root，并拒绝八项篡改（含遗漏修订及保留伪反例标签）。[conversion16 阶段前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-conversion16-reviewed.json) SHA `3cae9efbb4dd24c39b7dffc5a98d26187faed23cc01f7c1f386235d282688ea2`为 **5129 已观察、89 待核（P2 70、P3 0、P4 19）**；负控报告 SHA `8fa88966fb085880fc115aea047e834eade0c02205fd323ac7a86c9cbe94eead`。三次消费均零新增动态 case/hit，仅适用旧 `1dcc/default`，全部中间前沿保留。

随后[归约外层 Err2 独审](../../isla/target/float-support-review/final-coverage/vector/independent-reduction-outer-err2-review/certificate.json) SHA `4805ebdd237a6b6668f87f5a6cf56efe9f50e58d0a3316e5cf03573524644925`用独立反向到达定义算法检查完整 131 指令：End126 的 RETURN 定义只有 51/125，均为 Ok；Err 定义15在已审内部 Ok 前提下不可达。另核 fresh 局部 frame、无地址逃逸、正常返回仅写 caller destination，以及 Call 支配 Kind 和中间 Decl 不写返回。五项独审 TDD/抽象变异负控通过。[消费器](tools/solve_vector_coverage/consume_reduction_return_review.py)精确接受 RFVVTYPE `37580 true→37585` 和 RFWVVTYPE `37830 true→37835`，生成[旧版最新前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-reduction-Err2-reviewed.json)，SHA `d28b7f1a9f3761b3ae52db531e9ddb46193ed615a775e7db5d2f2fa8ce242c7e`：**5129 已观察、87 待核（P2 70、P4 17）**。七项消费负控报告 SHA `de04aad4d5b6f7bf5ae7b2a8e267cfcf1aa6d4adc26a679b3f61077d0f298a8d`；零新增动态，不证明终止或无异常，不迁 `56cc`。

### 后续 IR 的可复用证明合同

新 `56cc69` 来源与严格 trace 审计已通过，详见本文开头；完整源码义务仍需新 IR 实际重绑。V4 是 `valid_fp_op/illegal_fp_normal/valid_vtype/valid_rd_mask` 四个纯 Bool 改写，与前述四个 decoder mapping matches 无关；7 site/14 arm 已实查登记 `not_lowered`，仍要求实际 caller 消费。

[87 项根因清单](../../isla/target/float-support-review/final-coverage/vector/actionable-default-frontier-87.json) SHA `a4c84581cde00680bc1455842c6ca6c828a4514cd25d9a2984dd3e1f8d63965e`和[当前源码合同索引](../../isla/target/float-support-review/final-coverage/vector/source-proof-contract-index-87.json) SHA `2b65a05ab94063cfb1a740106a6505445f4ed2637bd6b8d0572380cccad0333d`保留 87 待核及本轮 198 独审排除的源码身份，链接已审 loop/mapping 合同及九项原因修订。原 285、164、126、89 等历史清单/索引完整保留。每项包含 function/clause/phase、源码表达式锚点哈希、前提、旧证据引用、证明状态与新 IR 重绑定门槛；表达式锚点不冒充完整 match 主体或等价证明，PC 仅属于版本绑定。

| 根因 | 旧待核数 | 后续工作 |
| --- | ---: | --- |
| P2 `<=16 false` / `<=64 true` | 70 | 新 35 root/70 方向已独审并消费至独立新账本；旧计数不迁移 |
| P3 数值 wrapper | 0 | 37 项旧版独审已消费；新 IR 重绑 |
| P4 valid_fp_op 宽度 | 0 | 44 项旧版独审已消费；新 IR 重绑 |
| P4 clause 断言 | 0 | 40 项旧版独审已消费；新 IR 重绑 |
| P4 accessor 整数/Err | 0 | 38 项旧版独审已消费；新 IR 重绑 |
| P4 illegal guard 前提 | 0 | 21 项旧版独审已消费；新 V4 源义务另审 |
| P4 转换 decode FS | 15 | 新15个AND LHS=false已独审消费，RHS未执行；旧计数不迁移 |
| P4 转换局部宽度 match | 0 | 9 项旧版完整 CFG 排除已消费，候选原因已修订 |
| P4 转换 outer enum 因子 | 0 | 7 项旧版 decode/enum 排除已消费 |
| P4 归约 mask Err 返回 | 0 | 整个 helper 正常返回及 caller 消费已独审；新 IR 另绑 |
| P4 slide 第二元素 | 2 | 新两条普通if方向已独审消费；旧计数不迁移 |

P2 的旧合同 ID `p2_count32_count64_actual_contexts` 仅保留历史命名：一个实际 num32 输入即可见证两条所需方向，并不要求 num64 在每个 root 可达。加宽路径在相应合法 SEW/LMUL 域内可能最多只有 num32。新 IR 见证不得反向增加旧版 observed 或扣除旧版这 70 项。

[归约外层 Err2 候选](../../isla/target/float-support-review/final-coverage/vector/reduction-outer-Err2-contract-candidate.json) SHA `ce036a63fc809ef2c502be84d9d89e2b7eddea3c7986134c3eea67a59ba9c696`由[完整返回分析工具](tools/solve_vector_coverage/reduction_return_contracts.py)生成。复用 accessor38 独审的两个真实 root 及 get_start 正常 Ok 前提后，另遍历 `init_masked_source` 全 131 指令：除 Kind 外的数字、mask、extra-ops 分派均保守双向，保留循环；正常 End126 的构造器集合只含 Ok，Exit128 单独列为异常，不证明总会终止。真实调用 `37578/37828` 到 Kind 消费者 `37580/37830` 间仅 Decl，返回构造器与不匹配极性已核。四项明确抽象语义突变负控不宣称冻结 IR 有实际输入反例。候选阶段保留旧89；后续独审及89→87消费见上文，**新56cc仍需另绑**。

[断言40候选](../../isla/target/float-support-review/final-coverage/vector/clause-assert40-contract-candidate-v2.json) SHA `724b31b7cf9e89b52c21db5df44456dcef18d614cdee52bc631125da03f9363c`从实际 SSA、decoder 宽度域、支配的 variable-width guard 和 R1 VL≤VLMAX 构造七类源公式，三项省略必要前提的反例能触发失败；后续40独审消费见上文。[访问器38候选](../../isla/target/float-support-review/final-coverage/vector/accessor38-contract-candidate.json) SHA `633cb9f7050682774353b242e702941e4de4e5002582f6311d33b752f25f3c5f`绑定七 helper、29 root 的实际参数，枚举保守 SEW/LMUL 域；两个归约 `init_masked_source` 复用已审 vstart=0 的实际 get_start→Ok→End 返回合同并核内部 caller Kind。Kind 的“不匹配”语义绑定冻结 executor。初次准备因未登记 `append/append_64` alias 显式中止且无输出；核实际同实现注册后，与 `eq_bit/eq_bits` 一起仅在本候选局部解释、保留原 sidecar 行。其后独审及 164→126 消费见上文；未外推为 execute 的两个外层 Err 排除。

[illegal guard21 候选](../../isla/target/float-support-review/final-coverage/vector/illegal-guard21-contract-candidate.json) SHA `23ca1ee9672ba66ac1f3ffb60b893a27d733ca40bce0810c0e5e0d00a0cca3f0`包含 20 root：128 个保守普通 R1 vtype 的 valid_vtype 均真；唯一 canonical vill 的 get_sew=8，与这些 constructor 成功 decoder 不含 SEW8 的域矛盾，沿无写前提到实际 execute root。另一个方向绑定 RFW 的实际 EEW=2×SEW≥8。移除成功 decode 或把 EEW 改为7的两个反例均使原排除边可达。候选阶段未扣数；其后独审及 126→105 消费见上文。

120 项原 lowering 库存另分九个根因：mapping18、完整 when22、loop29、转换局部 match15、纯分类/比较/FMA 宽度 match20、整数 assert match8、flags if2、VLEN if5、get_V if1。loop 和 mapping 后续独审合同见下文；这些静态结构合同不消除全部 caller/config 义务。

原有 **120 个尚无完整 lowering 的活动 site**清单独立保留：18 enum mapping、22 整体 mapping guard、29 loop、43 match、8 if。29 loop 随后完成下文独审结构和列定 context 账本，仍未枚举全部 caller/config；mapping18 随后也通过整表与 36 caller 独审，剩余 73 项尚待对应完整证明。清单给出候选 runtime 函数/PC 或无精确 anchor 的原因：转换局部 type match、纯 helper 格式 match、整数断言 match、`fp_gt/fp_ge` flags 选择、五个 VLEN 分派及 `get_V` 配置选择均未因未观察而删去。循环常按 `num_elem` 遍历并在 body 判断活动 lane，不能仅用 VL0 代替循环零迭代证据。

五个真实可达的 overlap pc119=true 缺口，根 Call 为 `24949/25230/26435/30271/30546`，现已全部有精确 caller 见证。[生成工具](tools/solve_vector_coverage/overlap_high_sources.py)对独立预期 baseline 做源物理 VPR 双射置换到 v8，同步初态、预期与 word；vm1、SEW32、LMUL1、VL1、目的 v4/v5 及其它源不冲突。原[五条输入](../../isla/target/float-support-review/final-coverage/vector/overlap-high5-inputs/suites.json) manifest SHA `12e1c4a073b77417a00df5711b5ab85a91682b6491ad2b6830615cecaa491a75`，实际审计 **5/5、15 终态**，但 FWVV 初版改了 vs1，命中已有 root24940，因此只闭四个目标。历史结果保留；修订字段为编码 vs2 bits24:20，新[单条输入](../../isla/target/float-support-review/final-coverage/vector/overlap-high1-fix-inputs/suites.json)使用新 ID，manifest SHA `49fc2bdf3c6a610f656d3b4518eaac3d05f3d3da301095f20f1b396016bdeadb`，审计 **1/1、3 终态**且 root24949 的 pc119=true 实际命中。

[decode outer 传播](tools/solve_vector_coverage/refine_decode_outer.py)将已独审的 zexecute pc26567/27504 固定 false，仅排除依赖 true 的 `VFWUNARY0/VFNUNARY0` execute 路径；四个 root Call 及其源码方向共 29 项排除，无动态见证冲突。false 旁路和 join 保留。与 overlap 六条增量合并后的[前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-plus-overlap6.json) SHA `b22e3099030d706e62496f8c9d3ad8ab477873bd646f00b13d4ccf2dbbffd927`，默认观察 5105、待核 2933。上表和 2967 分工清单保留为前一阶段快照。

[枚举 CFG 工具](tools/solve_vector_coverage/enum_outer_cfg.py)对 FVFTYPE 的 13 个、VFUNARY1 的四个完整 constructor 枚举分别传播 Bool/enum 常量；未知整数、mask、callee 返回保留双向，控制流 join 仅保留一致常量。独立[审定](../../isla/target/float-support-review/final-coverage/vector/independent-enum-outer-review/review.json) SHA `8b40f7a847a8b32f8c622d05286e83a06eccd9d6992d7e2a83c36f291882a07f` 从真实 IR enum type 核对全域、局部声明和唯一字段赋值，并以更保守的独立 CFG 复核 **86 项** root/edge 不可达。该结论仅适用列定 constructor、默认冻结配置及 caller；不会删除其它 helper 义务。[正式消费前沿](../../isla/target/float-support-review/final-coverage/vector/default-root-frontier-enum-reviewed.json) SHA `7646c7d53b752268365c35a3cd861b8563a8fbb3e69efd3dcefa1574581c9d69`，待核 **2847**，观察仍 5105；原候选与原审核分别保留，整体 `source_branch_closed=false`。

## 历史 c5 与 d012 基线

c5 IR 上三份分派配置的 **565 条结果及 1695 个终态**已有结果、全运行时 Jump、trace 与唯一终态账本守恒证据，见下文[接续复核](#c5-接续复核与最小下一批)。这些记录绑定旧 runner；该 runner 未将每个具体前态接入完整 `setup_pre_state`/Eq/SAT 门槛，故只保留定向结果和运行时 trace 历史证据。上述最终 1dcc 冻结的新结果独立完成实际 R1 验收，没有把旧 capability probe 或输入静态检查升级为逐例 R1 通过。

当时的 v4 输入包分为默认 FD **2501 条**、合法关闭 F/D 的配置 **22+9 条**；旧非法 misa **31 条**独立保留为 raw 诊断。另有 8 条 fractional-overlap 补例。c5 的七文件目录与最终冻结不同，历史复核仅使用 c5 冻结源码；后续 min/max、FmtVal、R1 gate 及 decoder 修改已按上文迁移至 1dcc 冻结。

以下 d012 结果保留为历史基线：**2526 个唯一输入结果通过**，含 guard/状态 988、独立数值 1498、活动归约 NaN 40；另外三种分派配置完成 **565 条结果回放**。成功用例逐项满足 SAT、观察状态差异 UNSAT、结构检查及唯一成功执行；非法用例分别验证译码拒绝或执行 `Illegal_Instruction`，保留被观察初始状态。

随后补充的 canonical `vill` 输入 **28/28** 在相同 d012 IR 通过：22 条先译码拒绝，6 条合法 SEW8 转换 enum 进入执行后拒绝。历史 2526 与补充 28 分列；这些原始输入的机器状态域尚未统一，不能把 2554 条全算作正式 R1 域内 witness。独立 R1 迁移包已生成 **2532 条**（2526 − 旧 raw vill 22 + 新 vill 28），随后按最终 FD 配置另建显式 Machine 输入，当前仍待最终完整 IR 回放。

这批 d012 证据未与 R3 动态 trace 的源码 site/arm 关联，**不能据此写源分支闭合或官方 `make solve` 全路径完成**。生产 P1/P2 改动之后，d012 仅保留历史基线；c5 的后续结果和待复验边界见本文当前结论。

| 受测对象 | SHA-256 |
| --- | --- |
| IR | `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409` |
| E 配置 | `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987` |
| 成功 runner | `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425` |
| 执行非法 runner | `e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3` |
| 译码拒绝 runner | `db2c6a686328b43219fb5aee5a76db0a38fd5b58d66465de62ebca22d1802eda` |

逐批命令、配置/输入/结果/runner 哈希、退出码与耗时保存在 [evidence-d012.json](tools/solve_vector_coverage/evidence-d012.json)。该清单使用 `$IR_STAGE`、`$VECTOR_STAGE`、`$NUMERIC_STAGE`；外部目录 basename 同样记录在清单，不把本机绝对路径写入文档。

## 已实施的输入义务

### Guard、寄存器组与状态：988

[guard_state.py](tools/solve_vector_coverage/guard_state.py) 和 [guard-state-obligations.json](tools/solve_vector_coverage/guard-state-obligations.json) 为 28 批输入登记稳定名字及 case ID。观察集合为 `vr0..vr31`、`f1/f3`、`fcsr/vstart/vl/vtype/mstatus/misa`；这不是所有机器 CSR 的全集。非法用例按被观察集合证明保持，成功用例含完整物理目标组及非目标寄存器。

| 输入批 | 条数 | 义务 |
| --- | ---: | --- |
| baseline、enum-sew | 22 + 274 | 22 clause 代表；97 enum 的合法格式及四个固定编码格式 |
| decode-disable、decode-disable-D | 66 + 9 | FSOff、VSOff、misaFOff 分别隔离；适用宽操作 misaDOff |
| decode-sew8、decode-sew64-wide、decode-convert-sew8 | 20 + 9 + 9 | 非法格式及转换 enum 的译码 guard |
| illegal-frm、illegal-vill、illegal-start、illegal-red-start | 66 + 22 + 19 + 2 | FRM 5/6/7、vill、vstart 非法和归约 vstart 非零 |
| illegal-vd0、illegal-emul、illegal-align、illegal-overlap、illegal-slide-alias | 15 + 8 + 41 + 9 + 1 | masked vd0、EMUL16、每个适用 src/dst 对齐、错误宽窄重叠、slide1up 自别名 |
| legal-lmul、legal-mf4、legal-mf8 | 102 + 22 + 2 | 整数/分数 LMUL；SEW8 整数与 FP16 转换的 mf8 |
| legal-policy、legal-overlap、legal-vd0、legal-slide-alias | 66 + 9 + 4 + 1 | vta/vma、合法高/低重叠、比较/归约写 v0、slide1down 自别名 |
| inactive-state、inactive-hazard | 60 + 52 | VL0、prestart、全 mask；不活动 sNaN 不新增 NV |
| last-lane、vs-dirty-state、move-payload | 16 + 44 + 18 | 跨物理寄存器最后 lane、VS Initial/Clean→Dirty、sNaN payload 与 malformed boxing |

有效 LMUL/VL 受 VLEN128/ELEN64 限制；未用 `VL>VLMAX` 伪造合法状态。目标组使用非零哨兵以区分 tail 保持与清零。`VFMVFS` 即使 VL0/prestart 仍取 element0；`VFMVSF` 此时不写目标。归约 VL0 提前返回，mstatus 保持 `0x6600`；非零 VL 全 mask 会复制 seed 并经 `set_vstart` 设置 VS/SD。

VS 初始非 Dirty 的结果只能证明最终状态：普通成功向量执行末尾的 `set_vstart` 自身调用 `dirty_v_context`，故不能据此独自证明 `wV` callback 已执行。这个区分已交付状态修复协作者。

### 正式状态域与 canonical vill 补例

`Target::init` 的向量上下文域要求：普通 `vtype` 编码合法且 `vl≤VLMAX`，或 `vtype=2^63` 且 `vl=0`。原 `illegal-vill` 22 条设置 `vill|SEW32`、`vl=1`，因此保留为域外 raw-state 诊断，不能用来闭合正式入口的执行 guard。原包其余 966 条 guard 输入、1498 条数值和 40 条归约的 `vtype/vl` 已按 VLEN128、ELEN64 精确整数规则检查。

[canonical_vill.py](tools/solve_vector_coverage/canonical_vill.py) 另建 28 条真实 word 补例及 [义务清单](tools/solve_vector_coverage/canonical-vill-obligations.json)。canonical vill 的低位为零，`get_sew()` 返回 8；22 条代表指令的普通浮点或 FP↔FP enum 在 encdec guard 拒绝。只有实际列出的六个 SEW8 enum 进入执行：`VFWUNARY0` 的 `FWV_CVT_F_X/FWV_CVT_F_XU`，`VFNUNARY0` 的 `FNV_CVT_X_F/FNV_CVT_XU_F/FNV_CVT_RTZ_X_F/FNV_CVT_RTZ_XU_F`。六者由 `valid_vtype=false` 拒绝。此结论按具体 mapping/enum 限定，不泛化到整个转换 clause。命令与输入、结果、runner 哈希见 [独立 d012 补例证据](tools/solve_vector_coverage/evidence-canonical-vill-d012.json)。

[canonical_state.py](tools/solve_vector_coverage/canonical_state.py) 从原包另建 R1 域输入，每例记录原名字/ID、新名字/ID和字段变更，原始文件不改。新名字增加 `.r1`，重新计算稳定 ID；只把 initial/expected `mstatus.SXL/UXL` 设置为 2，并检查 `MPP!=2` 和向量上下文域。FS/VS/SD 等其他位保持，R1 当前没有额外约束 SD。译码拒绝另登记统一 runner 的 `Decode_Illegal` 标签，保留原字段。Machine 的配置默认值已静态核对；最终 IR 的实际初始化、XLEN64、S/U 开启及 H 关闭仍须与 init sidecar 绑定，生成器不会把静态前置检查标为运行通过。

配置迁移分两步保留：E `8247c8d4…` 的实际 d866 初始化已确认 `cur_privilege=Machine` 为具体值，XLEN/FLEN64、VLEN128 与 R1 capability probe SAT 见 [initial-state-E-d866.json](tools/solve_vector_coverage/initial-state-E-d866.json)。最终集成改用冻结 FD `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`，其 privilege 没有初始化；因此新包启用 `--explicit-machine`，每条 initial 显式给 `cur_privilege="Machine"`，名字变为 `.r1fd` 并记录新增字段。这个正式包不借用 E 的初始化前提。最终 runner 必须支持枚举输入并记录该值，三个对照配置也从 FD 另生成。

随后系统比较 E→FD 全部 TOML：除 defaults 外完全相等；defaults 差异为 `cur_privilege`、`mstatus`、`__isla_always_aligned` 和 `vr0..vr31` 共 35 项。初版 `.r1fd` 数值包的 1498 例尚依赖旧 E 的缺省 VPR 零值，不能直接视为同一前态。因此新增 `--preserve-defaults-from`，另建 `.r1fdv3` 共 2532 条，每条显式初始化全部 VPR；共补 40876 个缺省字段，逐字段引用旧 E 哈希和有效值。已有 lane/mask、`expected`、`observe` 均与初版逐项相等。guard 和八条 overlap 补例原本已有全部 VPR，后者不需要迁移。`mstatus` 和 Machine 本已显式；`__isla_always_aligned` 在模型和实际 IR 无定义，是旧配置中未生效的遗留键，不作为虚假寄存器加入输入。这仅保留定向 witness 的前态，不收窄官方 solve 状态域。新包 basename 为 `isla-vector-r1-fd-v3-canonical-20260926`，manifest SHA 为 `eb220e3b25b21c6af293817b8c1513c3dacf109c57502a4a87d3705790b7b45e`。

[fractional_overlap.py](tools/solve_vector_coverage/fractional_overlap.py) 另补 8 条最小负例：SEW16、LMUL=1/2、源目标均为 v8，使 `valid_reg_overlap` 的 `ends_equal=true`，随后 `EMUL_pow_rs>=0=false`。范围为六个实际使用此 helper 的非 BF 加宽 clause，双向量源的两个调用位置分别隔离；`FWFTYPE` 只调用分组检查，不虚增同类用例。输入已迁移到 R1 字段域，d012 **8/8 PASS**，见 [逐例义务](tools/solve_vector_coverage/fractional-overlap-obligations.json)及[独立历史证据](tools/solve_vector_coverage/evidence-fractional-overlap-d012.json)。它们不并入原 2532 包，最终 IR 待复跑；源码末 RHS 是 Bool 返回而未单独产生 Jump，仍须 edge group 与结果证明结合。

### 数值与活动 NaN：1498 + 40

数值生成器、16 组精确分母、独立 SoftFloat/Spike oracle、全部结果与未测边界见 [numeric-results.md](tools/solve_vector_coverage/numeric-results.md)。包括 class 十类、estimate、五种舍入、FMA 符号组合、转换饱和/ROD、比较 qNaN/sNaN/±0、归约顺序和全 mask sNaN seed。数值包主要观察完整目标、fcsr、vstart、mstatus，不能借用 guard 包的更大观察集合替它声称全状态等价。

P2 归约设计复核发现旧包的 sNaN 源元素全部被 mask 屏蔽，缺少活动元素的加宽转换 NV。[reduction_hazards.py](tools/solve_vector_coverage/reduction_hazards.py) 因此补充 **40/40**：普通归约 SEW16/32/64、加宽归约 SEW16/32，各自 ordered/unordered sum × 活动 source/seed × qNaN/sNaN。独立预期为 canonical NaN；旧 DZ=`0x8` 保留，sNaN 新增 NV 后=`0x18`，qNaN 不新增标志。观察集合与 guard 包相同。

这些有限输入不穷举全部数值 helper 分支、estimate 表索引或浮点位模式。纯 helper 的任意输入证明仍属于 D 门槛，不能用单路径具体输入完成数替代。

## 配置分派对照

[configure.py](tools/solve_vector_coverage/configure.py) 从受测基础 TOML 精确替换一个 `true`，先断言键唯一。下表属于 d012/E 历史回放；最终 FD 对照包已另建并引用 v3 输入，仍待正式运行时回放。

| 配置 | 唯一改为 false 的键 | 回放结果 |
| --- | --- | ---: |
| default-lanes | `__isla_use_extra_ops` | 299/299 |
| default-vpr | `__isla_vector_vpr` | 184/184 |
| default-fpr | `__isla_vector_fpr` | 82/82 |

这些结果证明对照配置上的观察值符合预期。具体 default helper/寄存器分派 arm 仍需各自配置的动态 trace。

## 源码分母、不可达与迁移

[source-branch-catalog-d012.json](tools/solve_vector_coverage/source-branch-catalog-d012.json) 固定旧源码哈希，登记 22 execute clause 和显式选定的共享 guard/lane/寄存器 helper，共 59 函数、199 site、544 arm（95 if、77 match、27 loop）。这是**词法候选目录**，没有冒充编译器完整 CFG：inline 条件、短路因子、译码 mapping 和编译产生的分支最终以 R3 SourceLoc 目录为准。988 个输入义务也不能当成 988 个源码分支。

候选 arm 当前有 513 个待 case trace、4 个待对照配置 trace；27 个容器循环的零次迭代按合法固定长度登记不可达，并保留理由。各循环遍历完整元素/寄存器容器，VL0 控制活动或提前返回，不使容器长度为零；`VFMVSF` 从 1 开始的尾循环在 VLEN128、SEW≤64 下也至少迭代一次。需在最终 IR 长度约束与 site 绑定时复核这些声明。

其它固定配置约束见 [fixed-config-d012.json](tools/solve_vector_coverage/fixed-config-d012.json)：实际生成 JSON 和 IR 片段确认 `vector_support_level=Full`、VLEN128、ELEN64，`hartSupports` 的 Zve32f/Zve64f/Zve64d 条件静态成立，Zvfh/Zvfhmin 返回 true。其支持级别 false 分支需另生成不同模型 IR。运行时 FS/VS/misaF/misaD 禁用仍是可达条件，已分别测试。`misa[V]` 不是 Zve 浮点全部依赖的开关，不能把它清零伪称译码必拒绝。

普通 FP SEW8 的执行断言不能在真实编码下到达：encdec 已先拒绝；合法的 SEW8 转换另测。FLEN64 下合法 SEW16/32/64 的 `VFMVFS SEW>FLEN` 分支不可达。不可达均有配置边界，未静默删除分母。

生产 lane 改为纯 tuple/SMT ITE 后，重新生成独立 token 目录并保留旧目录；旧 site→新纯数据选择需链接等价证明，不能因为不再产生 executor branch 而删除旧义务。新 IR 与 trace runner 冻结后，本包负责三份配置的回放及实际 arm 关联，主集成负责 R1 域 2532 输入及完整 manifest；原始 2526 作为历史诊断保留。

## 可重现入口与剩余工作

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/guard_state.py \
  --output "$VECTOR_STAGE/inputs-final"
python3 agents/float_support_review/tools/solve_vector_coverage/reduction_hazards.py \
  --output "$VECTOR_STAGE/inputs-reduction-hazards/reduction-hazards.json"
python3 agents/float_support_review/tools/solve_vector_coverage/configure.py \
  --base "$IR_STAGE/rv64-e.toml" --output "$VECTOR_STAGE/configs-final"
python3 agents/float_support_review/tools/solve_vector_coverage/run_guard_state.py \
  --inputs "$VECTOR_STAGE/inputs-final" --output "$VECTOR_STAGE/results" \
  --ir-stage "$IR_STAGE" --decode-runner "$DECODE_RUNNER"
```

`run_guard_state.py` 还接受 `--config` 和 `--groups`，对照配置分组由 `alternate-configs.json` 记录。数值复现命令及 oracle 工具环境见数值报告。所有 2526 个基础 case ID 复算为 UTF-8 name 的 SHA-256 前 8 字节、big-endian u64，彼此唯一。

988 输入已重新生成并逐字节比较。唯一一次生成器可重现性修订是给 `legal-vd0` 的四条输入排序：原 set 迭代只影响行序，四条 case 内容和预期未变；确定化后单批重跑 4/4，证据 manifest 保留真实命令。初次数值归约 NX 预期错误的失败记录和修订依据保留在数值报告，未删改旧失败。

剩余：最终源码/IR 全量回放；R3 trace 的 site/arm 绑定；纯 lane 新旧映射与等价证明；以这些证据更新正式覆盖结论。旧审计追加案例、当前有限输入和官方 symbolic 完成性各自保留统计口径。

### 最终 trace 消费端准备

[catalog_v2.py](tools/solve_vector_coverage/catalog_v2.py) 增加 token 位置、1-based 展示列和 0-based UTF-8 `ir_column`、宏条件、22 个 encdec `when` guard、97 个 enum mapping arm、V 文件内数值 helper 与 rV/wV。同一行多个条件保持独立位置；`&`/`|` 保留待 typed IR 判别的候选，不把位串操作误认成短路分支。当前冻结源码目录为 [source-branch-catalog-final.json](tools/solve_vector_coverage/source-branch-catalog-final.json)：906 site、2391 arm，其中 SYMBOLIC 候选 695/1840，out-of-build 211/551，另有 73 个纯数据策略。目录哈希为 `fc3117925577ff161252b6f9e65ed59dee3f131a3e85ebb89b07a455dbc3d805`；这只是源码库存，须按每个 clause 的调用前提筛选义务。d012 目录不被覆盖。

初版冻结目录 788/2155（SHA `fcf65476…`）保存在 [source-branch-catalog-p2-initial.json](tools/solve_vector_coverage/source-branch-catalog-p2-initial.json)。复核发现返回 unit 的函数中，if/assert/Bool-let 语境短路只登记于 operator 候选而未进入控制 site；典型是 `write_vreg_default` 的第 470 行断言。本次补入这些项，已有 global site ID 不变。全部 325 个 operator 均保留台账：237 个活动 Bool 控制候选、45 个 out-of-build、43 个位串操作；后者在 d866 实际 sidecar 中逐项匹配 `and_bits/or_bits` typed primop，见 [operator-classification-d866.json](tools/solve_vector_coverage/operator-classification-d866.json)。分类证明不代表 Bool 因子已动态闭合。

与 scalar/BF16 采用共同键 `global_site_key={file,source_sha256,token_start_byte,token_end_byte,kind,subcondition_ordinal}`，按该字段顺序的紧凑 UTF-8 JSON（`ensure_ascii=false`）取 SHA-256 作为 `site_id`；byte 范围为半开区间。行列只作 `canonical_site_id` 展示。共享 helper 按这个键去重，各包的分母不能相加；non-SYMBOLIC 定义标 `out_of_build`，ITE/select 另存 `data_strategies`。原目录的 199/544 项由 [source_migration.py](tools/solve_vector_coverage/source_migration.py) 全部保留并列出当前控制/非 SYMBOLIC/数据策略候选，源码文本相似不当作等价证明。

短路候选的键统一为 `short_circuit_and/or`、物理 `&/|` token、`subcondition_ordinal=0`，不依赖各包如何分组外层 guard。最终迁移表 [source-migration-final.json](tools/solve_vector_coverage/source-migration-final.json) 保留旧 199/544：165 项有当前控制候选，34 项保留于 non-SYMBOLIC 并等待当前纯数据等价链接；没有把源码文本匹配当作闭合证明。

[clause_scopes.py](tools/solve_vector_coverage/clause_scopes.py) 建立 [22 clause 调用域](tools/solve_vector_coverage/clause-source-scopes-final.json)，按真实 encdec/execute 根登记调用位置、共享 site 和数据策略引用；`currentlyEnabled` 按声明的具体扩展参数匹配，V 的读写重载继续等待 typed IR 区分。每个 helper 的实际 arm 还需要调用前的 guard、enum 和循环前提，候选可达函数不等于其全部 arm 对所有 caller 都可达。另为 BF16 所有者提供[四个向量 clause 的共享引用](tools/solve_vector_coverage/bf16-shared-source-scopes-final.json)，不重复创建共享 site 或合计分母。

P2 IR `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9` 已成功生成，目录七个源码哈希与冻结 manifest 一致，见 [source-p2-binding.json](tools/solve_vector_coverage/source-p2-binding.json)。集成随后发现需要额外保留四个旧 helper，正在重生成完整 IR；d866 绑定与 sidecar 因此保留为阶段证据，不能冒充最终完整 IR。

补充四个 helper 后完整 IR 已生成：`c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c`，七个源码哈希未变。三份 FD 对照配置在 P2 运行时 `128d59a5…` 下的实际目录均为 2068 函数、380542 指令、25950 Jump；提取前逐一复核 manifest 中 510 个运行时文件、extractor 源码与二进制哈希。随后集成确认还有 MixedBits 运行时修复待独审，这组三目录因此明确保留为该修复之前的阶段证据；正式 trace 仍须等待新运行时冻结后重抽与双向核对。

[static_domains.py](tools/solve_vector_coverage/static_domains.py) 生成[最终源码的静态域候选](tools/solve_vector_coverage/static-domain-candidates-final.json)：29 个活动 loop site 中，27 个按固定正容器长度排除零迭代；另外两个 SEW8 fallback loop 只有 raw execute 可达，真实 word decoder 的转换 enum 限制排除整循环。还列出 `valid_fp_op` 宽度条件、VLEN128 的 assert 分派与 FLEN64 的前提。每项仍要求独立审核、逐 caller 域和最终 IR/config 绑定，不使用 VL0 伪造空容器，也不批量宣布共享 helper 全部分支可达或已闭合。

[short_circuit_candidates.py](tools/solve_vector_coverage/short_circuit_candidates.py) 从实际 Bool Jump、短路常量和 RHS 同目标写回建立 237 个因子的 495 组 lowering 候选；最小 SourceLoc 区间仅负责定位。[short_circuit_cfg.py](tools/solve_vector_coverage/short_circuit_cfg.py) 进一步核对源码 Bool 根和左右操作数 token、全部到达定义、短路与 RHS 的正常 CFG 写回路径；异常退出和无法证明的关系保留 unresolved。形状或 CFG 检查均不代替实际 case 的源码 arm witness。

[lowering_candidates.py](tools/solve_vector_coverage/lowering_candidates.py) 复用 scalar 的实际 SharedState AST/CFG 检查器，并为向量 match 提供每臂真实 body 区间。初版 622 个 SYMBOLIC 候选 site 中，266 项具有直接 if、match 或 assert 的初步形状匹配；没有真实 trace 参数时明确标 `actual_trace_catalog_verified=false`，仍待架构复核与 clause 调用域 witness。补充 Bool 因子及最终完整 IR 后须重新生成；`short_circuit` 和 `foreach` 没有借此自动闭合。

[typed_calls.py](tools/solve_vector_coverage/typed_calls.py) 对共享 V 读写语法逐项核实际 `Call`：23 个调用均按精确 SourceLoc 起点唯一绑定到 `get_V_bits/set_V_bits`，未选择 vregno 接口。分派条件的实际 Jump 与后继 Call 另列为待核 CFG；函数存在或源码位置吻合不代表调用已执行。三种对照配置也已各自提取同 `official-fork`、Optimistic、model-init=true 的目录，均含 2064 函数、380188 条指令、25944 Jump；版本、配置、extractor 与 sidecar 哈希见 [runtime-sidecars-p2.json](tools/solve_vector_coverage/runtime-sidecars-p2.json)，仍待与最终 runner 的实际 trace Jump 全集双向核对。

[loop_witnesses.py](tools/solve_vector_coverage/loop_witnesses.py)补充[29 个循环结构及有序见证](../../isla/target/float-support-review/final-coverage/vector/loop-structure-and-witnesses.json)，SHA `c69ae41e2b19c3a7fd002c6c824f7f4f71daa3c97492063513fe982728abcb21`：核对 typed `Gt(index,last)`、初值 0（VFMVSF 为 1）、步长 1、唯一递增/回边、长度减一及转换链；对函数末尾 assert handler 回入另核全前驱来自本循环。消费已审默认 baseline/enum-sew 与 default-lanes baseline，按 header true 拆分同 context 的调用实例，共 139 个 enter、129 个 continue、139 个 exit 的配置/clause/context 见证，覆盖 27 site。未观察的旧 VFW pc27177/VFN pc28169 受已独审 outer=false 控制。该产物仍待独立审查及 caller 长度域绑定；没有据未观察而排除 zero_iterations，也未把结构对应算成全部 29 个源码循环闭合。

后续 [v2 循环见证](../../isla/target/float-support-review/final-coverage/vector/loop-structure-and-witnesses-v2.json)，SHA `57689d641ef515de985916b578352070d9023cea9eb075296f12a57ceb237683`增加已有 default-lanes `legal-lmul` 的严格 trace，得到 **139 enter、138 continue、139 exit、27 site**。[最终独审证书](../../isla/target/float-support-review/final-coverage/vector/independent-loop-review/certificate.json) SHA `9fee8e68312bbe784bf68b5874723f423c3f781af89511ffcad267fab2caa183`通过全部 29 个结构、正长度域、有符号 64 位转换/增量安全，以及 99 个 helper context 的实际 root→Call→形参绑定；五项篡改负控均拒绝。九个 writer 的 continue 已由 v2 补齐，唯一 `VFMVSF` root31547 的 writer group 长度恒为 1，保留明确 caller 域排除。独审还记录共享 runtime_binding 的旧/新来源哈希及实际依赖函数 AST 同形证明，未绕过依赖变更。

[严格消费器](tools/solve_vector_coverage/consume_loop_review.py)核对候选、证书、依赖、源码 key、全部 trace 文件哈希及逐项 witness 后，建立[循环 context 账本](../../isla/target/float-support-review/final-coverage/vector/loop-reviewed-context-ledger.json)，SHA `60618004ed5ee0bc107820b938c7626c1fb104cf7a52e00c537ae3f2d243f928`。139 个列定 context 形成 556 条义务：416 个有序见证、139 个正长度 zero 排除、上述 1 个 continue 排除；默认 FD 的两个 outer 不可达循环再形成 8 个 arm 排除，总计 564。该账本未枚举全部可达 caller/config，不改变旧 14095 前沿或其 285 待核数，也不移用于新 `348147`。

[loop_contracts.py](tools/solve_vector_coverage/loop_contracts.py)将该账本导出为[141 个源码/caller/config 合同](../../isla/target/float-support-review/final-coverage/vector/loop-source-caller-contracts.json)，SHA `a7e69115a33abc84392282fad9247ab858f8a752c0948083d9f5d885094695af`。保存长度项及完整保守域、初值/步长、四 arm 时序语义、vtype 无写和外层不可达前提，旧 PC/context/见证置于 `historical_binding`；新 IR 必须重新定位源码/typed loop、核实际实参链、配置、长度安全与完整有序 trace。

[slide 两条输入](../../isla/target/float-support-review/final-coverage/vector/slide-two-lanes2-inputs/suites.json)已准备，manifest SHA `3be8407296c8af7779cf14da132394de8e7fbd6cf0d16d9edef28acc02895b95`。VL2 的独立纯位串预期为 slide1up `[scalar,source0]`、slide1down `[source1,scalar]`，保留 vta0 尾元素；目标为 zexecute pc29872=false 和 pc29899=true。因集成先冻结 9583 条输入做新 IR 全族复验，本两条尚未运行，不计上述结果总数。

[枚举编码表工具](tools/solve_vector_coverage/enum_mapping_tables.py)进一步准备[18 个 mapping 的完整 typed 表对应](../../isla/target/float-support-review/final-coverage/vector/enum-mapping18-lowering-candidate.json)，SHA `9df8e1b84996d3ec9de5dc48dd6a4d1dfa4324bd82a82fff68a2b1bf2b499854`。每个表核对冻结源码、真实 IR enum 全域、五种生成函数及所有 typed Call 来源；90 个函数共 2339 次有限解释逐返回与源码位串表相同。正常 backwards 的非法输入为 MatchFailure、matches 为 false；backwards_infallible 仅证明匹配域，其 caller 前提继续保留。它是静态 lowering 候选，不算新增动态 case，也尚未通过独立审查。

该候选随后通过[独立原始文本 IR 审查](../../isla/target/float-support-review/final-coverage/vector/independent-enum-mapping-review/review.json)，SHA `c5997339b01099c5eb8d41dacb9e92ef19273342d560180a8b8c0c3303c6d918`：18 张整表共 97 成员、90 函数/4599 PC、2339 次解释及 path/edge 对照；1024 个反向输入中 927 个非法值为 MatchFailure。另核全部 36 个 backwards_infallible caller：同一实参先匹配、定义支配，matcher=false 或跳过均不能到 value Call；六项负控拒绝，producer 逐字节复跑相同。[严格消费器](tools/solve_vector_coverage/consume_mapping_review.py)逐表、域和 caller 双射后产出[18 个可复用合同](../../isla/target/float-support-review/final-coverage/vector/enum-mapping18-reviewed-contracts.json)，SHA `89ce11af08fa7ee7866594e0bb34903bc61b8c7901145178dd38ff172b4d05a2`。本结论仅限旧 `1dcc` 默认配置，不新增动态 case，不继承到新 IR。

loop/mapping 消费端另做[七项独立篡改负控](../../isla/target/float-support-review/final-coverage/vector/contract-consumption-negative-controls/report.json)，SHA `04ac8f4c802570f6b4e4f6f9d632253ffa9cd44bf123ff2f9c9ca14fb4347335`：错源码 token、未证 zero 排除、假长度一排除、缺 caller、无 matcher guard、错表值及跨 IR 升级全部在创建输出前拒绝。encode21 消费端的反向 taken、错 global key 和跨 IR 三项负控也全部拒绝。

[转换禁 FS 六条输入](../../isla/target/float-support-review/final-coverage/vector/conversion-fs-off6-inputs/suites.json) manifest SHA `b8f111a7c167d39951a3ad82dc61adabbc80008180242291e0e108b293d2b0a0` 同样只准备未执行。六个 enum 代表分别覆盖 widened/narrowed helper 的剩余 15 个 decode LHS=false 候选；另 21 个 encode 同类方向已由上文旧版本 encode21 独审消费，仍不升级为新 IR 证据。

[trace_frontier.py](tools/solve_vector_coverage/trace_frontier.py) 复用共享 `solve_replay/audit.py` 的 R3 parser，检查输入与结果、稳定输入 ID、各阶段 terminal 数、唯一终态账本双向关联、实际 Jump 后继和 SourceLoc；输出已观察方向及缺失方向。它只按选定函数范围筛选运行时目录。`taken` 是实际 Jump 方向，不能直接当作源码 if 的 true 或某个 match arm；输出恒保留 `source_branch_closed=false`，等待 lowering、纯 ITE 等价或静态配置证明。

消费端检查已用合成 fixture 验证：错误后继、末尾截断、未知 case、错误终态及重复账本均被拒绝。该检查证明脚本接受边界，不代表真实指令已完成 trace 绑定。最终 run manifest 还必须固定 IR、配置、runner、source、trace 与 trace-map 哈希。

另以集成方已有 scalar 实际 smoke trace 验证终态协议：两个 `decoded`、一个 `encoded`、一个 `retire` 的唯一终态账本与 trace 双向一致。该 smoke 的 IR/状态不属于此向量最终回放，不能作为向量 source-arm 证据；它只验证消费端正确接受真实 runner 的 phase/status 及相对 `extensions/V/...` SourceLoc 格式。

初版准备阶段发现 R3 文本没有 `terminal_ordinal`，而按输入复用 `case_id` 会使同一 case/phase 多个 callback 无法唯一关联。主 agent 随后批准并由集成负责人修订合同：输入 ID 保持原规则；每个 callback 的 `terminal_case_id` 为 `SHA256(name + NUL + phase + NUL + decimal ordinal)` 前 8 字节 big-endian u64，R3 metadata 的 `case_id` 使用此终态 ID；结果和 trace-map 保存 input_name/input_case_id/phase/ordinal→terminal_case_id。消费端已切换新合同，强制拒绝重复 `(scope,terminal_case_id)`、错误哈希和采样，逐项核对 trace 与账本的唯一终态集合；不使用 path_signature 或文件顺序消歧。真实 final runner/IR 回放仍待执行。

### c5 接续复核与最小下一批

本节更新上述准备阶段的待执行状态，不改写 d012、d866、旧 P2 sidecar 或旧 runner 的历史结论。接续产物 basename 为 `isla-vector-final-directed-20260926`；`results/` 是结果，`trace-audits/` 是已有逐组 R3 审计。IR 为 `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c`，源码目录仍为 `fc311792…`。

| FD 对照配置 | 结果数 | 唯一终态数 | 已观察 scoped Jump 方向 | 结果 summary SHA-256 |
| --- | ---: | ---: | ---: | --- |
| default-lanes | 299 | 897 | 1001 | `1580c0a68a144ebfdfb9d994fff213beada7744be73f53f0fab048ef0b033981` |
| default-vpr | 184 | 552 | 991 | `9dae2bcf012a0491328add3fb6cf07955b57b5c28c0001e7c454a0277c5e5fd4` |
| default-fpr | 82 | 246 | 872 | `b51caebaef1f680f8e2158554a54a4ef4db878e7485fdf031c7838d6bdc34548` |

565 是 case×配置结果数，输入有重复；方向数也不能跨配置相加作为源码分母。三份 summary 的成功 runner SHA 相同，为 `229913d16fb182799da55109b1d8242cb99961d141aeeb9aac08373b03188760`；运行时 manifest 为 `6e00edd8ec17b627edcbfcd14dcdd50b4f3e6cd0ffeb11ca5343cf71a58fa084`。完整配置、runner、sidecar、输入、结果、trace、trace-map 及逐组审计哈希保存在[接续证据清单](tools/solve_vector_coverage/evidence-c5-resume.json)。

[resume_evidence.py](tools/solve_vector_coverage/resume_evidence.py) 已重新计算 14 组上述文件的哈希，核对输入/结果条数、SAT/差异 UNSAT/结构标志、trace-map 与结果内账本相等，以及原审计的唯一终态数和全 Jump 绑定。**复核 PASS 只指保存证据完整且仍匹配原版本**；本轮没有重跑 565 条或重新制造通过结论。清单显式写 `actual_R1_gate_verified=false`、`source_branch_closed=false`。

v4 状态域迁移 manifest 为 `30d7b3cb22be8818f4236815d34b31ae9d1ace21083101ade3e7b7cf1a318992`，basename 为 `isla-vector-r1-fd-v4-domains-20260926`。清单复算并核对默认 2501、合法 F-off 22、合法 D-off 9、raw-invalid-misa 31；旧原始输入没有被覆盖。`smoke-v2-results` 中 F-off/D-off 各一例的 runner 返回 0，但旧汇总器把译码路径数硬编码为 2，因此 summary 保留原 `FAIL`。公共汇总器已改为守恒校验；这两条仍待新 R1 runner 复验，不能静默把旧 summary 改成 PASS。

#### Typed 调用与短路独审

[review_frontier.py](tools/solve_vector_coverage/review_frontier.py) 及[紧凑关联清单](tools/solve_vector_coverage/source-frontier-c5-resume.json) 对每个 global key 重新计算 SHA，检查冻结源码七个哈希，重新用实际 `default-vpr` sidecar 生成 typed/短路候选，并逐项核对三配置相关 Jump 的函数、PC、后继、SourceLoc 和按符号名规范化的完整指令；实际 trace 目录已由对应原审计绑定，不能用旧编译器 PC 直接拼接。

- 23 个 `V(...)` 语法调用均唯一绑定 `get_V_bits/set_V_bits`。`get_V` 未保留于该 IR；`set_V` 虽存在，但三份 trace 都未执行它。函数存在和 typed Call 存在只解决类型解析，不能充当实际调用证明。
- `read_vreg/write_vreg` 的配置 Jump 为 pc0，`false` 直接进入 default Call，`true` 进入 extra Call；`get_V_bits/set_V_bits` 的 pc0 是实际 `__isla_vector_vpr` Bool。普通 VPR arm 与快速 VPR arm 都有旧 runner 的实际方向证据。这个极性是按条件符号、源码和后继逐项确认，不能推广成所有 `taken=true` 都是源码 true。
- 普通 lowering 保持 **695 活动 site / 338 有候选**：133 个 if 仍待谓词/主体极性复核，127 个 match 为同 subject mismatch 链及末臂结构检查，78 个 assert 为实际转换后 handler 检查。vector 目录未提供 `if_regions`，因此共享检查器没有为这些 if 自动证明 then/else 主体；不能把候选的 true/false 标签当成已验收极性。
- 短路 **237 源码因子 / 495 编译 lowering 实例**全部通过既有词法根、LHS 到达定义、短路常量和正常 RHS→join 写回检查。按三份 trace 合并观察，**49 实例双向、209 单向、237 无方向**。该数字仅为 runtime frontier，不是源码覆盖率；一个源码因子可能被多个译码函数展开。
- 162 个 lowering 含 `have_exception=true` 后经 Goto 到 `Arbitrary` 的路径，当前检查将其记录为独立异常出口。正常 Bool 路径检查通过不意味着这些异常义务闭合。`valid_fp_op.valid_sew` 的局部 let 及 `recip7.sub` 的形式参数使用显式名字绑定，仍需各 caller 的前置条件。

短路工具新增 `--model-root`，从 c5 `model/` 冻结目录读取源码并保留逐文件 SHA 断言。它只让旧证据可准确复核，不把当前 min/max 改动生成到旧库存。外部中间文件在 `isla-vector-audit-resume-20260926`，对应哈希已被关联清单收录。

#### 最紧 shared helper 缺口与 12 条候选

`valid_reg_overlap` 的 c5 源码位于 `vext_utils_insts.sail:71`。三份旧 trace 均未观察源对齐失败的 pc52=true、总对齐失败早返的 pc68=true；加宽重叠末端比较 pc131=false 也未观察。已有 default-lanes 的合法 overlap 能到 pc131=true，但末尾 `EMUL_pow_rs >= 0` 是普通 Bool 返回，**没有可凭空补记的 Jump**。同理，窄化第二个范围条件返回 false 要绑定 RHS 值和 caller 拒绝 guard。

[frontier_batch.py](tools/solve_vector_coverage/frontier_batch.py) 已从现有包选出 12 条，保持输入名字、ID、状态和独立预期：源/目标对齐各一条、加宽低位重叠一条、窄化高位重叠一条，再加原 8 条 fractional overlap，覆盖六个加宽 clause 的八个调用位置。产物 basename 为 `isla-vector-frontier-12-20260926`，manifest SHA 为 `b6ebb77ed69731610f8682a67b6ea90a4f0617ee62295da60982ba911bf5dd7f`；`selection.json` 逐例记录来源哈希及目标。**仅选样，尚未执行。**这是第一个最小缺口批，不承诺闭合其它 guard、enum、数值 helper 或全部 caller。

pc78=false 对应 `EMUL_pow_rs == EMUL_pow_rd`；本 22 clause 的实际 overlap 调用以 `LMUL_pow` 和 `LMUL_pow+1` 作为两端，故它应按 caller 域另列不可达证明候选。该结论不覆盖共享 helper 的其它调用者，更不能据此全局删掉源码 arm。新 freeze 后先迁移源 token/IR 绑定，再运行上述 12 条；按 trace 结果决定下一批，禁止把数值样本数替代源码分支账本。

另一个新冻结义务是 `vext_arith_insts.sail` 的 `encdec_nreg/vext_vs1` matches 纯 Bool 改写。当前七文件目录不含该文件；应从真实 decoder typed Call 域补共享引用及独立 32 输入/未知输入等价证明，保留旧 Jump→纯表达式迁移记录，不能把整个文件词法库存加入 22 clause 的分母。该证明由架构协作者交付，本包尚未验收。

工具核对还包括：六个修改/新增 Python 文件通过语法解析，本文本地链接可解析；12 条输入、manifest 和来源记录可逐字节重生成。负向检查使用已变化的工作树源码配 c5 目录，工具在 SHA 断言处拒绝且不生成结果，未绕过冻结来源检查。

接续之后，[audit_suite.py](tools/solve_vector_coverage/audit_suite.py) 已接入公共 [entry_contract.py](tools/solve_fix_integration/entry_contract.py)：运行摘要、实际 runtime manifest 与 sidecar header 的 runtime SHA 必须相等；每组真实命令须绑定 runner/IR/config/输入/结果/trace，初始化侧车及 trace-map 的 SHA 均为必需字段。随后按实际 `entry_mode/state_domain` 调用公共初始化校验，核完整四字段 R1、Target 源哈希、初始化 lets 摘要及逐例状态域证明。源码与 runtime 使用共同冻结 manifest 或独立双 manifest 的结构由共享 `verify_source_snapshot` 核验，本消费端不添加另一套来源格式。

消费端[九项接线与篡改负控制](tools/solve_vector_coverage/test_audit_suite.py)通过，命令为 `python3 -m unittest discover -s agents/float_support_review/tools/solve_vector_coverage -p test_audit_suite.py -v`。真实旧 c5 `default-vpr` summary 因缺少 runtime 绑定在读取 trace/创建输出前被拒绝，拒绝记录 basename 为 `isla-vector-gate-audit-_b2q0lia`。新入口只有全部门槛成立才输出 `actual_R1_gate_verified=true`；这次实现和消费端检查没有执行新指令批，也没有把上文旧 565 条证据升级。

复核命令如下；变量指向上述 basename 的真实目录，命令没有执行指令回放：

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/resume_evidence.py \
  --directed-stage "$DIRECTED_STAGE" --alternate-stage "$ALTERNATE_STAGE" \
  --domain-stage "$DOMAIN_STAGE" \
  --catalog agents/float_support_review/tools/solve_vector_coverage/source-branch-catalog-final.json \
  --output "$AUDIT_STAGE/evidence-c5-resume.json"
python3 agents/float_support_review/tools/solve_vector_coverage/frontier_batch.py \
  --domain-stage "$DOMAIN_STAGE" --fractional-stage "$FRACTIONAL_STAGE" \
  --output "$NEW_FRONTIER_STAGE"
```
