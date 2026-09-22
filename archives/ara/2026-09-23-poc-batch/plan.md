# Plan: Ara 处理器批量 PoC 测试（isla solve 输出 → Ara 仿真）

日期：2026-09-16

## 目标

1. Clone Ara 处理器仓库（含其向量测试套件/RVVTS 相关子模块）到 `ara/ara`。
2. 把 `isla/output/`（`make solve` 产物，约 19908 条，vreg 宽度 128-bit）中的单指令用例包装成符合 Ara 测试环境约定的 PoC（含向量上下文初始化、退出测试环境的操作）。
3. 在 Ara 的 Verilator emulator 上批量运行，分类汇总结果。

## 步骤

1. **Clone**：`git clone --recursive https://github.com/pulp-platform/ara.git ara/ara`（已完成，commit 34bd3bc1；重 toolchain 子模块不拉取）。
2. **环境调研**（Explore agent ×2 后台）：
   - 测试二进制约定：退出机制（tohost/exit）、boot 流程、最小裸机 .S 骨架、编译 flags。
   - 仿真构建：verilate 目标、Bender 依赖、Verilator 版本兼容、config（VLEN）选择。
3. **构建 emu**：按调研结论用系统 Verilator 5.038 或 pin 版本构建；选择与 isla 输出 vreg 宽度匹配的 VLEN 配置（当前输出为 128-bit）。
4. **PoC 生成器**（放 `ara/` harness 目录，复用 `assembly-gen` 的 `Value`/模板/V_INIT 思路）：
   - 解析 `isla/output/rv64_z*.json` 的 `gen[]`：`test-ins-encdec`（.insn 编码）、`isa-state`（GPR/FPR/CSR/vtype/vl/vstart/vr*）。
   - 生成骨架：`_start` → 标量/CSR/V 初始化 → 测试指令 → 按 ret_val 期望走 PASS/FAIL 退出。
   - 只对 `Retire_Success` 用例生成 V1；Illegal 类按 trap 处理（V2 可选）。
5. **批量运行**：并行跑 emu（xargs -P），超时控制，按 clause × 结果聚合矩阵；默认每 clause 抽样 N 条（全量 19k 太大），参数可调。
6. **记录**：结论写入 `agents/findings.md`，进展写入本目录 `status.md`。

## 风险

- Verilator 5.038 与 Ara pin 版本不兼容 → 需要额外构建 pin 版 Verilator（时间成本）。
- VLEN 不匹配（Ara 配置 vs isla IR 的 128-bit）→ 需重生成 IR 或筛选用例。
- 19k 用例 × 每次仿真启动开销 → 用抽样与并行控制规模。
- isla 输出含 Zvbb/Zvk* 等扩展指令，Ara 只支持 RVV 1.0 base → 预期大量 illegal trap，作为 unsupported 分类而非失败。
