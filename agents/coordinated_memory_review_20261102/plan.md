# Sail-RISC-V 与 Isla 内存协同审阅计划

日期：2026-11-02。用户要求同时审阅两个目录，按改动合理、沿用原有代码结构的口径判断是否可接受。

- 版本：Sail-RISC-V `feat/sail-riscv-memory-by-model-20261022@c70482a7`，基线 `4f2ac293`；Isla `feat/memory-consistency@bdd047bc`，专项基线 `f06371f`。后者基线已有 isarch 与执行限制，不将所有相对上游 master 的历史改动算成本次新增。
- 范围：segment 寄存器组界、共享 vstart 策略、IR 来源及预算坐标、MemoryCallbacks/SeqMemory、PMA/CSR 注入、最终见证与重放合同。
- 热点：模型 `vext_utils_insts.sail`、`vext_mem_insts.sail`；Isla `memory.rs`、`memory_model.rs`、`target.rs`、`exec.rs`、`ir.rs`、`smt.rs`。
- 步骤：先核对版本及未提交内容；沿源码审阅；在独立目录重跑最小反例与正面探针；区分结构判断、确证回归和既有能力缺口；保存结论及证据。
- 验证：完整现有 IR 的有界指令探针，记录命令、二进制/IR/配置哈希和退出；逐文件核对 provenance；核对 workaround 坐标。未新构建或运行硬件时明确注明。
- 边界：不修改生产源码、分支、索引、共享 target 或既有输出；Isla 的 README/scripts/run.mk 已有未提交修改须保留。审阅脚本和结果写本目录；后态断言实验的隔离IR副本写根仓`.tmp/coordinated_memory_review_20261102/`，生产IR不改。
- 未决：旧审阅中的 concrete/数组分离、GPR 漏导出和异常返回值问题是否仍适用；vstart 非陷阱策略在所有调用者的成功后态是否完整。
