# 内存符号化架构调研状态

2026-11-02：初步调研完成。已核对指定 worktree、isla-testgen 及 angr/KLEE/QEMU/AFL 上游来源，形成[架构报告](report.md)；[计划](plan.md)、[源码指纹](source-fingerprints.json)。

结论：保留 Sail 语义层与字节数组内容层；先闭合具体/符号初态和最终模型见证，再测量快照复制、alias、路径分叉及 checkpoint 重放。稀疏分页是候选优化，不替代 MMU/PMA/PMP，也不自动降低符号地址开销。

观察时 Isla HEAD bdd047bc 加在途修复；旧反例与当前实现分开记录。读取期间源码有变化，指纹记录对应时刻。未修改生产源码、未构建、未新跑动态测试/基准或硬件，无新增 PASS。修复验收仍见[原议题](../coordinated_memory_fixes_20261102/status.md)。
