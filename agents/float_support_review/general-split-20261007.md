# 通用修改归并到独立工作树（2026-10-07）

> 2026-10-08 修复交付：通用分支已追加三个 `fix(scope): 中文说明` 至 `4b141eb`，修复审查发现；精确及浮点组合的 V128/V256 MRET 均4 gen。原归并/拆分与审查失败版本仍保留为历史，见 [修复交付](../general_support_review/fix.md)。

> 独立审查接续：`2792afd` 相对 `7b7337b` 已确认 MixedBits 消费者和 VLEN256 全量具化两个 P1 回归；旧定向测试与 V128 MRET 的限定 PASS 不覆盖这些边界。原归并/拆分记录保留，当前分支需修复后复验，见 [审查报告](../general_support_review/report.md)。

> 当前接续：用户要求按改动类型拆分，原单提交方案被下方重做方案替代；旧记录保留为历史。

## 目标与边界

用户要求在根目录.worktree/新分支工作树完整带入当前Isla修改，将与浮点无关的通用修改合成一个commit。原isla工作区、索引及HEAD保留。目标目录`.worktree/isla-general-20261007`，分支`refactor/general-support-20261007`。只迁移isla源码改动，不复制target/output缓存，也不混入父仓库文档或其他子模块。

## 提交范围

一个提交包含MixedBits拼接/切片、宽位格式化、Model具体值缓存、路径采样标记、mapping错误处理、solve-state断言两臂、完整前后态/请求指令与编码的一致物化、通用不可编码诊断、RV64能力探测及特权状态合法性约束。后者属于RISC-V通用架构支持，不宣称为架构无关引擎。

浮点primop替换及专用dispatcher删除、scalar_sort（目前只有浮点消费者）、fcsr主动符号化、FS/VS偏好、官方名单、FD入口/配置、旧浮点测试迁移和整份生成IR均不纳入。本次不修改实现语义；混合文件按代码块提取。通用完整状态测试中的人工fcsr fixture只使用通用bitvector/struct机制，不依赖fcsr自动接入。

## 步骤与验证

1. 保存原HEAD、两层补丁、索引条目、24个改动文件哈希与最终副本。
2. 构造HEAD加通用改动的精确候选；测试不依赖未提交浮点实现，验证fmt、默认编译、isarch/位向量/模型缓存/执行器定向测试。
3. 创建新工作树，先按原分层应用全部补丁并核对文件哈希；用独立索引提交通用候选。
4. 新工作树索引归到新HEAD，剩余浮点改动统一未暂存。最终全部源码逐文件等于原工作区；原索引及HEAD不变。
5. 新工作树完整组合复验和make solve MRET；精确提交的smoke与完整组合分开记录。提交只新增一个，不push。

证据目录`isla/target/general-split-20261007/`。提交与核验已完成，见下文。

## 完成记录

新分支 `refactor/general-support-20261007` 位于 `.worktree/isla-general-20261007`，仅新增提交 `4089545ce1ebe2629ab4285f0c93364d10e44ff2`（完善符号执行通用数据处理、状态物化与结果校验），父提交为 `7b7337b0dea0c4105644436a606dbec5ae9b3fea`。11文件，+1458/-156，含回归测试；没有顺带重写实现。

原24个改动文件的最终内容在新工作树逐个SHA-256一致。新索引已归到新HEAD且无暂存内容；17个剩余路径保留浮点相关差异（含新增未跟踪文件）。原isla的HEAD、索引条目及24文件哈希均保持不变，未push，未移动父仓库gitlink。这里的“迁移”保留原目录作为副本。

### 验证与证据

精确通用候选通过：`cargo fmt --all -- --check`；`cargo check --offline -q -p isla --bin isarch`；以下测试统一使用 `--offline -q`、`--features itrace,smt-thread-interrupt` 和 `-- --test-threads=1`：

- `cargo test -p isla --lib --bin isarch`：79库＋25bin，无跳过。
- `cargo test -p isla-lib --lib executor::`：85项。
- 同一isla-lib命令分别过滤 `primop::tests::`、`fmtval::tests::`、`model_get_var`：67、2、3项。
- 精确候选 `make solve ALL=MRET THREADS=1 ITRACE=1`：退出0，4 gen。
- 新工作树完整组合：同一isla测试83库＋25bin、fmt通过；同一make命令退出0，4 gen。

