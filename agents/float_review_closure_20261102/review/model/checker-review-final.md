# 永久CFG检查器最终独审

签收候选 `check_float_closure_branches.py` SHA256 `48f80379dc69ba376febc3e373a6abd5c44d59ce39513015598529f02e5ba886`。实际新IR另有独立CFG证据，本页只签检查器实现及红绿结果，不代替动态数值验收。

独立运行 `python3 isla/test/float_ir/check_float_closure_branches.py --ir <21418d0生成IR>` 与迁移后的 `check_special_semantic_branches.py`，四配置全部 exit 0。闭环检查器覆盖RV64的54个目标、RV32实际52个目标；RV32缺失两项只允许从IR中核实XLEN32后的f16→I64/Ui64特例。旧IR `a877e245…` exit 1，明确因 changed 没有目标Jump拒绝。记录见 [同一冻结源码快照的四配置结果和旧IR红](checker-final-positive-frozen-21418d0.json)。

源码核查确认：changed直接比较old与old|flags，FS/SD由changed与Ext_F控制；六窄化谓词核源值/位宽/符号扩展、上下端点、NV与正常flags/低位；12整数包装核invalid→NaN→符号层级；ROD核模式6、有限源flags合流、NX控制的base|1及两个出口；OF/UF/NX保留各自事实，不假定OF必带NX；exact_threshold、fp_to_int_core、round、跨格式/BF16 gate全部纳入。源分类先于行为Jump且通过移除节点的可达性核真正支配关系。原special检查保留源角色、quiet/ordered模式、NaN出口、单次FMA和20个活动lane gate，run.py已同时调用两个检查器，README说明与代码一致。

18个算术异常helper的原因/finite谓词从实际IR纯Bool树求值，对H/S/D各12类带符号normal/subnormal/zero/Inf/sNaN/qNaN逐项比对原因合同，FMA遍历12³组合。符号位、非零、有限性及源角色均参与求值；未知变量或操作直接失败。各原因Jump真臂同时精确核NV出口，div第三项精确核DZ出口，避免仅谓词正确而flags返回错误。

本审查保留16个独立负变异，最终全部拒绝：旧值自比较、合并值自比较、SD清零、除法原因/finite误接、窄化自比较、乘法AND改OR、add符号反转、OF/NX互换、ROD丢base、FMA积符号反转、sqrt误判负零，以及add/mul/sqrt/FMA原因出口清NV。见 [负控脚本](audit_checker_negative_controls.py) 与 [结果](checker-negative-controls.json)。较早候选的误绿记录保留历史，最终签字只适用于上述哈希。

限制：此检查器对既定控制合同作结构/纯分类语义回归；不声称证明所有浮点数值公式，动态campaign及官方Z3结果由对应验收者负责。`8ad5e8e`→`21418d0`的54/52个语义目标IR规范化后相同，但动态记录仍按实际受测版本单列。

最终`48f80379…`在`cf9e9a0f…`基础上另核源分类调用从入口可达，避免无行为Jump时死代码调用满足数量断言。最终正控/旧IR均使用同一冻结模块对象，现场哈希复核一致；负控脚本同样一次读取并保存源码快照。
