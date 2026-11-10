# 4096 成本护栏独立复审

结论：旧 P2 的具体回退已修复；原反例在 `rlimit=10000` 下现在返回 SAT，未发现本次修订引入的语义问题。4096 是预处理成本护栏，不是“所有查询只会更快”或“相同资源预算下结果恒等”的证明。

## 受测修订

基线仍为 `8fbb275aba0472e862e289c7af1331b3bd5d512c`。独立计算源码四文件、`build/z3` 与 `build/libz3.so` 的 SHA256，全部匹配主 agent 冻结的 `independent-review/guarded-snapshot.json`；本轮实测快照见 [guarded/hashes.json](guarded/hashes.json)。

未修改 Z3 源码，未在共享 build 内编译；独立内部 probe 测试在本目录编译，仅链接冻结 build 的现有对象。未读取其他 reviewer 的报告。旧 [report.md](report.md) 的计时和 SAT→UNKNOWN 只适用于护栏前补丁，不能作为护栏后失败结论。

## 代码复核

`src/tactic/fpa/qffp_tactic.cpp` 对获准的每个枚举未解释常量，累计其 sort 的构造器数。超过 4096 则新 probe 返回 false，default 继续原分发；等于 4096 仍接受。构造器本身不产生枚举常量模型重建，因此不计数。

- **累计量与 eager ITE 成本匹配。** enum2bv 为每个唯一常量建立一个长度与枚举域大小相关的模型定义。护栏按“每个唯一常量的构造器数之和”收费，覆盖多个 sort、多个常量。该值保守覆盖模型 ITE 数量，但不限制 FP/BV 转换、AST 扫描或后续搜索的成本。
- **DAG 去重正确。** `goal.h::test` 在整个 goal 的全部断言间共享一个 `expr_fast_mark1`；`for_each_expr.h::quick_for_each_expr` 对引用数大于 1 的节点标记后只回调一次。一个枚举常量若出现在多个不同父项或多个断言中，引用数大于 1；若整个父项被共享，则父项自身去重。引用数为 1 的常量仅能沿其唯一父边到达一次。因此此处不是按语法出现次数累计。不同常量即使同名也由 AST 声明身份区分；正常 ast_manager 中同一声明的零参数 app 被共享。
- **无 unsigned 加法溢出漏洞。** 初值 0；仅在 `size <= 4096-current` 后加上 size，归纳保持 `current<=4096`。因此减法不会下溢，加法不会绕回。超过阈值通过现有 `found` 机制变为 probe false。
- **语义只进一步收窄。** 新增限制不接受任何旧 probe 拒绝的项，不改变 dt2bv 或 qffp 转换；拒绝后使用旧策略。原 `is-qffp` 在 `allow_enums=false` 时不执行计数。上一轮受限片段的域约束、模型恢复、NaN/RM/Real、proof/core 和类型边界分析继续适用。
- **有限域 UNSAT 回归已增强。** 去掉 `mode=F` 后，`distinct mode A B C D E F` 的不可满足性真正依赖有限域及编码边界，避免由已固定构造器直接矛盾掩盖 bounds 遗漏。

## 独立执行结果

以下命令从仓库根目录执行。旧产物保留，新结果均在 `semantics/guarded/`。

1. **旧反例恢复。** [原 budget-10000.smt2](budget-10000.smt2) 在冻结基线和修订后的 z3 均 SAT；30000/100000 两档也均 SAT。共六次，见 [guarded/budget-results.json](guarded/budget-results.json)。
2. **内部 probe 阈值与共享节点。** 独立 C++ 程序直接调用新 probe，七项全部符合预期：4096×1 接受、4097×1 拒绝、2048×2 接受、2049×2 拒绝、1000×4 且每个常量出现在 30 个不同父表达式中仍接受、1000×5 同样共享时拒绝、3×1 出现在 3000 个不同父表达式中接受。直接覆盖恰好阈值、越界、累计、DAG 去重，见 [guarded/probe-cost.cpp](guarded/probe-cost.cpp) 与 [结果](guarded/probe-cost-results.json)。
3. **关键功能与模型恢复。** [guarded/probe.py](guarded/probe.py) 共 28 个用例 × 两版，56 次均符合 SAT/UNSAT 预期；所有 SAT 的完整原约束回读 true。覆盖域大小 1..9（含非 2 次幂）、全域排除、多枚举/FP 条件耦合、NaN、零符号差异、RM、FP↔Real，以及枚举 ITE/recognizer 原路径，见 [guarded/results.json](guarded/results.json)。
4. **资源耗尽与 API 复用。** 护栏使旧低预算输入不再 UNKNOWN，因此恢复测试改用 `rlimit=1`，先确认实际 UNKNOWN，再将预算设为 1000000。分别对护栏外的 1000×100 输入、护栏内的 100×10 输入使用同一 default solver，均依次 SAT→相反假设 UNSAT→pop 后 SAT；两次 SAT 全部原断言（101 条 / 11 条）回读 true。见 [guarded/reuse-results.json](guarded/reuse-results.json)、[guarded/reuse-small-results.json](guarded/reuse-small-results.json)。这也覆盖修订后的模型 converter 及资源异常后清理。
5. **新增/原有 fpa 回归组。** 独立执行 `.tmp/z3-enum-fp-default/build/test-z3 fpa`，退出 0，见 [guarded/fpa-results.json](guarded/fpa-results.json)。
6. **护栏内补充资源样例。** 1000 构造器、4 个常量（累计 4000）在 rlimit 1000/2000/3000/5000/10000 下两版均 SAT，共十次，见 [guarded/below-bound-results.json](guarded/below-bound-results.json)。这不是所有护栏内输入的预算保证。
7. **性能回归重跑。** 原四种规模各两版两次，共 16 次均 SAT；1000×100 与 5000×10 已回到原策略，未重现先前约八倍成本，见 [guarded/performance.json](guarded/performance.json)。本轮墙钟有明显调度噪声，不能由这两次短查询得出精确收益比例。100×10 仍进入转换，仍可能比原生 SMT 多做工作。

## 剩余限制

没有发现新的可复现正确性问题。旧 P2 可以标记“具体反例已修复”，但不能升级为无回退保证：阈值内仍有枚举模型构建成本，FP/BV/Real 求解成本不由此阈值控制；阈值外新增 probe 本身也有遍历开销。任意 timeout/rlimit、内存耗尽和异步 interrupt 时刻的结果或响应时间都不承诺一致。

模型可取不同的合法见证，补丁不保证前后逐字段相同。上述测试和静态分析不代替全部位宽、全部参数、任意长期增量历史以及完整生产 Clause 的验证。
