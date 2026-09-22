# 整个工作区提交前的分类与行动计划（待审核）

执行增补（2026-09-21）：用户随后批准仅整理 `difftest-xiangshan/` 外层的批次。该批次的实际变更、验证与未完成项以同目录 [status.md](status.md) 为准；下文“只读/尚未执行”描述的是原审核轮次，不代表本批次当前状态。其他项目整理及 submodule 关联仍未执行。

审计日期：2026-09-20。工作区：`/home/baiyifan/workplace-local/isla-runner`。

审核修订：2026-09-21。以下文件数量、体积和差异是原审计快照，执行前应重新核对。本次仅修订计划，不表示已经执行其中的整理或提交。

## 0. 最新约束与执行边界

- 用户已明确：Isla 和 Sail-RISC-V 的代码改动不动，文档等文件可以整理。此约束同样适用于这两个仓库的额外 worktree。
- 这两个项目的源码、测试、构建逻辑、现有 IR/运行输入路径、HEAD、分支及源码暂存状态保持原样；不格式化、不提交源码、不回退、不合并实验分支。
- 版本关联采用主仓库的两个 submodule gitlink，固定第 11 节列出的现有 HEAD；不把未提交代码算进这对版本，不再询问是否先提交源码。
- 为同时保留现有 HEAD 和新整理的知识，本次优先复制这两个项目的文档到根 `agents/project-memory/<项目>/<原相对路径>`，运行证据到根 `archives/`。原文保留，新增副本附来源、源 HEAD、内容哈希及是否含未提交文档变更。复制后的内容是冻结快照，后续同步须显式进行。
- 本次不在这两个子仓库创建 docs commit，避免改变关联 SHA 或把现有 staged 源码带入文档提交。允许整理文档不等于允许整仓 `git commit`。
- 全工作区整理与版本关联分成独立批次；第 3 节其他项目的源码修复、工具改造及实验提交是后续建议，不作为完成本次关联的前置条件。本轮“继续”落实为修订审核文档，不执行这些建议。

本轮只读取 Git 状态、索引、差异、文件内容、目录大小和已有记录；唯一新增文件是本计划。未整理目录、修改源码或忽略规则，未删除、暂存、取消暂存、commit、push、fetch，也未运行会生成产物的构建/测试。本文件中的动作均是审核后的待办。

根 `AGENTS.md` 要求计划先交用户审核。本轮“只读、写一个计划文档”的明确要求优先，因此未追加 `agents/findings.md` 或新建 `status.md`；需要同步的发现集中记录在本文件，后续执行时再更新索引与 findings。

## 1. 建议审核的总体方案

1. **独立项目源码和测试归所属 Git 仓库**：归属不等于本次执行提交；Isla、Sail-RISC-V 及其 worktree 的源码提交全部排除。其他项目按明确批准的批次处理，不能用根目录一次 `git add .` 代替。
2. **工作区编排代码归主仓库**：现有 `difftest-xiangshan/`、`ara/` 外层没有自己的 `.git`，建议将其 harness 脚本作为主仓库源码提交；里面的 XiangShan/Ara 上游源码仍是独立仓库。此次不默认新建两个 harness 仓库或转换全部依赖为 submodule。
3. **运行档案统一放根目录 `archives/`**：报告、结果清单、输入、复现程序、关键日志和历史版本脚本按实验批次存放。项目内的可执行回归测试及其固定 fixture 留在项目。
4. **AI 文档保留并 commit**：`agents/`、分析报告、计划、决策、交接、人工/agent 提示及工具 memory 都保留。对隐藏目录逐项分类，不能把 `.omo/`、`.sisyphus/`、`.qoder/`、`.serena/` 一概当缓存。
5. **临时产物默认忽略、暂留磁盘**：只有确认可重建或已有校验一致的存档后才列入删除清单；本计划不以“让 status 干净”为由要求删除。
6. **worktree 独立保全**：本次以只读清单、分层 patch 和未跟踪文件副本保全，不创建源码提交，不自动合并或删除 worktree。

最先要解决的提交风险：difftest 暂存区混入大日志；`runner.py` 工作区有绕过比较的调试块；两个 harness 尚未正确纳入版本控制；隐藏目录内有未提交知识和实验源码；依赖版本尚未形成可复现的完整清单。

## 2. 真实仓库边界与当前状态

下表的 revision、ahead/behind 只以本地 Git 数据为准，未联网确认远端。

| 路径 | Git 边界 / 当前 HEAD | 当前修改与建议 |
| --- | --- | --- |
| `./` | 主仓库，`master`，`e3920b0` | `agents/findings.md` 修改，3 个新议题目录、`ara/`、根 trace 未跟踪；提交编排、知识、统一档案与依赖清单 |
| `isla/` | 独立仓库，`dev-isarch-runall-ext`，`97390b0` | 16 个已跟踪文件未暂存修改；新增 SMT 测试、validation 档案和 2 个小日志 |
| `sail/` | 独立仓库，detached `446fb477` | 工作区干净；无需人为制造提交，只固定版本 |
| `sail-riscv/` | 独立仓库，`isla/symbol-excution_6_14`，`5f1a0de0` | 3 个 V 扩展文件已暂存，工作区无额外差异 |
| `assembly-gen/` | 独立仓库，`dev`，`90d7855` | 主工作树只有 `.codex`、`1.txt` 未跟踪；本地比 `origin/dev` 领先 1 个已有提交 |
| `difftest/` | 独立仓库，`dev`，`a82afd8` | 29 个暂存变更，另有未暂存修改与运行目录；必须拆分 |
| `difftest-xiangshan/` | **不是独立仓库** | 根 `.gitignore` 整目录忽略，harness 源码也没进入主仓库 |
| `difftest-xiangshan/xiangshan/` | 独立上游仓库，detached `c8d7b3a5c` | 未跟踪 Scala 回归、`tests/v-rtl-regress/` 与空 `mill.dMWuA8`；已初始化的递归子模块本次检查未报告脏文件 |
| `ara/` | **不是独立仓库** | 根仓库尚未忽略内层依赖/产物；直接整体 add 有嵌套仓库和大批产物误入的风险 |
| `ara/ara/` | 独立上游仓库，`main`，`34bd3bc1` | 2 个子模块引用/状态变化、未跟踪 `hardware/build-v128/`；依赖目录另有构建补丁 |
| `difftest/difuzz-rtl/elf2hex/` | 独立仓库，`f28a310` | difftest 索引新增了指向它的 `160000` gitlink，**但没有 `.gitmodules`**；里面还有构建差异和未跟踪脚本 |

主仓库当前没有 submodule 条目。其 `.gitignore` 忽略 `isla/`、`sail/`、`sail-riscv/`、`assembly-gen/`、`difftest/` 和 `difftest-xiangshan/`。所以顶层提交既不会提交子项目修改，也不会自动记录它们的 revision。

