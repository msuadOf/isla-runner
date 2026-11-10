# HTCondor 调研与适配依据

本方案用本机承担主控、提交和计算职责，两个远端承担计算职责。三机采用相同的 Ubuntu 22.04 容器运行 HTCondor；任务的完整结果先保存在执行节点，再按选项回传。

**2026-11-10 新增 preston，配置总容量 208 CPU；尚未完成三节点部署与调度验收。** preston 数据由用户在宿主机实测后提供，本轮未重测网络。下表保留此前会话本机检查及受限预检的适用范围，不把主机可达或单元测试通过当作 HTCondor 集群通过。

## 证据范围

| 项目 | 信息与来源 | 本次核实状态 |
| --- | --- | --- |
| 本机 | `public-Super-Server`、192.168.104.13、128 vCPUs | hostname、128 CPU 已本地核实；IP 按用户提供值配置 |
| 本机系统 | Ubuntu 26.04.1 LTS，x86_64 | `/etc/os-release`、Python 探针已核实 |
| 主控工具 | Python 3.13.9；存在 Docker 客户端 | 已核实；Docker API 访问被拒绝，不能推断 daemon 是否正常 |
| 远端 | `public-4090server`、192.168.221.161、Ubuntu 22.04、48 vCPUs、2 × RTX 4090 | 用户提供；SSH 被会话沙箱阻止，未在远端复核 |
| 新增远端 | `preston`、192.168.103.89、Ubuntu 22.04 LTS、Linux 6.2.0-39-generic、32 vCPUs、无独立 GPU | 用户提供的宿主机实测，`nproc = 32` |
| preston 用户与服务 | `baiyifan`，UID/GID 1017/1017，免密 sudo 返回 `SUDO_OK`；Docker 29.8.1，服务 active | 用户实测；容器内仍使用主控配置的任务 UID/GID 1005/1005 |
| SSH、sudo | 用户已配置免密 SSH、免密 sudo | 宿主机授权与会话沙箱不同；当前会话仍无法使用 |
| 4090 下发带宽 | 500–700 Mbps，约 60–80 MB/s | 用户实测，本次未重测 |
| 4090 回传带宽 | 约 21 Mbps，约 2.5 MB/s | 用户实测，本次未重测 |
| 4090 延迟 | 约 0.45 ms | 用户实测，本次未重测 |
| preston 下发带宽 | 本机 → 192.168.103.89，iperf3 约 800 Mbps，约 100 MB/s | 用户实测，本次未重测 |
| preston 回传带宽 | 192.168.103.89 → 本机，iperf3 约 780–800 Mbps，约 100 MB/s | 用户实测，对称千兆链路，无 4090 节点 21 Mbps 回传瓶颈 |
| preston 延迟 | 约 0.55 ms | 用户实测，本次未重测 |
| HTCondor 包 | 候选为 25.x 系列，Ubuntu jammy 仓库 | 官网及包源不可访问；未核实当前版本、维护状态、密钥或包可用性 |

具体错误见 [预检记录](evidence/preflight.json)，验证摘要见 [RESULTS.md](RESULTS.md)。本文件不把官网链接当成已经在线读过的证据。

## 1. 架构和任务如何运行

HTCondor 把任务提交、资源匹配和实际执行分开。当前拓扑为一个主控兼计算节点（128 CPU）与两个计算节点（4090 节点 48 CPU、preston 32 CPU），组成一个 pool，即一个由共同主控管理的计算集群。

| 角色 | 守护进程 | 职责 | 本方案位置 |
| --- | --- | --- | --- |
| Central Manager，主控 | `condor_collector`、`condor_negotiator` | 收集机器和队列信息，匹配任务与空闲资源 | 本机 |
| Access Point，提交节点 | `condor_schedd`，以及每个运行任务的 `condor_shadow` | 保存队列，协调执行和文件传输，保存任务事件 | 本机 |
| Execution Point，执行节点 | `condor_startd`，以及任务对应的 `condor_starter` | 发布可用资源，启动和管理任务 | 三机 |
| 每机服务管理 | `condor_master`、`condor_shared_port` | 管理守护进程，共用接入端口 | 三机 |

节点通过 ClassAd 发布资源。ClassAd 是一组名称和值，例如 CPU 数、内存和 GPU 数。任务也声明需求，例如 `request_cpus = 8`。匹配器只把任务交给满足需求的节点。

