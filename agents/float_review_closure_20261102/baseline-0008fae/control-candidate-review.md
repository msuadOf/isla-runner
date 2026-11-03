# 最小候选：第二Sol源码签收

**源码签收通过，无源码阻断。** 独立named模型树以模型`21418d0b0d4942fae20061ed580ee04aff4a8a61`为基线，当前唯一受控差异是`model/core/ieee_fp_exceptions.sail`，候选SHA-256 `866f85a607b112d57a0ea8c6d9a85c1befb36ef11ea39b7058a252606df257cd`。按该内容哈希签收；此后提交若不改内容，结论仍适用。

第二审查者未调用实现者或第一审查者的改写/审计代码。从214 Git对象独立按[控制意见](control-opinion.md)重建完整期望文件，与现场候选**逐字节相同**，无需忽略空白或注释。独立确认14个函数修改、仅删除mask函数1个、371条let起始表达式原样；18个纯返回if恢复facts/原ITE，另删除mask定义内1个恒真调用下不再需要的if。所有其他源码均未改变。

因此没有删除NaN/sNaN、Inf/零、invalid原因、finite/valid入口等必要控制。12整数饱和包装、flags changed架构写回和ROD/普通模式包装位于其他文件，与214逐字不变；源NaN canonical和原flags亦保留。六个去mask的调用仍严格位于源finite臂，源`ieee_operand_invalid(false,a)`为false；传入的exact facts来自相同阈值helper，NV=DZ恒false。三项前提共同保证直接facts与mask覆盖字段完全一致，不是仅以字面true为由删除mask。

独立重跑8个任意OF/UF/NX元组、4个invalid/NX元组、全部131,072个16位base/NX jam组合，无差异；不假定OF⇒NX或OF/UF互斥。32位jam适用同一逐位恒等式。另核源f32/f64指数与四类mantissa代表的9,208项finite分类前提，以及8种facts字段mask恒等；分类证明本身来自finite=`exp!=all_ones`与NaN=`exp==all_ones && mantissa!=0`互斥，不能把代表值检查当作全mantissa穷举。全受控`model/test/preserve`已无mask引用；旧固定Jump数检查须由新candidate验证流程同步修订。

执行命令：`python3 agents/float_review_closure_20261102/baseline-0008fae/control-candidate-review.py`，退出0；脚本还执行`git diff --check`并核冻结runner-float核心源码与214 Git对象逐字相同。见[独立脚本](control-candidate-review.py)、[机器结果](control-candidate-review.json)。该审查未写任何生产源码、IR或inputs。

本签收仅覆盖候选源码和局部布尔/位向量等价，**不签尚未执行的新strict、IR、动态或性能结果**。去纯输出分支可能减少自然路径见证；需另按新覆盖口径验证。214版长跑及定向动态证据仍只属于214版，不迁署给本候选。
