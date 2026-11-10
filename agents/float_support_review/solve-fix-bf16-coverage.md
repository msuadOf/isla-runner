# BF16 六项 clause 的分支与状态补验

2026-09-26。用户已授权将浮点审计中的缺口逐项修复、调通。本工作包按主agent分工补充可复现定向测试；既有发现与首次71条、随后38条清flags证据见 [BF16审计](solve-audit-bf16.md)。本文与 `tools/solve_bf16_coverage/` 独占维护，生产BF16汇编映射由另一负责人修改，本包不改生产源码、旧输入或独立内存worktree。

## 验收范围与当前状态

范围为 `FCVT_BF16_S`、`FCVT_S_BF16`、`VFNCVTBF16_F_F_W`、`VFWCVTBF16_F_F_V`、`VFWMACCBF16_VV`、`VFWMACCBF16_VF`。按源码条件分别登记译码拒绝、执行Illegal、成功数值/flags和向量写回；保留固定配置中不可达分支的说明。输入具体化的分支触达不构成所有位串输入等价证明。

初始阶段基线IR SHA-256为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，XLEN64/VLEN128/ELEN64。该阶段成功与非法runner复用既有E接口；NaN/舍入/flags预期由独立 [SoftFloat oracle](oracle/README.md) 与架构寄存器/掩码规则生成。测试包实施与最终批次结果在下文持续记录；未实际执行的格不写PASS，各新版均独立复跑同输入。

**2026-09-27 现行摘要**：56cc69 新候选的 942 输入／2754 终态严格审计通过，另三条 overlap 增量／九终态通过；18 格 actual privilege 已核。新版保留短路RHS账现为 **139条实际见证＋23条caller域排除＋24条正常phase条件排除**，逐项保留适用范围及域外未决；三条增量另签三个LHS=true/RHS跳过方向。旧1dcc正常RHS为175 actual、22入口排除、29静态条件排除，40异常另有条件排除，不迁到新版。五个改写site的40旧控制已独审消退，多对一关联 **8个已审限定域callee-instance集成合同**；40条历史链接均为 `legacy_transformation_discharged`，严格Bool中间值不算新branch，原pending40只保留历史标签。phase完整闭包纯读FAIL保留，正常End的窄范围状态合同已按前提联立。无条件全源码排除为0，源码分支尚未闭合。

BF8现行依赖复核入口为 `v4-value-integration-reviewed-v2.json`：按正式独审许可将15个历史活动模型locator固定到同SHA快照，语义合同与v1全等。v1及原producer字节冻结，原路径强验命令保留为历史；详见文末依赖重定位附录。

## BF16乘积与融合运算的可辨识性

BF16普通有限值最多8位有效数，两个操作数的精确乘积最多16位有效数，小于f32的24位。因此，当乘积为有限f32正规数，或为能精确落在f32次正规网格上的值时，`fma(a,b,c)` 与先精确乘法再加法无法用一般尾数中点区分。次正规区的固定间距为`2^-149`，仅看“乘积大小在有限范围内”并不足以断定精确。旧 `1 + 1×2^-24` 中点样例只验证最终加法的舍入路由。

但BF16和f32具有相同的指数位宽，乘积可能超出f32指数范围或小到不能精确表示。融合运算保留未舍入的乘积直至与累加器相加，这两类输入可区分融合与分步运算。以下由独立oracle分别执行f32 FMA及f32 MUL→ADD、合并两步flags，已确认五种RM均可辨识：

| BF16乘数与f32累加器 | 融合结果 | 分步结果 | 检查意义 |
| --- | --- | --- | --- |
| a=b=`0x5f80`=`2^64`，c=`0xff7fffff`=`−max_f32` | 所有RM均为 `0x73800000`=`2^104`，flags0 | RNE/RUP/RMM为+inf；RTZ为+0；RDN为−0，均OF\|NX | 未舍入乘积 `2^128` 与大负累加器抵消；结果位与flags都可区分 |
| a=b=`0x1780`=`2^-80`，c=`0x3f800000`=1 | RUP为`0x3f800001`，其余RM为`0x3f800000`；均只有NX | 同样结果位，但两步累计UF\|NX | 极小乘积 `2^-160` 在融合后结果非tiny；额外UF可区分 |

两个类别都进入VF/VV五RM定向测试，保存oracle调用与结果，不强造普通精确乘积的尾数双舍入反例。前置探针在仓库外 `isla-bf16-fused-probe-f8boqpkj` 以原乘加RM输入为模板跑20例，d012下exit0、20条完成结果均通过，原始命令/输入/oracle输出/runner日志均保留；该探针只观察原模板的首个目的寄存器，最终测试包另扩大到完整目的组。

## 覆盖设计

| 类别 | 本包具体要求 |
| --- | --- |
| 标量RM | 静态0–4、动态FRM0–4；静态5/6译码拒绝；动态5/6/7执行Illegal且观察状态保持 |
| 向量guard | 四clause的SEW8/32/64译码拒绝；misa.F/FS/VS关闭拒绝；vill、vm0且vd0、m8扩宽EMUL16、源/目的失对齐及非法重叠、vstart超界 |
| 分支可达性 | `hartSupports(Zfbfmin/Zvfbfmin/Zvfbfwma)`在固定IR为生成配置常量；其false分支不伪称动态覆盖。`Fcsr_RM_Fatal`同样不属于当前Illegal配置的可达分支 |
| 合法寄存器布局 | SEW16合法fractional/m1/m2/m4；允许的窄化低端重叠、扩宽高端重叠；观察完整目的组，不止首个寄存器 |
| 活动状态 | vl0、全mask、部分mask、vstart=vl、合法vstart>vl、跳过sNaN前缀、首次活动lane非零时scalar sNaN；vta/vma四组合及尾部 |
| 标量boxing | f32和BF16正确boxing；未boxed有限数及低位sNaN均按对应格式canonical qNaN处理；完整FPR写回和五flags |
| 转换数值 | ±0/inf/qNaN/sNaN、精确/不精确有限数、奇偶中点、最小/最大次正规、最小正规、OF/UF边界邻点；窄化五RM |
| 乘加数值 | 两个BF16源及f32累加器分别NaN、q/sNaN组合、0×inf、无穷乘积加反号无穷、正负零、OF/UF、上述融合辨识例；旧flags0与非零分别观察 |
| 历史回归 | 原38条清flags及LMUL10从仓内源输入可重建，不能依赖临时目录作为唯一测试定义 |

`misa.V=0`的预期不能照搬`Ext_V`：当前 [vext_control.sail](../../sail-riscv/model/extensions/V/vext_control.sail) 的`currentlyEnabled(Ext_Zve32x)`不检查misa.V，源码明确标注此交互待定。BF16通过Zve32f/Zve32x依赖链，所以本包记录清V位仍可执行的当前行为，关闭VS才是已定义的拒绝分支；不将该既有扩展交互边界静默改成另一种语义。

canonical vill状态为仅最高位置1、其余位0、vl0；其SEW解读为8，BF16真实decoder先因SEW guard拒绝。注入`vill|0x8`虽可到达execute的`valid_vtype=false`，但不是正常vset/CSR可产生的状态，不能计入架构可达分支。固定E配置中`__isla_use_extra_ops`与`__isla_vector_fpr`为true，相关false臂单列为该配置不可达；执行前初始化绑定及该路径无开关写回由共享trace核对，FPR普通/快速入口等价另由生产修复专项验证。

## FS/SD修复引起的预期迁移

本轮另一生产负责人修复SYMBOLIC FPR写回未调用`dirty_fd_context`的问题。旧d012若标量转换没有新增flags，旧定向输入可能预期SD仍为0；修复后写目的FPR本身就必须标记FS Dirty并置SD，不能继续沿用该旧预期。

历史输入副本迁移规则只作用于成功的两项标量转换：`expected.mstatus |= (3<<13) | (1<<63)`，理由为FPR写回调用`dirty_fd_context`。初态、数值、fflags及其他观察项保持不变；Illegal和Decode_Illegal不迁移。BF16旧向量样例本已因目的写回置VS/SD，新增flags的FS更新也已在原预期体现，无需按此标量规则调整。迁移必须逐case保留old→new，不以新模型输出生成预期。

新建成功样例可另采用FS/VS/SD相互一致的初态FS=Clean、VS=Clean、SD=0（`mstatus=0x4400`），以独立观察状态变化：标量写FPR后为`0x8000000000006400`；向量写回但无新增flags时为`0x8000000000004600`；累计flags确有新增位时还将FS置Dirty，结果为`0x8000000000006600`。这一新profile不改写历史输入；d012基线和修复IR的预期分开记录。这里核对的是所测Machine模式下FS/VS/SD规则，不宣称任意未使用CSR字段都经过整机reset或WARL可达性证明。

## 实施与验证记录

实施入口已完成：[生成器](tools/solve_bf16_coverage/generate.py)、[运行器](tools/solve_bf16_coverage/run.py)、[使用说明](tools/solve_bf16_coverage/README.md)。两入口均要求仓库外的新目录或空目录，避免覆盖旧证据；`--oracle` 显式指定已构建的独立参考程序。生成器从仓内五个既有输入重建清flags38例，重建SHA-256仍为 `e42f74d7c947a59e38d70d3e06290b0b4f3ffe47bdebcf0e3191727bea67d616`，与首次清flags批一致；LMUL10例同样来自仓内固定输入。原输入没有改写。

阶段766条成功样例的记录仍保留于仓库外 `solve-bf16-coverage-baseline`，只作为建设阶段快照。完整v3基线已扩大到898条并全部通过；受测产物在 `solve-bf16-coverage-full-v3-20260926`，`summary.json` SHA-256为 `a9a24d634ce90ee437ff8644c302b258f5278b000775b7ef5bbeceac8733c003`。本审计又独立核对每条输入/输出名称、预期字典、SAT、全观察集差异UNSAT、结构标志、字段及观察寄存器位值；真实译码各两条遍历路径，成功与execute Illegal各一条encode和execute路径，decode Illegal无encode/execute。

| v3批次 | 条数 | 退出 | 秒 | 输入SHA-256 | 结果SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| 成功状态 | 811 | 0 | 56.349 | `602b950aa9b8b2555c3dd9647b78c5b6c885645362f815c4cf5f22da3b561da9` | `718639b9f415f1cff5f798844179f5eed31d8f91181b8ddd404c94d2ed5a2d31` |
| execute Illegal | 51 | 0 | 7.678 | `111e617d559990146661d54c2b26214457395ccd7be21924013b904ab799a580` | `de7401aa8adde983784ababf3e16afbdb038f7801811e42eae24ebd47c43f0e0` |
| 真实decode Illegal | 36 | 0 | 6.619 | `913a85858b53c6154c646264a3d72886e8535f77f544826156e360f4356a1721` | `8af63b86845875c17c8a682464c593e6ae571000d8876c047c100c4a8f5e9c96` |

该次运行使用d012 IR及config `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`；三个runner分别为 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`、`e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3`、`7b3a086e208527ea2a0e4fe7c3cfa527be553f795177bd52377573aaaa259f89`。oracle为 `0bb63bc72889502ef6a36cb739589745987a0788eb73d57e0570815a3c228bc6`。实际命令形式如下，证据中保存展开后的完整argv及全部输入/结果/日志哈希；外部目录basename分别为 `isla-float-ir-final-20260926.q1Auj4`、`isla-float-e-scalar-20260926`、`isla-float-oracle-build`：

```sh
python3 agents/float_support_review/tools/solve_bf16_coverage/run.py \
  --stage "$STAGE" \
  --decode-runner "$E_SCALAR/negative-target/debug/isla-float-e-illegal-runner" \
  --oracle "$ORACLE_BUILD/oracle" --profile baseline --out "$OUT"
