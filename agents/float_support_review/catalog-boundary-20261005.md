# catalog 提交边界收缩（2026-10-05）

> 后续（2026-10-06）：本文旧三提交已由 `9d8b915` 组合轨迹与 `c1d6bc6` 独立writer替代，旧链保留在backup/trace-before-20261006。本文是历史记录；现行开关、提交和验证见[轨迹重组记录](trace-composition-20261006.md)。

## 目标与步骤

用户要求修改 `8545e7c`，范围仅 catalog/itrace，不将浮点完整支持纳入收缩。

1. 保存 HEAD、index、工作区快照，在隔离候选中先补 catalog 不改变输出模式的回归。
2. 将紧凑输出设为独立显式选择；solve 仍显式选择原紧凑格式，保留完整 trace 能力。
3. 将 SharedSequence 性能重构移出提交；提交使用原 Vec/切片接口，重构连同测试保留在暂存层。
4. 将账本撤销后在精确提交中无生产消费者的采样标记、frame 查询接口移至暂存层，保留浮点消费者及挂起修复。
5. 验证精确候选、暂存组合、工作区组合，限定 make solve smoke；独立 index amend，并核对其他文件和已有增量。

## 实施结果

已 amend 为 `ef4ea1df7041c7aa7f93095b9eca3026383939c2`，父提交仍为 `b18d6b7`；取代 `8545e7c`，未 push、未提交父仓库 gitlink。

- 提交只涉及 `isla-lib/src/executor.rs`、`isla-lib/src/tracetool/itrace.rs`、`src/isarch/exec.rs`。`frame.rs` 和 `execution_limits.rs` 与父提交逐字相同。
- 增加独立的 `set_compact(bool)`；catalog 绑定只改变索引，保留当前输出模式。新建或重新 configure 的 handler 默认完整格式；solve 在原绑定位置显式调用 `set_compact(true)`，维持原紧凑输出。没有增加 CLI 或重构执行回调。
- 精确提交恢复 `Vec` 存储和 `records()` 切片接口，移出 SharedSequence、分块、迭代器、自定义析构及其配套测试。它们完整保留在暂存组合中，并通过组合测试。
- `sampled_execution_domain`、采样写入/查询、`LocalFrame::function_name()` 及相关测试移至暂存层，与原浮点消费者一起保留。未撤销浮点的 mapping、状态物化、IR、原语、配置或脚本。
- 原未暂存 worker panic 完成记账与 trace writer 唤醒修复保持原层次；所有其他 index 条目和其他已有修改文件逐字节核对保持。新增加的 staged 差异正是从原提交移出的代码，不是丢弃后重写。

## 验证

证据目录 `isla/target/catalog-boundary-20261005/`；`candidate/`、`staged/`、`worktree/` 分别对应精确提交、暂存组合、完整工作区组合。cargo 命令离线、串行测试，单命令外限180秒；共享 `isla/target` 构建缓存。逐命令、耗时和退出码见 `checks.json`。

| 版本与命令 | 结果 |
| --- | --- |
| 原 HEAD 加 `runtime_catalog_binding_preserves_full_trace`：`cargo test --offline -q -p isla-lib --lib --features itrace,smt-thread-interrupt runtime_catalog_binding_preserves_full_trace -- --test-threads=1` | 红例按预期失败：绑定 catalog 后缺少完整指令行，`red.log` |
| 候选：`cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --test-threads=1 --skip isarch::target::tests::rv64_target_trait` | 64库＋24bin通过；过滤既有x0失败 |
| 暂存／完整组合：同上 | 82＋24／83＋24通过 |
| 候选／完整组合：`cargo test --offline -q -p isla-lib --lib --features itrace,smt-thread-interrupt executor:: -- --test-threads=1` | 82／84通过 |
| 候选／完整组合：上条过滤改为 `tracetool::itrace::` | 53／58通过；包括完整格式、显式紧凑模式、重新配置与 catalog 重绑定；组合版包含共享存储测试 |
| 候选默认 features：`cargo test --offline -q -p isla --lib collector_preserves -- --test-threads=1`；`cargo check --offline -q -p isla --bin isarch` | 均通过 |
| 三份源码 `cargo fmt --all` 后 `cargo fmt --all -- --check` | 通过 |
| 候选：`make solve ALL=MRET THREADS=1 ITRACE=1`，离线构建，整命令外限300秒 | 退出0；4 gen、5 trace路径签名；JSON内容与旧8545e7c的MRET输出相同，分支边、签名、紧凑格式统计逐行一致 |

