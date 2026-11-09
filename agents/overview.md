# Agents Overview

- 2026-11-09 三仓及各工作树暂存区外文件审计与清理完成。审查 52 个实际 Git 工作目录，按内容比对恢复 79 份未暂存工作文件，删除 4,538 个确认无用的旧副本、编译缓存与字节码；未运行测试、未计算哈希。保留独有实现及历史证据，详见 [审计报告](../.worktree/unstaged-cleanup-20261109/audit.md)、[专题状态](unstaged_cleanup_20261109/status.md)。

- 2026-11-09 Isla 仓库历史大体积 RISC-V IR 文件彻底移除完成。使用 `git-filter-repo` 清理 `isarch`、`feat/linearize-tri-strategy-grafted`、`feat/witness-randomization` 及 tag `allai`，仓库 packed 大小从 101MB 缩减至 29MB，已强制推送到 GitHub 远端；主仓 `isarch` 子模块 gitlink 已同步更新推送到远端；各工作树已暂存 IR 残留亦已清理完毕，详见 [专题状态](push_index_cleanup_20261109/status.md)。

- 2026-10-24 Isla通用支持分支的设计与操作流程、原工作区对fix＋float组合的精确区别见 [深入说明](general_support_review/design-comparison-20261024.md)。

- 2026-10-23 继续本地 CPU fuzzing 反馈讨论，补充 DRVFuzz 2026、压力／时序／数据来源／双执行反馈，以及候选创新的边界；未开发或实验。[微架构反馈量](semantic_mutation_fuzzing/microarchitecture-feedback.md)、[证据等级](semantic_mutation_fuzzing/microarchitecture-feedback-sources.json)。

- 2026-10-22 用户要求先建立覆盖反馈的系统认识，再讨论选型；当前仅文献研究，本地CPU功能验证定位不变。[覆盖反馈与符号执行架构综述](semantic_mutation_fuzzing/coverage-feedback-review.md)、[来源与证据范围](semantic_mutation_fuzzing/coverage-feedback-sources.json)。

- 2026-10-22 Isla 种子变异议题已从论文讨论推进至 [E0–E7 实验矩阵](semantic_mutation_fuzzing/experiments.md)；完成既有随机化的12次生成侧 pilot，尚无新变异器或DUT效果结论。[结果与限制](semantic_mutation_fuzzing/pilot-results.md)、[议题状态](semantic_mutation_fuzzing/status.md)。

- 2026-10-22 Sail-RISC-V新建内存独立分支（2提交）及通用先行／浮点后续分支（4＋10提交），均从4f2ac293开始；model职责分类、通用边界及32次严格检查见 [交付](sail_riscv_commit_review/topics-20261022.md)。

- 2026-10-21按用户要求删除Sail-RISC-V旧23提交链的两个本地分支；保留功能归组分支及detached旧工作树。[清理记录](sail_riscv_commit_review/status.md)。

- 根仓 `float`／`memory` 双分支已建立，各自固定组件gitlink并提供独立worktree；入口与验证边界见 [双分支说明](../specs/topic-versions.md)。Sail-RISC-V独立subagent代码审阅已完成，见 [报告与建议](sail_riscv_commit_review/independent-review-20261021.md)。

- 2026-10-21 Sail-RISC-V／Isla分支与工作树已重新核对，内存、仅浮点、通用及随机化边界、已有试合并和接纳选择见 [分支核查状态](branch_merge_review/status.md)。

- Sail-RISC-V 已按model功能重组为11个模型提交＋1个忽略规则提交（2026-10-19，`3ea3cbaf`）；原23提交链保留。见 [交付与验证](sail_riscv_commit_review/commits-by-category-20261019.md)。

