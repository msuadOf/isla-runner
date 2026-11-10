# XiangShan issue 逐条复核

用户要求对公开 issue 逐条查看，不能仅以关键词筛选宣称找全。本轮输入为同目录上一级 `github-issues-all-20260929.json` 的 898 条标题和完整正文；`github-issue-details-20260929.json` 在收齐后提供各 issue 公开页面的评论、标签、关闭与关联 PR。若时间线首屏少于总数，标注 `timeline_incomplete`，不要猜测被隐藏的评论。

按全量快照数组的顺序分五批，四名 Sol 子代理只写各自 `batch-N.json`，主代理写 `batch-5.json` 并核对总账。代理不得修改主表、状态、其他批次、源码或 GitHub；不得调用二级代理。边界：1=索引 0–179（#16–#1609）、2=180–359（#1624–#3289）、3=360–539（#3306–#4664）、4=540–719（#4665–#6048）、5=720–897（#6057–#6647）。编号上下界只供导航，**以数组索引为准**。

每个 issue 在对应 JSON 的 `rows` 中恰有一项：`number`、`fp_relation`（`direct`／`shared-trigger`／`incidental`／`none`／`uncertain`）、`classification`（`dut-confirmed`／`dut-reported`／`reference-model`／`duplicate`／`invalid`／`tool-build`／`non-bug`／`out-of-scope`／`uncertain`）、`evidence`（简短指出题目、正文或哪位评论证明分类；`none` 也需写出该 issue 的实际主题）、`fix`（已知 PR/commit 或 null）、`timeline_incomplete`。`direct` 表示浮点指令／状态是被报告的错误对象；`shared-trigger` 表示 FP 指令是通用内存／异常／写回问题的实际故障指令；长 fuzz trace 里偶然出现 FP 指令记 `incidental`。非浮点的真实 bug 用 `out-of-scope`，不要误写 `non-bug`。

先逐条读标题／正文，再核对评论和关联 PR，**关闭不自动等于修复**；维护者在评论确认的已关闭 bug 应纳入候选。每批输出 180／最后178 条，不能漏号、重复号。主代理按每批 `direct`／`shared-trigger` 与旧表交叉检查，复核所有 `uncertain` 和首屏时间线未闭合的潜在 FP 条目后，更新同目录上一级 `xiangshan-github-float-issues.md` 及状态摘要。

## 本轮完成账（2026-09-29）

全量标题／正文 898/898；公开页面 898/898；37 条首屏未完时间线已取 `timeline_page=1`，最终 898/898 `visible=total`。五批 `batch-1.json` 至 `batch-5.json` 合计 898 行、898 个唯一编号，数组顺序逐条相等；关系分类为 `none` 796、`incidental` 56、`direct` 35、`shared-trigger` 10、`uncertain` 1。这里的 `direct/shared` 包含问题、误报、参考模型和重复项，**不等于 46 个真实 XiangShan FP bug**。最终表格为上一级 [xiangshan-github-float-issues.md](../xiangshan-github-float-issues.md)；自动守恒与快照哈希见 [summary.json](summary.json)。截图和附件没有逐一下载，清单只签公开标题／正文／评论的逐条核对。
