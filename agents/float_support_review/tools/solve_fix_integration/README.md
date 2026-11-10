# 定向 runner 与覆盖证据集成

三类 runner 执行成功、执行拒绝、译码拒绝用例。当前入口为 **decode-first 定向验证**；真实 word 经过 decode、适用时 reencode 和 execute，不能据此声明官方 encode-first 的所有路径已经完成。

## 构建和运行

`RUNTIME_STAGE/isla` 必须是独立冻结的完整 Isla 源码，`source-manifest.json` 必须逐文件绑定它。构建器拒绝文件哈希漂移，也拒绝未经重新审定的 `src/isarch/target.rs`。运行器必需 tracetool，固定使用 `assertions_to_jumps`、公开 `install_solve_wrapper`、Optimistic 和 `model_init=true`。

```sh
python3 agents/float_support_review/tools/solve_fix_integration/build_runners.py \
  --isla-root "$RUNTIME_STAGE/isla" --isla-lib "$RUNTIME_STAGE/isla/isla-lib" \
  --runtime-manifest "$RUNTIME_STAGE/source-manifest.json" \
  --z3-prefix "$Z3_PREFIX" --out "$RUNNER_STAGE"

python3 agents/float_support_review/tools/solve_fix_integration/run_suites.py \
  --repo . --manifest "$INPUT_STAGE/suites.json" \
  --ir "$MODEL_STAGE/ir/rv64d_final.ir" --config "$INPUT_STAGE/config.toml" \
  --runtime-manifest "$RUNTIME_STAGE/source-manifest.json" \
  --success "$RUNNER_STAGE/target/debug/solve-fix-success" \
  --illegal "$RUNNER_STAGE/target/debug/solve-fix-execute-illegal" \
  --decode "$RUNNER_STAGE/target/debug/solve-fix-decode-illegal" \
  --out "$RESULT_STAGE" --trace --timeout 90
```

每次使用新的输出目录。各配置分别运行；组内声明的配置哈希必须等于实际参数。默认 MISA、合法 alternate MISA 和 raw 非 WARL 诊断分开，当前 canonical runner 不接受 raw 输入。

`state_domain` 只表示 MISA 域，`configuration_domain` 另将配置与同一 runtime 清单中的 `configs/riscv64_difftest_fd.toml` 比较。关闭 extra ops、VPR/FPR/GPR 快速访问等对照配置即使保持默认 MISA，也属于独立配置义务，不能计作官方默认配置命中。

## 实际入口域与结果证明

case 先显式赋值到真实初始化得到的寄存器帧。独立求解器调用公共 `RV64::setup_pre_state` 建立完整 R1；保留其符号寄存器和约束，对帧中所有已具体初始化的 Target 寄存器逐字段加等式。`cur_privilege/mstatus/vtype/vl` 必须来自 case 的显式具体值，不能从 model 补值。SAT 检查失败即拒绝。当前审定 Target 源码的 R1 约束只依赖这四项；源码变化后构建器要求重审。

特权态按 Sail 的五个枚举转换，实际是否合法仍由公共 R1 与受测 IR 的 S/U/H 能力探测决定。当前冻结模型支持 Machine、Supervisor、User，H 关闭时 VirtualSupervisor、VirtualUser 必须在 R1 检查处被拒绝。旧版仅接受 Machine 的 runner 及其结果保留原二进制绑定；扩展后的 runner 单独构建并验证 User/Supervisor 增量，不能把旧证据重标为覆盖三种特权态。

`misa` 不属于 Target 的 arbitrary 寄存器列表，case 的值必须逐位等于实际配置初始化值。已审定配置为默认 `0x800000000034112f`、Voff `0x800000000014112f`、FDVoff `0x8000000000141107`、DVoff `0x8000000000141127`。其它非 Target 初态覆盖也须重新审定。机器能力与 XLEN/VLEN/ELEN 使用受测 IR 的实际值。

每个 SAT callback 都保存终态身份；返回值与其具化值的差异必须 UNSAT，观察状态与独立预期的差异也必须 UNSAT。译码拒绝允许实际一条或多条路径，要求所有 callback 都拒绝、没有 encode/execute 路径、终态序号连续且 ID 唯一。不会用历史固定路径数替代守恒检查。

decode、encode 和 execute 分别从同一 case 初态启动。跨 phase 使用具化返回值，除上述唯一性证明外，还需要同 IR、runtime 和配置下 `zext_decode` 与 `zencdec_forwards` 的完整纯读调用闭包证书，证明前两个 phase 不改写后续所需状态。证书的无写入、无未知调用结论属于静态前提；它不能代替本 runner 的实际 trace、终态守恒、错误拒绝或未采样证明。配置改变时须重新绑定该前提，不能仅重用默认配置标签。

**2026-09-27 修订：** 上段的完整纯读要求保留为原审计口径；当前 `56cc69` 的两个完整闭包均含 12 处隐式异常槽写入，完整纯读结论为 FAIL。现行[正常返回独审](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/independent-phase-purity-review/certificate.json)仅在绑定 IR/runtime、新入口 `have_exception=false`、无隐式槽覆盖或 shadow、无函数假设替换且根通过 `End` 正常返回时证明无异常槽写入。消费实际结果还须核对非 Poison、正确 Ctor/Bits 类型及实际入口；失败和 `Arbitrary` 路径不能由该条件证明许可。各配置与 caller 仍分别消费，官方 encode-first 观察另列。

每组输出包含结果 JSON、itrace、`.trace-map.json` 和 `.init.json`。初始化侧车记录真实寄存器值或未初始化状态、实际 lets 及其哈希、IR/config/binary/runtime 哈希和 R1 合同。summary 逐组保存真实 argv 和侧车哈希。消费者还须核对 trace 与台账、全 runtime Jump 目录、源码极性和调用域；仅结果通过不代表源码分支闭合。

## 2026-09-26 接续工具验证

`isla-directed-r1-review-20260926` 保存 c5 IR 和 runtime manifest `6e00edd8…` 上的入口验证：默认 scalar 与合法 alternate decode 各一例被接受；VL 越界、非 canonical vill、保留 MPP、错误 SXL、MISA 与配置不符五例被拒绝。相同非 canonical vill 输入被旧 runner 接受的红例也原样保留。它们只验证这一阶段的 runner 合同，新模型及新 runtime 冻结后须重建。

`isla-directed-r1-bound-smoke-20260926` 随后以同 c5/runtime 验证三种新 runner 和实际侧车：BF16 成功2条、执行拒绝1条、默认译码拒绝1条、合法 FDVoff 译码拒绝1条均通过。默认 summary SHA 为 `7606cb45b0f99dc081722660615a6d43d71a6f87a5f2133dae2a6a8fc2e79139`，FDVoff 为 `4236f1551f4b56a47dc4bd72f8ab4f05ad0d712fc7fe6223c4c9745825f986f8`。这是新入口协议的阶段结果，未把 c5 标签改成最终模型。