Isla、Sail-RISC-V 的可执行版本来源只使用主仓库 gitlink，不另建重复记录这两个 SHA 的 lock。其他依赖的 URL、SHA、补丁和子模块信息先写入归档环境清单；是否增加由初始化脚本消费的 `repositories.lock.json` 是后续独立议题。当前 `init.sh` 对多数项目按分支 fetch/pull，故本次只保证这两个项目的 commit 关联，不声称整个工具链已完全锁定。

## 3. 项目源码：逐仓库提交范围

### 3.1 Isla：不要修改

保留当前源码、测试、索引、HEAD 和所有 worktree。未跟踪的 `isla-lib/tests/smt_init.rs` 也属于受保护代码。仅在根仓库登记现有 HEAD；文档/证据按第 0、4、6 节复制保全，不在 Isla 内提交。

### 3.2 Sail-RISC-V：不要修改

保留已暂存的三个 V 扩展文件及其 staged 内容，不取消暂存、不重新 add、不 commit。根仓库固定现有 HEAD，不包含这些 staged 变化。额外 worktree 同样只读保全。

第 3.4–3.7 节保留为其他项目的分类与后续建议；编号沿用原审计以便对照，不恢复用户删去的第 3.3 节。

### 3.4 difftest：先清理提交集合，再提交功能

暂存区增加约 224 万行，其中 `spike_itrace_full.log` 本体 **118,923,674 字节（约 113.4 MiB）**，已超过 GitHub 普通 Git 单文件 100 MiB 限制。现在直接 commit 后再推送，很可能因这个文件失败；应在首次提交前移出提交集合。

| 路径（相对 `difftest/`） | 分类与具体行动 |
| --- | --- |
| `difuzz-rtl/run_difftest/runner.py` | 项目功能；已暂存 WFI 检测、MEIP 注入、ISA/RTL interrupt 文件分离、ELF 复制和重放对齐；工作区另有调试块，必须分开处理 |
| `run_spike.sh` | 可复用 Spike runner，应提交；先让 Spike 路径可配置/从 PATH 获取，避免固定 `/home/baiyifan/riscv/bin/spike`；整理默认 ELF 和输出目录 |
| `.vscode/settings.json`、`difuzz-rtl/.vscode/settings.json` | 内容是相对路径 `python.analysis.extraPaths` 和测试设置，属于可共享开发配置，可以提交，不因隐藏目录就丢弃 |
| `difuzz-rtl/run_difftest/infos` | **相对符号链接**，索引类型 `120000`，目标 `../Fuzzer/infos`；是运行所需元数据入口，应保留链接，不复制整个目标目录 |
| `.gitignore` | 项目卫生配置；现在新增了 `elfs/`、`out/`、`.serena/`，还不够覆盖实际产物，且 blanket `.serena/` 会遮住 memory，需调整 |
| `.codex` | 空文件，取消此次新增的暂存并精确忽略；无需提交 |
| `difuzz-rtl/Fuzzer/results.xml`、`difuzz-rtl/run_difftest/results.xml` | Cocotb 生成的带种子、耗时、环境路径的运行报告；有证据价值则归档，之后取消新增暂存并忽略 |
| `difuzz-rtl/run_difftest/out_debug/`、`out_test_maxcycles/`、`out_timing/` | 15 个已暂存文件是 signature、results、dummy interrupt、HEX 和符号表；整批转档案或保留本地输出，不作为代码提交 |
| `make_output.log`、`spike_commit.log`、`spike_itrace.log`、`spike_itrace_full.log` | 运行日志；先保存有用途的原文/摘要，再取消新增暂存并忽略原路径 |
| `difuzz-rtl/run_difftest/out*` 其他目录 | BOOM/Rocket、probe、smoke、ret 等运行批次；统一按源目录归档，不能只忽略 `out/` 漏掉 `out_boom/` 等 |
| `difuzz-rtl/run_difftest/build_rocket/` | 生成构建目录，忽略，确认可重建后才考虑删除 |
| `tmp_probe_elfs/` | 临时 ELF；有失败复现价值的与源码/输入一同归档，其余忽略 |
| `probe_true_exec_mismatch.log` | 本次检查为 0 字节；可选删除，或精确忽略 |

**提交阻断项：工作区 `runner.py` 的成功路径提前退出。**

