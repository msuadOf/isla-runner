# e9d69d2永久检查器独审

**最终新版检查器签收，无剩余阻塞。** `isla/test/float_ir/check_float_closure_branches.py` SHA256为`053b48b3b588c58f87d74a72c7a5d5097a610ccea37700d94380142fede5ad16`，README为`1ef9be2c99ddb649b2300e1912d856c15d9c5af6de0bf27c51e261483af1745d`；special和run字节仍等于旧签收的`af14d3cb…`、`d78fe01d…`。生成脚本与审计脚本的named模型路径已核，见[脚本审计](model-review.generation-scripts-e9d69d2.json)。

新版合同接受纯flags/jam值计算，取消旧的OF→UF→NX层级、round/FPint末层NX及ROD jam必须Jump的要求；mask helper删除后不再要求其存在。它保留changed/Ext_F写回、六窄饱和、18个异常原因与源分类、整数包装饱和、ROD模式及finite/valid gate的控制关系。新测试在纯rounded/exact末端禁止再新增Jump，是按本次最小生产结构的回归约束，不是声称所有等价浮点公式都不能使用条件。

检查器对rounded返回的OF/UF/NX字段和来源逐项核对；NX的两个FP相等比较必须分别是lo/hi对同一个扩宽目标结果，UF必须结合独立tiny和同NX。round和FPint的NX对原始值/舍入结果及raise_inexact因果核对。ROD非有限flags明确保留`operand_invalid(false, za)`，有限flags必须将exact facts汇入同一返回变量，ITE必须由该合流flags的NX选择原`base|1/base`。转换/BF16有限臂直接返回exact facts，非有限出口保留源quiet NaN分类。无“只要出现OR/ITE/一个source call就通过”的替代。

审查者单次加载冻结源码模块，检查e9四配置与原special检查共8项均通过；新闭环检查器覆盖RV64各53个目标、RV32实际51个目标，少的一项是已删除mask，RV32另沿用严格XLEN32/f16→I64/Ui64例外。旧a877 IR因缺changed Jump拒绝。见[正控/旧IR红证据](model-review.checker-positive-e9d69d2.json)及[可重跑脚本](model-review.checker-positive-e9d69d2.py)。尚未安装的e9 IR通过显式路径核查，不把根目录默认run.py全套检查冒称已对新安装资产运行。

31个独立定向负变异全部拒绝，见[负控记录](model-review.checker-negative-e9d69d2.json)与[脚本](model-review.checker-negative-e9d69d2.py)。保留的旧负控覆盖changed两种自比较、SD、窄化、特殊原因、FMA积符号、sqrt负零和NV出口；新负控覆盖OF/NX返回字段互换、lo==lo/x==x假NX、UF替成NX&&NX、raise_inexact合取误改析取、ROD改由NV选择jam/精确臂也jam/丢base/丢两臂flags，以及round/convert/ROD的quiet误改signaling。每次均保存准确checker源码快照，结果对应同一最终哈希。

旧214 checker与新e9 IR互不符合既定结构；新checker也拒绝旧214的纯输出Jump。两者仅是版本合同不匹配，不能把这些拒绝说成214计算有错，见[版本分离证据](model-review.checker-schema-e9d69d2.json)。旧214四文件原字节快照已独立核与manifest一致，原源审/IR/动态签收保留其版本。

本检查器是针对已核数值公式/控制合同的静态回归，不是通用FP数学证明器；FP原语、阈值数学与最终后态由源码精确变换、[实际IR表达式核对](ir-review-e9d69d2.md)及独立动态oracle分阶段支持。完整Clause预算和性能不在本页签字范围。
