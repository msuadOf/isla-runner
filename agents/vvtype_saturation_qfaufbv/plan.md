# VVTYPE saturation qfaufbv 超时修复计划

## 目标

在不固定 `vtype`、`vl`、`vstart`、mask 或寄存器选择的前提下，改写 Sail RISC-V 的定点饱和逻辑，避免 `VVTYPE` 在 `signed_saturation` 上界判定处形成 `qfaufbv` 长尾查询，并保持原 RISC-V 语义及 `vxsat` 副作用。

## 已确认现象

- timeout dump 对应旧 IR 的 `signed_saturation_result` 上界判断：`signed(elem) > signed(0b0 @ ones(len - 1))`。
- dump 已把 `len` 收敛为 64，但查询同时包含符号向量寄存器选择链、VSMUL 算术和 vtype 路径约束；整数化的有符号边界比较成为 `qfaufbv` 的慢查询点。
- 已有 first-party 回归测试 `test_vvtype_masked_vxsat.S`，用于检查 masked-off 饱和不能错误设置 `vxsat`。

## TDD 与实现步骤

1. 先运行现有 `test_vvtype_masked_vxsat.S`，记录修改前结果。
2. 为饱和值计算补充边界测试，覆盖：未溢出、正溢出、负溢出，以及 `vxsat` sticky 行为。
3. 在 `vext_utils_insts.sail` 的 SYMBOLIC 路径中，将“转无界整数后与动态 max/min 比较”改成“截断后再符号扩展，与原值比较”的位向量可表示性判断：
   - `truncated = elem[len - 1 .. 0]`
   - `overflow = elem != sign_extend(truncated)`
   - 由原始符号位选择 signed min/max
4. 饱和 helper 返回 `(result, saturated)`，由调用点结合 lane mask 更新 `vxsat`，避免 masked-off lane 产生副作用。
5. 仅生成 `generated_isla_rv64d` IR，不编 emulator；同步 Isla 使用的 `rv64d_v128_e64.ir`。
6. 串行运行 `VVTYPE`：总时长 40 分钟、CLI timeout 30 分钟、SMT timeout 10 分钟、thread interrupt feature，检查是否仍有 SMT timeout。
7. 运行格式/差异检查并把结论记录到 `status.md` 与 `agents/findings.md`。

## 修改边界

- 保留 `sail-riscv` 和 `isla` 当前所有既有 staged/unstaged 改动。
- 不修改 Z3 tactic，不固定运行态 CSR，不引入 fallback。
- 优先只改 saturation helper 及其必要调用点和测试。
