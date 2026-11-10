# 是否值得向Z3上游提出改进（2026-11-01）

## 判断

值得以default tactic对“浮点＋有限枚举”的性能改进议题向上游反馈，并准备小范围PR；当前证据不构成求解结果错误，不应要求维护者无条件在全局加dt2bv，也不能承诺任何SMT公式在固定时间内结束。本地组合策略可解决工作区问题；上游改进能让其他使用相同合法混合类型的用户自动获益，两者并不冲突。

## 独立最小复现

以下输入不依赖Sail、Isla或RISC-V；模式枚举与sqrt输入之间没有数据依赖：

```smt2
(declare-const x (_ FloatingPoint 8 24))
(declare-datatypes () ((Mode A B C D E F)))
(declare-const mode Mode)
(assert (= mode F))
(assert (fp.isNaN (fp.sqrt roundNearestTiesToAway x)))
(check-sat-using default)
```

同机Z3 4.16.0，每项独立单CPU、60秒query上限，各三次并行记录（计墙钟而非纯solver CPU）：

| 输入/策略 | 中位秒 | 范围秒 | 三次结果 |
| --- | ---: | --- | --- |
| 无枚举，仅sqrt NaN；default | 0.109 | 0.109–0.109 | 全SAT |
| 增加独立枚举约束；default | 15.826 | 6.613–16.028 | 全SAT |
| 同含枚举公式；dt2bv→default | 0.209 | 0.208–0.308 | 全SAT |

默认随机种子等未显式变化；调用为CLI check-sat-using default。此处default tactic与普通Z3 Solver()/SMT-LIB check-sat战略solver不混称，未对后者做同组实验。单次首测还得到default6.617秒、dt2bv-default0.312秒；正式三次有波动，按范围如实保留，不包装成稳定加速比例。

原始命令、各输入和资源位于[重复记录](repeat-results.json)、repeats/。实际工作区两个大query的对照及25个导出query结果见[前述源码调查](../z3-strategy-source/report.md)，可作为真实场景补充，不能代替该最小复现。

## 上游源码仍存在的限制

下载当前master相关源码并核对。记录的HEAD为 `8fbb275aba0472e862e289c7af1331b3bd5d512c`，提交时间 `2026-10-31T15:38:56Z`。master default较4.16.0增加有限域相关逻辑，但这里的浮点probe/default分发段仍然相同；master qffp_tactic.cpp与tag文件逐字相同。没有构建master二进制，故只说代码路径仍存在，不宣称master运行性能已复现。

default_tactic.cpp以is-qffp识别后选择qffp；qffp_tactic.cpp的类型检查不允许finite datatype sort，合法枚举因而绕过该流水线。dt2bv后两个真实query命中浮点probe，这与最小例子的数据一致。对应上游入口：

- https://github.com/Z3Prover/z3/blob/8fbb275aba0472e862e289c7af1331b3bd5d512c/src/tactic/portfolio/default_tactic.cpp
- https://github.com/Z3Prover/z3/blob/8fbb275aba0472e862e289c7af1331b3bd5d512c/src/tactic/fpa/qffp_tactic.cpp
- https://github.com/Z3Prover/z3/blob/8fbb275aba0472e862e289c7af1331b3bd5d512c/src/tactic/bv/dt2bv_tactic.cpp

原始下载保存在本目录master-*.cpp。GitHub API只读搜索 qffp/datatype、dt2bv/default、floating point/enumeration 等，没有定位到直接讨论此类分发问题的议题；搜索不证明不存在相关issue。已保存追加搜索[原始结果](issue-search.json)。检索中其它NaN正确性issue不是此性能问题，不混用其结论。

## 建议给社区的议题范围

建议标题：**有限枚举约束使混合浮点公式绕过default的qffp策略，造成明显性能下降**。

请求讨论的改进是：default在对含浮点及有限枚举的公式作策略分发前，是否应进行受限枚举规范化，使原本适合浮点流水线的公式进入该流水线。先提交上述最小例子、三个对照、版本/命令，以及type probe原因；由维护者判断放在default前处理还是在受限混合浮点策略中处理。

不建议直接把所有datatype放进is-qffp允许列表：递归ADT、带字段构造器、数组索引/元素中的枚举、量词、UF参数等不等同简单枚举，后续流水线/模型转换需验证。也不建议仅根据此例向所有default输入无条件增加可能增加成本的步骤。

候选PR的验收必须包括：

- 最小复现和混合FP/枚举的SAT、UNSAT语义回归；性能基准与正确性单测分开，单测不设脆弱的毫秒级通过门槛。
- 模型回读仍恢复原枚举、浮点类型，合法取值约束不能丢；覆盖check_assumptions、push/pop、model eval。
- 普通整数/BV、数组、非枚举ADT及已有浮点基准无不合理回退；适用proof/unsat-core模式按已有支持范围说明。
- 全局变更前需要上游benchmark而非只看我们的25个query。此证据足以发起议题，不足以直接宣布全局默认应立即修改。

## 交付边界

未发布issue、PR或向维护者发消息，未改Z3或生产Isla。已有本地复现与issue草稿足以供用户评审；发布需用户明确指示。

## 后续发布记录

2026-11-01按用户明确授权发布 [Z3Prover/z3 #11500](https://github.com/Z3Prover/z3/issues/11500)，已回读核对OPEN与正文一致。上文“未发布”描述为评估阶段的历史状态；现以此条为准。
