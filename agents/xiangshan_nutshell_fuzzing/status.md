# XiangShan / NutShell fuzzing 支持状态

## 当前状态

状态：隔离 worktree 中实现、审计修复和本地验证已完成；等待真实 XiangShan/NutShell emulator + diff-so smoke。

## 已完成

- 已确认用户目标是面向开源 CPU 的 bug 发现、社区提交和论文复现实验，不存在任务拒绝。
- 已确认仓库内没有 `disasemble-gen`，本任务按 `assembly-gen` + `difftest` 的端到端链路处理。
- 已创建两个独立 worktree：
  - `.worktrees/assembly-gen-xiangshan-nutshell`，`feature/xiangshan-nutshell@3f5fe7e`
  - `.worktrees/difftest-xiangshan-nutshell`，`feature/xiangshan-nutshell@a82afd8`
- 两个原工作树中的未提交修改和生成物均未触碰。
- `assembly-gen` 隔离基线测试：46 passed。
- 已固定并只读分析参考项目：
  - DiveFuzz `3c1991c8`
  - DRVFuzz `eb52806c`
- 已完成本地 `assembly-gen`、`difftest/run_difftest`、RTLSim、report 链路的只读映射。
- 已完成平台 profile、完整 ELF→BIN/IMG/HEX、构建 manifest、外部 emulator runner 与 PT_LOAD loader；审计后补齐 V ISA/VS、trap fail-closed、raw artifact/manifest、分类、证据 identity、进程组清理和 LMA/VMA guard。
- 最新验证：assembly-gen `71 passed`；difftest runner/loader `8 passed`；Ruff py38、Python 编译和两个 worktree `git diff --check` 通过。Rocket/BOOM 已在容器中使用真实 checker 各 `1/1 PASS`（修复前的 PT_LOAD 版本）。

## 已识别的关键问题

- `assembly-gen` 当前 `.bin/.hex` 只抽 `.text`，而入口代码在 `.text.init`，现有 raw 产物实际为空或近空。
- 当前 privilege 宏只改 MPP，没有执行 `mret`，User/Supervisor 用例仍在 M-mode。
- 原工作树 V 初始化产生 `.data.vr_init`，现有 RTL loader 不装载该段，向量初值会静默变为 0。
- 本地 Cocotb adapter 只支持 Rocket/BOOM TileLink；XiangShan/NutShell 更适合先采用官方 emulator + diff-so 后端。
- `difftest` 原脏树含一个 SUCCESS 后直接 `continue` 的未提交逻辑，会跳过 checker 和结果记录；不会带入隔离分支。
- 单目标结果路径无法表达 target×case 矩阵，必须按 target 隔离输出。

## 实现热点

- `assembly-gen/main.py`
- `assembly-gen/src/assemgen_core.py`
- `assembly-gen/resource/riscv/`
- `assembly-gen/resource/riscv/scripts/compile.mk`
- `difftest/difuzz-rtl/run_difftest/`
- `difftest/difuzz-rtl/Fuzzer/RTLSim/host.py`

## 剩余验证缺口

本机未提供 `XIANGSHAN_EMU`、`XIANGSHAN_DIFF_SO`、`NUTSHELL_EMU` 或 `NUTSHELL_DIFF_SO`，因此尚不能宣称真实开源 DUT 已跑通。具备匹配提交的二进制后，应使用 `external_targets.example.json` 对 assembly-gen 的 raw `.img` 运行双 target smoke，并确认真实 GOODTRAP、commit trace 与 negative-case 分类。
