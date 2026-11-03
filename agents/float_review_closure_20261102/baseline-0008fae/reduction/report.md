# IEEE 异常纯输出分支最小化：源码候选

受测模型为独立 named 树 `.worktree/sail-riscv-general-float-by-model-20261022`，基线提交 `21418d0b0d4942fae20061ed580ee04aff4a8a61`。只改 `model/core/ieee_fp_exceptions.sail`：原文件 SHA-256 `23fda9824c2280609062bbe2b9766597681c29af13a1e9cf1be045d9106757a8`，候选 `866f85a607b112d57a0ea8c6d9a85c1befb36ef11ea39b7058a252606df257cd`。完整差异见 [source.diff](source.diff)，16行增加、74行删除。冻结的 runner-float 214 模型和77条正式长跑未写；本候选未提交、推送或生成全模型IR。

根据两位独立审查的精确合同，三个rounded及exact_threshold末端共12处OF→UF→NX纯输出if改为原三位`ieee_exception_facts`数据构造；三个round的NX和fp_to_int_core有效臂NX共4处改为原Bool字段；两个ROD helper共2处jam改回RTZ base上的原`ite`选位。没有重算lo/hi、阈值、tiny、inexact、flags或ROD base。18个if仅选择返回位，不决定NaN/Inf/零/invalid原因、finite/valid入口、饱和或架构写回；这些控制均保留。

六个跨格式/BF16/ROD有限臂的`ieee_mask_exact_exceptions(invalid_nan,true,facts)`直接返回`facts`，随后删除无其他生产调用的helper。此处等价需要三项联合前提：外层finite分支表示指数非全1，故源不是NaN且`ieee_operand_invalid(false,a)=false`；六处传入的exact facts来自阈值helper，其NV和DZ均为false；mask的finite实参为字面true。`git grep`在受控模型树中只找到该helper定义和六调用，test与preserve没有直接引用。原根仓正式IR检查器还有三处旧结构依赖，须由主流程对新候选调整；旧214版证据原样保留。

[先红后绿脚本](check_reduction.py)在原214源码的f16 rounded目标结构断言退出1，记录在 [红测](tdd-red.log)；在候选退出0，见 [绿测](tdd-green.log)。它穷举8种任意OF/UF/NX组合、4种invalid/NX组合和131,072种16位ROD base/NX组合；并核371条`let`起始表达式与冻结文件一致、14函数的目标返回结构以及mask调用/定义消失。测试不假设OF⇒NX或OF/UF互斥。机械改写脚本有固定基线SHA及每处匹配次数断言，见 [apply_reduction.py](apply_reduction.py)。

`sail --fmt-only core/ieee_fp_exceptions.sail --fmt --fmt-emit stdout > /dev/null`在该模型`model/`目录退出0；`git diff --check`退出0，工作树只有指定生产文件被修改。这里仅签局部源码结构与布尔等价；完整Sail类型检查、新IR控制流和动态结果仍待主流程重新冻结验证，不沿用214版PASS，也不声称性能提高。