```

811条成功例含清flags38、旧LMUL成功2、vl0合法LMUL20、policy48、允许重叠4、首个活动lane非零2、活动重叠5、向量源非活动sNaN40、静态/负静态/动态RM20、未boxed标量4与VF2、清misa.V4、窄化410、扩宽32、FMA160、活动VLMAX完整目的组20。51条执行非法为旧LMUL8、guard20、保留FRM18、对齐/重叠5；36条译码拒绝为vill4（v5实际vl1，官方域更正见后文）、错误SEW12、保留静态RM4、扩展/FS/VS依赖16。

final profile仅迁移旧清flags38中的14条成功标量记录，其中12条old/new相同，两条qNaN例新增SD；迁移JSON保留名称、稳定u64 case-id、前后值和理由。新例以Clean FS/VS初态检验修复；FS-off为 `0x400`，VS-off为 `0x4000`。旧d012的 `unboxed_scalar__FCVT_S_BF16_finite` 已用final预期得到明确红例：f3与fcsr一致，实测mstatus仍为 `0x4400`，应为 `0x8000000000006400`，差异查询SAT，exit101。证据在 `solve-bf16-coverage-final-red-20260926`，stderr SHA-256 `88204dd51994cae9682c2b9a58e69f1e0eb083c610529467d15005368c3a36d7`。新IR须重新运行final，不转记baseline通过。

最终审阅另补无活动lane的VF标量sNaN8条与VF/VV累加器sNaN16条；各测 `vl=0`、全mask、非零 `vstart=vl`、`vstart>vl`，旧flags分别0/1，完整观察两个目的寄存器。后者用于独立检查新SYMBOLIC实现先计算FMA时产生的 `op_flags.NV` 是否被活动mask屏蔽；只有BF16源sNaN的用例通常在转换时产生NV、随后以qNaN进入FMA，不能替代这项观察。

新增24条在同一d012/config/成功runner独立复跑全部PASS，exit0、7.783s，逐条再核结果/flags、字段及路径。证据目录为 `solve-bf16-inactive-review-20260926-wpnlki47`，`summary.json` SHA-256 `2e6b04bac6a23b64fd158b04cd483accb0ebb80ea39405438d2056bf71f7dfa6`；输入SHA-256 `41fd5a69287948ea1020c5198cf50628f84b1359ee7eaa48b7f7065fb98910ff`，结果SHA-256 `372db71e5cfa04ea10ad22f4ea61e11572eb552257b5399046e28315113d3789`。命令为上述成功runner直接接受同IR/config、追加24的JSON和结果路径，完整argv保存在summary。

最终v5生成器SHA-256为 `3d9d06d87375fb3b2a29c852ec3b72181f90f91f1965256917d483474dab81b7`。已独立核对旧898条按名称和完整JSON逐项不变，922个稳定case-id无碰撞、跨profile一致；历史14条迁移记录采用名称与u64 ID共同绑定。基线835成功+51执行非法+36译码拒绝的结论由完整v3的898条及新增24条组成，没有伪称同一命令重跑了整个922条。最终输入在 `solve-bf16-coverage-baseline-v5-final-20260926` 与 `solve-bf16-coverage-final-v5-final-20260926`。

| 最终输入 | baseline SHA-256 | final SHA-256 |
| --- | --- | --- |
| `success.json`（835） | `abc3bc1cb1ca6050045a923b806e29b61f778a3b5a84e08bfef98ab9f0ef66e2` | `af24a3ab879273558cfcbc3802fb9ecea89ae64e1bfaf052c31555e8f625fed9` |
| `illegal.json`（51） | `111e617d559990146661d54c2b26214457395ccd7be21924013b904ab799a580` | `2c461426bb11514c0b4ceefa0ffc331690bc92b03f3b48fc930dea1dc3bb9101` |
| `decode.json`（36） | `913a85858b53c6154c646264a3d72886e8535f77f544826156e360f4356a1721` | `efea0aff89047c71c086fe9dc011c2683d84ee51c176e5472c4142f67227279e` |
| `coverage.json` | `4d3b87bbc443ecc4a7bf6cef9915f82cd7ad3533540c08233691fe55e4809c63` | `f634db5b68a70b5f3fe22c958be8fcbc1feaa0508948af280b54170d77819951` |

新IR与R3 trace集成负责人已接收最终v5输入；当前final整体状态为待复验。

按照本轮统一分支口径，coverage映射登记稳定case-id、源码文件/site和预期arm；`case_id = int.from_bytes(SHA256(name UTF-8)[:8], "big")`，全包无碰撞且baseline/final同名同ID。该映射是覆盖意图，不是实际PC证据；源码行号及arm分母应取同批IR的实际catalog。原E runner没有源码分支trace，所有条目保持 `pending_trace`、`path_id=null`。后续共享itrace须按同IR/config、case-id、phase和path-id绑定实际arm，包含失败与UNSAT终态，不能仅凭数值和状态通过写成分支PASS。真实word经`ext_decode`返回ILLEGAL的负例与constructor正向编码失败分别登记。

## 源码分母与动态关联进展

[源码清单生成器](tools/solve_bf16_coverage/source_catalog.py) 对四个BF16文件及FD中的两个BF16专属寄存器helper保存实际源码SHA、函数范围、逐词法site/arm及编译条件。当前人工核对总计60site/136arm；其中共同定义12site/24arm、SYMBOLIC定义20site/48arm，构成本次IR的专属32site/72arm。非SYMBOLIC的28site/64arm单列编译域，另有6个ITE和4个vector-select数据选择点，不能当作执行器分叉。此为原始共享site计数；最终义务须按clause、site、arm、入口模式和配置展开，共享helper在另一clause命中不能自动闭合本clause。

统一ID的catalog在 `solve-bf16-source-catalog-global-20260926`，SHA-256 `d84d90654d6539d1e5dc00d2e7d46de1244ec4652da5db03dead57afe03c5ea8`。独立复核了全部60处关键字token的UTF-8半开字节区间；`global_site_key` 按固定字段顺序保存file、source_sha256、token_start_byte、token_end_byte、kind、subcondition_ordinal，其紧凑JSON UTF-8的SHA-256作为site_id，行列仅展示。按BF16六clause引用展开，当前专属义务为88项：两scalar分别6/8、窄化/扩宽各16、VV20、VF22；尚须引用共享FD/V义务，不能把各包原始计数直接相加。所有在编译域内的arm仍未接真实观测，非SYMBOLIC的28site明确为 `out_of_build`。

四向量clause的SEW断言由真实decoder的SEW16守卫支配；扩宽LMUL断言由 `valid_eew_emul(SEW*2, LMUL+1)` 的EMUL≤3条件支配。固定VLEN128/SEW16时，`get_num_elem=(2^max(0,LMUL))*VLEN/SEW` 至少为8，因此四个SYMBOLIC容器循环的零次迭代臂不属于该入口域；vl0只令活动mask为零。上述是当前源码推导，仍须用冻结新IR的SourceLoc、实际支配关系及配置绑定，才能在最终表标为 `unreachable_proved`。

[轨迹关联校验器](tools/solve_bf16_coverage/trace_audit.py) 已按统一runner的 `trace_terminals` 接口实现输入/结果/运行摘要哈希、实际argv、终态守恒和逐edge后继/source检查。decode的两个终态分别保留，不能按输入ID或phase去重。集成协议进一步将输入ID与callback终态ID分开：`terminal_case_id=SHA256(name + NUL + phase + NUL + decimal ordinal)`前8字节大端u64，R3 metadata使用此终态ID，结果同时保存 `input_case_id`、`terminal_case_id` 和ordinal；校验器显式检查推导与无碰撞。R3只提供Jump catalog和真实edge，多个Jump可能共用SourceLoc；本工具仅输出真实边与已验证结果的关联索引，不猜源码arm。[十二条负控制/绑定测试](tools/solve_bf16_coverage/test_trace_audit.py) 已通过，包含错误后继、陈旧source、无关case、重复或缺失terminal、无catalog的edge拒绝，以及callback身份/阶段不符的拒绝和循环命中次数/先后顺序保留；这只是工具验证，尚不是BF16真实分支覆盖结果。

共享guard复核另确认一项必要的独立条件见证：扩宽 `valid_reg_overlap` 的末项为“源/目的组末端相同且源EMUL≥1”。主包m1同起点的非法重叠通常在“末端相同”已为false处短路，不能保证观察后一个条件的false。新增独立[四条输入](tools/solve_bf16_coverage/shared-overlap-illegal.json)，在合法mf2状态令源/目的同一物理寄存器，三项扩宽中VV两源分别测试；末端相同为true、源EMUL≥1为false。输入SHA-256 `8c56e249922173eea65e1c2246102a085a774d18ec553232e58425f9a16e2467`。同d012/config/执行非法runner运行4/4 PASS，exit0、5.051s，状态无写、译码/回编码及单执行路径均复核；结果SHA-256 `fbc531a5870a87ab13ae1f85553fc9817e6cee327c087a7d47abf838beb87abb`，证据目录 `solve-bf16-overlap-factor-20260926` 的summary SHA-256 `ad8c6fdc9c2a1ac9f287f61f389ce22c7d624564cffef0e64b8ff2ed6b0cb871`。922条主包不变；这4条须随新IR取得实际edge后才可闭合该条件。

### 短路因子与生产纯转换证明补录

短路条件另表保存，避免只记录外层guard而遗漏其独立条件。统一规则以物理 `&`/`|` token为半开UTF-8字节区间，kind为 `short_circuit_and/or`，`subcondition_ordinal=0`；同一父site中的扫描顺序仅作为 `factor_index` 展示。当前工作树清单 `solve-bf16-source-catalog-factor-zero-working-20260926/source-catalog.json` SHA-256为 `11f1d7f568adcc00e4e0ded2ca6cefe9e4cf86d6aebcf0ee6e4d6c2d3b46ac1f`，含19个词法因子/38个因子arm，其中13个因子/26arm在本编译域，6个因子/12arm在非SYMBOLIC域。按六clause引用展开为30个因子引用，即60个arm义务；本编译域21个因子引用，即42个arm义务。原60site/136arm另表保留，不混加数据选择点。该版本绑定当前五份源码，仍需按最终IR source manifest重生，不能称最终冻结。末项比较若没有独立Jump，必须依据外层控制边及数据前提建立证明，不能虚构运行时边。

生产 `bf16_to_f32` 的真实Sail小IR证明已复核：`test/symbolic_fp/solve_bf16_lanes/` 直接编入生产helper，以未知16位输入比较保留的旧转换体和新纯实现。4条旧/新路径分别先SAT、再完整flags/value差异UNSAT；新函数独立执行恰1条SAT路径。脚本另核新helper IR含3个generic `eq_anything` 且没有 `eq_bits/neq_bits`。受测小IR SHA-256 `63147a86d0e92ba7b0667fcbc51deb29b54bb4dcce893c141de8b6b3ad35d2b6`，生产helper `2c0693f4c578e6b237cc5de39d4a0014b6e46580cc69f66efdeb00f1785c6f07`，probe `dbb6d3b71052cf00abba2de031508af495143334cb7913f1989372d1304c18e6`，runner `4cc5902bb006e7b5a6ab4230e88f792fe01bb83f8ce564744d0a3fd997fbcfef`。证据目录标识为 `isla-bf16-lane-equivalence-20260926`，扩展后的 `report.json` 同时绑定三份BF16源及浮点core。命令从 `sail-riscv/` 执行：

```sh
bash test/symbolic_fp/solve_bf16_lanes/run.sh "$OUT" "$ISLA_PLUGIN"
```

该证明范围为纯转换返回值与flags。probe中的 `accrue_fflags` 为不调用的空stub，不将此结果记为CSR副作用或六条完整指令通过；最终922+4仍须在新完整IR复跑。通用lane flags聚合证明另见 [性能验证](solve-fix-performance.md)第9节。

### 官方状态域迁移与历史记录更正

最终source-arm见证须采用与官方相同的assert变换和模型寄存器初始化，并满足R1域。原922主包与4条overlap补例保持原样；规范化包使用新名称和新case ID，逐例记录来源及迁移原因。mstatus只按同IR静态S/U能力恢复只读SXL/UXL字段，FS/VS/SD、FRM、vtype的测试变化与数值预期不借机简化。最终实际state-domain manifest仍须与候选IR/config绑定。

本次逐项复核纠正此前“vill样例为vl0”的描述：冻结v5的4条vill输入虽然 `vtype=1<<63`，其 `vl` 实际为1，属于R1域外诊断状态。历史d012的decode拒绝结果及输入哈希保留，不能将其算作官方域的分支见证。规范化版本按R1的canonical vill要求将vl改为0，保留真实word及decode拒绝预期，并明确记录原阶段/目标阶段均为decode，待新runner验证；该变更源于canonical vill域约束。

[官方域迁移器](tools/solve_bf16_coverage/canonicalize.py)已实现。纯迁移核对覆盖全部926行：新ID无碰撞且与原ID集合不交；所有mstatus初态与预期只改变只读XLEN字段，4条vill仅额外改vl，原word/fields/观察集/结果类别及全部浮点数值、flags和vstart保持。273条标量例原未指定vtype/vl，历史config也没有默认值；旧runner采用 `use_model_register_init=false`，按 `isla-lib/src/init.rs` 进入 `UVal::Uninit`，因此不应声称旧config提供了某个确定值。两条标量BF16执行体与FD/RM依赖链不读vtype/vl；新副本明确增加vtype=SEW16/LMUL1、vl0以给出固定R1合法见证，并逐字段记录 `old=null`。该选择仅限定向输入，不改变official solve域。


P2完整IR生成后，已从其冻结checkout重建专属catalog，并逐份核五个源码文件的hash/bytes与source manifest一致。产物标识 `solve-bf16-source-catalog-p2-20260926/source-catalog.json`，SHA-256 `673bd280cde5fffeeb80e7ffc1e7c3326fff48e7217130e7565e0bacdfd7c096`；绑定IR `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9`。当前编译配置按六clause展开为基础88、短路42，共130项专属arm候选；共享FD/V的调用域与义务另表补足。篡改manifest源码hash的负控制exit2且未建立输出目录。计数与版本绑定是静态结果，尚无动态闭合结论。

轨迹校验器追加trace-map侧车的输入名、callback ID、阶段/状态/ordinal与双向终态守恒检查，连同原测试现15/15通过；名称替换与缺callback的负控制均拒绝。这仍是证据工具校验，不计BF16新IR模型PASS。

### P2规范化输入与静态映射证书

已完成的P2官方 `F_UN_RM_FF_TYPE_S` 独立诊断提供实际R1静态域：S/U=true、H=false、SXL/UXL=2、MPP∈{0,1,3}。本包已逐份核其IR/config/JSON/二进制/log SHA，再抽取静态域侧车 `solve-bf16-canonical-p2-domain-20260926/domain.json`（SHA-256 `2ba2d8e0c7ef7c6f790bb6d3092bc31d00406992a5df9f07059ea47f84a335da`）。它绑定P2 IR `d86655a4…` 与FD config `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`，仅作静态能力依据；不能替代定向runner实际初始化侧车，也不表示77项整批完成。

首个canonical版本随后被实际初始化检查指出特权态未具体化：FD config删除旧默认后，`model_init=true`并不自动给没有模型初始化体的 `cur_privilege` 一个Machine值。原canonical v1保留为未运行构建产物，不作见证。当前v2另建名称后缀 `__official_r1_v2` 和新ID，全部926行显式指定 `cur_privilege=Machine`；相对v1只增加此字段及身份变化。规范化目录标识为 `solve-bf16-canonical-p2-v2-20260926`，manifest SHA-256 `f3b290e842f4a92c29779ae3eafcf857ade64b3c690c694432beaf3202a7c6f9`，926条迁移记录 SHA-256 `c1a9f4a37f10e77c6b9be576ea41136f29fb733e6ae2d6d15c7d66f2a8967c73`。已独立逐行校验完整JSON与登记变更一致，旧例及旧canonical均未改写。

| P2 canonical v2输入 | 条数 | SHA-256 |
| --- | ---: | --- |
| success | 835 | `0e7fd943e84d3e8b3d34b01f768d3f6656909a6d3ca37512c6d85d9e38fb893e` |
| execute Illegal | 51 | `ec42d3f827ee3099e2ef71914251976d6610ef4619df3905f04ae52028cf3798` |
| decode Illegal | 36 | `88426c6c43bf6d517be2e27ef77ac6f80c716809966fac9e7fce94da01acb737` |
| 共享overlap补例 | 4 | `38375790a71ca5ca8905c1a39f28b29e19ff1ef16fd39c9d5f713960a5ca88ad` |

[基础lowering校验器](tools/solve_bf16_coverage/base_lowering.py)已在FD20851f配置的实际SharedState sidecar上生成20个BF16基础site的60个局部lowering：六条when的四种generated函数、六处if、五处match及三种BF扩展Bool的consumer。证据标识 `solve-bf16-base-lowering-p2-fd-20260926/certificate.json`，SHA-256 `fa3d8051d26a9b36b7b2bfcdfecb73195e784db181b89409b4f3095656705505`。match极性以被冻结executor中 `Kind(C,x)` 的实际语义“构造器不等于C”为依据，并核返回union只有两个成员；首臂为fallthrough，不将taken机械等同源码首臂。when的最终Not guard与上层结构分别核对，避免仅按SourceLoc归因。

独立架构证书 `isla-bf16-lowering-independent-p2-fd-20260926/certificate.json` SHA-256 `90f86a33f7910d593a1bf2458944d332328ed79a2bcd6ed00609d483bb7b6154` 另核13个词法短路因子的25个generated lowering、8个assert的实际handler及恢复PC、3个静态hart capability、4个foreach极性/回边。两份证书都绑定其header中的P2 IR/config与实际runtime catalog；它们是静态映射和指定前提下的不可达证明，尚未替代新runner动态见证。后续若完整IR或runtime变化，须重新生成并核对，不将P2标签直接升格为最终结论。

独立复核后进一步加固基础映射：冻结executor hash必须等于runtime source manifest对应项；Bool alias只沿正常CFG跟随goto，穿越异常判断须登记 `have_exception=false` 前缀，遇其他控制边/终止立即停止，被重新赋值的alias失效；boxing真臂另机器核低16位slice与实际return。加固证书标识 `solve-bf16-base-lowering-p2-fd-hardened-20260926/certificate.json`，SHA-256 `5be1879c237e87c04313ab31ba2543710864c5cd7e0d1ab3a777c798a1d2927d`，20site/60lowering不变，旧证书保留。

分母统一口径是 `(clause, entry_mode/config, source site, arm)`，不机械按phase乘倍。decode/encode/execute及generated function是实际证据标签，不能跨方向伪称命中。同一when的源拒绝臂可以由canonical decode拒绝满足；custom decode-first路径中encode拒绝因同状态先成功decode而被排除，与official encode-first入口的non-encodable义务不同，后者另由官方批次验证。共享FD/V的语法调用候选只有经实际typed调用及域前提审核才计入适用义务，原始候选总量不能直接报告为可达分母。

### canonical v3：完整重放历史VPR初态

后续系统核对旧E配置与FD配置发现，除特权态外，旧E提供的 `vr0..vr31=0` 也被删除。v2未显式指定的VPR因而会从历史具体零变成符号值，可能影响包含非活动lane的源寄存器组。当前v3为每例补齐旧配置实际生效的缺省零值，已有显式VPR、mask、lane和全部预期保持。全部926例现具有32个显式VPR，共新增27237个字段；每个新增字段在迁移记录中保存旧config SHA、完整键和值。此为定向见证的初态重放，不作为official solve的默认约束。

迁移器核对E→FD全部35项defaults差异：32个VPR零默认与Machine删除、mstatus默认0变为0x6600、旧 `__isla_always_aligned` 删除。每例原本均显式给mstatus，因此仍由case覆盖默认；后者经源码与实际P2 IR检查没有符号，旧配置项未生效，只记stale、不添加假初态字段。全部const_primops的名称和值相同。任何额外差异、IR/config与域manifest不符都会拒绝生成。

v3产物标识 `solve-bf16-canonical-p2-v3-20260926`，manifest SHA-256 `74f6cc4eda697845ad8fa06a564dd16bac8f68cef89f4f249cd3f2f5e0fb708c`，迁移表 `f671f22183a3820da1753301005d68819a2e3398162c87918fc4a0fcad078b96`。相对v2，独立逐行比较确认仅新增历史零VPR、新名称后缀及新ID；全部已有初态与预期字典保持。v1/v2和原始922+4均保留，不把旧canonical构建产物算作最终见证。当前v3仍绑定d866 IR的静态能力；集成候选IR变化后须重新探测并绑定。

| canonical v3输入 | 条数 | SHA-256 |
| --- | ---: | --- |
| success | 835 | `5177dfef3ffe955b41d62522e7d28a15a651a1f6a9064ae45af6002e34c7d1ab` |
| execute Illegal | 51 | `aad1c9f31d4510f80c19f9fd9843b204cb6f744353a54f6efbfeee8ddfe65e15` |
| decode Illegal | 36 | `db211039f63bb1ab4bc5b20b4cb9d40bb749fbd7e0204014cb5a519bb2065c1a` |
| 共享overlap补例 | 4 | `f1420556e7edf08992ba2c33a59654701ee3b81efaef6fc00cd3c16c01070dee` |

### misa入口域细分与合法替代补例

后续核对官方Target发现misa为固定初值 `0x800000000034112f`，并非R1域内任意可改字段。因此canonical v3只完成mstatus/vtype/vl等R1迁移，不能据此把其全部926例称为官方默认misa域见证。独立逐例核定后，916例保持默认misa；4例清V（`0x800000000014112f`）属于合法替代配置；6例仅清F但仍置D/V（`0x800000000034110f`）违反 `legalize_misa` 的D⇒F、V⇒F&D，保留为raw诊断。此前这些例的历史结果及输入哈希不变。

[域拆分器](tools/solve_bf16_coverage/split_domains.py)按此分类保存原926条完整JSON，并新增6条同时清F/D/V的合法替代译码拒绝例，misa为 `0x8000000000141107`，新名称后缀 `__alternate_misa_fdv_off_v1` 和独立ID。新增例相对各自来源只改变身份与initial.misa；word、观察集、Decode_Illegal和无写回预期保持，未使用模型输出生成预期。默认、合法替代、raw三域分别登记，替代或raw命中不闭合默认域源码义务。

每个misa值有独立TOML；派生文件相对FD20851f只改变 `registers.defaults.misa`，其余完整TOML结构及const_primops逐项相同。manifest保存parent SHA、逐字段diff及要求实际config初始化与能力探测，避免在默认配置上暗中覆盖初态。构建证据标识 `solve-bf16-classified-domains-p2-v2-20260926`，总manifest SHA-256 `5a6b29dda80c8722d2c4541f277d56e8a82b0bb568fb1d476c6a12211a8ee4b6`，来源表 `e77dcb2d79748dd6f75bae0af28df6e60b0e2a25eb958af5b64f3a6139394c0c`。独立核验原926逐条未变、新6只含已登记变更、新旧ID无碰撞；仍是输入构建核对，待实际运行。

| 域 | 组计数 | config SHA-256 |
| --- | --- | --- |
| 默认misa | success831 / execute Illegal51 / decode Illegal30 / overlap4，共916 | `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0` |
| 合法Voff替代 | success4 | `57fe2cc6c8d044cd7c585b3355d1c0f6c84f9ae90cab0dbb4d4ecfc540390bf9` |
| 合法FDVoff替代 | 新decode Illegal6 | `d3bfe08e4a1f55563a4760fe67ebaee082168aa46a868ca92e6fefbdd34fa8da` |
| raw Foff原始诊断 | 旧decode Illegal6 | `d8d96e07fababc39c6aad82f47eb232167fbb3f8dc1ac5e187d86063899c1ac4` |

### c5接续审计：冻结输入、静态证书与运行门槛

本节接续上述d866记录，保留其原适用版本。最新可复用输入是 `solve-bf16-classified-domains-c5cbb-v2-20260926`，manifest SHA-256 `ca02532aa35003d06d1f80084cd935e295421a49f15bb868d2f9f2e442649737`，绑定完整IR `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c`。逐条重核932行的数量、身份、输入及配置哈希通过：916条默认域、4条合法Voff、6条新增合法FDVoff、6条raw Foff诊断。此前的926来源例及新增6例分别保留。此轮只读核验和smoke输入选择记在 `solve-bf16-resume-audit-20260926/audit.json`，SHA-256 `61a5f3425a49bdaa95e34a7bf5d9a24bbc3511a4857f70e1b644e8acf7bc3bd6`；没有运行932条，也没有新增BF16模型PASS。

专属catalog现为 `solve-bf16-source-catalog-p2-full-20260926/source-catalog.json`，SHA-256 `31ce9e417869d335a7443ca1eec428cb69ca0327dd76211cf4a737269192e3fc`。五份实际冻结源码与source manifest逐份一致，60个基础site及19个短路site的global key均重新核对固定字段顺序、源码SHA、UTF-8半开token字节范围和ID摘要。SYMBOLIC域按六clause展开仍为88基础arm与42短路arm；共享FD/V引用另列。

| c5静态证书 | 证据目录标识及文件 | SHA-256 |
| --- | --- | --- |
| 基础极性，20site/60lowering | `solve-bf16-base-lowering-p2-full-20260926/certificate.json` | `d437bd8ee2c5fa1113fc88cbef1e25a3c3f3d580be8b005321a95174cb73f247` |
| 13短路site、8assert、4循环 | `isla-bf16-lowering-independent-p2-full-fd-20260926/certificate.json` | `a37b1d0b6c3f474bd9f3dfbfd3dab2e4a1db8375dce131dc3eb10f9913f35016` |
| Wma最后Zfbfmin条件的调用前提蕴涵 | 同目录 `wma-enabled-certificate.json` | `9cd8b2ce455f70ee53d26c96982732c80adcb3e6e935238e10a5a2c606b031aa` |
| 扩宽末项overlap前提 | 同目录 `overlap-certificate.json` | `0a96e97dc8568aaaa7584012fdb275104d679f064c36cda9afbc09fd924317f1` |

这四份证书绑定旧P2运行时manifest `128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346` 和FD `20851fdb…`，属于MixedBits/FmtVal最终修复前的静态证据。Kind“不等于构造器”的极性、when最终Not、正常CFG中的异常前缀、循环回边仍须随新freeze的实际SharedState复核。此前空edge工具演练得到130候选中24项有指定前提的静态排除、106项缺见证：24项分别为8assert失败、4零次循环、10按clause引用的hart capability假臂及2个Wma上下文Zfbfmin假臂。该演练不是实际trace，不能称“已覆盖24分支”；新freeze不能仅替换旧证书的版本标签。control/Wma证书脚本目前在对应仓外证据目录内，仍绑定旧路径，重生前须显式适配新冻结输入。

共享FD入口为 [shared_references.py](tools/solve_scalar_coverage/shared_references.py)，本次从c5生成的 `isla-scalar-resume-audit-20260926/shared-bf16-references-c5.json` SHA-256为 `55a1c82862a24b03df2e82aeb65df88104f7d8ef728b517113ae3d66ed2963f2`。18个clause/phase条目引用F/CSR合法性、标量RM映射、FPR读取/写回和Dirty/flags；12份源文件均与c5冻结一致。四向量clause继续引用 [BF16共享V作用域](tools/solve_vector_coverage/bf16-shared-source-scopes-final.json)，SHA-256 `e33ec446d14d0973c489307f15c862d912bbab9b6c61e04d37c4ed7b7c4f01d8`，其中10份源文件亦一致。向量RM检查来自 `illegal_fp_variable_width → valid_fp_op`，不冒用标量RM映射。共享表是调用候选，仍须typed重载、调用前guard及逐arm前提；其它clause的命中不能替代本BF16 clause。V侧 [接续证据](tools/solve_vector_coverage/source-frontier-c5-resume.json) 中23个typed调用绑定与短路极性核查也未带actual R1 gate，不能升格为本包默认域见证。

本次工具负控制先复现了两项缺口：同IR/config而runtime陈旧或缺失仍被 `arm_closure.py` 接受；`trace_audit.py` 固定要求两个decode callback。现已收紧动态/静态 `runtime_snapshot_manifest_sha256` 一致性，按实际正整数decode计数核callback、连续ordinal、trace与trace-map守恒，并绑定真实初始化侧车及逐case R1 SAT合同、具体值、misa域。工具检查25/25通过，含旧runtime、缺runtime、R1符号值和替代域冒用默认域的拒绝；这只是工具验证。

最小后续smoke已从原包原样选择6条，产物位于 `solve-bf16-resume-audit-20260926`：`default-manifest.json` 为标量/向量success各1、scalar动态FRM execute Illegal 1、FSoff decode Illegal 1；`alternate-v-off-manifest.json` 和 `alternate-fdv-off-manifest.json` 各1。三个manifest分别配本域TOML，用同一新冻结IR/runtime重建的三runner运行，先核实际初始化、callback守恒和状态，再扩大范围。完整例名及来源输入SHA保存在audit，不重新生成数值预期。随后优先加入现有4条mf2 overlap、canonical vill、BF16 boxing两臂及无活动sNaN回归；这些已有定向输入，当前短板是新freeze的实际见证及共享调用域绑定，尚无依据宣称需新增数值oracle用例。

随后初始化校验已抽为公共 [entry_contract.py](tools/solve_fix_integration/entry_contract.py)，BF16不再维护独立合同副本。公共函数固定Target SHA `d9779a183f228da58f536e89491178293542f2cf55efd6574d68d9da4f0b0804`、四个R1具体字段，并重算实际lets摘要。新增负控分别拒绝缩减字段、未经审定的Target、lets值变化及键序重排，完整工具检查现29/29通过。真实runner的serde_json启用 `preserve_order`；首次误按排序JSON核算使四组真实侧车被拒绝，随后按实际 `serde_json::to_vec` 原键序UTF-8格式修正校验。原产物未改写，此处明确修订排序假设。

集成负责人已在c5 IR与阶段运行时manifest `6e00edd8ec17b627edcbfcd14dcdd50b4f3e6cd0ffeb11ca5343cf71a58fa084` 上完成5条工具smoke。本包只读复核全部四组真实summary/argv、初始化合同、数值观察、trace及callback侧车：default-success为2例/6终态，default-illegal为1/3，default-decode为1/1，合法FDVoff为1/1，共5例11终态；四组均通过，实际每例decode为1条。审计产物 `solve-bf16-bound-smoke-audit-20260926/summary.json` SHA-256 `e0d46c1fc056e4a105cf431fbc1694917b311bfea9acc33d588a8a270832202b` 保存逐组证据哈希、工具源码哈希及实际argv。此项通过范围是新R1/trace协议在c5阶段产物上的一致性；未运行Voff smoke，未执行932条，也未把runtime `128d59a5…` 的旧静态证书套用到本批或称最终source-arm闭合。

进一步复核明确：上述五例的初版动态边报告仅核itrace自身catalog与runtime标签，尚未把全Jump目录与实际SharedState双向比较，因此仍只作trace/init协议证据，原文件及哈希保留。`trace_audit.py` 现强制 `--runtime-sidecar`，复用共享 `read_sidecar/verify_runtime_catalog`，先核IR/config/runtime及初始化模式，再逐个比较全Jump的function、PC、target、fallthrough、SourceLoc和完整指令；输出 `runtime_catalog_sha256`。`arm_closure.py` 同时要求base/control/Wma证书的sidecar SHA一致，且与动态报告相等，缺失完整目录核验的旧报告被拒绝。新增同runtime旧sidecar、缺sidecar、未比全Jump、静态证书sidecar冲突、遗漏未命中Jump及同位置改变条件等负控，完整工具检查36/36通过。

三组默认域产物已只读重核全部25950个Jump，通过实际SharedState目录 `isla-scalar-runtime-catalog-final-20260926/official-fd.jsonl`，SHA-256 `91611fa7a4c0f0f52a8c52f4706c7eedf00231d931ceaa016ac848c351ef83e7`；header与c5 IR、FD20851f、runtime6e00逐字段一致。新审计 `solve-bf16-catalog-bound-smoke-audit-20260926/summary.json` SHA-256 `f88ba995364b1e40967fa0b49a3ea0fc4fb35736e0d309c2a4158e34d31bf14e` 保存三份报告、公共校验代码哈希及命令。这是4个默认域输入的完整目录绑定，仍需同版BF16静态极性证书才能进行source-arm闭合；合法FDVoff没有对应config的full sidecar，维持协议通过、目录绑定待复验。本轮没有重新运行模型或提取旧完整目录。

### 最终冻结1dcc：专属目录重生

最终模型/运行时freeze的source manifest为 `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`，完整IR为 `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`。从该冻结目录重生的BF16清单位于 `isla-directed-final-coverage-20260926/bf16/source-catalog/source-catalog.json`，SHA-256 `1b39fded03901551ed62f35758ce41549a725fecac2f4b96dea68506f480db9f`。五份BF专属源码与c5的hash相同，79个global site key不变，本编译域仍为130个按clause展开的arm候选；IR及manifest绑定已独立更新，旧目录保留。

最终共享FD引用另取 `isla-directed-final-coverage-20260926/scalar/shared-bf16-references.json`，SHA-256 `52fde236e915a0971495b871f32e104b4ce2063f23ab402cdfcb3c50f7de9d5a`；已核其中13份源文件与最终manifest一致。目录、共享引用及版本比较记录在新目录的 `provenance-check.json`，SHA-256 `5cb88f409c20bb9a29fe30a5e6966f52f7c24fba6d9241511cda76c89a950a9d`。目前只完成生成与哈希核验；新runtime sidecar、基础/control/Wma极性证书和同配置真实trace仍须绑定后才计最终源码见证。

后续最终默认配置sidecar已到位，`isla-directed-final-runtime-catalog-20260926/official-fd.jsonl` SHA-256为 `aa069e7f2232b70990763073a2c4c58f73ca2f91c368e6edec284dc9e5acfc60`，含2060函数、378944指令和25772个Jump，实际header为IR1dcc/config20851f/runtime28fb。新基础证书 `isla-directed-final-coverage-20260926/bf16/base-lowering.json` SHA-256 `fdc52d30cfa61e708f796541dda067acf9838afcd5483d016c9529a167441ef2`，20site/60lowering。架构owner的新control证书 `507ea7ea375e16c99d884a17cd0ad64d7a1c767949aaa9fd2299fdc3c04920cf` 与Wma证书 `7397253c0d373e88720c34833d6a9eaeb707e69e93ba5ea61883c76cff708390` 位于 `isla/target/float-solve-evidence/architecture-certificates/final-20260926T160822Z/`，三者严格绑定同一个实际sidecar。

集成63条小批中的三个BF默认组（2个成功例、1个执行非法例、1个译码拒绝例）已核数值/R1/终态侧车及全部25772个Jump。生成的新 `bf16/minimal-arm-closure.json` SHA-256 `f0f5970e39ba6ba7801949e190232349c4ea65fb7ae765d449452db7d044f944`，同入口域130项专属候选中23项实际观察、24项按证书前提静态排除、83项缺见证。FCVT_BF16_S观察4/缺3，FCVT_S_BF16观察7/缺2，VFWCVTBF16_F_F_V观察12/缺6；其余三个clause尚不在该小批输入中。83项不能写为通过；共享FD/V分母也不包含在此130项内。

最终共享V作用域另重生为 `isla-directed-final-coverage-20260926/vector/bf16-shared-source-scopes.json`，SHA-256 `8f35042075e8ee55cdf81771f9322ea186b31eb64cf6424b11b981c333dc037c`；配置标签已改为default-FD，12份源码绑定最终manifest，仍为四clause候选引用、`source_branch_closed=false`。

合法全包已按配置原字节复制到 `isla-directed-final-full-inputs-20260926/bf16/`。总索引 `index.json` SHA-256 `902923dd4ef5d0e19e1b2030c2800e7294b75d9f224498cd423c586521cc95f5`，三套run计划分别为default916（831成功、51执行非法、4独立overlap、30译码拒绝）、Voff4成功、FDVoff6译码拒绝，共926；raw6仅记录排除、不进入运行包。输入与TOML及来源hash逐份核对，新manifest明确为PREPARED_NOT_RUN，旧c5绑定只作来源。现有全包包含上述专属缺口的预定样例，是否闭合仍待最终实际trace，不由输入库存推断。

### 最终全包运行与专属源码义务结果

上述输入计划随后由集成负责人按三个实际配置完整运行。本轮逐组复核真实 summary/argv、输入和结果、初始化及 R1 合同、trace-map、全部终态与实际 SharedState 的全部 25772 个 Jump，六组审计均通过。受测版本为 IR `1dcc8081…`、runtime manifest `28fb65ee…`，入口为 `directed-decode-first`；每个配置独立绑定对应 sidecar。

| 配置与组 | 输入数 | 终态数 | 审计结果 |
| --- | ---: | ---: | --- |
| 默认 FD：success | 831 | 2493 | PASS |
| 默认 FD：execute Illegal | 51 | 153 | PASS |
| 默认 FD：decode Illegal | 30 | 30 | PASS |
| 默认 FD：独立 overlap | 4 | 12 | PASS |
| 合法 Voff：success | 4 | 12 | PASS |
| 合法 FDVoff：decode Illegal | 6 | 6 | PASS |
| 合计 | 926 | 2706 | PASS（列定输入与观察集） |

实际运行摘要位于仓外 `isla-directed-final-full-results-20260926/bf16/` 的三个配置子目录。最终审计目录为 `isla/target/float-support-review/final-coverage/bf16/`，其中 `full-summary.json` SHA-256 为 `8f35fb0714fb3a9591963f15ef0087188c50948f997e93e7dd0d1d0f2221e337`，保存六组报告、输入/结果/初始化/trace-map、实际运行摘要和 sidecar 的完整哈希。默认配置报告在 `default-trace-audits/`；两个合法替代配置分别为 `alternate-v-off-trace-audit.json` 与 `alternate-fdv-off-trace-audit.json`。原始证据未移动或改写。

默认域的 `default-arm-closure.json` SHA-256 为 `594020a8bea95deaf9e971caa024cfdbf8160a4b531e8057d3e854e7679f19c8`。本版 **BF16 专属** 130 项 `(clause, entry/config, site, arm)` 义务为 **106 observed、24 unreachable_proved、0 missing_witness**；逐 clause 如下。

| Clause | 实际观察 | 按前提静态排除 |
| --- | ---: | ---: |
| FCVT_BF16_S | 7 | 1 |
| FCVT_S_BF16 | 9 | 1 |
| VFNCVTBF16_F_F_W | 18 | 4 |
| VFWCVTBF16_F_F_V | 18 | 4 |
| VFWMACCBF16_VV | 27 | 7 |
| VFWMACCBF16_VF | 27 | 7 |

24 项排除仍依赖前述同版 base/control/Wma 证书和其入口前提：8 个断言失败臂、4 个零次循环臂、10 个按 clause 引用的 capability 假臂、2 个 Wma 最后 Zfbfmin 假臂。control、Wma 与 overlap 三份证书另经架构独审实际复跑，产物逐字相同；静态排除不记为动态命中。小批 `23/24/83` 保留为历史阶段结果。

本次完整工具检查为 38/38 PASS，包含初始化、callback 守恒、陈旧 runtime/sidecar、遗漏未命中 Jump、指令条件变化、循环顺序及流式解析负控。生产 trace 解析逐终态读取、输出流式写入，避免复制巨大 JSON 字符串；default-success 报告仍保存全部见证。此处工具数对应全包审计时点，后续共享见证工具的测试另记。

共享 FD/V 的义务未计入上述 130 项。共享 FD 引用的 18 个 clause/phase 条目和共享 V 的四 clause 候选必须再按实际 typed 调用、root call PC、phase、config 与 arm 联立；其他标量或向量 clause 的全局 site 命中不能替代本 BF caller。合法替代配置的边也不消除默认配置义务。该结论只覆盖列定定向输入、专属源码分支和明确静态前提，不扩展为 official encode-first 或任意数值输入的全分支闭合。

### 共享 FD/V：实际 caller 见证接续

共享 FD 同版极性证书为仓外 `isla-directed-final-coverage-20260926/scalar/source-lowering.json`，SHA-256 `528cd7e26d53e26c47914e059e8a0a5a46751cb30fc24073bf44d9a0e3cf1758`。从最终 BF catalog 提取六条编译域内 execute 声明及六条 encdec 声明，保存到上述磁盘审计目录 `caller-definitions.json`（SHA-256 `25b81e35d6b9c2bab0fb75e31aa3fa2dfd59fa4c15dc532992213889966a827a`）。共享工具据实际 runtime Call、源码范围及调用闭包建立独立六 caller 候选表，未复制 49 标量的见证。

[共享见证提取器](tools/solve_bf16_coverage/shared_witnesses.py)逐 edge 读取大型 BF 审计、重核其完整文件 SHA 与 IR/runtime/sidecar，并复用共享 `summarize_source_arms` 极性映射。输出 `shared-fd-observations.json` SHA-256 为 `4ba96cdd183327f69ec8daca01c790de6011ad24aac117e9f4a90a9f8d3021b4`；再用 `matches_obligation` 精确匹配 clause、phase、config 和独立调用帧 `function:PC`，产出 `shared-fd-caller-witnesses.json`，SHA-256 `62a7cd6b92d121dec0c213e81040d4c33af1339a5f37d108a70736ff8e5bf3f1`。

| Clause | 默认域共享 FD caller 见证 | 尚待裁剪或证明的静态候选 |
| --- | ---: | ---: |
| FCVT_BF16_S | 20 | 127 |
| FCVT_S_BF16 | 13 | 82 |
| VFNCVTBF16_F_F_W | 3 | 5 |
| VFWCVTBF16_F_F_V | 3 | 5 |
| VFWMACCBF16_VV | 5 | 11 |
| VFWMACCBF16_VF | 7 | 50 |
| 合计 | 51 | 280 |

331 为静态调用过近似候选，不能作为已确认可达分母。280 项主要涉及 `rF/wF` 的不同实现路径、F/Zfinx 能力选择、固定 f32 helper 的其他格式臂、断言失败和 `nan_unbox` 的同宽早返回。已核 BF16 窄化 caller 的实际 boxing 两臂均有观察；当前缺的是外层 `n == m` true，须用 flen64/m32 的 typed 实参证明排除。共享 guard、短路 factor 与尚无 lowering 的 site 继续单列，不因未进入本表而自动排除。新增提取工具四项负控先红后绿，完整 BF 工具检查更新为 42/42 PASS。

共享 V 的四条 mf2 overlap 补例已由 V owner 按真实 summary、输入/结果、初始化、trace-map 与完整 Jump 目录重核。证据 `isla/target/float-support-review/final-coverage/vector/overlap-bf16-4-return-bindings.json` SHA-256 为 `7429437efcd1afd99838745e1070652ad2e5b167aae585f69fd37bba9083717f`。五次真实 helper 调用中，四个目标 caller 均由 `zvalid_reg_overlap` 的 pc136 比较 `EMUL_pow_rs >= 0` 返回 false，沿各自 caller 的 Bool 赋值与否定到实际拒绝 Jump，并在同一终态报 Illegal；另一次前置合法调用返回 true。该证据引用同版 overlap 证书 `d0230dc0…`，补齐四个独立 caller 的最后 RHS=false 见证；没有虚构末项 Jump，也不扩展到其他共享 V 分支。

默认四组的完整动态边另压缩为 `all-default-compact-edges.json`（SHA-256 `22cb8a23a7d835edffeb482f89a2787d7b1c9b9e4619cad27582cb3ba8f0522f`）：916 例、2688 终态、5017 个实际方向，每组只保留相同 edge/scope/phase/context 的首个代表；原审计保留全部见证和顺序。此文件供共享 V 逐 caller 关联，压缩本身不新增 source-arm PASS。

集成另提供 `isla/target/float-support-review/final-coverage/integration/phase-purity-binding.json`，SHA-256 `a2111746863feca2c636736f6f98ed69a1ff5a4483d317639f74c5d6bff388f9`，绑定八配置的 decoder/encoder 静态纯读证书与本批运行。它只支持分阶段初态一致性前提，没有新增动态 case 或跨 caller 见证。

随后复用共享 `refine_caller_candidates.py`，根据实际初始化 flag、不写/不逃逸扫描、固定能力解释和可达 CFG 重新计算每个 BF root-call 的闭包。`shared-fd-caller-refined.json` SHA-256 为 `e839ee1f66208853303b690fcfd5ae2e0b997d39d51dd0dc0906c3f6c7f5f4e0`，保留原 331 项为 51 实际见证、223 项依赖入口合同的固定 CFG 排除、57 待证明。工具强制拒绝排除已有实际见证。此时固定 CFG 证书仍要求核实入口不能覆盖内部访问器 flag 的前提，223 项应连同这一前提引用。57 项全部为固定位宽、断言或 RM 策略证明缺口：33 项 f32 helper 的其他格式臂、1 项 `nan_unbox` 同宽臂、23 项 capability/assert/Fcsr_RM 策略分支；尚未发现需为这些项目新增数值 oracle 输入。

[共享 V 关联器](tools/solve_bf16_coverage/shared_vector_witnesses.py)复用 V owner 的 `lowering-candidates-minimal12.json`、`short-circuit-candidates.json` 和 `short-circuit-cfg.json`，只接受匹配完整 edge 后继与极性的映射，并以 BF 共享作用域及实际调用上下文筛选。输出 `shared-v-caller-witnesses.json` SHA-256 为 `7750791bb639d8a4ea94eae779fc27cb0a18c451224de27dcbb8314bd640fb55`。

| Clause | 已核结构映射的 caller 见证 | 短路 LHS 实际见证，待规则独审 |
| --- | ---: | ---: |
| VFNCVTBF16_F_F_W | 117 | 32 |
| VFWCVTBF16_F_F_V | 128 | 35 |
| VFWMACCBF16_VV | 159 | 42 |
| VFWMACCBF16_VF | 128 | 36 |
| 合计 | 532 | 145 |

这里逐项身份保留 `(clause, phase, config, 完整 context, site, arm)`；532 是已观察条目数，没有将另一 context 的命中用于消除缺口。另列 984 项未观察静态引用候选、40 处基础 lowering 前沿，其中包含由独立短路表审查的 site；尚需按固定 VPR/SYMBOLIC 实现、typed 重载、SEW/LMUL 和调用前 guard 裁剪，不能据此构造已确认可达分母。两项新工具负控先红后绿，BF 工具总计 44/44 PASS。

### User/Supervisor 增量输入准备

为实际检查 R1 允许的 User 与 Supervisor，新增 `privilege-suites.json`（SHA-256 `e456037a8c04d51986181e11cd239d37dde05eac4e3c3b0a3a8759214199678c`），引用 `privilege-success12.json`（`c82a23764c78e4f9ad360e52b0e35f0feac9a79e866199cd07b472bd32da3212`）和 `privilege-illegal2.json`（`a24286d35cacf740322bc3a1133c58c213e082290c6ee6b9c06708c1a73155af`）。只派生已有独立预期的代表例，更改 case 身份和 `initial.cur_privilege`，原 word、观察集、数值及状态预期不变；全部前态为 `mstatus=0xa00004400`，FS/VS Clean。两个标量取静态 RM0，四向量取 vl1 的活动 lane/policy 例；非法两例取向量 FRM5，在写回前按 `valid_fp_op` 拒绝。

预期迁移依据及源 SHA 保存在 `privilege-input-manifest.json` 和 suite 的逐例来源中：`fdext_control.sail:18` 的 F guard 只读能力、misa.F、FS 和 Zicsr；`vext_control.sail:17-18` 的 Zve32x/Zve32f guard 再读 VS；`zicsr_insts.sail:12` 的 Zicsr guard 仅能力。BF 成功体、浮点/向量寄存器及 flags/Dirty 写回 helper 没有当前 privilege 或虚拟化条件；CSR 指令自己的权限检查不在这些成功路径内。本批仍为 **PREPARED_NOT_RUN**，须由支持三种 privilege 的新 runner 核实际 R1 和完整 trace，不把源码分析替代实际验证，也不将 H=false 版本类推到未来启用虚拟化的模型。

上述准备批随后在新 privilege runner 完成 **14/14 PASS**。逐 case 再核 actual R1 绑定为具体 `|User|` 或 `|Supervisor|`，与输入枚举精确相同，各 7 条；12 成功例共 36 终态、2 执行非法例共 6 终态，全部 42 终态与结果/trace-map 守恒，并核全部 25772 个 Jump 等于默认 aa069 sidecar。模型 IR、配置和 runtime freeze 仍为 1dcc/20851f/28fb；success runner SHA-256 为 `d17880a14f7cb6b04985386fa05f5dd869d6b104adb43106dfd5cb200cc9a745`，illegal runner 为 `fe7807cd6fce6853a49e2788d798df2b864275f1f53177af70d23ddba6b6ba5e`，不覆盖原 926 的 runner 或产物。

`privilege-summary.json` SHA-256 为 `b352bc6ca784faa229f8b978e852144d337b82e278d36ed777b7d2b49e3ac54e`，对应集成实际 summary `9242c06c4b7354fd8b0d76c6be44be32c287bcecf1449c25da2ad878b7866c6f`。两份严格审计分别为 `bf16-privilege-success12-trace-audit.json`（`744461d421e0972dba625ff3950dd4683f327678319067e1075fb8f28964e267`）和 `bf16-privilege-illegal2-trace-audit.json`（`b1045f557dc60161432af899b832b72e77732f784a8df34a15f2fb615047f15d`）。原 926 加本次独立 14 为 940 条列定验证、2748 个终态，须保留两个 runner 批次的版本记录。

增量共享关联额外以实际 privilege 分区：`privilege-shared-fd-witnesses.json`（`e4c6f7af01ccbed19d66c4d29e95dcb3932964979c4812ce7f7294f53a266541`）为 User/Supervisor 各 41 个精确 FD caller 见证；`privilege-shared-v-witnesses.json`（`b777394f53e4b3001a9de3123dc1133863c06b6daf27bad539d6ac7249a4ff2d`）为两域共 588 个结构映射见证、194 个待独审的短路 LHS 见证。同 clause/phase/context 而 privilege 不同的条目分别保留，新增负控先确认旧逻辑会合并，再修正；完整工具检查现 45/45 PASS。各域只登记实际观察子集，不能把 Machine 全包的全部分支结论转移到 User/Supervisor。

共享 FD 固定证书另更新到 `scalar/default/fixed-cfg-v3.json`（`828b2a1c77e37e4b292c4447b677a7995ce8f9abe0e817a1067b0423c1a0d87b`，同 final-coverage 根）。新增能力/断言的唯一且支配 use 的 def-use 证明及实际 `Fcsr_RM_Illegal` let 绑定，`shared-fd-caller-refined-v3.json` SHA-256 为 `7b66eaa00aaac87d724d9a2cb1d36fd21082421cbe6f009bb59110689a4be6f3`，当前默认 FD 是 **51 实际见证、246 项依赖入口合同的排除、34 项 typed 位宽证明待补**。34 项为 33 个 f32 helper 其他格式臂及 1 个 `nan_unbox` 同宽臂；此前 57 的阶段结果不改写。

共享 V 后续也按实际 root Call PC 建立候选并裁剪。为复用共享 caller 工具，`shared-v-caller-source-adapter.json` 与 `shared-v-caller-lowering-adapter.json` 只转换目录字段布局，保留原 global site ID、源 SHA 和全部已核结构映射正文，另保存原目录/证书 SHA；尚待谓词审阅的映射不进入这份表。调用域来自六 BF 源声明及实际 runtime Call，两个标量没有共享 V 候选。

`vector/default-fixed-cfg.json`（SHA-256 `213b3b92b05f20d65998976bdeeba7e816e6f7ea0facd58ffccbdfa0354d89f7`，同 final-coverage 根）固定实际 VPR/extra_ops/FPR/GPR 配置，逐 AST 核无写/无地址逃逸后计算可达 Call。`shared-v-root-caller-refined.json` SHA-256 为 `1d8437c5db68c6fdfef7b8c372627ee20c52a69d238f95a6603230991124fcb2`：1767 个静态 root-call/site/arm 候选中 **441 实际见证、941 项依赖入口合同的 CFG 排除、385 待 typed 参数或断言证明**。该口径按 root-call 合并其下不同完整 context，与前述 532 个完整 context 观测条目不同；两表不可直接相加。

385 项热点为 `assert_vector_num_elem_upto_128` 170、`assert_sew` 85、`read_vreg_extra` 38、`assert_lmul_pow` 21、`assert_vector_num_elem` 17、`get_sew_pow` 16、`valid_reg_overlap` 14，另有 24 项分布于配置/Dirty、宽度和初始化 helper。固定配置证书没有固定动态 SEW/LMUL 或函数实参，因此这些项目继续待证。14 个 overlap 候选对应窄化/扩宽实参恒差 1 的大小关系，须将此关系与各自实际 Call 参数及源码极性绑定；此前四条末项 RHS=false 的动态证据只覆盖自己的义务，不代替该参数证明。短路 LHS/RHS 和基础 lowering 前沿仍另表保留。

共享 typed 工具随后按 11 个 BF root 的 16 个实际调用帧传播 IR 类型及常量参数，34 项全部形成排除证明。`shared-fd-caller-typed.json` SHA-256 为 `91cb354972ce8046a3aae8888c0ff5ffe41ffeef1d2f2c4275b19437e4f30873`：**331 个已有结构映射的 FD root/site/arm 候选为 51 observed、246 fixed-CFG excluded、34 typed excluded，0 pending**。这仍不包含共享控制谓词、短路或 RM mapping。准确的额外引用为 5 个短路 site、4 个 Boolean 谓词和 1 个 `encdec_rounding_mode` mapping；不是将共享 FD 全部 81 个因子机械展开到 BF。五因子子集 `shared-fd-five-factors.json` SHA-256 为 `ac1ab1b5968415d391966d38043c997cde061877119baa9a9ec901e34f483ac9`。旧 factor 工具仅识别出 Ext_F 的 pc210/222 两项候选，其他三项仍为 lowering 前沿；候选报告 `shared-fd-factor-candidates.json`（`c3205cc99bd893cb812a205fbbd1dd6c51c3bd3ae23a7e2d0af8cb99d8f0e837`）不构成源码 PASS。

14 项 overlap 大小关系已独立审定。`vector/independent-predicate-review/overlap-arguments.json` SHA-256 为 `a5ada1c373db052dd4f4f5b48721b3647f4ada6e8e6e86b07610d7abf7fa4b42`（同 final-coverage 根），核实际参数的支配定义、同一 LMUL getter、精确整数转换范围、形参稳定性及 helper 控制依赖，六项负控均拒绝。按确切 root PC、phase、helper PC/方向引用后，`shared-v-root-caller-with-overlap.json` SHA-256 为 `4fc433bf1a2b2c3872697b9a882456fa4f0aeb226f06ea53cdd7e12174de8ac0`，当前 **441 observed、941 fixed-CFG excluded、14 exact-caller-argument excluded、371 pending**。剩余 typed 范围由独立审查接续，未据 source helper 的其他 caller 命中消除。

固定入口前提另见 `scalar/entry-invariants-v2.json`，SHA-256 `a02a45f8770245aaa63e6a49f8faf087cb877f1b547a7eb6f0c3c6b47136d153`：配置 `default_registers` 优先于模型 register 默认值，非 Target 内部 flag 不允许输入覆盖；旧冻结 runner 与新 U/S/alternate runner 的完整 `validate_official_entry` 逐字一致，由 `integration/phase-purity-increment-binding.json`（`640af0d934315e8bcd9edbad377548e45c1611a2d9bf7841166c44deb122dd6f`）桥接。这是排除证明的明确前提，不能替代各新批的实际初始化和 trace。

### 三配置的六 caller 代表补齐

Voff 原四条只覆盖四个向量 caller。两条标量实际仍可达：Zfbfmin→F 的 gate 不读取 misa.V，标量执行体也不读取该位。新增 `alternate-v-off-scalar2.json`（`a69c810bfa4f1b47e53ae3afb1898ef691b8b05cffe6076882acb3326b0b9359`）只按 Voff config57fe 更改已有两条 static RM0 代表的 misa、名称与 ID，word/观察集/独立预期保持；标准 suite `alternate-v-off-scalar-suites.json` SHA-256 为 `f3224529e064648a05b40727a254387a907ee73925dcf0b1aa464212a94ee893`。

新 runner 实际两例通过，严格审计核 6 终态、实际 R1/初始化、argv 与全部 25772 Jump 对同 Voff sidecar `943b54df…`。`alternate-v-off-scalar2-trace-audit.json` SHA-256 为 `b8caf9e34cacb24e926a86359f7d6877a8988821005ad964d68c844177ba6e61`。累计 **942 条列定输入、2754 个终态**：原 926、U/S 14 与新 Voff 标量 2 分批保留。

`caller-config-summary.json` SHA-256 为 `894a1ec3deca1c3ac37814930420d2eb43d55739c7e95562379b8fd40eeb697c`，逐六 clause/三个实际 config 保存输入数、终态数、阶段与实际 privilege。18 个 caller/config 单元都有代表证据：默认 FD 和 Voff 各六 caller 均有 decode/encode/execute，FDVoff 六 caller 均有真实 decode 拒绝。此表证明代表入口可达或守卫拒绝，**不表示每个单元的全部源码 arm 已闭合**。

### 共享 FD 控制与共享 V typed 前沿的独审消费

本节接续前述结构表，仍绑定 1dcc IR、aa069 默认 sidecar、20851f 配置及原默认 916 条实际输入。运行累计保持 942 条、2754 终态；没有因静态证明增加动态命中。

共享 FD 的五个短路 site 已全部建立实际 CFG 对应，不再停留在旧工具只识别两项的阶段。独审主件 `vector/independent-predicate-review/shared-fd-control.json` SHA-256 为 `6b167bf2a0dafeaf68bb922d42659d0ce9c705f751e7ff0aabbaba61a2c8fbb3`，分别证明五个短路 LHS/完整 Bool 真值表、四个语义谓词及 RM 的五个生成函数。其有限域解释属于静态规则验证，不当作模型运行。

新增 [控制见证关联器](tools/solve_bf16_coverage/shared_control_witnesses.py) 将主件与 BF 自身实际 root Call、config、phase、global source key、Jump 方向/后继及完整 witness 精确联立。最终 `shared-fd-reviewed-control-witnesses-v3.json` SHA-256 为 `f55c2ed993292406bb8ee6dbf8f51c121d349fa23de829936b08705fd5a6d87b`。

| 额外共享 FD 范围 | 实际见证 | 独审排除 | 待定 |
| --- | ---: | ---: | ---: |
| 五个短路 site 的 root/LHS 义务 | 50 | 30 | 0 |
| 四个谓词的 root/Bool 结果义务 | 54 | 42 | 0 |
| RM 生成函数的 root/实际 Jump 方向 | 103 | 17 | 0 |

30 个 factor 排除由 `shared-fd-exclusions.json`（同独审目录，SHA-256 `499d43ffff8de3d7d7d769a973941aa9356d276c3088e694a3f9f9753f71192e`）给出：12 个 hartSupports(F) 假臂、12 个默认 misa.F 假臂、6 个 encode 的 FS 假臂。最后六项依赖同 constructor 已成功 decode、BF extension⇒F 的必要条件、同初态与 decode/encode 纯读；decode 的 FS=false 仍保留真实见证。四谓词的 42 个排除分别为 36 个冻结 literal true 的假值及 6 个上述 encode F=false。语义 Bool 返回通过已审返回数据流绑定，没有把 extension 枚举选择器误称为源码 Bool 分支。

RM 的 17 个排除由 `shared-rm-domains.json`（SHA-256 `6e2c38dedf0348472ea67b3b7ff3b0b3a6119577b70a40e8a170cc9597b892dd`）给出：两 scalar 的 select 内部 forward 恒以 RM_DYN 为参数，各排五个非 DYN 方向；内部 backwards 仅接收 0..4，各排三个方向；FCVT_BF16_S 的直接 forward 只接成功 select 的五个非 DYN 枚举，排最后 DYN 方向。两个 decode backwards_infallible 另逐实参绑定同 bits3 的 matches=true 前提；5/6 处于该前提之外，不能把 infallible 视作一般拒绝入口。

两 scalar 各有 valid_rounding_mode 与 select 的 RHS 真/假，共八项实际语义见证。真实 FRM0 为真，FRM6 使 valid_rounding_mode 的末项为假，FRM7 使 select 的末项为假；记录同时核真实输入、同 root LHS、FRM getter bits[7:5] 与调用前 FCSR 保持证明。末项没有独立 Jump，故没有生成虚构方向。新增消费工具的负控拒绝错误 caller/config、源码身份/极性/后继、不存在的终态见证、排除已命中项、错误正常返回终态及 RM 前提变化；完整 BF 工具检查 **52/52 PASS**。

共享 V 的原 371 项随后全部取得独立 typed 域证明。`bf16/independent-typed-domain-review/certificate.json` SHA-256 为 `29019b40d80661d614283a21169f62e5d33c5cfc046d925c642e974f884e786e`，包含实际实参转发、SEW16 的 decode 合同、调用前后 LMUL 范围、有限域 helper CFG 及八项负控。特别是 `get_num_elem` 在 guard 前，不采用后续 guard 的 LMUL 上界；最后八项 dirty_v_context 的失败臂实际断言为 hartSupports(Zve32x)，由冻结 Full 能力证明排除，不能误写成 VS 动态寄存器断言。

逐原身份及 remaining edge 消费后，`shared-v-root-caller-typed.json` SHA-256 为 `569fd45143222e603c98f4ce2d5f6760dab1ae4d470ae92fb76edfa03a65dbe0`：**1767 个已列结构候选为 441 actual、941 fixed-CFG 排除、14 overlap 实参排除、371 typed 排除，0 pending**。任何已观察项均不能被排除；不同 helper PC 也不能直接复用这一证明。

结构表之外，共享 V 控制现在单列 `shared-v-control-caller-candidates.json`（SHA-256 `9334ce5b553921f5811ca0d6759b7e2144ef2867d82fb17665cf45db8eb18afe`）。23 个 source site 按 BF 自己的 root 展开 236 项：22 个短路 site 共 226 项，其中 145 有实际 LHS 待规则独审、73 待实参/路径证明或见证、8 有 fixed-CFG 排除；另一个 valid_reg_overlap pc68 的 if 已由原 31-if 独审中的对应项核定，十个 BF root/arm 均有真实见证。控制表独审继续进行，不能以结构 1767 已处理宣称共享 V 全部闭合。

### 替代配置数值关系：准备与审查边界

默认 FD 与 Voff 的数值关系正按同 constructor/fields 和相同体系数值前态证明，不把默认动态 arm 复制到替代配置。`default-voff-numeric-prefix-candidate.json` SHA-256 为 `116a399c7fd89809c4dc965f37c3004bb6bebb61e8d1e58f4b32410ad239b0d9`：六 clause 的十个数值 root、80 个 helper 与 execute 前缀共 4061 个实际 PC 已逐 normalized 完整指令比较相同；所查域没有直接 misa 读取或体系寄存器写。两个 TOML 只差 misa.V，实际 initialized lets 相同。六处 hartSupports 切口、64/128 位寄存器数组读取投影及 guard 接受前提仍需独审，当前状态为 **FOR_INDEPENDENT_REVIEW**，不是新增数值 PASS。

FDVoff 的数值 execute 域须另按实际 misa.F=0、decode 纯读、BF extension⇒F 和各 BF constructor 的唯一受守卫生成路径证明为空。该必要条件不能用于默认或 Voff，也不声称所有 32 位 word 都返回 None。User/Supervisor 仍只报告各自七条的实际观察子集；整个 decoder 的其他 privilege/CFI 路径不在此处等价声明中。

数值关系候选经初审补强为 `default-voff-numeric-prefix-candidate-v2.json`，SHA-256 `394bf72cbdb1c89b987c5297ad3fbb076a429c5293f22759d76f6461c8432de6`。同一 4061 PC 全部通过完整 destination Loc 检查、禁止 Field/Addr 写入、禁止可逃逸 Ref 和严格指令种类门禁；绑定固定入口合同。输入关系显式包含 callback 隐式读取的全部 FPR/GPR/VPR 槽、相同引用向量、合法且相同的索引，以及相同非 relaxed 初始化方式。旧 v1 没有这些完整门禁，保留为准备阶段记录。

`default-voff-guard-projection-candidate-v2.json` SHA-256 为 `12280e3b8aa95139cf6b1b4e0c211148be7f947ef413f6c4539bdf30ed87995e`，按 BF 的实际 Ext 实参切取八个 currentlyEnabled 上下文：实际 getter 只有 Misa_F、Mstatus_FS 和 Mstatus_VS，没有 Misa_V。数值前缀的六个 hartSupports 切口仅含 F/Zfinx；gate 的能力调用及 BF 唯一 mapping 前提由配置语义独审继续核定，两个 v2 候选均尚未据此写 PASS。

FDVoff 候选 `fdvoff-constructor-rejection-candidate-v2.json` SHA-256 为 `6c6b20dd5c9708c8ef0c90bab35ba43e611930b3d1cedb2901fe1da7dd161b65`。其相对初版新增完整初始化合同、实际 runner/IR/config/runtime、逐六例 R1/config_misa/non-target misa 一致性和纯读证书 root/IR/config/三项零写门禁；重核原六例严格审计 SHA 与全部 Jump。候选支持的是 BF constructor 不能由该入口产生的必要条件推导，仍等待独立审定文件。

### 共享 V 控制的三条最小补例准备

73 个未观察 caller 候选中，三项经源算式和精确实参确认可达。`shared-control-frontier3-suites.json` SHA-256 为 `3bcaccbd5f6326ab597fb9051fd098d84752ce13b47f875df0355b157fa4d2cf`，输入 `shared-control-frontier3.json` SHA-256 为 `ffc3a5384e1350f028ae7523f7e9f95f2b7a8250e1947e1269a7611a3dc95f05`，当前 **PREPARED_NOT_RUN**。

| Caller/root | 目标 helper 方向 | 输入与独立预期依据 |
| --- | --- | --- |
| VFWCVTBF16_F_F_V / 51403 | valid_reg_overlap pc119 true | 源 v24 在目的 v16..v17 之后，后续 vstart=64 的既有错误仍在数值运算前拒绝。 |
| VFWMACCBF16_VV / 51620 | valid_reg_overlap pc109 true | 第一源 v8 在目的 v16..v17 之前，后续 vstart=64 的既有错误仍拒绝。 |
| VFWMACCBF16_VV / 51620 | valid_reg_overlap pc52 true | LMUL2 的第一源 v25 未对齐，首个 overlap helper 立即拒绝。 |

三条只改旧已审 Illegal 例的寄存器编码、对应 expected_fields 和身份；initial、observe、expected、expected_result 均逐字保持，来源与逐字段变化保存在 suite。它们未增加数值 oracle 假设，仍须实际运行、R1/全 Jump 审计和确切 root 方向关联后才计入覆盖。

### 共享 V 控制独审消费与配置语义索引

以下继续限定旧 1dcc IR。新版 348147 的同输入运行和源码证书迁移由集成另行记录；本节所有静态结论均不自动迁移。旧动态基线保持 **942 条输入、2754 个终态**；上列三条 overlap 补例继续为 PREPARED_NOT_RUN。

22 个短路 site 的独立主审 `bf16/shortcircuit-proofs/independent-20260927/independent-review.json` SHA-256 为 `9bf0ae835e4ad4deeef36b3b497d816c9fc140b76790f0b8506657b2a026d047`。独审逐 CFG 确认唯一 LHS 定义支配 Jump，21 个源码跨度直接对应，`valid_fp_op:48` 的 `valid_sew` 别名另沿源定义和 def-use 核验；正常 RHS 值路径与五个异常出口分列。原 145 个短路实际义务及十个 overlap-if 实际义务合计 370 份见证已逐 caller、phase、config、context 和身份检查。

[共享 V 控制消费器](tools/solve_bf16_coverage/shared_v_control_review.py) 保留原 236 项身份，消费独审的规则和精确新 root 域证明。`vector/independent-predicate-review/bf-vector-control-domains.json` SHA-256 为 `ced1a1b54e773a2fa6f04d3ee46ad87b4342d89fbfc18b1d27a184a732afdb7c`，给出 24 个固定能力和八个同 constructor 成功 decode 后的 encode 状态排除。`bf-short-typed-domains.json`（同目录）SHA-256 为 `794f93c009e04ba14e1b7d9bc43905a1ee0a3fd5354f213b13244b3c8c17775c`，再给 14 个 overlap、12 个 eew、八个 fp、四个 illegal-width 排除。后者使用实际 BF constructor 的 SEW16 必要条件、vtype 保持和 guard 前 LMUL 保守域 -4..3，没有借用尚未经过的后续上界。

两批域证明分别消费，未将旧 371 typed 证书直接套到新 PC。产物 `bf16/shared-v-control-reviewed-caller-v2.json` SHA-256 为 `1c7c8ccde6dfd38d0a8affc0b582aeb56818eabe3b4fae7885cdc64cbf96586f`；236 项为 **155 actual、70 个独审域排除、三个待真实见证、八个待精确固定调用闭包证书绑定**。三个未决项就是上列已准备 overlap 输入。LHS 表的处理不扩展为无独立 Jump 的 RHS 值或整个共享源码已闭合。新增身份变化、已命中项及重复排除负控先红后绿，完整 BF 工具检查 **55/55 PASS**。

随后八个固定调用闭包义务也完成独审。`bf16/independent-write-default-cut-review/certificate.json` SHA-256 为 `3e676ee5139a1196f3a0f125672e4301e378f9d9a85e1b5c8f429e3bd7d39670`：四个实际 `zwrite_vreg` root 分别绑定 clause 分派、默认配置和入口不可覆写合同；全目录十处 extra-flag 引用无写/逃逸，按真实 wrapper 与下游 CFG 重算的闭包不含 `zwrite_vreg_default`。flag=false 负控则可以到达 default helper。该证明仅用于默认 FD，不能用于 default-lanes 配置。

最终阶段表 `bf16/shared-v-control-reviewed-caller-v3.json` SHA-256 为 `e49b2a5683c80420a1283d8866391a8ff1ec4033cbd81f390a6bd9c6a2a6f095`：**236＝155 actual＋70 typed/capability/state 排除＋八个固定调用闭包排除＋三个待实际见证**。精确 cut 消费的新负控对后继、完整 Jump 或实际见证变化均拒绝；定向四项测试通过。尚未运行的三条 overlap 不计动态命中，RHS 及整体源码闭合边界保持。

默认/Voff 数值与 typed gate 的最终独审 `bf16/independent-configuration-semantics-review/review.json` SHA-256 为 `565dd6e89505c279fc5f3706e11a2ce64b2a428986b5d5dcb136f33699e76595`，状态为 `PASS_CONDITIONAL_NUMERIC_PREFIX_AND_TYPED_GATE_PROJECTION`。它接受前述两个 v2 候选，独核十个数值 root、80 个 helper、4061 个实际 PC，以及九种能力上下文和八种 typed gate 上下文。两 producer 重跑经 JSON 键序及能力集合排序后一致，三个副作用门禁负控均拒绝。能力证明含 `vector_support_ge/num_of_vector_support` 与完整 Full 初始化，不仅依赖 xlen/flen/vlen。

该关系的必要前提是：两侧分别满足共同 R1 和冻结入口合同，misa 仅 V 位不同；分别成功 decode 至同一合法 constructor/fields；数值及 guard 状态相同；callback 引用向量、逐槽 FPR/VPR 值、合法索引及未初始化符号对应，寄存器模型非 relaxed；每次比较发生于对应正常路径及循环调用。结论仅到 typed gate Bool 和数值 helper 的输入/值语义，**不推出体系写回、flags/status 最终值、整 decoder 或整指令等价**。六条 Voff 成功代表均有实际 R1 和三阶段结果；两个 scalar 有默认同完整 bound state 配对，四个 vector 只有同 word/fields 代表，不能宣称已运行同完整初态配对。

FDVoff 独审 `vector/independent-predicate-review/bf-fdvoff-review.json` SHA-256 为 `e4fd82fd620b23f181352b6b46ace91c5525c74164418b313e8bf881017eef02`，状态 `PASS_SIX_CONSTRUCTOR_REJECTION_RULES`。独审逐字节重放 v2，核实际六条初始化/R1、纯读 phase 与严格审计，接受实际 misa.F=0 ⇒ F=false ⇒ BF extension=false ⇒ 六唯一 BF constructor 均不可产生。因此六格的 **decode-first 合法 BF execute 数值域为空**；其他 constructor 仍可能由任意 word 解码，不能扩大为所有 word 均 None。

[配置语义索引器](tools/solve_bf16_coverage/configuration_review_index.py) 将上述独审附到原 18 格，产物 `bf16/caller-config-reviewed-semantics.json` SHA-256 为 `fb261a32526a6b99ec39546e0325de649afd0d9f64a31f40fa977590c361e6e2`。每格保留原动态计数并携带必要前提、精确 root 或 constructor 规则及独审 SHA；动态新增数为零，原代表索引和所有候选产物保留。

### 新 348147 IR：词法目录准备

集成的新冻结候选绑定 IR `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061`、源清单 `1890f0a13d9dc877185c46bcf398ea0b2f12fbe3b0ee6802adb5de0a845f1ed9`。复用 `source_catalog.py --repo <新冻结候选> --source-manifest <候选清单> --ir <新IR> --out <独立输出目录>` 从候选实际五份源码重建，得到 `integration/p1-348147/bf16/source/source-catalog.json`，SHA-256 `2acdf92480de15174072b0dacdf91088591cbb7884f37cf8e8e221d14c9e6498`：26 个定义、60 个 site、136 个 arm、19 个短路因子。五个专属源码文件与 1dcc 冻结同字节；这只描述源码输入，不迁移旧 runtime PC、动态见证或独审证明。

`integration/p1-348147/bf16/source-catalog-input-binding.json` SHA-256 为 `a83d8873d21b60aad20f55988c648733e9eea8dc77e1fdf97a55e24cea582f9b`，保留实际 generation 的原源清单 `749c3c5bba2995ecc048e22fd9baf375e6daec9b677c562b96d3c6d07ec7c911`。候选清单与原生成清单的严格桥接由集成另审，当前状态 **SOURCE_CATALOG_PREPARED_GENERATION_BRIDGE_PENDING**；新严格动态审计尚未开始。

### 新 348147 IR：942 条实际 trace 严格审计

上述准备状态随后推进：共享 `verify_source_snapshot(..., runtime_manifest=..., source_bridge=...)` 接口逐三个实际配置重执行来源桥接，核原 generation749c、完整 v7、候选1890 与 runtime28fb 的实际文件关系。`integration/p1-348147/bf16/source-bridge-bindings.json` SHA-256 为 `33bf3e02a66e9493bda54d51253f03e4e6839c4c02a03bf7220ad7f192750f85`，三配置均为 `source_binding_complete=true` 且桥接 `reexecuted=true`；没有改写原生成源清单身份。

严格动态审计沿用 [trace_audit.py](tools/solve_bf16_coverage/trace_audit.py)，仅为新获准的 `integration/p1-348147/bf16/` 增加精确输出目录；验证逻辑不变。独立调度 `integration/p1-348147/bf16/run-strict.py` 先保存三配置桥接结果，再串行执行 `strict-plan.json` 的九条完整 CLI 命令。计划 SHA-256 为 `42ead7907c5e975fba75331d19bf3c465a99b363cd97fe10b8f27b45ada41570`，绑定实际 full-summary、每组 argv/input/results/trace/初始化/trace-map 和对应 sidecar。

九组全部自然退出 0，**942 条输入、2754 个未采样终态严格审计 PASS**，耗时 254.872 秒。每组均核实际初始化、R1、runner/IR/config、结果与 trace-map 双向守恒，以及新版 **25711 个全部 Jump** 的 function/PC/完整指令/SourceLoc/极性/后继。三个新 sidecar 为默认 `9c5b4ff1e9af7c328190d9f274c754f21046bb286b1dba7e88319fd747ab0276`、Voff `7c6ac88d78c089fe4a7ccb7ac44687a50a43ca870eb8db67909cc15480ead2f5`、FDVoff `a13cdb7ffbd59eff1d7ac80db49e1a4b621788c45fed4572511f81ce21960357`。旧版 25772 Jump 与其 PC/证明没有换标复用。

| 新版组 | 输入 | 终态 |
| --- | ---: | ---: |
| 默认 success / illegal / decode / overlap | 831 / 51 / 30 / 4 | 2493 / 153 / 30 / 12 |
| Voff 四向量 / 两标量 | 4 / 2 | 12 / 6 |
| FDVoff decode | 6 | 6 |
| User/Supervisor success / illegal | 12 / 2 | 36 / 6 |

最终 `integration/p1-348147/bf16/strict-summary.json` SHA-256 为 `7e1363cd1656fceec3b580225aba94d61282fa37035162906a0f4a24f47fc3ab`。九份完整审计逐份保留，摘要记录命令、输出 SHA、返回码和实际计数；运行前后四个审计/桥接工具文件哈希相同。新版仍是 **实际 runtime 边验证，不自动构成源码 arm 映射或闭合**；旧 1dcc 的专属 arm、共享控制、typed 排除和配置语义证明均未迁移。

新版 `integration/p1-348147/bf16/caller-config-summary.json` SHA-256 为 `45833c383c245ac0a948c2ac007d46784f1d53427dbb876eddcb053ea9abb5a9`。它从新版真实结果重建 18 格，逐例将实际 `bound_actual_registers.cur_privilege` 与输入枚举精确核对，记录各 phase/status、输入和终态数。其三配置六 caller 代表仍只表示实际观察子集；旧版有条件配置语义索引没有附到新版。

### 源码合同、BF 引用范围与 RHS 独立账

后续模型将再次生成 IR，本轮暂停新模型运行，先整理能复核、能重绑定的源码合同。旧 1dcc 与新 348147 的动态产物分别保留；两版均为各自实际 942 输入、2754 终态，不相加。以下新增账本绑定旧 1dcc，不新增动态命中，也不表示 `source_branch_closed`。

[合同模块](tools/solve_bf16_coverage/proof_contracts.py) 用完整 `global_site_key`（源码文件、SHA、UTF-8 token byte range、kind、ordinal）、source function、clause、phase、arm/value 和源码 root 调用锚构成语义键。PC 只在具体版本的 `actual_binding` 内。重新消费须分别核新 IR、sidecar、config、source/runtime manifest、实际调用与 typed 实参、CFG/极性/返回数据流、入口与域前提；observed 还必须有同新版严格实际见证。源码变化须先另审语义关系。消失分支只能单列 `not_lowered`，并绑定完整 runtime inventory 与变换审查；不能作为 observed 或 static exclusion。字段门禁要求调用方先核证据文件 SHA，本身不证明语义。

[范围账本工具](tools/solve_bf16_coverage/scoped_contract_ledger.py) 生成 `bf16/scoped-source-contract-ledger.json`，SHA-256 `3cb2fc97bc61c403b47cac383219e166a480a0fe976eb55cd6eaf67c0448534d`。原结构表的 unresolved 列来自整个共享目录：FD 的 94 项中 BF 引用只有 1，V 的 388 项中 BF 引用只有 40；外部 93/348 项不计为 BF 缺口。反向检查完整 BF 源码引用则发现：

| 引用范围 | unique source sites | 已有证据分类 | 未建立 caller 义务 |
| --- | ---: | --- | ---: |
| 共享 FD | 27 | 20 个已有结构 caller site | 7 个完全未建 site 的 28 条引用，另有 1 个部分 caller 未建 site 的 4 条引用 |
| 共享 V | 142 | 66 个结构 site、23 个独立 LHS/if site | 53 个 site，按四 clause 展开 212 条引用 |

未建立义务可能来自条件编译、常量折叠或 BF 实际 raw Call 闭包之外，均仍须源码及完整 runtime 分类证据。三个已准备 overlap 输入只是 LHS 表中的动态缺口，不能概括全部源码未决项。FD 的独立 Bool/短路/RM 控制表继续另计，以上源引用表不替代它。

FD 的额外部分引用是 `dirty_fd_context:111`：其他 caller 已有结构证据，四个向量 clause 的当前引用未建义务，不能借已有 caller 命中消除。其余七个为 `dirty_fd_context_if_present` 两项、`get_F` 两项、`set_F` 两项和非 SYMBOLIC `accrue_fflags` 一项。

[RHS 合同工具](tools/solve_bf16_coverage/rhs_contracts.py) 生成 `bf16/shared-v-rhs-exception-contracts.json`，SHA-256 `0801af0a930710e810b904994ac671f70315b09973d7e48aec59a462ac3e3e02`。22 个短路 site 按实际 caller/root 展开 113 组、226 个正常 RHS Bool 义务：22 项由 11 个 root 的已独审 LHS 域排除 RHS 入口（七个 typed/domain、四个固定调用 cut）；四项消费同 caller 的 overlap 真实返回数据流，均为 RHS=false；**200 项仍待 RHS 值见证或域证明**。工具按 AND/OR 的求值极性选择入口，并拒绝错误 caller/value 或把已观察项排除。

五个 currentlyEnabled site 的结构路径分析还列出同一末端 `Arbitrary`，按八个实际 BF root 展开 **40 项异常候选**。这些不是 Bool arm，也不表示异常实际可达；必须按实际 Ext 参数和完整 CFG 证明或精确见证处理。当前账均为 pending，未把既有 32 项 LHS 域证书扩张成异常排除。正常 RHS 与异常义务分开统计。

本轮旧工具完整检查按每个 `test_*.py` 独立 Python 进程执行，**62/62 PASS**。直接用单进程 unittest discovery 曾因 BF 与 scalar 同名 `shared_control_witnesses` 模块发生导入冲突而失败；该失败属于测试加载方式，保留记录，复现入口改为隔离逐文件运行。

### 未建立 caller 义务的完整 runtime 分类候选

[runtime 分类工具](tools/solve_bf16_coverage/scoped_runtime_inventory.py) 复用共享源码声明跨度和真实 sidecar 读取器，逐实际冻结源码字节核 manifest/generation，重新发现六 clause 的全部 **172 个实际 root Call**。它按整个声明的 SourceLoc 收集 runtime 宿主（包括内联），并保留全部 raw Call 边，未先用配置或后续 guard 裁剪。产物 `bf16/scoped-source-runtime-inventory.json` SHA-256 为 `420cfc4840672773bf19bdf7a45eee7a7530b08aafa3ed16b0117ee3f30ba3b4`，状态为 `CLASSIFICATION_CANDIDATES_ONLY`。

61 个 unique 待分类 site 来自 FD 的八个全缺或部分缺 caller site 和 V 的 53 个 site。FD 原 32 条引用中，26 条对应声明的实际 runtime 宿主在其 BF raw 调用闭包之外，六条非 SYMBOLIC `accrue_fflags` 引用没有匹配控制候选。V 原 212 条引用按 decode/encode/execute 保守展开为 636 条：580 条声明宿主在闭包外，24 条有控制候选，32 条需变换审查后判定 `not_lowered`。这里的 phase 展开数不等于新增已确认可达义务。

24 条控制候选只位于 execute，为六个 site 各四 clause：`assert_vector_num_elem_upto_128:149` match、`assert_lmul_pow:39` match、`read_vreg_default:349` loop、`write_vreg_default:472/474` 两 loop、`init_masked_result_default:316` loop。正常源码跨度与 Jump 共址仍不能直接作为 source-arm lowering，须新建实际 root 义务并消费相应独审。V 负责人已提供共享循环结构证书 `vector/independent-loop-review/certificate.json`（SHA-256 `9fee8e68312bbe784bf68b5874723f423c3f781af89511ffcad267fab2caa183`）；其中 99 个旧 caller context 属于普通 V，BF 实参和上下文需要另绑定。两个 match 的全部 source-arm lowering 尚未审定。

32 条 V 变换候选来自 `assert_vector_num_elem` 的五个 VLEN if（execute 20 条）与 `get_V:237`（三个 phase 共 12 条）；不因候选目录未找到 token-overlap Jump 就宣称静态不可达。原账及所有历史证据保留。新增四项测试先红后绿，检查 raw 递归闭包、内联宿主、闭包外候选，以及缺 SourceLoc 不会自动关闭源码义务。

### 正常 RHS 的通用数据流候选

[RHS 数据流工具](tools/solve_bf16_coverage/rhs_dataflow.py) 从独审机械证书读取 RHS 定义，逐条核实际 sidecar 完整指令；用原 trace 的有序 Jump 和精确 context 重建目标 helper 的完整无环正常返回路径。RHS 局部值沿 Assign、`znot` 和 AST Not 传播，结合实际消费 Jump 反推 Bool；必要时沿真实父 Call 的续体传播至消费边。父调用消费后的循环不影响已经消费的值，目标 helper 仍须完整正常 End。未知运算清除标签，局部 Ref/Addr 逃逸、异常出口和重复调用实例拒绝，没有制造 RHS Jump。

工具先做正常赋值/否定、覆盖、边漂移、循环、异常与引用逃逸负控，再重读旧默认四组全部 **916 输入、2688 终态**。未加载 3.4 GB success 审计为完整 JSON，复用流式读法；逐原审计 SHA、summary/输入/结果/初始化/trace-map、终态和全部 Jump 核验。四组自然退出 0，耗时 112.332 秒，均为零 unsupported。新模型运行次数为零。

| 旧 trace 组 | RHS 候选合同数 | v3 产物 SHA-256 |
| --- | ---: | --- |
| overlap | 77 | `d40625eb70e19b556bc11c807489b5f41395099d4e4f17f69af5f704422dba45` |
| illegal | 141 | `ac66ed6a0cd835335bf474dafea3ed956505398c4f4bf2706090cadf453e6e1d` |
| decode | 36 | `1260690c5d041b8952253dc21ca8043b436a3ad9988bb522c9b4c7934b760486` |
| success | 102 | `ec7f67c546c74fc5e44f55688e00a37dd351f98fffdd3ffb963b08a9705ee718` |

产物位于 `bf16/rhs-dataflow-<组>-candidates-v3.json`。producer SHA-256 为 `8b26fc0202622e349e1ffe3bd5f97c200106d1fadde235015ea8d80e2d8e6853`。早期 overlap v1、三组 v2 保留为阶段候选；最终独审输入为 v3。

[候选索引工具](tools/solve_bf16_coverage/rhs_candidate_index.py) 逐 13 个唯一依赖文件复核 SHA，精确核源码语义键、本版本完整 root Call、Bool 值及排除冲突。`bf16/rhs-dataflow-candidate-index.json` SHA-256 为 `7613af1f9665c4de016a1ab017a0b86c82a823b6b1e056da4457716aed8aceba`。去重后 **175 个 RHS 合同有候选：171 个原 pending，四个复现旧 actual**。原 `proof_status` 保持不变，尚未据此新增 source-arm PASS。

其余 29 个正常 RHS 合同有以下静态证明方向，仍待精确独审：

- currentlyEnabled 的 24 个 RHS=false：八个末项 Zicsr，以及成功 decode 后 encode 的四类 RHS 各四项；需保持实际 Ext、状态不变和 decode-first 合同。
- valid_fp_op 的四个 `sew <= 64` RHS=false：需把 BF 实际 decode 的 SEW16 必要条件绑定到对应调用前状态。
- VFWMACCBF16_VV 第二个 overlap root 的一个 `rd_int % rd_group != 0` RHS=true：前一个 overlap 必须返回 true 才能到达第二个，两个调用使用同一目的寄存器和 LMUL+1。此为前 guard 的跨调用不变量，不能用其它 caller 的样例替代，也不需要据此准备第四条动态输入。

正常 RHS 总账仍为 22 已审入口排除、四个旧 actual、200 pending（其中 171 已有待独审数据流候选、29 待静态域证明）。40 个异常候选由主 coverage 负责人另准备完整 CFG/exception 前提，未与正常 Bool 混计。独立逐文件测试现 **73/73 PASS**，新增 Python 文件编译检查与自有文件 diff-check 通过；三个原 LHS frontier 仍为 PREPARED_NOT_RUN。

### 新 56cc69 候选：源码迁移准备

新候选 IR 为 `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`，源码清单为 `fdf105d19a9ac62f9c5036fbc80759adb7e9b500a51a34fcc4f886016329129e`。BF 专属目录已从候选实际五份源码重建为 `integration/p1-56cc69/bf16/source/source-catalog.json`，SHA-256 `29a3ed7f44d9c0e3b5ea8cf7a8178748c8b9222f09225e562fda0b54e4deffde`。五文件与 348147 同字节，仍为 26 定义、60 sites、136 arms、19 短路因子。

[源码重绑定准备工具](tools/solve_bf16_coverage/source_rebinding_inventory.py) 另对旧共享账及 RHS/异常账的源码键逐实际文件核哈希，产出 `integration/p1-56cc69/bf16/source-rebinding-preparation.json`，SHA-256 `62da2c1fc85e1ee7c4cd0981c38895f776d60f3cfb1607e727221f450994cac1`。共享 169 个 unique source site 中，129 个仍为同字节源码候选，40 个所在文件变化（`vext_utils_insts.sail` 30、`vext_fp_utils_insts.sail` 七、`fext_insts.sail` 三），后者停止旧 global key 匹配，须先审新表达式及跨度。

此阶段为 `SOURCE_PREPARED_RUNTIME_GATES_PENDING`。generation 的 manifest 声明已原样保存，来源桥、严格配置和 runtime gate 由集成另审；`source_binding_complete=false`、`runtime_binding_complete=false`。没有迁移旧 PC、动态见证、排除或配置语义；尚未检查新完整 runtime，所以分支是否消失仍为未判定，后续经 inventory/变换审查后单列 `not_lowered`。本包未启动 56cc69 模型运行。

### 旧 1dcc：175 正常 RHS 与 40 异常的独审消费

上述候选随后完成独审。正常 RHS 独审 `bf16/independent-rhs-dataflow-review/review.json` SHA-256 为 `51bf6b63a824ee51738f73d1c9437d46d4f4fb36f0ce3f3322f5f025b5be6cfa`，逐完整 phase 的 Call/End 栈、所有 Jump 和 instruction_count 复核 916 输入／2688 终态，接受 175 个 RHS 合同、356 份见证。其中 171 个原 pending 转实际见证，四个原 actual 重新确认；不是新增输入。

异常独审 `bf16/independent-exception40-review/certificate.json` SHA-256 为 `d1c5a8dce959dcdae6db68c28373c11607b27c00dcd60cb7a90ebe4e81046e8b`，接受八个 root 的 40 项条件异常排除，保留实际入口 flag=false、固定状态投影、完整正常递归路径和原语总性的前提。异常不作为正常 Bool arm。

[消费器](tools/solve_bf16_coverage/rhs_review_consumer.py) 逐完整合同身份及证书依赖核 SHA，生成 `bf16/shared-v-rhs-exception-reviewed-v2.json`，SHA-256 为 `0da9ffe4ef96fb3e985e089c39680ca2bc88aa8bd016afdfb17686a7e0b68933`。旧 226 正常义务为 **175 actual＋22 已审入口排除＋29 pending**；40 异常均携全部独审条件单列排除。所有结论仍限旧 1dcc/default。

29 项静态候选已准备为 `bf16/rhs-static29-candidates.json`，SHA-256 `b9ac6be57ca09d7be4beef3bbffc15634eda61d22e422bd399e0288c6066589c`，状态 **FOR_INDEPENDENT_REVIEW**。24 项 currentlyEnabled 重跑 32 个 FS/VS×扩展投影并重放逐赋值值；四项 valid_fp_op 重跑 SEW16×八种 RM 的正常路径；一项第二 overlap 从先前调用支配、先前 false 不能到达第二调用、helper RHS=true 导致正常返回 false 构成候选。目的参数保持及模数表达式依赖仍列独审检查，不借旧证书签名增加排除。

### 新 56cc69：实际来源桥、942 严格审计与三条 overlap 增量

此前初步准备记录保留。最终 generation SHA-256 为 `9f01067ea8f2da31b37f5089e4c5870e47e8299f7622b9a456585a0648176a77`，v3 来源桥 SHA-256 为 `388f295c34f02f426a70899cb1960ff77ca176a3c5c60cb63adce2a85d8cc9c0`。driver 使用独立 `runtime_binding_v3.verify_source_snapshot`，显式绑定原 runtime28fb。三个实际配置均重执行来源桥且 `source_binding_complete=true`；`integration/p1-56cc69/bf16/source-bridge-bindings.json` SHA-256 为 `554acb2ac27f8048f50f6bf68e5b62284bbab52f8bcc85d8e0a91edbbb493a70`。

新九组计划 SHA-256 为 `aba884d5d9bf085654757791d1d6cb1db9a306b99dc8bc2c7ef5ceeb8bef4284`。实际输出、终态数与 sidecar 全部重新读取，不复制旧动态绑定。九组自然退出 0，**942 输入／2754 未采样终态严格 PASS**，耗时 212.403 秒；各组实际 R1、初始化、runner/config、结果/trace-map 守恒以及完整 **25676 Jump** 逐项相等。`strict-summary.json` SHA-256 为 `17d6b55da3e47c9f913d17a73df0dc91b63674c6a9ccaf2340fbe076af5ff56e`。`caller-config-summary.json` SHA-256 为 `01c659b96220af60d58e690120c50910dc8886d0e9354b1af1a21b4760899985`，18 格全部从新版真实结果重建，逐条实际 privilege 与输入相等。

主集成另外运行三条已准备 overlap 输入，本 owner 仅审其产物。三条／九终态严格审计 `overlap3-trace-audit.json` SHA-256 为 `e9ad55f8d5b688519d89e123f14e034e4d833ba1b0065e6d6868f95c07e91235`。按新源码左右操作数和实际 root 调用表达式重新绑定后，`overlap3-source-frame-binding.json` SHA-256 为 `7520b1e2e9d3f0619cd84c5199162c0c7d6ee7573fa70b6ac5d26ec3c668e6b8`。全部九个完整 phase 的 Call/End 平衡、Jump 顺序与 instruction_count 均相等，三个实际方向为：

| Caller | 新 root／helper PC | 新源码 LHS 值 |
| --- | --- | --- |
| VFWCVTBF16_F_F_V | 51403／119 true | `rs_int >= rd_int + rd_group`，24≥16+2 |
| VFWMACCBF16_VV | 51620／109 true | `rs_int + rs_group <= rd_int`，8+1≤16 |
| VFWMACCBF16_VV | 51620／52 true | `rs_int % rs_group != 0`，25%2≠0 |

新 `vext_utils_insts.sail` SHA-256 为 `72d1b65b7fc0d5e01337536c24feeac57324bf1015a6639937b9d594de0e49a9`，三个 `|` 的 token 起点分别为 3671、3639、3520。PC 恰好与旧版相等，但未用于选择新绑定。此为新实际 runtime 方向及本地源码/CFG 重绑，独立 lowering 签收仍待完成；三例与 942 基线分开，旧版三例 PREPARED_NOT_RUN 的历史描述不改为旧版已运行。

### 新 56cc69：正常 RHS 的重新准备

复用 V 新目录及冻结短路候选/CFG工具，在实际新源码与完整 sidecar 上重新执行，482 个共享候选 group 通过本地词法/CFG检查。针对旧 BF 的 22 site，以同函数且左右操作数 token 相等选择关系候选：**17 site／186 正常 RHS 合同保留**，五个 site／40 旧 RHS 合同的短路已在新源码改成严格 Bool 运算。五个site所涉两个helper的完整新 runtime 记录在此阶段仍只列 `not_lowered_candidate_requires_transformation_review`，没有记作 observed 或静态排除。

`integration/p1-56cc69/bf16/rhs-rebinding/contracts.json` SHA-256 为 `705030fc6686a55c81fa57d45baadb591f982cda73af3061c4249bd7c99963fc`，机械候选 SHA-256 为 `fe6c776334f16fbfd43d82592b33bd36bec65129acfbb0067d4ed9f6a7d36332`。所有新合同从 pending 开始，root 按新 sidecar 源码调用锚重建，未搬旧 actual、域排除或异常证书。

冻结 RHS producer 重读新默认四组 916 输入／2688 终态，四组均零 unsupported。新 `rhs-baseline-candidate-index.json` SHA-256 为 `4a3df43883c63039be83759abb12861ee8e8e3a284c0775057b2de400da034b7`，得到 **139 个正常 RHS 合同候选、47 个待见证或域证明**。它们仍须新完整 phase 数据流和源码独审；旧 175 独审不扩签。新增三例另存 `rhs-overlap3-candidates.json`，SHA-256 为 `a730af31be723dc0244bbb8c6d4540d56b6ce6829c167218a16076d8cac96b71`，36 个候选见证、零 unsupported，不增加 942 基线分母。

本轮新增静态候选与源码选择负控先红后绿。自有工具按独立进程全量 **86/86 PASS**，八个新/接续 Python 文件编译通过。根状态、结果和共享发现由主 coverage 汇总；这里仍不声明 BF 共享源码或全 77 已闭合。

### 旧 1dcc：29 条静态独审正式消费

随后独审 `bf16/independent-rhs-static29-review/certificate.json` 以 `PASS_29_CONDITIONAL_RHS_EXCLUSIONS` 签收 24 条 currentlyEnabled、四条 valid_fp_op 和一条第二 overlap，SHA-256 `c756ff99babf88353874cfc8f2ee3c14f5fa5e2e84447873bc767937a054cd77`。[静态消费器](tools/solve_bf16_coverage/rhs_static_review_consumer.py) 核完整合同、root、实际 RHS 定义 PC 及动态冲突，保留所有独审条件与限制。

新旧版独立列账：旧 `bf16/shared-v-rhs-exception-reviewed-v3.json` SHA-256 `45976cbcc5781325c5898cf9210f6a9f3d89df77f6286330f8f67002f3b4d432`，226 条正常 RHS 为 **175 actual＋22 入口排除＋29 静态条件排除，无正常 pending**；旧40异常条件排除不变。动态新增为零，不能据此改变56cc69的新合同状态。

### 新 56cc69：919 输入完整栈重核与独立签收

新基线916输入与三条增量合计919输入／2697终态。`rhs-919-candidate-index.json` SHA-256 `8e505ce981d0739d5f0bd6ea9d795394a08023772f50914a22011db9988e2fad` 收集139个唯一合同、327见证。[完整栈重核工具](tools/solve_bf16_coverage/rhs_frame_check_p1.py) 在新版实际数据上重新运行冻结通用算法，核完整phase的全部Jump、Call/End及instruction_count、精确root、helper正常End和真实消费。其本地结果 `rhs-919-complete-frame-check.json` SHA-256 `17db487580c01f25108f78418e34a91871874bf45d847856141aa2d49505eaf3`，本地复核不替代独审签名。

随后 `bf16/independent-rhs919-review/certificate.json` 独审状态为 `PASS_139_NEW_RHS_DIRECTIONS`，SHA-256 `0cfd132b3ded18ab45a8c2f9a42042e8bf1da2e9306037582b5038c6a56a0577`，接受 execute83、decode36、encode20。三条增量的36份RHS见证全部已有916基线合同，`new_over_baseline=[]`，不能另加36。[新版消费器](tools/solve_bf16_coverage/rhs_review_consumer_p1.py) 保留完整新合同及剩余47，不使用旧175/29/40证书。

消费产物 `bf16/rhs-reviewed-v1.json` SHA-256 为 `7ca5c7ca2e889f7d8126db7ccf7260238ede33e25f1b1b5938cbdb4d9cbedff8`，状态 `139_EXACT_RHS_ACCEPTED_47_PENDING`。327份独审见证逐精确合同与RHS定义消费，原新合同文件保持不变。

三条增量另由 `independent-bf-slide-fs20-review/bf3-certificate.json` 签收三个 **OR LHS=true、RHS跳过**方向，SHA-256 `3983b111feacf671fa3b87e98a8dd0bf52ed3c8a09d5ab645ae2b15e3b335ee9`。该证书只限新default/Machine、列定source/root/frame。[精确消费器](tools/solve_bf16_coverage/overlap3_review_consumer.py) 生成 `bf16/overlap3-reviewed-directions.json`，SHA-256 `1627157a25d3062c5580268a50c890c2bc0da0b91e4433de2ff5c9d90352cb2f`；正常RHS值接受数为零。

### 新 56cc69：47 条静态与40条消退候选

[新版静态生产器](tools/solve_bf16_coverage/rhs_static47_candidates.py) 输出 `bf16/rhs-static47-candidates.json`，SHA-256 `acfb5a383baf0ec0c5e1fd18c7ada94a37366ddfa4db55b2f553c63e6b844aaf`，状态 `FOR_INDEPENDENT_STATIC_REVIEW`。全部root、源token、RHS定义和实际调用均使用新版本，旧独审仅提供冻结通用算法，不借旧PC或签名排除新合同：

- currentlyEnabled24：32个FS/VS×扩展状态投影、完整递归frame和每次赋值、实际RHS到返回链、新caller异常流、成功decode构造器控制前提，以及新版runner同前态绑定。
- overlap15：五个新root的完整constructor CFG和唯一SSA，bv5寄存器与有符号三位LMUL域，窄化/扩宽共16384个静态类型组合。14项没有LHS入口；一项第二root要求第一root成功、相同目的SSA及相同目的LMUL。撤前结果条件的负控可到第二root。
- write-default8：四个新write root、全flag引用、默认真实初始化及非Target不可覆盖入口、flag=true的完整raw模型调用闭包和false负控。外部调用叶声明完整保留，其runtime不回调模型或改内部配置的义务交独审。

**phase前提尚未满足**：scalar的phase-purity v2原报告漏 `current_exception`、`have_exception`、`throw_location` 的隐式写入，独审为 `FAIL_FULL_PURITY`。本包拒绝完整无写结论，冻结失败报告到 `bf16/phase-purity-v2-failed-review-snapshot.json`，SHA-256 `6c04be608dc4691b8291edb2a95b47fd26b7ad3949cfcd4cd4a387b0617a3615`。24条currentlyEnabled候选明确保留phase传播条件，等待架构寄存器/显式let与框架异常scratch分别审定的新合同；不剪掉异常路径。

[消退候选工具](tools/solve_bf16_coverage/rhs_retirement_candidates.py) 输出 `bf16/rhs40-retirement-candidates.json`，SHA-256 `690a103fd9f5c2c65612b9ac884df27ee25b5930dc6e40d903f720a71f2e358b`。它把五个旧site的源码表达式哈希、40条完整旧合同身份、新root、两helper的完整新源码与typed body绑定到V4变换证据；实际两helper无Jump/Goto/Exit/Arbitrary。该包仍为 `FOR_INDEPENDENT_TRANSFORMATION_REVIEW`，控制消退和新Bool值义务分开，40条新值域/消费义务保持pending；V的LHS14不作为BF40闭合证据。

本轮新增工具负控先红后绿，自有逐文件独立进程测试 **96/96 PASS**，八个接续Python文件编译、自有文件尾空白及diff-check通过。本轮未启动模型运行。静态组合数不计动态输入，新增消费也不改变942基线及三条增量的独立分母。

### 新 56cc69：40 条控制消退独审消费（历史v1值义务标签）

后续独审 `bf16/independent-rhs40-retirement-review/review.json` 签收精确五个旧site／40条旧RHS控制义务，SHA-256 `1512a3eeacffd385b4b5e7ee5266b1cf76f768db4c3858dfa091e82d9ebe2c56`。核验文件 `verification.json` SHA-256 `d7ab08c473c8884e9f88a470523521e2a5273b7d93efd0e61812dd4c680227bc`，最终一致性 SHA-256 `11e47d068e1a3679892772b481d069952b1b5472f447e5b8fbe83e5c9b6144f2`。证据绑定新四root、两个helper完整28/12条指令及六函数纯闭包、实际typed body/完整IR、重新执行的v3来源桥。

[消退消费器](tools/solve_bf16_coverage/rhs_retirement_review_consumer.py) 逐旧完整合同字节hash、语义键、旧/新版本、新完整root及中间Call消费证书，复核116个直接证据和最终一致性所列文件。产物 `bf16/rhs40-retirement-reviewed-v1.json` SHA-256 `6f7ec869a9ea3cbfd10a0fb546621c875b4bf174f2f747a83463ff62167231b8`，状态 `40_LEGACY_CONTROLS_RETIRED_40_NEW_VALUES_PENDING`。

账本并列保留 `accepted_legacy_control_retirements` 的40条 `not_lowered` 与 `new_value_and_consumer_obligations` 的40条pending，后者分别有新版义务ID、历史语义方向、新root/中间Call和待证组件域。组件等价仅限RV64/vtype64、SEW恰8/16/32/64、rd5/vm1/rm3；尚未由本证书证明BF caller实际值域及返回消费。动态新增0、静态值排除新增0、`source_branch_closed=false`，V的LHS14不入BF计数；139已审＋47待审的186条保留短路RHS另账，原文件与旧证据均未修改。

新增三项消费负控先红后绿，检查旧合同字节与新root漂移、控制消退不能提升值排除。原96项与新增3项均通过；新增Python编译、自有文件尾空白和diff-check通过。本次无模型运行。

### 新 56cc69：架构裁定修订当前集成分母为8

后续架构审查修订了上节的计数口径：五个旧短路site的40条RHS方向仅属于历史迁移与已消退控制义务。新源码采用严格Bool表达式，其中间值不是branch，不能照旧 `5 site × 4 root × 2 RHS` 复制成40个新site或40个当前集成合同。此前 `rhs40-retirement-reviewed-v1.json` 的字节和“pending40”字段保持不变，现明确记作历史候选标签，非当前分母。

当前集成按四个实际execute root **51181、51395、51611、51890** 各经 `illegal_fp_variable_width` 调用 `valid_fp_op` 与 `valid_rd_mask`，共 **8个callee-instance合同**。每个合同需审typed域、完整返回公式、SSA聚合和caller Jump消费及其前提；生产器由主coverage独占维护，本包只消费后续证据。这里不将严格Bool值扩张为源码分支。

[迁移修订工具](tools/solve_bf16_coverage/rhs_retirement_ledger_revision.py) 生成 `bf16/rhs40-retirement-migration-v2.json`，SHA-256 `adbff5a5f7f03d37f97069ba352d99921270a22cf4b4acff2862932f660fcb1b`。40条 `migration_links` 精确多对一关联到8个新callee-instance：每个valid_fp_op实例关联8个旧键，每个valid_rd_mask实例关联2个旧键。目标键保留完整新版本、clause、phase、root及helper Call；正式contract ID待8合同生产器指定后逐项绑定。它不生产或接受typed域及消费证明。

旧5site／40控制的独审 `not_lowered` 结论保持；当前待审集成合同为8、由严格Bool值新增源码branch为0、动态与静态值排除新增均为0。保留短路139已审＋47待审另账，不能与40历史标签或8集成合同直接相加为源码分支方向。修订工具新增三项TDD先红后绿，检查40→8关系、callee错配和重复旧键；Python编译及文档格式检查通过。

### 新 56cc69：47 条限定范围静态独审正式消费

`bf16/independent-rhs-static47-review/certificate.json` 正式独审SHA-256为 `1bcb196431dbc217840e126514b0471e0f2f280307044b09af34282bdb1fc9ff`；返回依赖附证 `return-dependency-review.json` SHA-256为 `52628de2a6b5be5d8599b9a9ca544d1dc66acb9b637c35a24470898602e740c7`。附证在32投影的值与路径均仍相同后，独立拒绝以等值表达式替代实际RHS返回依赖，主证书未改写。

[新版限定域消费器](tools/solve_bf16_coverage/rhs_static47_review_consumer.py) 核精确合同、源码lowering与实际RHS定义，逐文件复核证书、附证及phase合同依赖；输出 `bf16/rhs-reviewed-v2.json` SHA-256 `76ca654169fc58e9034376635c0aa271a3f7c222781a3ae8e77e8b79856479d6`。139条已有动态合同及全部见证保持逐字一致，47条只按以下范围分类：

| 数量 | 正式状态 | 必须保留的范围 |
| --- | --- | --- |
| 15 | `STATIC_EXCLUSION_IN_BOUND_CALLER_DOMAIN` | 新constructor/root、bv5寄存器和LMUL[-4,3]保守类型域；第二overlap另需前root成功及目的SSA相同 |
| 8 | `STATIC_EXCLUSION_IN_BOUND_CALLER_DOMAIN` | 新默认配置的内部extra flag、初始化优先级、不可覆盖入口及完整调用前缀/闭包不变性 |
| 24 | `CONDITIONAL_EXCLUSION_NORMAL_PHASE_ONLY` | 四decode、20 encode；正常phase、同前态、正确返回类型及例外状态前提 |

每条合同原样携带 `scope`、`required_premises`、`unclosed_outside_scope`、`local_proof` 及独审限制。`can_close_exact_scoped_obligation` 只关闭该范围内义务，不能改写成全局无条件排除。186条为“实际见证或限定范围排除”的精确合同分类，`source_branch_closed=false`，无条件全源码排除数0、动态新增0。

24条条件排除联立 `scalar/phase-state-contract.json` SHA-256 `6ced618d84130dbdb366c0e1c51bcedaae4726109388792ef884406aa75d51f8`，其normal-return独审SHA-256为 `7f60693560ae1733d76305313876378a3a76ef1725511f77d9e969f85241b648`。完整闭包每root的12个异常scratch写仍为FAIL；窄范围结论要求新LocalFrame入口 `have_exception=false`、显式lets不覆盖三scratch、无函数假设替换或局部/参数shadow、完整root由正常End返回。实际case还须SAT、非Poison及正确Ctor/Bits类型；encode另需同constructor成功decode与同一原始前态。没有证明所有输入正常终止、Poison/Arbitrary或域外调用不可达。

本次不处理或扩签消失site、8个新V4集成合同及旧异常40；40→8修订账通过独立引用保留。新增四项消费TDD先红后绿，检查精确身份/动态冲突、完整条件保留、拒绝无条件升级及错误callee范围；Python编译与文档格式检查通过。本次没有模型运行。

### 新 56cc69：8 个 V4 集成合同正式独审消费

`bf16/v4-value-integration/candidate.json` SHA-256 为 `05cbe2e91bd567b80adb617703b00c4312d4289d91312625f2ef6375f87284c0`，包含四个实际execute root各两个helper实例。正式独审 `bf16/independent-v4-call-integration-review/review.json` SHA-256 为 `e833094953c48d18a14194ebbf04c8422f825e8fd51563450c5553c24a9e7e2f`，状态 `PASS_SCOPED_EIGHT_ACTUAL_V4_CALLEE_INTEGRATION_CONTRACTS`；其文件索引SHA-256为 `63be647a7fc38ad934ca5468e545ca703b06469369d4a6cc83665d1532d5c7a6`。证书报告13项测试、11项负控通过；本次消费重核其测试日志及工具哈希，没有重跑模型或独审语义算法。

[V4消费器](tools/solve_bf16_coverage/v4_integration_review_consumer.py) 只从正式 `accepted_contracts` 接受8项结论，证书 `contracts` 中的候选状态仅核快照。逐项重算canonical ID和迁移目标ID，比较完整新版root/helper Call、返回公式和全部旧键，保留全部accepted前提、候选scope及独审limits。候选的126个引用、独审runtime绑定和完整文件索引合计134个路径均重新核SHA通过。

新产物 `bf16/v4-value-integration-reviewed-v1.json` SHA-256为 `d2c7c72c368f258155319c792876a292526342abeebf753963c4565392bdd16b`，与此前 `rhs40-retirement-migration-v2.json`、`rhs-reviewed-v2.json` 并列保存。旧产物和生产器字节冻结：

| 项目 | 本次接受结果 |
| --- | --- |
| 当前V4集成分母 | 8个callee-instance，全部限定域接受，pending为0 |
| 40条历史控制键 | 多对一关联8个已审合同，链接状态均为 `legacy_transformation_discharged` |
| 新增源码branch／动态见证／无条件全源码排除 | 均为0 |
| 保留短路RHS | 原139实际＋23caller域＋24正常phase条件账不变 |

范围仍为56cc/default四root，RV64/vtype64、typed且非Poison。SEW实参来自正常get_sew，域为8/16/32/64；mask调用须此前valid_vtype=true，fp调用另需mask=true。仅接受抵达实际root/helper、SSA参数保持且其他predicate正常Bool返回时的值公式与caller消费集成。helper总性只联立已签组件域；不证明LMUL、get_num_elem、valid_eew_emul、overlap或Illegal_Instruction总性，不将其他callee异常/截断改为正常Bool。

8项关闭本范围的V4值集成缺口，40旧键为历史迁移消退，不能写成40项新排除。`source_branch_closed=false`；完整phase无写、全源码闭合、全局终止及域外行为未由本证书证明。139 RHS和47静态合同、旧异常40分别按原账范围保留。

本次消费器共10项TDD先红后绿，包含4项候选绑定及6项accepted消费检查，覆盖ID/root/公式/旧键错配、候选冒充接受、缺失或重复合同、丢失前提及计数升级。定向命令为 `PYTHONDONTWRITEBYTECODE=1 python3 agents/float_support_review/tools/solve_bf16_coverage/test_v4_integration_review_consumer.py`；实际消费命令见[工具说明](tools/solve_bf16_coverage/README.md)。两个Python文件编译、自有文件尾空白及diff-check通过。无新增模型动态运行。

### 新 56cc69：依赖重定位附录，不改语义接受范围

后续活动模型工作修改了 `sail-riscv/model/extensions/V/vext_fp_insts.sail`，原组件历史依赖中的活动locator不再返回此前SHA。56cc冻结快照仍保留同SHA原字节。此前v1在消费时的134路径复核是历史结果；现在直接重跑原producer仍按原locator强验并拒绝漂移，不能静默替换路径或改写旧账。

重定位候选 `bf16/v4-value-integration/dependency-relocation-candidate.json` SHA-256为 `84e15597a4c07347d6346dc6847f9ff41f3a71cdcf49b9714958a744d43bbc1b`。正式附证 `bf16/independent-v4-call-integration-review/dependency-relocation-review.json` SHA-256为 `94d0eb196cfa46affc1c219d5517b746569bbf5a52ad96059850230c47ab9b65`，状态 `PASS_SAME_BYTES_EXPLICIT_DEPENDENCY_RELOCATION`；附索引SHA-256为 `a20f60dffc4833f5f181955761d17730a152337f9d79d787d78f885123431e1f`。独审5项测试含4项有效负控通过，许可限定15条完整 `allowed_mappings`。

[重定位消费器](tools/solve_bf16_coverage/v4_dependency_relocation_consumer.py) 先核正式附证、原candidate/review/accepted-v1、manifest和v3来源桥，再按已签精确locator选择快照路径，校验原SHA及manifest模型键。未列路径在原位校验，失败立即拒绝；不按哈希失败搜索备用路径。126条候选原定位合并为124条resolved文件绑定，原账134条依赖合并为132条；15个定位替换中有两个目标已在原账存在，因此同SHA合并。

新账本 `bf16/v4-value-integration-reviewed-v2.json` SHA-256为 `af52904b2f6c96d2b88bb849c8677ef7eb99f4c9808b2d935b1a20024d8e3f04`。仅 `verified_dependencies` 更新为132条，新增 `dependency_relocation` 保存许可、精确映射、计数、限制和consumer/test绑定。除这两个字段外，全部顶层数据与v1逐项全等，包括8个合同ID、accepted前提、scope/limits、40条 `legacy_transformation_discharged` 链接及8/0/40/0计数。旧candidate、主证书、索引和accepted-v1均保持原字节。

本次只修订依赖定位，未重新执行语义算法、SMT或模型动态运行，不增加语义许可。`source_branch_closed=false`，原正常typed／非Poison范围及所有域外未决继续有效。新consumer10项TDD先红后绿，覆盖许可状态、映射扩大、非ASCII语义投影、ID变化、manifest/目标错配、快照字节变化、未列文件漂移及禁止失败后回退；两个Python文件编译、文档尾空白及diff-check通过。现行可执行命令见[工具说明](tools/solve_bf16_coverage/README.md)。

### 新 56cc69：官方 encode-first 的四方向候选及完整总账缺口

[官方候选工具](tools/solve_bf16_coverage/official_encode_witness_candidates.py) 复用冻结 scalar 独审栈算法，重新完整扫描两份 BF 官方 trace，并绑定当前 source token、constructor Kind、typed root、FS getter/`neq_bits` SSA 和实际 Bool 消费。候选 `integration/p1-56cc69/bf16/official-encode-fs0-candidates-v1.json` SHA-256 为 `51b3e3b4752207de1c40781f731424ec6086bdadd11adbda5e51a5c1e8d32993`，状态 `CANDIDATE_REQUIRES_INDEPENDENT_REVIEW`，已交架构独审。

两条官方非编码终态来自 `FCVT_BF16_S` 和 `FCVT_S_BF16`，各 case-id=1、FS=0、Machine。完整输入分别为1873/1657终态、12121665/10648311边；所选路径各549边、7次Call和6次End，保留wrapper与encoder的两帧开放栈，真实终止为 `zencdec_forwards:31276` MatchFailure。四候选方向为两个mapping guard拒绝及两个 `Ext_F` 的FS LHS=false、RHS跳过；RHS值未观察，不合成encoder End。11项范围负控通过。本次无新模型运行、无候选自行签OBSERVED或新排除，现有RHS186账范围不变。

**此时尚无当前56cc的完整BF source/caller总账。**旧169共享source site和172 actual root仅作为逐键迁移清单：129同字节site仍须新runtime绑定，40变化site须当前token/表达式重映射，不能搬旧PC或旧签名。旧61未分类site/668分类、244无caller源码引用也不能直接充当当前分母或已签排除。

已获架构允许建立完整分母候选：从六constructor各phase的当前源码及typed root向所有Sail callee/mapping谓词求固定点，包含core、prelude、RM、IEEE分类及异常；保留普通CPP宏分支、source-only、runtime-active、编译消退和未解析项。按source/arm、constructor、phase/config、entry域及实际root/SSA归账，共享source去重但caller前提不合并。official encode-first与audit decode-first分别保留，局部分账仅通过精确键与范围引用，不相加为全分母。24项正常phase条件排除的域外、完整phase异常scratch无写、全局终止及异常/Arbitrary行为继续OPEN；BF8的窄值域集成不能替代这些义务。

### 新 56cc69：四个官方方向正式接受

官方 BF 独审 `bf16/independent-official-encode-fs0-review/certificate.json` SHA-256 为 `38fb11907728aa4119444005a96ab6096d48acda917fb3d0b1471a25ab261b24`，状态 `PASS_SCOPED_OFFICIAL_DIRECT_OBSERVATIONS`。[精确消费器](tools/solve_bf16_coverage/official_encode_review_consumer.py) 重新校验44项依赖，并逐项比较source key、actual root/SSA、原始终态、真实边、Call/End链、Bool标签及版本；8项消费测试通过。

产物 `bf16/official-encode-fs0-reviewed-v1.json` SHA-256 为 `03cd9b5d19857279af6e8b32cd54b953e6c4c411114fb2ca19294ae6c769f4d3`。正式接受 **3个global source site／4个caller方向**：两条mapping guard拒绝，以及同一个FS LHS site经两个BF root分别观察为false。只限官方encode-first两条Machine/FS0/RM_RUP实际终态；RHS值新增、模型运行新增、静态排除新增均为0。scalar61与这4条精确交集为空，65只是所选范围的集合并集；不改scalar剩余109、BF186 RHS账或完整source闭合状态。

### 新 56cc69：完整源码总账候选、独审发现与v3修订

前述“尚无当前总账”的缺口已有实际产物。首版 `bf16/full-source-caller-inventory-candidate-v1.json` SHA-256 为 `ab0461d0eb2056bc4439c38bec532dd67b9316662f0512edc85aa0992802a30b`。其**完整性为FAIL**：独审发现未识别 `private function`，实际漏掉Stateen三个getter的六个if/match；八个BF foreach物理token被loop/foreach两套kind重复登记，且位向量OR及未认型operator曾混入source方向候选计数。原产物及producer字节冻结，历史计数不作现行分母。

v2重新扫描全源码声明并重算双闭包，独立处理private声明、普通CPP编译域、loop别名、数据操作和Bool待认型项；另接BF4正式证据与五个已审短路消退点。其SHA-256为 `f81452dc111b32d920497b63f952af41939cb683c6e027fdb1c970170f24651e`。随后独审指出注释示例中的 `let` 被计作声明，虽然未进入当前可达集合，仍保留该解析缺陷。

现行[候选工具v3](tools/solve_bf16_coverage/full_source_inventory_v3.py) 屏蔽注释、字符串及嵌套块注释的声明伪头，并按当前typed `or_bits`/`and_bits` 定位数据操作。`bf16/full-source-caller-inventory-candidate-v3.json` SHA-256 为 `a90821034f04771fd234973484d879396ad65d1a9f8965372e20d4ffca6860ce`。状态仍是 `DENOMINATOR_AND_MIGRATION_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW`，**`denominator_complete=false`、`source_branch_closed=false`**：

| 当前候选清单 | 已完成工作及限制 |
| --- | --- |
| 223个model/sail-lib源码文件、5972个声明 | 逐文件核当前manifest字节；全源码调用引用与typed raw调用共同求固定点779个声明，包含core、prelude、RM、异常及Stateen |
| 795个唯一词法site | 242控制候选、360 mapping合同候选、159待认型operator、18已签限定范围Bool operator、16typed位向量数据操作；这795不能直接叫已审branch分母 |
| 172个当前实际root | 全部从当前源码声明/调用锚与typed Call重新枚举；172个旧root逐一唯一关联，旧PC不用于选择，新实参/目的SSA保留，不迁旧见证 |
| 169个旧共享source site | 164个当前token关联，且所属整声明字节、macro context逐一相等；其余5个精确连接正式site退休及40→8集成关系，不制造新branch或排除 |
| 61个旧未分类site | 已逐条重查当前源码声明和root固定点；旧668分类及244无caller引用不作为当前排除 |
| 编译域与entry域 | 39个普通CPP source-only site保留独立backend/entry；Isla audit decode-first和official encode-first分别归账，八个foreach/loop别名只登记一次物理token |
| 精确证据引用 | 3个audit LHS＋4个official自身方向按原范围接受；RHS139 actual＋47 scoped仅在audit账，official186保持pending；8个callee集成另账，不与source方向相加 |

当前9410个source/caller/phase候选行以root和arm细分状态。其中source方向22529 pending／7 observed、mapping合同122168 pending、未认型operator10984 pending、普通CPP方向156 pending分别记数，**这些保守词法义务不能相加为已确认可达分母**。仍有120个声明含未解析call/constructor/builtin候选、76个外部runtime caller叶待合同；词法闭包、重载、mapping方向、类型和预处理域的完整性继续独审。24项normal-phase排除的域外、异常/Arbitrary、完整phase无写及全局终止仍OPEN。

v3的14项测试包含注释/嵌套注释伪头、private声明边界、带括号constructor、局部let、数据位或、闭包环、源token消退与重复上下文、禁止按旧PC选root、普通候选不得升级及normal-phase不得迁官方域。原v1/v2测试及字节均保留；没有新模型运行。

跨族身份检查另复用冻结 `solve_fix_integration/audit_global_sites.py::validate_site`：795个BF当前site与211个scalar、93个scalar control、879个vector、7个library factor逐token/hash/global-key核对，零身份错误。共有218个BF物理token跨族共址，零跨族kind冲突，未合并caller前提或迁移其它族证明。报告 `bf16/full-source-cross-family-identity-v1.json` SHA-256为 `15eb85b1a492f5b6019afb7d77d1e722e196ac8c0d3d49f2e4e1a0a39a2cd774`；该结果只证明源码身份一致，不证明全分母闭合。

### 新 56cc69：有限分母准备与三配置总账正式复审

有限独审 `bf16/independent-full-source-denominator-review/review.json` SHA-256 为 `bbe7c86df8ed46f6fe2eefe5ddde7c21ca2c8a4072b42f127e6ebd90bf5e8b65`；12文件索引SHA-256为 `3eee6b1ccb3616bb6ea78e8b3ab1e9dca3db619b47b8d9b9d21ca9402c2d2559`。其状态为 `V1_COMPLETENESS_FAIL_V3_SCOPED_CORRECTIONS_ACCEPTED_FULL_DENOMINATOR_OPEN`，只消费 `accepted_preparation_scope`：接受223文件、172实际root、18阶段调用闭包、795唯一token、164声明身份、5退休点精确引用、8非计数循环别名、16typed bits、39普通CPP site及原7方向链接。**779声明的源码语义闭包、795最终分母、mapping/match/loop、未知operator和中间callee可达输入域仍未获签。**v1失败历史保留。

[三配置工具](tools/solve_bf16_coverage/three_config_ledger.py)分别重新读取default、alternate-v-off、alternate-fdv-off三个实际sidecar，每份377980指令；typed字段逐项相同仅用于定位，不能推成配置值语义相等。v1产物 `bf16/three-config-source-caller-ledger-v1.json` SHA-256为 `e02df787ec0a88156014191865eff2450617f0f19182a569bd73724e7580aa8c`。[callee实例补齐工具](tools/solve_bf16_coverage/config_integration_completion.py)产生v2 `bf16/three-config-source-caller-ledger-v2.json` SHA-256为 `d7389a39cdd2281017e8dcdc5a8fad1cd19095ca458535bb2888c906005c0f3d`。每配置从当前源锚及实际Call独立枚举172root，合计516；54个phase raw Call闭包分别保存。每配置9340行source/caller合同；普通CPP 70行、39site单列一次。default保留7方向、RHS139实际＋47原限定域合同和BF8；两alternate的RHS各372行及其source方向全部pending。

v2另逐配置核实际execute root与helper Call/SSA，形成24个callee-instance：default8保留完整已接受证据与全部typed/正常域前提，两alternate16保持pending。未把默认值公式或已接受状态跨配置搬用，也不把callee数量加到source branch计数。

正式复审 `bf16/independent-three-config-caller-ledger-review/review.json` SHA-256为 `cc3628f13cf2928028aa820e0d9376ab9b3173000e6059049c1b018564958640`，索引SHA-256为 `24753da924b3fb40989a61e9f4742d20bc0968169080ba0a9aea80747067e906`；11项测试含10项有效负控通过。[消费器](tools/solve_bf16_coverage/three_config_review_consumer.py)只接受 `accepted_configurations`，重新核289项依赖，并检查配置、sidecar、caller/RHS计数、原状态、callee实际root/helper及OPEN限制。输出 `bf16/three-config-source-caller-ledger-reviewed-v1.json` SHA-256为 `cf8bd63b4de51295045279a754f0e0f02880c6cde906c5c1f9a543eb69575672`，以不可变候选引用保留完整表及原前提。新消费器8项TDD负控通过。

本次PASS仅为**三配置表守恒、来源和域隔离**。`source_branch_closed=false`、`denominator_complete=false`、最终source分母null；新增模型运行、方向/值排除、跨配置证据转移均为0。静态Call图闭包不证明phase路径可达性或无异常效果。

### 新 56cc69：未解析call-like引用的逐occurrence分类

原120个声明中的346个call-like occurrence已有[声明与编译器规则分类工具](tools/solve_bf16_coverage/source_occurrence_classification.py)。v1 `bf16/source-occurrence-classification-v1.json` SHA-256为 `36cc64961a3e783157358cc88d0076996a94ff1ee5405b9d72e74e676fec3537`，保留7条未认出的无参函数返回类型。独立[v2修订工具](tools/solve_bf16_coverage/source_occurrence_refinement.py)只修这7条明确的 `-> bits(...)` / `-> result(...)` annotation；现行 `bf16/source-occurrence-classification-v2.json` SHA-256为 `5a307ab1825351c2161f8959dda7e2bb3637f46e56ff20fb69bb9480fd15490b`。

逐真实token字节、声明边界、类型namespace和冻结Sail lexer/compiler生成规则，346条分为158类型annotation、40 lexer keyword、145已声明constructor、2生成enum转换调用和1 quoted external val调用。没有按名字白名单删除引用。`num_of_vector_support`两次调用绑定当前26指令body及enum生成规则；`parse_hex_bits`绑定quoted val和真实Call。后3条callee语义合同继续pending；constructor pattern及外围control也继续pending。

当前只是 `CLASSIFICATION_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW`，已交审。namespace unresolved=0仅指本清单346条，不证明整个源码调用闭包。源码site删除、caller关闭、动态新增均为0。分类工具6项、修订工具3项TDD测试通过；旧v1及producer冻结。

原生AST机制探针交付在 `integration/p1-56cc69/source-ast-probe/delivery.json`，SHA-256为 `64e4d6ecdfe9da6dafe840dc0c2c1e8488ac5ef571e7c76c562f90fc38e499f4`。它提供fixture下的native Bool/bits、private和SourceLoc机制证据；当前不是全模型typed目录，不能据此升级本候选完整性。全模型physical/raw/typed分层目录由对应工具负责人推进。

### 新 56cc69：运行叶的实际dispatch分类候选

[运行叶分类工具](tools/solve_bf16_coverage/runtime_leaf_classification.py)从三配置实际sidecar重读Call，绑定当前56cc原IR，以及 `28fb65…` runtime manifest内冻结的 `ir.rs` / `executor.rs`。产物 `bf16/runtime-leaf-classification-v1.json` SHA-256为 `0a120a87a7c181450d97f9466b785779684ac8e93d2cecfa25da58bc03c6d562`，含294依赖、228个config×phase叶行和1134个实际Call绑定。

原76个phase叶模板有20个不同runtime名称：17个来自实际IR union constructor声明（跨三配置174行）；2个由extern别名、符号常量注册、初始化lowering及executor分派共同绑定的寄存器向量读写特例（36行）；另1个 `parse_hex_bits` 保留为未lower的quoted external Call（18行）。constructor不按名称猜测，特例不靠名字白名单；相同extern声明可在IR合法重复，工具保存全部行号、拒绝冲突重声明。

此包仅为dispatch分类候选，未签callee正常返回：constructor payload求值、pattern、异常效果，寄存器向量索引/映射/值域/写回，以及external真实可达域均继续pending。冻结执行器含未知Call的 `NoFunction` 出口，但本包没有宣称BF运行已抵达 `parse_hex_bits` 或发生该异常。source site删除、caller关闭及模型运行新增均为0；独审排在346 occurrence之后。10项TDD测试通过，Python编译与自有文件尾空白检查通过。

### 新 56cc69：occurrence声明归属修订与生成enum局部值候选

346 occurrence独审发现原inventory的HEADER缺少 `newtype`：`extensions/FD/fdext_regs.sail` 第56、57、59行的 `bits(5)`、`range(0,31)`、`bits(3)` 被错归到前面的 `nan_unbox`。namespace类型分类可保持，但v2 enclosing scope不能作为正确证据。原v2、原清单及producer不改。

[声明归属修订工具](tools/solve_bf16_coverage/occurrence_scope_refinement.py)生成 `bf16/source-occurrence-classification-v3.json` SHA-256为 `cab92ac5c47c1b13c55699d5a197110e3a07f5d598236876013c92b9aa211615`。全部346 occurrence ID及158/40/145/2/1分类保持；原declaration_id/source_function移入 `inventory_identity`，三条 `enclosing_scope`分别绑定 `fregidx`、`fregno`、`cfregidx` 的真实newtype整行字节范围。其余343条保留原声明引用并显式待scope审查。120改称原inventory声明组数，不声称120个真实函数范围。四项TDD先红后绿；新版已交原审者，source/caller关闭仍0。旧779词法闭包不由这项修订升级。

另继续对两个生成enum调用进行局部值分析：[有限域工具](tools/solve_bf16_coverage/enum_conversion_contract.py)在三个实际配置中分别读取 `znum_of_vector_support` 的完整26指令及 `zvector_support_ge` 的10指令。对源码声明的五个enum值，逐实际SSA、Jump、Goto、整数转换和End重建返回0..4；随后核两个实际转换Call及 `gteq` 消费的全部25个typed值对。整数转换与比较绑定冻结runtime `primop.rs`，没有借用primop进程地址。

候选 `bf16/generated-enum-conversion-contract-v1.json` SHA-256为 `8e0a77ca0e0efa63c4ab626f3781fbc5637bb0760a47cb50c58297b25b6c3b7f`，306依赖、三配置15个转换值案和75个ge值对；11项TDD负控覆盖错误常量、实际返回依赖、callee、全局写入、未知primop、循环和enum域错误。**这是静态有限域候选，尚无独审、不是模型动态执行。**范围仅五个declared enum、非Poison且正常实参求值；BF外围root/header/getter域及异常行为仍pending，原两条callee义务等待独审后才能按窄域消费。编译器生成Jump新增source branch为0。

### 新 56cc69：346 namespace正式消费及三个callback字面量合同

独审 `bf16/independent-source-occurrence346-review/review.json` SHA-256为 `976e1e1945f2d51d0f0df967b403eb781ab243d297d4bb6fa5a3379115cd6ab4`，状态 `PASS_SCOPED_FINITE_NAMESPACE_AND_THREE_NEWTYPE_CORRECTIONS`。独审15项测试含17项负控，重核242依赖并确认19个constructor的实际IR union成员；保留v2三newtype归属FAIL。其余343条有限源码窗口起点匹配，不将窗口尾端称作native AST末端。

[精确消费器](tools/solve_bf16_coverage/occurrence_review_consumer.py)核逐occurrence来源、分类、historical identity、正式scope修订及所有限制。新账 `bf16/source-occurrence-classification-reviewed-v1.json` SHA-256为 `878935567a96ae9538115958f4f91a745327cc0b6b3f9fbcb18d94c53e957503`，249依赖重新核验，6项消费负控通过。仅接受346条namespace与3项scope修订；两个生成enum和一个external的语义仍pending，source/caller删除关闭和动态新增均0。

[callback字面量工具](tools/solve_bf16_coverage/callback_literal_contract.py)复用冻结scalar `AccessorFinite`，为三个BF配置分别新导出 `csr_name_map_backwards`、`csr_name_write_callback`、`csr_full_write_callback` 三个typed函数；每配置3804条PC与其实际sidecar全量比对。各自核 `fflags`、`fcsr`、`vstart`及任意typed非Poison bits64值，局部返回unit、无全局读写或初始化，不调用hex parser。CSR独立期望来自 `extensions/FD/fdext_control.sail` 第23/25行与 `extensions/V/vext_regs.sail` 第391行，分别为0x001、0x003、0x008。

候选 `bf16/callback-literal-contract-v1.json` SHA-256为 `226fa1a72a352bd79299f849196ae50658593d8d77422ff780f54ea9b8d77b65`，317依赖，9个字面量局部合同、48个实际callback条件caller行；18个 `long_csr_write_callback` 名称转发行继续pending。六项负控验证源名称实参、mapping返回依赖、真实callee和范围不升级。3次typed导出属于准备工作，模型动态运行、新source branch和静态排除均0。

本包只证明候选范围“实际callback Call已抵达且全部实参求值正常”下的局部行为；不证明外围phase总性、指令flags写回正确或全部异常调用域。`parse_hex_bits`来自保守 `csr_name_map_backwards` 的hex名称路径，列定字符串不调用它不能变成external全域排除。候选待独审，原leaf及总账不改。

下一步已进入全模型原生AST接通：按实际 `FCL_funcl` / `MCL_bidir` 的六BF构造器根，分别建立ordinary CPP与Isla SYMBOLIC域，替换HEADER词法发现层。原生包的正式manifest与有限exporter审查仍由工具负责人完成；Generated/Hint、mapping-pattern的Env未分类边及未选中源码解析失败继续保留，不能依据成功导出直接关闭source分母。


## 全模型原生 AST 根与全局入口（2026-09-27，候选）

[native 根工具](tools/solve_bf16_coverage/native_source_inventory.py)直接读取两域完整 typed AST，以 `FCL_funcl` / `MCL_bidir` 外层构造器识别六 BF 的执行、译码、编码根，共36个。v1 `bf16/native-full-ast-source-caller-preparation-v1.json` SHA-256为 `bf5f0d4a9827ce32823bd371ea405888845515a0b29b69bc75937fa24ff50bae`；ordinary / SYMBOLIC 分别410 / 406个单元、369 / 388个控制、mapping或effect节点。原795词法token只保留历史，不自动迁为原生分母。

[入口补齐工具](tools/solve_bf16_coverage/native_scope_completion.py)纳入嵌套definition、`DEF_impl`、顶层let与register初始化，按pattern、let、var、for的词法binder联立全局引用；private来自同module的实际 `DEF_val`，extern来自真实 `extern_spec`。v2 `bf16/native-full-ast-source-caller-preparation-v2.json` SHA-256为 `1646f820286cf80857cc877602e0799240b14b64cf47e643f803cb1e0e64dce8`，124依赖重核并逐文件SHA/bytes消费exporter-package-v1 manifest `829172d2…28dd3`。

| 原生候选 | ordinary CPP | SYMBOLIC Isla |
| --- | ---: | ---: |
| reached单元 | 590 | 593 |
| 函数 / register / global let / mapping clause | 445 / 117 / 14 / 14 | 441 / 121 / 17 / 14 |
| 控制、mapping与effect节点 | 396 | 415 |
| extern occurrence（语义未决） | 663 | 613 |
| public / private同module callee边 | 940 / 13 | 859 / 13 |
| typed union constructor occurrence | 34 | 40 |
| unresolved callee / mapping-pattern Env-open边 | 12 / 24 | 12 / 24 |
| 全局依赖边 | 275 | 293 |

36个根保持唯一；SYMBOLIC根关联三配置516个实际runtime root，ordinary保留独立source域。两工具分别10和8项TDD通过。**这些节点包含Generated、mapping和effect合同，不是最终source branch分母。**词法binder规则、生成mapping方向函数、raw/typed物理源码对应、宏域、Hint两分支与caller输入域仍待补齐和独审；v2尚未消费后来交付的exporter有限独审 `603bf10e…f7964`，该证也不签调用闭包或覆盖。


## 运行叶、enum与callback正式有限证据消费（2026-09-27）

[统一有限证据消费器](tools/solve_bf16_coverage/local_contract_review_consumer.py)逐SHA和bytes重核三份正式索引、原候选及依赖，只消费各证书的accepted字段；11项TDD范围/身份负控通过。三个新产物均保持source=false、denominator=false、caller关闭0、模型新增运行0、静态排除0。

| 有限范围 | 正式review SHA-256 | 消费产物与SHA-256 | 重核依赖 |
| --- | --- | --- | ---: |
| 20运行名字、228配置阶段叶行的dispatch分类 | `3563a9404b6e1005bdb0a54d37d9be1d2bc195c9f53e5fe92e8b88f11b83fbad` | `bf16/runtime-leaf-classification-reviewed-v1.json`：`1d899d373529faf5bfafadc4558ebfbac319cf1898a1633a458cb33d7c67af51` | 308 |
| 三配置合法enum局部15值、75对 | `197bd595f685ced30567c4b2a4d018c4915f30979229363304128f3961e305e1` | `bf16/generated-enum-conversion-contract-reviewed-v1.json`：`165992c47b9ed3c7379e231ed21f9a8b660c2eb206c9b274c2b97c90ba63da99` | 322 |
| 三配置三个callback字面量局部合同 | `4886318eac750417e4ec9d81f7903ee0806dbdccb86d4d87074397eac64f9d3e` | `bf16/callback-literal-contract-reviewed-v1.json`：`3773abe498b4c487d55c2d4eb4a8a2af683bdffca778a86e472c5f98bef7ca93` | 331 |

运行叶证书仅签dispatch；1134个Call是静态身份，constructor payload、异常效果、寄存器索引及写回域未获签。enum额外消费 `independent-generated-enum-review/runtime-enum-identity-check.json` SHA-256 `e8bfcc9f179e3697aed535d9605469d0601e5269753a49e5420d6c3f03b3851a`，确认真实运行enum相等包含类型身份及member位置。绕过前提的foreign或越界enum可能沿默认分支返回4，不能认成合法Full；Poison及外层getter/root正常域仍未证明。

callback独审12项测试、11组负控通过；每配置完整3函数、3804 PC，三个正常字面量映到CSR 1/3/8，任意typed非Poison bits64仅SSA局部复制，正常End返回unit，无全局读写。48条字面量caller与18条动态name转发行只签静态Call/root身份；实参正常求值、实际可达和支配、外围CSR/fflags更新与外层总性全部pending。此有限证据不关闭未知name、hex parser、MatchFailure、Arbitrary或异常域。


## mapping原生环境与方向声明接通（2026-09-27，候选）

exporter v2 manifest `source-ast-full/exporter-package-v2/manifest.json` SHA-256为 `d7a292daf17fd9d6fd46a9c7f05b8fd36864f802016a066f7d9207bacf137f3e`，完整attempt006分别绑定ordinary `f962fb93…7c45c9`、SYMBOLIC `e1cf0495…91519e`。新增MP/P/LE实际Env分类、attributes及instantiations；本阶段消费v1正式独审的结构发现有限范围，v2元数据增量审查尚未消费。Env class仅表示调用点环境的全局namespace成员检查，目标scope仍联立实际definition与private签名。

[mapping接通工具](tools/solve_bf16_coverage/native_mapping_completion.py)生成v3 `bf16/native-full-ast-source-caller-preparation-v3.json` SHA-256 `53147b9a2fe096021c9e80258b64629b2f3d627ae277a4e49cdceaacef3aab6d`，171依赖，8项TDD通过。两域各12处生成方向函数由实际mapping定义与本次工具链 `type_env.ml:add_mapping` 四方向注册、`type_check.ml` 的mapping表达式改写联立；源码片段与整文件SHA均保存，不以名字后缀单独推断。真实MP/P/LE Env替换旧24条保守边，并补入 `csr_name_map` 的343个clause。

v3余1条 `hex_bits` 无MD body，实际是 `Typ_bidir` val加四个手写方向函数。[手写方向接通工具](tools/solve_bf16_coverage/native_manual_mapping_completion.py)以真实val类型及四个实际函数联立，生成v4 `bf16/native-full-ast-source-caller-preparation-v4.json` SHA-256 `2707387fa518cd6bd1cdf462f77c85aa8b90c30216cfddd05928c2e7c1c0c97f`，174依赖，4项TDD通过。ordinary / SYMBOLIC reached单元952 / 955，控制、mapping与effect节点754 / 773，mapping clause各372；名称未解析边均0，extern occurrence668 / 618仍待语义合同。public目标跨module只涉及 `currentlyEnabled` 与 `csr_name_map`，每名字的所有目标clause均属于同一真实descatter后definition_key。

**名称未解析0不代表源码分母、callee总性或caller域闭合。**图仍保守纳入两侧mapping及matches，方向选择、失败/异常、Generated/raw对应、函数clause与pattern匹配顺序均待证明；source=false、denominator=false、动态新增与静态排除均0。下一层直接读取完整raw树及typed树，联立冻结source hash与UTF8半开byte，不能用未对应节点作排除。


## raw/typed物理源码身份与投影（2026-09-27，候选）

[物理绑定工具](tools/solve_bf16_coverage/native_physical_source_binding.py)直接读取完整raw/typed树，冻结alias、文件SHA与UTF8半开byte联立；function clause pattern另列。v1 `bf16/native-physical-source-binding-v1.json` SHA-256 `33198596cc8c6875c6202d407d0ab626fcae81d76ab108788761f7259b775c81`，400依赖、440唯一物理节点候选。首次执行遇到编译器生成pattern的空文件名Range时失败；修正为显式保留内部/生成来源pending，未丢弃位置或计作排除。7项TDD通过。

[投影修订工具](tools/solve_bf16_coverage/native_source_projection_refinement.py)核对 `scattered.ml:patch_mapcl_annot` 将原生MCL位置替换为实际scattered DEF位置，及 `initial_check.ml:apply_when_guard` 将一个raw when展开到两侧MPat_when。以349个真实raw声明、两侧pattern及同一guard范围联立，不按含糊包围窗口猜测；两侧guard归于同一物理guard，caller方向仍分别保留。v2 `bf16/native-physical-source-binding-v2.json` SHA-256 `adadc29c818aa5891661101a9a421d92a4eba91bae3c2083efdeb8cef0e6fbce`，405依赖，723个typed occurrence修订，6项TDD通过。ordinary / SYMBOLIC分别747 / 766节点获得身份候选，合并796个唯一物理节点。产物前一次执行拒绝了source key字段序变化导致的digest不守恒，修订按原键序后完整产出。

796包含mapping、effect与guard，不能称作最终source branch数。每域余7个生成来源义务：5个sizeof或隐式调用类型参数展开的E_if、1个 `num_of_vector_support` 的Unknown位置生成match、1个 `rF` assert后生成exit；全部保留待核。source分支新增、source排除、caller关闭、模型新运行均0。

位置规律补充：v1/v2按typed实际参数之间的源码间隙和raw E_infix联立operator；一个Unknown RHS例外以同范围唯一原生IT_op及唯一源码token联立。随后主agent查明raw `E_infix.args[0]` 每项实际是 `[IT_token, start_position, end_position]`，其相邻position已给精确原生byte。**IT_op自身无Loc不代表没有token坐标。**下一反向scope包将直接消费该三元组并核源码byte；旧产物与规则保留历史，不扩成最终分母证明。


## selected原生scope反向事件守恒候选（2026-09-27）

[反查工具](tools/solve_bf16_coverage/native_raw_scope_completeness.py)从每个reached原生unit反查完整raw scope，另将生成bitfield/enum helper按实际raw类型声明和本次compiler generator规则纳入。v1 `bf16/native-raw-scope-completeness-v1.json` SHA-256 `d2e17260138ba780f303119d6d1633b445a818d79890dd6f0c8cbd3f6a7d18dd`，425依赖，6项TDD通过。正式消费exporter v2独审 `e42ec7094bb812e4065c339a04c9611ccb24deb734363b8a2007ea52599f5001` 的 `STRUCTURAL_DISCOVERY_AND_PENDING_INVENTORY_ONLY` 范围及全部附证，未扩大到分母/覆盖。

[反向事件补齐工具](tools/solve_bf16_coverage/native_raw_event_completion.py)将349个scattered MCL及6个when事件联立已有实际投影链；其余raw `&` / `|`使用原生infix三元组精确坐标，联立最内层实际typed E_app、公开type AST和Env，得到ordinary5 / SYMBOLIC13个bits数据operator，无Bool真假方向。v2 `bf16/native-raw-scope-completeness-v2.json` SHA-256 `8ae2c9ada98ace3062486695d06561c076e907daeb327e2e7b863d6fa8abfc9b`，428依赖，5项TDD通过，已交架构安排独审。

| selected BF范围候选 | ordinary CPP | SYMBOLIC Isla |
| --- | ---: | ---: |
| reached原生unit | 952 | 955 |
| 精确name＋原生pattern/声明位置反查raw scope | 884 | 885 |
| 真实raw类型＋compiler generator来源 | 68 | 70 |
| 未解析unit来源 | 0 | 0 |
| 完整raw事件 | 742 | 769 |
| 同kind typed身份 / 已列mapping投影 / typed bits | 382 / 355 / 5 | 401 / 355 / 13 |
| 未分类raw事件 | 0 | 0 |

两后端raw scope合并912个，native根保持36，SYMBOLIC每配置172实际runtime root绑定保持。**零未分类只表示本层枚举与来源候选守恒。**实际module/visibility充分性、手写Typ_bidir四方向的绑定、生成来源及完整反向枚举仍待独审；extern668 / 618仅分类、值域和异常全OPEN。每域7个生成控制来源、mapping方向/匹配顺序、隐式失败与caller/entry输入域继续保留。旧795词法义务对账由跨族身份包推进，不在此静默删除；未选中instr_kinds原物理parse FAIL保持历史，不阻挡对真实selected域单独审查。


## 共享原生依赖、真实引用路径与有限独审（2026-09-27）

旧v4及raw v2的“selected scope完整”不成立：原引用提取漏掉 `E_ref`，SYMBOLIC全局GPRs/FPRs/VPRs共96条寄存器引用未列，其中 `x0` 未进原闭包。独审历史证 `bf16/independent-native-raw-scope-review/review.json` SHA-256 `189f97d7dc018275d8b7f16c4ebff8d4a52c2742e9c7422a04c833bbda61a7ca` 只签原列定节点/事件范围并明确完整性失败；原产物保持历史。

新的三族共享入口为 [native_semantic_dependencies_v8.py](tools/solve_bf16_coverage/native_semantic_dependencies_v8.py)，SHA-256 `dde355e6fa7e1ba445043f4312273885aa5338345b38817a2823ae28e5e36ba1`。`extract_semantic(path, backend)` 保留真实 `definition_key`、完整语法分类、作用域binder、E_ref/LE引用、effect与类型条件的逐节点义务。所有返回引用路径均为原始AST可导航的args/list索引，每次提取逐条还原kind/name/location；21项TDD通过。旧v5补E_ref后发现BF专用根过滤、过宽schema分类与extern选择不足；v6修这些但引用路径仍含虚拟role段；v7在合并独审修订时中断写出，半JSON不作证据。三个历史版本不改写。

v8补充要求：根必须来自actual Env `union_constructor`；其他outer application仅候选。`E_internal_return` 是monadic纯return降低义务，不能当普通early-return；`E_internal_assume` 单列source域/降低合同。全部Ast构造器按固定显式集合检查，新tag失败；schema计数不代替type/config依赖闭包。

extern按本次编译器真实规则：ordinary key为 `cpp`，SYMBOLIC Isla key为 `c`，先精确key再 `_`；extern即使有Sail body也优先。同名Sail body仍保留源码候选，`effective_execution_target_unit_ids` 另列实际后端候选；module目标充分性未签。调用次数与唯一真实 `DEF_val.definition_key` 分列，不能用唯一名字数代替声明。

| v8 BF组件候选 | ordinary CPP | SYMBOLIC Isla |
| --- | ---: | ---: |
| reached unit | 952 | 956 |
| 控制/mapping/effect旧分类节点 | 754 | 773 |
| E_ref依赖 | 0 | 96 |
| 额外effect/reference义务 | 323 | 349 |
| Nexp_if/NC_and/NC_or逐节点类型义务 | 1217 | 1404 |
| 当前target extern occurrence / 唯一声明 | 680 / 90 | 715 / 85 |
| 关联独立measure声明 | 10 | 10 |

BF图 `bf16/native-full-ast-source-caller-preparation-v8.json` SHA-256 `ed6e11d941c2f096f5d2416e9a7ea6f4b2543bf5f8c4a0e964b17190e54d051e`；共享核验包 `bf16/native-semantic-dependencies-v8-shared-check.json` SHA-256 `36faf87f88b54cf25d58225f6885a130e836a7e9f7970acac06e816483a71611`，各绑定183依赖。仅 `FCVT_BF16_S` 的SYMBOLIC execute组件root新增x0，其他root集合差为空；不得由union中已有95寄存器推断每root引用完整。

### raw完整scope重新绑定

[共享raw scope API](tools/solve_bf16_coverage/native_raw_scope_shared_v3.py)以完整raw树建立5083 scope，保留原子树hash、逐tag计数与原生infix三元组；新增return、sizeof、constraint、ref、write等语法事件，5项TDD通过。共享核验包 `bf16/native-raw-scope-shared-v3-check.json` SHA-256 `b1e5d6c673d89bb2cbe7a4905bd39990e919fa3764b6c98c5d9b7cf16c8ea5ff`。

[BF重新绑定工具](tools/solve_bf16_coverage/native_bf_scope_rebase_v3.py)仅在旧控制节点完整记录、既有unit definition_key/location均相等后复用原物理投影；每root仍由v8完整重算。3项负控通过。physical v3 `bf16/native-physical-source-binding-v3.json` SHA-256 `63a4a38272a7ca215b1ce4fa4b08324d99ba5ebdc55933edc5935391c1a953a0`；raw v3 `bf16/native-raw-scope-completeness-v3.json` SHA-256 `f953595faaa004f7d36e0100f6bbe129209f0962936ef087e4b4a72ad2a84920`，后者443依赖。旧bits派生属性拼写 `overload` 错误，新包从原完整annotation按 `overloaded` 重取；旧产物不改。

| raw v3 BF范围 | ordinary CPP | SYMBOLIC Isla |
| --- | ---: | ---: |
| 精确raw scope / 实际type生成来源 | 884 / 68 | 886 / 70 |
| 完整raw事件 | 968 | 1107 |
| 新增语义事件同kind+位置联立 | 114 | 219 |
| 新增语义事件降低/域待证 | 112 | 119 |

两域合并913 raw scope。独审正式证 `bf16/independent-native-raw-scope-review/increment-v8/review.json` SHA-256 `7be97a1ff954275571c5537a51615edb9d8892e993362d70ba6e5841dcc19304`，限定PASS显式图、义务身份和列定raw事件守恒；重核446依赖、3.114 GB，6项测试及8项真实负控。112/119未对应事件、生成来源、全部type/config/undefined与measure/outcome语义、外部值域、module充分性和完整入口域均保持OPEN。source、denominator关闭和新增动态覆盖均0。

### 生成控制来源和类型条件

[生成来源工具](tools/solve_bf16_coverage/native_generated_control_provenance.py)生成 `bf16/native-generated-control-provenance-v1.json` SHA-256 `dae10adae85076dbd1b44aa488e9450eb0e2b6690fd64f0695aea7ae3667237f`，432依赖、5项TDD。每域5个E_if联立实际公开Nexp_if、调用类型实例化、raw sizeof/调用点和本次compiler rewrite_sizeof/implicit规则；另1个enum match联立真实5成员/from_enum，1个rF exit联立raw assert(false)与实际同loc `[assert, exit]`。

两处raw `ATyp_if` 是新增source条件义务：`model/core/flen.sail:12` 的 `ext_d_supported ? 8 : 4`，`model/core/types.sail:29` 的 `base_E_enabled ? 4 : 5`。不能按Generated删除。完整raw中24个ATyp_if均保留，复杂类型条件未匹配不意味着不相关；完整type声明依赖由后续共享层处理。该候选仅raw/compiler/native来源，尚未证明native生成节点与实际IR的精确降低关系，待独审。

### 完整入口与有序dispatcher候选

[共享dispatcher API](tools/solve_bf16_coverage/native_dispatcher_order_v1.py)直接读完整原生AST，按实际definition及clause索引保序，按本次 `rewrite_ast_realize_mappings` 分方向联立matcher、guard与结果源子树；6项TDD通过。BF应用 `bf16/native-ordered-dispatcher-entry-domains-v1.json` SHA-256 `3ed764e99c132ff1272c572e14d2b0378b85ce02638cff43266cdd576727641c`，188依赖。每域encdec两个方向各392 clause、execute395 clause、ext_decode1 clause；216个backend/config/entry/ctor/phase域候选保留完整前后规则、失败后缀及最终ILLEGAL。

这些只是带显式待证D的入口义务：official从实际typed ctor参数和初态起，decode只能消费同一encoder正常成功image及相继状态；audit使用原始word和初态，不借official像域。每候选j的域为D与所有前候选正常失败；前候选异常另作终态。matcher可能含guard前执行的infallible binder投影，源码三段划分不能充当IR动态顺序证明。实际harness输入、phase-state/image关系、目标失败后suffix可达性与独立SAT/UNSAT尚待联立；本包没有任何body排除或新增运行。旧795词法候选、796物理身份均不升级为完整source分母。


## 共享机制正式消费与原生义务续接（2026-09-27，同56cc69）

本节仍仅绑定IR `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`、source manifest `fdf105d19a9ac62f9c5036fbc80759adb7e9b500a51a34fcc4f886016329129e`、runtime manifest `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`；不迁移到后续生产IR。下列路径以既有 `isla/target/float-support-review/final-coverage/integration/p1-56cc69/` 为基准。

### 共享expression库存的有限正式证

共享v8正式证 `source-ast-full/independent-shared-closure-checker-review/certificate.json` SHA-256 `ea9e5d80441cc4db5a6a88d90d12904313439f02ac91fe2578e286ff38e654cf`，manifest SHA-256 `8851ca4b728691908da5f3e35669439c195282fa96be8a5df9d213378ff82f01`；状态为 `PASS_SCOPED_NATIVE_EXPRESSION_EXTERN_INVENTORY`，21项工具测试与32项独审负控通过。证书只签列定expression/extern库存机制，family/raw/type/dispatcher/closure各项均未签。

[共享消费器](tools/solve_bf16_coverage/shared_native_review_consumer_v1.py)4项测试通过，逐SHA/bytes重核56依赖并保留全部限制，生成 `bf16/shared-native-expression-inventory-reviewed-v1.json` SHA-256 `d9261ca6d56efc001e4c62e4b4093a12b8026a0a677d63a2e3ec5492c514e796`。scalar/vector消费同一正式证，不用BF局部实例证替代各族应用验证。

### raw投影v3及BF应用v6

[共享投影API](tools/solve_bf16_coverage/native_raw_projection_v3.py) SHA-256 `39b5dfbab17b5589601104197590165a7565d75c52d7ed067aeb012b766e962e`，6项TDD通过。`build_projection_index`/`project_unit_events`联立完整scope、实际kind/位置、scattered annotation规则、两侧when、原生infix token及真实 `overloaded` 属性。两侧when展开的typed annotation整树hash可以不同；必须同时核实际两侧guard、相同相对AST路径、operator/name/type及两operand位置，保留两个typed occurrence和同一source身份。

BF [应用v6](tools/solve_bf16_coverage/native_bf_raw_projection_v6.py)生成 `bf16/native-raw-scope-completeness-v6.json` SHA-256 `a13ecb35dcbcd0ded7bab5a2da5b56c961da8a7852652e03d5665fb336db6507`，447依赖。全部968/1107事件守恒，旧747/766物理身份逐条相等。旧v4/v5及共享v1/v2保留历史；其中4个bits operator因要求两侧typed annotation hash相同而未联立的问题已在v3修订。

| 仍待降低/语义关系的raw事件 | ordinary CPP | SYMBOLIC Isla |
| --- | ---: | ---: |
| E_config | 93 | 93 |
| E_sizeof | 12 | 11 |
| E_assign | 7 | 15 |
| 合计 | 112 | 119 |

全部未投影assignment已定位为setter调用语法，包括 `F(i)`、`F_S(rd)`、`F_BF16(rd)`、`V(...)`、`wF(...)`、`wV(...)`。共同setter lowering关系由共享层接续；尚未据该分类删除source写义务。

### dispatcher v2纠正状态传递与实际审计域

前节v1的“D与所有前候选正常失败”不能直接化为同一state上的布尔合取。matcher、binder或guard可能改变state，现行 [共享v2](tools/solve_bf16_coverage/native_dispatcher_order_v2.py) SHA-256 `c5eea687314b6f8a933498a09d1ec487ae67b5d03eb23f27a0cda0b385e3839e` 使用关系递推：

```text
R0(w, σ) = D(w, σ)
Rj+1(w, σ') = ∃σ. Rj(w, σ) ∧ RejectNormally_j(w, σ, σ')
```

异常终态另列；只有独立证明纯读、total且state-preserving后才可简化。matcher包含guard前的 `_backwards_infallible` binder调用。实际execute末尾是剩余 `C_ILLEGAL` payload解包，不能记为通用MatchFailure。

独立边界调查 `source-ast-full/independent-dispatcher-boundary-review/review.json` SHA-256 `5e3d1c1fb68a523c7a923085e83b9d4602a6b084d7f0e22d1ef56a24667099cb` 纠正了审计harness状态关系：**audit每phase使用同一initial regs/lets、新solver和新frame，仅传decoded值；official wrapper连续传递状态。**942个实际BF case是固定word与初始化，广义mask仅作另列例子，不能以有限case收缩完整source分母。

BF [实际入口关系应用](tools/solve_bf16_coverage/native_bf_entry_relation_v2.py)生成 `bf16/native-ordered-dispatcher-entry-domains-v2.json` SHA-256 `1458a4d930286959d697054332400b2d72991bc82d0dd4bf3236852cac8aebb3`，228依赖，绑定942 cases、9初始化侧车、实际runner源码/二进制/build及真实argv；全部域ID重算。共享v2的3项测试通过。完整入口D、各phase实际状态关系、prefix/suffix可达与目标分支覆盖仍待证。

### 14个生成来源正式消费与enum/rF局部IR桥候选

生成来源正式证 `bf16/independent-generated-control-provenance-review/review.json` SHA-256 `bad05c55fa409c3656e7edd11093f94bce98d26642d1fb8abae8b4d56f5b3124` 仅签两域14个raw/compiler/native来源；两个Unknown enum根来自type checker完整性属性的 `Generated(Unknown)`，不能按Unknown漏项。[来源消费器](tools/solve_bf16_coverage/bf_native_origin_review_consumer_v1.py)4项测试通过，同时消费BF v8/raw3有限实例证，生成 `bf16/native-origin-and-scope-reviewed-v1.json` SHA-256 `688df7e807fe36638d617106dce2af1eee15d8e27cc51c55cf87c1892b703189`，485依赖。消费时14个实际IR关系仍OPEN；两处真实ATyp_if及全部24个raw类型条件保留。

[enum/rF桥工具](tools/solve_bf16_coverage/native_generated_ir_bridge_v1.py)5项测试通过，生成 `bf16/native-generated-enum-assert-ir-bridge-v1.json` SHA-256 `e18a23817f17e984a306732dee78f5c42c1626a1b7b28bec1e5e25d5a940cf3e`，586依赖。仅2个SYMBOLIC原生节点×3配置共6个局部IR桥候选；独审尚未消费本包。

- `rF`原生真实block为 `[assert(false, message), exit]`。raw IR PC425为assert、426为explicit exit；三配置实际运行侧车把425改为Goto434，434按Bool(false)选择435 `AssertionFailure`，436复制Unit、437返回426。explicit426唯一CFG前驱437；本断言局部路径实际终态是AssertionFailure，不能将结构存在的Explicit记为该路径动态终态。caller能否到该source arm、索引/FS域尚未证明。
- `num_of_vector_support` 原生5个分支为Disabled0、Integer1、Float_single2、Float_double3、Full4。实际26 PC中1/6/11/16为4个Neq；仅在同类型、合法五成员、非Poison域下，四比较全true的默认4等价于Full。三配置共15个合法谓词行联立每个源arm、完整实际body及精确PC路径。foreign/越界enum不得识别为Full；ordinary native counterpart只记录来源，实际CPP lowering未签。

### BF精确附接共享type/declaration候选层

父共享type包 `source-ast-full/type-dependency-preparation-v2/manifest.json` SHA-256 `3e7e2b5e7723d02f2fb1e5daeb252b8d05906942328fa486a4caeba8ed47be7e` 绑定全部6372/6410 unit附件。BF [附接工具](tools/solve_bf16_coverage/native_bf_type_attachment_v1.py)4项TDD通过，运行命令为 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_type_attachment_v1.py`，自然退出0，生成 `bf16/native-type-declaration-attachment-v1.json` SHA-256 `473b97bae90308dfe4afd06a93e6514d4385e7dcc9d27eaa036d0030cb906808`，197依赖。

