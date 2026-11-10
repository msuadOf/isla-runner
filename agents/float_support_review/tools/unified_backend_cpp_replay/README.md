# 完整指令 C++ witness replay

本工具调用真实 Sail C++ 模型的 `ext_decode(word)` 和 `execute(decoded)`，核对完整 AST、返回值和全部 102 项 post 状态。输入集合限同批 `run.mk` 的 `FD_NONMEM_RV64`（77 项），另接受物理 word 译码得到的 `ILLEGAL`。方案及验收边界见[完整指令 replay 方案](../../unified-backend-cpp-replay-plan.md)。

## 导出和构建

从仓库根目录执行。先将以下变量设为本批实际冻结路径：`FROZEN_STAGE`（含 IR、配置、`isla-lib`、`scripts/run.mk`）、`CPP_MODEL_BUILD`（完整 CMake 模型构建目录）、`MODEL_BUILD_MANIFEST`、`SAIL_LIB`（匹配生成器的 Sail runtime 头目录）、`MODEL_CONFIG`（实际模型 JSON）和 `EVIDENCE`（本批证据目录）。所有输出子目录须不存在。

```sh
CPP_REPLAY=agents/float_support_review/tools/unified_backend_cpp_replay

python3 "$CPP_REPLAY/schema.py" \
  --ir "$FROZEN_STAGE/rv64d.ir" \
  --isla-lib "$FROZEN_STAGE/isla-lib" \
  --run-mk "$FROZEN_STAGE/scripts/run.mk" \
  --output "$EVIDENCE/schema" --jobs 2

python3 "$CPP_REPLAY/build.py" \
  --build-dir "$CPP_MODEL_BUILD" \
  --schema "$EVIDENCE/schema/instruction-schema.json" \
  --schema-producer-manifest "$EVIDENCE/schema/schema-producer-manifest.json" \
  --model-build-manifest "$MODEL_BUILD_MANIFEST" \
  --sail-lib "$SAIL_LIB" --config "$MODEL_CONFIG" \
  --isla-config "$FROZEN_STAGE/configs/riscv64_difftest_fd.toml" \
  --output "$EVIDENCE/cpp"
```

`schema.py` 用 GNU make 展开实际集合，用冻结 Isla parser、`IRTypeInfo` 和 `Symtab` 导出类型、tuple 顺序和 enum 成员。Cargo 使用既有 replay 的模板与 lock；可用 `--cargo-target-dir` 复用独立编译缓存。若本机 Z3 不在默认链接路径，设置实际构建需要的 `RUSTFLAGS`；清单记录该变量。输入文件在导出前后核哈希，已有输出不会覆盖。

`prepare.py` 把 schema 与实际生成头逐项对齐，只接受已经检查的无资源指令 payload，生成所有叶字段的 AST visitor 及完整状态 codec。`build.py` 读取实际 `CMakeCache.txt`、`riscv_model.dir/flags.make` 和 emulator `link.txt`，沿用模型的源码目录、编译器、include、public 宏及四个链接库；因此兼容独立构建目录、JSONCons 缓存和系统 GMP，并保持 SoftFloat TLS ABI 一致。当前消费 Unix Makefiles 生成器，参数或依赖闭包变化会失败并要求复核。编译器依赖文件另绑定实际读取的头文件。清单保存头、源、库、配置、schema producer、工具源码、runner 和初始化合同的哈希。P1 模型应显式保留 `ext_decode`、`execute`。

历史模型诊断可用 `--historical` 替代 `--model-build-manifest`；结果明确标为 `historical-harness-only`。它不能证明 P1 同源兼容。

`initialization.py` 另生成 `effective-replay-config.json` 和逐键来源清单，在任何 `model_init` 前对齐 TOML 实际覆写的八项 top-level let：dirty update、misaligned access、CLINT base/size、instructions per tick、writable misa/fiom、PMP count。原 JSON 保留不改；其它配置项完全保留，包括 `pmp.usable_count`。当前 P1 只有 misaligned、tick、PMP count 三项实际变化。模型初始化后逐项读取八个实际字段并核对，在 decoder 后再次核不变；不直接写 let 字段。这个对齐步骤本身不等于完整初始化兼容性证明。

