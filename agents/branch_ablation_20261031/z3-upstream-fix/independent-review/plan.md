# 独立审查安排

两位独立reviewer分别审查源码语义与动态边界，只写各自semantics/或boundaries/目录。共同受审版本哈希见reviewed-snapshot.json，主agent在收到发现前冻结源码，避免审查漂移。审查覆盖：可识别片段、dt2bv约束/模型转换、SAT/UNSAT、假设/增量、proof/core与非目标类型；不能用有限输入宣称所有任务性能单调提升。

主agent核实问题、先修阻断再复审，最终保留新旧报告适用版本及未验证条件。未得到独立报告前不写独审通过。
