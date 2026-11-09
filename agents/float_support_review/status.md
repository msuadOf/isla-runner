# Isla 浮点分支审查状态（更新至2026-10-08）

**两分支试合并核对（2026-10-08，完成／意图一致）**：`be1296b`＋`09fe582` 在隔离工作树解决float.rs／exec.rs两处冲突后，候选相对原isla最终内容986同／15异／新增14／无缺失，包含未回写原工作区的通用及IR修复。用户澄清“等价”指代码意图及预期效果，允许bug fix；按此口径一致，前轮否定结论仅限文件树／精确行为。另已按用户要求创建干净detached基线工作树`.worktree/isla-float-support@7b7337b`，原工作区保留。候选93＋25、浮点10、集成15、默认编译／fmt通过；原HEAD／索引条目／两层补丁／1001源码不变，未移动分支或提交。未make／全量／硬件。[差异与证据](merge-check-20261008.md)。

**仅浮点修复交付（2026-10-08，限定PASS）**：`be1296b`，两个`fix(scope): 中文说明`提交补齐其他IR普通helper并恢复快速FPR副作用；1615helper、180状态＋20guard及4组make通过，RV32 SD31正确，独审通过。原isla未变，未push／全77／硬件；修前报告保留。[交付](../float_only_review/fix.md)。


**仅浮点分支独立复审（2026-10-08，发现新增P1）**：主审与gpt-6-astra high确认另外4份自带IR未随全局分派退役迁移；基线可执行，分支NoFunction，公共旧IR入口退出0但0gen。d012继承FPR Dirty错误；327例／67helper及BF16无活动元素修复通过。此前限定PASS仅保留原测试范围，不代表原行为全部正确。[复审报告](../float_only_review/report.md)。


**2026-10-08 通用审查修复交付**：三个 fix 已接至通用分支 `4b141eb`；MixedBits/宽物化回归修复，MPP 保留模型 reset 例外。精确与现有浮点组合测试及 V128/V256 MRET 四组通过；原isla与其他浮点分支未移动，通用工作树浮点剩余保留。[交付与版本边界](../general_support_review/fix.md)。


**仅浮点分支（2026-10-08，已完成／限定PASS）**：feat/float-only-20261008从7b7337b直接新增28f626a至d04883b六提交，无通用提交/未提交层，工作树干净。浮点10、legacy35、Target23、库68＋bin25及MRET4/BF16 39 gen通过；基线既有x0失败单列跳过。原isla保持不变。[记录](float-only-20261008.md)。


**浮点专用提交整理（2026-10-07，已完成／限定PASS）**：新工作树isla-float-20261007在2792afd上新增bc7bc59至2d46ce7六类提交，工作树干净；浮点10、legacy35、Target35、库83＋bin25及MRET4/BF16 39 gen通过。仅runner增加MixedBits兼容修正，原两工作树不变，已知通用回归未修；详见float-split-20261007记录。

**2026-10-07 通用分支独立审查**：`2792afd` 相对 `7b7337b` 确认两个 P1：MixedBits 消费者 Type、VLEN256 MRET 4 gen→0 gen（退出仍 0）；主审动态对照与独立 gpt-6-astra high 一致。本轮未改生产代码，旧限定 PASS 不覆盖这些边界，分支需修复后复验。[报告与证据](../general_support_review/report.md)。


**通用提交按类型重做（2026-10-07，已完成）**：4089545已替换为416b94f至2792afd的8类提交，各层定向测试通过；最终tree一致，原工作区及浮点剩余不变。工作树/分支沿用，未push；详见通用归并记录接续节。

**通用修改归并（2026-10-07，已完成）**：在`.worktree/isla-general-20261007`新分支已带入全部Isla改动，`4089545`一个commit收纳通用部分；浮点剩余未暂存，原工作区保留。精确候选定向测试及候选/完整组合MRET通过。[范围与验证](general-split-20261007.md)。

**局部结构修整（2026-10-07，已完成）**：四文件内联单调用逻辑、移除空转发、调整对象归属并恢复match布局；基线82、修改后82库＋25bin＋10浮点、默认编译/fmt及MRET通过。原索引和注释保留，未提交。[计划与验证](local-structure-20261007.md)。

