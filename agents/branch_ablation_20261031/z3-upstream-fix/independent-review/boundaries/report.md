# Z3枚举／浮点补丁：边界独立审阅

本轮未发现SAT／UNSAT计算错误；发现一项稳定性能退化，有限超时下可由SAT退为UNKNOWN。因此，当前证据支持受限片段上的正确性与目标慢query收益，不支持“各种输入都只改善性能”。建议先处理下面的转换成本边界，再接入。

审阅对象为 `.tmp/z3-enum-fp-default` 的四文件未提交补丁，基线 `8fbb275aba0472e862e289c7af1331b3bd5d512c`。修前、修后二进制均自报5.3.4，未混用系统4.16。源码、库哈希与原交付manifest一致，见 [source-manifest.json](source-manifest.json)、[results.json](results.json)。本轮没有改源码、编译共享build、读其他reviewer报告或启动二级agent；仅在本目录写入。CPU使用100–111，性能比较固定CPU100。

## P2：新增分发无转换成本限制，大枚举的轻量FP查询稳定变慢

位置：`src/tactic/portfolio/default_tactic.cpp:60–63`、`src/tactic/fpa/qffp_tactic.cpp:132–138`。新probe只判断类型形状，不限制枚举构造器数／变量数，就交给 `dt2bv → qffp`。

复现公式只有一个 `(fp.isNaN x)`，另有256个独立枚举变量，各断言 `ei != C0`。它们没有复杂FP操作，也没有枚举变量之间的关系。512构造器时，修前墙钟中位0.02268秒，修后0.24284秒，约10.7倍；1024构造器时0.02692→0.50185秒，约18.6倍。均三次AB／BA／AB、同CPU、双侧SAT。六构造器256变量也有0.02046→0.02586秒的小额增加，但不据此声称普遍显著退化。

相同512构造器公式设置100毫秒timeout，三次修前均SAT，修后均UNKNOWN。逻辑公式没有变错，但在同预算下可用性回退。见 [cost-case.smt2](cost-case.smt2)、[performance-results.json](performance-results.json)、[timeout-results.json](timeout-results.json)。辅助rlimit探针在30000及以上双侧SAT，未发现对应资源计数差异；不把墙钟退化说成rlimit退化。

源码机制吻合：`src/ast/rewriter/enum2bv_rewriter.cpp:163–175` 对每个自由枚举常量急建 `nc-1` 层原类型模型解释ITE，即使最终没有get-model。成本随枚举变量数乘构造器数增长。`dt2bv` 自身没有该规模门槛；qffp会继续执行浮点转换与位展开。该证据确认候选分发存在额外成本，不将全部墙钟差额归为单一内部函数。

修改建议：在混合probe或分发前统计转换成本，例如去重枚举常量数与每sort构造器数的乘积，超出明确定义的阈值保留原策略；同时评估只包含轻量分类谓词时是否值得切换。另一方向是先消除独立枚举约束／延迟模型转换。若采用限时尝试后fallback，须验证耗尽预算和取消后的行为，不能仅加一个无预算隔离的or_else。把上述轻量FP大枚举用例作为性能反例保留；任何阈值应同时重测原慢query，避免把目标收益滤掉。

## P2：现有域约束UNSAT回归不能发现非法位模式漏排除

位置：`src/test/fpa.cpp:455–463`。用例同时断言 `mode = F` 与 `distinct mode A B C D E F`。即使完全漏掉非2幂枚举的范围约束，这两个断言仍然矛盾，因此该测试通过不能证明不存在编码6／7等非法取值。

本轮用原样公式运行verbose，确认它确实进入dt2bv，随后propagate-values定UNSAT；不能说它在dt2bv之前就被simplify解决。详细见 [original-domain-test.json](original-domain-test.json)。