`audit_global_sites.py` 将多个目录与同一冻结源码绑定，逐项核 SHA、UTF-8 半开 token 范围、字段顺序和 site ID，并拒绝同一物理 token 采用不同 kind。它输出的是词法候选身份校验，不产生可达分母或动态覆盖结论。共享 helper 的义务仍按 clause、entry/config、site 和 arm 单列；共享身份不消除调用前提。

所有 trace 哈希按 1 MiB 块计算。三族消费各自定向包，复用流式 trace parser；官方整批的终态验证也使用流式入口，避免把巨大 itrace 整份读入内存。

## 2026-09-27 冻结 1dcc 增量汇总

[累计结果索引 v2](../../../../isla/target/float-support-review/final-coverage/integration/result-index-v2.json)（SHA `4df70ab8cbabeaa4e08aafcd94f9190c124640378865a27ffa1b83de88241b85`）保留原 9152 基线及各增量的独立 summary、配置、runner、结果、初始化与终态台账绑定。原 v1 索引和最小 63 条证据未改写。

| 指令族 | 实际 case/config 结果 | 终态 |
| --- | ---: | ---: |
| scalar | 5413 | 15305 |
| vector | 3206 | 9332 |
| BF16 | 942 | 2754 |
| 合计 | 9561 | 27391 |

全部列定结果通过；Machine 为 9285 条，User、Supervisor 各 138 条。另有最小 63 条和新版三类 runner 的 Machine 协议回归 3 条，未重复计入此表。生成器重新核对结果、台账、初始化哈希、实际 R1 与特权枚举，拒绝重复的 family/config/case ID；完整 itrace 的 Jump 和上下文审计由三族各自保存，本索引不将结果计数解释为源码分支分母。

新版 runner 支持合法 User/Supervisor 的增量；两个虚拟态在三类 runner 中均由当前公共 R1 以 Unsat 拒绝，未知枚举另有解析拒绝。七个预期拒绝记录在[特权负控汇总](../../../../isla/target/float-support-review/final-coverage/integration/privilege-rejections/summary.json)。这些结论绑定冻结 IR `1dcc8081…` 和 runtime 清单 `28fb65ee…`，不转记到后续生成的 IR。当前 `source_branch_closed=false`，官方 encode-first 全 77 项的验收仍独立记录。

[累计结果索引 v3](../../../../isla/target/float-support-review/final-coverage/integration/result-index-v3.json)（SHA `cc93ea74554ede872bb505b05f59518d06845c47a218cc34650485e83f43bc89`）随后加入 vector 的 estimate 21 条与 narrow FS-off 1 条。同一旧 IR 的累计数为 scalar 5413/15305、vector 3228/9396、BF16 942/2754，合计 **9583 条输入、27455 个终态**；均有各族完整 trace 审计。v2 保留其原适用范围。

## 2026-09-27 新 P1 IR 的同输入复验

新 IR `348147f8…` 重新运行上述 9583 条输入，28 个运行任务、87 个组全部通过，实际终态仍为 27455；Machine 9307 条，User、Supervisor 各 138 条。新最小 63 条另列通过。命令、输入、配置和真实结果见[运行汇总](../../../../isla/target/float-support-review/final-coverage/integration/p1-348147/full-summary.json)及[新结果索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-348147/result-index.json)。组预算为原基线 900 秒、增量 270 秒，不是官方 encode-first 的限时配置。

新模型原始生成记录继续绑定 v6 清单 `749c3c5b…`；v7 的 166 个 Sail 模型文件与 v6 逐件相同。重封候选清单为 `1890f0a1…`，Isla runtime 仍为原冻结 `28fb65ee…`。`verify_source_bridge.py` 核对原生成记录、工具链、IR 字节、166 个模型文件、125 个 Sail 库文件与 510 个 runtime 文件。消费时，`verify_source_snapshot` 通过显式 `source_bridge` 参数重新执行该验证器，比较完整报告、输入路径和生产者 SHA；不能仅凭证明文件中的 PASS 字段接受。

scalar 和 vector 的 `audit_suite.py`、scalar 的 `trace_binding.py` 支持 `--source-bridge "$SOURCE_BRIDGE"`。同时显式提供候选 `--snapshot-manifest`、原信息保留的 `--generation` 和实际 `--runtime-manifest`。BF16 在调度层先运行同一来源验证 API，再逐组消费完整 trace。缺少桥接参数时仍使用既有严格绑定规则。

八个配置均重新提取实际 runtime 目录：2054 个函数、378173 条指令、25711 个 Jump。三族全量已完成新版实际入口、完整 Jump、终态和来源审计：scalar 5413/15305、vector 3228/9396、BF16 942/2754。[总严格索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-348147/strict-audit-index.json)重新核对了 87 份逐组审计产物 SHA、输入分组和终态计数守恒；先前结果索引中的“strict 进行中”保留为当时记录。各族入口为 [scalar 严格汇总](../../../../isla/target/float-support-review/final-coverage/integration/p1-348147/scalar/strict-audit-summary.json)、[vector 严格索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-348147/vector/strict-audit-index.json)和 [BF16 严格汇总](../../../../isla/target/float-support-review/final-coverage/integration/p1-348147/bf16/strict-summary.json)。新[词法身份清单](../../../../isla/target/float-support-review/final-coverage/integration/p1-348147/global-site-identity.json)核定 1259 个唯一候选 site、10 个跨目录共享 site；该清单只证明源码 token 身份，不给出可达分母。旧版 arm、静态排除及配置等价证明没有自动迁移，`source_branch_closed=false`。

同版初始化额外提取了 mseccfg/menvcfg/senvcfg 和 12 个 stateen CSR，均为实际具体零值且无 TOML defaults 覆盖；其中 hstateen/mstateen 为 64 位，sstateen 为 32 位。见[三项初始化](../../../../isla/target/float-support-review/final-coverage/integration/p1-initialization-348147/extraction-report.json)与[stateen 初始化](../../../../isla/target/float-support-review/final-coverage/integration/p1-stateen-initialization-348147/extraction-report.json)。这些值来自新 IR 的实际 `model_init`，适用版本由报告逐项限定。

## 2026-09-27 V4 与 AMO 合批 IR 复验

新 IR `56cc69a4…` 通过完整 IR 的 V4/AMO 组件独审后，重新运行最小 63 例及上述 9583 例；三族实际结果和完整 trace 全部通过，终态为 27455。[结果索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/result-index.json)保留全部输入和特权分组；[总严格索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/strict-audit-index.json)（SHA `283b4accc810eb7132aa360a476a5bccfa875998367e7331b4869d0b1b0d5b52`）重核 87 份逐组审计、来源、计数及运行记录。每套实际目录为 2058 个函数、377980 条指令、25676 个 Jump。预算与 decode-first 入口仍同上一批。

此次实际构建源为 931 个文件，候选模型清单为 `fdf105d1…`，运行时继续使用逐文件相同的 `28fb65ee…`。新 `verify_source_bridge_v3.py` 核真实构建、候选 IR 副本、166 个模型文件、125 个 Sail 库文件、510 个 runtime 文件及工具链产物；新 `solve_scalar_coverage/runtime_binding_v3.py` 显式重执行四路径桥接并核当前 source catalog。旧来源验证器及旧 `runtime_binding.py` 保留字节，供旧证书继续复验。