MRET IR SHA-256 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`，配置 `71fb63e105331a0f329261c636e55446af42ba0367c96e45c9b49cb60332ad2d`，受测运行器 `7281d4e1ca6f8ad2c742b6fde7ea9aa03feb8279e2d8d56adb127529a12ae917`；核账见 `smoke.json`。限定MRET对照不代表其他指令等价或全量完成。未跑全量solve、全isla-lib或硬件重放。

## 边界核对

`after.json` 确认提交、index和工作区与各自已验证版本相同；原其他文件与index条目保持。后续若提交完整暂存区，将一并带入本轮移出的共享存储重构及浮点接口，需按其独立职责审阅，不能称为纯catalog提交。此前8545e7c的验证及结构说明保留为历史，现行提交不再包含前缀共享。

## 后续：两项 itrace 改动独立提交（2026-10-05）

用户明确要求将共享前缀存储和 writer 条件变量唤醒另建一个提交。实施目标是从原暂存/未暂存层精确提取这两项及测试适配，保持 ef4ea1d 不变；不纳入浮点、采样/frame 查询或 worker 异常记账。先从 HEAD 构造隔离候选、运行定向测试及工作区 smoke，再用独立索引提交并逐项核对原工作区和其他暂存条目。

已完成为 `64f74f3e0e513c5cc6da146d7606f05e4fb2938c`，父 `ef4ea1d`。只改 `isla-lib/src/tracetool/itrace.rs`、`isla-lib/src/executor/frame.rs`、`isla-lib/src/executor.rs`；后两者仅含共享存储的测试适配。新提交树 `21518ccfa154007603350d575da7107d7bf59790`。源码工作区逐文件哈希不变，主索引仅同步已提交的 itrace writer 改动，其他条目逐字不变。itrace.rs 已无暂存或未暂存差异；worker 异常记账仍未提交。本次复用既有实现与回归测试，未新增生产逻辑。

独立候选验证（均退出0）：

- `cargo fmt --all -- --check`。
- `cargo test --offline -q -p isla-lib --lib --features itrace,smt-thread-interrupt tracetool::itrace:: -- --test-threads=1`：58项。
- 同命令筛选 `executor::`：83项。
- `cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --test-threads=1 --skip isarch::target::tests::rv64_target_trait`：64库＋24bin，过滤既有x0测试。
- `cargo check --offline -q -p isla --bin isarch`。

完整工作区另执行 `make solve ALL=MRET THREADS=1 ITRACE=1`，退出0、4 gen、4条带 path_signature 的trace。该运行包含未提交浮点支持，不能称为精确提交的solve验证。本次 IR SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，配置 `71fb63e105331a0f329261c636e55446af42ba0367c96e45c9b49cb60332ad2d`，binary `bd884fb4502d65d02b66934ded189cf8f8640e7bd48558e7274db6459ffbb3f7`；未与前轮不同IR的trace计数作等价断言。

证据在 `isla/target/itrace-commit-20261005/`：候选源码、checks.json及各命令日志、smoke.json及运行前后产物、commit.patch、after.json。未跑全量solve或硬件验证；未push、未提交父仓库gitlink。上文“共享存储与writer仍未提交”仅适用于 ef4ea1d 刚完成时，当前由本节接续。

## 容量类型与比较运算符 amend（2026-10-05，完成）

用户选择重载比较运算符并要求 amend itrace 提交。计划仅在 itrace.rs 引入 ChunkCapacity::Limited(usize)/Unlimited，默认 Unlimited，通过 usize 与容量类型的 PartialEq/PartialOrd 保持长度比较可读；共享时仍换块。先用超过旧256阈值的独占序列回归确认红例，再验证无限和有限256配置、分叉共享及输出顺序。隔离候选验证后 amend 64f74f3，保留原其他暂存/未暂存改动。证据目录 `isla/target/itrace-capacity-amend-20261005/`。

实施结果：`64f74f3` amend 为 `5c376fb091ca1178448e99c0bdc0e3dc12d7fd58`，父仍为 `ef4ea1d`。本轮仅修改 itrace.rs，新增 ChunkCapacity 和 usize 跨类型比较，配置常量默认 Unlimited；有限配置可写 Limited(256)。长度判断保持 `self.head.len() >= ITRACE_CHUNK_CAPACITY`。没有新增算术重载、运行时配置入口或更改writer。既有块测试的数据量改用明确有限数值，不对无限容量做乘法。

验证：旧实现新增独占1025条记录测试失败（在256条分块）；修改后 Unlimited 和源码切换 Limited(256) 两次各60项 itrace 测试通过，覆盖比较边界（含 usize::MAX）、分块长度、分叉共享、记录顺序及既有完整/紧凑渲染字节对照。最终精确候选 executor83、isla64库＋24bin通过（过滤既有x0失败），默认编译、cargo fmt和diff检查通过。隔离候选执行 `make solve ALL=MRET THREADS=1 ITRACE=1`，IR_FILE/ISA_CONFIG显式指向工作区 rv64d.ir 与 configs/riscv64_difftest.toml，退出0、4 gen、5条签名trace；产物留在隔离候选 output，不覆盖主工作区输出。IR SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，配置 `71fb63e105331a0f329261c636e55446af42ba0367c96e45c9b49cb60332ad2d`，binary `62a9c3152f9c3e652b49212b602676142189c4ae4aad03fef03b249d3b41d13f`。未跑全量solve或硬件。

amend后原暂存补丁和未暂存补丁分别与本轮前逐字相同，其他跟踪文件哈希未变；itrace.rs工作区、暂存区与提交一致。证据见上述目录的 red/unlimited/finite/executor/isla/default/fmt/smoke 日志、checks.json、smoke.json、amend.patch和after.json。未push、未提交父仓库gitlink；上节64f74f3的结果保留为历史。

## CLI 可关闭 catalog（2026-10-05，实施中）

用户要求新建提交，允许开启 itrace 同时关闭 catalog。计划在现有CLI增加 `--no-itrace-catalog`，默认不变；将布尔参数传入 solve_state_main，仅条件化现有建表调用，保持 compact 和轨迹记录。热点仅 `src/isarch_main.rs` 与 `src/isarch/exec.rs`。从当前 HEAD `5c376fb` 提取独立候选并保留原暂存/未暂存层。验证先运行开/关真实CLI回归（旧版拒绝新参数），再检查新版本catalog段有无、轨迹及生成用例一致，执行定向测试、默认编译和make solve。证据放 `isla/target/catalog-cli-20261005/`。

### CLI 实施和验证完成

新提交 `d21ad62acdbd209732e30ee6791b347d9afbab43`（父 `5c376fb`），两个源码文件 +8/-2；原浮点及其他暂存/未暂存改动逐层保留。`--no-itrace-catalog` 仅跳过 runtime catalog 建表与输出，默认仍开启；`configure` 原有清空逻辑防止跨clause残留，compact选择保持不变。关闭后分支源码位置为unknown，不做catalog后继校验；真实边与签名仍记录。

TDD真实CLI旧版关闭场景返回1（不识别新参数），开启场景正常。精确候选和完整工作区各运行 `regression.py <binary> <label>`，分别用 `-A rv64d.ir -C configs/riscv64_difftest.toml -T 1 --timeout 60s --smt-timeout 1m --itrace=<path> [--no-itrace-catalog] solve-state --clause=MRET` 对照：catalog段有无正确，compact轨迹/实际边/签名保留，指令/编码/执行结果/签名一致。首次将完整gen逐字比较的检查失败于部分寄存器见证值；相同catalog开启配置重复运行也出现变化，故改为比较上述稳定观察，未声称具体状态逐字一致。修订后精确候选和工作区均PASS。

精确候选定向itrace、executor、isla库与isarch测试、默认feature编译和fmt均通过，命令/结果见 `checks.json`（沿用过滤既有x0测试）。完整工作区 `make solve ALL=MRET THREADS=1 ITRACE=1` 退出0、4 gen。具体IR、配置、二进制SHA见 `evidence.json`，精确提交树见 `after.json`，全部位于 `isla/target/catalog-cli-20261005/`。未跑全量solve或硬件；未push、未提交父仓库gitlink。
