# Isla 合流生产源码独立签收

冻结生产源码限定签收通过，最新 stage tree 为 `3d852a5fac6a07ae906e502a430a8ee14a65c075`，无当前源码阻断。独立 workspace 默认并发通过 Isla 197 项原回归加 7 项独立探针、其余库 13/5/1/394 项；另有 19 项集成测试及 4 个可编译错误变异拒绝证据。两轮测试初始化遗漏均已最小修复，原 14 项和随后 45+2 项分别逐一 fresh 进程通过。动态指令验收、全部 IR 来源和最终父仓 metadata 仍由对应审查单列签收，不将本报告外推为全 Clause 覆盖或预算通过。

## 受审版本与边界

固定输入是 memory Isla `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57` 与 float Isla `591693df2bc32019ea300511509ed683df09522e`，共同参照 `0008fae76f4cff86dae1a036d889f0414c228e9d`。候选位于 `.worktree/merge-float-memory-20261104/isla`。审查者只写议题 review 证据和自己的临时源码副本，未修改生产候选、原 dirty 树或分支。

首次生产合同冻结时完整文件 SHA-256 如下。后续 `exec.rs`/`target.rs` 仅测试区增加初始化及原因断言，生产区字节保持；最新完整文件哈希以本节末最终 seal 为准：

| 文件 | 冻结 SHA-256 |
| --- | --- |
| `src/isarch/exec.rs` | `bf3ed8f4ccff22b24d4634dbfb7e3874a6e110a7b9870bf803ba2879288644a8` |
| `src/isarch/target.rs` | `9a74e9f7b59c24ff4ec2fcd1619c4ffdf2c385ccbae0fe350d72caf9865c61d7` |
| `isla-lib/src/smt.rs` | `cbc61a63191bce19d2d6a578f2c7eb0a815f456165a3041dc915fdaf9d9e0663` |
| `scripts/run.mk` | `ea775308708f9cd1f085dbea141eb47bc779e5fec42dd33ae62c4cbedea598fe` |

[暂存源码清单](core/final/stage-source-seal.json)记录 56 个已变更 Rust/TOML/Make 文件的暂存与磁盘一致性；[独立副本输入](core/final/source-manifest.json)记录复制的完整编译源码、测试资源和本轮 `rv64d.ir` 哈希。[复核与实际链接](core/final/final-recheck-and-runtime.json)证明测试程序实际链接指定官方 `libz3.so.5.3`，并记录库/程序哈希、Rust 版本和冻结后源码一致性。

最终生成与验证 runner 的 8 行默认字段适配曾被随后 core stage 覆盖，导致正式构建 E0063 重现。这是共享树暂存竞态，失败记录保留；恢复后 v2 正式 Release 构建已退出 0。独立逐文件核对 v2 的 1042 项源码哈希、索引与磁盘一致，stage tree 为 `dbc7a451730ec5d142f45c17236f8d933e28cd86`；完整 manifest 为 `cdfc857291988ca8a48d3da5ca581df72f889de74d6bb67ac310dd809e3fd5b4`，inputs 为 `6718b04238010bc22db634e1a17d0aa6c0353af68b91000095b9ddbfb249813e`。证据见 [v2 完整 seal](core/final/final-v2-refseal.json)。相对独立受测源码，只有两个不参与本次库单元构建的 runner 各恢复四行字段默认值，四项生产关键哈希保持，见 [v2 差异](core/final/v2-versus-tested-delta.json)。不引用竞态前的完整 tree。

其后 v3 只增加 `executor.rs` 测试区 5 行和 `primop.rs` 测试区 9 行显式 SMT 初始化。独立核对每项改动均位于 `mod tests`，生产源码不变；再次逐文件核对 1042 项磁盘/索引及哈希，tree 为 `88a930026ca31c23225d5f9509b2b23502d14f77`，见 [v3 seal](core/final-tests-init/final-v3-refseal.json)与[独立完整源码清单](core/final-tests-init/independent-source-manifest-v3.json)。此 tree 随后形成组件合流提交 `7cce7834`。

提交后默认并发 workspace 又暴露 Isla crate 45 项同类测试初始化遗漏；独立 fresh 进程另确认两个 `catch_unwind` 测试会把未初始化 panic 误当预期类型错误而假绿。修补只涉及 `src/isarch/{exec,memory_model,mod,target}.rs` 的测试区初始化及三处实际 panic 原因匹配。独立核对这四个文件 `#[cfg(test)]` 前的生产区逐字等于 `7cce7834`，并逐项核对 1042 文件的磁盘/索引/哈希。最新签收 tree 为 `3d852a5fac6a07ae906e502a430a8ee14a65c075`，见 [最终 seal](core/workspace-init/final/final-refseal.json)与[完整源码清单](core/workspace-init/final/independent-source-manifest.json)。上列 v2/v3 仅保留为中间已核版本。

