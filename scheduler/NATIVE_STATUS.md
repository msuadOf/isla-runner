# 原生 Make / SSH 调度状态

2026-11-10：用户要求的 Make 接点、自动输入、文件版本缓存、静态 QoS、SSH worker、阻塞 proxy、日志尾部、完成证据及取数工具已实现。本地与模拟测试 **86/86 PASS**；真实三节点 Isla 求解尚未验收。逐次结果见 [RESULTS.md](RESULTS.md)。

所有本轮修改位于 `scheduler/`。保留原有 Condor 实现与历史证据，未修改 `isla/`、模型仓、根目录状态文件或其他工作树。按用户目录限制，代码发现与状态在本目录记录。

## 全面评审修复

2026-11-10：本轮集中审查并修复生命周期、IO 阻塞、调度锁、异常资源释放、输入角色与路径边界问题；26 项新增回归与原 60 项均通过。详细发现与证据见 [REVIEW.md](REVIEW.md)。local 仍直接在原 cwd 运行，QoS 半数公式保持不变。主控异常退出会结束本轮 Make；proxy 意外死亡时由 controller 按保存的启动身份接管原监督器。无法取得结束证据的本地任务会留下 local-unknown 记录，下一轮拒绝接管该节点。

## 动态半数阈值修订

2026-11-10 用户确认：用任务声明的线程数计算溢出门槛。Make 的 THREADS 传给 isarch -T，inputs.py 提取为 cores；本地与远端预约均使用 `max(1, cores // 2)`。T16/T32/T64 门槛分别为 8/16/32，派单后仍预约完整 cores。优先级、同级权重、节点容量上限、WAITING 与完成释放保持原有机制。节点配置不再要求 stop_free_cores，残留字段不参与调度。

已补动态边界、轻重任务、旧字段忽略、无旧字段配置加载和线程参数提取测试；旧固定门槛的验证按 RESULTS 对应历史版本保留。

## 本地就地执行修订

用户已确认：local 节点免 SSH、免拷贝，直接使用原 cwd。当前 `Controller.prepare` 仅保留原参数与 CPU 需求；缓存对象与 ELF 依赖只在选中远端后准备。`perform_local` 保持 QoS 预约，由持有原 stdout/stderr 和完整环境的 proxy 使用 `native/local.py` 启动原监督器。仅把 Python 入口换为 `sys.executable`，原参数、环境、TMPDIR 和产物路径保持原状，不建立 attempt 工作树。

本地运行期间，controller 等待本地监督器的完成证据后才释放资源；取消仍由原监督器清理 timeout 进程组。本地证据按 clause 与 supervisor PID 精确选择，避免共享 output/process 内的历史文件或并发任务干扰。远端 worker、传输与取数实现保持原状。本地当前文件的修改直接可见，远端继续使用冻结输入。

本轮测试修复 Make 的语言环境断言为 `(Error|错误) 7`。原 53 项结果保留在 RESULTS 历史节，不沿用其“本地也走缓存隔离”的行为描述。

## 目标与实施

