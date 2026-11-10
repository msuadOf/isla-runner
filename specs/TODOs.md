# TODOs — 当前协作状态

**isarch 方案 B 整合（2026-11-09，候选已实施／限定实测通过，原分支收尾阻塞）**：Python 153/210、path_merging 6、executor 396/5 ignored、原生 fuzz 20/20 认证及 20 次变异均退出 0。原 Git 元数据只读，候选已保存，原分支未清理。[状态](../agents/isarch_integration/status.md)。

**两分支合并前审查（2026-11-10）**：loop-region-merge 与 isarch-quick-failures 限相对 `daf61c04` 审查及当轮修复完成；带修复后可合并，无新增失败，顶层仍有原有缺 IR 七项失败；合并树待验证。[状态](../agents/isla_premerge_review_20261110/status.md)。

**路径合并与缓存实测（2026-11-10，主轮运行／第二轮等待）**：只测名单 221 项，双并发、T32/2h、无限制预算；主轮 PID 2128518 保持运行。新增独立第二轮：环境错误按原 tactic 补跑，指定 Poison 错误改 default；等待主轮完全收尾后再启动，其他错误／partial／超时不补跑。当前候选四项，名单随主轮更新；五项规则测试通过，最终汇总合并两轮。[状态](../agents/pathmerge_cache_all_clauses_20261110/status.md)。

**执行帧 CoW（2026-11-09，候选完成／主线快进待执行）**：独立 feature 提交7885b24d基于849900a6，新增纯读取契约和默认深拷贝保护，适配现行路径合并。frame6、trace执行器498/5忽略、数组内存34及axiomatic检查通过；真实预检和隔离快进／重复执行通过。原.git只读，主线仍849900a6；未推送或移动gitlink，无性能PASS。[交付与执行入口](../agents/cow_local_frame_20261109/status.md)。

**MMU 实验关停归档（2026-11-09，完成）**：按用户决策，现行路径合并已解决关注场景的路径规模问题，fuzz保留更大探索空间，停止旧预算调优。归档只留Markdown和处理后JSON/CSV；清理旧运行目录44393文件、169658699字节，仅留报告入口。历史超时计数仍为下界，36例后处理不算语义接纳证明。[最终报告](../agents/mmu_symbolic_experiment/final-report.md)。

**三仓及各工作树暂存区外文件审计与清理（2026-11-09，完成）**：审查 52 个实际 Git 工作目录，按内容语义比对保留分支（runner 的 isarch/float/memory、Sail-RISC-V 的 isarch/fix/zvksha2-sew-assert/model-fix-vd-nf、Isla 的 isarch/feat/linearize-tri-strategy-grafted/feat/witness-randomization）。恢复 79 份未暂存工作文件到各自索引版本，安全删除 4,538 个确认无用的旧副本、编译缓存与字节码（无沙箱阻挡）。Sail-RISC-V 主区旧浮点副本已清除；Isla 历史浮点审查树、旧内存修复树及诊断源码树均已干净；独有的 COW、MMU 采样预算、semantic-mutation 实现及历史证据文档保留。两个功能工作区残留的 10 个已暂存 IR 文件亦已 unstage 并清除。全程未运行测试、未计算或生成哈希，备份快照完好。[完整审计及清单](../.worktree/unstaged-cleanup-20261109/audit.md)、[专题状态](../agents/unstaged_cleanup_20261109/status.md)。

**Isla Git 历史大体积 IR 永久清除与远端同步（2026-11-09，完成）**：按用户要求，使用 `git-filter-repo` 将 `rv32d.ir`、`rv64d.ir` 及 `ir/rv64d_v*.ir` 从 Isla 仓库历史（`isarch`、`feat/linearize-tri-strategy-grafted`、`feat/witness-randomization` 及 tag `allai`）中彻底抹除，upstream `master` 保持原 SHA `b898a55d` 不变。仓库打包体积由 101MB 缩减至 29MB，已强制推送到 GitHub 远端；isla-runner 主仓库 `isarch` 分支子模块 gitlink 已同步更新至新 SHA `849900a6` 并推送到远端。[专题状态](../agents/push_index_cleanup_20261109/status.md)。

**Sv39 局部线性化与笛卡尔积后处理 A/B 对照（2026-11-03，完成／实测限定验证）**：在 `.worktree/mmu-symbolic-experiment/` 下对齐单线程 60s 硬时限负载完成三组实测。基线 179 路径（123 废弃 Fault）、89,017 次 Z3 查询、46.33s SMT 耗时；局部线性化（压平 PTE 两检查）后路径降至 105（降 41.3%）、Z3 查询降至 36,314（降 59.2%），并穿透至 1GiB/2MiB/4KiB 全部 3 级结构模板，但因权限和更新分支存在仍超时；基于模板的笛卡尔积后处理在 70.36ms 内批量解出 36 个微架构用例（0.452ms/例），100% 通过 Sv39 合法性核对。确立了“控制流骨架探索 + 数据流笛卡尔积扩增”的提效依据与边界。[报告](../.worktree/mmu-symbolic-experiment/exp-ab-comparison/comparison_report.json)、[状态](../agents/localized_path_merge_review/status.md)。 **2026-11-05 修订**：其中“100%通过Sv39合法性核对”依据手写小公式与写死模板，不能证明合法，现为待复验；新设计见[后处理展开方案](../agents/localized_path_merge_review/plan.md)。


**Isla通用分支设计解读与组合对照（2026-10-24，完成／只读核查）**：refactor/general-support与fix/general-review均为09fe582；相对7b7337b的14提交／19文件已沿执行、编码、物化、域约束和错误链路解释。原工作区对已解决fix＋float候选仍986同／15异／新增14，差异主要为复审修复、联合编码及五IR修复，无缺失；未合并或重跑功能测试。[详细说明](../agents/general_support_review/design-comparison-20261024.md)。

**Sail-RISC-V旧分类分支清理（2026-10-24，完成）**：按用户要求删除本地feat/sail-riscv-by-category-20261019；工作树保留为detached 3ea3cbaf，两条20261022模型分类分支保留，未删除文件或操作远端。[记录](../agents/sail_riscv_commit_review/status.md)。

**微架构反馈量与创新性（2026-10-23，文献讨论）**：核实 DRVFuzz 2026 的有序语义转移并补充压力、事件路径、数据传播与双执行反馈；提出语义条件下的实际事件关系、来源和向量子事务等候选，区分已有 DV 方法与待查新贡献。仅新增研究文档，无实现／新实验；下一步讨论指标与 DUT 可观测性。[专题](../agents/semantic_mutation_fuzzing/microarchitecture-feedback.md)、[来源](../agents/semantic_mutation_fuzzing/microarchitecture-feedback-sources.json)、[状态](../agents/semantic_mutation_fuzzing/status.md)。

**Isla反馈覆盖率知识准备（2026-10-22，文献整理完成）**：按用户当前要求先学习2025–2026 CPU／软件fuzzing如何选反馈，再谈本地CPU工具的指标；当前不继续实现／实验。已核实结构／数据／语义／目标反馈与不同调度作用，补读FuSS全文并比较其与SysFuSS／S²F／ColorGo的求解闭环，区分观测反馈、奖励、判错和评测。下条pilot保留历史适用范围。[系统综述](../agents/semantic_mutation_fuzzing/coverage-feedback-review.md)、[来源](../agents/semantic_mutation_fuzzing/coverage-feedback-sources.json)、[当前状态](../agents/semantic_mutation_fuzzing/status.md)。

**Isla 语义约束变异（2026-10-22，实验设计完成／生成侧 pilot）**：对照 2025–2026 工作并建立 E0–E7 独立对照。既有随机化2fefa72上两个目标开关各三次，共12次退出0／168条记录；vl并集5→13、1→8，中位命令耗时约+10.11%／+6.43%。仅为生成侧取值多样性观察：旧导出字段随开关变化，VSETIVLI覆盖旧vl；无新增DUT／RTL覆盖／检错PASS。新变异器与反馈闭环尚未实现，下一步选完整可重放访存种子、补E0负对照。[实验矩阵](../agents/semantic_mutation_fuzzing/experiments.md)、[结果及限制](../agents/semantic_mutation_fuzzing/pilot-results.md)、[状态](../agents/semantic_mutation_fuzzing/status.md)。

**Sail-RISC-V双议题按model重组（2026-10-22，完成／限定验证）**：共同基线4f2ac293；内存分支1fa93117含2提交，通用＋浮点分支18389a89先4通用后10浮点，通用边界0de6edd1。每提交含model文件，配套151路径保留，后者末端tree等于3ea3cbaf；最终32次精确普通／SYMBOLIC严格检查均通过。两新worktree干净、未push；原工作区／索引字节／旧分支／父gitlink与根仓float/memory指针保持。未生成IR或新增数值／C++／硬件验收。[交付与提交索引](../agents/sail_riscv_commit_review/topics-20261022.md)。

**Sail-RISC-V分支引用清理（2026-10-21，完成）**：按用户要求删除本地feat/sail-riscv-review-20261016与同名-readable分支、本地跟踪引用origin/fix/zfa-bf16-assembly；追加授权后也删除GitHub分支fix/zfa-bf16-assembly，push及远端不存在核对均退出0。原split工作树保留为detached cfde70ec，功能归组分支3ea3cbaf及原暂存改动不变。历史交付记录保留。[状态与核账](../agents/sail_riscv_commit_review/status.md)。

**根仓双议题版本与Sail-RISC-V独审（2026-10-21，完成／限定验证）**：float@3bb9e8d固定Isla be1296b＋模型候选3ea3cbaf并保存独审，memory@8b24dc8固定47ac90c＋4f2ac293，独立工作树均干净。两套manifest/gitlink/checkout/origin/IR哈希及初始化核对通过，原工作区保留；TLS查询失败、未push、无联合功能验收。独立subagent确认工具链P1和三个测试入口P2，未发现新确证数值／最终状态回归；18个普通C++算术包装704880调用一致（含重复），不外推其余包装或SYMBOLIC。[版本入口](topic-versions.md)、[实施与证据](../agents/branch_merge_review/status.md)、[独立审阅](../agents/sail_riscv_commit_review/independent-review-20261021.md)。

**分支与合并选择核查（2026-10-21，调查完成／未实施合并）**：定位Isla内存47ac90c、仅浮点be1296b、通用09fe582与随机化2fefa72；原7b7337b仍有24个dirty路径。Sail-RISC-V三条拆分链最终tree相同，仅较原索引少12pyc。确认detached cf128bb仅合浮点，通用＋浮点54fb4e8e仍待提交；7组文本合并试算已列冲突。建议按职责整合、保留可选项，未运行功能测试或移动分支，远端TLS查询失败。[报告与选择](../agents/branch_merge_review/report.md)。

**Sail-RISC-V 按功能重组提交（2026-10-19，完成／限定验证）**：`feat/sail-riscv-by-category-20261019@3ea3cbaf`，独立工作树 `.worktree/sail-riscv-by-category-20261019`；准确基线4f2ac293，11个模型功能＋1个忽略规则提交。最终完整tree等于755fea6e，151路径保留；22次精确中间树双模式严格类型检查通过，原两个工作树/旧分支/索引/gitlink保持，新worktree干净、未push。本轮未生成IR或验数值/C++/硬件。[交付与证据](../agents/sail_riscv_commit_review/commits-by-category-20261019.md)。