- FLI/BF16汇编修复已发布 [上游PR #2030](https://github.com/riscv/sail-riscv/pull/2030)；本地验证及线上状态见 [记录](sail_riscv_commit_review/pr-1a135b24-20261018.md)。

- `1a135b24` 对应的FLI/BF16汇编错误在官方最新0.16中仍存在；2026-10-18独立上游核查与复现见 [报告](sail_riscv_commit_review/upstream-1a135b24-20261018.md)。

- Sail-RISC-V 改动已在独立worktree拆为23个提交（2026-10-16，原工作区保留），见 [状态](sail_riscv_commit_review/status.md)及 [实际提交/文件/验证索引](sail_riscv_commit_review/commits-20261016.md)；[原14批逐文件提案](sail_riscv_commit_review/file-details.md)留作历史。

- 仅浮点分支 `feat/float-only-20261008` 本轮独立复审与修复见 [状态](float_only_review/status.md)。

- 通用支持分支 `refactor/general-support-20261007` 独立审查见 [状态](general_support_review/status.md)。

本文件是根目录 `AGENTS.md` 引用的代码分析入口索引。

- 仓库和代码逻辑的持续发现记录在 [findings.md](findings.md)。
- 当前 `zSTORE` / `zLOAD` 路径爆炸议题记录在 [zSTORE_path_explosion/](zSTORE_path_explosion/)。
- Ara 历史 PoC 分析见 [ara_poc_batch/status.md](ara_poc_batch/status.md)，证据入口见 [根档案索引](../archives/README.md)。
- XiangShan 草稿复现见 [vext_issue_draft_reproduction/status.md](vext_issue_draft_reproduction/status.md)；V 扩展收敛见 [v_symbolic_dedup/status.md](v_symbolic_dedup/status.md)。
- 新议题应在 `agents/<议题名>/` 下维护 `plan.md` 和 `status.md`，并把可复用的代码理解同步回 [findings.md](findings.md)。
- Isla 浮点支持调查与实施计划见 [float_support_review/status.md](float_support_review/status.md)，现行计划见 [float_support_review/plan.md](float_support_review/plan.md)。
- Isla `origin/feat/memory-support` 内存支持调查见 [memory_support_review/status.md](memory_support_review/status.md)。
- workaround 描述归属与运行配置生成见 [workaround_ownership/status.md](workaround_ownership/status.md)。
- 内存 clause 分支覆盖对照（W19+G1-G8）见 [memsolve_branch_coverage/status.md](memsolve_branch_coverage/status.md)。
- GitHub 内存 issue 与本仓 PoC／求解／DiffTest 分阶段对照见 [memory_github_xref/status.md](memory_github_xref/status.md)。

- 初态 TOML 配置实施见 [状态](initial_state_config/status.md)。

- 2026-10-29 初态部分符号化8948cc4已合入refactor/general-support，原dirty内容保留；[合入记录](initial_state_config/status.md)。

- 2026-10-29 general ef882f0＋float be1296b相对7b7337b复审：主体设计可接受，新增runner组合编译问题，旧ret_val具化缺口及偏好配置建议；[报告与测试](general_float_review_20261029/status.md)。

- 2026-10-29 general先、float再合入feat/float-support，最终31506ee；runner兼容与ret_val具化修复、独立GPT-6.1 Sol审阅通过，原dirty已stash保全。[交付](general_float_merge_20261029/status.md)。

- 2026-10-29 两源分支各自统一具体化术语，general cc7700b/float-only99a28b0，再顺序合回feat/float-support@75e7440。[交付与验证](terminology_concretization_20261029/status.md)。

- 2026-10-29按澄清重做原general/float两个merge，目标现b0138b7，代码tree不变；[记录](terminology_concretization_20261029/status.md)。

- 2026-10-30根float/memory分支已分别更新提交bb9d271/1731207，版本与初始化核对通过；[记录](branch_merge_review/root-version-update-20261030.md)。

- float/memory及子模块的JSON语义独立复审见[状态](json_semantic_review_20261030/status.md)。

- JSON语义复审修复与GCC/Clang双工具链验收见[状态](json_semantic_fixes_20261030/status.md)。

- 2026-10-30 JSON语义复审修复已提交到根float90bb726／memory31ef3b9；双工具链与IR同步限定验收见[报告](json_semantic_fixes_20261030/report.md)。

- 当前float/memory双subagent独立审阅见[状态](independent_topic_review_20261030/status.md)。

- 2026-10-30 两subagent独立复审完成：float／memory分别给出当前JSON语义与覆盖修改意见，未改实现。[汇总](independent_topic_review_20261030/summary.md)。

- NaN-boxing显式分支恢复见[状态](nan_unbox_branch_restore_20261031/status.md)。

- 2026-10-31按用户要求恢复NaN-boxing显式if，根float1c7a354；[实施与限定验证](nan_unbox_branch_restore_20261031/status.md)。

- 2026-10-31浮点分支合并同类改动盘点见[报告](branch_folding_inventory_20261031/report.md)。

- 浮点分支合并逐项并行消融见[状态](branch_ablation_20261031/status.md)。

- 2026-10-31五组并行消融完成：完整Clause时间与条件见证分别统计，超时不算加速比；[汇总](branch_ablation_20261031/report.md)。

- 浮点慢路径的SMT查询、策略重放和等价sqrt条件定位见[性能报告](branch_ablation_20261031/solver-diagnosis/report.md)。

- Z34.16统一策略源码调查：枚举阻断default浮点probe，预处理后通用分发候选验证见[报告](branch_ablation_20261031/z3-strategy-source/report.md)。

- Z3上游枚举/浮点策略改进的独立复现及本地议题草稿见[评估](branch_ablation_20261031/z3-upstream-assessment/report.md)。

- Z3 default浮点＋枚举源码修复及TDD、41query/双侧模型回读结果见[交付](branch_ablation_20261031/z3-upstream-fix/report.md)。

- Z3补丁两位独立审查、P2修复与修订复验见[汇总](branch_ablation_20261031/z3-upstream-fix/independent-review/summary.md)。

- 2026-11-01 Z3两个最小替代方案已分别独审并发布PR11505/11506，A修复lambda边界后重验，B两条长query仍待重测；[状态](branch_ablation_20261031/z3-alternative-prs/status.md)、[代码等价性](branch_ablation_20261031/z3-alternative-prs/equivalence.md)。

**Z3 fork主线选择A与数据共享（2026-11-01，完成）**：msuadOf/z3默认main已指向953e433；独立证据分支2dec1be8公开120次数据/12输入/哈希与便携复现脚本（40次smoke通过）。issue11500评论6553829092包含逐次结果、命令及内容，远端回读一致；未替换生产Z3。[交付记录](branch_ablation_20261031/z3-alternative-prs/status.md)。

**Isla CLI默认default、Make具体策略（2026-11-01，已修改／限定验证）**：float缺省Default并支持qffp；memory已有default不重复改；两条源码与runner快照Make的ALL显式qfaufbv、非访存浮点显式qffp，无新增报错、保留覆盖。TDD2/2、4×347目标dry-run及新Z3下CLI不传参数/Make qffp两次FLEQ_S均10条finished。未提交/推送/更新gitlink，未全Clause回归。[修改与证据](isla_tactic_defaults_20261101/status.md)。

**采用维护者Z3方案（2026-11-02，已切换fork main／新版CI待完成）**：maind5aa015a2正常合入PR11506 head6ef1c356（上游已MERGED），移除全局A，改为扩展原probe并在qffp内dt2bv；四solver/test文件与PR精确一致，保留发布CI。fpa/18API/64模型断言及Isla default/qffp两次FLEQ_S各10条finished通过；不外推旧性能数据，旧Release仍为A。[版本/验证/CI](z3_maintainer_route_20261102/status.md)。

**官方最新Z3编译（2026-11-02，完成／限定验证通过）**：干净官方master1fd1d3613（#11506），Release shell/libz3/test-z3构建安装至.tmp/z3-official-20261102/install；版本含官方SHA。fpa、两个default原查询（flags-11 8.33秒SAT）、18API/64原断言模型回读及Isla隔离default FLEQ_S10条finished通过；未全Clause或切换生产/系统库。[版本与使用目录](z3_official_build_20261102/status.md)。

**Isla正式切到官方Z3（2026-11-02，完成／限定验证）**：用户前缀~/.local/opt/z3-official-1fd1d3613，根/float/memory Make显式链接及RPATH、Release真实重编译，四处程序版本均官方1fd1d3613；根Debug亦切换。6次浮点/定向访存smoke全finished、无错误超时，SMT初始化2/2通过。保留旧系统库/在途源码/既有输出，未提交/推送/更新gitlink，未全Clause回归。[证据与边界](isla_official_z3_switch_20261102/status.md)。

- 浮点review三项集成与条件核账见[状态](float_review_completion_20261102/status.md)；新官方Z3的14工作负载受控消融已后台启动，见[实时报告](branch_ablation_official_z3_20261102/live-report.md)。

- 预算内显式语义分支恢复、Sail源码/Isla IR协同及GPT-6.1 Sol独审见[状态](explicit_branch_restore_20261102/status.md)。

- 其余特殊值及活动lane控制流恢复见special_control_restore_20261102/；flags/sat显式分支超时定位见explicit_branch_timeout_diagnosis_20261102/，均为2026-11-02当前任务。

- [flags/sat完整超时归因确认](explicit_branch_timeout_diagnosis_20261102/confirmation-report.md)：7200秒路径账、六策略臂、活动gate及collector因果控制。


**编码约束分离与饱和显式分支（2026-11-02，实施中）**：用户授权，独立Sol源码/IR/实际结果复核；保留完整路径最终验证及全部编码候选，修normal/压缩和异常可达性，四配置同步。见[状态](encoding_constraint_isolation_20261102/status.md)。

- Sail-RISC-V与Isla内存协同接纳审阅见[状态](coordinated_memory_review_20261102/status.md)。

- 2026-11-02 编码辅助约束分离与活动lane饱和分支完成，Sol独审及三完整Clause预算验收通过；[版本/证据/边界](encoding_constraint_isolation_20261102/status.md)。

- 内存协同正确性F1–F5修复及实施后Sol独审已完成，限定范围可接纳、无未关闭P1/P2；见[状态](coordinated_memory_fixes_20261102/status.md)、[独审](coordinated_memory_fixes_20261102/independent-review/report.md)。

- 2026-11-02 已发布三个浮点组件提交，遗留控制流与枚举重放闭环见[计划](float_review_closure_20261102/plan.md)。

- 2026-11-02 内存符号化架构调研完成：核对 SeqMemory/回调/fork 与在途 concrete 修复，对照 isla-testgen、angr/KLEE/QEMU/AFL；保留 Sail 语义权威，按快照、alias 和路径分叉分别优化；未新跑性能或动态测试。[报告](memory_symbolization_architecture_20261102/report.md)、[状态](memory_symbolization_architecture_20261102/status.md)。


2026-11-02 浮点遗留项：旧float a6b6ecd及子模块已安全推送。新模型8ad5e8e、Isla42000be已实现并通过独立Sol源码审查；新IR/完整Clause/动态验收待完成，不继承旧PASS。见 [专题](float_review_closure_20261102/status.md)。


2026-11-03 用户补充Isla共同参照0008fae最小性原则；两Sol已签18纯数据分支与mask包装收敛候选源码，独立named模型树实施，冻结214版77预算继续，未宣称整体PASS。后续strict/IR/定向/预算分别记录。见[现状](float_review_closure_20261102/status.md)。

- [Sv39 全符号页表实证](mmu_symbolic_experiment/status.md)：60秒预算对照完成；全符号返回至少415条，16线程至少3181条，完整计数未知；原始PTE见证核验通过。


2026-11-03 e9最小候选的源码、严格IR、永久回归及新定向数值/汇编/Make均获Sol分阶段限定签收；77项完整预算新批pool16已启动（初始2，资源门扩容），未宣称整体闭环。当前进展见[议题状态](float_review_closure_20261102/status.md)。

- 2026-11-03 [局部路径合并与直接fork评估](localized_path_merge_review/status.md)：静态核查完成，历史实现不具备等覆盖性能对照前提；新实验待实现。

- 2026-11-03 [函数线性化三策略评审](linearization_tri_strategy_review/status.md)：静态核查完成，发现断言、纯净性与 Union 合并边界；无新增动态 PASS。


- 2026-11-03 float收敛提交及发布闭环：根float0665526d、模型0f7b8fbc、Isla591693d，三远程回读一致；Sol限定验收通过，OPEN延期memory，见[交付与合流边界](float_review_closure_20261102/final-report.md)。


- 2026-11-03 float0665526d向memory合流的状态核对、隔离冲突预检和Sol独审见[合流议题](float_memory_merge_20261103/status.md)。


- 2026-11-04 float向memory正式合流实施/SchemaUnion与独审证据见[合流状态](float_memory_merge_20261103/status.md)。


2026-11-04 float→memory限定合流发布完成：根memory `29aa4765`、Isla `4d085b14`、模型 `bf861b3e`，三正式远程逐SHA回读及原目标三仓clean均获Sol独立终核。Rust610/665、永久26/104负控、315/300、union9、nat8/helper4、ExecuteAs、定向Make和双工具链通过；原F1/原域访存partial/全域无退化未证与OPEN继续单列，未扩功能。完整索引见 [合流状态](float_memory_merge_20261103/status.md)。

- 2026-11-04 合流后ALL全量JSON批次见[状态](full_generation_20261104/status.md)。


2026-11-04 全量生成已启动：memory29aa4765/Isla4d085/modelbf861，实际已审bin3e44，ALL347×三个RV64配置=1041任务，12×T1，Clause/路径/SMT各7200秒。79qffp/268qfaufbv按配置，默认128别名/RV32 solve不支持实证登记；资产冻结、FIFO压缩日志，输出`.worktree/runner-memory/output/full-generation-20261104/`。进度见`agents/full_generation_20261104/status.md`。


2026-11-04 用户要求全量生成仅v128并提并发：旧controller3047417和12个在途任务已定向优雅退出，原122项v128成果哈希不变；新controller367606仅重跑剩余225项，40并发×T2，无taskset/128CPU，预算均7200s。新入口`.worktree/runner-memory/output/full-generation-v128-fast-20261104/`，每15秒更新progress。见`agents/full_generation_20261104/status.md`；启动不代表任务成功。


2026-11-04 全量生成按最新用户指定改为仅v128、10worker×THREADS32、无taskset。旧367606及40个在途任务已定向优雅退出；旧155项产物保留，66项成功继承，89项非成功+192未完成共281新任务。新PID2047613，实测10个isarch均T32/128CPU，入口`.worktree/runner-memory/output/full-generation-v128-10x32-20261104/`，进度每15秒刷新。见`agents/full_generation_20261104/status.md`。


2026-11-04 服务器重启后v128续跑已启动：新宿主PID101892，严格4worker×T32，无taskset/128CPU，三层7200秒。132项旧成果/14085条JSON样例逐SHA保留（后来66项11881样例仍按partial/failed保留），10中断+205未执行共215项队列。新入口`.worktree/runner-memory/output/full-generation-v128-4x32-resume-20261104/`，显式gpt-6.1-terra每60秒专项监控。状态见`agents/full_generation_20261104/status.md`，启动不表示全量PASS。

- 2026-11-05 浮点向量/AMO/AES64理论路径与当前实际日志剖析见[状态](path_scale_20261105/status.md)。


- 2026-11-09 [历史分支清理](historical_branch_cleanup_20261109/status.md)：25个本地分支完成审计，12个列入清理；脚本及隔离验证完成，原Git只读，交付Claude沙箱外执行。


- 2026-11-09 std-gaps与isarch的[六提交核对及合并影响](historical_branch_cleanup_20261109/std-gaps-analysis.md)：已证明无Git文本冲突、x0保留；方案B按指定范围仅迁分页补丁，剩余向量变更须精确候选验收。


- 2026-11-09 用户授权[std-gaps正式合入isarch](isarch_std_gaps_merge_20261109/status.md)，独立候选实施与实测。


- 2026-11-09 [origin远程历史分支清理](origin_branch_cleanup_20261109/status.md)：10条指定分支，网络受限，准备提交租约保护的外部脚本。


- 2026-11-09 [三仓全分支推送与暂存区清理](push_index_cleanup_20261109/status.md)：审计223条暂存和12分支，先发布后仅清索引。


- 2026-11-09 [暂存区外审计与清理](unstaged_cleanup_20261109/status.md)：52个工作目录审计完成，恢复79份、删除4538个文件；COW/MMU等独有实现及证据保留，未跑测试和哈希核对。
