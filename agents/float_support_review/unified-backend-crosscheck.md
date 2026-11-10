# 统一 Sail helper 三方交叉验证（2026-09-27）

本报告只记录 P1 冻结候选的 67 个 RISC-V 浮点 helper。共用 Sail 函数体分别由真实生成 C++ 模型和 Isla IR 执行；独立进程中的 RISCV SoftFloat specialization 提供结果位与五个原生异常标志参考。具体用例和工具见 [专属入口](tools/unified_backend_crosscheck/README.md)。整指令、完整架构状态及官方 77 项验收另计。

## 版本与方法

- patched Sail/插件的真实严格生成记录为 `ir-generation.json`；候选 IR SHA-256 `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061`。v6 IR 源 manifest SHA-256 `749c3c5b…`，v7 模型 manifest SHA-256 `7e945fba…`。`cpp-source-v7-bind.json` SHA-256 `d4a31e79…` 确认 v7 只补 20 个 SoftFloat 平台构建文件，Sail model 树与生成 IR 的 v6 逐字一致。工具链构建 manifest SHA-256 `009f76a6…`，最终 C++ 生成头/源分别为 `45fd0f83…`、`3f2af389…`，三静库为模型 `8cd6d91d…`、SoftFloat `1671ac48…`、Sail runtime `4fd316e1…`。
- Isla 使用冻结 runtime 的 `primop.rs`、`ir.rs`、`fmtval.rs`、`smt.rs`（SHA-256 前缀分别 `6c6d5a42`、`d26e7923`、`43806138`、`3ce7310d`），runtime 快照 manifest `28fb65ee…`。测试只在证据目录复制 IR 并附加 67 个调用包装，原 IR 原件不改；wrapper 增量和哈希进入每轮 Isla 报告。
- [smoke 输入](tools/unified_backend_crosscheck/inputs.jsonl) 83 条，SHA-256 `f31a5600…`；[完整输入](tools/unified_backend_crosscheck/full-inputs.jsonl.gz) 17,586 条，压缩文件 SHA-256 `3a701790…`，67 个 helper 均在。后者来自已归档各格式和异常边界生成器，保留来源哈希及逐例输入。独立 SoftFloat oracle 二进制 SHA-256 `0bb63bc7…`，每例单独采集五 flags，不执行共用 Sail 的异常公式。
- C++ runner 逐名确认生成头/源有 67 个 `hart::Model::zriscv_*` 声明与函数体，直接调用并从真实 tuple 取 `ztup0/ztup1`。Isla runner 对每例记录真实 `Model::get_val` 的 `VALUE`，并要求普通函数进入 trace、SAT、恰好一条完成路径及规定结果位与全部五 flags 的差异 UNSAT。三方比较器再对实际 C++/Isla 结果及独立 native flags、适用的 native 结果位做逐项验证。

| 输入 | 三方结论 | C++具体执行 | Isla SAT＋差异UNSAT执行 | 汇总证据 |
| --- | --- | ---: | ---: | --- |
| 83 接线 smoke | 83/83、零差异 | 0.005 s | 5.010 s | [smoke 汇总](../../.tmp/unified-backend-crosscheck/triple-smoke-summary-final-v2.json)，SHA-256 `e5da51b5…` |
| 17,586 完整 profile | 17,586/17,586、零差异 | 0.064 s | 47.140 s | [完整汇总](../../.tmp/unified-backend-crosscheck/triple-full-summary-final-v2.json)，SHA-256 `54f92909…` |

完整 profile 中 14,161 例三方完整结果位全等；1,733 例仅屏蔽 native 原语未指定的 NaN payload，同时独立核对共用 helper 的 canonical NaN 位；1,692 例无效 FP→整数要求 native NV 与 RISCV specialization 饱和值 **三方完整位串全等**。全部 17,586 例的五 flags 均三方全等。三条协议负控通过，包括两共用后端给出相同但错误的整数饱和值必须失败。C++具体执行与 Isla 求解证明工作量不同，上表仅列原始耗时，不计算加速比；两者各轮构建耗时另见汇总 JSON。

第一次 C++ smoke 因测试 runner 在 `model_init` 前漏装配置，实得 `.base.E` 缺项并退出 1；[失败摘要](../../.tmp/unified-backend-crosscheck/cpp-p1-v7-smoke/summary.json)保留。修正后使用同一 build 的 RV64D/V128/E64 JSON，经 `sail_config_set_string` 再初始化，在新证据目录通过；未修改生产模型。C++ build 的配置源、规范化 JSON、真实 argv、链接库及二进制哈希均在两轮汇总中。

