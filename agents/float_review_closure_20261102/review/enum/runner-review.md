# 完整 Clause 运行与程序冻结独立复核

本页接续枚举修复审查，只审验证入口和程序冻结；生产代码、验证脚本由各自实施者维护。

**启动后修订：下文对 `fe4bdceb…` 候选与 runner `7b126047…` 的准备签存在遗漏，不能再作为启动77条批次的充分条件。** 该候选只有 `smt-thread-interrupt`，未启用固定 `--itrace` 所需的 `tracetool`；首批14条均在CLI参数检查时退出1、无JSON，余63条停止排队。真实失败见[批次说明](../../validation/full_batch/batches/float-closure-8ad5e8e-42000be-20261102/startup-failure.md)。这不是求解超时。此前 reviewer 只跑 `--version` 和 watchdog 探针，没有按完整 harness 参数实跑，漏掉 feature 与固定 CLI 的兼容性检查；原签收文字保留作版本记录，新程序须经完整 FLEQ_S smoke、非空 itrace、完整 JSON 和新 feature 强门后重新签收。

新 `acda0dce…` 程序与 `b154941b…` runner 已经完成这些补验并重新限定签收，详见文末。

## 先行发现与历史修订

初版 `isarch-42000be-default` 未启用 `smt-thread-interrupt`，不能仅凭命令含 `--smt-timeout 7200s` 就声称单次 SMT 限时生效。`configure_z3_timeout` 仍保存参数，但无 feature 的实际调用宏执行 `Ok($call)`，不会启动 watchdog。发现已通知实施者与主 agent，要求正式程序启用该 feature，并用短探针确认 watchdog。

同一检查也适用于上轮冻结程序 `abce451a11e0e4a8a3c9658d4a8462634f284085f219cca79f439ca176853a1a`：原元数据 features 仅 `default`，原构建日志包含 `Interrupted` 未构造警告，实际 ELF 不导入 `Z3_interrupt`，对应 `cf1aa14` 源码宏的无 feature 分支直接调用 Z3。见[旧程序审计](old-binary-timeout-audit.json)。

因此，旧结果中“整条 Clause 外限 7200 秒”仍成立；“单次 SMT 也执行 7200 秒限时”须修订为**仅传入参数，实际未启用单次 watchdog**。本审查未重跑旧长 Clause，不撤销旧实际退出码、墙钟、JSON 或模型检查，也不将这项修订静默写回原始证据。主 agent 应在历史摘要入口追加本修订。

## seed17 独立实测

已读冻结 `seed_control.c`：拦截所有 `Z3_params_set_uint` 的 `seed`/`random_seed` 字符串参数，统一改为环境指定值；只记录首条日志，后续调用仍全部改值。Isla 正式求解器只经该 C API 设置能力探测选出的随机种子，当前官方 qffp 对应 `random_seed`。

独立[短探针](seed_probe.c)在官方 qffp solver 设置 `random_seed=987654321`，实际读取参数变为17，检查 SAT。拦截库 SHA256 `8b26e6567f153ec28f35dfaddc15e9dfa3d53dcfa7fb1fe23d4922452bf429ae`；`LD_DEBUG=libs` 确认实际装入官方库，见[结果](seed-probe-result.json)及[装载日志](seed-probe-loader.log)。构建曾因默认 Linuxbrew linker 失败两次，改系统 PATH、系统 linker 与显式 `-lm` 后通过；失败与最终命令已记录，未计为通过。

## 运行入口审查

原 `run_clause.py` 有两处会误判的薄弱条件，已交验证 owner 修订：缺失 summary 计数被默认为0；seed 日志只搜索 `random_seed` 子串。加严版要求所有错误/超时/未完成/采样等字段存在且为非 bool 的非负整数、全部为0，目标 Clause 正确、单份 JSON、至少一条用例、状态 finished；seed 日志逐行解析并核 fixed=17，当前官方 qffp 至少出现一次 random_seed。

