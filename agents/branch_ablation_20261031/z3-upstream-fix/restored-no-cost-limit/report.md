# 按用户要求移除4096成本护栏（2026-11-01）

用户认为性能退化可以接受，要求恢复逻辑。本轮仅移除enum模型成本计数/4096分发限制及对应护栏策略回归；恢复所有原受限类型片段的FP＋有限枚举走dt2bv→qffp。类型安全范围、proof/core绕过和原is-qffp语义不变。保留独审发现后增强的自由枚举排除全部构造器UNSAT测试，不恢复原不足测试。

构建z3/test-z3/libz3成功；fpa/check_assumptions/bit_vector/get_consequences/model_evaluator五组测试均退出0。此前护栏版独立review结果仅适用guarded-snapshot；初版独审中大枚举性能P2是实际存在的开销，本轮按用户选择不再抑制，不能继续写成当前版已关闭。

为避免前次护栏版几毫秒比较造成误解，恢复后用相同轻量FP＋独立枚举公式、CPU100、AB/BA/AB三对重测。以下是同一当前二进制default/qffp的进程墙钟中位数：

| 构造器×变量 | 无护栏default秒 | 直接qffp秒 |
| --- | ---: | ---: |
| 512×256 | 0.490857 | 0.045279 |
| 1024×256 | 0.896431 | 0.045038 |

这是移除护栏后枚举模型展开带回的开销；前次约2–3ms差异属于护栏版，不适用当前版。全部12个比较运行均SAT；这里只测试成本暴露probe，不外推所有工作负载/Clause性能。命令/输出见[comparison-results.json](comparison-results.json)，测试退出见[tests.json](tests.json)。当前源码/二进制/补丁哈希以父目录manifest.json为准；guarded-manifest/guarded-default-fp-enum.patch保留供历史核账。

系统Z3、生产Isla/Sail与根float/memory组件未改；未发布PR或更新官方issue。
