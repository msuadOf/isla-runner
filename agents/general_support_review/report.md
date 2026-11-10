# 通用支持分支审查结论（2026-10-07）

> 修复接续：2026-10-08 已以 `3074b7b`、`a906c7a`、`4b141eb` 修复并接入目标分支；V256 MRET 已恢复 4 gen，MPP 保留现行 Sail reset 的 0 例外。本文以下是 `2792afd` 的历史审查结论，现行交付及限定复验见 [fix.md](fix.md)。

受审为 Isla `refactor/general-support-20261007@2792afd73b3585144387bc68ff866b6e09c3e981`，直接基线 `7b7337b0dea0c4105644436a606dbec5ae9b3fea`。**不能按保持正确行为验收：确认两处 P1 回归，另有合法状态域的功能遗漏。** 主审动态对照与独立 gpt-6-astra high 只读审查一致；没有修改生产代码或提交。

## P1：拼接表示变化破坏既有 primop 调用链

`416b94f` 的 `isla-lib/src/primop.rs:1597–1607` 将 `append(Symbolic, Bits)` 和反序结果改为 `MixedBits`。位值本身仍与 SMT concat 等价，但 `add_bits_int`（684 行）、`sub_bits_int`（736 行）没有处理该表示；已提交的 `primop/float.rs:129` 宏生成的 `fp32_from_ieee` 等入口也只接受 Symbolic。

对相同合法表达式运行两版：7 位未知量与 1 位常量拼成 8 位，再加减具体整数或符号整数；两个拼接方向共 8 例。基线 **8/8 通过**且数值符合预期；分支 **8/8 返回 Type**。另一个 31 位未知量拼接 1 位常量后调用 `fp32_from_ieee` 的探针，基线通过、分支 Type。浮点工作树的剩余补丁不能用来替已提交分支消除这个问题。

建议复用已有 `replace_mixed_bits` 等机制适配消费者，并补组合回归。现有新增测试覆盖 concat 等价、固定切片、模型值和格式化，切题但缺少进入算术/转换消费者的覆盖，因而漏掉此回归。

证据：[算术探针](evidence/tests/review_general.rs)、[基线最终日志](evidence/base-final.log)、[分支算术失败](evidence/append-head.log)、[分支转换失败与缓存测量](evidence/head-final.log)。

## P1：全量前态具化令 VLEN=256 的求解丢失全部用例

`70707d7` 在 `src/isarch/exec.rs:855–868` 为 mapping 输入对所有 `target.pre_state` 字段调用 `model.get_val`。生产 CLI 使用 B129，而 `smt.rs:1626–1633` 的 `model_bits_to_bv` 拒绝超过 129 位的单个值。`vr*` 由 let vlen 符号化，因此 VLEN=256/512 即使执行非向量指令，也会在此失败。

使用两版都跟踪、哈希相同的 `ir/rv64d_v256_e64.ir` 做 MRET 对照：基线生成 **4 条**（3 Retire、1 Illegal），分支生成 **0 条**；两次 make 都退出 **0**。分支日志仍有 4 个执行完成终态，collector 在具化时放弃输出。`SolveCollectorState::record_error` 只保留 Timeout/SMT 错误，这个 Type 没有变成失败退出或明确错误日志。该错误处理策略原已存在，本次新增调用让它影响全部宽向量前态。

同环境默认 VLEN=128 的 MRET，两版均退出 0、生成 4 条、编码均为 `32'h3020_0073`。这说明旧 MRET smoke 的 PASS 不覆盖 VLEN=256。宽度探针另确认 formatter 可处理 128/129/256/512 位，而 `get_val` 在 256/512 位返回 `exceeds MAX_WIDTH=129`。

建议以可表达宽值的分片表示准备 mapping 状态；测试必须覆盖生产 B129 与实际 VLEN=256 IR，并检查生成用例，不能只检查退出码。新增完整状态测试主要使用 B64、小宽度，未覆盖此链路。

证据：[四组 smoke 汇总](evidence/smoke-summary.json)、[基线 V256 JSON](evidence/base256/rv64_zMRET.json)、[分支 V256 JSON](evidence/head256/rv64_zMRET.json)、[分支完成终态日志](evidence/head256/MRET.log)、[宽度探针](evidence/tests/review_width.rs)、[探针最终日志](evidence/width-assert-final-valid.log)。

## RV64 合法域功能遗漏（不是新增行为回归）

`2792afd` 的 `src/isarch/target.rs:593–597` 仅排除 MPP=2；当 hart 不支持 S 时仍接受 MPP=Supervisor。复用现有 fixture，S/U/H 均 false、当前 Machine、mstatus MPP=1 的查询返回 Sat，manifest 同时报 `validated`、allowed-privileges=Machine、mstatus-mpp=0,1,3。

当前 Sail `model/core/sys_regs.sail:159–165,237` 的 `have_nominal_privLevel`/`legalize_mstatus` 不会保留这个 MPP=1。应补能力相关的 MPP 约束，或者明确 manifest 只验证所列有限规则，不能视为完整合法状态域的证明。旧基线也允许此状态，因此这是新增功能覆盖不足；本轮没有用实际关闭 S 的完整生成 IR 运行该配置，仅有真实执行器/求解器 fixture。

