# scheduler 本轮评审与修复

结论：发现了影响退出、取消、资源释放与远端输入正确性的真实问题，已在同一轮修复并补充回归。全套 **86/86 PASS**，命令退出 0，33.013 秒。没有需要用户重新决定架构的事项；真实三节点求解仍未验收。

受审基线为本次 scheduler 交付提交 `a4cbabf6` 及其工作区实现。范围包括 native/、integration/、Make 入口、manage_data 的新增后端选择、nodes.conf 和对应测试。已有 Condor 原型的内部实现不作历史架构评审，保留 22 项旧测试用于兼容检查。全部本轮修改仅在 scheduler/，仓库其他既有未提交内容保留。

## 问题、影响与修复

| 编号 | 级别 | 原问题及具体影响 | 本轮处理与验证 |
| --- | --- | --- | --- |
| R1 | P1 | Make 只等自身结束；controller 已退出但未 reap 时，proxy 的 kill(pid,0) 仍判活，双方可能一直等待。启动期取消也可能返回错误状态或继续启动 Make | 包装入口同时监控 Make/controller；识别 zombie 与 PID 启动身份；启动前处理取消；清理有界等待并回收。实际强制结束主控和启动期 TERM 测试通过，分别返回基础设施失败 125 和取消 143 |
| R2 | P1 | 本地 proxy 异常退出后，独立 session 的监督器可能继续求解；local 执行线程抛异常时缺少最终结果，proxy 永久等待 | 本地派发增加异常收尾；保存 supervisor 启动身份，proxy 消失后主控定向接管 TERM 并取得完成证据。当前 Conda Python 缺少 pidfd_open，故使用原监督器也要求的系统 Python 打开 pidfd、再次核对启动身份并发信号。实际杀死 proxy 后监督器结束、Make 非零、预约归零 |
| R3 | P1 | 冻结大文件时持有主控调度锁，其他任务完成释放和取消可能被磁盘 IO 阻塞 | 输入冻结改持独立锁；不占用 QoS/状态事务锁。测试让 freeze 停在事件上，同时成功获取调度锁；本地仍不建立缓存 |
| R4 | P1 | SSH stderr pipe 可能被诊断填满；心跳线程可能卡在 stdin 写入/关闭；worker 在日志输出阻塞时无法及时处理取消与租约 | stderr 改临时文件并有界读取；execute 改为单一非阻塞 IO 循环，按租约调整心跳间隔；worker 输出有截止时间，管道不可写则停止发送并进入清理。256 KiB stderr、短租约、小管道停止读取、EOF 与忽略 TERM 后代的真实进程测试通过 |
| R5 | P1 | 缓存输入引用与输出路径重合时，可写输出可能沿符号链接落到只读缓存；配置符号链接解析后丢失原目录层级 | 拒绝输入与可写输出目录冲突，worker 限定解析后的路径不得越出对应根目录；保留逻辑输入名，冻结解析后的源内容。现有越界测试、输入/输出冲突拒绝与配置链接逻辑路径测试通过 |
| R6 | P2 | 普通 flag 的值若恰好是本地文件，会被当输入改写；参数值可能再次被当作线程选项。扫描未使用 TOML 的输出字段可能误拒绝合法任务 | 按选项角色一次消费参数值，普通数值/策略值原样保留；CPU 请求只取唯一线程声明；仅检查实际使用配置的输出语义。覆盖同名普通文件、文件名类似线程 flag、可选无值 flag、未使用 TOML 与缺失未知文件参数 |
| R7 | P2 | preflight 的启动错误在 try 之外，单节点失败可能终止整个 controller；坏请求、本地线程异常和日志尾部写失败可能遗留状态/预约；取消 staging 被误记失败并隔离健康节点 | 将启动错误纳入单节点预检；坏请求记 FAILED；已确认退出先释放 CPU，日志失败单列 retrieval=pending；启动前取消记 CANCELLED 并释放，保持健康节点在线。分别补故障注入回归 |
| R8 | P2 | worker 信号处理安装晚于启动程序；监督器继承协议 stdin；启动意图与 running 记录之间有空窗；删除 job 内的锁文件会破坏后续互斥身份 | 提前安装信号处理，远端程序 stdin 使用 DEVNULL；启动前持久化 task 意图，owner 拒绝未确认意图；START、summary/fetch/delete 共用 jobs 父目录的持久锁，取数期间持锁。原有重复 START、活动删除、取数与新增未确认启动意图测试通过 |
| R9 | P2 | shell 赋值的部分 GNU Make 形式、缩写 stdin Makefile、内层 -- 和隐藏目录参数未正确处理；取数工具在连接/建立路径前未检查 job-id；非法外部占用与非有限租约可进入配置 | 拒绝不支持的 Make 参数及继承覆盖；提前验证取数 job-id；验证外部占用范围和有限正租约；缺 backend 值时给明确错误。参数、连接前拒绝、配置负例与双模 Make 回归通过 |