| 附件身份 | ordinary CPP | SYMBOLIC Isla |
| --- | ---: | ---: |
| BF选中unit / root | 952 / 18 | 956 / 18 |
| source reference ID | 30070 | 30515 |
| source obligation ID | 1350 | 1447 |
| 传递候选声明 | 223 | 221 |
| 关联measure / outcome声明 | 10 / 0 | 10 / 0 |
| runtime rewrite候选unit | 0 | 0 |

每root仅引用其真实reached unit的冻结附件；编译前件不是runtime callee，runtime候选为空也不证明L_undef已闭合。type/config常量化、module/target实际目标、undefined重写语义及5个type生成if实际IR桥由共享层与独审续接。全部新产物仍为 `source_branch_closed=false`、`denominator_complete=false`，无新增动态覆盖或静态排除。

### 普通CPP的enum/rF局部桥候选

[CPP局部桥工具](tools/solve_bf16_coverage/native_generated_cpp_bridge_v1.py)先以8项TDD确认新增效果调用、错误enum结果/域、重复label及assert后插入语句会被拒绝，再核完整实际生成函数。运行命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_generated_cpp_bridge_v1.py` 自然退出0，生成 `bf16/native-generated-enum-assert-cpp-bridge-v1.json` SHA-256 `410a7e58907af415a281a8b95af24d6ee9221beef038b4f51c407c4dae07bf37`，509依赖；本包尚待独审。

实际构建为 `isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/model-build.json` SHA-256 `d6b825afde5af170332f79e9136f73db936e583fd8dbc1ae0806c61b05547259`，CPP/头分别为 `96d18ceab0ca1f392a25d925826f608cfb8ed2c0c8de9c90a2c7dea8e1cd5e74`、`f79d000975c119700323b282d28b4ece8dc7f549309d1c95881b87b31883ef97`。冻结IR候选generation记录联立该成功构建，未重新生成或替换模型。

CPP完整 `znum_of_vector_support` 为同序4个Neq与默认4；五合法成员分别保存精确源码行路径，返回0至4。仅对真实同类型合法域作局部等价，未运行非法CPP enum值。完整 `zrF` 在索引选择前有 `hartSupports(F)` 断言；其值及caller域仍OPEN。抵达列定literal false断言后，实际 `sail_assert` 先输出消息并 `exit(EXIT_FAILURE)`，因此紧邻的生成 `sail_match_failure("rF")` 不会沿此正常控制链执行；`c_backend.ml` 的实际 `I_exit` 降低规则也已绑定。

`bf16/native-generated-cpp-runtime-probe-v1/` 用原模拟器实际链接的 `libsail_runtime.a` 做两次小探针：true返回0且输出 `ASSERT_RETURNED`，false退出1且仅输出 `Assertion failed: invalid floating point register number`。这只验证已链接runtime断言，不执行完整Model。CPP的进程退出与Isla的 `AssertionFailure` 分别记录；不从二者推断异常恢复或state关系。本包新增模型运行、source分支观察、source排除均0。

### 共享type有限正式证的BF消费

共享正式消费 `shared-native-type-declaration-inventory-reviewed-v1.json` SHA-256 `2bc5e03c20fec2d42b347d455af03588dedbef6e039bca17072f18ef9dc4c4a6` 绑定正式证 `7ecdf0bc3adcf4f05a5fc40cb1db3695f7b0cb767c61aff5e74bf2e72f04b34e`；仅许可完整type身份、保守unit附件及每域列定13个measure声明表达式作为build前件。

[BF消费器](tools/solve_bf16_coverage/bf_native_type_review_consumer_v1.py)5项TDD红到绿；直接复用共享 `consume`，逐条核BF952/956附件与正式全unit附件相等，再按backend、真实definition_key及声明ID绑定每域10个BF关联measure。命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_native_type_review_consumer_v1.py` 自然退出0，生成 `bf16/native-type-declaration-attachment-reviewed-v1.json` SHA-256 `09dfbd8563d33c57b5700aac02e10498e58f85e910debbd1c85d2ce9e26aa609`，260依赖。

