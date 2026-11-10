# 新 P1 完整指令 replay 独立审计

## 2026-09-27异常隐式let漏检勘误

**此前完整闭包纯读结论撤回；发现时暂停的连续语义签收，现已按文末[正常返回域补证](#正常返回域补证及最终限定签收)恢复为列定输入的限定PASS。** 下文保留原签收及冻结hash作为历史记录；已经逐条核实的AST、ret、102项post、八let及15项辅助回读匹配仍是实际运行事实。八let及15aux不包括下面三项异常状态，不能据此证明所有运行时状态不变。

新调查确认，主replay源码`5d07dceb…`的`decoder_purity`只把IR `Def::Register`和`Def::Let`纳入global集合，遗漏`LocalFrame::new`注入的`CURRENT_EXCEPTION`、`HAVE_EXCEPTION`、`THROW_LOCATION`。`executor::assign_with_accessor`向`local_state.lets`赋值不发出`WriteReg`事件，动态事件白名单因此也不能弥补静态遗漏。证书闭包包含`internal_error`特化，故原`global-writes=0`只能理解为工具对其不完整集合的结果，不能解释为完整闭包零状态写。

主runner在decode阶段传入`observed=[]`，仅证明返回AST唯一；`Outcome`未保存或检查这三项异常let。随后execute阶段以原`state.lets/regs`重新启动。现有成功结果JSON因此不能单独证明实际decode路径未写异常状态，也不能证明遗失这些状态不影响连续decode→execute语义。完整return/102post的UNSAT证明仍适用于该runner实际启动的各阶段；它未自动覆盖两阶段间未保存的状态。正常返回及handler路径是否排除异常写，正由架构审查按实际CFG与执行器语义核验，不能仅因字段名含exception就排除。

| 受影响范围 | 原纯读证书SHA-256 |
| --- | --- |
| 348147历史18,584输入及同版定向检查 | `41db23960433bfdc6a93240508710d6e30f9fcb74207e154f5ad45480ac235a3` |
| 56cc历史18,584、新官方D 1,096及长批wave001 6,230 | `7a82f0a56bf6d235f2625025a0584831bd73a967273020d59b1cd3b9bf4dc326` |
| wave001辅助encoder的decoder闭包 | `584660d1d6ec393405a183d5d9822d854897cd7bdc0ca2d760c9c2a9db879ae0` |
| wave001辅助encoder的encoder闭包 | `4dc811846323bade3f534bf0cae9aa7675dcd90511b9e8f0bfb876b761a9dd35` |

原证书、配对结果及审计JSON均未改写。发现时wave001仅签来源与全量实际观察，语义门槛暂挂；其后补充证明和修订结论另见文末，不将旧证书改为完整闭包PASS。

新官方D代表独审见[官方F_MADD_TYPE_D](#官方f_madd_type_d)。历史seed的新版本复验见[56cc69](#56cc69)。此前348147审计原文保留，其PASS仅适用于原冻结版本。

日期：2026-09-27。范围：新 IR `348147`、配对 C++ `cpp-r03` 与 Isla replay runner，完整历史 seed 集合。

## 限定签收

**PASS_SCOPED_HISTORICAL_FULL_SEED_REPLAY**：历史1dcc的全部18,477条gen、83条直接decoder负例和24条派生decoder负例，共18,584条，在新Isla与新C++中重新执行；独审逐条复核实际输出，完整AST、ret及102项post一致。所有输入ID恰好返回一次，两后端各18,584条可行执行结果；decode/execute Dead均为0。

这些输入来自历史完成的50个clause。新官方77项求解、完整源码分支闭合仍未完成；`whole77-complete`、`source-branch-closed`和`new-official-solve-output`均为false。本结论不扩展到未生成输入、另27个历史超时目标或访存指令。

独审未重新执行全量模型，而是核验已完成的真实运行产物、构建及输入来源，并独立遍历全部结果重新比较。审计命令退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-audit/audit_p1.py
python3 .tmp/unified-backend-cpp-replay-independent-audit/audit_full.py
```

审计只写本报告与ignored证据；实施工具、共享状态表和生产源码未由本独审改动。

## 冻结证据

本次运行根目录为`isla/target/float-solve-evidence/unified-backend-cpp-replay/p1-348147-20260927/`。下表列出关键绑定；完整文件哈希在审计JSON中。

| 对象 | SHA-256 |
| --- | --- |
| 新IR | `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061` |
| Isla FD配置 | `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0` |
| `cpp-r03/build-manifest.json` | `a8d3449148f050a9ba98df764e8a6df2f0401963516cc871083ce31fabc518ea` |
| `cpp-r03/cpp-init-contract.json` | `0577c80c0dbc42a813a673f30af261a0cee5605c29882859c91675bd74df0c6e` |
| C++ runner | `da361d1a221dbbd432db0b5eb094b761e68045517d021c0e94486c72d818cd04` |
| Isla runner | `45c1a4b1ee41154208053e711a5f39219dc3ae886cb8d9ff1342bafe83d6ca1f` |
| Isla runner源码 | `5d07dcebec07efe1ce043756f037852a6b7b64978f102f44b962e6618ed54594` |
| `historical-full-seeds/seed-manifest.json` | `55f762c57e19f145eabbd5974ec587db2eb800dda50fe84ff0d287c4a26be644` |
| `historical-full-paired/summary.json` | `4c5d1995b7ed5dedb543d59ee0d0824cb06c9b1cb1ebedfa08064fcf3bcabcb5` |

独立证据：

- [静态、初始化及seed审计](../../.tmp/unified-backend-cpp-replay-independent-audit/p1-static-audit.json)，SHA-256 `73168c3fc13dfa0b499ba7209336c7c36196af4d36f828390ccab772819f7b55`。
- [全量配对审计](../../.tmp/unified-backend-cpp-replay-independent-audit/p1-full-audit.json)，SHA-256 `7d84219ad371cc75718c1d30631254101471a8d7307c83b50e32451c4aad71ee`；绑定2,418个实际文件。

## 构建与schema

已逐hash核对C++清单的458个构建输入/产物、v7模型920个源码文件、schema producer的62项输入，以及初始化提取器使用的510个冻结Isla文件。C++生成头/源、模型静库、SoftFloat、Sail runtime、GMP、实际CMake include/宏及编译器依赖头均绑定。C++仍使用`THREAD_LOCAL=thread_local`及`SOFTFLOAT_FAST_INT64`等实际模型宏。

v7仅补齐此前快照漏掉的SoftFloat平台源码；核对`cpp-source-v7-bind.json`、v6 IR生成记录与v7源码清单，Sail模型来源关系一致。此次没有以文件名或版本前缀替代内容哈希。

`schema-r02`从实际新IR和冻结`FD_NONMEM_RV64`导出77个constructor加`ILLEGAL`，再与实际C++头对齐。102个witness字段及15个辅助字段全部存在；tuple按真实IR顺序对应`ztupN`，enum按成员身份生成switch，全payload递归受无资源类型门槛约束。C++ AST visitor读取实际译码字段，未从expected AST构造执行输入。

## 初始化与译码不变性

已核源码顺序为：加载`effective-replay-config.json` → `sail_config_set_string` → 每case新建Model并`model_init` → 八let回读 → TOML固定defaults → 完整102项witness → 102项回读 → 实际`ext_decode` → 实际`execute`。没有通过CSR/FPR/VPR写接口装配witness，也没有随后reset/boot。

有效JSON保留原文件，八项覆盖中仅三项改变：misaligned access `true→false`、instructions per tick `2→10`、PMP count `16→0`。独立重建这些字段后与有效JSON完整比较，未发现其它字段改变；`pmp.usable_count`等未被连带改写。有效JSON SHA-256为`dd6f75c19dcb6145426188133bb98cfbbed0145c489617916d88458eeb539adc`。

已核新IR上的真实`initialize_architecture`提取及producer命令、二进制、源码和配置哈希：

- mseccfg/menvcfg/senvcfg：64位具体零，提取SHA-256 `1920a420d1b707a0e8c078891c6f463c1cf52fd8feecf8a8b57d882306a7839f`。
- hstateen0–3、mstateen0–3：64位具体零；sstateen0–3：32位具体零，提取SHA-256 `92b0f951d22b2474c1fdaad63c67daa682b23be1499f35969dff75c11e091d75`。

C++没有给这些隐藏字段填入猜测值；全18,584条实际回读均与提取值及位宽相符。所有case的八let也均实际回读一致。绑定runner在decoder后检查102项、所有固定环境字段、八let及全部15个辅助字段不变；执行结果中没有decoder写回调。

初始化闭包采用架构独审的[限定证书](../../isla/target/float-solve-evidence/unified-backend-configuration-review/348147-20260927/initialization-review.json)，SHA-256 `e8ee1f7eccf2ca0209a7b3241712ecc448270ab419ada479e8fd5e25db42bbbf`，并逐hash复核其输入与本次实际产物绑定。其四个Isla表示flag及x0地址引用条件继续有效；不将这些条件简化为全局“没有物理x0读取”。

## 全量输入与输出

19个分片的每条新seed都回查原始数组索引、源文件哈希、原case规范哈希和原ID；除新run-id、来源元数据及由原AST重算的规范串外，指令与前后状态语义字段完全相同。原始四个输入文件中的18,584条记录恰好各出现一次，跨片无重复或缺失。

全量逐条复核包括：

1. Isla、C++和提交输入的三元ID集合一致；C++原始JSONL与协调器结果去除比较注记后完全一致。
2. 两后端所有可行path的完整decoded AST、完整ret及102项post逐字段相符，保留VPR全部128位、FPR boxing位和未改写状态。
3. 各片绑定同版decoder纯读证书：253个函数、578个调用，global/indirect writes与unclassified callees均为0；证书绑定IR、配置、runner和源码哈希。
4. 已核绑定Isla runner的证明路径：拒绝采样、执行错误和非SAT终态；对每个可行path，将完整返回及观察寄存器相对模型物化值的差异断言求解为UNSAT，才返回通过。独审再比较所有返回path，未复用1dcc的观察唯一性结论。
5. 每片两端进程均退出0；最终`input-drift=[]`。没有通过抽样或忽略失败case取得全量结论。

配对总墙钟为201.601秒。实际编排是四个顺序执行“Isla→C++”的配对worker，各片C++内部`jobs=1`；工具未单独限制最多两个C++进程，因此不以“4 Rust+2 C++固定并发”描述该测量。此时间包括分片启动与核验，不作为隔离后端速度比。

## 控制与适用版本

新`cpp-r03`的16项smoke（3正、13负）逐条核读通过，覆盖post fcsr/mstatus/FPR/VPR高位、AST、word、ret、错误位宽、缺/多字段、enum、溢出及A→B→A隔离。其二进制和init均绑定本次r03。

五种实际故障注入日志亦逐hash核读：初始化let改变、decoder架构状态写、decoder隐藏CSR写、禁用callback和Sail异常均被拒绝；Sail异常首条结果先落盘、worker退出2，后续ID明确记为missing。它们使用新P1的`cpp-r02`控制构建；与r03的runner源码差异仅为追加12个stateen观测字段，不能把这五组日志写成r03重新执行。新增15辅助状态观测和r03全量执行已单独在上文核验。

Isla纯读白名单的`strict_and_bool`补充TDD曾遇到共享Cargo target与保留旧mtime导致复用绿色缓存；`rust-tdd-reconfirmation`这次无效补跑保留并明确排除。已独核修订后的`rust-tdd-reconfirmation-r02`：两次日志均实际重新编译主crate，红例退出101、11/12，仅未审`strict_and_bool`测试失败；绿例退出0、12/12，源码哈希精确等于正式冻结的`5d07dceb…`。见[补充审计](../../.tmp/unified-backend-cpp-replay-independent-audit/p1-tdd-supplement.json)。正式18,584条运行始终使用冻结的`45c1a4b1…`二进制，19份实际decoder证书亦同时绑定该二进制和`5d07dceb…`源码；补跑缓存失误未进入全量结果证据链。

本轮未发现阻止上述限定签收的新缺陷。模型、IR、配置、schema、runner或初始化合同变化后须重新绑定并复验。

## 56cc69

### 新版本限定签收

2026-09-27新运行独审结论：**PASS_SCOPED_HISTORICAL_FULL_SEED_REPLAY**。已对新IR `56cc69`、新C++ `cpp-r01`和新编译Isla runner重新逐hash、逐case核验，没有迁记348147的PASS。

19片全部18,584个提交ID在两后端各返回一次：18,477条gen、83条直接decoder负例、24条派生负例。两后端各18,584条可行执行结果，decode/execute Dead均为0；完整decoded AST、ret、102项post、每条八let及15项辅助初始化回读全部一致。C++原始JSONL与最终结果去除比较注记后完全一致。

范围仍为历史完成的50个clause的全部seed；`whole77-complete`、`source-branch-closed`及`new-official-solve-output`均为false。没有将另27个历史超时目标计为通过。新配对运行墙钟204.427秒，四个配对worker；`input-drift=[]`。

### 来源与初始化桥接

新运行根为`isla/target/float-solve-evidence/unified-backend-cpp-replay/v4-amo-56cc69-20260927/`。独审重新核对458项C++构建输入/产物、931个实际模型源码文件、166个候选重新打包的模型文件、schema producer的62项输入，以及候选与提取器冻结runtime各510个实际源码文件。候选模型逐文件对应同一次C++/IR模型构建；Sail实际生成argv亦与`model-build.json`一致。

初始化提取报告引用旧generation SHA `338dc3bacfb7d0600bad8fd33de48eb3ae468d69c663518576c9dd12dd8a5e4a`，其完整字节保存在`p1-initialization-56cc69/generation-preliminary.snapshot.json`。当前generation SHA为`9f01067ea8f2da31b37f5089e4c5870e47e8299f7622b9a456585a0648176a77`。独立比较确认**唯一变化键**为`isla_runtime_source_manifest_sha256`：`1890f0a1…`改为提取器实际绑定的`28fb65ee…`；IR、模型、配置、生成命令及其它字段均未变。

桥接同时核验了候选manifest `fdf105d1…`与提取器`28fb65ee…`中的510项runtime记录完全相同，并分别对两份实际源码重新算hash。保留原提取报告及旧generation，未把旧摘要当成当前文件摘要，也未以忽略不符项放行。新15辅助值来自实际输入新IR的初始化提取，SHA-256 `6ff5d6a2a3bee01cb339ae83536aae837fa17dc922b456f88af9fa1dbeb9c1b1`；未迁用348147的状态结果。

有效JSON在`model_init`前加载，仍仅改变misaligned access、tick和PMP count三个已列字段；八let与15辅助字段的初始化及decoder后不变检查均存在于新绑定runner。新初始化限定证书SHA-256 `11c869ff50389dc6a1fecc92d88a7c7ce766da04817ebb1e01c323e22bd43576`的全部文件与条件已核，包括四个Isla表示flag及x0残余观察唯一性义务。

### 新结果与控制

全部seed重新回查原数组、索引、原ID与语义字段，确认无遗漏、重复或语义改写。19份新decoder纯读证书均绑定新IR与新runner：257个函数、582个调用，零global/indirect writes及未分类callee。每条Isla结果仍须通过绑定源码中的完整观察差异UNSAT检查；所有实际返回path又由独审逐字段核对。

本轮16项smoke及五项故障控制均在新56cc构建上实际执行并通过预期。五控制全部包含15辅助状态观测，分别检出初始化let改变、decoder架构写、decoder辅助写、禁止callback及Sail异常；异常先保留当前失败，再明确记录后续missing ID。新候选Rust构建的12项单测通过。此处没有使用旧版控制执行日志替代新版本测试。

### 新冻结摘要与独审证据

| 对象 | SHA-256 |
| --- | --- |
| 新IR | `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac` |
| 新C++构建清单 | `adacaf2ebba713e4f732f7c11ed0a3d100edcd7c572464044a23bab382cb0f56` |
| 新C++初始化合同 | `1e470ecfa56f6e11e512d63cce7e5b0012a664b358f28188eb83b4b82b8f0618` |
| 新C++ runner | `58b1db06aa700d802e8ccb9c8a749a221ffc00e1d7d936502268a14ae6b16a72` |
| 新Isla runner | `1e2efa76188820deca0ac2a46b3ed607005133fa6a995b992da6e5502cc63e6c` |
| 新seed清单 | `55292574fd200fb77aa085d7550f5694c1eb0a84d39cf3e6116d0ee5ffe6b52f` |
| 新全量配对summary | `cad2f88a2114c8e7131d6cd9c0014650b4683b7f31744546e745d69f763e7b0a` |
| 新最终589文件索引 | `9dedd8419c727d668a7c7e5f4a1eb9022f72fccc842866699e15000c426fdae6` |
| 新delivery summary | `a1c4fc6afd08c746fb8d7d14850b371f24f5e6d9053572736047d13461c45bad` |

实际独审命令均退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-audit-56cc69/audit_static.py
python3 .tmp/unified-backend-cpp-replay-independent-audit-56cc69/audit_full.py
```

[新静态审计](../../.tmp/unified-backend-cpp-replay-independent-audit-56cc69/static-audit.json) SHA-256 `d2643633ecb83ccf7ef24102808bec53a459cf189e9438e8efb86cd0faa33317`；[新全量审计](../../.tmp/unified-backend-cpp-replay-independent-audit-56cc69/full-audit.json) SHA-256 `0f2e324e4bbfca061b2a4ec9611ff2f8ce438e2454bc09fb16390fd425f9d177`。新全量审计绑定3,224个实际文件，包含最终589项交付索引的逐项验证。独审重新验证既有真实执行产物，未另外重跑18,584次模型执行。

## 官方F_MADD_TYPE_D

### 新官方输出限定签收

2026-09-27独审结论：**PASS_SCOPED_NEW_OFFICIAL_F_MADD_TYPE_D_FULL_OUTPUT_REPLAY**。输入来自`representatives-56cc-20260927-061428`在IR `56cc69`上的新官方实际求解输出，唯一clause为`zF_MADD_TYPE_D`。1,096个完整终态包括840个retire、252个illegal及4个non-encodable；全部1,092条gen和四个译码负例均进入两后端配对，无缺失、重复、采样或suppressed输入。

两后端各1,096条可行执行结果的完整decoded AST、ret及102项post逐条一致；Isla decode/execute Dead均为0。全部C++结果的八let和15项辅助初始值实际回读一致，两个worker的原始JSONL与最终结果逐条对应。四项sstateen保持32位，其余11项辅助寄存器为64位。

本次`new-official-solve-output=true`；`whole77-complete=false`、`source-branch-closed=false`。同批`FVVMATYPE`不在本签收中，也不把历史18,584个seed的回归结果合计为新官方完成数。独审复核已完成的真实双后端产物，本轮仅重新运行来源/trace审计与标准汇编，没有另启模型重放。

### 来源、trace及负例

求解根为`isla/target/float-solve-evidence/representatives-56cc-20260927-061428/`，配对根为`isla/target/float-solve-evidence/unified-backend-cpp-replay/official-fmadd-d-56cc69-20260927/`。已重新核验28项配对索引及外部绑定、515个官方runtime/source文件、163个官方模型文件、458项C++构建文件及初始化独审证书的1,512项文件。新官方IR/FD配置、候选generation、实际求解二进制、冻结输入、初始化证书和新56cc两端runner均按内容hash相连。

实际CLI保持outer/solve/SMT预算300/270/30秒、两线程、`--probe-all --trace-all`及完整encode-decode-execute入口，D目标无workaround参数；目标make/isarch退出码均为0。独审重新遍历完整trace的25,676个catalog条目、1,096个终态块及3,418,976条边；日志的每个case-id、status、phase和signature均与JSON逐条一致。全部1,092条汇编文本重新通过LLVM编码回原word，未使用reviewed-illegal例外。

四个non-encodable终态没有直接产出编码字。负例按完整requested AST在同批gen中找到对应项，借用其实际物理word和汇编，保留原non-encodable终态的完整102项pre；期望post等于该pre。没有借用关联gen的状态，也没有另调encoder生成word。两端随后真实译码为`ILLEGAL`并返回`Illegal_Instruction(())`：

| 原non-encodable case-id | 关联gen case-id | 实际word | 汇编 |
| --- | --- | --- | --- |
| 5 | 105 | `32'h0200_1043` | `fmadd.d f0, f0, f0, f0, rtz` |
| 6 | 107 | `32'h0200_104f` | `fnmadd.d f0, f0, f0, f0, rtz` |
| 46 | 309 | `32'h0200_1047` | `fmsub.d f0, f0, f0, f0, rtz` |
| 48 | 337 | `32'h0200_104b` | `fnmsub.d f0, f0, f0, f0, rtz` |

四项guard来源均为`extensions/FD/dext_insts.sail 249:24 - 249:69`。gen与四负例的ID并集恰好覆盖全部原终态，负例gap为空。

### 初始化及观察证明边界

采用上节已审的新56cc provider，并重新核对其实际文件与本批输入/输出。当前批decoder纯读证书绑定同一新IR、FD配置、实际Rust runner及源码，257个函数、582个调用，零global/indirect writes及未分类callee。绑定源码逐路径拒绝采样、执行错误、非SAT终态及未导出的PC/x0读取；完整return和102项观察post相对物化值的差异须求解为UNSAT。独审又逐条比较了本批全部实际path。

C++独立summary仍将`input_audit_complete`、`initialization_compatible`、`aux_observation_evidence`及`cpp_replay_complete`保留为false；这些是该独立工具未自行建立的义务。此处双后端限定签收分别由重新执行的输入来源审计、新版初始化独审证书及本批Isla逐路径观察证明补足，未改写C++原始summary，也未把辅助初值回读当成观察唯一性证明。

实际Isla运行29.914秒，C++两个worker共1.279秒；两者均退出0。这些时间保留其原工具统计范围，不作为隔离后端性能比。

### 冻结证据

| 对象 | SHA-256 |
| --- | --- |
| 官方D replay manifest | `003666710974d5409a81b5645b77acde736d41ee9957702384ae060285e00867` |
| 官方D freeze | `5d9e99b40ef060b0cfdac555a3015fdb568b67d17b80e1da6b8ae11a2b580ad2` |
| 官方D输出JSON | `4d8d8341928f69dfa8da88b32a8a8a5bd53902481352d39b04e084f537fc3fa3` |
| 官方D完整trace | `e1ed8691bfc32bbc232e0c164181c3522bcb2f2d5ee1c43e4ef5db2ef5ed43ef` |
| 本批全部输入 | `5fbea950c76bbce5deceb01598536670ee27eaad77deccdf4840c5085f076bf5` |
| 本批Isla结果 | `5f4301fc20f2e6890b3cdbe91edfa2d1adcdad8efdc653db740d2408353d417a` |
| 本批C++结果 | `b85d6bc1fa92a3312f859514e912f6e69c9e649c4736332ca44636ebd7e35e25` |
| 本批paired summary | `ee922578640d7f0d256a5a8165afa61a2f038757f2da0817ca14e8385d9ddb3f` |
| 本批28文件索引 | `009674368a7c1abcf1841a06a05abd715baaf7c408908f95f6f14aea9064d243` |
| 独审脚本 | `470f13f1051a6df04869e46efc33e74db58fb63095fbb3114ec2db7bc3decc10` |
| 独审结果 | `db60facd2f98aa8b72cd6f9ba4cb7a55c977e070db21f99f8202d0046fb866b6` |

实际独审命令退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-official-fmadd-d-56cc69/audit.py
```

[独审JSON](../../.tmp/unified-backend-cpp-replay-independent-official-fmadd-d-56cc69/audit.json)绑定2,245个实际文件。审计使用冻结`solve_replay/audit.py`；因归档目录改变其相对模块路径，仅显式提供逐hash绑定的原汇编检查模块，输入/trace/重汇编检查逻辑保持原样。LLVM实际二进制及版本亦在独审JSON中绑定。

后续77项按自然完成且来源冻结的wave逐批签收；受信号中断而未完成的目标不进入完成集合。新wave须单独提供实际solve输出及配对结果，不能复用本代表或历史seed的PASS代替。

## 官方长批wave001

### 首轮来源及观察审计

2026-09-27首轮独审结论为**PASS_FULL_INPUTS_AND_OBSERVATIONS_ONLY_SEMANTIC_GATE_PENDING_EXCEPTION_LETS**。当时受报告开头异常隐式let勘误约束，仅签来源和观察；随后正常返回域补证见文末。原owner的配对summary及其PASS字段按原样保留；本轮待补证JSON也保留，不覆盖为后来结论。

求解目录`isla/target/float-solve-evidence/official-56cc-long-20260927-064348/`中的首wave恰好覆盖26个自然完成目标。已与`stopped-batch-audit.json`核对：6个失败、8个人为中断、37个未启动目标均不在输入集合。批次整体make退出-9，不能以26个目标的局部退出0代替全批完成。自然目标保持1800/1740/30秒预算、两线程、完整ITRACE及真实encode-decode-execute入口。

本wave全部6,195条gen（5,457个Retire、738个Illegal）加22个直接译码负例和13个真实encoder补齐的负例，共6,230条。输入三元ID与全部原终态一一对应；两端各6,230条实际可行结果，无decode/execute Dead，完整AST、ret、102项post逐条一致。C++每条八let、15aux及原始单worker JSONL亦逐条通过。

独审重新遍历26目标完整trace：每目标25,676个catalog条目，总计6,230个终态块、32,912,166条边；日志与JSON的case-id/status/phase/signature逐条一致。全部6,195条gen实际通过LLVM重汇编回原word，无reviewed-illegal例外、采样或suppressed条目。

### 13个真实encoder补齐负例

原`input/`如实保留13个缺word项及`input-queue-complete=false`，`input-complete/`另存完整结果。逐项核验原non-encodable终态的requested AST、结构化payload、mapping-source及102项pre；encoder输入的辅助context完整来自同clause实际Retire gen。13条输入在同版实际`zencdec_forwards`中各得唯一32位word，再于辅助context真实译码回原完整AST，均退出0、无Dead。所用辅助runner源`14043ff9…`由主replay源`5d07dceb…`派生，依赖库、Cargo和实际源码hash均逐项相同。

最终13个负例用编码器返回word，但完整pre/post恢复为原non-encodable终态的pre；全部13项都与辅助context不同。随后两后端实际译码为`ILLEGAL`并执行出`Illegal_Instruction(())`，原状态保持不变。完整对应表含clause、原case-id、辅助gen case-id、word和mapping-source，保存在独审JSON的`encoder-input-links`。

辅助decoder/encoder证书分别列257/582和164/204个函数/调用；本轮只签其版本和结构元数据已核，异常隐式let漏检如报告开头所列。不能用这些旧纯读证书替代尚缺的正常返回域证明。

### 薄工具与证据

已读冻结`prepare_official.py`、`complete_official.py`及`pair_official.py`：前者要求自然退出和完整来源/trace/汇编审计，缺word退出2并保留缺口；补齐器要求缺口精确覆盖、原payload/pre不变及同版encoder；配对器要求输入完整、来源hash未漂移、后端退出0、完整ID/观察比较，任何失败或最终漂移均不得给配对PASS。原prepare/complete/pair的5/5、5/5、6/6测试证据已核，并在独占临时目录重新执行冻结版本，合计16/16通过，覆盖遗漏输入、状态改写、未闭合缺口、后端IR错配、文件漂移及encoder AST/辅助context错误拒绝。

配对根为`isla/target/float-solve-evidence/unified-backend-cpp-replay/official-long-wave001-56cc69-20260927/`。实际顺序为一个Isla worker后一个C++ worker；Isla187.595秒，C++协调器18.943秒，其中worker14.011秒。独审未重跑模型。

| 对象 | SHA-256 |
| --- | --- |
| 官方wave manifest | `0bb5cd9fefed7ef4cafda627e8f15a5c0212fea9fcf4db337a9bc3514a1d3e65` |
| 补齐输入manifest | `bcf0a83fdc7597968620796929dc3f15003c0c630ad31756e2e717c60f00d532` |
| 补齐全部6,230输入 | `141e87c2f7d150ca13d9eca7e1bac536fec03eeecd88346854058e4a249a53b5` |
| Isla全部结果 | `b5a416e351f99be62fbc3e6e55b2d51557c66cefcb4dd39c3527b91ea173ecfe` |
| C++全部结果 | `a86989ecae81ee04feb4d874dc0c6f5bf33adf10ebae5c91cbb3661306201c13` |
| 原paired summary | `154efe1476cba7bb4390f9e701f998be8e69c64bc45c4dce30cfccf894dd372b` |
| 外层52文件索引 | `84e3cef943c85715ce1f0e62879c867edf3279370c6adedfc579f3e8dc39b6c9` |
| 独立全量来源及观察审计 | `aeb21c0b09d5017462d7195d0b66a21cb73df16c27180a19d4d4b647bb3c612f` |
| 冻结工具16测试独立复跑 | `125697c40ba3e61c86acfc508d3fc905a046717cc39e07b2d14dfd30cd6c6266` |

实际独审命令退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/audit.py
```

[全量独审JSON](../../.tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/audit.json)绑定2,393个实际文件；[测试复跑记录](../../.tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/tests-reconfirmation.json)另绑冻结测试源码、命令及日志。`new-official-solve-output=true`，`whole77-complete=false`、`source-branch-closed=false`；异常正常返回域的补证单独追加，不能静默把本轮待补证状态改成完整PASS。

## 正常返回域补证及最终限定签收

最终修订为**PASS_SCOPED_NORMAL_RETURN_REPLAY_WITH_FULL_CLOSURE_PURITY_FAIL**。适用范围是已经核验成功的348147历史18,584条、56cc历史18,584条、新官方D代表1,096条和首wave 6,230条，以及本wave 13个辅助编码输入。恢复的是这些具体输入在正常返回域上的两阶段重放签收；完整decoder/encoder闭包的零隐式let写结论仍为FAIL。

独立消费架构侧[补充证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/independent-phase-purity-review/certificate.json)，SHA-256 `7f60693560ae1733d76305313876378a3a76ef1725511f77d9e969f85241b648`，并重新执行两版IR、两个root的完整静态检查及异常状态固定点，与原报告所有对应字段完全一致。每个闭包仍有12条异常let写；从`have_exception=false`入口出发，四个固定点均在六轮收敛，根返回摘要恰为：

| 根返回方式 | have_exception | 是否曾写异常let |
| --- | --- | --- |
| `End` | false | false |
| `Arbitrary` | true | true |

这个证明保留一般条件的两条分支、跨所有调用保存“曾经写过”状态，并将子调用`Arbitrary`视为返回调用者继续执行，未把异常函数当作天然不返回。处理异常后清标志并正常`End`的负控会检出曾经写入；13项控制测试已独立复跑通过。

已逐hash确认该证明使用的executor、frame、init、IR和primop源码与两版实际冻结replay runtime一致。`LocalFrame::new`将异常标志初始化为false；架构`state.lets`从空集合开始，只收显式`Def::Let`，而精确IR没有这些隐式名称的显式定义、参数或局部shadow。因此入口值不会被随后`add_lets`覆盖。静态检查同时排除其它显式寄存器/let写、间接写、引用逃逸、不透明extern及未声明目标写。

在实际绑定runner中，根`Arbitrary`产生`Finished(Poison)`并被拒绝；越界完成得到的Unit也不能通过decoder的Ctor校验或encoder的32位Bits校验。错误、采样和非SAT路径均被拒绝。联立这些实际成功结果与新固定点，可得列定输入的decoder/encoder正常返回路径未写三个异常let，补足原两阶段丢弃这些状态的缺口。完整AST/ret/102post逐路径UNSAT及两后端实际比较继续沿用各自冻结产物，本轮没有重跑模型。

审计重新核验四套实际文件绑定，唯一变化项是工作区`agents/float_support_review/tools/solve_replay/runner/Cargo.toml.in`后来增加`itrace`feature，当前hash为`f8017bc1…`。两版实际冻结的Cargo文件、源码、依赖及二进制均未改变；从两份冻结Cargo分别把唯一库路径反替换为`@ISLA_LIB_PATH@`，得到相同字节，精确匹配原模板hash `640a6e4d…`。该[显式重建记录](../../.tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/template-reconstruction.json)及[漂移清单](../../.tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/historical-binding-drift.json)保留，不把当前模板冒充旧模板，也没有改动旧清单。

实际命令退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/consume_normal_return.py
```

[最终独立消费记录](../../.tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/normal-return-consumption.json) SHA-256 `4cbc8ca93539128681c8358055b20c29d43026ef2f0ebdfb5b9df65d0a54e521`，绑定6,401个实际文件；消费脚本SHA-256 `73b98cc27d125cc324a10cb7efd9cf4b140d438d03df642484d6d7755f950d50`。原待补证审计与[漏检影响清单](../../.tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/exception-scope-audit.json)均保留。

该修订不签异常路径不变、所有输入终止、全77完成或源码分支闭合。全闭包失败事实、原工具漏检和限定正常返回证明须同时保留；后续IR、runtime或runner变化后须重新绑定。

## 最终 observer 的实际分组重放独审

### 冻结运行时与共同绑定

新的实际运行位于`isla/target/float-solve-evidence/unified-backend-cpp-replay/exception-observer-56cc69-20260927/three-groups/`。按冻结计划以单worker、每片最多1,024条依次执行D代表1,096条、官方wave001 6,230条、历史18,584条；每片都实际调用Rust与C++。计划SHA-256 `4cdf3603f699e70fbb3775b5d0ed836650a933357f34bf316ad889e895957dbe`。独审只消费自然冻结的整组，不签正在运行的分片。

独立逐项核对旧候选runtime与observer各510个文件、5个符号链接。唯一文件差异是`isla-lib/src/executor/frame.rs`增加immutable `instruction_trace()` getter；从新文件删除这段getter后与旧文件逐字相同，已有ITRACE实现未变。冻结runtime清单SHA-256 `3c0636ae8708709481fc64ea0e5615b560408e74ae3bcdc6c5eae01d82b20676`；最终runner源码`30559da1e9d93a1615dd5ab94c9a068779cabd63887c18fc484870fa4f07f4a7`、二进制`07295152a84ddee88c698506762db3e71e6f3a5d56a27caef6f41ae5a05e5fb8`。最终构建的9项文件、49项Rust库源码及`itrace` feature均已绑定；C++458项构建文件和1,512项初始化审计依赖亦逐hash核对。

消费[独立接口审计](../../isla/target/float-solve-evidence/replay-scratch-observer-20260927/independent-review/interface-review.json)，SHA-256 `77af68b113d139da649e5d77d3efffcd189e1a0f6430fbd73d85f45cc51a4d17`。该审计绑定最终源码和二进制、20项独立复跑控制测试，以及variadic、special-call、frame实现审查。观察器从实际完整typed trace逐条取function/PC对应的opcode，检查全部目标写变体、Call返回目标、局部shadow、Addr/Ref逃逸和lazy读取，并将实际函数指针/Reset Arc约束到审过的实现。逐phase同时检查三异常槽typed初末状态；不会仅凭`have_exception=false`末值推断没有写后恢复。

[共同独审JSON](../../.tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/static-audit.json) SHA-256 `2ece8ac6d82d8ae33bc607890cf55cf21739ecbe5595c598298d3c986bb82012`，绑定2,100个实际文件；[独审脚本](../../.tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/audit.py) SHA-256 `2233ddb95c2e0a0bfab7f28148cbeef776738c220095c19a3c7a3c43bb09ec35`。实际命令退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/audit.py static
```

### D 代表1,096条

独审结论为**PASS_SCOPED_ACTUAL_OBSERVER_REPLAY_WITH_FULL_CLOSURE_PURITY_FAIL**。分片1,024+72条，全部原输入三元ID恰好覆盖且原顺序不变；两端各1,096条，decoder与execute共2,192个实际phase，累计19,715,227条指令观测，沿途scratch写为0。每个phase的三个异常槽初末精确相等：`current_exception`为未初始化Union、`have_exception`为`Bool(false)`、`throw_location`为未初始化String，均正常`Finished`。

独审直接规范化并比较新旧Rust每个ID的完整AST、ret、102项post观察多重集，全部一致，decode/execute及Dead计数也一致；两端完整观察分别与原输入逐项相符。C++全部八let和15aux逐条核验，四个`sstateen`保持32位；真实worker JSONL去掉协调器新增比较字段后与最终结果完全一致。核对每片真实命令、退出码、来源输入、报告和全部文件hash，组索引41文件完整覆盖。

| 对象 | SHA-256 |
| --- | --- |
| D组summary | `5f88418e2137877208eb6e26251e5ddddbc69f6eb33ab8391a12ff56dbf769d6` |
| D组41文件索引 | `ac48d2c13643031c6d24927b27963a5da5eacd2bbbddfb5dd21e4bbf4f6c7258` |
| 最终v2阶段证书 | `7d2d0886df16b76d272c810ca7e3436d8797abec62934c1f63d53fb6f7940e7a` |
| D组独审JSON | `ad6e1d8cd1c9fac10d3d50260ba22a409931b8e67956252c42788fe04b8dd447` |

实际命令退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/audit.py official-d-1096 5f88418e2137877208eb6e26251e5ddddbc69f6eb33ab8391a12ff56dbf769d6 ac48d2c13643031c6d24927b27963a5da5eacd2bbbddfb5dd21e4bbf4f6c7258
```

[D组独审JSON](../../.tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/official-d-1096-audit.json)绑定2,143个实际文件。本轮没有独立重跑模型，也没有从磁盘重建逐指令hash：磁盘保存的是已绑定观察器在内存遍历完整typed trace后输出的计数/hash和typed状态，独审通过冻结实现、独立接口审计及实际结果绑定消费。两片v2证书均显式保留完整闭包12个异常scratch写站点及`full-global-write-free=false`；旧正常返回域静态补证继续保留，`whole77-complete`、`source-branch-closed`、`full-closure-pure`均为false。后两组须各自冻结后追加独审结论。

### 调度交接：四worker分区核验

上述单worker计划是初始执行合同。D全组及原wave第0、1片各1,024条自然完成后，后续调度改为四个独立worker，每worker内部C++仍为一进程；模型、输入全集及每片最多1,024条的边界不变。新`parallel-transition-4workers/guarded-plan-index.json` SHA-256 `509fc4fb0cf88f4273b7fa84177550e36ea0c7becc56130bf9a5ef389602dfd9`明确引用原计划。不能把原协调器全组未完成当作原始输入集合缩小，也不能将四worker各自子集summary冒充完整组结论。

已独立复算四份guarded plan与实际run-contract的分区：原wave已完成2,048条；其余wave4,182条加历史18,584条，共22,766条分配为6,230、6,144、5,272、5,120条。24个剩余原分片的输入及旧结果逐条等于原计划选片，分片边界完整保留；所有分区互斥，连同D1,096条合计25,910个全局三元ID唯一且无遗漏。内存guard仅在启动下一子进程前检查`MemAvailable>=32GiB`，然后以原command/options调用进程，不修改输入内容。

此时结论仅为**PASS_PARTITION_BINDINGS_ONLY_RESULTS_PENDING**；原协调器outer exit的交接记录及剩余实际结果尚待各自冻结。原预置`shard-002`目录目前只有`handoff-stop.json`，没有模型结果，不计入已完成集合。

```sh
python3 .tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/transition_audit.py
```

命令退出0。[交接分区独审](../../.tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/transition-partition-audit.json) SHA-256 `9a260af7dd97a29c7789519f1eb51d6633580d9c1d44b783f79a27e329674ee5`，绑定2,174个实际文件；脚本SHA-256 `16897fa51d0ee7d120c7f4cd0200a9b2e156313f5d89f46ba7c2733dda258426`。这份分区记录按当时状态保留，后续实际执行签收另行追加。

### 官方wave001全部6,230条

聚合冻结入口为`exception-observer-56cc69-20260927/merged-groups/official-wave001-6230/`，其中每片保存原group/shard、实际source-directory、source-report及hash和原报告。独审从原完整输入重建7片，逐项映射原协调器两片和四worker五片；每个实际worker的run-contract与冻结工具也重新逐hash核验，没有改写实际命令路径来伪造单协调器运行。

结论为**PASS_SCOPED_ACTUAL_OBSERVER_REPLAY_WITH_FULL_CLOSURE_PURITY_FAIL**：两端各6,230条完整ID，12,460个decode/execute phase，累计212,000,423条指令观测，三个异常槽初末精确typed相等、沿途写0。新旧Rust完整AST/ret/102post观察多重集及路径计数直接一致；C++原始worker JSONL与最终结果一致，每条八let和15aux完整核对。7片实际command/exit/log及报告文件全部覆盖，聚合索引2,280文件核验通过。

| 对象 | SHA-256 |
| --- | --- |
| wave聚合summary | `d1ff428c1bafc678b3b421fb9a96435a87581b3ad2b8a56931bfc7db31c213e4` |
| wave聚合文件索引 | `1e74299b606594827997a1f6e8385b9d63723589e0313f149ef2c87f6f6f55ff` |
| 并行分组独审脚本 | `2210f54cdc7b32bf0ccc8c9dec15b74ab46312793f3c6d0d63ef634838fa2484` |
| wave完整独审JSON | `89a2b939e8c0cf679f8effecf7d72dd861b3ae042eb7529bd2e00964d7b862b8` |

实际命令退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/audit_parallel.py official-wave001-6230 d1ff428c1bafc678b3b421fb9a96435a87581b3ad2b8a56931bfc7db31c213e4 1e74299b606594827997a1f6e8385b9d63723589e0313f149ef2c87f6f6f55ff
```

[wave完整独审JSON](../../.tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/official-wave001-6230-audit.json)绑定2,298个实际文件。独审新建并行消费脚本，原D审计脚本与结果保持冻结；共同运行时及观察器接口审查沿用前节精确绑定。所有分片均使用同一v2阶段证书`7d2d0886…`，完整闭包12个异常槽写站点与FAIL结论保留。此处新增的是既有官方输入的observer实际重放证据，不增加官方solve目标数，也不扩为全77完成。

调度证据限制：owner报告原协调器exec session 61017在预置下一片目录后退出1，但未保存原outer stdout/stderr及退出记录到磁盘。独审不把后写说明当作原始日志，也不宣称已独立验证该outer退出码。能够独立核验的是交接sentinel、原两片模型的真实退出0和完整产物，以及随后所有原输入ID的实际结果；这些证据足以支持本节限定的全输入回放验收。

### 历史18,584条及三组最终收口

历史组冻结入口为`exception-observer-56cc69-20260927/merged-groups/historical-18584/`。独审按原19片逐条核验18,584个三元ID、输入来源、实际命令和两端完整AST/ret/102post；37,168个phase累计547,638,980条指令观测，三异常槽初末typed精确相同，沿途写0。新旧Rust完整观察多重集及路径计数直接一致；C++原始JSONL、完整提交输入、八let和15aux均逐条通过。

首轮历史独审在提交输入检查处拒绝：wave审计脚本假设`expected-decoded-normalized`仅由C++协调器新增，而历史原输入本来已包含该字段。检查只从submitted删除该字段后比较原输入，导致审计自身断言不成立，未发现模型结果失败。保留[首轮说明](../../.tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/historical-attempt1.json)及失败日志，另建历史专用脚本，要求完整`submitted == 原partition`，同时继续逐条重算规范AST。原D/wave脚本与已签产物保持冻结。

| 对象 | SHA-256 |
| --- | --- |
| 历史聚合summary | `da1b28dcd414f6e76ce45c2a307c619f8397d7e95334042c02b3103cb3db3ddb` |
| 历史聚合文件索引 | `0b204acfb11484a152ed295f8e17c22632038378c19974a6b470fd87cc635771` |
| 历史独审脚本 | `844fde0974953b53897c344f6f3d35c8b453a9a5bf4f1ad3105b3e783a351965` |
| 历史完整独审JSON | `23ff694a9d24eb7f2779f6ddd32da61b5feef557f11d1bbb00bff8818861bdeb` |

实际历史独审命令退出0，[结果](../../.tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/historical-18584-audit.json)绑定2,578个实际文件：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/audit_historical.py historical-18584 da1b28dcd414f6e76ce45c2a307c619f8397d7e95334042c02b3103cb3db3ddb 0b204acfb11484a152ed295f8e17c22632038378c19974a6b470fd87cc635771
```

最终消费`exception-observer-56cc69-20260927/three-groups-final/`的完整包，结论为**PASS_THREE_COMPLETE_GROUPS_ACTUAL_OBSERVER_REPLAY_WITH_FULL_CLOSURE_PURITY_FAIL**。

| 原分组 | 两端完整输入数 | decode/execute phase | 实际指令观测 | 沿途scratch写 |
| --- | ---: | ---: | ---: | ---: |
| 新官方D代表 | 1,096 | 2,192 | 19,715,227 | 0 |
| 官方wave001 | 6,230 | 12,460 | 212,000,423 | 0 |
| 同56cc历史回归 | 18,584 | 37,168 | 547,638,980 | 0 |
| 合计 | 25,910 | 51,820 | 779,354,630 | 0 |

最终独审重新核验总索引2,738个文件，逐条重算25,910份原完整case的canonical SHA并核对原组、原三元ID及真实source-report，确认全局唯一且精确覆盖。四worker的实际outer命令与launch记录一致，监督退出均为0，最终输入漂移均为空；48次实际后端启动按顺序逐一等于各片保存的Rust/C++命令，均通过32GiB内存门槛，没有等待记录。这里48次仅指四worker承接的24片，原已完成D两片与wave两片另有完整命令/退出证据。原协调器缺outer原日志的限制继续保留；后补交接说明SHA-256 `50119c7d6809fa638448ac01ceac234a6279a50a7e015ee2bdc4bd7ce515bd6c`已绑定，但不作为原始退出签证。

| 最终对象 | SHA-256 |
| --- | --- |
| owner三组总summary | `f180542532f3de133860f6e7bde6bc662020cbfd54d40ddbc1858e381c1c787c` |
| owner总证据索引 | `f2de4fc3298f5079486851620106eefb1ccb44732cad092c3f5dae6078b33a84` |
| 全25,910条case coverage | `406276a9a06b58b714eb9df8a9131b7b41e783036973f1ac7049f8b0f3b6fa09` |
| 最终独立消费脚本 | `40bba18d10c1ca92daefcca0703b88f9aac3d183013bb0800e33dd353791df50` |
| 最终独立消费结果 | `bb1a24598555e2fa7147e05943dea601211276d353567105b4171f0d58edb7fa` |

```sh
python3 .tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/final_audit.py
```

命令退出0。[最终独审JSON](../../.tmp/unified-backend-cpp-replay-independent-exception-observer-56cc69/final-audit.json)绑定2,761个文件。13个真实encoder辅助输入的observer证据另计，没有混入25,910条；后续同根lock等新observer变体也不在本签收范围。所有结论只适用于上述冻结版本与列定实际正常返回路径；旧正常End静态补证、完整闭包12个异常槽写站点及full closure FAIL同时保留，`whole77-complete=false`、`source-branch-closed=false`不变。

## sharedtrace 新官方23目标全输入最终独审

本轮独立消费`isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-incremental-56cc69-20260927/family-final/`冻结总包，结论为 **PASS_SCOPED_23_SHAREDTRACE_OFFICIAL_TARGETS_FULL_INPUT_AND_TWO_BACKEND_OBSERVATIONS**。这是新官方自然完成目标的实际证据，旧25,910条结论保持原版本边界，未迁为本轮PASS。逐包审计、来源补充桥及最终消费均位于`.tmp/unified-backend-cpp-replay-independent-sharedtrace-family-56cc69/`。

| 新官方组 | 完整原终态/双端输入 | gen | direct negative | derived negative | replay phase | 指令观测 | 沿途scratch写 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 首轮成功21目标 | 7,265 | 7,203 | 49 | 13 | 14,530 | 159,266,321 | 0 |
| VFNCVTBF16_F_F_W新目录重跑 | 1,119 | 1,116 | 3 | 0 | 2,238 | 47,365,113 | 0 |
| VFWCVTBF16_F_F_V新目录重跑 | 1,308 | 1,305 | 3 | 0 | 2,616 | 53,978,710 | 0 |
| 合计23目标 | 9,692 | 9,624 | 55 | 13 | 19,384 | 260,610,144 | 0 |

13个真实encoder辅助输入另计26个phase、186,986条指令观测，未并入9,692个原终态。逐包核对完整原payload/pre、合法gen辅助上下文、实际encoder返回word及完整decoder AST，并重建derived输入，确认原三元ID和原pre完整保留。

### 来源、完整trace与逐值复核

各实际solve stage的517份源码逐项等于受审sharedtrace stage，实际solve二进制均绑定provider `e669a22f65ac7324e861c9224531039b15d46d7befaf384032a15145ef21d175`。独立补充桥把该实际provider对接原受审`0c73a17e6cf289b0b0827b2526bdb862c781fd8ff9dcd2751fc298c8c1b7cce3`：两树517源码、全部252份fingerprint JSON集合与内容、workspace生成文件逐字相同，build output只允许stage绝对路径替换，实际解析到的native库亦相同。没有将原bridge `309dc98e…`冒充直接覆盖实际e669 provider。

独立重新调用冻结`2f0948bb…`输入审计器，遍历全部源solve trace的47,438,081条边，并逐条核对日志PATH_RESULT与原JSON的ID、状态、phase和signature。9,624条gen中9,233条独立LLVM重汇编通过；其余391条仍实际调用LLVM，诊断与经独立审查的精确非法操作数组合逐条一致。所有原终态均由gen/direct/derived全集精确覆盖，最终重新计算9,692份完整case的canonical SHA，核对family coverage及全局三元ID唯一性。

Rust与C++均对全部9,692个原ID核对完整AST、返回值和102项post状态。C++同时逐条核对八let、15项aux初始化，完整submitted输入、真实worker JSONL与最终结果一致；实际命令、退出码、工具快照和各层文件索引均绑定。公共适配器4项测试独立复跑通过，observer/encoder各20项构建测试记录与独立接口/身份审查一并消费；新encoder身份证书为`12b6356e46f292b335dcea674ddb90fe3122849bccdf9671d4f2fc96d0aa8cb4`。

### BF16重跑与保留失败

两BF16目标初次prepare因LLVM非法操作数诊断失败，原`results/<target>/`没有`paired/`，原consumer失败事件和`initial-consumer-passed=false`完整保留。独立guard证书只豁免391个精确组合：narrow 126条mask-v0；wide 265条，其中157条同base、108条mask诊断，18条同时命中两个guard。原word/text/AST/Illegal终态与冻结guard逐项一致，未匹配失败和多余豁免均为0，16项负控全部拒绝。

经该精确清单后，以新`results-retry/<target>/`从准备到双端模型完整重跑，两项真实退出均为0。重跑driver相对原版只新增必填`--reviewed-illegal`并传入prepare，最终独审逐字验证这一差异及retry plan/exits。

本独审器首轮BF16消费遗漏review文档的`records`包装解包，导致自己的断言失败；已保留首次源码、失败日志和说明，修复后完整重新遍历两包trace和2,421条gen汇编检查。此失败不代表模型失败，也未改owner数据。最终汇总脚本首次使用旧21证书的`packages`字段读取新23证书而触发KeyError；在首次签收前按新`package_reviews`结构适配，再次消费退出0，逐包已签文件未改。

### 逐phase证书与最终绑定

独立语义消费全23目标scratch证书，逐包重新匹配原三元ID、phase数量及decode/execute完整hash列表。19,384个replay phase和26个辅助encoder phase均正常返回；三个异常槽typed初末精确相同，沿途写0。完整闭包仍含12个异常scratch写站点，**full closure purity FAIL仍保留**。

| 冻结对象 | SHA-256 |
| --- | --- |
| owner family summary | `3f7971a726473d0f1378552a50150d87425190d9d6f2d33de19fb68b70f4eb48` |
| owner family索引（16,145文件） | `c7aae772e10c1f0cc9b0a44e6d8dc7cb926bdad881c4bd1a4eeb131a75af72a4` |
| provider独立补充桥 | `98dffa0966fdec224048d6db6459a2f70ce93a70feba1ebb5ecb558134f06eca` |
| BF391精确guard证书 | `25d0d16a88c8fae523fdff206bff83020c3e787c69aa87ad499081414d54215f` |
| family23 scratch证书 | `dc88188a2f5c7667520c5d2878769e3f73d81e5561c51725ab4ac4fd2d0177b2` |
| scratch绑定索引（20,447文件） | `71362e02e6e8e5a8a6d9406b983a2bb7bd104b4362af68cf2fe36491dc2f7aee` |
| 最终独立消费脚本 | `12f2fbe8371854df04b9b1d213c8270186dc4ee5946057cf0dc10aa6e58a98bf` |
| 最终独立消费结果（24,250文件） | `12a39845bf2e0ab8a2b1eca46255de4cacd595c4fb13efa054564f4537aec39d` |

实际最终命令退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-sharedtrace-family-56cc69/final_family_audit.py .tmp/unified-backend-cpp-replay-independent-sharedtrace-family-56cc69/phase-certificates.json
```

[最终独审JSON](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-family-56cc69/final-audit.json)联立全部23份逐值审计和独立phase证书；逐包原JSON中的待phase签收状态保持冻结，由本最终证补足。完整源solve trace已从磁盘独立遍历，observer原始opcode未另存，其指令计数/hash通过冻结实现、独立接口与逐phase审查及实际结果绑定消费，不能称为从磁盘独立重算observer opcode。`prior-25910-reused=false`、`whole77-complete=false`、`source-branch-closed=false`、`full-closure-pure=false`；结论仅适用所绑定版本和上述列定输入。

## sharedtrace continuation 七目标队列：前五逐包签收

第二队列使用`isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-continuation-56cc69-20260927/`新目录，复用精确相同的冻结后端plan `a210271c…`与driver `4cdc8d3e…`。独审位于`.tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-56cc69/`，逐值审计源码与前23轮逐字相同，另以`finish_target.py`联立每包完整观察与独立scratch证书；前23总证保持冻结。以下五包均实际自然完成及双后端退出0，逐包结论为 **PASS_SCOPED_CONTINUATION_TARGET_FULL_INPUT_AND_TWO_BACKEND_OBSERVATIONS**；此时后两包VFMERGE/VFMV尚待完成，未签七包总PASS。

| 目标 | 原终态/两端输入 | gen/direct/derived | 源solve完整trace边 | replay phase | replay指令观测 |
| --- | ---: | --- | ---: | ---: | ---: |
| F_MADD_TYPE_H | 8,740 | 8,736/0/4 | 30,737,376 | 17,480 | 190,312,725 |
| F_MADD_TYPE_S | 8,740 | 8,736/0/4 | 22,018,488 | 17,480 | 130,362,364 |
| F_BIN_RM_TYPE_H | 4,372 | 4,368/0/4 | 14,683,880 | 8,744 | 89,022,741 |
| F_BIN_RM_TYPE_S | 4,372 | 4,368/0/4 | 10,763,408 | 8,744 | 62,585,583 |
| F_BIN_RM_TYPE_D | 1,096 | 1,092/4/0 | 3,352,154 | 2,192 | 19,194,118 |
| 已签五包合计 | 27,320 | 27,300/4/16 | 81,555,306 | 54,640 | 491,477,531 |

27,300条gen全部独立LLVM重汇编通过，完整源trace和PATH_RESULT守恒重新检查。16个真实encoder辅助输入另计32个phase、225,020条指令观测，原pre、合法辅助上下文、实际word和完整decoded AST逐条复核。两端全ID、完整AST/ret/102post及C++八let/15aux/raw JSONL全部匹配；每包完整canonical输入hash亦重新计算。逐phase证书按每个原三元ID及decode/execute/encode完整hash列表消费，三个异常槽typed初末相等、沿途写0。

| 逐包最终独审文件（上述新独审目录内） | SHA-256 | 绑定文件数 |
| --- | --- | ---: |
| `F_MADD_TYPE_H-final-audit.json` | `89dfd2b4e91cf4e61297c4be00bb40112594cbafeccda0560523063736b192bf` | 8,302 |
| `F_MADD_TYPE_S-final-audit.json` | `e4f3e29571738ee127c4b6f9bdef1875e31c4068742e538ce58fd46b1c1fb358` | 8,302 |
| `F_BIN_RM_TYPE_H-final-audit.json` | `7d20c1c2852830aff93868ad8e8227eadfae8b5352dddc29d23a2659667ee00b` | 8,302 |
| `F_BIN_RM_TYPE_S-final-audit.json` | `e809dc7bae24b4c3106037e1e422351734998b145f37f6462fe0abad2e3d97c8` | 8,302 |
| `F_BIN_RM_TYPE_D-final-audit.json` | `35bf764394a91803206d645f322e0da14b87a2560de117d71aab64b8aece0ace` | 8,293 |

实际各包先运行`audit_family.py`与本目录`target-<目标>.json`冻结参数，日志为`<目标>-audit.log`；再运行`finish_target.py <目标> <独立phase证路径> <phase证SHA-256>`，日志为`<目标>-final-audit.log`，上述十次命令均退出0。每份最终JSON记录phase证精确路径/hash与源码hash，`finish_target.py` SHA-256为`1a66e2ea9c105ed7e9ba4b7af22662777482cf92f50178341a5a0e664faa81f6`。源码/实际provider补充桥、C++初始化和共用构建绑定全部重新核对；未改模型或owner工具。完整闭包12个异常写站点及FAIL、observer未另存opcode的证据限制、旧25,910不迁、全77及源码分支未闭合均继续保留。

等待后两包期间，以`snapshot_first_five.py`实际退出0冻结[前五汇总快照](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-56cc69/first-five-snapshot.json)，SHA-256 `12003f3210b713f4d03b3067157902c6b0aa56bcc798234ff1b07be1ac3f57d7`。该快照核对五份最终签收及coverage hash、27,320个全局原ID唯一性与上述总数，明确列出当时仍待完成的VFMERGE/VFMV；后两目标实际结果须另行追加，不回写此历史快照。

### VFMERGE实际外限及等待consumer交接

随后VFMERGE在`single-56cc-20260927-020959-06-vfmerge/`实际到达1800秒外限。独审核对原`single-run.json`、make日志与`stage/output/process/VFMERGE-124607.json`：make退出2，timeout子进程退出124，耗时1800.729秒，监督信号列表为空、未发SIGKILL、未触发资源停止。实际二进制e669、IR56cc和FD配置20851仍逐hash匹配；原目标没有完整`rv64_zVFMERGE.json`或replay manifest，未产生其双后端paired目录。

回放owner只终止等待COMPLETE且当时无子进程的旧consumer，冻结的handoff记录为退出143；前五条成功事件逐字hash保持，并与本独审五份最终签收逐项对应。交接记录SHA-256 `d227a74d624277ff7d4bf174bd525e57e252cd4d23a02b2e7ccae6facae8c634`。这里对SIGTERM及无子进程状态的结论来自owner保存的监督记录，不冒称由本独审agent亲自发信号或waitpid。该退出不是前五包任一模型回放失败。

```sh
python3 .tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-56cc69/vfmerge_timeout_audit.py
```

命令退出0。[失败及交接独立消费记录](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-56cc69/vfmerge-timeout-audit.json) SHA-256 `78332c86d2f54d366b90eb8906bd51c1a717691f428394028ec8fc5a869c79cc`，绑定24份实际文件。未完成的trace大小为38,647,799,897字节，本记录只保存路径和大小，不签内容hash或完整trace验收。独审初稿尝试对该未完成trace计算hash，随后仅终止自身审计进程并保留原稿及原因，再以实际退出/缺完整JSON证据完成本失败核验；没有修改源trace或模型进程。

因此原七目标队列不能签全部PASS，七包总消费脚本未运行，前五限定PASS及旧23总证保留。VFMV当时已在源队列继续运行，若后续自然完成，需要新监督目录和独立完整回放签收；不把前五或未来六包改称原七目标全部通过。

### VFMV独立续包最终签收

VFMV随后自然完成，完整source manifest SHA-256为`db6f11c18f8ff7cf385b7d22cbb3a7cc1a25835ee479edf42e6a55fc0a00681a`。owner在`isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-continuation-vfmv-56cc69-20260927/`建立仅含VFMV的新监督队列，等待自然完成终态及COMPLETE manifest后实际启动回放；source、consumer及两后端退出记录均为0，原七目标未全通过的标记明确保留。

独审使用新目录`.tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-vfmv-56cc69/`。逐值审计源码与前23轮逐字相同，完整重新检查5,475个原终态：5,472条gen和3条direct negative，无derived或encoder辅助输入。独立遍历全部38,148,123条源trace边，5,472条gen全部LLVM重汇编通过；原日志/JSON/trace守恒、两端完整AST/ret/102post、C++八let/15aux及原始worker JSONL均逐条通过。

独立phase证书按原三元ID及全部decode/execute hash列表消费：10,950个phase、169,958,254条指令观测，三个异常槽typed初末相等、沿途写0。最终重算全部canonical输入hash，核对VFMV原ID与前五包27,320个ID完全互斥；同时消费新source-and-replay退出记录、完整单目标consumer事件及旧VFMERGE失败/交接记录。结论为 **PASS_SCOPED_VFMV_SEPARATE_CONTINUATION_FULL_INPUT_AND_TWO_BACKEND_OBSERVATIONS**。

| VFMV冻结对象 | SHA-256 |
| --- | --- |
| owner observer summary | `c35df807fdba6ee965117acd2a1669c5376fc4291f6f242185526d759da4ec50` |
| owner evidence index | `decab33a602e23f6a02dac3d0f207400797e94e928f6f6f371313e8ba24c4a16` |
| 独立phase证书 | `77d42ca1a5d8a9fb7ac41eee5d9978192d5442b1217ef1e0f16a39416282650c` |
| source-and-replay退出记录 | `c17fa9cbfce4253edc0edd0adc02e4308368c7afe2b7637f44dd0df94b2fd980` |
| 最终独立消费脚本 | `9a6b5bda790f0d57dba9e60e96ff0751076a54581d5c3027880fc284da73d2c4` |
| 最终独审JSON（8,332文件） | `2d980eeddd82952deab80d9df59826dded065c7fa8caed6bb200a860c406f612` |

实际两步均退出0：

```sh
python3 .tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-vfmv-56cc69/audit_family.py .tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-vfmv-56cc69/target-VFMV.json
python3 .tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-vfmv-56cc69/finish_target.py VFMV isla/target/float-solve-evidence/replay-scratch-observer-20260927/sharedtrace-continuation-independent-review/packages/VFMV.json 77d42ca1a5d8a9fb7ac41eee5d9978192d5442b1217ef1e0f16a39416282650c
```

[VFMV最终独审JSON](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-vfmv-56cc69/VFMV-final-audit.json)保留`original-seven-target-pass=false`及前五/旧23/旧25,910证据边界。完整闭包12个异常写站点及full closure FAIL、observer opcode未另存的限制、whole77和源码分支未闭合均不变。

再以`aggregate_six.py`实际退出0生成[六完成、一外限的固定汇总](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-vfmv-56cc69/six-complete-one-timeout-audit.json)，SHA-256 `ae9fe916a260f685be161be6b5251c0deae6e9de08bda18ed87d21276713826c`。汇总直接核对14份已签证书/coverage文件，底层完整来源、数值及phase证据由六份逐包最终证绑定；六个已完成目标共32,795个唯一原ID，即32,772 gen、7 direct、16 derived，完整源trace119,703,429条边、32,772条LLVM重汇编，65,590个replay phase、661,435,785条指令观测、沿途写0。encoder仍单列16个辅助输入、32个phase、225,020条指令。VFMERGE外限124、旧等待consumer交接143、新VFMV监督退出0均显式保留；该六目标签收不替代原七目标全部通过，原七包全PASS脚本未运行。

## VFMERGE独立2小时源：分片适配器先行独审

新source位于`isla/target/float-solve-evidence/vfmerge-2h-56cc-20260927-c/`，manifest SHA-256为`6c5749ca13d2c9b400fa9ec8f11a9cdb530d5fc65f26640bac34dba6435456e3`。先行独审已核对其实际517份源码与受审sharedtrace源相同，IR56cc/FD配置20851/e669 provider及既有补充桥逐项匹配；实际source进程使用7200/7140/30秒预算，自然退出0，无监督信号。此为新预算、新run-id的独立证据，旧30分钟124及原七目标队列历史记录保持冻结。

新薄适配器`agents/float_support_review/tools/unified_backend_cpp_replay/sharded_official.py` SHA-256为`d49c0a3f65710dc851c64efed7a06bfb3e4113787252a692eb3e491f5c5f1631`。代码审查确认：完整父输入先校验；按完整对象连续分片、原ID不重复且覆盖精确；每片用新Python进程调用已冻结的配对逻辑，再实际启动独立Rust/C++，避免跨线程修改配对校验函数。局部分片manifest绑定父manifest，局部PASS不代表完整源；父调度最后再次核对全部完整对象分区和全部来源漂移。非零退出、缺失或失败摘要、输入总数不守恒都会阻断全组PASS。

原6项TDD测试已独立复跑通过；另对实际`run_sharded_pair`补充8项控制，覆盖完整嵌套字段及3/3/1顺序、有效摘要但子进程非零、退出0但缺摘要/失败摘要、无法启动子进程、嵌套输入修改、丢失输入和父来源漂移的拒绝行为。控制测试模拟子进程，不冒充真实模型回归。真实smoke另消费已审的旧完整七输入：3/3/1三片两后端实际退出0，完整AST/ret/102post、C++八let/15aux/raw JSONL、实际提交输入/命令/退出和父分区均通过；共14个phase、130,683条指令观测。smoke目录名称含e6a，但实际绑定a592观察器、56cc模型，不据名称迁移为e6a模型PASS。

```sh
python3 -B .tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/test_adapter_controls.py
python3 .tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/adapter_audit.py
```

命令退出0。[适配器限定独审](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/adapter-audit.json) SHA-256 `e33d064ff3082f30b2b7777ac872c632aedb6f60d35653824b1c9a0da43e40c5`，绑定8,890个实际文件。该独审器首次漏加载`observer_audit`的`run`模块依赖而失败；原稿、错误日志及说明均保留，补齐独审器加载顺序后通过，未修改owner适配器或模型。

此时只签适配器、七输入真实smoke及新预算身份绑定；新30,603终态的完整源trace/汇编及全分片数值/phase验收仍待独立完成。实际计划为4个独立分片进程、每片256条、启动前`MemAvailable>=32GiB`，完整终态集合不缩减；后续完整结果单独追加，whole77/source-branch/full-closure边界均不变。


## VFMERGE独立2小时源：首次prepare失败与严格trace补证

首次新队列 `sharedtrace-vfmerge-2h-56cc69-20260927` 的被测命令退出 **1**，用时2443.292秒，提交分片 **0**。外层写证据脚本退出0只说明退出记录已保存。原目录的 `exit.json`、`supervisor-exit.json`、`run.log` 与空结果目录均保留，不能据外层状态或后续重跑改写该次失败。原prepare未保存抛错前的完整audit，独审首次合并运行也在三flag断言失败后丢失内存明细；两者的旧脚本/日志保留，下面的补证不冒充首次内存结果。

独立复诊完整30,600条gen，22,985条通过LLVM重汇编，7,615条被LLVM拒绝；失败全是原 `Illegal_Instruction(())`、word的vd字段为0、文本目的向量为v0。首例case10556为 `vfmerge.vfm v0, v5, f16, v0`，原word `32'h5c58_5057`；LLVM诊断为目的向量寄存器组不能为V0。该诊断本身不构成ISA guard审核；后续需逐ID结合冻结Sail guard及原输入复核，不能沿用BF16清单或通配放行，也不能声称所有动态路径均已走到vd=0检查。

- [汇编复诊](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/assembly-diagnosis.json)：SHA-256 `c6ecc14daa37c8c13fd88fef6f0cdbfacf6b50bb2a2c2aae8ab90f2841140396`。
- [完整7,615失败原对象](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/assembly-failures.json)：SHA-256 `8705c0ba8517f7a98a43960d8ac99225df7eb89dc2545e24fd62c1504ee4b632`。
- [失败诊断包装独审](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/diagnostics-audit.json)：SHA-256 `96bf4c2ec9e43987de47defb5b035c827070b161c955cfbce04b7b533261baf5`；原3测试独立复跑通过。包装仅捕获原collect的AuditError，保存完整audit与队列后原异常重抛，独占新文件拒覆盖；不宣称可捕获所有前置校验异常。

严格trace独证随后实际退出0并立即落盘。同一遍读取原始 **44,122,131,855 bytes** 同时计算SHA-256与调用未改动的 `validate_trace_stream`：完整 **30,603**终态块、**215,491,497**执行边、**25,676**目录坐标全部通过；读前后size/mtime/inode一致，trace SHA-256 `6bf32f6202f0fc320b87225aedfc13dbad8538b5a99ad6810d2f22188755a39a`。完整payload为30,603终态、30,600gen、suppressed=sampled=0，runner/materialized完整。

```sh
python3 .tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/audit_trace.py
```

[严格trace独证](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/trace-audit.json) SHA-256 `7983151f98b9d275a621b4ceb56b79841c58d1751d1948db3e175aba1645f98f`，绑定686个文件；[精确复用附证](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/trace-reuse-certificate.json) SHA-256 `dfe19ce2ffdcde983bf4820be0fdeff4d5cf4fe4859dd9cd4e0d4a2f93d2deb5`。附证绑定原manifest/JSON、trace路径/bytes/SHA、validator文件及函数、完整终态canonical SHA `34cd66d5612c763fae2d5b5c254a6634760d887fc38131858c4586c63d2a590a` 与quota-off/完整流选项；封附证这一步复用前述严格扫描，没有再次扫描trace。

普通batch的trace_facts缺少严格块边界及sample_branch_condition拒绝检查，不能替代本严格证。拟供新隔离适配器只复用严格parser四字段结果，原audit_run仍真实hash原trace；适配器须完整核证/路径/终态/选项及hash期间文件稳定性并独审后才可使用。此段只签源payload和trace，以及限定的失败诊断包装；非法操作数guard与新完整双后端回放仍待独审，旧30分钟timeout和原七目标未全通过结论原样保留。


### 精确guard、复用适配器与新完整队列启动

架构独审交付 [7,615条guard证书](../../isla/target/float-solve-evidence/vfmerge-2h-56cc-20260927-c/stage/independent-illegal-operands-review/certificate.json)，SHA-256 `f900c97b72c28159fed5eb973667f1a304703baff1760a9c6e39809372ee8f9f`；其逐ID `reviewed-illegal.json` SHA-256 `dd7beb8cdd3038134c6ae3c3861e49e290e8d275bba6ccbaf34958a5da941898`。证书逐条核原word/AST/pre/post/Illegal、全部日志终态及冻结源码guard，并明确vd=0只是正常抵达guard的充分拒绝条件，不证明每条动态抵达。完整30,603条仍保留用于两端真实word decode/execute。

独审再次执行全部7,615条LLVM拒绝校验，并逐条对账该guard证和原输入canonical；另22,985条重汇编结果精确复用先前完整诊断的冻结结果。结合已封严格trace独证，重建未改 `audit_run` 的完整返回结构、30,600条gen和3条direct-negative，全部30,603条PATH_RESULT的ID/status/phase/signature重新核对一致；无derived、无negative gap。此重建不冒充首次失败的内存audit，也不宣称再次扫描trace。

```sh
python3 .tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/source_reviewed_audit.py
```

[补证后的完整源独审](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/source-audit.json) SHA-256 `ef812fb106d41916e124d20c8592e94fdd3ef6801e9d4dc0cf59ffc65f0b9620`，绑定715文件，实际退出0。该独审器首次误用trace终态的默认JSON格式计算guard canonical，而guard独审使用既定compact格式，断言失败；原脚本和失败日志另存，修正独审器格式后全量通过，未改guard证、源输入或生产模型。

[精确复用包装限定独审](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/trace-reuse-wrapper-audit.json) SHA-256 `e80cc2f46d951fc1f655d12b4df265c360154bd7c6f001de0885bd98b27b6168`，绑定22文件。新 `trace_reuse.py` SHA-256 `d1bbed6d44935ed73dba9338e58a6ae66c9b7492d9c17f65a7bd3bfc10e27698`；原4测试独立复跑通过，另5项控制覆盖不同路径、旧文件描述符、hash期间修改、原返回对象/审核对象保持、一次复用、异常恢复与输入manifest保留。控制使用临时合成流，不作为模型验证。实际严格附证成功构造；原audit_run仍核原trace哈希，复用前还核hash前后与已打开fd的dev/inode/size/mtime/ctime、完整终态canonical、validator与选项，仅返回原严格parser四字段结果。

新队列 [启动命令](../../isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-vfmerge-2h-reviewed-56cc69-20260927/command.json) 使用精确复用包装、失败诊断包装、reviewed driver与既审分片工具；实际PID2733316、监督PID2733275。输入仍为完整30,603条，4个独立进程、每片256，共预计120片（119×256+139）。启动绑定上述guard/trace/包装证书，首次prepare失败目录原样保留。此处仅记录新运行已启动，完整数值、phase及外层退出仍待验收。


### 新VFMERGE完整30,603条最终独审

新reviewed队列实际命令退出0，用时3524.787秒；120片全部真实双后端退出0，分区为119×256+139。原完整30,603个终态ID逐条且仅一次覆盖：30,600 gen、3 direct-negative、0 derived、0 gap，encoder另计0。输入审计与独立重建逐对象相同，22,985条重汇编和7,615条精确guard保留；没有缩减输入集合。

| 冻结证据 | SHA-256 |
| --- | --- |
| [完整输入三方对账](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/prepared-audit.json) | `375f8d71104f5a86e302f117fdd25cb5c3a1aaf353d23cfa222b701eeb003c92` |
| [全部120片数值独审](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/replay-audit.json) | `39ec127c43cf3cf610211bd5d7764be6a69933cea59e2398d2f76be53f189707` |
| [完整phase独证](../../isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-vfmerge-2h-reviewed-56cc69-20260927/independent-phase-review/certificate.json) | `e925f35cc5cd3d530e4ffcc5644899dce30edcc5a37c551c63af6cac7ea21b9e` |
| [最终联合独证](../../.tmp/unified-backend-cpp-replay-independent-sharedtrace-vfmerge-2h-56cc69/final-audit.json) | `74eff86cd5a09b5fb94c0e60c962cdc98b651358268c06cf587f917a3dbe5b5a` |

数值独审重新核对13,180个文件绑定、全部原输入完整字段、每片partition和真实命令/退出、两端完整AST/ret/102 post、C++每条8let/15aux初始化、原始JSONL与提交对象。完整观察为 **61,206 phase、940,516,587条指令、scratch沿途写0**；独立phase证逐ID、typed初末值、调用/返回与序列hash均联立一致。

最终联证对7,807项phase文件按数值独审冻结索引逐一匹配，另外重新hash9个新增phase文件，并核对完整逐ID phase与canonical覆盖、owner summary/index及真实外层退出。原44.1 GB trace在源独证中逐边核对，又在数值独审来源阶段重新计算字节hash；最终联证和phase reviewer按该显式冻结证消费，没有冒称再次逐边扫描。observer原始opcode未另存，不能称作磁盘原opcode重算证明。

**结论：PASS，仅新2小时预算自然完成的VFMERGE完整输出与该120片双后端观察。** 完整decoder/encoder静态闭包的12处异常scratch写仍保留，`full-closure-pure=false`、`whole77-complete=false`、`source-branch-closed=false`。原30分钟VFMERGE timeout、原七目标未全通过、首次prepare退出1/0分片与全部独审失败尝试原样保留，不以新独立运行覆写，也不迁移旧25,910历史集合的通过结论。


## 56cc自然完成输出的57唯一目标机器汇总

按主agent要求，消费上述已封完整数值/phase证、源manifest、input-audit、分类文件和coverage索引，对每个目标单列自然完成来源与完整回放闭环。实际汇总退出0，确认 **57个不同目标、80,416个不同 `(run-id, clause, case-id)`**；没有同目标重复计数，32个run-id在机器结果中完整列出。

| 来源包 | 唯一目标 | gen | direct-negative | derived-negative | 输入总数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 官方D代表 | 1 | 1,092 | 4 | 0 | 1,096 |
| 中断长批内26个自然完成目标 | 26 | 6,195 | 22 | 13 | 6,230 |
| sharedtrace 23目标 | 23 | 9,624 | 55 | 13 | 9,692 |
| 续队列六个完成目标 | 6 | 32,772 | 7 | 16 | 32,795 |
| 独立2小时VFMERGE | 1 | 30,600 | 3 | 0 | 30,603 |
| **合计** | **57** | **80,283** | **91** | **42** | **80,416** |

[机器摘要](../../.tmp/unified-backend-cpp-replay-independent-57-target-scope-56cc69/summary.json) SHA-256 `2b85853542a1ec1a0c0f0dde943d04e5787fcb53a0461303010d0efda0cdeefd`；[逐目标来源与双独审映射](../../.tmp/unified-backend-cpp-replay-independent-57-target-scope-56cc69/target-map.json) SHA-256 `52b0b27f4de4b47733e1e6282f800e162a62ded4c304f9950cf96a496c05f6d3`；[完整唯一ID及原canonical索引](../../.tmp/unified-backend-cpp-replay-independent-57-target-scope-56cc69/identity-coverage.json) SHA-256 `d3637583815a267d0a3d0b2982bc592c74564a74f8d96ab086a9fae410f644c6`。

各目标源make/isarch退出均为0，完整input-audit的runner/trace/assembly通过、materialized全部、suppressed/sample均0；gen与两类negative精确构成原完整终态集合。汇总重新hash215个直接证书/来源/审计/分类/coverage文件，逐目标消费已有完整数值与独立phase冻结证；本步不重跑模型、不重扫trace、不重新hash全部传递依赖，canonical值按原已审coverage索引消费。

这57个目标共同绑定IR `56cc69a4…` 与FD配置 `20851fdb…`，源二进制分别为 `4fc2ea00…`、`96efd569…`、`e669a22f…`，不能称作单一新runtime的一次完整批次。历史18,584条跨版本回归以及另42条encoder辅助输入未计入80,416；不迁移为e6a/441c的新模型PASS。原长批中断、原七目标队列timeout及首次VFMERGE prepare失败仍保留；全77、源码分支闭合和完整闭包纯读均为false。

## 单次父进程 trace receipt 工具及完整七输入独审（2026-09-27）

实施前[合同快照](../../.tmp/unified-backend-cpp-replay-independent-source-receipts/preimplementation-contract.json)继续保持 `PRE_IMPLEMENTATION_CONTRACT_SNAPSHOT_NOT_PASS`，不改写为结果。后续冻结候选为 `isla/target/float-solve-evidence/unified-backend-cpp-replay/source-receipts-development-20260927/candidate-freeze.json`，SHA-256 `8d2761aac0ad93738b5075c3775fbe02dd3de5de8a34e1a0a5c18d4e29f899ad`；其158文件独立重核，合同快照内9份旧工具及计划未漂移。既有VFMERGE冻结工具和运行证保持原样。

新增 `source_receipts.py`（`c0876ee7043539d4fce4f57b2e15f4a51ff4d21acacf1e0137cd4fff3be61d64`）与 `receipt_official.py`（`6d69f0bfccedd792e36122cf290987fe7f2522a1a871af3739916b9ec857e2b8`）限定一个canonical原trace、一个父PID和audit epoch。初始prepare真实hash不创建凭据；原audit真实hash后持有只读FD；三个中间调用核完整绑定及路径/FD身份后复用；最终来源遍历显式强制真实hash。生成的sharded副本只增加import和遍历前后两个callback，删除这三行与原文件逐字相等，邻接两个依赖亦逐字相等；不按hash调用次数或错误消息判断阶段。

[限定独证](../../.tmp/unified-backend-cpp-replay-independent-source-receipts/final-audit.json) SHA-256 `9984f6c08b17819d70a8e81e32b99c8f8c07e4200e1e68c4b832e38846a4b51c`，状态 `PASS_SINGLE_PARENT_EPOCH_TRACE_RECEIPT_TOOL_AND_SEVEN_CASE_SMOKE`，绑定1810文件。原21测试独立复跑通过，另7项独立控制通过：原audit在mint后抛错时保留异常对象并恢复全部引用/关闭FD；缺final门拒绝；完整terminal扩展字段改变拒绝；屏蔽元数据门的专用fixture中final字节SHA仍拒绝改变；初始hash不能代mint；新运行不能接受旧epoch；全部三个生成anchor各自缺失/重复均拒绝。原测试中的同长度改字节并恢复mtime、inode/symlink/FD替换、scope/parser/options/expectedSHA变化、真实fork、最终读期间漂移及缺最终trace读取负控均保留。合成控制不计为模型执行。

独立实际命令见[命令记录](../../.tmp/unified-backend-cpp-replay-independent-source-receipts/seven-command.json)，使用同一新入口，将所有输出改到独审目录；[退出记录](../../.tmp/unified-backend-cpp-replay-independent-source-receipts/seven-exit.json)为真实0、4.106216766871512秒。完整旧目标 `single-56cc-20260927-014615-03-f_un_f_type_d` 的7输入（6gen＋1direct，0derived、0gap）按3＋3＋1分片重新执行Isla与CPP，14phase、130683指令观察、scratch写0。完整输入/AST/ret/102 post、每条CPP 8let/15aux和raw JSONL均核对；原七条、owner候选与独跑的完整结果对象相等。比较只排除Isla每行顶层 `elapsed-ms`，以及CPP每行顶层 `decode-us`、`execute-us`、`load-us`、`model-init-us`、`total-us`；全部嵌套对象原样保留。

独跑[receipt报告](../../.tmp/unified-backend-cpp-replay-independent-source-receipts/receipt-report.json) SHA-256 `06a284e38acd7aa27cdc268f40d096cd77a0ed098a23a7cd3326e4f5114c9cad`核到真实六调用：3次完整读取＋3次复用。原trace为9,614,790字节，单次回放实际读取28,844,370字节；三个真实hash累计0.028034663060680032秒，三个复用累计0.000647268258035183秒，另有5554次非trace真实hash。独审额外以同一遍raw字节SHA和未改严格parser重验该完整trace，15,263边、7终态、25,676 catalog sites，与来源附证一致。上述额外独审读取不计入回放receipt指标；未重扫44GB trace，不将进程I/O或小包墙钟外推为下一大包的耗时结论。全77、源码分支闭合与完整闭包纯读仍为false；逐opcode原序列未落盘的既有限制保留。
