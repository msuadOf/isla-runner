# 有限枚举使default错过浮点策略的性能改进建议

这是本地草稿，尚未发布。完整复现、版本、源码依据、正式三次结果与验收范围见[评估报告](report.md)。

问题：在浮点query中增加一个不依赖浮点变量的有限枚举相等约束后，default策略变慢；预先dt2bv能改善。分类probe排除datatype提供可核对的原因。

希望讨论：是否应对浮点＋有限枚举的受限组合做预处理或分发改进，使用户不必自行组合dt2bv。这个报告是性能改进建议，不是SAT/UNSAT错误；没有对任意datatype、任意SMT公式保证求解时间。

```smt2
(declare-const x (_ FloatingPoint 8 24))
(declare-datatypes () ((Mode A B C D E F)))
(declare-const mode Mode)
(assert (= mode F))
(assert (fp.isNaN (fp.sqrt roundNearestTiesToAway x)))
(check-sat-using default)
```

对照1：删除Mode声明及mode约束，其余不变。对照2：原公式将最后一行换为 `(check-sat-using (then dt2bv default))`。结果和完整命令见report.md及repeat-results.json。

后续：已按用户指示发布 [#11500](https://github.com/Z3Prover/z3/issues/11500)；实际英文提交正文见[issue-body.md](issue-body.md)。