完整域锁定正式 FD 配置精确 SHA256 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`；该母本无 initial_state、execution_limits、指令切片或运行态 vl/vstart/vtype/mask 固定值。FS/VS=Dirty 和平台/扩展开关是明确既有前提，不能将其结果外推 FS Clean/Initial。命令不传额外执行限额、定向初态或切片参数；IR 拒绝已知定向 wrapper。

整 Clause 使用外层 `timeout 7200s`，超时TERM后10秒KILL；未另加较短单路径限时。单次 SMT 参数为7200秒，**还须正式程序启用 feature 的冻结证据和 watchdog 实测**，才能签两项限时同时有效。

`freeze_source.py` 检查完整 HEAD 与已跟踪文件无未提交差异，并逐个哈希全部已跟踪文件；运行器再核清单文件哈希、源码HEAD与各源文件。它不把未跟踪文件纳入冻结；若构建或生成依赖未跟踪源文件，须在生成 provenance 另列，不能只靠本脚本证明来源。

## 正式程序与入口限定签收

正式候选 `isarch-42000be-interrupt` SHA256 `fe4bdcebd1d970d6f026c0f81ccd22f807f5cb4729da27ef67e20b2c08d09d80`，提交 `42000be47596ec088623881d03c0eadc5cf0ba27`。实际 binary 与构建 manifest 一致，isarch/isla-lib 两份 Cargo fingerprint 均含 `smt-thread-interrupt`，实际 ELF 导入 `Z3_interrupt`；独立启动 `--version`、实际装载日志及官方 Z3 哈希核对通过，见[正式程序运行证据](formal-binary-runtime.json)。

独立[watchdog 探针](watchdog_probe.rs)直接链接正式程序同批已构建 `libisla_lib-b4e99d5da1d30452.rlib`，没有重编依赖。以10毫秒 deadline 包裹真实 check，诊断专用 preload 仅将该 check 延后80毫秒，观察实际 `Z3_interrupt` 调用1次，受测 Rust wrapper 返回 `SmtError::Timeout`、limit=10毫秒、墙钟81毫秒。见[探针结果](watchdog-result.json)、[诊断延迟层](watchdog_delay.c)与[实际装载日志](watchdog-runtime.log)。这是同一已构建代码的 watchdog 证明，不是假借命令参数或零项过滤器通过。

最终受审 runner 已加入正式 binary manifest 与 watchdog 证据的哈希和内容检查；静态调用闭包也要求与最终模型/Isla提交一致、clean状态与64条分母一致。清单中77条正式非访存浮点 Clause 分为64条受影响、13条兼容回归，二者不重复。当前静态闭包指向 clean 模型 `8ad5e8e9e0fc2a567a3b989a3738698f5c520bde` 和 Isla `42000be`，后续模型变更须重新生成。

独立13项输入反例检查通过：合法 JSON/seed 接受；缺计数、bool/负计数、错误 Clause、缺 gen、缺输入来源或错误 IR 哈希拒绝；seed18、垃圾、空日志及混杂错误seed拒绝。见[反例检查](runner-negative-probes.json)。JSON 中程序自己记录的 `-A/-C` 输入哈希与冻结 IR/config 也须一致，不能只靠起跑前的文件检查。

本页据此**限定签收正式候选程序和完整 Clause 入口的准备条件**；无新增阻断。受审文件哈希见[清单](runner-source-hashes.json)。最终 IR 集成若改变 Isla HEAD，仍须满足同源构建 manifest 与源码清单契约，不能自动将42000be候选的签收迁到新HEAD。实际77条完整域尚未由本审查运行，本页不构成完整预算或语义覆盖 PASS。

主 agent 已明确分阶段版本：第一阶段正式 inputs 使用 runner-float 中 clean Isla `42000be`，IR 使用外部 generation 产物及其精确哈希，不提前移动受测子模块 HEAD。第二阶段再安装五 IR 与永久测试并提交；若仅这些产物/测试变化，可用运行期编译源逐项哈希一致的证据说明前阶段结果的适用范围，或在新 HEAD 再执行相同 cargo build 并生成新 manifest。第一阶段不声称受测了尚未产生的新 HEAD。

## 含轨迹支持的新候选重新签收

新程序 `isarch-42000be-interrupt-itrace` SHA256 `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`，两份实际 Cargo fingerprint 均为 `default,itrace,smt-thread-interrupt,tracetool`。新版 runner SHA256 `b154941be1eaf7cd788c66053edbe564458a39eb8ba65f962aa85d26eaabc7b1`，正式 inputs SHA256 `0e57cf681917c9a3f05070c146b877b7ed30e108dc2135d3f31740966965f90c`。完整冻结列表见[新哈希清单](runner-itrace-hashes.json)。

新 runner 在起跑前要求顶层 `itrace` 与 isla-lib 的 `tracetool`，每个作业 PASS 还要求实际 itrace 非空并记录大小/哈希。用原失败 inputs 执行新版 dry-run，已经在创建作业目录和启动进程前拒绝缺轨迹 feature 的旧程序，见[反例](runner-reject-untraced.json)。

独立 reviewer 用新版 runner dry-run **实际构造的完整命令**运行 FLEQ_S，参数与实施者 smoke 完全相同，仅物理核换为预检空闲的 CPU32（同胞96）。命令保留 T1/qffp/seed17、整 Clause/SMT各7200秒、所有debug/probe/trace与itrace选项；没有定向输入或较短 smoke 限时。运行自然退出0，16.517秒，48条退休 JSON，summary finished且所有错误/超时/采样/遗漏计数为0；实际itrace为17,956,378字节。`LD_DEBUG=libs`确认该真实命令装入官方 Z3，JSON自身记录的IR/config来源与冻结哈希一致，见[完整结果](harness-smoke-itrace/result.json)。生成JSON SHA256 `e299bfe083aaaac18a3fe032038a9b3384458dbf42318c61ce9901455f434e6b` 与实施者 CPU99 独立运行完全相同。审查者使用的 inputs 与正式新 inputs 内容及 SHA256 均相同。

新程序同批 `libisla_lib-a482be6289cbafd1.rlib` 的 watchdog 也重新独立实测：10毫秒deadline、延迟80毫秒真实check，观察实际 `Z3_interrupt` 一次和 Timeout（limit10毫秒、wall81毫秒），官方库实际装载通过，见[新 watchdog 结果](watchdog-itrace-result.json)。未将旧rlib结果直接迁到新feature构建。

据此**重新限定签收新程序、完整CLI合同与启动门**，允许使用新唯一批次继续完整 Clause 验证。原14条启动失败、63条未启动的旧批次原样保留；本次 smoke 不增加77条正式批次完成数，也不替代完整域预算和语义覆盖验收。

本轮冻结脚本另增加 `--isla-source`：常规仍固定全部已跟踪文件，该选项排除全部 `.ir` 与生成provenance JSON，文件清单明确标记 `isla-source-excluding-generated-ir`。当前精确排除五份生成IR、两份测试fixture IR和provenance，共8文件；正式运行IR已在 inputs 逐份独立哈希，生产 Rust/构建源码仍在清单内。此边界与分阶段版本方案一致，不能把该1021文件清单写成1029文件全量冻结。