## 批量运行

```sh
python3 "$CPP_REPLAY/run.py" \
  --cpp-manifest "$EVIDENCE/cpp/build-manifest.json" \
  --init "$EVIDENCE/cpp/cpp-init-contract.json" \
  --runner "$EVIDENCE/cpp/runner" \
  --solve-manifest "$SOLVE_MANIFEST" \
  --reviewed-illegal "$REVIEWED_ILLEGAL" \
  --aux-initialization "$AUX_INITIALIZATION" \
  --stateen-initialization "$STATEEN_INITIALIZATION" \
  --jobs 2 --timeout 120 --output "$EVIDENCE/replay"
```

`--reviewed-illegal`、`--aux-initialization`、`--stateen-initialization` 均可省略。第一个复用既有逐条非法寄存器重叠审核；后两个只能使用绑定本批 IR/config 的真实 Isla 初始化提取，分别比较 `mseccfg/menvcfg/senvcfg` 和 12 项 `h/m/sstateen0..3` 的实际值。辅助 CSR 均不赋猜测值；位宽从真实 IR schema 导出，P1 的 `sstateen` 为 32 位，`h/mstateen` 为 64 位。

独立定向输入可用 `--cases CASES_JSON` 替代 `--solve-manifest`，此时没有 solve 输入审计。每项必须有唯一 `(run-id, clause, case-id)`、物理 32 位 word、requested/decoded AST、entry-domain、允许的 ret，以及各恰好 102 项的 pre/post。派生 `expected-decoded-normalized` 始终由协调器从原始 AST 重算。

输出包含 `submitted-cases.json`、各 worker 输入/JSONL/stdout/stderr、完整 `results.json` 和 `summary.json`。`initial_lets_match` 单列八项配置实际回读，`aux_initial_values_match` 单列三个隐藏 CSR，`stateen_initial_values_match` 单列 12 项 stateen。`--solve-manifest` 另保存 `input-audit.json`，分别报告 runner、assembly、trace 审计；非编码终态仍须有可审核的物理 decoder 负例，否则列入 `negative-gaps`。

## worker 合同

- 每个 case 都新建模型，按 `model_init → TOML fixed defaults → 102 项 witness → 全量回读 → ext_decode → execute → model_fini` 执行；不 reset/boot，不经有副作用的寄存器写接口。
- 128 位寄存器完整导入 GMP，保留高半部和全部非活动位。decoder 前后比较 102 项、所有固定环境字段、八项初始化 let 及 15 项辅助 CSR。
- experimental extensions、print、RVFI 均明确关闭。execute 的寄存器写 callback 只记事件；decoder 中这类 callback，以及任何 fetch/内存/PTW/reservation/PC/trap/终端 callback 均失败。
- 只有完整实际 AST 一致且 constructor 在白名单内才执行。ret 只接受带 unit payload 的 `Retire_Success` 或 `Illegal_Instruction`。JSONL 每项 flush；Sail 异常先写当前失败，再退出 worker，避免 `model_fini` 吞掉结果。
- `--jobs` 启动独立进程；同一 worker 顺序处理多项，不跨线程共享模型或 GMP scratch。崩溃、超时及截断 JSONL 保留已完成行，未返回 ID 记为 `worker-missing-result`。重复 ID、非本 worker 的 ID 及残缺观察值均记协议错误，仍落盘全部提交 ID；重复或无效结果标为 `worker-invalid-result`。

`concrete-match` 表示这一次具体模型执行的 AST/ret/post 一致。协调器独立再比较一次；全部输入具体匹配且 worker 均正常退出才返回 0。`run.py` 单独运行不会消费完整初始化独审或 Isla 观察唯一性证明，因此其 `initialization_compatible`、`aux_observation_evidence`、`cpp_replay_complete`、`whole77_complete` 固定为 false。下述 `pair_history.py` 在绑定额外证据后另行报告限定范围的配对验收。

