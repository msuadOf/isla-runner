# 修订 A 独立复审

**结论：原 lambda 阻断已关闭，本轮未发现新的阻断，可以作为上游备选提交。** 仍须明确接受纯枚举任务的预处理成本；本结论不承诺所有输入更快或相同预算返回相同状态。

本轮仅审查修订提交 `953e43301f406bbf41cf1ae8e600641345a8823b`，基线仍为 `8fbb275aba0472e862e289c7af1331b3bd5d512c`。使用 `A-revised/` 冻结二进制和库重新执行，三个产物 SHA256 与 manifest 一致，见 [provenance.json](provenance.json)。旧 A `4e6105c` 的 [原报告](../report.md) 保留历史结论；本报告不以旧 PASS 代替修订版复测。

## 已关闭：lambda 类型回退

修订源码 `src/tactic/portfolio/default_tactic.cpp:48–49` 将原有转换包在 `when(not(has_quantifier), ...)` 内。`src/tactic/probe.cpp:538–564` 的 `has_quantifier_probe` 通过 `quick_for_each_expr` 遍历全部断言，`quantifier*` 回调不区分 forall、exists、lambda，遇到任意一种即返回 true。`src/ast/for_each_expr.h:84–103` 遍历嵌套表达式和量词子项，因此 lambda 藏在应用、其他量词内也会被发现。

`tactical.cpp:1184–1185` 中 `when` 的 false 分支是 `skip`，所以首轮 simplify 后仍含量词或 lambda 的整个 goal 会跳过新 `dt2bv`，再进入原默认分发。不存在先转换一部分断言再回退的情况。若首轮 simplify 已完全消除 lambda/量词，其残留的无量词 goal 可以安全使用该预处理。proof/core 的原 wrapper 仍完整保留。

重新执行原最小反例 [lambda-array-true.smt2](lambda-array-true.smt2)：基线与修订 A 均 UNSAT，reason-unknown 为空。旧 A 的 UNKNOWN/sort mismatch 不再出现。新增的 lambda-under-or、lambda-nested-quantifier 也均为 UNSAT，与基线一致；独立枚举加整数 forall 的 goal 同样保持 UNSAT。详见 [boundaries-results.json](boundaries-results.json) 和对应 stderr。保留量词的三项 stderr 均无新增 `fd-num-translated`，与 guard 源码吻合。

guard 仅在当前 goal 上检查，未来增量加入 lambda/量词时由后续检查处理；原独立增量/API 测试已针对本修订库重新执行，未发现状态残留。

## 保留的性能取舍

无量词纯枚举任务仍会执行 `dt2bv`，模型恢复 ITE 的“常量数 × 构造器数”成本没有改变。重新跑两组各三次双侧查询，全部 SAT。本轮墙钟中位数：1024 构造器×32 常量，基线 0.097 秒、修订 A 0.293 秒；8192×32，基线 0.217 秒、修订 A 2.399 秒。当前机器并发负载与旧报告不同，不据此宣称修订 guard 本身令性能进一步退化；稳定结论是额外成本仍存在。

这是已知设计取舍，不作为本轮阻断。PR 应说明新增预处理覆盖所有无量词 goal，不能把影响范围描述成只针对 FP。guard 还会使包含无关量词的 FP＋枚举输入继续采用旧路径，不宣称改善这类任务。

## 本轮新执行

- 原独立 11 项语义/模式用例双侧执行：22 次全部符合预期，涵盖原 lambda 反例、forall/exists、UF、数组值域、ADT selector、core、proof 和增量。
- 两组纯枚举成本查询：双侧各三次，共 12 次，全部 SAT。
- 新增 4 项边界/资源用例双侧执行：lambda 藏在 OR、lambda 内嵌 exists、无关整数 forall，以及 FP＋枚举资源红例，共 8 次。前三项双方 UNSAT；资源例基线 UNKNOWN、修订 A SAT，保留修复收益。
- 使用修订 `libz3.so` 重跑独立 C API：三个 SAT 场景、14 次原断言/假设模型回读全部 true；push 矛盾 UNSAT、pop 恢复 SAT。

以上共 42 次新 CLI 进程执行及一套新 API 执行。CPU 112–115、系统 `/usr/bin/python3`；复现入口为本目录 `independent.py`、`boundaries.py`、`api-independent.py`。所有原始输出在本目录，未覆盖旧 A 证据。

本轮未重跑作者 90-query、真实 25 个慢 dump 或完整 Clause；未构建 debug/ASan、未测 RSS。未改源码、未编译共享 build、未切分支，写入仅限 A/review。
