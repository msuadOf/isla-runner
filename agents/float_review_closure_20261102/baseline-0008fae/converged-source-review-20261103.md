# 77处回退最终实际提交源码独审

**实际模型提交源码签收，无源阶段阻塞。** 新树`.worktree/sail-riscv-float-converged-20261103`干净，最终模型为`0f7b8fbc6724103f91f929ef6918f123df75d6c9`，基于冻结e9。用户已明确授权应用77处回数据流，OPEN按e9保持并延期，延期事项不作为本阶段必须继续研究的阻断。

三个单亲提交职责和实际变动文件完全匹配：

| 提交 | 范围 |
| --- | --- |
| `3d9ceebb8ae81b45ccafcde7cab81c0ab5b49bd8` | core算术异常33处原因分支恢复Bool事实 |
| `7eb4bd5c137c500209678f2f6eb007b572179b74` | 六窄适配器本轮八处纯结果分支回6202数据流 |
| `0f7b8fbc6724103f91f929ef6918f123df75d6c9` | FD十二整数包装36处纯结果分支回6202数据流 |

五个实际文件逐字等于[已签候选](architecture-candidates-review-20261103.md)：core SHA256 `7ed9529b…`、V工具 `34191de9…`、FD f16 `71579579…`、f32 `ffe71d8f…`、f64 `b5b8ea9e…`；完整哈希见[机器结果](converged-source-review-20261103.json)。166个受控模型文件中，其余161个逐字等于e9；除这五文件没有其他提交增量，无未提交源码。

已专门核全部KEEP及延期OPEN保持：changed/Ext_F所在FD寄存器整文件、两ROD模式包装、FPint/round/转换/BF16/ROD内层helper、普通六窄adapter、NaN分类/canonical和汇编映射保持原字节；18算术helper的finite/valid gate仍在；f16→I16既有外overflow if保留，其内端点回ITE。原33原因谓词及flags五位、完整FP数值算式及负NaN饱和规则由前次实际候选源证明支持，本次精确文件一致核查未发生漂移。

延期清单：29个有限/范围计算gate、changed外层1处、ROD模式2处及6202既有f16→I16外overflow1处。用户接受按e9留存到后续配置/版本讨论，本阶段不继续扩研究，也不把延期改署架构永久批准。十个underflow/facts局部名原样保持，为非阻断文字选择。

冻结named e9与runner-float214的HEAD及各166个模型源哈希仍与其生成清单一致，没有修改其源码、IR或inputs。本结论是最终实际提交的源码身份/范围签收；**新ordinary/SYMBOLIC strict、新IR/配置及最小永久checker、动态预算另行验收**，旧e9/214结果不迁作新模型PASS。

重跑入口：[独立源码审查脚本](converged-source-review-20261103.py)，仅写审查结果，不修改生产。
