# Make solve 的纯 Python + SSH 调度

直接运行原生 Make 时仍全部在本机执行。只有通过 `make_solve.py` 才启用分布式调度；不修改 `isla/` 的 Makefile、监督脚本或二进制。

调度到 `local=true` 节点的任务直接在请求的原 cwd（例如 `isla/`）执行原命令，使用 `sys.executable` 和原环境。跳过输入冻结、缓存、stage 与 SSH，不建立 `attempt/work/root`，不注入 `_runtime/` loader 或 TMPDIR。JSON、trace、process、status 和 outputs 等产物原地生成，完整 stdout/stderr 直接继承原 recipe 的日志重定向。本地仍受相同 QoS 预约、等待、释放与取消逻辑管理。远端继续使用 SSH、增量缓存和独立 attempt。

```bash
# 方式 A：从仓库根目录启动分布式调度。
python3 scheduler/scripts/make_solve.py -- \
  -C isla -f scripts/run.mk solve -j208 THREADS=32

# 方式 B：在 isla/ 中原生本机运行。
make -f scripts/run.mk solve
```

分布式入口也接受 `solve-memory`、`solve-fd-float`、`solve-fd-nonmem` 和单个 `solve-<clause>`。本地由原程序检查输入，远端分发前检查输入；目前工作区默认 `isla/rv64d.ir` 缺失，实际运行须准备 IR 或传入有效的 `IR_FILE=...`。

本轮本地及模拟验证见 [RESULTS.md](RESULTS.md)。两个远端的真实 SSH 连接被当前会话网络沙箱禁止，尚未完成三节点真实 Isla 求解验收。

## 环境与节点

主控需要 Python ≥ 3.11、GNU Make、Bash、GNU timeout 和 SSH 客户端；节点需要 Linux、Python ≥ 3.10、Bash、GNU timeout。均只需普通用户权限，无 pip 包、容器、sudo 或常驻服务安装。首次连接前须在用户终端建立免密 SSH 和可信 known_hosts；程序启用严格主机密钥检查。

[nodes.conf](nodes.conf) 中的原生字段如下。旧 `[cluster]` 的容器字段只供历史入口使用，新入口不读取容器资源、UID 或镜像设置。

| 节点 | CPU 上限 | priority | weight | work_dir |
| --- | ---: | ---: | ---: | --- |
| public-Super-Server | 128 | 100 | 4 | `scheduler/runtime` |
| preston | 32 | 100 | 1 | `~/isla-runner/scheduler/runtime` |
| public-4090server | 48 | 50 | 1 | `~/isla-runner/scheduler/runtime` |

`work_dir` 优先于旧的 `remote_runtime`。本机相对路径以仓库根目录为基准，远端相对路径与 `~/` 在 SSH 用户主目录展开。本机 `work_dir` 仅保存节点管理锁等元数据，不作为任务 cwd；已有旧缓存与旧 attempt 保留，新的本地任务不使用它们。CPU 容量再受节点在线 CPU 和 affinity 限制。可选 `external_cores` 静态扣除其他工作负载占用；本版本不使用瞬时 CPU busy 或 loadavg 推算动态空闲。

任务通过 Make 的 `THREADS=32` 声明预计线程数；Make 将其传给 isarch 的 `-T 32`，`native/inputs.py` 自动提取为 `cores=32`。直接 argv 也支持 `--threads 32` 和 `--threads=32`。调度器按这份声明预约，不修改任务参数；声明是资源估计，不是线程数硬限制，`-j208` 只控制 Make 同时启动的 recipe 数。

先选最高优先级的可接单节点，同级按平滑加权轮询分配。本机与 preston 同级为 4:1；该级都不能接单时才使用 4090。接单门槛按每个任务动态计算：

```text
free_cores = cpus - external - reserved
threshold = max(1, cores // 2)
接单条件：节点 online，cores <= cpus，free_cores >= threshold
接单后：reserved += cores
```