**FLI/BF16 上游修复PR（2026-10-18，已发布／待审阅）**：[riscv/sail-riscv #2030](https://github.com/riscv/sail-riscv/pull/2030)，`fbacdfff`，e5acebb0基线1提交/5文件。Sail0.20.3全模型严格检查、定向C/C++与104文本/LLVM编码、32往返、GNU12项及格式/拼写通过，DCO通过；未验完整CMake/CTest/其他CI，原子仓和gitlink保留。[记录](../agents/sail_riscv_commit_review/pr-1a135b24-20261018.md)。

**1a135b24 上游核查（2026-10-18，完成／问题仍在）**：官方最新master `e5acebb0`（0.16）仍有FLI常量索引文本和四条BF16分隔错误；抽取实际映射104条被LLVM全部拒绝，临时模型补丁后104文本/编码及32往返通过；GNU另确认FLI静默错码。检索未见专门修复，#1008为相关通用议题；未发布issue，原子仓/索引/gitlink保留。[证据与建议](../agents/sail_riscv_commit_review/upstream-1a135b24-20261018.md)。

**FLI小常量可读性复核（2026-10-18，完成／限定PASS）**：四个长小数的精确值核对正确；普通/科学计数/十六进制浮点形式在GNU as2.45.50及LLVM MC22.1.8下共24次FLI.S汇编编码一致，`0x1p-16` 等写法可读且可用。未改生产映射或验H/D。[证据](../agents/sail_riscv_commit_review/fli-syntax-20261017.md#2026-10-18-四个小常量的可读写法)。

**FLI GNU/LLVM语法复核（2026-10-17，完成／限定PASS）**：官方文档/源码及15次独立汇编确认，GNU as2.45.50/2.46与GCC14.2接受 `fli.s f0, 0x10`，但按16.0生成索引25，LLVM MC/Clang22.1.8拒绝；正确1.0文本在全部工具保留索引16。未改变模型/IR/索引/gitlink或运行硬件。[证据](../agents/sail_riscv_commit_review/fli-syntax-20261017.md)。

**Sail-RISC-V 合并价值说明（2026-10-16，审阅完成）**：按指定起点1a135b24至cfde70ec共22个实际提交，逐项说明价值、依赖及接纳条件；优先正确性修复，共用后端和大范围lane优化需补精确验证。确认d59577a0兼含widening reduction SEW8合法域修复。无新功能测试、未合并或改变源码/索引/gitlink。[逐提交建议](../agents/sail_riscv_commit_review/merge-value-20261016.md)。

**Sail-RISC-V 分批提交（2026-10-16，已完成／限定验证）**：`.worktree/sail-riscv-split-20261016`、`feat/sail-riscv-review-20261016@cfde70ec`新增23个单功能提交；163件完整复制、151件非缓存入库、12pyc保留本地。最终tree与原索引排除pyc后一致，原HEAD/分支/索引字节/补丁/文件及父gitlink保留，新worktree干净、未push。42次逐层双模式类型检查、汇编104/FLI32、flags方程、完整C++、BF16两项CTest、共享类型/AMO及move14通过；旧vector helper构造器失败，其他旧fixture/workaround/工具链边界仍在，未验全量或每层C++。[实际提交与完整文件索引](../agents/sail_riscv_commit_review/commits-20261016.md)。

**Sail-RISC-V 逐文件说明（2026-10-15，调查完成／未提交）**：当前HEAD/gitlink与163路径暂存补丁哈希均与10-14审阅一致；14个建议commit的逐文件说明覆盖151个非缓存路径，另列12个pyc排除项，并给出共享文件的函数/hunk边界。本轮未重跑功能验证，未改子模块源码/索引或实际拆分。[完整清单](../agents/sail_riscv_commit_review/file-details.md)。

**Sail-RISC-V 分批提交审阅（2026-10-14，调查完成／待用户判断）**：`feat/isla-workarounds@4f2ac293` 的163个暂存文件整理为14个建议单元，区分公共Bool接口、小修复、共用浮点后端和向量改写；未stage/unstage/commit或改生产源码。当前汇编104文本/编码及32FLI往返通过，4项lane源码检查通过；旧合法性fixture/纯比较恢复失败、minmax检查器过时，workaround坐标与空白检查失败；12个暂存pyc建议排除。完整后端还依赖仓库外Sail编译器补丁，精确中间候选及全模型未复验。[方案、文件映射与检查](../agents/sail_riscv_commit_review/report.md)。

**两分支试合并核对（2026-10-08，完成／意图一致）**：`feat/float-only-20261008@be1296b`＋`refactor/general-support-20261007@09fe582` 的合并候选相对原isla最终内容986同／15异／新增14，含通用与IR后续修复；两处冲突已在隔离目录解决。用户澄清等价指代码意图／预期效果，允许bug fix，按此口径一致；前轮否定仅限文件树／精确行为。另已按用户要求创建干净detached基线工作树`.worktree/isla-float-support@7b7337b`，原工作区保留。候选93库＋25bin、浮点10、集成15、默认编译／fmt通过；原HEAD／索引／两层补丁／1001源码保留，未提交或移动生产分支，未make／全量／硬件。[核对记录](../agents/float_support_review/merge-check-20261008.md)。

**通用复审第二轮修复（2026-10-08，已接入／限定PASS）**：`refactor/general-support-20261007@09fe582`，40b2a48／83cd0dd／09fe582均为`fix(scope): 中文说明`，修复复审三P1及一P2。精确89＋25、组合93＋25及持久集成／默认编译／fmt通过；两种版本V128/V256的VSETIVLI各12gen、MRET4／ITYPE32／SRET6。原isla HEAD／索引／24文件不变，浮点剩余保留，未push／全量／硬件／整体性能验收。[交付与证据](../agents/general_support_review/fix2-20261008.md)。

**仅浮点修复（2026-10-08，已提交／限定PASS）**：`feat/float-only-20261008@be1296b`，`5ceb3ad`＋`be1296b`均为`fix(scope): 中文说明`。补齐4旧IR helper、修复5IR快速FPR状态，保留RV32 SD31及历史v512实际256。1615helper、180状态＋20guard、原定向/legacy及4组make通过，旧V256 FLEQ.S0→16gen，独审通过。原isla HEAD／索引／两层补丁不变，未push／全77／硬件。[交付](../agents/float_only_review/fix.md)。

**通用分支最新复审（2026-10-08，完成／发现回归）**：`4b141eb` 对 `7b7337b`，主审与独立 gpt-6-astra high 确认三组 P1（MixedBits 访存／具化消费者、选模后编码拒绝丢失合法见证）及一组 P2（assert 转换与 mapping 默认拒绝）。新增 5＋1 探针基线通过、当前失败；同 IR V128/V256 VSETIVLI 各 12→0 gen／退出0，VS 非零诊断恢复12；原定向与 MRET 仍通过。整体未验收，不改生产代码／分支，待修复后复验。[报告](../agents/general_support_review/rereview-20261008.md)。

**仅浮点分支复审（2026-10-08，完成／发现新增P1）**：`d04883b` 删除全局分派但4份自带IR未迁移，helper对照基线4过／分支4败；公共旧IR入口退出0但0gen。d012继承FPR Dirty缺陷；327例／67helper数值及BF16无活动元素修复通过。旧限定PASS不覆盖这些缺口；未改生产代码。[报告](../agents/float_only_review/report.md)。



**仅浮点分支（2026-10-08，已完成／限定PASS）**：feat/float-only-20261008从7b7337b直接新增28f626a至d04883b六提交，无通用提交/未提交层，工作树干净。浮点10、legacy35、Target23、库68＋bin25及MRET4/BF16 39 gen通过；基线既有x0失败单列跳过。原isla保持不变。[记录](../agents/float_support_review/float-only-20261008.md)。

**通用审查修复（2026-10-08，已接入／限定PASS）**：`refactor/general-support-20261007@4b141eb`，三个 `fix(scope): 中文说明` 修复 MixedBits 消费者、宽值物化及 MPP 字段域；保留 Sail reset 的 MPP=0 例外。精确 81＋25、组合 85＋25、持久集成 8＋2＋3及定向/默认编译/fmt通过，精确与组合 V128/V256 MRET 四组各退出0、4 gen。独审通过，原工作树和通用浮点剩余保留，未push/全量/硬件。[交付与证据](../agents/general_support_review/fix.md)。


**浮点专用提交整理（2026-10-07，已完成／限定PASS）**：新工作树isla-float-20261007在2792afd上新增bc7bc59至2d46ce7六类提交，工作树干净；浮点10、legacy35、Target35、库83＋bin25及MRET4/BF16 39 gen通过。仅runner增加MixedBits兼容修正，原两工作树不变，已知通用回归未修；详见float-split-20261007记录。

**通用分支独立审查（2026-10-07，完成／发现回归）**：受审 `2792afd` 相对 `7b7337b`，主审与独立 gpt-6-astra high 一致确认两个 P1：MixedBits 拼接后消费者 Type；同一 V256 IR 的 MRET 基线 4 gen→分支 0 gen，退出仍为 0。另有 MPP 能力域遗漏。定向回归通过，但不能据此验收分支；缓存局部 Z3 调用 20,000→1，未证整体提速；全库两版均受旧 enum sort 重名阻断。无生产修改/提交。[报告与证据](../agents/general_support_review/report.md)。


**通用提交按类型重做（2026-10-07，已完成）**：4089545已替换为416b94f至2792afd的8类提交，各层定向测试通过；最终tree一致，原工作区及浮点剩余不变。工作树/分支沿用，未push；详见通用归并记录接续节。

**通用修改归并（2026-10-07，已完成）**：在`.worktree/isla-general-20261007`新分支已带入全部Isla改动，`4089545`一个commit收纳通用部分；浮点剩余未暂存，原工作区保留。精确候选定向测试及候选/完整组合MRET通过。[范围与验证](../agents/float_support_review/general-split-20261007.md)。

**局部结构修整（2026-10-07，已完成）**：四文件内联单调用逻辑、移除空转发、调整对象归属并恢复match布局；基线82、修改后82库＋25bin＋10浮点、默认编译/fmt及MRET通过。原索引和注释保留，未提交。[计划与验证](../agents/float_support_review/local-structure-20261007.md)。

**worker panic独立提交（2026-10-06）**：`7b7337b`，候选有界panic/执行器回归和编译/fmt通过；其他暂存及工作区内容保持，未push。[记录](../agents/float_support_review/solve-process-commit-20261006.md#接续worker-panic-记账独立提交)。

**smtperf测试独立提交（2026-10-06）**：`d9f0fe0`单文件+3/-1；两种feature各4/4、fmt通过，无生产逻辑变化，其他暂存/未暂存保留，未push。[记录](../agents/float_support_review/solve-process-commit-20261006.md#接续通用-smtperf-测试修正独立提交)。

**solve进程管理独立提交（2026-10-06，已完成）**：`1eddd68`提交四个脚本中的监督/清理及测试；候选12项、工作区MRET通过。浮点入口仍暂存，其余修改与原分层不变，未push。[计划和验证](../agents/float_support_review/solve-process-commit-20261006.md)。

**轨迹临时分支清理（2026-10-06）**：已按确认名单删除5个临时分支、移除两个trace worktree并清理3个失效登记；保留两个回退点和其他功能分支，运行输出已备份。主HEAD、暂存区及未提交文件核验不变。[记录](../agents/float_support_review/trace-composition-20261006.md#临时分支清理2026-10-06完成)。

**FLOAT-01 itrace数据归属（2026-10-06，限定PASS）**：重做两提交为 `69cf43a`＋`a9884b2`，恢复itrace::ItracePerInstr及itrace_records，通用接口保留trace命名；61/62项定向、fmt和MRET通过，原暂存两层补丁不变。未全量复验、未push。[记录](../agents/float_support_review/trace-composition-20261006.md#itrace-数据归属修正并重做两提交2026-10-06完成)。

**FLOAT-01 提交重做（2026-10-06）**：按要求将平级修正合入轨迹提交，当前 `9da2eaa`＋独立writer `48619f2`，替代旧三提交；最终tree不变，原验证适用，第一提交61项定向通过，暂存区/未提交文件不变，未push。[记录](../agents/float_support_review/trace-composition-20261006.md#按原提交重做2026-10-06完成)。

**FLOAT-01 tracetool平级结构（2026-10-06，限定PASS）**：`4a84366` 已迁回，itrace/ftrace/btrace平级，公共状态、writer和共享序列独立。三层定向、CLI、MRET同层输出对照通过；原暂存/未暂存分层保持。未push、未跑全量。[证据](../agents/float_support_review/trace-composition-20261006.md#tracetool-平级归属修正2026-10-06完成)。

**FLOAT-01 轨迹组合重组（2026-10-06，已迁回／限定PASS）**：`9d8b915`主轨迹＋`c1d6bc6`独立writer，替代旧三提交；静态清单、实际分支、签名及生成结果在精确和完整同层MRET对照一致，三层定向测试通过。原暂存/未暂存改动保留，备份分支和worktree保留；未push、未跑全量。[实施与验证](../agents/float_support_review/trace-composition-20261006.md)。


**catalog CLI（2026-10-05，已提交）**：`d21ad62` 新增 `--no-itrace-catalog`，默认行为不变；精确候选与工作区CLI开关对照、定向/编译/fmt及工作区MRET通过，未push；[计划与证据](../agents/float_support_review/catalog-boundary-20261005.md)。

**FLOAT-01 itrace 容量比较（2026-10-05）**：`64f74f3` amend 为 `5c376fb`，ChunkCapacity重载比较、默认Unlimited，可配置Limited(256)。两配置定向/编译/fmt及精确候选MRET通过，原暂存/未暂存补丁不变。[记录](../agents/float_support_review/catalog-boundary-20261005.md#容量类型与比较运算符-amend2026-10-05完成)。


**FLOAT-01 itrace 独立提交（2026-10-05）**：`64f74f3` 在 `ef4ea1d` 后单独提交共享前缀和writer唤醒，itrace.rs无剩余差异。精确候选定向/编译/fmt通过，完整工作区MRET退出0、4 gen；其他未提交改动保留，未跑全量、未push。[详细记录](../agents/float_support_review/catalog-boundary-20261005.md#后续两项-itrace-改动独立提交2026-10-05)。


**FLOAT-01 catalog 边界收缩（2026-10-05，限定 PASS）**：已amend为`ef4ea1d`，三文件仅含catalog/实际边/路径签名及显式输出模式；Vec/切片恢复，前缀共享与浮点使用的采样/frame接口移至暂存层，原其他修改保持。三层测试64＋24／82＋24／83＋24及executor/itrace/default/fmt通过；`make solve ALL=MRET THREADS=1 ITRACE=1`退出0，4 gen及trace观测与旧版一致。未跑全量；[详情](../agents/float_support_review/catalog-boundary-20261005.md)。

**FLOAT-01 catalog 局部修补（2026-10-03，限定 PASS）**：已 amend 为 `8545e7c`，exec.rs 相对父提交生产区仅 +13/-3，恢复原回调/排序/早退；撤销终态账本及case-id，仅保留catalog/实际边/共享前缀/路径签名关联。三层候选64＋24／82＋24／83＋24及定向检查通过，`make solve ALL=MRET THREADS=1 ITRACE=1` 退出0、4 gen。原浮点、IR、脚本和挂起修复继续保留未提交；未跑全量，旧schema证据不迁记。[详情](../agents/float_support_review/catalog-local-patch-20261003.md)。

**FLOAT-01 挂起修复（2026-09-30）**：原PID及父cargo已退出；异常完成记账/原panic传播、trace阻塞唤醒已修。红例10秒超时→修后通过，executor84/itrace72/isla库83及原挂起测试通过，每命令限时10秒；全isla-lib枚举重名失败、make solve未跑。未提交，保留原改动；[验证](../docs/RESULTS.md)。下条保留修前现场。

**FLOAT-01 挂起测试现场（2026-09-30）**：旧 catalog-minimal 候选 PID 1363231 约34小时未结束，trace writer 忙等占满一核；测试等待 pending=1，但 worker 已退出。异常完成记账漏洞与现场一致，原始 panic 待恢复；本次非 PASS。未改代码/杀进程；下一步补有界 panic 回归并修生命周期与阻塞唤醒，见 [状态](../agents/float_support_review/status.md)。

**MEM-COVER-01 T3b 最新 v3/v2 独立复验与上游发布（2026-09-30，限定 PASS）**：原 `case-007` 错位 `vsse32.v` 已最小化，**对齐**普通 RAM 也在最新 v3 `09453ff8` 停于目标 store 前；`--no-diff -C30000` 同样无进展，unit-stride 对照 GOOD TRAP。最新 v2 `e7bab53` 的对齐／错位 strided、unit 和 no-diff 四项均 GOOD TRAP。两名 agent 仅按[完整无附件 issue 正文](../agents/memsolve_branch_coverage/vsse32_issue/issue-body.md)独立构建/运行，核账见[findings](../agents/findings.md)。用户审核后已发布 [XiangShan #6655](https://github.com/OpenXiangShan/XiangShan/issues/6655)；线上正文一致，无附件、无模板标签（当前账号无加标签权限）。未证明独立 RTL 根因。此前“错位”为原发现地址，非现行必要触发条件；旧 `case-004` 仍与 #5279 同类，不计原创。

**MEM-COVER-01 T3b 原载体与 GitHub 去重（2026-09-30，限定复核）**：`case-007` 的错位 `vsse32.v` 确在目标 store 前停止提交，无 DiffTest 跑至 30000 周期仍冻结；普通 RAM 条件下未找到同条件上游报告，暂列新症状候选，独立根因待对齐对照／波形。`case-004` 的错位 `vse32.v` 已提交但首个读回仍为 `0xa5`，与既有 XiangShan #5279 同类，不计独立原创 bug；真实 RAM 写效与读转发机制未拆分。E 线草稿的 `vse32` 目标 PC 有误，须修订。[详细核账](../agents/findings.md)、[议题摘要](../agents/memsolve_branch_coverage/status.md)。

**FLOAT-01 73df 标量 `execute` arm 限定核账（2026-09-30）**：51 个 clause 的 `execute` 本体共 242 个词法 arm，51 份完整 trace 观察到 228；其余 14 个是固定 RV64／FLEN64 下不可达的 `xlen`／`flen` 断言失败臂。共享 helper、译码 guard、短路因素和 ITE 数值选择尚无同版完整可达分母，不能据此声称源码 branch 全闭合；[口径与证据](../agents/findings.md)。

**FLOAT-01 catalog观测范围收缩（2026-09-29）**：已amend为 `323021b`，只纳入catalog及关联信息；恢复原错误退出/trace策略，summary.complete只报告，保留8早退/1次最终SMT查询及原注释。精确64＋24、暂存82＋24、完整工作区83＋24及默认定向/编译/fmt通过（过滤已知x0失败），未跑全量solve/重放。原27文件暂存及exec.rs未暂存浮点层保留；[现行证据](../agents/float_support_review/catalog-commit-review-20260929.md#catalog限于观测信息2026-09-29)。31523ab及更早catalog记录为历史。

**FLOAT-01 XiangShan GitHub 浮点 issue 清单（2026-09-29，逐条核完）**：`OpenXiangShan/XiangShan` 全 898 条 issue 标题／正文和公开时间线均已读取；37 条时间线第二页补齐。四名 Sol＋主 agent 按 180/180/180/180/178 分批逐条判断，898/898 编号、顺序、评论数机器核对通过。[表格文件](../agents/float_support_review/xiangshan-github-float-issues.md)现列 27 条直接相关 XiangShan 浮点报告（12 open／15 closed）、17 条重复／参考模型／无效等相关报告及 7 条性能／FP 代码配置／构建交集；新识别 #2890 的 `vfmacc.vf` 工作负载、#3735 的 FP 调度参数笔误、#4980 的 MMIO `fld` DiffTest 同步，#6410 的 FP 泛化推论另列未证。关闭不自动等于本地修复；未运行硬件。[逐项总账](../agents/float_support_review/github-issue-audit/summary.json) SHA `491c2e30…af5cbb`、[快照](../agents/float_support_review/github-issues-all-20260929.json) SHA `b6af07e4…0c15e`、[完整公开时间线](../agents/float_support_review/github-issue-details-20260929.json) SHA `af17f7dc…990e29`。

**FLOAT-01 77 项直接入口完整 trace 基线（2026-09-29，整组未通过）**：隔离 `e893` IR／`196809a4` 运行器、无抽样、`make solve-fd-nonmem` `-j4`／300-270-30秒／ITRACE 已完成全 77 项启动退出：51 标量＋4 向量自然完成，55 份完整 JSON／1432 `gen`，22 向量外限 124 且无最终 JSON；进程/JSON/trace 守恒错误0，资源未止损。超时前缀 2635 次 fork，热点为 vstart 上界486、vm判断286、LMUL正负100、重叠检查158；`FVFTYPE`／`VFUNARY1` 局部抽样与隔离 `FVVTYPE` 按 lane 延迟计算候选均未在300秒内收束。只计符号执行基线，源码有效 if/else、enum、数值域覆盖未签；正式77项签收仍0/77。[逐项报告和证据](../agents/float_support_review/vector-sampling-20260929.md#直接入口完整-trace-批次与卡点2026-09-29)。

**FLOAT-01 标量运行结果本地备份（2026-09-29，PASS）**：73df v3 的51个标量求解目标（1344 gen）JSON／日志／trace、冻结IR／配置／运行器，以及当前工作区 XiangShan DiffTest 输入、ELF、逐例结果、重试诊断和受测emu/NEMU已封为本工作区`archives/_raw/float-scalar-73df-20260929.tar.zst`（约80MiB，SHA-256 `c0111394…09815`）。5639个原始文件／链接有逐项清单；压缩包完整性、tar内容与现存原件比较、原件逐项哈希均通过。原件保留；`_raw/`被Git忽略，仅本机备份。[备份说明](../archives/float-scalar-2026-09-29/README.md)。

**MEM-XREF-01 GitHub 内存 issue 对照（2026-09-29，限定范围 PASS）**：核对 XiangShan #6475/#6486/#6296/#6605/#6085、已合并 PR #6316 和 Sail-RISC-V #1574/#1752；当前工作区定向 `vsseg3e32` 触发 ROB 断言，nf=2 对照通过；GitHub #6486 原 ELF 在本地 emu 复现同 PC store 数据分歧，合成单指令非零源值用例通过。旧 #6475 自动批次未选触发编码，属于生成／见证覆盖而非 pipeline 无法编译；#1574 缺错位成功见证且当前配置关闭错位访问；#6605 locked PMP 被旧配置及重放前导排除；#6085 旧批无最终 JSON。已纠正“向量／AMO 低地址错位都被 pipeline preclass 跳过”的泛化：W24 与当前正则仅匹配标量 `sb/sh/sw/sd`。没有 Z3 SAT 错判证据，#6486 所需精确前态与序列依赖尚未拆开。定向[机器核账](../difftest-xiangshan/work/github-memory-review/evidence.json) SHA-256 `55c8474a…f45521`，分组与版本限制见[专题报告](../agents/memory_github_xref/report.md)；不迁记历史内存分支的全量 PASS。

**MEM-XREF-01 已修复 bug 触发覆盖补账（2026-09-29，限定 PASS）**：旧 Vext JSON 的 #5809 `vmv.x.s`＋`vill=1` 原始行经当前工作区 pipeline 重编后，XiangShan `a13efc8` payload 报 cause 2、GOODTRAP／退出 0；#5744 修复提交在当前 HEAD 祖先链，计“历史求解触发条件覆盖并验证修复后行为”，不计当前 DUT bug、73df 标量浮点或 d012 官方求解。旧 trap 补跑基线 `case-4815` 已曾记 success；最初 Retire-only 批次过滤和后续补跑不可混写。#5739 缺 `csrr vl` 序列，#6316 缺 MMIO／NC 条件证明，均不计覆盖。[逐项归因](../agents/memory_github_xref/report.md#已修复-bug-的触发条件覆盖另列的向量非访存例)、[机器核账](../difftest-xiangshan/work/github-memory-review/fixed-coverage-evidence.json) SHA-256 `4af0be30…33f615`；旧 Vext IR／配置未重新绑定。

**FLOAT-01 浮点向量抽样接续（2026-09-29，整组未通过）**：现工作树的 Sail 宽度 guard 与 Isla 终态编码见证修复已实施、未暂存；Sail 双后端严格检查、实验 V128 IR 生成、Isla 23 项定向测试通过。同 IR 的独立具体编码／状态样例八包894/894通过，限列定输入。IR `e893e127…4d9`＋运行器 `196809a4…a81c8` 的 26 向量 60 秒、8 路×T2 预检中，仅 `VFMVFS`／`VFMVSF` 自然退出并有完整 JSON（6／18 可编码 gen），另 24 项外限无最终 JSON。局部采样仍未使 `FVFTYPE` 收束；BF16／widening 的每路径5次 fork 试验没有 Retire。两项成功目标仅完成终态与观察分支核账，尚未证明静态源码分母、值域、物理译码及完整回放；正式77项签收仍0/77。正式主 IR 仍 d012，未运行全量 `make solve-fd-nonmem`。[实施、版本、逐次结果与下一步](../agents/float_support_review/vector-sampling-20260929.md)。

**FLOAT-01 历史全批卡点回查（2026-09-29，只读）**：d012／1dcc 分别确有77项目标的全启动退出账本，但不是77项全完成；73df剩余20个向量的19×30分钟＋`FVFTYPE`两小时均外限无最终JSON。19份原日志58,845个实际fork集中于译码、变量宽度guard、LMUL/寄存器组与vstart；`FVFTYPE`两小时95,679次已完成SAT检查的累计耗时占匹配worker窗口约98%，没有单次长期阻塞。旧FullEncoded32入口的结论不直接迁给当前直接`zexecute`。[版本与聚合证据](../agents/float_support_review/vector-sampling-20260929.md#已有完整批次与长时卡点复核2026-09-29只读)。

**FLOAT-01 catalog 回调结构恢复（2026-09-29）**：用户要求保留注释并继续最小化结构改动，已amend为 `31523ab`。恢复父提交原callback布局/日志/注释，通过原submit_itrace追加信息；隔离64库＋24bin、工作区82库＋24bin及默认collector/编译/fmt通过（过滤已知x0失败）。原27文件暂存保留、无unstaged；未跑全量solve/硬件重放。[现行证据](../agents/float_support_review/catalog-commit-review-20260929.md#恢复回调原结构和注释2026-09-29)，下方6fef及更早记录为历史。

**FLOAT-01 当前工作区 XiangShan DiffTest（2026-09-29，PASS／限定范围）**：冻结 73df IR、v3 Isla 二进制、FD 配置的 51 个标量 JSON 共 1344 条，在本仓 `difftest-xiangshan/xiangshan@a13efc8` 的 MinimalConfig `emu` `8714169…a85ee`＋同 checkout NEMU SO `9188e7d…ef43` 重跑；1322 条可支持输入（1145 Retire＋177 Illegal）最终全部 GOODTRAP／退出0，32 个 FPR 原始位值与 fcsr 的 Isla post 检查通过。22 条 BF16 Retire 于 payload 报 cause 2，单列为本配置不支持；FPR 一位错误负对照停在指定检查循环。首轮30秒、24路产生超时后封存，120秒、24路及5条低并发重试形成最终成功账本，不把超时 trace 计 PASS。[本地逐例审计](../difftest-xiangshan/work/float-v3-20260929/current-workspace-audit.json) SHA-256 `97b8dfe3…cb610bf`；[实施／运行记录](../agents/difftest_xiangshan_v/status.md)。未发现此输入分区的香山 bug；C++/Isla 全量重放、物理译码与源码 branch 闭合仍未完成，77 项正式签收不变。

**FLOAT-01 catalog 封装收敛（2026-09-29）**：按用户最小改动要求，已amend为 `6fefb6b`，exec.rs移除六个单调用/无生产调用函数，保留信息和行为；隔离64库＋24bin、主工作区82库＋24bin及默认collector/编译/fmt通过（仍过滤已知x0失败）。原27文件暂存保持、无unstaged；未跑全量solve/硬件重放，见[现行证据](../agents/float_support_review/catalog-commit-review-20260929.md#撤销单调用封装2026-09-29)。下面f5aa/d740均为历史阶段。

**FLOAT-01 catalog 最小修正（2026-09-29）**：已按用户要求 amend `d740e02` 为 `f5aa97d`；仅撤 exec.rs 两处结果白名单并补 finished 记账，保留物化/信息关联/模块结构。隔离66库＋24bin、主工作区84库＋24bin及默认定向/编译/fmt通过（库过滤已知x0失败），未跑全量solve/硬件重放。原27文件继续暂存、无unstaged，见[实施证据](../agents/float_support_review/catalog-commit-review-20260929.md#最小修正与-amend2026-09-29)。以下 d740e02 审查为修复前历史。

**FLOAT-01 d740e02 职责复审（2026-09-29）**：静态审查发现通用 collector 只接受两类 ExecutionResult，将 EBREAK/WFI 等正常架构结果误判为执行器错误（P1）；单提交主线及层级边界基本合理，建议拆开 catalog/格式选项和编排/报告模型。未改 Isla 源码、未新跑动态验证；下一步补异常结果回归并修分类，见[审查报告](../agents/float_support_review/catalog-commit-review-20260929.md)。

**FLOAT-01 catalog 单提交收拢（2026-09-29）**：按用户纠偏将窄范围 `1b7276b` amend 为 `d740e02`，父提交仍 `b18d6b7`；catalog、分支轨迹、终态关联及前缀共享统一7文件，浮点/完整状态等其余改动继续暂存。72项trace、83项executor、65库＋24bin及默认编译/fmt通过；另有原提交可复现的target x0测试失败，过滤后回归，未跑全量solve。原index及31个工作区文件字节保持。见[提交与验证](../agents/float_support_review/status.md#catalog-单提交收拢2026-09-29)。

本文件是根仓库动态议题状态总表。目标与验收口径见 [GOAL.md](GOAL.md)，逐次验证与历史证据见 [RESULTS.md](../docs/RESULTS.md)及保持原位的 `agents/` 专题记录。下表从议题状态提炼，历史实验的“已完成”不自动代表当前工作树的 PASS。

**FLOAT-01 catalog 原因回查（2026-09-29）**：已核实其用于解决 assert 改写后的运行时PC/原IR定位失配；紧凑输出则是后续有明确批准与历史体积对照的优化。删编码wrapper不消除assert定位需要。本轮未改代码或重跑实验，见[专题说明](../agents/float_support_review/status.md#catalog-引入原因回查2026-09-29)。

**FLOAT-01 编码残留清理（2026-09-28）**：用户限定只清理暂存新增范围、保留原有求解后编码输出；已在工作区 `exec.rs` 删除编码模式框架/校验/专属字段及FS/VS钉值。真实物化16组合红绿通过，84库＋24bin（itrace,smt-thread-interrupt）及fmt检查 PASS；未重新暂存、未跑全量 solve/重放。catalog仅解释未改，见[实施接续](../agents/float_support_review/scope-review-20260928.md#用户明确边界后的实施接续)。

**FLOAT-01 范围 review（2026-09-28）**：按实际 `isla@b18d6b7`＋31 个暂存文件完成聚焦/封装审查，未改生产代码。FP 核心方向合理；发现 FS/VS 全局见证约束冲突、不可达完整编码入口、隐式 trace 格式变化及 Python 测试环境硬编码。默认 features 小测试 10＋24＋84 PASS，系统 Python 清理兼容测试 FAIL；修复与全量复验未进行，见[审查报告](../agents/float_support_review/scope-review-20260928.md)。

**FLOAT-01 最新接续（2026-09-28）**：恢复直接 `zexecute` 入口后，73df 隔离 IR 与 v3 运行器（SHA-256 `4e315e9a…59ae0`）、FD 配置 `20851fdb…723d0` 的 51 个标量目标在完整符号输入配置域、`make -j48`、1800/1740/30 秒、ITRACE 下全部正常退出并逐条核对 JSON/日志/trace，1344 gen；[逐项目标账本](../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/batch-v3-scalar-audit.json)。这是**求解候选 51/77**，物理译码、C++/Isla 重放及源码 branch 闭合未签；当前 v3 整组正式验收 0/77。向量 v2 的 `-j16` 批次因具体编码失败和 Sail `execute` Assertion 主动中止，最终 23 启动、7 份不完整 JSON、16 项无最终 JSON、3 项未启动，0 项完成；v3 `VFMVFS` 定向预检仍 3 Retire＋3 Illegal＋2 物化错误＋1 Assertion、退出 1，26 向量全未完成。现有 replay runner 对当前 `isla-lib` 有 6 处 API 编译不匹配。旧 56cc 的 57/77 与重放保持历史版本限定；正式主 IR 仍 d012。根因、源文件行号、运行版本和后续顺序见[浮点专题最新状态](../agents/float_support_review/status.md)。

## 更新规则

- 每项分别写**实施**和**验证**。验证用 `PASS`、`FAIL`、`未测`、`待复验`、`阻塞` 或 `待核实`；PASS 必须有可追溯证据。
- 修改实现、IR 或关键配置后，受影响的旧 PASS 退回待复验；历史结果保留在 `docs/RESULTS.md` 或专题文件。
- 本表给当前判断和下一步，实验过程、完整命令及日志分析写入专题文件。修改细节后同步本表对应行。
- 对仅有历史记录、无法判定现行版本的议题，标“历史/待核实”，不要推测为已验收。

| ID | 议题 | 实施 | 验证 | 证据与下一步 |
| --- | --- | --- | --- | --- |
| DOC-01 | 按 nacc_boom 方案重构项目级文档 | 已完成 | PASS（原路径、链接与静态检查） | [议题摘要](../agents/agent_collaboration_rules/status.md)、[实施与修正记录](../agents/agent_collaboration_rules/migration.md)；`agents/` 文件留在原位。 |
| INIT-01 | 依赖仓库初始化 | 已实现 | PASS（入口静态验证） | [历史状态](../agents/init_repositories/status.md)、[提交整理](../agents/commit_workspace_audit/status.md)；当前 `init.sh --help` 已核对，动态 checkout 结果以原记录和现工作树为准。 |
| INST-01 | 指令扩展分组表 | 已记录实现 | 待核实 | [状态](../agents/instruction_extension_tables/status.md)；复用前核对当前 Isla 代码和测试。 |
| ZSTORE-01 | zSTORE 路径爆炸与 PMA/PMP | 历史多阶段实现 | 待复验 | [状态](../agents/zSTORE_path_explosion/status.md)、[审查](../agents/zSTORE_path_explosion/audit.md)；先确认当前 IR/配置，再决定 Phase 5 结论能否复用。 |
| VMASK-01 | read_vmask A/B 迭代 | 历史研究 | 待核实 | [状态](../agents/read_vmask_ab_iterate/status.md)、[报告](../agents/read_vmask_ab_iterate/report.md)。 |
| VINIT-01 | V 扩展上下文初始化 | 历史实现 | 待复验 | [状态](../agents/v-ext-init/status.md)；原记录的测试结果只对应当时 assembly-gen 版本。 |
| VDEDUP-01 | V 扩展 SYMBOLIC 去重 | 历史实现 | 待复验 | [状态](../agents/v_symbolic_dedup/status.md)、[性能](../agents/v_symbolic_dedup_perf/report.md)。 |
| VDEDUP-02 | V 去重性能对照 | 已完成历史实验 | PASS（所记四类样本） | [状态](../agents/v_symbolic_dedup_perf/status.md)、[报告](../agents/v_symbolic_dedup_perf/report.md)；不代表全量 V 扩展性能。 |
| VWORK-01 | V IR 与 workaround 绑定 | 已记录同步 | PASS（2026-09-25 版本；当前源码待复验） | [历史状态](../agents/v_symbolic_ir_workarounds/status.md)；当前暂存 Sail 源码已有坐标漂移，不能沿用旧 PASS。 |
| VWORK-02 | workaround 配置直接归 Sail-RISC-V | 已实现并本地提交 | PASS（79 配置解析、Make 入口、Rust 告警单测、f8ce849 源码132区域/22锚点）；当前暂存源码 FAIL | [状态](../agents/workaround_ownership/status.md)；Isla 副本已删除，`strict=false` 失配告警；相关 Sail 代码修改造成旧坐标漂移，待逐区域重绑和同源 IR 复验。 |
| VVTYPE-01 | saturation qfaufbv | 历史实现 | PASS（所记定向测试） | [状态](../agents/vvtype_saturation_qfaufbv/status.md)；性能差异只有单轮信号。 |
| VVTYPE-02 | 局部限制与均衡采样 | 历史实验 | PASS（当时 30 分钟验收） | [状态](../agents/vvtype_balanced_local_limits/status.md)；对应旧 IR/配置。 |
| ARA-01 | Ara 批量 PoC | 历史实验已归档 | 待核实 | [状态](../agents/ara_poc_batch/status.md)、[冻结证据](../archives/ara/2026-09-23-poc-batch/README.md)。 |
| XS-01 | XiangShan RVV DiffTest | 历史 harness 实现 | 待复验 | [状态](../agents/difftest_xiangshan_v/status.md)；区分 fake smoke 与真实 DUT 回归。 |
| XS-02 | XiangShan Issue 草稿复现 | 历史实验已归档 | 待核实 | [状态](../agents/vext_issue_draft_reproduction/status.md)、[冻结证据](../archives/xiangshan/2026-09-23-issue-reproduction/README.md)。 |
| XS-03 | XiangShan/NutShell fuzzing | 隔离 worktree 历史实现 | 阻塞（真实 smoke） | [状态](../agents/xiangshan_nutshell_fuzzing/status.md)；需匹配 emulator 与 diff-so。 |
| SAIL-01 | Sail-RISC-V 符号执行改进研究 | 研究完成，方案待定 | 未测 | [状态](../agents/sail_riscv_improvement/status.md)、[报告](../agents/sail_riscv_improvement/report.md)。 |
| FLOAT-01 | Isla 浮点及统一 Sail 双后端 | 既有类型复用、状态/宽位输出/纯 helper 修复已冻结1dcc候选；C++/SoftFloat 与 Isla/Z3 共用模型P0通过，共享模型/CMake与公有adapter已应用；统一IR348147生成并通过decoder结构独审，v7修复平台源码快照遗漏，完整C++模拟器已链接，67 helper三方已过；下一V纯判断/AMO前端候选组件独审及合批构建通过，IR56cc69的V/AMO真实接线独审通过，严格129项保留/1项退役迁移及独审通过，官方两代表已启动，D FMA自然完成、V FMA外限124但已进入数值前沿，全77长批1800/1740/30秒的j8运行出现资源压力/信号退出，已停调度（26完成/6信号失败/8中断/37未启动）；j1 FVFTYPE亦因RSS增长至约119.5GiB受控停止，完整trace前缀共享已实现且72+2测试通过，组件独审通过，新j1完整30分钟峰值34.8GiB、17 Retire，但外限124无JSON；caller两表达式组件及完整e6a IR/SSA/严格行为迁移独审通过，准备新FVFTYPE对照；后续23家族j1全部自然完成，合并同56cc跨stage唯一完成50/77、23新增9692完整回放及独审通过；H/S FMA与三BIN_RM续批自然完成且27320输入双独审通过，VFMV又自然完成，VFMERGE独立长预算39分19秒自然完成，同56cc57/77唯一完成、20未完，完整30603输入首轮回放prepare失败；7615个vd=0 LLVM拒绝经Sail/IR guard逐case独审后，新目录30603输入全120片回放完成且真实退出0，完整数值/phase双独审与最终联证通过，57完成目标全部可用输出80416（80283gen＋91direct＋42derived）已闭环，机器映射排除重复并分列32runID/3源binary；e6a FVFTYPE仍30分钟外限无JSON，但五配置89定向双后端完整独审已过；LMUL+unary新441c同源CPP/IR完整构建PASS，strict/source及完整IR独审均通过，67 helper新83＋17586三方实际回归独审通过，新441c FVFTYPE2h仍外限124无JSON；RF/RFW/VFUNARY1新30分钟队列全外限124，BFVV与RFW独立2h均外限124无JSON，新441c VFUNARY1两小时仍外限124无JSON，接续nan86f FVFMTYPE30m亦外限124无JSON，新89整指令回放及来源/phase/数值独审通过、最终包已封，nan_unbox单行ITE经组件独审后已生产应用/双strict通过，下一86f112完整CPP/IR构建及完整IR/strict/source独审通过，新nan86f FVFTYPE两小时仍外限124无JSON，新67 helper及89整指令回放完整双独审通过；回放trace receipt六次读取减为3真＋3复用经小包独审通过；修订归约两helper经组件证及nan前件桥后应用、双strict通过，组合a040完整构建和完整IR/strict/source双独审PASS，新67 helper及89整指令配对最终独审通过，下一RFW stage因旧snapshot schema/多前像不兼容在启动前拒绝，显式装配经入口独审f43ad通过、a040 RFW/RF分别7200.76/7201.04秒外限124无JSON；fc4新67/89双独审及89最终封包已齐；首次FVVMTYPE/FVFMTYPE stage随后人为中断且无JSON，本轮新建两份独立stage以同517源码/b42二进制/新IR及79配置按1800/1740/30秒完整域/trace重启，运行中不计完成；最小默认off Z3诊断v2独审通过、独立30m诊断1800.55秒外限124无JSON，最终查询统计独审通过（199501完成调用/匹配worker窗口FFI97.942108%），匹配a040基线同预算独立诊断1800.60秒外限124无JSON，最终199004完成查询/97.864493%有限统计已独审；valid_reg_group末尾Eq热点隔离候选组件独审通过，生产来源桥已独审并应用、完整双strict通过，下一CPP/IR已完整构建PASS（fc4ce909），双独审/严格迁移已通过，新67 helper证f5313cf0及89 native/phase最终证8e774fd9与交付40296a3d已通过；同e7ba新版诊断1800.66秒外限124、无最终JSON，219605完成调用/FFI匹配窗口97.636480%，不计官方完成；源码合同导航v12共262入口并接17类剩余义务，56cc BF三配置symbolic RM局部历史证本轮封存（ceb6750e、无新动态运行），后继导航c2c42e05补已有encoder/bits引用，17全局/8 BF门仍OPEN、未迁fc4；历史PASS按各自冻结版本限定，正式主IR仍d012 | 1dcc定向累计9583/9583、helper及FD/VPR direct列定门槛PASS；新348147的17586 helper三方、9583定向结果/trace及direct通过；两热点仍外限124；1dcc全77为50自然退出0/27外限124，全组未通过；50项全部输出重放通过，27项无JSON、源码分支闭合未完成；统一双后端P0及公有adapter隔离门槛通过，完整67 helper列定数值三方通过，348147历史18584输入双后端配对及独审通过；56cc18584数值/状态配对及9583定向/严格trace通过；新发现decoder/encoder审计漏隐式异常lets，完整闭包纯读FAIL；经normalEnd域静态证明及独审恢复列定成功输入等价，动态observer三组25910全量及独审亦通过；fc4列定67 helper及89整指令新双后端复核PASS，旧56cc完成库存57/77、20未完，两个fc4新官方目标均1800秒外限124、无最终JSON，branch17门OPEN；旧证据保留，分支闭合待验 | [当前状态](../agents/float_support_review/status.md)、[统一方案](../agents/float_support_review/unified-backend-plan.md)、[77项审计](../agents/float_support_review/solve-audit-batch.md)。1dcc批按300/270/30秒完整trace结束，50完整目标的日志/trace守恒及18477条gen重放已核；旧c5批41退出0/36外限仅诊断，不转记。普通make solve排除浮点，使用solve-fd-nonmem；10访存不验收，不进入独立内存分支。09-28追加：fc4 FVVMTYPE/FVFMTYPE官方求解运行约7分钟后被人工终止、无JSON不计完成（库存57/77不变）；57目标80416 case分支覆盖核账完成——指令层控制流基本全达、Illegal全归因零残留，数据通路层系统性未达（BF16向量Retire全vl=0、标量操作数仅+0/qNaN两值、rm=101/110译码分支零覆盖），见[分支覆盖汇总](../agents/float_support_review/branch-coverage/SUMMARY.md)与[分布图](../isla/target/float-solve-evidence/branch-coverage-distribution-20260928/distribution.md)，补例走定向通道。本轮另核fc4 67 helper/89整指令终证哈希，重启两独立官方stage后FVVMTYPE/FVFMTYPE分别1800.64/1801.05秒外限124、无JSON，57/77保持；完整源码/IR相等顺序隔离候选构建PASS，五分钟同runtime诊断局部Eq调用162→30、FFI64.787→16.006秒，两边均外限124无JSON；30分钟新IR诊断也外限124/无JSON，五处Eq相对fc4旧诊断1612→384、FFI642.207→144.109秒，局部终态606→684，整项目标仍OPEN、不计官方完成；追加RM纯比较隔离候选完整CPP/IR及67 helper的83＋17586三方列定回归PASS，30分钟同runtime诊断RM位点448次／228.735秒→0、局部终态684→732，仍外限124/无最终JSON；同73df新版89原输入重新物化后五配置CPP/Isla实际配对89/89、178阶段异常写0，限列定输入不迁官方库存（[限定复核](../isla/target/float-solve-evidence/num-elem-order-rm-eq-replay89-20260928/independent-scope-review.json)）；fc4另有FADD.S保留rm=101原89定向证和本轮rm=110双后端新见证（[限定证](../isla/target/float-solve-evidence/fc4ce-rm6-directed-20260928/final-summary.json)），不迁56cc官方覆盖。见[退出账本](../isla/target/float-solve-evidence/fc4ce-resumed-two-targets-20260928-summary.json)与[性能对照](../agents/float_support_review/solve-fix-performance.md)。09-28本轮新IR续验：73df的FVFTYPE两小时诊断和FWFTYPE/VFUNARY0/FVFMATYPE/FVVMATYPE各30分钟诊断运行中；FVVMTYPE/FVFMTYPE同73df完整域1800秒均外限124无JSON，57/77仍不变（[双目标账本](../agents/float_support_review/status.md)）。09-28又追加：Z3无原生随机满足赋值经四路研究定论（实测/文档/中英社区，[汇总](../agents/float_support_review/z3-random-model/SUMMARY.md)），据用户指示在worktree实现`--witness-sampling <seed>[:dims]`见证值采样注入（splitmix64采样+check-sat-assuming，UNSAT回退，默认关零行为）、独审A–G全过并合回主isla工作树（VFMVFS A/B verdict全同、vl 6值→15值含VLMAX、同seed元数据一致；主树--lib 96/bin 23/专项14全绿），[实施记录](../agents/float_support_review/solve-fix-value-sampling.md)。随后按用户架构裁定重构下沉 smt 封装层（`isla-lib/src/smt/witness.rs`+isarch单开关`--witness-randomization <seed>`，删除isarch层维度实现），r2独审整改（fmt、f*实为BitVec(64)事实更正）后通过，r3增强（CLI无值自动seed、TOML键witness_randomization）后按用户指示改为纯净分支交付：`feat/witness-randomization`@`2fefa72`（纯f4f8e45基线仅witness，10文件+1255/−8，纯树测试全绿+e2e VFMVFS off=on一致、vl 5→8值），`feat/float-support`已回退`fc9ba69`仅含6个浮点批次，后续合并时再合witness；官方启用前须stage预检单独记账。09-28接续：73df候选对旧20未完目标均已建立独立完整域诊断stage；其20项隔离诊断全外限124无JSON（19项30分钟＋FVFTYPE两小时），库存57/77不变；两小时Z3单次检查均<5秒、实际fork6828，主因为路径增长，见[路径爆炸诊断](../agents/float_support_review/path-explosion-diagnosis-20260928.md)；按用户纠偏停止新跑和盲目优化（FVFTYPE两小时，其余30分钟），0项新增签收；机器队列及逐次退出见浮点专题状态。 |
| REPO-01 | 旧仓库 agent 重构提案 | 仅计划，未实施 | 未测 | [历史方案](../agents/repo_agent_restructure/plan.md)；其更大范围目录/子模块方案未获确认，不并入 DOC-01。 |
| MEM-REVIEW-01 | Isla 内存支持分支调查 | 静态调查完成；无代码修改 | 未测（动态） | [状态](../agents/memory_support_review/status.md)、[报告](../agents/memory_support_review/report.md)；远端 f06371f：已接初始内存和事件输出，未接同址读写一致性，事件逆序，压缩访存未续执行，真实读写/硬件重放尚缺验收。 |
| MEM-IMPL-01 | Isla 内存一致性实施（feat/memory-consistency） | W2-W6 subagent 实施完成：MemoryCallbacks 数组一致性（`memory_model.rs`）、事件正序、pre/post 物化、ExecuteAs 续执行、空区域约束修复、Solver Sat 模型缓存与超时降级、零配置全符号语义；W7 完成：显式区域联立 Unsat 早判死（回调返回 bool + 读/写后 check_sat 立即 BadRead/BadWrite）；W8 完成：区域约束语义分层（默认不生成区域地址约束、成功与 fault 路径并存；其 `ISLA_RISCV_CONSTRAIN_ADDR_TO_REGIONS` 白名单开关已被 W9 删除）；W9 完成：`region_type = "excluded"` 判死区域替换白名单（`smt_excluded_constraint`"触到即死"+ 立即 check_sat，具体地址命中直接 Err，零判死=零约束）；worktree `isla/.worktrees/memory-consistency`（基于 f06371f，已收口 commit 59e2b5d，含用户并行改动）；W12 完成：`difftest-xiangshan/pipeline.py` 消费 pre/post（前导 sb store/0xA5 填充/post 逐字节检查+park、两遍 ELF 窗口、`--sample-mode`），测试 +428、改动仅限 3 个允许文件；W14 完成：`riscv64_difftest_mem_excluded_pma.toml`（pma 对齐 emu 8TB + PMP 寄存器钉死 NAPOT-RWX）与 pipeline.py 预分类（tests +9 共 44/44），根仓库收口 commit b11a6f6 | 部分 PASS：单测（isla --lib 115 过+1 预存红、isla-lib 223 过）、CLI 三件套、零配置 zC_LD/zLOAD 闭环、zSTORE 定向模式闭环（19 写事件全 ∈ sym_ram、data==post 19/19）、W8 两档 600s RC=0（默认档 77 Retire/2554 AccessFault）、W9 两档（默认档复现 W8 基线逐项一致；判死档写事件落 MMIO 52→0、2579 gen 自洽）、W12 重放单测 34/34 与端到端成功路径 104/104 GOODTRAP（探针 256MB 上界 2/2）均有证据；fault 抽样 9 条 W13 裁定 5/2/2（5 条 pma 顶界 vs emu 8TB 不对齐、2 条低位 NEMU/emu mcause 真分歧、2 条 PMP 假 fault；证据 `/tmp/isla-memimpl-w13-20260927-053000/`）、W14 修复后 fault32 复跑 9 失败→0（30/30）、green 新分布 128 gen=24 成功/104 fault/图内假 fault 107→0、定向图外对照边界精确（证据 `/tmp/isla-memimpl-w14-20260927-065108/`）、W15 销案勘误（"2^43 非单调"为探针误读销案、35 探针手算 100% 吻合非 Isla bug；size 修正 0x7FF80000000，green 24 OK/104 FAULT 为修正后基线且 24 写事件全归 8TB 内、`-p isla --lib` 117 过/1 预置败；证据 `/tmp/isla-memimpl-w15-20260927-080623/`）、W16 后 `-p isla --lib` 118/118 全绿、预置失败清零（rv64_target_trait 断言未跟上 fd92696 设计变更；证据 `/tmp/isla-memimpl-w16-20260927-084122/`）、zC_LD 收敛与事件不能同得（fork 悬崖 9↔10）、无预算不收敛、默认档 fault:success≈33:1 为受限 | [状态](../agents/memory_support_review/status.md)、[实施计划](../agents/memory_support_review/plan.md)、[pipeline 计划](../agents/memory_support_review/plan-pipeline.md)；证据 `/tmp/isla-memimpl-w6-1532/`、`w7-1748/`、`w8-20260926-234713/`、`w9-20260927-023425/`、`w12-20260927-050541/`、`w14-20260927-065108/`、`w15-20260927-080623/`；WT 59e2b5d（W2-W14）→ f1fb43f（W15）→ 21b4388（W16）→ d643e0e（W17）→ 0c4fd52（W20）→ 898e267（W21）、根仓 b11a6f6→8cadc13→608f756→8631735→5ba0cec→6c56001（W18），此后每 W 一 commit；W10 转入 MEM-PMA-01、W13-W16 完成、"2^43 非单调"已销案；队列已清（rv64_target_trait 已由 W16 清零）；遗留：RV32::reg_list 旧语义、④⑤ 真分歧上报不修、mcause 断言、符号化平台属性、zC_LD 探索优化、MMIO 细化、unsat dump 撞名、按平台地图过滤、多指令序列。 |
| MEM-PMA-01 | Isla 符号化 PMA | S1 已完成（W10，同 worktree `isla/.worktrees/memory-consistency`）：TOML `[[pma_regions]]`（base/size + ram/rom/mmio/hole 别名或明细字段）→ `config.rs` 自校验解析 → `target.rs` 构造 `Val::List` → `isarch_main.rs` 写 `zpma_regions`；未配置不注入，IR 与模型零改动；S0 重放环境地图确认 DRAM [0x80000000,0x90000000)（W13 修订：该 emu 实际有效 RAM 为 [0x80000000,0x80000000000) 8TB，256MB 宏属 difftest csrc 侧不约束 emu）；S2 已完成最小实现（W17，worktree d643e0e）：PmaSize{Concrete|Symbolic{min,max}}、size="symbolic"+可选 size_bounds（默认 [0x1000,2^43) 锚 emu 顶界）、域校验硬失败、setup_pre_state 后 checkpoint 前注入、solve_pre_state 侧通道输出 size、新配置 `riscv64_difftest_mem_excluded_pma_sym.toml`；S4 pipeline 侧已完成（W18，根仓 6c56001）：解析 pma size 模型值、map-hypothesis 过滤（成功<顶界/fault≥顶界，不一致跳过计数）、`--map-limit` 可配、hypothesis_consistent 诊断，并修 8 字节占位 .data 误判 code-overlap；S3 属性符号化仍候选 | 部分 PASS：单测 6/6 GREEN、`-p isla --lib` 117 过+1 预存红、isla-lib 250 全过（跳 3 预存 enum）、fmt、shell config-error PASS（zSTORE shell 用例 180s 盒 SKIP，600s 证据覆盖）、三件套 3/3；zSTORE 600s 三组端到端——RED 复现 W9 基线、GREEN 131 写事件全落地图内且边界精确（max addr=0x8fffffff）、UNCONF 与基线一致；emu RAM 大小构建覆盖未确认为待核实（W13 实测修订为 8TB）；S2（W17）spike 三点单测过、钉址同址两类路径（Retire_Success+写事件/AccessFault）3/3 稳定 ~1.0s、具体基线回归一致、超域对照证域约束生效、回归 119/119+fmt 过（证据 `/tmp/isla-memimpl-w17-091536/`）；S4（W18）测试 61/61、case0 真机 GOODTRAP 1.39s、case1 正确跳过、W12 ok 重建 104/27 逐数一致、fault32 30/2 与预分类一致（证据 `/tmp/isla-memimpl-w18-20260927-104711/`） | [计划](../agents/memory_support_review/plan-pma.md)、[状态](../agents/memory_support_review/status.md)；证据 `/tmp/isla-memimpl-w10-20260927-032747/`（RESULT.txt/judge.py/三组 JSON）；S3 属性符号化为后续候选；S4 遗留：zLOAD 符号条目、多符号 region 仅记录 sizes。 |
| MEM-COVER-01 | 内存 clause 分支覆盖对照（W19+G1-G8） | 调查与对照完成；W20/W21 修复已提交（0c4fd52/898e267）；W24 campaign（WT e4410fe）完成生成+24 路重放并分诊 F1-F8；六线并行轮（2026-09-29）：C 修 F3/F4 并顺带修 F6(a)(b)（worktree 0d70b06+根仓 419dafb）、D 增 csr_sym_vs（9f82a87）、A 在隔离分支 model-fix-vd-nf@46f8273a 移植上游 #1752+#1744（不合回）、B1/B2/B3 上游交叉对照（纯研究） | 部分 PASS：45/48 clause 有 JSON、zAMO 670 gen、Zcd 恢复 32/32/24/24；W24 重放 1683 实跑 1307 pass（77.7%，剔环境类 89.8%）；上游对照定论——F1=PR#1752 已修（0.13）、F2=PR#1744 已配置化、F5=difftest#969、F8=裁定实现自由、#1574 判 Z3 未覆盖；C 复验 F3 7→0、F4 30→0、合计 517 pass（isla 127 绿/pipeline 77 绿）；A 探针 F1 翻 6/F2 翻 2、重放 4/4；D 四 clause 3-9 倍恢复超旧 survey；E 线定向复现已知 XiangShan bug 4/4 全触发（T1 #6475、T2 #6486 精化错选源、T3a #6316 类 v2/v3 均现、T3b #6296 族新变体疑似新 issue、T4 #6605 恶化为停摆） | [状态](../agents/memsolve_branch_coverage/status.md)、[合并矩阵](../agents/memsolve_branch_coverage/coverage-matrix.md)、[CSR 审计](../agents/memory_support_review/csr-audit.md)；证据 `/tmp/isla-memsolve-survey-20260927-125738/`、`campaign24-20260928-193712/SUMMARY.md`、`github-xref-b{1,2,3}/NOTES.md`、`model-fix-20260929/`、`isarch-fix-f3f4-20260929-005822/`、`vs-explore-20260929-004109/`、`xs-known-bugs-repro-20260929-034817/`（均在 /data1/baiyifan/tmp/）；emu 谱系：根仓 `difftest-xiangshan/xiangshan`@a13efc8775=v3（四 bug 全活）、`isla-xiangshanv2`@f86f50b83=v2；候选：P1 值域 signposting（启动）、模型修复转正、ldu 枚举过滤、LOAD 汇总修复、错位采样偏置、cherry-pick #1603/#1625/#1900、#1800/F5/E 线草稿上报、F7 前置 LR、VLX/VSX 泳道、emu 升级评估。 |
| MEM-BUGHUNT-01 | 找 bug 能力改造（signposting/预分片/守卫过滤） | 第一波 P1/P2/P3 已完成并提交（worktree 60ca0e0/58c9766/47ac90c、根仓 488803f）：P1 `[[value_hints]]`、P2 `[[encoding_slices]]`+`--instruction-bits` 向量译码 panic 根因修复、P3 译码回环过滤+preclass 可见化；第二波 P4 账本/P5 模式库/P6 序列重放待启动 | 部分 PASS：错位形态 0→192（#1574 类材料）、VSSEG 28/28 组合且 vsseg3e32 重放**无定向参数自动命中 #6475** ROB assert、VLX 缩域 32 条破超时、ldu 16→0、测试 140/148/80 绿、回归逐项一致（zSTORE 128/2579 按 P2 口径注记）；F 线验收战役完成：#6475 自动级 155 例、#6486 自动级 295 例含 41 例真分歧、三族新 DUT bug 候选自动发现（NC-1 死锁/NC-2 垃圾访存/NC-3 mtval+0x10）、AMO 过滤后全量重放 0 失败、zSTORE 错位 0→256+——改造达标；T3b 未复现（待原载体复验） | [计划](../agents/memory_support_review/plan-bughunt.md)、[findings](../agents/findings.md)、F 线产物根仓 `.tmp/accept1-20260929-124451/`（gitignored）；上游上报包 7 项（E 线四草稿+NC-1/2/3）；证据底座=W24 campaign+B 组归因+E 线定向复现。 |
| PREEXEC-01 | C ADD pre-exec constraints | 仅见计划 | 未测 | [计划原文](../agents/c_add_pre_exec_constraints/plan.md)；待核对实施状态。 |
| COMMIT-01 | 工作区提交审计 | 历史批次完成 | 待核实 | [状态](../agents/commit_workspace_audit/status.md)；仅描述 2026-09-23 批次。 |
| LOOPMERGE-01 | path merge 支持循环内分叉合并 | M0–M2、vector_update 改纯已提交，经合并前审查修复（6861c94e），与 QUICKFAIL-01 合入集成分支 `feat/isarch-integration-20261110`（c1559ad8）；226 个 clause 集成实测运行中 | 合并树 isla-lib 单元测试 844 通过；实测进行中 | [状态](../agents/loop_region_merge_20261110/status.md)、[设计与计划](../agents/loop_region_merge_20261110/plan.md)、实测目录 `.worktree/integration-run-20261110/` |
| QUICKFAIL-01 | isarch 快速失败修复（Poison/Z3、浮点函数缺失、无合法编码、未完成路径、LOAD_FP panic） | 四类修复和 Z3≥5.4.0 检测已提交（9a4f5c91，审查修复 02e92c2d），已合入集成分支 c1559ad8；剩 CPOP/CPOPW、LOAD_FP、浮点 helper | 原 Poison 37/39、无编码 10/10、未完成 22/22 通过（10 分钟外限）；make solve-MRET 通过 | [状态](../agents/isarch_quick_failures_20261110/status.md)、[诊断](../agents/isarch_quick_failures_20261110/diagnosis-20261110.md)、[修复后结果](../agents/isarch_quick_failures_20261110/after-fix-20261110.md) |
| GENERIC-01 | Isla 对 Sail 模型通用：模型语义迁到配置或模型侧 | 合法初态域、RVV 初态规则已迁到 `[constraints].initial` 与 `symbolic_registers`（集成分支 31a36d2f）；随机数待模型侧实现；映射名后续 | 等价证明通过；7 个 clause 回归一致 | [状态](../agents/isla_model_agnostic_20261110/status.md)、[审查](../agents/isla_model_agnostic_20261110/review-20261110.md) |

没有独立 `status.md` 的专题仍以其计划或报告作为证据入口。新增议题先在本表登记，再按根 `AGENTS.md` 的要求建立可审阅方案。

**初态 TOML 部分符号化（2026-10-29，已实现／限定验证）**：8948cc4已按要求合入refactor/general-support，支持通用位模式0/1/?/x，无架构字段别名；89/25及核心279（跳三项enum）通过，make solve-MRET四条初态断言通过；全量受基线可复现enum错误阻塞。原工作区/父gitlink保留。[状态和证据](../agents/initial_state_config/status.md)。

**初态配置合入后复审（2026-10-29）**：8948cc4实际复现两项P2配置panic（非法数值UTF-8／不支持的寄存器类型），已由ef882f0修复并合入general，负例退出1；90/279（跳三项）/25及MRET验证通过；[建议与证据](../agents/initial_state_config/review.md)。

**通用＋浮点组合复审（2026-10-29，完成／有待修项）**：ef882f0＋be1296b对7b7337b，发现独立runner缺ISAConfig新字段的P2；临时兼容补丁后1615helper/180state/20guard及94/25/267（跳三项）/20集成通过，公共短入口和显式初态约束通过。主体设计可接受，需修runner再正式合并；旧ret_val未具化与FS/VS偏好配置建议另列，未改正式分支。[报告](../agents/general_float_review_20261029/report.md)。

**种子候选包（2026-10-29，抽检／非全面覆盖）**：W19 内存调查 45 个 JSON、35 非空共 4124 条，含失败退出与空文件；本地精简目录及逐文件哈希核对完成。一个 VSETIVLI smoke 和一个 STORE 例本机重放成功；STORE sh 缺成功样本，LOAD 含 ldu 且生成退出非零。尚无全面模型路径覆盖、全量重放或迁移验证。[状态](../agents/semantic_mutation_fuzzing/status.md)。

**general/float顺序合并（2026-10-29，完成／限定验证）**：feat/float-support按2dbad3b先合general、9217e17再合float并补runner字段、31506ee修ret_val；独立GPT-6.1 Sol最终审阅通过。94/25与五make入口通过，最终1015件与受测候选一致，工作树干净；原24dirty文件完整stash保全。未push/未改父gitlink，未全77/硬件验收。[交付与证据](../agents/general_float_merge_20261029/status.md)。

**术语统一与提交说明修订（2026-10-29，完成）**：新增TRANSLATOR.md并由AGENTS.md声明为中英文术语依据；“物化返回值”改为“具体化返回值”，feat/float-support提交说明重做为daa8bb1，代码tree及父提交不变，未push。[术语](../TRANSLATOR.md)、[记录](../agents/general_float_merge_20261029/status.md)。

**两源分支术语统一并合回（2026-10-29，完成）**：general cc7700b、float-only99a28b0各自新增术语规范/入口，符号值动作改用concretize；目标顺序合并至75e7440。90＋3、65（跳原一项）及独立runner编译、最终94＋3通过；独立review确认无语义回退。general原dirty保留，未push/改gitlink。[状态](../agents/terminology_concretization_20261029/status.md)。

**术语合并历史重整（2026-10-29，完成）**：按澄清重做原两个merge，当前0df2388先general、42ac15e再float、b0138b7重放返回值修复；移除第一父链上的额外同步merge。最终tree完全不变，独立review核对通过，未push。[记录](../agents/terminology_concretization_20261029/status.md)。

**根仓float/memory更新（2026-10-30，完成／版本核对）**：float bb9d271固定Isla b0138b7＋模型18389a89，memory1731207固定Isla47ac90c＋模型1fa93117；gitlink/manifest/checkout/IR哈希及两套初始化检查通过，工作树干净。未重生IR/联合功能/推送。[记录](../agents/branch_merge_review/root-version-update-20261030.md)。

**根float/memory JSON语义独立复审（2026-10-30，完成／存在阻断）**：专项能力有正面测试，但memory源码/IR两项错配、float FLI文本错码及无partial覆盖合同阻止整体目标签收。18个新探针、1615helper/180state/20guard及30数组测试有证据；只读、未改分支。[报告](../agents/json_semantic_review_20261030/report.md)。

**JSON语义复审修复准备记录（2026-10-30；已完成，现行结果见末尾）**：同步两套IR、补结果合同与SC域，汇编要求GCC/Clang均通过且编码一致。[计划](../agents/json_semantic_fixes_20261030/plan.md)。

**JSON语义复审修复（2026-10-30，完成／限定验收）**：根float90bb726与memory31ef3b9固定新模型和完整重生IR；95/149项isarch、42项执行限制、浮点22步/1615helper通过；GCC/Clang264项JSON＋16项内存往返通过。partial/诊断/来源合同、SC双结果与源码预算迁移已提交。源码全控制流、全77/全访存域及硬件仍未验收，动态终值超时探针未触发。[报告](../agents/json_semantic_fixes_20261030/report.md)。

**双议题subagent独立复审（2026-10-30，进行中）**：分别评估当前float/memory固定模型、IR、JSON及覆盖证据，独立给出修改意见，源码只读。[计划](../agents/independent_topic_review_20261030/plan.md)。

**双议题subagent独立复审（2026-10-30，完成／未实施修复）**：float发现非法BF16布局Clang拒绝、默认算术见证全qNaN退化及ExecuteAs假完成；memory发现concrete/符号数组状态分裂、漏源GPR破坏重放及异常ret_val含Sym。14＋7有界新探针，两个独立报告分列实证与能力缺口；六个受审工作树版本/干净状态保持。[汇总](../agents/independent_topic_review_20261030/summary.md)。

**NaN-boxing显式分支恢复（2026-10-31，实施中）**：按用户要求恢复nan_unbox原if，完整重生浮点IR并核对两侧见证，不以未证实的性能收益保留路径合并。[计划](../agents/nan_unbox_branch_restore_20261031/plan.md)。

**NaN-boxing显式分支恢复（2026-10-31，完成／限定验收）**：根float1c7a354（Isla80231ce9／模型9c339044）恢复nan_unbox原if，五IR重生；普通严格检查、23步回归、两源boxing四组合及416＋20双汇编/make-FLEQ通过。四算术52→208条，有限数源0→40条；单次耗时9.78→55.70秒，不作同覆盖性能比。memory未动、其余review问题未修。[报告](../agents/nan_unbox_branch_restore_20261031/report.md)。

**分支合并同类盘点（2026-10-31，只读完成）**：nan_unbox以外仍有flags条件更新、min/max与分类/饱和、向量mask/归约及合法性聚合。局部存在1566→12、8lane256→1等实测，不能外推完整Clause收益或全覆盖；未批量回退。[报告](../agents/branch_folding_inventory_20261031/report.md)。

**浮点分支合并并行消融（2026-10-31，进行中）**：五组独立副本控制变量，完整Clause主测、组内A/B交替三重复，记录时间/fork/输出/覆盖及超时；不改生产分支。[协议](../agents/branch_ablation_20261031/protocol.md)。

**浮点分支合并并行消融（2026-10-31，完成／限定域）**：五组逐项完整IR与AB/BA/AB三对。min/max 5.510→12.816秒、20→36见证；mask 7.65→11.17秒、27→54，归约4.17→5.21秒、12→24；显式分支补条件见证。flags算术ITE约52.288秒完成、if三次60秒超时；NaN规范化与饱和同样ITE完成/if超时，分类及宽域guard双臂超时。guard窄域小幅耗时/非法分区取舍，不算等覆盖加速。生产版本/干净状态保持、未实施回退；全格式/全部调用点未验。[汇总与建议](../agents/branch_ablation_20261031/report.md)。

**消融2小时预算续测（2026-10-31，进行中）**：用户明确每Clause7200秒；原60秒超时只作历史短预算证据。flags算术、分类/NaN/饱和及宽域guard重测，两臂同预算，撤去30秒路径/10秒SMT截断，独立pair并行。结果待后台任务；生产未改。[修订协议](../agents/branch_ablation_20261031/protocol.md)。

**两小时消融核查更正（2026-11-01，续测中）**：分类769.93/1099.23秒、310/508条，两臂三次完整，if补齐十类；宽域guard132.69/133.68秒、81/108条均完整。发现未传SMT参数仍默认60秒，flags/NaN以partial退出而非外限；三项受影响实验现显式SMT7200秒重测，不沿用旧完成性建议。[核查](../agents/branch_ablation_20261031/budget-2h-audit-20261101.md)。

**浮点超时性能定位（2026-11-01，调查完成／未改生产）**：flags慢于包含f32/f64除法的changed可达性查询；NaN慢于isNaN(sqrt)查询。相同dump重放flags qfaufbv60秒unknown，qffp三次约3.71秒SAT；NaN37.74→约0.209秒。等价sqrt输入NaN/负非零条件在原query约0.108秒SAT，差异UNSAT。增量seed影响和完整Clause仍未验证，不以延长限时或合并分支替代性能处理。[报告](../agents/branch_ablation_20261031/solver-diagnosis/report.md)。

**Z3统一策略源码调查（2026-11-01，query验证完成／未接入）**：源码和probe确认Sail枚举阻断default的is-qffp分类；qffp直接调用提前浮点转换。统一simplify→dt2bv→fpa2bv→simplify→default通过25真实慢dump（flags9.3–16.8秒、NaN0.21–0.41秒）及10混合类型探针，2次C API带假设与模型原断言回读为true；完整Clause7200秒及seed接入未验证。[证据](../agents/branch_ablation_20261031/z3-strategy-source/report.md)。

**Z3上游贡献评估（2026-11-01，准备完成／未发布）**：六行独立例子仅增加无关枚举即可使default变慢；三次无枚举中位0.109秒，含枚举15.826秒（6.613–16.028），dt2bv后0.209秒。master相关浮点probe代码限制仍在，未编译master；建议提出受限混合类型分发性能议题和回归，而非正确性bug或无条件放宽datatype。未向社区发消息。[评估与草稿](../agents/branch_ablation_20261031/z3-upstream-assessment/report.md)。

**Z3性能issue发布（2026-11-01，完成）**：按用户要求提交并回读核对官方 [Z3Prover/z3 #11500](https://github.com/Z3Prover/z3/issues/11500)，包含独立枚举/浮点最小例、三重复对照和受限策略分发建议；OPEN，未创建PR或修改生产。[记录](../agents/branch_ablation_20261031/z3-upstream-assessment/status.md)。

**Z3 default浮点/枚举源码修复（2026-11-01，完成／限定验证）**：独立上游8fbb275分支fix/default-fp-enum-11500中新增受限mixed分发dt2bv→qffp，保留数组/ADT/proof等原路径。红例资源预算unknown→SAT；fpa及4组既有测试PASS、41query预期一致，2真实query假设双侧模型回读为true。未替换生产Z3/Isla、未PR；全Clause7200秒未验。[报告与补丁](../agents/branch_ablation_20261031/z3-upstream-fix/report.md)。

**Z3补丁独立审查（2026-11-01，进行中）**：两位reviewer独立审查源码等价性与动态类型/模型/证明边界，源码哈希冻结；发现问题后修复复审，不把既有自测当独审。[安排](../agents/branch_ablation_20261031/z3-upstream-fix/independent-review/plan.md)。

**Z3补丁独立审查完成（2026-11-01，修订后复验通过）**：两位独立reviewer发现大枚举性能/预算P2及域测试不足，已增加4096模型成本护栏并增强自由枚举域UNSAT回归；原反例关闭。56/110双侧功能执行、成本边界、假设/增量/资源恢复及原模型断言检查未发现正确性变化；最终源码hash冻结。不能保证所有输入都更快或同预算UNKNOWN不变，全Clause未验。[独审汇总](../agents/branch_ablation_20261031/z3-upstream-fix/independent-review/summary.md)。

**Z3枚举策略恢复（2026-11-01，完成）**：按用户要求去掉4096模型成本护栏，恢复受限FP＋枚举dt2bv→qffp；保留增强域UNSAT测试。构建与五组回归通过；恢复后大例default约0.49/0.90秒、qffp约0.045秒，之前几毫秒差异仅适用护栏版。性能P2按用户选择保留开销，生产未改。[记录](../agents/branch_ablation_20261031/z3-upstream-fix/restored-no-cost-limit/report.md)。

**Z3两个最小替代PR（2026-11-01，已发布／有界验证）**：A953e433在default复用dt2bv，Bae64857受限FP/枚举直接qffp；分别独审，A初版lambda类型回退已用现有quantifier probe保护并复审。A90query/18API通过，B独立27query与三API模式通过，作者88/90在60秒内符合预期、另两flags显式7200秒query探针待结果。官方[PR11505](https://github.com/Z3Prover/z3/pull/11505)、[PR11506](https://github.com/Z3Prover/z3/pull/11506)及issue评论已发布；非堆叠方案，未改生产/未验完整Clause。[状态与代码结论](../agents/branch_ablation_20261031/z3-alternative-prs/status.md)。

**Z3 B长query续测完成（2026-11-01）**：两个60秒UNKNOWN的flags探针在7200秒显式预算下均SAT，395.04/436.12秒；结合88项短预算结果，90项均取得预期答案。计时含初期CPU共享/绑核调整，不作严格A/B性能比，完整Clause未验。PR11506及issue11500原评论同步更新。[证据](../agents/branch_ablation_20261031/z3-alternative-prs/B/combined-summary.json)。

**Z3 A/B交叉五重复（2026-11-01，开始）**：发布版A953e433与Bae64857，同八个query workload，各按AB/BA/AB/BA/AB五对；每workload同CPU、不同workload并行，显式SMT7200秒。含两条真实慢flags，记录全部耗时/结果/CPU/RSS与哈希，不改生产或PR。[实验计划](../agents/branch_ablation_20261031/z3-alternative-prs/comparison-five/plan.md)。

## 五重复交叉实验完成（2026-11-01）

最终A953e433与Bae64857，8个相同workload，各版本5次，AB/BA/AB/BA/AB，固定每组CPU，80/80均SAT且退出0，输入和二进制哈希核对一致。无预热，SMT7200秒/外限7210秒；机器共享，独立query而非完整Clause。

墙钟中位秒A/B：NaN0.1456/0.2356、flags6.4469/15.4842、最小例0.3525/0.2135、枚举6×256为0.1636/0.1198、512×256为0.5946/0.0676、1024×256为1.2632/0.0552、flags-7为6.3014/41.4227、flags-11为1.8329/119.0785。四个真实query均A更快；最小及三枚举规模query均B更快。不能外推全workload；短例进程启动/共享负载影响明显，B慢例波动较大（flags-7为41.29–234.50秒、flags-11为85.70–241.24秒）。原计时pilot因wait(timeout)轮询尾延迟废弃，正式80次全部从头重跑，未复用pilot数据。

[全部五次数据与原始证据](../agents/branch_ablation_20261031/z3-alternative-prs/comparison-five/report.md)。

**六成员枚举变量规模复测（2026-11-01，进行中）**：6成员固定，变量64/256/512/1024，最终A/B各5次交叉，共40次；保持旧合成约束，256输入字节核对一致。[计划](../agents/branch_ablation_20261031/z3-alternative-prs/enum-six-five/plan.md)。

**六成员枚举变量规模复测完成（2026-11-01）**：A953e433/Bae64857，64/256/512/1024变量，AB/BA/AB/BA/AB各5次，共40/40均SAT、退出0。墙钟中位毫秒A/B：39.20/29.71、63.34/47.29、70.09/45.64、91.69/52.29，A额外9.49/16.05/24.45/39.40ms。256输入与旧测试字节一致；每变量仅约束不等于C0，另有独立fp.isNaN(x)，不含真实浮点运算耦合；短时进程墙钟含启动/解析，机器共享，不能从跨规格非单调耗时推导算法下降。未改生产/PR。[五次原始数据与来源](../agents/branch_ablation_20261031/z3-alternative-prs/enum-six-five/report.md)。

**Z3 fork主线选择A与数据共享（2026-11-01，完成）**：msuadOf/z3默认main已指向953e433；独立证据分支2dec1be8公开120次数据/12输入/哈希与便携复现脚本（40次smoke通过）。issue11500评论6553829092包含逐次结果、命令及内容，远端回读一致；未替换生产Z3。[交付记录](../agents/branch_ablation_20261031/z3-alternative-prs/status.md)。

**Z3 fork预编译包Actions（2026-11-01，实施中）**：新增fork main原生五平台自动构建/测试/发布流程，显式GITHUB_TOKEN权限，本机打包验证后推送触发；未替换生产Z3。[计划](../agents/branch_ablation_20261031/z3-alternative-prs/fork-actions/plan.md)。

**Z3 fork二进制Actions（2026-11-01，已启用／首次云端构建待完成）**：main32f4df28，五平台native构建/fpa/解压smoke及GitHub Release/SHA256，无外部secret；本机Linux打包与actionlint通过。首轮[Actions41279354596](https://github.com/msuadOf/z3/actions/runs/41279354596)由push触发，尚未宣称发布成功，未替换生产Z3。[状态与验证]( ../agents/branch_ablation_20261031/z3-alternative-prs/fork-actions/status.md )。

**Z3 fork Actions首轮修复（2026-11-01，修订后云端构建中）**：首轮Make目标z3不存在失败，5292580e5改用shell；全新Make目标核对及当前提交本地重编译/fpa/迁移打包通过。最新[运行41279556474](https://github.com/msuadOf/z3/actions/runs/41279556474)进行中，release仍待矩阵成功。[原失败与修订证据](../agents/branch_ablation_20261031/z3-alternative-prs/fork-actions/status.md)。

**Isla使用fork Z3 A（2026-11-01，隔离加载与限定验证通过）**：实际Release5292580e5校验和通过；float isarch副本显式换新libz3，ldd -r/版本验证通过，default种子能力校验未阻塞，FLEQ_S 4.08秒/10条/finished/无错误超时。MRET新旧均partial/unfinished=1，未作完整验收。使用A须新库＋--tastic default；尚未正式重链接/修改生产或分支。[证据]( ../agents/branch_ablation_20261031/z3-alternative-prs/isla-integration/status.md )。

**Isla默认default与Make具体策略（2026-11-01，实施中）**：CLI不传参数改default，Make按已有Clause分组显式qffp/qfaufbv，不增报错规则，保留覆盖；float源码与memory Make分别处理。[计划](../agents/isla_tactic_defaults_20261101/plan.md)。

**Isla CLI默认default、Make具体策略（2026-11-01，已修改／限定验证）**：float缺省Default并支持qffp；memory已有default不重复改；两条源码与runner快照Make的ALL显式qfaufbv、非访存浮点显式qffp，无新增报错、保留覆盖。TDD2/2、4×347目标dry-run及新Z3下CLI不传参数/Make qffp两次FLEQ_S均10条finished。未提交/推送/更新gitlink，未全Clause回归。[修改与证据](../agents/isla_tactic_defaults_20261101/status.md)。

**采用维护者Z3策略（2026-11-02，准备）**：按PR11506扩展原probe，移除fork main A前处理，保留发布CI；先fpa/API/Isla隔离验证，通过后推进main。[计划](../agents/z3_maintainer_route_20261102/plan.md)。

**采用维护者Z3方案（2026-11-02，已切换fork main／新版CI待完成）**：maind5aa015a2正常合入PR11506 head6ef1c356（上游已MERGED），移除全局A，改为扩展原probe并在qffp内dt2bv；四solver/test文件与PR精确一致，保留发布CI。fpa/18API/64模型断言及Isla default/qffp两次FLEQ_S各10条finished通过；不外推旧性能数据，旧Release仍为A。[版本/验证/CI](../agents/z3_maintainer_route_20261102/status.md)。

**编译官方最新Z3（2026-11-02，实施中）**：官方master最新head独立检出/Release构建并验证default修复，保留现有fork与系统库。[计划](../agents/z3_official_build_20261102/plan.md)。

**官方最新Z3编译（2026-11-02，完成／限定验证通过）**：干净官方master1fd1d3613（#11506），Release shell/libz3/test-z3构建安装至.tmp/z3-official-20261102/install；版本含官方SHA。fpa、两个default原查询（flags-11 8.33秒SAT）、18API/64原断言模型回读及Isla隔离default FLEQ_S10条finished通过；未全Clause或切换生产/系统库。[版本与使用目录](../agents/z3_official_build_20261102/status.md)。

**Isla正式切换官方Z3（2026-11-02，实施中）**：用户已授权根/float/memory切换官方1fd1d3613，版本化用户前缀、Make链接参数与正式重新编译，不改系统库/父gitlink；保留在途源码。[计划](../agents/isla_official_z3_switch_20261102/plan.md)。

**Isla正式切到官方Z3（2026-11-02，完成／限定验证）**：用户前缀~/.local/opt/z3-official-1fd1d3613，根/float/memory Make显式链接及RPATH、Release真实重编译，四处程序版本均官方1fd1d3613；根Debug亦切换。6次浮点/定向访存smoke全finished、无错误超时，SMT初始化2/2通过。保留旧系统库/在途源码/既有输出，未提交/推送/更新gitlink，未全Clause回归。[证据与边界](../agents/isla_official_z3_switch_20261102/status.md)。

**2026-11-02：官方新Z3受控消融复测，冻结旧程序避免混入review修复，14workload×三对、固定SMT种子、完整Clause两小时外限及显式SMT两小时，12独立物理核后台已启动、进行中**。[计划](../agents/branch_ablation_official_z3_20261102/protocol.md)。

**2026-11-02：浮点review三项并行完成，assembly/ExecuteAs代码待主集成验证，数据条件非重叠核账已交付**。[计划](../agents/float_review_completion_20261102/plan.md)。


**浮点 review 三项集成（2026-11-02，限定验证／覆盖仍部分）**：真实BF16两批与压缩例13条JSON、78项GCC/Clang检查符合预期，保留Illegal路径及三种表示；ExecuteAs红绿例x8由7修为1027。数据条件6次Clause/40条JSON均finished，补左源sNaN/qNaN及估算正常/次正规活动lane；右源独立及BF16/多lane等义务未闭合。统计尾段快照红绿回归通过，collector11/11＋三表示5/5＋API1/1＋统计1/1；根与runner-float源码同步、正式Release构建及真实make solve smoke通过。独立复审P2关闭。未提交/推送/gitlink更新。[状态与全部证据](../agents/float_review_completion_20261102/status.md)。


**显式语义分支恢复（2026-11-02，实施中）**：按用户预算和特殊值控制流原则，独立GPT-6.1 Sol源码审阅5文件无阻断；先恢复min/max/minm/maxm、f32 NaN出口、十分类、两个mask循环及三个合法性helper。模型按model分类提交7f3f50d/fd71c9a，四配置完整IR、普通严格检查及五IR24步回归通过，Isla f152290已提交；真实make与72项双工具链检查通过；组合七Clause四项完成、三项后台继续。flags算术与饱和仍待消融完结，不以窄域结果代替。[计划](../agents/explicit_branch_restore_20261102/plan.md)。


## 2026-11-02 最终后台验证结果

七项新组合Clause全部退出0、finished、无错误或超时。FVVTYPE 3121.758秒（329条），VFUNARY1 1880.107秒（520条），RFVVTYPE 290.252秒（184条），其余四项15.471–150.914秒；均低于完整Clause7200秒预算。以validation/report.md和summary.json的最终记录为准，旧“运行中”记录仅适用于提交时快照。

单变量消融84/84已结束。flags算术和转换饱和的显式分支B各三次均触及7200秒外限，故不符合本轮恢复条件，保留ITE；不能写成这些情况不需要控制流或覆盖已经完整。其他格式/循环、右源独立NaN、BF16融合及多lane异常等仍有覆盖验证义务。


**剩余特殊值/活动lane控制流与超时定位（2026-11-02，进行中）**：按用户要求由独立GPT-6.1 Sol判定必要控制流后恢复源操作数NaN分类、其他格式NaN出口及剩余真实FP/BF16运算gate；FMA融合数值本身只验证不改算术。另用实验专用SMT调用观测定位flags/sat显式分支超时，不改生产求解器。前置版本模型fd71c9a、Islaf152290、根floatbfe6e43；实施/严格生成/组合预算待验证。


**剩余特殊值控制流（2026-11-02，定向验收通过／最终同步中）**：模型四类提交350a072/f263774/eb17b05/a9fd947，四配置严格生成与普通检查通过，Sol源码/实际CFG/动态结果独审通过。56项定向完整Clause全部退出0、156条JSON、3518断言通过；固定域及vl≤2，不宣称全域完整覆盖。flags超时主要为SMT累计成本，旧sat另有不活动lane先计算造成额外分叉；新活动gate已纠正，overflow显式化须另行复测。详见[状态](../agents/special_control_restore_20261102/status.md)。


## 2026-11-02：独立源NaN与活动lane分支

模型四分类提交350a072/f263774/eb17b05/a9fd947，Isla对应IR提交99a83bb9；四配置严格生成、普通严格检查、五IR25步回归通过。独立GPT-6.1 Sol源码、实际CFG、56项定向结果复核通过。156条JSON、3518断言、正式make solve及GCC/Clang60项编码检查通过。固定域与vl≤2，不代表全域完整覆盖。

flags超时主要为昂贵浮点异常约束导致多次SMT求解变慢；旧饱和实验对不活动lane提前计算，导致额外分叉，新的活动gate已纠正。饱和overflow显式化仍需重新预算实验；flags changed及其余特殊异常分界未全部恢复。见[本轮状态](../agents/special_control_restore_20261102/status.md)和[超时定位](../agents/explicit_branch_timeout_diagnosis_20261102/report.md)。未推送。


**2026-11-02：完整超时归因确认进行中**：按用户要求，路径上界/7200秒任务账、可靠原始query的tactic对照、正确活动lane循环的overflow A/B并行；此前300秒观测不用于排除tactic。见[确认方案](../agents/explicit_branch_timeout_diagnosis_20261102/confirmation-plan.md)。


## 2026-11-02：flags/sat超时完整归因确认

六臂冻结B的qffp/default/smt完整Clause对照均7200s外限exit124，无完整JSON；CPU约99.5–99.7%，更换这两策略未使本轮负载完成。插桩主路径2h账：flags结构上界332、创建256、执行返回150/收集返回149、排队106+collector中1；sat上界1033、创建435、执行返回199/收集返回198、排队236+collector中1。主树/编码辅助树/JSON分别计数。

flags已完成SMT查询约94.5%时间在collector，最长单次1038.658s SAT；sat最长4.819s、16951次已返回查询累积，兼旧8lane溢出组合。两项已返回check无UNKNOWN，外限截断时各一条刚开始的pending。旧源只加活动gate、保留overflow-if，同seed17三次57–64秒完整finished，确认不活动lane过早转换是重要原因。flags干净同具体FDIV_S编码诊断：原路径约束36.50秒，隔离后0.04–0.05秒，同机器码；不能据此直接删除生产约束。

独立review发现并修正计数混合、旧探针残留同核竞争、check边界误归属；先前240/455秒性能值撤回为受干扰诊断。未微观定位原17分钟query为何跨轮变动，不宣称tactic普遍无影响或会话历史bug。生产源码/模型/策略未改。完整证据见[确认报告](../agents/explicit_branch_timeout_diagnosis_20261102/confirmation-report.md)。


**编码约束分离与饱和显式分支（2026-11-02，实施中）**：用户授权，独立Sol源码/IR/实际结果复核；保留完整路径最终验证及全部编码候选，修normal/压缩和异常可达性，四配置同步。见[状态](../agents/encoding_constraint_isolation_20261102/status.md)。

**内存协同接纳审阅（2026-11-02，审阅完成／需修改后接纳）**：Sail-RISC-V c70482a7与Isla bdd047bc的分层方向可接受；9主探针16JSON重现concrete/数组初态分离及GPR漏导出两个P1、异常返回值Sym；另有静态字段求值错误传播缺口。8finished/1partial（动态宽度错误另已复跑定位）；另4次隔离IR断言确认全寄存器访存正常早退漏清零vstart（P2）。IR及模型哈希/预算坐标一致。未修改生产源码或移动分支，未全量/硬件验收。[报告与证据](../agents/coordinated_memory_review_20261102/report.md)。


## 2026-11-02：编码候选约束分离与活动 lane 饱和分支（完成／限定验收）

Isla `cf1aa14`、模型 `6202e23`：辅助编码仅保留指令字段原断言，所有候选仍在完整执行约束下验证；恢复活动 lane 内 f16→i16 overflow 显式分支。独立 GPT-6.1 Sol 源码、四配置 IR、实际 JSON 和官方库 Rust 回归签收通过。

完整旧显式 flags B / 当前正式浮点算术 / 新 VFUNARY0 分别 2626.07 / 1127.51 / 22.33 秒 finished，均 T1/qffp/seed17、Clause 与单次 SMT 各 7200 秒，原配置未缩域；错误及 partial 均零。56 项定向、126 项双工具链、15 项官方库 Rust 回归及真实 Make 入口通过。两版各 1258 条实际见证的指令、编码、完整前后态、返回值多重集合相同；不推断全域覆盖或严格加速比。

五 IR/四配置严格生成和 25 步回归通过；flags changed 与其他未验窄转换仍维持现实现。既有枚举同 Context 重放单测失败单列，不计入通过数。旧 eager lane 饱和 B 初版诊断7200.20秒外限exit124、无完整JSON，不替代新模型验收。根 float 更新组件与证据，本轮未推送。详见[本轮状态](../agents/encoding_constraint_isolation_20261102/status.md)。

**内存协同正确性修复（2026-11-02，修复及Sol独审完成／限定接纳）**：F1–F5沿既有结构修复；独审发现的四个汇编/编码错误出口亦补齐，无未关闭P1/P2。最终Release、Isla lib163/163、12组19JSON/65断言、vstart后态8/8、make C_MUL finished、GCC/Clang38/38通过；四配置5IR及636源哈希/补丁一致，预算79/130/22有效。Sol独立跑两探针finished。既存store动态宽度/MRET Poison仍partial，未全量/硬件验收、未提交或移动gitlink。[实施与证据](../agents/coordinated_memory_fixes_20261102/report.md)、[独审](../agents/coordinated_memory_fixes_20261102/independent-review/report.md)。


**浮点遗留项闭环（2026-11-02，发布已完成／实施准备）**：模型6202e23、Isla cf1aa14与根float a6b6ecd均已非强推到对应正式远程分支，逐项SHA回读一致。接续flags changed、其他窄转换/异常控制流及枚举重放，实施/IR/结果均由GPT-6.1 Sol独审。[计划](../agents/float_review_closure_20261102/plan.md)。

**内存符号化架构调研（2026-11-02，初步结论完成／未实施架构改造）**：核对 Isla bdd047bc 加在途修复与 isla-testgen，比较 angr/KLEE/QEMU/AFL；建议保留 Sail MMU/PMA/PMP 语义与字节数组内容分层，先统一具体/符号状态和最终模型见证，再测量并优化 concrete 快照、alias、checkpoint 与路径规模。旧审阅问题和当前修复分开记录；无新增动态/性能/硬件 PASS。[报告](../agents/memory_symbolization_architecture_20261102/report.md)、[状态](../agents/memory_symbolization_architecture_20261102/status.md)。


2026-11-02 浮点遗留项：旧float a6b6ecd及子模块已安全推送。新模型8ad5e8e、Isla42000be已实现并通过独立Sol源码审查；新IR/完整Clause/动态验收待完成，不继承旧PASS。见 [专题](../agents/float_review_closure_20261102/status.md)。


2026-11-03 用户补充Isla共同参照0008fae最小性原则；两Sol已签18纯数据分支与mask包装收敛候选源码，独立named模型树实施，冻结214版77预算继续，未宣称整体PASS。后续strict/IR/定向/预算分别记录。见[现状](../agents/float_review_closure_20261102/status.md)。

**Sv39 全符号页表实证（2026-11-03，预算实验完成／全量计数未完成）**：指定现成二进制与IR，Bare／具象Identity均1成功；全符号单线程60秒返回415条（76成功／291页故障／48访问故障），8564次已完成检查累计26.629秒；16线程返回3181条仍触限。两条原始数组/PTE见证独立核验通过；完整路径总数及过滤数未知。报告和日志在`.worktree/mmu-symbolic-experiment/`。[状态](../agents/mmu_symbolic_experiment/status.md)。


2026-11-03 浮点最小候选已提交e9d69d2（core +16/-74），双Sol源码签收；ordinary/四配置strict及IR来源、数值依赖、必要控制已由Sol独审。e9 flags300组已新跑并独立限定签收，转换与异常等新版本验收接续，完整预算另批准备。冻结214的77项继续，当前尚未整体闭环；权威动态状态见[议题状态](../agents/float_review_closure_20261102/status.md)。


2026-11-03 e9最小候选的源码、严格IR、永久回归及新定向数值/汇编/Make均获Sol分阶段限定签收；77项完整预算新批pool16已启动（初始2，资源门扩容），未宣称整体闭环。当前进展见[议题状态](../agents/float_review_closure_20261102/status.md)。


2026-11-03 最新浮点架构指导：新增显式分支受理论/实测证据门限制，数据流保持原生求解，控制流分类不能自动批准新增fork。GPT-6.1 Sol正重新审定flags changed、窄转换及异常条件；此前数值签收不自动成为架构批准。冻结实验保留，裁决见[议题状态](../agents/float_review_closure_20261102/status.md)。


2026-11-03 最新双门Sol裁决完成：纯flags原因、窄结果选择和十二整数包装新增分支建议REVERT；changed/finite-valid/ROD模式证据不足OPEN，不继承旧架构批准。候选仅在议题目录准备，冻结e9/214实验继续。见[正式逐项裁决](../agents/float_review_closure_20261102/baseline-0008fae/architecture-decision-20261103.md)。

- 2026-11-03 [局部路径合并可行性评估](../agents/localized_path_merge_review/status.md)：当前非完整COW；历史合并有约束与任务保留问题。已制定等覆盖实验，未新增性能PASS。

**局部路径合并方案补充评审（2026-11-03，只读源码核查完成）**：明确 IPDOM/异常返回、独立 solver 合并、事件 guard 与当前 MultiRuntime 的边界；建议先独立批量见证，再限制纯数据区域合并。无实现或新增性能 PASS；详见[状态](../agents/localized_path_merge_review/status.md)。


2026-11-03 用户要求收敛结束float：77处纯data选择回退已按core/V/FD提交为最终候选0f7b8fbc，Sol已签实际源码。OPEN保持并延期memory合流；新IR/限定回归/两完整入口→独审→最终提交正在实施，不再扩通用配置研究，不宣称77全域通过。见[当前状态](../agents/float_review_closure_20261102/status.md)。

- 2026-11-03 [函数线性化三策略评审](../agents/linearization_tri_strategy_review/status.md)：静态评审完成；配置可行但现有 pass 不满足安全契约，Union/ITE_PHI 与断言边界需修正。未实施、未复现崩溃、无性能 PASS。


2026-11-03 三策略实施方案独立复审：self_test 对 Exit/Suspended/Dead 的判定及状态覆盖仍阻断签收；需强化网关、扩展安全检查、统一 CLI 调度。见[复审](../agents/linearization_tri_strategy_review/implementation-review.md)。无新增动态 PASS。


2026-11-03 float最终收敛限定验收完成：模型0f7b8fbc/Isla591693d，77纯data选择回退、OPEN冻结延期memory。Sol已签新strict/IR/104错误变异/安装26步/300状态/819+282+183转换/315异常/双工具链与Make/两完整域入口，最终限定签收无阻断；不声称全77预算或全域覆盖。组件已安全推送回读一致，根float封存接续。见[交付报告](../agents/float_review_closure_20261102/final-report.md)。


2026-11-03 float最终交付发布完成：根float0665526d7e14a207eb9928e282e627584b5635fe固定模型0f7b8fbc/Isla591693d；三远程分支均已非强推并逐SHA回读一致，float与两子模块工作树clean。GPT-6.1 Sol已签实际源码/IR/限定回归及2173路径最终根提交（新生产改动只在子模块；根含审查证据），OPEN冻结延期memory，memory未改未合。最终后发布收据见agents/float_review_closure_20261102/publication/post-publication.json，本轮不为自引用另加root commit。


2026-11-03 float→memory合流启动：固定float0665526d及子模块，目标memory31ef3b9；发现memory Isla两项未提交配置，原样保留。当前仅隔离冲突预检/独立Sol审查，不引入额外功能。见[合流计划](../agents/float_memory_merge_20261103/plan.md)。


2026-11-03 float→memory预检/Sol独审完成：父9/Isla15（dirty叠加16）/模型19配置冲突，另两处自动合并nat/OkErr接口不兼容。六仓HEAD及dirty原样保留，尚未实施合流或新IR/回归。见[预检报告](../agents/float_memory_merge_20261103/preflight-report.md)。


2026-11-04 float→memory正式六步实施中：独立候选merge-float-memory-20261104，按用户SchemaUnion/单最终Model原子failclosed裁决合核心；模型nat/region并集、全量strictIR及联合回归/三Sol分审同步推进，原dirty保护。尚未更新目标或宣称验收通过。见[状态](../agents/float_memory_merge_20261103/status.md)。


2026-11-04 float→memory限定合流发布完成：根memory `29aa4765`、Isla `4d085b14`、模型 `bf861b3e`，三正式远程逐SHA回读及原目标三仓clean均获Sol独立终核。Rust610/665、永久26/104负控、315/300、union9、nat8/helper4、ExecuteAs、定向Make和双工具链通过；原F1/原域访存partial/全域无退化未证与OPEN继续单列，未扩功能。完整索引见 `agents/float_memory_merge_20261103/status.md`。

2026-11-04 基于memory29aa4765启动ALL全量JSON生成：准备核验/资产冻结中，默认三个可用RV64配置共1041任务，RV32入口不支持明确登记；不修改生产实现。见[状态](../agents/full_generation_20261104/status.md)。


2026-11-04 全量JSON批次已正式启动：memory29aa4765/Isla4d085/modelbf861，实际已审bin3e44，ALL347×三个RV64配置=1041任务，12×T1，Clause/路径/SMT各7200秒。79qffp/268qfaufbv按配置，默认128别名/RV32 solve不支持实证登记；资产冻结、FIFO压缩日志，输出`.worktree/runner-memory/output/full-generation-20261104/`。进度见`agents/full_generation_20261104/status.md`。


2026-11-04 用户要求全量生成仅v128并提并发：旧controller3047417和12个在途任务已定向优雅退出，原122项v128成果哈希不变；新controller367606仅重跑剩余225项，40并发×T2，无taskset/128CPU，预算均7200s。新入口`.worktree/runner-memory/output/full-generation-v128-fast-20261104/`，每15秒更新progress。见`agents/full_generation_20261104/status.md`；启动不代表任务成功。


2026-11-04 全量生成按最新用户指定改为仅v128、10worker×THREADS32、无taskset。旧367606及40个在途任务已定向优雅退出；旧155项产物保留，66项成功继承，89项非成功+192未完成共281新任务。新PID2047613，实测10个isarch均T32/128CPU，入口`.worktree/runner-memory/output/full-generation-v128-10x32-20261104/`，进度每15秒刷新。已显式指派 gpt-6.1-terra 监控子代理对该批次持续巡检并输出快照至 `monitor-terra/`。见`agents/full_generation_20261104/status.md`。


2026-11-04 服务器重启后v128续跑已按用户指示完全停止并清理：控制器PID101892、监控采集器PID3837962及底层isarch求解进程已全部终止，临时运行目录`.worktree/runner-memory/output/full-generation-v128-4x32-resume-20261104/`及相关分析文件已清理；机器恢复空闲。历史已归档成果（132项/14085条JSON样例）安全保留于archives。


**历史分支清理（2026-11-09，审计与脚本预检完成／本环境删除阻塞）**：逐一审计三仓25个本地分支，计划清理12个已由保留主线或组件gitlink覆盖的分支；5个未合并分支保留。隔离脚本验证2/2通过，真实预检通过，实际apply因.git只读在修改前停止（删除0）；保留所有worktree与备份。[状态](../agents/historical_branch_cleanup_20261109/status.md)。


**历史分支清理后续与std-gaps核对（2026-11-09）**：Claude已在沙箱外清理12分支，三仓真实引用已回读。std-gaps六项增量中两分页补丁已入isarch，四项向量/配置改动未入；独立副本合并树无冲突且保留x0，无新功能PASS。[状态](../agents/historical_branch_cleanup_20261109/status.md)、[具体分析](../agents/historical_branch_cleanup_20261109/std-gaps-analysis.md)。


**std-gaps合入isarch（2026-11-09，实施与验证中）**：用户已授权完整合并；独立副本进行类型检查、IR重生及回归。[状态](../agents/isarch_std_gaps_merge_20261109/status.md)。


**std-gaps合入isarch（2026-11-09，候选完成／全部要求的限定实测通过）**：模型cbb4766f、Isla79d0e335、runner fb9916b9。普通/SYMBOLIC严格类型、新v128 IR、path merge6、executor396/5忽略、Python153/210子测试、向量22、原生fuzz20/20认证及20次变异均exit0。收尾脚本通过真实预检与隔离执行验证，原.git只读，原引用导入和源分支删除待Claude沙箱外执行。[状态](../agents/isarch_std_gaps_merge_20261109/status.md)。


**origin历史分支清理（2026-11-09，审计与脚本准备中）**：用户授权清理10个已删除本地分支对应origin分支；真实dry-run因网络不可达失败，未修改远端。[状态](../agents/origin_branch_cleanup_20261109/status.md)。


**origin历史分支清理（2026-11-09，审计/参数校验/隔离验证完成，真实网络操作阻塞）**：10条目标，9条主线或组件覆盖、p0-replay明确退役（24独有提交不记整枝合并）。3项隔离验证通过；三仓真实dry-run因网络不可达退出128，未删远程或prune。外部--apply脚本已交付。[状态](../agents/origin_branch_cleanup_20261109/status.md)。


**全部分支推送与暂存区清理（2026-11-09，审计/脚本准备中）**：12分支与必要archive提交先推送；11个Git存储47条worktree记录中3处暂存共223条；仅清索引且保留工作区与备份。[状态](../agents/push_index_cleanup_20261109/status.md)。


**全部分支推送与暂存清理（2026-11-09，审计/脚本/隔离验证完成）**：12分支+5archive发布计划参数通过，网络不可达未验证全部远端引用；外部已清三处223条暂存及唯一dead记录，本轮终核cached空、文件保留。207条历史精确覆盖，16条旧源码/缓存独立保存；不称全部已合并。两项隔离验证通过。[状态](../agents/push_index_cleanup_20261109/status.md)。


- 2026-11-09 [暂存区外审计与清理](../agents/unstaged_cleanup_20261109/status.md)：52个工作目录审计完成：恢复79份未暂存文件、删除4538个文件；独有实现和历史证据保留。未测试，未计算或比对哈希。


**std-gaps合入isarch（2026-11-09，候选实施与限定实测通过）**：模型cbb4766f；双模式严格类型、v128 IR重生、path merge6、executor396/5忽略、Python153/210子测试、向量22、原生fuzz20认证/20变异均exit0。原仓库导入待沙箱外执行。[状态](../agents/isarch_std_gaps_merge_20261109/status.md)。
