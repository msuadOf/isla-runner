# flags 终态收集器求解成本核查（2026-11-02）

## 当前结论

`F_BIN_RM_TYPE_S` 的 flags 显式分支在首条主路径返回后，昂贵的浮点约束继续留在终态收集器的求解上下文。收集器先重新检查路径可满足性，再从该上下文的 checkpoint 执行符号指令编码；编码辅助执行器的每个分支及终态也会做 SMT 检查。实际阶段标记与 Z3 FFI 计时均显示，这些重复检查是首条 B 路径收集耗时的重要来源。

在清除残留探针后，隔离 CPU112 上完成一条受控诊断：同一条已具体化的 `FDIV_S` 指令交给相同 `encoding_paths` helper。保留原执行 checkpoint 时，编码阶段 **36.50 秒**，7 次 Z3 check 累计 **36.418 秒**；重放原 solver 的 540 个声明／定义、移除 15 条路径 `Assert` 后，同一具体参数三次编码分别 **0.05／0.05／0.04 秒**，Z3 check 累计 **0.007524／0.008160／0.007072 秒**。两侧均得唯一机器编码 `0x191f7053`，输出集合逐字相等。这是实际性能因果对照，说明这条具体路径的断言是编码辅助重求解变贵的来源；不能据此直接在生产中移除断言，因为其它符号候选的可达性和编码集合可能改变。

先前两次同输入对照也得相同编码，但诊断进程未正确退出，CPU112 上存在多轮探针互抢；其 240.32／454.96 秒只能作为**受污染历史观察**，不用于干净性能比。早期 300 秒采样的单查询最长 22.27 秒同样不能外推到完整 7200 秒运行。

## 干净首路径对照及退出核账

[clean-result.json](clean-result.json)记录启动时本探针进程为 0、完整 `wait` 返回码为**87**（诊断专用首 case 退出码）、总墙钟 59.94 秒、user 57.95 秒、sys 1.86 秒、退出后本探针 PID 为 0；`control_only_exit` 标记确实出现。`clean-run.log` 的路径返回为 538150.68，collector 主检查 538150.68→538158.53 为 7.85 秒；随后三次无路径断言的编码 538158.55→538158.69，原 checkpoint 编码 538158.69→538195.19 为 36.50 秒。[clean-stage.json](clean-stage.json)按原始 Z3 FFI query ID 抽取累计时间：主检查 48，三次新上下文分别 49–55、56–62、63–69，原 checkpoint 为 70–76。所有这些查询均返回 SAT。`/proc/uptime` 阶段时戳仅精确到 10 ms，因此三次新上下文的边界按 `PATH_ACCOUNT` 的纳秒级辅助任务完成／启动事件核对：第一段末尾 538158.603758／第二段开头 538158.604125，第二段末尾 538158.651611／第三段开头 538158.651962。query55 和 query62 分别属于第一、第二段。

具体字段 `F_BIN_RM_TYPE_S|S0=17|S1=30|S2=RM_DYN|S3=0|S4=FDIV_S`，规范串 SHA256 `fe16ed4e91f38c0ef2a2a544c2aa0f3cbfb4e9aa194b7eb224dbd51e65509837`。[input-comparison.json](input-comparison.json)按字段解析 `clean-run.log`，与旧两次对照为同一具体参数；干净轮的原／新编码集合 `equal=true`。

探针专用补丁 [clean-probe.patch](clean-probe.patch)把首次 case 的 `CONTROL_ONLY` 改为 `std::process::exit(87)`；[clean_run.py](clean_run.py)同步等待整个命令完成，并在前后按二进制路径扫描 `/proc`。命令、环境、二进制／IR／配置／Z3 SHA 在 [clean-launch.json](clean-launch.json)，`/usr/bin/time` 原始记录在 [clean-time.txt](clean-time.txt)。这轮只验证首条 collector case，未生成完整 Clause JSON，不能写完整 Clause PASS。

## 版本与原始证据