原root与引用/义务ID不变，没有重跑AST或按measure名字删除同名runtime helper/caller。配置实际求值、undefined实际绑定、outcome实例化仍OPEN；保留共享证对历史live457三项漂移的失败边界，不扩成新producer完整性许可。三个closure标志仍false，source排除和动态覆盖增量0。

### typed constructor的实际入口前缀与encoder拒绝后缀

[实际标签路径工具](tools/solve_bf16_coverage/native_bf_tag_prefix_v1.py)7项TDD红到绿，生成 `bf16/native-typed-constructor-dispatch-prefix-v1.json` SHA-256 `b99955ac5d9f1889023dc9f01188b59cf69e8f790049f69d3d062d3545cd68f8`，552依赖。命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_tag_prefix_v1.py` 自然退出0；三配置共36个encoder/execute前缀及18个encoder guard false后缀关系候选，待独审。

在入口参数是实际固定标签的 `Val::Ctor` 时，六BF encoder路径长度371至376、execute长度386至391，仅经过局部Decl及同一参数的Kind比较；按executor真实语义，Kind返回“标签不等”。每条精确PC路径以原生matcher主位置、clause ID和v2两入口域ID绑定。encoder目标guard正常false进入后缀后，其余不同标签只做比较，最终抵达PC31276 `MatchFailure`；这条拒绝路径没有供official decoder使用的成功word image。

这些局部路径在**未截断前提下保持model寄存器及隐式lets**；execution-limit bookkeeping会改变，预算截断和外部中断另列，不能称无条件runtime total。目标guard调用的值/状态/异常仍不透明，suffix仅相对其入口状态保持不变。audit encode/execute或official execute只能在实际decoded值已具有该标签时应用此关系，不能反向限制decoder原word域。

完整native前后规则均保留。实际encoder外层标签检查为378个，native encdec为392条；实际decoder option边界381个。计数差可能涉及编译合并/消除，尚须逐条来源关系，不能据路径纯读而删除未联立source分支。

### decoder六个目标块的实际状态与失败关系

[decoder关系工具](tools/solve_bf16_coverage/native_bf_decoder_relation_v1.py)6项TDD红到绿，命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_decoder_relation_v1.py` 自然退出0，生成 `bf16/native-decoder-local-state-relations-v1.json` SHA-256 `fb618dc301db45799c5f0e89b93ae02bd5de70ae113faea3957f1834af40362f`，555依赖，待独审。三配置共18个完整目标块、54条Some/None局部路径及3条最终ILLEGAL复制关系。

