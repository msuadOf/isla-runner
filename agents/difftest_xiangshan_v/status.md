# XiangShan RVV DiffTest 状态

## 2026-09-29：当前工作区 XiangShan 浮点重放完成

- **实施**：本工作区 `difftest-xiangshan/xiangshan/` 的独立 checkout HEAD `a13efc8775abb093e23727772a562f0605380685`、工作树干净；以 `NOOP_HOME`、`TMPDIR`、`JAVA_TOOL_OPTIONS` 均指向此 checkout 的构建环境，运行 `make emu CONFIG=MinimalConfig EMU_THREADS=4 -j16`，最终退出 0。实际 `build/emu` SHA-256 `871416926352103051fce0efac7bf219602547c0852d5aa24af0c01a35ea85ee`；同 checkout NEMU SO SHA-256 `9188e7dda30709962f0bfbc1dd87cea73d88a18c92c30892f93ed529c22def43`。编译器 `riscv64-unknown-elf-gcc 14.2.0+19`，消费端 `pipeline.py` SHA-256 `8099715d…22390c`。构建日志见[本地构建](../../difftest-xiangshan/work/float-v3-20260929/current-workspace-build-r2.log) SHA-256 `a5a936f2…2e3266`。
- **验证 PASS（本地可支持分区）**：冻结 IR `73dfb2e17bfbd67686442cc59bfd69e2ca84a497db345d04abb2916bfb671d2a`、Isla 二进制 `4e315e9a…59ae0`、FD 配置 `20851fdb…723d0` 的 51 个标量 JSON 共 1344 条。本地 1/1 烟雾通过；1322 条可支持分区（1145 Retire＋177 Illegal）最终 **1322/1322** 本地 `emu`/NEMU GOODTRAP、退出 0，ELF 内对 Isla post 的 32 个原始 FPR 位值和 `fcsr` 全部检查通过。24 路、30 秒首轮产生 104 成功＋31 超时后主动停止，已封存（31 条中 25 条 trace 到达 GOODTRAP）；120 秒、24 路第二轮含首轮 104 个成功记录，最终 1317 成功＋5 超时（5 条 trace 均到达 GOODTRAP）；5 个超时在 120 秒、5 路重跑中全部 2.3–3.4 秒通过。超时 trace 不直接计 PASS，只用最终正常退出记录计数。
- **范围与负对照**：22 条 `FCVT.BF16.S`／`FCVT.S.BF16` Retire 输入在本地 MinimalConfig 上 22/22 于 payload PC 报对应指令编码的 cause 2，属本配置不支持，未计入 1322 通过分区。故意仅翻转 FLI.S post `f0` 一位的本地负对照失败，commit trace 反复停在 `fp_post_park_f0` (`0x80000308`)，证明 post 检查实际生效。当前输入中未发现 XiangShan/NEMU 分歧或相对 Isla post 的浮点错误；这不覆盖 BF16 Retire，也不证明所有数值域或微架构无 bug。
- [本地机器核账](../../difftest-xiangshan/work/float-v3-20260929/current-workspace-audit.json) SHA-256 `97b8dfe3adf7e0727d449801c221e6a4a909297e02c9187672fb9452fcb610bf` 逐例绑定51份冻结求解JSON、输入、ELF 哈希、r1/r2/r3 正常退出与归属、22 条异常 trace、负对照、IR／Isla／配置／XiangShan／NEMU／pipeline 版本；核账命令为 `python3 difftest-xiangshan/audit_current_float_campaign.py --work difftest-xiangshan/work/float-v3-20260929 --stage isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/stage-v3 --emulator difftest-xiangshan/xiangshan/build/emu --diff-so difftest-xiangshan/xiangshan/ready-to-run/riscv64-nemu-interpreter-so --xiangshan-source difftest-xiangshan/xiangshan`，退出 0。管线测试在工作区 `TMPDIR` 下 77/77 通过。成功用例日志是 `HIT GOOD TRAP` 摘要，完整 commit trace 仅在超时／失败诊断中采集。此处是 XiangShan DiffTest＋上述 Isla post 检查，**不替代**同 IR 的 C++/Isla 全量重放、77 目标源码 branch 闭合或官方完整域求解。

**2026-09-29 范围修正（历史）**：下节旧 1322/1322 运行调用了另一工作区的 `emu` 与 NEMU SO，虽输入、ELF 和日志位于本仓库，仍**不符合用户要求的当前工作区代码与运行边界，不计本轮 XiangShan 验收**。原结果和哈希保留为历史诊断；[范围修正账本](../../difftest-xiangshan/work/float-v3-20260929/scope-correction.json) SHA-256 `58851f50…092c6d3`。后来在本工作区重新构建并运行，现行结果见上节。

## 2026-09-29：73df 直接入口的标量浮点 JSON 实跑