冻结源码 `09ffa91`，B IR／config 为 `agents/branch_ablation_official_z3_20261102/inputs/flags-arithmetic/`，官方 Z3 `1fd1d3613`，QFFP、单线程、seed17，Clause 和 SMT 均为 7200 秒预算。私有探针在本目录隔离源码副本中增加阶段标记和诊断对照；干净复核版本见 [clean-probe.patch](clean-probe.patch) 与 [clean-source-hashes.json](clean-source-hashes.json)，旧错误退出版本见 [probe.patch](probe.patch) 与 [source-hashes.json](source-hashes.json)。生产源码与原始 B IR 未修改。历史实验均绑在 CPU112，但首轮外层 `/usr/bin/time` 退出后 `timeout` 创建的独立进程组和 `isarch` 子进程未退出，后续多轮同核竞争；命令及二进制／IR／配置 SHA 见 [control3-launch.json](control3-launch.json)、[fresh3-launch.json](fresh3-launch.json)、[replicate-launch.json](replicate-launch.json)。查询原始事件在相邻 `*-queries.tsv`，阶段事件和具体指令／编码在相邻 `*-run.log`。可提交的精简文件清单见 [commit-files.txt](commit-files.txt)。

以下表格为**历史受同核竞争污染的观察值**，仅保留可追溯记录，不用于干净性能比。

| 诊断 | 首条主路径返回后阶段 | 墙钟秒 | 完成 check | Z3 check 累计秒 | 结果 |
| --- | --- | ---: | ---: | ---: | --- |
| control3 | 主路径再次 `check_sat` | 53.58 | 1 | 53.579 | SAT |
| control3 | 同具体指令，新上下文编码 | 0.29 | 7 | 0.124 | 唯一 `0x191f7053` |
| control3 | 同具体指令，原 checkpoint 编码 | 240.32 | 7 | 239.972 | 唯一 `0x191f7053` |
| fresh3 | 同具体指令，新上下文重复 1／2／3 | 0.51／0.61／0.63 | 7／7／7 | 0.237／0.283／0.286 | 每次 `0x191f7053` |
| replicate | 同具体指令，新上下文重复 1／2／3 | 0.74／0.71／0.72 | 7／7／7 | 0.349／0.328／0.331 | 每次 `0x191f7053` |
| replicate | 同具体指令，原 checkpoint 编码 | 454.96 | 7 | 454.551 | 唯一 `0x191f7053` |

具体指令字段：`F_BIN_RM_TYPE_S|S0=17|S1=30|S2=RM_DYN|S3=0|S4=FDIV_S`；规范串 SHA256 `fe16ed4e91f38c0ef2a2a544c2aa0f3cbfb4e9aa194b7eb224dbd51e65509837`。逐字段核对见 [input-comparison.json](input-comparison.json)；`control3-run.log`、`fresh3-run.log`、`replicate-run.log` 首条 `COLLECTOR_CONTROL concrete_arg` 均为这些值，字段哈希表打印顺序不同。`control3` 和 `replicate` 首条新上下文编码集合和原 checkpoint 编码集合逐字比较均为 `equal=true`。新上下文重放原 trace 的非 `Assert` 定义，继承符号编号，故比较的是同一个 helper 和具体 instruction；两边约束集合不同，仅对本条具体指令的输出相等。

首条 `control3` 主路径在单独探针中于单调时钟 535159.077 返回；collector 的主检查从 535159.07 到 535212.65，新上下文编码从 535212.71 到 535213.00，原 checkpoint 编码从 535213.00 到 535453.32。对应 query ID 分别为 48、49–55、56–62。原 checkpoint 的 7 次 check 中多次耗时 15–57 秒，累计 239.972 秒；新上下文 7 次总计 0.124 秒。query55 在阶段边界前开始、边界后结束，按原始 begin 时间归入新上下文；此前脚本按粗粒度阶段时戳误归属，已修订。阶段时间以 0.01 秒 `/proc/uptime` 标记，精确 check 时间来自原 Z3 FFI 包裹器；少量边界归属以阶段顺序与 query ID 核对。

