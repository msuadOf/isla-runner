# 当前执行状态

## 2026-09-23：最终提交授权

用户已授权提交当前审核后的主仓库暂存集合。提交范围包含 submodule gitlink、初始化入口、两个外层 harness、根 archives 证据及 agents 持久文档；不包含 Isla/Sail-RISC-V 工作区内未提交代码，也不 push。下文各节的“未 commit”表述记录对应执行步骤当时的状态。

## 2026-09-23：submodule 初始化入口适配

根 init.sh、Makefile、README 已改为以父仓库 gitlink 初始化 Isla/Sail-RISC-V。现有 checkout 只核对 remote/commit/HEAD：HEAD 匹配时无论 dirty 与否均原样保留并告警，HEAD 不同或路径非 Git worktree 时停止；仅缺失/空路径会执行 submodule update。新增 `--submodules-only` 供 Makefile 和已有 clone 使用。

Makefile 不再自行 clone Sail-RISC-V/Isla，不再自动 apply 历史 patch，distclean 不再 rm 子模块源码目录。其他独立仓库初始化逻辑保持原样。

验证完成：`bash -n`、ShellCheck、help、Makefile dry-run、差异空白检查通过；当前真实 dirty 子仓库执行 `--submodules-only` 成功并仅告警，操作前后两个仓库的 HEAD、staged/unstaged diff 和状态哈希完全相同。隔离仓库验证匹配 checkout、dirty 文件保留、HEAD 不匹配拒绝、gitlink 缺失拒绝均符合预期。缺失子模块的实际 clone 本轮未执行；它直接使用标准 `git submodule update --init`。

2026-09-23 联网只读核验：Isla `dev-isarch-runall-ext` 远端分支精确指向 `97390b0a5f05896a3255af72939e314eb5feaab5`；Sail-RISC-V `isla/symbol-excution_6_14` 精确指向 `5f1a0de0d8219537f27680d325b7adcac5db3478`。因此 `.gitmodules` URL 当前可发现这两个 gitlink commit。不 commit/push。

## 2026-09-23：剩余文档、证据与 Ara 外层源码

用户批准分类整理并暂存，不 commit、不删除。本批次保存 Ara 成套目录 253 文件、93,109,366 字节，以及 XiangShan 草稿复现目录 37 文件、58,074 字节，分别至根 archives 的 2026-09-23 批次。复制时逐文件核对哈希，并在整批完成后重检源集合及源哈希；清单记录源/目标与大小、SHA-256。随后只给原 status 加归档入口，档案内 status 保持复制时原文。

源 snapshot 和 issue1/2/3 已精确忽略，源码及证据完整副本进入根档案；原字节未删除。三个主题的持久化文档、findings 的既有 151 行有效历史记录及整理阅读提示纳入暂存。阶段性结论和纠正均保留，不冒充重新验证。

Ara pipeline.py 原样纳入主仓库，新增 README 说明依赖、默认非官方 VLEN128 配置与输出覆盖风险。CLI --help 及 5 项纯函数冒烟通过，不代表完整功能或 RTL 验证；未修改执行逻辑。单个最大归档文件 16,501,068 字节，其余完整集合均低于 100 MiB。原上游 Ara 和两个已关联 submodule 不做写操作。

建议提交分组：Ara harness 源码与说明；根运行证据与忽略规则；持久化知识文档。当前只是暂存集合，不自动拆分或创建 commit。

最终核对：主仓库已无未跟踪文件，暂存区外仅 Isla/Sail-RISC-V 的既有 dirty 状态；两者 HEAD、两层差异和状态摘要，以及 Ara pipeline.py SHA-256 均与本批次操作前一致。`git diff --cached --check` 提示档案原始汇编/日志中的尾随空白，为保持证据哈希未格式化；不将其报告为全绿。

## 2026-09-23：长期不提交路径的忽略规则

按用户要求补充根 `.gitignore`：本机 `.vscode/settings.json`（内容仅为绝对 CMake 路径）、Python 缓存、根实时 trace、Ara 独立上游 checkout、Ara work/work-* 输出与实时 trace。这些路径不作为主仓库源码提交，原文件全部保留；有保全价值的实验结果仍可另行选择复制到 archives，不表示可删除原输出。

