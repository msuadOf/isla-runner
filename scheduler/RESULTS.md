# 实施与验证状态

## 2026-11-10：按任务声明线程数使用动态半数阈值

**实现完成，全套测试 PASS，60/60，退出 0，14.378 秒。** 命令：`python3 -m unittest discover -s scheduler/tests -v`。证据：[dynamic-half-qos-tests.log](evidence/dynamic-half-qos-tests.log)。受测对象为本轮 `scheduler/` 工作区源码与已移除 stop_free_cores 的 nodes.conf，Python 3.13.9；38 项原生测试与 22 项旧后端测试全部通过。所有修改均限于 scheduler/，未改动 Isla、模型仓、根目录状态文件或其他工作树。

任务通过 Make 的 `THREADS=32` 声明预计线程数，Make 传为 isarch `-T 32`，`native/inputs.py` 提取为 cores=32；同样支持 `--threads 32`、`--threads=32`。本地和远端都据此预约，调度器不修改真实执行参数。该声明是资源估计，并非线程硬上限；Make 的 -j 不参与线程门槛计算。

现行接单逻辑：`free_cores = cpus - external - reserved`，`threshold = max(1, cores // 2)`；节点须在线、cores 不超过节点总容量，且 free_cores 至少达到 threshold。派单后扣除完整 cores。T16、T32、T64 的门槛分别为 8、16、32；低于对应门槛时溢出，全部无法接单时 reserve 返回 None，任务 WAITING，完成事件释放预约后继续派发。stop_free_cores 不再必填，也不参与判定；旧配置残留字段不影响接单。

| 验证 | 结果 | 实测范围 |
| --- | --- | --- |
| T16/T32/T64 门槛边界 | PASS | free 恰为 8/16/32 时接单，少 1 核则拒绝；高优先级用满后溢出低优先级，全满返回 None，释放后恢复 |
| 单线程和奇数线程 | PASS | T1/T3 门槛 1，T5 门槛 2；验证下限和向下取整 |
| 同一空闲容量适应轻重任务 | PASS | 同一 128 核节点剩余 16 核时，T64 被拒绝，T32/T16 可接单，完整预约后新任务等待 |
| 旧字段兼容与配置加载 | PASS | legacy stop_free_cores=1/16/128 均不改变 T16/T64 判断；无该字段的原生配置成功加载并预约 |
| 线程声明提取 | PASS | T16/T32/T64 分别使用 -T、--threads、--threads= 三种形式，提取 cores 与声明一致 |
| 既有调度及双模回归 | PASS | 优先级、4:1 平滑轮询、T32 超售、外部占用、失败试探不消耗轮询额度、幂等释放、WAITING、本地原地执行、模拟 SSH 缓存与取数、取消与退出码通过 |

新增 QoS 测试先在原固定门槛实现上失败（[初始日志](evidence/dynamic-half-qos-before.log)），更新策略与配置校验后通过。历史 55/53 项测试记录保留原版本与固定门槛语境；现行公式以本节和 [README.md](README.md) 为准。未新跑真实集群长任务，真实远端验收仍不在本轮 PASS 范围内。

## 2026-11-10：local 节点直接在原 cwd 执行

**实现完成，全套测试 PASS，55/55，退出 0，14.152 秒。** 命令为 `python3 -m unittest discover -s scheduler/tests -v`，完整日志见 [local-in-place-tests.log](evidence/local-in-place-tests.log)。适用版本为本轮 `scheduler/` 工作区源码；33 项原生/本地执行测试与 22 项旧后端测试全部通过。本轮未修改 `isla/`、模型仓、其他工作树或根目录代码和状态文档。

local=true 由 proxy 使用 `sys.executable` 和原 argv，在请求的绝对 cwd 直接启动原监督器，完整继承原环境、TMPDIR 及 recipe 的 stdout/stderr 重定向。不调用 stage，不冻结或复制输入，不创建缓存对象、硬链接、符号链接或 attempt/work/root，不注入缓存 loader。本地只新增 scheduler 内的启动、完成及调度元数据。远端继续使用 SSH、增量缓存、运行库重定位和 attempt 隔离；输入冻结推迟到实际选中远端节点后。

