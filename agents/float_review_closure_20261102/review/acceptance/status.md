# 最终动态独审状态

**本轮用户授权的浮点收敛范围限定通过，无剩余阻断。** 最终签收：[final-signoff.md](final-signoff.md)、[机器证据与完整哈希](final-signoff.json)。模型`0f7b8fbc`，集成Isla`591693df`，受测程序明确由`42000be`构建、SHA`acda0dce…`；591仅六生成+四测试，生产Rust/Cargo字节相同。父仓最终gitlink提交由主agentrefseal。

| 最终验收 | 结果与证据 |
| --- | --- |
| 77回退/OPEN冻结 | 五文件逐字等于批准候选，NaN/trap和非目标字节保持；[来源绑定](converged-source-binding-independent.json)、[源码主签](../../baseline-0008fae/converged-source-review-20261103.md) |
| strict/IR/永久检查 | ordinary+四配置strict、276672返回比较；8正控/104负控、安装5入口；[IR主签](../../baseline-0008fae/converged-ir-review-20261103.md) |
| flags300 | actual old/incoming/pre-state独算全符；[数值](flags-converged-independent.json)、[来源](flags-converged-provenance-independent.json) |
| 转换819+282+183 | 独立Fraction及直接runner观察域通过；[数值](conversions-converged-independent.json)、[来源](conversions-converged-provenance-independent.json) |
| 异常315 | actual JSON/SoftFloat全符无skip；[数值](exceptions-converged-independent.json)、[状态来源](exceptions-converged-evidence-independent.json) |
| assembly/Make | 新1104前向/5824字节，Make8JSON/48通过；[汇编](assembly-converged-records-independent.json)、[Make](make-converged-independent.json) |
| 正式完整入口 | FLEQ_S48/27.67s、C_ADDI4SPN1/2.038s，原完整域/T1/qffp/seed17/双7200；[FLEQ](clause-FLEQ_S-converged-independent.json)、[C](clause-C_ADDI4SPN-converged-independent.json) |
| 集成/时序 | 最终10文件精确树/hash、run-all26全过、官方库；315在共享clone变动前完成；[集成](final-integration-independent.json)、[时序](final-execution-timeline-independent.json) |
| 旧77历史 | 21449/28、e952/25，失败53项全外限124无完整JSON；迁存保留；[失败分类](historical-full77-failures-independent.json)、[迁存](historical-migration-independent.json) |

最终范围按[用户授权退出矩阵](final-exit-scope.md)，详情见[最终动态报告](model-converged-results-review.md)。不宣称新全77预算或全输入/向量域/所有FMA/Zfinx/硬件/动态反解析。changed、29 finite/valid、2ROD模式、既有f16→I16外overflow和策略问题按用户决定冻结延期memory，不自动变成KEEP，不再作为本轮结项阻断。

历史[e9签收](modele9-results-review.md)、[214签收](model214-results-review.md)及旧8ad报告保持原版本，不迁PASS。原先将全77预算或逐异常原因自然路径当作本轮必要退出条件的记录已被最新授权范围取代，保留历史依据。
