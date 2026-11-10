# 超时路径性能定位（2026-11-01）

## 结论

60秒默认SMT限时暴露了真实的单查询性能问题，不应仅归为实验配置问题。已从完整Clause失败日志定位两类显式分支，并在同一Z3 4.16.0（运行器链接同版本库）上独立重放导出的SMT，确认求解策略与浮点条件表达是已证实的性能影响因素。尚未修改生产模型/求解器；未证明下面所有方案对完整Clause都有效。

## 慢在哪里

1. flags：源文件 `model/extensions/FD/fdext_regs.sail` 的显式 `if changed`。条件为 `old != old|flags`，flags包含浮点除法异常公式。导出query含f32除法结果及向下/向上舍入的f64除法以推导overflow/underflow/inexact；更新mstatus本身还没执行。第一个超时位置line550，事件1至10及12为CheckSatAssuming，事件11为CheckSat。
2. NaN规范化：`model/extensions/FD/softfloat_symbolic_f32.sail` line10的显式NaN判断。在FSQRT.S上query为 `fp.isNaN(fp.sqrt(RMM, input))`。input仍经32个FPR的符号索引选择；求解器必须判断该结果条件是否存在输入满足。不是NaN输入建模错的证据。
3. 执行器 `isla/isla-lib/src/executor.rs` 的符号Jump，先依次调用check_sat_with(condition)、check_sat_with(not condition)，都得到SAT后才fork。任一调用遇到SMT超时会经`is_sat()?`返回错误，当前路径中止并计入partial；不是Clause总时间到7200秒。已有两个方向查询的设计，未发现足以证明重复查询bug的证据。

## 同一超时查询的重放

原dump完整约束不删减，只有check-sat-using策略改变。每个probe固定单CPU，SMT探针60秒；该限时只用于比较单查询，不冒充7200秒完整Clause。全命令、资源、源哈希、query与输出保留在本目录。

| 导出query | qfaufbv | smt | qffp（额外三重复） | simplify→fpa2bv→qfaufbv |
| --- | --- | --- | --- | --- |
| flags首个超时query | 60.26秒，unknown | 60.26秒，unknown | 3.711–3.715秒，均SAT | 13.92秒，SAT |
| NaN首个超时query | 37.74秒，SAT | 26.73秒，SAT | 0.208–0.209秒，均SAT | 0.208秒，SAT |

qfaufbv是现有完整Clause实验显式选用且代码默认的策略，名字表示数组/未解释函数/位向量；query实际含原生浮点sqrt/div及混合位向量/枚举。该策略并非算错，但这些样本上比专门浮点策略差。`Tactic`目前只暴露default/qfaufbv/smt，没有qffp或显式浮点预处理组合。不能仅将字符串换为qffp就宣称适用于全仓数组/内存查询。

重要限制：dump是从checkpoint导出的独立check-sat查询；生产执行为带假设、随机seed和增量历史的solver。独立重放不是逐调用完全一致复现。NaN独立qfaufbv约37.7秒而生产超过60秒，说明求解状态/seed/调用方式仍可能影响结果；本轮没有单独消融它们，不能归为已确定的原因。flags独立query仍60秒unknown，说明不依赖整个执行器也存在困难查询。

## NaN条件的等价改写探针

对于f32平方根，`isNaN(sqrt(RMM,x))`与`isNaN(x) or x<+0`等价，后者包含负无穷、不包含负零。对任意f32输入的两式差异用qffp检查UNSAT，见sqrt-nan-equivalence.smt2和结果JSON；只证明此表达式关系，并非全模型等价。

在原NaN导出query中只替换这一个谓词，其余路径约束不变，仍用qfaufbv，0.108秒SAT。说明可保留显式NaN/非NaN分支，但让分支条件依据输入分类，避免为分类问题求解完整平方根电路。这不是把数据具体化或把分支折为ITE。

## 修改建议与未完成验证

优先验证浮点求解策略/显式fpa2bv预处理，使原显式分支可正常求解；需要继续验证全Clause、两方向、混合枚举/数组、SAT/UNSAT及最终模型读取。另一个局部方向是为sqrt结果NaN构造已证明等价的输入分类条件，不删除分支；其它add/div/fma需各自证明，不能套用sqrt公式。

flags异常条件的f64定向舍入除法也可能是公式成本来源，本轮仅核对源码和导出算子，未做替换公式消融，不能单独判定该异常算法有错或是不必要计算。不得通过固定flags/FPR或跳过分支规避。

当前建议是先处理求解路径性能，再讨论ITE取舍；不能用慢查询直接证明必须合并模型控制流，也不能仅延长限时当作性能修复。

追加default/smt三重复比较见[报告](default-smt-comparison.md)：flags均60秒unknown；default当前isarch接入还会因种子能力校验panic。
