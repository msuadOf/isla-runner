# 浮点类型收敛与 BF16 修复后的 V128 IR 集成

2026-09-26 最终 C1 模型的 V128 IR 已与 79 份严格配置同批切入主 `isla/`。当前正式 IR SHA-256 为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。本节记录当前验证；末尾单列未切入主树的 A 候选及其未知输入超时，保留历史失败边界。

外部原始证据位于独立目录 `isla-float-ir-final-20260926.q1Auj4`，下文用 `IR_STAGE` 指代该仓库外目录。`source-manifest.json` 锁定 165 个 `model/` 文件的逐项 SHA-256；复制前后与原主源码逐项相同。Sail-RISC-V HEAD 为 `f8ce8490981eac6396a31013180a2e718615757d`，Isla HEAD 为 `f4f8e4584a70588c66c9e7a6286cc20211618f18`，二者另含本议题未提交修改。manifest SHA-256 为 `1458881ee1154470f33c7c5d1f4ec103fea60c4cddf7cf72e76ea56509700450`；共享异常文件与公共包装文件 SHA-256 分别是 `d80c4aabcc40f6c0de5aad439aab24a012de51a98ec1a3669ff4a52a781c9bf6`、`ee9ba560fb4acb70ed664593da95a52657dfef9bd6643ed830a1d4a4d5b0a881`，BF16 文件为 `814008056c5a43d1bf3c38af1aa3da1d31bc4518619fdf55051879961ea14b60`。

## 最终 C1 生成与集成

复跑时由调用者设置 `IR_STAGE` 为仓库外新目录；以下命令中的插件和 JSON 须使用本次所列版本。Sail 为 0.20.1（`446fb477`）；插件 SHA-256 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`，`rv64d_v128_e64.json` SHA-256 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`，配置为 XLEN64/VLEN128/ELEN64。

```sh
: "${IR_STAGE:?set an external frozen source and output directory}"
cd "$IR_STAGE/model"
mkdir -p "$IR_STAGE/memo" "$IR_STAGE/ir"
sail -plugin "$IR_STAGE/sail_plugin_isla.cmxs" -isla -D SYMBOLIC \
  --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 \
  --memo-z3-path "$IR_STAGE/memo/sail_smt_cache" --all-modules \
  --isla-preserve encdec_compressed_forwards \
  --isla-preserve encdec_compressed_forwards_matches \
  --isla-preserve encdec_compressed_backwards \
  --isla-preserve encdec_compressed_backwards_matches \
  --isla-output-dir "$IR_STAGE/ir" --config "$IR_STAGE/rv64d_v128_e64.json" \
  -o rv64d_final riscv.sail_project
```

此次生成完整退出码 0，real/user/sys 为 377.33/135.10/247.23 秒；原始输出在外部 `ir/generate.log`。共享机器有其他高 CPU 任务，耗时不用于性能比较。生成的新 IR SHA-256 为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。切换前保存主树与 Isla 子仓 `git status --short`、原 IR 及全部 TOML 到外部 `reports/pre-switch-*.txt` 和 `main-before-switch/`。集成脚本逐文件要求主 IR 仍为旧 `c9e1bfe2…`，候选 79 份 TOML 与主文件除严格哈希外逐字节相同；通过后先暂存，再安装 IR 和 79 份 TOML，最终逐文件核对。主 IR 与配置现均为新哈希。

## 最终 C1 验证