SXL/UXL 固定 2 则与当前模型一致：Sail reset 按能力设置，legalize 禁止动态修改，不应把其他实现允许 RV32 的通用规范行为当成本模型回归。其余 mstatus 保留位、SD 与 FS/VS 等关系本轮没有宣称完成合法域闭合。

证据：[追加 fixture 补丁](evidence/mpp-fixture.patch)、[失败日志和 manifest](evidence/mpp-domain.log)。

## 语义与预期效果逐项判断

| 提交 | 判断 |
| --- | --- |
| 416b94f MixedBits | concat 位值等价和具体字段切片优化成立；新表示破坏消费者。无效索引由旧截断/不完整结果转为明确 panic，空切片返回空值也是行为修正。 |
| 7ba488c 宽位格式化 | `to_vec()` 保留高于 64 位的数据，测试覆盖 65/128/129 位、分段顺序与 arbitrary mask，未发现缺陷。 |
| d57304f Model 缓存 | 单 Model 内只缓存具体值、completion 切换清空、Arbitrary/错误不缓存；检查和测试未发现值语义错误，有局部收益。 |
| b96022e 采样记账 | 记录已采样标志并随 frame 继承；对应执行器测试通过，没有改变分叉选择算法。 |
| c9b9f3b mapping | 有意将原任取/覆盖结果改为拒绝多终态与传播错误，新增测试验证错误臂不可被成功臂掩盖；外层 solve 的非 SMT 错误退出策略仍是原策略。 |
| 5186d8e assert | solve-state 默认转换成显式控制流，实质增加失败臂与分叉/签名/预算开销。新增探针确认转换后的成功和 AssertionFailure 两臂可达；collector 仍丢弃 AssertionFailure，失败臂不会成为 gen。未补完整 CLI 人工 assert fixture。 |
| 70707d7 状态物化 | 新增 requested-instruction、完整兴趣寄存器前后态、completion 和具体 mapping 状态，确实改变输出与任意值选择，但宽 VLEN 失败。complete 是 Target 前态集合的完整性，并不涵盖所有架构寄存器，例如 PC 不在此集合。未做全套重放等价验证。 |
| 2792afd RV64 域 | 约束当前特权级、SXL/UXL 和 MPP 保留编码并输出 state-domain，有意缩小域；MPP 能力关联遗漏。JSON 删除原硬编码 arch.ext，属于输出 schema 变化。 |

这批提交包含修复和新行为，不能整体描述为纯重构、保持所有原行为。正常 V128 MRET 的返回类别/编码对照相同，不代表任意模型、clause、状态或 JSON 内容都相同。

## 性能证据与验证边界

同样的 debug 构建、`itrace,smt-thread-interrupt`、系统 Z3 4.13.3，单 Model 对同一个已约束 BV64 查询 20,000 次：基线 Z3 调用 **20,000**、循环约 **2.119 秒**；分支调用 **1**、约 **0.0058 秒**，均检查返回值。该测量证明缓存目的在重复查询热点实现，不能外推整条求解的倍数。MixedBits 固定字段切片保留具体值，也有定向测试和源码依据；没有本轮完整工作负载的端到端性能结论。全量前后态具化、额外 mapping SAT 检查和 assert 分叉同时增加工作量。

本轮通过：isla 库 79＋isarch bin 25；isla-lib executor 85、primop::tests 67、fmtval 2、model_get_var 3；默认 cargo check、fmt；转换后 assert 两臂和宽值边界两个探针；V128 两版 MRET、V256 基线 MRET。**V256 分支不是 PASS**，退出 0 但 gen=0 是已复现失败。

全 isla-lib 运行：分支 354 项、基线 344 项均在 Z3 `enumeration sort name is already declared` 处退出 1，证明该全量障碍不由这八提交首次引入；均不能计为全量通过。未运行全 clause、硬件差分或完整 CPP/Isla 重放。

原有库/bin命令：`CARGO_TARGET_DIR=../cargo cargo test --offline -q -j 8 -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --test-threads=1`；isla-lib 定向命令将包改为 isla-lib、目标改为 --lib，并分别添加 executor::、primop::tests::、fmtval::tests::、model_get_var 过滤。集成探针使用 --test 指定 [保存的测试源](evidence/tests/)。

MRET 命令：`CARGO_TARGET_DIR=../cargo CARGO_BUILD_JOBS=8 CARGO_NET_OFFLINE=true make solve ALL=MRET THREADS=1 ITRACE=1 OUTER_TIMEOUT=60s SOLVE_TIMEOUT=50s TASTIC=qfaufbv`；V256 额外加 `IR_FILE=./ir/rv64d_v256_e64.ir`。Make 使用 Homebrew Z3 4.16.0；每组均保存独立 JSON/日志/trace，IR、配置、二进制 SHA-256 和工具版本见 [provenance](evidence/provenance.json)。

快照位于 `.worktree/general-review-20261007/{head,base}`。基线跟踪文件与 git tree 逐项相符；分支仅在 cfg(test) 内追加 MPP fixture，生产代码与受审 tree 相符。新集成测试只在隔离快照追加，测试副本及补丁已保存。探针准备阶段出现过错误路径、缺少 trait、tactic 配置、调试格式和未声明局部变量等 harness 问题；初次日志保留，以上结论只引用有效最终运行，不将这些准备失败归因于分支。

下一步优先修复两个 P1 并用相同探针、两种 VLEN 和定向回归复验；再补 MPP 能力域及必要的 CLI/重放覆盖，之后才适合开展完整性能 A/B。
