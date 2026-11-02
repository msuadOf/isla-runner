# 超时归因独立审核

2026-11-02 05:05 UTC 初审。完整六臂及主树两小时观测仍运行；本文不将它们记为通过。审核仅写本目录，没有修改生产或其他实验文件。

## 当前判断

主 Clause 的 332／1033 可接受为冻结配置下的控制流结构上界；不能作为全系统任务上界或耗时上界。原 2444／8551 辅助累计上界存在证明缺口，已反馈并由作者降为条件估算。最终结论应不使用这两个数排除路径规模。

当前证据支持“多次求解累计成本很高”和“旧饱和循环不活动 lane 提前转换造成额外分叉”。还不能将历史 flags 三次两小时外限一概归于某个具体查询、排除策略因素，或解释同 seed 一次自然完成的原因。最终结论须等完整观测。

## 主树与辅助树

独立脚本 [audit.py](audit.py) 复算原始日志，结果 [audit.json](audit.json)：flags A 为 172 条主任务（160 Retire、12 Illegal），sat A 为 13 条（12 Retire、1 Illegal）；均 `initial+fork=run_return=task_done`，全部返回 Finished，JSON summary 的 sampled/error/timeout/unfinished 均为零。

`executor.rs` 的 MultiRuntime 在 `run()` 返回后才调用 collector；冻结 `exec.rs` 无 ExecuteAs 续执行。因此 collector 的模型选择不改变该轮主树。主执行的 `__monomorphize` 在存在剩余解时提交剩余域任务，未限制时为枚举，不是任取单个模型；这与 A 的 sampled=0 一致。

flags A/B 唯一函数差异是 `zaccrue_fflags`，成功算术仅新增一次 changed 判断，Illegal 早于它返回，故 `12+160×2=332`。sat A/B 除 `zriscv_f16ToI16_pure` 外的文本变化经逐函数参数重命名归一化后消失；固定 SEW16/LMUL1/VLEN128 时两种有符号转换各两条基础主路径、每条最多八个 overflow 判断，故 `9+4×256=1033`。这些界依赖“其余控制流相同、正常求解、未增采样”前提，不表示全部组合可达或一定在预算内完成。

原辅助推论不严格：`exec.rs` 在符号 `encoding_paths` 之后调用 `model.get_val(fun_args)`，具体化寄存器，再执行 `try_get_assembly_name` 和 `try_get_assembly_encdec`。辅助日志把这些具体指令执行也计入；B 增加约束可能改变所选具体模型。即使 B 解集包含于 A，A 单次选中模型对应的辅助任务数也不必是全域最大。因此不能从 A 实测的每主路径 5／7／20／22 条辅助任务直接推出 B 的严格上界。作者已撤回该强断言，阻断关闭；辅助实测总数可保留。

## 策略证据

同 AST 比较保存原 assert AST 引用，并把原 assumptions 单独传给三个新 solver；冻结程序不导入 push/pop/reset/assert_and_track，引用生命周期与源码调用相符。每策略三次交错运行，显式 random_seed=17，结果逐项均 SAT，原增量检查也 SAT。该证据可用于这两条原查询的策略比较；没有独立模型断言验证，不能另行宣称全查询语义或模型正确性验收。

flags 九次版本未对新 solver 设置显式 timeout，但全部自然返回；报告已披露，不影响返回结果。sat 修订版设 7200000 ms。导出文本存在 unknown sort，不能作为有效 SMT-LIB 重放；同 context 原 AST 对照绕过打印缺陷，报告已正确区分。三种策略共享 context，且有机器共享负载，应把结果称为本轮同输入新 solver 观察，不能外推生产增量会话或所有查询。两条 `is-qffp-after-simplify=1` 只覆盖这两个 goal，不能证明完整 Clause 每次 default 都走同一路线。

逐次 query 探针从进入 hook 到 check 返回计墙钟，包含开始日志及指定 dump 成本；不是纯 CPU 或纯 Z3 内部时间。无 dump 的绝大多数项足以判断累计成本占主导，精确百分比应称“检查包装区间”。外限时 pending 项必须单列；最长已返回查询不能排除正在执行的查询更长。

六臂旧启动器顺序 wait 的 elapsed 不可直接作为完成墙钟。独立 `/proc` 观察可提供近似退出时间，CPU 采样是末次读到的累计值；没有精确采到退出瞬间时，不应写成精确 CPU。报告现已披露这些边界。

## 活动 lane 控制

