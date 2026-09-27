# Isla → XiangShan RVV DiffTest

## 版本管理与存档

本目录的 Python/Bash 工具、Dockerfile、测试、smoke 输入和 `poc-final/*.S` 由外层 `isla-runner` 主仓库管理。`xiangshan/` 是独立上游 checkout，未作为本目录源码提交；克隆主仓库不会自动获得它。可按根目录初始化说明准备上游仓库，再选择与实验记录匹配的版本和构建配置。

`inputs/`、`work/`、PoC ELF 和 `emu-baseline-*` 是本地运行数据，保留原路径并忽略。2026-09-21 整理快照见 [根目录存档](../archives/xiangshan/2026-09-21-harness/README.md)：输入、复现文件及结果摘要纳入主仓库；完整 work 树与旧模拟器的本地大档案只登记哈希，不包含在普通 Git clone 中。

测试目录的 `fake_diff.so`、`tests/tools/*-so` 是文本测试替身，应随测试提交；不能按 `.so` 后缀清除。现有模拟器与结果不因纳入 Git 而成为本轮重新验证的结果。

这个目录提供 Isla V 指令 JSON 到 XiangShan DiffTest 的端到端链路：保留每条 JSON 的寄存器上下文和 payload 指令，逐条生成 XiangShan 入口为 `0x80000000` 的 ELF，再通过官方 `emu -i ELF --diff riscv64-nemu-interpreter-so --dump-commit-trace` 执行。

默认输入是 `smoke/isla-v128-vsetivli.json`：由 Isla 在 VLEN=128 IR 上以 `--timeout 60` 运行 `zVSETIVLI` 得到的一个 V 扩展样本。该样本不含向量寄存器初值，因而不存在 256/128 位截断；它用于验证 V 扩展的 JSON→ELF→XiangShan+NEMU 链路。

## 一键运行

先准备来自同一 XiangShan 构建的 `emu`，以及该构建匹配的 NEMU DiffTest 动态库 `riscv64-nemu-interpreter-so`：

```bash
export XIANGSHAN_TOOLS=/absolute/path/to/tools
export XS_VLEN_BITS=128
./run-docker.sh
```

脚本默认通过 XiangShan emulator 的 `--diff` 参数连接 NEMU。若要改用其他官方参考模型，例如 Spike：

```bash
export XIANGSHAN_DIFF_SO_NAME=riscv64-spike-so
./run-docker.sh
```

容器固定命名为 `dx_run_difftest`，结束后自动移除。产物和逐例 `difftest.log` 在 `work/elf/case-*/`，汇总在 `work/elf/results.json`。

不用 Docker 时可设置 `XIANGSHAN_EMU`、`XIANGSHAN_DIFF_SO` 后执行 `./run.sh`。

本地工作区已准备官方 XiangShan 源码 `xiangshan/`（不随本 harness 提交，新 clone 需单独准备）。在该上游目录完成 `make emu CONFIG=MinimalConfig EMU_THREADS=4 -j16` 后，直接执行：

```bash
./run-v128-smoke.sh
```

它固定 `XS_VLEN_BITS=128`，使用 `xiangshan/build/emu` 与 `xiangshan/ready-to-run/riscv64-nemu-interpreter-so`。汇总结果为 `work/elf/results.json`。

## VVTYPE 全量上下文回放

先在 Isla 生成 VLEN=128 的最新 JSON，再将全部条目放入本目录并逐条测试：

```bash
cd ../isla
rm -rf output/ && make solve-VVTYPE THREADS=8

cd ../difftest-xiangshan
python3 pipeline.py prepare-json \
  --source ../isla/output/rv64_zVVTYPE.json \
  --vlen-bits 128 \
  --output inputs/rv64_zVVTYPE.json
python3 pipeline.py build \
  --input inputs/rv64_zVVTYPE.json \
  --vlen-bits 128 \
  --output work/vvtype-vcontext/elf
python3 pipeline.py run \
  --cases work/vvtype-vcontext/elf \
  --emulator xiangshan/build/emu \
  --diff-so xiangshan/ready-to-run/riscv64-nemu-interpreter-so
```

`prepare-json` 默认保留全部 JSON 条目，即使 payload 编码相同但寄存器上下文不同也会生成不同 ELF。每个 ELF 在执行 payload 前按 JSON 设置 `vtype`、`vl`、`vstart`、`vcsr`（`vxrm`/`vxsat`）与所有 `vr*`；`cur_privilege=User`/`Supervisor` 会通过 `mret` 进入对应特权级。为保证测试映像在降权后仍可取指，入口会先配置一条只服务于测试的全地址 RWX PMP 规则。