建议新增三个基数1／3／6的自由枚举变量，分别排除全部构造器，保持FP断言且不先固定变量，预期UNSAT；再新增基数n上的n+1个两两不同变量，预期UNSAT。对基数3、6逐一排除其余构造器，核对模型仍能取每个合法构造器。本轮这些例子全部通过，且verbose确认非平凡域探针进入dt2bv。应将有意义的最小子集放入正式回归，而非依赖本目录脚本。

## 本轮验证与可确认事实

运行命令（工作区根目录）：

```sh
/usr/bin/python3 agents/branch_ablation_20261031/z3-upstream-fix/independent-review/boundaries/run.py
taskset -c 100-111 /usr/bin/python3 agents/branch_ablation_20261031/z3-upstream-fix/independent-review/boundaries/api.py
/usr/bin/python3 agents/branch_ablation_20261031/z3-upstream-fix/independent-review/boundaries/perf.py
```

55个独立SMT-LIB输入，修前／修后各一次，共110运行全部符合预期，退出0、无parser错误。每次内部timeout8秒、外部12秒，详细命令、输入、stdout、verbose stderr、状态与版本见 [run.py](run.py)、[cases.json](cases.json)、[results.json](results.json)。机器结果属于有界样本，不是全集等价证明。

| 范围 | 新证据与限制 |
| --- | --- |
| 枚举1／3／6 | 合法模型取值、排除全部构造器、鸽巢UNSAT均符合预期；多个不同枚举同时SAT，模型仍使用原构造器。 |
| ITE／UF／array／ADT／量词 | UF枚举入参、UF枚举返回、枚举数组、FP数组、ADT selector、量词均正确，verbose未进入新增dt2bv路径。枚举ITE原式可由simplify规约为Bool组合，因此该样本最终进入新路径；这是规约后的受限式，不能声称所有含ITE源输入都绕过新路径。 |
| 非目标片段 | 纯BV、纯FP、纯enum、仅未用enum声明、不解释sort、Int混合均符合预期；未观察到dt2bv误分发。只有unused sort declaration不会触发。 |
| FP／Real／舍入 | Real到FP且要求NaN为UNSAT；NaN的fp.to_real可取任意实数，SAT；五种舍入模式的半ULP加法结果符合IEEE预期，反结果均UNSAT。qNaN、sNaN、负无穷、负数sqrt产生NaN，负零和最小正subnormal sqrt为非NaN。具体运算样本部分可由重写求值，不外推深度FP电路。 |
| proof／core | 两种模式均UNSAT且分别取得proof／core，无报错，verbose未出现dt2bv；未由外部proof checker验证proof对象。 |
| CLI增量 | SAT→带假设UNSAT→push后SAT→嵌套矛盾UNSAT→pop恢复SAT，全序列一致。 |
| C API模型转换 | 修后default策略solver上，1／3／6各6次check，共18次；正假设SAT、负假设UNSAT、UNSAT后恢复、两层push／pop均正确。64次原断言model_eval全部true。见 [api.py](api.py)、[api-results.json](api-results.json)。未构建baseline库，API对照基于已知逻辑预期及双侧CLI，并未声称同版本双库API比较。 |

对照实际 `dt2bv` 实现：`check_fd` 先排除不能转换的sort，重写enum等号／distinct／recognizer；`enum2bv_rewriter` 采用至少1位编码，在非2幂以及基数1上添加上界约束；模型转换器隐藏新BV符号并补回原枚举常量解释。新probe允许的枚举节点是零参数不解释常量和构造器，拒绝一般enum返回表达式；FP、BV、Bool、Real限制继承原probe。proof／core路径显式绕过。该结构与本轮边界结果一致。

## 未测与结论边界

未测试完整Clause7200秒、Isla实际长增量历史、跨线程context／solver translate、取消与内存极限、模型completion=false、目标系统全部FP宽度（本轮新增数值例为binary32）、符号舍入模式深度运算、所有参数组合、随机fuzz或外部完整证明检查。没有给出所有输入的性能保证。现有测试覆盖和源码复核未发现逻辑不等价反例；性能反例已足以否定“改后只有改善、没有回退”的绝对主张。
