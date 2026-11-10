# Z3 4.16.0统一策略源码调查（2026-11-01）

## 结论

问题不是Z3缺通用策略，而是当前查询含Sail枚举，Z3 default的浮点分类探针不接受它，导致未选中qffp流水线。直接调用qffp则绕过这个分类门槛，先对浮点整体转换和预处理，即使最后仍有其它理论，也能交回SMT。

建议作为统一候选验证 `(then simplify dt2bv fpa2bv simplify default)`：不按指令或workload名称选策略，先把可处理的枚举和浮点约束规范化，再由default自动选择BV/数组/其它后端。浮点/枚举不存在时相应步骤没有这些对象可转换；不能由此宣称成本恒为零。

本轮已完成25个真实超时dump、10个混合类型探针、2个带假设的C API查询及模型回读；尚未接入生产或完成整Clause/全指令/全内存域7200秒验收。统一策略的工程目标是让本仓规定的任务集在预算内完成，不是对任意SMT公式给出最坏时间承诺。

## 版本和源码

运行Z3为4.16.0，Homebrew receipt版本4.16.0。读取上游tag z3-4.16.0发布源码，来源URL、tar哈希和各源码哈希见[source manifest](source-excerpts/manifest.json)。这是匹配发布版本的源码调查，未重编译证明Homebrew bottle与tag逐字一致。

源码入口（均已按原文含版权头保存）：

- [default_tactic.cpp](source-excerpts/default_tactic.cpp)：`mk_default_tactic`先simplify，再按probe分发，其中明确有 `cond(mk_is_qffp_probe(), mk_qffp_tactic, ...)`，未命中则 `mk_preamble_tactic + mk_smt_tactic`。前置简化没有先对Sail枚举做dt2bv。
- [qffp_tactic.cpp](source-excerpts/qffp_tactic.cpp)：`is_non_qffp_predicate`只接受Bool、FP、RM、BV和限定Real等，枚举sort不在允许项，故含活动枚举的查询不能命中is-qffp。这里是语法分类，不是说理论无法求解。
- 同文件 `mk_qffp_tactic`：simplify → propagate-values → fpa2bv → propagate-values → simplify → 可选Ackermann化 → bit-blast → simplify → 按剩余理论交SAT/NRA/SMT。直接调用qffp不会先强制通过is-qffp，所以混合枚举query也能得到这套预处理。
- [qfaufbv_tactic.cpp](source-excerpts/qfaufbv_tactic.cpp)：预处理含simplify/solve-eqs等，但没有整体fpa2bv；非纯QF_BV时最终交SMT。当前Isla固定选择它，不能自动得到qffp的前置流水线。
- [theory_fpa.cpp](source-excerpts/theory_fpa.cpp)：通用SMT也实现浮点转换，`convert`调用浮点rewrite并缓存，internalize处理原子和项。不能说smt“不支持浮点”或“完全不做位向量转换”。区别在转换/简化/bit-blast的阶段与组合，以及其它理论残留；本轮没有给Z3内部每阶段做CPU剖析，不能把全部差额单归某个子过程。
- [dt2bv_tactic.cpp](source-excerpts/dt2bv_tactic.cpp)：处理符合限制的有限枚举并附加界约束，登记模型转换；不对所有递归/带字段datatype盲目替换。不符合可转换要求的sort保留给后端。
- [fpa2bv_tactic.cpp](source-excerpts/fpa2bv_tactic.cpp)：整体浮点转换并登记fpa2bv模型转换，用于取回原始浮点模型；不是把浮点含义丢掉。

## 直接验证default没有认出浮点

对两个真实dump运行 `simplify; fail-if(not is-qffp)` 均失败。改为 `simplify; dt2bv; fail-if(not is-qffp)` 均通过。NaN查询用solve-eqs也能去掉影响识别的等式，flags只用solve-eqs仍未通过。原文件及probe输出保留在[theory-probes](theory-probes/)。

随后保持原完整断言，仅更换流水线，独立查询probe结果为：

