# 56cc 已映射 source/root 子集独审

本工具只写独立审查证据。生产源码、原 v1 账本及其 producer 均不修改。

`review.py` 从冻结源码重算 ordinary 结构规则，并以冻结 typed sidecar 独立枚举原 v1 的 source/arm/root 键。短路结构在 default 配置重跑词法与 CFG 检查，其余配置核对相关完整函数的 typed 结构一致。每个有见证的义务选择一个实际 case，逐 phase 重建完整指令、Jump、嵌套 Call 和正常 End，校验日志中的指令数和函数集合。完整输入、结果、R1、trace-map、所有终态及全部 runtime Jump 目录逐组核验。

`finalize.py` 将六配置与 15 主批加 3 增量的实际审计清单联立，核对 extractor 的实际 argv、二进制、源码、IR 与 config，再按精确键复核既有 num32 的 70 项。它拒绝超出枚举的 `allowed_claim`。证书中的计数和总状态不能代替逐键许可。

范围为每配置 547 个已有映射 site 产生的 13825 个保守义务。121 个缺映射 site 的 caller 展开、短路 RHS 值与异常、27 项迁移、每配置 228 个 V4 `not_lowered` 义务均不因此闭合。原始 70 项仅继承 default、Machine、SEW16、LMUL4、VL0 域。ordinary 结构重算和动态见证不会自动升级源码 predicate；短路许可只覆盖 LHS。

在仓库根目录执行，`p1_snapshot` 指向冻结目录 `isla-unified-p1-v4amo-candidate-20260927.nb1d9n1s`；`ledger_review_output` 必须使用新的空目录：

```sh
python3 -m unittest discover \
  -s agents/float_support_review/tools/solve_vector_ledger_review \
  -p test_review.py

python3 agents/float_support_review/tools/solve_vector_ledger_review/review.py \
  --stage isla/target/float-support-review/final-coverage/integration/p1-56cc69 \
  --snapshot "$p1_snapshot" \
  --output "$ledger_review_output"

python3 agents/float_support_review/tools/solve_vector_ledger_review/finalize.py \
  --stage isla/target/float-support-review/final-coverage/integration/p1-56cc69 \
  --review "$ledger_review_output"
```

`--config` 可按配置前缀分别复核；default 配置须先生成短路函数结构摘要。工具只解析现有证据，不运行 solver。单进程实际驻留内存约 1.1 GiB。

最终证据入口为根目录下 `isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-source-root-ledger-review/attempt3/certificate.json`。

六个调用重建拒绝测试先红后绿。实际负控使用另一真实同 callee root、真实替代 context、另一源码 arm、已有不同 callee、另一真实 config、删除 Jump、减少指令数、删除实际输入 case。只有 decode 拒绝的 F-off 配置没有执行期 root 负控；其它五配置各八项，合计 40 项拒绝。

准备过程的失败日志保留：第一次发现共享标量校验器按字符串比较十六进制前导零，现只规范化同字段数值拼写并保留原文件 SHA；第二次完整路径遇到 `internal_vector_init`，现核对冻结 executor 与符号表后显式允许向量 init/update 原语。最终汇总首次在构造 schema 字段示例时失败，修复后重新核验全部依赖并生成证书。这些失败均属于独审工具准备，不是模型求解失败。
