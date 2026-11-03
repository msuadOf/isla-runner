# 剩余特殊行为控制流恢复

目标：NaN/sNaN/qNaN 分类、格式转换 canonical NaN、活动 lane 对运算与异常贡献的选择使用真实显式分支。普通数值公式、FMA 单次舍入、异常集合 OR 保持。

范围：仅修改 float 模型工作树；根 sail-riscv 未提交内容不得触碰。修改 core/ieee_fp_exceptions、FD 三格式实现、V 三类运算文件与 BF16 转换/运算文件。accrue_fflags changed、窄整数饱和 overflow 保留 ITE，其超时由另一调查负责。

步骤：源码结构红测；最小行为分界修改；独立 GPT-6.1 Sol 审查与普通严格检查；按模型文件分类提交；干净提交四配置严格 SYMBOLIC 重生；主 agent 安装并审计 IR、运行代表 Clause 与双工具链检查。普通缓存使用平面完整路径。

风险：每个源独立分类会产生真实的类别组合；每 lane 活动分支可能使路径相乘。小初态域测试不能替代完整域预算。异常 flags 位打包、Inf 抵消等尚无本轮显式化承诺；BF16 融合边界只验证，不添加人为分支。

验证：完整 Clause 外限和 SMT 限时均7200秒；禁止静默缩短预算或用超时前 JSON 数称完整通过。SOURCE region 与注释锚点按行号迁移并逐项核对。