| BF目标 | 实际block入口 | 正常拒绝后缀入口 |
| --- | ---: | ---: |
| FCVT_BF16_S | 45968 | 46085 |
| FCVT_S_BF16 | 46085 | 46202 |
| VFNCVTBF16_F_F_W | 46202 | 46321 |
| VFWCVTBF16_F_F_V | 46321 | 46440 |
| VFWMACCBF16_VV | 46440 | 46559 |
| VFWMACCBF16_VF | 46559 | 46678 |

每个目标以真实constructor输出位置联立native clause；各mapping matcher与infallible binder分别按原生调用完整位置和次序核等。实际CFG验证：pattern成功门支配binder，binder支配guard入口，最终guard门支配constructor输出，完整block只有列定入口可从外部进入。pattern false与guard false各构造一个None，按实际局部复制及Some标签检查进入下一后缀；Some走成功归并。所列CFG关系不证明不透明callee总性或值域。

这里修订dispatcher v2中“异常即时终止”的笼统抽象：**Sail异常flag和Poison可以作为callee返回状态继续运行，只有实际检查点才消费它们；executor error另作终态。**matcher/infallible之后并非都有have_exception检查，不能在抽象图中提前终止并略去真实后继。每个Call保留 `Returned(value, σ')` 或 `ExecutorError` 关系，whole attempt纯读及total均为false。

