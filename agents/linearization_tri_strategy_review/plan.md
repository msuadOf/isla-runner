# 函数线性化三策略评审计划

目标：核查 none/full/bounded 的语义、加载顺序、类型及覆盖边界。
范围：静态审查当前 Isla 与 Sail-RISC-V，不修改生产代码或冻结实验。
热点：isla/src/opts.rs、isla-lib/src/ir/{linearize,partial_linearize,ssa}.rs、executor.rs、primop_util.rs、config.rs 与 model/sys/vmem_pte.sail。
步骤：核对既有调查；追踪改写及 SSA；核查 ITE/Union、断言与覆盖；提出验收要求。
验证：源码核查；本轮不复现崩溃，不新增动态或性能 PASS。
未决：用户崩溃所用版本、IR、命令及回溯；等覆盖端到端收益。