| 验证 | 结果 | 实测内容 |
| --- | --- | --- |
| 本地不建立缓存 | PASS | 新增单元测试把 Cache/runtime_files/stage/worker execute 替换为遇调用即失败；本地准备和派发仍通过。Make 集成测试确认主控该 workspace 与本机节点均无新增 cache 对象目录 |
| 本地不使用 SSH 或隔离树 | PASS | 集成测试在 PATH 放置一调用就写标记并失败的 ssh，本地任务成功且无标记；不出现 attempt/work/root |
| 原 cwd、argv 与运行环境 | PASS | 两个本地任务的结果 cwd 等于原 isla 目录；Python 入口为 sys.executable，无 --library-path；自定义环境变量及 TMPDIR 保留原值 |
| 全部产物原地生成 | PASS | output/result-OK.json、output/trace/native-OK.txt、outputs/native-OK.txt、output/process 的本次 PID 证据及 output/status.intime.log 均出现在原 cwd |
| 本地日志完整、实时、不重复 | PASS | stdout 的 70000 个字符完整出现，stdout/stderr 首行各出现一次，无 scheduler 日志首部、截断或尾部重放；长任务结束前已能读取其日志首行 |
| QoS、等待与取消 | PASS | 128 核/T32 的派发单元测试确认完成后释放预约；既有两核四任务峰值预约为 2、结束 reserved=0；运行中 SIGTERM 返回 143、原监督器完成清理并释放预约 |
| 退出码与 locale | PASS | 任务退出 7 仍交还 Make，Make 返回 2；断言改为 `(Error|错误) 7`，接受中英文 Make 错误文本 |
| 远端路径回归 | PASS，模拟 SSH | 原完整 Make 模拟 SSH 流程仍通过，远端 attempt/work/root 存在，原 cwd 无该远端任务 JSON；第二轮仅修改小 TOML，仅传该文件字节数 |
| 原生 Make 及其他回归 | PASS | 原生直接 Make、缓存并发/变更检测、远端 worker 租约/取消、取数和 ELF 运行库等既有测试通过 |

新增的 `test_local_execution.py` 两项测试先在旧实现上失败，再随实现修复通过。原双模测试更新为检查本地原地产物；新增同一进程环境、完整日志和原地目录断言。原 53 项结果保留在下节，适用于初版“local 同样缓存并隔离”的历史版本，其本地行为描述已由本节取代。现行说明见 [README.md](README.md) 和 [NATIVE_STATUS.md](NATIVE_STATUS.md)。

本轮实际执行使用 scheduler/runtime 下的 Makefile/监督器副本与短任务，不启动真实 Isla 长任务或修改原目录产物。远端验证仍为模拟 SSH，不把既有网络沙箱阻断改记为真实三节点 PASS。

## 2026-11-10：纯 Python + SSH 双模调度

**实现已落地，单元与模拟测试 PASS，53/53；真实三节点 Isla 求解 BLOCKED／未验收。** 全部本轮写入位于 `scheduler/`。实现与边界见 [NATIVE_STATUS.md](NATIVE_STATUS.md)，现行使用入口见 [README.md](README.md)。以下旧 Condor 结果保留各自适用范围，不作为原生后端验收。

受测版本为本轮未提交的 scheduler 工作区源码和当前 nodes.conf；主控 Python 3.13.9。双模测试复制当前 Isla HEAD `a38c5e0232d721da46bc80b230e9eeff274c57ee` 的工作区 `scripts/run.mk`、`run_ctrl_c.mk`、`solve_process.py` 到 `scheduler/runtime/`，使用真实 GNU Make 与短小 isarch 替代程序，不修改 Isla 源码。当前模型仓 HEAD 为 `cbb4766f95370c405bf9070e459045ce5aaa281e`；本轮未生成 IR、未重新运行模型或改变导出数据有效性结论。

