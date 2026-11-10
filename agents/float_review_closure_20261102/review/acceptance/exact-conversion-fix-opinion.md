# 精确转换助记符最小修复意见

用户允许没有工具链精确助记符时交付`.insn`/字节。按此合同，应修五种转换的rm=000规范文本；非零rm保留原文本和机器字，并明确GNU不能用该助记符精确保留编码，实际消费精确表示。无需在generic Isla中硬编码RISC-V语义或新增JSON兼容性字段。

## 独立工具链界定

[112次探针](exact-conversion-syntax-independent.json)实际覆盖两工具链×8操作×7种RM文本：

| 操作 | GNU | Clang |
| --- | --- | --- |
| FCVT.D.S、FCVT.D.H、FCVT.S.H、FCVT.D.W、FCVT.D.WU | 只接受省略RM，编码rm=000；显式rne也拒绝 | 省略RM或显式rne/rtz/rdn/rup/rmm/dyn均接受，实际字段保留 |
| FCVT.D.L、FCVT.D.LU、FCVT.S.W（负对照） | 显式RM接受并保留 | 同左 |

五种精确转换中，32位整数均可放入53位有效精度的D；H→S/D与S→D也精确。D.L/LU及S.W可能舍入，不能套用删除RM。此意见不改任何数值、flags、编码或合法性规则。

## 最小生产边界

仅改模型相对路径 `model/extensions/FD/dext_insts.sail` 的 `F_UN_RM_FF_TYPE_D` 和 `F_UN_RM_XF_TYPE_D` assembly映射，以及 `model/extensions/FD/zfh_insts.sail` 的 `F_UN_RM_FF_TYPE_H` assembly映射：五个指定op且RM_RNE时输出不含RM的标准文本；其余op或非零rm保留原文本。新增条款须避免与原泛化映射重叠造成双向解析歧义；用实际Sail assembly往返测试证明解析回来仍是原op/RM_RNE，而非只对字符串做替换。

rm非零不能简单删参数，因为GNU会编码rm=000；须保留原助记符文本和原精确位串/`.insn`。GNU这部分的拒绝可记录为已实测工具链能力边界，但验收必须实际汇编选中的`.insn`或字节并与原机器字比较，不能只把失败布尔值改为预期拒绝。Clang显式RM仍应精确通过。

`src/isarch/representation.rs`现有合同明确“不推断助记符是否合法”，已经提供mnemonic、complete位串/hex/bytes及`.insn`。这里无需增加按操作码猜工具链兼容性的字段，也无需改成RISC-V专用输出器。消费者应按本机汇编器实际结果及字节比对选择已提供的精确形式；这与内部不变量错误的兜底不同。当前 `difftest-xiangshan/pipeline.py` 的 `payload_insn_line`已始终按原机器字发`.2byte/.4byte`，助记符仅用于注释/前导识别，此问题不使它的payload改字。

## 验证与完整批次

先红后绿验证五op×RM0–4/dyn×两个工具链，精确rm000检查无RM文本、非零检查Clang保字与GNU精确替代；负对照D.L/LU/S.W保持显式RM。生成实际新IR并跑真实JSON三表示，不能只测试手写字符串。

assembly映射会进入IR并改变IR哈希。当前完整批次既已停止等待重封，建议在修复、严格生成和最终inputs冻结后再启动，避免把正式77条拆为第三个未稳定版本；停止的旧批次只留真实退出/日志，不当完整预算结果。数值表达式和控制流未变时，可通过逐函数IR差异、生产执行源码哈希和已完成动态证据界定适用范围，不能静默宣称旧结果受测了新commit。

前一页18项GNU助记符FAIL为原验收器要求所有助记符都精确汇编时的真实结果，应保留。按本页用户允许精确替代的合同，修完rm000语法并验证非零精确替代后，非零GNU能力边界本身不再是生成器阻断。
