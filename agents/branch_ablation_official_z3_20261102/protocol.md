# 新官方Z3下控制变量消融

A=当前ITE/严格布尔聚合，B=仅恢复该项显式if/短路。模型9c339044及旧已核验完整IR变体不变（nan_unbox已恢复）；重用旧IR必须再验证sha及函数差异，不冒称重新生成全模型。运行程序先冻结当前正式Release（包含已验证CLI/Make改动，尚未包含本轮review修复），以其SHA与上一轮正式切库记录逐字核对；新官方Z3 1fd1d3613，库SHA固定。修复程序另目录，不混入实验。

每workload三对AB/BA/AB，单线程，每对固定独立物理CPU且两臂不迁移；最大12个pair同时运行。各workload有独立输入/预算，不同workload允许并行。完整Clause总墙钟7200秒，外层TERM后10秒KILL；显式--smt-timeout 7200s，无更短路径预算，不设额外采样/配额，两臂输入/初态域/solver tactic相同，固定使用qffp（当前浮点Make配置）。本轮与旧qfaufbv结果不混算，新旧solver+执行策略改变只发生于不同实验轮。

种子控制：Isla原fresh_random_seed取时间。仅在冻结实验程序进程使用LD_PRELOAD拦截Z3_params_set_uint，将seed/random_seed设为每pair固定值17/29/43；A/B同seed，所有solver保持一致。不改生产源码。独立日志证实替换发生，真实时间/预算不劫持。Rust hash容器和共享主机噪声仍可能影响路径/模型，重复和CPU/user时间一起报告，不声称完全确定性或独占CPU。初期试跑/短例用于验证runner，不混入三次正式数据。无新增长预热。

14 workload：flags比较/算术，min/max、minm、maxm，mask与顺序归约，NaN结果规范化、转换饱和、class，valid/normal/reduction窄域guard以及normal宽域。严格的性能结论须检查两臂均finished、错误/超时、状态域相同；输出集合不同时时间比只能作为时间/条件见证取舍，不能写等覆盖加速。记录user/sys/RSS、原JSON、输入/源码差异/版本/库/环境、见证类别及不可靠fork总数说明。每次结束自动更新summary/report；外限/partial不作完成耗时比较。