| 检查 | 结果与可核对证据 |
| --- | --- |
| IR 结构与源码差异 | 使用迁移前 `6fc39efd…` IR 作基线，[名称检查器](tools/check_d_ir.py)确认原 79 声明、12 旧体、67 新体以及模型同名依赖均齐。67 根可达 152 个普通函数，无缺体、assert 或 throw；仅 `zfloat_decompose` 因已知位宽选择出现 Jump，动态单路径另验。去 SourceLoc 与形参重编号后，旧 `c9e1bfe2…`→新 IR 的 2052→2049 个函数中，新增 12、移除 15，现存 71 个函数体变化：70 个浮点辅助/包装与 BF16 `zexecute`。报告在外部 `reports/{check_d_ir,helper-closure,ir-function-diff}.json`。 |
| 277 个未知入口 | f16 90/90、f32 96/96、f64 91/91，均 SAT、普通函数进入、恰好一条完成路径；三格式 real 分别为 5.25/5.31/5.25 秒，外部 `logs/unknown_{f16,f32,f64}.log`。这项只证明列出的未知输入入口没有新增数据路径，不证明所有符号输入数值等价。 |
| helper 与旧断言迁移 | 67/67 原 helper、估算 350/350+1618/1618+420/420、旧 12 体 39/39+24/24、旧测试迁移 35/35，均按独立预期验证完整结果位和五 flags：先 SAT 再差异 UNSAT，检查普通体调用及单条完成路径。外部 `logs/{cases,spike-estimate-cases,estimate_sweep,estimate_special,old12_cases,old12_narrow_boundaries,legacy}.log`；总入口 `run_helper_gates.sh` exit 0，`reports/provenance.sha256` 保存 IR、包装器、runner 和输入哈希。 |
| RV64 非访存定向矩阵 | 24 个输入组、1509/1509 条具体编码与状态样例 PASS，基线输入逐名覆盖 77/77 个非访存 clause。每例经译码、反编码、执行、SAT 与状态差异 UNSAT；外部 `matrix/summary.json` SHA-256 `9f4fccb7c3fb973afbee2dd491e4c56f2135d556b35f6ad590f957628d7396f5`，逐组固定输入/输出哈希。Astra 独立逐例复核。该结果不代表每项全部 RM、SEW 或输入域。 |
| BF16 LMUL8 与严格配置 | [BF16 专包](tools/bf16_lmul/cases.json)10/10（8 非法、2 合法）由同一新 IR 完整运行且差异 UNSAT，外部 `reports/bf16-lmul-results.json`。主树官方脚本检查 79 份严格配置、67 个其关注的 V region 和 22 锚点；额外全量脚本对 132 个 region 逐项核对，均退出 0，外部 `reports/workarounds-main.json`。 |
| 主入口及通用单测 | `CARGO_BUILD_JOBS=4 make -C isla -j1 solve-MRET THREADS=1 OUTER_TIMEOUT=60s SOLVE_TIMEOUT=55s SMT_TIMEOUT=30s TASTIC=qfaufbv` 退出 0，4 条完成路径中 3 条 `Retire_Success`、1 条 `Illegal_Instruction`；同参数 `solve-FCVT_S_BF16` 退出 0，39 条中 36 条退休、3 条非法，均无 Unknown/timeout。`cargo test -q -p isla-lib --lib primop::float` 为 10/10。完整命令与执行器日志见外部 `logs/main-solve-{MRET,FCVT_S_BF16}-*.log`、`logs/main-float-unit.log`；原主 `output/` 已先备份，未覆盖旧证据。 |

动态测试复用已构建 runner：D、未知、Legacy、E 非访存和 BF16 非法路径二进制 SHA-256 分别为 `eabdccd795b12236c72f9a0bc07411d4139c219227c29604a3071de736ec511c`、`67eb9e5117bc208e5ad3f0c7d1352388f9eeb1bed8bcbbfae626e8110ab4804c`、`5024b554d5ddab75b03aed9b4e09cc6b38dd310acc8fbb7522db7dad06be75f1`、`bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`、`e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3`。前面三个二进制及输入另见外部 `reports/provenance.sha256`，E 与 BF16 的哈希见外部实际文件及矩阵摘要。本轮生产 Rust 执行器未改；另有 `smtperf` 测试宏修复，不影响预构建 runner 语义。所有 runner 均解析并执行最终新 IR；主入口另用当前源码构建的 `isarch` 执行。

普通 `make solve` 的旧有 220 项整组未完成、10 个浮点访存 clause 依赖独立内存议题；本轮上述通过范围不扩展为全 E 阶段 PASS。旧 `c9e1bfe2…` 的官方 77 批次结果只适用于旧 IR，不转记为新 IR 验收。

## 历史 A 候选：表示层首次收敛，未切主

以下记录仅对应外部目录 `isla-float-ir-refresh-20260926.rbXR3F`，与最终 C1 的快照和哈希不同。目录中的 `source-manifest.json` 记录当时 165 个模型文件逐项 SHA-256、两个子仓 HEAD、Sail 版本、插件、V128 配置和模型差分哈希；快照前后源文件哈希相等。

### 生成输入与结果

- Isla HEAD：`f4f8e4584a70588c66c9e7a6286cc20211618f18`；Sail-RISC-V HEAD：`f8ce8490981eac6396a31013180a2e718615757d`，均另含本议题未提交修改。完整模型快照 manifest SHA-256：`678fa776a36c2b8e26bf8c2cbd3e2a9987e10f9583240e06a56da5a4e2552e87`。BF16 文件 SHA-256：`814008056c5a43d1bf3c38af1aa3da1d31bc4518619fdf55051879961ea14b60`。
- Sail 0.20.1（`446fb477`）；Isla Sail 插件 SHA-256 `c4eccb06af9f85820c28bd67556ae0f191361c93cbe1afb334900f9e1f0e22f6`；`rv64d_v128_e64.json` SHA-256 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`，明确为 XLEN64/VLEN128/ELEN64。
- 在冻结 `model/` 下运行 `sail -plugin "$IR_STAGE/sail_plugin_isla.cmxs" -isla -D SYMBOLIC --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --memo-z3-path "$IR_STAGE/memo/sail_smt_cache" --all-modules`，再分别传四项 `--isla-preserve encdec_compressed_forwards`、`encdec_compressed_forwards_matches`、`encdec_compressed_backwards`、`encdec_compressed_backwards_matches`，最后传 `--isla-output-dir "$IR_STAGE/ir" --config "$IR_STAGE/rv64d_v128_e64.json" -o rv64d_refresh riscv.sail_project`。外部 `ir/generate.log` 记录工具输出与耗时；生成 exit 0，real 433.69 秒、user 167.14 秒、sys 265.51 秒。共享机器另有高 CPU 任务，本次耗时不用于性能对比。
- 候选 `ir/rv64d_refresh.ir` SHA-256：`361980eac11c52d06d940a552b0b6144777461f47d104315ea7df86e088f67cd`。生成过程仅写仓库外目录；在 A 候选测试时，正式 IR 哈希为 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`。

