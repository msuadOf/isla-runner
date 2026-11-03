# 精确转换助记符：现行设计与历史方案

现行版本为模型 `21418d0b0d4942fae20061ed580ee04aff4a8a61`。五条固定 `(op, RM_RNE)` 的双向专映射位于完全保留的 generic 双向映射之前。Sail 按顺序选择具体模式，因此五个 RNE 指令输出不带 RM 的 canonical 文本；其他 op 与非零 RM 进入原 generic 映射。旧显式 `, rne` 的反向声明保留。这些模式有重叠，不能称为互斥 guard。

独立检查已确认仅增加五块、20行源码，删除这些块可逐字节恢复 `8ad5e8e` 的两个文件；真实 Sail→C→native forward probe 1104/1104 通过。新四配置 IR 仅三个 assembly forward 函数变化；三函数×五op×四配置的60组顺序检查确认具体 RM_RNE 检查先于 generic，非匹配失败边进入后继映射，generic 仍调用 `frm_mnemonic_forwards`。证据见 [源码审查](assembly-source-review.json)、[实际IR顺序](assembly-ir-order-21418d0.json)。

反向执行有既存工具限制：baseline 与 candidate 的完整 string-concat reverse mapping 都在真实 Sail 中标为 NonExec。当前只能签反向声明/类型合同，不能声称实际 reverse runtime PASS；验收者记录该边界。方向拆分方案曾使 forward 也变为 NonExec，已撤销。

以下保留实施前与中间方案记录，均已被上述现行设计取代，不作为最终实现说明。

## 历史：实施前独审

认可只改五个指定 op 在 RM_RNE 时的 canonical assembly 映射，生产范围为模型 `FD/dext_insts.sail` 的 FF/XF 映射与 `FD/zfh_insts.sail` 的 FF 映射。依据为独立验收者的 [112个工具链探针](../acceptance/exact-conversion-syntax-independent.json)与[最小修复意见](../acceptance/exact-conversion-fix-opinion.md)。普通数值、flags、编码、合法性及 generic Isla representation 不在本次源码修改范围。

| 映射 | 新无RM专映射 | generic forwards 保留条件 |
| --- | --- | --- |
| D-FF | `(FCVT_D_S, RM_RNE)` | `op != FCVT_D_S OR rm != RM_RNE` |
| D-XF | `(FCVT_D_W, RM_RNE)`、`(FCVT_D_WU, RM_RNE)` | `(op != FCVT_D_W AND op != FCVT_D_WU) OR rm != RM_RNE` |
| H-FF | `(FCVT_S_H, RM_RNE)`、`(FCVT_D_H, RM_RNE)` | `(op != FCVT_S_H AND op != FCVT_D_H) OR rm != RM_RNE` |

以上三个 op 集分别有3、4、5个成员，RM 枚举有6个合法成员（0–4及动态7）。72个 op/RM 组合中，新专映射恰覆盖5项，generic覆盖其余67项，互斥且完整。无RM文字反解析回固定 RM_RNE；非零 RM 不省略，仍精确保留原编码。D.L、D.LU、S.W 可能舍入，属于负对照，不能套用此规则。

初案（已撤销）：guard 同时作用于双向映射，因此五个 op 的旧显式 `, rne` 文本将被排除；新 canonical 无RM文本可反解析。已向主 agent 说明该输入兼容边界并要求实际负例，不声称只改变输出而保持全部旧解析文字。若要继续接受旧显式RNE文字，需要另行设计仅 backwards 的别名；当前不扩大最小生产范围。

源码阶段须核固定枚举、寄存器类型和顺序、guard 的括号/优先级、两向互补及非目标文本不变。验证须实际执行 Sail assembly 与 backwards mapping、encoded bits 往返；单纯Python字符串替换不能证明模型映射。五op×六RM与D.L/D.LU/S.W负对照，以及GNU/Clang实际字节/.insn比较均须核账。非零RM的GNU显式文本拒绝仍是能力边界，不能省略RM导致机器字变成000后冒称精确通过。

本页仅签设计。源改后重新冻结 commit、生成 IR、检查函数差异/CFG；`8ad5e8e` 的已有来源与动态结论保留历史适用版本，不迁作新版本 PASS。

主 agent 后续明确要求保留旧显式RNE输入。现行方案将三条generic映射拆成带上述互补guard的forwards，以及保留原显式RM全域的backwards；五条无RM固定RM_RNE双向映射保持。故同一RNE指令只输出canonical无RM文本，但新无RM与旧显式RNE均反解析到原指令。文本域按有无RM后缀分开，须实际验证整串消费以免非零RM被前缀误解析为0。最终源码和双向验收由acceptance独立审查者接续，本审查者回到memo/CFG。
