# 代码结论：两种路线的等价性

结论：对 B 接管的无量词 FP＋简单枚举片段，A、B 都保留原公式的可满足性，并能返回满足原断言的模型；两条流水线和具体模型不要求相同。两份补丁的整体影响范围不同，因此不能说全局行为等同。

- A 在 default 的 simplify 之后执行现有 dt2bv，再沿原有 probe 分发。enum2bv_rewriter.cpp 的 value2bv 为每个构造器给出不同编码；constrain_domain 排除非法编码；自由变量的 enum_defs 为模型提供逆映射。dt2bv_tactic.cpp 隐藏辅助 BV 声明、添加原枚举定义。因此在支持的枚举项上，原枚举赋值与合法 BV 编码之间一一对应，等式/不等式及布尔组合保持。浮点项仍由原有策略处理。
- B 的新 predicate 只放行枚举自由常量和零参数构造器，其余项沿现有 is_non_qffp_predicate 检查；量词、lambda、数组、一般 ADT、枚举函数和枚举 ITE 不被新 probe 接管。枚举表达式原样保留。qffp 的 fpa2bv 处理浮点；bit-blast 后若仍有枚举，is-propositional 和 is-fp-qfnra 不接受它，最后选择 mk_smt_tactic，由 datatype theory 处理枚举。不是将枚举视为任意新变量，也不是忽略枚举断言。
- 两个论据分别来自编码/逆映射和原约束保留，不以有限样例代替源码理由。FP 转换本身复用上游 fpa2bv，本补丁没有改变其语义。

## 已修复的适用性缺口

A 初版4e6105c将dt2bv扩展到含lambda的goal。现有enum2bv转换body中的枚举变量，却不转换lambda binder，导致类型不一致。独立最小例：三值枚举E，数组等于lambda(y:E).y=A，又等于全true数组，基线UNSAT而初版UNKNOWN。详见A/review。

A修订953e433使用现有has-quantifiers probe，在goal含任意quantifier节点（包括lambda）时跳过新增预处理，保留旧default路径，并增加上述回归。初版90-query PASS不能说明此边界正确，旧证据只适用初版；修订版需单独复测与独审。

## 不同的范围和成本

A还影响不含浮点的安全枚举公式，以及原有策略在枚举消除后的选择；B只新增混合FP/简单枚举分发。proof/core均沿原路线。同rlimit/timeout的UNKNOWN与具体SAT模型可以不同，不属于逻辑可满足性相反。A会急建枚举模型恢复表达式，B可能在剩余SMT中处理更大公式。性能须以具体查询计量，不宣称同速或全面更快。全Clause7200秒未验。
