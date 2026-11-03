# 最终版验证入口与预算

本文件规定完整域预算与定向验证的不同证据口径；逐次运行结果见议题状态和全仓结果账。[义务矩阵](matrix.md)列语义分母，[最终完整域输入](inputs.model-21418d0-itrace.json)固定77条名单，取自 `isla/scripts/run.mk` `FD_NONMEM_RV64`；访存与两个 RV64 不支持的 FMV 条目不混入本批。[模型实际调用闭包](../inventory/affected-clauses.json)在最终模型 `21418d0` 与 Isla `42000be` 下给出 **64 条受影响 Clause**，另 **13 条兼容回归**；两栏完成数不得混算。64 条覆盖 `accrue_fflags` 的比较、min/max、估算、Zfa、BF16、转换、归约与向量调用者。若最终源码调用图显示新 Clause，必须追加；未受影响的13条单列为同版本兼容回归。

## 冻结和运行

最终源码提交后，先用 `freeze_source.py --tree <runner-float模型工作树> --commit <完整SHA> --output <新批次清单>` 固定模型，再对 runner-float Isla 工作树加 `--isla-source` 固定编译源码；脚本拒绝未提交的已跟踪改动。普通与 SYMBOLIC 严格检查、四配置完整生成、五份 IR、79 workaround 配置/region/锚点及生成 provenance 另有独立审计。把最终模型/Isla commit、两个源码清单、五 IR、实际 FD 完整域配置、新 Release 二进制及其 `smt-thread-interrupt` 构建清单/watchdog 实测、官方 `1fd1d3613` 库和 seed17 拦截库的精确路径与 SHA-256 填入 **新文件** `inputs.<批次>.json`，保留 `inputs.template.json` 不变。旧 IR `a877e245…`、旧二进制 `abce451a…` 只用于基线核对；旧程序未启用单次 SMT watchdog，不能用于本轮双7200秒验收。官方库 SHA `899cbc70…` 在本轮继续使用。

本批模型清单含全部1011个已跟踪文件。Isla源码清单以 `--isla-source` 冻结1021/1029个已跟踪文件，精确排除五份另行逐字节哈希的生成IR（`rv64d.ir`、`rv32d.ir`、`ir/rv64d_v128_e64.ir`、`ir/rv64d_v256_e64.ir`、`ir/rv64d_v512_e64.ir`）、`ir/provenance/manifest.json` 以及两个测试fixture IR（`isla-lib/tests/fixtures/ir_cache_assumption.ir`、`isla-lib/tests/fixtures/source_region_foreach_match.ir`）。这是当前 `freeze_source.py` 对全部 `.ir` 和该provenance清单的精确展开；源码版本仍固定为Isla提交 `42000be`，新IR由生成目录的独立哈希固定。旧生成脚本来源快照额外读到一个被忽略的 `model/sail_smt_cache`，补审清单将其明确排除，并核166个已跟踪模型输入及实际Sail二进制/标准库/插件。编译期Z3为Linuxbrew 4.16.0程序（SHA `a7eac84c…`），运行时为官方1fd库（SHA `899cbc70…`），两者不混称。

每次先 `python3 validation/run_clause.py --inputs validation/inputs.<批次>.json --batch <批次> --job <Clause> --cpu <独占逻辑核> --dry-run`，核全部哈希、官方动态链接和完整域条件，再去掉 `--dry-run`。程序写入独立 `runs/<批次>/<Clause>/`，已存在目录会失败，不覆盖旧输出或 target。运行参数固定 `T1/qffp/seed17`，整 Clause 外限 7200 秒、单次 SMT 7200 秒，完整 itrace、日志、time、命令和输出哈希保留。完整域配置以正式 `riscv64_difftest_fd.toml` 为母本：静态 `sys_enable_fdext=true`、`sys_enable_zfinx=false`，并规定平台常量和寄存器初始化默认值。其中 `mstatus=0x6600` 是初始化默认值；solve-state 的 `Target::setup_pre_state` 随后为目标寄存器清单重新建立符号值，mstatus也被覆盖，不能据该默认值认定求解初态固定为FS/VS=Dirty。配置**没有** `[initial_state]`，不额外固定运行时 `vl/vstart/vtype/mask/寄存器选择`。完整域 IR 不得带定向 `zvalidation_original_execute` wrapper；脚本自动拒绝定向初态配置和该wrapper。

