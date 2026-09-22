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