| 验证 | 结果 | 命令/证据与适用范围 |
| --- | --- | --- |
| 全套测试 | PASS，53/53，退出 0，17.941 秒 | `python3 -m unittest discover -s scheduler/tests -v`；[最终日志](evidence/native-tests-final.log)。31 项原生测试＋22 项旧后端测试，旧取数测试显式指定 backend=condor |
| 原生本机 Make | PASS，短任务 | 不加载 scheduler 时结果在原 cwd；无 scheduler run 生成，原日志无调度包装，进度 `[1/1]` 保留 |
| 当前真实 run.mk dry-run | PASS，退出 0 | `make -C isla -f scripts/run.mk -n -o build-isarch solve-MRET SOLVE_TOTAL=1 THREADS=32`；[日志](evidence/native-original-make-dry-run.log)。未编译、未求解，不作为真实求解 PASS |
| 包装入口与任务退出码 | PASS，短任务 | 两任务保留 `[n/2]`；输入自动定位；结果留在 attempt；任务退出 7 原样交还 Make，Make 返回 2 |
| 模拟 SSH 完整流程 | PASS，模拟传输 | 替代 ssh 执行远端命令，使用独立 Python 进程、不同 HOME、含空格 work_dir 与真实二进制协议；第二轮只改 TOML，传输字节数恰好等于该文件大小 |
| 文件版本与 single-flight | PASS | 40 并发冻结共享一个对象；12 并发 stage 总计只上传一次 IR；同大小改写保留 mtime 仍检测到变化；源修改不污染旧版本 |
| QoS 与等待队列 | PASS | 同级 50 次选择为本机 40/preston 10；高优先级满后溢出 4090；48 核节点接两个 T32；全满 WAITING；两核四个 T1 任务峰值预约为 2，完成后 reserved=0 |
| 生命周期 | PASS，真实子进程 | SIGTERM、EOF、租约到期均定向清理；重复 START 返回原结果；缺退出证据记 UNKNOWN，下一主控拒绝接管 |
| 缓存运行库 | PASS，本机普通 ELF | 缓存 getconf、loader、依赖，通过 worker 启动并输出 glibc 版本；不代替真实远端 isarch 兼容性验证 |
| 延后取数 | PASS，本地 worker | list/summary/fetch/delete、完整归档、节点副本保留、活动任务/路径越界删除拒绝 |
| 三节点真实预检 | 本机 PASS，远端 BLOCKED | [预检 JSON](evidence/native-preflight-20261110.json)：本机 x86_64、affinity 128 CPU、Python/Bash/timeout 可用；两个 SSH 均为 socket Operation not permitted |
| 真实 isarch / 三节点求解 | 未测 | 默认 `isla/rv64d.ir` 缺失，且当前会话不能建立远端 SSH；未借用其他在途实验输入，未启动真实长任务 |

预检的复现入口是 `Controller.preflight`，分别以 nodes.conf 三节点建立 owner worker；本轮未提交求解任务，结束后关闭全部 owner。主控会把不可达节点记为离线；它们不参与本轮资源选择，预检错误会显示在入口终端和 run/preflight.json。

本轮调查中的失败已修复：最初快速任务退出前没有实时首块，导致日志开头遗漏；现补发有界首块。新增生命周期测试发现 stdin 守护线程引发 Python 退出锁错误，以及过早取消使监督器来不及落证据；现改为单事件循环并等待监督器启动 timeout。最终 53 项测试在这些修复后执行；此前 41/45/50 项 PASS 仅属于当时版本。

原方案中的第三方 AST 库已按用户零依赖要求改为有限语法检查；主控自动续跑、跨 controller 共享节点、动态外部 CPU 估计、大文件内部差量与全 run 日志整形尚未提供。完整边界列于 [NATIVE_STATUS.md](NATIVE_STATUS.md)。实际远端验收需在可用 SSH 的宿主机终端完成，不能将上述模拟测试改记为真实集群 PASS。