## 同版旧入口回归与独审

- [闭包报告](../../.tmp/unified-backend-crosscheck/helper-p1-closure.json) SHA-256 `e8387f11…`：历史 79 个 helper 均有 `val/fn`，含四个显式 preserve 的窄整数旧体；当前 94 个 `riscv_*` 声明与函数体齐全。
- [旧样例全套](../../.tmp/unified-backend-crosscheck/helper-p1-v7-all/reports/summary.json) SHA-256 `ec9ef1b1…`：277 个未知入口按 f16/f32/f64 为 90/96/91，各 SAT、单路径并有普通体 trace；67 原 helper、估算 350/1618/420、旧 12 体 39/24、legacy 35 均在真实 IR 普通体上核完整结果位与五 flags 差异 UNSAT，十组 exit 0。输入与前一批归档逐文件 SHA-256 相同，三个 runner 均重新构建。此旧回归与三方完整 profile 分别记录，不相互代替。
- 同一 IR/runtime 的 [FD/VPR direct 报告](../../isla/target/float-solve-evidence/direct-state-p1-348147/reports/summary.json) SHA-256 `b0e9d977…` 由状态验证负责人运行：FD getter/setter/具体与全符号 `accrue_fflags` 四组通过，符号完整状态差异 UNSAT；VPR 24 组合对两入口共 48 次调用通过。执行配置为原 RV64 E TOML SHA-256 `8247c8d4…`。
- 独立审查的[三方数值报告](../../.tmp/unified-backend-crosscheck/independent-review/final-review.json) SHA-256 `347cb58d…` 为 `PASS_SCOPED_67_HELPERS`；[最终 manifest 绑定](../../.tmp/unified-backend-crosscheck/independent-review/manifest-binding-review.json) SHA-256 `b006521d…` 为 `PASS_FINAL_MANIFEST_BINDING`。审查者逐项核对 83/17,586 输入输出、实际二进制复跑、67 方法符号、模型/运行时/配置/静库以及报告哈希；历史 277 和 79/94 只复核版本绑定，不扩大该独审的语义签收。

上述 PASS 均固定于 IR `348147f8…`、该模型/工具链/runtime、列定输入和独立 oracle。后续 Sail、IR 或关键配置改变后须重新复验；当前报告不证明未知符号输入全值域、97 个 typed FP 声明、TLS/环境隔离、源码分支闭合或整指令 77 项通过。

## V4＋AMO 同源候选重跑（2026-09-27）

V 扩展四个纯合法性 helper 与 AMO SYMBOLIC 编码修改后，以上 `348147f8…` 结果只保留历史。新 [真实构建报告](../../isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/model-build.json) SHA-256 `d6b825af…` 为 PASS，原子复制并逐项锁定 931 个 Sail-RISC-V 源文件；真实 Sail 严格生成 IR SHA-256 为 `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`，C++ 生成头/源分别为 `f79d0009…`、`96d18cea…`，模型/SoftFloat/Sail runtime 静库分别为 `3dbc3b43…`、`1671ac48…`、`4fd316e1…`。新候选快照 manifest SHA-256 `fdf105d1…`，含同源模型166、Sail库125和Isla runtime510文件；[v3 来源桥接](../../.tmp/unified-backend-crosscheck/v4-amo-provenance/source-repackage-proof-v3.json) SHA-256 `388f295c…` 为 PASS，明确绑定原931文件构建、候选快照、新IR、工具链及原冻结runtime。该三份候选来源文件也复制于 `v4-amo-provenance/` 以供本工作区核对，未替换原构建或候选原件。

新头/源中 67 个普通 `hart::Model::zriscv_*` 声明与定义再核齐，C++ 和 Isla runner 均从新候选重建。对相同83条 smoke 和17,586条完整输入，真实 C++ tuple、Isla `Model::get_val` 与独立 native SoftFloat 比较仍为零差异；Isla逐例普通体 trace、SAT、单完成路径及结果位/五flags差异 UNSAT 仍成立。适用域仍为14,161条全位三方相等、1,733条 native NaN payload 限定屏蔽和1,692条无效整数 RISCV 饱和值全位核对，五flags全部三方相等。

| 新 IR 输入 | 三方结论 | C++具体执行 | Isla SAT＋差异UNSAT执行 | 同源汇总 |
| --- | --- | ---: | ---: | --- |
| 83 smoke | 83/83、零差异 | 0.006 s | 5.921 s | [新 smoke](../../.tmp/unified-backend-crosscheck/v4-amo-triple-smoke-summary-v3.json)，SHA-256 `e892a5fb…` |
| 17,586 full | 17,586/17,586、零差异 | 0.086 s | 61.939 s | [新 full](../../.tmp/unified-backend-crosscheck/v4-amo-triple-full-summary-v3.json)，SHA-256 `1abe66ef…` |