读取并核对的行号：[difftest/difuzz-rtl/run_difftest/runner.py:300-307](../../difftest/difuzz-rtl/run_difftest/runner.py#L300-L307)。这一段在 `ret == SUCCESS` 后复制 `rtl_sig.snapshot`，随后执行 `continue`，因此下面 [runner.py:310](../../difftest/difuzz-rtl/run_difftest/runner.py#L310) 的 WFI interrupt 同步和 [runner.py:347-348](../../difftest/difuzz-rtl/run_difftest/runner.py#L347-L348) 的 `checker.check(symbols)` 都被绕过，也跳过正常 PASS 统计。这段 **9 行只在未暂存差异中**；已暂存版本没有它。

执行阶段应先保存该调试改动的原始 patch，随后决定把签名采集做成显式诊断模式，或保留快照但不跳过正式比较；在决定前不要 `git add runner.py` 覆盖现有暂存边界。验证至少覆盖普通成功、WFI 触发中断、无中断观测、真实差异与统计条数，确保“成功执行”仍经过 oracle。

本环境没有可用 LSP 工具，本轮依据 Git diff 和带行号原文定位；这里只指出可直接从控制流确认的提交风险，不声称完成完整语义审查。

**elf2hex 必须单独处理：**

- 当前 difftest 索引新加了 gitlink `difuzz-rtl/elf2hex`，但仓库没有 `.gitmodules`，会形成无法正常初始化的依赖记录。
- `difuzz-rtl/setup.sh` 已经通过 `git clone https://github.com/sifive/elf2hex.git` 安装它。推荐维持这个依赖管理模式：取消此次 gitlink 新增暂存、精确忽略安装目录，并在安装说明/版本清单中 pin `f28a310…`。若改正式 submodule，则必须连 `.gitmodules`、版本和初始化流程一起做；两种方案不能混搭。
- 子仓库 `Makefile.in`、`aclocal.m4` 差异是 Automake 1.16.2 → 1.16.1 的生成差异；`configure~` 是备份。默认作为本机构建状态保留/忽略，**对已跟踪生成文件添加 ignore 不会消除差异**，若恢复需先保存 patch 后另行执行。
- 未跟踪 `elf2bin` 实际是 shell 脚本，调用固定 `/opt/riscv/bin/riscv64-unknown-elf-objcopy`，不是可执行二进制垃圾。保留内容；若是项目需要的工具，建议迁到 difftest 自有 `scripts/elf2bin` 并参数化工具路径后单独提交，不让它埋在被忽略的第三方 clone 中。

建议拆成：runner 功能提交、Spike/转换工具提交、开发配置与忽略规则提交、知识文档提交。运行档案在根仓库单独提交。

### 3.5 XiangShan 外层 harness：从全量忽略中救出源码

建议主仓库追踪这些路径：

```text
difftest-xiangshan/README.md
difftest-xiangshan/Dockerfile
difftest-xiangshan/.gitignore
difftest-xiangshan/pipeline.py
difftest-xiangshan/analyze_trap_results.py
difftest-xiangshan/rerun_shard.py
difftest-xiangshan/run-docker.sh
difftest-xiangshan/run-local-xiangshan.sh
difftest-xiangshan/run-v128-smoke.sh
difftest-xiangshan/run.sh
difftest-xiangshan/tests/test_pipeline.py
difftest-xiangshan/tests/fake_emu.py
difftest-xiangshan/tests/fake_diff.so
difftest-xiangshan/tests/tools/*
difftest-xiangshan/smoke/isla-v128-vsetivli.json
```

内容依据：pipeline 提供 JSON→汇编→ELF→DiffTest 流程，trap analysis 解析结果与差异日志，rerun_shard 提供分片和超时清理。均为项目代码，不是因为用于某次实验就当临时文件。

特别注意：`tests/fake_diff.so` 是 90 字节说明文本，`tests/tools/emu` 是断言参数并打印 `HIT GOOD TRAP` 的 Python 测试替身，另两个 `*-so` 也是 fixture；**不能用全局 `*.so` 或“无扩展名可执行文件全部忽略”规则丢掉它们**。

其余分类：

- `inputs/` 中 11 份 JSON：大多是批次输入/筛选结果，应归档；`bisect_vstart_hang.json`、`smoke_trap.json` 等若被正式测试引用，再保留一份 fixture。不要一律按 JSON 后缀忽略。
- `poc-final/*.S`：可复用回归源程序；建议保留在 harness 的 `poc/` 或现目录，与构建/运行说明一同提交。旁边 3 个 `.elf` 属于实验二进制，放根档案记录哈希，后续可重建。
- `emu-baseline-7bf51a8`：241,307,984 字节（约 230 MiB），是旧基线模拟器，不进入普通 Git。保留到根大型档案，记录源码 SHA、构建参数、二进制 SHA-256 和保管位置。
- `work/` 约 1.2 GiB：批次输出，按第 4 节归档/忽略；`__pycache__/` 是缓存。

移路径时还要更新 run 脚本默认输出、Docker 挂载和 README：不能只把输出改到根 `archives/`，却让容器只挂载 harness 子目录导致写不到目标。

### 3.6 XiangShan 上游仓库：新测试属于这里

- `src/test/scala/xiangshan/backend/fu/vector/ByteMaskTailGenParameterizedTest.scala`：完整 Chisel 测试，验证 VLEN 128/256 下 LMUL=8 的第 5 个物理向量寄存器 mask；应在 XiangShan 的开发分支提交。
- `tests/v-rtl-regress/`：保留 `README.md`、`Makefile`、`.gitignore`、`xiangshan.ld`、`vstart_restart.S`、`vxsat_clear_then_sat.S`、`vxsat_sat_then_clear.S`，属于回归测试源码。
- `tests/v-rtl-regress/build/` 的 ELF 和约 12 MiB 日志属于测试输出；有结果价值的迁根档案，build 保持忽略。
- `mill.dMWuA8` 是空文件，属于临时文件候选，精确忽略/可选删除。

当前 detached HEAD，执行时先在原 SHA 上创建用于保存这些测试的本地分支，再选择性提交；不在 detached HEAD 上留下难找的 commit，也不直接推向官方仓库。以后若需要远端持久化，再决定 fork/remote。

### 3.7 Ara：外层生成器、上游依赖与构建补丁分清

- `ara/pipeline.py`（44,091 字节）是完整生成/执行/差分工具，建议提交主仓库；需要补充 harness README、版本和构建说明。
- `ara/ara/` 是上游源码依赖，主仓库应精确忽略，不整体 add；`ara/work*`、`ara/trace_hart_0.dasm` 分类到档案/输出。
- `hardware/build-v128/` 是非官方 VLEN=128 实验构建产物，忽略；归档时必须注明配置。既有正式结论强调以合法 VLEN=2048 复验为准，不能合并为无配置区分的一个结果。
- `cheshire/sw/cva6-sdk` 的上游 gitlink 从 `44fdb08e…` 变成工作目录 `cb35d1db…-dirty`；内部有 **41 个 staged deletion**。`riscv-vectorized-benchmark-suite` 从 `edf3385e…` 到 `8924cbb5…-dirty`，内部有 **155 个 staged deletion**。这不是可以顺手提交的普通升级；可能涉及未完成 checkout/本地裁剪，原因本轮没有定论。执行前保存索引和状态，单独确认用途；不要把这些删除和指针变化提交为 Ara 功能。

额外检查了会被父仓库状态遗漏的依赖源码：

| 依赖 | 当前差异 | 实际归类 |
| --- | --- | --- |
| `hardware/deps/tech_cells_generic`，`7968dd6` | `src/rtl/tc_sram.sv` 的 Verilator 写通路和 DPI memload | 与 Ara 自带 `hardware/patches/0001-tech-cells-generic-sram.patch` 的稳定 patch-id 完全相同：`100a5cb445174c88a047e40d6835ce446e7c649c` |
| `toolchain/riscv-isa-sim`，`204b88de` | `riscv/execute.cc`、`interactive.cc`、`processor.h`、`sim.h` | 与 Ara 自带 `patches/0003-riscv-isa-sim-patch` 的稳定 patch-id 完全相同：`78709e44434a33cc4c05e0cefee9335d131fbaa5` |

以上是已经由构建流程应用的已版本化补丁，**不需要当新功能重复提交到依赖仓库**。保留 patch 应用说明、源 SHA 和 build 模式即可。`toolchain/riscv-isa-sim/build-mod/` 是生成构建目录，忽略。不要为消除 dirty 状态而撤回实际运行依赖的这些补丁。

## 4. 运行结果统一归档：具体迁移表

本次按下表建立根目录档案副本，表中的“迁移/迁根”对当前批次均指复制快照，不删除源目录。Isla 的 output、IR、fixture 和原运行路径保持不变；其他运行目录也先确认无活跃写入再取快照。复制前后核对清单与哈希，若源仍变化则标记快照不完整并重新取得稳定版本，不把混合时刻数据称为完整批次。调整消费者路径或清理源文件属于后续独立动作。

建议结构（`archives/` 位于主仓库根目录）：

```text
archives/
  README.md                         # 分类、命名、复现与大文件保管约定
  index.json                        # 批次、基线、结果入口和保管级别
  isla/<日期或原批次名>/
  xiangshan/<日期与基线>/
  ara/2026-09-16-17/
  difftest/<原批次名>/
  assembly-gen/<原批次名>/
  worktrees/<分支名>/<批次名>/
  _raw/                             # 大型原始产物，本地保全；默认不进普通 Git
```

“根目录统一存放”与“全部字节提交普通 Git”是两个不同决定。推荐报告、JSON/NDJSON 结果、原始小日志、源码 PoC、哈希、重放命令和必要小 ELF 进 Git；GiB 级完整运行树/模拟器放根 `_raw/`，在提交的 manifest 里登记。**仅忽略的 `_raw/` 不是远端备份**；若目标还包括异机完整恢复，审核时选择 Git LFS 或外部持久存储，并确认上传/下载校验后再清理源目录。本轮不假设存在任何远端归档服务。

| 原路径 | 建议根目录目标 | 内容判断 / 保留要求 |
| --- | --- | --- |
| `agents/ara_poc_batch/snapshot/`（约 90 MiB） | `archives/ara/2026-09-16-17/` | 已有 REPORT、inputs、results、poc、legal2048 和 triage 探针，是成套档案；优先整体保全，不能因 `tmp-artifacts` 名称删除 |
| `isla/agents/validation/Vext-test-9-16-difftest-xiangshan/`（约 66 MiB） | `archives/xiangshan/2026-09-16-19/` | 保留全部报告、issue 草稿、PPTX、bug JSON、make-solve-json、PoC 与 `archive-20260919/`；现成档案不拆散到无法重放 |
| `agents/vext_issue_draft_reproduction/issue1/`、`issue2/`、`issue3/` | `archives/xiangshan/2026-09-19-draft-reproduction/issue*/` | `.S`、`link.ld`、ELF、编译/emu stdout/stderr、退出码、哈希全部成组；即使空 stderr 也有证明意义，不按 0 字节一概丢弃 |
| `isla/Report.md` | `archives/xiangshan/2026-09-16-success-replay/Report.md` | 属于本轮 success-only 历史实验报告，与后续含 trap 的全量报告分批次保存 |
| `isla/reports/6.14_test_solve_all/`、`6.16_test_solve_all/`、`6.28_v_ext_solve/`、`reports/profiling/` | `archives/isla/<原批次名>/` | 报告及 profile 证据迁根；可复用设计分析可留项目 docs/agents 并链接档案 |
| `isla/reports/6.18_explain_fix/review_report.md` | 默认保留项目知识目录并挂根索引 | 属于解释/审查材料；若与某次实验绑定可同批归档，不能当输出删除 |
| `isla/agents/start_multi_inline_spawn/out/` | `archives/isla/start-multi-inline-spawn/` | CPU CSV、summary、run.log 是已存在性能证据；脚本和 plan/status 留项目 |
| `isla/output/`（约 409 MiB）及 `output.*` 历史目录 | `archives/isla/<原目录名或已确认批次>/`，大型 trace 放 `_raw/` | 复制 solve JSON、参数/错误/超时和 profile 元数据；当前输入及其消费者路径不动 |
| `difftest-xiangshan/inputs/`、`work/`（work 约 1.2 GiB） | `archives/xiangshan/<原work批次>/` | 重点保全 success 全量、scalar-contexts、trap entries、rerun-c8d7b3a、verify-itrace、v128 smoke 及 8-shard 结果；fixture 例外留 harness |
| `difftest-xiangshan/emu-baseline-7bf51a8` | `archives/_raw/xiangshan/7bf51a8/` | 模拟器与版本/构建说明一起登记，不进普通 Git |
| `ara/work-all/`（约 672 MiB）、`work-full/`（65 MiB）、`work-diff/`（2.1 GiB） | `archives/ara/<对应批次>/` 和 `_raw/ara/` | 核对 snapshot 已覆盖哪些结果；全量原文不重复提交，但仅有摘要不能视为完整备份 |
| `ara/work/`、`work-fp/`、`work-mret/`、`work-v128/` | `archives/ara/<对应批次>/` | MRET 修复后的结果不能被旧 work-all 结果覆盖；emu/spike、VLEN128/2048 分开标注 |
| difftest 所有 `run_difftest/out*` | `archives/difftest/<原目录名>/` | `out/` 约 738 MiB、probe scan 约 41 MiB、BOOM 单批约 19–20 MiB；优先保存失败输入、预期/实际 signature、结果和重放命令 |
| difftest 顶层 4 个日志及 2 份 `results.xml` | `archives/difftest/legacy-debug/`，大日志放 `_raw/` | 原件不改写；索引中的 results.xml 与当前文件不同，备份时分别保留 index/worktree 版本 |
| 根、Ara 外层的 `trace_hart_0.dasm` | `archives/ara/unattributed-traces/` | 在确认对应 PoC 前标为来源待确认。根 trace 与 snapshot/legal2048 同名文件大小都是 1488 字节但 SHA 不同，不能按文件名或大小去重 |
| `isla/inrange.log`、`isla/oob.log` | 小型诊断记录或可选删除 | 两者都是 84 字节、仅 emulator 启动信息，无范围检查结果；留文档摘要后可删除，不当成功证据 |
| 根 `report/passed-intr-report.md` | `archives/difftest/passed-intr/`（如需保留当前报告） | 已忽略的生成报告；`report/passed-intr.sh` 是已跟踪工具，应留主仓库 |

归档必须同时做：

1. 每批生成 manifest：原路径、新路径、大小、SHA-256、运行时间（不明则明确未知）、输入来源、生成器 revision、DUT/REF revision、IR hash、VLEN/ELEN、命令、返回码、结论状态。
2. 原始内容保持原样；不要为了满足空白检查改写日志。需要解释或更正时增加旁注/新报告。
3. `results.json/ndjson` 中的绝对 ELF/log 路径也需要处理；保存原文，额外输出相对路径映射或重放适配层。只改 Markdown 链接不足以恢复工具运行。
4. 先复制并校验，再由主仓库提交已审阅的档案和索引。本次到此为止，不在 Isla/Sail-RISC-V 提交路径移除，不删除原始运行输入；其他源目录清理另列具体清单。
5. 档案中使用过的 generator 快照应保留。例如 `ara/pipeline.py` 与 `snapshot/poc/pipeline.py` 当前 SHA 相同（`5ffae78b…`），前者是维护源码，后者是实验使用的冻结快照；可通过版本引用减少重复，但不要未经核验删除。
6. 更新根 `agents/findings.md`、议题 status、档案索引和被纳入本批次的 harness README。保留子项目原文链接；根快照用额外来源映射说明旧路径与档案位置，不改写原始实验数据。

现有报告存在阶段性结论，归档时不合并成一个“最终数字”：Ara status 中仍留有先前 B7/B8 结论，snapshot REPORT 与 findings 后续有撤销/修正；XiangShan success-only 报告与新基线包含 trap 的统计覆盖范围不同。`archive-20260919/全量bug统计表.md` 汇总里同时使用新旧基线及近似数，不能直接按互斥类别相加当作新基线 19,908 条的分区。应保留历史原文，在索引说明适用基线和修订关系。

## 5. 已跟踪的生成物：ignore 不会自动移除

本节是历史文件分类，不是本次移除追踪的授权。Isla/Sail-RISC-V 的已有 IR、配置、patch 和运行路径原样保留，取消其中涉及改生成逻辑、迁 IR、取消追踪的本次执行步骤；允许在根 archives 复制有价值的版本。以下表格仅用于说明后续若单独启动迁移需要满足的条件。

本次发现以下历史文件已经进入 Git，不能仅添加忽略规则就声称整理完成，也不能无条件删除：

| 路径 | 判断与行动 |
| --- | --- |
| `isla/rv32d.ir`、`isla/rv64d.ir` | 已跟踪，虽然匹配当前 `/*.ir` ignore；属于模型产物，但 Makefile、`scripts/run.mk` 和 CLI 测试仍使用 `rv64d.ir`。如统一归档，需先配置新的 IR 路径/获取生成流程，保持现有入口可运行，再移除追踪 |
| `isla/ir/rv64d_v128_e64.ir`、`rv64d_v256_e64.ir`、`rv64d_v512_e64.ir`（合计约 44 MiB） | 多 VLEN 模型基线，不是随手日志；先作为版本化模型/fixture 保留。若迁根 model 档案，必须维护 hash 与 workaround/config 的一致性 |
| `isla/log` | 已跟踪的执行日志，Makefile 会写它；建议迁根历史档案，修改生成输出路径后取消源文件追踪 |
| `isla/itrace` | 内容是含 `...` 和占位路径的 trace 格式示例；建议作为 `doc/` 的示例保留，不能当真实运行 trace 清除 |
| `isla/test_args.yaml` | 大型指令参数列表；先核查生成方式和消费者。`profiles/riscv/test.py` 实际读取同目录 `args.yaml`，不能据此直接证明顶层列表已无用途；保留或迁为明确 fixture，暂不删 |
| `difftest/progs/` | 已跟踪 724 个文件，约 4.7 MiB，多种 ASM/BIN/DIS/DUMP/ELF/HEX/MAP；TODO/draft 明确把它们当输入样本。保留 fixture 必需集，历史批量生成件可迁根 corpus 档案并修改示例路径 |
| `sail-riscv/diff` | 已跟踪的历史 GPR 改造 patch；保留为变更依据，可重命名至文档/补丁目录并解释适用基线，不作为临时文件删除 |
| `isla/.idea/*`、`.vscode/*` | 一部分已跟踪，即便匹配 `.*/` 仍会进入后续修改；共享相对路径配置保留，机器状态另拆，不全删 |

IR 路径迁移不在本次范围。根既有 `sail-riscv.patch`、Dockerfile、Makefile 和初始化脚本是构建源码/配方，保留文件；其中根 Makefile 的依赖获取和自动应用补丁入口需要按第 11 节调整，不能沿旧入口改变两个受保护项目。

## 6. AI / agent 持久化文档的保留策略

### 6.1 保留并提交的具体集合

表中 Isla 的知识文件统一复制到根 `agents/project-memory/isla/<原相对路径>` 后由主仓库提交；Sail-RISC-V 如有新增待保全知识使用对应 `sail-riscv/` 命名空间。活跃工具原目录保留，避免迁移后工具找不到计划/技能。下面原来建议的 Isla docs commit、项目内 `agents/tool-memory/` 路径改为此根目录目标；不创建子仓库文档提交、不改变固定 HEAD。

| 位置 | 保留内容 | 建议归属 |
| --- | --- | --- |
| 根 `AGENTS.md`、`CLAUDE.md`、`agents/overview.md`、`agents/findings.md` | 仓库约定、索引、跨项目知识 | 主仓库，保持 CLAUDE 符号链接 |
| 根 `agents/*/` | 所有 plan/status/review/report/subagents 记录；包含 zSTORE 多 agent 工作交接 | 主仓库；仅成套运行证据迁到根 archives |
| `agents/ara_poc_batch/{plan,status,bugs}.md` | 计划、状态、问题演变 | 主仓库，链接迁移后的 snapshot |
| `agents/v_symbolic_dedup/`、`agents/vext_issue_draft_reproduction/{plan,status}.md` | 本次尚未跟踪的持久化记录 | 主仓库 |
| 根 `.claude/skills/rtl-difftest/SKILL.md` | 项目自有工作流程 | 已跟踪，继续保留；不同于 settings.local |
| 根 `.serena/memories/*.md` | 已检查 4 份项目概览、约定、命令和完成标准 | 建议迁/复制到根 `agents/tool-memory/serena/` 并 commit，注明原路径；工具活跃副本仍可保留 |
| `isla/agents/`、`plans/`、`vibecoding/` | 技术方针、计划、提示、分析、状态 | 根 `agents/project-memory/isla/` 下保留原相对路径；实验输出另归档 |
| `isla/.omo/plans/`、`drafts/`、`notepads/` | 真实设计决策、审核反馈和用户确认边界 | 根 `agents/project-memory/isla/.omo/` 冻结副本 |
| `isla/.sisyphus/plans/`、`drafts/`、`notepads/` | 同类持久化内容 | 核对 `.omo` 重复后保留唯一正文及来源映射；不能把有差异部分覆盖掉 |
| `isla/.omo/boulder.json` | 包含 active_plan、task 标题、agent/session 对应关系和时间 | 冻结副本存入根 `agents/project-memory/isla/.omo/`；不是“所有 JSON 都是缓存” |
| `.omo/evidence/`、`.sisyphus/evidence/` | QA 汇总及运行文本 | SUMMARY 等解释保留知识索引，原始证据转根 archives；两处重份按 hash 核对 |
| `isla/.qoder/repowiki/zh/content/`、`meta/repowiki-metadata.json` | 约 1.8 MiB 的生成代码知识库及引用元数据 | 根 `agents/project-memory/isla/.qoder/` 快照，标注 AI 生成、源 revision/核验情况；另加可移植索引 |
| `isla/.codex/skills/build-sail-riscv/SKILL.md` | 项目技能源码 | 原件保留，副本进根 `agents/project-memory/isla/.codex/`；不能与空 `.codex` 文件混为一类 |
| `difftest/AGENTS.md`、`CLAUDE.md`、`TODO.md`、`boot.md`、`draft.md`、`report.md` | 工作约定、设计/启动/历史分析 | 默认保留 difftest；report 中纯运行证据部分可链接根 archives |
| `difftest/.serena/memories/*.md` | 4 份持久 memory | 迁/复制到 difftest `agents/tool-memory/serena/` 并 commit |
| 各 worktree 的独有 `agents/`、`vibecoding/`、`.sisyphus/` 文档 | 实验上下文和未合入结论 | 冻结到根 `agents/project-memory/worktrees/<worktree名>/`，保留来源 SHA，不创建实验提交 |

本次 `diff -qr` 检查 `.omo` 与 `.sisyphus` 的 plans/notepads 未报告差异；`.omo` 另有 `boulder.json`、额外 draft 和更多 continuation。去重仍应保留来源清单，不能简单删除整个 `.sisyphus`。

### 6.2 本地状态与文档的界线

- `run-continuation/*.json`：调度状态，不是完整对话；先保全一份小型会话映射快照，与 boulder 一起记录 agent 协作脉络，再忽略持续变化的活跃副本。不要假称仓库里存了所有聊天记录。
- `.serena/cache/*.pkl` 是代码索引缓存，`.serena/project.local.yml`、`.claude/settings.local.json` 属于机器设置；默认忽略。`.serena/project.yml` 中可移植配置若需要共享，去掉本机字段后另行提交。
- `.mimocode/.cron-lock`、PID/lock/socket、空 `.codex`、空 `.agents/` 不是知识文档；忽略/暂留。空目录 Git 本来也不会保存，不需要为之创建占位文件。
- difftest `.humanize/` 本次未列出文件；assembly-gen ignore 中的 `.humanize/`、`goal-tracker.md`、`summary.md` 等规则可能屏蔽将来的知识文件。按真实内容归档，不把“某工具目录”当作删除依据。

本次不需要更改 Isla 的 `.*/` 忽略规则，因为提交的是主仓库中的文档副本。对根快照使用 `git check-ignore -v` 和 `git ls-files` 验证可提交且已跟踪；不使用强制添加整个隐藏目录的方式绕过逐文件分类。

## 7. 隐藏 worktree：不能当临时文件删除

本次所有 worktree 只保全不提交：复制 staged/unstaged patch、未跟踪源码和独有文档，并记录所属仓库及 HEAD。表中的原实验提交建议属于后续独立开发，不是当前执行步骤。

根 `.worktrees/` 约 4.7 GiB，Isla `.worktrees/` 约 38 GiB。空间大主要不代表没有工作价值。本次检查了 22 个现存额外 worktree 的 Git 状态；其中 **11 个有变更**。它们与主工作树共享对象库，但有独立 HEAD、索引、工作区；在主目录 commit 不会保存这里的未提交内容。

| worktree | 实际未提交内容 | 行动 |
| --- | --- | --- |
| `.worktrees/assembly-gen-xiangshan-nutshell` | 14 个 tracked 修改、7 个未跟踪条目；平台 profile、manifest、向量初始化、模板/链接/编译脚本、测试及文档 | 分层 patch 与新文件副本保全，不提交/合入 |
| `.worktrees/difftest-xiangshan-nutshell` | host.py、runner.py 修改；新增 elf_loader、external_dut_runner、配置示例、测试与说明 | 分层 patch 与新文件副本保全，不覆盖主工作树 runner |
| `.worktrees/isla-A`、`.worktrees/isla-B` | 各有 tracked `rv64d.ir` 修改 | 作为实验 IR 归档，记录分支 SHA/生成配置/hash；无需凭产物变化制造功能提交 |
| `.worktrees/sail-A2` | `vext_control.sail` 增加符号 read_vmask extern 路径 | 未完成/历史实验源码，单独实验分支保全；不能自动并入本次 SYMBOLIC 去重 |
| `.worktrees/sail-B` | `vext_vm_insts.sail` 的 VIMTYPE 将 assertion 改为绑定返回 num_elem | 单独实验改动，对照当前基线确认是否已被等价实现取代；先保存，不删 |
| `isla/.worktrees/dev-isarch-infra` | `itrace.rs` 同时有 staged/unstaged 重构，另有 `log`、`log.1` | 保存两层 patch，trace 功能留分支，日志转档案；不要只保存最后工作区而丢索引版本 |
| `isla/.worktrees/dev-isarch-loop-limmit` | 5 个 Rust 文件，fork admission、执行限制和调用传递 | 只读 patch 保全，不提交实验源码 |
| `isla/.worktrees/dev-isarch-mem-sym-with-loop-limit` | 50 个 staged 条目，包含 `sanity-test/` 迁移、新测试 runner、Cargo/Makefile/spec/exec 变化；混入 `log`、`log.1` | staged patch 保全且不改变索引；`expected/summary.txt` 是测试预期，不按名字忽略 |
| `isla/.worktrees/dev-isarch-pathmerge` | 9 个 tracked 修改、4 个新日志/dump；merge waiting、yield、executor/primop/simplify 变化 | 源码 patch 保全，日志/dump 复制至根实验档案，不提交源码 |
| `isla/.claude/worktrees/multithread-limit-adapt` | `primop.rs` 小改动与 `agents/findings.md` 新增 96 行 | 两者都保全，尤其 findings 不能因在 `.claude/worktrees` 而被删 |

其余本次状态干净：`isla-AB`、`isla-B1`、`sail-A`、`sail-A3`、`sail-AB`、`sail-B1`、`sail-B2`、`sail-B3`、`sail-B4`、`feat-memory-support`、`float-support`。**干净仅说明无工作区差异，不证明分支已合并或可以删除。** 之后检查独有 commit 和独有被忽略文档，再决定保留/归档分支。

Git 还登记 `/tmp/isla-quota-stage` 为 prunable；这是元数据状态，本轮没有 prune。不要把 `git worktree prune` 混入提交整理。

## 8. 忽略规则的具体调整方向

以下是审核后的规则设计，不是本轮已修改的内容。精确规则优先，避免用 `*.json`、`*.md`、`*.S`、`*.so`、`plan.md`、`summary.md` 这类全局规则误伤源码与知识。

### 主仓库

- 移除 `/isla/`、`/sail-riscv/` 对应忽略，按第 11 节登记带 `.gitmodules` 的 gitlink；继续忽略 `/sail/`、`/assembly-gen/`、`/difftest/`，不误纳为普通目录或裸 gitlink。
- 移除整个 `difftest-xiangshan/` 的忽略，改为 `/difftest-xiangshan/xiangshan/`、`/difftest-xiangshan/work/`、`/difftest-xiangshan/__pycache__/`、`/difftest-xiangshan/emu-baseline-*`、`/difftest-xiangshan/poc-final/*.elf`；inputs 在完成归档/fixture 划分后再按用途忽略。
- 新增 `/ara/ara/`、`/ara/work/`、`/ara/work-*/`、`/ara/__pycache__/`、`/ara/trace_hart_*.dasm`。
- 根 trace 归档后忽略 `/trace_hart_*.dasm`；保留现有 `/out/`（Mill daemon/worker 缓存，约 84 KiB）、`.worktrees/` 等本地状态规则。
- 增加 `/archives/_raw/`，但不忽略 `archives/` 本身；每个被忽略大对象仍需有提交的 manifest。
- 根 `.serena/` 可以继续忽略活跃工具状态，前提是 memory 已在 `agents/tool-memory/serena/` 保全并提交。

### difftest

- 精确覆盖 `/.codex`、`/difuzz-rtl/elf2hex/`（采用 clone 管理方案时）、`/difuzz-rtl/run_difftest/build_rocket/`、`/difuzz-rtl/run_difftest/out*/`、两处 `/results.xml`、顶层已识别日志、`/tmp_probe_elfs/`、Python 缓存。
- 删除/收窄按文件名屏蔽持久文档的 `plan.md`、`draft.md` 规则；本次 `draft.md` 虽已跟踪仍会影响新目录同名文件。
- 现有 `.serena/` 保留为缓存规则的前提同上：先把 memories commit。
- 取消“此次新增到暂存区”的日志/空文件/gitlink 时，只动索引，保留工作区；已有 tracked corpus 的移除则需独立确认和迁移提交。这两类不能用一个粗暴清空索引操作处理。

### Isla / Sail-RISC-V / assembly-gen / XiangShan

- Isla：本次保留现有忽略规则与 tracked IR/log；skills/知识复制至主仓库，日志复制归档，不改当前输出路径。
- Sail-RISC-V：现有 `/build`、`/build-symbolic-*/`、`sail_smt_cache` 是合理构建忽略；不添加 V 扩展源文件或历史 patch 到 ignore。
- assembly-gen：增加空 `.codex` 和具体 scratch 路径；检查 docs/plan、goal-tracker、summary 等知识屏蔽规则。已有 Python/build/venv 忽略继续保留。
- XiangShan：保持回归 `tests/v-rtl-regress/.gitignore` 的 build 排除；空 mill 临时文件可精确忽略。不要为解决这个文件而误忽略所有 Mill 构建描述。

## 9. 建议的实际执行顺序与提交分组

### 阶段 A：保护现有边界

1. 为每个主工作树和脏 worktree 记录 HEAD、branch、remotes、index/worktree 状态、未跟踪文件清单。
2. 在根归档的受控目录保存 staged 与 unstaged 两份 binary patch，并复制未跟踪源码/文档；未跟踪文件不包含在 `git diff` 里，不能遗漏。
3. 对 `MM runner.py`、`MM itrace.rs`、`AM results.xml` 保留两层版本；Ara 两个异常子模块保存索引，不自动提交/恢复。
4. 不运行 `init.sh`、`make distclean`、`git clean`、reset/checkout 批量回退或 worktree 删除来“整理”。

### 阶段 B：先建立主仓库的保全和目录约定

1. 新建 archives 索引、manifest 规范，复制现有 Ara/XiangShan成套档案并校验。
2. 先救出被忽略的 harness 源码及 AI 文档；对历史知识标明来源/版本。
3. 收窄忽略规则；保存到根的日志/结果采用独立归档提交，避免与代码混合。
4. 更新根档案索引和来源映射，保留子项目原报告与运行目录；本批次不删除/替换它们。

### 阶段 C：主仓库提交分组，子项目源码提交排除

| 建议顺序 | 所属仓库 | 提交主题 / 边界 |
| --- | --- | --- |
| 1 | 主仓库 | `.gitmodules`、两个现有 HEAD 的 gitlink、根忽略规则与初始化入口/README；可独立完成，不依赖全面整理 |
| 2 | 主仓库 | Isla/Sail-RISC-V 及 worktree 文档快照、跨项目 AI 记录、来源清单 |
| 3 | 主仓库 | 运行证据副本与索引，按 Ara/XiangShan/其他批次拆分 |
| 4 | 主仓库 | 全面整理批次中纳入的外层 harness 现有源码、fixture 和说明 |
| 排除 | Isla / Sail-RISC-V 及其 worktree | 不提交源码、测试、IR 或子项目文档，不修改其 HEAD/分支/索引 |
| 后续独立 | difftest / XiangShan / assembly-gen | 功能修复、工具参数化、新测试和源码提交另行实施；不阻塞两个 submodule 关联 |

阶段 B 的保全提交可以先于上表。两个 gitlink 固定已有 SHA，不等待子项目新提交；其他依赖环境清单不重复充当这两个版本的锁文件。Sail 无源码差异无需 commit；assembly-gen 主树已有 ahead 提交也无需重复创建。

提交操作只针对已审阅的主仓库路径，不递归暂存子项目。未来发布前需确认 gitlink 引用的两个 commit 能从 `.gitmodules` 对应远端取得；本地 remote-tracking ref 不能代替远端可获取验证。无法联网核验时明确记为未验证，不宣称远端完整可复现。主仓库版本组合不包含未提交源码，归档里的 patch 也不等于这些修改已成为子项目正式 commit。

### 阶段 D：完成检查

- 每个仓库分别检查 `git diff --cached --name-status`、`--stat`、`--check`；不只看根 status。
- 检查 Git 索引文件模式：只有确实配置好的依赖才允许 `160000`，infos/CLAUDE 等预期链接保持 `120000`。
- 检查新加文件大小；普通 Git 中不出现超过 100 MiB 的单文件，建议对超过 10 MiB 的每个新增文件单独说明用途。
- 检查 archive manifest 与源对象 hash 一致，报告/JSON 路径可解析，复现输入/源代码/工具版本齐全。
- 对实际修改的主仓库初始化脚本做语法和隔离场景验证；不在受保护目录运行格式化、模型构建或 SMT 回归。只做版本关联不需要重跑语义测试；若后续改功能，另行验证。
- 对两个项目及其 worktree 比较操作前后的 HEAD、分支、源码/测试内容哈希、源码索引项及 staged/unstaged patch；本批次不在其中写入文件，现有未跟踪源码也必须保持不变。不能只凭主仓库 status 判断“没动代码”。
- 对 AI 文档用 `git ls-files` 验证已跟踪；仅在磁盘存在、或文件被 ignore，都不等于已保全到 Git。
- 对最终各项目工作区未提交残留逐项标注：本地缓存、构建补丁、待确认实验、异常子模块。无需为了全绿而删内容。
- 更新根 AGENTS 目录介绍（现介绍仍主要描述早期 Sail/Isla）、agents overview、议题 status 和 findings，写清哪些已提交、哪些仅本地归档、哪些等待远端保存。

## 10. 本轮验证范围与审核项

本轮已读取主工作树的关键代码 diff、新增 SMT 测试、Sail V 重构、difftest runner staged/unstaged 差异、两套 harness 主要入口/说明、XiangShan 新测试、Ara 依赖补丁、主要档案说明和 AI 持久化目录内容；扫描了工作区内 22 个额外 worktree 状态，并对脏实验的关键改动/文档做定向读取。大型 trace/成千上万的生成 ELF/JSON 按目录、结构、代表内容和体积分类，**未逐字读取全部二进制或逐条复核科学结论**；第三方全依赖源码也不在完整代码审查范围。

只读 whitespace 检查：Isla 工作区、Sail-RISC-V 暂存区、difftest 未暂存差异未报告错误；difftest 暂存差异报告 `make_output.log` 的空白错误，这是日志误入暂存的进一步证据。没有为了通过检查改写原始日志。

请审核以下决定；在确认前不执行整理：

- [ ] 接受 harness 外层由主仓库管理、内部上游项目独立管理的边界；若一定要求 harness 也独立 repo，需要另定初始化和远端方案。
- [ ] 接受根 `archives/` 统一归档；小型完整证据进 Git，大型原文先保全 `_raw/`。若要求所有原文可从远端恢复，选择 LFS/持久存储后再清理。
- [ ] 接受 Isla/Sail-RISC-V 知识快照保留到根 `agents/project-memory/`，跨项目记录留根，历史证据复制到 archives；原文和活跃工具状态保留。
- [ ] difftest 提交前必须处理提前 continue、大日志及 elf2hex 裸 gitlink；作为后续独立批次，不是本次版本关联的前置条件。
- [ ] 接受 worktree 只做 patch/文件副本保全，不创建源码提交、不自动合入、不删除。
- [ ] Ara 两个子模块的 41/155 项删除暂不提交，先确认是否未完成 checkout 或有意裁剪。
- [ ] 当前 IR/corpus、output 和消费者路径保持原样；复制档案不等于移除追踪，后续如需迁移另行规划。
- [x] 用户已明确 Isla/Sail-RISC-V 代码改动不动；按现有 HEAD 关联，不先提交源码。其余未勾选项仍是计划建议，不把用户询问 harness 含义当成批准全部整理。

审核后的第一步是保存各仓库现有 index/worktree 边界和关键证据，而不是执行批量删除或批量 add。

## 11. 2026-09-21 补充：用 submodule 绑定 Isla 与 Sail-RISC-V

用户最新目标：把当前 Isla commit 与当前 Sail-RISC-V commit 关联起来，且代码改动不动。方案是仅把这两个已有独立仓库登记为主仓库的 submodule，以主仓库的一个 commit 保存这一对已有版本。正文已统一为 gitlink 管理；其他依赖和全面整理不因此自动进入执行范围。

本轮只读确认的待固定版本：

| submodule 路径 | URL（建议采用 HTTPS，便于统一初始化） | 精确 commit |
| --- | --- | --- |
| `isla` | `https://github.com/ariscv/isla.git` | `97390b0a5f05896a3255af72939e314eb5feaab5` |
| `sail-riscv` | `https://github.com/msuadOf/sail-riscv.git` | `5f1a0de0d8219537f27680d325b7adcac5db3478` |

主仓库 commit 中的两个 `160000` gitlink 保存精确 SHA，`.gitmodules` 只保存路径和 URL。无需给两个子仓库制造相互依赖，也无需修改它们已有的提交历史。主仓库的新 commit 就代表一个版本组合；今后版本升级时，在子仓库完成提交，再由主仓库提交新的 gitlink。

待审核后的实施细节：

1. 从根 `.gitignore` 去掉 `isla/` 和 `sail-riscv/` 两条，其他忽略规则保持原状。
2. 新增 `.gitmodules`，只登记上述两个路径和 URL；不设置自动跟随分支更新。
3. 将现有目录登记为 submodule，两个 gitlink 固定上述 SHA。保留两个子仓库现有 `.git`、分支、索引及工作区；尤其不执行重新 clone、checkout、reset 或 `absorbgitdirs`，避免影响已有 worktree。
4. 调整根 `init.sh` 对这两个目录的逻辑：以主仓库索引中的 gitlink 为待检出版本（正常已提交状态下与 HEAD 一致），不再按分支 pull。目标完全不存在或为空目录时可初始化；已存在且 HEAD 相同的 checkout 原样保留，即使 dirty 也仅提示；HEAD 不同或非空非 Git 目录则停止该项并报告，不 checkout、不覆盖。缺失 gitlink 或存在未合并索引时明确报错。两个条目不进入旧的分支更新函数，其余依赖流程保持原行为。迁移当前工作区时不运行该脚本。
   同步调整根 Makefile 的 Isla/Sail-RISC-V 下载目标，使用相同固定版本入口，不能继续从分支 clone；移除正常构建时自动执行 `git apply ... sail-riscv.patch` 的行为，保留 patch 为历史配方并说明未自动应用。隔离环境验证直接 `make` 的获取入口，不在当前工作区执行构建。既有破坏性清理目标不用于验证或整理。
5. README 说明新 clone 可用 `git clone --recurse-submodules <主仓库URL>`，已有 clone 使用 `git submodule update --init isla sail-riscv`（先确认各子仓库工作区状态）；说明 submodule 初始化通常是 detached HEAD，日常开发需在各子仓库使用开发分支。
6. 校验 `.gitmodules` 和 gitlink 一致、SHA 精确匹配、子仓库 staged/unstaged 内容未改变，并对初始化脚本做语法/隔离场景验证。登记过程不迁移整个 Git 元数据，也不对当前脏目录试跑更新。
7. 主仓库仅提交这次 submodule/初始化/说明的明确文件和 gitlink，不把根既有 findings、Ara、trace 或其他未审核内容一起提交。提交前再次核对 SHA，避免期间子仓库 HEAD 变化导致记录到不同版本。

重要边界：当前 Isla 仍有 SMT 等未提交修改，Sail-RISC-V 的 3 个 V 扩展修改仍仅暂存。上述 SHA **均不包含这些修改**。固定当前 HEAD 保留这些工作区内容，但别人检出主仓库只能获得已有 commit；`git status` 可能继续显示 submodule dirty，这是正常且不能隐藏的问题。本次不创建子项目源码或文档提交，新增文档保全副本进入主仓库，因此既能保存知识，又不改变固定 SHA。

这次建议直接采用 submodule，不再同时引入记录相同两个 SHA 的 lock 文件，避免两个版本来源漂移。若明确不想改变现有嵌套仓库管理方式，备选才是版本清单 + 按 SHA 检出的脚本。

状态：用户的“不动代码”约束已落实，固定现有 HEAD 的范围不再作为待询问题。审核意见已整合到正文；当前仅修订计划，尚未修改忽略规则、`.gitmodules`、脚本或任何索引，也未执行整理/提交。