## 2026-11-10：preston 与每节点 work_dir

**实现完成，本地单元测试 PASS，22/22。三节点实际部署与端到端调度未测。** 受测对象是本轮 `scheduler/` 工作区源码及 [nodes.conf](nodes.conf)：主控 128 CPU、public-4090server 48 CPU、preston 32 CPU，共 208 CPU，所有节点关闭 GPU 调度。本轮没有修改 `scheduler/` 以外的文件。

| 项目 | 结果 | 证据与适用范围 |
| --- | --- | --- |
| 单元测试 | PASS，22/22 | `python3 -m unittest discover -s scheduler/tests -v`，退出 0；[完整日志](evidence/work-dir-tests-20261110.log) |
| 配置与路径解析 | PASS，单元测试 | local/remote 自定义绝对、`~/...`、相对路径，缺省配置、旧字段别名及新字段优先；拒绝危险路径与指向系统目录的符号链接 |
| 目录初始化与命令生成 | PASS，单元测试 | 实际运行初始化 Python 片段，检查目录和用户所有权；模拟 Docker 调用，核对每节点挂载源和 preston hosts 条目，未运行真实 Docker 挂载 |
| 提交、取数、离线渲染 | PASS，单元测试 | 自定义主控目录内实际打包与离线渲染；取数命令和归档落地使用配置目录，SSH/Docker 与下载内容使用替代调用 |
| 当前三节点配置离线渲染 | PASS | `python3 scheduler/scripts/deploy_cluster.py --render-only`，退出 0；生成三份 `scheduler/runtime/rendered/*.conf`，未经过 Condor 自身解析 |
| 已有节点目录检查 | PASS，单元测试 | 旧字段切换到等价 `work_dir` 可接受；实际更换 local/remote 目录要求单独迁移已有数据 |
| preston 主机与网络 | 用户已实测，本轮未重测 | Ubuntu 22.04、32 CPU、无独立 GPU、Docker active、免密 sudo；下发约 800 Mbps、回传约 780–800 Mbps、延迟约 0.55 ms，详见 [RESEARCH.md](RESEARCH.md) |
| 三节点服务及九任务验收 | 未测 | 主机与网络实测、命令生成及本地任务包装器测试均不能替代此项 |

新增实现同时保留固定在 `scheduler/runtime/` 的管理和退役节点记录，以比较已有节点的数据位置；节点数据、提交包、渲染输出及取回归档则使用对应 `work_dir`。初始化会为提交、渲染和取回目录设置任务用户所有权，使 sudo 创建的自定义目录也可供主控脚本写入。可复用的实现说明和配置方式见 [PLAN.md](PLAN.md)。

下一步：在具备宿主机权限的环境按方案执行预检、部署和三节点九任务验收。以下旧记录只适用于当时的两节点配置和旧源码，保留历史 PASS 与失败原因，不作为当前配置的部署或语法验收。

## 此前两节点验证记录（原文保留）

**2026-11-10：脚本与文档已完成本地验证，真实两机部署阻塞。** 没有安装 HTCondor，没有确认两节点在线，也没有完成实际任务调度或数据跨机回传。不能把本页的本地 PASS 理解为集群 PASS。

本次仓库写入限制在 `scheduler/`。既有其他目录的未提交内容保留。按用户指定范围，本议题没有登记到根目录状态表。

## 当前结果