- 输入来自浮点议题的冻结 `stage-v3`：51 目标、1344 gen，IR SHA-256 `73dfb2e1…671d2a`，Isla 二进制 `4e315e9a…59ae0`，FD 配置 `20851fdb…723d0`。harness 新增完整 `isa-state-complete` 的 32 个 FPR/fcsr 装载，以及 `isa-state-post` 的逐寄存器原始位值检查；浮点输入缺字段或与 `isa-state` 冲突时硬失败。三条新增测试先红后绿，`test_pipeline.py` 70/70；实际 FLI.S 一条先过，故意翻转其 post `f0` 一位的真实 emu 负对照按预期失败并停在 `fp_post_park_f0`。
- XiangShan 源 HEAD `f86f50b834c26597426b5ede7c25afaff84d11ce`、MinimalConfig `emu` SHA-256 `48eeda61…ad53b7`、同 checkout NEMU SO `7b5a235c…127cd`、GCC 14.2.0+19。74 条分层试跑为 72 PASS＋2 BF16 Retire 失败；两条 payload 分别 `0x44807053` 和 `0x40607053`，commit trace 在 payload PC `0x80000188` 报 `Illegal Instruction` cause 2，随后进入不预期 trap 的停机循环。该 MinimalConfig 不支持这两种 Zfbfmin 转换，不能据此认定 XiangShan 功能 bug。
- 对其余 **1322/1322** 条以 `pipeline.py run --jobs 24 --timeout 30` 完整运行，全部 emu exit 0、GOODTRAP，Xi​​angShan/NEMU 无分歧，ELF 内对 Isla 的 FPR/fcsr post 检查全部通过；包括 1145 Retire、177 Illegal、892 个不同编码，覆盖 51 个源 JSON。22 条 BF16 Retire 单独以 `--jobs 24` 探测，22/22 失败；短 trace 和 11 条延长 trace 合计全部确认 payload 指令 cause 2。没有在本批可支持输入中发现香山 bug；输入值仍由原 JSON 决定，按汇编操作数名称计只有 142 条含非零浮点寄存器值，不能外推未覆盖的数值域。
- [逐例机器核账](../../difftest-xiangshan/work/float-v3-20260929/audit.json) SHA-256 `957ad2461e46f5e4ec6bcd154810cc4093bc81f2266997e7d4b2309c7ff29b59` 绑定输入分区、1322 个 ELF SHA/退出、22 条异常指令与 cause、负对照、IR/配置/运行器、真实 emu/NEMU 与 pipeline 版本。该结论是 XiangShan/NEMU DiffTest＋所列 Isla post 值检查；不是原议题的 C++/Isla 全量重放或 77 目标源码 branch 闭合。

以下“当前修改／约束／已验证／真实 DUT 构建”是早期 RVV smoke 的历史记录，所述 checkout 和环境判断只适用于当时；本轮标量浮点结论以本文件开头的当前工作区段落为准。

## 当前修改

- `difftest-xiangshan/pipeline.py`：小 JSON 选择、严格 VLEN 校验、逐条 ELF 构建和 DiffTest 批跑。
- `difftest-xiangshan/run.sh` / `run-docker.sh`：本地及 Docker 一键入口。
- `difftest-xiangshan/smoke/isla-v128-vsetivli.json`：使用 VLEN=128 Isla IR、`--timeout 60`、`zVSETIVLI` 生成的最小 V 扩展输入；`run-v128-smoke.sh` 固定使用它。

## 约束

- 历史 `VVTYPE` JSON 使用 256-bit vreg 状态，必须配合 VLEN=256 的 XiangShan emulator；实现拒绝静默截断。默认的 VLEN=128 smoke 改用不含 vreg 初值的 Isla `VSETIVLI` JSON。
- 当时环境尚未找到可用的 XiangShan `emu` 和匹配的 `riscv64-spike-so`，该句是早期记录；本轮已在当前工作区构建 `emu` 并配套 NEMU SO。

## 已验证

- 本机 `riscv64-linux-gnu-gcc` 已把四个样本编译为 ELF64 RISC-V，入口均为 `0x80000000`；每个汇编都包含原始测试编码与 `0x0000006b` GOODTRAP。
- fake emulator 完成 4/4 成功分类，覆盖逐 ELF 调用和 `--diff` / `--dump-commit-trace` 参数。
- Docker 镜像 `dx_run_difftest:latest` 已构建；用 `tests/tools` fake emulator 运行 `run-docker.sh` 后，临时名为 `dx_run_difftest` 的容器完成 4/4，并被 `--rm` 自动移除。
- 用 `--vlen-bits 128` 构建该 256-bit JSON 被预期拒绝。

## 真实 DUT 构建

- 已 clone 官方 XiangShan 源码及必要子模块到 `difftest-xiangshan/xiangshan/`，固定主仓库 commit 为 `7bf51a8`；其 `ready-to-run/riscv64-nemu-interpreter-so` 已存在。
- 官方 `make emu CONFIG=MinimalConfig EMU_THREADS=4 -j16` 已完成，真实 Verilator emulator 位于 `difftest-xiangshan/xiangshan/build/emu`。
- `./run-local-xiangshan.sh` 已在真实 XiangShan emulator 加载 `ready-to-run/riscv64-nemu-interpreter-so` 后执行完成：4 个由 Isla JSON 衍生的 RVV ELF 全部返回 GOODTRAP，汇总为 `work/elf/results.json` 的 `4/4 success`。
- `./run-v128-smoke.sh` 已在真实 XiangShan MinimalConfig（VLEN=128）和同源码树 NEMU 上完成：Isla 生成的 `vsetivli x31, 0x0, 0x4` 被编译为入口 `0x80000000` 的 ELF，DiffTest 结果为 `1/1 success`。该样本没有 vreg 初值，因此没有使用 reset-zero 截断规避。
