# 仅浮点分支复审与修复状态

2026-10-08：**修复已提交／限定PASS**。`feat/float-only-20261008@be1296b`，两个提交`5ceb3ad`和`be1296b`均按`fix(scope): 中文说明`。四份旧IR的缺体helper补齐；五份IR的快速FPR getter/setter恢复扩展断言、转换、callback和Dirty副作用，RV32仍更新SD31。

最终1615例helper差分、180状态＋20隔离guard、BF16六例、legacy35、原语10、isla68＋bin25（跳1个既有失败）、默认编译/fmt及两装配负例通过。四份RV64 make均MRET4／FLEQ.S16，默认另BF1639／FLI.S32。独立gpt-6-astra high复核通过；受审工作树干净，原isla HEAD／索引／两层补丁hash不变，未push。

未全77项／硬件／公共RV32入口。其他旧IR的BF16 execute历史实现与v512实际V256保持；组件装配不是全模型重生。原报告仍适用于修前d04883b。

- [修复交付、提交与最终证据](fix.md)
- [计划](plan.md)
- [修前审查报告](report.md)

2026-10-29 当前general ef882f0＋float be1296b相对7b7337b的组合复审完成；新增独立runner缺字段兼容问题，旧ret_val具化缺口及配置偏好建议另列。[现行复审](../general_float_review_20261029/report.md)。历史版本的PASS与受审边界保留。

2026-10-29后续交付：两分支已按指定顺序合入feat/float-support@31506ee，runner兼容及ret_val具化两项已修复，独立GPT-6.1 Sol最终审核通过；旧结论按其版本保留。[合并记录](../general_float_merge_20261029/status.md)。

2026-10-29术语后续：源general已cc7700b、float-only已99a28b0，分别独立统一具体化命名并新增术语规范，目标按序合回75e7440。[状态与验证](../terminology_concretization_20261029/status.md)。