## 相对共同基准的继承与本轮增量

`0008fae76` 是观察实际增量的共同坐标，不是本次新功能的起点。三组路径/行数见 [共同基准](core/final/delta-0008fae.numstat)、[相对 memory](core/final/delta-memory.numstat)、[相对 float](core/final/delta-float.numstat)，行数包含已有测试，不能作为本轮生产复杂度或新增能力数量。

| 来源 | 合流中保留的已有功能 |
| --- | --- |
| memory 侧相对共同基准 | 数组内存与区域/排除/PMA/PMP、CSR 符号化、固定编码/前态、value hints/encoding slices、访存事件与前后内存、模型缓存及终值时间盒、回环过滤、skip/diagnostics 与批次 partial 记账 |
| float 侧相对共同基准 | 原生浮点/宽位向量具体化、完整寄存器前后态及 initial_state、编码分支与执行约束重接、同 Context 枚举缓存及引用生命周期、类型化 tactic/default/qffp/种子能力校验、真实 frame ExecuteAs 续执行、trace 和三种指令表示 |
| 本轮必要兼容增量 | JSON 并集接入同一个最终 Model；访存必需值错误整体拒绝并保留原错误；nested Poison 与 decoder 未完成/多结果错误不能伪装成功；initial_state 与 symbolic CSR 复用同一变量并兼容具体 fixed-prestate 位宽；合并接口/测试初始化、Make 配置及文档同步 |

未增加新的数值语义分支、ITE/符号化配置层、控制流线性化能力或 OPEN 策略。`execution_limits` 相对 float 的生产行为未增改；`frame.new_call` 保留 float 已有语义。现有 memory 分片/提示与 float 初态域属于输入分支继承，不记成本轮新增配置。未摄取外树 F1–F5 dirty 补丁；既有混合内存后端等基线边界仍应分账。

## Schema Union 与调用链结论

源码保留 `memory-events`、`pre-memory`、`post-memory`，FPR/fcsr 与 GPR 的完整前后态，requested-instruction/path-signature，三表示，hint/slice、state-domain 及错误/partial/skip 记账。collector 先将编码辅助约束接回完整执行域，再取得唯一最终 `Model`。指令、编码、门所用具体前态、完整寄存器前后态、返回值及全部访存数据在该作用域查询，只有全部成功后才构建并提交完整条目。辅助汇编/译码函数使用从此 Model 取得的具体参数和具体寄存器环境；未用独立求解结果替换最终机器状态。

必需值任一查询/类型错误整例不进入 `gen`，保留错误与 `incomplete` 诊断；nested Poison 同样拒绝。合法空值只有明确来源：无事件的空数组、read 的不适用 data，以及事件账本证明 write-first 且未观测的自由旧字节。它们与 Model 查询失败分开。详细合同见 [合同表](core-contract.md)。

ExecuteAs 使用 `frame.new_call` 与原 task_id/checkpoint 续执行，保留原寄存器、内存、lets、路径签名、累计时间、执行预算及 trace；独立两阶段探针检查首阶段内存写入、次阶段读取、两段寄存器修改和两段事件都保留。枚举 sort 在同 Context 内缓存并正确持有/释放引用，原 solver 全部析构后 checkpoint 仍可重放；同/跨 Context、多成员/结构字段及冲突硬失败回归通过。tactic 初始化探测与实际创建一致，未恢复 memory 的不支持 seed 时静默跳过。

## 独立执行与错误变异

全部测试在独立副本、独立 target 运行，`CARGO_BUILD_JOBS=4`，显式 `RUSTFLAGS` 链接指定官方 Z3，启用 `tracetool smt-thread-interrupt`。未复用正式构建产物。实测入口：

```sh
cargo test -p isla --lib --features 'tracetool smt-thread-interrupt' -- --test-threads=4
cargo test -p isla-lib --lib --features 'tracetool smt-thread-interrupt' -- --test-threads=4
cargo test -p isla-lib --features 'tracetool smt-thread-interrupt' \
  --test smt_init --test smt_tactic --test model_concretization \
  --test mixed_bits_memory --test mixed_bits_consumers --test mixed_bits_float_consumers \
  -- --test-threads=4
```