不忽略 `ara/pipeline.py`、agents 持久文档及待归档复现证据，不添加全局 `*.log`/`*.json`/`*.elf` 规则。Isla/Sail-RISC-V 子仓库文件及索引不动，不配置 submodule ignore=dirty。已跟踪修改不靠 gitignore 隐藏。此次只暂存忽略规则与本状态记录，不 commit。

## 2026-09-22：登记两个 submodule

用户确认使用 submodule。本批次新增并暂存根 `.gitmodules`，移除 Isla/Sail-RISC-V 的根忽略规则，暂存两个 `160000` gitlink：

- `isla`：`97390b0a5f05896a3255af72939e314eb5feaab5`，URL `https://github.com/ariscv/isla.git`。
- `sail-riscv`：`5f1a0de0d8219537f27680d325b7adcac5db3478`，URL `https://github.com/msuadOf/sail-riscv.git`。

未创建 commit/push；未执行子仓库 checkout/reset/pull、索引更新或 Git 元数据迁移。两个目录保留原独立 checkout，现有未提交修改不包含在 gitlink 中，根状态显示 dirty 属于正常情况。远端是否可取得这些 commit 尚未联网核验。

本批次仅登记版本关联，未修改 `init.sh`/Makefile：旧初始化入口仍不能视为按 gitlink 恢复版本的入口，暂勿用其更新这两个目录。发布主仓库提交后，新 clone 可使用 `git clone --recurse-submodules <主仓库URL>`。已有干净 clone 可用 `git submodule update --init isla sail-riscv`；当前脏工作区不要执行更新。当前工作树已经能由 gitlink 识别两个子模块；没有执行更新命令。

后续若需统一旧初始化/构建入口，再按 plan 第 11 节实施；以下 2026-09-21 记录为上一批次历史状态。

## 2026-09-21：仅整理 difftest-xiangshan 外层

用户已同意外层代码由主仓库管理、上游香山独立管理。本批次精确解除外层忽略，保留工具、测试替身、smoke 与 PoC 源码，复制输入及结果到根 archives，并记录完整原始数据的本地归档。

不改变外层 Python/Bash/汇编代码，不改变运行路径，不操作内层 XiangShan、Isla、Sail-RISC-V 的代码与索引。Isla/Sail-RISC-V submodule 关联及其余仓库整理未在本批次执行。

## 执行结果

- 根忽略规则不再屏蔽整个 harness；内层上游、inputs/work、PoC ELF、旧模拟器与缓存仍精确忽略。
- 外层源码、测试 fixture（含文本 `.so`）、smoke、3 份 PoC 汇编原样纳入主仓库暂存；README 说明边界。没有 commit、push 或删除源数据。
- 根 `archives/xiangshan/2026-09-21-harness/` 保存 67 份证据，共 114,293,787 字节（约 109 MiB），另附 README 和 manifest。每份副本均与源哈希校验一致；最大单个证据文件 9,246,839 字节。
- 完整 work 与旧模拟器的 tar 为 959,979,520 字节（约 916 MiB），位于被忽略的 `archives/_raw/`，已记录 SHA-256；只在本机保全，不是远端备份。
- tar 创建成功；比对时仅 monitor.log 的大小和 mtime 不同（日志仍每分钟追加），其余成员未报告差异。另存较新 monitor.log 并校验。本次为明确标注的非原子归档，不宣称同一时刻完整快照，不停止用户进程。
- 四个 Bash 入口语法检查通过。单测 14 项中 10 项通过、4 项报错：测试 mock run，但实现调用 Popen。原有代码/测试没有修复，当前不能宣称测试全绿；未重跑 RTL。
- PoC 原 linker script 与旧 ELF/当前源码对应关系未核实，已在归档 README 标注，不编造可重建保证。
- Isla、Sail-RISC-V、内层 XiangShan 的 HEAD、staged/unstaged diff 和状态摘要与操作前一致；外层代码、测试、smoke、PoC 哈希一致。基线见 `xiangshan-boundary-baseline.txt`。
- 本批次选择性暂存；`agents/findings.md` 仅暂存新增 7 行，既有 151 行用户修改仍未暂存。其他未跟踪议题、Ara、根 trace 等未纳入。

## 后续边界

用户审核暂存集合后自行决定提交；测试修复、停写后一致快照、大档案远端保管及其他仓库整理均未执行。不要对整个工作区直接 `git add .`。
