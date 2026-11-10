# itrace / ftrace / btrace 重组（2026-10-06）

## 目标与边界

用户要求移除 catalog/compact 概念及实现，按逐指令、函数调用/返回和实际条件分支组合轨迹；相关后续修改整合为原 ef4ea1d 的替代提交。writer 阻塞等待/唤醒独立提交。遵循原执行流程局部修改，不纳入浮点支持或 worker 异常记账。

在 `isla/.worktrees/trace-composition`、分支 `refactor/trace-composition-20261006` 从 b18d6b7 实施；主工作区当前 d21ad62 的 HEAD、index、工作区分层备份在 `isla/target/trace-composition-20261006/`。实施完成并验证三层兼容后迁回，迁回前核对主工作区无外部变化。

## 实施步骤

1. 用旧提交作参照保留共享前缀容量语义，分离 writer 修改。
2. 先写组合轨迹、真实执行位置及分支/函数事件回归；旧实现运行红例。
3. 删除全局运行时指令表、建表查询及完整/紧凑模式；逐指令记录直接取实际 IR，分支直接记录位置、来源、后继、方向及上下文；ftrace 复用 SMT Function 事件。
4. 添加可组合 CLI，保留路径签名、计数、耗时和诊断。旧 --itrace 恢复逐指令语义，ftrace+btrace 提供原省略指令行的信息。
5. 精确候选、原暂存组合及完整工作区组合验证；make solve 限定 smoke，保存版本/IR/配置/输出。
6. 建立主轨迹提交和独立 writer 提交；迁移原暂存/未暂存补丁并核对，保留回退分支及证据。

## 未决边界

用户已明确要求保留未执行分支的静态清单。btrace 在入口直接枚举实际 IR 的条件 Jump 输出 branch sites，随后独立记录实际经过的 branch_edge；不缓存查询表，不能将静态清单当作已执行证据。

## 状态

已在独立 worktree 完成实现、分层验证和迁回。主工作区 HEAD 为 c1d6bc6，原28文件暂存和两文件未暂存改动保持。旧提交链保留在 backup/trace-before-20261006，独立 worktree 保留。

## 最终实现与提交

- `9d8b9152660a501e167c84ada4322bb618b96a30`（父 b18d6b7）：组合 itrace/ftrace/btrace，整合原 ef4ea1d、共享前缀（保留无限容量语义）及后续 CLI 需求。执行点直接保存实际指令、Jump 来源/条件/方向/后继；btrace 入口仅枚举、排序并输出静态清单，不建立持久查询表。ftrace 使用已有 Function 事件，最外层入口补入同种调用事件，完成路径时投影为调用/返回文本。
- `c1d6bc6a829fa00ad8b2862bfdae057a7b34dfce`：独立 writer 条件变量等待/入队唤醒/关闭唤醒和生命周期测试，不改轨迹语义。
- 主提交涉及8文件，writer仅1文件；均未纳入浮点支持、采样查询或 worker 异常记账。实现源码不再含旧 catalog/compact API、存储或模式分支。

CLI：`--itrace=FILE` 输出完整指令，`--ftrace --btrace --trace-output=FILE` 输出函数与分支；组合全部使用 `--itrace=FILE --ftrace --btrace`。三种输出共用一个文件，多clause仍按原规则加后缀。Make 对应 `ITRACE=1`、`FTRACE=1`、`BTRACE=1`。公共签名、指令数量、函数集合、时间和诊断不依赖单一轨迹类型。旧 --no-itrace-catalog 已移除。

## 验证与证据

证据根目录：`isla/target/trace-composition-20261006/`。