新[15 项实际初始化报告](../../../../isla/target/float-support-review/final-coverage/integration/p1-initialization-56cc69/extraction-report.json)重新运行 `initialize_architecture`；值均为具体零且无 defaults 覆盖，stateen 宽度同上。提取后生成记录只修正 runtime 身份字段，旧记录逐字冻结，差异由[最终生成绑定](../../../../isla/target/float-support-review/final-coverage/integration/p1-initialization-56cc69/generation-binding-v2.json)精确核对。FD 4 项及 VPR 24 组直接状态检查亦通过，见[direct 汇总](../../../../isla/target/float-solve-evidence/direct-state-p1-56cc69/reports/summary.json)；该检查采用 RV64 E 配置 `8247c8d4…`，与定向整指令的 FD 配置分别记录。

另外运行了 BF16 overlap 3 例、向量 slide 2 例、conversion FS-off 6 例及 num32 8 例，共 19 例、45 终态，均有独立结果和严格 trace 审计，不并入 9583。[单列严格索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/increment-strict-index.json)（SHA `fccc712438833185a2b82f47b35338ffcaca845ab3ba856693991163fa321889`）重新核对四包产物，并排除与主批重复的 family/config/case ID。

num32 输入使用 SEW16、LMUL4、VL0，从新版实际 caller 为两条条件的 70 个方向提供见证；这些方向是 `num_elem <= 16` 的 false 和 `num_elem <= 64` 的 true，输入不要求 `num_elem=64`。该子集已通过独审并精确消费到[新版本账本](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/new-ir-observed-num32-70-ledger.json)，限定当前 FD 配置、Machine 和 35 个列定 root。旧 `1dcc` 前沿不回填。slide/FS 与 BF overlap 的源码方向独审分别记录，FS/BF 这些见证只证明短路 LHS，不充作 RHS 返回值证据。

新版[词法身份清单](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/global-site-identity.json)为 1252 个唯一 site、10 个共享 site。V4 中消失的 7 个源 site、14 个 arm 保留为 `not_lowered`，不记动态命中。完整 caller/config/phase/privilege、正常 RHS 与异常义务仍需分别闭合，当前 `source_branch_closed=false`。

[三族合同导航 v3](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v3.json)保存 34 个分版本入口，明确候选、独审证书和已消费账本的区别，并重核上一版及其原 22 个产物未漂移。它只导航各自合同的分母，不将其中计数求和，也不把旧版静态排除或动态观察自动迁入新版本。

随后按真实 scalar 数值调用闭包发现原目录未收录的四个 Sail 库文件、七个短路因子，另建候选及四配置 caller 义务，见[补充库存](../solve_scalar_numeric_helpers/README.md)。[全局词法身份 v2](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/global-site-identity-v2.json)追加它们后为 1259 个唯一候选、10 个共享候选；原 1252 时点的文件保持原样，新数量不代表源码分支闭合。

### 后续有限合同消费

[三族合同导航 v5](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v5.json)（SHA `5059f311b4c1674e8bff20d7ed78fbb06cca789312054857509cf0a2aa5abbd2`）保留前四版原字节，重核并导航 71 个版本限定入口。新接入结果包括：

- scalar 完整调用库存与七个库因子的 63 个精确 LHS；34 个源码点在四配置的限定消退合同；正常返回字段、runner 入口、phase 状态及 predicate 合同。
- vector 两项当前归约 Err 的正常返回域排除；默认仍为 87 个源码语义观察、2 个静态排除，结构执行与源码语义待证继续分层。
- BF16 正常 RHS 的 139 个实际见证、23 个 caller 域排除、24 个正常 phase 条件排除；八个当前 V4 callee-instance 的值集成合同。旧 40 个控制键仅迁移到这八个实际合同，未增加新的分支或动态命中。

scalar 的 174 项新入口组合只适用定向 audit 的正常 phase：170 项依赖成功 decode 后再进入 encode，另外 4 项为正常 guard 条件恒空。官方 wrapper 先 encode，因此官方 170 项仍为 OPEN，源码方向移除为 0。完整 decoder/encoder 闭包纯读 FAIL 保留。default 三个 FCLASS 库方向的互斥候选及修订后的 vector flags 候选在此时点仍待独审消费，`source_branch_closed=false`。

[后续导航 v6](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v6.json)（SHA `33f29216ba12b04cac0002c2e20d07b36512d50c7bde33ea09942f35adcf8a12`）重核并导航 83 个入口，补入下列结果，v5 保留其历史时点：

- vector flags 已正式消费六配置 24059 项限定静态排除；default 为 87 个源码语义观察、4465 个 flag 排除、2 个 Err 排除、4877 个结构执行待源码语义、74 个 predicate 待核、4320 个域或见证待证。
- scalar 三个 default/Machine FCLASS 方向已消费为精确 caller 域排除；库因子总体为 63 个实际 LHS 观察、3 个排除、102 个待证，RHS 未闭合。三种 alternate 配置的 336 个 mapping 配置对、1347 个字段配置对也已消费局部正常返回及字段语义。
- BF8 账本 v2 修复历史组件引用活动模型路径的问题：15 个 locator 显式重定位到冻结同 SHA 字节，134 个验证引用合并为 132 个物理文件；八个合同、40 个历史链接及全部语义前提不变。

官方既有 wave 的 encode 拒绝 trace 提供 53 个方向候选，完整 D FMA 代表再提供 8 个不重叠方向候选；联合 61 个仍待独审，不能直接从官方 170 项中扣除。向量 typed/num 的 366 个调用合同、1318 个排除候选也仍待独审。此次均复用已有输入和 trace，没有新增模型运行。

[后续导航 v7](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v7.json)（SHA `c52564b17b5cc7c4f1661552cb31363ec3cb794c53be7df1e4ba1de0fdec2921`）重核并导航 91 个入口，保留 v6 的历史时点：

- 官方 wave 的 53 个方向及 D FMA 的 8 个方向已分别通过独审，并在[官方并集合同 v2](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/official-encode-observed-union-contract-v2.json)严格消费。精确并集为 **61 个已观察方向、109 个 OPEN**：36 个 guard、24 个 AND 左侧 false 后跳过右侧、1 个 OR 左侧 false 后进入右侧。64 条见证引用对应 37 个自身终态；右侧取值许可、静态排除和新增执行均为 0，未传播定向 audit 的静态排除字段。两次消费分别通过 14 项和 8 项测试。
- 向量 typed/num 的主证书及必需形参／算术附证已联立消费到[账本 v6](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v6/index.json)。default 精确新增 **1318 项限定域排除**，367 个保留方向、其它行及五个备用配置逐项不变；10 个消费负控通过。default 的 13825 项为 87 个源码语义观察、4465 个 flag 排除、2 个 Err 排除、1318 个 typed 域排除、4877 个结构执行待源码语义、74 个 predicate 待核和 3002 个域或见证待证。六配置静态排除总数为 25379，实际输入／终态仍为 3244／9432。