**worker panic独立提交（2026-10-06）**：`7b7337b`仅executor.rs +25/-2，保证任务panic后记账并继续传播；候选有界panic/执行器回归、编译/fmt通过，原浮点暂存改动和工作区保留，未push。[证据](solve-process-commit-20261006.md#接续worker-panic-记账独立提交)。

**smtperf测试独立提交（2026-10-06）**：`d9f0fe0`仅修宏参数和测试Z3上下文；精确候选两种feature各4/4、fmt通过，其他改动原分层保留，未push。[记录](solve-process-commit-20261006.md#接续通用-smtperf-测试修正独立提交)。

**solve进程管理独立提交（2026-10-06，已完成）**：`1eddd68`提交四个脚本中的监督/清理及测试；候选12项、工作区MRET通过。浮点入口仍暂存，其余修改与原分层不变，未push。[计划和验证](solve-process-commit-20261006.md)。

**轨迹临时分支清理（2026-10-06）**：已按确认名单删除5个临时分支、移除两个trace worktree并清理3个失效登记；保留两个回退点和其他功能分支，运行输出已备份。主HEAD、暂存区及未提交文件核验不变。[记录](trace-composition-20261006.md#临时分支清理2026-10-06完成)。

## itrace 数据归属与两提交重做（2026-10-06）

现行 `69cf43a`（轨迹）＋`a9884b2`（writer）。逐指令数据恢复ItracePerInstr并归itrace.rs，公共层组合itrace_records；各工具独立采集入口保留。61/62项定向、fmt、三开关MRET通过；原暂存/未暂存补丁逐字不变，未push。[记录](trace-composition-20261006.md#itrace-数据归属修正并重做两提交2026-10-06完成)。

## 轨迹提交重做（2026-10-06）

按用户要求将平级修正并入原轨迹提交：现为 `9da2eaa`（轨迹）＋`48619f2`（writer），已从新分支迁回。最终tree与此前4a84366完全相同，暂存区及未提交文件逐项不变；以下旧hash为历史记录。[记录](trace-composition-20261006.md#按原提交重做2026-10-06完成)。

## tracetool 平级结构修正（2026-10-06，已迁回）

`4a84366` 将三种工具分别归入 itrace.rs/ftrace.rs/btrace.rs，公共状态和writer归tracetool；CLI及静态未执行分支清单保留。三层定向测试和同层MRET对照通过（跳过既有x0失败），原28暂存文件及两文件未暂存层保留。未push、未跑全量。[实施与证据](trace-composition-20261006.md#tracetool-平级归属修正2026-10-06完成)。

## 轨迹组合重组（2026-10-06，已迁回）

主轨迹`9d8b915`＋独立writer`c1d6bc6`已从worktree迁回，替代旧三提交；ftrace复用Function事件，btrace保留全部静态分支及实际边，移除旧查询表/模式机制。精确、暂存、完整三层回归与MRET对照通过；原28文件暂存和两文件未暂存改动保持，旧链备份于backup/trace-before-20261006。未push、未跑全量。[实施与证据](trace-composition-20261006.md)。


## catalog CLI 已提交（2026-10-05）

`d21ad62` 新增 `--no-itrace-catalog`，默认保持catalog开启；开启itrace时可单独关闭建表与catalog输出。两文件+8/-2，原暂存/未暂存改动保留。精确候选和工作区开/关CLI对照、定向/编译/fmt及工作区MRET通过，未push。[详细记录](catalog-boundary-20261005.md#cli-实施和验证完成)。


## itrace 容量比较 amend（2026-10-05）

`64f74f3` 已 amend 为 `5c376fb`：ChunkCapacity 表达 Limited(n)/Unlimited，重载长度比较，默认无限，仅共享后追加触发换块。有限256/无限各60项 itrace、executor83、isla64＋24、编译/fmt通过；精确候选 MRET退出0、4 gen。原暂存及未暂存补丁逐字保留，未push。[详细记录](catalog-boundary-20261005.md#容量类型与比较运算符-amend2026-10-05完成)。


## itrace 两项独立提交（2026-10-05）

已按用户要求新建 `64f74f3`，父 `ef4ea1d`：共享前缀存储＋writer 条件变量唤醒及必要测试适配。精确候选 itrace58、executor83、isla64＋24、默认编译及fmt通过；完整工作区 MRET退出0、4 gen。itrace.rs已无未提交差异，其他原暂存/工作区内容保留；worker异常记账仍未提交。未push。[版本与验证记录](catalog-boundary-20261005.md#后续两项-itrace-改动独立提交2026-10-05)。


## catalog 提交边界收缩（2026-10-05）

已将 `8545e7c` amend 为 `ef4ea1d`，只剩 executor/itrace/exec 三文件。catalog 不再切换输出模式，solve显式选择紧凑格式；精确提交恢复Vec/切片，SharedSequence和无生产消费者的采样/frame接口移至暂存层，原浮点与挂起修复保持。候选64＋24、暂存82＋24、工作区83＋24，executor82/84、itrace53/58及默认/格式检查通过；限定make solve MRET退出0、4 gen，JSON与trace观测同旧版。未跑全量，未push。[完整记录](catalog-boundary-20261005.md)。

## catalog 局部修补 amend（2026-10-03）

已将 `323021b` amend 为 `8545e7c`（父 `b18d6b7`），撤销终态账本和 case-id，恢复 exec.rs 原回调/排序/早退；生产区相对父提交仅 +13/-3。保留 catalog、实际边、共享前缀及路径签名关联；签名不保证唯一。原浮点/IR/脚本/挂起修复继续按原暂存层保留，工作区域说明改放顶层 `state-domain`。候选64＋24、暂存82＋24、工作区83＋24及执行器/itrace/default/格式通过；`make solve ALL=MRET THREADS=1 ITRACE=1` 退出0、4 gen关联通过，未跑全量。旧 summary/terminals schema 和历史 PASS 限原版；[实施与完整验证](catalog-local-patch-20261003.md)。

## 旧 catalog 测试挂起（2026-09-30）

后续：已按用户要求终止进程并修复 worker 异常记账/panic传播、writer条件变量阻塞唤醒。TDD红例10秒超时，修后通过；原挂起测试、executor84、itrace72、isla库83均通过（每命令10秒外限，库83过滤已知x0测试）。全isla-lib因Z3枚举重名失败，未跑make solve；原始旧候选panic仍未恢复。详见 [验证记录](../../docs/RESULTS.md)。下段为修前现场。

PID 1363231 的 catalog-minimal 候选运行约34小时未结束，不是 PASS。trace writer 空队列 yield 占满一核；测试等待 pending=1，但 worker 已退出。候选及当前源码存在异常退出完成记账漏洞，原始 panic 待恢复。未改代码或杀进程；下一步补有界 panic 回归并修生命周期与阻塞唤醒，见 [findings](../findings.md)。

## 73df 标量 `execute` arm 限定核账（2026-09-30）

冻结 Sail 来源与 51 份完整 trace 对照，51 个标量 clause 的 `execute` 本体 242 个词法 arm 中观察到 228 个；未观察的 14 个均为固定 RV64／FLEN64 下 `xlen`／`flen` 断言失败臂，当前配置不可达。这个数字不含共享 helper、译码 guard、短路因素或 ITE 数值选择；完整源码分母与 branch 闭合仍未签。逐项口径见[findings](../findings.md)。

## catalog 限于观测信息（2026-09-29）

已按用户授权 amend 为 `323021b`，父仍 `b18d6b7`，提交仅含catalog/关联记录。恢复原Timeout/SMT退出策略，complete只报告，原8个早退/1次最终SMT检查和注释均保持。精确候选64＋24、暂存组合82＋24、完整工作区83＋24及默认定向/编译/fmt通过，过滤已知x0失败；未跑全量solve/硬件重放。原27文件暂存、exec.rs未暂存浮点逻辑分层保留；[完整证据](catalog-commit-review-20260929.md#catalog限于观测信息2026-09-29)。31523ab及更早记录为历史阶段；当前退出0不再隐含账本complete。

## XiangShan GitHub 浮点相关 issue 全量索引（2026-09-29）

已对 `OpenXiangShan/XiangShan` 898/898 条公开 issue 逐条审标题、正文及公开时间线；37 条首屏未完的时间线补第二页，最终 898/898 完整。四名 Sol 子代理与主代理按 180/180/180/180/178 分批各写[逐条账本](github-issue-audit/README.md)，机器校验 898 编号顺序、无重漏、每条评论数守恒。补查发现 #2890 的 `vfmacc.vf` SAXPY 工作负载经 PR #3140 修复但根因未证为 FP 单元；#3735 的 FP 调度参数笔误经 PR #3749 修复、无运行时失效证；#4980 是 MMIO `fld` 被 DiffTest 跳过时 FS 状态未同步；#6410 仅推断可能影响 FP move，未实测并被上游关闭。[表格清单](xiangshan-github-float-issues.md)现列 27 条直接相关 XiangShan 报告（含已修、开放及未确认）、17 条重复／参考模型／被否定或不独立报告，另列 7 条性能、配置代码或构建交集；主表 12 open／15 closed。GitHub 关闭与当前本地 emu 是否含修复分开记账。[全量快照](github-issues-all-20260929.json) SHA-256 `b6af07e4…0c15e`、[完整时间线](github-issue-details-20260929.json) SHA-256 `af17f7dc…990e29`、[总审计](github-issue-audit/summary.json) SHA-256 `491c2e30…af5cbb`。本轮未重跑硬件或浮点求解。

## 77 项直接入口完整 trace 批次（2026-09-29，整组未通过）

- 冻结 `e893` IR／`196809a4` 运行器／FD 配置，无抽样运行 `make solve-fd-nonmem` 的 77 项、`-j4`、每目标 300/270/30 秒和完整 ITRACE；77 项均启动退出。51 个标量和 4 个向量自然完成，合计 55 份完整 JSON／1432 条 `gen`；另 22 个向量外限 124、无最终 JSON。进程、JSON、终态与 trace 逐项核账错误 0；结束后无遗留 stage 进程。四个完成向量是 `VFMERGE`、`VFMV`、`VFMVFS`、`VFMVSF`。这仅是本次符号执行完成数，正式源码语义分支闭合仍未通过，77 项签收仍 0/77。
- 22 个超时目标的残缺前缀共 2635 次 fork，热点为 `vstart` 上界 486、vm 分支 286、LMUL 正负 100、重叠检查 158；逐 lane slide／估算有局部指数潜力，但多项目标的 SYMBOLIC 主体已用 ITE，不能统一归因于 `2^32`。`FVFTYPE`／`VFUNARY1` 局部限制和隔离 `FVVTYPE` 延迟计算候选均在 300 秒内无最终 JSON，未合入生产。逐版本、命令、资源、源码位置与证据见[专题报告](vector-sampling-20260929.md#直接入口完整-trace-批次与卡点2026-09-29)。

## 73df 标量求解与本地 XiangShan 结果备份（2026-09-29）

- 已在当前工作区创建独立压缩包[本地备份说明](../../archives/float-scalar-2026-09-29/README.md)：`archives/_raw/float-scalar-73df-20260929.tar.zst`，约80 MiB，SHA-256 `c0111394…09815`。包含51个标量目标的1344条JSON、对应日志和trace、冻结IR/配置/isarch、v3求解账本、本地XiangShan输入/ELF/逐例结果/重试日志及受测emu/NEMU。受测旧`pipeline.py`字节另存，未用当前变动版本冒充。
- [逐文件清单](../../archives/float-scalar-2026-09-29/manifest.json)覆盖5639个原始文件/链接；`zstd -t`、`tar -I zstd -df`及归档后原文件5639/5639哈希复核均通过。原文件未移动或删除；`_raw/`为Git忽略的本机副本，不是远端备份。

## 浮点向量抽样接续（2026-09-29，部分通过／整组未通过）

- **实施**：在当前 Sail-RISC-V 未提交模型上，普通 FP 与 widening 算术 guard 拒绝无编码的 SEW8，BF16 四个 clause 的两个后端在断言前拒绝 SEW≠16；Isla 仅对官方浮点终态做可满足性检查后优选 FS/VS Dirty 编码见证，不相容路径保留原约束。非法状态编码为空单列 `non-encodable`，成功执行编码为空仍报错。原暂存改动保留，本轮源码改动尚未暂存；正式主 IR 未切换。
- **验证**：Sail 0.20.1 的 SYMBOLIC／普通后端严格检查、V128 实验 IR `e893e127…4d9` 生成、Isla exec 定向 23/23、16 组合 collector 与 fmt/diff 检查通过。当前工作区运行器 `196809a4…a81c8`＋该实验 IR、FD 配置、60/55/60 秒、`qfaufbv`、每分支 fork≤1、8 路×T2 的 26 向量预检中，`VFMVFS`、`VFMVSF` 退出0且分别有6、18条可编码 `gen`；其余24项外限124、无最终JSON。两项成功者的 ITRACE/JSON 终态守恒，已观察到的 clause 内实际分支边有双向见证，但静态源码分母、值域和完整状态尚未闭合。同 IR 的独立具体编码／状态 runner 八包共894/894通过，限列定输入。限制到每路径5次 fork 的 BF16／widening 试验虽不再断言，却没有 Retire，不能计成功。正式77项签收仍0/77，旧51标量结果仍按旧版本限定。逐命令、哈希、理论规模和覆盖缺口见[本轮报告](vector-sampling-20260929.md)，逐项退出账本在工作区 `.tmp/float-vector-sampling/matrix/summary.json`。
- **旧完整批次卡点复核**：d012／1dcc 的 77 项均有完整启动与退出账本，分别 40/36/1（成功/外限/SMT 失败）和50/27（成功/外限）；56cc跨stage57/77完成而非同批全完成。73df剩20目标的19×30分钟＋FVFTYPE两小时均外限、无最终JSON。19份日志共58,845实际fork，反向译码无源码位点至少12,866、浮点变量宽度guard 9,542、LMUL判断3,917、vstart上界2,334；冻结SYMBOLIC clause `foreach`源码区间仅直接命中12，不能将旧FullEncoded32路径爆炸归给lane if。FVFTYPE两小时单次SMT均不足5秒，95,679次SAT检查累计占worker窗口约98%。该历史诊断与当前直接入口分开适用，详见[报告](vector-sampling-20260929.md#已有完整批次与长时卡点复核2026-09-29只读)。

## catalog 回调原结构恢复（2026-09-29）

已按用户纠偏将 `6fefb6b` amend 为 `31523ab`（父仍 `b18d6b7`）。以父提交恢复 callback 的原嵌套分支、日志、早退和全部注释，信息通过原 submit_itrace 闭包追加；不再用物化标签块。精确候选64库＋24bin、主工作区82库＋24bin、默认collector/编译/fmt通过，仍过滤已知x0旧失败，未跑全量solve/硬件重放。原27文件继续暂存、其他文件及index条目保持；[实施与验证](catalog-commit-review-20260929.md#恢复回调原结构和注释2026-09-29)。下方6fef/f5aa记录保留为历史阶段。

## 当前工作区 XiangShan DiffTest 消费 73df 标量 JSON（2026-09-29）

- 对冻结 IR `73dfb2e1…671d2a`、Isla 二进制 `4e315e9a…59ae0`、FD 配置 `20851fdb…723d0` 的 51 个完整域标量求解 JSON（1344 gen），在**当前工作区** `difftest-xiangshan/xiangshan@a13efc8775abb093e23727772a562f0605380685` 的 MinimalConfig `emu` `8714169…a85ee` 与同 checkout NEMU SO `9188e7d…ef43` 上重新运行。消费端 `pipeline.py` `8099715d…22390c` 装载完整 32 个 FPR/fcsr 并核对 post；1322 条可支持输入经首轮封存、24 路 120 秒批次及5条低并发重试后 **1322/1322** GOODTRAP＋退出0（1145 Retire＋177 Illegal）。22 条 BF16 Retire 在 payload 处 cause 2，单列为本配置不支持；故意翻转 FLI.S post f0 一位的负对照停在 `fp_post_park_f0`。本轮未发现该可支持输入集的 XiangShan/NEMU 或 Isla post 浮点分歧。逐例版本、51份冻结JSON、ELF、日志、超时重试及负对照见[本地核账](../../difftest-xiangshan/work/float-v3-20260929/current-workspace-audit.json) SHA-256 `97b8dfe3…cb610bf` 与[硬件专题状态](../difftest_xiangshan_v/status.md)。
- **验收边界**：这是硬件 DiffTest 和列明 post 字段的消费端核对；73df 的 C++/Isla 全量重放、物理译码配对、源码 clause/branch 证据仍未闭合，77 目标正式签收仍 0/77。旧另一工作区的同数目运行已撤销本轮效力，见硬件专题的历史范围修正。

## catalog 单调用封装整理（2026-09-29）

- 已按用户进一步要求 amend `f5aa97d` 为 `6fefb6b`，父提交仍 `b18d6b7`。exec.rs移除物化、终态创建/更新/来源设置、汇总及旧unused判断六个函数；逻辑就地执行，无新增生产函数或闭包，输出信息和正常返回处理保持。
- FS/VS16组合改为真实collector验证，终态测试改为真实双路径关联；隔离64库＋24bin、主工作区82库＋24bin、默认两项collector测试/编译/fmt通过，仍过滤已知x0旧失败。未跑全量solve/硬件重放。原27文件继续暂存，其余index条目和文件保持、无unstaged；见[实施和证据](catalog-commit-review-20260929.md#撤销单调用封装2026-09-29)。

## catalog 最小修正并 amend（2026-09-29）

- 已按用户要求将 `d740e02` amend 为 `f5aa97d`，父提交仍 `b18d6b7`。仅在 exec.rs 删除物化前后两处返回值白名单，新增 finished 记账并同步完整性/配额统计；原始返回值、物化流程、信息关联、catalog 和文件结构保持，不做模块重构。
- 真实 collector 红例复现 Memory_Exception 被拒绝；修复后八场景含正常返回/物化失败/配额及 JSON/trace 关联通过。隔离候选66库＋24bin、主工作区84库＋24bin、默认feature定向测试、默认编译与fmt通过；两套库回归均过滤已知x0旧失败。未跑全量solve或硬件重放。
- 独立index收口，原27文件仍暂存，其余index条目和工作区文件核对保持、无unstaged；未push、未提交父gitlink。见[实施与完整证据](catalog-commit-review-20260929.md#最小修正与-amend2026-09-29)。下方审查和旧提交记录保持历史适用范围。

## d740e02 提交职责复审（2026-09-29）

- 静态审查确认 catalog/分支边/终态关联/前缀共享的单提交主线合理，执行器与 trace/isarch 的层级边界基本正确；发现通用 collector 只接受 Retire_Success/Illegal_Instruction，使同提交 IR 中 EBREAK 的正常 Memory_Exception、WFI 的 Enter_Wait 等被判为错误（P1）。
- 建议分离 catalog 数据与渲染模式、执行编排与报告模型，清理脱离生产路径的旧 Dead 测试。未改 Isla 源码/index，未新跑测试或 solve；原隔离测试保留其适用范围。详见[审查报告](catalog-commit-review-20260929.md)，下一步补正常架构异常 collector 回归并修正分类。

## catalog 单提交收拢（2026-09-29）

- 用户明确要求把有价值的 catalog 配套逻辑放进同一个 commit，不再细拆；已停止子代理，由主 agent 独立核对并 amend `1b7276b` 为 `d740e021b62005e6788058aad3871e9c136e4e3e`，父提交仍为 `b18d6b7`，没有新增第二个提交。下节首轮窄范围提交记录保留为历史，现行边界以本节为准。
- 单提交7文件包含运行时 catalog、实际分支边、紧凑输出、终态元数据及 JSON/trace 关联、错误终态记账、采样完整性标记、trace 前缀共享和对应测试。保留原有求解后 `test-ins-encdec` 字段；浮点原语、完整 pre/post 状态物化、编码 mapping 重构、自动 assert 改写及其余修改继续暂存。
- 精确 tree `4f8cbfcd47ed7f5dc9cac4cf980acd3f512c69aa` 隔离验证：`cargo test --offline -q -p isla-lib --features itrace,smt-thread-interrupt --lib itrace` 72通过；同命令过滤 `executor::` 为83通过。`cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt` 首轮库65通过/1失败，失败为原有 `isarch::target::tests::rv64_target_trait` 的 x0 列表断言；在精确 `1b7276b` 候选同名测试上复现同一失败后，追加 `-- --skip isarch::target::tests::rv64_target_trait`，库65及bin24通过。默认 `cargo check --offline -q -p isla --bin isarch`、fmt及diff检查通过。未跑全量make solve，不宣称全套测试无失败。
- [证据目录](../../isla/target/catalog-complete-20260929/)保存隔离候选、组合diff、逐命令退出账本 `checks.json`、原失败/基线复现日志及 `after.json`。主index文件与原31个改动文件哈希保持，剩余27个文件暂存、无unstaged改动；未push、未提交父仓库gitlink。测试临时目录和构建缓存分别使用该证据目录的 `tmp/` 与 `isla/target`。

## catalog 独立提交（2026-09-29）

- 按用户要求，在 Isla `feat/float-support` 创建 `1b7276bffd15336ffcde02124044e6c88f662b3c`，父提交 `b18d6b7`。仅提交 `executor.rs`、`tracetool/itrace.rs` 和 `src/isarch/exec.rs` 中的运行时 catalog、实际分支边、紧凑输出及相关测试（3 文件，+543/-2）。绑定 catalog 后启用 compact 的既有行为保留。
- 浮点实现、终态元数据/账本、trace 前缀共享、采样完整性及其余改动保留暂存。提交前后主 index tree 均为 `bd524f1206b84e03393167bb859205360d74f39e`，原31个改动文件的字节哈希全部一致，无 unstaged diff；未提交父仓库 gitlink，也未 push。此前清理的 Execute 入口改动在本轮开始时已被暂存，未被本次提交带入。
- 对精确候选 tree `54b4c24200b3498637d0f826b0033cfc743c2e93` 隔离验证：`cargo test --offline -q -p isla-lib --features itrace,smt-thread-interrupt --lib itrace` 66/66；`cargo check --offline -q -p isla --bin isarch` 默认和追加 `--features itrace,smt-thread-interrupt` 均通过；`cargo fmt --all -- --check`、diff 检查通过。测试覆盖改写后的 assert PC、具体/符号/单侧可满足分支及紧凑输出证据保持。未跑全量 make solve，不迁记浮点或重放结果。
- 首轮拆分测试为65通过/1失败，原因是测试中残留已移出本提交的 `path_signature` 断言，删去该断言后重跑66通过；生产行为未因此修改。验证目录为 [catalog-split-20260929](../../isla/target/catalog-split-20260929/)，含精确候选、diff、测试日志与提交前后守恒记录；测试临时文件置于该目录的 `tmp/`，构建缓存使用 `isla/target`。

## catalog 引入原因回查（2026-09-29）

- 已从初次审计、R3设计/实施记录与当前源码核实：catalog 最初解决 assert 转 Jump 后运行时 PC 与原 IR 文本不一致，并支撑分支覆盖核验；这项需要在删除编码 wrapper 后仍存在。
- 紧凑输出是后续经协调批准的减小 trace 体积方案；历史 FLI_S 对照约298MB→60MB、23.17s→22.10s，保留全部有序分支边。原审查关于输出模式耦合的事实仍成立，但不能把这项有动机的格式变更理解为偶然副作用。详见[当时记录](solve-fix-trace.md#p1-fli_s-联合运行及紧凑模式)。本轮只读回查及文档补充，未改代码、未新跑实验。

## 按用户边界清理编码模式残留（2026-09-28）

- 实施：仅修改 `isla/src/isarch/exec.rs`，删除暂存改动新增的编码/译码入口、校验、专属账本字段及 FS/VS=3 强制约束；保留基线已有的求解后 `test-ins-encdec` 输出。源码改动未重新暂存，catalog 行为未改。
- 验证：新物化回归旧代码在 FS=VS=0 报 NoModel，清理后16组合通过；`itrace,smt-thread-interrupt` 下84库＋24bin测试及fmt/diff检查 PASS。全量 solve/重放未重跑，旧批次不得迁记。详见[实施接续](scope-review-20260928.md#用户明确边界后的实施接续)。

## 当前工作树的范围与封装 review（2026-09-28）

- 实施：只读审查及文档记录完成，未修改 Isla 源码。实际 HEAD 为 `b18d6b7`、正式 IR 仍 d012；下方 fc9ba69/73df 段落保持原批次身份。
- 结论：FP 原语及专用分发退役聚焦，三个入参 helper 和共享 trace 前缀属合理复用；需处理全局 FS/VS=3 见证约束、不可达 FullEncoded32 框架、catalog 隐式改变 trace 输出、机器相关 Python 测试。进程管理与通用性能改动建议独立提交。详见[范围与封装报告](scope-review-20260928.md)。
- 验证：当前默认 features 的 FP 10/10、isarch bin 24/24、isla lib 84/84 PASS；系统 Python 环境下清理兼容测试 1 项 FAIL。未重跑官方长批或完整 IR 等价，不迁移历史 PASS。FS/VS 输出约束的冲突风险修订了下方“仅选择见证”的解释，原批次实测计数保留。

## 直接 `zexecute` 入口接续（2026-09-28，73df 隔离候选）

- 现行 Isla `fc9ba690` 加未提交入口回退，正常 `solve-state` 调 `zexecute`；v3 运行器 SHA-256 `4e315e9a73234cfb6d65e2fa36ab74b894bc2c256d7e135215792eaa81c59ae0`，`exec.rs` `616f668bf70547c6644b126a03e7b5b2eabf5ba0cab705ac4892b1ea5c8519f6`，`isarch_main.rs` `d4d72cbef514ec532d45cde7e3aabc11986813261b5df9a268d9cb157da09653`；实验 IR `73dfb2e17bfbd67686442cc59bfd69e2ca84a497db345d04abb2916bfb671d2a`，FD 配置 `20851fdb…723d0`，正式主 IR 仍 `d012`。求解保持完整符号输入；v3 仅在执行终态后为输出见证选择 `mstatus.FS=VS=Dirty`。Sail `zfa_insts.sail:65–67` 的编码守卫调用 `currentlyEnabled(Ext_Zfa)`，`fdext_control.sail:18` 依赖 FS；v2 直接入口的 51 标量全部 1167 个 Retire 见证 FS=Off，故 v2 的 JSON/trace 守恒不等于物理字重放。
- v3 以 `make -o build-isarch -k -j48` 跑完整 51 标量，`THREADS=1`、1800/1740/30 秒、`qfaufbv`、ITRACE：51/51 子进程正常退出、最终 JSON `complete=true`，1344 gen＝1167 Retire＋177 Illegal，51 份日志/trace 与 JSON 的 case-id、status、path-signature 一一相符；所有 1344 个输出见证 FS=VS=3。逐项文件哈希与退出账本见[机器核账](../../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/batch-v3-scalar-audit.json) SHA-256 `91a0a3a124dec2fb3af288a7f09be7eafc56f9b89c7d78e43f5cb77dec7b5fa2`；[命令与身份](../../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/batch-v3-scalar-launch.json) `2528f5b9…04ef0`。此处只签**直接 execute 求解及终态账本**，物理译码／Isla／C++ 重放和源码 branch 闭合仍未签。
- 修复采用红绿验证：v2 FLI_S 的 32/32 物化失败为实际失败证据；v3 的 `constrain_enabled_fp_vector_witness` 测试先因缺实现编译失败、实现后通过，`cargo test --lib --features itrace,smt-thread-interrupt` 最终 87/87。v3 对 `FLI_S`、`FCVT_BF16_S`、`VFMVFS` 的 120/90/30 秒定向预检单独封存，不迁作上述正式预算结果。
- v2 向量批 `-j16` 因预检失败主动中止；首次 Ctrl-C 只使会话返回 130，宿主复查发现 make/timeout/isarch 仍在运行，随后针对 stage-v2 的 make 发 SIGTERM，复查进程集合为空。最终 26 项中 23 启动，7 项有 `complete=false` JSON，16 项无最终 JSON，3 项未启动，0 项完成；[最终停止账本](../../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/batch-v2-vector-stop.json) SHA `cb432bbd…f131ed9`，旧输出全部保留。v3 `VFMVFS` 120 秒定向预检真实退出 1：9 终态＝3 Retire＋3 Illegal＋2 物化无编码＋1 Sail Assertion，不能计完成。`vext_fp_insts.sail:1840–1858` 的直接 execute 在 SEW=8 路径到达 `assert(num_elem > 0 & SEW != 8)`；两条 Illegal 路径的具体编码映射也因当前 SEW=8 守卫返回空。须先明确直接入口对这些合法 vtype、但浮点指令不支持的 SEW=8 状态的语义，再重跑向量；不得把失败或无 JSON 迁作 PASS。
- 同版本重放尚有工具接口阻塞：现有 `solve_replay/runner/main.rs` 对当前 `fc9ba690` 的 `isla-lib` 编译出现 6 个 API 不匹配（含缺少 `LocalFrame::instruction_trace`），[真实构建退出账本](../../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/replay-v3-build-failed.json)记录 exit 101、日志 SHA `72672159…db401e61`。因此 v3 标量尚无物理译码／Isla 及 C++ 全量重放结果。旧 56cc 的 57/77 与 80416 条回放仅属旧版本，不能迁到 v3。当前新版本整组签收仍 **0/77**，标量 51/77 是待重放的求解候选。

## 当前状态与文档入口

### 当前快照（下文历史按各自版本保留）

| 项目 | 当前结论 |
| --- | --- |
| 统一架构 | 共用Sail原生类型、数值/flags与ISA状态，C++ SoftFloat和Isla Z3后端已实现并实际配对验证。190条公共声明由186个C++原生绑定＋4个Sail工具组成，完整公共fixture已执行251个生成方法；a040的adapter/工具链/构建[身份链复核](../../isla/target/float-solve-evidence/unified-backend-current-interface-audit-20260927/brief.md)完成。全模型状态仍按独立进程隔离。 |
| 官方完成与回放 | 同56cc IR的57/77唯一目标自然完成；全部80416输入数值/phase独审闭环，32runID/3源binary分列；20目标未完成。 |
| 当前官方运行 | a040 RFWVVTYPE/RFVVTYPE分别7200.76/7201.04秒外限124；fc4首次FVVMTYPE/FVFMTYPE人为中断，随后在独立新stage以1800/1740/30秒、j1×T2、完整符号域/trace重跑，分别1800.64/1801.05秒外限124、make2、均无最终JSON。fc4 FVFTYPE独立30m诊断亦外限124；库存仍57/77；73df隔离FVFTYPE两小时及其余19项目标各30分钟均外限124、无JSON，均不计完成。 |
| 最新生产源码与运行版本 | fc4ce909为valid_reg_group末尾相等候选，组件、931源桥、普通/SYMBOLIC完整strict、CPP/IR构建与完整IR/strict-source双独审均通过。新67 helper（83＋17586）独审证`f5313cf0…3291`、原89整指令新IR/五配置/178阶段独审证`8e774fd9…02b2a`和最终封包`40296a3d…e499`已齐；均限列定输入，不能迁用a040结论为新官方完成。正式主IR仍d012。 |
| 性能诊断 | 86f/a040匹配诊断均1800秒外限、无JSON；完成调用199501/199004，FFI占匹配worker窗口97.942108%/97.864493%。fc4同e7ba二进制、同1800/1740/30秒与全符号域运行1800.66秒外限124、无最终JSON，完整JSONL已独立读出219605完成调用、FFI占匹配worker窗口97.636480%；最终分析与独审封包另记；隔离顺序候选同e7ba/30m外限124，局部Eq调用1612→384、FFI642.207→144.109秒但无最终JSON；追加RM纯比较候选同e7ba/30m亦外限124无JSON，RM位点448次／228.735秒→0，不能称整项收敛。73df两小时最终Z3核账95679次SAT检查，已完成单次最大4.398秒、≥5秒零次；6828实际fork，主因为全模型decoder及符号vtype/fcsr守卫的路径增长，见路径爆炸诊断。 |
| 源码分支 | 原生AST声明/调用/入口分母继续补齐；[v12导航](../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v12.json)共262入口（旧179保留＋83新增），已建立[17类剩余义务](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/unified-remaining-obligations-v1/remaining.md)，`source_branch_closed=false`。 |
| 分支覆盖核账 | 57目标80416 case的[分布图](../../isla/target/float-solve-evidence/branch-coverage-distribution-20260928/distribution.md)与12组逐clause对照（[汇总](branch-coverage/SUMMARY.md)）完成：指令层控制流基本全达、35857 Illegal全归因零残留；真缺口在数据通路层（BF16向量Retire全vl=0、标量操作数仅+0/canonical qNaN两值、56cc官方rm=101/110译码分支零覆盖；fc4定向另有FADD.S rm=101/110各一例），其余补例须走定向通道。 |
| 见证值采样 | Z3无原生随机满足赋值（[四路研究](z3-random-model/SUMMARY.md)：实测/官方文档/中英社区一致；开销标量<1%、向量热点+4~6%）。机制下沉 smt 封装层：`isla-lib/src/smt/witness.rs`（splitmix64采样+check_sat_with一次注入+UNSAT二分丢弃回退plain）+CLI `--witness-randomization [seed]`（无值自动seed入元数据）+TOML键`witness_randomization`（true/整数，CLI>TOML>关）。**交付形态（r4）**：纯净分支`feat/witness-randomization`@`2fefa72`（worktree `.worktrees/witness-pure`，基线纯f4f8e45，10文件+1255/−8，纯树67/23全绿+预存失败不变，e2e VFMVFS off=on verdict一致、vl 5→8值、accepted 16/16）；`feat/float-support`已回退至`fc9ba69`仅含6个浮点批次，witness后续合并时再加。两轮独审过（r2整改后）；浮点侧验证：VFMVFS A/B verdict多重集diff=0、vl 7值→14/18值、同seed元数据跨进程252/252全等、接受率240/252。 |
| 正式主IR | `d012`，尚未切换到候选。 |

### 2026-09-28 接续核账

- **73df 20项隔离诊断全外限，先停新跑并定位机理**：FVFTYPE 两小时完整域/e7ba运行器 stage 于7201.319秒child124、make2、无最终JSON，局部2212终态＝33 Retire＋2176 Illegal＋3 nonenc，trace 2,687,990,476字节只封哈希；[退出账本](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/exit-audit.json) `78a07ed4…ee72e`。加此前b42运行器19项目标各30分钟外限，73df全部旧20未完目标仍OPEN，[总退出汇总](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/target20-exit-summary.json) `89922cad…6327be`；旧56cc库存57/77不变。两小时Z3共95679次已完成SAT检查，p99分别1.236/1.001秒、最慢4.398/3.057秒、≥5秒零次；日志有6828实际双可满足fork，主要是运行器FullEncoded32入口额外调用全模型反向译码2544、`valid_reg_group`1449、FVFTYPE复合guard1305；译码不来自Sail `execute` 自调用或结束后的具体打印。具体Sail→IR映射与来源限制见[路径爆炸诊断](path-explosion-diagnosis-20260928.md)：当前是路径数及累计短查询问题，未见单次SMT失控。停止新模型求解；隔离bit测试候选的会话停止返回130，但构建报告与七件输出哈希实际为PASS（IR fa36a733）；仅签构建，严格配置/回放/求解未验、未上生产。
- **73df 的19项目标30分钟诊断均外限**：新增11项 VFNUNARY0、FWVTYPE、FWVFMATYPE、FWVVMATYPE、FWVVTYPE、RFVVTYPE、RFWVVTYPE、VFUNARY1、VFWMACCBF16_VF/VV、VFWUNARY0 的独立stage逐项审计均为 child124、make2、无最终JSON、无signal/资源止损。连同此前8项，19项目标全部按 b42/73df、77活跃strict、完整符号域/ITRACE、j1×T2、1800/1740/30秒尝试；局部日志合计32522终态、残缺trace合计42,018,002,096字节只封逐项哈希。[19项机器汇总](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/target19-exit-summary.json) `34c03da3…00b7`绑定所有逐项账本；19项仍OPEN，不做完整trace守恒或双后端回放，57/77库存不变。FVFTYPE两小时仍在原stage运行，待实际退出。
- **73df FVVTYPE/FWVFTYPE 真实退出**：同 b42/73df、77活跃strict及完整域/ITRACE/1800-1740-30秒预算，两项child 1801.373／1801.252秒外限124、make2、无最终JSON；局部日志1591＝16 Retire＋1572 Illegal＋3 nonenc、3356＝4＋3349＋3；残缺trace 1,878,152,835／4,531,340,390字节仅封哈希。无signal/资源止损。[VV账本](../../isla/target/float-solve-evidence/fvvtype-73df-diagnostic-20260928/evidence/exit-audit.json) `9e041ce8…2acd`、[WVF账本](../../isla/target/float-solve-evidence/fwvftype-73df-diagnostic-20260928/evidence/exit-audit.json) `f8e34828…72a7`；仍OPEN，不计回放或旧57库存。
- **73df FVFMATYPE/FVVMATYPE 真实退出**：两独立 b42/73df stage 均完整符号输入/ITRACE、j1×T2、1800/1740/30 秒；child 1801.720／1801.335 秒外限124、monitor/make2、无最终 JSON，且无 signal/资源止损。局部日志分别2356＝15 Retire＋2338 Illegal＋3 nonenc、1813＝36＋1774＋3；残缺 trace 2,729,862,142／2,183,077,089 字节仅封哈希、不签完整守恒。[VFMA 账本](../../isla/target/float-solve-evidence/fvfmatype-73df-diagnostic-20260928/evidence/exit-audit.json) `97ee1203…0423`、[VVMA 账本](../../isla/target/float-solve-evidence/fvvmatype-73df-diagnostic-20260928/evidence/exit-audit.json) `2fef431e…380e`；两项仍 OPEN，无双后端回放可做，旧56cc库存57/77不变。
- **73df 全20未完目标已各有独立诊断stage**：截至14:08本地时间，FVVMTYPE/FVFMTYPE/FWFTYPE/VFUNARY0四项已核外限124、无最终JSON；其余16项（含FVFTYPE两小时，其余30分钟）均有实际`started`和资源监控，尚无可签收退出。新增VFNUNARY0、FWVTYPE、FWVFMATYPE、FWVVMATYPE、FWVVTYPE、RFVVTYPE、RFWVVTYPE、VFUNARY1、VFWMACCBF16_VF/VV、VFWUNARY0共11个stage均以73df IR、b42运行器、77活跃strict、完整符号输入/ITRACE及原预算预检通过；[机器队列](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/remaining-target-queue.json)现列16运行、4外限、0未启动。启动只计尝试，不增57/77、不签trace守恒；结束后逐项核最终JSON、log、trace与双后端回放。
- **73df FWFTYPE/VFUNARY0外限与后继**：两独立全符号域stage分别1800.551／1800.698秒child124、monitor/make2，均无最终JSON/资源止损。残缺日志2932＝57 Retire＋2872 Illegal＋3 nonenc、1451＝49＋1399＋3，trace约3.91／1.75GB已封SHA但不签完整守恒；[FW退出账本](../../isla/target/float-solve-evidence/fwftype-73df-diagnostic-20260928/evidence/exit-audit.json) `c850f84c…7fe8d`、[unary退出账本](../../isla/target/float-solve-evidence/vfunary0-73df-diagnostic-20260928/evidence/exit-audit.json) `554269ed…95e4`。两目标仍OPEN，空槽已接续FVVTYPE/FWVFTYPE新stage（manifest`27031a2a…7e2e`／`f84f98b3…21e8`），均保留完整输入域及原预算。
- **73df首两向量目标真实退出**：FVVMTYPE/FVFMTYPE在独立b42/73df完整符号域stage分别1800.722／1800.945秒child124、monitor/make2，均无最终JSON、无外部signal/资源止损。残缺日志局部1199＝16 Retire＋1180 Illegal＋3 nonenc、1572＝16＋1553＋3；trace约1.46／1.98GB仅封字节和SHA，未签完整守恒。[VV退出账本](../../isla/target/float-solve-evidence/fvvmtype-73df-diagnostic-20260928/evidence/exit-audit.json) `a0389388…30cf`、[VF退出账本](../../isla/target/float-solve-evidence/fvfmtype-73df-diagnostic-20260928/evidence/exit-audit.json) `d7b2720c…fa30`。两目标仍OPEN，旧56cc库存57/77不变；已释放两槽转入FVFMATYPE/FVVMATYPE各独立新stage，manifest`d7826c14…885e`／`00685f3c…772f`，实际启动证据另在stage。
- **Z3随机值研究与见证值采样注入落地**：完成四路研究（实测E1–E8、官方文档、中英文社区帖，[汇总](z3-random-model/SUMMARY.md)）——Z3无原生随机采样，UF包裹/自由变量任何seed/相位下模型恒0（本项目vl/载荷形态），`check-sat-assuming`注入域内100%命中；[最小复现](../../isla/target/float-solve-evidence/z3-random-model-experiments-20260928/minimal/results.md)证明direct形态能出非零值（phase=random给34）但同参数确定、washed形态恒0；[开销基准](z3-random-model/assumption-overhead.md)50%拒绝率下循环+1.9~9.6%（每case+0.30~0.45ms），外推F_MADD≈+0.4~0.6%、FVFTYPE≈+4~6%，EE警示原生FP理论冷启动7~45×（isla现行BV+UF形态不适用）。经用户批准在worktree `isla/.worktrees/value-sampling`（基线=HEAD f4f8e45+主树未提交diff+4未跟踪源文件）实施`--witness-sampling <seed>[:dims]`：splitmix64(seed^path_signature)采样、注入点exec.rs plain check SAT后经`Z3_solver_check_assumptions`（不入增量栈）、UNSAT回退plain check并计数、terminal/summary元数据记录。TDD红绿＋14单测＋VFMVFS端到端A/B（off/on verdict全同189/3/63、vl 6值约59%零→15值含VLMAX、同seed元数据252/252一致、接受率17/252由回退兜底）；[独立复核](witness-sampling-independent-review.md)A–G全CONFIRMED（含独立重跑A/B、默认关零行为、53警告全预存）。已按精确5文件差异合回主isla工作树（feat/float-support未提交态之上，未commit/未动gitlink，原文件备份`isla/.tmp-merge-backup-20260928/`），主树复验--lib 96/bin 23/专项14全绿。关键新事实：f/v载荷均为模型变量（f*为SMT Float），phase 2载荷注入无需扩初始化。实施记录[采样注入](solve-fix-value-sampling.md)；官方启用前须按stage流程预检并单独记账，不影响当前运行中的73df诊断（其用冻结二进制）。
- **73df隔离候选89整指令重放**：新IR重导schema仅IR哈希变，五配置新CPP runner均构建exit0。初轮因fc4旧初始化侧车版本不符被回放器拒绝，原失败保留；改用冻结原始89输入在73df IR上重新物化及生成实际初始化侧车，13组89条全部物化PASS。新包五配置Isla/CPP实际重放89/89完整AST/ret/102字段一致，178阶段/2,533,781指令/沿途异常写0；[结果](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-replay89-20260928/summary-v2.json) `0aff37a3…1e31`、[来源与结果复核](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-replay89-20260928/independent-scope-review.json) `10e77958…dd71`绑定84文件。新旧89条case顶层字段零差异；初始化侧车除IR哈希外`zpma_regions`序列化字段顺序变化，未外推全局初始化等价。该结果限列定输入，不转官方77或源码17门；另补同73df IR的FADD.S rm=110原始编码双后端单例（[限定证](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-rm6-directed-20260928/summary.json) `ce61b42a…388d`），生产模型仍fc4。
- **73df独立两小时FVFTYPE诊断已启动**：仅用隔离73df IR及77活跃strict，e7ba原诊断runtime、完整符号输入域/ITRACE、j1×T2、7200/7140/30秒，79配置预检0问题；[stage manifest](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/manifest.json) `03131fa6…d212`联新67 helper与89整指令列定证。已实际出现`started`、资源监控及Z3 JSONL；最终退出/JSON/完整日志trace尚未核，当前不增57/77库存。
- **73df两向量目标隔离全域诊断已启动**：在89/67列定门齐后，FVVMTYPE/FVFMTYPE各以独立新stage复用517冻结runtime/b42二进制，替换73df IR与77活跃strict哈希，79配置预检0问题，执行1800/1740/30秒、j1×T2、完整符号输入域/ITRACE与5秒资源监控。[VV manifest](../../isla/target/float-solve-evidence/fvvmtype-73df-diagnostic-20260928/evidence/manifest.json) `32e85ddc…0b49`、[VF manifest](../../isla/target/float-solve-evidence/fvfmtype-73df-diagnostic-20260928/evidence/manifest.json) `8098b5bd…5d0f`均已出现`started`和资源监控。最终退出、JSON、trace待核，旧fc4两目标外限记录仍保留，此轮不是同56cc IR的官方57库存。
- **73df追加两类向量代表诊断**：FWFTYPE与VFUNARY0同样用独立b42 stage、新73df IR/77活跃strict、全符号输入域/ITRACE及1800/1740/30秒j1×T2启动，79配置预检均0问题；manifest分别`38248752…89dd`／`c5f9635c…49e9`，均见实际资源监控与目标进程。与既有FVFTYPE/FVVMTYPE/FVFMTYPE共五路隔离诊断并行，各自不改原始输入域，尚无最终JSON/完成签收；资源按stage 96GiB RSS/48GiB可用阈值监控，最终结果以真实退出为准。
- **RM纯比较第二隔离候选**：在先前match顺序候选上，只把`riscv_valid_rm_to_ieee`四个3-bit判断改为现有`eq_anything(B3)`；完整CPP/IR构建PASS，新IR`73dfb2e1…d2a`，2049函数仅此函数相对前一候选改变。83 smoke和17,586 full列定helper输入的CPP/Isla/native三方均PASS，[限定总证](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-crosscheck-20260928/overall-summary.json) `3c36b568…7d01d`；完整符号域FVFTYPE五分钟隔离诊断外限124、无JSON；两轮五分钟前缀都未到RM转换位点，故不能判断RM改动收益。新30分钟同runtime诊断已结束，child1800.601秒外限124、无最终JSON；RM位点相对前一顺序候选448次／228.735秒→0次／0秒，完整Z3调用245494→261566、局部终态684→732；[限定对照](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/long-comparison.json) `3c1b584a…c6bb`，整项目标仍OPEN。此候选不在生产模型/主IR，不把helper回归转为整指令或官方77通过。
- **fc4保留RM译码定向补例**：89原输入已有FADD.S编码`rm=101`、FS使能的raw拒译例，本轮以同完整初态派生`rm=110` word`0x0020e1d3`、独立run-id并实际重跑Isla与C++。两阶段Isla PASS、沿途异常槽写0，CPP AST/ret/102字段和8let/15aux与预期匹配；[限定证](../../isla/target/float-solve-evidence/fc4ce-rm6-directed-20260928/final-summary.json) `36aa0dad…2509`。首次派生输入误沿旧run-id的产物和身份修正记录保留，仅v2计最终见证。该1例补fc4定向分母，不改56cc官方57目标rm=101/110零覆盖，也不签其它clause或源码17门。
- **fc4两路新官方stage最终退出**：`fvvmtype-fc4ce-resume-20260928/`、`fvfmtype-fc4ce-resume-20260928/`的supervisor无外部signal，child分别1800.640747/1801.049378秒外限124、make2，`status.timeout.log`各一条、均无`rv64_z*.json`。新stage源码/IR/配置与manifest重核一致，运行器仍b42；残缺日志局部终态分别1145（3 nonenc/1130 Illegal/12 Retire）和1435（3/1420/12），残缺trace分别1,397,504,170／1,820,636,161字节，全文SHA与退出侧车已冻结但不签完整终态守恒。[双目标核账](../../isla/target/float-solve-evidence/fc4ce-resumed-two-targets-20260928-summary.json) `b954049d…04d3`联各目标审计`78b31166…629e8`／`3cbe7694…04f40d`；57/77库存不变，两目标仍OPEN。
- **本轮从实际产物接续**：检查时无既有浮点求解进程或其他agent；fc4 67 helper证`f5313cf0…3291`及89整指令交付`40296a3d…e499`原文件SHA重核一致，FVFTYPE诊断汇总`97ebd663…9466`仍为1800.66秒外限124/无JSON。旧两官方stage的`single.started`和残缺输出原样保留；分别创建`fvvmtype-fc4ce-resume-20260928/`、`fvfmtype-fc4ce-resume-20260928/`，逐字节复制冻结源码/IR/config/二进制与准备证据，排除旧输出，写`resume-provenance.json`并各以官方`run-single-target`启动。两stage的新manifest分别`8dd4643a…f2af0`、`65cbaeac…dac7a`；目标仍全符号、完整trace、1800/1740/30秒、j1×T2。启动不是完成，最终退出码、JSON和trace核账待新运行结束。性能只读复核指出fc4的`assert_vector_num_elem_upto_128`五处Eq后均有Jump，直接改泛型Eq可能搬移/增加查询；先考虑隔离测试`<=16`互斥match顺序`16,8,4,2,1`，不得把642.207秒热点统计写成收益。
- **整数match顺序隔离候选已构建并短诊断**：仅在独立模型副本将`assert_vector_num_elem_upto_128`的`<=16`五臂由`1,2,4,8,16`换为`16,8,4,2,1`，不动生产Sail/主IR。整数集合差异SMT为UNSAT；同源完整CPP/IR构建自然退出0，报告`303507a1…2121`、新IR`58663c4e…d1b3`，2049函数仅该函数改变且函数外IR字节一致。e7ba同二进制/完整域/trace/j1×T2/300-270-30秒的两份独立短诊断均外限124、无最终JSON；五处Eq完成查询162→30、FFI 64.787→16.006秒，日志终态前缀128→131，总FFI均约577秒。机器对照`d77a2b78…0669`只支持局部热点减少，不签整体收敛或官方完成。相同e7ba runtime/新IR的独立30分钟全域诊断已结束，child1800.599秒外限124、无最终求解JSON；五处Eq调用相对fc4旧30m诊断1612→384、FFI642.207→144.109秒，局部终态606→684，整项仍OPEN。[长预算对照](../../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/long-comparison.json) `ed51cb64…9a95`。详见[性能记录](solve-fix-performance.md#198-末尾整数match顺序隔离候选2026-09-28)。
- **fc4 FVVMTYPE/FVFMTYPE两路官方求解被人工终止**：01:11/01:12 UTC+8 启动后约7分钟（01:18）按用户指示连同全部codex进程一并终止；两组stage progress counter=1、无最终JSON，prepare/dryrun/manifest等证据目录原样保留（`fvvmtype-fc4ce-prepared-20260928`/`fvfmtype-fc4ce-prepared-20260928`）。记为人为中断、不计完成，完成库存仍57/77；如需该两目标官方结论须重新启动stage。
- **57目标分支覆盖核账完成**：80416 case分布图（44559 Retire+35857 Illegal、162 mnemonic）落在[branch-coverage-distribution-20260928](../../isla/target/float-solve-evidence/branch-coverage-distribution-20260928/)，12个subagent按家族逐clause对照Sail源码（报告[branch-coverage/G1–G12](branch-coverage/SUMMARY.md)）。结论：指令层控制流分支57 clause基本全达，Illegal全归因零残留（FRM保留值执行期Illegal／FS=Off译码负例／vd=v0 7560／组对齐／vstart越界等，VFMERGE vd=0与历史7615独审吻合）；唯一普遍控制流缺口为指令编码rm=101/110译码失败分支零覆盖。数据通路层系统性未达：BF16向量两clause全部Retire vl=0（元素级分支0达）、标量操作数实际仅+0.0/canonical qNaN两值（±0、lt=true、D版NaN臂、sNaN→NV、±inf、非精确/溢出真臂、fdiv非零除数均未达）、helper内部分支verdict层不可判。口径修正：gen内Illegal归因是fcsr.FRM保留值而非指令rm编码；direct-negative定论FS=Off；BF16向量译码要求SEW=16。定向补例清单见SUMMARY.md第5节，不并入官方完整符号输入域账目。
- fc4模型IR SHA-256 `fc4ce9091c91b654351672c89b51304afba0876cea435f251193b4537a686415`；67 helper独证`f5313cf04d13f72717e4c2ce6bd4f1c54951fcce945ae974e3528f5e86d03291`重核18,240文件零漂移。89整指令以五配置、13份初始化侧车重新执行并对比C++/Isla完整AST、返回值和102字段，178阶段/2,535,845次指令访问、沿途异常写0；native终证`8e774fd9f8892e7a808c14f54b10099e0827cf45ebc58dc7b8f97987d3402b2a`、[最终封包](../../isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-valid-reg-group-replay-20260927/final-directed89/summary.json) `40296a3d579c47bf6441b941bc740f74e2abd4d788dd44457805a58175d8e499`，22,640绑定文件重哈希零漂移。原57 Retire/22 Illegal/10 Decode Illegal及新版新增10个Illegal execute分别记账；官方stage身份和全77仍不据此签收。
- fc4独立FVFTYPE诊断在1800.655874秒由监督器记录子进程124，无外部信号，stage仅有`status.timeout.log`、残缺日志/trace，无最终JSON。原173,591,569字节Z3 JSONL完整读出219,605次完成调用、2个未完；匹配worker窗口的已完成FFI比例97.636480%，独立分析[summary](../../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-fvftype-analysis-20260927/final-030m/summary.json) SHA`97ebd663…9466`。局部601 Illegal/2 Retire/3 nonenc，完整trace正文未签；其余batch退出sidecar缺失，不补造。该诊断不计官方完成，完成库存仍57/77。新热点为`assert_vector_num_elem_upto_128`五个整数相等1612次/642.207秒；仅作为隔离候选，不凭局部计数宣称加速。
- fc4首次官方stage由原517源码/b42ac4f5…47e7二进制及新IR构成，77活跃strict重绑、2归档保留；FVVMTYPE/FVFMTYPE准备manifest分别`0ccc34ac…1996`/`d84707d7…4f81`，79配置预检问题0、dry-run无执行限制。两路曾实际出现`single.started`及带正确目标/预算/完整trace argv的5秒资源监控；其后人工中断、无最终JSON，现以本节新stage的外限结果为准。
- 57目标旧56cc汇总`2b858535…deefd`的57份最终JSON约973MB及32个来源、215个直接引用重新核哈希零漂移；80416输入=80283gen＋91direct＋42derived。源码v12导航262项约2.9GB亦重哈希零漂移，但17类语义门仍OPEN，`source_branch_closed=false`。
- 56cc BF16三配置symbolic RM正常未截断helper路径的历史19PC/六成员局部证已补最终封存，[证书](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/independent-three-config-symbolic-rounding-enum-contract-review-v1/certificate.json) SHA`ceb6750e…3a80c`，1501依赖零漂移、34封包项校验通过；本轮新动态运行0。[BF后继导航](../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/resume-navigation-20260928/index.json) `c2c42e05…08ceb`补已有BF v3/encoder/symbolic bits引用，v12不改。17全局及8 BF语义门仍OPEN，不能迁记fc4。


> **纯读审计勘误（本轮最新）**：replay与scalar phase检查器仅收集显式Register/Let，漏掉frame注入的`current_exception`、`have_exception`、`throw_location`；隐式let写也不产生WriteReg事件。348147及56cc既有decoder/encoder完整纯读结论暂撤回，完整双后端等价验收待修复后补证/复跑。已观察的数值、AST/ret、102架构字段及8let/15aux匹配事实保留；下面历史“独审通过”限其原证书，不能越过此勘误。原冻结证据不改，详见[独审修订](unified-backend-cpp-replay-independent-audit.md)。 **后续补证已通过**：架构证书`7f606935…b648`及独立消费`4cbc8ca9…e521`证明指定IR/初态/非Poison正常返回域无隐式写，恢复348147/56cc历史18584、新D1096和wave6230的列定成功输入双段语义签收；完整闭包纯读仍FAIL，异常路径不签。新动态observer的D1096与wave6230均已全量通过并独审（`ad6e1d8c…dd447`、`89a2b939…862b8`），分别2192/12460个实际ext_decode＋execute阶段、沿途异常写0（encode来源负例的encoder证据单列）；历史18584亦已完成；三组25910/51820阶段/779354630指令写0，最终全量独审通过（`bb1a2459…b7fa`，2761文件绑定，summary`f1805425…787c`）。13 encoder负例专项另独审通过，不混入三组计数。


- **统一双后端开始实施**：按用户最新方向，共用 Sail 原生浮点/RM 类型、数值辅助、五 flags 与 ISA 状态规则，底层 extern 分别绑定 C++/SoftFloat 与 Isla/Z3。Astra 已核定 [具体计划](unified-backend-plan.md) 和 [C++ 可行性](unified-backend-cpp-feasibility.md)，隔离 P0 已补 Sail 原生类型 lowering、默认返回、泛型 equality 和 f128 适配，[P0隔离验证](tools/unified_backend_p0/README.md)已通过共享 f32/f64 Add 的26条 C++/Isla 完整bits/flags与独立原生oracle对照、f128全位/NaN抽象/未知单路径及类型ABI门槛（manifest `d05ddcf5…f7b72`）；含12标量min/max去重的16文件共享模型/CMake变更已应用并通过普通/SYMBOLIC完整strict；公有adapter已接入，完整模型IR已生成；完整C++模拟器已链接，两后端语义验收继续。独立 SoftFloat 原生 flags 保留为 oracle；[三方工具](tools/unified_backend_crosscheck/README.md)与[完整验证报告](unified-backend-crosscheck.md)记录17,586条完整语料及83条接线smoke，新IR与同源C++的83 smoke及17,586完整语料三方比较已通过Astra独审（数值审查 `347cb58d…50f21`，最终来源绑定 `b006521d…14504`），CPP实际执行0.064秒、Isla含证明执行47.140秒；该结果限定67 helper和列定输入，完整ISA仍待验。
- **统一完整模型新 IR 已生成**：隔离工具链实际生成退出0（388.687秒），IR `348147f8…aac061` 保留79历史接口及 `get_F/set_F/set_V`；真实两份decoder的378个constructor顺序和四处guard已独审通过。v6快照误排SoftFloat的Git跟踪 `build/` 平台源码，首轮C++构建失败；已修快照规则并冻结920文件v7，manifest `7e945fba…02093`，保留v6及失败日志。v6/v7 Sail树相同，IR无需重生；C++补件后恢复构建已自然退出0，`sail_riscv_sim` 与共享模型静库已产出；新67 helper三方交叉验证、严格配置迁移及两个官方热点复验正在衔接。见[统一方案](unified-backend-plan.md)与[构建记录](unified-backend-build.md)。新IR尚未通过全77或完整源码分支验收。
- **1dcc 全77批已结束，全组未通过**：IR `1dcc8081…8180`、源码 manifest `28fb65ee…a055e`；130 活跃 region/22 锚点与 77 配置绑定通过，两归档配置保持旧版。批次 `isla/target/float-solve-evidence/official-1dcc-20260927-002314/` 按 300/270/30 秒、4目标并行、每目标2线程、完整 ITRACE 运行完毕；50项自然退出0、27项外限124、0项底层错误退出，make退出2。严格审计确认50项JSON/日志/完整trace终态守恒、分支边对catalog有效，日志未匹配执行/SMT异常；27超时均无最终JSON。50项的全部18,477条gen已通过完整AST/返回值/102字段重放；107不可编码终态负例亦通过，18,076标准汇编重编码同word，另401条逐case确认为非法操作数拒绝。该完成子集通过，不覆盖27超时目标或全域数值正确性。正式主 IR 仍为 d012。50项全部可用输出重放已完成；27项无JSON，源码分支闭合仍未完成。
- **构建日志告警已逐类核对**：冻结v7普通/SYMBOLIC `--all-warnings --just-check`均退出0，展开的24条是旧有effect注解弃用，SYMBOLIC另4条旧有V不完整match；C++现行旗标下无新增诊断，历史代理下载/缺平台头失败保留。新56cc另实际展开复验：普通24条与v7同字节；SYMBOLIC为24条Deprecated＋旧4条V部分匹配＋新1条AMO value部分匹配，两模式strict均exit0（`e3f8db65…f33a5`）。AMO非法opcode保持MatchFailure，decoder matcher→value调用域已独审，不填默认合法值。详见[告警审计](tools/unified_backend_model/warning-audit.md)。
- **历史全量输入已在新双后端配对通过**：1dcc全部18,477条gen及107不可编码负例共18,584条，在348147新Isla与同源CPP逐条重新执行；19/19片、4进程流水，201.601秒全部匹配完整AST/ret/102post。8let及15辅助CSR初始化按scoped合同实际核对，逐例余留辅助输入观察唯一性通过；[汇总](../../isla/target/float-solve-evidence/unified-backend-cpp-replay/p1-348147-20260927/historical-full-paired/summary.json) SHA `4c5d1995…abcb5`，[最终独审](unified-backend-cpp-replay-independent-audit.md)已通过（`7d84219a…d71ee`），662文件索引 `679875a5…3bc42` 零漂移。这是历史输入跨版本回归，`whole77-complete=false`、`source-branch-closed=false`，不冒充新官方输出。
- **56cc新整指令历史输入回归已执行通过**：新的初始化scoped证书 `11c869ff…43576` 绑定实际8let/15aux及77/decoder读取闭包；19片共18,584条输入在新CPP/Isla重新执行，完整AST/ret/102post及辅助态观察唯一性全部匹配，204.427秒，summary `cad2f88a…e7b0a`。589文件索引 `9dedd841…fdae6` 已冻结、Astra全量独审通过（`0f2e324e…9d177`，3,224文件绑定重核）；这些是历史输入的新版本回归，非新官方77输出。
- **56cc官方D FMA代表闭环通过，长批发生资源中断**：代表86.50秒自然退出0，1092 gen＋4 nonenc输入全部双后端重放及独审通过（`db60facd…866b6`），完整trace/汇编守恒。按新trace启动的77项长批为1800/1740/30秒、8目标×2线程；多向量进程各占17–28GiB，出现137/15信号退出且无JSON，已停止本批调度保留证据。cgroup无OOM kill计数，不断言内核OOM；改为1目标×2线程先重跑FVFTYPE并记录内存峰值，清理器已改为本timeout专属进程组收束，10项真实测试及Astra复跑通过（`306ce57f…c849c`），数值runtime保持同字节。停止后最终核账26项自然完成（6195 gen/6230终态）、6项信号退出、8项人为中断、37项未启动；26项另冻结全量重放，中断项不记通过。
- **j1仍受内存限制，trace共享实施中**：FVFTYPE单目标约4分25秒RSS已62GiB，后峰值约119.5GiB，按资源策略仅终止本stage supervisor；实际预算尚未耗尽，无最终JSON。最终时间戳核实采样从约7分18秒后开始，共52条；早先4分25秒为瞬时进程观察，未伪补前段。手动kill入口因PATH Python缺`os.pidfd_open`而安全拒绝（系统Python支持；早先合并报错不能归为缺`signal.pidfd_send_signal`），已核PID后局部TERM收束，兼容修复待验。Astra限定ITRACE不可变前缀共享优化，保完整trace/顺序/输入域，72项trace及2项集成测试通过，snapshot负载复制262144→0、输出逐字一致（manifest`b1fef6f2…44e66`）；组件独审`7a36af35…fddec`通过；新j1完整1805.04秒外限124，无JSON：17 Retire/24990 Illegal/3 nonenc局部终态，345资源采样峰值RSS34.8GiB、最少可用105.7GiB，28.9GB trace；对照旧约697秒119.5GiB受控停止，内存改善但求解未完成。
- **56cc唯一自然完成目标达到50/77**：旧j8自然26＋D代表1＋后续23家族全部自然完成，集合无重叠；每目标有独立stage/预算/runtime记录，机器索引`single-family-queue-20260927-014615/aggregate-completed-56cc.json`。23新目标9692输入的完整双后端/阶段观察及最终独审通过（`12a39845…aec39d`，19384阶段，391条LLVM拒绝按实际guard审核）；后续H/S FMA与三BIN_RM又自然完成且27320输入双独审通过，当前唯一完成56/77（VFMV亦自然完成，21未完）；余目标仍须完整求解与回放，不能称单批77或全组语义PASS。
- **56cc续批前五目标完成完整闭环**：H/S FMA各8740、H/S BIN_RM各4372、D BIN_RM1096，共27320输入/54640阶段/491477531指令，全部来源、完整trace/汇编、两端状态与异常槽观察双独审通过；encoder16输入另计。VFMERGE外限124无JSON，VFMV约464秒自然完成，5475输入完整回放与独审通过（`2d980eed…6f612`）；七项总PASS不成立。
- **FVFTYPE后续caller候选进入完整构建**：仅SYMBOLIC两处纯判断改strict聚合，生产源`de047560…5763`，总行数/其它内容保持；364形状/1040可行路径等价、560 Isla/516 CPP边界及独立复跑通过，组件独审`e4631adb…2b965`。最终if与shape/断言顺序保留，完整IR`e6a3232d…7d27e`、结构/跨SSA及严格行为迁移独审通过（`7681cf6b…5464e`）；129保留region实际为127非空＋2历史空，旧129全实际引用说法撤回；新FVFTYPE已运行，1805.23秒外限124无JSON：31 Retire/14106 Illegal/3 nonenc，峰值30.8GiB；85694666条边有效、日志/trace14140终态守恒，仍不计完成；当前56cc标量家族队列继续，不中断已冻结版本。
- **VFMERGE长预算已自然完成，当前57/77**：独立7200/7140/30秒运行在2359.20秒自然退出0，30603终态（8784 Retire/21816 Illegal/3 nonenc）、215491497分支边及44.12GB完整trace守恒，峰值RSS4.81GiB；manifest`6c5749ca…456e3`，去重索引`d0d0988a…8b05d`。57个唯一自然目标/20未完；全量回放首轮prepare在完整输入审计处失败（2443.29秒、退出1），尚未提交分片，已定位assembly_complete为false：30600条LLVM检查22985成功、7615因vd=0拒绝，原记录均Illegal；逐case Sail/IR guard独审已通过（`f900c97b…e8f9f`），完整trace独证 `7983151f…5f98f`；解析结果精确复用门独审 `e80cc2f4…b6168` 已通过，新目录 `sharedtrace-vfmerge-2h-reviewed-56cc69-20260927/` 已实际启动完整30603输入回放（4worker、256/片）；新prepare已通过（input `cf99b87d…3ec87`、audit `2350bd25…5cb96`），30600gen＋3direct、gaps0且与独审源结果逐对象一致，完整合并input亦已冻结（`f82e8a1e…f5323`，encoder/derived/gap均0），120/120分片全部双后端PASS、30603输入守恒；全源漂移检查通过、顶层真实退出0（3524.787秒），summary `119a6cfb…016fa`、index `47ef31d8…0746c`，61206阶段/940516587指令/异常槽沿途写0，最终双独审及联证通过（数值 `39ec127c…89707`、phase `e925f35c…21b9e`、联证 `74eff86c…e5b5a`）；原失败与30分钟超时均保留。RFWVVTYPE与BF16 VV WMACC继续独立求解；LMUL/unary两组件已审并最小合批，新IR `441c145b…5f47c` 与同源C++完整构建PASS，严格配置及源码桥独审通过（`2ba9c521…1313`，3735绑定、真实selector6536043次交叉核对），完整IR/C++独审亦通过（`37609239…e6612`，2841输入＋36审查文件）；已冻结运行包并联立两份独审证交付调度，快照/严格预检/dryrun通过，同一runtime binary复用证 `1c4e04e8…106d7`；新FVFTYPE已于06:52 UTC实际启动两小时全域运行（7200/7140/30秒、j1×T2、完整trace，30分钟检查点待到期），尚无新版官方结果，新67 helper及整指令回归另验。见[生成记录](solve-fix-ir-generation.md)。
- **56cc定向结果与严格trace全部通过**：9583输入/27455终态（scalar5413/15305、V3228/9396、BF942/2754），87组来源、初始化、逐组计数及trace完整审计通过，strict-index `283b4acc…d5b52`、result-index `07f7e6ba…c790a`；M9307/U138/S138分别记账。最小63及FD4/VPR48另通过，额外19输入/trace也通过但源码义务仍待精确消费；保持`source_branch_closed=false`。
- **86f FVFTYPE两小时仍未完成，a040 RF接续**：7200.89秒监督器child124、无信号/JSON/资源stop。a040 RFVVTYPE已10:58 UTC以7200/7140/30、j1×T2完整域/fulltrace接续，现与a040 RFW构成两个官方目标；另一路nan86f Z3诊断独立至约11:08。库存仍57/77。
- **86f FVFMTYPE外限与a040快照入口修订**：FVFMTYPE原1800/1740/30预算外限124、无最终JSON。a040下一RFW尚未启动：旧snapshot脚本不识v7报告schema及56cc runtime→86f前版配置→a040新配置的多层来源，启动前拒绝已保留；已以517 runtime清单、新79配置逐hash与d103/517双证显式装配，最小入口独审 `f43ad333…beef1` 通过（1210绑定、6负控）；a040 RFW已10:42 UTC实际启动（7200/7140/30、j1×T2/fulltrace），不改候选/证书，不重编译。
- **441c VFUNARY1两小时仍未完成**：7200.64秒监督器child124、无信号，make/monitor2、无最终JSON；09:44 UTC释放slot已实际启动nan86f FVFMTYPE（1800/1740/30、j1×T2、全域/fulltrace），归约a040双独审尚未齐不提前运行。官方完成库存仍57/77。
- **441c FVFTYPE两小时仍未完成，86f112接续**：7200.90秒监督器实际child124、无外信号，make/monitor2、无最终JSON。已于08:56 UTC启动独立nan86f FVFTYPE（7200/7140/30、j1×T2、完整域/trace/资源监控），另一路441c VFUNARY1继续；官方完成库存仍57/77。86f schema及五CPP runner实编通过（`0b29fc9e…d7bec`），helper/89输入动态独审另验。
- **57目标完整输出闭环机器汇总通过**：[汇总](../../.tmp/unified-backend-cpp-replay-independent-57-target-scope-56cc69/summary.json) `2b858535…deefd`、逐目标映射 `52b0b27f…5f6d3`：80416＝80283gen＋91direct＋42derived，57目标及全部(run-id,clause,case-id)无重复。共同IR56cc/FD20851，32runID及三源binary逐项保留；排除历史18584与额外42encoder。消费既有数值/phase独证，不重扫全部trace，不称单批77或新版441c通过；20未完与source分支未闭合保持。
- **441c新helper回归与下一隔离优化**：67 helper的新83 smoke/17586完整输入三方执行均0差异（报告 `ae4a9a2f…7ef06`），新版独审实际复跑亦通过（`3f197c8f…463e1`，3815绑定；14161全位＋1733 canonical NaN＋1692 invalid-int，全部五flags一致），未迁记旧版PASS。下一nan_unbox候选只改内层数值选择，29形状及Isla/CPP各1580检查已过（manifest `b1cbb871…df0dfeb`），隔离独审已通过（`55d32438…0b81c`），已单行应用生产并完成双模式完整strict（普通186.82秒、SYMBOLIC194.33秒），其余930源不变，handoff `764baa22…2724` 已交新完整CPP/IR构建且PASS（报告 `60af7f07…c9052`，IR `86f1121b…7e61f`），完整IR/C++独审 `4f0f7e08…31b26` 与strict/source独审 `43e1e908…ba975` 均通过，FVFTYPE已08:56 UTC实际启动；归约初案因eager新增SMT查询/timeout行为差异暂停，收窄改法另审。
- **nan＋归约组合已应用、完整构建中**：归约v1因新增SMT查询错误行为撤回，修订v2保任意EEW/GMP整数lazy前件；组件现行证 `c76e79d6…36e85`（旧73e因manifest漂移保历史），nan前件桥 `8c99975d…27b83` 核准。生产只改两归约helper、保FDdc8b，931源精确符合expected，V真实＋3行；普通181.54秒/SYMBOLIC188.28秒strict均0，handoff `a79109b4…ff50c` 已完成一次完整构建（561秒exit0，报告 `9f47ff72…ac9ee`，IR `a0405074…dfa7d`，79＋3接口齐），真实＋3行strict/source独审 `517a7cad…ba7ae` 已通过（3762绑定、6525336实际selector调用、129region/422引用保持），完整IR/CPP独审 `d1031e6a…9e5f8` 已通过（7523依赖无漂移、1664GMP及6负控），双门齐；新83＋17586 helper三方独审 `902c1d60…83332` 已通过（11737绑定），89整指令最终双独审通过（native `04a03b0d…9f609`、witness `63bb5c1c…84b9d`，summary `3df8df58…a22dc`），a040 RFW已实际启动，旧官方冻结stage不变。
- **Z3默认关闭诊断修订版独审通过**：只记录三类受保护操作，begin在watchdog启用前写出，FFI内部仅计时；worker/线程序号及累计不随fork回滚，未知上下文明确null，未结束operation不冒充FFI耗时下界。9默认＋9interrupt＋真实timeout及2旧契约通过，旧off/新off/新on actual IR29形状83终态、各1580结果逐字一致，4180调用begin/end已核；manifest `57f00f13…b5b5f`、独立binary `b8b4f452…fc8be` 已交独审；v1 phase字段歧义及分析器六类拒绝缺口被拦（错误计数/窗口/FFI区间/未知schema/worker结束后调用等），v2须phase一律null并补负控重验，不把decoder/helper误标solve execute或输出伪耗时比例。v2正式独审 `10115c84…4a056` 已通过：24消费端控制、677封包/518源码和真实结果复核，独立binary `e7ba503a…10f81`；已于10:38 UTC实际启动单独nan86f FVFTYPE30分钟全域诊断（1800/1740/30、j1×T2、独立JSONL/完整trace、5秒资源监控），不计官方库存。现官方/live runtime未改。
- **Z3诊断首固定前缀已有实测**：实际启动后362.365秒，JSONL固定[0,37269980)、SHA `ad32d688…b26d`；47258完成operation/131worker（128closed、3open）、2 begin无end。完成FFI 701.210秒/匹配worker观测窗口718.657秒＝97.5723%，closed子集97.5654%；CheckSatAssuming502.646秒、CheckSat198.446秒、ModelEval0.118秒。summary `6be3de20…2983`，只签该有限窗口统计，不能称CPU/FP主导；独立复核 `2e6de8ee…53613` 已通过；精确PC聚合125组/98site：valid_reg_group PC29末尾zeq_int 458次/216.367秒，未知context CheckSat628次/173.244秒，execute PC29144 guard189次/104.953秒。下轮只改末尾Eq的隔离组件实施中；未结束operation不记FFI下界。
- **完整回放减少重复trace读取的工具独审通过**：source receipt限定同父进程/同audit epoch，保初始真hash、audit真hash与final fresh；六调用实际3真读＋3复用。21测试＋7独立负控及独立7输入/3片回放通过，14阶段/130683指令/异常槽写0，9.6MB trace实际读28844370B；独证 `9984f6c0…4b51c`（1810绑定）。旧成功工具及证据不改；允许下一包使用，不外推大包墙钟。
- **86f新67 helper三方独审通过**：83 smoke＋17586完整输入、17669精确tuple类型真实新IR检查、CPP/native独立复跑及19测试控制通过；独证 `fe432ce3…5bc06`，11070依赖核验。后续归约已改变live V源，历史结构证该一项明确投影至同原hash的86f冻结源并记录drift=1，旧证不改；不扩签整指令/全77/完整源码分母。
- **86f新89完整配对及最终双独审通过**：新IR/五CPP已实编，原89输入全量重新物化与配对均退出0，178阶段/2535669指令/异常槽写0；owner摘要 `a9d55733…0e53`（444绑定），新版本witness/source/phase `c899afe3…a37d1`（13280绑定）及native初始化/数值 `a49d144e…feb24`（15105绑定）正式通过，summary `668b4509…933da`、index `3197f857…e6ae3`、联链 `8414ffaf…fe4d8` 已封；不迁441c89证。
- **441c新89整指令回放及独审已完成**：使用新IR及五份新CPP runner重新物化并执行63＋26输入，89/178阶段/2529965指令/异常槽沿途写0；来源桥保留actual stage从e6a provider复用同字节binary的实际构建链，不能把candidate/runtime树旧56cc IR误作新441c。来源/phase证 `a48bdd53…b2878`、provider `b5758211…f887f`、新89数值 `2ba4713c…4df16` 均通过，最终summary `aad0ffdf…413c5`、index `dc68ef89…31493` 已封；native最终总证 `9fb13e89…394f6`（7853绑定）及联链 `e0635e97…d6b74` 亦已封存，不迁e6a89旧证。
- **e6a新版本89定向完整双后端独审通过**：五配置、63最小输入＋26 FVFTYPE输入无重复；完整AST/返回值/102字段及8let/15aux一致，178实际阶段、2531598指令、异常槽沿途写0。summary `1dba7eeb…e23c7`，v2/v3输入身份桥及最终数值/初始化独证 `0d414d76…5f6ca`（5215依赖）已冻结；见[重放记录](solve-fix-replay.md)。限新e6a列定输入，不迁记56cc证书，不增加官方完成数。
- **新三目标30分钟队列已结束**：RFVVTYPE、RFWVVTYPE、VFUNARY1全部外限124、无完整collector JSON，VFUNARY1无资源止损；局部Retire443/Illegal4006/nonenc3不算完成。BF16 VV WMACC独立2小时诊断已7201.33秒外限124、无最终JSON/资源止损；RFWVVTYPE亦7202.35秒外限124、无最终JSON/资源止损；新441c FVFTYPE已运行，另一释放slot已于07:41 UTC实际启动新441c VFUNARY1全域两小时，各j1×T2、7200/7140/30秒、5秒资源监控，保持最多两个官方目标并行；库存仍57/77。
- **源码分支闭合继续**：[三族机器合同索引v11](../../isla/target/float-support-review/final-coverage/integration/source-contract-index-v11.json) `b00de06c…a4482`（179入口，v1至v10保留） 汇总根因、条件前缀、loop/mapping、typed域与RHS/异常义务，保留各自分母；`source_branch_closed=false`。新性能源码消去的纯判断须标明not_lowered并绑定等价证据，不能沿用旧PC或把未观察算成覆盖。
- **56cc性能候选的完整IR接线已通过**：V四个total纯判断及AMO前端matcher保留原输入域、非法width与value/when/Fatal次序；931文件同源CPP/IR构建PASS，IR `56cc69a4…9956ac`。V完整IR结构证书 `afa7d113…af687`、AMO完整IR证书 `cd6090cf…d0d6` 已通过；新helper的83 smoke/17,586完整输入及旧十组已执行零差异，最终来源绑定独审通过（`7421e482…73ca6d`，范围限67 helper）。旧valid_rd_mask的一条region在新IR已无Jump，精确退役证书 `72e53ee2…c4fb` 只授权130→129活跃region、另列1退役项；其余129项严格迁移及最终独审通过（`0ab22029…72e8f`），官方两代表已启动，D FMA自然完成，V FMA外限124但到达53 Retire及数值/写回前沿；架构已审定同56cc全77长批1800/1740/30秒、8目标×2线程，保持完整输入域和trace，首轮长批资源中断，降并发续跑准备中。新整指令回放与定向覆盖另开新证据，正式主IR仍d012。
- **新348147验证进展**：9583定向用例28组全部自然退出0（full-summary `5a953a7c…c2c6a`），最小63、FD direct4、VPR48调用通过；[三族完整trace来源桥接审计](../../isla/target/float-support-review/final-coverage/integration/p1-348147/strict-audit-index.json)已通过（9583输入/27455终态，`92dfd023…2fffa`），旧源码arm证书不迁记。官方两个热点 `FVVMATYPE`/`F_MADD_TYPE_D` 在同300/270/30秒预算仍均外限124、make2，尚无新全77通过；正在按新trace继续定位。C++完整ISA重放另补TOML覆盖初始化及纯读extern审核。
- **1dcc定向追加稳定索引**：累计9583/9583结果、27455终态，标量5413/15305、向量3228/9396、BF16 942/2754；[v3索引](../../isla/target/float-support-review/final-coverage/integration/result-index-v3.json) SHA `cc93ea74…3bc89`，旧9152/v2索引保留。仍为 `source_branch_closed=false`；新348147的全部9583定向、FD/VPR direct已另开同源复验，不能沿用旧PASS。
- **同版定向结果 9152/9152 PASS**：标量5121、向量3105、BF16 926，13配置、26394台账终态；[结果索引](../../isla/target/float-support-review/final-coverage/integration/result-index.json) SHA `f6e074b8…44878`。默认域、合法 alternate 配置分别记账，定向组900秒预算不等同官方求解预算；`source_branch_closed=false`，不据此声称每条源码分支已覆盖。
- **同版 helper/direct 门槛 PASS**：79历史接口及94个现有 `riscv_*` 函数体完整；277未知入口及全部列定数值组通过，FD direct 4/4、VPR 24组合×2入口通过。见 [helper](solve-fix-helpers.md)、[FD](solve-fix-fd-state.md)、[VPR](solve-fix-vpr-state.md)。官方代表 FMINM_S 自然退出0，85终态=84退休+1不可编码；不代替全77结论。实际旧新 decoder 的 VV/VF 两固定形状已按四个独立方向、各120秒预算完成双向完整 AST/payload 差异证明；[证据](../../isla/target/float-solve-evidence/mapping-decoder-1dcc-20260927-lxm85ubv/final-proof.json) SHA `3fd93f28…d6b5e`。前次两组各120秒超时保留，不扩推整个 decoder。

- **定向覆盖追加**：原9152结果保留版本。另补倒数估算15条（45终态）以及User/Supervisor 276条（标量204、向量58、BF16 14），全部列定结果通过；新runner三条Machine回归及六个H关闭下Virtual状态、一个无效枚举的拒绝控制通过。新增输入按实际R1约束绑定，逐调用点源码/trace审计继续，不据此外推全部特权状态空间。

- **下一候选性能修复已落源码**：H/S/D `negate` 共用符号位XOR，VMVR/VEXT完整译码布局将纯字段匹配合并；分别通过完整位串差异证明、小IR测试及双模式strict检查，见[修复证据](solve-fix-decoder-layout-negate.md)。新IR `348147` 的实际全decoder guard顺序已独审通过，官方性能仍待同预算复验；不得复用1dcc通过结果为新源码背书。

- **统一后端集成准备**：[隔离工具链](unified-backend-build.md)已真实构建Sail及其匹配Isla插件；[P2剩余62入口](tools/unified_backend_p2_native_extra/README.md)已真实生成、链接并通过15,623次返回/环境检查及6,224次数学参考对照。任意宽转换另有[合同及探针](unified-backend-wide-conversion-contract.md)。这些隔离证据不代替完整190声明、公有adapter/TLS、共享模型与77项的新版本验收；[C++完整指令重放工具](tools/unified_backend_cpp_replay/README.md)已具备可复现schema/来源绑定、102字段loader和完整AST/ret/post比较；历史模型16控制、所选72条及协议故障测试通过，当前仅concrete-match，新共享模型/aux正式门槛待验。

### 2026-09-26 阶段记录（按当时版本理解）

- **新模型快照/IR生成已启动**：标量min/max已Astra局部放行；两纯mapping `*_matches` 已通过双模式strict、32值成员测试/无效值错误保持、未知Bool及synthetic完整AST差异UNSAT，生产 `vext_arith_insts.sail` 冻结 `60c1f6f2…`。运行时 `fmtval.rs` `43806138…` 和 `smt.rs` `3ce7310d…` 均经独审；后者缓存只限同Model具体值，保留completion和错误边界。候选生成与mapping独审并行，真实旧新decoder、helper/状态回归、77项及全量重放仍待新IR。
- **下一候选正在收敛**：标量12个min/max改为复用V既有纯helper，初步验证旧实现1566条可行路径与新12个单路径入口的完整bits/五flags差异UNSAT，待最终独审冻结。性能诊断确认重复ModelEval与每次看门狗调度开销，单Model具体值缓存的VFMVFS实验保持255终态且逐命中复算一致，单轮17.934→13.771秒；生产缓存另做TDD和复核。另以真实trace定位两个纯mapping成员测试，拟保持值映射及clause顺序消除数据分叉。这些局部门槛不代表77项已收敛，新模型/运行时将统一冻结重跑。
- **FmtVal宽位修复已完成局部回归**：`fmtval.rs` `43806138…` 改用既有 `BV::to_vec()`，debug/release测试及旧红新绿探针通过，覆盖0–129位边界、tag、宽Mixed片段和mask；独立复核进行中。旧77诊断不转记通过。定向runner另修非法译码的固定路径数假设，并将逐case复用实际R1约束检查，防止具体输入覆盖符号寄存器后绕过初态约束。见[输出修复](solve-fix-fmtval.md)。
- **c5首轮77项已全部结束（旧FmtVal诊断）**：`official-c5cbb-20260926-204047` 在300/270/30秒、全trace下为41自然退出0、36外限124；41份JSON均complete且suppressed=0，36外限无最终JSON。日志累计40434 Retire、60961 Illegal、214不可编码，其中28854 Retire属于未完成目标，不能计整项通过。宽位输出缺陷使本批不作语义PASS；现推进FmtVal修复、标量12个min/max复用既有纯helper及向量/collector耗时定位，待同版重新冻结验收。详见[官方记录](solve-fix-official.md)。
- **宽位状态输出阻断已复现，当前77批转为诊断**：独审确认 `FmtVal::BitVal::from_bv` 对B129超过64位只取 `lower_u64`，debug移位溢出、release重复低64位；128位高低半部不同的最小例已复现。符号值经 `Exp::Bits` 的输出路径不受此例影响，不能据此前局部绿灯忽略具体宽位状态。正在复用既有 `BV::to_vec()` 修复并补全宽/混合片段测试；已启动的 `official-c5cbb-20260926-204047` 保留全部诊断结果，最终验收须重新冻结运行时和批次。
- **最终运行时已冻结，正式批次准备启动**：完整候选IR `c5cbb0bb…` 配合主树 `primop.rs` `6c6d5a42…` / `ir.rs` `d26e7923…`；MixedBits拼接通过67项局部测试及58对真实decoder完整AST差异UNSAT，两位Astra独审放行。该decoder探针未使用官方全部初始化/断言转换，故仅作表示等价证据。正式77项按300/270/30秒、4目标并行、每目标2线程、完整ITRACE重跑；最终helper、定向覆盖和全部输出重放使用同版runtime。见[MixedBits记录](solve-fix-mixed-bits.md)及[官方批次](solve-fix-official.md)。
- **MISA覆盖域修订**：官方求解保持FD配置的固定MISA，不声称穷尽所有MISA状态。标量旧包4999条属于默认域，122条直接写入违反D⇒F、V⇒F∧D依赖的状态只保留为raw诊断，另建合法alternate配置用例；BF16相应为916默认、6 raw及4合法alternate，并补6合法关闭F/D/V例。各配置分别绑定实际初始化和源码覆盖证据，不混合计为官方默认域覆盖。
- **审计修复进行中（用户已授权全部调通）**：按[本轮架构](solve-fix-architecture.md)推进77目标、完整状态/错误账本、同约束译码执行、分支证据及重放。已新增 `solve-fd-nonmem` 并通过入口红绿测试；FPR快速写遗漏Dirty已复现并修源码；P1外部候选IR（f5141217…）已通过真实getter/setter及全符号flags累计状态检查，原FADD.S红例转绿。运行器FLI_S联调得到96 Retire+1明确不可编码终态，完整pre/post已输出；VPR快速写同类遗漏已另获direct红例并修源码；向量纯lane、纯数据比较优化及最终77项仍待联合验证。旧d012结果保留历史，不计新候选PASS。
- **P2候选已严格生成（外部验证中）**：FD/VPR状态、向量纯lane、BF16/归约及纯数据比较源码已冻结；两模式严格编译通过，V1 49项、共享比较27项及BF16转换未知输入的局部等价证据已独审。P2 IR `d86655a4…` 的FD直接状态/全符号flags、VPR48组直接写和FADD.S/FLI.S旧红例已通过；严格配置坐标迁移、完整数值覆盖、C++及77项官方验收仍在进行，正式IR/config尚未切换。
- **最终冻结追加门槛**：P2生成器消除了4个不再被调用的旧窄整数helper，历史79接口仅75仍在IR，完整277包装门槛因此未通过。现按源接口合同显式preserve并重新生成完整候选；前驱d866结果保留。向量前段profile显示大量SMT用于恢复已知编码片段，已审定最小通用MixedBits拼接优化，正做独立红绿与语义验证。
- **完整接口候选已生成**：同模型的 `rv64d_p2_full.ir` SHA `c5cbb0bb…` 已恢复79个旧接口，277未知入口、67helper、估算350+1618+420、旧12体39+24及legacy35在冻结旧runtime上全部通过。通用MixedBits运行器修改完成后仍须重建并复验，当前不转记为最终77 PASS。
- **P2官方热点复验**：`F_UN_RM_FF_TYPE_S` 同90/80/15秒预算自然退出0，79终态=60Retire/18Illegal/1不可编码，完整78输出、无错误/SMT超时；两个向量代表仍外限124，未有最终JSON。P1比较热点已修，向量未据局部绿灯宣称通过，正式77首批仍待运行。
- **P1热点诊断仍失败**：三个代表目标均触发90秒外限；`F_UN_RM_FF_TYPE_S` 的flags比较在构造布尔值时仍主动发起SMT查询，出现10条15秒超时。该根因正在修复；P1未包含后续向量纯lane/VPR改动，不能据此否定或验收新实现。
- **覆盖域进一步核对**：最终source-arm证据使用与官方相同的初始化、显式断言转换和R1合法状态域。旧raw定向包保留；只读SXL/UXL另包迁移，旧22条非规范`vill`状态另标raw诊断并补canonical译码/执行负例。多条可行辅助路径须逐条证明完整观察结果唯一，不能仅比较一次模型物化值。
- **新增定向覆盖包已冻结**：标量5121输入（旧d012已验证4202），向量2526加三配置565、BF16扩至922的旧基线结果已通过。新纯lane实现后须全部按最终IR复验，并将实际trace绑定源码分母；静态标签不计分支覆盖。见[标量包](solve-fix-scalar-coverage.md)、[向量包](solve-fix-vector-coverage.md)、[BF16包](solve-fix-bf16-coverage.md)。
- **新增运行与分支审计已完成，全组未通过**：普通 `make solve` 排除全部浮点；现 d012 IR 的77个显式非访存目标均已尝试，40退出0/36外限124/1 SMT退出1。11目标有SMT超时，另1目标有路径超时；12目标限时内仅观察到Illegal。新增/复跑433条定向状态记录全部PASS，已补min/max局部72选择叶子、向量OF/UF与flags区分能力，但其余源码分支未穷尽。确认JSON缺fcsr/输出状态及FLI、BF16汇编文本问题，详见[本轮审计](solve-audit.md)、[77项表](solve-audit-batch.md)、[日志语义](solve-audit-log-semantics.md)。
- **现行实现：C1已落地并切换正式V128 IR**，SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`，79份严格配置同批更新。复用 Sail 的 `float_bits`/`float_decompose`、内建 `float_rounding_mode` 和出口 `fp_exception_flags`；内部保留局部五Bool事实，避免中间位串化引起的性能回退。见[架构取舍](type-reuse-architecture.md)、[性能对照](type-reuse-performance.md)与[最终IR记录](ir-refresh.md)。
- **最终候选定向验证PASS**：277未知入口（90/96/91）全部SAT、单路径、普通体trace，各组约5秒；67 helper、估算350+1618+420、旧12体39+24、legacy35完整bits/五flags差异UNSAT；24组1509条状态样例覆盖77个RV64非访存clause。79配置/132region/22锚点通过。Astra独立核对原始日志、输入输出及版本绑定。上述均为列定范围，不是任意输入等价证明或E全阶段PASS。
- **本轮新增修复**：BF16 VF的e16,m8现在先返回非法指令；新IR8非法+2合法边界样例通过，现有C++ BF16两项在V128/V256通过。M09四个旧比较函数补齐限制/迁移说明；smtperf测试旧宏接口已修，两种feature组合各4/4通过。主树同批切换后通用测试10/10、MRET与FCVT_S_BF16 smoke通过；命令及限定见[IR记录](ir-refresh.md)。
- **未完成边界**：普通 `make solve` 全220项仍未通过；旧c9e1bfe2官方77项为39退出0/37外限124/1 SMT超时退出1，见[续跑记录](official-continuation.md)，不可转记新IR。10个访存clause不在本浮点任务验收范围；公共RV32 solve-state仍有限制，两Zfa隔离证据保留。全库Z3 enum既有失败保留，未伪称修复。
- 本轮模型、IR和配置有未提交修改，未移动gitlink或触碰独立内存worktree。实施细节及A/B失败候选保留在[实施记录](implementation.md)，现行步骤见[计划接续调整](plan.md#2026-09-26-接续调整复用已有-sail-类型)。

## 此前阶段状态快照（历史）

以下保留各阶段当时的判断；其中“当前”“待复验”和c9e1bfe2均按原时点理解，现行状态以上文及最终IR记录为准。

- 用户已收窄本任务：只做浮点支持，独立 `isla/.worktrees/memory-consistency` 不由本任务修改、集成或验收。此前将内存候选读写结果计为浮点 E 的表述已撤回；10个访存clause在本任务中标未验收。详见[范围修订](implementation.md#范围修订独立内存分支不纳入本任务)。
- 2026-09-26 用户已确认[实施计划](plan.md)并启动 A–E 实施；启动版本、文件边界和逐步结果记入[实施记录](implementation.md)。Astra xhigh 审定关键语义，Luna medium 初筛清单，Sol 在独占文件边界内编码。A/B 与分格式隔离 helper 已按各自范围通过；E有定向真实指令样例，但全范围尚未PASS。
- A 阶段已在 Isla 通用接口新增 9 个原语，保留旧 73 个名称；先复现旧单测初始化失败，修后单独旧测试 1/1、通用测试 10/10、旧 SoftFloat 测试 21/21、浮点模块 31/31，Astra 独立复核通过，**仅 A 通用接口门槛 PASS**。B 的双后端隔离实验确认 C++/Lem extern 与 `SYMBOLIC` 同名函数体可共存，正式 helper 仍待逐名验证。[接口与异常契约](exception-contract.md)明确 C/D 的五 flags 算法及待差分门槛；[clause 矩阵](clause-matrix.md)已初筛 89 项，扩展和子操作仍待正式执行复核。
- BF16 VF 副作用修复先有旧模型 `vl=0` 失败、修后 V256 C++ 两项通过的红绿记录；当前联合 Sail 源码已独立重建并在 V256 CTest 2/2、显式 V128 配置运行两项均输出 SUCCESS，详见[实施记录](implementation.md)。新 Isla IR 的 BF16 指令状态仍待 E 复验。
- B 阶段最小调用链已过独立审查：f32 quiet Eq 的8组样例与SoftFloat一致，受限未知输入的结果/五flags差异为UNSAT；独立加法位串演示和BF16接口小式可运行，未知Eq/add各一条路径，C++生成仍调用原SoftFloat。**仅B当时范围PASS**；完整加法函数体与flags已在后续C/D隔离候选验证。详见[实施记录](implementation.md)。
- C/D 已写出原外部67个helper的Sail函数体并按f16/f32/f64分为22/23/22，由不同负责人独占。共享异常库在隔离IR中通过算术/比较3888例及转换/取整/BF16/ROD至少4353例的SoftFloat差异证明；分格式隔离helper样例数分别为f16 3042、f32 570+3734+1178、f64 807，Astra独立审查无阻断。这些PASS只适用于各自隔离测试域，不能代替完整IR或指令状态。
- D已从冻结快照生成退出0的V128候选 IR `c9e1bfe2…`，原79个helper均有普通函数体；隔离删除旧分发后67项SoftFloat对照、六个Recip7/Rsqrte7的350+1618+420项独立Spike/规范对照，以及原12函数体39+24项回归均先SAT再对完整结果位与五flags差异求UNSAT。277项未知入口各一条路径，旧IR负控制正确失败。当前联合BF16 C++指令在V256/V128配置各两项通过。Astra独立核对后判定**D阶段PASS（固定候选与所列样例范围）**；新Isla IR的完整指令与E全部门槛尚未完成。详见[实施记录](implementation.md)与[完整D记录](d-run.md)。
- E 已将删除旧分发的 Isla 源码、新 V128 IR `c9e1bfe2…`、79份匹配严格配置和35条旧断言迁移回归同批切入主工作树；主配置校验79份/67个旧V region/22锚点通过，附加检查覆盖132个region。主浮点通用测试10/10、迁移回归35/35、`make solve-FCVT_S_BF16` 与 `make solve-MRET` 定向入口退出0。三个独立指令包的clause集合47+20+10且无重叠，**77个RV64非访存clause各至少一条具体编码样例**经真实译码、成功退休及状态差异UNSAT；仅覆盖所列子操作/配置，不代表各clause全部变体。普通 `make solve` 在60秒全局限时下退出137，220项未完成；`isla-lib` 全库既有Z3 enum单测仍FAIL。E非访存指令验收继续，访存不在本任务范围；详见[实施记录](implementation.md)。
- 官方 `make solve-X` 另在排除 `.worktrees` 的主浮点精确副本固定77个RV64非访存目标。交接快照前35项中24项底层退出0、11项向量目标触发60秒外限且无最终JSON；第36–44项运行中，后续未测。官方入口结果只验证本次运行路径，不替代上述独立数值/状态差异证明，见[交接说明](handoff.md)与[批次证据](tools/official_float/README.md)。
- 历史只读预检 [E访存与RV32集成审查](memory-integration.md)当时确认：`LOAD_FP`/`STORE_FP`还含H宽度2字节的FLH/FSH；四个Zcf和两个Zfa RV32限定项的现有`solve-state`入口无条件panic，须另建完整RV32 IR合法译码/执行证据或修入口。内存worktree的RV32数组地址BV32与模型实际物理请求BV64不符，区域末端、无合法区域和Concrete写后读语义也待处理。10个浮点访存条目仍需真实内存读写和前后状态，不以`Finished`计通过。这些是当时的静态时点结论，内存分支已不在本浮点任务范围，不作为当前实施指令或动态PASS。
- 已完成用户要求的 [逐项修改参考总表](reference-list.md)：73 个通用 primop、16 项 ITE 相关接口、15 处浮点私有 ITE、79 个 RISC-V helper（67 外部+12已有函数体）、模型支撑函数及18项底层检查。每项给出保留/修改/补充/迁移或待验证意见。
- 新发现包括真实 ROD=6 窄化路径无法执行、BF16 VF 无活动元素仍可能置NV、通用 union ITE 的条件关联缺陷，以及加法无穷输入和整数转f16的额外flags反例。Sail中的旧比较辅助无调用但不可直接复用。计划已补充相关项；静态推导尚未记为动态复现。
- 早期小范围命令行Z3检查仅确认比较/min语义、ToIEEE打印及简单混合公式，详情见 [原语清单](inventory-primops.md)和[支撑清单](inventory-support.md)；现已另有A–D隔离动态证据，仍无完整E指令回归。
- 用户进一步明确主要依据：IEEE数值计算由Z3/Isla提供，ISA的flags、分支和状态由模型负责；用RISC-V/ARM/x86检查同一个primop换ISA后含义是否不变。[计划第1节](plan.md#1-要完成什么)已补入此标准及例子，验收第1条和阶段A同步增加逐个原语的检查。ITE负责通用选值，ISA规则留模型；共有异常公式可留Sail共享库。本次范围仍为RISC-V。
- 用户已认可五条验收标准并确认按[实施计划](plan.md)执行；计划写明职责、验收方法、涉及文件、A–E 步骤和结果记录方式，[设计说明](refactoring-plan.md)保留具体接口与算法讨论。正式V128 IR已同批切换，E逐项指令验收未完成。
- 本轮已完成 [文档前后核对](documentation-review.md)：补齐参考编号到实施阶段的对应关系；B 阶段使用只返回位串的独立加法样本，C 才验收完整加法；D 在隔离候选使用测试 IR、函数进入记录和禁用旧分发确认迁移，E 将正式删除分发、新 IR 和严格配置同批集成。BF16 接口形状提前在 B 做最小编译确认，C/D 异常算法先经 Astra xhigh 审定契约。异常、ROD、BF16 的算法与功能验证仍未完成。
- 实施起点 Isla HEAD 为 `f4f8e4584a70588c66c9e7a6286cc20211618f18`、Sail-RISC-V 为 `f8ce849`；两者随后有本议题未提交修改。父仓库 Isla gitlink 仍为 `85d7c70`，本轮未更新。
- 待实施验收：Isla 不依赖旧 RISC-V 浮点名称分发；结果与五个标志正确；覆盖特殊数字、边界、未知输入和 ROD；迁移的 67 个纯 helper 及新增纯辅助中的选值不新增执行分叉；完整标量/RVV/访存行为另测。原有 12 个函数体保留并回归，不承诺本次消除其全部查表/归一化循环。
- 73 个基线 primop、79 个 helper 已逐名登记；89 个 FD_FLOAT clause 的[静态矩阵](clause-matrix.md)和[动态验收索引](e-coverage.md)已建立。RV64非访存77项和RV32两Zfa各有至少一条固定IR/配置下的具体编码样例通过；10个访存clause依赖独立内存分支，本浮点任务未验收。各clause未列的子操作与状态仍需持续验收。79 个 helper、79 份严格配置、89 个 clause 是三种不同的集合，不能互相代替。
- 按用户调度要求，Astra xhigh 定设计、语义及取舍，Luna low/medium 批量初筛并由主 agent 或 Astra 复核，Sol medium/high/xhigh 在确认的文件边界内执行。具体工作包和交接见 [计划第 6 节](plan.md#6-怎么记录结果和分工)；当前 E 集成、非访存、RV32与内存前置在独立文件边界推进。
- 参考来源按操作区分：同语义算术/转换对照固定配置的 SoftFloat；近似查表、FCVTMOD、状态更新和无序归约按各自规范判定。BF16 无活动元素测试同时检查旧 flags 非零时保持原值。
- 实施：A/B/C/D已按各自固定测试范围完成；E主Isla浮点入口、IR和严格配置已同批切换，BF16 VF副作用已修，浮点非访存指令矩阵继续验证。验证：当前主浮点通用10/10、旧数值回归35/35、BF16联合Sail C++ V128/V256两项各通过；77个RV64非访存clause及两项RV32 Zfa各有具体编码样例，标量/向量多enum与RM扩展另见实施记录。10个访存clause不计PASS，普通make solve完整回归仍未通过。

## 调查起点（历史记录）

以下至文末保留调查过程；其中“本轮”指各段当时的调查，当前版本与实施安排以上文及 `plan.md` 为准。旧源码行号不能直接当作最新 checkout 的位置。

审查对象：`isla` 的 `origin/feat/float-support`，头提交 `1a1910e`，基线 `0008fae`。原记录称工作树仍在基线；2026-09-25 复核时干净 HEAD 是 `85d7c70`，与浮点分支已分叉。当时远端查询确认分支头仍为 `1a1910e`。该次仅静态审查，不切换分支。

详细结论及固定提交源码入口见 [复核报告](report.md)，调查范围见 [方案](plan.md)。实施：审查记录已更新，未改实现；验证：未测（分支动态运行）。

## 2026-09-26 分层细化

- 本轮收尾时Isla HEAD已更新为合并提交 `8148bc1`，`float.rs`与 `1a1910e` 相同，IR/严格配置未在该次合并中改变。方案已改为保留通用改进、完成模型替代后移除现有专用分发；此前85d7c70描述属于调查起点。
- 用户认可职责方向并要求细化；[实施设计稿](refactoring-plan.md)给出三层契约、加法/转换/比较示例、文件边界、阶段及验收。当前只完成设计与源码核对。
- 当时核对的Isla已有公开通用ITE及FP/RM类型通路，需复用；具体BV入口、ToIEEE/ToUnsigned公开原语属于首阶段。目标格式错误已随浮点分支合入修复，首阶段是保留并验证这项修复，不是再次从头修。
- Sail位串浮点库可复用分类函数，但flags布局与RISC-V不同；旧native浮点库的rounding_mode别名会与ISA冲突，需最小编译核对。
- BF16类型/接口、精确Div/FMA异常及实际无fork编译均设明确验证点。IR生成要显式维持V128，不能沿CMake默认V256配置误生成。

## ITE与建模边界补充

- [全量清单与边界建议](ite-boundary.md)逐项记录15处新增ITE调用；IEEE数值操作本身已用Z3原生FP，ITE负责编码、异常辅助及模型结果策略。本身不会产生Isla执行路径fork。
- IEEE五类异常条件与RISC-V的fflags布局/CSR累计应区分；建议前者放共享建模库，后者连同rm编码、规范NaN、非法整数转换结果放ISA模型，Isla核心保留通用FP映射。
- 当前flags+result helper契约要求先建立模型包装，才能移除核心里的ISA特判；通用ToIEEE/ToUnsigned的Sail原语出口仍需补齐。这里只提出接口边界，未改实现。

## 扩展调查补充（历史记录）

- 接口层覆盖67个无函数体 helper；RVV经逐元素 Sail 函数复用这些 helper，相关缺陷也影响向量浮点。FD_FLOAT 共89个 clause，默认 `make solve` 排除该组。
- 除下述原三项问题，本轮确认 Sub 的 NX 用 Add 公式、NaN/invalid 多置 NX、负 qNaN 开方误置 NV、浮点↔整数转换范围/符号处理错误。`f32ToUi32(+0, RDN)` 可由源码推导错误返回 `0xffffffff`，已经影响结果位。
- f16/f32→i64/ui64 的界构造存在内部宽度不足导致的下溢/错误移位风险；未动态复现，详见报告。
- 21个测试中20个调用Z3、1个只测分发；输入全具体，只有RNE和少量RTZ。作者报告的通过不覆盖本轮反例；数值/NV/转换精确度声明应收紧。
- 后续修复应覆盖完整结果和5位flags，并适配SMT初始化、求解配置及IR版本，再做同语义SoftFloat对照和RVV集成。原先仅列三项修复的建议不再足够；现行参考来源和范围以计划第3节为准。

## 最初分支中确认的事实（历史记录）

- 新增 5 个提交、8 个文件。浮点 helper 绑定在 `isla-lib/src/primop/float.rs`，执行入口在 `isla-lib/src/executor.rs:1196-1229`，SMT 转换在 `isla-lib/src/smt.rs` 与 `isla-lib/src/smt/smtlib.rs`。运行配置见分支 `configs/riscv64_difftest_fd.toml`、`scripts/run.mk`。
- `rv64d.ir` 中 79 个 `zriscv_*` val：12 个有 IR 函数体；67 个无函数体，均在分支 helper 名称解码覆盖范围内。12 个带函数体的名称是 `Recip7`/`Rsqrte7`（各 f16/f32/f64）和窄整数转换（f16 的 I8/Ui8/I16/Ui16、f32 的 I16/Ui16）。
- 分支覆盖 f16/f32/f64 的加减乘除、FMA、开方、比较、roundToInt、32/64 位整数双向转换、格式转换，以及 f32→BF16。结果通过 SMT FP 运算后转为 IEEE 位向量；fflags 在位向量表达式中单独计算。
- 已知语义近似：除法/FMA NX、一般下溢 UF、定向舍入下的 OF。性能方面，分支文档报告复杂 FP clause 求解很慢，可能超时或 OOM；这些是分支作者的报告，本轮未复测。

## 最初列出的四项问题（历史记录，非完整清单）

1. `float.rs:745-758`：符号 rm 的 ite 链始终返回 RNE。影响 rm/frm 符号化时的结果和依赖结果的标志。需增加符号 rm 测试，修正各分支舍入模式选择。
2. `float.rs:1162`：`Eq` 使用 signaling 比较的 NaN→NV 规则；SoftFloat `f32_eq` 对 qNaN 不置 invalid。需区分 Eq 与 Lt/Le，并覆盖 qNaN、sNaN。
3. `float.rs:1116-1124`：FMA 未检测无穷大乘积加反号无穷大；NV 漏报且 NaN 位模式不受规范化保护。需加入该无效情形测试。
4. 分支的精确度矩阵本身已承认 OF/UF/NX 的近似；若目标是与 RISC-V SoftFloat 逐位一致，还需精确编码这些异常条件。当前 21 个测试覆盖边界样本，未提供随机差分或全面精确度证明。

## 原后续验证建议（历史记录）

下段保留最初只针对三类错误的建议，现已由 [完整实施计划](plan.md)取代；不能据此只修三项后宣称完成。

在隔离的分支检出中先添加上述三类失败测试，再修正实现；随后运行 `cargo test -p isla-lib --lib softfloat` 和代表性 `make solve-FLEQ_S`/大路径浮点 clause，最后与 Sail SoftFloat 对数值结果及 fflags 做差分。此处记录为建议，未在本轮执行。
