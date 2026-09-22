# 状态

整理注（2026-09-23）：本文的“未暂存或提交”描述原执行轮次；当前子仓库暂存状态以 Git 为准。本轮只保留并暂存本文档，不更改 Sail-RISC-V 的源码或索引。

重构完成，修改 sail-riscv/model/extensions/V 下 vext_arith_insts.sail、vext_control.sail、vext_utils_insts.sail，净减少 249 行。未暂存或提交。

验证通过：
- RV64 VLEN256/ELEN64 普通模式与 SYMBOLIC 模式 Sail 严格类型检查。
- CMake generated_sail_riscv_model 的 C++ 代码生成。
- Isla 后端 RV64 IR 生成，产物 /tmp/sail-refactor-rv64d.ir。
- git diff --check。

未运行指令回归测试或性能对比。保留 Isla 原语及原有开关行为。构建中 CLI11 下载最初被沙箱阻止，经授权重试成功。

## 后续完整构建验证

- cmake --build build -j4 成功，最终 sail_riscv_sim target 100%。日志 /tmp/sail-symbolic-dedup-build.log。
- 独立重新生成 RV64 VLEN256/ELEN64 Isla IR 成功，产物 /tmp/sail-symbolic-dedup-ir-ysltsb8v/rv64d.ir，15398208 字节；generation.log 同目录。
- RV32/RV64 的 misaligned_vector_register_groups、v_fixed_rounding、vvtype_masked_vxsat 六项 CTest 全部通过。
- 生成 IR 中 vector_select_masked 仍调用 isla_vector_select。未运行符号执行性能对比。