`control3`、`fresh3` 和 `replicate` 的 `CONTROL_ONLY` 仅从 collector 返回，**没有退出整个 solve-state 进程**。当时仅向外层 time PID 所在进程组发出 TERM，未终止 `timeout` 的独立进程组；其子进程继续运行，后来由主代理按 `/proc` 匹配清理。这是本次实验控制错误。它们没有完整 JSON，不能作为完整 Clause PASS。较早的 `run.log` 探针在首次 collector 编码持续超过 204 秒后主动结束，也只支持阶段定位。`control-run.log`、`control2-run.log` 的首次新上下文构造不完整而 panic，已保留失败原始记录，不用于性能结论。

## 调用链与其它阶段

- 主路径执行器调用 collector 前的标记在冻结 `isla-lib/src/executor.rs:980-982`。`Run::Finished` 后，`src/isarch/exec.rs:799` 首次 `check_sat`，`:817` 将当前 solver 的 checkpoint 传给 `encoding_paths`。
- `src/isarch/encoding.rs:95-109` 先执行普通 `zencdec_forwards`，仅在正常拒绝域追加压缩编码；`:25-70` 的辅助执行器从 checkpoint 起步，执行分支时检查可满足性，终态再 `check_sat`。因此原主路径的 flags/浮点约束会参与辅助编码查询。`isla-lib/src/executor.rs:2838-2868` 确认该 helper 是从 checkpoint 启动的单线程辅助任务。
- `src/isarch/exec.rs:875` 对官方浮点条目试探 FS/VS 偏好；`:927` 再做一次最终 SAT 检查；`:952-1206` 用最终模型具体化初态、指令、汇编、完整前后态与返回值。这些步骤解释了**为什么终态有多个求解点**。干净诊断在首条编码对照后主动退出，尚未走到 FS/VS 偏好、最终检查和后态具体化，故不把这些阶段列作已测主成本。
- `src/isarch/mod.rs:109-223` 的 `try_get_assembly_name`／`try_get_assembly_encdec` 会对具体参数另启 mapping 求解器，不直接继承上述主路径 checkpoint。本次未测这两个调用的 B 首条路径耗时，不把汇编打印视作已证实原因。非法路径的有限域多样化在 `src/isarch/exec.rs:894-924`，首条具体 `FDIV_S` 退休路径没有进入该分支，亦不是这条慢路径的原因。

独立路径核账见 [path-accounting/theory.md](../path-accounting/theory.md)：A flags 主执行树 fork171／完成172，编码等辅助单线程树 fork244，旧 `-D f` 位置415是两树之和；A sat 为主 fork12／完成13、辅助 fork31，旧位置43亦为两树之和。故不能将 collector 的辅助 fork 冒充 flags/sat 主 Clause 路径增长。A flags 首条 `run_return` 到 `task_done` 为 1.021 秒，172条 collector 中位 1.071 秒、最长 5.749 秒；该对照只说明 B 首条收集器明显更慢，不按不同运行条件计算完整 Clause 加速比。

正式 B 路径插桩的较长观测还出现单次长查询：`path-accounting/final-flags-arithmetic/run.log` 中一条主路径在单调时钟 534446.925 返回后尚在 collector；其 `queries.tsv` 的 query 685 为 `check_sat_assumptions`，从 535032.937 至 536071.595，耗时 **1038.658 秒并返回 SAT**。同一辅助 solver 指针后续 query 687 又耗时 40.167 秒、query 691 的普通 check 耗时 44.728 秒。这说明早期 300 秒样本“最长 22.27 秒”只适用于其采样窗，不能推广到完整 B 运行；本次至少有一次超过 17 分钟的单次查询。该正式轮尚未结束，最终 Clause 状态由主路径报告给出。

sat 的 collector 调用链相同，但本目录未对 sat B 做同指令上下文对照，不能据 flags 的结果断言 sat 超时也是这一原因。完整 7200 秒 Clause 结果以主任务的正式路径核账为准。