| 项目 | 当前实现 | 验证 |
| --- | --- | --- |
| 双模 | 原 Make 独立执行；包装入口动态加载附加 Makefile | 真实 GNU Make、当前 run.mk 与监督器副本，本地/包装两种模式通过 |
| Make 接点 | `integration/solve.mk` 的 private SHELL；`make_shell.py` 保留本地准备与进度，仅接管受管 exec | 原生管理目标、失败码、不支持结构拒绝、SIGTERM 通过 |
| 输入 | 本地仅识别原命令与 CPU；远端识别输入/输出、配置镜像和 ELF 依赖 | 路径空格、长参数等号、外部输入、缺失输入与输出角色通过 |
| 远端缓存 | stat 索引、不可变复制、内容校验、节点 single-flight、READY generation | 同大小改写保留 mtime 可被检测；并发只传一次；改 TOML 只传该文件 |
| QoS | priority 阶梯、同级 4:1 平滑轮询、max(1, cores // 2) 动态门槛、完整预约、完成释放 | T16/T32/T64 与奇数/单线程边界、溢出等待、资源归还及不重复释放通过 |
| 运行 | local 由 proxy 在原 cwd 直接启动；远端 transport/worker 保留 attempt 隔离 | 原地环境、完整日志与产物通过；模拟 SSH 完整流程通过 |
| 取消/退出 | lease、EOF、原监督器清理、重复 START 不重复执行、未知状态保留预约 | 真实子进程取消与缺少证据负例通过 |
| 数据 | 本地完整日志与产物原地生成；远端有界日志、64 KiB 尾部与 list/summary/fetch/delete | 实际归档、节点数据保留、活动删除拒绝通过 |

## 已核实的代码事实

- 当前 `run.mk` 的 `solve-%` recipe 分两次调用 shell：本地 mkdir，然后原子计数、打印进度及 exec。适配器分别核对这两类命令，无需复制 clause 清单或超时规则。
- `solve-pre`、`solve-kill` 也匹配 `solve-%`，须恢复原 shell；private 阻止 shell 接点沿依赖传播给 build-isarch。
- 原监督器创建独立 timeout session；只杀 proxy、SSH 或 worker 进程组不能保证 timeout 后代结束。本地 proxy 与远端 worker 均把 TERM 交给原监督器，并取得其完成证据。
- 取消若早于监督器安装信号处理，会缺少退出证据。本地 proxy、接管助手和远端 worker 等到监督器已启动 timeout 子进程再发送 TERM；启动异常仍按基础设施失败处理。
- worker 和 execute transport 均使用单一 IO 循环，控制通道不由阻塞心跳线程持有；worker 日志输出有截止时间，停止读取日志不会阻止租约清理。
- 单纯观察 supervisor 已退出不足以归还 CPU；缺少匹配的 process JSON 时保持 UNKNOWN 并保留预约；远端下一轮 owner 和 delete 同样拒绝把它当成已确认完成。
- 同一文件名的内容变化通过 ctime 与内容校验识别，已发布缓存不会随源文件原地修改。内容摘要只作缓存身份与传输校验，不判定导出数据的语义有效性。

## 与原方案的差异及边界

1. 用户要求零依赖，故未引入第三方 Bash AST 库。标准库 shlex 实现有限语法检查，仅支持当前 recipe 契约；未知结构在执行求解前拒绝。
2. 使用原生 SSH 流协议传缺失文件版本，未调用 rsync；变动大文件仍传完整新版本，不提供文件内部块差量。
3. SQLite 保存任务当前状态与状态事件，JSON 保存逐任务证据；尚无主控崩溃后的自动恢复入口。失联后只有限重连取证，不自动重跑未知任务。
4. CPU 预约统计本调度器与显式 `external_cores` 静态扣除量，不动态估算其他任务 CPU 占用；不提供内存/磁盘硬配额。
5. 每节点由单个 controller 持独占锁；不同工作树暂不能同时共享同一节点。该限制防止跨 run 重复预约容量。
6. 远端日志采用固定 tail 策略与每任务配额，未提供 stream/none 模式和全 run 带宽整形。
7. 记录提交参数、有效命令和输入版本；未冻结全部 Make include 文件或检查运行中 Makefile 编辑。GNU Make 自己在启动时求值，后续调用再读取修改。
8. 远端仅需受管 Python worker，不安装服务。真实跨发行版 isarch/loader 兼容性、完整求解正确性与长时间故障恢复仍须宿主机验收。

## 下一步

在可使用 SSH 的宿主机终端准备有效 IR，确认旧后端无活动任务，再按 [README.md](README.md) 先运行单个 clause、核对退出证据和实际 JSON，最后扩大到多机全组。当前两个远端的 SSH 均被会话网络沙箱阻断；不将模拟结果记为真实集群 PASS。