新版 [闭包](../../.tmp/unified-backend-crosscheck/v4-amo-helper-closure.json) SHA-256 `ab0cc8b7…` 再证历史79个 `val/fn`、四个窄helper以及当前94个 `riscv_*` 函数体齐全；[旧样例全套](../../.tmp/unified-backend-crosscheck/v4-amo-helper-all/reports/summary.json) SHA-256 `42dd208d…` 再过277未知入口90/96/91、原67、估算350/1618/420、旧12体39/24、legacy35，十组exit 0。FD/VPR 同 IR 的[直接状态门槛](../../isla/target/float-solve-evidence/direct-state-p1-56cc69/reports/summary.json) SHA-256 `f70a0bdd…` 已由状态验证负责人运行：FD4/4、VPR24组合乘两入口通过；使用RV64 E配置 `8247c8d4…` 与同冻runtime，独立于本包三方结果。

[新组装命令](../../.tmp/unified-backend-crosscheck/v4-amo-assemble-commands-v3.json)固定具体参数与退出码。`assemble.py` 对新版本逐项复核真实931文件、候选166/125/510文件及v3桥接，另核IR/CPP与三静库、工具链、runtime、配置和三个runner输出哈希后才报告 `PASS_HELPER_TRIPLE_PROFILE`。[Astra新版独审](../../.tmp/unified-backend-crosscheck/v4-amo-independent-review/review.json) SHA-256 `7421e482…` 为 `PASS_SCOPED_67_HELPERS_AND_VERSION_BINDING`；独立重算83/17,586三方完整位与五flags，复跑CPP smoke/full TSV、Isla smoke及native83，并用四个协议负控和一个真实Isla错误flags负控检验拒绝路径。独审另核2484个来源链文件与82项证据引用零漂移；[复核摘要](../../.tmp/unified-backend-crosscheck/v4-amo-independent-review/verification.json) SHA-256 `24d1c24f…`，[最终一致性](../../.tmp/unified-backend-crosscheck/v4-amo-independent-review/final-consistency.json) SHA-256 `45815a75…`。历史十套件与79/94闭包只做版本及执行证据绑定，未扩签其语义；`source_branch_closed=false`，本次不外推为官方整指令77项或全部typed接口通过。

## 441c 合批候选的 67 helper 实跑与独审（2026-09-27）

LMUL 与 unary 合批后，本节重新执行同一套列定输入，不沿用 `56cc69a4…` 的动态 PASS。[441c 完整构建](../../isla/target/float-solve-evidence/unified-backend-build/model-lmul-unary-20260927/model-build.json) SHA-256 `752f10c9e1a0d18e05628ef28d77decc11cd23c57b47ef276bd5001d2c2add12` 生成 IR `441c145b0d27c1978d273c09ff561300c3c52244437df40cc75182665715f47c`，同源 C++ 源/头 SHA-256 分别为 `e30bc39e7b794aa75d91f7c85aa28fd5679541d168b182e2dcda31cfab5ab696`、`3eb389a92c88fe363c7ee8ff55d0ea2376b1014d177b6c3f909d64c3a7f6e556`，模型库和 SoftFloat 库分别为 `dc9134adceb8179e0ee4986a17edbbbf624fbd927e13335493eec942369f2a7f`、`1671ac4816c2b093baefaffb1fffccc124619822283c01812e12e26aacb3d226`。候选 `source-manifest.json` SHA-256 `628e3169601ef40092d09f278a2811b6cd579ed8d8ecc44e3e5950118a89ee6c` 锁模型、Sail 库与 517 个 Isla runtime 文件；另一个独立的 `candidate-freeze.json` SHA-256 `683bde37a24002d16b5dc9e4928932333ec78ee8bf8f23e5f259b175b4885321` 锁来源、构建、IR 和配置证据。两者职责和哈希分列，不互代。441c 完整 IR/C++ 的[结构独审](../../isla/target/float-solve-evidence/unified-backend-build/model-lmul-unary-20260927/independent-full-ir-review/certificate.json)和[严格配置/来源独审](../../isla/target/float-solve-evidence/unified-backend-build/model-lmul-unary-20260927/independent-strict-source-review/certificate.json)已分别通过；本节的运行直接消费上述构建产物和同版冻结 runtime。