| 流水线 | NaN秒 | flags秒 |
| --- | ---: | ---: |
| simplify → solve-eqs → default | 0.209 SAT | 60.258 unknown |
| simplify → dt2bv → default | 0.109 SAT | 8.515 SAT |
| simplify → fpa2bv → default | 23.227 SAT | 16.426 SAT |
| simplify → dt2bv → fpa2bv → default | 0.208 SAT | 10.116 SAT |
| simplify → dt2bv → fpa2bv → smt | 48.850 SAT | 15.822 SAT |
| qffp直接调用 | 0.210 SAT | 3.912 SAT |

本表为单次结构消融，且各probe并行；不称各流水线的稳定排名或完整Clause加速比。目的是验证“规范化枚举/浮点后再通用求解”可行，而非给每种workload挑最快。全命令/资源见[compare.py](compare.py)和[原始结果](probe/results.json)。前轮default/smt/qfaufbv三重复证据另见[对照](../solver-diagnosis/default-smt-comparison.md)。

## 统一候选的覆盖探针

使用同一 `(then simplify dt2bv fpa2bv simplify default)`，单查询probe60秒：

- 原flags组一臂全部12个超时dump：12/12得到SAT，9.324–16.841秒。
- 原NaN组一臂全部13个超时dump：13/13得到SAT，0.211–0.414秒。
- 另10个合成输入：数组读写SAT/UNSAT、枚举SAT/UNSAT、浮点与数组混合SAT/UNSAT、位向量SAT/UNSAT、枚举值数组、非枚举record，各自均符合预期。SAT样例同时调用get-model/get-value，保留枚举/数组/record等原始sort的模型输出。

上述35个query全部得到SAT或UNSAT、无unknown或输出error；25个真实dump原先是unknown，本轮SAT只证明可满足，不能替代全路径及模型数值正确性验证。合成探针明确不作为真实内存Clause验收。完整输入/命令/模型/资源见[validate-unified.py](validate-unified.py)、[35项结果](unified-validation/results.json)。

再用与运行器相同的libz3，经C API构造该tactic solver，将dump临时条件作为check_assumptions输入，路径约束作为assert，包含push/pop：NaN约0.130秒SAT，flags约7.938秒SAT。取得solver model后，分别model_eval原始两条断言，全部为true；恢复的模型含原始Sail枚举。见[API探针](api-probe.py)、[NaN结果](nan-api.stdout)、[flags结果](flags-api.stdout)。探针早期缺少AST vector引用保持及参数描述引用，曾在ctypes脚本中异常，已修正后重跑，最终结果以此处JSON为准；该脚本错误不能归为Z3性能缺陷。

## 接入与验收还差什么

1. 当前Isla default接入会因seed参数描述检查panic。Z3 [lazy_tactic](source-excerpts/tactic.cpp)为default延迟构造后端，未覆写collect_param_descrs，继承默认空实现；因此顶层描述不暴露后端seed，不能由此推断所有后端不能设置seed。需明确在真实后端配置并验证随机种子，不能直接删校验假装接入完成。
2. 统一候选尚未修改Tactic枚举或new_z3_solver，也没有更改模型/IR。接入时应保留现有solver抽象、check_assumptions、checkpoint与模型回读链路。
3. 新入口需用显式控制流模型跑完整浮点Clause与memory的LOAD/STORE/STORECON/数组场景，7200秒总预算，两臂同配置；检查finished与partial、异常、SAT/UNSAT、原始类型模型回读和JSON语义。不能用单query时间相加替代Clause完成时间。
4. 对既有常规整数/数组查询，检查预处理开销或模型转换回归。若后续采用多个求解分支共享预算的portfolio，也应作为同一入口内固定策略并单独验证，而不是让用户按workload选开关；本轮还没有需要portfolio的实证结论，不先增加复杂度。

下一步是把此统一候选做成可选实验入口并完成上述验收，再决定是否作为默认；不再把“通用策略不擅长所以只能折叠分支”作为理由。