旧基底 gate 版保留显式 overflow helper，源码仅改变 VFUNARY0 活动块；IR 审计显示 helper 逐字不变、其他变化为参数编号重排，gate 假出口绕过两个转换调用。该版本 seed17 三次完整结束，57.29–63.78 秒、28 条 JSON，足以证明“旧基底上只加活动 gate 已能完成，其他新源码改动不是完成的必要条件”。

历史旧 B seed17 仅一次外限，且 CPU40、无 probe；gate 版 CPU98、有 probe。故不能声称严格同硬件、同插桩加速倍数或全部随机种子都完成。旧 B seed29/43 不可冒充 seed17 重复。当前报告已明确这些限制。新基底 ITE/if 各五次完成只适用于已测固定域，不扩展为全部转换宽度或多 lane 验收。

## 等待最终证据

- 六臂实际退出码、summary、退出观察时间和末次 CPU 采样。
- 主树完整 7200 秒日志中的已创建、返回、collector 完成、排队、执行中数量及守恒关系。
- 每次检查总数、累计检查包装时间、最长已返回项及 pending 项的实测时长界限。
- collector 分段观测与独立上下文对照。阶段时间与 query 时间可能嵌套，汇总时不能重复相加。

## Collector 对照复审（05:30 UTC）

具体输入和补丁链已独核。[collector-audit.json](collector-audit.json) 从原始日志重新抽取三轮首条指令，均为 `F_BIN_RM_TYPE_S|S0=17|S1=30|S2=RM_DYN|S3=0|S4=FDIV_S`，规范串 SHA 与作者一致；两次配对均输出唯一 `0x191f7053` 且 equal=true。在独审目录从 `09ffa91` 重建两个源文件后应用 `probe.patch`，修改前后 SHA 与 `source-hashes.json` 全部相同，见 [重建核对](collector-reconstruction.json)。探针两臂传入同一 concrete_arg、shared_state、symbolic_regs、lets，只在 checkpoint 中移除原 15 条 Assert，保留 540 个声明/定义及下一个符号编号。两臂编码均另建 solver，不是拿热的原 solver 与冷 solver 比较。

此对照支持“这个具体输入的原执行断言是编码辅助求解变慢的重要因素”。不能推出可以安全删除断言，也不能由一条具体指令外推全部符号编码合同或完整 Clause 耗时。1038.658 秒的 query 685 已实际返回 SAT，须在最终归因明确保留单次长尾，不可沿用旧 135 秒最大值排除长查询。

发现两项需修订的证据问题，已通知主 agent 和实验作者：

1. 报告称探针在首条 case 后终止，但 `CONTROL_ONLY` 的 `return` 仅返回 collector。05:29 左右独审发现四个 isarch PID 663635／887159／917523／937631 仍运行且同绑 CPU112；对应 timeout 已成为孤儿，原日志持续增长。快照见 [进程证据](collector-process-snapshot.txt)。因此不能称已主动结束、独占单核或据 240／455 秒算严格性能倍率；需真正清理本实验进程并披露同核竞争。这不改变首条具体输入和已返回 check 的事实，但影响绝对计时。
2. control3 的 query 55 应归 fresh：开始 535212.987368797、返回 535213.004286708；fresh_end／original_begin 的 `/proc/uptime` 都打印 535213.00，存在 10ms 截断。原 checkpoint 首次 check 是 #56（535213.053876900）。因此 fresh 是 #49–55 共 **7 次、0.124096734 秒**，original 是 #56–62 共 **7 次、239.971792925 秒**。作者原 `analyze.py` 用固定 −0.02 秒边界把 #55 错移到 original，导致 6／8 次及 0.107／239.989 的错误表格。replicate 的 7 次、454.550590 秒已独核相符。应依据调用顺序和截断区间修表，而非把模糊边界自动当精确归属。

修订前，collector 报告的终止状态和首轮检查数不能签收；对“原断言显著增加该输入的编码成本”的限定定性结论没有新增反证。

## 六臂与干净 collector 重测复审（06:16 UTC）

六臂已独立核对，见 [clean-and-full-audit.json](clean-and-full-audit.json)：全部 exit124、seed17，当前冻结 binary／IR／config 哈希匹配，各自无 JSON；独立退出观测墙钟约 7200.17–7200.43 秒，末次采样 CPU 累计 7165.71–7175.32 秒。签收“本次 qffp/default/smt 都未使旧 B 在两小时内完成”。这些不是单次 SMT timeout 的证据，也不支持排除所有策略或程序优化。CPU 几乎持续得到运行时间，不支持把主要超时归咎于未获得 CPU；共享缓存、内存、频率干扰仍存在。