实际最后拒绝点PC46973后，ILLEGAL构造PC46976携带原始word，经完整复制链返回End；不会清除继承的异常flag，phase成功仍须wrapper实际检查。此结论以已抵达最后拒绝点为前提，不证明此前381个option尝试都失败，也不证明任何完整D的最终译码值。official成功encoder关系像与audit独立word/初态继续分列；完整source分母及CPP dispatcher降低仍OPEN，动态覆盖和静态排除增量0。

### enum/rF双后端局部独证正式消费

前述两个候选现已由 `bf16/independent-generated-enum-assert-bridge-review/certificate.json` SHA-256 `0a67905173ccb381b37cfa04e34f7e23e52c1e7265a3f6ae499ea3c3cf7c0727` 独审为 `PASS_FOUR_LISTED_NATIVE_NODE_LOCAL_IR_CPP_RELATIONS`。独审重跑13项既有测试、9项实际产物变异负控与2次重链runtime探针；这些仅支持列定局部关系。

[正式消费器](tools/solve_bf16_coverage/bf_generated_backend_review_consumer_v1.py)7项TDD红到绿，逐项重核19个签名文件、616项独审依赖和844项完整上下文依赖；命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_generated_backend_review_consumer_v1.py` 自然退出0。输出 `bf16/native-generated-backend-local-relations-reviewed-v1.json` SHA-256 `c3c96767edf51fc345ba0e6a29851cad67ca4dd6050b3ded5840c4760ba44db0`，866依赖。

原14个来源全部保留；仅两域enum/rF四个精确 `(backend, unit_id, node_id)` 新增局部后端许可，余10个type生成节点仍OPEN。历史 `ir_lowering_status=OPEN` 保留其逐rewrite-pass轨迹未签含义，局部许可另记 `local_backend_bridge_status`，不能用后者扩成完整生成链结论。两个真实ATyp_if、完整24个raw类型条件、454项原路径与3项精确历史snapshot边界均保留。

许可前件仍为：enum同类型合法五成员、正常非Poison参数；rF真实控制已到列定literal false断言。caller/index/FS/扩展前件、完整Model运行与两后端异常恢复/状态等价均未签。来源分支覆盖与静态排除增量0，三个闭合标志仍false。

### 完整392条source到381个decoder option边界的分组

前文计数差“可能涉及编译合并/消除”的调查现有逐条关系候选。[分组工具](tools/solve_bf16_coverage/native_decoder_partition_v1.py)5项TDD通过，语法与尾空白检查通过；命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_decoder_partition_v1.py` 自然退出0，冻结 `bf16/native-complete-decoder-source-partition-v1.json` SHA-256 `427578f1f394d2d7628fc8df10323189a5fde37c3a3ab5a7cb0c9a6a881bb87a`，558依赖。三配置1176个source绑定、42条残余拒绝关系、12个共享source组；已交增量独审，尚无正式许可。

