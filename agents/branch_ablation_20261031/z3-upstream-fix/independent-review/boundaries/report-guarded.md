# 成本护栏版独立复验

原报告的两项P2已在本轮受测范围内解决：大枚举查询恢复原策略，原100毫秒反例三次双侧均SAT；正式域约束测试已移除固定构造器，必须排除非法编码才能证明UNSAT。未发现新的逻辑错误或护栏绕过，不保留这两项为未修P2。小额分发／probe开销仍然存在，不能将结论写成所有输入都会更快。

本次仅审阅主agent冻结的护栏版四文件补丁与实际 `dt2bv`／`test(goal, predicate)` 实现；未改源码、重编译或读另一位reviewer报告。受测源码、z3和libz3哈希全部匹配 `independent-review/guarded-snapshot.json`，自报版本仍为同基线master 5.3.4。逐项核账见 [guarded-source-manifest.json](guarded-source-manifest.json)。旧版 [report.md](report.md) 与原始结果保持原状。

## 两项修复的证据

1. **模型转换成本护栏有效。** 对唯一枚举自由常量累计对应构造器数，超过4096拒绝新路径。`src/tactic/goal.h:233–242` 的 `test` 在整个goal共用一个visited标记，不会因跨断言重复引用而重复计数。`size > max-current` 在累加前判断，维持 `current <= 4096`，没有无符号下溢／加法溢出的入口。计数跨sort累计，构造器自身不计入自由常量模型ITE成本。
2. **域约束回归确实增强。** `src/test/fpa.cpp` 原枚举域UNSAT删除 `mode=F`，只保留自由mode排除全部六构造器。独立运行该精确形状得到UNSAT，verbose包含dt2bv；见 [guarded-domain-test.json](guarded-domain-test.json)。1／3／6基数的排除全部与鸽巢例也全部再次通过。

护栏分发边界用verbose核对实际路径，结果全部符合预期：

| 公式成本 | 预期／实际 |
| --- | --- |
| 128构造器×31常量＝3968 | 进入dt2bv |
| 128×32＝4096 | 进入dt2bv |
| 4097×1＝4097 | 保留原策略 |
| 3×1365＝4095 | 进入dt2bv |
| 3×1366＝4098 | 保留原策略 |
| 1024构造器，同一个常量在100个不同Bool公式中出现 | 去重后进入dt2bv |
| 两个sort，各1024构造器×3常量，合计6144 | 保留原策略 |

见 [guarded-results.json](guarded-results.json)。以上全部SAT，不将“护栏拒绝”误记为逻辑UNSAT。此门槛约束的是枚举模型转换规模，不能对FP电路规模、所有前处理成本或总耗时作上界保证；这些成本不是此次新增枚举展开引入的同一问题。

## 性能反例复验

CPU100，三次AB／BA／AB，独立进程，均SAT。护栏版与baseline在本轮环境内比较，不把跨轮墙钟直接作精确加速比。

| 构造器×变量 | baseline中位秒 | 护栏版中位秒 |
| --- | ---: | ---: |
| 6×256（低于门槛） | 0.02710 | 0.03934 |
| 128×64 | 0.02533 | 0.02956 |
| 512×256 | 0.03259 | 0.03653 |
| 1024×256 | 0.03383 | 0.03823 |

原大枚举10.7／18.6倍退化已消除，剩余毫秒级probe／分发开销仍可观察。512×256原反例加100毫秒timeout后三次baseline／护栏版全部SAT，不再复现修前SAT／候选UNKNOWN。见 [guarded-performance-results.json](guarded-performance-results.json)、[guarded-timeout-results.json](guarded-timeout-results.json)。4096阈值是控制新增成本的工程选择，未证明它是最优阈值；不将这些样本外推为普遍性能保证。

## 功能和模型回读复验

执行入口：

```sh
taskset -c 100-111 /usr/bin/python3 agents/branch_ablation_20261031/z3-upstream-fix/independent-review/boundaries/guarded.py
taskset -c 100-111 .tmp/z3-enum-fp-default/build/test-z3 fpa
```

原55例双侧共110运行全部通过，覆盖基数1／3／6合法域与模型、多enum、ITE／UF／array／ADT／量词、Real、纯BV／纯FP／纯enum、五种舍入模式、NaN／sNaN／负零／负无穷／subnormal、proof／unsat-core和CLI增量状态。追加7例护栏边界的SAT与实际分发全部符合预期。proof／core和非目标片段仍按原报告的范围解释。

修后同库C API再次运行18次检查，64次原断言model_eval均true；覆盖正反假设、UNSAT后恢复、两层push／pop。见 [guarded-api-results.json](guarded-api-results.json)。没有baseline库，故不声称双库API对照。独立fpa组结果见 [guarded-fpa-test.json](guarded-fpa-test.json)。

原报告的未测项继续适用：完整Clause7200秒、Isla真实深增量历史、跨线程／translate、取消／内存极限、completion=false、所有FP宽度与参数组合、随机fuzz、外部proof checker均未新增验收。此次结论是两项明确P2已获针对性修复和独立复验，未发现新的阻断项；不是所有公式的语义形式证明或性能保证。
