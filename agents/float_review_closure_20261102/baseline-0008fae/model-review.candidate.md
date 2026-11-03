# 最小化候选源码独审

源码审查通过，无剩余源码阻塞。受审对象为独立named模型树`.worktree/sail-riscv-general-float-by-model-20261022`，基于模型`21418d0b0d4942fae20061ed580ee04aff4a8a61`；受审文件`sail-riscv/model/core/ieee_fp_exceptions.sail` SHA256为`866f85a607b112d57a0ea8c6d9a85c1befb36ef11ea39b7058a252606df257cd`。签字按内容哈希，主agent随后提交不改变该结论的适用内容。

审查者从214 Git对象独立重建[最小性裁决](model-review.md)的全部替代，未使用实现者的重写结果作预期。候选完整文件去空白/行注释后与独立预期逐字相同；唯一受控模型差异为该文件，14个既有函数改变、删除mask函数1个，无其他模型函数增删或数值算式变动。实际补丁为16行增加、74行删除。

18处局部纯返回条件已恢复数据流：4个rounded/exact_threshold末端改为同一OF/UF/NX facts，三个round与fp_to_int_core有效臂仅直接构造原NX，两个ROD jam改回原ITE。保留全部NaN/Inf/零/invalid原因、finite/valid、饱和、changed、ROD模式和数学表达式。六个有限臂mask调用直接返回原facts，定义删除；有限源必非NaN且exact facts的NV/DZ恒false，因此不是仅凭实参true删除字段覆盖。

独立重跑8个任意OF/UF/NX元组、4个invalid/NX元组和131072个16位jam组合均等价；不假定OF⇒NX，不假定OF/UF互斥。32位jam适用同一逐位恒等式。模型全仓test/preserve无mask直接引用；新checker应更新旧的三处结构依赖，旧214检查器与结果保留历史署名。

冻结runner-float模型HEAD仍为21418d0，166个受控模型文件现场哈希逐一与其生成源码清单一致，均未改变。本次只签源码范围和局部静态等价；**尚未签Sail strict、新IR、数值/完整Clause动态验证或性能**。后续结果须绑定新commit/IR/inputs；现有214版77项运行继续记录214，不迁作新候选通过。

可复核证据：[独立脚本](model-review.candidate.py)、[机器报告](model-review.candidate.json)。第二Sol的[独立意见](control-opinion.md)对18处替代及mask前提交叉一致。