| 项目 | 结果 | 证据或边界 |
| --- | --- | --- |
| 方案、调研、节点配置和模板 | 已提供 | [PLAN.md](PLAN.md)、[RESEARCH.md](RESEARCH.md)、[nodes.conf](nodes.conf) |
| Python 源码与嵌入式远端脚本语法 | PASS | [verification.json](evidence/verification.json)；runner 和远端片段按 Python 3.10 语法检查 |
| Shell 语法 | PASS | `bash -n scheduler/scripts/test_cluster.sh` |
| 两节点配置离线渲染 | PASS | `deploy_cluster.py --render-only`；未经过 Condor 自身解析 |
| 本地行为测试 | PASS，9/9 | [offline-tests.log](evidence/offline-tests.log) |
| 本机系统探针 | 已核实 | Ubuntu 26.04.1、x86_64、128 CPU、存在 Docker 客户端 |
| 预检 | BLOCKED，退出 1 | [preflight.json](evidence/preflight.json)：sudo 无法提权，远端 SSH socket 被禁止 |
| 实际部署命令 | BLOCKED，退出 1 | [deploy.log](evidence/deploy.log)：在本机 sudo 预检阶段停止，未安装或修改服务 |
| 端到端测试命令 | BLOCKED，退出 1 | [e2e.log](evidence/e2e.log)：读取节点状态前被 sudo 限制，执行任务数 0 |
| 官方文档和包源在线核实 | BLOCKED | 代理连接被拒绝；直连不能解析官网域名 |
| NVIDIA/GPU 发现与任务 | 未测 | 当前 `enable_gpus = false`；硬件信息由用户提供 |

执行命令、退出码和时间汇总在 [verification.json](evidence/verification.json)。`e2e-*.json` 是验收脚本生成的逐次报告：预条件不满足时，报告中的运行结果是 FAIL；本页按根因归类为环境 BLOCKED，不将其改写为成功。

## 本地行为测试覆盖

```bash
python3 -m unittest discover -s scheduler/tests -v
```

这 9 项测试实际启动本地子进程、构建任务包并运行任务包装器，检查：

1. 完整回传归档包含 2 MiB 结果，节点副本仍保留。
2. 摘要策略只复制限量摘要与日志，记录超限摘要名称。
3. 不回传策略不生成任务回传文件，节点结果与退出摘要仍在。
4. 程序非零退出保留退出码和 stderr。
5. 同一任务再次执行创建独立 attempt，不覆盖旧结果。
6. 输入符号链接被拒绝。
7. 包内越界路径及链接被拒绝。
8. 模板替换与节点定向提交描述符合本次约定。
9. 本机普通 ELF `getconf` 的 loader 和依赖打包后，实际执行得到预期 glibc 版本。

测试没有启动 HTCondor，不覆盖其提交语法解析、认证握手、排空行为、Docker 挂载、真实文件传输或远端运行。Python 3.10 的语法检查也不能替代在该解释器下的运行验证。

### 调查中的失败

最初用 Ubuntu 26.04 的 `printf` 测试 ELF 打包，程序退出 1，报告 `coreutils: unknown program 'ld-linux-x86-64.so'`。该机器的 `printf` 指向 Rust coreutils；直接通过 loader 启动会改变它用于识别自身的执行路径。即使设置 `--argv0` 也未解决。

因此没有把该失败写成已修复。当前测试改用普通 ELF `getconf`，并在调研中明确限制：`--bundle-libs` 不保证支持多调用程序及依赖 `/proc/self/exe` 的程序。真实 Isla 二进制还需单独验收。

## 阻塞与下一步

阻塞来自当前 agent 会话的安全限制，而非已证明宿主机缺少免密授权。主要错误为：

```text
sudo: The "no new privileges" flag is set, which prevents sudo from running as root.
socket: Operation not permitted
ssh: connect to host 192.168.221.161 port 22: failure
```

在具有正常宿主机权限的终端，先核实候选 25.x jammy 包源、签名密钥与支持状态，然后执行：

```bash
python3 scheduler/scripts/deploy_cluster.py --check
python3 scheduler/scripts/deploy_cluster.py
bash scheduler/scripts/test_cluster.sh
```

只有部署成功、两节点资源广告正确、六个策略任务全部通过后，才能记录该版本的集群 PASS。之后仍须单独验证安全负例、实际 Isla 二进制、节点退役和异常恢复。新增验证记录保留命令、实际版本与结果；实现或配置改变后，不沿用旧结果冒充新版本通过。
