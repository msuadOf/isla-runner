# 0008fae共同参照下的最小性收敛

用户2026-11-03要求：Isla共同参照0008fae76f4cff86dae1a036d889f0414c228e9d，增量越小越好；除有实测超时/理论依据或必须控制语义，不加多余branch/wrapper/helper。该对象只在Isla存在；模型按原4f2、短期6202/214逐项关联，不跨仓git diff。

独立Sol审查分两组：enum_review核Isla生产增量及已有证据；model_review与acceptance分别核模型控制/数据流与精简等价。枚举缓存、编码隔离、ExecuteAs都有实际错误/超时证据，保留最小实现。历史trace/V/用户初态配置不擅删；其他策略候选与输出影响分别见[Isla审查](isla-review.md)。

实施确定项：在独立named模型树（非runner-float冻结214）仅改core/ieee_fp_exceptions.sail，18处纯返回条件恢复facts/原ITE，6个已被finite gate保护的mask调用直接facts并删除冗余helper；NaN/Inf/零、invalid原因、finite/valid、饱和、changed写回和ROD模式分支保留。完整算式/flags不变，不假定OF⇒NX，不宣称性能提升。

候选源签后提交→新模型路径严格生成四配置IR/ordinary（独立copy同配置已审memo）→更新永久测试合同，仅检查必要控制，不再要求纯数据fork→重新定向oracle/flags/双工具链→独立Sol分阶段签→预算/版本同步。214/420冻结77长跑继续记录对照，不能改其HEAD/输入/文件。若预算超时，先核单次SMT/路径/trace开销与CPU竞争，不直接定性源码退化。

当前18site+mask精简已提交为模型 `e9d69d2f28586c089244c8e37ee4c904c5114458`，两位独立Sol均签收源码；ordinary及四配置strict/IR均生成成功，模型Sol已签来源与IR数值/控制核查；永久checker与动态仍分别验收。不将源码签收视为动态通过。


## 最新架构准则优先

上文关于保留控制的判断属于e9精简时的旧审查口径。用户随后收紧了新增显式分支的证据要求：按[统一最新准则](../../../specs/GOAL.md#浮点架构决策准则2026-11-03-最新用户指导)，控制流分类不能替代实际瓶颈或预算路径规模证据；普通数值饱和/flags返回也不能仅凭名称判控制流。Sol正在另出逐项架构裁决，旧源码/数值等价签收不自动构成新口径的架构批准。当前冻结源码/IR/输入不改。