### 2026-11-03：mstatus初态范围说明纠正

此前本节写“`mstatus=0x6600` 固定 FS/VS=Dirty”，并把它称为“完整域运行的明确限制”；该推断混淆了初始化默认值与求解前重新符号化，现予以纠正。依据为Isla `42000be` 的 `src/isarch/target.rs:124–156`：`symbolic` 创建新值，`regs.assign` 覆盖执行寄存器，`pre_state.insert` 保存同一符号；RV64目标清单在该文件第631行包含mstatus。

代表见证还有独立策略：`src/isarch/exec.rs:861–904` 对名单内浮点Clause，在完整编码可行域中尝试FS=Dirty且VS=Dirty，只有SAT才添加该偏好约束；路径要求关闭等情况使偏好UNSAT时保留原域，UNKNOWN也不添加偏好。因此不能把正式批次说成“初态FS/VS一开始固定Dirty”，也不能反向推断一次finished已经见证全部FS/VS状态。F1仍须按[矩阵](matrix.md)核对实际初态FS/SD、旧/新flags及changed两臂；Clean/Initial和旧位重叠可用定向helper/指令证据补足，理由是见证覆盖须逐项核实，以及整指令FPR写回可独立置Dirty，而非默认配置已排除了这些输入。

本次只纠正说明，不更改冻结inputs、manifest、脚本、原始结果或预算；既有运行结论仍按其实际前后态和覆盖证据解释，不据本文补记新PASS。

定向批次复用 `agents/special_control_restore_20261102/validation/run.py` 的 56 个 `jobs()/wrapper()/inspect()` 语义合同，`agents/float_support_review/oracle/` 的 native SoftFloat 及旧三表示检查 `agents/float_review_completion_20261102/assembly/check_json.py`。在新批次中冻结这些脚本、oracle 可执行文件与输入哈希，再将 `GEN/BIN/ORACLE/BASE/输出根` 指向新批次独立资产；旧脚本使用模块常量和原输出路径，不能原地直接启动。旧 56 项的固定操作/寄存器、`vl≤2`、mask 与部分 SEW 只是定向证，必须在定向账本注明；按新矩阵补 f16/f32/f64 的原因、ROD、flags old-bit、BF16/多 lane、H/S/D 与 SEW 分区。每例核原始源位串、实际读源角色、完整前后态、目的位和五 flags，native oracle 与 Isla 结果配对；三表示对每条完成 JSON 的助记符、位串/小端字节及 `.insn` 执行 GCC/Clang 核对。真实 Make smoke 在独立工作目录、冻结二进制和配置上执行，不调用共享 `target/`。所有这些属于“定向固定值”栏，**不增加** 77 条完整域 Clause 的完成计数。

## 完整域分区与物理核

五份逻辑 IR 是 rv64 default、rv32 default、rv64 VLEN128/256/512 的生成/CFG 覆盖；正式输入中rv64 default与V128由同一`rv64d.json`生成产物按同字节别名记录，分别核安装目标；77 条完整域第一轮用 rv64 VLEN128，静态 VLEN=128、ELEN=64、XLEN=64。SEW8/16/32/64 是运行态合法分支，不能靠固定一个 `vtype` 代替；对各 Clause 应把合法 SEW 与实际子操作交叉成账本。若资源要求按合法 SEW 分区，四个互斥分区的约束并集必须等于原合法域，另列非法/保留编码路径，逐分区每条仍给 7200 秒和同源输入；分区总完成不能被一条子域 PASS 替代。VLEN256/512 的 IR 严格与 CFG 检查不等于这两种静态配置已完成动态预算；若验收扩大到 VLEN 变体，分别建立完整域批次。