## 全量历史输入的新版本配对

`prepare_history.py` 接受显式指定及固定哈希的旧 `replay-aggregate-final.json`，验证三份 wave 的输入绑定、401 项非法操作数审核及真实 encoder 生成的 24 个负例；完整导出 18,477 gen、83 直接负例及 24 派生负例。每条保存原身份和来源哈希，只更换新运行标识，word、AST、pre/post、ret 均保留。当前按 1,024 条分成 19 片；使用 `--help` 查看必需路径参数。旧 PASS 不会写作新结果。

`pair_history.py` 消费该种子清单，并要求绑定实际 IR、TOML、CPP 构建及初始化合同的独立审查证书。每片先运行新冻结 Isla replay，复用现有完整结果和 decoder 纯读证书校验，再运行相同输入的 C++ replay。每条 Isla 执行仍须证明残余辅助状态对完整观察无影响；CPP 只提供具体观察。脚本保存冻结工具、命令、退出码、逐片报告和总汇总，任何不匹配、缺失或版本漂移均失败。默认 4 个独立 worker，不跨线程共享模型。

配对汇总的 `historical-input-full-pair-pass` 只描述这份明确历史输入集在新版本上的回归结果，`initialization-compatible-scoped` 继承受审范围。新官方 solve 产物、未自然完成的 27 个 clause 和源码分支闭合仍需各自验收，`whole77-complete` 始终为 false。

## 新官方增量输入

只消费运行 owner 已冻结、退出码均为 0 的 target/wave manifest。`prepare_official.py` 接受其明确哈希，复用既有 source/model/IR/config、完整 trace、102 状态和汇编 word 审计，按原身份完整导出 gen 及可由同 payload 的真实 gen word 构造的 decoder 负例：

```sh
python3 "$CPP_REPLAY/prepare_official.py" "$FROZEN_WAVE_MANIFEST" \
  --manifest-sha256 "$FROZEN_WAVE_SHA256" --output "$EVIDENCE/official-input"
```

可传 `--reviewed-illegal` 使用逐项非法操作数证据。导出不改变 gen 语义，负例始终保留原不可编码终态的 pre；每个 ID 恰好出现一次。若缺真实 word，保留已核输入与 `negative-gaps.json`，退出 2 且 `input-queue-complete=false`，须按真实 encoder 合同补齐后才能签整份输出完成。另一仍运行的目标和缺 JSON 的超时目标均不进入当前队列。导出的 `all-cases.json` 可交同版冻结 Isla replay 和本工具 `run.py --cases`；最终还须汇总同版辅助观察证明，不能仅凭 CPP 的退出 0 验收。

存在 word 缺口时，复用 `solve_replay/negative_words.py` 导出原 payload，并用 `prepare_negative_encoder.py` 从同版冻结 replay 派生真实 encoder。辅助编码上下文取同 clause 的完整合法 gen；编码后核对真实译码 AST 与原 payload 一致。`complete_official.py` 消费编码结果、正常退出记录、构建来源及 encoder/decoder 两份纯读证书，逐项复核原 collector 和合法辅助上下文，把原 nonenc pre 同时放回负例 pre/post。该工具输出新目录，不改初版缺口记录；必须精确关闭全部缺口。必需参数见 `--help`。

`pair_official.py` 接受完整 `input-manifest.json` 及其固定哈希，绑定同版 IR/TOML、两个冻结 runner、构建来源及初始化独审。每个 wave 使用 1 个 Isla worker，结束后再运行 1 个 CPP worker，保存完整命令、退出码、AST/ret/102post、Isla 观察唯一性和纯读证书、CPP 的实际 8 let/15 aux 读值，并对 ID 与来源漂移作最终检查。`paired-summary.json` 中 `official-completed-wave-pair-pass` 仅代表该 wave 的完整输出；`whole77-complete` 与 `source-branch-closed` 始终为 false。