本方案为每机建立一个可分割的 slot。一个 slot 是调度器管理的一份资源；接到任务后，HTCondor 从它分出任务所需的 CPU 和内存。128 + 48 + 32 = **208 个逻辑 CPU** 是配置容量，不代表各机每核性能相同，也不保证任意任务有 208 核的加速比。preston 是纯 CPU 节点；4090 节点虽有两张硬件 GPU，当前也未启用 GPU 调度。

### 工作目录与存储选择

`nodes.conf` 每个节点使用 `work_dir` 指定独立工作目录，支持绝对路径、`~/...` 及相对路径。local 相对路径以 isla-runner 根目录为基准，remote 在 SSH 用户环境中展开，通常以其主目录为基准。缺省值分别是 `scheduler/runtime` 与 `~/isla-runner/scheduler/runtime`；旧 `remote_runtime` 字段仍可用，同时存在时优先使用 `work_dir`。

取消旧的 `/scheduler/runtime` 后缀限制，节点可按磁盘容量选择 `/data1/baiyifan/condor-runtime` 或 `/home/baiyifan/condor-runtime`。仍要求专用目录并校验危险路径，规则见 [PLAN.md](PLAN.md)。目标路径在各节点解析后用于目录初始化和 Docker 挂载，例如 `<work_dir>/data:/srv/isla`。容器内路径保持固定，主控的提交包、取回归档及离线渲染使用主控配置的目录。管理和退役节点记录保留在仓库内 `scheduler/runtime/`，供后续部署比较实际位置；单纯从旧字段改为等价的 `work_dir` 无需迁移，实际更换已有节点目录须先迁移数据。

`request_cpus` 决定资源预留，不能自动改变 Isla 的线程参数。提交多线程程序时，仍须传入程序自身的线程选项。包装器只为常见数值库设置线程环境变量。

主控是单点。主控停机后不能正常提交和匹配新任务；已经运行的任务是否继续，取决于提交节点连接、租约和恢复情况。这里没有实现高可用，也没有把“HTCondor 可以恢复连接”当成整机故障无损保证。

## 2. 认证、授权和链路保护

认证回答“连接方是谁”；授权回答“这个身份允许做什么”。两者都需要配置。IP 白名单不能替代认证。

| 机制 | 工作方式 | 适合场景与限制 |
| --- | --- | --- |
| `FS` | 用本地文件系统权限确认 Unix 用户 | 供同一容器内的提交和管理命令使用；不要求各机共享 `/tmp` |
| `PASSWORD` | 两端用共同持有的 pool password 认证 | 小型集群部署简单；知道共享口令的一方拥有共同的 daemon 身份，难以逐节点撤销 |
| `IDTOKENS` | 客户端持有签名 token，服务端按签名、身份和授权验证 | 适合更多节点、身份区分、限定权限和有效期；须维护签名密钥与 token 发放 |

IDTOKENS 的 token 是 bearer credential：拿到它就可能获得其权限。它不等于用户的 SSH 密钥，也不应放进代码仓库。签名密钥通常由 `SEC_PASSWORD_DIRECTORY` 管理；它与本方案的 `SEC_PASSWORD_FILE` 用途不同。撤销签名密钥会影响使用该密钥签发的 token；不能把删除一个节点配置理解为已撤销所有已发凭据。

本次实现采用 **PASSWORD 进行跨机认证，FS 进行容器内认证**。`condor_store_cred` 在主控生成口令文件，部署脚本通过 SSH 标准输入分发。口令不出现在脚本日志、配置模板或提交描述中。生成工具内部短暂通过参数接收口令，主机 root 仍有能力读取进程及凭据。

跨机权限授予 `condor_pool@*` 这一认证身份；本地 daemon 也可通过 FS 以 condor 账户通信。本地管理权限只授予 root；本地提交权限授予配置中的单一任务用户。`SEC_DEFAULT_AUTHENTICATION`、`SEC_DEFAULT_ENCRYPTION` 和 `SEC_DEFAULT_INTEGRITY` 均设为 `REQUIRED`。最终仍须用实际安装版本验证权限和有效配置。

口令保存在各节点 `<work_dir>/auth/`，目录为 root 独占。容器只读挂载口令文件，文件所有者按镜像内 condor UID 设置，供降权后的守护进程读取。缺省运行目录被 `.gitignore` 排除；自定义目录应选择仓库外专用目录，仓库内新位置须自行确保不提交凭据与运行数据。