392条native encdec中，末条ordinal391是ILLEGAL；前391条按原顺序映射381个实际option边界。四组source共用边界：

| source ordinal | 构造器 |
| --- | --- |
| 2、3、4 | PAUSE、LPAD、UTYPE |
| 33、34 | FENCE_TSO、FENCE |
| 35至40 | ECALL、MRET、SRET、EBREAK、WFI、SFENCE_VMA |
| 375、376、377 | SFENCE_W_INVAL、SFENCE_INVAL_IR、WRS |

实际成功constructor输出378个（含ILLEGAL）另列，不能与option边界混算。无成功输出的14个source为69 ZBB_EXTOP、71 REV8、300至309的四个AES32与六个SHA512、328 ZIP及329 UNZIP。**这些source的matcher、infallible binder和两条None拒绝仍在完整IR，未删除任何整条source义务。**

成功输出按原生value主位置和constructor精确绑定；14个残余块按原生matcher主位置、每个mapping调用位置/次序绑定，验证两None切断所有entry到option join的CFG路径，并沿真实复制链进入后缀。全部source ordinal拼接恰为0至390，无缺漏重复且顺序不变。保存源guard真实文本，但guard常量化实际桥、callee值/状态合同、CPP dispatcher关系及完整D可达仍OPEN，覆盖与排除增量0。

### setter来源独证接回完整BF raw表

共享 `shared-native-setter-source-identity-reviewed-v1.json` SHA-256 `4342fe34a7bf65feaaaa4fb29e395ffa3f4f204b55c8e306ef9a7914e66f8966` 仅许可241个精确setter来源身份。[BF消费器](tools/solve_bf16_coverage/bf_native_setter_review_consumer_v1.py)6项TDD红到绿，复用共享 `native_setter_review_consumer.consume` 重消费并与冻结包全等；再按backend、unit、raw scope/node及effect类别逐项附接BF7/15个setter。

命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_native_setter_review_consumer_v1.py` 自然退出0，输出 `bf16/native-raw-setter-source-identity-reviewed-v1.json` SHA-256 `0f06a6c5e807f9963b1c4e3b0a5c407be64843cec9f03eda9d454027f6957489`，762依赖。全部968/1107原始事件及effect义务保留；来源投影pending从112/119降至105/104，余项仍为config93/93与sizeof12/11。

本轮没有重扫AST、改写旧raw包或删除写效果。正式许可不覆盖setter callee值/状态、actual IR或运行分支；历史live来源3处漂移及初次失败边界照旧保留，覆盖和排除增量均0。

### 六BF dispatcher局部独证正式消费及所有权前件

`bf16/independent-native-dispatcher-local-relation-review/certificate.json` SHA-256 `fb7fc78d358b40eafe5bfb0488872126382e4c71fb058309ebcebca0075eb208` 已签有限36个typed前缀、18个encoder拒绝后缀、18个decoder完整局部块、54个option路径及3个最终ILLEGAL路径。独审完整复演与原产物逐字节相等，13项producer测试、4项新增所有权TDD、5项真实负控通过。

[消费器](tools/solve_bf16_coverage/bf_dispatcher_review_consumer_v1.py)6项TDD红到绿，重核21个签名文件及560个独证依赖。命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_dispatcher_review_consumer_v1.py` 自然退出0，输出 `bf16/native-dispatcher-local-relations-reviewed-v1.json` SHA-256 `161dca54081606c9e4d65caf96f10226bd47e70a226e0d3de79c6e3952a17c31`，582依赖。

每配置完整保留421处去重写入的前件：唯一已执行Decl支配写点，或RETURN在frame入口创建。实际executor的Id赋值先查frame vars、再查lets、再写register，因此不能仅凭Id复制声称保持模型状态。Some读取支配它的已初始化BF constructor输出，None读取Unit；六BF及Some/None/ILLEGAL均绑定实际union身份且无同名函数。原word仅PC1写入并支配最终拒绝点。

