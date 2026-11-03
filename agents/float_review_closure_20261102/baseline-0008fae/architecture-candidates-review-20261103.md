# 新准则下回数据流准备候选的源码独审

**议题目录内三个候选通过源码/公式审查，没有生产实施许可。** 审查对象位于[候选目录](reduction/new-policy/)，基准是冻结e9，回退表达式对照6202精确Git对象。最新架构裁决见[逐项记录](architecture-decision-20261103.md)。所有OPEN项仍OPEN，不借局部源等价签字将它们批准。

- 异常候选`candidate-ieee_fp_exceptions.sail` SHA256 `7ed9529baac57717875ea49e8fff5130d3ec611f824aa71483b2b856d67c96b4`：只改18个算术异常函数体，删除33个仅返回NV/DZ的原因if，保留finite/valid gate。独立从候选实际let/返回式递归展开，逐个5字段与6202原式核同；任意NV/DZ/gate/OF/UF/NX共64个组合，原gate掩码与候选gate返回事实相等，不需要OF⇒NX或互斥假设。90个FP数值let与e9和6202相同，所有其他源字节等于e9。每源NaN分类调用的参数与顺序不变；FMA的`invalid_nan OR (zero_inf OR inf_cancel)`恢复原式，0×Inf搭配qNaN/sNaN加数仍NV，div的NV与DZ为独立事实字段，未因去优先分支而覆盖。
- 12整数wrapper候选：每目标函数逐字等于6202；将这12个函数置回e9整文件后，分别与三个实际候选文件逐字相同，非目标字节与两个ROD模式函数保持e9。独立12288个invalid/NaN/sign/candidate/flags组合全部相等，含负NaN必须正端点、unsigned负数0、signed负端点及valid候选保留。flags打包来源与数值计算没有改变。
- 六窄候选`candidate-vext_fp_utils_insts.sail` SHA256 `34191de93086708b44f552606b39878e1ad68be07c67fb2321eb7bec1b1172e1`：完整文件逐字等于6202，普通native六函数及6202既有f16→I16外overflow if保留，回掉本轮八个新增纯返回if。这是已核原表达式的精确回置，不将既有外if的OPEN擅自裁成KEEP。

三个候选的精确哈希、逐函数证明、全部组合计数见[机器结果](architecture-candidates-review-20261103.json)，[审查脚本](architecture-candidates-review-20261103.py)只写自身审查结果。异常证明直接读取实际候选公式，不以手写理想模型替代源合同；wrapper证明同时以精确Git体及独立选择真值核对。每次审查结束现场e9与214全部受控模型文件仍与各自生成来源清单相等。

未签内容：生产应用、Sail strict、新IR/CFG、新动态/77项Clause预算、性能、finite/valid/changed/ROD模式等OPEN架构接纳。候选进入新模型树须由主agent另行授权；旧e9/214的受测结果不改署这些尚未生成的候选。