这些合同均绑定原 `56cc69` 及各自明确配置和 caller。全部源码分母、RHS、异常及其它未许可义务仍分别待证，`source_branch_closed=false`；后续模型或 runtime 不能仅替换哈希迁用。

[后续导航 v8](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v8.json)（SHA `74428ceb32f9a2df5d214c1d4506773016c42202d3aac308ed92724de3533c6a`）保留上述各版，重核并导航 108 个入口：

- scalar 四配置 RM/FRM 及 180 个 caller 配置对的局部合同已消费；8640 个输入组合、2160 个异常组合分别保留适用域，静态分支排除许可仍为 0。三个备用配置的九项 FCLASS 条件排除也已消费，库因子现为 63 个观察、12 个条件排除、93 个 pending。
- BF 从原官方 wave 的两条终态另签并消费 4 个自身方向：2 个 guard、同一 FS source site 的两个 caller LHS。与 scalar 的 61 个方向精确交集为空，但所选并集 65 不是 scalar 的 170 项分母，也不是完整 BF 分母。完整 BF source/caller 总账仍继续建立和审查。
- vector 另消费 24 个 `get_num_elem` 局部失败方向排除、45 个数值宽度／索引方向排除，以及 799 个既有 trace 的源码谓词语义许可。现行[账本 v9](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v9/index.json)保留原 87 个观察行，另以独立状态登记 799 项，总源码语义观察为 886；结构待源码语义为 4078、谓词待核为 74、域或见证待证为 2933。六配置静态排除总数 25448，实际 3244 个输入、9432 个终态不变。

本版新增证明及消费均复用既有运行，没有新增模型执行。新 sharedtrace 的 23 个完整官方目标另作来源和 trace 审计，尚未据其预先扣除 scalar 的 109 个 OPEN；新 e6a 的源码身份准备见下节，不能据相同源码键自动迁移证明。

[后续导航 v9](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v9.json)（SHA `4f9aa54cb4e5ed7ed14a87aa027611114a1f1f6dfd8b736f42530a805aa1fed6`）保留 v8 的 108 个完整记录，新增至 121 个入口：

- scalar 新 sharedtrace 的 23 个目标已经独审并[严格消费](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/official-sharedtrace23-observed-contract.json)：新运行时自身为 85 个观察、85 个未观察，包含 56 个 guard、27 个 AND 左侧跳过、2 个 OR 左侧进入；12 项消费测试、17704 个依赖核验通过。旧 61 个见证保持原运行时身份；跨运行时动态并集未授权，两证都未见的 24 个键仅描述源码义务关系。
- BF16 已[消费三配置 caller 表](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/three-config-source-caller-ledger-reviewed-v1.json)的限定审查：516 个实际根、54 个 phase 闭包、28020 个 source/caller 候选行，CPP 70 行单列。default 的既有证据保持，alternate 不借用；完整语义分母继续 OPEN。346 个源码 occurrence 的命名来源分类另为候选，不能据此关闭分支。
- vector 的 `currentlyEnabled` 枚举域新增 1056 个精确排除，已消费到[账本 v10](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v10/index.json)。default 的 13825 项为 886 个源码观察、6910 个限定排除、4078 个结构待语义、74 个 predicate 待核及 1877 个域／见证待证。六配置静态排除 26504，实际 3244 个输入、9432 个终态不变。

e6a 实际目录及三个重新证明的分类候选亦已导航，详见下节及[数值库说明](../solve_scalar_numeric_helpers/README.md)。它们尚待各自独审，没有自动迁移旧结论；当前仍为 `source_branch_closed=false`。

[后续导航 v10](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v10.json)（SHA `decfb567351dc4689ddfaf122d6b40b7ecb17e9ce5ee3d9a2a7ed45e2f0ce2e6`）完整保留上述 121 条记录，新增至 153 个入口：