P1 表示会造成任务残留、长时间挂起或破坏输入/输出边界；P2 表示会造成特定故障分支或输入配置下的错误行为。以上问题均已修改，本表不是仍待处理的问题清单。

## 重点审查结论

- **本地运行**：仍由原 cwd 的 proxy 使用 sys.executable 与原 argv 启动监督器，不走 stage/SSH，不复制、不硬链接、不缓存项目文件，不建立 attempt 工作树。stdout/stderr 直接继承原 recipe 日志，70000 个字符完整保留，首行不重复；环境和 TMPDIR 不改变。
- **退出证据**：本地与远端均选择本次 clause/PID 的 process JSON，核对 PID、cwd 与退出码；本地再核对 clause。其他任务或历史 JSON 不计入本次证据。已确认退出但尾部取数失败不会继续占 CPU；无法确认后代结束时仍保留 UNKNOWN 预约，避免把未知任务当空闲。
- **QoS**：max(1, cores // 2)、节点总容量上限、priority、平滑 4:1 轮询保持不变。失败试探不消耗 credit，release 按 lease 幂等；启动前失败/取消释放，确认退出释放，未知状态保守保留。旧 stop_free_cores 不参与接单。
- **缓存**：冻结锁与节点 stage single-flight 仍保持，多任务共享不可变对象；传输等待可取消，临时文件失败后清理。对象元数据检查补上非负大小、只读/执行权限和链接拒绝，不改变按文件版本增量传输方式。
- **Make 接点**：审查 solve.mk 和 make_shell.py，未改 recipe 结构契约。未受管目标沿原 shell 执行；受管目标仅允许既有本地准备及 exec 结构，不支持的结构拒绝。直接原生 Make 不加载 scheduler；对应回归通过。
- **配置与旧入口**：当前 nodes.conf 的三节点资源和动态门槛无需改动。旧容器部署/提交实现保留，manage_data 默认 native，显式 condor 分支回归通过。

## 验证与适用范围

```bash
python3 -m unittest discover -s scheduler/tests -v
git diff --check -- scheduler
```

全套结果为 86 项通过、0 失败，包含原 60 项与本轮 26 项新增回归。完整输出见 [review-tests-final.log](evidence/review-tests-final.log)。diff 空白检查通过。测试使用 scheduler/runtime 内的 Makefile/监督器副本、短程序、真实子进程和模拟 SSH，不修改 Isla 和模型仓，也不借用在途实验数据。

首轮回归发现本机 Conda Python 不暴露 pidfd_open，导致接管清理保持 UNKNOWN；已改为系统 Python 的身份核验信号助手，并重新通过完整测试。该调查失败保留在 [review-tests-regressions.log](evidence/review-tests-regressions.log)，不改写为历史成功。

当前限制仍见 [NATIVE_STATUS.md](NATIVE_STATUS.md)：主控不提供自动续跑，未知租约不自动重派；单节点一次仅有一个 controller；线程声明属于预约估计，不是硬配额；主动逃离原 timeout 进程组的后代不在原监督器的支持范围内。若本地接管后依然不能确认结束，owner 会拒绝 native/local-unknown 中留有记录的节点，须人工核对后再恢复。

真实 SSH 与跨发行版 isarch 验收仍受原网络沙箱阻断结论限制。本轮只签收上述静态检查与已执行的本地/模拟故障回归，不宣称真实三节点生产验收。