以上使用 `CARGO_TARGET_DIR` 指向原 `isla/target`。候选和新工作树的target链接用于兼容Make固定运行路径；`.worktree/sail-riscv`链接到原sail-riscv以保持相邻配置路径。候选首次smoke因缺少运行路径链接未启动（子进程127），修复环境后重跑通过；首次失败日志保留，不算PASS。

精确候选IR SHA-256为 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`，完整组合为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。两次是不同IR的独立smoke，不作为行为等价证明。精确候选配置SHA-256为 `71fb63e105331a0f329261c636e55446af42ba0367c96e45c9b49cb60332ad2d`。

证据目录内 `checks.json`、`candidate-smoke.json`、`full-smoke.json`、`full-tests.log`、`commit.patch` 和 `after.json` 分别保存命令结果、二进制哈希、精确补丁及迁移核验。未运行全量isla-lib、浮点全套及硬件差分；本轮仅对归并边界和上述回归作限定PASS。

## 按改动类型重做（已完成）

用户澄清控制数量不等于全部合并。沿用工作树和分支，将4089545替换成8个职责明确的提交：MixedBits运算、宽位格式化、模型缓存、采样记账、mapping结果校验、solve-state断言分支、完整前后态/编码物化、RV64特权域。每类测试随实现提交，跨文件按职责分块。

先保存原索引/HEAD、新工作树残余补丁及24文件哈希，逐层构造并定向测试。最后必须验证新链末端tree等于4089545，以保证浮点残余与最终代码均不变；只更新新分支，保存旧提交回退引用，原isla和父gitlink不动。证据目录为`isla/target/general-resplit-20261007/`。最终tree相同则沿用同版MRET证据，不重复运行无变化的完整组合。

### 新提交链与验证结果

| 提交 | 内容 |
| --- | --- |
| `416b94f` | 修正 MixedBits 拼接、切片及空位向量边界 |
| `7ba488c` | 修正超过 64 位的位向量值格式化 |
| `d57304f` | 缓存 SMT 模型具体值以复用符号求值结果 |
| `b96022e` | 记录路径采样状态并随执行帧继承 |
| `c9b9f3b` | 严格校验汇编 mapping 结果并传播执行错误 |
| `5186d8e` | 为 solve-state 保留符号断言的成功与失败分支 |
| `70707d7` | 使用同一模型物化完整前后态、请求指令和编码 |
| `2792afd` | 依据 hart 能力约束 RV64 特权状态并报告状态域 |

新链末端`2792afd`的tree与旧4089545完全一致。原单提交保留于`backup/general-single-20261007`，现行分支不再包含4089545。工作树路径及分支名不变；原isla HEAD/索引、两处24文件哈希、新工作树未提交补丁均核验不变，新暂存区为空。未push。

逐层测试统一 `cargo test --offline -q`，feature为`itrace,smt-thread-interrupt`，测试参数为`--test-threads=1`，共享`isla/target`构建缓存：第1层isla-lib `primop::tests::` 67项、第2层 `fmtval::tests::` 2项、第3层 `model_get_var` 3项、第4层 `executor::` 85项、第5层isla库 `isarch::tests::` 4项、第6层isarch bin 25项、第7层isla库73＋bin25、第8层库79＋bin25均通过。各层运行cargo fmt，最终全部跟踪文件及符号链接逐项匹配旧提交。

首次逐层复制保留时间戳，导致Cargo复用第7层测试产物（第8层显示73）；已改为刷新时间戳，并从基线完整重跑八层，最终第8层确认79项。哈希核验脚本也已修正符号链接和非ASCII路径处理。最终结论以重跑后的`checks.json`及各层日志为准。最终tree和未提交组合内容无变化，沿用上节两套MRET成功证据，本轮没有重复make solve或全量测试。

`general-resplit-20261007/after.json`记录逐提交tree、diff stat和不变性核验；`groups.json`保存职责与文件清单，`verify.py`/`commit.py`保存验证和Git重组步骤。此次仅重组历史，不改实现，不把浮点专用层纳入。
