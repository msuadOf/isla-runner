# 三表示与真实 Make 独立审查

新IR批次的三表示验收仍有阻断：111条实际JSON的666项工具链检查中648通过、18项GNU助记符失败。真实Make定向smoke则限定签收：退出0、4.02秒、8条JSON、48项三表示检查通过。不能用Make成功覆盖前者失败。

同批固定模型 `8ad5e8e`、Isla `42000be`、IR `5ecea371…`、interrupt程序 `fe4bdceb…`、正式inputs `25a1a624…`、官方库 `899cbc70…`、seed17。原始入口分别为 [三表示报告](../../validation/representations/report.md)和 [Make结果](../../validation/make/model-8ad5e8e/smoke/result.json)。

## 阻断：精确宽化的 GNU 助记符

`sqrt-H`所在完整Clause还生成了宽化转换，12项GNU助记符失败；`sqrt-D`对应6项失败。三个操作是 `fcvt.d.s`、`fcvt.d.h`、`fcvt.s.h`，例如 `fcvt.d.h f0,f0,rne`（机器字`0x42200053`）及 `fcvt.d.s f0,f0,rdn`（`0x42002053`）。这些JSON的Sail返回都是Retire_Success。Clang接受显式舍入模式并保留实际机器字；GNU拒绝该语法。两工具链的字节和.insn表示均匹配。

独立24次汇编探针见 [widening-representations-independent.json](widening-representations-independent.json)：省略RM时两工具链都编码为rm=000；显式rne/rdn被GNU拒绝，Clang分别保留0/2；`.insn`在两侧均保留原字。因此只删除RM能修rm=000文本，但对非零RM会改变机器字，不能称三表示精确一致。应由实现阶段确定可移植表示合同并修复；不能把这18项合法输出的失败改为“预期拒绝”后宣称PASS。

## 独立核账与 Make 范围

[audit_representation_results.py](audit_representation_results.py)从实际JSON机器字重新推导字节，核全部encoding位串/hex/bytes/.insn字段，逐条检查归档源代码、工具退出及实际.bin字节，不只读取all_pass。见 [独立结果](representations-make-independent.json)：111条JSON/666检查的失败分布确认为上述18项GNU mnemonic，其他648项符合合同。非法BF16布局的Clang助记符拒绝另按既有合同计，原始精确编码和.insn仍可用。

Make使用冻结runner-float的真实run.mk、私有程序软链、新IR及固定初态配置；JSON自身provenance实际argv为T1/qffp、执行和SMT各7200秒，IR/config哈希与实际文件一致，seed日志实际fixed17。8条FLEQ.S见证覆盖有限/有限、有限/qNaN、qNaN/有限、qNaN/qNaN四种实际读源组合各2条。独立从机器字解源/目的寄存器，核flags与数值比较结果、FPR和其他GPR保持；4条rd≠x0直接可观察结果，另4条写x0被架构丢弃，不将其说成可观察目的结果。48项GCC/Clang助记符/字节/.insn归档字节全部一致。

Make只是固定初态的入口smoke，不是64受影响Clause的完整域预算。此页只签42000be/指定IR当前实际证据；后续表示修复须重新绑定程序/源码，并重跑相关三表示与入口验收。