实际调度先看 `lscpu -e=CPU,CORE,SOCKET,ONLINE`、`ps -eo pid,psr,pcpu,rss,comm` 和 cgroup 可用核。当前机器 64 个物理核/128 逻辑 CPU，同核 SMT 逻辑号相隔 64；每个 T1 Clause 只给一个空闲物理核，不与另一个任务占同核另一逻辑 CPU。内存与当前其他任务占用决定并行数，建议先 2 个互不相邻的空闲物理核测 RSS，再按最坏单任务峰值和保留量增到 4–8；CPU 编号运行前重新选择，不把当前瞬时空闲视为长期许可。64×7200 秒的受影响名单理论最坏核时为 128 小时，附加13条兼容回归后77项共154核时；4个独立物理核分别至少约32/38.5小时，8核分别约16/19.25小时，未计排队、重试与 I/O。先跑 F1 标量、N 类、E3/ROD 和 BF16/归约代表入口作早期风险观测，再全名单，不将阶段性完成称整组通过。

## 路径规模与早期观测

恢复的每个二叉条件在最坏情况下令路径数乘2；一个活动 lane 的 signed 窄饱和有“范围内/正/负”至多3出口。8 个独立 lane 的二叉组合上界 `2^8=256`，三出口上界 `3^8=6561`；VLEN128、SEW8时物理 lane 最多16，二叉上界 `2^16=65536`。这只是独立条件的结构上界，合法性、mask、操作种类和不可达输入会压低实际数，SEW/LMUL、`vl/vstart`、mask、寄存器组与 RM 又增加合法笛卡尔积。先从生成 IR 确认 active gate 支配 helper 调用；旧 eager lane 版本在 `vl=1` 仍为8 lane 分叉，不能把其超时直接迁到新模型。F1 的 changed 每调用多一个条件，但求解耗时还取决于浮点异常公式；旧 300 秒窗口出现 255 次已完成查询、累计约297秒，不能误称单次 SMT 卡两小时。

正式运行起始 5/15/30 分钟记录 `run.log` 最新主树 fork/Retire、itrace 增量、生成 JSON、SMT timeout dump、进程 CPU/RSS 和已运行秒数。新完整域尚无逐查询结构化计时接口；仅凭进程 CPU 约100%或 JSON 缺失不能判定单次 SMT 卡住。若到 7200 秒外限，分别保存主树已创建/已完成/排队路径、编码辅助 checkpoint 候选/完成/拒绝、collector 中路径、单次 SMT 已返回与 pending 的数量和时长；日志不提供的字段标“不可观测”，必要时用**另建且哈希独立**的诊断程序/短窗采样，不修改正式结果。SMT2 dump 只有真实超时且可独立解析、连同完整断言/assumption 回读才可作单次证据；过去两种不完整 dump 曾解析失败，不能重用其 SAT/耗时结论。超时状态为 OPEN，定向固定值或分区诊断均不能替代完整域预算。

## IR CFG 红绿门

`check_cfg.py --ir <IR>` 在旧 `a877e245…` 上退出1，[红测记录](red-baseline.json)有7个预期缺口。它从实际 IR 的 Jump 条件追溯到 overflow/changed 谓词，检查目标 Jump 两臂的可达节点、结果构造或 Dirty 写回受该 Jump 控制；signed 窄饱和还要求溢出臂中的正/负端点 Jump。它不以全函数 Jump 总数单独判 PASS。最终五份 IR 须逐份绿测，并由独立审查补 E1–E7、R1/R2 的原因优先级、finite gate 与调用者 active gate 控制关系；本脚本当前只覆盖 F1 与六窄 helper，不能把它的绿色当整个特殊行为闭合。永久文件位于 `isla/test/float_ir/`，由主 agent 确定写入边界后迁移并与既有 `check_special_semantic_branches.py` 合并测试入口。
