# 当前状态

源码已分类提交至 `a9fd947`；独立 GPT-6.1 Sol 对源码、四配置实际 IR、56项动态结果均审查通过。五份IR已安装，25步整体回归、正式make入口及双工具链检查均通过；Git版本同步见versions.json。

| 提交 | 范围 |
| --- | --- |
| `350a072` | core 中每个源独立的 NaN/sNaN/qNaN 异常行为 |
| `f263774` | f16/f64 与 f32 转格式结果的 canonical NaN 出口 |
| `eb17b05` | 剩余 16 个普通/比较/归约浮点运算活动 gate |
| `a9fd947` | BF16 分类及四个转换/融合运算活动 gate |

模型来源为 float 工作树，普通 V/BF16 `$else` 实现与上一版逐字相同。没有触碰根 `sail-riscv/` 未提交内容。BF16 FMA 仍为单次原生 fused 运算，flags 仍按集合 OR 合并。

证据：[源码红测](implementation/source-red.json)、[源码绿测](implementation/source-green.json)、[独立字段核算](implementation/source-oracle.json)、[修改函数清单](implementation/changed-functions.json)、[源码区域检查](implementation/region-validation.log)、[Sol 审查](review/classification.md)。区域检查79配置/132region/22锚点通过，历史基准IR哈希警告保留，不等于当前IR行为验证。

普通严格检查、四配置 SYMBOLIC 严格生成全部退出0，源提交及166件模型源哈希全程未变；记录见 [生成汇总](implementation/generation-summary.json)。实际 IR 行为由独立审查另行签收，不能以编译通过代替控制流检查。完整 Clause 外限与 SMT 限时均7200秒；新增多源与多 lane 组合能否在预算内完成仍待新 IR 实测。

未纳入：`accrue_fflags changed`、窄整数 `overflow` 两处超时条件；五位 flags 最终打包、Inf 抵消/零除等其他异常原因与 ROD 选择均未在本轮全部显式化，不能宣称所有特殊行为覆盖已经闭合。

## 新 IR 实际结果

四配置来源审计、24个异常函数独立源角色、15个NaN出口、20个运算活动分支均通过；六个破坏分支控制关系的负变异均被永久回归拒绝。见 [Sol报告](review/report.md)。

56项定向完整Clause全部退出0、finished，156条JSON、3518项断言通过，单项2.468–53.174秒。左右独立NaN、H/S/D分类、BF16三源sNaN、VV/VF两种融合边界×五舍入模式、mask0/1/2/3与vl0均有实际结果。见 [结论](validation/conclusion.md)。这是固定域、vl≤2的定向验证，不代表默认全域或全模型完整覆盖。

超时调查见 [报告](../explicit_branch_timeout_diagnosis_20261102/report.md)：flags主要是昂贵浮点异常约束导致许多SMT查询变慢；旧饱和实验还对vl1以外的七个lane先计算再屏蔽，造成额外分叉。新增活动分支已跳过不活动lane，但旧饱和超时不能直接外推至修正后的循环，overflow显式化仍需重新预算实验。

最终25步整体回归全部退出0；正式make solve-FLEQ_S为3.692秒、8条JSON；GCC/Clang三表示60/60精确编码检查通过。无Rust源码改动，无需重新格式化或重编译Release；生产变更为模型与其完整IR。未推送远端。