[本轮 producer 总索引](../../isla/target/float-solve-evidence/unified-backend-build/model-lmul-unary-20260927/helper-crosscheck-441c-20260927/report.json) SHA-256 `ae4a9a2f3d337d73fbe9ddc3d5a7f535b614363045acefe93d6ec8610247ef06` 保存实际命令、输入/IR/CPP/库/runtime、runner、逐端输出与日志哈希。[预检](../../isla/target/float-solve-evidence/unified-backend-build/model-lmul-unary-20260927/helper-crosscheck-441c-20260927/preflight.json)逐项核构建报告的七个产物哈希、C++ 链接命令及 include/静库路径。两个 profile 都实际运行独立 native SoftFloat、真实生成 C++ 普通 helper 体和真实 Isla IR 普通函数体；Isla 逐例要求 trace、SAT、单完成路径及规定结果位和五 flags 差异 UNSAT。C++ 与 Isla 原始结果再与 native 比较：14,161 例全位三方相等，1,733 例按既定 native NaN payload 例外检查共用 canonical 位，1,692 例无效整数按 RISCV 饱和值全位比较；五 flags 全部相等。

| 441c 输入 | producer 三方结果 | 独立复核 | 证据 |
| --- | --- | --- | --- |
| 83 smoke，覆盖 67 helper | 83/83 PASS，零差异 | 实际结果重算及精确 tuple 型检查通过 | [smoke 汇总](../../isla/target/float-solve-evidence/unified-backend-build/model-lmul-unary-20260927/helper-crosscheck-441c-20260927/smoke/summary.json) |
| 17,586 full，覆盖同一 67 helper | 17,586/17,586 PASS，零差异 | 实际结果重算及精确 tuple 型检查通过 | [full 汇总](../../isla/target/float-solve-evidence/unified-backend-build/model-lmul-unary-20260927/helper-crosscheck-441c-20260927/full/summary.json) |

[独立证书](../../isla/target/float-solve-evidence/unified-backend-build/model-lmul-unary-20260927/helper-crosscheck-441c-20260927/independent-review/certificate.json) SHA-256 `3f197c8fee1178fdb9df58e4ceac4312de084d2e225848e178f2075bc74463e1` 绑定 3,815 个文件且零漂移。审查者独立重算 83＋17,586 个三方结果，重新运行 C++ 与 native，并用加严的实际 IR 返回类型门复跑 Isla **17,669** 个 `ztup0/ztup1` 精确字段及类型检查；15 项测试和负控通过，含错误 flags 拒绝。证书明确只签这 67 个 helper 的列定输入；不签 decoder AST、全部 typed 接口、源码分母或官方 77 项整指令完成，`source_branch_closed=false`。

## nan86f 候选的 67 helper 重新实跑与独审（2026-09-27）

nan_unbox 改动后的[完整构建](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/model-build.json) SHA-256 `60af7f079d533318c61dd2b9b5cae0eb283ce8c3705ef2f3471bf7cee80c9052` 实际生成 IR `86f1121b09634575e60629c272cfddb741c809182a2fa4b337acb6755b17e61f`；C++ 源/头为 `0a0ea5d7…06fa` / `b3656fdf…d2f8`，模型、SoftFloat、Sail runtime 静库为 `be0d2ed4…fd6c` / `1671ac48…d226` / `4fd316e1…ca4e2`。[新包预检](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/helper-crosscheck-nan-20260927/preflight.json)逐项钉实际 IR、CPP、配置、静库和命令；候选源码清单 SHA-256 `f0c20ae855c04c2d51fc2d51dc191ec8b5754dbcd94a39d527dd7e3463925f09`，候选冻结清单 SHA-256 `acbf736be7e8ab07a030bfbcbfeb452f763f8daa65576d8b60d2487ac5ac67b2`。冻结 Isla runtime 与候选 `isla-lib` 全树逐字相同。本轮重新编译并运行 C++ 和 Isla runner，复用原 83/17,586 输入及独立 oracle；其结果与441c部分输出哈希相同，但执行身份、构建及退出证据均来自新目录。

| nan86f 输入 | 三方结果 | 实际汇总 |
| --- | --- | --- |
| 83 smoke，67 helper | 83/83 PASS，零问题 | [smoke](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/helper-crosscheck-nan-20260927/smoke/summary.json)，SHA-256 `4168290a…ab00a` |
| 17,586 full，67 helper | 17,586/17,586 PASS，零问题 | [full](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/helper-crosscheck-nan-20260927/full/summary.json)，SHA-256 `f84a9a29…3eb13` |

