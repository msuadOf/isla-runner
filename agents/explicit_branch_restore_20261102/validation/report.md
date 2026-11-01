# 显式分支组合 Clause 验证

状态：running；更新时间 2026-11-01T20:06:47.511413+00:00。

单次组合正确性及预算验收，不是单变量性能实验。完整 Clause 外限和 SMT 均7200秒；qffp、T1、固定种子17。

|Clause|状态|秒|JSON|Retire|非法|partial|目标类别|
|---|---|---:|---:|---:|---:|---|---|
|F_BIN_TYPE_F_S|PASS|59.715|36|36|0|False|{'NaN:finite/nan': 2, 'NaN:nan/finite': 2, 'NaN:nan/nan': 2, 'NaN:nan/zero': 2, 'NaN:zero/nan': 2, 'finite_lt': 2, 'other_opcode': 12, 'zero_pair:0/0': 6, 'zero_pair:0/1': 2, 'zero_pair:1/0': 2, 'zero_pair:1/1': 2}|
|FMINM_S|PASS|30.359|12|12|0|False|{'NaN:finite/nan': 1, 'NaN:nan/finite': 1, 'NaN:nan/nan': 1, 'NaN:nan/zero': 1, 'NaN:zero/nan': 1, 'finite_eq': 1, 'finite_lt': 1, 'zero_pair:0/0': 3, 'zero_pair:0/1': 1, 'zero_pair:1/0': 1}|
|FMAXM_S|PASS|15.471|12|12|0|False|{'NaN:finite/nan': 1, 'NaN:nan/finite': 1, 'NaN:nan/nan': 1, 'NaN:nan/zero': 1, 'NaN:zero/nan': 1, 'finite_eq': 1, 'finite_lt': 1, 'zero_pair:0/0': 3, 'zero_pair:0/1': 1, 'zero_pair:1/0': 1}|
|F_UN_RM_FF_TYPE_S|PASS|150.914|36|30|6|False|{'result_finite': 9, 'result_nan': 20, 'result_zero': 1}|
|FVVTYPE|running|||||||
|RFVVTYPE|PASS|290.252|184|172|12|False|{'masked_active_only': 66, 'masked_inactive_only': 4, 'masked_mixed': 36, 'unmasked': 66}|
|VFUNARY1|running|||||||

初态、flags、原始命令、返回值、错误及旧 A/单项 B 类别对照分别见各工作负载 result.json。

只有自然退出0、summary=finished且所有错误/截断计数为0才标为PASS；JSON条数不是fork数。

七Clause均采用新组合IR；历史A/B来自冻结的旧程序，故只比较见证类别，不能用于净性能归因。
