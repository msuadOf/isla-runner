# 独立语义审查

结论：未找到 SAT/UNSAT 算错或模型重建错误；新分支在受限片段上的可满足性保持，有直接代码依据。不过，“各种条件下前后等价、只改善性能”不能成立：发现可复现性能回退，并且同一资源预算下原版 SAT、补丁版 UNKNOWN。有限探针不构成所有输入的正确性证明。

## 已确认问题（按严重性）

### P2：无枚举规模限制的新分发，可让简单约束慢约 8 倍并消耗额外资源

定位：`.tmp/z3-enum-fp-default/src/tactic/portfolio/default_tactic.cpp:60–64`，以及新 probe 的 `src/tactic/fpa/qffp_tactic.cpp:132–138,175–176`。

触发输入只需要一个 `fp.isNaN x`，加上 100 个类型为 1000 构造器枚举的常量，各自约束 `distinct e_i C0`。这些枚举常量与浮点运算无关。两版都是 SAT，但两次独立进程墙钟如下：

| 枚举构造器 / 常量数 | 基线两次（秒） | 补丁两次（秒） |
| --- | --- | --- |
| 100 / 10 | 0.0191 / 0.0190 | 0.0232 / 0.0244 |
| 1000 / 10 | 0.0199 / 0.0202 | 0.0336 / 0.0314 |
| 1000 / 100 | 0.0234 / 0.0238 | 0.2020 / 0.1963 |
| 5000 / 10 | 0.0283 / 0.0309 | 0.1074 / 0.0995 |

同一 1000 / 100 输入设置 `:rlimit 10000`，基线 SAT，补丁 UNKNOWN，原因是 `max. resource limit exceeded`；30000 和 100000 均 SAT。完整输入为 [budget-10000.smt2](budget-10000.smt2)，输出见 [budget-results.json](budget-results.json)。复现命令（从仓库根目录）：

```sh
agents/branch_ablation_20261031/z3-upstream-fix/baseline-z3 agents/branch_ablation_20261031/z3-upstream-fix/independent-review/semantics/budget-10000.smt2
.tmp/z3-enum-fp-default/build/z3 agents/branch_ablation_20261031/z3-upstream-fix/independent-review/semantics/budget-10000.smt2
```

原因有源码依据：原生 SMT 可直接满足各个简单枚举排除；新分发无条件进入 dt2bv。`src/ast/rewriter/enum2bv_rewriter.cpp:163–181` 为每个枚举常量生成包含全部构造器的模型重建 ITE 链，成本随“构造器数 × 常量数”增长。没有模型要求时，该实现同样构建 converter。该问题是求解成本/可用性回退，不是 UNKNOWN 被当成 UNSAT 的不健全。

建议：上游提交说明应限定改善目标；加入该类性能回归，评估枚举规模、浮点工作量或策略回退限制。任何限制或回退都需单独验证，不能从现有收益外推无条件加速。

## 源码所支持的等价性边界

