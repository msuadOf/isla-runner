# 新官方 Z3 消融状态

正式后台队列已启动；运行期间请看只由新监视器写入的 [实时机器汇总](live-summary.json)、[实时报告](live-report.md)。旧 worker 仍可能短暂覆盖普通 `summary.json`/`report.md`；全部 worker 退出后监视器会将最终格式写到这两个普通入口。PID 及固定设置见 [launch.json](launch.json)。本页不重复会变动的计数。

14 项输入及完整 Clause 对照已冻结，逐项来源/哈希/2053 个函数定义的差异见 [input-verification.json](input-verification.json)。[形式参数审计](alpha-audit.json)说明 mask 的 22 个附加函数差异只是编译形式参数改号；去源码位置并按形式参数位置 alpha 归一化后，mask/reduction 各仅目标 `zexecute` 不同。验证只去位置元数据和真正的形式参数改号，没有忽略其它 IR 定义差异。

官方运行器 SHA-256 `c9c5bb8b32289006b1af621f71f03537aecf4a1b0b9ed9b51bc68e573785e2f2` 与切库记录一致，RUNPATH 链到官方 Z3 `1fd1d3613`，库 SHA-256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。seed 拦截器 SHA-256 `8b26e6567f153ec28f35dfaddc15e9dfa3d53dcfa7fb1fe23d4922452bf429ae`；真实 `FLEQ_S` A 小例在 `pilot/seed-a/intercept.log` 记录 `random_seed` 被固定为 17 且自然完成 10 见证，B 小例同样记录拦截但触及 30 秒 pilot 外限，未计入正式数据。

正式工作负载严格按 [协议](protocol.md)执行；原始命令、拦截日志、时间、输出在 `runs/<workload>-pairN/<arm>/`。12 个 worker 可在代理本轮结束后继续运行；监视器持续用最新汇总代码刷新报告，并在全部 worker 退出后最后重写一次，避免旧 worker 的中途写入覆盖最终格式。没有额外长预热。

旧 `qfaufbv`/60 秒试验见 `agents/branch_ablation_20261031/`，只作独立历史证据。本轮性能和覆盖只按官方 Z3/qffp/7200 秒正式记录判断。
