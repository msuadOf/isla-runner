# 显式分支组合 Clause 验证

状态：complete；更新时间 2026-11-01T20:52:17.851147+00:00。

单次组合正确性及预算验收，不是单变量性能实验。完整 Clause 外限和 SMT 均7200秒；qffp、T1、固定种子17。

|Clause|状态|秒|JSON|Retire|非法|partial|目标类别|
|---|---|---:|---:|---:|---:|---|---|
|F_BIN_TYPE_F_S|PASS|59.715|36|36|0|False|{'NaN:finite/nan': 2, 'NaN:nan/finite': 2, 'NaN:nan/nan': 2, 'NaN:nan/zero': 2, 'NaN:zero/nan': 2, 'finite_lt': 2, 'other_opcode': 12, 'zero_pair:0/0': 6, 'zero_pair:0/1': 2, 'zero_pair:1/0': 2, 'zero_pair:1/1': 2}|
|FMINM_S|PASS|30.359|12|12|0|False|{'NaN:finite/nan': 1, 'NaN:nan/finite': 1, 'NaN:nan/nan': 1, 'NaN:nan/zero': 1, 'NaN:zero/nan': 1, 'finite_eq': 1, 'finite_lt': 1, 'zero_pair:0/0': 3, 'zero_pair:0/1': 1, 'zero_pair:1/0': 1}|
|FMAXM_S|PASS|15.471|12|12|0|False|{'NaN:finite/nan': 1, 'NaN:nan/finite': 1, 'NaN:nan/nan': 1, 'NaN:nan/zero': 1, 'NaN:zero/nan': 1, 'finite_eq': 1, 'finite_lt': 1, 'zero_pair:0/0': 3, 'zero_pair:0/1': 1, 'zero_pair:1/0': 1}|
|F_UN_RM_FF_TYPE_S|PASS|150.914|36|30|6|False|{'result_finite': 9, 'result_nan': 20, 'result_zero': 1}|
|FVVTYPE|PASS|3121.758|329|293|36|False|{'masked_active_only': 117, 'masked_inactive_only': 9, 'masked_mixed': 50, 'unmasked': 117}|
|RFVVTYPE|PASS|290.252|184|172|12|False|{'masked_active_only': 66, 'masked_inactive_only': 4, 'masked_mixed': 36, 'unmasked': 66}|
|VFUNARY1|PASS|1880.107|520|504|16|False|{'class_bit_0': 11, 'class_bit_1': 10, 'class_bit_2': 17, 'class_bit_3': 10, 'class_bit_4': 10, 'class_bit_5': 17, 'class_bit_6': 10, 'class_bit_7': 10, 'class_bit_8': 17, 'class_bit_9': 12, 'class_other_0x0': 76, 'other_opcode': 304}|

初态、flags、原始命令、返回值、错误及旧 A/单项 B 类别对照分别见各工作负载 result.json。

只有自然退出0、summary=finished且所有错误/截断计数为0才标为PASS；JSON条数不是fork数。

七Clause均采用新组合IR；历史A/B来自冻结的旧程序，故只比较见证类别，不能用于净性能归因。