| 声明线程数 cores | 动态门槛 threshold |
| ---: | ---: |
| 16 | 8 |
| 32 | 16 |
| 64 | 32 |

`//` 向下取整，1 线程和 3 线程任务的门槛均为 1。恰好达到门槛就允许派单，接单后仍预约完整 cores，可出现有限超售。例如 48 核节点可以接两个 T32 任务，预约余量显示为 -16。同一节点剩余 16 核时，可以接 T16 或 T32，不能接 T64；T64 还须满足节点总容量至少 64 核。

剩余核心低于本任务门槛时溢出给其他可接单节点；全部无法接单时 `reserve` 返回 None，任务保持 WAITING，任意任务完成释放容量后继续派发。`stop_free_cores` 已从 nodes.conf 移除，不再必填；旧配置中残留的同名字段只作兼容保留，不参与调度。

两种后端不能同时把同一组机器当作全部空闲。启用原生入口前应确认旧 HTCondor 无活动任务。

## Make 与输入

入口启动本轮 controller，再在用户 Makefile 后附加一个含 `-include scheduler/integration/solve.mk` 的 Makefile。只有 `solve-%` 使用适配 shell；编译和 `solve-pre`、`solve-kill` 等管理目标使用原 shell。原始 `mkdir`、`flock` 和 `[n/TOTAL]` 在主控执行；进度表示 recipe 已启动，不表示远端完成。proxy 一直等待真实退出证据，把任务退出码交给 Make；GNU Make 自身遇到任务失败通常返回 2。

适配器使用标准库 `shlex` 检查当前 recipe 的有限语法，再由 Bash 执行原文本并在 `exec` 函数处转交真实 argv。它接受当前计数器、进度、`RUST_BACKTRACE=1 exec python3 scripts/solve_process.py run` 和日志重定向结构。改成直接 isarch、`command exec`、其他监督器、动态 shell 参数或额外本地命令会被拒绝；显式 `SHELL`、`.SHELLFLAGS` 覆盖和 `--eval` 也会被拒绝。它不是通用 Bash 解析器。

排队时只识别原 cwd、监督命令和 `-T`，不读取输入内容或创建缓存。选中远端节点后，才从真实 argv 自动获取 isarch、IR、ISA 配置、workaround、编码片段配置、样本输入与输出参数。支持长参数的 `--key=value`，保留路径中的空格。少量 TOML 配置目录自动镜像；workaround 的 `file="...sail"` 是 IR 源位置，不会上传整个模型源码。已核实的 TOML 输出字段只建立输出位置。工作区外文件映射到 `_external/`；输出须位于 attempt 内。未知文件接口仍需增加角色识别，目录输入与未确认的配置 include 语义不在当前支持范围内。

远端输入按设备、inode、size、mtime、ctime 检查；变化时复制并校验内容，发布不可变对象。源工作文件不硬链接进缓存。本轮首次准备远端任务时发现的文件版本固定，后续运行感知修改。本地直接读取原文件，行为与原生 Make 相同。各节点以文件锁合并并发传输，只接收缺失对象；小 TOML 改动不会重传 IR 或二进制。这里的增量单位是文件版本，未实现同一大文件内部的 rsync 差量。

远端动态 ELF 的 loader 与 `ldd` 依赖会自动缓存，并在原 timeout 内通过缓存 loader 启动，不依赖远端绝对 Z3 RPATH。缓存 ELF 本地执行已验证；真实 isarch 在远端的 glibc 兼容性仍待验收。额外工具、动态打开的隐藏依赖不能由 `ldd` 自动证明完整。

## 状态、日志和结果

每轮入口在终端打印 `scheduler/runtime/native/runs/<run-id>/`。其中 `status.json` 为资源与状态摘要，`state.sqlite` 保存任务状态与状态事件，`jobs/<job-id>/` 保存参数和退出证据。本地额外保存启动/完成元数据，不复制产物或日志；远端另保存实时片段、最终 `tail.log` 与产物索引。

