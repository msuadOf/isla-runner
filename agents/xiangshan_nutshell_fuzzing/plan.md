# assembly-gen / difftest 支持 XiangShan 与 NutShell

## 目标

在不污染现有脏工作树的前提下，把 Isla 生成的 RISC-V 用例接入开源 CPU 的可复现 fuzzing/差分验证链路：

1. `assembly-gen` 能按 `difuzz`、`xiangshan`、`nutshell` profile 生成正确的汇编、ELF 和 raw image。
2. `difftest` 能批量调用香山与 NutShell 的开源 emulator/difftest shared object，稳定区分成功、差分、超时、崩溃、BADTRAP 和异常循环。
3. 每个失败用例都保留可向开源社区提交、也可用于论文复现实验的完整证据：输入、二进制哈希、目标版本、命令、日志、状态、耗时和一键重放命令。
4. 现有 Rocket/BOOM 与默认 DiFuzzRTL 行为保持兼容。

用户消息中的 `disasemble-gen` 按本仓库实际结构解释为 `assembly-gen`；完整 DUT 支持同时需要修改独立仓库 `difftest`。

## 隔离工作树

- `assembly-gen`
  - 原工作树：`assembly-gen/dev`，含未提交的 V 扩展初始化改动，不触碰。
  - 隔离目录：`.worktrees/assembly-gen-xiangshan-nutshell`
  - 分支：`feature/xiangshan-nutshell`
  - 基线：`3f5fe7e`
- `difftest`
  - 原工作树：`difftest/dev`，含大量 staged/unstaged 修改和生成物，不触碰。
  - 隔离目录：`.worktrees/difftest-xiangshan-nutshell`
  - 分支：`feature/xiangshan-nutshell`
  - 基线：`a82afd8`

实现中只选择性移植与本任务有关的有效改动；不会整体复制原工作树、index 或生成物。

## 参考基线

- DiveFuzz：`3c1991c8c13d304272dd9b1b9eeed7cdd785dd2c`
  - XiangShan 子模块：`d5cc24e88fe207105d4ad6d113a972dd6847dd56`
  - NutShell 子模块：`63a2687089ec374e6bd19d85ec040caab297dbff`
- DRVFuzz：`eb52806c4dc2166d2c23c6ab332154bbe774f891`

只借鉴公开接口和设计，不直接复制第三方实现；文档记录来源提交和许可证。

## 核心设计决策

1. **平台 profile 与 ISA 状态解析分离**：XiangShan/NutShell 差异放在模板、链接、工具链、镜像和 runner 配置层，不新增处理器型号专用 `RISCV` 子类。
2. **首版使用官方 emulator 外部适配**：参照 DiveFuzz/DRVFuzz 调用预构建 `emu` 与 diff shared object；不把新 RTL 强塞进当前只支持 Rocket/BOOM TileLink 的老 Cocotb/Verilator 4.106 adapter。
3. **默认兼容**：未指定 profile 时仍使用当前 DiFuzzRTL 模板和输出约定。
4. **无 shell 拼接**：runner 使用参数数组启动进程，显式处理 timeout、进程组清理和日志落盘。
5. **失败证据优先**：结果分类和重放元数据是功能的一部分，不依赖人工从控制台复制。

## 实施步骤

### 1. 锁定基线与回归测试

- 保留 `assembly-gen` 当前 46 项基线测试。
- 从原工作树选择性移植 V 扩展初始化的源码与测试，排除 `docs/plan.md` 删除、`.codex`、`1.txt` 等无关内容；移植后恢复 62 项测试基线。
- 为当前默认 DiFuzz profile 增加 golden/结构测试，确保平台化前后输出契约不变。

### 2. assembly-gen 平台 profile

- 新增 `--platform difuzz|xiangshan|nutshell`，默认 `difuzz`；`--template` 仍可显式覆盖。
- 顶层 Makefile 增加 `PLATFORM`、`MARCH`、`MABI`、`CROSS_COMPILE`、`LD_SCRIPT` 可覆盖配置。
- 将现有模板明确归为 `difuzz` profile；新增 XiangShan、NutShell 的启动/异常/结束 harness 与链接脚本。
- 三个 profile 共享 `0x80000000` 入口，但分别声明支持的 ISA、特权能力和结束约定：
  - XiangShan：RV64，启用匹配 emulator 的扩展；支持 `GOODTRAP`/skiptrap 结束标记。
  - NutShell：按实际配置限制到其支持的整数/压缩/CSR 扩展，不在初始化阶段无条件执行 F/D/V 指令。
  - DiFuzz：保留 `tohost`、signature 和现有随机数据段 ABI。
