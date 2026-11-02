# 编码隔离后的完整约束重复成本：只读分析

状态：只读核对 Isla 源提交 `de00adb`、当前 IR 提交 `8e5a3f7` 对应的运行入口。旧 flags `F_BIN_RM_TYPE_S` 仍在运行；截至本次读取，`validation/runs/old_flags/run.log` 只有四条 primop 提示，`time.txt` 为空，没有完整 Clause 退出码、逐阶段计数或查询耗时。本报告只指出源码上的重复，不将当前十余分钟未结束归因到某个调用，也未启动实验或改运行进程。

## 每条主执行路径会做什么

|阶段|源码位置|完整原约束及查询|必要性|
|---|---|---|---|
|主路径入口|`isla/src/isarch/exec.rs:817–836`|在原执行 solver 上 `check_sat`，随后取 checkpoint|必要：主执行结束不保证最终约束可满足；也给后续“原执行域 SAT”证明提供前提。|
|辅助探索|`isla/src/isarch/encoding.rs:115–139`、`isla/isla-lib/src/executor.rs:2275–2306`|按任务从去掉旧 Assert 的 checkpoint 重放；符号 Jump 在 `executor.rs:1623–1624` 查两方向|这些分支查询用于穷举辅助候选，检查的是较宽的辅助域，未直接重放旧昂贵 Assert。每个 fork 任务仍重建辅助 solver。|
|终态验证|`isla/src/isarch/encoding.rs:52–68`|每个非 Dead、非采样终态接回旧 Assert，创建新 `Context`/`Solver`，完整重放后 `check_sat`|若候选新增分支 Assert 与原路径互斥，这次检查不可省；UNSAT 过滤，UNKNOWN/Error 传播。正常拒绝和异常也先验证，以免辅助域的不可达错误污染主路径。|
|输出收集|`isla/src/isarch/exec.rs:856–860,893,945`|每个通过验证的编码再次创建完整 solver；float77 每个候选额外 `check_sat_with(FS∧VS)`，最后 `check_sat` 取得最终模型|本负载 `F_BIN_RM_TYPE_S` 在 `official_float77.txt:41`，因此 FS/VS 偏好查询每个候选都会尝试。偏好探测是不同公式；最终查询在当前独立 solver 上建立可供 `Model::new` 读取的模型。|

在没有提前错误退出的主路径上，若有 `T` 个需验证的辅助终态，其中 `M` 个编码最终返回，则源码至少安排 `1 + T + M` 次带完整原约束的 `check_sat`；`F_BIN_RM_TYPE_S` 还对每个 `M` 做一次完整约束加 FS/VS 偏好的 `check_sat_with`。此式只计这些显式入口，实际辅助分支查询、非法指令多样化和模型求值另计；不能用它推出真实次数或耗时。

`Checkpoint::without_assertions` 在 `smt.rs:219–235` 每条主路径克隆完整 trace 并移去旧 Assert；`with_suffix_from` 在 `smt.rs:237–256` 每个终态克隆辅助新增段。`Solver::from_checkpoint` 在 `smt.rs:2591–2619` 顺序重放所有 SMT 事件，但自身不执行 `check_sat`。完整重放在终态验证和输出收集各做一次；这是确定的重复构造，尚无本轮数据证明它比 Z3 查询耗时大。

## 哪些检查可证明重复，哪些不能直接删

终态新增 `C` 含任一 `Def::Assert` 时，原路径 `D∧A` 已 SAT 不能证明 `D∧A∧C` SAT；例如原路径要求 `x=true` 而辅助候选要求 `x=false`。因此 `encoding.rs:56` 的完整域过滤在一般情形必要。若某个终态从辅助基点起**没有新增 Assert**，且新增事件只有已验证的声明、定义、枚举及 trace 事件，则它不缩小原有 SAT 解集；该终态的可行性检查在逻辑上冗余。当前实现未检测这个特例，也没有候选分类计数，不能断言实际旧 flags 中有多少次命中。

普通映射的拒绝终态在 `encoding.rs:56` 先验完整域 SAT，再把辅助 checkpoint 交压缩映射。拒绝本身不输出编码，其增量 Assert 会完整传给压缩。理论上可以把拒绝域的验证推迟到压缩终态，以免同一拒绝域被单独检查一次；但需要同时证明压缩无终态、辅助异常、UNKNOWN/Error 和原有错误报告口径不变。现有接口没有这个证明，不能直接删除。

对已经通过 `encoding.rs:56` 的成功候选，若 collector 尚未增加偏好或多样化 Assert，`exec.rs:945` 的 SAT 命题与前一次相同；即使 FS/VS 偏好查出 SAT 并加入 Assert，也可从该次假设查询推出新公式 SAT。**这只是可满足性判断上的重复**。`exec.rs:860` 新建了不同 Z3 context 和 solver；`Model::new` 在 `smt.rs:1676` 直接从这个 solver 取模型，随后读取编码、初态、后态及返回值。原验证 solver 的 SAT/模型没有跨 API 边界传入；因此不能只删 `exec.rs:945`，否则新 solver 未必有可用的最终模型。保留同一最终模型输出还要求在任何 FS/VS Assert 与非法多样化 Assert 之后取模型。

非法指令路径另在 `exec.rs:921–926` 进入 `diversify_unconstrained_finite_domains`：该函数 `exec.rs:324` 先做 SAT 以取得模型，候选值经 `check_sat_with` 后才 Assert，最终又到 `exec.rs:945`。这里有更多完整查询，但旧 flags 的非法/退休路径占比及耗时仍未知。`exec.rs:1037` 的具体编码回环会重新运行 mapping；它使用已具体化指令/寄存器的新辅助 solver，不携带原主执行的昂贵 Assert，不应混入上述“完整约束重复”计数。

若本轮旧 flags 超过 7200 秒，优先在隔离副本为 `exec.rs:817`、`encoding.rs:56`、`exec.rs:893/945` 分别记调用次数、SAT/UNSAT/UNKNOWN、墙钟与原 trace Assert 数，并单列辅助 Jump 查询和 checkpoint 重放时间。这样才能分辨主要成本是候选完整域过滤、最终取模型、FS/VS 偏好，还是辅助候选数；旧版诊断的 collector 占比不能直接外推到这次新流程。潜在改动顺序应先证实热点，再考虑无新增 Assert 的安全跳过或让验证与最终模型共用一次 solver 生命周期；后者涉及 collector 接口和模型所有权，超出本次只读任务。