此实现面向一个可信使用者。所有任务使用同一容器账户，能够访问同账户的持久结果。Docker 管理权限本身也接近宿主机 root 权限。若扩为互不信任的多用户服务，须重新设计账户隔离、授权和数据权限。

## 3. 端口与通信方向

本方案要求三机内网双向可达，不依赖共享文件系统，也不依赖公网 NAT 穿透。

| 通信 | 端口/协议 | 用途 |
| --- | --- | --- |
| 主控到各节点 | TCP 22 | SSH 部署、镜像下发、按需取数 |
| 三机之间 | TCP 9618 | Collector、Shared Port 和路由到其他守护进程的连接 |
| 三机之间 | TCP 9700–9799 | 限定范围的传输连接及未复用 Shared Port 的监听；是否实际使用须实测 |
| 主控到外部 | HTTPS 443、DNS；包源可能使用其他已配置协议 | 拉取 Ubuntu 镜像、签名密钥、软件包 |
| 远端到外部 | 安装 Docker 所需的系统包源 | 已有可用 Docker 时，HTCondor 镜像由本机经 SSH 下发 |

`USE_SHARED_PORT = True` 让多个 HTCondor 进程共用监听端口。主控额外设置 `COLLECTOR_USES_SHARED_PORT = True`，避免 Collector 和 Shared Port 各自占用 9618。开启 TCP 更新并关闭 UDP command socket 后，本方案不要求放行 UDP 9618。

**不能仅凭开启 Shared Port 就断言只需一个端口。** 文件传输、插件和版本默认行为仍须核实。因此模板同时限制 `LOWPORT/HIGHPORT` 与 `IN_LOWPORT/IN_HIGHPORT`，并在方案中预留 9700–9799。范围是否足够，取决于任务并发和实际监听方式；三机九任务测试不是大并发容量测试。

防火墙应只允许这三台机器互访对应端口，以及已有 SSH 管理来源。部署脚本不清空或重写宿主机防火墙。若现有策略阻断端口，`condor_status` 验证会失败，须按现有防火墙管理方式放行。

容器采用 host 网络，配置中固定发布内网地址。节点名写入容器 hosts，机器广告使用明确的 `FULL_HOSTNAME` 和 `IslaNode`。没有部署 CCB、VPN、反向隧道或公网转发。

## 4. Ubuntu 26.04 与 22.04 的适配

此前本机检查确认为 Ubuntu 26.04；4090 节点 22.04 尚未在该次预检通过 SSH 复核，新增 preston 的 22.04 来自用户本轮实测。不能推断 HTCondor 当前提供原生 resolute 包，也不能把 jammy 源直接加入 26.04 宿主机。

因此，HTCondor 用户空间统一放在 **Ubuntu 22.04 容器** 中。Docker Engine 使用宿主机的安装方式；HTCondor、Python 3.10 和其依赖在容器内安装。镜像只在本机构建一次，再经 `docker save` / SSH / `docker load` 发给远端。三节点使用相同 image ID 和 HTCondor 版本。

这解决了 HTCondor 自身依赖的一致性，仍有以下待验证边界：

1. 本机 Docker daemon 的状态、Ubuntu 26.04 上的 Engine 可用性与内核行为尚未验证。
2. `nodes.conf` 中 25.x jammy 包源及 `HTCondor-25.0-Key` 是候选配置，尚未下载核实。
3. 构建过程要求 HTTPS 下载成功、APT 签名验证成功、存在 `htcondor` 包。
4. 构建后检查 `condor_version` 必须满足 `version_prefix = "25."`。实际版本进入部署证据。
5. 模板的实际解析、认证、Shared Port 和守护进程路径须在该镜像内验证。本地文本渲染通过不等于 Condor 配置通过。

若该包源不再提供候选系列，应先按官方支持表更新 `nodes.conf` 中的源、密钥和版本要求。脚本会在新镜像构建失败时停止，已有 HTCondor 容器仍保持运行；不会自动降级、关闭签名验证或混用宿主机发行版。

### 任务二进制与运行库

本机编译的 ELF 程序可能依赖较新的 glibc、libstdc++ 或私有 Z3。直接复制可执行文件到 22.04 用户空间，可能报 `GLIBC_x.y not found`。

`submit_job.py --bundle-libs` 会用本机 `ldd` 收集启动依赖，连同 glibc loader 一起下发。任务通过这个 loader 启动。普通 ELF 的这一执行路径已用本机 `getconf` 验证；**尚未在远端执行，也没有用 Isla 二进制验收**。

