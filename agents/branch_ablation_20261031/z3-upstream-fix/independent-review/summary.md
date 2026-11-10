# Z3补丁独立审查汇总（2026-11-01）

## 结论

两位独立reviewer分别完成源码语义审查、动态边界审查，以及修订版复验。最终受审文件与构建哈希均匹配[guarded-snapshot.json](guarded-snapshot.json)。初版两项P2已经修复并复验，未发现新的错误SAT/UNSAT、枚举域或模型恢复问题；没有剩余已确证的阻断项。

本结论是独立审查和测试支持的受限语义保持，不是对所有SMT输入的形式化证明。SAT时选择的具体模型可以改变；允许解的语义应保持。资源耗尽时SAT/UNSAT/UNKNOWN、总耗时、内存与取消响应不能保证逐项相同，不能声称所有输入都只提速。

## 发现与修复

| 初版问题 | 修复 | 独立复验 |
| --- | --- | --- |
| 大枚举简单FP公式因急建模型ITE产生明显回退，甚至同预算SAT变UNKNOWN | 对唯一enum自由常量累计构造器数，超过4096保留原default路径；仅控制新路径成本，不固定模型或删约束 | 两位原rlimit反例均恢复SAT；原100ms案例三次双侧SAT；4096/4097、多sort合计及重复引用DAG去重均正确 |
| 原枚举域UNSAT测试同时固定变量，不能检测非法编码漏排除 | 去掉固定mode构造器，让自由枚举排除全部6个值，必须依赖真实域约束UNSAT | 独立确认真实进入dt2bv；1/3/6合法域、穷尽排除与鸽巢UNSAT通过 |

## 语义核对的主要依据

- 现有is-qffp判定保持；新增分支只接受受限FP＋简单枚举，枚举ITE/非零参数函数/数组/一般ADT/量词不被直接接纳。判定针对simplify后的goal，因此原始文本出现某类项但已被化简消除时可能进入新路径。
- dt2bv的构造器索引一一对应，单值和非2幂域有上界约束，防止额外编码成为伪解；已有模型转换恢复原枚举并隐藏辅助BV，浮点继续使用原qffp/fpa2bv语义。
- proof/unsat-core模式沿原路径；不存在此补丁引入的新浮点运算定义、舍入规则、NaN近似或Sail控制流合并。
- 增量假设、push/pop、UNSAT后恢复、资源UNKNOWN后提高预算复用，以及模型对原断言求值均通过独立检查。

## 两位独立证据

- [语义初审](semantics/report.md)、[修订复验](semantics/report-guarded.md)：28独立功能例×两版56执行；NaN/零/RM/Real/域、proof/core及原101断言回读；成本阈值、共享DAG与资源恢复。原始版本报告保留，不静默覆盖。
- [边界初审](boundaries/report.md)、[修订复验](boundaries/report-guarded.md)：55例×两版110执行，另7个成本边界；18个API检查、64次原断言model_eval为true；五种舍入模式、特殊值、数组/UF/ADT/量词、proof/core、模型与增量。
- 主agent修订后再跑[41条query](../validation-guarded/results.json)全部预期一致，并确认fpa组通过。不能把上述数量简单相加当不同输入总数，可能有重复覆盖。

## 仍有限制

4096为工程成本门槛，并非最优阈值或总求解时间保证；阈值内仍可能有额外转换开销。全Clause7200秒、生产Isla接入/深增量历史、所有FP宽度/参数组合、跨线程translate、异步取消与内存极限、completion=false和外部proof checker未全面验收。没有证明任意查询都比原来快，也没有承诺完全相同的具体模型。

补丁与当前源码哈希以[manifest](../manifest.json)为准；[default-fp-enum.patch](../default-fp-enum.patch)已更新，原初版保存为initial-default-fp-enum.patch。未替换系统Z3/生产组件，未提交PR或向官方issue追加评论。

## 后续用户选择

2026-11-01用户要求移除4096性能护栏；已执行并保留域测试修正。本文护栏版P2关闭结论仅适用于guarded-snapshot。当前版性能P2接受其开销，不再以护栏抑制。[记录](../restored-no-cost-limit/report.md)。