远端任务的数据位于 `<work_dir>/native/`：

```text
cache/<workspace-id>/objects/                 # 不可变共享对象
cache/<workspace-id>/generations/<id>/READY    # 已发布 generation
jobs/<job-id>/attempt-<id>/work/root/isla/     # 独立执行目录
jobs/<job-id>/attempt-<id>/work/stdout.log     # 完整日志
jobs/<job-id>/attempt-<id>/result.json         # 退出证据、索引和尾部
```

本地任务的 `output/log/<clause>.log` 是完整原生日志，直接实时写入，没有调度器首部、截断或尾部重放。本地结果已在原 cwd，无需 fetch；其调度证据见 run/jobs 下的 `result.json`。

远端任务在主控原有的 `output/log/<clause>.log` 接收最多 1 MiB 实时片段（每任务约 4 KiB/s）及最终 64 KiB 尾部，并标明两者可能重叠。它不是完整远端日志。完整 JSON、trace、样本和 SMT dump 留在节点；自动回传监督器 process JSON、状态行、退出码及产物路径/大小。主控不伪造本地监督器 PID，不给大 JSON 写空占位文件。日志配额按任务控制，当前没有额外的全 run 带宽整形。

```bash
python3 scheduler/scripts/manage_data.py --node preston list
python3 scheduler/scripts/manage_data.py --node preston --job-id <job-id> summary
python3 scheduler/scripts/manage_data.py --node preston --job-id <job-id> fetch
python3 scheduler/scripts/manage_data.py --node preston --job-id <job-id> delete
```

`fetch` 默认保存到 `scheduler/runtime/native/retrieved/`，也可指定 `--destination <archive.tar.gz>`。归档保留完整结果；其中输入符号链接引用节点缓存，不是可搬移的输入包。取数不会重新求解，删除拒绝未确认结束的 attempt。

Ctrl-C/TERM 只取消本轮任务。本地 proxy 直接启动原监督器，继承原日志文件与完整环境；收到取消或检测到主控退出时，把 TERM 交给原监督器清理 timeout 和后代。收取本地证据时按本次 clause 和 supervisor PID 精确读取 process JSON，保留历史状态行，不将同目录其他任务或旧结果计入完成证据。远端仍由 worker 监督，控制通道 EOF 或 60 秒租约失效也会触发清理。断线时短暂重连读取最终证据；无法确认则记录 UNKNOWN、返回 125、保留预约并隔离节点，不自动重跑。下一轮发现旧 attempt 未确认结束会拒绝该节点，须先查看节点 result.json 与进程证据。SQLite 用于留存与核查，目前不提供主控崩溃后的自动续跑。

同一 cwd 有 Make 运行锁；每节点还持有主控独占锁，防止多个 controller 重复计算同一份容量。因此当前不同工作树也不能同时共享同一节点。此限制不影响单轮多机调度。原生模式不会申请这些锁。

## 验证与历史入口

```bash
python3 -m unittest discover -s scheduler/tests -v
```

测试使用 `scheduler/runtime/` 下的原生 Makefile 副本与短任务，覆盖两种模式、本地零缓存/零 stage/零 SSH、原地完整日志和产物、原环境、QoS、远端增量缓存、SSH 协议、退出码、租约、取消、取数及 ELF 运行库。实际验证范围和日志见 [RESULTS.md](RESULTS.md)，实现状态见 [NATIVE_STATUS.md](NATIVE_STATUS.md)。

旧容器部署与提交工具保留，历史记录见 [PLAN.md](PLAN.md)、[RESEARCH.md](RESEARCH.md)。读取旧 Condor 数据须显式使用 `manage_data.py --backend condor ...`；默认取数后端已经改为 native。旧验证不能作为原生三节点验收。