1. **原有公开 probe 判定保持。** 原 `is-qffp`、`is-qffpbv` 仍调用默认 `allow_enums=false` 构造器。新增状态变量不改变原有返回/抛出条件。`m_has_fp` 的赋值只是局部状态，无全局副作用；`datatype_util` 在该分支不执行枚举查询。可支持旧 probe 真值相同，不支持执行成本完全相同。
2. **新 probe 接受的枚举表达式可被 dt2bv 消除。** `datatype_util::is_enum_sort` 只接受所有构造器均为零参数的 datatype。新逻辑只接受这种类型的零参数未解释常量与构造器；枚举 ITE、枚举返回函数均拒绝。有效类型检查下，获准的其他家族中，枚举直接使用位置只剩 basic equality/distinct；它们都被 `dt2bv::check_fd` 允许，并被 enum2bv 重写。datatype recognizer 因返回 Bool 而进入原判定，并被拒绝；这是保守遗漏，不会误接受。新 probe 遍历整个表达式 DAG；`test(goal, Predicate&)` 按引用保留 has_fp/has_enum，不存在标记丢失。
3. **域与模型重建有双向对应。** 构造器索引是 0..n−1，位宽足够区分索引；非 2 次幂及单元素域增加 `bvule fresh (n−1)`，防止伪枚举值。原 equality/distinct 等价于索引 equality/distinct。每个原枚举常量用按索引选择构造器的 ITE 重建，辅助 BV 被隐藏。generic model converter 逆序执行 add/hide，先重建再隐藏。模型转换组合逆序应用，先恢复浮点，再恢复枚举。这里给出的是在既有重写器和 model converter 正确的前提下，受限片段的变换正确性理由。
4. **NaN、舍入与 Real 没有新近似。** dt2bv 只改枚举项，保留原 FP、RM、Real 项；新增枚举 BV 可通过 Boolean 条件与 FP 相互约束，并非仅支持独立合取。qffp 继续调用既有 fpa2bv 和模型恢复。Real 常量、数值、FP↔Real 转换和 basic equality 可被接受；一般 Real 算术项仍被原判定拒绝。qffp 自带剩余非 BV 目标的 SMT/NRA 分发，不意味着所有混合 Real 目标均转为 SAT。没有重新证明 fpa2bv 全部 IEEE 特例；小格式动态测试只补强证据。
5. **边界与原路径。** 量词及 bound variable、Array、一般 ADT、非零参数 UF 均被新 probe 拒绝；一般 ADT 中嵌入 FP 仍会因其 ADT 类型节点而拒绝。proof/core goal 上新增 guard 为假，沿旧分发。此前已有分支位于新分支之前，真值未改变。判断发生在 default 的原始 simplify 之后，因此原输入含数组/ADT/ITE 不表示必定不触发：若 simplify 已消除这些项，剩余目标可以进入新路径。这是对化简后目标的判定，不是整份原 SMT 文本的语法限制。
6. **增量与异常恢复没有新增持久符号映射。** `tactic2solver::check_sat_core2` 每次用当前完整断言/假设创建 goal，执行前后 cleanup；dt2bv cleanup 清除 sort 集合，单次 enum2bv 映射为栈上对象。静态未发现一次 check 的枚举映射污染下一次。实际资源耗尽后的同一 solver 恢复测试也通过，但未覆盖任意异步 interrupt 时刻。

## 本轮独立执行

受测源码 HEAD `8fbb275aba0472e862e289c7af1331b3bd5d512c`，四文件未提交补丁；没有重编译、修改源码或生产组件。使用交付的同基线未修二进制与当前 `build/z3` / `build/libz3.so`。命令均在仓库根目录执行，Python 使用 `/usr/bin/python3`。

- [probe.py](probe.py)：28 个自建输入 × 基线/补丁，共 56 次，结果均符合预期；SAT 的完整原断言通过 `get-value` 回读 true，并设置 `:model_validate true`。覆盖域大小 1..9（单元素、2 次幂和非 2 次幂）、穷尽排除 UNSAT、多枚举与 FP 布尔耦合、NaN 自相等与 `fp.eq` 差异、正负零、RM 合法域、FP↔Real；另含枚举 ITE/recognizer 的原路径输入。结果见 [results.json](results.json)。
- [performance.py](performance.py)：四种枚举规模各两版两次，16 次，均 SAT；具体计时见 [performance.json](performance.json)。这只证明这些输入存在回退，非通用性能统计。
- [budget-results.json](budget-results.json)：三档相同资源预算 × 两版共 6 次，确认上述 SAT→UNKNOWN 回退。
- [guard-results.json](guard-results.json)：相同低预算反例打开 proofs 或 unsat cores 后，两版均 SAT，共 4 次。与 guard 源码一致；这里未单独校验证明对象和 core 最小性。
- [reuse.py](reuse.py)：补丁 libz3 的同一 default solver 先以低预算得到 UNKNOWN，再提高预算，依次 SAT、相反假设 UNSAT、pop 后 SAT；两次 SAT 的全部 101 条原约束回读 true。见 [reuse-results.json](reuse-results.json)。

## 尚不能声称的保证

- 不要求补丁前后模型逐字段相同：SAT 允许不同合法见证；未指定的 NaN→BV、FP→Real 等结果尤其不能用字面模型相等验收。
- 不保证相同 rlimit/timeout 的 SAT/UNSAT/UNKNOWN 一致，本轮已经有反例；不保证全输入运行时间/内存下降。
- 不保证取消响应时间相同：新增 probe、dt2bv 预扫描以及枚举 ITE 构建存在无显式 cancellation checkpoint 的循环。源码可支持增加工作量的判断；本轮未测外部并发 interrupt、超大构造器域的响应延迟或内存耗尽。
- 本轮不证明所有 FP 位宽、所有 Real 转换、全部参数组合、整个 Z3 tactic 框架均正确；也未验证完整 Clause、长期深度增量历史或生产 Isla。
