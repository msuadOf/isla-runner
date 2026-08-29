# XiangShan RVV DiffTest 状态

## 当前修改

- `difftest-xiangshan/pipeline.py`：小 JSON 选择、严格 VLEN 校验、逐条 ELF 构建和 DiffTest 批跑。
- `difftest-xiangshan/run.sh` / `run-docker.sh`：本地及 Docker 一键入口。
- `difftest-xiangshan/smoke/isla-v128-vsetivli.json`：使用 VLEN=128 Isla IR、`--timeout 60`、`zVSETIVLI` 生成的最小 V 扩展输入；`run-v128-smoke.sh` 固定使用它。

## 约束

- 历史 `VVTYPE` JSON 使用 256-bit vreg 状态，必须配合 VLEN=256 的 XiangShan emulator；实现拒绝静默截断。默认的 VLEN=128 smoke 改用不含 vreg 初值的 Isla `VSETIVLI` JSON。
- 当前环境尚未找到可用的 XiangShan `emu` 和匹配的 `riscv64-spike-so`，真实 DUT 烟雾测试待其可用后执行。

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