仓库内的 `tests/tools/` 仅供 CI/本地 smoke：它模拟 emulator 输出 `HIT GOOD TRAP`，用于验证 Docker、JSON、ELF 和批处理连接；它不是 XiangShan，也不能替代真实 DiffTest 结论。

若要转换其它 Isla JSON，可显式传入输入文件：

```bash
ISLA_JSON=/absolute/path/to/isla.json XS_VLEN_BITS=128 ./run-local-xiangshan.sh
```

## 内存上下文重放

Isla 输出的 `pre-memory`（首触内存，首触写为 `value: null`）、`post-memory`（最终字节）与 `memory-events`（访存事件，仅抄录诊断）会被 `pipeline.py` 消费，重放到生成的 ELF 中：

- **初始内存（pre）**：payload 前按 JSON 给定序（即重放序）逐段逐字节 `sb` 恢复，只用 `t0`/`t1`，插在特权/向量设置之后、标量 `li` 之前，不破坏 JSON 标量初值；`value: null` 的自由字节按固定 `0xA5` 填充（非零模式，避免掩盖"硬件恰返回复位零"类问题）。地址为 null 的段跳过并计数。
- **最终字节检查（post）**：payload 后逐段逐字节 `lbu` + `bne` 与模型期望比对，任一失配跳该段专属 `post_park_N` 标号（死循环，run 侧超时判 failure，commit trace 末 PC 定位失配段）；全过才执行 GOODTRAP。地址或 value 为 null 的检查段跳过并计数；若全部 post 段皆 null，整条跳过（`skipped_reason: post-all-null`）。
- **fault 路径**：复用既有 `expects_trap` 哨兵机制（payload 处 trap → handler 按 `mepc==payload_ins` 判 GOODTRAP），不做 mcause/mtval 断言（后续工作）。
- **fault 预分类（W13 对账）**：`build` 解析 fault 条目的 zSTORE 有效地址（`test-ins` 偏移 + `isa-state` 基址），对照 emu 实际有效 RAM [0x80000000,0x80000000000)（8TB，探针+源码实测；difftest csrc 的 256MB DRAM 宏对该 emu 不适用）预分类：
  - 低位错位（有效地址 <0x80000000 且未对齐）：emu 报 access fault（mcause7）、NEMU 报 store misaligned（mcause6），difftest 对 mcause 分歧直接 ABORT——两侧都 fault、Isla 判 fault 正确，属工具链级真分歧，跳过重放并计数（`skipped_reason: lowaddr-misaligned-mcause-divergence`）。
  - 图内对齐（[0x80000000,8TB) 且对齐）：Isla 历史上因 PMP 符号化产出假 fault（W13 全量 107/2479）；isla 侧在 `[registers.defaults]` 钉死 PMP 后应消失。**不跳过**，仅标注计数（`preclass: in-map-aligned-fault`，进 `build-summary.json` 的 `preclass`），出现即提示上游回归。
  - 图内错位（emu 支持错位退休 vs Isla `plat_enable_misaligned_access=false`）为另一真分歧（W13 ⑤），当前用例集未触发，不在此处理。