- e6a 实际 debug 目录与三个 FCLASS 条件方向已各自独审，三个方向已正式消费；旧 56cc 观察和分母没有迁入。
- scalar 四配置 2056 条访问器局部正常路径和 736 个实际 AST Bits5 索引条件前件已消费；完整 caller／RHS／异常仍待证。新增 26 条 decode-first 输入的 41 个自身 LHS 已通过独审，等待严格消费。
- 新 `direct-constructor-execute` 入口针对真实 Foff／Doff 的 FCLASS 源码根补充 24 个唯一输入；v1 compact 历史结果保留，v2 同 24 个输入以完整 trace 重跑成功。52 个自身 LHS 仍待完整 Call/End 独审，入口域不升级为 decode-first 或 official。详见[新入口和失败记录](../solve_scalar_numeric_helpers/README.md#失能-misa-下的直接构造子执行)。
- vector 197 个 getter、969 个寄存器及 1068 个 enabled 源码方向已经严格消费至 v13。default 的 13825 项为 **3120 个源码观察、6910 个限定排除、1844 个结构待语义、74 个 predicate、1877 个域／见证待证**；六配置实际 3244 个输入、9432 个终态未新增。
- BF16 的 346 occurrence 分类已修复旧 v2 漏 `newtype` 的归属错误，并与 runtime 叶、生成枚举、字面量 callback 的有限合同正式消费。原生完整树正在替换候选库存，extern、完整 caller 和物理源码分母仍待审；声明图或命名分类不能算分支覆盖。

导航只索引已冻结的产物及其许可范围，`source_branch_closed=false`。未通过独审或消费的候选继续保留 pending；后续新增证书在下一版另行登记。

[后续导航 v11](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v11.json)（SHA `b00de06cbf60142cbd53b7f282b5a8c8bf93ee953d8ba83df06f6dc536aa4482`）完整保留 v10 的 153 条历史记录，新增至 179 个入口，并分列各自分母：

- scalar alternate41 与 direct52 均已严格消费。选定库表 168 项为 **104 个 decode-first 自身观察、52 个 direct 自身观察、12 个条件排除**；列定入口合计 pending 为 0，但 decode-first 仍有 52 个未观察，完整 caller、RHS、异常和源码分母仍 OPEN。新访问器 6 个直接 F 入口也已消费，联合 22 个入口的 3080 条局部路径不代表完整 caller 闭合。
- vector 主表 v14 的 default 13825 项为 **3293 个源码观察、6910 个限定静态排除、1671 个结构待语义、74 个 predicate、1877 个域／见证待证**。mapping291 则单独消费到补充表：4325 项为 291 个观察、4034 个 pending，主表零增量；RHS 的 5640 项／1880 个 context 保留。实际 3244 个输入、9432 个终态未新增。
- exporter v2 的有限结构独审、旧 1259 个 raw 身份的主证／来源附证／严格消费已导航。旧身份合同明确保留历史 live 输入的三项漂移 FAIL，不能替代完整源码分母或 producer 完整性。
- 三族采用同一个原生依赖提取器重算根应用。BF v4／vector v1 的旧候选漏 `E_ref`，共享 v5 后又发现构造子过滤和 schema 默认分类问题；v11 记录的共享 v6 仍为候选。**v11 冻结后，独审进一步发现 v6 的部分 `references.ast_path` 使用虚拟 role 路径，需按 v7 的真实 `args`／列表索引重新验证**；原产物保留，不签来源身份或完整分母。

原生构造子根只构成组件。完整入口必须分别记录官方 encode-first 的实际 encode 成功像域、audit decode-first 的原始 word 域和直接构造子域，保留有序 matcher／guard／value 求值、目标失败后的后续尝试及最终 ILLEGAL，并保留 encode／execute 的选择和拒绝桥。未经独立域、顺序和可达证明的义务继续 OPEN。

### 完整原生树与旧词法键的来源对应

`native_global_identity.py` 直接遍历冻结 `attempt-006/raw-ast.jsonl` 的 6673 个完整定义，自建结构路径并核文件 hash、UTF-8 byte／行列，不使用尚未独审双射的派生节点索引。`native_global_refinement.py` 再补原生相邻节点之间的关键词／标点关系，保留 v1 原产物。

[跨族 raw 身份候选 v2](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/global-native-token-identity-v2.json) SHA `36ff54ae3ba4618b8e16ab26dabf6b1e94da785455ec5c7b77f336a43f693a0e`将旧 1259 个键全部关联为来源候选：413 个 `&/|` 使用原生 `E_infix` 的 `[IT_token,start_position,end_position]` 三元组，815 个关键词使用原生节点的精确起点，28 个 `when` 使用实际 mapping 与 guard 间隔，3 个 `=` 使用 `currentlyEnabled` 的 pattern 与 body 间隔。等号在这里只表示函数定义分隔符，不授予分支许可。

候选阶段 10 项测试先红后绿，依赖重新核验见[验证记录](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/global-native-token-validation-v1/validation.json)。该阶段尚未独审；1259 只是旧词法库存到 raw 的来源对应。

随后[独立证书](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-global-native-token-identity-review/certificate.json)（SHA `c2e3a645a56595633ff390bc2d6090e1936a2042921f2b7aa2c143e03b39c775`）完整走查 6673 个 raw 定义、6605029 个值和 596024 个位置，逐字段核对 1259 个精确匹配及 271 个包围关系候选。它必须联立[来源附证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-global-native-token-identity-review/provenance-annex.json)：历史 `attempt-006/inputs.json` 的 457 个 live 路径中，`tools/solve_source_ast_catalog/` 的 `plan.md`、`freeze_exporter.py`、`README.md` 三项已漂移，故 live 输入门明确 **FAIL**。既有 `input-recheck457` 映射到冻结副本仍为 457 个 hash 匹配，但不授完整 producer 无漂移或历史 PASS 迁移许可。

`native_global_identity_consumer.py` 联立主证、报告、来源附证、输入索引和全部匹配，重核 641 个依赖，12 项消费测试通过后输出[旧键身份消费 v1](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/global-native-token-identity-reviewed-v1.json)（SHA `7425182026397577d23f5b363a1cd63c925a4298fe8802362c09a4c37112f381`）；[消费验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/global-native-token-consumption-validation-v1/validation.json)保留红绿日志。该合同只签旧 raw 身份，原样保留 live FAIL，`producer_chain_integrity_permission_added=false`。完整 typed 闭包、反向新增节点、宏域、Generated／Hint 和 caller 义务继续建立；未删除旧键，动态观察和静态排除增量均为 0。

### e6a 候选的源码身份准备

`source_identity_transition.py` 只建立两版源码身份变化库存。它逐文件核对两侧 166 个模型文件和 125 个 Sail 库文件，使用现有 `catalog_v2.generate` 重现旧向量目录全部 site 字典，再从新冻结源提取词法候选；源码行匹配仍沿用 `source_migration` 的候选口径，不证明语义或运行时坐标保持。

```sh
python3 agents/float_support_review/tools/solve_fix_integration/source_identity_transition.py \
  --old-snapshot "$OLD_MODEL_STAGE" --new-snapshot "$NEW_MODEL_STAGE" \
  --old-identity "$OLD_EVIDENCE/global-site-identity-v2.json" \
  --old-vector-catalog "$OLD_EVIDENCE/vector/catalog/source-branch-catalog.json" \
  --new-freeze "$NEW_MODEL_STAGE/candidate-freeze.json" \
  --output "$NEW_EVIDENCE/source-identity-transition"
python3 agents/float_support_review/tools/solve_fix_integration/source_identity_macro_domains.py \
  --transition "$NEW_EVIDENCE/source-identity-transition" \
  --old-vector-catalog "$OLD_EVIDENCE/vector/catalog/source-branch-catalog.json" \
  --output "$NEW_EVIDENCE/source-identity-transition/macro-domain-breakdown.json"
```

当前[源码身份报告](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/source-identity-transition/report.json) SHA `cd38c10f7fc510d858e74e4c151ca91670518c26da0cf43d113d73289ec4ce98` 绑定 `56cc69` 与新 IR `e6a3232d…`：只改变 `extensions/V/vext_fp_insts.sail`。原 1259 个词法身份中 784 个 source key 相同，475 个因整个文件 SHA 变化获得新 key 候选；新词法库存为 1255 个，向量部分由 879 变为 875。上述数字均不构成完整可达源码分母。

[宏域补录](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/source-identity-transition/macro-domain-breakdown.json) SHA `2e202f75ef79ad7b46c26a28da93fe4f276c28e2be5037ab8ad6f27b955efd57` 明确列出 FVFTYPE 的 5 个旧 active 源点及 1 个新最终判断源点。旧 active 点在普通后端找到同文候选，不代表 SYMBOLIC 域保持；须联立新组件证明并重提实际 Call/Jump。此时未绑定 e6a runtime sidecar，没有沿旧 PC 迁移，也没有转记任何动态见证、静态排除或正常 RHS／异常许可。

[源码限定复核](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/source-identity-transition/source-only-validation.json)重新检查 597 个绑定文件无漂移，并用上述宏域脚本在独立临时目录重现补录，产物逐字相同。它只验证源码身份与候选生成，不增加运行时或语义许可。

### e6a 实际运行时目录准备

随后用已冻结的 sharedtrace debug 提取器实际读取新 IR，输出[目录准备报告](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/runtime-catalog-preparation-v1/report.json)（SHA `303f874f845f65daf7f94c347d3d4e436b447034e8305da3716e99d1f113fa4b`）。实际侧车 SHA 为 `03a7762e5282c095bb03f8b944357307cd874c3848bb505ba0fbdac0e3bb4c7c`，含 2058 个函数、377970 条指令、25672 个 Jump；入口为 `official-fork`、`model_init=true`、`Optimistic`。

`runtime_catalog_e6a.py` 重新执行 source-v4 并与冻结报告逐字核对，确认两份运行时 manifest 的 517 个源文件逐一相同，再核提取器源树仅有既定 Cargo 入口改动及两个新增文件。提取后重核 1365 个依赖无漂移；[限定验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-e6a323/runtime-catalog-validation-v1/validation.json)保存 6 项先红后绿的身份负控及实际 header／全记录计数检查。

```sh
python3 agents/float_support_review/tools/solve_fix_integration/runtime_catalog_e6a.py \
  --candidate "$NEW_MODEL_STAGE" \
  --catalog-build "$OLD_EVIDENCE/scalar/official-sharedtrace23-candidates/catalog-build" \
  --out "$NEW_EVIDENCE/runtime-catalog-preparation-v1"
```

输出目录必须不存在。此步骤只执行初始化及公共 RV64 域探针，没有执行待测指令。debug 侧车只绑定自身实际 typed 结构与原语别名，不证明 release 的唯一分发。新模型的静态合同仍须重新核 source、caller、SSA 和配置并独审；旧动态观察及静态排除迁移数均为 0，`source_branch_closed=false`。

## 原生类型库存有限证的公共消费

[`native_type_review_consumer.py`](native_type_review_consumer.py) 严格消费[类型独审主证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/independent-native-type-dependencies-review/certificate.json)（SHA `7ecdf0bc3adcf4f05a5fc40cb1db3695f7b0cb767c61aff5e74bf2e72f04b34e`），联立输入索引、producer manifest、两域身份与附件报告及两个实际目标规则附证。

[公共消费产物](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-type-declaration-inventory-reviewed-v1.json) SHA `2bc5e03c20fec2d42b347d455af03588dedbef6e039bca17072f18ef9dc4c4a6` 重新核验 86 个依赖。普通／SYMBOLIC 两域分别绑定 7912／8016 个声明、461615／477560 个引用、12253／12543 个义务及 6372／6410 个 unit 附件。三族复用冻结引用与许可，无须再生成大体积 AST 库存。

每域 `measure_declaration_build_premises` 仅列 11 个 `DEF_measure` 和 2 个 `DEF_loop_measures` 的精确声明 key 与节点 hash。实际 CPP／Isla 规则许可这些声明表达式作为构建前件；同名 helper 或其他运行时调用者仍须核验。配置求值、undefined 实际生成调用和 outcome 实例化桥仍 OPEN，完整源码分母与依赖闭合仍为 false，新增动态观察和运行时分支排除均为 0。历史 live457 的三项漂移 FAIL 原样保留。

[验证记录](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/type-review-consumption-validation-v1/validation.json) 保存 11 项先红后绿测试，覆盖完整分母误升级、measure 漏项／按名扩大、target 混用、附件输入断链和常量库存误当消除等负控。

```sh
python3 agents/float_support_review/tools/solve_fix_integration/native_type_review_consumer.py \
  --review "$OLD_EVIDENCE/source-ast-full/independent-native-type-dependencies-review" \
  --output "$OLD_EVIDENCE/shared-native-type-declaration-inventory-reviewed-v1.json"
```

输出必须不存在；已有冻结产物不原位覆盖。

## Setter 原始赋值来源增量

[`native_lvalue_lowering.py`](native_lvalue_lowering.py) 按冻结编译器 `initial_check.to_ast_lexp` 的 unit／tuple 参数展开及 `type_check.bind_assignment` 的 setter 属性、RHS 追加规则，核 raw `E_assign` 与实际 typed `E_app`。完整赋值位置、setter 属性的 LHS 范围、原名或实际 non-infix overloaded 属性、全部参数位置及次序、unit 返回类型和核心 call 路径均须吻合；多候选或缺字段不授许可。

[三族实际候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/setter-source-lowering-preparation-v2/candidate.json) SHA `04261995864504daf71c1c385a0ac2176163be86125efc0beb29a62e59d0c75f` 重核 665 依赖。scalar 的 106／107、vector 的 11／19、BF16 的 7／15 个原 pending 赋值均有唯一来源对应，去重后为 116／125 个事件。[冻结 manifest](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/setter-source-lowering-preparation-v2/manifest.json) 保存 11 项先红后绿测试及实际应用日志。该候选待独审，只证明来源与调用库存；不转记动态观察、运行时排除或完整源码分母。

首轮实际映射成功，但结束时对历史 live457 的检查遇到已知三个工具文件漂移，故失败停止；[首轮日志](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/setter-source-lowering-preparation-v1/attempt1.log)保留。v2 明确消费已经独审的旧身份合同及既有冻结替换，继续记录 live FAIL 和 `producer_chain_integrity_permission_added=false`，没有把冻结 hash 匹配改写成 producer 完整性证明。

## 配置访问来源增量

[`native_configuration_projection.py`](native_configuration_projection.py) 用原生 raw `E_field` 链重建完整点分配置键及整段位置，与实际 typed 表达式逐一对应。[冻结候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/configuration-source-projection-preparation-v2/candidate.json) SHA `17c852c70a61fc998a5cccf84b4e7ff1ed8c83fd0813c8d3358e6abbad6c44f8` 绑定每域 94 个去重事件；scalar 94／94、vector 92／92、BF16 93／93 均唯一匹配。普通后端保留全部实际 `E_config`；SYMBOLIC 的 90 个字面量及 4 个枚举值与实际配置逐值相等，枚举还联立原生 `TD_enum` 成员。

[冻结 manifest](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/configuration-source-projection-preparation-v2/manifest.json) 保存 9 项先红后绿测试、674 个依赖重核、完整命令及解析后的配置。解析使用 [`native_config_json.ml`](native_config_json.ml) 调用 Sail 相同的 `Yojson.Safe.from_file` 入口，保留原配置中的注释语义。首轮使用 Python 严格 JSON 读取含注释文件而失败的[日志](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/configuration-source-projection-preparation-v1/attempt1.log)保留，v2 明确替换读取步骤，没有解析失败后的静默替代路径。

该包待独审，仅提供完整配置访问来源及已导出值的候选。普通运行时配置、后续调用／分支与实际 IR 对应仍须各自证明；完整源码分母、运行时许可和 producer 完整性均未升级。

### 上述来源候选的正式独审与消费

后续独审已完成，旧候选字节保留。公共消费者只升级已核的来源身份，`actual_call` 中的 callee 语义候选、调用者、IR 对应及完整源码分母继续保留各自状态。

| 来源 | 正式公共产物 | 已核范围 | 消费验证 |
| --- | --- | --- | --- |
| setter | [shared-native-setter-source-identity-reviewed-v1.json](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-setter-source-identity-reviewed-v1.json)（SHA `4342fe34a7bf65feaaaa4fb29e395ffa3f4f204b55c8e306ef9a7914e66f8966`） | 两域 116／125 个准确行，逐原 row／关系／typed 路径及节点 hash 联立 | 704 依赖、8 项先红后绿测试；[验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/setter-review-consumption-validation-v1/validation.json) |
| 局部类型变量 sizeof | [shared-native-sizeof-source-identity-reviewed-v1.json](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-sizeof-source-identity-reviewed-v1.json)（SHA `85f1fce63c3e9ad5d8399ed6fa1acbba6a17276e7db6d7ed439bb45d3dce387a`） | 95／120 个准确 `__size` overload 来源；4 个命名类型 occurrence 原样 pending | 707 依赖；与配置合计 10 项测试及[验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-projection-consumption-validation-v1/validation.json) |
| 配置访问 | [shared-native-configuration-source-identity-reviewed-v1.json](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-configuration-source-identity-reviewed-v1.json)（SHA `99c5cce2564700897a95f15e66864b2f0d26fd82ca84f393b525aa4a454d7105`） | 每域 94 个准确行；普通保留读取，SYMBOLIC 逐实际导出值核对 | 728 依赖；与 sizeof 共用上述验证 |

接口分别为 [`native_setter_review_consumer.py`](native_setter_review_consumer.py) 的 `consume(review_dir)` 及 [`native_source_projection_consumers.py`](native_source_projection_consumers.py) 的 `consume(mode, review_dir)`，后者 `mode` 明确为 `sizeof` 或 `config`。调用会重新核全部依赖，不能将 source 身份许可当作分支极性或动态覆盖。

sizeof 的剩余 named alias 已另建[候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/named-sizeof-source-projection-preparation-v1/candidate.json)（SHA `e074564ae28386f2cbc258e9f1a796a7dedb9b5bdecc3abdd8e3e2832c207155`）：两域各 2 个 global let 分别按真实 `flen → flen_bytes`、`regidx_bit_width` 数值声明链展开，与实际完整 `E_app/E_if/E_constraint/L_num` 形状相等，6 项测试及 667 依赖重核。此包待独审，所有 `NC_id` 条件仍保留；没有提前折叠普通后端配置或签运行时／IR 关系。raw 来源待处理项归零也不代表反向生成控制、完整入口和动态分支分母闭合。

后续[命名 sizeof 独证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/independent-named-sizeof-source-projection-review/review.json) SHA `361a5abd53689269818253c5b2b545ab745ecac47e8519b7c5a51ba06f43e9e1` 已准确核验这 4 条来源及 4 个原 nested `E_if`。[`native_named_sizeof_review_consumer.py`](native_named_sizeof_review_consumer.py) 的 `consume(review_dir)` 联立原始 row、完整表达式、别名声明、真实路径、所有 family keys 与 nested controls，重核 728 依赖后输出[正式增量](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-named-sizeof-source-identity-reviewed-v1.json)（SHA `cdf9e3e3e97d80b6b3c4e54a6eac27e8aafcf0b910df2d5e9edfe2f6e04044b6`）；[验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/named-sizeof-consumption-validation-v1/validation.json) 保存 8 项先红后绿测试。旧 215 条 sizeof 证及其 4 条 pending 历史原样保留，由新增量表达准确来源许可；配置条件、模块选择、IR 和完整分母未升级。

## 旧 official 库存新增 when 身份

[`native_mapping_guard_identity.py`](native_mapping_guard_identity.py) 复用原生范围与唯一间隔 token 规则，为旧 official 库存中另 112 个 `encdec_when` 键联立两域的完整 `MCL_when` mapping／condition 节点、raw 路径、源文件 hash 和精确 token 位置。这些 token 与旧 1259 库存的物理 token 交集为 0；没有新增解析器或按名称近似配对。

[独立证书](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-additional-encdec-when-identity-review-v1/certificate.json) SHA `e316b165b009f6eccd09bbf741624573d7d13580a2d00276c359e0276dd5abf2` 核验 112 个定义、4 个源文件及 224 条后端绑定，并实际重现候选字节。[`native_mapping_guard_review_consumer.py`](native_mapping_guard_review_consumer.py) 的 `consume(review_dir)` 重新核 686 个依赖，输出[正式来源合同](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-additional-encdec-when-raw-identity-reviewed-v1.json)（SHA `2c97aab04c269a83a8ca96821aa2ce23c8fd1b37220dc1749a03cea47ef4bad6`）。[消费验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/additional-encdec-when-consumption-validation-v1/validation.json) 保存 6 项先红后绿测试。

许可仅为准确来源身份；分支极性、旧 696 条观察的正式迁移、静态排除和完整源码分母均未升级。历史 live457 中三项漂移仍为 FAIL，`producer_chain_integrity_permission_added=false`。

## 实际 initial pass 的有限消费

[`native_initial_pass_review_consumer.py`](native_initial_pass_review_consumer.py) 的 `consume(certificate_path, root)` 消费[真实 pass 独证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/independent-native-type-dependencies-review/initial-pass-annex-v2/certificate.json)（SHA `6e1a8245946c54fe783db7ddcd348fd0f4e24af72dff9534695a7a7479e12505`），核对原／fresh pre 全流字节相等、4 个真实编译命令、post 节点、23 个 Unknown 位置的规则与上下文和原静态类型义务。

[正式公共产物](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-initial-pass-literal-reifications-reviewed-v1.json) SHA `68c21ced853cdde4b8e53c61bc6b7f33a14cfb95033051b520438cf8db8e277f` 重核 1547 依赖，只授列定 331 个表达式经实际 `Frontend.initial_rewrite` 成为字面量的许可。原 333 行中的另 2 行继续 OPEN，不作为字面量；BF16 两域共 10 个 `E_if` 和两臂仍存在。普通条件保留 `E_constraint`，SYMBOLIC 的 5 个条件变为 4 true／1 false，这不证明后端控制消除。

[消费验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/initial-pass-consumption-validation-v1/manifest.json) 保存先红后绿测试、9 种字段／权限变异拒绝和实际 CLI 日志。类型元数据的 module 在 initial 重检前后可能变化；本证不声称完整 `Type_check.Env` 相等，也不授 actual IR PC、运行分支排除或完整分母许可。

原两处 Zbkb 后缀另经[独审](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/independent-native-type-dependencies-review/zbkb-exit-annex-v3/certificate.json)（SHA `745f7f2fcce995965ddd43e13f513339f3bce697f65146b2d78dcba4c912c24e`）确认来源原因：ZIP／UNZIP 的实际 `assert(xlen == 32)` 在冻结 RV64 类型环境中条件为 false，初始重检保留该断言，并把之后含 `zeros()` 的 `E_let` 后缀替换为 `E_exit(unit)`。[`native_zbkb_exit_review_consumer.py`](native_zbkb_exit_review_consumer.py) 的 `consume(certificate_path, root)` 重核 1573 依赖、两个完整块与外部 clause 语法，输出[正式两行附层](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-zbkb-initial-exit-origins-reviewed-v1.json)（SHA `5741ba5a1fe714d116bcc108dab388df1deef6995f0c2f7265a53599708038c0`）；[验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/zbkb-initial-exit-consumption-validation-v1/manifest.json) 保存 8 种变异拒绝。此附层只签两处实际 source cause，字面量新增 0，v2 两个 OPEN 历史仍在，未签 IR 或运行分支排除。

## 实际环境查询附层候选

[`native_env_resolution_probe.ml`](native_env_resolution_probe.ml) 在冻结原生节点的实际环境中调用公开 `get_val_specs`、`get_val_spec`、`get_val_spec_orig` 和 `lookup_id`。首轮尝试底层 `get_val_spec_opt`，但 `Type_check.Env` 没有公开该接口，构建失败保留在[首轮目录](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/environment-resolution-preparation-v1/build.log)。第二轮明确改用实际可见 map 的 key 和原／freshened 签名；没有修改 compiler 或旧 exporter。

[冻结候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/environment-resolution-preparation-v2/candidate.json) SHA `5cf4035aba1e4cfd91d1ca92a7a85f1a3cbd7f40a179f22f732de5a335ad0282` 重核 810 依赖，16 项测试与 4 个实际 compiler scope 用例通过。两个后端均实际重新导出；[`native_env_resolution.py`](native_env_resolution.py) 剥离新增 metadata 后，普通／SYMBOLIC 全流分别与旧 `f962fb93…`／`e1cf0495…` **逐字节相同**，不是仅比较选定函数。

| 同阶段查询 | 普通 | SYMBOLIC |
| --- | ---: | ---: |
| 全部查询 | 55584 | 57975 |
| 实际可见签名 | 27506 | 28380 |
| 完整标识符、原签名、backend extern 与原生 `DEF_val` 同时相等的候选 | 13926 | 14452 |
| 可见签名尚未完成上述原生声明对应 | 13580 | 13928 |

全部查询还保存 Local／global let、register、enum、布尔语法等角色。106／119 个 `lookup_id` 的 UNBOUND 全是赋值 `LE_id` 在该节点原环境中的查询结果，不作全局调用未解析结论。生成构造子／mapping 签名及规范化类型差异原样 pending；可见 map key 的位置也没有伪装成直接读取 `item.loc`。私有模块、未 opened 模块、重复 val 最新 key 与局部 shadow 的实际用例及早期测试失败均保留。

此包正在独审，只描述 `post_finalize_pre_backend_rewrites` 且 `skip_initial=true` 的准确阶段。它不证明 post-initial 环境相等、唯一局部 binder、完整 callee body、运行分支或完整源码分母。方案见[环境附层计划](native-env-resolution-plan.md)。

## 统一剩余义务与 Env 后续

上述 Env 段落保留独审前的候选时点。[Env v2 有限独证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/independent-environment-resolution-review-v2/certificate.json)（SHA `c185ed2699bc95dbbe0d97a110e636290c35dfa804d83fcf3b9dfa441ca300c0`）现已完成：两次完整导出及 scope 用例通过，保留两域各两个 `DEF_loop_measures` 内没有 typed Env 的 `E_id`。2340／2384 仅是按 selected Id、original binding 和 extern 聚类的来源任务；6807／7060 个完整查询变体仍全部保留。`get_union_id` 也会 freshen，因此每域各 13 组同时存在 `freshened_binding` 和 `union_binding` 的变化，不能把聚类解释为仅删一个 freshened 字段。

[统一剩余义务表](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/unified-remaining-obligations-v1/remaining.md)及其[机器索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/unified-remaining-obligations-v1/index.json)将缺口归入 source、typed、IR、caller、D 五层的 17 个语义门。scalar 11710、vector 8、BF 8 与公共 2 条原记录逐行保留准确 JSON pointer、原 ID 和整行 hash；不同族的粒度不同，记录数不能相加为分支分母。50 份 vector 完整原表已逐内容复核，原 occurrence、旧 ref、root 与入口域映射仍在冻结输入中。输入、工具与验证均由[manifest](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/unified-remaining-obligations-v1/manifest.json)（SHA `d7a606b0a5f72c009931d8affc2802a0044b169a8ed39e22e07b6993e2612a43`）绑定。

下一项明确验收是实际写入到节点选择再到源声明的双向来源：在隔离 compiler 中记录真实历史 item，覆盖 user／synthesized val、union、mapping 四方向与 outcome；所有查询和原来源记录保留，剥附层后的两个完整 AST 必须逐字节等于冻结原树，再交独审。`DEF_val` 的 `annot.env` 是声明检查前环境；`check_with_envs` 没有原 `check_defs_progress` 的 global/private 包装，不能替代原流水线的 after-state。此项仍在实施，未授完整 module、binder、callee、运行或分母许可。

[三族合同导航 v12](../../../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v12.json)（SHA `5445f80071f6148feb576719c3e91b6a5c39131d0d2c01f0470e12acfe7a48b4`）完整保留并重核 v11 的 179 条记录，新增至 262 个入口。它接入公共类型／setter／配置／sizeof／when／initial 来源、三族正式附接、BF guard 正式消费、Env v2 有限独证及统一剩余表，并以单独字段说明当前入口、补充关系与历史版本。scalar 七库 IR 桥及其旧引用附接、BF encoder 成功像仍列候选；Env 公共消费者在该导航冻结时仍在实施。

[v12 导航验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-contract-index-v12-validation-v1.json)记录两个先红后绿测试、原记录保全、输入重 hash 和全部当前 ID／别名解析检查。此步骤没有运行模型，没有新增运行观察或静态排除，也没有改变历史 live457 的三项漂移 FAIL。三族所选 raw 来源 pending=0，完整来源分母与全部运行分支闭合继续为 false。

v12 冻结后，[Env 正式公共附层](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-environment-resolution-reviewed-v1.json)（SHA `01e156b053b54f7babb485bef51c6c33df75e34f0e70858067ec62dddbf29af8`）已由 [`native_env_review_consumer.py`](native_env_review_consumer.py) 的 `consume(certificate_path, root)` 生成。1039 个依赖全部重核，6807／7060 个完整 query 和 55584／57975 个 occurrence 均按原 owner、完整节点、路径、selection 与 declaration join 核对。16 项 TDD 与 7 个实际证书／索引变异负控通过，命令和结果见[消费 manifest](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/environment-resolution-consumption-validation-v1/manifest.json)。它仍只签原 pre-backend、skip-initial 阶段的有限查询及精确声明候选。

[`native_env_measure_attachment.py`](native_env_measure_attachment.py) 再消费该附层和原类型构建前件证，生成[四个无 typed Env 节点的准确附接](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/shared-native-untyped-environment-measure-attachment-v1.json)（SHA `f6d42d0330e7cdedfd2e33fe9e13864cefafd98a4c2f0fc33a8d2f62e805ffdc`）。1105 个依赖重核；backend、definition key、完整声明 hash、实际 `E_id`、父路径和位置全部匹配。四条原未查询记录继续保留，分类为“无 typed Env 的构建前件节点”；Env／binder／callee 选择继续 OPEN，同名 runtime 调用未被排除。[验证](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/environment-measure-consumption-validation-v1.json)保存 6 项测试及实际命令退出 0。

四节点附接随后通过[独立审查](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/source-ast-full/independent-untyped-environment-measure-attachment-review-v1/certificate.json)（SHA `c9c50bc3daff673274438f61378440581e1935b200857ef378b0d644d9092574`）：1132 份绑定文件最终重 hash 无漂移，原 6 项及独立 12 项测试通过，消费者实际复演逐字节等于 `f6d42`。独证范围仍仅限上述准确附接，原 Env 查询和运行义务保持原状态。
