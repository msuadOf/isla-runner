# 精确转换三表示复验准备（未运行新 IR）

本轮仅更新验证侧消费规则，生产模型与 Isla 未改。前一批次 `model-8ad5e8e` 的 18 项 GNU 助记符失败仍保留在 [原报告](report.md)和原始 `toolchains/results.json`；它不能迁为修后通过。

[新检查器](check_exact_json.py)继续实际执行通用检查器的 GCC/Clang×助记符/`.insn`/精确字节六项汇编，并保留原 `results.json`。仅当实际机器字的 `(funct7,rs2)` 是 `FCVT.D.S`、`FCVT.D.H`、`FCVT.S.H`、`FCVT.D.W`、`FCVT.D.WU` 且 RM 非零时，允许 GNU 原助记符失败后选择**本次已实际汇编**且与原机器字逐字相同的 `.insn`；同次字节形式与 Clang 原助记符也必须精确通过。选择及原失败数另写 `selection.json`，不把原 `pass_` 改写成预期拒绝。RM=000 的五种操作必须使用无 RM 助记符，GNU 与 Clang 都须成功并逐字相同。`FCVT.D.L`、`FCVT.D.LU`、`FCVT.S.W` 是负对照，仍须显式 RM 且两工具链助记符精确成功。

验证：`PYTHONDONTWRITEBYTECODE=1 python3 agents/float_review_closure_20261102/validation/representations/test_exact_checker.py` 退出0；核独立 112 次工具链探针的八种操作分类、五种精确操作×六 RM 的 30 个消费组合、三种负对照×六 RM 的 18 个组合，以及 `.insn`/Clang 失败、RM0有显式参数、负对照失败等红例。将检查器应用于前一批次真实 sqrt H/D JSON 与工具链记录，分别仅能接受 10/5 个非零 RM GNU 回退，RM0 仍留下 2/1 项原失败，结果保持红。这证明检查器没有用回退吞掉必须由模型源码修复的 RM0 文本。

当前只完成脚本准备和旧批次红测；新模型提交、严格 IR、冻结 inputs 及新 JSON 均尚未用于此检查器。脚本变更已送独立审查，审查签收后才按新唯一批次运行。修后动态结论另记新结果，不覆盖此页。
