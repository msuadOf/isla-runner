# 饱和 overflow 与活动 lane 交叉控制

目标：在相同 Clause、状态域和 7200 秒预算下，检验旧显式 overflow 超时是否由不活动 lane 提前计算放大，并区分当前活动 gate 与旧模型其他变化。

范围：仅本目录冻结实验 IR、旧模型副本、脚本和日志；不改生产源码、旧实验输入或原结果。使用旧官方 Z3 冻结 isarch、QFFP、T1、seed17、同一 sat 配置，外层 Clause 与 SMT 均 7200 秒。

步骤：

1. 当前 `a9fd947` 的 v128 IR 作 A；B 仅替换 `riscv_f16ToI16_pure` 的 overflow ITE 出口为旧显式 if，对两臂做字节与 CFG 审计。
2. 同物理核顺序 AB/BA 交叉重复；独立 C API 插桩记录每个 Z3 check 及 unknown，逐臂核对退出码、完整 Clause 摘要和 JSON。带 fork 日志的另一次运行只用于定位，不混入耗时配对。
3. 从旧 `9c339044` + overflow-if 冻结模型复制一份，只改 `VFUNARY0` 的活动 gate；严格生成 IR，并与旧 B IR 核对函数差异，然后用相同配置运行完整 Clause。旧基底 gate 前后是更严格的单变量因果对照。

旧基底严格 IR 已生成并三次自然完成。原生 fork 日志只给实际分支事件，不当作完整全局路径数。
