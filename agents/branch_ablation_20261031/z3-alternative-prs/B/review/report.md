# 候选 B 独立审查

结论：在本次源码审查和有界验证范围内，未发现阻断发布的正确性问题。候选 B 可以作为独立替代方案提交 PR；这不代表所有输入都更快，也不代表真实长查询或完整 Clause 已通过。

## 受审版本与边界

- base：`8fbb275aba0472e862e289c7af1331b3bd5d512c`；候选：`ae64857b47ed6123c034c825e4b4dcb930e75b81`，`fix/default-fp-enum-direct`。
- 只读受审 checkout 的源码与 B 的补丁、manifest、独立构建产物；未阅读候选 A 或其他 reviewer 报告，未修改源码、切分支或编译共享 build。
- 独立核对 B 二进制 SHA256：`z3=a881ecaad2ddcce34ded275ce007eb49b5d0975f94dedb14555b034bef0d4663`，`libz3.so=160392cb9bfd6e55ed0065762880f8f21d6d90e40d235b4e6ece475b629b4880`，与 manifest 相符。
- 审查范围为四个变更文件及所调用的 FP/BV/枚举处理链；测试只写当前 `review/`，CPU 116–119，使用 `/usr/bin/python3`。

## 源码判断

1. **类型范围未发现漏挡。** `src/tactic/fpa/qffp_tactic.cpp:158–183` 继承原 predicate：只对结果为有限枚举的零参常量或构造器放行；其他节点仍通过原分类。`using ...::operator()` 保留 var/quantifier 拒绝逻辑。枚举返回的 UF/ITE 被拒绝；枚举 recognizer 和枚举参数返回 Bool 的 UF 因 family 不符被拒绝。数组、一般 ADT、Int、量词仍不在新增范围。AST 遍历访问所有实际子表达式，因此无法单凭 Bool/BV/FP 的父节点隐藏非法子类型。`has_fp/has_enum` 避免新增分支接管纯枚举任务。default 的首轮 simplify 可能先消除某些上述项，因此“源码 probe 拒绝”不等同于某个已简化 query 一定走 fallback。
2. **枚举保留原来的 datatype 语义，不产生整数/BV 编码空洞。** `src/ast/fpa/fpa2bv_rewriter.cpp:62–94` 只转换 FP/RM 常量和相应等式；枚举常量、等式与构造器保留。`src/ast/rewriter/bit_blaster/bit_blaster_rewriter.cpp:404–433` 的常量、等式和 ITE 转换以 BV 类型为条件。`src/ackermannization/ackr_helper.h:124–147` 不收集零参应用；新增 fragment 也不放行枚举 UF，所以 ackermannization 不会把枚举自由常量或构造器改成独立的无域值。
3. **残留理论不会被误送给纯 SAT。** `src/tactic/fpa/qffp_tactic.cpp:93–102` 只有 propositional goal 才用 SAT。残留枚举被 `src/tactic/probe.cpp:250–268` 的 propositional predicate 拒绝，也被 FP/NRA predicate 拒绝，最终进入 SMT，由原 datatype theory 处理有限域。独立 `-v:10` 日志 [dispatch.stderr](dispatch.stderr) 实际出现 `fpa2bv → ackermannize_bv → bit-blast → smt.tactic start`。若枚举已被等值传播消除，走 SAT 是正常的。
4. **模型链保留枚举解释。** `src/tactic/fpa/fpa2bv_model_converter.cpp:53–75` 重建 FP/RM 后拷贝所有其余常量和函数；枚举解释不会因 FP 模型转换丢失。独立 API 对原断言的 `Z3_model_eval(..., true)` 全为 true。CLI SAT query 也对每个完整原断言回读，而非只比较一个枚举变量。
5. **NaN、RM、Real 语义继续使用原 qffp。** 新 probe 对非枚举部分调用原 predicate，没有增加 FP 算子的转换分支。Real 的接受范围继承原 predicate，包含 Real 常量/数值和相应 FP 转换，不意味着任意 Real 算术都被接管。本次验证包括 NaN 的 SMT 等式与 IEEE `fp.eq` 差异、五种 RM 的域约束、自由 Real 到 FP 和 NaN 的未指定 `fp.to_real`。
6. **proof/core 保持原分发。** `src/tactic/portfolio/default_tactic.cpp:58–61` 只在新增分支上禁止 proof/core，原 `is-qffp` 分支保持原行为。`mk_or` 短路，因此原纯 FP 命中时不会计算新增 probe。对同一真正混合 query 的 [proof 日志](dispatch-proof.stderr) 与 [core 日志](dispatch-core.stderr) 均无 qffp 的 `fpa2bv` tactic 阶段；相应检查 SAT。C API 单独验证了 proof 可取、假设 core 非空以及 push/pop 恢复。