该选项不能打包 `dlopen()` 才加载的库、外部命令、解释器模块、模型和配置。它也不能完全模拟内核直接加载程序的行为。依赖 `/proc/self/exe` 的多调用程序可能识别到 loader；本次 Ubuntu 26.04 的 Rust coreutils `printf` 就出现此问题。旧式 RPATH、运行时插件和子进程也需逐应用检查。已知兼容 Ubuntu 22.04 的静态程序或在该用户空间构建的程序可直接分发，不必使用此选项。

脚本输入按普通文件复制。用户自行提供的 Python 程序须兼容容器内 Python 3.10；本机的 Python 3.13 不随脚本自动下发。

### GPU

远端的两张 RTX 4090 是用户提供的硬件信息。当前配置 `enable_gpus = false`，只启用 CPU 调度。启用 GPU 前须确认宿主机驱动、NVIDIA Container Toolkit 和 `docker --gpus all` 正常。

将对应节点改为 `enable_gpus = true` 后，部署脚本向容器传入 GPU，并启用 HTCondor GPU 发现。提交通过 `--gpus N` 声明需求。GPU 发现、CUDA 工作负载及设备隔离均未实测；这里不把两张硬件卡计为已可调度 GPU。

## 5. 按节点带宽选择数据策略

4090 节点的输入和镜像下发较快，完整结果回传较慢。preston 的下发与回传均接近 800 Mbps，可更快取回完整结果。集群仍默认只回传摘要，需要完整数据时显式选择。

按用户给出的十进制近似速率估算，不计压缩与协议开销：

| 内容 | 方向 | 纯传输耗时估算 |
| --- | --- | --- |
| 10 GB 输入 | 本机 → 4090 节点，60–80 MB/s | 约 125–167 秒 |
| 10 GB 结果 | 4090 节点 → 本机，2.5 MB/s | 约 4,000 秒，即 67 分钟 |
| 100 GB 结果 | 4090 节点 → 本机，2.5 MB/s | 约 11 小时 |
| 1 MB 摘要 | 4090 节点 → 本机，2.5 MB/s | 约 0.4 秒 |
| 10 GB 输入或结果 | 本机 ↔ preston，约 100 MB/s | 约 100 秒 |

低延迟利于调度控制消息，无法补偿大数据回传的吞吐限制。4090 节点多任务同时完整回传时，约 21 Mbps 是该节点的共享瓶颈，不是每个任务各有 21 Mbps；不应把这个限制套用到 preston。

包装器把任务输入和输出放到执行节点的持久目录。默认只回传用户指定的摘要文件、结束状态和日志尾部。`--retrieve-data` 才创建完整归档；`--no-retrieve` 把 stdout/stderr 指向 `/dev/null`，并明确指定空的 `transfer_output_files`，避免 Condor 自动把整个 scratch 目录取回。

“不回传”指不回传任务文件。Condor 的控制消息、退出状态和提交节点事件日志仍然存在。其大小不能记为绝对零网络流量。

## 6. 参考入口与未核实项

以下是官方资料入口，供联网环境复核。**当前会话未能下载这些页面；链接和参数需结合实际安装版本检查。**

- [HTCondor 文档入口](https://htcondor.readthedocs.io/)
- [获取 HTCondor](https://htcondor.readthedocs.io/en/latest/getting-htcondor/index.html)
- [管理员手册](https://htcondor.readthedocs.io/en/latest/admin-manual/index.html)
- [安全机制](https://htcondor.readthedocs.io/en/latest/admin-manual/security.html)
- [配置宏](https://htcondor.readthedocs.io/en/latest/admin-manual/configuration-macros.html)
- [condor_submit](https://htcondor.readthedocs.io/en/latest/man-pages/condor_submit.html)
- [condor_store_cred](https://htcondor.readthedocs.io/en/latest/man-pages/condor_store_cred.html)
- [condor_token_create](https://htcondor.readthedocs.io/en/latest/man-pages/condor_token_create.html)
- [condor_off](https://htcondor.readthedocs.io/en/latest/man-pages/condor_off.html)
- [Docker host 网络](https://docs.docker.com/engine/network/drivers/host/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

后续实测应补齐：包源与支持矩阵、镜像构建、实际 `condor_config_val`、认证负例、端口监听、三节点共 208 CPU 广告、三策略九任务、真实 Isla 二进制以及必要的 GPU 测试。完成其中一项只能签收该项，不能据此把整个集群改为 PASS。