干净 collector 重测的进程控制问题已修正：`clean_run.py` 等待整个命令，程序首次 case 显式 exit87，`clean-result.json` 记录前后无该探针进程，`clean-time.txt` 为墙钟59.94、user57.95、sys1.86秒。从冻结09ffa91重新应用 `clean-probe.patch` 的两个源文件 SHA 均匹配。具体输入与编码保持前述值，原 checkpoint 编码阶段36.50秒／#70–76七次检查累计36.418114140秒；清除路径 Assert 的三次编码阶段0.05／0.05／0.04秒。这一输入上的成本因果结论可接受，旧240／455秒已明确降为受污染历史值，原进程控制阻断关闭。

干净轮的 fresh 三次 check 分界仍有同类表格错误，已通知作者修订且不要求重跑。精确 `PATH_ACCOUNT` 边界证明第一次辅助树结束于538158.603758，第二次开始于.604125；第二次结束于.651610，第三次开始于.651961。因此应分 #49–55／#56–62／#63–69，各7次，全SAT，累计分别 **0.007524375／0.008159833／0.007071823秒**。原 `clean-stage.json` 的6／7／8分组来自10ms阶段时标截断，不可沿用。阶段墙钟0.05／0.05／0.04秒与原36.50秒不受该归属修订影响。

主路径最终两小时账仍待结束，本次签收不替代最终截止时的主树守恒、pending检查及collector占时核对。

06:16 UTC 复核：作者已按精确辅助任务边界修正 `clean-stage.json` 与 collector 报告，三组均7次、累计与上述独核一致。collector 检查归属阻断关闭，限定因果结论签收。

## 主路径最终账独立复算（06:28 UTC）

两条插桩完整观测均以 exit124 到达进程外限。原始主事件与每次 check 直接复算保存为 [final-path-audit.json](final-path-audit.json)。

| 项目 | flags | sat |
| --- | ---: | ---: |
| 主任务创建数（初始+fork） | 256 | 435 |
| 模型执行返回 Finished | 150 | 199 |
| collector 完成 | 149 | 198 |
| 排队 | 106 | 236 |
| 正在 collector | 1 | 1 |
| check 进入／返回 | 6388／6387 | 16952／16951 |
| SAT／UNSAT／UNKNOWN 已返回 | 4801／1586／0 | 11287／5664／0 |
| 执行阶段 check 累计秒 | 396.786 | 2900.641 |
| collector check 累计秒 | 6777.716 | 4195.809 |
| 最长已返回 check 秒 | 1038.658 | 4.819 |

守恒分别是 `256=149+106+1`、`435=198+236+1`。flags 最长 query685 返回SAT，发生在第8条主路径模型执行结束后的collector；它确为长尾，但占整轮约14%，不是单次查询独自耗尽两小时。sat 已返回16951次检查全部短于4.82秒，最终pending16952在预算末尾才进入，故当前实测支持多次求解成本累积，不能描述为单次SMT卡住两小时。

flags 最终pending6388开始539950.167663，sat pending16952开始539950.145897，均为单调秒。它们没有返回，不能计为UNKNOWN或推断其最终SAT/UNSAT。启动器没有每臂精确终止时钟，且flags的首次退出poll晚约60秒；应报告时长界或明确近似，不能用末次monitor充当精确kill时间。sat在预算附近的poll已退出，pending时长上界约0.52秒；flags根据下一次poll只有约60.5秒的保守上界。均远短于两小时，足以排除最终pending本身长达两小时。

可接受最终表述：flags 在该固定域中主树最多332条，实测主要时间落在collector重复求解，兼有17分钟单次长尾；干净同具体指令对照确认继承执行断言会增加编码求解成本。旧sat最多1033条主树，提前转换不活动lane产生额外分叉，两小时观测是大量短查询累积；旧基底只加活动gate即可完成该域该seed。三种受测tactic本次均外限，不能把“换default/smt未解决”扩大为所有策略都正确或策略不可能优化。

## 最终签收

已回读 `confirmation-report.md`、`path-accounting/report.md` 及最终结果，任务守恒、阶段计时、返回状态与独立复算一致，限定归因口径通过，无剩余实质阻断。不能把未完成的整Clause标为PASS；已完成的是两小时观测和针对性诊断。17分钟长尾的微观求解器原因仍未证实，最终报告已明确保留。

归档前仅需清理两处文案：总汇旧“仍须等完整截止账”句删除；路径报告“八个不活动lane”改为“8个物理lane，其中7个因vl1而不活动”。pending的约一秒是按启动窗口与进程wall估算，不是逐进程精确终止计时；最终结论无需依赖这一精度。