- TDD：新增组合记录接口红例编译失败（red.log）；真实函数入口回归在缺入口事件时断言失败（ftrace-root-red.log），补入既有 Function 事件后通过。首次改写测试还暴露旧格式预期以及测试SMT初始化缺失，修正后复验；中间失败日志保留，不记PASS。
- 精确主候选：`cargo test --offline -q -p isla-lib --lib --features itrace,smt-thread-interrupt tracetool::itrace:: -- --test-threads=1` 60项；同命令 executor::84项。`cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --test-threads=1 --skip isarch::target::tests::rv64_target_trait` 64库＋25bin；过滤既有x0失败。
- 默认无feature的CLI定向测试及仅 `--features ftrace,btrace` 编译通过；fmt通过。命令、耗时、退出状态见checks.json。
- 独立writer：itrace61项通过；新增测试覆盖入队及时写入、并发提交不丢不重、排空、重启和空队列退出。见writer.log。
- 原暂存组合82库＋25bin、executor84；完整组合83库＋25bin、executor85；两层fmt通过。命令见layer-checks.json，均过滤既有x0失败。
- 主候选在独立worktree运行 `make solve ALL=MRET THREADS=1 ITRACE=0 FTRACE=1 BTRACE=1 IR_FILE=<主工作区rv64d.ir>` 退出0、4 gen。完整组合运行 `make solve ALL=MRET THREADS=1 FTRACE=1 BTRACE=1` 退出0、4 gen。make日志分别为smoke.log、combined-smoke.log。
- 使用同d012 IR、同配置，分别用旧精确d21ad62对新主候选、旧完整工作区对新完整组合，运行单独i/f/b、f+b、i+f+b CLI对照。静态清单、实际边、每路径签名/指令计数/函数集合和生成指令/编码/结果逐项一致；开关之间只改变选择的输出。见smoke-checks.json、combined-checks.json和各smoke/combined子目录的observations.json。ftrace新增函数调用/返回，原轨迹没有这部分，故验证存在性、顺序继承及真实入口回归，不声称旧版逐字存在同样文本。
- 精确版本：25560静态分支、1745实际边、5条签名trace；完整组合：25852静态分支、1708实际边、4条签名trace。差异来自原有未提交断言处理等改动；最初误把完整旧binary对精确新候选出现差异，重新绑定同层版本后通过，不能跨层混用数字。
- IR SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`；配置 `71fb63e105331a0f329261c636e55446af42ba0367c96e45c9b49cb60332ad2d`。旧/新精确与完整binary哈希见evidence.json。

迁移时只解决scripts/run.mk与src/isarch_main.rs两处相邻追加冲突，保留原进程管理和断言转换语义。原暂存差异逐行核对一致（run.mk只增加新轨迹参数），原未暂存新增/删除行逐字一致。其他暂存条目不变；迁回后HEAD/index/worktree与受测层一致，见layer-audit.json、resolved.json和after.json。主工作区再次fmt与两层diff检查通过，itrace.rs没有未提交差异。

未运行全量solve、全isla-lib测试或硬件重放；不据MRET推断完整覆盖或全工作负载性能。未push，也未提交父仓库gitlink或原有浮点改动。

## tracetool 平级归属修正（2026-10-06，完成）

用户指出三种工具应共同隶属tracetool，而不是让itrace成为容器。本轮在既有独立worktree做职责归属修正：公共Handler/Path/CompletedPath、writer、共享序列移入tracetool，itrace/ftrace/btrace各自保留专属记录/渲染逻辑；共享字段及提交入口改中性名称。保持输出、CLI、原执行流程与writer机制不变，作为独立结构整理提交接续已有两提交。

新备份与验证证据：`isla/target/tracetool-peers-20261006/`。先运行新公共入口红例，再验证现有功能回归、精确/暂存/完整组合及MRET对照；仅迁移受测文件，保留浮点修改层次。准备阶段主工作区未修改；以下为最终迁移结果。


已提交并迁回 `4a84366fc50405298345fac9725f5ed3abe765b4`，接续 `c1d6bc6`；旧 HEAD 备份为 `backup/tracetool-before-20261006`，独立 worktree 保留。18 文件差异主要为原 itrace.rs 拆分和公共名字替换，新增净行数55；没有重写执行器控制流。writer 机制仍来自独立前置提交。Make 的公共构建 feature 改为 tracetool。

- 公共入口：`isla-lib/src/tracetool.rs`，TraceOptions 与 TraceHandler 位于该入口，TracePerPath/TraceCompletedPath 仅库内可见。
- 平级工具：`tracetool/itrace.rs`、`ftrace.rs`、`btrace.rs`；公共组合、writer、共享序列各自分文件。btrace 继续输出未执行分支的静态清单。
- 新层级入口测试先红后绿；精确候选 tracetool 62、executor 84、isla库64＋bin25通过。默认CLI及仅ftrace,btrace编译通过；暂存层82＋25／executor84，完整层83＋25／executor85通过。各层fmt通过。isla库测试按既有记录跳过 `isarch::target::tests::rv64_target_trait`，并非全套测试全绿。
- 精确与完整层分别运行 `make solve ALL=MRET THREADS=1 ITRACE=0 FTRACE=1 BTRACE=1 IR_FILE=<主工作区rv64d.ir>` 退出0；CLI单独i/f/b、组合fb/ifb均对照同层旧二进制。静态清单、实际边、函数call/return序列、路径签名、计数、生成指令/编码/返回值一致；精确25560 sites／1745 edges／302函数事件，完整25852／1708／284，均4 gen。没有比较耗时字段或声明全输出逐字一致。
- 实際命令、配置、日志和回归数据：`isla/target/tracetool-peers-20261006/{checks.json,layer-checks.json,smoke-checks.json,combined-checks.json}`；make日志为smoke.log与combined-smoke.log。最后仅注释/测试名及Make公共feature变化，完整make已覆盖最终feature。
- 对原28文件暂存和两文件未暂存内容分别做三方合并。仅exec.rs的encdec格式发生冲突，保留原concrete_regs取值。机械改名＋rustfmt归一化后，两层增删行与原层完全一致（layer-audit.json）。迁移后逐文件核对受测暂存/完整快照，其他index条目未改变（after.json）。未提交浮点修改、未push、未运行全量solve或硬件回归。

## 按原提交重做（2026-10-06，完成）

用户纠正提交方式：平级归属修改应合入原轨迹提交，不应追加第三个修正提交。新建分支 `refactor/trace-recommit-20261006` 和 worktree `isla/.worktrees/trace-recommit`，从 b18d6b7 重做为：

1. `9da2eaa993e0498e63e22367bb4ebee76ff8485f`：平级 itrace/ftrace/btrace，包含此前主轨迹与结构修正。
2. `48619f2f974a0bc2ad81374cb1982dbdbb4034d7`：独立 writer 等待/唤醒，仅 writer.rs 和 tests.rs，+62/-3，与原 writer 改动对应。

第一提交的 `cargo test --offline -q -p isla-lib --lib --features tracetool,smt-thread-interrupt tracetool:: -- --test-threads=1` 61项通过，cargo fmt通过。最终提交tree与旧4a84366完全相同，因此前节精确/暂存/完整层验证继续适用，没有重新声称运行整套测试。主分支仅CAS更新引用，index所有条目和28个未提交文件SHA均保持，未改工作文件；旧链保留在 `backup/trace-pre-recommit-20261006`。证据 `isla/target/trace-recommit-20261006/{base-test.log,result.json}`。未push。

## itrace 数据归属修正并重做两提交（2026-10-06，完成）

用户明确：工具平级不要求把所有数据泛化为trace；itrace数据可被其他工具复用，但仍属于itrace。本轮沿用隔离worktree，新建 `refactor/trace-ownership-20261006`，amend轨迹提交后重新接上writer。现行链为 `69cf43adf95df0d9ba25b10e3626c0f80c45025f`＋`a9884b20dac3dd8965bee90b30f9e9f8b04000d0`；前节9da2eaa/48619f2为历史。

将common::TraceRecord恢复为itrace::ItracePerInstr；record_summary/records/record_count移回itrace.rs，存储名为itrace_records。TracePerPath仍组合指令记录、函数事件、分支条件/边；配置、完成路径提交和writer保留公共命名。各工具现有采集入口保留，不新增框架或改变采集/输出算法。相对此前最终源码只改README、common.rs、itrace.rs，净行数不变。

第一提交tracetool定向61项，writer后62项通过，cargo fmt通过；隔离worktree运行 `make solve ALL=MRET THREADS=1 ITRACE=1 FTRACE=1 BTRACE=1 IR_FILE=<主工作区rv64d.ir>` 退出0。日志 `isla/target/trace-recommit-20261006/ownership-{test,writer-test,smoke}.log`。本轮未重跑前版全部组合对照或完整浮点测试，不把旧版结果视为新一轮验证。

迁回前后原暂存binary diff、未暂存binary diff逐字一致，28个原未提交文件SHA一致；证据 `isla/target/trace-ownership-20261006/result.json`。旧链备份 `backup/trace-before-ownership-20261006`，未push。

## 临时分支清理（2026-10-06，完成）

经用户确认，删除refactor/trace-ownership-20261006、refactor/trace-recommit-20261006、refactor/trace-composition-20261006、backup/trace-before-ownership-20261006、backup/tracetool-before-20261006。移除两个干净的trace worktree，清理三个失效的/tmp worktree登记。前文“保留worktree/备份”描述为当时状态。

保留backup/trace-before-20261006与backup/trace-pre-recommit-20261006两个回退点，以及所有其他功能分支。两个worktree的output/outputs已备份到isla/target/trace-cleanup-20261006/，共享target未删除。清理后HEAD、index条目、工作区状态及原未提交文件SHA与清理前一致；证据在同目录。未操作远端分支。
