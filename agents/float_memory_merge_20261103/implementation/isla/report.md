# Isla float→memory 候选合流实施记录

本轮只修改独立候选 `.worktree/merge-float-memory-20261104/isla`，输入为 memory `bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57` 与 float `591693df2bc32019ea300511509ed683df09522e`。原 memory 工作树及其 README/run.mk 未提交补丁保持不动。五份 IR、来源侧车与 manifest 由验证负责人从合并模型重新生成和安装，不作文本合并。

## 实施合同

- 合并 `memory-events`、`pre-memory`、`post-memory` 与浮点侧 `requested-instruction`、`isa-state-complete`、`isa-state-post`、三种指令表示、`state-domain`，保留既有 `isa-state`、`ret_val`、标签、`summary`、`diagnostics` 和编码拒绝计数。RV32/RV64 的目标寄存器清单保留 FPR、VPR、fcsr 与内存侧必需状态。
- 每条编码见证在最终 Sat 后取得一个 `Model`；指令参数、汇编编码、完整寄存器前后态、返回值和按时间顺序重放的访存事件均在同一模型作用域内具体化。必需值失败时记录不完整诊断、计入错误并拒绝整例；首次触碰为写且未观测的旧字节仍是合法自由初态 `null`。结束阶段保留 memory 的缓存 Sat 模型、独立终值时间盒、Unsat dump 和 float 的编码辅助域/完整执行域可达性验证。
- ExecuteAs 使用原 frame 的 `new_call`、原任务 ID 和 checkpoint 续执行，保留第一段寄存器与内存写入。`initial_state` 与符号 CSR 同名时复用同一符号并叠加位约束；具体固定初态的位约束也可在已有具体位串上验证。`run.mk` 保留官方 Z3、`qffp`/`qfaufbv`、tracetool、`SOLVE_CONFIG` 与 `ISA_CONFIG` 覆盖入口。

## 验证与边界

- 官方 Z3 前缀 `~/.local/opt/z3-official-1fd1d3613`；独立 Cargo target 目录。`cargo check --bin isarch --features smt-thread-interrupt` 通过；`cargo test --lib --features smt-thread-interrupt,tracetool -- --test-threads=4` 为 197/197 通过，本轮本地日志。两项命令均指定用户目录下的官方 Z3 lib 搜索路径与 RPATH；正式可复现命令以 `scripts/run.mk` 为准。
- P3 回环独立夹具未固定 `cur_privilege` 时，合并、原 memory、原 float 三份 IR 对合法 `lb` `0x40000003` 都可探索 `VirtualSupervisor/VirtualUser`，并在 `extensions/cfi/zicfilp_regs.sail:31/32` 抛出“Hypervisor extension not supported”。原异常没有被过滤；夹具固定 Machine 后合法编码测试通过。生产 collector 的辅助译码寄存器按同一最终模型将 `cur_privilege` 具体化。完整命令见本轮原始测试日志，不能据此宣称所有架构状态下的译码完整覆盖。
- `cargo fmt --all` 已执行；随后恢复两份非本代理负责的浮点永久 runner 文件的工作区格式改动，保持其索引内容。独立 Sol 对最终暂存树 `88a930026ca31c23225d5f9509b2b23502d14f77` 的源码与探针签收后，已形成 Isla 双亲合并提交 `7cce7834b6f1376293dfce1d52b7e944fa237941`（第一父 `bdd047bc`、第二父 `591693df`），提交树与签收树一致，工作树干净。正式 Release、永久 IR 与动态矩阵由验证负责人按该提交另行记录；此前测试不冒充完整验收。

已暂存的本轮生产/文档路径执行定向 `git diff --cached --check -- <本轮路径>` 无错误；全量暂存差异的历史 `agents/validation/.../case-086/verify-diff-trace.log` 含原有尾随空格，保持原日志字节不变，不把全量检查标为干净。

独立 Sol 最终复核见[源码签收](../../review/core-final-report.md)。为消除测试顺序依赖，另在 `isla-lib/src/executor.rs` 的5项测试与 `isla-lib/src/primop.rs` 的9项测试各加入一次显式SMT初始化；生产逻辑未变。官方Z3下 `cargo test -p isla-lib --lib --features smt-thread-interrupt,tracetool --offline` 默认并发394/394通过；Sol另以14个fresh进程逐项复验14/14。

## 后续测试入口与动态边界

首次双亲合并提交 `7cce7834` 后，默认并发 `cargo test --workspace --lib` 暴露47项测试顺序依赖：45项独立测试直接建Solver却未初始化全局策略，另2项`catch_unwind`把未初始化panic误当预期配置panic。仅在四个`src/isarch/`测试模块各测试入口显式调用已有`configure_tastic(Qfaufbv)`，两处负例再核预期panic文字；生产字节未变。独立Sol签收完整树`3d852a5fac6a07ae906e502a430a8ee14a65c075`，workspace默认并发全部通过，47项fresh进程均通过。附加测试提交`4d085b14aa0f987436b86d72f41fab1df9e9a132`指向该树，第一父是双亲合并提交，工作树干净。

完整`LOAD_FP`在同一FD配置与qfaufbv/T1下，合流版为`partial`、4错误、0见证；其中2条是`zvmem_read_addr → zzzeros`的符号宽度错误，2条是严格译码回环遇到Poison。原memory bdd版同配置/旧IR也为`partial`、6错误、0见证，6条均有相同的`zzzeros`错误；两版路径数和IR不同，不把错误计数当作同一用例一一对应。`split_misaligned`产生动态宽度而`zeros`要求已证明的固定宽度，这是继承边界，本次未改生产。

VFMERGE此前固定机器字探针的启动Assertion来自测试输入：CLI中的vtype/fcsr使用短十六进制值，位宽不匹配。验证负责人改用旧float已见证的合法机器字`0x5c005fd7`及足宽的Machine、mstatus、vtype、vl、vstart、fcsr钉值后，独立最小探针正常退出且生成1条退休见证；四种vstart动态矩阵仍由验证负责人按最终提交另行记录。

最终`4d085b1`输入绑定的vstart定向矩阵经只读复核：VFMERGE与VLSEGTYPE各四种`vstart`（0、等于`vl`、大于`vl`、全1高值）共8项均exit0、`summary.finished`、各1条匹配固定机器字的退休见证。VFMERGE活动路径把vr31低32位从`0x12345678`写为`0x3f800000`，其余三种早退保持原值；VLSEGTYPE活动路径有1条读事件，其余三种早退无访存事件；八项执行后vstart均为0。该结果是固定机器字和完整钉值的限定验证，输入及原始JSON由动态验证负责人另行记录。

STORE/C_LD 原域 Make 均为`partial`。STORE的922条辅助译码回环 Poison 诊断、112条顶层Poison，以及C_LD的7条顶层Poison已分账；独立临时探针从最终模型捕获STORE两类及C_LD一类代表，在原 memory bdd047bc程序/旧IR与合流程序/新IR的同具体状态直接复放中，三条代表均触发相同的模型内部异常。旧版回环错误不计入summary.errors的机制差异已注明；此限定结论不覆盖剩余路径，原memory完整域对照仍在途。具体命令、输入、源码位置及复放边界见[Make `partial` 边界](full-make-boundary.md)。
