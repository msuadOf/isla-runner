# 动态验收独立预审

当前仅签验证方法的准备边界；新 IR 动态结果、64 条完整 Clause 预算均未签收。独立审查者不改生产源码，也不启动未经冻结的长测。源码与 IR CFG 由另一独立 Sol 单独签收。

受审入口：[验证方案](../../inventory/validation_plan.md)、[执行规程](../../validation/procedure.md)、[矩阵](../../validation/matrix.md)、[完整 Clause 启动器](../../validation/run_clause.py)。源码阶段已签模型 `8ad5e8e` 与 Isla `42000be`，它们不构成本阶段 PASS。

## 已发 owner 的边界

- flags：helper 直接隔离 changed 真/假，old=0/new=0、同位、首次新增、旧异位新增；FS Initial/Clean/Dirty、SD 与其他 mstatus 位；FFLAGS OR 与两个 callback 顺序。指令写 FPR 可独立置 Dirty，不能据此替代 helper 状态证明。
- conversions：六窄和十二 FP→整数包装各查真实源位串、结果/flags、可达边界、五 RM/RTZ、NaN/Inf；f16→ui16 有限正 overflow 不可达，f16→宽 signed 整数有限 overflow 不可达。向量完整目的组、mask/multi-lane/prestart/tail/vstart 与合法 LMUL 分列。RV64 scalar 32 位整数写回含 sign extension。
- exceptions：H/S/D 分开核算术异常原因与正常对照，独立 SoftFloat 对实际 result/flags；两个 ROD 宽度核 exact/inexact、低位0/1、五 RM 对照、tiny/OF/NaN；BF16 三源与融合、多 lane/mask。相同 NaN 结果不合并不同 NV 原因。
- representations/make：最终真实 JSON 的助记符、位串、.insn 分别用 GCC/Clang 提取机器字对比；Illegal 合法表示合同分列。真实 Make recipe 必须执行最终程序和 IR，保存命令、环境、退出、summary、JSON 和哈希。
- full Clause：重算最终调用闭包，64 受影响和13保守兼容分别计数；每条原完整域，T1/qffp/seed17，整 Clause 与 SMT 均7200秒。固定域定向样例不能替代预算结果；有限样例不能外推全域。

## 启动前待修的证据门

`run_clause.py` 初稿仅检测 seed 日志含 random_seed，且对缺失 summary 字段默认为0。已通知 owner：解析实际 seed 日志 fixed=17；必需 summary 字段存在且类型正确，核实际 gen 数及 Retire/Illegal 分类；规程统一64+13分母。owner 已确认会在正式运行前修正，当前无新完整 Clause 运行。

## 签收条件

每批固定模型/Isla commit、IR/config/binary/oracle/官方库/seed 拦截器及脚本哈希；核实际输出的 input-manifest 与命令一致。按新输出独立重算数值、flags、状态与编码，保留失败/超时和诊断。最终报告分别列阻断、非阻断与覆盖未验证；旧 PASS 不继承。