新增工具的守恒测试分别为 `test_official.py`、`test_complete_official.py`、`test_pair_official.py`；缺输入、状态改变、未关闭负例、辅助上下文改变、真实 AST 不同、IR 不同及文件漂移均须失败。

## 异常状态观察器与旧纯读证书勘误

旧 `isla-replay-decoder-purity-v1` 只统计 IR 显式 register/let，漏掉 executor frame 注入的 `current_exception`、`have_exception`、`throw_location`。完整 decoder/encoder 闭包存在异常 helper 写入，旧 `global-writes=0` 不能解释为完整闭包零写。旧逐条 AST/ret/102post 数值事实保留；正常返回域的连续执行验收另依同 IR/config 的完整 CFG、未写路径与未读未初始化异常槽独立证明。完整闭包纯读仍为 FAIL。

新冻结 replay 使用独立 runtime 快照，增加读取既有完整 ITRACE 的只读 getter，并启用 `itrace`。每个实际阶段从真正初始 frame 读取三项 typed 值，核完整指令路径的写点、局部遮蔽、延迟初始化读、间接写、特殊调用和经独审的 variadic/配置 reset 身份；记录初末值、沿途写数、完整指令数及带调用上下文的哈希。写后恢复也失败。每个阶段结束即释放完整 trace，只保留该阶段的审计结果。

旧 trace 快照的 getter 返回 slice；共享 trace 快照的 getter 只收集完整记录的引用，runner 仅相应借用迭代。新共享 trace 观察器在对应 solve stage 的隔离副本根 package 中添加 bin，沿用根 `Cargo.lock`、release profile 和相同 features，以 `cargo --locked` 构建；记录解析依赖闭包及实际编译 fingerprint、生成 parser 和 Z3 身份。独立 runner 的锁即使使用相同版本声明，也可能解析出不同依赖，不能据此签 runtime 同版。CLI 仍为 `runner IR CONFIG CASES_JSON RESULTS_JSON`；每次证书绑定实际传入的 IR、配置、binary 和 source。当前共享快照的独审桥限定受测原始文本 IR，不覆盖 `.irx` 缓存的版本身份。既有回归结论保留其原始 runtime 版本边界。

`observer_audit.py` 仅接受 `isla-replay-phase-effects-v2` 及逐阶段观察，不把旧证书视为新观察器证明。`observer_pair.py` 按固定哈希的三组计划，使用一个 worker 完整分片重跑 Isla 和 CPP，逐 ID 分别核对旧、新观察与原输入，并检查实际初始化。每片保存原输入/旧结果、新命令/退出码/RSS/结果/证书，整组及总索引保留失败和缺失；分片不改变输入数量或状态。`full-closure-pure`、`whole77-complete` 和 `source-branch-closed` 均为 false。新工具测试见 `test_observer_audit.py`、`test_observer_pair.py`。

经明确交接清单分给多个独立进程时，`observer_merge.py` 以原计划完整输入为权威，保留每片原编号、实际输出目录与原始报告，检查分区互斥且无遗漏，直接比较旧新完整结果（仅排除耗时和新增观察器字段；路径按多重集比较）。同时逐条重核 CPP 原始 JSONL、8 项 let、15 项 aux 和实际提交输入。`--handoff`、`--handoff-sha256`、`--group`、`--output` 指定被冻结的交接及新的汇总目录；不改原日志或原执行命令。遗漏、重复、同 ID 字段变化和观察多重集变化的测试见 `test_observer_merge.py`。