[producer 报告](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/helper-crosscheck-nan-20260927/report.json) SHA-256 `28f8c2a6b4209f97fcffcccb99e45369ac490fb322767c17a718131c5b9f6b78`保存实际命令、双端结果、原始 IR 与依赖哈希。[独立证书](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/helper-crosscheck-nan-20260927/independent-review/certificate.json) SHA-256 `fe432ce3dc4284fcd2b0c9a068dc94e584aaf6f861599861b937871428e5bc06`独立重编译和复跑 C++/native、核 **17,669** 个实际 Isla 返回 tuple 的精确两字段与宽度并拒绝 Poison/List，19 项测试及控制通过，11,070 项依赖重哈希零漂移。旧审计脚本的一项 live V 源哈希已变化，独审按[冻结来源投影](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/helper-crosscheck-nan-20260927/independent-review/historical-live-projection.json)单独记历史漂移，投影 SHA-256 `c8c198a6…b04b60`；没有把现行根工作树当作 nan86f 候选。

## nan＋reduction a040 候选的 67 helper 重新实跑与独审（2026-09-27）

两个 reduction Illegal helper 合入 nan 候选后，[新完整构建](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/model-build.json) SHA-256 `9f47ff72341f10cf77ec8fc1cf76ec5dceb27c6ca02189aeeaa1ea32582ac9ee` 实际生成 IR `a04050747af5354db3db507097d9ed52e3bd9daa157f2ab043b48ef2952dfa7d`；C++ 源/头为 `75c5fa5a…630b` / `b3656fdf…d2f8`，模型、SoftFloat、Sail runtime 静库为 `a18c35af…cc2a` / `1671ac48…d226` / `4fd316e1…ca4e2`。运行命令的 `--candidate-manifest` 如实指向实际构建输入的931文件[清单](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/helper-crosscheck-nan-reduction-20260927/source-manifest.json)，SHA-256 `2774d000226747c6ccf0cdafa36898899ca52e1a460d04f3e0af4432cf133a04`；另以[候选来源桥](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/helper-crosscheck-nan-reduction-20260927/source-bridge.json) SHA-256 `ef6db045…f6bb`核完整候选 `source-manifest.json` SHA-256 `20588fb7…7efdb`、`candidate-freeze.json` SHA-256 `8d5fedf4…53dc`及其517个Isla、166个模型、125个Sail库文件，与实跑模型/runtime/IR逐字对应。没有用完整候选清单替换实跑时的931文件输入身份。

| a040 输入 | 三方结果 | 实际汇总 |
| --- | --- | --- |
| 83 smoke，67 helper | 83/83 PASS，零问题 | [smoke](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/helper-crosscheck-nan-reduction-20260927/smoke/summary.json)，SHA-256 `c1705a6a…2daa` |
| 17,586 full，67 helper | 17,586/17,586 PASS，零问题 | [full](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/helper-crosscheck-nan-reduction-20260927/full/summary.json)，SHA-256 `983c72fb…d509` |

[producer 报告](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/helper-crosscheck-nan-reduction-20260927/report.json) SHA-256 `a93981607be79ecbc70afd29825e7d50ce4c6cfd0c86736bdfc0411e5a27321f`保存本次全命令及退出码。[独立证书](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/helper-crosscheck-nan-reduction-20260927/independent-review/certificate.json) SHA-256 `902c1d605db33892d69137f35817ecc61acf9cdb172faaaab2440b771c583332`独立复跑两组 C++/native 和 **17,669** 个实际 Isla tuple 精确字段、类型与宽度；15 项测试/控制通过，11,737 项来源依赖零漂移。本批采用正式候选冻结与实际构建桥接，无 nan86f 旧审计脚本的 live V 源投影。两版的完整 IR/C++ 与严格配置/来源独审分别见 nan86f [结构](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/independent-full-ir-review/certificate.json)/[严格](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/independent-strict-source-review/certificate.json)、a040 [结构](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/independent-full-ir-review/certificate.json)/[严格](../../isla/target/float-solve-evidence/unified-backend-build/model-nan-reduction-build-20260927/independent-strict-source-review/certificate.json)。两版输入仍分别按原规则核14,161条全位三方相等、1,733条native NaN payload例外及1,692条无效整数RISCV饱和值，17,669条五flags均三方全等。nan86f结构/严格证书SHA-256为`4f0f7e08…31b26`/`43e1e908…ba975`；a040为`d1031e6a…9e5f8`/`517a7cad…a7ae`。以上证据只签67个 helper 的列定输入和精确返回；不扩为97 typed接口全集、decoder AST、源码分支闭合或官方77项整指令验收。