- **符号边界地图假设过滤（S4，W17 配套）**：Isla `[[pma_regions]] size="symbolic"` 求解的用例，每条路径 `isa-state` 携带 `pma_regions.<name>.size` 模型值（侧通道；fault 路径 `memory-events` 为空）。`build` 对含该键的路径执行 S4 oracle 过滤——路径期望行为必须在目标平台真实地图下成立：成功路径要求有效地址 < 真实顶界、fault 路径要求 ≥（有效地址复用 zSTORE 解析：指令偏移 + 基址寄存器，与 fault 预分类同源）；不成立则跳过（`skipped_reason: map-hypothesis-mismatch`，计入 `build-summary.json` 的 `skipped` 与 `map_hypothesis{checked,skipped}`）。此类路径的价值在生成期一次求解覆盖多地图假设，不在固定平台重放。无符号 size 的条目零影响；含符号 size 却无法解析有效地址的条目构建期报错（宁可失败也不重放未核实的假设）。
- **真实顶界配置**：默认 `0x80000000000`（emu 实测有效 RAM 顶界，模块常量 `EMU_RAM_LIMIT`），`build --map-limit 0x...` 可覆盖（如重放到可配地图的平台）。假设顶界（base+size）仅为诊断记录，不参与判定：JSON 不携带 base 字段，按约定单 region `ram` 取 DRAM 基界 `0x80000000`（`EMU_RAM_BASE`，与 W17 符号配置一致），连同 region/size/top/address/一致性写入 `manifest.json` 与 `case.json` 的 `map_hypothesis` 字段，其中 `hypothesis_consistent` 校验该 base 约定与 ret_val 是否自洽、`consistent_with_real_map` 是过滤判定本身；多符号 region 只记录各 size、top 置空。
- **代码窗口（两遍构建）**：第一次链接后解析 ELF 各 ALLOC section 的实际占用区间，pre/post/memory-events 触碰地址与代码（含 `.data`）重叠的条目精确跳过（`skipped_reason: code-overlap`，汇编保留供诊断），避免前导 store 覆写自身代码；其余条目再链接一次生成最终 ELF。无 vreg 初始状态的条目不发射占位 `.data`：原 8 字节 `vector_initial_state` 占位恰落在链接脚本的 0x80001000 对齐位，会与以该地址为访存窗口的用例相撞而误判 code-overlap，且占位无任何引用。
- **采样**：默认全量；大批量可用 `build --sample-mode first-per-encoding` 每个编码仅保留首条。
- **产物**：`manifest.json` 逐条含 `path_class`（`ok`/`fault`）、`memory` 计数与 pre/post/events 抄录、fault 条目的 `preclass` 标注、符号边界条目的 `map_hypothesis` 记录；`build-summary.json` 汇总 built/skipped/path_class/preclass/map_hypothesis 计数；`run` 自动跳过无 ELF 的条目。

```bash
python3 pipeline.py prepare-json --source /path/to/rv64_zSTORE.json --vlen-bits 128 \
  --ret-val-regex '^Retire_Success' --output work/store-mem/ok.json
python3 pipeline.py build --input work/store-mem/ok.json --vlen-bits 128 \
  --output work/store-mem/elf --jobs 8
python3 pipeline.py run --cases work/store-mem/elf \
  --emulator xiangshan/build/emu \
  --diff-so xiangshan/ready-to-run/riscv64-nemu-interpreter-so
```

## 边界

- JSON 中存在 vreg 初始状态时，`XS_VLEN_BITS` 必须与其 bit width、以及 XiangShan 构建参数一致；宽度不一致时流程会失败，绝不截断或补零。
- 合法 `vtype` 的 JSON 必须提供 `vl`；Isla 的 V 上下文导出会为未约束的 `vl`、`vstart`、`vcsr` 完成模型具化，保证完整重放。
- 退出使用 XiangShan DiffTest 的 custom `0x0000006b` GOODTRAP 编码，异常或无 GOODTRAP 均被当作失败。

## 挂死问题必须保存 itrace

对“指令不退休”或“核心挂死”的问题，超时、cycle 上限和 GOODTRAP 不可达只能证明现象，不能定位最后退休的指令或 RTL 内部卡点。提交 issue 前必须保存同一份新编译 ELF 的 itrace/commit trace **和 `EMU_TRACE` 波形**；报告最后退休指令与第一条未退休指令的反汇编地址和编码，并保留覆盖该窗口的 VCD。

先用 `--no-diff` 确认纯 RTL 挂死；再用匹配的 NEMU SO 和 `--dump-commit-trace` 保存定位证据：

```bash
# 先构建带 VCD 支持的 emulator；不要复用未开启 EMU_TRACE 的 emu
cd xiangshan
NOOP_HOME=$(pwd) make emu CONFIG=MinimalConfig EMU_THREADS=4 \
  SIM_ARGS=--fpga-platform EMU_TRACE=1 -j4

# 纯 RTL：确认挂死
./build/emu -i ../poc.elf --no-diff -C 2000

# itrace：定位最后退休/第一条未退休指令
./build/emu -i ../poc.elf \
  --diff ready-to-run/riscv64-nemu-interpreter-so \
  --dump-commit-trace -C 2000 > ../commit-trace.log 2>&1

# VCD：覆盖同一 cycle 窗口；--dump-wave-full 需要 EMU_TRACE=1
./build/emu -i ../poc.elf --no-diff -C 2000 \
  --dump-wave-full --wave-path ../hang-window.vcd
```

`--dump-commit-trace` 是 DiffTest commit trace；`--no-diff` 的超时输出不能代替 itrace。`EMU_TRACE=1` 是 VCD 的构建期开关，运行时 `--dump-wave-full` 不能补救未开启该开关的 emulator；波形与 commit trace 都是挂死报告的必需证据，不能互相替代。