### 静态与具体语义检查

| 检查 | 候选 A 结果与证据 |
| --- | --- |
| 原 79 个接口、12 个旧体、67 个新体 | [名称检查器](tools/check_d_ir.py)使用迁移前 `6fc39efd…` IR 作基线，exit 0；外部 `reports/check_d_ir.json`。67 根可达 151 个普通函数，无缺体、assert 或 throw。闭包内唯一 Jump 位于按已知位宽分派的 `zfloat_decompose`；静态结果不替代未知输入单路径检查。 |
| 函数结构差异 | 去 SourceLoc 并按形参顺序做 alpha 归一后，2052→2048 个函数：新增 11 个、移除 15 个格式专属分类函数，已有函数中 121 个变化。120 个属于 IEEE/RISC-V 浮点辅助或包装；另一项 `zexecute` 的结构差异集中在 BF16 VF guard 与断言次序。未变函数 1916 个。详情见外部 `reports/ir-function-diff.json`；声明与类型变更由独立源码审查覆盖。 |
| BF16 LMUL8 | [专包](tools/bf16_lmul/cases.json)的 8 个非法及 2 个合法编码，旧固定 runner 在新 IR 上 exit 0、10/10 差异 UNSAT；外部 `reports/bf16-lmul-results.json`。旧 IR 红例是 guard 前断言失败，见专包记录。 |
| helper 具体结果 | D 阶段归档 runner 使用新的完整 IR 测试副本，67/67 原 helper、350/350 估算定向、1618/1618 查表扫点、420/420 特殊值、旧 12 体的 39/39 与 24/24 边界均通过。每例检查普通体调用、SAT、完整 bits/五 flags 差异 UNSAT 与单条完成路径；原始日志在外部 `logs/{cases,spike-estimate-cases,estimate_sweep,estimate_special,old12_cases,old12_narrow_boundaries}.log`。 |
| 旧测试迁移 | 新候选 IR 加调用包装器后，`test/softfloat_legacy/cases.tsv` 的 35/35 项 exit 0，检查同上；外部 `logs/legacy-after-unknown-timeout.log`。 |
| RV64 非访存矩阵 | 24 个归档输入组共 1509 条具体样例全部通过，基线输入集合与官方 77 个 RV64 非访存 clause 清单逐名相等。每条检查真实编码→译码→反编码→执行、SAT 与状态差异 UNSAT；外部 `matrix/summary.json` 保存输入/输出哈希、逐组数量与耗时。该结果不代表每个 clause 的全部输入域。 |
| 严格配置候选 | 仅在外部复制的 79 份 TOML 中，将旧 `c9e1bfe2…` 哈希逐项改为 A 候选哈希。按冻结模型核对 79/79 严格绑定、全部 132 个 region 坐标及 22 个注释锚点，exit 0；外部 `reports/workarounds-candidate.json`。A 候选时正式配置未切换。 |

动态检查复用已有 D、Legacy 与 E 非访存 runner 二进制，其 SHA-256 分别为 `eabdccd795b12236c72f9a0bc07411d4139c219227c29604a3071de736ec511c`、`5024b554d5ddab75b03aed9b4e09cc6b38dd310acc8fbb7522db7dad06be75f1`、`bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`；未知输入 runner 为 `67eb9e5117bc208e5ad3f0c7d1352388f9eeb1bed8bcbbfae626e8110ab4804c`，BF16 非法路径 runner 为 `e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3`。它们链接的是本议题已经删除旧专用浮点分发的 Isla 执行器；本轮新增的 Rust `smtperf` 改动仅在测试宏调用，不改变这些 runner 的执行语义。所有动态判断都实际解析并运行上述新 IR。

### 未通过门槛及其后续处理

277 个未知输入/RM 包装器的 f16 第一组设 600 秒外限，只完成前 17/90 项，每项已报告 SAT、普通函数进入和一条完成路径，随后外限 exit 124；最后完成 `d_unknown_riscv_f16Div_rm1`。f32/f64 未运行。旧 D 候选的同组 90 项约 5.47 秒，A 候选出现显著耗时增长，不能把 17 项写成 277 项 PASS。原始日志为外部 `logs/unknown_f16.log`，外层 `run_helper_gates.sh` 因超时停止；35 条旧测试已另行补跑。随后通过隔离表示实验收敛为现行 C1，重新冻结、生成完整 V128 IR 并复跑上述门槛；A 候选从未切入主 IR 或严格配置。官方 77 项旧 IR 批次亦不转记为 C1 结果。