- 修复 raw image 生成：不再只抽取 `.text`，而是由 ELF 的所有 loadable 内容生成 `.bin/.img/.hex`；断言入口机器码实际存在。
- 修复特权级切换：User/Supervisor 用例必须真正执行 `mret` 到目标权限，而不是只改 `mstatus.MPP`。
- 输出 manifest，记录平台、ISA、入口、ELF/img 路径、SHA-256、源 JSON 和测试指令。

### 3. difftest 外部 DUT runner

- 新增声明式 target 配置：目标名、emulator 路径、diff-so 路径、输入格式、额外参数、timeout、ISA 参数和结果解析规则。
- XiangShan 命令契约以 `emu -i <ELF或IMG> --diff <spike-so>` 为基础，并可选 `--dump-commit-trace`。
- NutShell 命令契约以 `emu -i <IMG> --diff <NEMU-so>` 为基础。
- 支持单文件与目录批量运行；每个 target 使用独立输出目录，结果主键为 `(target, case)`。
- 结果优先级：进程超时 > mismatch/different-at-pc > 异常循环/无提交 > DUT 周期或指令上限 > BADTRAP/崩溃 > GOODTRAP/成功。
- 每个 case 保存：stdout/stderr、命令 JSON、目标配置、耗时、退出码、分类、输入哈希和重放脚本/命令。
- 汇总生成 JSONL/CSV/文本，便于统计吞吐、超时率、差分率和去重后的失败数。

### 4. 现有 DifuzzRTL 正确性修复

- 将现有 ELF 装载从“`_start.._end_main` + 六个 random 段”改为通用 PT_LOAD 装载，包含 `.data.vr_init` 等所有 loadable 段，并对 `p_memsz - p_filesz` 清零。
- 现有 Rocket/BOOM adapter 保持不变；target 抽象不向 `tileAdapter` 继续堆处理器名分支。
- 排除原脏树中 RTL SUCCESS 后无条件 `continue` 的错误快照逻辑，确保 checker 和 results 始终执行。
- Spike ISA/priv/varch 参数由 target 配置提供，避免 DUT 与参考模型扩展不一致。

### 5. 研究复现与社区提交证据

- 对每个异常建立稳定 case ID：输入内容、目标 commit/profile、ELF/img 哈希共同决定。
- 生成最小重放说明，包含环境变量、完整命令和预期 marker。
- 保存首次差分位置、相关 commit trace 片段和工具版本；不自动向外部社区发送内容。
- 汇总表提供论文常用指标：执行数、有效样本数、exec/s、timeout、mismatch、crash、unique failure、目标版本。

## 测试与验收

### 自动测试

- `assembly-gen`：现有 46 项 + V 初始化 16 项全部通过。
- profile CLI：默认兼容、三 profile 选择、非法 profile、显式模板覆盖、无残留占位符。
- artifact：最小 JSON 能编译；ELF entry 为 `0x80000000`；必需段/符号存在；`.img` 非空并与 `objcopy -O binary` 一致。
- 特权：反汇编证明 User/Supervisor 路径包含并执行 `mret`。
- runner：用 fake emulator 覆盖 success、mismatch、timeout、crash、BADTRAP、异常循环、参数含空格和进程清理。
- PT_LOAD loader：覆盖全部 file bytes、BSS 清零，并专门验证 `_vr_data` 非零数据被装入。
- 回归：Rocket 与 BOOM 已知 add ELF 仍能运行到真实 checker，并各自产生一条非空结果。

### 真实 DUT smoke

在用户环境存在对应 emulator/diff-so 时：

- 同一最小 RV64I case 分别在 XiangShan、NutShell 跑通。
- negative case 能稳定分类为 mismatch 或 BADTRAP，而不是空结果或误报 PASS。
- 每个 target 的输出与汇总互不覆盖，一条命令可重放。

若本机缺少预构建 emulator/diff-so，则完成所有静态、fake-runner、artifact 和现有 Rocket/BOOM 验证，并把真实 DUT smoke 明确列为唯一环境验证缺口。

## 完成条件

- 两个隔离 worktree 内实现、测试、文档均完成，原工作树状态不变。
- XiangShan/NutShell 至少具备可配置、可批量、可超时、可分类、可重放的执行后端。
- 生成产物与目标 ISA/启动 ABI 匹配，raw image 不为空，所有 PT_LOAD 数据可达。
- 失败证据可以独立复现并用于社区 issue/论文实验记录。
- 无已知 checker 旁路、结果覆盖或 false-PASS 路径。
