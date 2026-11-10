# 内存符号化架构调研计划

日期：2026-11-02。

## 目标与范围

核对指定 Isla 内存一致性工作树与 isla-testgen 的当前机制，比较 angr/KLEE/QEMU/AFL 的内存表示，形成面向 Sail 规范执行的初步技术结论。只研究，不修改生产源码、不运行新性能基准或硬件测试。

## 热点文件

Isla 的 src/isarch/memory_model.rs、isla-lib/src/memory.rs、src/isarch/target.rs、memory_builder.rs、executor/frame.rs 与 smt.rs；外部 isla-testgen 的 src/execution.rs、src/target.rs；现有协同审阅和修复记录。

## 步骤与验证

1. 阅读根入口、术语与表达规则，保存工作树版本边界。
2. 核对数组读写、初态、回调、fork、checkpoint 和最终模型输出。
3. 区分 bdd047bc 的旧探针结论与当前在途修复；记录源码指纹。
4. 从上游实现和文档核对比较工具；区分机制事实与性能假设。
5. 形成报告、同步可复用发现和状态；核对链接与文档一致性。

## 未决

本轮没有同覆盖性能数据；候选分页/混合后端收益待实验。当前正确性修复仍由原议题管理，本报告不宣布其验收。