每配置6个have_exception真边抵达PC47360 Arbitrary，实际行为是向caller或顶层返回Poison；wrapper真路径为1→3→5，假路径为1→2→4，lets不会因callee返回自动清除。这里进一步限定前述 `Returned(value, σ') OR ExecutorError`：它只描述分析中的返回及错误片段，**并非不透明callee的穷尽终态列表**；显式退出、中断和不返回仍单列未证。

state保存仅指列定路径相对其入口的模型寄存器与隐式lets；frame局部、trace、探针、预算记账可变。typed前缀要求顶层已初始化具体Val::Ctor，payload可含合类型符号数据，未知SymbolicCtor/Poison顶层不在许可内。所有source prefix/suffix仍保留，完整D、encoder成功像、ordinary CPP及完整分母继续OPEN；392分区包另审，动态覆盖与静态排除增量0。

### config及局部sizeof来源独证增量消费

共享config包 `shared-native-configuration-source-identity-reviewed-v1.json` SHA-256 `99c5cce2564700897a95f15e66864b2f0d26fd82ca84f393b525aa4a454d7105`、sizeof包 `shared-native-sizeof-source-identity-reviewed-v1.json` SHA-256 `85f1fce63c3e9ad5d8399ed6fa1acbba6a17276e7db6d7ed439bb45d3dce387a` 已正式冻结。[BF消费器](tools/solve_bf16_coverage/bf_raw_source_review_consumer_v1.py)5项TDD红到绿，复用公共 `consume(mode, reviewdir)` 重消费并与两冻结包全等，再按精确backend/unit/raw scope/node附接原raw事件。

命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_raw_source_review_consumer_v1.py` 自然退出0，输出 `bf16/native-raw-source-identities-reviewed-v1.json` SHA-256 `ec5735f5cea8da6871570ea2474570572b21540ea0612187f420cfbd4c365215`，861依赖。共2075原始事件、22个已审setter全部保留，新许可config93/93及局部sizeof11/10准确来源；每后端各余1个flen named alias，保持原样pending。

普通CPP的E_config保留运行时读取，SYMBOLIC实际导出值仅作来源关系；局部sizeof只签raw表达式到实际size overload的来源。actual IR、callee语义、局部binder解析及完整分母仍未签。未据配置常量或alias删除条件，覆盖与排除增量0。

### 完整381个实际decoder块的状态关系组合候选

[完整关系工具](tools/solve_bf16_coverage/native_complete_dispatcher_relation_v1.py)7项TDD红到绿，命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_complete_dispatcher_relation_v1.py` 三配置逐一自然完成。输出 `bf16/native-complete-decoder-ordered-state-relations-v1.json` SHA-256 `3684f8689996b9200d104ac9af08bf9ac481082cfc90e8e0fdfb89f5f3417ec6`，588依赖；候选已交独审排队。

完整47,361 PC的decoder在每配置均分为381个有序option块及尾部，所有跨块入口只落对应entry。离块边精确分为option正常拒绝、Some成功归并与Arbitrary返回，三配置共1,572条Arbitrary出口全部保留。未把Arbitrary视为自动executor error，也未丢弃显式异常flag检查。

共1,143个条件Some归并关系静态跟踪完整PC链，证明真实已初始化Some的payload精确传到RETURN/End。复用已独审的 `verify_local_writes`，三配置分别核1,143个去重成功链写点，共3,429处Decl/RETURN局部所有权；没有借默认配置替代alt。14残余源码即使没有成功输出，也保留条件成功链作为实际CFG结构，其可达性不由本包签署。

关系递推保留完整Σ（模型寄存器/lets、frame局部、solver约束及预算记账），逐块用真实拒绝边连接，不能投影成同一模型状态上的布尔合取。全部actual Calls/Primops及392个source身份仍在；callee错误、显式退出、不返回、solver失败及预算/外部中断另列。完整D、ordinary CPP、encoder成功关系像、共享source组内部语义和source guard常量化仍OPEN，动态覆盖与静态排除增量0。

### 392来源分区独证正式消费与计数澄清

`bf16/independent-decoder-source-partition-review/certificate.json` SHA-256 `0bad19ef39038627b84d370b013339e13f367492eee10316e03715d2958b1c79` 已签冻结SYMBOLIC来源身份及局部runtime分区关系。5项producer测试、8项独立测试、25项实际输入负控及完整复跑通过；587文件重核。

[正式消费器](tools/solve_bf16_coverage/bf_decoder_partition_review_consumer_v1.py)5项TDD红到绿；命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_decoder_partition_review_consumer_v1.py` 自然退出0，输出 `bf16/native-complete-decoder-source-partition-reviewed-v1.json` SHA-256 `49a6affa73d23301c2ceb9e0afd474d2a141ec86cdb8359d8293207aa86615e5`，591依赖。

此处澄清候选字段 `residual_none_relations=42`：它实际计数为**42个残余块，包含84条独立None到suffix路径**。正式消费按1176个source身份和84条完整路径逐条联立，附接168处真实写点的Decl支配前件。历史候选字段及产物保持原样。

14条source及其matcher/binder/两None全部保留，四共享source组精确不变。最终ILLEGAL在本证仅签source身份与constructor PC，原word完整返回链继续由前述fb7fc78d局部证承担。guard常量化、CPP、callee、完整D、raw到typed完整来源桥和全source分母仍OPEN；没有新增覆盖、静态排除或整条source删除许可。

### 完整381块有序状态关系独证正式消费

`bf16/independent-complete-decoder-ordered-review/certificate.json` SHA-256 `6b5a5cfaeb8514f4164adaeade12a67bd051e53723af7b35cd77d244e4965f3f` 已签前述完整CFG关系。独审重核588依赖、591输入及616文件，7项producer测试、8项独立测试和18项负控通过；独立DAG支配计算与原局部所有权工具一致，复跑关系一致。

[正式消费器](tools/solve_bf16_coverage/bf_complete_dispatcher_review_consumer_v1.py)5项TDD红到绿，命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_complete_dispatcher_review_consumer_v1.py` 自然退出0。输出 `bf16/native-complete-decoder-ordered-state-relations-reviewed-v1.json` SHA-256 `6ac50ec1fe93c513bfbc3f38491fc7c8fea1e0e54d03d09548b23bcbc0e4e93e`，620依赖。逐配置381块联立完整组合、Some前件hash、Calls/Primops/异常检查PC和3429处ownership；所有callee、来源可达、CPP及完整D边界保持OPEN，动态覆盖和静态排除增量0。

### 有限mapper及六BF原word pattern合同候选

[mapper/pattern工具](tools/solve_bf16_coverage/native_bf_mapper_pattern_contract_v1.py)复用已审scalar `Types`、`Fields`、`helper_run` 和 `local_boolean_run`，7项TDD红到绿；命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_mapper_pattern_contract_v1.py` 自然退出0。冻结 `bf16/native-finite-mapper-and-caller-pattern-contract-v1.json` SHA-256 `6be46ab6a4a5de961824ba2e4bbc7d472cbb4d1fa33089aa279bc7554b4843dd`，647依赖；已交独审，当前仅候选。

三配置各自完整重算freg/vreg/rounding三个mapper，共216个有限输入；default freg/RM证明与既有scalar正式包逐结构相等。SYMBOLIC源8个mapping clause的双向AST、48对真实matcher/binder同word同slice参数及每配置512行pattern原子真值表全部联立。freg/vreg全部32值恒等返回；RM的0至4及7映射六个合法enum，5/6 matcher返回false。域外unchecked `_backwards_infallible` 实际读未初始化局部，不能写成具体enum或MatchFailure；普通 `_backwards` 的失败行为另列。

原生 `L_bin` 的分组digit AST由新增负控核对；初次错误字符串假设在冻结产物前修正，历史失败不转作PASS。正常已初始化非Poison有限参数、真实pattern成功门与None后缀前件保留。`currentlyEnabled`、`get_sew`、caller状态及所有入口D仍未由本包签署，未新增动态覆盖或静态排除。

### 最后两个flen named sizeof来源正式附接

共享 `shared-native-named-sizeof-source-identity-reviewed-v1.json` SHA-256 `cdf9e3e3e97d80b6b3c4e54a6eac27e8aafcf0b910df2d5e9edfe2f6e04044b6` 的两个BF来源许可已接回原raw表。[BF消费器](tools/solve_bf16_coverage/bf_named_sizeof_review_consumer_v1.py)复用公共 `consume`、vector `join_named_sizeofs` 及其scalar完整行join，5项TDD红到绿，语法与尾空白检查通过。

命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_named_sizeof_review_consumer_v1.py` 自然退出0，冻结 `bf16/native-raw-source-identities-reviewed-v2.json` SHA-256 `ae1c62fee5a2e0c72daba5911d4cea3e0578cbecd74471dae3cf5da8f78b5deb`，901依赖。各域1个flen的准确scope/node、完整候选行、numeric alias表达式和嵌套控制均核等；2075原raw事件、22setter、186config、21局部sizeof来源保留，原pending事件另作历史字段。

仅这组已选raw事件的来源投影pending从1/1降到0/0；完整分母、反向来源、模块绑定、callee与入口D仍OPEN。嵌套E_if保留，未签配置折叠或actual IR；未新增运行覆盖、静态排除或完整依赖闭合许可。

### 有限mapper与实际pattern独证正式消费

`bf16/independent-finite-mapper-pattern-review/certificate.json` SHA-256 `9c21989f35e33c4e810520e786ae43bab9dcb8776fed7dc60236b3db99129acb` 已签8个双向来源mapper、六个完整32位word布局、216输入、48对调用和1536行pattern真值路径。7项producer测试、9项独立测试和19项实际负控通过，738冻结文件全部复核。

[正式消费器](tools/solve_bf16_coverage/bf_mapper_pattern_review_consumer_v1.py)5项TDD红到绿，语法与尾空白通过；命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_mapper_pattern_review_consumer_v1.py` 自然退出0。输出 `bf16/native-finite-mapper-and-caller-pattern-contract-reviewed-v1.json` SHA-256 `bc6cf2a62c8a5c5fd1ce70e478653e934ba7113ee288fb3a6bc7d6249082cb6e`，742依赖。

每配置完整有限表、双向来源身份、pattern路径、binder准确PC及gate支配/拒绝不可到binder全部联立。独审进一步明确：RM5/6的unchecked infallible在PC79首读未初始化local2412，实际runtime创建fresh symbolic值；候选解释器null不等于运行时None或自动ExecError。

局部正常执行前件下，helper私有frame、pattern前缀及准入binder前缀仅写已声明locals，保持model寄存器及implicit lets，包括继承的异常槽；caller实际赋值仍保留。此项不要求incoming exception为false，也不清除它。完整Σ、guard、入口D、CPP、符号总性和完整分母仍OPEN，新增覆盖和静态排除均0。

### 三配置BF当前guard与get_sew完整局部合同候选

[实际guard工具](tools/solve_bf16_coverage/native_bf_guard_contract_v1.py)复用scalar `ConstantIR`、`getter_projection` 和既有V4 `expr/prim/run`。原V4控制层不支持enum条件及Arbitrary，旧StateIR又预置异常flag为false，因此新增有限控制层，保留真实Decl、Call、callee返回和caller异常检查。9项TDD红到绿，语法与尾空白通过；命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_guard_contract_v1.py` 三配置完整运行并自然退出0。

候选 `bf16/native-three-config-guard-and-get-sew-contract-v1.json` SHA-256 `b764fa265e7ed4cedd2dcd1eb90ad8fdeccb4595cd4a34a1f16a5157c826c156`，772依赖、676完整递归实际关系，已交独审。每配置完整八个Ext上下文及八个hartSupports能力路径；default六个已审能力的完整路径与scalar正式证相等，alt各自重算。四个getter精确投影任意正常64位输入：misa.F、mstatus.FS/VS及vtype.vsew；其余位不参与本组guard。

共576行currentlyEnabled投影、24行get_sew八值表及9216行六个准确decoder guard组合，保留F二值、FS/VS各四值、vsew八值和incoming have_exception真假。局部向量能力let为实际初始化的Full、已抵达准确guard首个Decl且按实际函数体执行是前件；本包不证明此前381个尝试维持这些前件。

| 实际caller终态 | 投影组合行数 |
| --- | ---: |
| 正常guard false | 3492 |
| 正常guard true | 684 |
| Arbitrary返回Poison | 4608 |
| get_sew的AssertionFailure | 432 |

incoming异常flag为true时，三个BF扩展与六caller均在真实检查点走Arbitrary，Poison仍是返回值，不等于正常false或自动ExecError。flag为false时，scalar启用条件为F且FS非零；vector再要求VS非零，不读misa.V。向量decoder先判断扩展，true才调用get_sew；vsew0至3分别给8/16/32/64且只有16通过，4至7触发实际断言失败。扩展false会跳过get_sew，因此不能给所有非法vsew一律标断言失败。

所有实际写点检查已创建frame局部，model寄存器和implicit lets仅在这些局部合同内保持；完整solver/path/bookkeeping不宣称恒等。表格不是动态运行或来源分支观察，不把guard合取代入381全部前缀，不由结果constructor倒推official/audit D。符号runtime总性、executor/solver错误、资源/预算、中断、不返回、CPP、完整来源降低及分母仍OPEN。

### 初始编译pass的五个BF条件literal正式附接

共享 `shared-native-initial-pass-literal-reifications-reviewed-v1.json` SHA-256 `68c21ced853cdde4b8e53c61bc6b7f33a14cfb95033051b520438cf8db8e277f` 已正式消费331个列定literal；[BF附接器](tools/solve_bf16_coverage/bf_initial_pass_review_consumer_v1.py)复用其 `consume` 并重核冻结全等，以完整before节点hash、准确backend/node、top definition和condition AST path连接BF子集。

5项TDD红到绿，语法及尾空白通过；命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_initial_pass_review_consumer_v1.py` 自然退出0。输出 `bf16/native-generated-control-with-initial-pass-reviewed-v1.json` SHA-256 `4078f34757d66d4afb5a96678cd8a0458c1aea9c639920876a98865b97c07093`，1958依赖。

仅SYMBOLIC五处条件联立已签literal ID：flen、rF_BF16、wF_BF16、wF_S为true，fregidx_to_regidx为false。两后端共十个原生E_if及其两臂均保留；普通CPP五处条件仍为E_constraint。完整原14来源、24raw类型条件与既有enum/rF四处局部后端许可均保留。此项不签控制消除、完整Type_check Env、actual IR、运行分支或完整分母。

### 当前权威输入和剩余语义门导航

`bf16/authoritative-inputs-and-remaining-semantic-gates-v1.json` SHA-256 `fd0d4eb2954e93c819398466b7f64ba267d4dc3306e873c75757350946603c67` 汇合九个冻结输入，并按source、typed、IR、caller、D去重列出八个未过门类别。每行明确已审许可、剩余前件、下一步与owner；双后端36个原root及完整occurrence、external、unresolved映射按准确输入和JSON pointer保留，不重新编号或删除。

八类分别是完整来源闭包、生成控制逐阶段降低、完整decoder其它callee、ordinary CPP、六BF准确guard、六BF encoder成功像、official连续状态D、audit各phase重新初始化D。该表只作当前导航，不是新source分母，不改变RHS186/BF8/BF4既有范围。guard的9216理论行继续与动态覆盖分列，encoder成功像工作继续。

### 三配置guard全64位局部合同正式消费

独证 `bf16/independent-three-config-guard-and-get-sew-review-v1/certificate.json` SHA-256 `2cd9ed2e1b86b787639f24f776fec770f544f463879b20ff9d0912e557ddbeb7` 已签冻结候选；9项producer、11项reviewer、22项负控及108个primitive/range检查通过。四getter由独立完整抽象term证明任意正常64位CSR的准确投影，并核所有实际整CSR读取仅进入这四个getter；不以采样代表全域。完整676递归关系与9216 caller行一致，实际get_sew调用864次。

[正式consumer](tools/solve_bf16_coverage/bf_guard_review_consumer_v1.py) 7项TDD由缺模块RED到GREEN，语法及尾空白检查通过。命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_guard_review_consumer_v1.py` 全重核870个独证文件后自然退出0，产物 `bf16/native-three-config-guard-and-get-sew-contract-reviewed-v1.json` SHA-256 `7a098afd9c47c55b9be4eb4db4cd3e57c5d68fafdd296aa1e248cae6007dba6a`，874依赖。

正式合同保留五个局部前件：已到达准确guard首Decl、正常初始化64位CSR及准确enum、Full、incoming异常Bool、执行真实函数体。异常true经实际Arbitrary返回Poison；AssertionFailure对应实际ExecError，表内null表示无正常返回。未初始化首读实际创建fresh symbolic，独审拒绝表示超出初始化证明域，不能称必然runtime error。完整381前缀保持/可达、full D、其它callee、CPP、symbolic总性及完整分母仍OPEN，覆盖与排除新增0。

### 六BF encoder具体成功word及局部payload逆向候选

[encoder工具](tools/solve_bf16_coverage/native_bf_encoder_image_v1.py) 复用scalar Types、Fields及既有helper_run，仅为真实constructor Unwrap增加薄表达式规则。10项TDD由RED到GREEN，语法及尾空白检查通过；命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_encoder_image_v1.py` 三配置完整运行自然退出0。候选 `bf16/native-three-config-local-encoder-success-image-v1.json` SHA-256 `f78c10cee02ba2b1b2673867b950d3c048a9f07cf62133a046ee7234224048a2`，890依赖，已交独立审者。

每配置两个寄存器mapper各32值、rounding enum六值，共210正向输入与210已准入反向输入联立；恢复18个完整32bit word布局及60个准确decoder payload字段。18个encoder/decoder guard CFG按实际局部变量alpha改名相等，保留所有Decl、Call、Primop、Jump/Goto与Arbitrary，未预设guard成功以删除拒绝控制。完整成功返回链至RETURN/End仅写已创建locals。

append与append_64的实际同指针别名、冻结primop完整body、BV append及B129 MAX_WIDTH=129均绑定；实际中间宽不超过32，因此具体Bits分支返回Some且不调solver。本轮许可限正常具体有限payload；符号/MixedBits运行值提升另证。局部payload逆向不证明完整decoder此前381次尝试拒绝、完整round-trip、official/audit D或CPP。候选保持其历史guard输入b764不改写；正式后继需附接已签guard许可。

### 权威输入及剩余语义门v2

后继导航 `bf16/authoritative-inputs-and-remaining-semantic-gates-v2.json` SHA-256 `bc3d99e828bedf1bb619699e87306d3f3c9fe0b100adea57cec16f5847052718` 重核原九项及新增两项输入。v1冻结保留；v2加入正式guard和待审encoder，准确保留Full、到达guard、前缀、完整D及symbolic总性等剩余门。八组仍为导航，原36root、occurrence映射及全部source身份未改号或删除；三个闭合标志仍false。

### Encoder符号bits与MixedBits正常word关系候选

[符号bits工具](tools/solve_bf16_coverage/native_bf_encoder_symbolic_bits_v1.py) 8项Python TDD及[实际Primops runner](tools/solve_bf16_coverage/encoder_symbolic_append_runner_v1.rs) 2项Rust TDD均由RED到GREEN，`cargo fmt`、Python语法及尾空白检查通过。命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_encoder_symbolic_bits_v1.py` 完整三配置自然退出0，产物 `bf16/native-three-config-local-encoder-symbolic-bits-image-v1.json` SHA-256 `f6ffab9fdc9c01fb4c706f127702a9c797b76d76ee766c5a3cd52b340901c87f`，1452依赖，已交增量独审。

实际freg/vreg正向mapper在三配置的完整六PC仅作正常初始化bits5局部复制，因此保持Bits、BV5 Symbolic或完整MixedBits表示。原语部分绑定append完整九个表示组合、具体BV代数及`smt_value`完整segment左fold；所有段正宽、MixedBits非空、字段总宽准确、实际中间宽≤32时，正常返回值表示的位串等于有序Concat。Symbolic/Symbolic仍创建实际solver定义，不能声称solver/path/frame/bookkeeping恒等或runtime总性。

runner复用冻结库公开`Primops`、`smt_value`与Solver API，沿候选的实际encoder表达式树调用真实append，并与原生layout的独立拼接比较。972个三配置word/表示组合及九个原语表示配对共981项，均先验证solver基底SAT，再验证不等式UNSAT；反序Concat负控可SAT。runtime报告、编译日志和锁文件在 `bf16/encoder-symbolic-bits-runtime-v1/`；510个冻结runtime源码输入在编译前后复核，实际binary与动态链接libz3均绑定。

本提升仅针对bits1/bits5正常字段；RM仍为六个合法具体enum之一。981项是直接原语检查，其中符号段未约束、具体段为列定值；一般任意正常段序列关系由源码代数候选承接，不将这些检查称为全表示穷举或新增model source观察。完整decoder符号切片/mapper接线、完整D、前381拒绝、CPP及符号总性继续OPEN。f78c和导航v2保留冻结；本后继候选不改变正式许可与三个闭合标志。

### 具体encoder成功像独证正式消费

独证 `bf16/independent-three-config-local-encoder-success-image-review-v1/certificate.json` SHA-256 `f288b8606df6aa41381e306a769a5ab7f2f333d10c0124aed2ae245e9e7da18e` 已签f78c的有限具体范围。931输入重哈希无漂移，10项producer、8项独立TDD、8项实际负控通过，完整producer复演逐字节相同；独立重算210正反mapper、18完整word及60字段、18 guard PC/局部变量双射、108个具体append实际位宽。审者额外核了Decl杀死旧值、decoder word准确根复制且后续无改写/Ref，以及guard实际11callee体逐配置相同。

[正式consumer](tools/solve_bf16_coverage/bf_encoder_image_review_consumer_v1.py) 6项TDD由缺模块RED到GREEN，Python语法及尾空白检查通过。命令 `python agents/float_support_review/tools/solve_bf16_coverage/bf_encoder_image_review_consumer_v1.py` 完整重核931输入与21独审输出后自然退出0，正式包 `bf16/native-three-config-local-encoder-success-image-reviewed-v1.json` SHA-256 `c1d8903ba768f0cf30658b8dd4afa289b827bb94ce427a8d61439675b8e247ac`，955依赖。首次完整执行因误把独审输出manifest的`{bytes, sha256}`对象当SHA字符串而拒绝；按实际schema核哈希与字节数后成功，没有放松核验。

正式包精确附接b764候选→2cd9 guard独证→7a098正式guard链，只授正常具体Val::Ctor及bits1/bits5字段、合法六RM、原guardtrue局部前件下的word/局部payload逆向关系。Symbolic/MixedBits候选f6ff未消费；前381、完整official/audit D、CPP、符号总性和完整分母仍OPEN。已有三闭合标志保持false，覆盖及排除新增0。

权威导航后继 `bf16/authoritative-inputs-and-remaining-semantic-gates-v3.json` SHA-256 `730cb029e658198d868ca2da9ed3a01dc893f261865585716b88e55907e9325c` 重核13个输入，加入正式具体encoder及待审符号bits入口；v1/v2保持冻结。八组剩余门及36原root映射不改号，official D组只附接已签局部具体成功像，完整入口前件与连续state/decoder前序关系仍保留。

### Symbolic RM准确六enum正常路径候选

[RM工具](tools/solve_bf16_coverage/native_bf_symbolic_rounding_v1.py) 5项Python TDD及[真实executor runner](tools/solve_bf16_coverage/symbolic_rounding_runner_v1.rs) 2项Rust TDD由RED到GREEN，`cargo fmt`、语法及尾空白通过。命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_symbolic_rounding_v1.py` 自然退出0，产物 `bf16/native-three-config-symbolic-rounding-enum-contract-v1.json` SHA-256 `72e1ee52a53517f0f39a62d897d2290adae54c187696502ce92a65041db6d4e2`，1479依赖。

三配置RM完整19PC、五个实际Neq及六成员enum与正式具体encoder逐条相同。六正常路径在准确enum域内互斥且穷尽：前五分别RNE/RTZ/RDN/RUP/RMM，最后五个不等式只剩DYN，返回bits3={0,1,2,3,4,7}。runner逐字抽取原enum、signature和完整helper体，复用真实parser、SharedState、LocalFrame、start_single及Solver，从已声明正确sort的Symbolic Enum起跑；incoming exception真假各六条正常路径，共72成员可满足性检查，逐路径唯一成员SAT、其它UNSAT，全部implicit lets保持、无采样。

运行输入、完整报告和编译日志在 `bf16/symbolic-rounding-runtime-v1/`，TDD证据另在 `bf16/symbolic-rounding-runtime-tdd-v1/`。初次GREEN编译因LocalFrame/Run没有Debug而拒绝，改为只打印实际ExecError及固定非正常退出说明后通过；失败日志保留。510冻结runtime源码前后重核，binary及实际libz3绑定。

这是两次准确局部helper执行及三配置完整体/类型的适用性桥，不冒充三配置完整encoder执行；源码分支观察和排除新增0。已有约束可以排除不可达enum路径；solver Unknown/错误、预算、资源和中断仍单列。此候选尚未正式附接encoder像，f6ff符号bits候选及v3导航保持冻结，完整D和前381拒绝仍OPEN。下一优先为encoder word像上的真实完整decoder前缀正常拒绝关系。

### 具体encoder像上连续decoder块0/1候选

[前缀工具](tools/solve_bf16_coverage/native_bf_encoder_prefix01_v1.py) 及对应测试完成8项TDD红到绿，语法和尾空白检查通过；命令 `python agents/float_support_review/tools/solve_bf16_coverage/native_bf_encoder_prefix01_v1.py` 自然退出0。候选 `bf16/native-three-config-concrete-encoder-image-prefix01-v1.json` SHA-256 `a8608b06802c55f2b30904c168fe1470618cd3334777a8f6ec3f2a452fd80568`，964依赖，已交独立审者，工具和候选冻结。

本候选从三配置真实decoder PC0开始，连续联立块0的ZICBOP和块1的NTL，状态按PC0→107→209递推。六个正式具体encoder像的固定literal给出保守word上界；实际先行cbop、reg、ntl matcher每配置128个完整有限输入（reg包含base_E_enabled真假），共384输入及6个实际嵌套znot输入先证明正常Bool和仅局部写。随后保守展开360条原子Bool组合，逐条沿真实短路、opcode比较、Not、Goto、None(Unit)、option复制及Kind检查到后缀。不能依据opcode不重叠跳过先行callee。

所有可执行写点均检查唯一实际Decl及从PC0支配，完整reg matcher内嵌znot实际两PC和两输入绑定；15条实际runtime片段约束具体比较、取bit4、域内切片、Decl和option语义。incoming异常不清除、不提前消费；仅对正常具体Val::Bits32与已初始化base_E_enabled Bool授条件关系，frame/solver/预算等仍按实际路径递推。测试负控包括缺matcher、修改opcode、模型写入、None载荷、嵌套znot及vector_access语义漂移。

本项只覆盖原381块中的前两块及原source ordinal0/1；块2的PAUSE/LPAD/UTYPE共享结构与其后全部来源、14条无成功source仍保留。符号word、完整前缀、official/audit D、CPP、总性及完整分母继续OPEN，新增source观察和静态排除均0。