| 验证 | 实际结果与证据 |
| --- | --- |
| Isla 原测试和独立探针 | 204/204：[日志](core/final/isla-all-tests.log) |
| isla-lib 全单元测试 | 最终默认并发 394/394：[日志](core/final-tests-init/default-concurrency.log)；先前四线程绿的顺序依赖已修订，见下文 |
| 原 14 项失败测试逐项 fresh 进程 | 14/14：[结果](core/final-tests-init/fresh-fourteen-results.json) |
| 六组集成测试 | 19/19：[日志](core/final/integration-tests.log) |
| 错误变异 | 4/4 编译成功后被断言拒绝：[清单](core/final/mutations.json) |
| 变异恢复正控 | 7/7：[日志](core/final/restored-seven-probes.log) |
| 最新 workspace 默认并发 | 204/13/5/1/394/0/0 全通过，其中 Isla 含 7 项独立探针：[日志](core/workspace-init/final/workspace-default-concurrency.log) |
| 随后 45 项失败及 2 项假绿逐项 fresh 进程 | 47/47，且均无未初始化消息：[结果](core/workspace-init/final/fresh-forty-seven.json) |

独立探针覆盖关联的 x1/f0/fcsr、前后态、编码与返回值、访存事件/内存；七维实际 Unbound 查询失败；write-first free-null；无访存空数组；nested Poison；decoder Exit；ExecuteAs 多阶段内存/状态续接。四个变异分别删除 memory-events schema、从剥离执行/编码约束的独立 solver 取 Model、吞必需前态错误返回空 map、续执行重置寄存器。变异只能在审查副本注入，原候选未改。

## RED 的修订与验证边界

中间独立 RED 保存在 [Poison 日志](core/probe2/nested-poison-red.log)和[decoder Exit 日志](core/probe2/decoder-exit-red.log)，冻结版本对应探针均转绿。同名 CSR/initial_state 和具体 fixed-prestate 组合测试通过。

P3 真实 IR 测试曾因未钉 cur_privilege 探索到 VirtualSupervisor/User，再触发 Zicfilp 的未支持 Hypervisor 内部异常而返回 Poison。owner 对候选、bdd、float 三 IR 复证同红；绕过 wrapper 仍同红，因此保持 wrapper 和异常拒绝，fixture 显式 Machine 后通过。它不是将真实错误重新归为正常 guard 拒绝。

**真实 CLI 的同类输入边界仍单列。** 动态验证随后发现固定编码的启动期 `decode_fixed_instruction` 在未钉 cur_privilege 时也触发相同辅助域异常，返回“依赖符号状态，不能跨 solver 复用”。源码路径明确使用原始 regs 加 fixed-prestate；不含主 solver 已建立的架构初态域。正确拒绝 Poison 不能撤回，但 fixture 的 Machine 修正不能代替该无钉输入的真实 CLI 通过。定向验证可显式给出 Machine 并注明输入域；未钉输入应保留失败边界，不能默默增加默认值或把该情况记为普通 guard 拒绝。此项动态验收口径由主 agent 裁决，尚不在本报告的 PASS 中。

主 agent 已裁决本轮 union 按已有明确 Machine 定向域（显式 prestate）验证，不默加默认值，不重构全域 decoder。未钉权限的 startup 失败及对应基线证据继续保留，不声称固定编码入口覆盖全部未钉权限域。

正式 isla-lib 默认并发运行随后暴露 380/394，14 项均未初始化 SMT。独立审查用自己四线程全绿的同一二进制，在 fresh 进程逐测两个代表项也都失败，见 [fresh 进程证据](core/final/fresh-test-initialization.json)。来源是 memory `bdd` 在未初始化时默认 tactic，14 个测试未主动配置；float `591` 改为显式能力探测，合流需适配旧测试初始化。这是本轮测试接口遗漏，不能归为无关旧失败或在生产恢复自动初始化。最终 14 行测试初始化补丁已独立审核，默认并发 394/394 和逐项 fresh 进程 14/14 均通过，关闭该项。

随后 workspace 默认并发的 Isla crate 为 152/197，另 45 项同源初始化错误；前述单包/四线程绿不能覆盖该失败。独立 [fresh 红例](core/workspace-init/fresh-red.json)确认三个代表项失败；[两项假绿](core/workspace-init/fresh-falsegreen.json)返回成功但其实捕获未初始化 panic。owner 最小补测试初始化并校验实际配置错误原因；最终默认 workspace 与 47 项 fresh 进程通过，关闭此项。生产没有恢复自动初始化，没有更改 tactic 或约束。

旧 deadline 测试要求一个可快速求解的乘法式在 1ms 内必超时，独立重现实际 SAT。冻结版本改为验证真实 deadline 调用可完成或正确报超时且 solver 可继续使用；确定性 watchdog 中断由既有受控调用测试验证，两者均通过。未把偶发 SAT 改称超时，也未添加难题/改变生产约束。

最新 tree 源码签收允许继续正式动态验收并形成测试兼容修正提交。最终 IR 全配置来源、真实 Make/GCC/Clang/数值/访存产物、最终组件与父仓 metadata/gitlinks、远端可获取性另行签收；旧 PASS 不改署合流版本。
