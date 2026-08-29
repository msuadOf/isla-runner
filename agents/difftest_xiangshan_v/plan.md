# XiangShan RVV DiffTest 支持计划

1. 从已存在的 Isla `VVTYPE` JSON 中选择少量 RV64 V 指令，避免重新符号执行全量 V 子句。
2. 在 `difftest-xiangshan/` 生成每指令一个 XiangShan 兼容 ELF，并保留向量状态宽度检查。
3. 使用官方 emulator 与 DiffTest `.so` 的参数约定批量执行，并提供命名为 `dx_run_difftest` 的 Docker 一键入口。
4. 以交叉编译产物和 fake emulator 验证内部链路；若本机没有真实 XiangShan 产物，明确记录为外部验证缺口。