没有发现必须修改的 P0/P1/P2 问题。新增 predicate 与原 predicate 的继承关系使放宽范围清楚；生产部分没有独立 dt2bv、额外模型编码或新增 tactic 流水线。保留 `has_fp/has_enum` 和 proof/core 门控有明确范围作用，未找到值得进一步删除的生产逻辑。

## 独立验证

执行入口：

```sh
taskset -c 116-119 /usr/bin/python3 agents/branch_ablation_20261031/z3-alternative-prs/B/review/probe.py
taskset -c 116-119 /usr/bin/python3 agents/branch_ablation_20261031/z3-alternative-prs/B/review/crosscheck.py
taskset -c 116-119 agents/branch_ablation_20261031/z3-alternative-prs/B/test-z3 fpa
```

- **27/27 独立 CLI query PASS**：[输入与 API 脚本](probe.py)、[结果](query-results.json)。覆盖自由 6 值枚举排除全部构造器、7 变量/6 构造器鸽巢、1/2/3/5/7/9/17/65 值域、FP/枚举条件耦合、NaN、自由 RM、Real，以及枚举 ITE/UF/recognizer、FP UF、数组、一般 ADT、量词和 Int 的语义保留。SAT/UNSAT 均按各自已知逻辑预期核对；SAT 还要求每个原断言在返回模型中为 true。
- **27/27 base default 一致、27/27 B 显式 smt 一致**：[交叉脚本](crosscheck.py)、[base 结果](base-results.json)、[SMT 结果](smt-oracle-results.json)。base binary 使用议题已有 `z3-upstream-fix/baseline-z3`；这些是另一个检查路径，不是对 oracle 独立实现的证明。
- **3/3 C API 模式 PASS**：[结果](api-results.json)。plain、unsat_core、proof 各用新 context 与 `Z3_mk_solver_from_tactic(default)`，分别得到 SAT → push 矛盾 UNSAT → pop SAT → 矛盾假设 UNSAT → 去假设 SAT。三次初始模型的三个原断言全为 true；proof 非空，core 含 1 个假设。
- **既有 fpa 测试独立重跑 EXIT 0 / PASS**：[stdout](fpa.stdout)、[stderr](fpa.stderr)。没有以作者先前执行的 PASS 代替本次执行。

## 限制与发布表述

- 上述小 query 每次 SMT timeout 15 秒，外层 20 秒；不是完整 Clause 7200 秒验收。本次未重跑真实 flags/NaN 大 dump、全格式穷举、大枚举规模压力或 cancellation/内存耗尽。
- 不保证同预算结果总相同：改变策略可能使 SAT/UNSAT 与 UNKNOWN 的资源分界移动。父 agent 通知作者套件中两个真实 flags query 在 60 秒返回 UNKNOWN/canceled、正在延长预算；这里未独立执行这些 query，不能将它们记为 PASS，也不能仅据 UNKNOWN 判定语义错误。
- proof/core 只验证可取与恢复；没有独立 proof checker 验证完整 proof，也没有对所有 core 做最小性检查。补丁的新增分支本来禁止这两种模式。
- 模型允许选择不同的合法枚举/FP 值；审核标准是原断言成立。本次没有要求新旧模型文本完全相同。
- PR 可以准确描述为“在受限 FP＋有限枚举输入上提前采用已有 qffp 流水线，保留 datatype 残留给 SMT”；不能声称所有 datatype、所有增量工作负载、所有预算下均提速。