新官方输出使用 `official_observer.py` 为既有 `pair_official.py` 显式接入 v2 证书和逐阶段观察校验，配置 reset 白名单来自实际 TOML；调用结束恢复原接口。负例仍复用既有 `complete_official.derive`，同版真实 encoder 的每个成功编码和译码阶段另由 `validate_encoder_observations` 检查，辅助编码输入不混入官方终态计数。冻结入口脚本及补充索引须同时绑定该适配器、原配对工具、实际 runtime／依赖锁与独审桥。缺阶段、沿途写及误用旧 v1 证书的测试见 `test_official_observer.py`。

## 控制与历史证据

以下命令使用本目录保留的历史高半部 fixture，只验证 harness：

```sh
python3 "$CPP_REPLAY/smoke.py" \
  --runner "$EVIDENCE/cpp/runner" \
  --init "$EVIDENCE/cpp/cpp-init-contract.json" \
  --case "$CPP_REPLAY/fixtures/high-half-historical.json" \
  --output "$EVIDENCE/smoke"
```

该 fixture 来自既有[高半部 fixture](../solve_replay/fixtures/replay-vector-high-half.json)，仅把 AST tuple 键修订为真实 schema 的单次 zdecode 协议（保留 `%enum zfvvfunct6`），数值与 word 不变；不是 P1 同版本重生成结果。smoke 包含 3 个正例、13 个负例，以及 A→B→A 隔离检查。负例覆盖 post 的 fcsr/mstatus/FPR/VPR 高半部、AST 字段、word、ret、错误位宽、缺字段、额外字段、非法 enum 和溢出。

构建时 `--test-control decoder_write|decoder_aux_write|forbidden_callback|sail_exception|initial_let_write` 可生成单独的故障注入 runner；必须使用新输出目录。带控制宏的二进制只用于错误路径验证。

协调器的协议故障测试用 `python3 -m unittest discover -s "$CPP_REPLAY" -p test_orchestration.py -v` 运行。这些测试替换 worker 启动，验证重复/孤儿 ID、残缺 path、截断末行和无观察值的假成功都保留失败记录；不执行模型。

2026-09-27 历史模型结果：所选 50 clause 的 72 条执行全部具体匹配；16 项 smoke 控制均符合预期；四种故障注入均被检出，异常 worker 保留当前失败并补齐剩余 missing ID。这组测试使用旧 C++ 模型和 1dcc 输入，仅为工具诊断。P1 结果及 77 项全量验收须另行建立，不能复用上述结论。

2026-09-27 P1 新结果：IR `348147`、FD TOML `20851` 和 `cpp-r03` 通过独立初始化范围审查；全部 18,584 条历史输入在两个新后端逐条重新配对通过（18,477 gen、83 直接负例、24 派生负例，50 个自然完成 clause）。19 片、4 个流水 worker 实测端到端 201.601 秒；每片 CPP 使用 1 个进程，最多 4 个 CPP 进程。另有新版本 16 项正负控制通过。汇总见 ignored `isla/target/float-solve-evidence/unified-backend-cpp-replay/p1-348147-20260927/historical-full-paired/summary.json`，SHA-256 `4c5d1995b7ed5dedb543d59ee0d0824cb06c9b1cb1ebedfa08064fcf3bcabcb5`。这不是新官方 77 项 solve 完成或源码分支闭合。

随后 V4＋AMO 候选 IR `56cc69` 使用新 schema、实际 CPP 构建、重新编译的冻结 Isla replay 和新初始化提取完成复验：定向 72＋高半部 1 条、16 项控制及 5 项真实故障注入符合预期；全量 18,584 条再次逐条配对通过，19 片、4 worker 耗时 204.427 秒。新汇总为 ignored `isla/target/float-solve-evidence/unified-backend-cpp-replay/v4-amo-56cc69-20260927/historical-full-paired/summary.json`，SHA-256 `cad2f88a2114c8e7131d6cd9c0014650b4683b7f31744546e745d69f763e7b0a`。运行前已绑定新完整 IR 接线及初始化范围审查；generation 记录从初版到正式版仅变更 runtime 清单引用，有独立显式桥接，初版和旧结果均保留。此结果同样只覆盖指定历史输入集。
