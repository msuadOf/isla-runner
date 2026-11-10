# 全域访存边界与 bdd 对照

这份记录只比较实际相同配置、seed17、T1、qfaufbv、Clause/SMT各7200秒的正式入口。候选 `4d085b14`/bin `3e44cdd6…` 的 `make solve-STORE/C_LD/LOAD_FP` 在 `runs/full-make-4d08/`；bdd 基线为独立归档源码/Release bin `70d3fa13…`、IR `c65b26c8…`，同一配置 `riscv64_difftest_mem.toml` SHA `f05ab1ce…` 或 FD SHA `20851fdb…`，运行在 `runs/merge-baseline-full-v1/`。两侧 IR/模型版本不同，计数不要求相同。

| Clause | 新候选原域 | bdd 同配置当前证据 | 可下的结论 |
| --- | --- | --- | --- |
| LOAD_FP | exit2，partial，errors4，gen0；日志2次 `SymbolicLength("zeros")`，另有译码回环 Poison | exit0，partial，errors6，gen0；同 `zzzeros` 调用栈 | 符号宽度无见证缺口已存在于bdd；新回环 Poison 单列，不能据总数减少称修复。 |
| C_LD | exit0，partial，unfinished7，gen89；日志7条 Ctor Poison | bdd原域仍在7200秒预算运行，日志已见同 Ctor Poison 类型 | 该错误类别有基线实证；全域是否退化仍待完成。 |
| STORE | 新 `4d085b14`正式bin `3e44cdd6…` exit2，partial，errors922/unfinished112，gen130；日志112条 Ctor Poison，末尾译码回环 Poison | bdd原域仍在7200秒预算运行，日志已见同 Ctor Poison 类型 | 该错误类别有基线实证；未完基线不能证明全域无退化。 |

三个实际失败代表已有独立同输入复放：[核心分类](../../review/core/partial-boundary/report.md)与[验收复核](../../review/acceptance/limited-signoff.md)。STORE 的一个回环 Poison 使用捕获的同一机器字和 183 项门寄存器，在新旧程序及各自 IR 中都得到 SAT、Poison 和相同的 Zicfilp Hypervisor 不支持异常；STORE、C_LD 各一个顶层 Poison 则保留原构造子及 102 项前态，在两侧都得到相同的无效 privilege 异常。它们证明这三个具体代表的模型边界已继承；全部 922 条回环错误、112/7 条未完成尚未逐例复证，原域仍为 partial，完整基线对照仍待实际退出。

代表固定机器字 `STORE=0x0020b023`、`C_LD=0x6000` 在 `probes/partial-representatives/` 使用两侧相同的 memory 配置、T1/qfaufbv和 600秒外限；这些临时探针没有seed17注入，仅作诊断。候选未钉完整 mstatus 域分别生成 partial/unfinished5、partial/unfinished7，旧bdd两例均到600秒外限退出124、没有最终JSON。因此代表对照没有完成，不能用来签全域继承。另试 `STORE=0x01ffb023`、VirtualSupervisor/mstatus0/x31=1，两版普通CLI都在启动译码 solver 因值依赖符号状态拒绝，不能代替生产collector捕获的同Ctor后段P3 Poison；后段 P3 已由上述直接构造子／完整门状态复放单独确认。定向 Make 的 Machine/mstatus 固定正例另在 `runs/directed-make-4d08/`，四入口均 finished；它证明合法定向域可完成，不关闭上述原域 partial。
