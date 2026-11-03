# 五种精确转换 assembly 源码独审

模型 `21418d0b0d4942fae20061ed580ee04aff4a8a61` 的两文件修改及正向输出限定签收，无新增源码阻断，可进入完整严格生成与新IR验收。**反向字符串映射只签源码/类型合同，未通过动态执行**；当前Sail的NonExec与解释器限制在下文单列。

| 模型相对文件 | 受审 SHA-256 |
| --- | --- |
| `model/extensions/FD/dext_insts.sail` | `1e0397fbc2988383a064a6cfc26f8870464122cd136fc62537e0612ab07ee688` |
| `model/extensions/FD/zfh_insts.sail` | `f5e7311bc490c2cb728fc8702d0491be263dee0cb822e32648bc33c405f9512e` |

[精确差异](assembly-reviewed.patch)相对8ad5e8e仅增加20行、五个RM_RNE专用双向mapping，置于原generic条款之前。独立移除这五条新增mapping后，两文件与8ad5e8e**逐字相同**，包括原generic双向条款；所有数值、flags、编码、合法性、寄存器写回和其他assembly逻辑未动，见[静态核验](assembly-source-static.json)。未改generic Isla representation或JSON schema。

五op分别为D.S、D.H、S.H、D.W、D.WU。前置专用条款只匹配RM_RNE，输出无RM文本；其余op/RM仍落入原generic。生成C的`zassembly_forwards`实际将专用分支放在generic之前并在成功后结束match；不是仅凭源顺序推测。原generic的旧显式`, rne`反向条款未被guard或删除，新无RM文本对应固定RM_RNE。源级预期保留全部72种旧op/RM族并增加5种canonical文字族。

## 独立实际验证

重新执行owner脚本，输出放本独审目录：

```sh
taskset -c 36 python3 agents/float_review_closure_20261102/validation/assembly-fix/probe.py \
  --output agents/float_review_closure_20261102/review/acceptance/assembly-independent
```

[结果](assembly-independent/result.json)：baseline与候选均实际Sail类型检查、生成C并编译；baseline首个旧显式RNE正向结果不符合新canonical要求而退出1，候选1104/1104正向通过。覆盖五目标op×六RM×全部32源/目的寄存器，以及触及映射的其余七op和S.W负对照×六RM×三组寄存器。probe抽取实际生产enum、mnemonic与assembly条款，寄存器名字映射在隔离probe中固定为f0–f31/x0–x31，因此不额外声称ABI名字或Zfinx运行已验。

独立追加`-D SYMBOLIC`的严格类型检查、C生成、编译和执行，[实际命令与结果](assembly-independent/current/symbolic-generated.json)显示1104项输出与ordinary逐项相同。此处是抽取映射的实际生成/执行，不是完整模型ordinary/SYMBOLIC严格生成；后者按提交后的正式生成流程另验。

[audit_assembly_toolchains.py](audit_assembly_toolchains.py)读取上述实际Sail输出并按机器码字段独立构造预期，批量交GNU/Clang汇编并提取字节，共[5824项指令核对](assembly-toolchains-independent.json)全部匹配：Clang 1104条助记符；GNU 304条canonical/负对照助记符；两工具链各1104条`.insn`及字节表示。800条非零RM精确转换的GNU助记符能力边界由先前[112个实际探针](exact-conversion-syntax-independent.json)证明；本次对它们验证精确`.insn`/字节，未删除RM改机器字。D.L、D.LU、S.W仍保留显式RM并在两工具链精确汇编。

## 反向动态能力限制

初稿directional拆分因Sail效应分析使正向调用也成为NonExec，已撤销；相关静态差异另存`*-directional.*`。最终采用五个专用双向条款在前、原generic逐字保留的更小表达，不修改编译器。

实际工具链`effects.ml:176/219`把P_string_append标为NonExec，普通函数调用`assembly(string)`会被拒，baseline亦同。不能给测试加`$non_exec`后声称运行通过。当前解释器的`Semantics.v:917`/`extraction/Semantics.ml:846`对该模式仍是TODO空绑定，不能作为替代反向验收。

独立对最终映射抽取进行REPL反向诊断，canonical及显式rdn均产生Runtime type error；Sail进程仍退出0，见[诊断](assembly-interpreter-result.json)和[原始日志](assembly-interpreter.log)。因此本审查没有将进程0、类型通过、源码保留或工具链汇编误称为Sail反向执行PASS。反向只签新专用条款固定RNE及原generic字节保留的源码合同；动态反解析仍未验证。

下一阶段必须用新提交重生成并冻结IR/inputs，实际JSON验证五op的canonical与精确表示选择，再执行完整Clause预算。8ad5e8e的数值/状态证据保留其旧版本，不能直接改成21418d0的新动态PASS。
