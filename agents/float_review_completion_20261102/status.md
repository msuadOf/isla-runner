# 浮点 review 剩余项（2026-11-02）

汇编三表示与 ExecuteAs 已实施、独立复审和限定集成验证通过；数据条件核账及定向补验已完成，覆盖仍为 PARTIAL。消融单独冻结修复前程序，见 [协议](../branch_ablation_official_z3_20261102/protocol.md)，不混算修复影响。

- [汇编表示](assembly/report.md)：模块五项单测、36项 GCC/Clang 定向检查通过；生产 CLI 三批13条、78项双工具链检查通过，保留4条Clang拒绝助记符的非法用例。非法 BF16 助记符保留，精确位串/字节及 `.insn` 同时提供，不删除模型非法路径。
- [ExecuteAs](executeas/status.md)：真实红绿例完成：`0x1fe0`、x2=7、立即数1020，旧输出x8=7/ExecuteAs，新输出x8=1027/Retire_Success；[绿例](executeas/green/checks.json)。保留阶段状态及累计预算；补充独立collector借用生命周期，旧公开接口别名兼容。collector库测试11/11、三表示5/5、API与SMT统计各1/1通过，后两项均有红例。
- [数据条件](data-conditions/report.md)：6次Clause/40条JSON均finished，补左源单独sNaN/qNaN及rec7/rsqrt7正常/次正规四个活动lane见证。右源单独qNaN/sNaN仍缺，其他格式、静态rm非法编码、BF16融合/多lane异常仍有义务，详见25组账本，不作为覆盖率分母。
- [独立代码审阅](assembly/review.md)：未发现新状态/预算/编码阻断；SMT累计统计尾段快照P2已修复、先红后绿复核关闭，无新增阻断。

未修改 Sail 模型/IR/父 gitlink，未提交或推送。root Isla 与 runner-float的5个改动文件已逐字同步，二者正式Release均构建通过、确认链接官方1fd1d3613；[最终版本及make验收](final-verification.json)。新统计版本在隔离输出目录执行真实`make solve-C_ADDI4SPN`，原编码立即数4、x2=7、x8=11且Retire_Success，runner独立CLI绿例亦通过。memory不属于本轮代码修改范围。

本页前文是三项修复当时的交付记录（含当时未提交状态）；后续已通过Isla09ffa91/09678a7提交并由f152290同步新模型IR。显式分支恢复和最终7/7组合验证见[现行状态](../explicit_branch_restore_20261102/status.md)。历史数据条件见证仍受其受测版本和定向域限制。
